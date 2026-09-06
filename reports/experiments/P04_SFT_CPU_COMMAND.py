"""Record a real local command with immutable logs and source identities."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def source(root):
    names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True).splitlines()
    return {name: sha((root / name).read_bytes()) for name in names if (root / name).is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    assert ".toolalign-local" in out.parts
    out.mkdir(parents=True, exist_ok=False)
    command = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    record = {"argv": command, "cwd": str(root), "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip(),
        "source_files_before": source(root),
        "environment": {k: os.environ[k] for k in (
            "PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "USE_TORCH", "USE_TF", "USE_FLAX", "TOKENIZERS_PARALLELISM",
            "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "TOOLALIGN_TOKENIZER_DIR", "TOOLALIGN_QWEN_TOKENIZER",
            "WANDB_MODE", "OMP_NUM_THREADS", "MKL_NUM_THREADS") if k in os.environ}}
    save(out / "started.json", record)
    started, error = time.monotonic(), None
    with (out / "stdout.log").open("xb") as stdout, (out / "stderr.log").open("xb") as stderr:
        try:
            result = subprocess.run(command, cwd=root, stdout=stdout, stderr=stderr, timeout=args.timeout)
            code = result.returncode
        except BaseException as exc:
            code, error = 124 if isinstance(exc, subprocess.TimeoutExpired) else 1, repr(exc)
    record.update(ended_at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic() - started,
                  exit_code=code, error=error, source_files_after=source(root),
                  stdout_sha256=sha((out / "stdout.log").read_bytes()),
                  stderr_sha256=sha((out / "stderr.log").read_bytes()))
    record["source_unchanged_during_command"] = record["source_files_before"] == record["source_files_after"]
    save(out / "receipt.json", record)
    print(json.dumps({k: record[k] for k in ("argv", "exit_code", "wall_seconds", "source_unchanged_during_command",
                                             "stdout_sha256", "stderr_sha256")}))
    return code


if __name__ == "__main__":
    sys.exit(main())
