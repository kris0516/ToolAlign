"""Independent CPU process-lifetime probes; no model or real GPU lease is used."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

import psutil
import pytest

from toolalign.training.compatibility import execution
from toolalign.training.compatibility.core import Budget


def supervised_child(monkeypatch, tmp_path, failure, mode="math"):
    """Drive the real launch supervisor around one inert, identity-tracked child."""
    run_root = tmp_path / "run"
    ready = run_root / "child-ready.json"
    config = {
        "run_id": "p01-r1-cpu-supervisor",
        "mode": mode,
        "output_dir": str(run_root),
        "budget": asdict(Budget(max_wall_seconds=1)),
    }
    if mode == "smoke":
        fixture = json.loads((Path(__file__).resolve().parents[3]
                              / "tests/fixtures/contracts/run.json").read_text())
        config.update(git_commit=fixture["git_commit"],
                      data_manifest_hash=fixture["data_manifest_hash"],
                      model_identity=fixture["model"], hardware=fixture["hardware"],
                      dependency_versions=fixture["dependency_versions"])
    config_path = tmp_path / "requested.json"
    config_path.write_text(json.dumps(config))
    monkeypatch.setattr(execution, "prepare_config", lambda supplied: supplied)
    original_popen = subprocess.Popen
    owned = []
    signals = []

    class InertChild(original_popen):
        def wait(self, timeout=None):
            # Exercise the escalation branch with a short test-only grace period.
            return super().wait(timeout=0.1 if timeout == 10 else timeout)

        def terminate(self):
            signals.append("terminate")
            return super().terminate()

        def kill(self):
            signals.append("kill")
            return super().kill()

    child_script = (
        "import json,os,signal,sys,time\n"
        "from pathlib import Path\n"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        "Path(sys.argv[1]).write_text(json.dumps({'pid':os.getpid()}))\n"
        "time.sleep(30)\n"
    )

    def spawn(args, **kwargs):
        assert args[1:5] == ["-m", "toolalign.training.compatibility", "_worker", "--config"]
        child = InertChild([sys.executable, "-u", "-c", child_script, str(ready)], **kwargs)
        owned.append(child)
        deadline = time.monotonic() + 3
        while not ready.exists():
            if child.poll() is not None or time.monotonic() > deadline:
                child.kill()
                child.wait()
                raise AssertionError("Inert child did not reach its synchronization point")
            time.sleep(0.005)
        assert json.loads(ready.read_text())["pid"] == child.pid
        owned_identity = psutil.Process(child.pid)
        child.observed_create_time = owned_identity.create_time()
        assert owned_identity.ppid() == os.getpid()
        return child

    def pressure(args, **kwargs):
        assert args == ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]
        if failure == "unreadable_pressure":
            raise subprocess.CalledProcessError(1, args, stderr="CPU injected read failure")
        if failure == "malformed_pressure":
            return "not-an-integer\n"
        return "2\n" if failure == "pressure" else "1\n"

    monkeypatch.setattr(execution.subprocess, "Popen", spawn)
    monkeypatch.setattr(execution.subprocess, "check_output", pressure)
    error = None
    result = None
    try:
        result = execution.launch(config_path)
    except Exception as exc:  # retain a real supervisor exception for explicit assertions
        error = exc
    finally:
        for child in owned:
            if child.poll() is None:
                # A test safety net must not hide a failed production cleanup assertion.
                child.leaked_before_test_cleanup = True
                child.kill()
                child.wait()
    assert len(owned) == 1
    child = owned[0]
    assert not getattr(child, "leaked_before_test_cleanup", False)
    assert child.returncode == -signal.SIGKILL
    assert signals == ["terminate", "kill"]
    with pytest.raises(ChildProcessError):
        os.waitpid(child.pid, os.WNOHANG)
    return result, error, run_root


@pytest.mark.parametrize("failure", ["pressure", "wall"])
def test_real_supervisor_stops_and_reaps_owned_stubborn_child(monkeypatch, tmp_path, failure):
    result, error, root = supervised_child(monkeypatch, tmp_path, failure)
    assert error is None
    assert result == 124
    raw = json.loads((root / "resources.json").read_text())
    assert raw["exit_code"] == 124 and raw["raw_process_exit_code"] == -signal.SIGKILL
    assert raw["stop_reason"] == ("memory_pressure" if failure == "pressure" else "wall")


@pytest.mark.parametrize("failure", ["unreadable_pressure", "malformed_pressure"])
def test_monitor_error_retains_terminal_resource_evidence(monkeypatch, tmp_path, failure):
    _, error, root = supervised_child(monkeypatch, tmp_path, failure, mode="smoke")
    assert isinstance(error, (subprocess.CalledProcessError, ValueError))
    # Every attempted run needs a terminal resource record even when monitoring fails.
    manifest = json.loads((root / "run.json").read_text())
    assert manifest["status"] == "failed" and manifest["ended_at"] is not None, (
        "Owned child was reaped, but the run manifest remains running without a terminal record")
    assert (root / "resources.json").exists()


def test_worker_exception_retains_lease_through_failure_serialization(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    script = """
import json,sys
from pathlib import Path
from toolalign.runtime import inspect_gpu_lock
from toolalign.training.compatibility import numerical
from toolalign.training.compatibility.execution import worker
root=Path(sys.argv[1])
class ProbeFailure(RuntimeError):
    def __str__(self):
        with (root/'held-during-failure.jsonl').open('a') as stream:
            stream.write(json.dumps({'held':inspect_gpu_lock()['held']})+'\\n')
        return 'intentional CPU failure'
def operation():
    assert inspect_gpu_lock()['held']
    raise ProbeFailure()
numerical.check_numerics=operation
worker({'run_id':'p01-r1-worker-failure','mode':'math','budget':{},'lock_timeout_seconds':0},root)
raise AssertionError('Worker returned before OS process exit')
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[3] / "src")
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        env=env, cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2, result.stderr
    assert json.loads((tmp_path / "failure.json").read_text())["type"] == "ProbeFailure"
    held = [json.loads(line)["held"] for line in
            (tmp_path / "held-during-failure.jsonl").read_text().splitlines()]
    assert held and all(held)
    from toolalign.runtime import inspect_gpu_lock

    assert inspect_gpu_lock(tmp_path)["held"] is False
