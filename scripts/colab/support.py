"""Small stdlib helpers shared by the Colab controller and remote runner."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".write-", delete=False) as out:
        temporary = Path(out.name)
        out.write(json_bytes(value))
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value):
        raise ValueError("run/session names must be simple nonempty identifiers")
    return value


def positive_integer(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def time_remaining(payload: dict) -> float:
    started = datetime.fromisoformat(payload["allocated_at_utc"])
    if started.tzinfo is None:
        raise ValueError("allocated_at_utc must include a timezone")
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    if elapsed < 0:
        raise ValueError("allocation start must not be in the future")
    limit = positive_integer(payload["max_allocation_seconds"], "max_allocation_seconds")
    return limit - elapsed


def validate_payload(payload: dict, repository: Path) -> dict:
    """Check the control fields; the trainer owns training/data validation."""
    run = json.loads(payload["run_config_text"])
    expected_hash = hashlib.sha256(payload["run_config_text"].encode()).hexdigest()
    if expected_hash != payload["run_config_sha256"]:
        raise ValueError("run configuration hash mismatch")
    run_id = name(payload["run_id"])
    session = name(payload["session"])
    if not session.startswith("toolalign-"):
        raise ValueError("this controller only manages toolalign-* sessions")
    if not payload.get("endpoint"):
        raise ValueError("a checked existing session endpoint is required")
    for key in ("run_id", "source_commit", "dependency_lock_sha256"):
        if run[key] != payload[key]:
            raise ValueError(f"run/control {key} mismatch")
    for key, length in (("source_commit", 40), ("dependency_lock_sha256", 64)):
        if not re.fullmatch(f"[0-9a-f]{{{length}}}", payload[key]):
            raise ValueError(f"invalid {key}")
    if Path(run["output_dir"]) != repository / "runs" / run_id / "output":
        raise ValueError("output_dir must be /content/toolalign/runs/RUN_ID/output")
    if Path(run["lock_root"]) != repository:
        raise ValueError("all runs must use the same actual Git repository for GPULease")
    positive_integer(run["max_wall_seconds"], "max_wall_seconds")
    positive_integer(run["max_output_bytes"], "max_output_bytes")
    positive_integer(run["max_optimizer_steps"], "max_optimizer_steps")
    staging = repository.parent / "toolalign-staging" / run_id
    if Path(run["persistent_dir"]) != staging:
        raise ValueError("persistent_dir must be the run's ToolAlign staging directory")
    if Path(run["repository"]) != repository:
        raise ValueError("repository must be the shared /content/toolalign checkout")
    time_remaining(payload)
    return run


def file_manifest(directory: Path, *, max_bytes: int, exclude: tuple[str, ...] = ()) -> dict:
    files = {}
    total = 0
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory).as_posix()
        if path.is_symlink():
            raise ValueError(f"output symlink is not transferable: {relative}")
        if path.is_dir() or relative in exclude:
            continue
        if not path.is_file():
            raise ValueError(f"non-file output: {relative}")
        size = path.stat().st_size
        total += size
        if total > max_bytes:
            raise ValueError("output exceeds the transfer byte budget")
        files[relative] = {"bytes": size, "sha256": digest(path)}
    return files


def verify_manifest(directory: Path, manifest: dict) -> None:
    actual = file_manifest(
        directory, max_bytes=manifest["max_bytes"], exclude=("MANIFEST.json",)
    )
    if actual != manifest["files"]:
        raise ValueError("recovered output does not match its complete file manifest")
