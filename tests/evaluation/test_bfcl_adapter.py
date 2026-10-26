"""Original CPU adapter, isolation and strict-gate invariants; no official imports."""

import copy

import pytest
from bfcl_original_cases import action, original_record, selected

from toolalign.contracts import ContractError, canonical_hash
from toolalign.evaluation.bfcl.adapter import (
    StrictActionDecoder,
    Unrepresentable,
    adapt_prompt,
    parameter_projection,
    restore_parameters,
)
from toolalign.evaluation.bfcl.scoring import score_action
from toolalign.evaluation.bfcl.source import selected_answers
from toolalign.evaluation.bfcl.subset import choose_subset, connected_groups


def candidates(n=1):
    return [{"category": "simple_python", "ordinal": i, "record": original_record(f"original-{i}")} for i in range(n)]


def test_lossless_names_parameters_and_prompt():
    record = original_record(names=("lab.pick_version", "lab_pick_version", "LAB.pick_version"))
    before = copy.deepcopy(record)
    converted = adapt_prompt(record)
    assert record == before
    mapping, inverse = converted["name_map"], converted["inverse_name_map"]
    assert len(set(mapping.values())) == 3 and all(inverse[value] == key for key, value in mapping.items())
    assert converted["model_input"]["messages"][0]["content"] == record["question"][0][0]["content"]
    for original, tool, change in zip(record["function"], converted["model_input"]["tools"], converted["schema_type_rewrites"], strict=True):
        assert restore_parameters(tool["parameters_json_schema"], change["type_rewrites"]) == original["parameters"]
    assert StrictActionDecoder(mapping).decode_ast(action(mapping["lab.pick_version"])) == [{"lab.pick_version": {"revision": 17}}]


@pytest.mark.parametrize("schema,code", [
    ({"type": "object", "properties": {}}, "object_not_explicitly_closed"),
    ({"type": "string"}, "string_without_supported_bound"),
    ({"type": "array", "items": {"type": "integer"}}, "array_without_supported_bound"),
    ({"type": "tuple", "items": {"type": "integer"}}, "unsupported_parameter_type"),
    ({"type": "integer", "default": 17}, "unsupported_schema_keyword"),
])
def test_reject_inexpressible_schema_without_dropping_or_adding_constraints(schema, code):
    record = original_record()
    record["function"][0]["parameters"]["properties"]["revision"] = schema
    before = copy.deepcopy(record)
    with pytest.raises(Unrepresentable) as caught:
        adapt_prompt(record)
    assert code in {issue["code"] for issue in caught.value.issues}
    assert record == before


def test_recursive_type_aliases_roundtrip():
    schema = {"type": "dict", "properties": {"ratio": {"type": "float"},
                "values": {"type": "array", "items": {"type": "dict", "properties": {}}}}}
    projected, changes = parameter_projection(schema)
    assert projected["properties"]["ratio"]["type"] == "number"
    assert restore_parameters(projected, changes) == schema


def test_decoder_distinguishes_bad_action_from_valid_no_tool_and_unknown_alias():
    decoder = StrictActionDecoder({"lab.pick_version": "projected_name"})
    for kind in ("final", "clarify", "refuse"):
        assert decoder.decode_ast(action(kind=kind)) == []
    with pytest.raises(ContractError):
        decoder.decode_ast("")
    assert decoder.decode_ast(action("unknown_tool")) == [{"unadvertised:unknown_tool": {"revision": 17}}]


def test_ordered_caps_lengths_and_all_decisions_are_retained():
    rows = candidates(25)
    counts = iter([1793, 1792] + [100] * 23)
    selection, inputs, audit = choose_subset(rows, [], lambda value: next(counts))
    assert len(selection["ledger"]) == 25 and len(inputs) == 20
    assert [e["task_id"] for e in inputs] == [f"original-{i}" for i in range(1, 21)]
    assert selection["ledger"][0]["length_status"] == "EXCEEDS_CONTEXT"
    assert selection["ledger"][1]["length_status"] == "PASS"
    assert selection["ledger"][21]["disposition"] == "category_cap"
    assert len(audit["components"]) == 1 and selection["selected_groups"] == 1
    assert selection["official_scoring"] == selection["model_evaluation"] == "NOT_RUN"


def test_transitive_reference_overlap_propagates_through_excluded_candidate():
    rows = candidates(3)
    rows[0]["record"] = original_record("original-0", names=("alpha",))
    rows[1]["record"] = original_record("original-1", names=("alpha", "beta"))
    rows[1]["record"]["function"][1]["parameters"]["properties"]["revision"]["default"] = 17
    rows[2]["record"] = original_record("original-2", names=("beta",))
    references = [{"origin": "P02", "group_id": "heldout-metadata-only", "keys": {"tool:" + canonical_hash({"name": "beta"})}}]
    audit = connected_groups(rows, references)
    assert len(audit["components"]) == 1 and all(item["overlap"] for item in audit["assignments"].values())
    selection, inputs, _ = choose_subset(rows, references, lambda _: 100)
    assert not inputs and selection["status"] == "NO_ELIGIBLE_INPUTS"
    assert all(any(issue["code"] == "known_group_overlap" for issue in row["issues"]) for row in selection["ledger"])


def test_unrepresentable_never_tokenizes_and_scope_cannot_expand():
    row = candidates()[0]
    del row["record"]["function"][0]["parameters"]["additionalProperties"]
    def forbidden(_):
        raise AssertionError("No lossy model input may be tokenized")
    selection, inputs, _ = choose_subset([row], [], forbidden)
    assert not inputs and selection["ledger"][0]["input_tokens"] is None
    with pytest.raises(ValueError, match="scan_limit"):
        choose_subset(candidates(51), [], forbidden)


def test_unrun_scorer_does_not_fill_any_measured_score():
    item = selected(original_record(), "irrelevance")
    row = {"plan": {}, "batch_sha256": "fixture", "status": "not_started", "result": None}
    result = score_action(row, item, None, None)
    assert result["official_status"] == "NOT_RUN"
    assert result["official_raw_valid"] is result["strict_success"] is None


def test_no_answer_access_without_saved_nonempty_selection(tmp_path):
    path = tmp_path / "selection.json"
    path.write_text('{"status":"NO_ELIGIBLE_INPUTS"}')
    from toolalign.data.common import file_hash
    with pytest.raises(ValueError, match="nonempty_frozen_selection"):
        selected_answers(tmp_path / "nonexistent-source", path, file_hash(path), tmp_path / "answers")
    assert not (tmp_path / "answers").exists()
