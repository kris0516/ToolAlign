"""Real CPU processes exercise supervisor cleanup without data or frameworks."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from toolalign.training.cuda_sft import runtime
from toolalign.training.cuda_sft.protocol import CONFIG_SHA256


def _original_cpu_child(command, request, connection):
    os.setsid()
    root = Path(request["output_dir"])
    (root / "ready.tmp").write_text(json.dumps({"pid": os.getpid(), "pgid": os.getpgrp(),
        "frameworks": sorted({"torch", "transformers", "mlx", "peft"} & set(sys.modules))}))
    (root / "ready.tmp").replace(root / "ready.json")
    if request["fixture_mode"] == "success":
        connection.send({"status": "PASS"})
        connection.close()
        return
    deadline = time.monotonic() + 30
    with (root / "heartbeat.txt").open("w") as heartbeat:
        while time.monotonic() < deadline:
            heartbeat.write("alive\n")
            heartbeat.flush()
            time.sleep(0.05)


def _actor(root, mode):
    # Only the work body is replaced; spawn, session, deadline and cleanup are real.
    runtime._child = _original_cpu_child
    previous = signal.getsignal(signal.SIGTERM)
    workspace_before = os.environ.get("CUBLAS_WORKSPACE_CONFIG")
    assert "torch" not in sys.modules
    request = {"schema": "toolalign.cuda-sft-prepare.v1", "authorized_by": "S1",
        "run_kind": "capacity", "profile": "formal", "source_commit": "1" * 40,
        "config_sha256": CONFIG_SHA256, "repository": str(Path(__file__).resolve().parents[2]),
        "output_dir": str(root), "max_wall_seconds": 2 if mode == "deadline" else 20,
        "max_output_bytes": 4096, "fixture_mode": mode}
    try:
        result = runtime.supervise(request, command="prepare")
    except BaseException as exc:
        result = {"error": type(exc).__name__, "exit_code": getattr(exc, "code", None)}
    result["handler_restored"] = signal.getsignal(signal.SIGTERM) == previous
    result["parent_policy_unchanged"] = ("torch" not in sys.modules
        and os.environ.get("CUBLAS_WORKSPACE_CONFIG") == workspace_before)
    (root / "result.json").write_text(json.dumps(result))


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


@pytest.mark.parametrize("mode", ["external_sigterm", "deadline", "success"])
def test_supervisor_reaps_owned_child_and_restores_handler(tmp_path, mode):
    ready = None
    with (tmp_path / "actor.log").open("w") as log:
        actor = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), str(tmp_path), mode],
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not (tmp_path / "ready.json").exists():
                assert actor.poll() is None, (tmp_path / "actor.log").read_text()
                time.sleep(0.02)
            ready = json.loads((tmp_path / "ready.json").read_text())
            assert ready["pid"] == ready["pgid"] and ready["pgid"] != os.getpgrp()
            assert ready["frameworks"] == []
            if mode == "external_sigterm":
                os.killpg(actor.pid, signal.SIGTERM)
            actor.wait(timeout=10)
            child_alive = _alive(ready["pid"])
            observation = {"mode": mode, "actor_exit_code": actor.returncode,
                           "child_pid": ready["pid"], "child_alive_after_return": child_alive}
            (tmp_path / "observation.json").write_text(json.dumps(observation))
            assert not child_alive, observation
            assert actor.returncode == 0, (tmp_path / "actor.log").read_text()
            result = json.loads((tmp_path / "result.json").read_text())
            assert result["handler_restored"]
            assert result["parent_policy_unchanged"]
            if mode == "external_sigterm":
                assert result["error"] == "SystemExit" and result["exit_code"] == 143
            elif mode == "deadline":
                assert result["error"] == "TimeoutError"
            else:
                assert result["status"] == "PASS"
        finally:
            if ready is None and (tmp_path / "ready.json").exists():
                ready = json.loads((tmp_path / "ready.json").read_text())
            if ready is not None and _alive(ready["pid"]):
                os.killpg(ready["pgid"], signal.SIGKILL)
            if actor.poll() is None:
                os.killpg(actor.pid, signal.SIGKILL)
            actor.wait(timeout=5)


if __name__ == "__main__":
    _actor(Path(sys.argv[1]), sys.argv[2])
