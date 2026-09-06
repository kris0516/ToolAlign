"""SFT CPU semantic boundaries, separate from framework numerical replays."""

import copy
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from sft_cases import records, sequence

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError
from toolalign.data.training_selection import load_config as data_config
from toolalign.training.sft import collate_sequence, epoch_plan, validate_plan
from toolalign.training.sft.__main__ import main
from toolalign.training.sft.config import load_config
from toolalign.training.sft.data import view_from_records
from toolalign.training.sft.plan import EpochPlan, Segment
from toolalign.training.sft.validation import (
    Score,
    ValidationTotals,
    choose_score,
    parameter_content_hash,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("count,updates,divisors", [
    (1, 1, [1]), (7, 1, [7]), (8, 1, [8]), (9, 2, [8, 1]), (13, 2, [8, 5]),
    (1600, 200, [8]), (6013, 752, [8, 5]),
])
def test_epoch_all_ranks_once_and_actual_tail_divisor(count, updates, divisors):
    plan = epoch_plan(count)
    validate_plan(plan, range(1, count + 1))
    assert plan.updates == updates
    assert [s.divisor for s in plan.segments] == divisors
    assert [i for s in plan.segments for i in range(s.start + 1, s.stop + 1)] == list(range(1, count + 1))
    assert plan.record()["optimizer_updates_executed"] == 0


@pytest.mark.parametrize("count", [0, -1, True, 1.5])
def test_empty_or_noninteger_epoch_fails(count):
    with pytest.raises(DataError):
        epoch_plan(count)


@pytest.mark.parametrize("ranks", [[1, 2, 2], [1, 3], [2, 1, 3], [0, 1, 2], [1, 2, 4], [True, 2, 3]])
def test_duplicate_missing_out_of_order_or_range_ranks_fail(ranks):
    with pytest.raises(DataError):
        validate_plan(epoch_plan(3), ranks)


@pytest.mark.parametrize("segments", [
    (Segment(0, 8, 8),), (Segment(0, 8, 8), Segment(7, 13, 6)),
    (Segment(0, 8, 8), Segment(9, 13, 4)), (Segment(0, 8, 8), Segment(8, 13, 8)),
    (Segment(0, 8, 8), Segment(8, 16, 8)),
])
def test_invalid_segment_coverage_and_tail_scaling_fail(segments):
    with pytest.raises(DataError):
        validate_plan(EpochPlan(13, segments), range(1, 14))


def test_shared_sequence_shift_eos_and_padding():
    seq = sequence()
    p, n = len(seq.prompt_ids), len(seq.sequence_ids)
    batch = collate_sequence(seq, bucket=1024, pad_token_id=151643)
    assert batch.causal_input_ids == batch.sequence_ids[:-1]
    assert batch.causal_target_ids == batch.sequence_ids[1:]
    assert batch.causal_loss_mask == batch.loss_mask[1:]
    assert batch.first_supervised_causal_position == p - 1
    assert batch.last_supervised_causal_position == n - 2
    assert batch.causal_target_ids[n - 2] == 151645
    assert batch.effective_supervised_targets == n - p
    assert batch.causal_loss_mask[:p - 1] == (0,) * (p - 1)
    assert sum(batch.causal_loss_mask[n - 1:]) == 0
    assert batch.attention_mask == (1,) * n + (0,) * (1024 - n)


@pytest.mark.parametrize("mutation", ["eos", "mask", "prefix", "truncate", "boolean_token", "denominator"])
def test_invalid_sequence_or_batch_fails(mutation):
    seq = sequence()
    with pytest.raises((DataError, ValueError)):
        if mutation == "denominator":
            replace(collate_sequence(seq, bucket=1024, pad_token_id=151643), effective_supervised_targets=0)
            return
        if mutation == "eos":
            seq = replace(seq, eos_token_id=8)
        elif mutation == "mask":
            seq = replace(seq, loss_mask=(1,) * len(seq.sequence_ids))
        elif mutation == "prefix":
            seq = replace(seq, prompt_ids=(0,))
        elif mutation == "boolean_token":
            ids = (True,) + seq.sequence_ids[1:]
            seq = replace(seq, sequence_ids=ids, concatenated_ids=ids[:-1], prompt_ids=ids[:len(seq.prompt_ids)])
        collate_sequence(seq, bucket=1 if mutation == "truncate" else 1024, pad_token_id=151643)


def view(values, sidecars, **overrides):
    config = data_config(ROOT / "configs/training-data.v1.json")
    args = dict(examples=values, sidecars=sidecars, config=config, profile="smoke", split="train",
                selection_sha256="a" * 64, expected_count=2,
                expected_identity=canonical_hash([e["example_id"] for e in values]))
    return view_from_records(**(args | overrides))


def test_view_preserves_original_fields_ranks_and_returns_isolated_values():
    values, sidecars = records(data_config(ROOT / "configs/training-data.v1.json"))
    result = view(values, sidecars)
    assert [r.example for r in result.rows] == values
    assert [r.sidecar for r in result.rows] == sidecars
    result[0].example["messages"][0]["content"] = "consumer mutation"
    values[0]["messages"][0]["content"] = "caller mutation"
    assert result[0].example["messages"][0]["content"] == "Check the original lamp."


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "order", "bucket", "rank", "split", "profile", "identity", "action"])
def test_view_rejects_broken_coverage_identity_and_sidecars(mutation):
    values, sidecars = records(data_config(ROOT / "configs/training-data.v1.json"))
    kwargs = {}
    if mutation == "missing":
        values.pop()
    elif mutation == "duplicate":
        values[1], sidecars[1] = copy.deepcopy(values[0]), copy.deepcopy(sidecars[0])
    elif mutation == "order":
        values.reverse()
        sidecars.reverse()
    elif mutation == "bucket":
        sidecars[0]["padding_bucket"] = 1536
    elif mutation == "rank":
        sidecars[0]["selection_rank"] = 2
    elif mutation == "split":
        kwargs["split"] = "test"
    elif mutation == "profile":
        kwargs["profile"] = "../formal"
    elif mutation == "identity":
        kwargs["expected_identity"] = "0" * 64
    else:
        values[0]["expected_action"]["content"] = "changed"
    with pytest.raises(DataError):
        view(values, sidecars, **kwargs)


def test_validation_weights_by_supervised_tokens_and_checks_exact_coverage():
    totals = ValidationTotals(profile="smoke", split="validation", expected_ids=["a", "b"])
    totals.add(example_id="a", profile="smoke", split="validation", ce_sum=2.0, tokens=1)
    with pytest.raises(DataError, match="incomplete"):
        totals.finish()
    totals.add(example_id="b", profile="smoke", split="validation", ce_sum=12.0, tokens=6)
    assert totals.finish() == 2.0
    with pytest.raises(DataError):
        totals.add(example_id="b", profile="smoke", split="validation", ce_sum=2.0, tokens=1)


@pytest.mark.parametrize("change", [{"tokens": 0}, {"tokens": True}, {"ce_sum": math.nan}, {"ce_sum": math.inf},
                                   {"example_id": "b"}, {"profile": "formal"}, {"split": "test"}])
def test_validation_rejects_nonfinite_empty_or_wrong_scope(change):
    totals = ValidationTotals(profile="smoke", split="validation", expected_ids=["a"])
    args = dict(example_id="a", profile="smoke", split="validation", ce_sum=3.0, tokens=2)
    with pytest.raises(DataError):
        totals.add(**(args | change))


def score(**changes):
    return replace(Score("TOY_CPU", "a" * 64, "b" * 64, "c" * 64, "d" * 64, 1, 8, 4.0, 2, 2.0), **changes)


def test_selector_uses_finite_ce_then_actual_step_then_file_hash():
    low = score(ce_sum=2.0, validation_ce=1.0, optimizer_step=2, processed_microsteps=13)
    assert choose_score([score(), low]) == low
    assert choose_score([score(optimizer_step=2), score()]) == score()
    assert choose_score([score(), score(checkpoint_file_sha256="0" * 64)]).checkpoint_file_sha256 == "0" * 64
    for bad in (score(validation_ce=math.nan), score(supervised_tokens=0), score(scope="FORMAL"),
                score(optimizer_step=0), score(parameter_content_sha256="claimed-path")):
        with pytest.raises(DataError):
            choose_score([bad])
    with pytest.raises(DataError):
        choose_score([score(), score(selection_sha256="e" * 64)])


def test_parameter_hash_binds_actual_content_name_shape_and_dtype():
    item = ("table", "float32", (1, 2), bytes(8))
    digest = parameter_content_hash([item])
    for other in [("other", *item[1:]), (item[0], "float16", *item[2:]),
                  (*item[:2], (2, 1), item[3]), (*item[:3], bytes(7) + b"x")]:
        assert parameter_content_hash([other]) != digest
    with pytest.raises(DataError):
        parameter_content_hash([item, item])


def test_default_config_imports_and_no_training_command(tmp_path):
    assert load_config(ROOT / "configs/sft-cpu.v1.json")["training_authorized"] is False
    assert not {"mlx", "mlx_lm", "torch", "transformers"} & set(sys.modules)
    altered = tmp_path / "config.json"
    altered.write_text('{}')
    with pytest.raises(DataError):
        load_config(altered)
    with pytest.raises(SystemExit) as exc:
        main(["--train"])
    assert exc.value.code == 2


def test_cli_failure_is_diagnostic_and_existing_output_untouched(tmp_path):
    output = tmp_path / ".toolalign-local" / "failed"
    flags = [v for key in ("sft-config-path", "public-selection-manifest-path", "selection-path",
             "config-path", "data-manifest-path", "representation-path", "audit-path", "protocol-path")
             for v in ("--" + key, str(tmp_path / "missing"))]
    assert main([*flags, "--output", str(output)]) == 1
    old = (output / "preparation.json").read_bytes()
    assert json.loads(old)["status"] == "FAIL"
    assert main([*flags, "--output", str(output)]) == 1
    assert (output / "preparation.json").read_bytes() == old
