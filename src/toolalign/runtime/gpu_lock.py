"""Advisory local-Mac flock shared by all worktrees of a Git repository.

All model entry points must cooperate. Expiry never breaks a held lock, and lock
files are never unlinked (unlinking can let two processes lock different inodes).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


class LockBusy(TimeoutError):
    """A model job already holds this repository's gpu0 lease."""


def lock_path(repository: str | Path = ".") -> Path:
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve() / "toolalign-runtime-locks" / "gpu0.lock"


def _open_lock(repository: str | Path):
    path = lock_path(repository)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Private metadata; do not follow a substituted final path.
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    os.set_inheritable(descriptor, False)
    return os.fdopen(descriptor, "r+", encoding="utf-8")


def inspect_gpu_lock(repository: str | Path = ".") -> dict:
    with _open_lock(repository) as handle:
        held = True
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            held = False
        except BlockingIOError:
            pass
        try:
            metadata = json.load(handle)
        except (json.JSONDecodeError, UnicodeError):
            metadata = None
        if not held:
            fcntl.flock(handle, fcntl.LOCK_UN)
        return {"held": held, "owner" if held else "last_owner": metadata}


class GPULease:
    def __init__(
        self,
        *,
        task_id: str,
        worker_alias: str,
        run_id: str,
        expected_job: str,
        memory_strategy: str,
        repository: str | Path = ".",
        timeout_seconds: float = 0,
    ):
        if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
            raise ValueError("Lock timeout must be finite and nonnegative")
        self.repository = repository
        self.timeout_seconds = timeout_seconds
        self.metadata = {
            "task_id": task_id,
            "worker_alias": worker_alias,
            "run_id": run_id,
            "expected_job": expected_job,
            "memory_strategy": memory_strategy,
        }
        self._handle = None

    def __enter__(self):
        if self._handle is not None:
            raise RuntimeError("Lease is not reentrant")
        handle = _open_lock(self.repository)
        deadline = time.monotonic() + self.timeout_seconds
        try:
            while True:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise LockBusy("gpu0 is busy; no model job was started") from None
                    time.sleep(min(0.05, max(0, deadline - time.monotonic())))
            process_started = subprocess.run(
                ["ps", "-p", str(os.getpid()), "-o", "lstart="],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            metadata = {
                **self.metadata,
                "pid": os.getpid(),
                "process_started_at": process_started,
                "host_fingerprint": hashlib.sha256(socket.gethostname().encode()).hexdigest(),
                "acquired_at": datetime.now(timezone.utc).isoformat(),
            }
            handle.seek(0)
            handle.truncate()
            json.dump(metadata, handle, sort_keys=True)
            handle.flush()
            self._handle = handle
            return self
        except BaseException:
            handle.close()
            raise

    def __exit__(self, *_):
        if self._handle is not None:
            fcntl.flock(self._handle, fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None
