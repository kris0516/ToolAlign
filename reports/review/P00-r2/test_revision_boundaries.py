"""Independent CPU probes for P00 r2; all records and Git repositories are synthetic."""

import copy
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from toolalign.cli import main
from toolalign.contracts import (
    ContractError,
    schema_for,
    validate_record,
    validate_tool_arguments,
)

ROOT = Path(__file__).resolve().parents[3]
SCANNER = ROOT / "scripts/check_public_content.py"
LIMIT = 1_048_576


def record(kind):
    return json.loads((ROOT / "tests/fixtures/contracts" / f"{kind}.json").read_text())


def closed(properties):
    return {"type": "object", "properties": properties, "additionalProperties": False}


@pytest.fixture
def offline(monkeypatch):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Unexpected network operation")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    yield
    assert not attempts


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize(
    "node,irrelevant",
    [
        (closed({}), "items"),
        ({"type": "array", "maxItems": 2, "items": {"type": "integer"}}, "properties"),
        ({"type": "string", "maxLength": 16}, "items"),
        ({"type": "integer"}, "properties"),
        ({"type": "number"}, "items"),
        ({"type": "boolean"}, "properties"),
        ({"type": "null"}, "items"),
    ],
)
def test_every_primitive_rejects_hidden_schema(node, irrelevant, nested, offline):
    tool = record("tool")
    leaf = copy.deepcopy(node)
    wrapper = {"type": "array", "maxItems": 2, "items": closed({"leaf": leaf})}
    tool["parameters_json_schema"] = closed({"payload": wrapper if nested else leaf})
    validate_record(tool)  # Positive control: the surrounding portable schema is valid.
    remote = {"$ref": "https://example.invalid/synthetic-schema"}
    leaf[irrelevant] = {"hidden": remote} if irrelevant == "properties" else remote
    with pytest.raises(ContractError):
        validate_record(tool)


def test_schema_like_enum_and_description_remain_plain_data(offline):
    tool = record("tool")
    literal = {"$ref": "https://example.invalid/plain-data"}
    tool["parameters_json_schema"] = {
        **closed({"$ref": {"type": "string", "maxLength": 64}}),
        "description": json.dumps({"items": {"pattern": "not a schema"}}),
        "enum": [literal],
    }
    validate_record(tool)
    validate_tool_arguments(tool, literal)
    with pytest.raises(ContractError):
        validate_tool_arguments(tool, {"$ref": "different data"})


def git(repo, *args, data=None):
    return subprocess.run(
        ["git", "-C", str(repo), *args], input=data, capture_output=True, check=True, timeout=10
    ).stdout


def scan(repo):
    return subprocess.run(
        [sys.executable, str(SCANNER)], cwd=repo, capture_output=True, text=True, timeout=10
    )


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "-q")
    return tmp_path


@pytest.mark.parametrize("source", ["index", "working tree", "untracked"])
@pytest.mark.parametrize(
    "payload",
    [b"x" * (LIMIT + 1), b"\xff\xfe", ("ghp_" + "q" * 40).encode()],
    ids=["oversized", "non_utf8", "synthetic_token"],
)
def test_scanner_checks_each_content_source(repository, source, payload):
    path = repository / "candidate.txt"
    path.write_bytes(payload if source == "index" else b"safe public data")
    if source != "untracked":
        git(repository, "add", "--", path.name)
    path.write_bytes(b"safe replacement" if source == "index" else payload)
    if source == "index":
        assert git(repository, "show", ":candidate.txt") == payload
    result = scan(repository)
    assert result.returncode == 1
    assert "working tree" in result.stdout if source == "untracked" else source in result.stdout
    assert "q" * 40 not in result.stdout + result.stderr


@pytest.mark.parametrize("mode", ["100644", "100755"])
def test_exact_size_and_regular_git_modes_are_accepted(repository, mode):
    path = repository / "candidate.txt"
    path.write_bytes(b"x" * LIMIT)
    git(repository, "add", "--", path.name)
    oid = git(repository, "rev-parse", ":candidate.txt").decode().strip()
    git(repository, "update-index", "--cacheinfo", f"{mode},{oid},{path.name}")
    assert scan(repository).returncode == 0


@pytest.mark.parametrize("mode", ["120000", "160000"])
def test_index_special_modes_rejected_with_regular_working_file(repository, mode):
    path = repository / "candidate.txt"
    path.write_text("safe regular file")
    oid = git(repository, "hash-object", "-w", "--stdin", data=b"synthetic-target").decode().strip()
    git(repository, "update-index", "--add", "--cacheinfo", f"{mode},{oid},{path.name}")
    result = scan(repository)
    assert result.returncode == 1
    assert "index" in result.stdout and "unsupported" in result.stdout


def test_unmerged_index_rejected_with_safe_working_file(repository):
    (repository / "candidate.txt").write_text("safe regular file")
    oid = git(repository, "hash-object", "-w", "--stdin", data=b"safe data").decode().strip()
    entries = f"100644 {oid} 1\tcandidate.txt\n100644 {oid} 2\tcandidate.txt\n"
    git(repository, "update-index", "--index-info", data=entries.encode())
    result = scan(repository)
    assert result.returncode == 1 and "unmerged" in result.stdout


def test_substituted_parent_symlink_is_not_followed(repository, tmp_path):
    directory = repository / "tracked"
    directory.mkdir()
    path = directory / "candidate.txt"
    path.write_text("safe public fixture")
    git(repository, "add", "--", "tracked/candidate.txt")
    path.unlink()
    directory.rmdir()
    # A nonexistent target proves rejection occurs before reading target content.
    directory.symlink_to(tmp_path / "absent", target_is_directory=True)
    result = scan(repository)
    assert result.returncode == 1 and "symlink" in result.stdout


def test_sensitive_filename_is_redacted(repository):
    marker = "sk-" + "q" * 40
    path = repository / (marker + "\tfixture.txt")
    path.write_text("safe text")
    git(repository, "add", "--", path.name)
    result = scan(repository)
    assert result.returncode == 1 and "redacted path" in result.stdout
    assert marker not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "location", ["dependency", "extra_field", "argument", "schema_property", "schema_keyword"]
)
def test_cli_and_contract_messages_omit_synthetic_keys(location, tmp_path, capsys):
    marker = "synthetic_payload_key_private"
    if location == "dependency":
        value = record("run")
        value["dependency_versions"] = {marker: {marker: 1}}
    elif location == "extra_field":
        value = record("trace")
        value["model"][marker] = marker
    elif location == "argument":
        value = record("example")
        value["expected_action"]["tool_calls"][0]["arguments"] = {marker: marker}
    else:
        value = record("tool")
        schema = value["parameters_json_schema"]
        if location == "schema_property":
            schema["properties"][marker] = {"type": marker}
        else:
            schema[marker] = {marker: marker}
    with pytest.raises(ContractError) as error:
        validate_record(value)
    assert marker not in str(error.value)
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(value) + "\n")
    assert main(["validate", str(path), "--jsonl"]) == 2
    output = capsys.readouterr()
    assert "INVALID:" in output.err
    assert marker not in output.out + output.err


def pattern_nodes(node, path=()):
    if isinstance(node, dict):
        if "pattern" in node:
            yield path, node
        for key, child in node.items():
            yield from pattern_nodes(child, (*path, key))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from pattern_nodes(child, (*path, index))


PATTERNS = list(pattern_nodes(schema_for("example")))


@pytest.mark.parametrize("path,node", PATTERNS, ids=["/".join(map(str, p)) for p, _ in PATTERNS])
def test_every_exported_identity_pattern_matches_whole_string(path, node):
    field = [path[i + 1] for i, item in enumerate(path[:-1]) if item == "properties"][-1]
    if field in {"started_at", "ended_at", "deadline_utc"}:
        positives = ["2026-09-06T00:00:00Z", "2026-09-06T00:00:00.125+00:00"]
        negatives = ["2026-09-06T00:00:00", "2026-09-06T00:00:00+01:00"]
    elif field == "name":
        positives, negatives = ["a", "a" * 64], ["A", "a" * 65]
    elif field == "git_commit" or field.endswith("hash") or field in {"sha256", "artifact_id"}:
        size = 40 if field == "git_commit" else 64
        positives = ["a" * size]
        negatives = ["a" * (size - 1), "a" * (size + 1), "A" * size]
    else:
        positives, negatives = ["A", "A" * 128], ["-a", "A" * 129]
    validator = Draft202012Validator(node)
    for value in positives:
        assert validator.is_valid(value)
        for suffix in ("\n", "\r", "\r\n", "\u2028", "\u2029", "\x00", " "):
            assert not validator.is_valid(value + suffix)
        assert not validator.is_valid("\n" + value)
    for value in ["", *negatives]:
        assert not validator.is_valid(value)


def append_observed_target(value):
    calls = copy.deepcopy(value["expected_action"]["tool_calls"])
    value["messages"].append(
        {"role": "assistant", "content": "", "tool_calls": calls, "tool_call_id": None}
    )
    for call in reversed(calls):
        value["messages"].append(
            {"role": "tool", "content": "synthetic observation", "tool_calls": [],
             "tool_call_id": call["call_id"]}
        )


def test_two_tool_rounds_preserve_history_target_uniqueness():
    value = record("example")
    template = copy.deepcopy(value["expected_action"]["tool_calls"][0])
    seen = []
    for turn in range(2):
        calls = [{**copy.deepcopy(template), "call_id": f"round-{turn}-{i}"} for i in range(2)]
        value["expected_action"]["tool_calls"] = calls
        validate_record(value)
        for prior in seen:
            collision = copy.deepcopy(value)
            collision["expected_action"]["tool_calls"][1]["call_id"] = prior
            with pytest.raises(ContractError):
                validate_record(collision)
        duplicate = copy.deepcopy(value)
        duplicate["expected_action"]["tool_calls"][1]["call_id"] = calls[0]["call_id"]
        with pytest.raises(ContractError):
            validate_record(duplicate)
        append_observed_target(value)
        seen.extend(call["call_id"] for call in calls)
    value["expected_action"] = {"kind": "final", "tool_calls": [], "content": "Synthetic final"}
    validate_record(value)
    for prior in seen:
        collision = copy.deepcopy(value)
        collision["expected_action"] = {
            "kind": "tool_calls", "tool_calls": [{**template, "call_id": prior}], "content": ""
        }
        with pytest.raises(ContractError):
            validate_record(collision)
