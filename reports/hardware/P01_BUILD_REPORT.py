"""Build a sanitized P01 summary from private evidence; never copy raw data/logs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from toolalign.contracts import validate_record
from toolalign.training.compatibility.core import file_hash, write_json


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def summarize(root: Path) -> dict:
    runs = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or not (directory / "resources.json").exists():
            continue
        config = load(directory / "config.json")
        resources = load(directory / "resources.json")
        result = load(directory / "result.json")
        partial = load(directory / "partial-result.json") or {}
        progress = load(directory / "progress.json") or {}
        manifest = load(directory / "run.json")
        raw = result or partial
        record = {
            "run_id": config["run_id"],
            "mode": config["mode"],
            "git_commit": config["git_commit"],
            "source_hash": config["source_hash"],
            "exit_code": resources["exit_code"],
            "stop_reason": resources["stop_reason"],
            "wall_seconds": resources["wall_seconds"],
            "peak_rss_bytes": resources["peak_rss_bytes"],
            "max_swap_growth_bytes": max(
                (s["swap_growth_bytes"] for s in resources["samples"]), default=0
            ),
            "max_pressure_level": max((s["pressure"] for s in resources["samples"]), default=None),
            "model_id": config.get("model_id"),
            "sequence_bucket": config.get("sequence_length"),
            "raw_result_status": raw.get("status"),
            "hardware": config["hardware"],
            "dependency_versions": config["dependency_versions"],
            "compile_disabled": config.get("fallback_disable_compile", False),
            "dpo_checkpointing": config.get("fallback_grad_checkpoint", False),
            "sft_checkpointing": config.get("grad_checkpoint", False),
            "evidence_hashes": {},
            "progress": progress,
        }
        for name in [
            "run.json",
            "config.json",
            "stdout.log",
            "resources.json",
            "result.json",
            "partial-result.json",
            "token-audit.json",
            "sft-steps.json",
            "fallback-dpo-steps.json",
            "progress.json",
            "events.json",
            "failure.json",
        ]:
            if (directory / name).exists():
                record["evidence_hashes"][name] = file_hash(directory / name)
        if manifest:
            validate_record(manifest)
            for artifact in manifest["artifacts"]:
                path = directory / artifact["relative_path"]
                if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError("Artifact path escapes its run root")
                if (
                    path.stat().st_size != artifact["size_bytes"]
                    or file_hash(path) != artifact["sha256"]
                ):
                    raise ValueError("Private artifact differs from frozen run manifest")
            record["manifest_artifacts_verified"] = len(manifest["artifacts"])
            record["model_identity"] = manifest["model"]
            record["reference_model_hash"] = manifest["reference_model_hash"]
            record["training_tokens"] = manifest["training_tokens"]
            record["optimizer_steps"] = manifest["optimizer_steps"]
        for key in [
            "token_audit",
            "sft",
            "dpo",
            "primary_dpo",
            "cross_library",
            "reference",
            "generation",
            "checkpoint_io",
            "phase_seconds",
            "complete_task_inference",
        ]:
            if key in raw:
                record[key] = raw[key]
        device = load(directory / "device-resources.json") or {}
        record["mlx_peak_bytes"] = raw.get("mlx_peak_bytes", device.get("mlx_peak_bytes"))
        if config["mode"] == "math":
            record["math"] = raw
        # Independently catch the early implementation's false positive: its preflight
        # ln2 passed but the actual compiled training path did not. Raw evidence stays intact.
        steps = load(directory / "fallback-dpo-steps.json") or []
        first_cycle = [
            s["train_loss"]
            for s in steps
            if s["iteration"] <= config.get("fallback_accumulation", 8)
        ]
        if first_cycle:
            record["actual_initial_training_loss_max_abs_error"] = max(
                abs(x - math.log(2)) for x in first_cycle
            )
        if resources["exit_code"] != 0:
            record["assessment"] = "STOPPED_RESOURCE" if resources["stop_reason"] else "FAILED"
        elif first_cycle and any(abs(x - math.log(2)) > 2e-6 for x in first_cycle):
            record["assessment"] = "FAIL_TRAINING_PATH_LN2"
        elif raw.get("status") == "PARTIAL":
            record["assessment"] = "PARTIAL_SFT_PASS_DPO_FAILED"
        else:
            record["assessment"] = raw.get("status", "UNKNOWN")
        runs.append(record)
    return {
        "scope": "P01 self-test evidence; pending independent R1/S0 acceptance",
        "units": {"memory": "bytes; GiB = bytes / 2**30", "time": "synchronized seconds"},
        "runs": runs,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_json(args.output, summarize(args.private_runs))
