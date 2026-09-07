"""Original CPU regressions for type-preserving views and their references."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "r1_boundaries", Path(__file__).with_name("r1_test_independent_boundaries.py")
)
R1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R1)
VALUES = importlib.import_module("json_values")


def test_json_categories_nested_values_and_number_representations():
    values = [None, False, True, 0, 1, 0.0, 1.0, -0.0, "0", "false", [], {}]
    for i, left in enumerate(values):
        for j, right in enumerate(values):
            assert VALUES.json_equal({"nested": [left]}, {"nested": [right]}) is (i == j)
    assert VALUES.json_equal(json.loads('{"z": [false, null], "a": 1}'),
                             json.loads('{\n"a":1,"z":[ false,null ]}'))
    assert not VALUES.json_equal([False, 0], [0, False])


def test_non_json_values_are_rejected():
    for value in ((0,), {0: "numeric key"}, {"nested": [float("nan")]}, float("inf")):
        with pytest.raises((TypeError, ValueError)):
            VALUES.json_key(value)


@pytest.mark.parametrize("number,boolean", [(0, False), (1, True)])
def test_nested_observation_type_change_is_visible(tmp_path, number, boolean):
    value = R1.packet("nested-observation", observation={"nested": [number]},
                      normalized_observation={"nested": [boolean]})
    view, packets, _ = R1.view_fixture(tmp_path, "fixture", value)
    assert R1.verify_semantic_views.verify(view, packets)["sources"] == 1
    message = next(json.loads(line.split(" ", 2)[2]) for line in view.read_text().splitlines()
                   if line.startswith("NORMALIZED_MESSAGE ")
                   and json.loads(line.split(" ", 2)[2])["role"] == "tool")
    assert type(message["content"]) is str
    assert R1.encoded(json.loads(message["content"])) == R1.encoded(
        {"ok": {"nested": [boolean]}}
    )


def test_key_order_spacing_and_cross_packet_exact_references_still_work(tmp_path):
    value = R1.packet("valid-references", observation={"a": 1, "b": [False, None]},
                      normalized_observation={"b": [False, None], "a": 1},
                      two_decisions=True)
    for decision in value["valid_decisions"]:
        message = decision["example"]["messages"][2]
        message["content"] = json.dumps(json.loads(message["content"]), indent=2)
    paths = [tmp_path / "packets" / (name + ".json") for name in ("first", "second")]
    for path in paths:
        R1.save(path, value)
    rendered, coverage = R1.semantic_view.render(paths)
    view = tmp_path / "view.txt"
    view.write_text(rendered)
    R1.save(view.with_suffix(".json"), {"view_sha256": R1.digest(view), "coverage": coverage})
    assert '"equal_json_value_ref":' in rendered and '"exact_string_ref":' in rendered
    assert R1.verify_semantic_views.verify(view, paths[0].parent)["decisions"] == 4
    assert all(item["toolset_count"] == 1 for item in coverage)


def test_nested_toolsets_and_history_are_not_deduplicated_across_types(tmp_path):
    value = R1.packet("distinct-toolsets-and-messages", two_decisions=True)
    first, second = value["valid_decisions"]
    for decision, flag in ((first, 0), (second, False)):
        tool = decision["example"]["tools"][0]
        # Optional schema values may differ even when the invoked target is the same.
        tool["parameters_json_schema"]["properties"]["unused"] = {
            "type": "object", "properties": {"flag": {"type": "boolean"}},
            "additionalProperties": False, "enum": [{"flag": flag}],
        }
        decision["example"]["messages"][1]["tool_calls"][0]["arguments"]["flag"] = flag
        R1.validate_record(decision["example"], "example")
    view, packets, coverage = R1.view_fixture(tmp_path, "fixture", value)
    assert R1.verify_semantic_views.verify(view, packets)["decisions"] == 2
    targets = [json.loads(line.removeprefix("TARGET ")) for line in view.read_text().splitlines()
               if line.startswith("TARGET ")]
    assert coverage[0]["toolset_count"] == 2
    assert targets[0]["toolset"] != targets[1]["toolset"]
    assert targets[0]["complete_prefix_message_refs"][1] != targets[1]["complete_prefix_message_refs"][1]


def tamper(view, prefix, change):
    lines = view.read_text().splitlines()
    offset = next(i for i, line in enumerate(lines) if line.startswith(prefix))
    value = json.loads(lines[offset][len(prefix):])
    change(value)
    lines[offset] = prefix + R1.encoded(value)
    view.write_text("\n".join(lines) + "\n")
    R1.rehash_view(view)


@pytest.mark.parametrize("location", ["raw_tools", "normalized_tool", "message", "header",
                                      "coverage", "turn", "message_ref_bool", "message_ref_float",
                                      "toolset_bool", "toolset_float"])
def test_verifier_rejects_type_changes_even_with_updated_view_digest(tmp_path, location):
    value = R1.packet("tampering")
    value["valid_decisions"][0]["example"]["tools"][0]["parameters_json_schema"]["properties"]["flag"]["enum"] = [False]
    R1.validate_record(value["valid_decisions"][0]["example"], "example")
    view, packets, _ = R1.view_fixture(tmp_path, "fixture", value)
    assert R1.verify_semantic_views.verify(view, packets)["decisions"] == 1
    if location == "raw_tools":
        tamper(view, "RAW_TOOLS ", lambda v: v[0]["parameters"].update(additionalProperties=0))
    elif location == "normalized_tool":
        tamper(view, "NORMALIZED_TOOL 0:0 raw_tool_index=0 DELTA ",
               lambda v: v[0].__setitem__(2, [0]))
    elif location == "message":
        tamper(view, "NORMALIZED_MESSAGE 1 ",
               lambda v: v["tool_calls"][0]["arguments"].update(flag=0))
    elif location == "header":
        tamper(view, "PACKET fixture ", lambda v: v.update(source_index=False))
    elif location == "coverage":
        metadata = json.loads(view.with_suffix(".json").read_text())
        metadata["coverage"][0]["toolset_count"] = True
        R1.save(view.with_suffix(".json"), metadata)
    elif location == "turn":
        tamper(view, "TARGET ", lambda v: v.update(source_turn_index=3.0))
    elif location.startswith("message_ref_"):
        replacement = False if location.endswith("bool") else 0.0
        tamper(view, "TARGET ", lambda v: v["complete_prefix_message_refs"].__setitem__(0, replacement))
    else:
        replacement = False if location.endswith("bool") else 0.0
        tamper(view, "TARGET ", lambda v: v.update(toolset=replacement))
    with pytest.raises(AssertionError):
        R1.verify_semantic_views.verify(view, packets)


def test_same_type_reordered_toolset_and_message_are_reused(tmp_path):
    value = R1.packet("key-order", two_decisions=True)
    first, second = value["valid_decisions"]
    second["example"]["tools"] = [dict(reversed(list(tool.items())))
                                   for tool in copy.deepcopy(first["example"]["tools"])]
    second["example"]["messages"][1] = dict(reversed(list(first["example"]["messages"][1].items())))
    view, packets, coverage = R1.view_fixture(tmp_path, "fixture", value)
    assert R1.verify_semantic_views.verify(view, packets)["decisions"] == 2
    assert coverage[0]["toolset_count"] == 1
    targets = [json.loads(line.removeprefix("TARGET ")) for line in view.read_text().splitlines()
               if line.startswith("TARGET ")]
    assert targets[0]["complete_prefix_message_refs"] == targets[1]["complete_prefix_message_refs"][:3]
