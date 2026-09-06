"""Check the meaning of actual startup failures in the production report interface."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize("stage,mode,baseline", [
    ("initial_swap", "smoke", 0), ("popen", "smoke", 0),
    ("popen", "smoke", 4096), ("popen", "math", 4096),
])
def test_actual_failure_summary_retains_initialization_meaning(
    monkeypatch, tmp_path, stage, mode, baseline,
):
    checks = module("r4_startup_checks", ROOT / "tests/training/compatibility/test_initialization_failures.py")
    root = checks.exercise_startup_failure(monkeypatch, tmp_path, stage, mode, baseline)
    builder = module("r4_report", ROOT / "reports/hardware/P01_BUILD_REPORT.py")
    (record,) = builder.summarize(root.parent)["runs"]
    assert record["assessment"] == "FAILED_INITIALIZATION" and record["exit_code"] == 1
    assert record["child_started"] is False and record["raw_process_exit_code"] is None
    assert record["failure_stage"] == stage
    assert record["initialization_error_type"] == ("OSError" if stage == "initial_swap" else "BlockingIOError")
    assert record["peak_rss_bytes"] is None
    assert record["max_swap_growth_bytes"] is None and record["max_pressure_level"] is None
    assert record["initial_swap_bytes"] == (None if stage == "initial_swap" else baseline)
    assert record["progress"] == {} and record["raw_result_status"] is None
    if mode != "math":
        assert record["training_tokens"] == record["optimizer_steps"] == 0
    assert json.dumps(record, allow_nan=False)
