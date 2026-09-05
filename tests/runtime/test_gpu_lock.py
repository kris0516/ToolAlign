import os
import subprocess
import sys

import pytest

from toolalign.runtime import GPULease, inspect_gpu_lock, lock_path


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    return repo


def lease(repo, **kwargs):
    return GPULease(
        task_id="P00",
        worker_alias="S0",
        run_id="cpu-lock-test",
        expected_job="CPU-only lock test",
        memory_strategy="no model",
        repository=repo,
        **kwargs,
    )


CHILD = """
import sys
from toolalign.runtime import GPULease, LockBusy
try:
    with GPULease(task_id='P00', worker_alias='test', run_id='child', expected_job='CPU only',
                  memory_strategy='no model', repository=sys.argv[1], timeout_seconds=0.1):
        print('ACQUIRED', flush=True)
        if len(sys.argv) > 2:
            sys.stdin.read(1)
except LockBusy:
    print('BUSY', flush=True)
    sys.exit(17)
"""


def test_two_processes_cannot_hold_lock_together_and_timeout_does_not_run_job(repository):
    with lease(repository):
        result = subprocess.run(
            [sys.executable, "-c", CHILD, str(repository)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 17
        assert result.stdout.strip() == "BUSY"
        status = inspect_gpu_lock(repository)
        assert status["held"] is True
        assert status["owner"]["pid"] == os.getpid()
        assert status["owner"]["process_started_at"]
    result = subprocess.run(
        [sys.executable, "-c", CHILD, str(repository)], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "ACQUIRED"


def test_exception_releases_os_lock_without_unlinking(repository):
    with pytest.raises(RuntimeError, match="fixture failure"):
        with lease(repository):
            inode = lock_path(repository).stat().st_ino
            raise RuntimeError("fixture failure")
    with lease(repository):
        assert lock_path(repository).stat().st_ino == inode
    assert inspect_gpu_lock(repository)["held"] is False
    assert lock_path(repository).stat().st_mode & 0o777 == 0o600


def test_abrupt_owner_exit_releases_lock(repository):
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(repository), "wait"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "ACQUIRED"
        assert inspect_gpu_lock(repository)["held"] is True
        child.kill()  # Only this test-owned child; production never kills another job.
        child.communicate(timeout=5)
        with lease(repository):
            assert inspect_gpu_lock(repository)["owner"]["pid"] == os.getpid()
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=5)


def test_separate_worktrees_resolve_same_common_directory_and_contend(repository):
    worktree = repository.parent / "other"
    subprocess.run(
        ["git", "-C", str(repository), "worktree", "add", "-b", "other", str(worktree)],
        check=True,
        capture_output=True,
    )
    assert lock_path(repository) == lock_path(worktree)
    with lease(repository):
        result = subprocess.run(
            [sys.executable, "-c", CHILD, str(worktree)], capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 17
    with lease(worktree):
        assert inspect_gpu_lock(repository)["held"] is True


@pytest.mark.parametrize("timeout", [-1, float("inf"), float("nan")])
def test_invalid_timeout_is_rejected(repository, timeout):
    with pytest.raises(ValueError):
        lease(repository, timeout_seconds=timeout)
