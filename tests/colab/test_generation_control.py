"""The same Colab transport admits generation through one fixed module only."""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
import test_control
from support import atomic_json, json_bytes, read_json, validate_payload
from test_control import control, local_spec, remote

run = test_control.run
cli = test_control.cli


def generation_payload(run, *, max_wall_seconds=1):
    repository, directory, payload = run
    config = json.loads(payload["run_config_text"])
    config.update(schema="toolalign.cuda-generation-run.v1", run_kind="generation", max_trajectories=4,
                  max_wall_seconds=max_wall_seconds)
    del config["max_optimizer_steps"], config["persistent_dir"]
    payload = payload | {"run_config_text": json_bytes(config).decode(),
                         "run_config_sha256": hashlib.sha256(json_bytes(config)).hexdigest()}
    atomic_json(directory / "control.json", payload)
    (directory / "run.json").write_text(payload["run_config_text"])
    with remote.registry(repository, payload) as state:
        state["runs"][payload["run_id"]]["run_config_sha256"] = payload["run_config_sha256"]
    return repository, directory, payload


def test_controller_accepts_generation_without_fictional_optimizer_steps(run, cli, tmp_path):
    repository, _, payload = generation_payload(run)
    _, spec, _ = local_spec(tmp_path, cli, payload)
    assert control.make_payload(spec, payload["endpoint"]) == payload
    config = validate_payload(payload, repository)
    assert config["max_trajectories"] == 4
    assert "max_optimizer_steps" not in config


@pytest.mark.parametrize("patch", [
    {"schema": "toolalign.arbitrary-shell.v1"},
    {"run_kind": "shell"},
    {"max_trajectories": 513},
    {"max_optimizer_steps": 1},
    {"max_wall_seconds": 21601},
])
def test_generation_whitelist_and_budgets_reject_invalid_control(run, patch):
    repository, _, payload = generation_payload(run)
    config = json.loads(payload["run_config_text"]) | patch
    raw = json_bytes(config)
    changed = payload | {"run_config_text": raw.decode(), "run_config_sha256": hashlib.sha256(raw).hexdigest()}
    with pytest.raises(ValueError):
        validate_payload(changed, repository)


@pytest.mark.parametrize("timeout", [False, True])
def test_generation_worker_cleanup_export_and_recovery_use_existing_paths(run, tmp_path, timeout):
    # Successful process startup is not a one-second performance assertion.
    repository, directory, payload = generation_payload(run, max_wall_seconds=1 if timeout else 5)
    executable = repository / ".toolalign-local/cuda-env/bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text(f"#!{sys.executable}\n" + """
import json, pathlib, sys, time
run = json.loads(pathlib.Path(sys.argv[-1]).read_text())
output = pathlib.Path(run['output_dir'])
output.mkdir()
(output / 'candidates.jsonl').write_text('{"status":"CPU_CONTROL_FIXTURE"}\\n')
print('original local generation-control fixture', flush=True)
""" + ("time.sleep(30)\n" if timeout else ""))
    executable.chmod(0o700)
    atomic_json(directory / "launch.json", {"submitted_at_utc": "CPU_FIXTURE"})
    assert remote.worker(repository, payload) == (124 if timeout else 0)
    record = read_json(directory / "exit.json")
    assert record["argv"][-4:] == ["toolalign.training.cuda_generate", "generate",
                                  "--run-config", str(directory / "run.json")]
    assert record["timed_out"] is timeout
    if timeout:
        assert record["timeout_cleanup_completed"] is True
    with pytest.raises(ProcessLookupError):
        os.kill(read_json(directory / "process.json")["pid"], 0)
    receipt = remote.export(repository, payload)
    target = tmp_path / "recovered-generation"
    control.extract_verified(Path(receipt["archive_path"]), target, receipt, payload)
    assert (target / "output/candidates.jsonl").read_bytes() == (directory / "output/candidates.jsonl").read_bytes()
    remote.acknowledge_recovery(repository, payload, receipt)
    assert remote.stop_ready(repository, payload)["stop_ready"] is True
