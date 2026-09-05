import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from toolalign.training.compatibility.core import (
    Budget,
    BudgetExceeded,
    EncodedExample,
    ReferenceIdentity,
    digest,
    padded_batch,
    standard_dpo,
    verify_adapter_metadata,
    verify_reload,
)
from toolalign.training.compatibility.execution import collect_artifacts, preserve_wired_limit
from toolalign.training.compatibility.samples import smoke_samples


def row():
    return EncodedExample((1, 2, 3, 9), (0, 0, 1, 1), 2, 9)


def identity():
    return ReferenceIdentity(
        "a" * 64, "b" * 64, "c" * 64, "d" * 64, "none; bfloat16", "e" * 64, "sft_smoke"
    )


def test_completion_alignment_and_padding():
    ids, masks = padded_batch([row()], 0, 8, pad_to=6)
    assert ids == [[1, 2, 3, 9, 0, 0]]
    assert masks[0][1:] == [0, 1, 1, 0, 0]
    assert sum(masks[0][1:]) == 2


@pytest.mark.parametrize("mask", [(0, 1, 1, 0), (0, 0, 0, 1), (1, 1, 1, 1), (0, 0)])
def test_bad_shift_or_prompt_supervision_rejected(mask):
    with pytest.raises(ValueError):
        replace(row(), completion_mask=mask).validate(8)


@pytest.mark.parametrize(
    "change",
    [
        {"token_ids": (1, 2, 3, 8)},
        {"prompt_length": 0},
        {"prompt_length": 4},
        {"token_ids": (1, 2, 3, -1)},
    ],
)
def test_bad_eos_or_boundary_rejected(change):
    with pytest.raises(ValueError):
        replace(row(), **change).validate(8)


@pytest.mark.parametrize("pad_to", [2, 9])
def test_no_silent_truncation(pad_to):
    with pytest.raises(ValueError):
        padded_batch([row()], 0, 8, pad_to=pad_to)


def test_reference_gate_and_cache_identity():
    ref = identity()
    ref.validate(smoke_only=True)
    with pytest.raises(ValueError):
        ref.validate(smoke_only=False)
    replace(ref, stage="accepted_sft").validate(smoke_only=False)
    with pytest.raises(ValueError):
        replace(ref, stage="original").validate(smoke_only=True)
    with pytest.raises(ValueError):
        replace(ref, adapter_hash="").validate(smoke_only=True)
    with pytest.raises(ValueError):
        ref.assert_unchanged(replace(ref, adapter_hash="f" * 64))
    assert ref.cache_key(row(), row()) != replace(ref, template_hash="f" * 64).cache_key(
        row(), row()
    )
    assert ref.cache_key(row(), row()) != ref.cache_key(
        row(), replace(row(), token_ids=(1, 2, 4, 9))
    )
    assert ref.cache_key(row(), row()) != ref.cache_key(
        row(), replace(row(), completion_mask=(0, 1, 1, 1))
    )


def test_scaling_and_reload_fail_closed():
    expected = {"rank": 8, "scale": 2, "dropout": 0, "keys": ["q", "v"], "num_layers": 28}
    verify_adapter_metadata(expected, dict(expected))
    for key, value in [("scale", 16), ("rank", 16), ("keys", ["q"]), ("num_layers", 16)]:
        with pytest.raises(ValueError):
            verify_adapter_metadata(expected, {**expected, key: value})
    assert verify_reload([0, 1], [0, 1 + 1e-7], 1e-6) < 1e-6
    for values in ([0, 1.1], [0, math.nan], [0]):
        with pytest.raises(ValueError):
            verify_reload([0, 1], values, 1e-6)


def test_dpo_math_gradient_direction():
    assert standard_dpo(-2, -3, -2, -3) == math.log(2)
    assert standard_dpo(-1, -3, -2, -3) < math.log(2)
    assert standard_dpo(-3, -3, -2, -3) > math.log(2)
    eps = 1e-5
    grad_c = (standard_dpo(-2 + eps, -3, -2, -3) - standard_dpo(-2 - eps, -3, -2, -3)) / (2 * eps)
    assert grad_c == pytest.approx(-0.05, abs=1e-10)
    assert math.isfinite(standard_dpo(-1e8, 1e8, 0, 0))
    for beta in (0, -1, math.nan):
        with pytest.raises(ValueError):
            standard_dpo(-2, -3, -2, -3, beta)


@pytest.mark.parametrize(
    "key,value",
    [
        ("max_rss_bytes", 31 * 1024**3),
        ("max_mlx_bytes", 25 * 1024**3),
        ("max_disk_bytes", 21 * 1024**3),
        ("max_microsteps", 0),
        ("max_wall_seconds", float("inf")),
    ],
)
def test_budget_authorization(key, value):
    with pytest.raises(ValueError):
        replace(Budget(), **{key: value}).validate()


@pytest.mark.parametrize(
    "measurement",
    [
        {"wall": 901},
        {"wall": 0, "microsteps": 33},
        {"wall": 0, "processed_tokens": 65537},
        {"wall": 0, "mlx_bytes": 24 * 1024**3 + 1},
        {"wall": 0, "rss_bytes": 30 * 1024**3 + 1},
        {"wall": 0, "swap_growth_bytes": 1024**3 + 1},
        {"wall": 0, "pressure": 2},
    ],
)
def test_stop_thresholds(measurement):
    with pytest.raises(BudgetExceeded):
        Budget().check(**measurement)


def test_never_invokes_wired_setter_and_restores():
    calls = []

    def setter(value):
        calls.append(value)

    module = SimpleNamespace(set_wired_limit=setter)
    events = []
    with pytest.raises(RuntimeError), preserve_wired_limit(module, events):
        module.set_wired_limit(1000)
        raise RuntimeError("training failed")
    assert calls == []
    assert module.set_wired_limit is setter
    assert events == [{"event": "wired_limit_request_suppressed", "requested_bytes": 1000}]


def test_artifact_integrity_and_symlink_escape(tmp_path):
    (tmp_path / "result.json").write_text('{"ok":true}')
    artifacts = collect_artifacts(tmp_path)
    assert artifacts[0]["sha256"] == artifacts[0]["artifact_id"]
    assert artifacts[0]["size_bytes"] == 11
    (tmp_path / "escape").symlink_to(tmp_path.parent)
    with pytest.raises(ValueError):
        collect_artifacts(tmp_path)


def test_original_smoke_cases_are_stable_train_only():
    samples = smoke_samples()
    assert len(samples) == 32 and len({s["id"] for s in samples}) == 32
    assert all(s["split"] == "train" for s in samples)
    assert {s["kind"] for s in samples} == {"call", "observation", "no_tool", "clarify"}
    assert all(s["messages"][-1]["role"] in {"user", "tool"} for s in samples)
    assert digest(samples) == digest(smoke_samples())


def test_fallback_label_mask_is_explicitly_shifted():
    from toolalign.training.compatibility.fallback_probe import fallback_masks

    ids, masks = padded_batch(
        [row(), replace(row(), token_ids=(1, 2, 3, 4, 9), completion_mask=(0, 0, 1, 1, 1))], 0, 8
    )
    shifted = fallback_masks(masks)
    assert shifted == [[0, 1, 1, 0, 0], [0, 1, 1, 1, 0]]
    assert sum(shifted[0][:-1]) == 2
    assert sum(shifted[1][:-1]) == 3
    assert ids[0][4] == 0 and shifted[0][3] == 0


def test_initial_gate_checks_actual_training_loss():
    from toolalign.training.compatibility.core import assert_initial_dpo_loss

    assert_initial_dpo_loss(0.6931471824645996)
    for loss in [0.6945998072624207, 0.679811418056488, 0.9140625, float("nan")]:
        with pytest.raises(ValueError):
            assert_initial_dpo_loss(loss)


def test_checkpoint_timing_uses_real_writer_and_restores(tmp_path):
    from toolalign.training.compatibility.execution import measure_checkpoint_io

    calls = []

    def writer(path, values):
        calls.append(values)
        path.write_text("checkpoint")

    fake = SimpleNamespace(save_safetensors=writer, synchronize=lambda: None)
    events = []
    with measure_checkpoint_io(fake, events, "sft"):
        fake.save_safetensors(tmp_path / "adapter", {"weights": 1})
    assert fake.save_safetensors is writer
    assert calls == [{"weights": 1}]
    assert events[0]["phase"] == "sft"
    assert events[0]["seconds"] >= 0


@pytest.mark.parametrize(
    "change",
    [
        {"max_wall_seconds": 901},
        {"max_microsteps": 121},
        {"max_processed_tokens": 524289},
        {"max_swap_growth_bytes": 2 * 1024**3},
    ],
)
def test_probe_cannot_expand_into_formal_training(change):
    with pytest.raises(ValueError):
        replace(Budget(), **change).validate()
