"""Build and install the candidate using only public tracked files in a tiny worktree."""

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run(args, cwd):
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f"{args[0]} exit={result.returncode}; output_sha256=" + hashlib.sha256(
            result.stdout + result.stderr
        ).hexdigest())
    return result.stdout


def main():
    tracked = run(["git", "ls-files", "-z"], ROOT).decode().split("\0")
    with tempfile.TemporaryDirectory(prefix="r2-public-build-") as temporary:
        parent = Path(temporary)
        repository = parent / "repository"
        repository.mkdir()
        for name in filter(None, tracked):
            source, destination = ROOT / name, repository / name
            assert source.is_file() and not source.is_symlink()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        run(["git", "init", "-q"], repository)
        run(["git", "add", "."], repository)
        run(["git", "-c", "user.name=Review Fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "--no-gpg-sign", "-qm", "Public candidate build"], repository)
        checkout = parent / ".codex/worktrees/fixture"
        checkout.parent.mkdir(parents=True)
        run(["git", "worktree", "add", "--detach", "-q", str(checkout), "HEAD"], repository)
        assert (checkout / ".git").is_file()
        run(["uv", "build"], checkout)
        for path in sorted((checkout / "dist").glob("toolalign-*")):
            print(path.name, "bytes=" + str(path.stat().st_size),
                  "sha256=" + hashlib.sha256(path.read_bytes()).hexdigest(), flush=True)
        result = run(["uv", "run", "--locked", "python", "reports/review/P00/verify_wheel.py"], checkout)
        print(result.decode().strip(), flush=True)
        print("PASS: tracked-public candidate sdist build and isolated wheel installation/CLI")


if __name__ == "__main__":
    main()
