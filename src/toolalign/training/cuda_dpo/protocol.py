"""Frozen DPO configuration and a separate finite S1 execution request."""

from __future__ import annotations

import re
from pathlib import Path

from toolalign.training.cuda_sft.protocol import document, positive_int, read_bytes, require, sha

CONFIG_SHA256 = "fafb91a32e75cfbb15e452d528aa30c9e3db4e3149d0684834f459564c679ce3"
RUN_SCHEMA = "toolalign.cuda-dpo-run.v1"
LOCK_FILE = "requirements/dpo-linux-py312.lock.txt"


def load_protocol(repository):
    root = Path(repository)
    value = document(root / "configs/dpo-cuda.v1.json", digest=CONFIG_SHA256)
    for name, digest in value["bindings"].items():
        require(sha(read_bytes(root / name)) == digest, "DPO_protocol_binding")
    return value


def validate_run(request):
    fields = {"schema", "authorized_by", "run_kind", "run_id", "source_commit", "config_sha256",
              "repository", "lock_root", "model_root", "sft_checkpoint_dir", "input_root",
              "input_manifest_sha256", "prepared_data_sha256", "pair_count", "total_optimizer_steps",
              "stop_after_optimizer_step", "checkpoint_every_steps", "dependency_lock",
              "dependency_lock_sha256", "output_dir", "max_wall_seconds", "max_output_bytes"}
    optional = {"resume_from", "resume_checkpoint_sha256", "capacity_pair_ids"}
    require(type(request) is dict and fields <= set(request) and set(request) <= fields | optional,
            "DPO_run_fields")
    require(request["schema"] == RUN_SCHEMA and request["authorized_by"] == "S1"
            and request["run_kind"] in ("dpo", "dpo_capacity"), "separate_S1_DPO_request_required")
    require(request["config_sha256"] == CONFIG_SHA256, "DPO_config_identity")
    require(type(request["run_id"]) is str
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", request["run_id"]), "DPO_run_id")
    for key, length in (("source_commit", 40), ("input_manifest_sha256", 64),
                        ("prepared_data_sha256", 64), ("dependency_lock_sha256", 64)):
        require(type(request[key]) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", request[key]), key)
    for key in ("repository", "lock_root", "model_root", "sft_checkpoint_dir", "input_root",
                "dependency_lock", "output_dir"):
        require(type(request[key]) is str and Path(request[key]).is_absolute(), "absolute_" + key)
    require(Path(request["dependency_lock"]).resolve() == (Path(request["repository"]) / LOCK_FILE).resolve(),
            "dedicated_DPO_dependency_lock_required")
    require(positive_int(request["max_wall_seconds"], "max_wall_seconds") <= 21600,
            "DPO_wall_ceiling")
    require(positive_int(request["max_output_bytes"], "max_output_bytes") <= 1024**3,
            "DPO_output_ceiling")
    count = positive_int(request["pair_count"], "pair_count")
    require(count <= 128 and positive_int(request["total_optimizer_steps"], "total_optimizer_steps")
            == (count + 7) // 8,
            "DPO_complete_epoch_step_count")
    require(positive_int(request["stop_after_optimizer_step"], "stop_after_optimizer_step")
            <= request["total_optimizer_steps"], "DPO_segment_stop")
    positive_int(request["checkpoint_every_steps"], "checkpoint_every_steps")
    if request["run_kind"] == "dpo_capacity":
        plan = request.get("capacity_pair_ids")
        require(type(plan) is list and len(plan) == count <= 24
                and all(type(item) is str and item for item in plan), "DPO_capacity_plan")
    else:
        require("capacity_pair_ids" not in request, "DPO_formal_order_cannot_change")
    if "resume_from" in request or "resume_checkpoint_sha256" in request:
        require(type(request.get("resume_from")) is str and Path(request["resume_from"]).is_absolute()
                and Path(request["resume_from"]).resolve() != Path(request["output_dir"]).resolve(),
                "DPO_resume_path")
        require(type(request.get("resume_checkpoint_sha256")) is str
                and re.fullmatch(r"[0-9a-f]{64}", request["resume_checkpoint_sha256"]), "DPO_resume_hash")
    return request


def select_pairs(prepared, summary, request):
    require(summary["prepared_data_sha256"] == request["prepared_data_sha256"],
            "DPO_prepared_data_identity")
    require(prepared["accepted_pairs"] > 0, "DPO_no_eligible_pairs")
    rows, expected = prepared["rows"], prepared["expected"]
    if request["run_kind"] == "dpo_capacity":
        by_id = {row["preference_id"]: (row, tokens)
                 for row, tokens in zip(rows, expected, strict=True)}
        plan = request["capacity_pair_ids"]
        require(set(plan) <= set(by_id), "DPO_capacity_unapproved_pair")
        lengths = {row["preference_id"]: max(row["chosen_tokens_including_eos"],
                                            row["rejected_tokens_including_eos"])
                   for row in prepared["dispositions"] if row["disposition"] == "accepted"}
        require(lengths[plan[0]] == max(lengths.values()), "DPO_capacity_longest_pair_first")
        # A separately frozen diagnostic plan may repeat an approved pair to
        # exercise optimizer/save/resume. Its occurrences never enter formal DPO.
        rows, expected = [], []
        for index, original_id in enumerate(plan):
            row, tokens = by_id[original_id]
            identity = f"capacity-{index:03d}:{original_id}"
            rows.append(row | {"preference_id": identity})
            expected.append(tokens | {"preference_id": identity})
    require(len(rows) == request["pair_count"], "DPO_frozen_pair_count")
    return rows, expected
