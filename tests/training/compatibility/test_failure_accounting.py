"""CPU regression coverage for terminal monitor records and completed-step accounting."""

from __future__ import annotations

import ast
import importlib.util
import json
import math
import os
import signal
import subprocess
import sys
import textwrap
import time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolalign.contracts import validate_record
from toolalign.training.compatibility import execution, fallback_probe
from toolalign.training.compatibility.core import Budget, assert_initial_dpo_loss, write_json


@pytest.mark.parametrize("outcome", [
    "command_error", "malformed", "read_timeout", "pressure", "wall", "cancel", "success",
    "worker_failure",
])
def test_terminal_records_preserve_monitor_failure_and_reap_only_owned_child(
    monkeypatch, tmp_path, outcome,
):
    root = tmp_path / "run"
    fixture = json.loads((Path(__file__).parents[2] / "fixtures/contracts/run.json").read_text())
    config = {
        "run_id": "p01-fix-r3-cpu", "mode": "smoke", "output_dir": str(root),
        "budget": asdict(Budget(max_wall_seconds=1)),
        "git_commit": fixture["git_commit"], "data_manifest_hash": fixture["data_manifest_hash"],
        "model_identity": fixture["model"], "hardware": fixture["hardware"],
        "dependency_versions": fixture["dependency_versions"],
    }
    requested = tmp_path / "requested.json"
    write_json(requested, config)
    monkeypatch.setattr(execution, "prepare_config", lambda supplied: supplied)
    # Default CPU dependencies stay unchanged. Only resource values are stubbed;
    # the two children, signals, escalation and wait/reaping are real OS actions.
    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(
        Process=lambda pid: SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=4096)),
        swap_memory=lambda: SimpleNamespace(used=0), NoSuchProcess=ProcessLookupError,
    ))
    original_popen = subprocess.Popen
    owned, signals = [], []
    script = """
import json,os,signal,sys,time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
root=Path(sys.argv[1])
(root/'ready.tmp').write_text(json.dumps({'pid':os.getpid(),'parent':os.getppid()}))
(root/'ready.tmp').replace(root/'ready.json')
time.sleep(0.05 if sys.argv[2] in {'success', 'worker_failure'} else 30)
sys.exit(2 if sys.argv[2]=='worker_failure' else 0)
"""

    class Child(original_popen):
        def wait(self, timeout=None):
            return super().wait(timeout=0.05 if timeout == 10 else timeout)

        def terminate(self):
            signals.append("terminate")
            return super().terminate()

        def kill(self):
            signals.append("kill")
            return super().kill()

    def spawn(args, **kwargs):
        assert args[1:5] == ["-m", "toolalign.training.compatibility", "_worker", "--config"]
        child = Child([sys.executable, "-c", script, str(root), outcome], **kwargs)
        owned.append(child)
        deadline = time.monotonic() + 3
        while not (root / "ready.json").exists():
            if child.poll() is not None or time.monotonic() > deadline:
                raise AssertionError("CPU child failed to start")
            time.sleep(0.005)
        identity = json.loads((root / "ready.json").read_text())
        assert identity == {"pid": child.pid, "parent": os.getpid()}
        return child

    def pressure(args, **kwargs):
        if outcome == "command_error":
            raise subprocess.CalledProcessError(3, args, stderr="CPU sampling failure")
        if outcome == "malformed":
            return "unreadable-pressure\n"
        if outcome == "read_timeout":
            raise subprocess.TimeoutExpired(args, 0.1)
        if outcome == "cancel":
            raise KeyboardInterrupt()
        return "2\n" if outcome == "pressure" else "1\n"

    unrelated = original_popen([sys.executable, "-c", "import time; time.sleep(30)"])
    monkeypatch.setattr(execution.subprocess, "Popen", spawn)
    monkeypatch.setattr(execution.subprocess, "check_output", pressure)
    failure = None
    try:
        try:
            returned = execution.launch(requested)
        except (subprocess.SubprocessError, ValueError) as exc:
            failure = exc
        assert len(owned) == 1 and owned[0].poll() is not None
        child = owned[0]
        with pytest.raises(ChildProcessError):
            os.waitpid(child.pid, os.WNOHANG)
        assert unrelated.poll() is None
        resource = json.loads((root / "resources.json").read_text())
        manifest = json.loads((root / "run.json").read_text())
        validate_record(manifest)
        assert manifest["ended_at"] is not None
        assert resource["peak_rss_bytes"] == 4096
        assert any(item["relative_path"] == "resources.json" for item in manifest["artifacts"])
        if outcome in {"command_error", "malformed", "read_timeout"}:
            assert failure is not None
            assert resource["monitor_error"] == {
                "type": type(failure).__name__, "message": str(failure),
            }
            assert resource["stop_reason"] == "monitor_error"
            assert resource["exit_code"] == manifest["exit_code"] == 1
        else:
            assert failure is None and resource["monitor_error"] is None
            expected = {"success": 0, "worker_failure": 2}.get(outcome, 124)
            assert returned == resource["exit_code"] == manifest["exit_code"] == expected
        assert manifest["status"] == ("succeeded" if outcome == "success" else "failed")
        natural_exit = outcome in {"success", "worker_failure"}
        expected_child_code = {"success": 0, "worker_failure": 2}.get(outcome, -signal.SIGKILL)
        assert resource["raw_process_exit_code"] == expected_child_code
        assert signals == ([] if natural_exit else ["terminate", "kill"])
    finally:
        for child in [*owned, unrelated]:
            if child.poll() is None:
                child.kill()
            child.wait()


def callback_unit(tmp_path, iteration, *, check_error=False):
    # Execute only the actual callback class, without importing or constructing an
    # MLX backend. Upstream update-before-callback order has separate source evidence.
    source = Path(fallback_probe.__file__).read_text()
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "run_fallback")
    cls = next(node for node in function.body if isinstance(node, ast.ClassDef))
    path = tmp_path / "callback.py"
    path.write_text(textwrap.dedent("".join(source.splitlines(True)[cls.lineno-1:cls.end_lineno])))
    spec = importlib.util.spec_from_file_location("p01_callback_regression", path)
    unit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unit)
    chosen = SimpleNamespace(token_ids=(1, 2, 3, 9), completion_mask=(0, 0, 1, 1))
    rejected = SimpleNamespace(token_ids=(1, 2, 4, 5, 9), completion_mask=(0, 0, 0, 1, 1))
    progress = {"microsteps": 32 + iteration - 1, "training_tokens": 281,
                "processed_tokens": 6594, "processed_nonpadding_tokens": 6594,
                "optimizer_steps": 4}
    checks = []

    def check():
        checks.append(True)
        if check_error:
            raise RuntimeError("CPU injected resource check failure")

    unit.__dict__.update(
        mx=SimpleNamespace(synchronize=lambda: None), math=math, time=time,
        accumulation=8, assert_initial_dpo_loss=assert_initial_dpo_loss,
        active_pair=(chosen, rejected), progress=progress, sft_optimizer_steps=4,
        optimizer=SimpleNamespace(step=SimpleNamespace(item=lambda: iteration // 8)),
        iteration_start=time.perf_counter(), reports=[], root=tmp_path,
        write_json=write_json, check=check,
    )
    return unit, checks


@pytest.mark.parametrize("iteration,loss", [
    (8, math.log(2)), (1, 0.6945998072624207), (8, 0.6945998072624207),
    (1, float("nan")), (8, float("nan")), (8, float("inf")), (8, -float("inf")),
    (9, float("nan")),
])
def test_failed_loss_keeps_completed_step_loss_tokens_and_actual_optimizer(tmp_path, iteration, loss):
    unit, checks = callback_unit(tmp_path, iteration)
    failing = not math.isfinite(loss) or abs(loss - math.log(2)) > 2e-6
    if failing:
        with pytest.raises(ValueError):
            unit.Callback().on_train_loss_report({"iteration": iteration, "train_loss": loss})
    else:
        unit.Callback().on_train_loss_report({"iteration": iteration, "train_loss": loss})
    progress = json.loads((tmp_path / "progress.json").read_text())
    assert progress == unit.progress
    assert progress["microsteps"] == 32 + iteration
    assert progress["optimizer_steps"] == 4 + iteration // 8
    assert progress["training_tokens"] == 285
    assert progress["processed_tokens"] == progress["processed_nonpadding_tokens"] == 6601

    def reject_nonstandard(value):
        pytest.fail(f"Nonstandard JSON constant: {value}")

    (record,) = json.loads((tmp_path / "fallback-dpo-steps.json").read_text(),
                          parse_constant=reject_nonstandard)
    assert record["iteration"] == iteration and record["optimizer_steps"] == iteration // 8
    assert record["supervised_tokens"] == 4 and record["processed_tokens"] == 7
    if math.isfinite(loss):
        assert record["train_loss"] == loss
    else:
        assert record["train_loss"] is None
        assert record["nonfinite_values"]["train_loss"] == repr(loss)
    if failing:
        assert record["status"] == "failed" and record["failure"]["type"] == "ValueError"
        assert not checks
    else:
        assert "failure" not in record and checks == [True]


def test_finite_loss_keeps_work_if_following_resource_check_fails(tmp_path):
    unit, _ = callback_unit(tmp_path, 8, check_error=True)
    with pytest.raises(RuntimeError, match="resource check failure"):
        unit.Callback().on_train_loss_report({"iteration": 8, "train_loss": math.log(2)})
    assert json.loads((tmp_path / "progress.json").read_text())["optimizer_steps"] == 5
    assert json.loads((tmp_path / "fallback-dpo-steps.json").read_text())[0]["iteration"] == 8


def test_nonfinite_auxiliary_metric_remains_json_and_does_not_drop_loss(tmp_path):
    unit, _ = callback_unit(tmp_path, 8)
    with pytest.raises(ValueError, match="report metric"):
        unit.Callback().on_train_loss_report({
            "iteration": 8, "train_loss": math.log(2), "train_chosen_reward": float("inf"),
        })
    (record,) = json.loads((tmp_path / "fallback-dpo-steps.json").read_text())
    assert record["train_loss"] == math.log(2) and record["train_chosen_reward"] is None
    assert record["nonfinite_values"] == {"train_chosen_reward": "inf"}
    assert record["status"] == "failed" and unit.progress["optimizer_steps"] == 5
