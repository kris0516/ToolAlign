"""Independent original CPU cases for the frozen P04 preparation candidate.

The character sequences below are synthetic, not Qwen measurements. No worker
fixture, real Example, tokenizer, numerical backend, or training loop is used.
The same cases can run with the new wheel; that repetition is not a new count.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import struct
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError, encoded
from toolalign.data.training_selection import load_config
from toolalign.model_io import Sequence
from toolalign.model_io.format import encode_action
from toolalign.training.sft import collate_sequence, epoch_plan, validate_plan
from toolalign.training.sft.__main__ import main
from toolalign.training.sft.config import consumer_identity
from toolalign.training.sft.data import view_from_records
from toolalign.training.sft.mlx_adapter import backend
from toolalign.training.sft.plan import EpochPlan, Segment
from toolalign.training.sft.validation import (
    Score,
    ValidationTotals,
    choose_score,
    parameter_content_hash,
    validate_score,
)

ROOT = Path(__file__).resolve().parents[3]
DATA_CONFIG = Path(os.environ.get("TOOLALIGN_REVIEW_CONFIG", ROOT / "configs/training-data.v1.json"))


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def rank(ident):
    return digest(["toolalign.training-selection.v1", 42, ident]), ident


def original_records():
    config = load_config(DATA_CONFIG)
    examples = []
    for ident, answer in (("review-cpu-a", "blue\n蓝色"), ("review-cpu-b", "left < right"),
                          ("review-cpu-c", "\"yes\"")):
        examples.append({
            "schema_version": "toolalign.example.v1", "example_id": ident,
            "source": "toolalign-original-r1-sft-cpu", "source_revision": "r1",
            "license_id": "MIT", "source_record_hash": digest(["original", ident]),
            "group_id": "group-" + ident, "split": "train", "category": "original_cpu",
            "tools": [], "messages": [{"role": "user", "content": "Read the sign.",
                                         "tool_calls": [], "tool_call_id": None}],
            "expected_action": {"kind": "final", "tool_calls": [], "content": answer},
        })
    examples.sort(key=lambda item: rank(item["example_id"]))
    sidecars = []
    for position, item in enumerate(examples, 1):
        # Character IDs are invented original fixtures. Only the already accepted
        # format's Action encoder and Sequence metadata are reused as inputs.
        completion = encode_action(item["expected_action"])
        prompt = "R1|"
        pids = tuple(map(ord, prompt))
        joined = pids + tuple(map(ord, completion))
        sequence = Sequence(prompt, completion, pids, joined, joined + (151645,),
                            (0,) * len(pids) + (1,) * (len(completion) + 1), 151645)
        audit = {
            **sequence.metadata(),
            **{key: item[key] for key in ("example_id", "source", "source_revision",
                                          "source_record_hash", "group_id", "split")},
            "common_binding_sha256": config["representation_common_binding_sha256"],
            "example_sha256": digest(item),
            "model_input_sha256": digest({key: item[key] for key in ("messages", "tools")}),
            "action_sha256": digest(item["expected_action"]),
            "parser_action_sha256": digest(item["expected_action"]), "kind": "final",
            "sequence_error": None, "parser_error": None, "parser_accepted_exact": True,
            "rendered_inverse_exact": True, "raw_byte_cap_pass": True,
            "raw_node_cap_pass": True, "raw_depth_cap_pass": True,
            "raw_byte_cap": 131072, "action_nodes": 4, "action_depth": 1,
            "action_native_utf8_bytes": len(encoded(item["expected_action"])),
            "causal_input_ids_sha256": digest(list(sequence.sequence_ids[:-1])),
            "causal_target_ids_sha256": digest(list(sequence.sequence_ids[1:])),
            "role_bindings_sha256": digest(["original-character-fixture"]),
        }
        sidecars.append({"profile": "smoke", "split": "train", "selection_rank": position,
                         "ranking_sha256": rank(item["example_id"])[0],
                         "padding_bucket": 1024, "audit": audit})
    return dict(examples=examples, sidecars=sidecars, config=config, profile="smoke", split="train",
                selection_sha256="1" * 64, expected_count=3,
                expected_identity=digest([item["example_id"] for item in examples]))


def tiny_sequence():
    # An EOS in historical prompt data is not an appended completion EOS.
    return Sequence("historical prompt", "original target", (7, 2), (7, 2, 3, 4),
                    (7, 2, 3, 4, 7), (0, 0, 1, 1, 1), 7)


def score(**changes):
    return replace(Score("TOY_CPU", "1" * 64, "2" * 64, "3" * 64, "4" * 64,
                         1, 8, 9.0, 3, 3.0), **changes)


def test_view_copies_every_original_value_and_nested_return():
    args = original_records()
    expected = copy.deepcopy(args)
    view = view_from_records(**args)
    assert [row.example for row in view.rows] == expected["examples"]
    assert [row.sidecar for row in view.rows] == expected["sidecars"]
    args["examples"][0]["messages"][0]["content"] = "caller mutation"
    args["sidecars"][0]["audit"]["source"] = "caller mutation"
    view[0].example["messages"][0]["content"] = "consumer mutation"
    view[0].sidecar["audit"]["source"] = "consumer mutation"
    assert view[0].example == expected["examples"][0]
    assert view[0].sidecar == expected["sidecars"][0]


@pytest.mark.parametrize("mutation", ["missing_example", "missing_sidecar", "duplicate", "reorder",
                                      "count", "identity", "rank", "ranking_hash", "larger_bucket"])
def test_view_requires_complete_ranked_smallest_bucket_selection(mutation):
    args = original_records()
    if mutation == "missing_example":
        args["examples"].pop()
    elif mutation == "missing_sidecar":
        args["sidecars"].pop()
    elif mutation == "duplicate":
        args["examples"][1] = copy.deepcopy(args["examples"][0])
        args["sidecars"][1] = copy.deepcopy(args["sidecars"][0])
    elif mutation == "reorder":
        args["examples"].reverse()
        args["sidecars"].reverse()
    elif mutation == "count":
        args["expected_count"] = 2
    elif mutation == "identity":
        args["expected_identity"] = "0" * 64
    else:
        key, value = {"rank": ("selection_rank", 0), "ranking_hash": ("ranking_sha256", "0" * 64),
                      "larger_bucket": ("padding_bucket", 1536)}[mutation]
        args["sidecars"][0][key] = value
    with pytest.raises(DataError):
        view_from_records(**args)


@pytest.mark.parametrize("mutation", ["profile", "test", "ood_test", "row_split", "sidecar_profile",
                                      "action", "audit_identity", "audit_loss_mask", "audit_success"])
def test_view_binds_allowed_split_original_action_and_full_audit(mutation):
    args = original_records()
    if mutation in ("test", "ood_test"):
        args["split"] = mutation
    elif mutation == "profile":
        args["profile"] = "../formal"
    elif mutation == "row_split":
        args["examples"][0]["split"] = "validation"
    elif mutation == "sidecar_profile":
        args["sidecars"][0]["profile"] = "formal"
    elif mutation == "action":
        args["examples"][0]["expected_action"]["content"] += "changed"
    else:
        key, value = {"audit_identity": ("example_sha256", "0" * 64),
                      "audit_loss_mask": ("causal_loss_mask_sha256", "0" * 64),
                      "audit_success": ("parser_accepted_exact", False)}[mutation]
        args["sidecars"][0]["audit"][key] = value
    with pytest.raises(DataError):
        view_from_records(**args)


def test_collator_exact_arrays_and_historical_eos():
    batch = collate_sequence(tiny_sequence(), bucket=8, pad_token_id=0)
    assert batch.sequence_ids == (7, 2, 3, 4, 7, 0, 0, 0)
    assert batch.attention_mask == (1, 1, 1, 1, 1, 0, 0, 0)
    assert batch.loss_mask == (0, 0, 1, 1, 1, 0, 0, 0)
    assert batch.causal_input_ids == (7, 2, 3, 4, 7, 0, 0)
    assert batch.causal_target_ids == (2, 3, 4, 7, 0, 0, 0)
    assert batch.causal_loss_mask == (0, 1, 1, 1, 0, 0, 0)
    assert (batch.first_supervised_causal_position, batch.last_supervised_causal_position) == (1, 3)
    assert batch.effective_supervised_targets == 3
    assert batch.causal_target_ids[batch.last_supervised_causal_position] == 7


def test_padding_keeps_target_denominator_and_never_truncates():
    plain = collate_sequence(tiny_sequence(), bucket=5, pad_token_id=0)
    padded = collate_sequence(tiny_sequence(), bucket=16, pad_token_id=0)
    assert plain.effective_supervised_targets == padded.effective_supervised_targets == 3
    assert padded.causal_loss_mask[:4] == plain.causal_loss_mask
    assert not any(padded.causal_loss_mask[4:])
    with pytest.raises(ValueError):
        collate_sequence(tiny_sequence(), bucket=4, pad_token_id=0)


@pytest.mark.parametrize("change", [
    {"eos_token_id": 6}, {"loss_mask": (0, 1, 1, 1, 1)}, {"prompt_ids": (7, 6)},
    {"concatenated_ids": (7, 2, 3)},
    {"sequence_ids": (7, 2, 7, 4, 7), "concatenated_ids": (7, 2, 7, 4)},
])
def test_collator_rejects_changed_shared_boundaries(change):
    with pytest.raises(DataError):
        collate_sequence(replace(tiny_sequence(), **change), bucket=8, pad_token_id=0)


def test_batch_rejects_forged_shift_padding_and_denominator():
    batch = collate_sequence(tiny_sequence(), bucket=8, pad_token_id=0)
    for change in ({"causal_target_ids": batch.causal_input_ids},
                   {"causal_loss_mask": (1,) * 7}, {"effective_supervised_targets": 4},
                   {"sequence_ids": (7, 2, 3, 4, 7, 1, 0, 0)}):
        with pytest.raises(DataError):
            replace(batch, **change)


@pytest.mark.parametrize("count,divisors,updates", [
    (1, (1,), 1), (7, (7,), 1), (8, (8,), 1), (9, (8, 1), 2),
    (13, (8, 5), 2), (1600, (8,), 200), (6013, (8, 5), 752),
])
def test_plan_visits_exactly_one_epoch_with_actual_remainder(count, divisors, updates):
    plan = epoch_plan(count)
    validate_plan(plan, range(1, count + 1))
    visited = [i for part in plan.segments for i in range(part.start, part.stop)]
    assert visited == list(range(count))
    assert tuple(part.divisor for part in plan.segments) == divisors
    assert plan.updates == updates
    assert plan.record()["optimizer_updates_executed"] == 0


def test_plan_rejects_empty_invalid_counts_and_noncanonical_coverage():
    for count in (0, -2, True, 13.0):
        with pytest.raises(DataError):
            epoch_plan(count)
    for plan in (EpochPlan(13, (Segment(0, 8, 8),)),
                 EpochPlan(13, (Segment(0, 8, 8), Segment(7, 13, 6))),
                 EpochPlan(13, (Segment(0, 8, 8), Segment(8, 13, 8)))):
        with pytest.raises(DataError):
            validate_plan(plan, range(1, 14))
    for ranks in ([1, 1, 3], [1, 3], [2, 1, 3], [0, 1, 2], [1, 2, True]):
        with pytest.raises(DataError):
            validate_plan(epoch_plan(3), ranks)


def test_validation_is_total_ce_over_all_supervised_tokens():
    totals = ValidationTotals(profile="formal", split="validation", expected_ids=("a", "b", "c"))
    for ident, numerator, denominator in (("a", 2.0, 1), ("b", 12.0, 4), ("c", 40.0, 8)):
        totals.add(example_id=ident, profile="formal", split="validation",
                   ce_sum=numerator, tokens=denominator)
    assert totals.finish() == 54.0 / 13
    assert totals.finish() != (2.0 + 3.0 + 5.0) / 3


def test_validation_requires_exact_identity_scope_order_and_coverage():
    for ids in ((), ("a", "a")):
        with pytest.raises(DataError):
            ValidationTotals(profile="smoke", split="validation", expected_ids=ids)
    totals = ValidationTotals(profile="smoke", split="validation", expected_ids=("a", "b"))
    args = dict(example_id="a", profile="smoke", split="validation", ce_sum=2.0, tokens=1)
    for change in ({"example_id": "b"}, {"profile": "formal"}, {"split": "test"}):
        with pytest.raises(DataError):
            totals.add(**(args | change))
    assert (totals.count, totals.numerator, totals.denominator) == (0, 0.0, 0)
    totals.add(**args)
    with pytest.raises(DataError):
        totals.add(**args)
    with pytest.raises(DataError):
        totals.finish()


def test_validation_nonfinite_zero_and_overflow_fail_closed():
    totals = ValidationTotals(profile="TOY_CPU", split="validation", expected_ids=("a", "b"))
    args = dict(example_id="a", profile="TOY_CPU", split="validation", ce_sum=1.0, tokens=1)
    for change in ({"tokens": 0}, {"tokens": -1}, {"tokens": True}, {"tokens": 1.5},
                   {"ce_sum": math.nan}, {"ce_sum": math.inf}, {"ce_sum": -math.inf}, {"ce_sum": -1}):
        with pytest.raises(DataError):
            totals.add(**(args | change))
    totals.add(**(args | {"ce_sum": 1e308}))
    totals.add(**(args | {"example_id": "b", "ce_sum": 1e308}))
    with pytest.raises(DataError):
        totals.finish()


def test_score_selection_is_finite_then_earliest_step_then_file_hash():
    baseline = score()
    lower = score(optimizer_step=2, processed_microsteps=13, ce_sum=6.0, validation_ce=2.0)
    earlier = score(ce_sum=6.0, validation_ce=2.0)
    hash_first = replace(earlier, checkpoint_file_sha256="0" * 64)
    assert choose_score((baseline, lower)) == lower
    assert choose_score((lower, earlier)) == earlier
    assert choose_score((earlier, hash_first)) == hash_first
    assert choose_score((hash_first, earlier)) == hash_first


def test_score_rejects_unbound_identity_counter_scope_and_loss():
    for changes in ({"parameter_content_sha256": "filename"}, {"selection_sha256": "F" * 64},
                    {"optimizer_step": 0}, {"processed_microsteps": 0}, {"supervised_tokens": 0},
                    {"validation_ce": math.nan}, {"ce_sum": math.inf}, {"validation_ce": 2.0},
                    {"scope": "FORMAL"}, {"profile": "formal"}):
        with pytest.raises(DataError):
            validate_score(score(**changes))
    for changes in ({"selection_sha256": "a" * 64}, {"validation_identity_sha256": "b" * 64}):
        with pytest.raises(DataError):
            choose_score((score(), score(**changes)))
    with pytest.raises(DataError):
        choose_score(())


def test_parameter_hash_binds_bytes_and_metadata_independent_of_entry_order():
    first = ("weights", "float32", (2,), struct.pack("<ff", 0.25, -0.5))
    second = ("bias", "float32", (1,), struct.pack("<f", 0.0))
    expected = digest(sorted([[name, dtype, list(shape), hashlib.sha256(data).hexdigest()]
                              for name, dtype, shape, data in (first, second)]))
    assert parameter_content_hash((first, second)) == parameter_content_hash((second, first)) == expected
    for changed in (("other", *first[1:]), (first[0], "float16", *first[2:]),
                    (*first[:2], (1, 2), first[3]), (*first[:3], struct.pack("<ff", 0.5, -0.5))):
        assert parameter_content_hash((changed, second)) != expected
    for values in ((), (first, first)):
        with pytest.raises(DataError):
            parameter_content_hash(values)


def test_default_api_loads_no_optional_backend_and_refuses_unleased_backend():
    forbidden = {"mlx", "mlx_lm", "torch", "transformers", "tokenizers", "tensorflow", "flax", "jax"}
    assert not forbidden & {name.split(".")[0] for name in sys.modules}
    with pytest.raises(DataError, match="active_shared_lease_required"):
        backend(None)
    assert not forbidden & {name.split(".")[0] for name in sys.modules}
    assert len(consumer_identity()) == 8
    if target := os.environ.get("TOOLALIGN_REVIEW_TARGET"):
        for name, module in tuple(sys.modules.items()):
            if name == "toolalign" or name.startswith("toolalign."):
                assert Path(module.__file__).resolve().is_relative_to(Path(target).resolve())


def test_cli_rejects_training_and_preserves_existing_diagnostic(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--train"])
    assert exc.value.code == 2
    flags = [value for key in ("sft-config-path", "public-selection-manifest-path", "selection-path",
                               "config-path", "data-manifest-path", "representation-path", "audit-path",
                               "protocol-path") for value in ("--" + key, str(tmp_path / "absent"))]
    output = tmp_path / ".toolalign-local" / "diagnostic"
    assert main([*flags, "--output", str(output)]) == 1
    original = (output / "preparation.json").read_bytes()
    assert json.loads(original)["status"] == "FAIL"
    assert main([*flags, "--output", str(output)]) == 1
    assert (output / "preparation.json").read_bytes() == original


def test_independent_json_digest_matches_frozen_contract():
    assert digest(["original", "蓝色", {"value": 3}]) == canonical_hash(["original", "蓝色", {"value": 3}])
