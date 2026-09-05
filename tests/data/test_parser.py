import copy
import json

import pytest

from toolalign.contracts import model_input_from_example, validate_record
from toolalign.data.common import DataError, loads
from toolalign.data.toolace import (
    MARKER,
    convert_tool,
    extract_tools,
    inspect_record,
    parse_calls,
    tool_findings,
)


def test_literal_parser_exact_names_and_order():
    assert parse_calls(
        '[Read Tool(from="demo", n=2, ok=true), Read Tool(from="next")]', ["Read Tool"]
    ) == [
        {"name": "Read Tool", "arguments": {"from": "demo", "n": 2, "ok": True}},
        {"name": "Read Tool", "arguments": {"from": "next"}},
    ]


@pytest.mark.parametrize(
    "text",
    [
        '[read_build(build_id=__import__("os"))]',
        '[read_build(build_id="x")] trailing',
        '[read_build(build_id="a", build_id="b")]',
        "[read_build(build_id=NaN)]",
        "[read_build(build_id=1e999)]",
        '[read_build(build_id={"a":1,"a":2})]',
        "[read_build(build_id='a')]",
        '[read_build("a")]',
        '[read_build(**{"build_id":"a"})]',
        "[read_build(build_id=x.y)]",
        '[read_build(build_id="a",)]',
        "[]",
        '[read_build(build_id="a"),]',
        "[unknown()]",
        "[read_build(build_id=[x for x in y])]",
    ],
)
def test_malicious_or_ambiguous_calls_fail(text):
    with pytest.raises(DataError):
        parse_calls(text, ["read_build"])


@pytest.mark.parametrize(
    "text", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}', "{} {}"]
)
def test_strict_json(text):
    with pytest.raises(DataError):
        loads(text)


def test_tool_schema_never_repaired(original_tool):
    raw = copy.deepcopy(original_tool)
    raw["parameters"]["type"] = "dict"
    del raw["parameters"]["additionalProperties"]
    del raw["parameters"]["properties"]["build_id"]["maxLength"]
    del raw["side_effect_class"]
    original = copy.deepcopy(raw)
    assert {
        "schema_type_unsupported",
        "schema_object_unclosed",
        "schema_string_unbounded",
        "side_effect_unknown_or_forbidden",
        "schema_contract_rejected",
    } <= tool_findings(raw)
    with pytest.raises(DataError):
        convert_tool(raw)
    assert raw == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("$ref", "https://example.invalid/schema"),
        ("pattern", ".*"),
        ("default", "demo"),
        ("oneOf", [{"type": "string"}]),
    ],
)
def test_schema_keywords_fail(original_tool, field, value):
    original_tool["parameters"]["properties"]["build_id"][field] = value
    with pytest.raises(DataError):
        convert_tool(original_tool)


def test_production_write_never_relabelled(original_tool):
    original_tool["side_effect_class"] = "production_write"
    with pytest.raises(DataError):
        convert_tool(original_tool)


def test_real_dialect_isolated_using_original_fixture(original_tool, record_factory, source):
    del original_tool["side_effect_class"]
    original_tool["parameters"]["type"] = "dict"
    info, examples = inspect_record(record_factory(original_tool), source, 1)
    assert examples == []
    assert "schema_contract_rejected" in info["decisions"][0]["reasons"]
    assert "side_effect_unknown_or_forbidden" in info["decisions"][0]["reasons"]


def test_prefixes_exclude_targets_and_keep_prior_observations(record_factory, source):
    record = record_factory(second=True)
    info, examples = inspect_record(record, source, 0)
    assert len(examples) == 2
    assert len(examples[0]["messages"]) == 2
    assert len(examples[1]["messages"]) == 4
    assert examples[1]["messages"][-1]["role"] == "tool"
    assert "build-002" not in json.dumps(examples[1]["messages"])
    for example in examples:
        validate_record(example)
        assert set(model_input_from_example(example)) == {"messages", "tools"}
    assert len({d["normalized_hash"] for d in info["decisions"]}) == 2


def test_prose_not_given_invented_semantic_label(record_factory, source):
    record = record_factory()
    record["conversations"][1]["value"] = "Please provide the build identifier."
    info, examples = inspect_record(record, source, 0)
    assert examples == []
    assert info["decisions"][0]["reasons"] == ["action_kind_unlabelled"]


def test_argument_truth_violation_rejected(record_factory, source):
    record = record_factory()
    record["conversations"][1]["value"] = "[read_build(build_id=7)]"
    info, examples = inspect_record(record, source, 0)
    assert examples == []
    assert info["decisions"][0]["reasons"] == ["example_contract_rejected"]


def test_tool_observation_ambiguity_poisoned_prefix(record_factory, source):
    record = record_factory(second=True)
    record["conversations"][2]["value"] = '[{"name":"other_tool","results":{}}]'
    info, examples = inspect_record(record, source, 0)
    assert len(examples) == 1
    assert "invalid_history_prefix" in info["decisions"][1]["reasons"]


def test_unsupported_tool_format_does_not_guess():
    with pytest.raises(DataError, match="unsupported_tool_format"):
        extract_tools({"system": "<table>no canonical JSON tool list</table>", "conversations": []})


def test_duplicate_tool_json_keys_rejected():
    with pytest.raises(DataError):
        extract_tools({"system": MARKER + '[{"name":"a","name":"b"}]', "conversations": []})


def test_bad_assistant_shape_is_counted(record_factory, source):
    record = record_factory()
    record["conversations"][1]["value"] = {"unexpected": "object"}
    info, examples = inspect_record(record, source, 0)
    assert not examples
    assert len(info["decisions"]) == 1
    assert info["decisions"][0]["reasons"] == ["assistant_turn_shape"]


def test_nonstring_tool_metadata_fail_closed(original_tool):
    original_tool["side_effect_class"] = []
    with pytest.raises(DataError):
        convert_tool(original_tool)
    with pytest.raises(DataError):
        parse_calls("[tool()]", [{"name": "tool"}])
