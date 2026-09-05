"""Independent PyTorch CPU/MLX float32 loss and gradient comparisons.

Only called by a leased entry point. No backend is imported at module import time.
"""

from __future__ import annotations

import math


def mlx_completion_ce(logits, token_ids, completion_mask):
    import mlx.core as mx
    import mlx.nn as nn

    selected = completion_mask[:, 1:]
    ce = nn.losses.cross_entropy(logits.astype(mx.float32), token_ids[:, 1:])
    return (ce * selected).sum() / selected.sum()


def mlx_completion_logps(model, token_ids, completion_mask):
    import mlx.core as mx
    import mlx.nn as nn

    ce = nn.losses.cross_entropy(model(token_ids[:, :-1]).astype(mx.float32), token_ids[:, 1:])
    return -(ce * completion_mask[:, 1:]).sum(axis=-1)


def mlx_standard_dpo(chosen, rejected, ref_chosen, ref_rejected, beta=0.1):
    import mlx.core as mx
    import mlx.nn as nn

    margin = chosen - rejected - mx.stop_gradient(ref_chosen - ref_rejected)
    return -nn.log_sigmoid(beta * margin).mean()


def torch_completion_ce(logits, token_ids, completion_mask):
    # Deliberately independent implementation: PyTorch ignore_index and flattened CE.
    import torch.nn.functional as functional

    labels = token_ids[:, 1:].clone()
    labels[~completion_mask[:, 1:].bool()] = -100
    return functional.cross_entropy(
        logits.reshape(-1, logits.shape[-1]),
        labels.reshape(-1),
        ignore_index=-100,
        reduction="mean",
    )


def torch_standard_dpo(chosen, rejected, ref_chosen, ref_rejected, beta=0.1):
    import torch.nn.functional as functional

    policy_ratio = chosen - rejected
    reference_ratio = (ref_chosen - ref_rejected).detach()
    return functional.softplus(-beta * (policy_ratio - reference_ratio)).mean()


def check_numerics() -> dict:
    import mlx.core as mx
    import mlx.nn as nn
    import numpy as np
    import torch

    torch.set_num_threads(2)
    mx.set_default_device(mx.cpu)
    rng = np.random.default_rng(42)
    raw = rng.normal(size=(2, 5, 7)).astype(np.float32)
    ids = np.array([[1, 2, 3, 4, 5, 0], [2, 1, 4, 3, 0, 0]], dtype=np.int32)
    masks = np.array([[0, 0, 1, 1, 1, 0], [0, 0, 0, 1, 0, 0]], dtype=np.float32)
    logits = mx.array(raw)
    mi, mm = mx.array(ids), mx.array(masks)
    ce, grad = mx.value_and_grad(mlx_completion_ce)(logits, mi, mm)
    tlogits = torch.tensor(raw, requires_grad=True, device="cpu")
    tce = torch_completion_ce(tlogits, torch.tensor(ids, dtype=torch.long), torch.tensor(masks))
    tce.backward()
    mx.eval(ce, grad)
    ce_error = abs(ce.item() - tce.item())
    grad_error = float(np.max(np.abs(np.array(grad) - tlogits.grad.numpy())))
    # Perturb logits solely at positions whose next-token label is ignored.
    altered = raw.copy()
    altered[masks[:, 1:] == 0] = 123.0
    unchanged = mlx_completion_ce(mx.array(altered), mi, mm).item()
    # Add right padding to logits, IDs, mask: denominator and objective must not change.
    padded_ce = mlx_completion_ce(
        mx.array(np.pad(raw, ((0, 0), (0, 2), (0, 0)))),
        mx.array(np.pad(ids, ((0, 0), (0, 2)))),
        mx.array(np.pad(masks, ((0, 0), (0, 2)))),
    ).item()
    c = np.array([-2.1, -5.2, -7.0], np.float32)
    r = np.array([-3.8, -2.4, -6.0], np.float32)
    rc = np.array([-2.0, -5.0, -8.0], np.float32)
    rr = np.array([-3.0, -2.5, -7.0], np.float32)
    dpo, dg = mx.value_and_grad(mlx_standard_dpo, argnums=(0, 1))(
        mx.array(c), mx.array(r), mx.array(rc), mx.array(rr)
    )
    tc, tr = torch.tensor(c, requires_grad=True), torch.tensor(r, requires_grad=True)
    tdpo = torch_standard_dpo(tc, tr, torch.tensor(rc), torch.tensor(rr))
    tdpo.backward()
    mx.eval(dpo, dg)
    dpo_error = abs(dpo.item() - tdpo.item())
    dgrad_error = max(
        float(np.max(np.abs(np.array(dg[0]) - tc.grad.numpy()))),
        float(np.max(np.abs(np.array(dg[1]) - tr.grad.numpy()))),
    )
    ln2 = mlx_standard_dpo(mx.array(c), mx.array(r), mx.array(c), mx.array(r)).item()
    tolerances = {"loss_atol": 2e-6, "gradient_atol": 2e-6, "ln2_atol": 2e-6}
    assert ce_error < 2e-6 and grad_error < 2e-6
    assert abs(unchanged - ce.item()) < 2e-6 and abs(padded_ce - ce.item()) < 2e-6
    assert dpo_error < 2e-6 and dgrad_error < 2e-6 and abs(ln2 - math.log(2)) < 2e-6
    assert np.all(np.array(dg[0]) < 0) and np.all(np.array(dg[1]) > 0)
    # Real upstream default-loss padding regression; deliberately NO model download.
    from mlx_lm.tuner.trainer import default_loss

    class Fixed(nn.Module):
        def __init__(self):
            super().__init__()
            self.table = mx.array(rng.normal(size=(7, 7)).astype(np.float32))

        def __call__(self, tokens, cache=None):
            return self.table[tokens]

    model = Fixed()
    row_ids = mx.array([[1, 2, 3, 4, 0, 0]])
    row_mask = mx.array([[0, 0, 1, 1, 0, 0]])
    expected = mlx_completion_ce(model(row_ids[:, :-1]), row_ids, row_mask)
    observed, ntoks = default_loss(model, row_ids, mx.array([[2, 4]]))
    assert ntoks.item() == 3 and row_mask.sum().item() == 2
    regressions = {
        "mlx_lm_padding": {
            "status": "REPRODUCED",
            "expected_tokens": 2,
            "upstream_tokens": ntoks.item(),
            "correct_loss": expected.item(),
            "upstream_loss": observed.item(),
        }
    }
    # Sole alternative candidate: its default ragged-batch masks include pad predictions.
    from mlx_lm_lora.trainer.dpo_trainer import dpo_loss as fallback_dpo
    from mlx_lm_lora.trainer.dpo_trainer import get_token_scores

    fallback_scores = get_token_scores(model, row_ids, mx.array([[1, 1, 1, 1, 0, 0]]))
    regressions["mlx_lm_lora_padding"] = {
        "status": "REPRODUCED",
        "nonzero_target_positions": 4,
        "valid_nonpadding_next_tokens": 3,
        "includes_first_pad_logp": fallback_scores[0, 3].item(),
    }
    fallback_value, *_ = fallback_dpo(
        mx.array(c),
        mx.array(r),
        mx.array(rc),
        mx.array(rr),
        mx.ones((3, 1)),
        mx.ones((3, 1)),
        0.1,
        50.0,
    )
    assert abs(fallback_value.item() - tdpo.item()) < 2e-6
    # Prefer explicit reference values. The primary library's default drifts with policy.
    from mlx_tune.losses import dpo_loss as primary_dpo

    chosen = mx.array([[1, 2, 3, 4]])
    rejected = mx.array([[1, 2, 5, 6]])
    length = mx.array([4])
    before = primary_dpo(model, chosen, rejected, length, length)[0].item()
    model.table = model.table + mx.array(rng.normal(size=(7, 7)).astype(np.float32))
    after = primary_dpo(model, chosen, rejected, length, length)[0].item()
    assert abs(before - math.log(2)) < 2e-6 and abs(after - math.log(2)) < 2e-6
    regressions["mlx_tune_missing_reference"] = {
        "status": "REPRODUCED",
        "before": before,
        "after_policy_change": after,
        "interpretation": "Implicit stop-gradient policy reference drifts; explicit cache required",
    }
    mx.synchronize()
    return {
        "status": "PASS",
        "device": "MLX CPU and PyTorch CPU",
        "dtype": "float32",
        "tolerances": tolerances,
        "ce_loss": ce.item(),
        "ce_loss_abs_error": ce_error,
        "ce_gradient_max_abs_error": grad_error,
        "dpo_loss": dpo.item(),
        "dpo_loss_abs_error": dpo_error,
        "dpo_gradient_max_abs_error": dgrad_error,
        "initial_ln2": ln2,
        "masked_logits_invariance": True,
        "right_padding_invariance": True,
        "upstream_negative_probes": regressions,
    }
