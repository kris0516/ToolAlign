"""R1 independent scalar/analytic checks of the existing PyTorch CPU references."""

from __future__ import annotations

import importlib.abc
import json
import math
import random
import sys


class RejectModelImports(importlib.abc.MetaPathFinder):
    forbidden = {"mlx", "mlx_lm", "mlx_lm_lora", "mlx_tune", "transformers"}

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in self.forbidden:
            raise AssertionError("Model/MLX imports are forbidden in this CPU audit")
        return None


def main():
    sys.meta_path.insert(0, RejectModelImports())
    import torch

    from toolalign.training.compatibility.numerical import (
        torch_completion_ce,
        torch_standard_dpo,
    )

    torch.set_num_threads(2)
    rng = random.Random(3701)
    errors = {"ce_loss": 0.0, "ce_gradient": 0.0, "dpo_loss": 0.0, "dpo_gradient": 0.0}
    cases = 0
    for batch in (1, 3):
        for width in (4, 8):
            for vocabulary in (5, 11):
                values = [[[rng.uniform(-2.5, 2.5) for _ in range(vocabulary)]
                           for _ in range(width - 1)] for _ in range(batch)]
                ids = torch.tensor([[rng.randrange(vocabulary) for _ in range(width)]
                                    for _ in range(batch)], device="cpu")
                masks = torch.tensor([
                    [int(1 + row % (width - 2) <= column < width - (row % 2))
                     for column in range(width)] for row in range(batch)
                ], device="cpu")
                logits = torch.tensor(values, dtype=torch.float32, device="cpu", requires_grad=True)
                loss = torch_completion_ce(logits, ids, masks)
                loss.backward()
                selected_count = int(masks.sum())
                expected_loss = 0.0
                for row in range(batch):
                    for position in range(width - 1):
                        numbers = logits.detach()[row, position].tolist()
                        pivot = max(numbers)
                        exponents = [math.exp(number - pivot) for number in numbers]
                        total = math.fsum(exponents)
                        target = int(ids[row, position + 1])
                        selected = int(masks[row, position + 1])
                        expected_loss += selected * (pivot + math.log(total) - numbers[target])
                        for token in range(vocabulary):
                            derivative = selected * (exponents[token] / total - (token == target))
                            derivative /= selected_count
                            errors["ce_gradient"] = max(errors["ce_gradient"], abs(
                                float(logits.grad[row, position, token]) - derivative))
                errors["ce_loss"] = max(errors["ce_loss"], abs(
                    float(loss.detach()) - expected_loss / selected_count))
                changed = logits.detach().clone()
                changed[masks[:, 1:] == 0] = torch.linspace(-100, 100, vocabulary)
                assert float(torch_completion_ce(changed, ids, masks)) == float(loss.detach())
                # Add three right-padding positions, all ignored after next-token shift.
                padded_logits = torch.cat((logits.detach(), torch.zeros(batch, 3, vocabulary)), dim=1)
                padded_ids = torch.cat((ids, torch.zeros(batch, 3, dtype=ids.dtype)), dim=1)
                padded_masks = torch.cat((masks, torch.zeros(batch, 3, dtype=masks.dtype)), dim=1)
                assert abs(float(torch_completion_ce(padded_logits, padded_ids, padded_masks))
                           - float(loss.detach())) < 2e-6
                cases += 1

    for size in (1, 2, 7):
        for beta in (0.05, 0.1, 0.2):
            tensors = [torch.tensor([rng.uniform(-10, -1) for _ in range(size)],
                                   dtype=torch.float32, device="cpu", requires_grad=True)
                       for _ in range(4)]
            c, r, rc, rr = tensors
            loss = torch_standard_dpo(c, r, rc, rr, beta)
            loss.backward()
            assert rc.grad is None and rr.grad is None
            expected_loss = 0.0
            for index, values in enumerate(zip(*(tensor.detach().tolist() for tensor in tensors))):
                chosen, rejected, reference_chosen, reference_rejected = values
                z = beta * ((chosen - rejected) - (reference_chosen - reference_rejected))
                expected_loss += max(-z, 0) + math.log1p(math.exp(-abs(z)))
                derivative = -beta / (1 + math.exp(z)) / size
                errors["dpo_gradient"] = max(errors["dpo_gradient"],
                    abs(float(c.grad[index]) - derivative), abs(float(r.grad[index]) + derivative))
            errors["dpo_loss"] = max(errors["dpo_loss"],
                                    abs(float(loss.detach()) - expected_loss / size))
            alias_c = c.detach().clone().requires_grad_()
            alias_r = r.detach().clone().requires_grad_()
            initial = torch_standard_dpo(alias_c, alias_r, alias_c, alias_r, beta)
            initial.backward()
            assert abs(float(initial.detach()) - math.log(2)) < 2e-6
            assert all(abs(value + beta / (2 * size)) < 2e-6 for value in alias_c.grad.tolist())
            assert all(abs(value - beta / (2 * size)) < 2e-6 for value in alias_r.grad.tolist())
            cases += 1

    assert max(errors.values()) < 2e-6
    assert not any(name.split(".")[0] in RejectModelImports.forbidden for name in sys.modules)
    print(json.dumps({
        "status": "PASS", "cases": cases, "seed": 3701, "torch": torch.__version__,
        "device": "cpu", "dtype": "float32", "threads": torch.get_num_threads(),
        "absolute_tolerance": 2e-6, "maximum_errors": errors,
        "masked_logits_and_padding_invariance": True, "reference_detached": True,
        "same_tensor_initial_reference_retains_policy_gradient": True,
        "mlx_or_model_import": False, "historical_fallback_mlx_reexecution": "NOT_RUN",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
