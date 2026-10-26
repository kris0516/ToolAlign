"""G6 service whitelist and bounded local controller execution; no Colab calls."""

import hashlib
import json
import sys

import pytest
import test_control
from support import atomic_json, json_bytes, read_json, validate_payload
from test_control import control, local_spec, remote

run = test_control.run
cli = test_control.cli


def service_payload(run):
    repository, directory, payload = run
    config = json.loads(payload["run_config_text"])
    config.update(schema="toolalign.service-run.v1", run_kind="serving", max_generations=12,
                  max_wall_seconds=900, max_output_bytes=256 * 1024**2,
                  listen_host="127.0.0.1", listen_port=8080, cache_enabled=True)
    del config["max_optimizer_steps"], config["persistent_dir"]
    raw = json_bytes(config)
    payload = payload | {"run_config_text": raw.decode(), "run_config_sha256": hashlib.sha256(raw).hexdigest()}
    atomic_json(directory / "control.json", payload)
    (directory / "run.json").write_bytes(raw)
    with remote.registry(repository, payload) as state:
        state["runs"][payload["run_id"]]["run_config_sha256"] = payload["run_config_sha256"]
    return repository, directory, payload


def test_existing_controller_dispatches_fixed_service_module(run, cli, tmp_path):
    repository, directory, payload = service_payload(run)
    _, spec, _ = local_spec(tmp_path, cli, payload)
    assert control.make_payload(spec, payload["endpoint"]) == payload
    assert validate_payload(payload, repository)["run_kind"] == "serving"
    executable = repository / ".toolalign-local/cuda-env/bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text(f"#!{sys.executable}\n" + """
import json,pathlib,sys
run = json.loads(pathlib.Path(sys.argv[-1]).read_text())
output = pathlib.Path(run['output_dir'])
output.mkdir()
(output / 'summary.json').write_text('{"execution_kind":"ORIGINAL_CPU_CONTROL_FIXTURE"}')
""")
    executable.chmod(0o700)
    atomic_json(directory / "launch.json", {"submitted_at_utc": "CPU_FIXTURE"})
    assert remote.worker(repository, payload) == 0
    assert read_json(directory / "exit.json")["argv"][-4:] == [
        "toolalign.service", "serve", "--run-config", str(directory / "run.json")]
    receipt = remote.export(repository, payload)
    target = tmp_path / "recovered"
    from pathlib import Path

    control.extract_verified(Path(receipt["archive_path"]), target, receipt, payload)
    assert (target / "output/summary.json").read_bytes() == (directory / "output/summary.json").read_bytes()
    remote.acknowledge_recovery(repository, payload, receipt)
    assert remote.stop_ready(repository, payload)["stop_ready"]


@pytest.mark.parametrize("patch", [
    {"run_kind": "shell"}, {"max_generations": 13}, {"max_generations": True},
    {"max_wall_seconds": 901}, {"max_wall_seconds": 5}, {"max_output_bytes": 256 * 1024**2 + 1},
    {"max_optimizer_steps": 1}, {"persistent_dir": "/tmp"}, {"listen_host": "0.0.0.0"},
    {"listen_port": True}, {"listen_port": 65536}, {"cache_enabled": 1},
])
def test_controller_rejects_service_scope_and_budget_expansion(run, patch):
    repository, _, payload = service_payload(run)
    raw = json_bytes(json.loads(payload["run_config_text"]) | patch)
    with pytest.raises(ValueError):
        validate_payload(payload | {"run_config_text": raw.decode(),
                                    "run_config_sha256": hashlib.sha256(raw).hexdigest()}, repository)


def test_controller_rejects_allocation_beyond_g6_ceiling(run):
    repository, _, payload = service_payload(run)
    with pytest.raises(ValueError, match="G6 time ceiling"):
        validate_payload(payload | {"max_allocation_seconds": 7201}, repository)
