"""G5 uses the existing bounded Colab worker and transport; all runs here are local fixtures."""

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


def evaluation_payload(run, *, seconds=5):
    repository, directory, payload = run
    config = json.loads(payload["run_config_text"])
    config.update(schema="toolalign.cuda-evaluation-run.v1", run_kind="evaluation", mode="action-only",
                  plan=[{"unit_id": 0}], stop_after_unit=1, max_wall_seconds=seconds)
    del config["max_optimizer_steps"], config["persistent_dir"]
    raw = json_bytes(config)
    payload = payload | {"run_config_text": raw.decode(), "run_config_sha256": hashlib.sha256(raw).hexdigest()}
    atomic_json(directory / "control.json", payload)
    (directory / "run.json").write_bytes(raw)
    with remote.registry(repository, payload) as state:
        state["runs"][payload["run_id"]]["run_config_sha256"] = payload["run_config_sha256"]
    return repository, directory, payload


def test_controller_accepts_only_fixed_evaluation_module(run, cli, tmp_path):
    repository, _, payload = evaluation_payload(run)
    _, spec, _ = local_spec(tmp_path, cli, payload)
    assert control.make_payload(spec, payload["endpoint"]) == payload
    config = validate_payload(payload, repository)
    assert config["run_kind"] == "evaluation" and "max_optimizer_steps" not in config


@pytest.mark.parametrize("patch", [
    {"run_kind": "shell"}, {"mode": "arbitrary"}, {"max_wall_seconds": 14401},
    {"mode": "capacity", "max_wall_seconds": 61}, {"plan": [{}] * 225},
    {"mode": "l1", "plan": [{}] * 105}, {"mode": "replay", "plan": [{}] * 9},
    {"mode": "capacity", "plan": [{}] * 3}, {"max_optimizer_steps": 1},
    {"persistent_dir": "/tmp/fake"}, {"max_output_bytes": 1024**3 + 1}, {"stop_after_unit": 2},
])
def test_control_rejects_evaluation_scope_or_budget_expansion(run, patch):
    repository, _, payload = evaluation_payload(run)
    raw = json_bytes(json.loads(payload["run_config_text"]) | patch)
    with pytest.raises(ValueError):
        validate_payload(payload | {"run_config_text": raw.decode(),
                                    "run_config_sha256": hashlib.sha256(raw).hexdigest()}, repository)


@pytest.mark.parametrize("timeout", [False, True])
def test_local_worker_timeout_cleanup_export_and_recovery(run, tmp_path, timeout):
    repository, directory, payload = evaluation_payload(run, seconds=1 if timeout else 5)
    executable = repository / ".toolalign-local/cuda-env/bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text(f"#!{sys.executable}\n" + """
import json,pathlib,sys,time
run = json.loads(pathlib.Path(sys.argv[-1]).read_text())
output = pathlib.Path(run['output_dir'])
output.mkdir()
(output / 'results.jsonl').write_text('{"status":"ORIGINAL_CPU_CONTROL_FIXTURE"}\\n')
print('original local evaluation-control fixture', flush=True)
""" + ("time.sleep(30)\n" if timeout else ""))
    executable.chmod(0o700)
    atomic_json(directory / "launch.json", {"submitted_at_utc": "CPU_FIXTURE"})
    assert remote.worker(repository, payload) == (124 if timeout else 0)
    record = read_json(directory / "exit.json")
    assert record["argv"][-4:] == ["toolalign.evaluation.cuda_eval", "evaluate", "--run-config", str(directory / "run.json")]
    assert record["timed_out"] is timeout
    if timeout:
        assert record["timeout_cleanup_completed"] is True
    with pytest.raises(ProcessLookupError):
        os.kill(read_json(directory / "process.json")["pid"], 0)
    receipt = remote.export(repository, payload)
    target = tmp_path / "recovered-evaluation"
    control.extract_verified(Path(receipt["archive_path"]), target, receipt, payload)
    assert (target / "output/results.jsonl").read_bytes() == (directory / "output/results.jsonl").read_bytes()
    remote.acknowledge_recovery(repository, payload, receipt)
    assert remote.stop_ready(repository, payload)["stop_ready"] is True
