import copy
import json

import pytest
from jsonschema import Draft202012Validator

from toolalign.cli import main
from toolalign.contracts import (
    ContractError,
    canonical_hash,
    model_input_from_example,
    schema_for,
    validate_record,
    validate_tool_arguments,
)
from toolalign.contracts.validation import KINDS


@pytest.mark.parametrize("kind", KINDS)
def test_self_contained_schemas_and_positive_records(kind, record):
    Draft202012Validator.check_schema(schema_for(kind))
    value = record(kind)
    assert validate_record(value) == value
    assert validate_record(value) is not value


@pytest.mark.parametrize("kind", KINDS)
def test_versions_missing_fields_and_unknown_fields_are_rejected(kind, record):
    original = record(kind)
    for change in (
        lambda v: v.pop("schema_version"),
        lambda v: v.update(schema_version=f"toolalign.{kind}.v2"),
        lambda v: v.update(undeclared=True),
    ):
        value = copy.deepcopy(original)
        change(value)
        with pytest.raises(ContractError):
            validate_record(value)


def test_oracle_metadata_never_enters_model_projection(record):
    value = record("example")
    model_input = model_input_from_example(value)
    assert set(model_input) == {"messages", "tools"}
    assert "expected_action" not in json.dumps(model_input)
    model_input["messages"][0]["content"] = "modified"
    assert value["messages"][0]["content"] != "modified"


@pytest.mark.parametrize("split", ["validation", "test", "ood_test"])
def test_preference_only_uses_train_split(split, record):
    value = record("preference")
    value["split"] = split
    with pytest.raises(ContractError):
        validate_record(value)


def test_preference_rejects_ties_unverified_chosen_and_wrong_prompt(record):
    for update in (
        {"rejected": record("preference")["chosen"]},
        {"prompt_hash": "f" * 64},
        {
            "chosen_validation": {
                "outcome": "unknown",
                "reason": "unverified",
                "trace_hash": "0" * 64,
            }
        },
    ):
        value = record("preference")
        value.update(update)
        with pytest.raises(ContractError):
            validate_record(value)


def test_preference_shared_prompt_includes_tool_versions(record):
    value = record("preference")
    value["tools"][0]["tool_version"] = "changed"
    with pytest.raises(ContractError, match="prompt_hash"):
        validate_record(value)


def test_schema_rejects_writes_duplicate_names_and_remote_refs(record):
    tool = record("tool")
    tool["side_effect_class"] = "production_write"
    with pytest.raises(ContractError):
        validate_record(tool)
    value = record("example")
    value["tools"].append(copy.deepcopy(value["tools"][0]))
    with pytest.raises(ContractError, match="unique"):
        validate_record(value)
    tool = record("tool")
    tool["parameters_json_schema"]["properties"]["build_id"] = {
        "$ref": "https://example.invalid/never-fetch.json"
    }
    with pytest.raises(ContractError, match="Unsupported"):
        validate_record(tool)


def test_tool_arguments_are_strict_and_nonfinite_json_is_rejected(record):
    tool = record("tool")
    validate_tool_arguments(tool, {"build_id": "demo-01"})
    for arguments in (
        {},
        {"build_id": 42},
        {"build_id": "demo-01", "shell": "pwd"},
        {"build_id": "x" * 65},
        {"build_id": float("nan")},
    ):
        with pytest.raises(ContractError):
            validate_tool_arguments(tool, arguments)


def test_tool_schema_bounds_and_required_names(record):
    for schema in (
        {"type": "object", "properties": {}, "additionalProperties": True},
        {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
            "required": ["missing"],
        },
        {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "integer"}}},
            "additionalProperties": False,
        },
    ):
        tool = record("tool")
        tool["parameters_json_schema"] = schema
        with pytest.raises(ContractError):
            validate_record(tool)


def test_run_terminal_status_timestamps_and_dpo_reference(record):
    for fields in (
        {"ended_at": None},
        {"exit_code": 1},
        {"started_at": "2026-99-06T00:00:00Z"},
        {"started_at": "2026-09-07T00:00:00Z"},
        {"purpose": "dpo", "reference_model_hash": None},
        {"status": "running", "ended_at": None, "exit_code": 0},
    ):
        value = record("run")
        value.update(fields)
        with pytest.raises(ContractError):
            validate_record(value)


def test_trace_budget_and_outcome(record):
    value = record("trace")
    value["budget_consumed"]["output_tokens"] = -1
    with pytest.raises(ContractError):
        validate_record(value)
    value = record("trace")
    value["task_outcome"] = None
    with pytest.raises(ContractError):
        validate_record(value)


def test_hash_is_order_stable_and_sequence_sensitive():
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})
    assert canonical_hash([1, 2]) != canonical_hash([2, 1])


def test_non_json_python_values_rejected_without_coercion():
    for value in ({1: "not a JSON key"}, (1, 2), {"x": float("inf")}):
        with pytest.raises(ContractError):
            canonical_hash(value)


def test_observations_and_assistant_completion_cannot_be_misused_as_input(record):
    for message in (
        {"role": "assistant", "content": "target answer", "tool_calls": [], "tool_call_id": None},
        {
            "role": "tool",
            "content": "orphan observation",
            "tool_calls": [],
            "tool_call_id": "orphan",
        },
    ):
        value = record("example")
        value["messages"].append(message)
        with pytest.raises(ContractError):
            validate_record(value)


def test_expected_action_requires_registered_tools_and_valid_arguments(record):
    value = record("example")
    value["expected_action"]["tool_calls"][0]["name"] = "unregistered"
    with pytest.raises(ContractError):
        validate_record(value)
    value = record("example")
    value["expected_action"]["tool_calls"][0]["arguments"]["build_id"] = 42
    with pytest.raises(ContractError):
        validate_record(value)


def test_run_artifacts_cannot_escape_private_root(record):
    value = record("run")
    value["artifacts"] = [
        {
            "artifact_id": "0" * 64,
            "sha256": "0" * 64,
            "relative_path": "../other/weights",
            "size_bytes": 1,
            "media_type": "application/octet-stream",
        }
    ]
    with pytest.raises(ContractError, match="relative"):
        validate_record(value)


def test_cli_success_error_empty_jsonl_and_duplicate_keys(tmp_path, record, capsys):
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record("tool")))
    assert main(["validate", str(path)]) == 0
    assert "VALID: 1 record(s)" in capsys.readouterr().out
    path.write_text('{"schema_version":"toolalign.tool.v1","schema_version":"v2"}')
    assert main(["validate", str(path)]) == 2
    path.write_text("")
    assert main(["validate", str(path), "--jsonl"]) == 2
