"""Recheck existing PyTorch references only; forbid MLX/model-package imports.

This bounded tensor check is not the historical MLX/PyTorch comparison and does
not call the full compatibility math CLI, which imports MLX and both candidates.
"""

from __future__ import annotations

import importlib.abc
import json
import math
import sys
from pathlib import Path


class ForbidModelImports(importlib.abc.MetaPathFinder):
    roots = {"mlx", "mlx_lm", "mlx_tune", "mlx_lm_lora", "transformers"}

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in self.roots:
            raise AssertionError("CPU-only check attempted a model/MLX package import")
        return None


def main() -> None:
    sys.meta_path.insert(0, ForbidModelImports())
    import numpy as np
    import torch

    from toolalign.training.compatibility.numerical import (
        torch_completion_ce,
        torch_standard_dpo,
    )

    torch.set_num_threads(2)
    raw = np.random.default_rng(42).normal(size=(2, 5, 7)).astype(np.float32)
    ids = torch.tensor([[1, 2, 3, 4, 5, 0], [2, 1, 4, 3, 0, 0]], device="cpu")
    masks = torch.tensor([[0, 0, 1, 1, 1, 0], [0, 0, 0, 1, 0, 0]], device="cpu")
    logits = torch.tensor(raw, requires_grad=True, device="cpu")
    ce = torch_completion_ce(logits, ids, masks)
    ce.backward()

    # Independent scalar log-sum-exp and analytic gradient, using only stdlib math.
    count = int(masks[:, 1:].sum())
    terms, gradient_errors = [], []
    for row in range(2):
        for position in range(5):
            values = raw[row, position].tolist()
            peak = max(values)
            exponentials = [math.exp(value - peak) for value in values]
            normalizer = sum(exponentials)
            target = ids[row, position + 1].item()
            selected = masks[row, position + 1].item()
            if selected:
                terms.append(peak + math.log(normalizer) - values[target])
            for token, exponential in enumerate(exponentials):
                expected = selected * (exponential / normalizer - (token == target)) / count
                gradient_errors.append(abs(logits.grad[row, position, token].item() - expected))
    ce_error = abs(ce.item() - sum(terms) / count)
    altered = logits.detach().clone()
    altered[masks[:, 1:] == 0] = 123.0
    assert abs(torch_completion_ce(altered, ids, masks).item() - ce.item()) < 2e-6

    chosen = torch.tensor([-2.1, -5.2, -7.0], requires_grad=True, device="cpu")
    rejected = torch.tensor([-3.8, -2.4, -6.0], requires_grad=True, device="cpu")
    ref_chosen = torch.tensor([-2.0, -5.0, -8.0], requires_grad=True, device="cpu")
    ref_rejected = torch.tensor([-3.0, -2.5, -7.0], requires_grad=True, device="cpu")
    dpo = torch_standard_dpo(chosen, rejected, ref_chosen, ref_rejected)
    dpo.backward()
    terms, dpo_gradient_errors = [], []
    for index, (c, r, rc, rr) in enumerate(zip(
        chosen.tolist(), rejected.tolist(), ref_chosen.tolist(), ref_rejected.tolist()
    )):
        margin = 0.1 * ((c - r) - (rc - rr))
        terms.append(math.log1p(math.exp(-margin)))
        expected = -0.1 / (1 + math.exp(margin)) / len(chosen)
        dpo_gradient_errors.extend((abs(chosen.grad[index].item() - expected),
                                    abs(rejected.grad[index].item() + expected)))
    assert ref_chosen.grad is None and ref_rejected.grad is None
    dpo_error = abs(dpo.item() - sum(terms) / len(terms))
    ln2 = torch_standard_dpo(chosen, rejected, chosen, rejected).item()
    historical = next(
        run["math"] for run in json.loads(
            (Path(__file__).parent / "P01_RESULTS.json").read_text()
        )["runs"] if run["run_id"] == "p01-math-r2"
    )
    errors = {
        "ce_loss_vs_scalar": ce_error,
        "ce_gradient_max_vs_analytic": max(gradient_errors),
        "dpo_loss_vs_scalar": dpo_error,
        "dpo_gradient_max_vs_analytic": max(dpo_gradient_errors),
        "ln2_abs_error": abs(ln2 - math.log(2)),
        "ce_vs_historical_mlx": abs(ce.item() - historical["ce_loss"]),
        "dpo_vs_historical_mlx": abs(dpo.item() - historical["dpo_loss"]),
    }
    assert max(errors.values()) < 2e-6
    assert all(t.device.type == "cpu" for t in (logits, chosen, rejected, ce, dpo))
    assert not any(name.split(".")[0] in ForbidModelImports.roots for name in sys.modules)
    print(json.dumps({
        "status": "PASS", "device": "PyTorch CPU only", "torch": torch.__version__,
        "dtype": "float32", "atol": 2e-6, "errors": errors,
        "ce_loss": ce.item(), "dpo_loss": dpo.item(), "initial_ln2": ln2,
        "reference_gradients_absent": True, "masked_logits_invariance": True,
        "model_or_mlx_imported": False, "gpu_calibration": "NOT_RUN",
        "full_mlx_torch_math_replay": "NOT_RUN",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
