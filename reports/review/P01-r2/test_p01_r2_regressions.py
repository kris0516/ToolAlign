"""Independent CPU checks of repaired monitoring and completed-step accounting."""

from __future__ import annotations

import ast
import errno
import hashlib
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

import psutil
import pytest

from toolalign.contracts import validate_record
from toolalign.training.compatibility import execution, fallback_probe
from toolalign.training.compatibility.core import Budget, assert_initial_dpo_loss, write_json

ROOT = Path(__file__).resolve().parents[3]


def load_report_builder():
    spec = importlib.util.spec_from_file_location(
        "r1_p01_r2_report_builder", ROOT / "reports/hardware/P01_BUILD_REPORT.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def smoke_request(tmp_path):
    fixture = json.loads((ROOT / "tests/fixtures/contracts/run.json").read_text())
    run_root = tmp_path / "runs" / "one"
    request = {
        "run_id": "p01-r2-original-cpu-check",
        "mode": "smoke",
        "output_dir": str(run_root),
        "budget": asdict(Budget(max_wall_seconds=3)),
        "git_commit": fixture["git_commit"],
        "source_hash": "3" * 64,
        "data_manifest_hash": fixture["data_manifest_hash"],
        "model_identity": fixture["model"],
        "hardware": fixture["hardware"],
        "dependency_versions": fixture["dependency_versions"],
    }
    path = tmp_path / "request.json"
    write_json(path, request)
    return path, run_root


def strict_json(path):
    def reject_constant(value):
        raise AssertionError(f"Nonstandard JSON number: {value}")

    return json.loads(path.read_text(), parse_constant=reject_constant)


@pytest.mark.parametrize("fault", ["pressure_timeout", "swap_read", "rss_read", "wait_control"])
def test_monitor_errors_preserve_original_exception_and_completed_progress(
    monkeypatch, tmp_path, fault
):
    requested, root = smoke_request(tmp_path)
    monkeypatch.setattr(execution, "prepare_config", lambda value: value)
    real_popen, real_process = subprocess.Popen, psutil.Process
    real_swap = psutil.swap_memory
    children, signals, waits, pressure_samples = [], [], [], []
    original_error = {
        "pressure_timeout": subprocess.TimeoutExpired(
            ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], 0.01
        ),
        "swap_read": OSError("R1 injected swap sample read failure"),
        "rss_read": psutil.AccessDenied(os.getpid(), "R1 injected RSS read failure"),
        "wait_control": None,
    }[fault]
    child_script = """
import json,os,signal,sys,time
from pathlib import Path
root=Path(sys.argv[1])
signal.signal(signal.SIGTERM,signal.SIG_IGN)
progress={'microsteps':7,'training_tokens':29,'processed_tokens':41,
          'processed_nonpadding_tokens':41,'optimizer_steps':2}
(root/'progress.json').write_text(json.dumps(progress))
(root/'ready.tmp').write_text(json.dumps({'pid':os.getpid(),'ppid':os.getppid()}))
(root/'ready.tmp').replace(root/'ready.json')
until=time.monotonic()+30
while not (root/'release').exists() and time.monotonic()<until:
    time.sleep(0.002)
"""

    class Child(real_popen):
        def wait(self, timeout=None):
            actual_timeout = 0.04 if timeout in (1, 10) else timeout
            try:
                return super().wait(timeout=actual_timeout)
            except subprocess.TimeoutExpired:
                waits.append(timeout)
                raise

        def terminate(self):
            signals.append("terminate")
            return super().terminate()

        def kill(self):
            signals.append("kill")
            return super().kill()

    def spawn(args, **kwargs):
        assert args[1:5] == ["-m", "toolalign.training.compatibility", "_worker", "--config"]
        child = Child([sys.executable, "-c", child_script, str(root)], **kwargs)
        children.append(child)
        until = time.monotonic() + 3
        while not (root / "ready.json").exists() and time.monotonic() < until:
            time.sleep(0.002)
        assert strict_json(root / "ready.json") == {"pid": child.pid, "ppid": os.getpid()}
        child.actual_create_time = real_process(child.pid).create_time()
        return child

    def pressure(args, **kwargs):
        assert args == ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]
        pressure_samples.append(1)
        if fault == "pressure_timeout" and len(pressure_samples) == 2:
            raise original_error
        if fault == "wait_control" and len(pressure_samples) == 3:
            (root / "release").touch()
        return "1\n"

    swap_calls = 0

    def swap():
        nonlocal swap_calls
        swap_calls += 1
        if fault == "swap_read" and swap_calls == 3:
            raise original_error
        return real_swap()

    def monitored_process(pid):
        owned = real_process(pid)
        reads = 0

        def memory_info():
            nonlocal reads
            reads += 1
            if fault == "rss_read" and reads == 2:
                raise original_error
            return owned.memory_info()

        return SimpleNamespace(memory_info=memory_info)

    unrelated = real_popen([sys.executable, "-c", "import time; time.sleep(30)"])
    monkeypatch.setattr(execution.subprocess, "Popen", spawn)
    monkeypatch.setattr(execution.subprocess, "check_output", pressure)
    monkeypatch.setattr(psutil, "Process", monitored_process)
    monkeypatch.setattr(psutil, "swap_memory", swap)
    result, caught, escaped_to_test_cleanup = None, None, False
    try:
        try:
            result = execution.launch(requested)
        except Exception as exc:
            caught = exc
        assert len(children) == 1
        child = children[0]
        escaped_to_test_cleanup = child.poll() is None
        assert not escaped_to_test_cleanup
        with pytest.raises(ChildProcessError):
            os.waitpid(child.pid, os.WNOHANG)
        assert unrelated.poll() is None
        assert 1 in waits, "An ordinary real child wait timeout must occur before the outcome"
        manifest = strict_json(root / "run.json")
        resources = strict_json(root / "resources.json")
        validate_record(manifest, "run")
        assert manifest["ended_at"] is not None
        assert manifest["training_tokens"] == 29 and manifest["optimizer_steps"] == 2
        assert resources["samples"] and resources["peak_rss_bytes"] > 0
        for artifact in manifest["artifacts"]:
            path = root / artifact["relative_path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
            assert path.stat().st_size == artifact["size_bytes"]
        (summary,) = load_report_builder().summarize(root.parent)["runs"]
        if fault == "wait_control":
            assert caught is None and result == 0 and not signals
            assert manifest["status"] == "succeeded"
            assert resources["monitor_error"] is None
            assert resources["exit_code"] == resources["raw_process_exit_code"] == 0
            assert len(resources["samples"]) == 3
        else:
            assert caught is original_error
            assert manifest["status"] == "failed" and manifest["exit_code"] == 1
            assert resources["stop_reason"] == "monitor_error"
            assert resources["raw_process_exit_code"] == child.returncode == -signal.SIGKILL
            assert resources["monitor_error"] == {
                "type": type(original_error).__name__, "message": str(original_error)
            }
            assert signals == ["terminate", "kill"]
            assert summary["assessment"] == "FAILED_MONITOR"
            assert summary["training_tokens"] == 29 and summary["optimizer_steps"] == 2
        write_json(tmp_path / "monitor-observation.json", {
            "fault": fault,
            "same_original_exception": caught is original_error,
            "owned_pid": child.pid,
            "actual_child_create_time": child.actual_create_time,
            "actual_child_returncode": child.returncode,
            "owned_child_already_reaped": True,
            "unrelated_child_remained_alive": True,
            "wait_timeouts": waits,
            "signals": signals,
            "manifest_status": manifest["status"],
            "manifest_training_tokens": manifest["training_tokens"],
            "manifest_optimizer_steps": manifest["optimizer_steps"],
            "resources_sha256": hashlib.sha256((root / "resources.json").read_bytes()).hexdigest(),
            "summary_assessment": summary["assessment"],
        })
    finally:
        for child in [*children, unrelated]:
            if child.poll() is None:
                child.kill()
            child.wait()


@pytest.mark.parametrize("stage", ["initial_swap", "popen"])
def test_initialization_failure_leaves_a_terminal_attempt(monkeypatch, tmp_path, stage):
    requested, root = smoke_request(tmp_path)
    monkeypatch.setattr(execution, "prepare_config", lambda value: value)
    original_error = OSError(
        errno.EIO if stage == "initial_swap" else errno.EAGAIN,
        "R1 injected initial swap baseline read failure" if stage == "initial_swap"
        else "R1 injected process creation failure",
    )
    launches = []

    def failing_baseline():
        if stage == "initial_swap":
            raise original_error
        return SimpleNamespace(used=0)

    def unexpected_launch(*args, **kwargs):
        launches.append(True)
        if stage == "popen":
            raise original_error
        raise AssertionError("No child should be launched after a failed resource baseline")

    monkeypatch.setattr(psutil, "swap_memory", failing_baseline)
    monkeypatch.setattr(execution.subprocess, "Popen", unexpected_launch)
    with pytest.raises(OSError) as caught:
        execution.launch(requested)
    assert caught.value is original_error
    assert len(launches) == int(stage == "popen")
    manifest = strict_json(root / "run.json")
    validate_record(manifest, "run")
    summary = load_report_builder().summarize(root.parent)
    write_json(tmp_path / "initialization-observation.json", {
        "stage": stage,
        "same_original_exception": True,
        "popen_calls": len(launches),
        "actual_created_children": 0,
        "manifest_status": manifest["status"],
        "manifest_ended_at": manifest["ended_at"],
        "manifest_exit_code": manifest["exit_code"],
        "resources_exists": (root / "resources.json").exists(),
        "summary_runs": len(summary["runs"]),
    })
    assert manifest["status"] == "failed" and manifest["ended_at"] is not None, (
        "An initialization failure left an attempted run permanently running"
    )
    assert len(summary["runs"]) == 1


def actual_callback_unit(tmp_path):
    source = Path(fallback_probe.__file__).read_text()
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "run_fallback")
    callback = next(node for node in function.body
                    if isinstance(node, ast.ClassDef) and node.name == "Callback")
    isolated = textwrap.dedent("".join(source.splitlines(True)[callback.lineno - 1:callback.end_lineno]))
    path = tmp_path / "actual_callback.py"
    path.write_text(isolated)
    spec = importlib.util.spec_from_file_location("r1_p01_r2_actual_callback", path)
    unit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unit)
    unit.callback_source_sha256 = hashlib.sha256(isolated.encode()).hexdigest()
    unit.progress = {
        "microsteps": 32, "training_tokens": 400, "processed_tokens": 1000,
        "processed_nonpadding_tokens": 1000, "optimizer_steps": 4,
    }
    unit.checks = []
    unit.__dict__.update(
        mx=SimpleNamespace(synchronize=lambda: None), math=math, time=time, accumulation=8,
        assert_initial_dpo_loss=assert_initial_dpo_loss, sft_optimizer_steps=4,
        reports=[], root=tmp_path, write_json=write_json,
        check=lambda: unit.checks.append(True),
    )
    return unit


class CPUScalar:
    """Use the same scalar extraction boundary as native numeric report values."""

    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


CALLBACK_CASES = [
    (1, "finite_bad"), (4, "finite_bad"), (8, "finite_bad"),
    (1, "nan"), (8, "nan"), (8, "inf"), (8, "-inf"),
    (9, "nan"), (9, "inf"), (9, "-inf"),
    (8, "near_upper"), (8, "near_lower"), (9, "finite_after_first_cycle"),
    (8, "aux_nan"), (8, "aux_inf"), (8, "aux_negative_inf"),
]


@pytest.mark.parametrize("last_iteration,kind", CALLBACK_CASES)
def test_sequential_callbacks_preserve_every_completed_step(tmp_path, last_iteration, kind):
    unit = actual_callback_unit(tmp_path)
    loss = {
        "finite_bad": math.log(2) + 3e-6,
        "near_upper": math.log(2) + 1e-6,
        "near_lower": math.log(2) - 1e-6,
        "finite_after_first_cycle": math.log(2) + 0.25,
        "nan": float("nan"), "inf": float("inf"), "-inf": -float("inf"),
    }.get(kind, math.log(2))
    auxiliary = {"aux_nan": float("nan"), "aux_inf": float("inf"),
                 "aux_negative_inf": -float("inf")}
    expect_failure = kind not in {"near_upper", "near_lower", "finite_after_first_cycle"}
    caught = None
    for iteration in range(1, last_iteration + 1):
        # Alternating original pairs consume 7/9 processed and 5/7 supervised tokens.
        lengths = (5, 4) if iteration % 2 else (6, 5)
        unit.active_pair = tuple(
            SimpleNamespace(token_ids=tuple(range(length)), completion_mask=(0, 0) + (1,) * (length - 2))
            for length in lengths
        )
        unit.optimizer = SimpleNamespace(step=CPUScalar(iteration // 8))
        unit.iteration_start = time.perf_counter()
        final = iteration == last_iteration
        info = {"iteration": iteration, "train_loss": CPUScalar(loss if final else math.log(2))}
        if final and kind in auxiliary:
            info["train_chosen_reward"] = CPUScalar(auxiliary[kind])
        try:
            unit.Callback().on_train_loss_report(info)
        except ValueError as exc:
            assert final and expect_failure
            caught = exc
    assert (caught is not None) is expect_failure
    odd, even = (last_iteration + 1) // 2, last_iteration // 2
    expected = {
        "microsteps": 32 + last_iteration,
        "training_tokens": 400 + 5 * odd + 7 * even,
        "processed_tokens": 1000 + 7 * odd + 9 * even,
        "processed_nonpadding_tokens": 1000 + 7 * odd + 9 * even,
        "optimizer_steps": 4 + last_iteration // 8,
    }
    assert unit.progress == strict_json(tmp_path / "progress.json") == expected
    reports = strict_json(tmp_path / "fallback-dpo-steps.json")
    assert len(reports) == last_iteration
    assert [row["iteration"] for row in reports] == list(range(1, last_iteration + 1))
    assert [row["optimizer_steps"] for row in reports] == [i // 8 for i in range(1, last_iteration + 1)]
    assert sum(row["supervised_tokens"] for row in reports) == expected["training_tokens"] - 400
    assert sum(row["processed_tokens"] for row in reports) == expected["processed_tokens"] - 1000
    assert all(math.isfinite(row["synchronized_seconds"]) for row in reports)
    last = reports[-1]
    if math.isfinite(loss):
        assert last["train_loss"] == loss
    else:
        assert last["train_loss"] is None
        assert last["nonfinite_values"]["train_loss"] == kind
    if kind in auxiliary:
        assert last["train_chosen_reward"] is None
        assert last["nonfinite_values"] == {"train_chosen_reward": repr(auxiliary[kind])}
    if expect_failure:
        assert last["status"] == "failed"
        assert last["failure"] == {"type": "ValueError", "message": str(caught)}
    assert len(unit.checks) == last_iteration - int(expect_failure)
    write_json(tmp_path / "callback-observation.json", {
        "kind": kind, "last_iteration": last_iteration,
        "callback_source_sha256": unit.callback_source_sha256,
        "raised_exception": type(caught).__name__ if caught is not None else None,
        "progress": expected, "recorded_reports": len(reports),
        "last_loss": last["train_loss"], "nonfinite_values": last.get("nonfinite_values", {}),
        "strict_json_valid": True,
    })
