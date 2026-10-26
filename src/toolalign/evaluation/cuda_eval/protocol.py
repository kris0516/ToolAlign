"""Strict heldout, action-only, development replay and capacity input contracts."""

from __future__ import annotations

import re
from pathlib import Path

from toolalign.contracts import validate_record
from toolalign.contracts.interfaces import OracleTask
from toolalign.model_io.cuda_generation import ADAPTER_SHA256, CHECKPOINT_SHA256
from toolalign.model_io.format import validate_action, validate_model_input
from toolalign.tools import LocalToolExecutor, LocalToolRegistry
from toolalign.tools._json import INPUT_BYTES, encode
from toolalign.training.cuda_generate.protocol import SAMPLING
from toolalign.training.cuda_sft.protocol import (
    CONFIG_SHA256,
    MAX_BUNDLE_BYTES,
    document,
    encoded,
    positive_int,
    require,
)

RUN_SCHEMA = "toolalign.cuda-evaluation-run.v1"
CATALOG = "heldout-devops.v1"
MODES = ("l1", "action-only", "replay", "capacity")


def fields(value, expected, reason):
    require(type(value) is dict and set(value) == set(expected.split()), reason)


def identifiers(entries, field):
    values = [entry[field] for entry in entries]
    require(all(type(v) is str and 0 < len(v) <= 128 for v in values)
            and len(values) == len(set(values)), "evaluation_identifiers")


def read_inputs(path, digest, mode):
    value = document(path, digest=digest, limit=64 * 1024**2)
    require(mode in MODES, "evaluation_mode")
    registries = {}
    if mode == "l1":
        fields(value, "schema_version purpose catalog registry_hash tasks recovery_task_ids", "evaluation_task_fields")
        require(value["schema_version"] == "toolalign.evaluation-tasks.v1"
                and value["purpose"] == "heldout-model-evaluation"
                and value["catalog"] == CATALOG, "evaluation_task_schema")
        registry = LocalToolRegistry(catalog_id=CATALOG)
        require(registry.catalog_id == CATALOG and value["registry_hash"] == registry.registry_hash,
                "evaluation_registry_identity")
        entries = value["tasks"]
        require(type(entries) is list and 0 < len(entries) <= 48, "evaluation_task_count")
        for entry in entries:
            fields(entry, "task_id family_id group_id category example oracle_task faults tool_names",
                   "evaluation_task_entry")
            example = validate_record(entry["example"], "example")
            task = OracleTask(**entry["oracle_task"])
            validate_action(task.expected_action)
            require(task.split == example["split"] and task.split in ("test", "ood_test")
                    and entry["task_id"] == task.task_id == example["example_id"]
                    and entry["group_id"] == task.group_id == example["group_id"],
                    "evaluation_task_identity_or_split")
            require(type(entry["tool_names"]) is list
                    and len(entry["tool_names"]) == len(set(entry["tool_names"])), "evaluation_tool_names")
            subset = LocalToolRegistry(entry["tool_names"], catalog_id=CATALOG)
            require({t["name"]: t for t in subset.tools} == {t["name"]: t for t in example["tools"]},
                    "evaluation_task_tool_schema")
            require(type(task.oracle_payload) is dict and type(entry["faults"]) is dict,
                    "evaluation_oracle_or_faults")
            LocalToolExecutor(subset, faults=entry["faults"])
            registries[entry["task_id"]] = subset
        recovery = value["recovery_task_ids"]
        require(type(recovery) is list and len(recovery) <= 8 and len(set(recovery)) == len(recovery)
                and set(recovery) <= {e["task_id"] for e in entries}, "evaluation_recovery_subset")
    elif mode in ("action-only", "capacity"):
        fields(value, "schema_version purpose inputs", "evaluation_input_fields")
        require(value["schema_version"] == "toolalign.evaluation-inputs.v1"
                and value["purpose"] == ("action-only-model-evaluation" if mode == "action-only"
                                          else "original-capacity-probe"), "evaluation_input_schema")
        entries = value["inputs"]
        require(type(entries) is list and 0 < len(entries) <= (60 if mode == "action-only" else 2),
                "evaluation_input_count")
        for entry in entries:
            fields(entry, "task_id family_id group_id category model_input" +
                   (" model" if mode == "capacity" else ""), "evaluation_input_entry")
            encode(validate_model_input(entry["model_input"]), INPUT_BYTES)
            if mode == "capacity":
                require(entry["model"] in ("M0", "M1"), "evaluation_capacity_model")
        if mode == "action-only":
            categories = [e["category"] for e in entries]
            require(set(categories) <= {"simple_python", "multiple", "irrelevance"}
                    and all(categories.count(c) <= 20 for c in set(categories)), "evaluation_bfcl_count")
    else:
        fields(value, "schema_version purpose sequences", "evaluation_replay_fields")
        require(value["schema_version"] == "toolalign.evaluation-replay.v1"
                and value["purpose"] == "development-prefix-replay", "evaluation_replay_schema")
        sequences = value["sequences"]
        require(type(sequences) is list and 0 < len(sequences) <= 4, "evaluation_replay_count")
        identifiers(sequences, "sequence_id")
        for sequence in sequences:
            fields(sequence, "sequence_id tenant_id requests", "evaluation_sequence_fields")
            require(type(sequence["tenant_id"]) is str and 0 < len(sequence["tenant_id"]) <= 128,
                    "evaluation_tenant")
            requests = sequence["requests"]
            require(type(requests) is list and len(requests) == 3, "evaluation_replay_three_requests")
            identifiers(requests, "request_id")
            for request in requests:
                fields(request, "request_id model_input", "evaluation_replay_request")
                encode(validate_model_input(request["model_input"]), INPUT_BYTES)
        return value, registries
    identifiers(entries, "task_id")
    require(all(type(e[k]) is str and 0 < len(e[k]) <= 128 for e in entries
                for k in ("family_id", "group_id", "category")), "evaluation_group_fields")
    return value, registries


def evaluation_plan(value, mode):
    plan = []

    def add(task_id, condition, model, seed, *, cache=False, recovery=True):
        plan.append({"unit_id": len(plan), "task_id": task_id, "condition": condition,
                     "model": model, "seed": seed, "cache_enabled": cache,
                     "recovery_enabled": recovery})

    if mode == "replay":
        for i, sequence in enumerate(value["sequences"]):
            for enabled in ((False, True) if i % 2 == 0 else (True, False)):
                add(sequence["sequence_id"], "M1-cache-" + ("on" if enabled else "off"), "M1",
                    42 + i * 3, cache=enabled)
    else:
        entries = value["tasks" if mode == "l1" else "inputs"]
        for i, entry in enumerate(entries):
            models = [entry["model"]] if mode == "capacity" else (("M0", "M1") if i % 2 == 0 else ("M1", "M0"))
            for model in models:
                add(entry["task_id"], model, model, 42 + i)
        if mode == "l1":
            for task_id in value["recovery_task_ids"]:
                i = next(i for i, entry in enumerate(entries) if entry["task_id"] == task_id)
                add(task_id, "M1-recovery-off", "M1", 42 + i, recovery=False)
    return plan


def validate_run(request, inputs):
    required = {"schema", "authorized_by", "run_kind", "mode", "run_id", "source_commit", "config_sha256",
                "input_path", "input_sha256", "model_root", "checkpoint_dir", "checkpoint_sha256",
                "adapter_sha256", "dependency_lock", "dependency_lock_sha256", "repository", "lock_root",
                "output_dir", "plan", "main_seed", "sampling", "stop_after_unit", "max_wall_seconds", "max_output_bytes"}
    require(type(request) is dict and required <= set(request)
            and set(request) <= required | {"resume_from", "resume_batch_sha256"}, "evaluation_run_fields")
    require(request["schema"] == RUN_SCHEMA and request["authorized_by"] == "S1"
            and request["run_kind"] == "evaluation" and request["mode"] in MODES,
            "separate_S1_evaluation_request_required")
    require(request["config_sha256"] == CONFIG_SHA256 and request["checkpoint_sha256"] == CHECKPOINT_SHA256
            and request["adapter_sha256"] == ADAPTER_SHA256, "evaluation_selected_identity")
    require(type(request["run_id"]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", request["run_id"]),
            "evaluation_run_id")
    for key, length in (("source_commit", 40), ("input_sha256", 64), ("dependency_lock_sha256", 64)):
        require(type(request[key]) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", request[key]), key)
    for key in ("input_path", "model_root", "checkpoint_dir", "dependency_lock", "repository", "lock_root", "output_dir"):
        require(type(request[key]) is str and Path(request[key]).is_absolute(), "absolute_" + key)
    require(Path(request["repository"]).resolve() == Path(request["lock_root"]).resolve(), "evaluation_shared_lock")
    require(type(request["main_seed"]) is int and request["main_seed"] == 42
            and encoded(request["sampling"]) == encoded(SAMPLING)
            and encoded(request["plan"]) == encoded(evaluation_plan(inputs, request["mode"])), "evaluation_frozen_plan")
    limit = {"l1": 104, "action-only": 120, "replay": 8, "capacity": 2}[request["mode"]]
    require(0 < len(request["plan"]) <= limit
            and positive_int(request["stop_after_unit"], "stop_after_unit") <= len(request["plan"]), "evaluation_plan_ceiling")
    require(positive_int(request["max_wall_seconds"], "max_wall_seconds") <=
            (60 if request["mode"] == "capacity" else 14400), "evaluation_wall_ceiling")
    require(positive_int(request["max_output_bytes"], "max_output_bytes") <= MAX_BUNDLE_BYTES, "evaluation_output_ceiling")
    if "resume_from" in request or "resume_batch_sha256" in request:
        require(type(request.get("resume_from")) is str and Path(request["resume_from"]).is_absolute()
                and Path(request["resume_from"]).resolve() != Path(request["output_dir"]).resolve(), "evaluation_resume_directory")
        require(type(request.get("resume_batch_sha256")) is str
                and re.fullmatch(r"[0-9a-f]{64}", request["resume_batch_sha256"]), "evaluation_resume_identity")
    return request
