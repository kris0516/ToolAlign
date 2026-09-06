"""Original adversarial fixtures for the approved policy; no upstream records."""

import copy
import json

import pytest

from toolalign.contracts import canonical_hash, validate_record
from toolalign.data.common import DataError
from toolalign.data.grouping import normalized_group_guard, normalized_schema_semantics
from toolalign.data.source_policy import POLICY_SHA256, SourcePolicy, text_hash
from toolalign.data.toolace import MARKER, extract_tools, inspect_record


@pytest.fixture
def policy_tool():
    return {
        "name": "Read Original Build",
        "description": "Retrieve an original local build fixture.",
        "parameters": {
            "type": "dict",
            "properties": {
                "build_id": {"type": "string"},
                "limit": {"type": "int", "default": 3},
                "weight": {"type": "float"},
                "labels": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["build_id"],
        },
        "required": None,
    }


def test_conversion_preserves_values_and_reversible_lineage(policy_tool):
    untouched = copy.deepcopy(policy_tool)
    policy = SourcePolicy()
    converted = policy.convert_tool(policy_tool)
    tool = converted["tool"]
    schema = tool["parameters_json_schema"]
    assert policy_tool == untouched == converted["raw_tool"]
    assert validate_record(tool, "tool") == tool
    assert schema["type"] == "object" and schema["additionalProperties"] is False
    assert schema["required"] == ["build_id"]
    assert schema["properties"]["limit"]["type"] == "integer"
    assert schema["properties"]["weight"]["type"] == "number"
    assert schema["properties"]["labels"]["maxItems"] == 1000
    assert schema["properties"]["build_id"]["maxLength"] == 16384
    assert "default" not in schema["properties"]["limit"]
    assert "never auto-filled" in schema["properties"]["limit"]["description"]
    annotation = converted["default_annotations"][0]
    assert annotation["value"] == 3 and annotation["value_type"] == "integer"
    assert annotation["value_hash"] == canonical_hash(3)
    assert annotation["inserted_into_arguments"] is False
    assert tool["name"] == "ta_read_original_build_" + canonical_hash(policy_tool)[:12]
    assert tool["side_effect_class"] == "sandbox_only" and tool["timeout_ms"] == 1000
    assert converted["original_side_effect_class"] == "unknown"
    assert converted["execution_binding"] == "none" and converted["policy_hash"] == POLICY_SHA256
    assert converted["normalized_tool_hash"] == canonical_hash(tool)
    expected_name = tool["name"]
    converted["tool"]["name"] = "mutated"
    assert policy.convert_tool(policy_tool)["tool"]["name"] == expected_name
    assert policy.tools[canonical_hash(policy_tool)]["tool"]["name"] != "mutated"


@pytest.mark.parametrize(
    "node",
    [
        {"type": "str"},
        {"type": ["string", "null"]},
        {},
        {"type": "string", "pattern": ".*"},
        {"type": "string", "format": "email"},
        {"type": "string", "examples": ["fixture"]},
        {"type": "string", "$ref": "https://example.invalid/schema"},
        {"type": "string", "oneOf": [{"type": "string"}]},
        {"type": "array"},
        {"type": "string", "maxLength": 16385},
        {"type": "array", "maxItems": 1001, "items": {"type": "int"}},
        {"type": "dict", "properties": {}, "additionalProperties": True},
        {"type": "int", "default": "3"},
        {"type": "int", "default": True},
        {"type": "string", "maxLength": 2, "default": "long"},
        {"type": "dict", "properties": {}, "default": {"extra": 1}},
        {"type": "array", "items": {"type": "int"}, "default": ["1"]},
        {"type": "string", "default": "ok", "pattern": "ok"},
        {"type": "string", "minLength": 20, "maxLength": 10, "default": "short"},
    ],
)
def test_unknown_constraints_and_invalid_defaults_cannot_be_laundered(policy_tool, node):
    policy_tool["parameters"]["properties"]["extra"] = node
    policy = SourcePolicy()
    with pytest.raises(DataError):
        policy.convert_tool(policy_tool)
    assert canonical_hash(policy_tool) in policy.failures
    assert not policy.tools


@pytest.mark.parametrize("value", [[], ["build_id"], "build_id"])
def test_nonnull_outer_required_quarantined(policy_tool, value):
    policy_tool["required"] = value
    with pytest.raises(DataError, match="outer_required"):
        SourcePolicy().convert_tool(policy_tool)


@pytest.mark.parametrize("name,slug", [("查看", "tool"), ("A" * 100, "a" * 47), ("İ A-B", "a_b")])
def test_name_mapping_is_ascii_bounded(policy_tool, name, slug):
    policy_tool["name"] = name
    result = SourcePolicy().convert_tool(policy_tool)
    assert result["normalized_name"] == f"ta_{slug}_" + canonical_hash(policy_tool)[:12]
    assert len(result["normalized_name"]) <= 64
    assert result["raw_name"] == name


def test_hash_collision_fails_globally(policy_tool):
    policy = SourcePolicy()
    name, _ = policy.name_for(policy_tool)
    policy.names[name] = "f" * 64
    with pytest.raises(DataError, match="normalized_name_hash_collision"):
        policy.convert_tool(policy_tool)


def test_policy_bytes_and_source_identity_are_pinned(tmp_path):
    path = tmp_path / "changed.json"
    path.write_text("{}\n")
    with pytest.raises(DataError, match="source_policy_hash_not_approved"):
        SourcePolicy(path)
    with pytest.raises(DataError, match="policy_source_identity_mismatch"):
        SourcePolicy().bind_source({"repo_id": "not-approved"})


def test_targets_history_observations_renamed_and_no_default_filled(
    policy_tool, record_factory, source
):
    record = record_factory(tool=policy_tool, second=True)
    policy = SourcePolicy()
    info, examples = inspect_record(record, source, 0, policy)
    assert not info["record_reasons"] and len(examples) == 2
    name = examples[0]["tools"][0]["name"]
    for example in examples:
        call = example["expected_action"]["tool_calls"][0]
        assert call["name"] == name and set(call["arguments"]) == {"build_id"}
        assert example["tools"][0]["parameters_json_schema"]["required"] == ["build_id"]
        assert validate_record(example, "example") == example
    second_history = examples[1]["messages"]
    assert second_history[2]["tool_calls"][0]["name"] == name
    assert second_history[3]["tool_call_id"] == second_history[2]["tool_calls"][0]["call_id"]
    binding = info["observation_bindings"][0]
    assert binding["executed_here"] is False
    assert binding["evidence_kind"] == "historical_observation_only"
    assert binding["results_hash"] == canonical_hash({"status": "pass"})
    assert info["strict_record_reasons"] and info["policy_hash"] == POLICY_SHA256


@pytest.mark.parametrize(
    "arguments", ['build_id="build-002", extra=1', 'build_id="build-002", limit="3"', "limit=3"]
)
def test_later_invalid_arguments_exclude_entire_record(
    policy_tool, record_factory, source, arguments
):
    record = record_factory(tool=policy_tool, second=True)
    record["conversations"][-1]["value"] = f"[{policy_tool['name']}({arguments})]"
    info, examples = inspect_record(record, source, 0, SourcePolicy())
    assert not examples and "out_of_policy_arguments" in info["record_reasons"]
    assert all(d["normalized_hash"] is None for d in info["decisions"])
    assert info["decisions"][0]["attempted_normalized_hash"]


def test_later_unreliable_observation_invalidates_prior_candidate(
    policy_tool, record_factory, source
):
    record = record_factory(tool=policy_tool, second=True)
    record["conversations"][2]["value"] = json.dumps([{"name": "unknown", "results": 1}])
    info, examples = inspect_record(record, source, 0, SourcePolicy())
    assert not examples and "policy_history_observation_unreliable" in info["record_reasons"]


def test_system_context_preserved_unknown_text_not_deleted(
    policy_tool, record_factory, source, monkeypatch
):
    import toolalign.data.source_policy as module

    preamble = "Original test-only preamble. "
    monkeypatch.setattr(module, "PREAMBLE_LENGTH", len(preamble))
    monkeypatch.setattr(module, "PREAMBLE_HASH", text_hash(preamble))
    record = record_factory(tool=policy_tool)
    record["system"] = preamble + "Today is 2026-09-06, Sunday. " + record["system"]
    info, examples = inspect_record(record, source, 0, SourcePolicy())
    assert len(examples) == 1 and "2026-09-06" in examples[0]["messages"][0]["content"]
    assert info["system_conversion"]["preserved_context"] == "Today is 2026-09-06, Sunday."
    assert MARKER not in examples[0]["messages"][0]["content"]
    record["system"] = (
        preamble
        + "Important user-specific condition. "
        + record_factory(tool=policy_tool)["system"]
    )
    info, examples = inspect_record(record, source, 0, SourcePolicy())
    assert not examples and "policy_system_context_unknown" in info["record_reasons"]
    _, span = extract_tools(record)
    with pytest.raises(DataError, match="policy_system_context_unknown"):
        SourcePolicy().normalize_system(record["system"], span, MARKER)


def test_normalized_semantics_retains_property_names_and_ignores_annotation_order():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "description": {"type": "string", "maxLength": 10},
            "default": {"type": "integer"},
        },
        "required": ["default", "description"],
    }
    equivalent = copy.deepcopy(schema)
    equivalent["required"].reverse()
    equivalent["description"] = "Changed annotation"
    assert normalized_schema_semantics(schema) == normalized_schema_semantics(equivalent)
    changed = copy.deepcopy(schema)
    changed["properties"]["default"]["type"] = "boolean"
    assert normalized_schema_semantics(schema) != normalized_schema_semantics(changed)


def test_normalized_bridge_guard_preserves_original_assignments():
    infos = [
        {"source_record_hash": "a", "normalized_schema_keys": ["shared", "only-a"]},
        {"source_record_hash": "b", "normalized_schema_keys": ["shared"]},
        {"source_record_hash": "c", "normalized_schema_keys": ["only-c"]},
    ]
    assignments = [
        {"group_id": "one", "split": "train"},
        {"group_id": "two", "split": "test"},
        {"group_id": "three", "split": "test"},
    ]
    original = copy.deepcopy(assignments)
    excluded, conflicts, report = normalized_group_guard(infos, assignments)
    assert assignments == original and excluded == {"a", "b"}
    assert conflicts[0]["normalized_schema_key"] == "shared"
    assert report["bridge_keys"] == report["cross_split_bridge_keys"] == 1
    assert report["original_assignments_changed"] is False
