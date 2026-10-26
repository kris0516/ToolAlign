"""Small CPU checks for the standalone diagnostic; no real checkpoint or model."""

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolalign.model_io import Sequence
from toolalign.training.cuda_sft.protocol import CONFIG_SHA256
from toolalign.training.sft.collator import collate_sequence

PROBE = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                          "reports/experiments/P04_CUDA_RESUME_DIAGNOSTIC.py"))


def test_probe_scope_rejects_extra_work():
    request = {"schema": "toolalign.cuda-sft-resume-diagnostic.v1", "authorized_by": "S1",
        "run_kind": "capacity", "profile": "formal", "source_commit": "1" * 40,
        "training_source_commit": "97637f336df4299a4bfd59b06f9716bb3c104796",
        "config_sha256": CONFIG_SHA256, "repository": "/repo", "output_dir": "/out",
        "lock_root": "/repo", "array_dir": "/arrays", "dependency_lock": "/lock",
        "model_root": "/model", "checkpoint_dir": "/checkpoint", "max_wall_seconds": 300,
        "max_output_bytes": 128 * 1024**2, "max_optimizer_updates": 0, "max_backward_groups": 4,
        "diagnostic_passes": list(PROBE["CASES"]), "validation_every_steps": 2,
        "checkpoint_every_steps": 2}
    assert PROBE["validate_request"](request) == request
    for patch in ({"max_optimizer_updates": 1}, {"max_backward_groups": 5},
                  {"max_wall_seconds": 301}, {"diagnostic_passes": ["arbitrary"]},
                  {"max_output_bytes": 129 * 1024**2}):
        with pytest.raises(ValueError):
            PROBE["validate_request"](request | patch)


def test_probe_captures_expected_gradient_without_update():
    torch = pytest.importorskip("torch")
    torch.set_num_threads(2)

    class Original(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.zeros(4, 4))

        def forward(self, *, input_ids, attention_mask, use_cache):
            return SimpleNamespace(logits=self.weight[input_ids])

    model = Original()
    sequence = Sequence("original", "fixture", (0,), (0, 1), (0, 1, 3), (0, 1, 1), 3)
    batch = collate_sequence(sequence, bucket=8, pad_token_id=0)
    gradients, observation = PROBE["backward_only"](model, [("a", batch), ("b", batch)], device="cpu")
    expected = torch.tensor([[0.125, -0.375, 0.125, 0.125],
                             [0.125, 0.125, 0.125, -0.375], [0., 0., 0., 0.], [0., 0., 0., 0.]])
    torch.testing.assert_close(gradients["weight"], expected, rtol=0, atol=0)
    assert int(torch.count_nonzero(model.weight)) == 0 and len(observation["per_example_loss"]) == 2
    same = PROBE["compare_gradients"](gradients, gradients)
    changed = PROBE["compare_gradients"](gradients, {"weight": gradients["weight"] * 2})
    assert same["exact_tensor_count"] == 1 and same["max_abs"] == 0
    assert changed["exact_tensor_count"] == 0 and changed["relative_l2"] == 1
    assert not PROBE["exact"]({"a": 1, "b": 2}, {"b": 2, "a": 1})
