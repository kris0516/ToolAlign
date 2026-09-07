"""Original, synthetic selection checks; no ToolACE content or real calls."""

import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from audit_sample import CONFIG_SHA256, index_sources, load_config, patterns_for, select_sources

from toolalign.contracts import canonical_hash

REPOSITORY = Path(__file__).resolve().parents[3]


@pytest.fixture
def config():
    # Original small fixture policy, never substituted for the signed real input.
    return {
        "sampling": {"rank_domain": "toolalign.quality-review.v1", "seed": 42,
                     "random_by_split": {"train": 2, "validation": 1},
                     "targeted_max_per_pattern": 2, "new_source_limit": 15},
        "patterns": [
            {"name": "conditional_history", "user_text_regex": r"\b(if|unless|only after|provided that)\b",
             "or_valid_decision_count_greater_than": 1},
            {"name": "identifier_scope", "invoked_parameter_name_suffix_regex": r"(id|slug|symbol|code)$"},
            {"name": "unit_or_encoding", "invoked_parameter_name_or_description_regex": r"\b(rate|percent|percentage|unit|units|currency|sort|direction|page)\b"},
            {"name": "relative_time", "user_text_regex": r"\b(today|tomorrow|yesterday|recent|current|next|last|this)\b"},
            {"name": "parallel_object", "maximum_expected_tool_calls_at_least": 3},
            {"name": "optional_arguments", "any_invoked_declared_optional_parameter_omitted": True},
        ],
    }


def example(tag, split="train"):
    value = json.loads((REPOSITORY / "tests/fixtures/contracts/example.json").read_text())
    value.update(example_id="audit-fixture-" + tag, source_record_hash=canonical_hash(tag), split=split)
    return value


def assignment(value, index):
    return {key: value[key] for key in ("source_record_hash", "split", "group_id")} | {
        "source_index": index
    }


def test_real_config_hash_is_fixed_and_wrong_input_is_rejected(tmp_path):
    assert len(CONFIG_SHA256) == 64
    path = tmp_path / "fixture-config.json"
    path.write_text('{"seed": 43}')
    with pytest.raises(ValueError, match="S0-authorized"):
        load_config(path)


def test_all_valid_decisions_and_previous_review_exclusion(config):
    first, second, old, heldout = [example(tag) for tag in ("a", "b", "old", "heldout")]
    second["source_record_hash"] = first["source_record_hash"]
    heldout["split"] = "test"
    assignments = [assignment(value, index) for index, value in enumerate((first, old, heldout))]
    pool, descriptors, valid, invalid = index_sources(
        {"train": [first, second, old], "validation": []}, assignments,
        {old["source_record_hash"]}, config,
    )
    assert set(pool) == {first["source_record_hash"]}
    assert descriptors[first["source_record_hash"]]["valid_decision_count"] == 2
    assert len(valid[first["source_record_hash"]]) == 2 and not invalid
    assert "conditional_history" in pool[first["source_record_hash"]]["pattern_hits"]


@pytest.mark.parametrize("mistake", ["heldout_input", "wrong_file", "wrong_assignment", "duplicate"])
def test_split_and_identity_mistakes_fail_closed(config, mistake):
    value = example("x")
    rows = {"train": [value], "validation": []}
    assigned = [assignment(value, 0)]
    if mistake == "heldout_input":
        value["split"] = "test"
        rows = {"test": [value]}
    elif mistake == "wrong_file":
        value["split"] = "validation"
    elif mistake == "wrong_assignment":
        assigned[0]["group_id"] = "different-group"
    else:
        rows["train"].append(copy.deepcopy(value))
    with pytest.raises(ValueError):
        index_sources(rows, assigned, set(), config)


def test_invalid_example_is_not_an_effective_source(config):
    value = example("invalid")
    value["expected_action"]["tool_calls"][0]["arguments"] = {}
    pool, _, _, invalid = index_sources({"train": [value]}, [assignment(value, 0)], set(), config)
    assert not pool and len(invalid) == 1


def test_six_patterns_use_user_prefixes_and_invoked_parameters(config):
    value = example("patterns")
    value["messages"][0]["content"] = "Only after checking today, read three fixture builds."
    schema = value["tools"][0]["parameters_json_schema"]
    schema["properties"]["page"] = {"type": "integer", "description": "Page number"}
    schema["properties"]["optional_note"] = {"type": "string", "maxLength": 64}
    value["expected_action"]["tool_calls"] = [
        {"call_id": str(i), "name": "read_fixture", "arguments": {"build_id": "demo", "page": 1}}
        for i in range(3)
    ]
    assert patterns_for([value], config) == [p["name"] for p in config["patterns"]]
    value["messages"][0]["role"] = "system"
    value["expected_action"]["tool_calls"] = []
    assert patterns_for([value], config) == []


def test_identifier_normalization_and_word_boundaries(config):
    value = example("normalization")
    schema = value["tools"][0]["parameters_json_schema"]
    schema["properties"] = {"customer_ID": {"type": "string"}, "interest_rate": {"type": "number"}}
    schema["required"] = list(schema["properties"])
    value["expected_action"]["tool_calls"][0]["arguments"] = {"customer_ID": "demo", "interest_rate": 1}
    assert "identifier_scope" in patterns_for([value], config)
    assert "unit_or_encoding" not in patterns_for([value], config)
    schema["properties"]["interest_rate"]["description"] = "Percentage rate"
    assert "unit_or_encoding" in patterns_for([value], config)


def test_fixed_rank_random_first_global_dedup_and_shortfall(config):
    pool = {}
    for number in range(5):
        source_hash = canonical_hash(["original-fixture", number])
        pool[source_hash] = {"source_record_hash": source_hash,
                             "split": "validation" if number == 4 else "train",
                             "pattern_hits": [p["name"] for p in config["patterns"]]}
    selected, phases = select_sources(pool, config)
    repeated = select_sources(dict(reversed(list(pool.items()))), config)
    assert (selected, phases) == repeated
    independent = sorted(
        [key for key, row in pool.items() if row["split"] == "train"],
        key=lambda key: (hashlib.sha256(json.dumps(
            ["toolalign.quality-review.v1", 42, key], ensure_ascii=False,
            separators=(",", ":"), sort_keys=True,
        ).encode()).hexdigest(), key),
    )
    assert [r["source_record_hash"] for r in selected[:2]] == independent[:2]
    assert len(selected) == len({r["source_record_hash"] for r in selected}) == 5
    assert [phase["selected"] for phase in phases] == [2, 1, 2, 0, 0, 0, 0, 0]
    assert all(phase["shortfall"] == 2 for phase in phases[3:])


def test_rank_tie_uses_source_hash(config):
    pool = {key: {"source_record_hash": key, "split": "train", "pattern_hits": []}
            for key in ("c", "a", "b")}
    with patch("audit_sample.rank", return_value="same-rank"):
        selected, _ = select_sources(pool, config)
    assert [r["source_record_hash"] for r in selected] == ["a", "b"]


def test_heldout_diagnostic_cannot_escape_guard(config):
    pool = {"heldout": {"source_record_hash": "heldout", "split": "ood_test",
                        "pattern_hits": ["conditional_history"]}}
    with pytest.raises(ValueError, match="Held-out"):
        select_sources(pool, config)
