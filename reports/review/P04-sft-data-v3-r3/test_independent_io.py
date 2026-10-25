"""Original bounded I/O checks for the exact nonregular-read revision."""
from __future__ import annotations

import errno
import hashlib
import json
import os
import select
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from toolalign.data.common import DataError
from toolalign.training.sft import data_v3 as v


def now():
    return datetime.now(timezone.utc).isoformat()


def race_child(root, kind):
    target = root / "replaced-original-file"
    target.write_bytes(b"")
    other = root / "original-symlink-target"
    other.write_bytes(b"original fixture target")
    original_open, original_fdopen = os.open, os.fdopen
    descriptors, flags_seen, reads = [], [], []

    class ObservedStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def fileno(self):
            return self.stream.fileno()

        def read(self, *args):
            reads.append(args)
            return self.stream.read(*args)

    def swapped_open(path, flags, *args, **kwargs):
        assert Path(path) == target and not flags_seen
        flags_seen.append(flags)
        assert flags & os.O_NONBLOCK and flags & os.O_NOFOLLOW
        target.unlink()
        if kind == "fifo":
            os.mkfifo(target, 0o600)
        elif kind == "symlink":
            target.symlink_to(other)
        else:
            target.mkdir()
        fd = original_open(path, flags, *args, **kwargs)
        descriptors.append(fd)
        return fd

    def observed_fdopen(fd, *args, **kwargs):
        return ObservedStream(original_fdopen(fd, *args, **kwargs))

    v.os.open, v.os.fdopen = swapped_open, observed_fdopen
    error = None
    print("READY", flush=True)
    start = time.monotonic()
    try:
        v._read(target, size=0, content=False)
    except DataError as exc:
        error = str(exc)
    finally:
        v.os.open, v.os.fdopen = original_open, original_fdopen
    assert error == ("v3_regular_file_budget" if kind == "fifo" else "v3_input_io_failure")
    assert not reads and len(flags_seen) == 1
    for fd in descriptors:
        try:
            os.fstat(fd)
        except OSError as exc:
            assert exc.errno == errno.EBADF
        else:
            raise AssertionError("Rejected object leaked its descriptor")
    current = target.lstat()
    assert (stat.S_ISFIFO(current.st_mode) if kind == "fifo" else
            stat.S_ISLNK(current.st_mode) if kind == "symlink" else
            stat.S_ISDIR(current.st_mode))
    print(json.dumps({
        "kind": kind, "error": error, "writer_calls": 0, "payload_read_calls": len(reads),
        "open_flags": flags_seen, "opened_descriptors": len(descriptors),
        "all_opened_descriptors_closed": True, "seconds": time.monotonic() - start,
        "module_origin": v.__file__,
        "module_sha256": hashlib.sha256(Path(v.__file__).read_bytes()).hexdigest(),
    }), flush=True)


@pytest.mark.parametrize("kind", ["fifo", "symlink", "directory"])
def test_replacement_before_open_is_bounded_and_closes_descriptor(tmp_path, kind):
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--race-child", str(tmp_path), kind]
    started = now()
    with (tmp_path / "child-stderr.log").open("xb") as stderr:
        child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=stderr, text=True)
        timed_out, ready_line, remainder = False, "", ""
        try:
            ready, _, _ = select.select([child.stdout], [], [], 15)
            assert ready, "Original child did not finish imports"
            ready_line = child.stdout.readline()
            assert ready_line == "READY\n"
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                timed_out = True
                child.kill()
                child.wait(timeout=5)
            remainder, _ = child.communicate(timeout=5)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
            child.stdout.close()
    (tmp_path / "child-stdout.log").write_text(ready_line + remainder)
    receipt = {"argv": argv, "pid": child.pid, "exit_code": child.returncode,
               "child_reaped": child.poll() is not None, "timed_out": timed_out,
               "started_at_utc": started, "finished_at_utc": now(), "writer_calls": 0}
    (tmp_path / "child-receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
    assert not timed_out
    assert child.returncode == 0, (tmp_path / "child-stderr.log").read_text()
    result = json.loads(remainder)
    assert result["payload_read_calls"] == result["writer_calls"] == 0
    assert result["all_opened_descriptors_closed"]
    assert result["module_origin"] == v.__file__
    assert result["module_sha256"] == hashlib.sha256(Path(v.__file__).read_bytes()).hexdigest()


@pytest.mark.parametrize("content", [True, False])
def test_hash_and_content_stay_on_original_descriptor_after_path_replacement(
    tmp_path, monkeypatch, content,
):
    target = tmp_path / "original-readable-file"
    original = b"R1 original descriptor bytes\x00\xff\n"
    replacement = b"R1 replacement path bytes, a different inode"
    target.write_bytes(original)
    old_fstat, captured = os.fstat, []

    def replace_after_open(fd):
        before = old_fstat(fd)
        captured.append(fd)
        assert len(captured) == 1
        target.unlink()
        target.write_bytes(replacement)
        return before

    with monkeypatch.context() as patch:
        patch.setattr(v.os, "fstat", replace_after_open)
        actual = v._read(target, digest=hashlib.sha256(original).hexdigest(),
                         size=len(original), content=content)
    assert actual == (original if content else None)
    assert target.read_bytes() == replacement
    with pytest.raises(OSError) as error:
        old_fstat(captured[0])
    assert error.value.errno == errno.EBADF


def test_growth_after_stat_keeps_byte_budget_and_closes_descriptor(tmp_path, monkeypatch):
    target = tmp_path / "original-growing-file"
    target.write_bytes(b"R1")
    old_fstat, captured = os.fstat, []

    def grow_after_stat(fd):
        before = old_fstat(fd)
        captured.append(fd)
        assert len(captured) == 1
        with target.open("ab") as stream:
            stream.write(b"original growth fixture" * 2)
        return before

    with monkeypatch.context() as patch:
        patch.setattr(v.os, "fstat", grow_after_stat)
        with pytest.raises(DataError, match="^v3_input_byte_budget$"):
            v._read(target, size=2, limit=8, content=False)
    with pytest.raises(OSError) as error:
        old_fstat(captured[0])
    assert error.value.errno == errno.EBADF


if __name__ == "__main__":
    assert len(sys.argv) == 4 and sys.argv[1] == "--race-child"
    race_child(Path(sys.argv[2]), sys.argv[3])
