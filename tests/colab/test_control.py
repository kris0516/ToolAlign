"""CPU fixtures for control behavior; none allocate or connect to Colab."""

from __future__ import annotations

import copy
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts/colab"
sys.path.insert(0, str(SCRIPTS))
import control  # noqa: E402
import remote  # noqa: E402
from support import atomic_json, digest, json_bytes, read_json  # noqa: E402


@pytest.fixture
def run(tmp_path, monkeypatch):
    repository = tmp_path / "content/toolalign"
    repository.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    (repository / "requirements").mkdir()
    lock = repository / remote.LOCK_FILE
    lock.write_text("torch==2.8.0+cu128\n")
    config = {
        "schema": "toolalign.cuda-sft-run.v1", "authorized_by": "S1",
        "run_id": "fixture-1", "source_commit": "a" * 40,
        "dependency_lock_sha256": digest(lock), "repository": str(repository),
        "lock_root": str(repository), "output_dir": str(repository / "runs/fixture-1/output"),
        "persistent_dir": str(repository.parent / "toolalign-staging/fixture-1"),
        "max_wall_seconds": 1, "max_optimizer_steps": 3, "max_output_bytes": 4096,
    }
    data = json_bytes(config)
    payload = {
        "session": "toolalign-fixture", "endpoint": "fixture-endpoint",
        "run_id": config["run_id"], "source_commit": config["source_commit"],
        "dependency_lock_sha256": digest(lock), "run_config_text": data.decode(),
        "run_config_sha256": hashlib.sha256(data).hexdigest(),
        "allocated_at_utc": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        "max_allocation_seconds": 600,
    }
    monkeypatch.setattr(control, "REPOSITORY", repository)
    monkeypatch.setattr(remote, "verify_source", lambda *args: None)
    monkeypatch.setattr(remote, "tmux_exists", lambda *args: False)
    directory = remote.run_directory(repository, payload)
    directory.mkdir(parents=True)
    atomic_json(directory / "control.json", payload)
    (directory / "run.json").write_bytes(data)
    with remote.registry(repository, payload) as state:
        state["runs"][payload["run_id"]] = {
            "run_config_sha256": payload["run_config_sha256"], "recovered": None,
        }
    return repository, directory, payload


@pytest.fixture
def cli(tmp_path):
    """Real local executable with the observed 0.7.4 status format."""
    executable = tmp_path / "fixture-cli"
    state = tmp_path / "fixture-cli.json"
    atomic_json(state, {"endpoint": "fixture-endpoint", "calls": []})
    executable.write_text(f"#!{sys.executable}\n" + '''
import json, pathlib, shutil, sys
path = pathlib.Path(__file__).with_suffix('.json')
state = json.loads(path.read_text())
args = sys.argv[1:]
state['calls'].append(args)
session = args[args.index('-s') + 1]
if args[0] == 'status':
    if state['endpoint']:
        print(f"[{session}] {state['endpoint']} | Hardware: L4 | Shape: default | Variant: GPU | Status: IDLE")
    else:
        print(f"[colab] Session '{session}' not found.")
elif args[0] == 'stop':
    state['endpoint'] = None
elif args[0] == 'download':
    shutil.copyfile(state['export_path'], args[-1])
elif args[0] == 'ssh':
    raise SystemExit('fixture: an SSH proxy must not be opened in a missing-session test')
path.write_text(json.dumps(state))
''')
    executable.chmod(0o700)
    return executable, state


def local_spec(tmp_path, cli, payload):
    executable, _ = cli
    config_file = tmp_path / "run.json"
    config_file.write_text(payload["run_config_text"])
    spec = {
        "schema": "toolalign.colab-control.v1", "cli": str(executable),
        "ssh_identity": str(tmp_path / "unused-key"), "run_config_file": str(config_file),
        "run_config_sha256": payload["run_config_sha256"], "run_id": payload["run_id"],
        "session": payload["session"], "local_root": str(tmp_path / ".toolalign-local/recovery"),
        "allocated_at_utc": payload["allocated_at_utc"],
        "max_allocation_seconds": payload["max_allocation_seconds"],
    }
    path = tmp_path / "spec.json"
    atomic_json(path, spec)
    _, directory = control.load_spec(path)
    current = control.session_status(str(executable), payload["session"])
    assert control.owner(spec, directory, current, create=True) == payload
    return path, spec, directory


def terminal_output(directory):
    atomic_json(directory / "exit.json", {"exit_code": 7})
    atomic_json(directory / "launch.json", {"submitted": True})
    checkpoint = directory / "output/checkpoint-2"
    checkpoint.mkdir(parents=True)
    (checkpoint / "state.pt").write_bytes(b"original fixture optimizer, RNG, cursor and adapter bytes")
    atomic_json(checkpoint / "manifest.json", {"checkpoint_sha256": digest(checkpoint / "state.pt")})
    return checkpoint


def test_missing_session_never_opens_auto_creating_proxy(run, cli, tmp_path, monkeypatch):
    _, _, payload = run
    path, _, _ = local_spec(tmp_path, cli, payload)
    state = read_json(cli[1])
    state["endpoint"] = None
    atomic_json(cli[1], state)
    monkeypatch.setattr(sys, "argv", ["control.py", "--spec", str(path), "proxy"])
    with pytest.raises(ValueError, match="absent"):
        control.main()
    assert {call[0] for call in read_json(cli[1])["calls"]} == {"status"}


def test_other_project_and_recycled_endpoint_are_rejected(run, cli, tmp_path):
    _, _, payload = run
    _, spec, directory = local_spec(tmp_path, cli, payload)
    with pytest.raises(ValueError, match="toolalign"):
        control.session_status(str(cli[0]), "other-project")
    with pytest.raises(ValueError, match="different instance"):
        control.owner(spec, directory, {"endpoint": "replacement"})


def test_setup_plan_is_installation_only():
    commands = remote.setup_commands(Path("/content/toolalign"), "/usr/bin/python3.12")
    assert commands[0][1:3] == ["-m", "venv"]
    assert "--require-hashes" in commands[1] and remote.CUDA_INDEX in commands[1]
    assert commands[2][-2:] == ["pip", "check"]
    assert not any("train" in word or "model" in word for command in commands for word in command)


def test_setup_refuses_mac_without_installing(run, monkeypatch):
    repository, directory, payload = run
    shutil.rmtree(directory)
    with remote.registry(repository, payload) as state:
        state["runs"].clear()
    monkeypatch.setattr(remote.platform, "system", lambda: "Darwin")
    with pytest.raises(ValueError, match="Linux x86_64"):
        remote.setup(repository, payload)
    assert not (repository / ".toolalign-local/cuda-env").exists()
    assert read_json(directory / "setup-exit.json")["exit_code"] == 1


def test_partial_setup_preserves_failure_and_cannot_repeat(run, monkeypatch):
    repository, directory, payload = run
    # Start a new real control claim, with a fixture installer that fails.
    shutil.rmtree(directory)
    with remote.registry(repository, payload) as state:
        state["runs"].clear()
    monkeypatch.setattr(remote.platform, "system", lambda: "Linux")
    monkeypatch.setattr(remote.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(remote.shutil, "which", lambda _: sys.executable)
    monkeypatch.setattr(remote, "setup_commands", lambda *args: [
        [sys.executable, "-c", "print('fixture install failure'); raise SystemExit(9)"]
    ])
    with pytest.raises(subprocess.CalledProcessError):
        remote.setup(repository, payload)
    saved = (directory / "setup-exit.json").read_bytes()
    assert read_json(directory / "setup-exit.json")["exit_code"] == 9
    assert "fixture install failure" in (directory / "setup.log").read_text()
    with pytest.raises(ValueError, match="already claimed"):
        remote.setup(repository, payload)
    assert (directory / "setup-exit.json").read_bytes() == saved
    assert remote.export(repository, payload)["archive_bytes"] > 0


def test_launch_keeps_failed_claim_and_refuses_resubmission(run, monkeypatch):
    repository, directory, payload = run
    atomic_json(directory / "environment.json", {"fixture": True})
    def failure(argv, **kwargs):
        raise subprocess.CalledProcessError(4, argv, output="", stderr="fixture tmux failed")
    monkeypatch.setattr(remote.subprocess, "run", failure)
    with pytest.raises(subprocess.CalledProcessError):
        remote.launch(repository, payload)
    assert read_json(directory / "launch-error.json")["exit_code"] == 4
    with pytest.raises(FileExistsError):
        remote.launch(repository, payload)


def test_existing_job_blocks_launch_and_export(run, monkeypatch):
    repository, directory, payload = run
    atomic_json(directory / "environment.json", {"fixture": True})
    monkeypatch.setattr(remote, "tmux_exists", lambda _: True)
    with pytest.raises(ValueError, match="existing tmux"):
        remote.launch(repository, payload)
    with pytest.raises(ValueError, match="still active"):
        remote.export(repository, payload)
    assert not (directory / "launch.json").exists()


@pytest.mark.parametrize("body, expected", [
    ("print('fixture failed', flush=True); raise SystemExit(7)", 7),
    ("import time; print('fixture waiting', flush=True); time.sleep(30)", 124),
])
def test_worker_records_actual_exit_and_reaps_timed_out_process(run, body, expected):
    repository, directory, payload = run
    executable = repository / ".toolalign-local/cuda-env/bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text(f"#!{sys.executable}\n{body}\n")
    executable.chmod(0o700)
    assert remote.worker(repository, payload) == expected
    record = read_json(directory / "exit.json")
    assert record["exit_code"] == expected
    assert record["timed_out"] == (expected == 124)
    assert "fixture" in (directory / "console.log").read_text()
    assert record["argv"][-4:] == ["toolalign.training.cuda_sft", "train", "--run-config", str(directory / "run.json")]
    with pytest.raises(ProcessLookupError):
        os.kill(read_json(directory / "process.json")["pid"], 0)


def test_ssh_timeout_retains_event_without_resubmission(run, cli, tmp_path, monkeypatch):
    _, _, payload = run
    path, spec, directory = local_spec(tmp_path, cli, payload)
    monkeypatch.setattr(control, "session_status", lambda *args: {"endpoint": payload["endpoint"]})
    def timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 1, output=b"partial fixture output")
    monkeypatch.setattr(control.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="inspect status"):
        control.remote_call(path, spec, directory, payload, "launch")
    events = list((directory / "events").glob("*.json"))
    assert len(events) == 1
    assert read_json(events[0])["timed_out"] is True
    assert read_json(events[0])["stdout"] == "partial fixture output"


def test_complete_checkpoint_download_readback_ack_and_owned_stop(run, cli, tmp_path, monkeypatch):
    repository, directory, payload = run
    checkpoint = terminal_output(directory)
    path, spec, local = local_spec(tmp_path, cli, payload)
    def transport(spec_path, spec, local, payload, action, *, recovered=None):
        if action == "export":
            receipt = remote.export(repository, payload)
            state = read_json(cli[1])
            state["export_path"] = receipt["archive_path"]
            atomic_json(cli[1], state)
            receipt["archive_path"] = "/content/toolalign/.toolalign-local/colab/exports/fixture.tar"
            # The fixture instance registry contains the same public transfer receipt.
            with remote.registry(repository, payload) as registry:
                registry["runs"][payload["run_id"]]["export"] = receipt
            return receipt
        if action == "ack":
            return remote.acknowledge_recovery(repository, payload, recovered)
        assert action == "stop-ready"
        return remote.stop_ready(repository, payload)
    monkeypatch.setattr(control, "remote_call", transport)
    result = control.recover(path, spec, local, payload)
    recovered = Path(result["directory"]) / "output/checkpoint-2/state.pt"
    assert recovered.read_bytes() == (checkpoint / "state.pt").read_bytes()
    assert control.stop(path, spec, local, payload)["status"] == "STOPPED_AND_ABSENCE_VERIFIED"
    state = read_json(cli[1])
    assert state["endpoint"] is None
    assert [call for call in state["calls"] if call[0] == "stop"] == [["stop", "-s", payload["session"]]]


def test_stop_refuses_missing_receipt_and_changed_durable_bytes(run, cli, tmp_path):
    repository, directory, payload = run
    terminal_output(directory)
    path, spec, local = local_spec(tmp_path, cli, payload)
    with pytest.raises(FileNotFoundError):
        control.stop(path, spec, local, payload)
    receipt = remote.export(repository, payload)
    target = tmp_path / "recovered"
    manifest = control.extract_verified(Path(receipt["archive_path"]), target, receipt, payload)
    atomic_json(local / "recovered.json", {"export": receipt, "directory": str(target), "manifest": manifest})
    (target / "output/checkpoint-2/state.pt").write_bytes(b"changed")
    with pytest.raises(ValueError, match="complete file manifest"):
        control.stop(path, spec, local, payload)
    assert not any(call[0] == "stop" for call in read_json(cli[1])["calls"])


def test_stop_ready_requires_all_recovered_runs_and_free_gpu_lease(run):
    from toolalign.runtime.gpu_lock import GPULease
    repository, directory, payload = run
    with pytest.raises(ValueError, match="not been recovered"):
        remote.stop_ready(repository, payload)
    terminal_output(directory)
    remote.acknowledge_recovery(repository, payload, remote.export(repository, payload))
    with GPULease(task_id="fixture", worker_alias="fixture", run_id="fixture", expected_job="CPU fixture",
                  memory_strategy="no model", repository=repository):
        with pytest.raises(ValueError, match="GPU lease"):
            remote.stop_ready(repository, payload)
    assert remote.stop_ready(repository, payload)["stop_ready"] is True
    assert read_json(repository / ".toolalign-local/colab/session.json")["stopping"] is True


def test_recovered_run_cannot_launch_and_changed_output_cannot_be_stopped(run, monkeypatch):
    repository, directory, payload = run
    atomic_json(directory / "environment.json", {"fixture": True})
    atomic_json(directory / "setup-exit.json", {"exit_code": 0})
    remote.acknowledge_recovery(repository, payload, remote.export(repository, payload))
    monkeypatch.setattr(remote.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0))
    with pytest.raises(ValueError, match="already recovered"):
        remote.launch(repository, payload)
    (directory / "new-output.txt").write_text("created after acknowledged recovery")
    # Use a real Git checkout for the shared lease observation.
    monkeypatch.undo()
    monkeypatch.setattr(remote, "tmux_exists", lambda _: False)
    with pytest.raises(ValueError, match="changed since recovery"):
        remote.stop_ready(repository, payload)


def test_export_requires_terminal_record_and_rejects_symlinks(run, tmp_path):
    repository, directory, payload = run
    with pytest.raises(ValueError, match="no terminal"):
        remote.export(repository, payload)
    terminal_output(directory)
    (directory / "output/unsafe").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="symlink"):
        remote.export(repository, payload)


@pytest.mark.parametrize("corruption", ["bytes", "traversal", "missing", "changed-file"])
def test_archive_recovery_rejects_corruption(run, tmp_path, corruption):
    repository, directory, payload = run
    terminal_output(directory)
    receipt = remote.export(repository, payload)
    archive = Path(receipt["archive_path"])
    if corruption == "bytes":
        with archive.open("ab") as handle:
            handle.write(b"changed")
    else:
        with tarfile.open(archive) as source:
            members = [(copy.copy(item), source.extractfile(item).read()) for item in source.getmembers()]
        with tarfile.open(archive, "w") as target:
            for member, data in members:
                if member.name.endswith("state.pt"):
                    if corruption == "missing":
                        continue
                    if corruption == "traversal":
                        member.name = "../escape"
                    else:
                        data = b"wrong checkpoint"
                        member.size = len(data)
                target.addfile(member, io.BytesIO(data))
        receipt.update(archive_sha256=digest(archive), archive_bytes=archive.stat().st_size)
    with pytest.raises(ValueError):
        control.extract_verified(archive, tmp_path / "recovered", receipt, payload)
    assert not (tmp_path / "escape").exists()
