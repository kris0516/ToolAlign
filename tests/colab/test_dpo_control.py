"""Original CPU-only control fixtures for the separate native DPO environment."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
import test_control
from support import atomic_json, digest, json_bytes, read_json, validate_payload
from test_control import control, local_spec, remote

run = test_control.run
cli = test_control.cli


def dpo_payload(run):
    repository, directory, payload = run
    lock = repository / "requirements/dpo-linux-py312.lock.txt"
    lock.write_text("trl==0.26.2\n")
    config = json.loads(payload["run_config_text"])
    config.update(schema="toolalign.cuda-dpo-run.v1", run_kind="dpo", pair_count=10,
                  total_optimizer_steps=2, stop_after_optimizer_step=1, max_wall_seconds=5,
                  dependency_lock=str(lock), dependency_lock_sha256=digest(lock))
    del config["max_optimizer_steps"], config["persistent_dir"]
    data = json_bytes(config)
    payload = payload | {"run_config_text": data.decode(), "run_config_sha256": hashlib.sha256(data).hexdigest(),
                         "dependency_lock_sha256": digest(lock)}
    atomic_json(directory / "control.json", payload)
    (directory / "run.json").write_bytes(data)
    with remote.registry(repository, payload) as state:
        state["runs"][payload["run_id"]]["run_config_sha256"] = payload["run_config_sha256"]
    return repository, directory, payload, config


def test_dpo_control_and_setup_select_only_the_separate_environment(run, cli, tmp_path):
    repository, _, payload, config = dpo_payload(run)
    _, spec, _ = local_spec(tmp_path, cli, payload)
    assert control.make_payload(spec, payload["endpoint"]) == payload
    assert validate_payload(payload, repository) == config
    lock, environment, ready = remote.environment_paths(repository, config)
    assert lock == repository / "requirements/dpo-linux-py312.lock.txt"
    assert environment == repository / ".toolalign-local/dpo-env"
    assert ready == repository / ".toolalign-local/colab/dpo-environment.json"
    commands = remote.setup_commands(repository, sys.executable, config)
    assert commands[0][-1] == str(environment)
    assert commands[1][0] == str(environment / "bin/python")
    assert "--isolated" in commands[1] and "--require-hashes" in commands[1]
    assert commands[1][-1] == str(lock)
    assert "https://pypi.org/simple" in commands[1] and remote.CUDA_INDEX in commands[1]
    assert remote.environment_paths(repository)[0] == repository / remote.LOCK_FILE
    generation = {"schema": "toolalign.cuda-generation-run.v1", "authorized_by": "S1", "run_kind": "generation"}
    assert remote.environment_paths(repository, generation) == remote.environment_paths(repository)
    assert remote.setup_commands(repository, sys.executable, generation) == remote.setup_commands(repository, sys.executable)


@pytest.mark.parametrize("change", [
    {"run_kind": "arbitrary-shell"}, {"pair_count": 129}, {"total_optimizer_steps": 1},
    {"stop_after_optimizer_step": 3}, {"max_optimizer_steps": 1},
    {"max_wall_seconds": 21601}, {"max_output_bytes": 1024**3 + 1},
    {"dependency_lock": "/content/toolalign/requirements/cuda-linux-py312.lock.txt"},
])
def test_dpo_control_rejects_mixed_protocol_or_budget(run, change):
    repository, _, payload, config = dpo_payload(run)
    data = json_bytes(config | change)
    changed = payload | {"run_config_text": data.decode(), "run_config_sha256": hashlib.sha256(data).hexdigest()}
    with pytest.raises(ValueError):
        validate_payload(changed, repository)


def test_pip_parses_dpo_lock_with_only_explicit_indexes(monkeypatch):
    pytest.importorskip("pip")
    from pip._internal.commands import create_command
    from pip._internal.req.req_file import parse_requirements

    monkeypatch.setenv("PIP_INDEX_URL", "https://invalid.example/simple")
    monkeypatch.setenv("PIP_EXTRA_INDEX_URL", "https://invalid.example/extra")
    root = Path(__file__).resolve().parents[2]
    run = {"schema": "toolalign.cuda-dpo-run.v1", "authorized_by": "S1", "run_kind": "dpo"}
    argv = remote.setup_commands(root, sys.executable, run)[1]
    command = create_command("install", isolated=True)
    options, _ = command.parse_args(argv[argv.index("install") + 1:])
    with command._build_session(options) as session:
        finder = command._build_package_finder(options, session)
        requirements = list(parse_requirements(str(root / "requirements/dpo-linux-py312.lock.txt"),
                                               session=session, finder=finder, options=options))
        assert finder.index_urls == ["https://pypi.org/simple", remote.CUDA_INDEX]
        assert len(requirements) == 69
        assert any(item.requirement.strip() == "trl==0.26.2" for item in requirements)


def test_partial_dpo_environment_does_not_touch_existing_sft(run, monkeypatch):
    repository, directory, payload, config = dpo_payload(run)
    shutil.rmtree(directory)
    with remote.registry(repository, payload) as state:
        state["runs"].clear()
    old_env = repository / ".toolalign-local/cuda-env"
    old_env.mkdir(parents=True)
    marker = old_env / "unchanged.txt"
    marker.write_text("existing SFT environment")
    _, new_env, _ = remote.environment_paths(repository, config)
    new_env.mkdir()
    monkeypatch.setattr(remote.platform, "system", lambda: "Linux")
    monkeypatch.setattr(remote.platform, "machine", lambda: "x86_64")
    with pytest.raises(ValueError, match="partial/unowned"):
        remote.setup(repository, payload)
    assert marker.read_text() == "existing SFT environment"
    assert not (repository / ".toolalign-local/colab/environment-install.json").exists()
    assert read_json(directory / "setup-exit.json")["exit_code"] == 1


def test_dpo_worker_uses_selected_interpreter_and_recoverable_original_transport(run, tmp_path):
    repository, directory, payload, config = dpo_payload(run)
    _, environment, _ = remote.environment_paths(repository, config)
    executable = environment / "bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text(f"#!{sys.executable}\n" + '''
import json, os, pathlib, sys
run = json.loads(pathlib.Path(sys.argv[-1]).read_text())
assert os.environ['HF_DATASETS_OFFLINE'] == '1'
output = pathlib.Path(run['output_dir'])
output.mkdir()
(output / 'fixture.json').write_text('{"synthetic":true,"real_DPO":"NOT_RUN"}')
print('synthetic DPO control fixture', flush=True)
''')
    executable.chmod(0o700)
    atomic_json(directory / "launch.json", {"submitted_at_utc": "SYNTHETIC"})
    assert remote.worker(repository, payload) == 0
    ended = read_json(directory / "exit.json")
    assert ended["argv"][0] == str(executable)
    assert ended["argv"][-4:] == ["toolalign.training.cuda_dpo", "train", "--run-config", str(directory / "run.json")]
    with pytest.raises(ProcessLookupError):
        os.kill(read_json(directory / "process.json")["pid"], 0)
    receipt = remote.export(repository, payload)
    recovered = tmp_path / "recovered-dpo"
    control.extract_verified(Path(receipt["archive_path"]), recovered, receipt, payload)
    assert (recovered / "output/fixture.json").read_bytes() == (directory / "output/fixture.json").read_bytes()
    remote.acknowledge_recovery(repository, payload, receipt)
    assert remote.stop_ready(repository, payload)["stop_ready"] is True
