"""Run startup failures through installed P01 and the separately shipped report source."""

import errno
import importlib.util
import json
import pathlib
import subprocess
import sys
from dataclasses import asdict
from types import SimpleNamespace

from toolalign.contracts import validate_record
from toolalign.training.compatibility import execution
from toolalign.training.compatibility.core import Budget, write_json

assert sys.flags.isolated == 1
assert pathlib.Path(execution.__file__).resolve().is_relative_to(pathlib.Path(sys.prefix).resolve())
fixture_path, report_path, private = map(pathlib.Path, sys.argv[1:])
fixture = json.loads(fixture_path.read_text())
spec = importlib.util.spec_from_file_location("r4_installed_report", report_path)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
results = []
original_popen = subprocess.Popen
try:
    for stage in ("initial_swap", "popen"):
        root = private / ("startup-" + stage)
        config = {
            "run_id": "p01-r4-installed-" + stage, "mode": "smoke", "output_dir": str(root),
            "budget": asdict(Budget(max_wall_seconds=3)), "source_hash": "3" * 64,
            "git_commit": fixture["git_commit"], "data_manifest_hash": fixture["data_manifest_hash"],
            "model_identity": fixture["model"], "hardware": fixture["hardware"],
            "dependency_versions": fixture["dependency_versions"],
        }
        request = private / (stage + "-request.json")
        write_json(request, config)
        error = OSError(errno.EIO if stage == "initial_swap" else errno.EAGAIN, "CPU installed startup failure")
        launches = []

        def swap():
            if stage == "initial_swap":
                raise error
            return SimpleNamespace(used=4096)

        def popen(*args, **kwargs):
            launches.append(True)
            assert stage == "popen"
            raise error

        execution.prepare_config = lambda value: value
        sys.modules["psutil"] = SimpleNamespace(swap_memory=swap, NoSuchProcess=ProcessLookupError)
        execution.subprocess.Popen = popen
        try:
            execution.launch(request)
        except OSError as caught:
            assert caught is error
        else:
            raise AssertionError("Original startup error did not propagate")
        assert len(launches) == int(stage == "popen")
        manifest = json.loads((root / "run.json").read_text())
        validate_record(manifest, "run")
        assert manifest["status"] == "failed" and manifest["ended_at"] is not None
        record = next(row for row in builder.summarize(private)["runs"] if row["run_id"] == config["run_id"])
        assert record["assessment"] == "FAILED_INITIALIZATION" and record["failure_stage"] == stage
        assert record["child_started"] is False and record["raw_process_exit_code"] is None
        assert record["training_tokens"] == record["optimizer_steps"] == 0
        assert record["peak_rss_bytes"] is record["max_swap_growth_bytes"] is record["max_pressure_level"] is None
        assert record["initial_swap_bytes"] == (None if stage == "initial_swap" else 4096)
        results.append({"stage": stage, "popen_calls": len(launches), "created_children": 0,
                        "same_original_error": True, "summary": record})
finally:
    subprocess.Popen = original_popen
print(json.dumps({"status": "PASS", "cases": results, "installed_execution": True}, allow_nan=False, sort_keys=True))
