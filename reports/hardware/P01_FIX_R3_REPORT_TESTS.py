"""CPU checks for summaries of failed monitors and JSON-normalized loss failures."""

import importlib.util
import json
import math
from pathlib import Path

import pytest


def summarize(root):
    spec = importlib.util.spec_from_file_location(
        "p01_report_builder", Path(__file__).with_name("P01_BUILD_REPORT.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.summarize(root)


@pytest.mark.parametrize("kind", ["monitor_error", "nan_loss", "finite_gate_failure"])
def test_failure_remains_in_summary_and_standard_json(tmp_path, kind):
    run = tmp_path / "cpu-synthetic"
    run.mkdir()
    config = {"run_id": "p01-fix-r3-report", "mode": "math", "git_commit": "1" * 40,
              "source_hash": "2" * 64, "hardware": {}, "dependency_versions": {},
              "fallback_accumulation": 8}
    resources = {"exit_code": 1 if kind == "monitor_error" else 2,
                 "stop_reason": "monitor_error" if kind == "monitor_error" else None,
                 "wall_seconds": 1.0, "peak_rss_bytes": 4096, "samples": []}
    if kind == "monitor_error":
        resources["monitor_error"] = {"type": "CalledProcessError", "message": "synthetic"}
    else:
        step = {"iteration": 8, "train_loss": None if kind == "nan_loss" else math.log(2) + .1,
                "status": "failed", "failure": {"type": "ValueError", "message": "loss gate"}}
        if kind == "nan_loss":
            step["nonfinite_values"] = {"train_loss": "nan"}
        (run / "fallback-dpo-steps.json").write_text(json.dumps([step], allow_nan=False))
    (run / "config.json").write_text(json.dumps(config))
    (run / "resources.json").write_text(json.dumps(resources))
    (record,) = summarize(tmp_path)["runs"]
    assert record["exit_code"] == resources["exit_code"]
    assert record["assessment"] == ("FAILED_MONITOR" if kind == "monitor_error" else "FAILED")
    assert "resources.json" in record["evidence_hashes"]
    if kind == "monitor_error":
        assert record["monitor_error_type"] == "CalledProcessError"
    else:
        assert record["training_callback_failure"]["type"] == "ValueError"
    if kind == "nan_loss":
        assert record["actual_initial_training_loss_has_nonfinite"] is True
    assert json.dumps(record, allow_nan=False)
