"""R1 original counterexamples; no corpus records or production parser oracle."""

import copy
import json

import pytest

from toolalign.contracts import canonical_hash, model_input_from_example
from toolalign.data.common import DataError
from toolalign.data.grouping import normalized_group_guard, normalized_schema_semantics
from toolalign.data.source_policy import SourcePolicy
from toolalign.data.toolace import MARKER, inspect_record, parse_calls

SOURCE = {"source": "r1-original", "source_revision": "fixture-r1", "license_id": "MIT"}


def original_tool(name="R1 Read Note"):
    return {
        "name": name,
        "description": "An original hypothetical note fixture without an execution binding.",
        "parameters": {
            "type": "dict",
            "properties": {
                "note": {"type": "string"},
                "optional": {"type": "int", "default": 2},
            },
            "required": ["note"],
        },
        "required": None,
    }


def record(tools=None):
    tools = tools or [original_tool()]
    return {
        "system": MARKER + json.dumps(tools),
        "conversations": [
            {"from": "user", "value": "Read note alpha; preserve its punctuation."},
            {"from": "assistant", "value": '[R1 Read Note(note="alpha")]'},
            {"from": "tool", "value": '[{"name":"R1 Read Note","results":{"value":"old"}}]'},
            {"from": "user", "value": "Now read a different note."},
            {"from": "assistant", "value": '[R1 Read Note(note="target-only-sentinel")]'},
        ],
    }


@pytest.mark.parametrize(
    "node",
    [
        {"type": "string", "nullable": False},
        {"type": "string", "maxItems": 2},
        {"type": "int", "required": []},
        {"type": "boolean", "minimum": 0},
        {"type": "array", "items": {"type": ["string", "null"]}},
        {"type": "dict", "properties": {}, "additionalProperties": {}},
        {"type": "string", "maxLength": True},
        {"type": "string", "maxLength": 4.0},
        {"type": "array", "items": {"type": "int"}, "maxItems": -1},
        {"type": "string", "default": "x", "not": {"enum": ["x"]}},
        {"type": "array", "items": {"type": "int"}, "default": [True]},
        {"type": "null", "default": "null"},
    ],
)
def test_unknown_or_inapplicable_schema_cannot_disappear(node):
    tool = original_tool()
    tool["parameters"]["properties"]["optional"] = node
    before = copy.deepcopy(tool)
    info, examples = inspect_record(record([tool]), SOURCE, 0, SourcePolicy())
    assert examples == [] and info["record_reasons"]
    assert tool == before


@pytest.mark.parametrize(
    "node,value,kind",
    [
        ({"type": "null"}, None, "null"),
        ({"type": "boolean"}, False, "boolean"),
        ({"type": "array", "items": {"type": "string"}}, ["a"], "array"),
        ({"type": "dict", "properties": {"q": {"type": "int"}}}, {"q": 2}, "object"),
    ],
)
def test_nested_typed_annotations_never_supply_arguments(node, value, kind):
    tool = original_tool()
    node["default"] = value
    tool["parameters"]["properties"]["optional"] = node
    policy = SourcePolicy()
    _, examples = inspect_record(record([tool]), SOURCE, 0, policy)
    assert len(examples) == 2
    annotation = policy.convert_tool(tool)["default_annotations"][0]
    assert annotation["value"] == value and annotation["value_type"] == kind
    assert annotation["value_hash"] == canonical_hash(value)
    assert annotation["inserted_into_arguments"] is False
    for example in examples:
        assert example["tools"][0]["parameters_json_schema"]["required"] == ["note"]
        assert set(example["expected_action"]["tool_calls"][0]["arguments"]) == {"note"}


@pytest.mark.parametrize("position", [1, 4])
@pytest.mark.parametrize(
    "arguments",
    ['note="ok", extra=1', 'note="ok", optional=true', 'note="ok", optional="2"', 'optional=2'],
)
def test_any_invalid_call_excludes_every_source_decision(position, arguments):
    raw = record()
    raw["conversations"][position]["value"] = "[R1 Read Note(" + arguments + ")]"
    info, examples = inspect_record(raw, SOURCE, 0, SourcePolicy())
    assert not examples and "out_of_policy_arguments" in info["record_reasons"]
    assert all(d["normalized_hash"] is None for d in info["decisions"])


@pytest.mark.parametrize("limit_kind", ["string", "array", "nested_object"])
def test_missing_project_bounds_apply_to_later_calls_without_truncation(limit_kind):
    tool = original_tool()
    node, value = {
        "string": ({"type": "string"}, "x" * 16385),
        "array": ({"type": "array", "items": {"type": "int"}}, [0] * 1001),
        "nested_object": ({"type": "dict", "properties": {}}, {"undeclared": 1}),
    }[limit_kind]
    tool["parameters"]["properties"]["optional"] = node
    raw = record([tool])
    raw["conversations"][4]["value"] = (
        '[R1 Read Note(note="beta", optional=' + json.dumps(value) + ")]"
    )
    info, examples = inspect_record(raw, SOURCE, 0, SourcePolicy())
    assert not examples and "out_of_policy_arguments" in info["record_reasons"]


def test_reversed_observations_keep_exact_call_identity_and_temporal_prefix():
    tools = [original_tool(), original_tool("R1 Second Note")]
    raw = record(tools)
    raw["conversations"][1]["value"] = (
        '[R1 Read Note(note="alpha"), R1 Second Note(note="second")]'
    )
    raw["conversations"][2]["value"] = json.dumps(
        [{"name": "R1 Second Note", "results": 22}, {"name": "R1 Read Note", "results": 11}]
    )
    info, examples = inspect_record(raw, SOURCE, 0, SourcePolicy())
    assert len(examples) == 2 and not info["record_reasons"]
    history = examples[1]["messages"]
    assert [m["content"] for m in history if m["role"] == "tool"] == ["11", "22"]
    assert [m["tool_call_id"] for m in history if m["role"] == "tool"] == ["c-1-0", "c-1-1"]
    for e in examples:
        projected = model_input_from_example(e)
        assert set(projected) == {"messages", "tools"}
        assert "target-only-sentinel" not in json.dumps(projected)
    assert all(b["executed_here"] is False for b in info["observation_bindings"])


@pytest.mark.parametrize(
    "text",
    [
        '[R1 Read Note(note="a"), Unknown(note="b")]',
        '[R1 Read Note(note={"x":{"y":1,"y":2}})]',
        '[R1 Read Note(note="a")]; import os',
        '[R1 Read Note(note=(lambda: 1)())]',
        '[R1 Read Note(note=null, note="again")]',
        '[R1 Read Note(note=' + "[" * 66 + "0" + "]" * 66 + ")]",
        '[R1 Read Note(note="' + "a" * 131072 + '")]',
    ],
)
def test_literal_grammar_refuses_code_duplicates_unknown_names_and_budgets(text):
    with pytest.raises(DataError):
        parse_calls(text, ["R1 Read Note"])


def test_literal_grammar_preserves_nested_json_and_delimiter_characters():
    value = {"quoted": 'a,b)=]\"', "values": [None, False, 0, 1.5, {"nested": "中"}]}
    text = "[R1 Read Note(note=" + json.dumps(value) + ")]"
    assert parse_calls(text, ["R1 Read Note"]) == [
        {"name": "R1 Read Note", "arguments": {"note": value}}
    ]


@pytest.mark.parametrize("location", ["head", "tail"])
def test_unknown_system_requirements_reject_instead_of_being_erased(location):
    raw = record()
    if location == "head":
        raw["system"] = "Keep a user-specific safety condition. " + raw["system"]
    else:
        raw["system"] += " Return only a conflicting format."
    info, examples = inspect_record(raw, SOURCE, 0, SourcePolicy())
    assert not examples and any(r.startswith("policy_system_") for r in info["record_reasons"])


def test_normalized_guard_ignores_annotations_order_and_implicit_empty_constraints():
    first = {
        "type": "object", "additionalProperties": False,
        "properties": {"description": {"type": "string", "maxLength": 3, "enum": ["b", "a"]}},
    }
    second = copy.deepcopy(first)
    second["required"] = []
    second["description"] = "Annotation only"
    second["properties"]["description"].update(minLength=0, enum=["a", "b"])
    key = canonical_hash(normalized_schema_semantics(first))
    assert key == canonical_hash(normalized_schema_semantics(second))
    infos = [
        {"source_record_hash": str(i), "normalized_schema_keys": [key], "record_reasons": ["x"]}
        for i in range(3)
    ]
    assignments = [
        {"group_id": "old-a", "split": "train"},
        {"group_id": "old-b", "split": "train"},
        {"group_id": "old-c", "split": "ood_test"},
    ]
    before = copy.deepcopy(assignments)
    excluded, conflicts, report = normalized_group_guard(infos, assignments)
    assert excluded == {"0", "1", "2"} and len(conflicts) == 1
    assert report["cross_split_bridge_keys"] == 1 and assignments == before


def test_duplicate_named_observations_invalidate_the_entire_source():
    raw = record()
    raw["conversations"][1]["value"] = (
        '[R1 Read Note(note="first"), R1 Read Note(note="second")]'
    )
    raw["conversations"][2]["value"] = (
        '[{"name":"R1 Read Note","results":1},{"name":"R1 Read Note","results":2}]'
    )
    info, examples = inspect_record(raw, SOURCE, 0, SourcePolicy())
    assert not examples and "policy_history_observation_unreliable" in info["record_reasons"]
