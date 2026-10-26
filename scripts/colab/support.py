"""Small stdlib helpers shared by the Colab controller and remote runner."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RUN_COMMANDS = {
    "toolalign.cuda-evaluation-run.v1": ("toolalign.evaluation.cuda_eval", "evaluate"),
    "toolalign.cuda-sft-run.v1": ("toolalign.training.cuda_sft", "train"),
    "toolalign.cuda-generation-run.v1": ("toolalign.training.cuda_generate", "generate"),
    "toolalign.cuda-dpo-run.v1": ("toolalign.training.cuda_dpo", "train"),
}


def run_command(run: dict) -> tuple[str, str]:
    if run.get("schema") not in RUN_COMMANDS or run.get("authorized_by") != "S1":
        raise ValueError("expected S1's whitelisted CUDA run configuration")
    if run["schema"] == "toolalign.cuda-generation-run.v1" and run.get("run_kind") != "generation":
        raise ValueError("generation schema requires generation run_kind")
    if run["schema"] == "toolalign.cuda-dpo-run.v1" and run.get("run_kind") not in ("dpo", "dpo_capacity"):
        raise ValueError("DPO schema requires dpo or dpo_capacity run_kind")
    if run["schema"] == "toolalign.cuda-evaluation-run.v1" and run.get("run_kind") != "evaluation":
        raise ValueError("evaluation schema requires evaluation run_kind")
    return RUN_COMMANDS[run["schema"]]


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
    """Check bounded control fields; each whitelisted module validates its data."""
    run = json.loads(payload["run_config_text"])
    run_command(run)
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
    if run["schema"] == "toolalign.cuda-generation-run.v1":
        if "max_optimizer_steps" in run:
            raise ValueError("generation must use max_trajectories, not optimizer steps")
        if positive_integer(run["max_trajectories"], "max_trajectories") > 512:
            raise ValueError("generation exceeds 512 trajectories")
        if run["max_wall_seconds"] > 21600 or payload["max_allocation_seconds"] > 21600:
            raise ValueError("generation exceeds the G4 time ceiling")
        if run["max_output_bytes"] > 1024**3:
            raise ValueError("generation exceeds the output ceiling")
    elif run["schema"] == "toolalign.cuda-evaluation-run.v1":
        if "max_optimizer_steps" in run or "persistent_dir" in run:
            raise ValueError("evaluation uses a fixed unit plan")
        limits = {"l1": 104, "action-only": 120, "replay": 8, "capacity": 2}
        if run.get("mode") not in limits:
            raise ValueError("unknown evaluation mode")
        plan = run.get("plan")
        if type(plan) is not list or not 0 < len(plan) <= limits[run["mode"]]:
            raise ValueError("evaluation plan exceeds its mode ceiling")
        if positive_integer(run["stop_after_unit"], "stop_after_unit") > len(plan):
            raise ValueError("evaluation stop exceeds its frozen plan")
        ceiling = 60 if run["mode"] == "capacity" else 14400
        if run["max_wall_seconds"] > ceiling or payload["max_allocation_seconds"] > 14400:
            raise ValueError("evaluation exceeds the G5 time ceiling")
        if run["max_output_bytes"] > 1024**3:
            raise ValueError("evaluation exceeds the output ceiling")
    elif run["schema"] == "toolalign.cuda-dpo-run.v1":
        if "max_optimizer_steps" in run or "persistent_dir" in run:
            raise ValueError("DPO uses a complete epoch total and an optimizer-boundary segment stop")
        count = positive_integer(run["pair_count"], "pair_count")
        total = positive_integer(run["total_optimizer_steps"], "total_optimizer_steps")
        stop = positive_integer(run["stop_after_optimizer_step"], "stop_after_optimizer_step")
        if count > 128 or total != (count + 7) // 8 or stop > total:
            raise ValueError("DPO step bounds must preserve the complete one-epoch total")
        if run["run_kind"] == "dpo_capacity" and count > 24:
            raise ValueError("DPO capacity is at most three optimizer steps")
        if run["max_wall_seconds"] > 21600 or payload["max_allocation_seconds"] > 21600:
            raise ValueError("DPO exceeds the G4 time ceiling")
        if run["max_output_bytes"] > 1024**3:
            raise ValueError("DPO exceeds the output ceiling")
        if Path(run["dependency_lock"]) != repository / "requirements/dpo-linux-py312.lock.txt":
            raise ValueError("DPO requires its dedicated dependency lock")
    else:
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
