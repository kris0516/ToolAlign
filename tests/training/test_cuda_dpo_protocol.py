"""Synthetic input, quality-gate, and finite-run contracts; no model files."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from toolalign.contracts import canonical_hash
from toolalign.data.preferences.review import apply_review, freeze_review
from toolalign.model_io.cuda_generation import selected_model_identity
from toolalign.training.cuda_dpo.data import bind_input, prepare_rows, read_input, reviewed_input
from toolalign.training.cuda_dpo.protocol import (
    CONFIG_SHA256,
    load_protocol,
    select_pairs,
    validate_run,
)
from toolalign.training.cuda_sft.protocol import encoded

ROOT = Path(__file__).resolve().parents[2]


class CharacterTokenizer:
    """An original reversible character fixture, not the Qwen tokenizer."""

    eos_token_id = 2

    def render(self, messages, *, tools, add_generation_prompt, enable_thinking):
        assert tools is None and add_generation_prompt is True and enable_thinking is False
        return "\n".join(row["role"] + ":" + row["content"] for row in messages) + "\nassistant:\n"

    def encode(self, text, *, add_special_tokens):
        assert add_special_tokens is False
        return [ord(char) + 3 for char in text]

    def decode(self, ids, *, skip_special_tokens):
        assert skip_special_tokens is False
        return "".join(chr(value - 3) for value in ids)


def preference(record):
    value = record("preference")
    chosen = record("example")["expected_action"]
    rejected = copy.deepcopy(chosen)
    rejected["tool_calls"][0]["arguments"]["build_id"] = "demo-02"
    value["chosen"] = "  " + json.dumps(chosen, indent=2) + "\n"
    value["rejected"] = json.dumps(rejected, separators=(",", ":"))
    return value


def request(output):
    return {"schema": "toolalign.cuda-dpo-run.v1", "authorized_by": "S1", "run_kind": "dpo",
            "run_id": "synthetic-control", "source_commit": "a" * 40, "config_sha256": CONFIG_SHA256,
            "repository": str(ROOT), "lock_root": str(ROOT), "model_root": "/synthetic/not-loaded",
            "sft_checkpoint_dir": "/synthetic/not-loaded", "input_root": "/synthetic/not-loaded",
            "input_manifest_sha256": "b" * 64, "prepared_data_sha256": "c" * 64,
            "pair_count": 10, "total_optimizer_steps": 2, "stop_after_optimizer_step": 1,
            "checkpoint_every_steps": 1, "dependency_lock": str(ROOT / "requirements/dpo-linux-py312.lock.txt"),
            "dependency_lock_sha256": "d" * 64, "output_dir": str(output),
            "max_wall_seconds": 20, "max_output_bytes": 1024**2}


def test_raw_actions_full_prompt_tokens_eos_and_overflow_denominator(record):
    value = preference(record)
    tokenizer = CharacterTokenizer()
    prepared = prepare_rows([value], tokenizer, context_cap=20000)
    assert prepared["accepted_pairs"] == 1 and prepared["original_pairs"] == 1
    row, tokens = prepared["rows"][0], prepared["expected"][0]
    assert row["chosen"] == value["chosen"] and row["rejected"] == value["rejected"]
    assert "read_fixture" in row["prompt"] and "additionalProperties" in row["prompt"]
    for side in ("chosen", "rejected"):
        ids = tokens[side + "_input_ids"]
        assert ids[-1] == tokenizer.eos_token_id and ids.count(tokenizer.eos_token_id) == 1
        assert tokenizer.decode(ids[:-1], skip_special_tokens=False) == value[side]
        assert tokens["prompt_input_ids"] + ids[:-1] == tokenizer.encode(
            row["prompt"] + value[side], add_special_tokens=False)
    maximum = max(prepared["dispositions"][0][side + "_tokens_including_eos"]
                  for side in ("chosen", "rejected"))
    assert prepare_rows([value], tokenizer, context_cap=maximum)["accepted_pairs"] == 1
    overflow = prepare_rows([value], tokenizer, context_cap=maximum - 1)
    assert overflow["original_pairs"] == overflow["excluded_pairs"] == 1
    assert overflow["rows"] == overflow["expected"] == []
    assert overflow["dispositions"][0]["disposition"] == "context_overflow"


def test_joint_encoding_conflict_is_explicit_no_silent_retokenization(record):
    class BoundaryMerge(CharacterTokenizer):
        def encode(self, text, *, add_special_tokens):
            ids = super().encode(text, add_special_tokens=add_special_tokens)
            marker = "\nassistant:\n"
            if marker in text and not text.endswith(marker):
                ids[text.index(marker) + len(marker) - 1] += 1
            return ids

    with pytest.raises(ValueError, match="prompt_completion_boundary"):
        prepare_rows([preference(record)], BoundaryMerge(), context_cap=20000)


def test_q1_bundle_binds_raw_files_order_and_original_review_denominator(record, tmp_path):
    # Entirely fabricated metadata exercises the formal-format acceptance branch.
    # The reviewer and every judgment explicitly identify this as a synthetic test.
    value = preference(record)
    value["generation_model"] = selected_model_identity(ROOT)
    line = {"preference_id": value["preference_id"], "synthetic": False,
            "error_class": "argument_semantics", "prompt_hash": value["prompt_hash"],
            "chosen": {"generation_parameters": value["generation_parameters"]},
            "trace_hashes": {side: value[side + "_validation"]["trace_hash"]
                             for side in ("chosen", "rejected")}}
    sample = freeze_review([value], [line], synthetic=False)
    review = {"sample_hash": canonical_hash(sample), "reviewer": "synthetic-Q1-fixture-not-a-review",
              "judgments": [{"preference_id": value["preference_id"], "verdict": "pass",
                             "reason": "Synthetic acceptance-branch test; no real review occurred."}]}
    result = apply_review(sample, [value], [line], review)
    training = result.pop("training_preferences")
    result.pop("remaining_preferences")
    extraction, reviewed = tmp_path / "synthetic-extraction", tmp_path / "synthetic-reviewed"
    extraction.mkdir()
    reviewed.mkdir()
    for name, data in (("preferences.jsonl", value), ("lineage.jsonl", line), ("q1-sample.json", sample)):
        (extraction / name).write_bytes(encoded(data) + b"\n")
    (reviewed / "training-preferences.jsonl").write_bytes(encoded(training[0]) + b"\n")
    (reviewed / "review-result.json").write_bytes(encoded(result) + b"\n")
    review_path = tmp_path / "synthetic-review.json"
    review_path.write_bytes(encoded(review) + b"\n")
    output = tmp_path / "synthetic-bundle"
    binding = bind_input(extraction=extraction, reviewed=reviewed, review=review_path, output=output)
    restored, manifest = read_input(output, binding["input_manifest_sha256"])
    assert restored == [value]
    assert manifest["q1_result"]["original_review_denominator"] == 1
    assert manifest["q1_result"]["training_authorized"] is False
    (output / "training-preferences.jsonl").write_bytes(encoded(value) + b" \n")
    with pytest.raises(ValueError, match="input_file_identity"):
        read_input(output, binding["input_manifest_sha256"])
    contents = {path.name: path.read_bytes() for path in output.iterdir() if path.name != "input-manifest.json"}
    packet = json.loads(contents["q1-sample.json"])
    packet["synthetic"] = True
    contents["q1-sample.json"] = encoded(packet)
    with pytest.raises(ValueError, match="synthetic_preferences_cannot_train"):
        reviewed_input(contents)


@pytest.mark.parametrize("change", [
    {"pair_count": 0}, {"total_optimizer_steps": 1}, {"total_optimizer_steps": True},
    {"stop_after_optimizer_step": 3}, {"run_kind": "sft"}, {"max_wall_seconds": 21601},
    {"max_output_bytes": 1024**3 + 1}, {"capacity_pair_ids": ["x"]},
    {"dependency_lock": str(ROOT / "requirements/cuda-linux-py312.lock.txt")},
])
def test_finite_run_and_separate_environment_contract(tmp_path, change):
    assert load_protocol(ROOT)["is_run_authorization"] is False
    assert validate_run(request(tmp_path / "output"))["total_optimizer_steps"] == 2
    with pytest.raises(ValueError):
        validate_run(request(tmp_path / "output") | change)


def test_capacity_plan_is_distinct_longest_first_and_cannot_change_formal_order(tmp_path):
    prepared = {"accepted_pairs": 2, "rows": [{"preference_id": "short"}, {"preference_id": "long"}],
                "expected": [{"preference_id": "short"}, {"preference_id": "long"}],
                "dispositions": [{"preference_id": name, "disposition": "accepted",
                                  "chosen_tokens_including_eos": length,
                                  "rejected_tokens_including_eos": length - 1}
                                 for name, length in (("short", 5), ("long", 9))]}
    summary = {"prepared_data_sha256": "c" * 64}
    run = request(tmp_path / "output") | {"run_kind": "dpo_capacity", "capacity_pair_ids": ["long"] * 10}
    validate_run(run)
    selected, tokens = select_pairs(prepared, summary, run)
    assert len(selected) == len(tokens) == 10 and len({row["preference_id"] for row in selected}) == 10
    assert prepared["rows"] == [{"preference_id": "short"}, {"preference_id": "long"}]
    with pytest.raises(ValueError, match="longest_pair_first"):
        select_pairs(prepared, summary, run | {"capacity_pair_ids": ["short"] * 10})
    with pytest.raises(ValueError, match="unapproved_pair"):
        select_pairs(prepared, summary, run | {"capacity_pair_ids": ["missing"] * 10})
    formal = request(tmp_path / "output") | {"pair_count": 2, "total_optimizer_steps": 1}
    assert select_pairs(prepared, summary, formal)[0] == prepared["rows"]
