"""G4 task input, fixed candidate order and separate S1 run authorization."""

from __future__ import annotations

import re
from pathlib import Path

from toolalign.contracts import validate_record
from toolalign.contracts.interfaces import OracleTask
from toolalign.model_io.cuda_generation import ADAPTER_SHA256, CHECKPOINT_SHA256
from toolalign.model_io.format import validate_action
from toolalign.tools import LocalToolExecutor, LocalToolRegistry
from toolalign.training.cuda_sft.protocol import (
    CONFIG_SHA256,
    MAX_BUNDLE_BYTES,
    document,
    encoded,
    positive_int,
    require,
)

RUN_SCHEMA = "toolalign.cuda-generation-run.v1"
TASK_SCHEMA = "toolalign.preference-tasks.v1"
MAX_TASKS = 128
CANDIDATES_PER_TASK = 4
MAIN_SEED = 42
SAMPLING = {"temperature": 0.7, "top_p": 0.9, "max_new_tokens": 256}


def read_tasks(path, expected_sha256):
    value = document(path, digest=expected_sha256, limit=64 * 1024**2)
    require(type(value) is dict and set(value) == {"schema_version", "purpose", "registry_hash", "tasks"}
            and value["schema_version"] == TASK_SCHEMA
            and value["purpose"] == "train-candidate-generation", "generation_task_schema")
    registry = LocalToolRegistry()
    require(value["registry_hash"] == registry.registry_hash, "generation_registry_identity")
    tasks = value["tasks"]
    require(type(tasks) is list and 0 < len(tasks) <= MAX_TASKS, "generation_task_count")
    seen = set()
    for entry in tasks:
        require(type(entry) is dict and set(entry) == {
            "task_id", "family_id", "group_id", "category", "example", "oracle_task", "faults"},
            "generation_task_fields")
        example = validate_record(entry["example"], "example")
        task = OracleTask(**entry["oracle_task"])
        validate_action(task.expected_action)
        require(task.split == example["split"] == "train"
                and entry["task_id"] == example["example_id"] == task.task_id
                and entry["group_id"] == example["group_id"] == task.group_id,
                "generation_task_identity_or_split")
        require(entry["task_id"] not in seen, "duplicate_generation_task")
        seen.add(entry["task_id"])
        require(all(type(entry[k]) is str and entry[k]
                    for k in ("family_id", "category", "group_id")), "generation_group_fields")
        require(type(task.oracle_payload) is dict and type(entry["faults"]) is dict,
                "generation_oracle_or_faults")
        # Validate host-side fault schedules without consuming them.
        LocalToolExecutor(registry, faults=entry["faults"])
        registered = {tool["name"]: tool for tool in registry.tools}
        require(all(registered.get(tool["name"]) == tool for tool in example["tools"]),
                "generation_task_tool_schema")
    return value, registry


def candidate_plan(tasks):
    """Task file order, then candidate-0..3; seed 42 + global ordinal."""
    return [{"task_id": task["task_id"], "candidate_id": f"candidate-{index}",
             "seed": MAIN_SEED + offset * CANDIDATES_PER_TASK + index}
            for offset, task in enumerate(tasks) for index in range(CANDIDATES_PER_TASK)]


def validate_run(request, tasks):
    required = {"schema", "authorized_by", "run_kind", "run_id", "source_commit", "config_sha256",
                "tasks_path", "tasks_sha256", "model_root", "checkpoint_dir", "checkpoint_sha256",
                "adapter_sha256", "dependency_lock", "dependency_lock_sha256", "repository",
                "lock_root", "output_dir", "candidate_plan", "main_seed", "sampling",
                "max_trajectories", "max_wall_seconds", "max_output_bytes"}
    require(type(request) is dict and required <= set(request)
            and set(request) <= required | {"resume_from", "resume_batch_sha256"},
            "generation_run_fields")
    require(request["schema"] == RUN_SCHEMA and request["run_kind"] == "generation"
            and request["authorized_by"] == "S1", "separate_S1_generation_request_required")
    require(request["config_sha256"] == CONFIG_SHA256
            and request["checkpoint_sha256"] == CHECKPOINT_SHA256
            and request["adapter_sha256"] == ADAPTER_SHA256, "generation_selected_identity")
    require(type(request["run_id"]) is str
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", request["run_id"]), "generation_run_id")
    for key, length in (("source_commit", 40), ("tasks_sha256", 64), ("dependency_lock_sha256", 64)):
        require(type(request[key]) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", request[key]), key)
    for key in ("tasks_path", "model_root", "checkpoint_dir", "dependency_lock", "repository",
                "lock_root", "output_dir"):
        require(type(request[key]) is str and Path(request[key]).is_absolute(), "absolute_" + key)
    require(Path(request["repository"]).resolve() == Path(request["lock_root"]).resolve(),
            "generation_shared_repository_lock")
    require(request["main_seed"] == MAIN_SEED and type(request["main_seed"]) is int
            and encoded(request["sampling"]) == encoded(SAMPLING)
            and encoded(request["candidate_plan"]) == encoded(candidate_plan(tasks["tasks"])),
            "generation_frozen_plan")
    require(positive_int(request["max_trajectories"], "max_trajectories")
            <= len(request["candidate_plan"]), "generation_trajectory_ceiling")
    require(positive_int(request["max_wall_seconds"], "max_wall_seconds") <= 21600,
            "generation_wall_ceiling")
    require(positive_int(request["max_output_bytes"], "max_output_bytes") <= MAX_BUNDLE_BYTES,
            "generation_output_ceiling")
    if "resume_from" in request or "resume_batch_sha256" in request:
        require(type(request.get("resume_from")) is str and Path(request["resume_from"]).is_absolute()
                and Path(request["resume_from"]).resolve() != Path(request["output_dir"]).resolve(),
                "generation_resume_directory")
        require(type(request.get("resume_batch_sha256")) is str
                and re.fullmatch(r"[0-9a-f]{64}", request["resume_batch_sha256"]),
                "generation_resume_identity")
    return request
