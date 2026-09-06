"""Standalone semantics and reversible bytes, including frozen historical freedoms."""

import copy
import hashlib
import json
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest
from model_io_cases import action, cases, message, public_example

from toolalign.contracts import (
    ContractError,
    canonical_hash,
    model_input_from_example,
    validate_record,
)
from toolalign.model_io import (
    DESCRIPTOR_SHA256,
    FORMAT_ID,
    INSTRUCTION_SHA256,
    ModelIOError,
    encode_action,
    encode_json,
    format_descriptor,
    format_identity,
    prompt_messages,
    validate_action,
    validate_model_input,
)


def request():
    return {"messages": [message("user", "Continue the original task.")], "tools": []}


def test_descriptor_is_the_authorized_installed_resource():
    resource = files("toolalign.model_io").joinpath("descriptor.v1.json").read_bytes()
    source = Path(__file__).resolve().parents[2] / "configs/model_io.action-json.v1.json"
    assert resource == source.read_bytes()
    assert hashlib.sha256(resource).hexdigest() == DESCRIPTOR_SHA256
    descriptor = format_descriptor()
    assert descriptor["format_id"] == FORMAT_ID
    assert hashlib.sha256(descriptor["instruction"].encode()).hexdigest() == INSTRUCTION_SHA256
    descriptor["template"]["enable_thinking"] = True
    assert format_descriptor()["template"]["enable_thinking"] is False
    assert format_identity()["instruction_sha256"] == INSTRUCTION_SHA256


def test_same_original_fixture_set():
    fixture_set = [{"name": name, "example": example} for name, example in cases()]
    assert canonical_hash(fixture_set) == "81347cd9f79a4e00478b07046a48d95b12f4b37f23396c2fb480e8923b9f3852"


@pytest.mark.parametrize("name,example", cases(), ids=[n for n, _ in cases()])
def test_each_original_case_preserves_all_values_and_roles(name, example):
    before = copy.deepcopy(example)
    model_input = model_input_from_example(example)
    projected = prompt_messages(model_input)
    instruction = format_descriptor()["instruction"]
    assert projected[0]["role"] == "system"
    catalog = json.loads(projected[0]["content"][len(instruction) + 1:])
    assert catalog == {"format_version": FORMAT_ID, "tools": model_input["tools"]}
    recovered = []
    for i, item in enumerate(projected[1:]):
        assert set(item) == {"role", "content"}
        assert "<" not in item["content"] and ">" not in item["content"]
        record = json.loads(item["content"])
        assert record["message_index"] == i
        assert item["role"] == record["message"]["role"]
        assert "kind" not in record["message"]
        recovered.append(record["message"])
    assert canonical_hash({"messages": recovered, "tools": catalog["tools"]}) == canonical_hash(model_input)
    assert canonical_hash(json.loads(encode_action(example["expected_action"]))) == canonical_hash(example["expected_action"])
    assert example == before


def test_missing_target_is_not_synthesized_or_required():
    value = request()
    assert validate_model_input(value) == value
    assert prompt_messages(value)


@pytest.mark.parametrize("key", ["expected_action", "oracle", "split", "schema_version", "template"])
def test_extra_model_input_fields_rejected(key):
    with pytest.raises(ContractError):
        prompt_messages(request() | {key: "FORBIDDEN_INPUT_SENTINEL"})


def test_legal_words_and_target_changes_do_not_leak_or_disappear():
    example = public_example()
    example["messages"][0]["content"] = 'Discuss "expected_action", "oracle", "split" as words.'
    first = prompt_messages(model_input_from_example(example))
    example["expected_action"] = action("final", "UNIQUE_OUTPUT_ONLY_947")
    example["split"] = "validation"
    second = prompt_messages(model_input_from_example(example))
    assert first == second
    assert "UNIQUE_OUTPUT_ONLY_947" not in str(first)
    assert all(word in first[1]["content"] for word in ("expected_action", "oracle", "split"))


@pytest.mark.parametrize("current_catalog", [False, True])
def test_history_does_not_gain_current_catalog_or_parameter_requirements(current_catalog):
    tool = public_example()["tools"][0]
    historical_call = {"call_id": "past-1", "name": tool["name"], "arguments": {"retired_field": 7}}
    value = {
        "messages": [
            message("assistant", "Original historical call.", [historical_call]),
            message("tool", "Original observation.", call_id="past-1"),
        ],
        "tools": [tool] if current_catalog else [],
    }
    # An original fully labeled case confirms the public frozen history semantics;
    # the production standalone validator never constructs an Example or target.
    original_case = public_example() | value | {"expected_action": action("final", "History read.")}
    assert validate_record(original_case)["messages"] == value["messages"]
    assert validate_model_input(value) == value


def history():
    calls = [
        {"call_id": "a", "name": "retired_a", "arguments": {}},
        {"call_id": "b", "name": "retired_b", "arguments": {}},
    ]
    return {
        "messages": [
            message("user", "Inspect both."), message("assistant", "", calls),
            message("tool", "second", call_id="b"), message("tool", "first", call_id="a"),
        ], "tools": [],
    }


def test_observations_can_arrive_in_reverse_order():
    assert validate_model_input(history()) == history()


@pytest.mark.parametrize("failure", ["missing", "duplicate", "unknown", "pending_user", "reused", "pending_final"])
def test_invalid_history_associations(failure):
    value = history()
    messages = value["messages"]
    if failure == "missing":
        messages.pop()
    elif failure == "duplicate":
        messages.append(copy.deepcopy(messages[-1]))
    elif failure == "unknown":
        messages[2]["tool_call_id"] = "unknown"
    elif failure == "pending_user":
        messages.insert(2, message("user", "Interleaving is invalid."))
    elif failure == "reused":
        messages += [message("assistant", "", [copy.deepcopy(messages[1]["tool_calls"][0])]), message("tool", "again", call_id="a")]
    else:
        messages[1]["tool_calls"].append({"call_id": "c", "name": "retired_c", "arguments": {}})
    with pytest.raises(ContractError):
        validate_model_input(value)


@pytest.mark.parametrize("role", ["system", "assistant"])
def test_input_must_end_before_an_assistant_decision(role):
    with pytest.raises(ContractError):
        validate_model_input({"messages": [message(role, "Text")], "tools": []})


def test_returned_validation_values_are_isolated():
    value = history()
    result = validate_model_input(value)
    result["messages"][1]["tool_calls"][0]["arguments"]["new"] = True
    assert "new" not in value["messages"][1]["tool_calls"][0]["arguments"]


@pytest.mark.parametrize("failure", ["empty_messages", "129_messages", "65_tools", "duplicate_tools", "extra_message_field", "tool_observation_null", "user_call_id", "tool_schema_extension"])
def test_frozen_shapes_and_tool_schema_subset(failure):
    value = request()
    if failure == "empty_messages":
        value["messages"] = []
    elif failure == "129_messages":
        value["messages"] *= 129
    elif failure == "65_tools":
        value["tools"] = [public_example()["tools"][0] | {"name": f"tool_{i}"} for i in range(65)]
    elif failure == "duplicate_tools":
        value["tools"] = public_example()["tools"] * 2
    elif failure == "extra_message_field":
        value["messages"][0]["kind"] = "final"
    elif failure == "tool_observation_null":
        value["messages"] = [message("tool", "No linked ID.")]
    elif failure == "user_call_id":
        value["messages"][0]["tool_call_id"] = "a"
    else:
        value["tools"] = public_example()["tools"]
        value["tools"][0]["parameters_json_schema"]["properties"]["build_id"]["pattern"] = "remote"
    with pytest.raises(ContractError):
        validate_model_input(value)


def test_exact_frozen_array_bound_and_empty_content_remain_legal():
    value = {"messages": [message("user", "") for _ in range(128)], "tools": []}
    assert len(validate_model_input(value)["messages"]) == 128


@pytest.mark.parametrize("kind", ["tool_calls", "final", "clarify", "refuse"])
def test_action_kind_is_always_explicit(kind):
    calls = public_example()["expected_action"]["tool_calls"] if kind == "tool_calls" else []
    value = action(kind, "Same content.", calls)
    assert json.loads(encode_action(value)) == value


@pytest.mark.parametrize("failure", ["missing_kind", "extra_key", "unknown_kind", "empty_calls", "nonempty_final_calls", "empty_final", "duplicate_call_id"])
def test_invalid_actions(failure):
    value = copy.deepcopy(public_example()["expected_action"])
    if failure == "missing_kind":
        value.pop("kind")
    elif failure == "extra_key":
        value["schema_version"] = "invented"
    elif failure == "unknown_kind":
        value["kind"] = "repair"
    elif failure == "empty_calls":
        value["tool_calls"] = []
    elif failure == "nonempty_final_calls":
        value["kind"], value["content"] = "final", "Text"
    elif failure == "empty_final":
        value = action("final", "")
    else:
        value["tool_calls"] *= 2
    with pytest.raises(ContractError):
        encode_action(value)


def test_action_validator_does_not_invent_a_catalog():
    value = action("tool_calls", "", [{"call_id": "x", "name": "unregistered", "arguments": {"x": 1}}])
    assert validate_action(value) == value


@pytest.mark.parametrize("value", [(1, 2), {1: "bad key"}, {"x": object()}, {"x": float("nan")}, {"x": float("inf")}, {"x": "\ud800"}])
def test_json_never_coerces_unsupported_values(value):
    with pytest.raises(ContractError):
        encode_json(value)


def test_json_cyclic_and_excessive_depth_rejected():
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ContractError):
        encode_json(cyclic)
    value = None
    for _ in range(66):
        value = [value]
    with pytest.raises(ContractError):
        encode_json(value)


def test_json_preserves_types_ordered_arrays_and_escape_distinctions():
    value = {'key<>":': [True, 1, 1.0, -0.0, None, "", "\n\t\u0000 中文😀", "<", "\\u003c", "<|im_end|>"]}
    text = encode_json(value)
    assert "<" not in text and ">" not in text
    assert canonical_hash(json.loads(text)) == canonical_hash(value)
    assert encode_json({"b": 2, "a": 1}) == encode_json({"a": 1, "b": 2})


def test_no_tokenizer_or_model_import_on_pure_import():
    script = """import sys
import toolalign.model_io
import toolalign.model_io.offline
blocked = {'tokenizers','transformers','torch','mlx','mlx_lm','tensorflow','flax','jax'}
assert not blocked.intersection(name.split('.')[0] for name in sys.modules)
print('PURE_IMPORT_PASS')
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "PURE_IMPORT_PASS"


def test_corrupt_descriptor_fails_without_cwd_fallback(monkeypatch):
    import toolalign.model_io.format as module

    class Corrupt:
        def joinpath(self, _):
            return self

        def read_bytes(self):
            return b"{}"

    module._descriptor.cache_clear()
    with monkeypatch.context() as patch:
        patch.setattr(module, "files", lambda _: Corrupt())
        with pytest.raises(ModelIOError, match="format_descriptor_hash_mismatch"):
            format_descriptor()
    module._descriptor.cache_clear()
    assert format_descriptor()["format_id"] == FORMAT_ID
