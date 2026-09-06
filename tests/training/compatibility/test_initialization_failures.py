"""CPU checks for failed registered attempts before a worker can produce metrics."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import signal
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolalign.contracts import validate_record
from toolalign.training.compatibility import execution
from toolalign.training.compatibility.core import Budget, write_json


def prepared_request(tmp_path, mode):
    fixture = json.loads((Path(__file__).parents[2] / "fixtures/contracts/run.json").read_text())
    root = tmp_path / "runs" / "attempt"
    config = {
        "run_id": "p01-r4-cpu-attempt", "mode": mode, "output_dir": str(root),
        "budget": asdict(Budget(max_wall_seconds=3)), "source_hash": "3" * 64,
        "git_commit": fixture["git_commit"], "data_manifest_hash": fixture["data_manifest_hash"],
        "model_identity": fixture["model"], "hardware": fixture["hardware"],
        "dependency_versions": fixture["dependency_versions"],
    }
    requested = tmp_path / "requested.json"
    write_json(requested, config)
    return requested, root


def exercise_startup_failure(monkeypatch, tmp_path, stage, mode="smoke", baseline=4096):
    """Inject only the selected startup failure into the actual launch path."""
    requested, root = prepared_request(tmp_path, mode)
    monkeypatch.setattr(execution, "prepare_config", lambda config: config)
    error = OSError(errno.EAGAIN if stage == "popen" else errno.EIO, "CPU startup failure")
    calls = {"baseline": 0, "popen": 0, "process_handle": 0}

    def swap():
        calls["baseline"] += 1
        if stage == "initial_swap":
            raise error
        return SimpleNamespace(used=baseline)

    def no_process(*args, **kwargs):
        calls["process_handle"] += 1
        pytest.fail("No child exists to monitor or reap")

    def popen(*args, **kwargs):
        calls["popen"] += 1
        assert stage == "popen"
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        raise error

    class Environment(dict):
        def copy(self):
            raise error

    real_open = Path.open
    streams = []

    def open_file(path, *args, **kwargs):
        if path == root / "stdout.log":
            if stage == "stdout_open":
                raise error
            stream = real_open(path, *args, **kwargs)
            streams.append(stream)
            return stream
        return real_open(path, *args, **kwargs)

    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(
        swap_memory=swap, Process=no_process, NoSuchProcess=ProcessLookupError,
    ))
    monkeypatch.setattr(execution.subprocess, "Popen", popen)
    monkeypatch.setattr(Path, "open", open_file)
    if stage == "environment":
        monkeypatch.setattr(execution.os, "environ", Environment(os.environ))
    with pytest.raises(OSError) as caught:
        execution.launch(requested)
    assert caught.value is error
    assert calls == {"baseline": int(stage != "environment"),
                     "popen": int(stage == "popen"), "process_handle": 0}
    assert all(stream.closed for stream in streams)
    resources = json.loads((root / "resources.json").read_text())
    assert resources["initialization_error"] == {"type": "BlockingIOError" if stage == "popen"
                                                else "OSError", "message": str(error)}
    assert resources["monitor_error"] is None
    assert resources["failure_stage"] == stage
    assert resources["stop_reason"] == "initialization_error" and resources["exit_code"] == 1
    assert resources["child_started"] is False and resources["raw_process_exit_code"] is None
    assert resources["peak_rss_bytes"] is None and resources["samples"] == []
    expected_baseline = None if stage in {"environment", "initial_swap"} else baseline
    assert resources["initial_swap_bytes"] == expected_baseline
    assert resources["wall_seconds"] >= 0
    assert not (root / "progress.json").exists()
    if mode == "math":
        assert not (root / "run.json").exists()
    else:
        manifest = json.loads((root / "run.json").read_text())
        validate_record(manifest, "run")
        assert manifest["status"] == "failed" and manifest["ended_at"] is not None
        assert manifest["exit_code"] == 1
        assert manifest["training_tokens"] == manifest["optimizer_steps"] == 0
        assert any(item["relative_path"] == "resources.json" for item in manifest["artifacts"])
        for item in manifest["artifacts"]:
            path = root / item["relative_path"]
            assert path.stat().st_size == item["size_bytes"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    return root


@pytest.mark.parametrize("mode", ["smoke", "math"])
@pytest.mark.parametrize("stage", ["environment", "initial_swap", "stdout_open", "popen"])
def test_unstarted_attempt_preserves_error_and_missing_measurements(monkeypatch, tmp_path, mode, stage):
    exercise_startup_failure(monkeypatch, tmp_path, stage, mode)


def test_failure_before_first_rss_reaps_real_child_without_inventing_a_measurement(
    monkeypatch, tmp_path,
):
    requested, root = prepared_request(tmp_path, "smoke")
    monkeypatch.setattr(execution, "prepare_config", lambda config: config)
    error = OSError(errno.EACCES, "CPU injected monitor handle failure")
    actual_popen = subprocess.Popen
    children = []

    def popen(*args, **kwargs):
        child = actual_popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        children.append(child)
        return child

    def process(pid):
        assert len(children) == 1 and pid == children[0].pid
        raise error

    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(
        Process=process, swap_memory=lambda: SimpleNamespace(used=4096),
        NoSuchProcess=ProcessLookupError,
    ))
    monkeypatch.setattr(execution.subprocess, "Popen", popen)
    try:
        with pytest.raises(OSError) as caught:
            execution.launch(requested)
        assert caught.value is error and len(children) == 1
        assert children[0].returncode == -signal.SIGTERM
        with pytest.raises(ChildProcessError):
            os.waitpid(children[0].pid, os.WNOHANG)
        resources = json.loads((root / "resources.json").read_text())
        assert resources["child_started"] is True
        assert resources["raw_process_exit_code"] == -signal.SIGTERM
        assert resources["initialization_error"] is None
        assert resources["monitor_error"] == {"type": type(error).__name__, "message": str(error)}
        assert resources["peak_rss_bytes"] is None and resources["samples"] == []
        assert resources["failure_stage"] == "monitor"
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait()
