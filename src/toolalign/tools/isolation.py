"""Owned spawn processes with bounded file IPC, monotonic waits and real reaping.

This is process/lifetime isolation for trusted local implementations, not an OS
security sandbox for arbitrary code. No PID discovery, process groups or futures.
"""

from __future__ import annotations

import multiprocessing
import os
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from toolalign.tools._json import INPUT_BYTES, decode, encode


class CancellationToken:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        self._event.set()

    def is_cancelled(self):
        return self._event.is_set()


def utc_remaining(expiry):
    try:
        value = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        if value.tzinfo is None or value.utcoffset().total_seconds() != 0:
            raise ValueError
        return (value - datetime.now(timezone.utc)).total_seconds()
    except (AttributeError, ValueError, TypeError) as exc:
        raise ValueError("Deadline must be UTC") from exc


def write_packet(path, value, limit=INPUT_BYTES):
    raw = encode(value, limit)
    staging = path.with_suffix(".pending")
    with staging.open("xb") as stream:
        stream.write(raw)
    staging.replace(path)


def read_packet(path, limit=INPUT_BYTES):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    return decode(raw, limit)


class OwnedProcess:
    """Every stop acts only on the exact multiprocessing.Process started here."""

    def __init__(self, root, target, arguments, label):
        root = Path(root)
        if not root.is_absolute() or root != root.resolve(strict=True) or not root.is_dir():
            raise ValueError("Sandbox root must be an existing resolved directory")
        self._temporary = tempfile.TemporaryDirectory(prefix="toolalign-owned-", dir=root)
        self.directory = Path(self._temporary.name)
        self.owner_id = uuid.uuid4().hex
        self.process = multiprocessing.get_context("spawn").Process(
            name=f"toolalign-{label}-{self.owner_id}",
            target=target,
            args=(str(self.directory), *arguments),
            daemon=True,
        )
        self.record = {
            "owner_id": self.owner_id,
            "label": label,
            "pid": None,
            "exitcode": None,
            "reaped": False,
            "stopped": False,
            "directory_cleaned": False,
        }
        self._process_closed = False
        self._closed = False
        try:
            self.process.start()
            self.record["pid"] = self.process.pid
        except BaseException:
            self.close()
            raise

    def wait(self, filename, expires_monotonic, cancellation):
        path = self.directory / filename
        while True:
            if cancellation.is_cancelled():
                return "cancelled", None
            remaining = expires_monotonic - time.monotonic()
            if remaining <= 0:
                return "timed_out", None
            if path.exists():
                try:
                    return "completed", read_packet(path)
                except (ValueError, OSError):
                    return "error", None
            if not self.process.is_alive():
                if path.exists():
                    continue
                return "error", None
            time.sleep(min(0.01, remaining))

    def close(self):
        if self._closed:
            return
        if not self._process_closed:
            process = self.process
            if process.pid is not None:
                process.join(timeout=0.05)
                if process.is_alive():
                    self.record["stopped"] = True
                    process.terminate()
                    process.join(timeout=0.2)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
                if process.is_alive():
                    raise RuntimeError("Owned child could not be reaped")
                self.record["exitcode"] = process.exitcode
                self.record["reaped"] = True
            process.close()
            self._process_closed = True
        # Directory cleanup can fail after the process handle has been closed.
        # A later retry must only repeat the unfinished directory cleanup.
        self._temporary.cleanup()
        self.record["directory_cleaned"] = True
        self._closed = True


def enter_child(directory):
    os.chdir(directory)
    os.umask(0o077)
