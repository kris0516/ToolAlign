"""Original CPU review probes; failing assertions document candidate defects.

Run explicitly: uv run --locked pytest -q reports/review/P00/test_independent.py
All records, repositories and markers are synthetic. No model or network is used.
"""

import copy
import json
import shutil
import socket
import subprocess
import sys
from dataclasses import fields
from pathlib import Path
from typing import get_type_hints

import pytest

from toolalign.cli import main
from toolalign.contracts import (
    ContractError,
    canonical_hash,
    model_input_from_example,
    schema_for,
    validate_record,
)
from toolalign.contracts import interfaces as api
from toolalign.runtime import GPULease, inspect_gpu_lock, lock_path

ROOT = Path(__file__).resolve().parents[3]
KINDS = ("example", "tool", "preference", "run", "trace")


def record(kind):
    return json.loads((ROOT / "tests/fixtures/contracts" / f"{kind}.json").read_text())


@pytest.mark.parametrize("kind", KINDS)
def test_all_required_wire_fields_and_nested_identity_are_enforced(kind):
    original = record(kind)
    for key in original:
        changed = copy.deepcopy(original)
        del changed[key]
        with pytest.raises(ContractError):
            validate_record(changed)
    for change in ({"extra": True}, {"schema_version": f"toolalign.{kind}.unknown"}):
        with pytest.raises(ContractError):
            validate_record({**original, **change})
    identity_key = {"run": "model", "trace": "model", "preference": "generation_model"}
    if kind in identity_key:
        for key in original[identity_key[kind]]:
            changed = copy.deepcopy(original)
            del changed[identity_key[kind]][key]
            with pytest.raises(ContractError):
                validate_record(changed)


def test_python_interface_shapes_match_wire_and_keep_oracle_separate():
    definitions = schema_for("example")["$defs"]
    for interface, name in (
        (api.ToolCall, "call"),
        (api.Message, "message"),
        (api.ToolSpec, "tool"),
        (api.Action, "action"),
    ):
        assert set(get_type_hints(interface)) == set(definitions[name]["required"])
    for interface, name in ((api.ToolResult, "tool_result"), (api.TaskScore, "task_score")):
        assert {field.name for field in fields(interface)} == set(definitions[name]["required"])
    assert set(get_type_hints(api.ModelInput)) == {"messages", "tools"}
    assert get_type_hints(api.ModelBackend.generate)["request"] is api.ModelInput
    assert get_type_hints(api.TaskOracle.score)["task"] is api.OracleTask
    for interface, method in (
        (api.ModelBackend, "generate"),
        (api.ToolRegistry, "validate"),
        (api.ToolExecutor, "execute"),
        (api.TaskOracle, "score"),
        (api.TrainingBackend, "train"),
        (api.ArtifactStore, "resolve"),
    ):
        assert callable(getattr(interface, method))
    value = record("example")
    projected = model_input_from_example(value)
    value["expected_action"]["content"] = "synthetic label marker"
    value["tools"][0]["description"] = "changed after projection"
    assert "synthetic label marker" not in json.dumps(projected)
    assert projected["tools"][0]["description"] != value["tools"][0]["description"]


@pytest.mark.parametrize("split", ["validation", "test", "ood_test"])
def test_no_evaluation_split_preferences(split):
    with pytest.raises(ContractError):
        validate_record({**record("preference"), "split": split})


@pytest.mark.parametrize("side", ["chosen_validation", "rejected_validation"])
@pytest.mark.parametrize("outcome", ["unknown", "tie", "not_scored"])
def test_ambiguous_preference_labels_are_rejected(side, outcome):
    value = record("preference")
    value[side]["outcome"] = outcome
    with pytest.raises(ContractError):
        validate_record(value)


@pytest.mark.parametrize("field", ["messages", "tools"])
def test_shared_prompt_hash_covers_both_inputs(field):
    value = record("preference")
    value[field] = (
        []
        if field == "tools"
        else [{"role": "user", "content": "changed", "tool_calls": [], "tool_call_id": None}]
    )
    with pytest.raises(ContractError):
        validate_record(value)
    value["prompt_hash"] = canonical_hash({key: value[key] for key in ("messages", "tools")})
    validate_record(value)


@pytest.fixture
def no_network(monkeypatch):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Network access attempted by schema validation")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    yield
    assert not attempts


@pytest.mark.parametrize(
    "fragment",
    [
        {"$ref": "https://example.invalid/schema"},
        {"$id": "https://example.invalid/schema", "type": "string", "maxLength": 8},
        {"type": "string", "maxLength": 8, "pattern": "(a+)+$"},
        {"type": "string", "maxLength": 8, "allOf": [{"type": "string"}]},
        {"type": "string", "maxLength": 8, "unknown_keyword": True},
        {"type": "array", "maxItems": 1001, "items": {"type": "integer"}},
        {"type": "string", "maxLength": 16385},
        {"type": "object", "properties": {}, "additionalProperties": True},
    ],
)
def test_active_dangerous_schema_is_rejected_offline(fragment, no_network):
    value = record("tool")
    value["parameters_json_schema"]["properties"]["build_id"] = fragment
    with pytest.raises(ContractError):
        validate_record(value)


@pytest.mark.parametrize("placement", ["object_items_ref", "string_properties_ref", "items_regex"])
def test_forbidden_schema_cannot_hide_in_type_inapplicable_keywords(placement, no_network):
    """R1-01: the advertised portable subset rejects refs/regex in every schema location."""
    value = record("tool")
    parameters = value["parameters_json_schema"]
    remote = {"$ref": "https://example.invalid/schema"}
    if placement == "object_items_ref":
        parameters["items"] = remote
    elif placement == "string_properties_ref":
        parameters["properties"]["build_id"]["properties"] = {"nested": remote}
    else:
        parameters["items"] = {"type": "string", "pattern": "(a+)+$"}
    with pytest.raises(ContractError):
        validate_record(value)


@pytest.mark.parametrize(
    "event", ["finalized", "rejected", "budget_exhausted", "timed_out", "cancelled"]
)
def test_each_terminal_trace_requires_outcome(event):
    value = {**record("trace"), "event": event, "task_outcome": None}
    with pytest.raises(ContractError):
        validate_record(value)
    for outcome in ("success", "failure", "unknown", "not_scored"):
        value["task_outcome"] = {**record("trace")["task_outcome"], "outcome": outcome}
        validate_record(value)


@pytest.mark.parametrize("status", ["running", "succeeded", "failed", "cancelled"])
def test_run_terminal_fields_consistent(status):
    value = {**record("run"), "status": status}
    if status == "running":
        value.update(ended_at=None, exit_code=None)
    elif status == "failed":
        value["exit_code"] = 1
    validate_record(value)
    for key in ("ended_at", "exit_code"):
        changed = copy.deepcopy(value)
        changed[key] = record("run")[key] if status == "running" else None
        with pytest.raises(ContractError):
            validate_record(changed)


@pytest.mark.parametrize(
    "kind,path",
    [
        ("run", ("git_commit",)),
        ("run", ("model", "model_hash")),
        ("tool", ("name",)),
        ("trace", ("trace_id",)),
    ],
)
def test_identity_fields_reject_terminal_newline(kind, path):
    """R1-04: an identity must match the complete string, including its last character."""
    value = record(kind)
    node = value
    for part in path[:-1]:
        node = node[part]
    node[path[-1]] += "\n"
    with pytest.raises(ContractError):
        validate_record(value)


def test_cli_error_does_not_echo_data_controlled_keys(tmp_path, capsys):
    """R1-03: free-form object keys are payload too, not safe diagnostic field names."""
    value = record("run")
    marker = "synthetic_private_marker"
    value["dependency_versions"] = {marker: 123}
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(value))
    assert main(["validate", str(path)]) == 2
    assert marker not in capsys.readouterr().err


def test_target_call_ids_do_not_collide_with_input_history():
    """R1-05: an accepted target should remain valid when it becomes history."""
    value = record("example")
    call = copy.deepcopy(value["expected_action"]["tool_calls"][0])
    value["messages"] += [
        {"role": "assistant", "content": "", "tool_calls": [call], "tool_call_id": None},
        {
            "role": "tool",
            "content": "synthetic observation",
            "tool_calls": [],
            "tool_call_id": call["call_id"],
        },
    ]
    with pytest.raises(ContractError):
        validate_record(value)


def test_public_scan_checks_staged_blob_even_when_working_copy_is_clean(tmp_path):
    """R1-02: only a fake token is staged in an isolated, uncommitted temporary repo."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    candidate = tmp_path / "candidate.txt"
    marker = "sk-" + "r" * 40
    candidate.write_text(marker)
    subprocess.run(["git", "-C", str(tmp_path), "add", "candidate.txt"], check=True)
    control = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_public_content.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert control.returncode == 1
    assert marker not in control.stdout + control.stderr
    candidate.write_text("sanitized working copy\n")
    staged = subprocess.check_output(["git", "-C", str(tmp_path), "show", ":candidate.txt"])
    assert marker.encode() in staged
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_public_content.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert marker not in result.stdout + result.stderr
    assert result.returncode == 1


def test_freeze_detects_independent_byte_change_in_each_declared_file(tmp_path):
    manifest = json.loads((ROOT / "contracts.v1.lock.json").read_text())
    assert set(manifest["files"]) == {
        "src/toolalign/contracts/v1.json",
        "src/toolalign/contracts/validation.py",
        "src/toolalign/contracts/interfaces.py",
        "configs/protocol.v1.json",
    }
    for name in ("scripts/check_contract_freeze.py", "contracts.v1.lock.json", *manifest["files"]):
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    command = [sys.executable, str(tmp_path / "scripts/check_contract_freeze.py")]
    assert subprocess.run(command, capture_output=True, timeout=5).returncode == 0
    for name in manifest["files"]:
        target = tmp_path / name
        original = target.read_bytes()
        target.write_bytes(original + b"\n")
        assert subprocess.run(command, capture_output=True, timeout=5).returncode == 1
        target.write_bytes(original)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def lease(repo):
    return GPULease(
        repository=repo,
        task_id="synthetic-review",
        worker_alias="review-fixture",
        run_id="synthetic-run",
        expected_job="CPU probe",
        memory_strategy="no model",
    )


def test_independent_worktree_timeout_and_entry_exception_release(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--allow-empty",
        "-m",
        "synthetic fixture",
    )
    other = tmp_path / "other"
    git(repo, "worktree", "add", "--detach", str(other), "HEAD")
    assert lock_path(repo) == lock_path(other)
    program = (
        "from toolalign.runtime import GPULease, LockBusy\n"
        "import sys\n"
        "try:\n"
        " with GPULease(repository=sys.argv[1], task_id='synthetic-review', "
        "worker_alias='fixture', run_id='synthetic-child', expected_job='CPU', "
        "memory_strategy='no model', timeout_seconds=0.1):\n"
        "  print('ENTERED')\n"
        "except LockBusy:\n"
        " sys.exit(17)\n"
    )
    with lease(repo):
        inode = lock_path(repo).stat().st_ino
        result = subprocess.run(
            [sys.executable, "-c", program, str(other)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 17 and "ENTERED" not in result.stdout
    assert lock_path(repo).stat().st_ino == inode
    broken = lease(other)
    broken.metadata["expected_job"] = object()
    with pytest.raises(TypeError):
        with broken:
            pytest.fail("Failed metadata serialization must prevent entering the job")
    with lease(other):
        assert inspect_gpu_lock(repo)["held"] is True
    assert inspect_gpu_lock(repo)["held"] is False
