"""Regressions for R1's owned-group and all-run durable recovery findings."""

from __future__ import annotations

import copy
import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
import test_control
from test_control import (
    atomic_json,
    control,
    json_bytes,
    local_spec,
    read_json,
    remote,
    terminal_output,
)

run = test_control.run
cli = test_control.cli


def test_timeout_cleans_same_group_descendant_after_leader_exit(run, tmp_path):
    repository, directory, payload = run
    executable = repository / ".toolalign-local/cuda-env/bin/python"
    executable.parent.mkdir(parents=True)
    child_pid_file, heartbeat = tmp_path / "child.pid", tmp_path / "heartbeat"
    config = read_json(directory / "run.json")
    config["max_wall_seconds"] = 3
    raw = json_bytes(config)
    payload.update(run_config_text=raw.decode(), run_config_sha256=hashlib.sha256(raw).hexdigest())
    atomic_json(directory / "control.json", payload)
    (directory / "run.json").write_bytes(raw)
    child = tmp_path / "child.py"
    child.write_text(
        "import os,signal,time\nfrom pathlib import Path\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        f"Path({str(child_pid_file)!r}).write_text(str(os.getpid()))\n"
        "until = time.monotonic() + 30\n"
        "while time.monotonic() < until:\n"
        f"    Path({str(heartbeat)!r}).write_text(str(time.monotonic_ns()))\n"
        "    time.sleep(0.03)\n"
    )
    executable.write_text(
        f"#!{sys.executable}\nimport subprocess,sys,time\nfrom pathlib import Path\n"
        f"subprocess.Popen([sys.executable, {str(child)!r}])\n"
        f"while not Path({str(child_pid_file)!r}).exists(): time.sleep(0.01)\n"
        "print('descendant READY', flush=True)\ntime.sleep(30)\n"
    )
    executable.chmod(0o700)
    try:
        assert remote.worker(repository, payload) == 124
        ended = read_json(directory / "exit.json")
        assert ended["timed_out"] is True and ended["timeout_cleanup_completed"] is True
        assert "descendant READY" in (directory / "console.log").read_text()
        previous = heartbeat.read_bytes()
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            assert heartbeat.read_bytes() == previous
            time.sleep(0.03)
        # The group's leader has exited and been reaped, and no member remains.
        with pytest.raises(ProcessLookupError):
            os.killpg(read_json(directory / "process.json")["pid"], 0)
    finally:
        if child_pid_file.exists():
            child_pid = int(child_pid_file.read_text())
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                state = subprocess.run(["ps", "-p", str(child_pid), "-o", "stat="],
                                       capture_output=True, text=True, timeout=2)
                if not state.stdout.strip():
                    break
                time.sleep(0.03)
            assert not state.stdout.strip(), "fixture descendant was not cleaned up"


@pytest.fixture
def recovered_pair(run, cli, tmp_path, monkeypatch):
    repository, first_directory, first = run
    terminal_output(first_directory)
    second = copy.deepcopy(first)
    config = read_json(first_directory / "run.json")
    config.update(run_id="fixture-2", output_dir=str(repository / "runs/fixture-2/output"),
                  persistent_dir=str(repository.parent / "toolalign-staging/fixture-2"))
    raw = json_bytes(config)
    second.update(run_id="fixture-2", run_config_text=raw.decode(),
                  run_config_sha256=hashlib.sha256(raw).hexdigest())
    second_directory = remote.run_directory(repository, second)
    second_directory.mkdir(parents=True)
    atomic_json(second_directory / "control.json", second)
    (second_directory / "run.json").write_bytes(raw)
    with remote.registry(repository, second) as state:
        state["runs"][second["run_id"]] = {
            "run_config_sha256": second["run_config_sha256"], "recovered": None,
        }
    terminal_output(second_directory)

    def transport(spec_path, spec, local, payload, action, *, recovered=None):
        if action == "export":
            receipt = remote.export(repository, payload)
            state = read_json(cli[1])
            state["export_path"] = receipt["archive_path"]
            atomic_json(cli[1], state)
            receipt["archive_path"] = "/content/toolalign/.toolalign-local/colab/exports/fixture.tar"
            with remote.registry(repository, payload) as state:
                state["runs"][payload["run_id"]]["export"] = receipt
            return receipt
        if action == "ack":
            return remote.acknowledge_recovery(repository, payload, recovered)
        assert action == "stop-ready"
        return remote.stop_ready(repository, payload)

    monkeypatch.setattr(control, "remote_call", transport)
    local_runs = []
    for payload in (first, second):
        parent = tmp_path / payload["run_id"]
        parent.mkdir()
        local = local_spec(parent, cli, payload)
        control.recover(*local, payload)
        local_runs.append(local)
    return first, second, local_runs, cli[1]


def map_first_recovery(local_runs):
    path, spec, directory = local_runs[1]
    spec["recovery_directories"] = {"fixture-1": str(local_runs[0][2])}
    atomic_json(path, spec)
    loaded, loaded_directory = control.load_spec(path)
    assert loaded_directory == directory
    return path, loaded, directory


@pytest.mark.parametrize("damage", ["checkpoint", "archive", "both", "forged-manifest"])
def test_earlier_run_damage_blocks_stop_until_it_is_recovered_again(recovered_pair, damage):
    first, second, local_runs, cli_state = recovered_pair
    newer = map_first_recovery(local_runs)
    earlier_receipt = local_runs[0][2] / "recovered.json"
    receipt = read_json(earlier_receipt)
    checkpoint = Path(receipt["directory"]) / "output/checkpoint-2/state.pt"
    if damage in {"checkpoint", "both", "forged-manifest"}:
        checkpoint.write_bytes(b"damaged after the original verified recovery")
    if damage in {"archive", "both"}:
        Path(receipt["archive"]).unlink()
    if damage == "forged-manifest":
        # Even a locally self-consistent edited manifest must match the remote snapshot.
        receipt["manifest"]["files"]["output/checkpoint-2/state.pt"] = {
            "bytes": checkpoint.stat().st_size, "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        }
        atomic_json(earlier_receipt, receipt)
    with pytest.raises(ValueError, match="run fixture-1"):
        control.stop(*newer, second)
    state = read_json(cli_state)
    assert state["endpoint"] == second["endpoint"]
    assert not any(call[0] == "stop" for call in state["calls"])
    control.recover(*local_runs[0], first)
    assert control.stop(*newer, second)["status"] == "STOPPED_AND_ABSENCE_VERIFIED"
    # Re-reading an uncertain/completed stop uses the saved complete inventory.
    assert control.stop(*newer, second)["status"] == "STOPPED_AND_ABSENCE_VERIFIED"
    stops = [call for call in read_json(cli_state)["calls"] if call[0] == "stop"]
    assert stops == [["stop", "-s", second["session"]]]


def test_different_recovery_roots_require_explicit_correct_mapping(recovered_pair):
    _, second, local_runs, cli_state = recovered_pair
    with pytest.raises(ValueError, match="recovery_directories"):
        control.stop(*local_runs[1], second)
    path, spec, directory = local_runs[1]
    spec["recovery_directories"] = {"fixture-1": str(directory)}
    with pytest.raises(ValueError, match="differs from the instance snapshot"):
        control.stop(path, spec, directory, second)
    assert not any(call[0] == "stop" for call in read_json(cli_state)["calls"])
    assert control.stop(*map_first_recovery(local_runs), second)["status"] == "STOPPED_AND_ABSENCE_VERIFIED"


def test_unconfirmed_timeout_cleanup_cannot_be_exported(run):
    repository, directory, payload = run
    terminal_output(directory)
    atomic_json(directory / "exit.json", {
        "exit_code": 124, "timed_out": True, "timeout_cleanup_completed": False,
    })
    with pytest.raises(ValueError, match="cleanup is unconfirmed"):
        remote.export(repository, payload)
