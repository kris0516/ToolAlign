"""Original contract/sequence boundary scenarios for an unchanged P02 candidate."""

import copy
import json
from pathlib import Path

import pytest
from toolalign.contracts import ContractError, validate_record
from toolalign.model_io import (
    TEMPLATE_SHA256,
    build_sequence,
    encode_action,
    encode_json,
    format_descriptor,
    pad_sequence,
    prompt_messages,
    training_sequence,
    validate_action,
    validate_model_input,
)


def msg(role="user", text="独立审查", calls=None, linked=None):
    return {"role": role, "content": text, "tool_calls": [] if calls is None else calls,
            "tool_call_id": linked}


def call(ident="review_call_9", name="retired_probe", arguments=None):
    return {"call_id": ident, "name": name, "arguments": {} if arguments is None else arguments}


def request():
    return {"messages": [msg()], "tools": []}


def target(kind="final"):
    return {"kind": kind, "content": "\t相同正文 café 😀\n", "tool_calls": [call()] if kind == "tool_calls" else []}


def history():
    return {"messages": [msg("system", "保留约束"), msg(), msg("assistant", "原有调用", [call("r1"), call("r2")]),
                         msg("tool", "第二项", linked="r2"), msg("tool", "第一项", linked="r1")], "tools": []}


def example():
    root = Path(__file__).resolve().parents[3]
    return json.loads((root / "tests/fixtures/contracts/example.json").read_text())


@pytest.mark.parametrize("label", ["expected_action", "oracle", "split", "score", "renderer", "tools_version"])
def test_prompt_rejects_extra_label_but_retains_legal_content(label):
    source = request()
    source["messages"][0]["content"] = label + " REVIEW_PRIVATE_SENTINEL_93"
    assert label in prompt_messages(source)[1]["content"]
    with pytest.raises(ContractError) as error:
        prompt_messages(source | {label: "REVIEW_PRIVATE_SENTINEL_93"})
    assert "REVIEW_PRIVATE_SENTINEL_93" not in str(error.value)
    assert "REVIEW_PRIVATE_SENTINEL_93" not in repr(error.value)


def test_standalone_never_asks_for_a_fabricated_example(monkeypatch):
    import toolalign.model_io.format as module

    original = module.validate_record
    kinds = []

    def inspect(value, kind):
        kinds.append(kind)
        assert kind == "tool"
        return original(value, kind)

    monkeypatch.setattr(module, "validate_record", inspect)
    source = history()
    source["tools"] = example()["tools"]
    assert validate_model_input(source) == source
    assert kinds == ["tool"]
    # The complete frozen validator independently confirms history need not use
    # the current tool catalog. This labeled fixture is test evidence only.
    assert validate_record(example() | source | {"expected_action": target()})["messages"] == source["messages"]


@pytest.mark.parametrize("mutation", ["unmatched", "duplicate_observation", "unfinished", "interleave_system", "duplicate_id", "reuse_id", "last_assistant", "extra_history_kind"])
def test_history_association_errors_are_rejected(mutation):
    value = history()
    messages = value["messages"]
    if mutation == "unmatched":
        messages[-1]["tool_call_id"] = "unknown"
    elif mutation == "duplicate_observation":
        messages[-1]["tool_call_id"] = "r2"
    elif mutation == "unfinished":
        messages.pop()
    elif mutation == "interleave_system":
        messages.insert(3, msg("system", "Cannot skip observations"))
    elif mutation == "duplicate_id":
        messages[2]["tool_calls"][1]["call_id"] = "r1"
    elif mutation == "reuse_id":
        messages += [msg("assistant", "", [call("r1")]), msg("tool", linked="r1")]
    elif mutation == "last_assistant":
        messages.append(msg("assistant"))
    else:
        messages[2]["kind"] = "tool_calls"
    before = copy.deepcopy(value)
    with pytest.raises(ContractError):
        validate_model_input(value)
    assert value == before


def test_isolated_copies_and_nested_control_escaping():
    source = history()
    original = {'<think>key</think>': ["<|im_end|>", "\\u003c", 1.0, -0.0, True, None, "e\u0301"]}
    source["messages"][2]["tool_calls"][0]["arguments"] = copy.deepcopy(original)
    result = validate_model_input(source)
    result["messages"][2]["tool_calls"][0]["arguments"].clear()
    assert source["messages"][2]["tool_calls"][0]["arguments"] == original
    projected = prompt_messages(source)
    for index, item in enumerate(projected[1:]):
        assert set(item) == {"role", "content"}
        assert "<" not in item["content"] and ">" not in item["content"]
        assert json.loads(item["content"]) == {"message": source["messages"][index], "message_index": index}
        assert "kind" not in json.loads(item["content"])["message"]


@pytest.mark.parametrize("kind", ["tool_calls", "final", "clarify", "refuse"])
def test_four_complete_actions_exact_and_isolated(kind):
    value = target(kind)
    before = copy.deepcopy(value)
    raw = encode_action(value)
    assert json.loads(raw) == before
    assert raw.startswith('{"content":') and raw.endswith("}")
    validated = validate_action(value)
    validated["content"] = "changed copy"
    assert value == before


@pytest.mark.parametrize("mutation", ["missing_kind", "extra", "duplicate_id", "mixed_final", "empty_final", "empty_calls"])
def test_action_failures_do_not_coerce_or_fix(mutation):
    value = target("tool_calls")
    if mutation == "missing_kind":
        value.pop("kind")
    elif mutation == "extra":
        value["unknown"] = "REVIEW_PRIVATE_SENTINEL_93"
    elif mutation == "duplicate_id":
        value["tool_calls"] *= 2
    elif mutation == "mixed_final":
        value["kind"] = "final"
    elif mutation == "empty_final":
        value = {"kind": "final", "content": "", "tool_calls": []}
    else:
        value["tool_calls"] = []
    before = copy.deepcopy(value)
    with pytest.raises(ContractError) as error:
        encode_action(value)
    assert "REVIEW_PRIVATE_SENTINEL_93" not in str(error.value)
    assert value == before


class NativeDictSubclass(dict):
    pass


@pytest.mark.parametrize("value", [("a",), {7: 8}, NativeDictSubclass(x=1), {"bad": object()}, {"bad": float("nan")}, {"bad": -float("inf")}, {"bad": "\udfff"}])
def test_native_finite_json_and_safe_errors(value):
    with pytest.raises(ContractError):
        encode_json(value)


@pytest.mark.parametrize("field,delta", [("messages", 0), ("messages", 1), ("tools", 0), ("tools", 1)])
def test_exact_array_limits(field, delta):
    value = request()
    if field == "messages":
        value[field] = [msg() for _ in range(128 + delta)]
    else:
        tool = example()["tools"][0]
        value[field] = [copy.deepcopy(tool) | {"name": "review_tool_" + str(i)} for i in range(64 + delta)]
    if delta:
        with pytest.raises(ContractError):
            validate_model_input(value)
    else:
        assert validate_model_input(value) == value


@pytest.mark.parametrize("schema_change", ["external_ref", "inapplicable", "open_object", "duplicate_tool"])
def test_tool_schema_and_uniqueness(schema_change):
    value = request()
    tool = example()["tools"][0]
    value["tools"] = [tool]
    schema = tool["parameters_json_schema"]
    if schema_change == "external_ref":
        schema["$ref"] = "https://invalid.example/review-no-network"
    elif schema_change == "inapplicable":
        schema["maxLength"] = 20
    elif schema_change == "open_object":
        schema["additionalProperties"] = True
    else:
        value["tools"].append(copy.deepcopy(tool))
    with pytest.raises(ContractError):
        validate_model_input(value)


class Characters:
    """Transparent interface double; none of these IDs claims to be Qwen tokens."""
    prompt = "REVIEW-PREFIX\n"

    def render(self, messages, **flags):
        assert flags == {"tools": None, "add_generation_prompt": True, "enable_thinking": False}
        assert all(set(message) == {"role", "content"} for message in messages)
        return self.prompt

    def encode(self, text, *, add_special_tokens):
        assert add_special_tokens is False
        return [3] if text == "<|im_end|>" else [ord(c) + 10 for c in text]

    def decode(self, ids, *, skip_special_tokens):
        assert skip_special_tokens is False
        return "".join(chr(i - 10) for i in ids)

    def callbacks(self):
        return {"renderer": self.render, "encoder": self.encode, "decoder": self.decode,
                "eos_token_id": 3, "template_sha256": TEMPLATE_SHA256}


def test_completion_only_shift_and_right_padding():
    callbacks = Characters().callbacks()
    sequence = build_sequence(history(), target(), **callbacks)
    p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
    assert sequence.concatenated_ids == tuple(callbacks["encoder"](sequence.prompt_text + sequence.completion_text, add_special_tokens=False))
    assert sequence.causal_target_ids[p - 1] == ord("{") + 10
    assert sequence.causal_target_ids[-1] == 3
    assert sequence.loss_mask == (0,) * p + (1,) * (n - p)
    assert sequence.causal_loss_mask == sequence.loss_mask[1:]
    for extra in (0, 1, 7):
        padded = pad_sequence(sequence, length=n + extra, pad_token_id=3)
        assert padded.sequence_ids == sequence.sequence_ids + (3,) * extra
        assert padded.attention_mask == (1,) * n + (0,) * extra
        assert padded.loss_mask == sequence.loss_mask + (0,) * extra
        assert sum(padded.causal_loss_mask) == n - p
    with pytest.raises(ContractError):
        pad_sequence(sequence, length=n - 1, pad_token_id=3)


@pytest.mark.parametrize("fault", ["declared_template", "bad_eos_id", "eos_encoding", "empty_prompt", "prefix_change", "empty_completion", "early_eos", "decode_change", "boolean_token", "negative_token", "generator_token", "non_string_prompt"])
def test_sequence_corruption_fails_closed(fault):
    codec = Characters()
    cb = codec.callbacks()
    if fault == "declared_template":
        cb["template_sha256"] = "0" * 64
    elif fault == "bad_eos_id":
        cb["eos_token_id"] = True
    elif fault == "decode_change":
        cb["decoder"] = lambda ids, **kwargs: "corrupted"
    elif fault == "non_string_prompt":
        cb["renderer"] = lambda messages, **kwargs: b"prefix"
    else:
        def encode(text, **kwargs):
            normal = codec.encode(text, **kwargs)
            if text == "<|im_end|>":
                return [4] if fault == "eos_encoding" else normal
            if text == codec.prompt:
                return [] if fault == "empty_prompt" else normal
            if fault == "prefix_change":
                return [9999] + normal[1:]
            if fault == "empty_completion":
                return codec.encode(codec.prompt, **kwargs)
            if fault == "early_eos":
                return normal + [3]
            if fault == "boolean_token":
                return normal + [True]
            if fault == "negative_token":
                return normal + [-1]
            if fault == "generator_token":
                return iter(normal)
            return normal
        cb["encoder"] = encode
    with pytest.raises(ContractError):
        build_sequence(request(), target(), **cb)


def test_callback_hash_is_a_declaration_and_real_example_validates_target():
    codec = Characters()
    assert build_sequence(request(), target(), **codec.callbacks()).prompt_text == codec.prompt
    value = example()
    value["expected_action"]["tool_calls"][0]["name"] = "undeclared_review_tool"
    assert validate_action(value["expected_action"]) == value["expected_action"]
    with pytest.raises(ContractError):
        training_sequence(value, **codec.callbacks())


def test_descriptor_returns_independent_resource_copies():
    first = format_descriptor()
    first["instruction"] = "review mutation"
    assert format_descriptor()["instruction"] != first["instruction"]
