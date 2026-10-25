"""Original <=4096-parameter CPU fixtures; each trajectory has at most 3 updates."""

from __future__ import annotations

import copy
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
torch.set_num_threads(2)
torch.set_num_interop_threads(2)

from toolalign.model_io import Sequence  # noqa: E402
from toolalign.training.cuda_sft.checkpoint import (  # noqa: E402
    CheckpointStore,
    capture,
    deserialize,
    inspect_checkpoint,
    parameter_hash,
    restore,
    serialize,
)
from toolalign.training.cuda_sft.engine import (  # noqa: E402
    attach_adapter,
    completion_ce,
    evaluate,
    groups,
    make_optimizer,
    train_group,
)
from toolalign.training.cuda_sft.protocol import load_protocol  # noqa: E402
from toolalign.training.cuda_sft.runtime import require_cuda, rng_hash  # noqa: E402
from toolalign.training.sft.collator import collate_sequence  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASE = [[0.2, -0.1, 0.5, 0.1], [-0.2, 0.4, 0.1, 0.6],
        [0.3, -0.4, 0.7, 0.2], [-0.1, 0.8, 0.2, 0.1]]
SHORT = ((0, 1), (2,))
LONG = ((0,), (1, 2, 1, 2))


def batch(parts):
    prompt, completion = parts
    joined = prompt + completion
    sequence = Sequence("original", "fixture", prompt, joined, joined + (3,),
                        (0,) * len(prompt) + (1,) * (len(completion) + 1), 3)
    return collate_sequence(sequence, bucket=8, pad_token_id=0)


class Tiny(torch.nn.Module):
    def __init__(self, *, stochastic=False):
        super().__init__()
        self.base = torch.nn.Parameter(torch.tensor(BASE), requires_grad=False)
        self.adapter = torch.nn.Parameter(torch.zeros((4, 4)))
        self.stochastic = stochastic
        assert sum(p.numel() for p in self.parameters()) <= 4096

    def forward(self, *, input_ids, attention_mask, use_cache):
        assert input_ids.device.type == "cpu" and input_ids.shape[1] <= 16
        assert attention_mask.shape == input_ids.shape and use_cache is False
        logits = (self.base + self.adapter)[input_ids]
        if self.stochastic and self.training:
            noise = random.random() + float(np.random.random())
            logits = torch.nn.functional.dropout(logits, p=0.2, training=True) * (0.8 + noise / 5)
        return SimpleNamespace(logits=logits)


def manual(parts):
    """Independent scalar CE and gradient from original prompt/completion tokens."""
    prompt, completion = parts
    sequence = prompt + completion + (3,)
    total, gradient = 0.0, [[0.0] * 4 for _ in range(4)]
    tokens = len(completion) + 1
    for index in range(len(prompt) - 1, len(sequence) - 1):
        source, target = sequence[index], sequence[index + 1]
        values = BASE[source]
        denominator = sum(math.exp(v) for v in values)
        total += math.log(denominator) - values[target]
        for col, value in enumerate(values):
            gradient[source][col] += (math.exp(value) / denominator - (col == target)) / tokens
    return total, torch.tensor(gradient)


def test_independent_ce_gradient_mask_eos_right_pad_and_single_shift():
    model = Tiny()
    for parts in (SHORT, LONG):
        model.zero_grad(set_to_none=True)
        total, count = completion_ce(model, batch(parts), device="cpu")
        expected_ce, expected_gradient = manual(parts)
        assert count == len(parts[1]) + 1
        # The production reduction is FP32; compare the independent FP64 sum
        # within two representable FP32 increments, including input rounding.
        assert float(total.detach()) == pytest.approx(expected_ce, rel=0,
                                                       abs=2 * float(np.spacing(np.float32(expected_ce))))
        (total / count).backward()
        torch.testing.assert_close(model.adapter.grad, expected_gradient, atol=3e-8, rtol=1e-6)
        assert model.base.grad is None
    # Training weights examples equally; validation weights supervised tokens.
    model.zero_grad(set_to_none=True)
    losses = [completion_ce(model, batch(parts), device="cpu") for parts in (SHORT, LONG)]
    equal = sum(total / count for total, count in losses) / 2
    token_weighted = sum(total for total, _ in losses) / sum(count for _, count in losses)
    assert abs(float((equal - token_weighted).detach())) > 1e-3
    equal.backward()
    torch.testing.assert_close(model.adapter.grad, (manual(SHORT)[1] + manual(LONG)[1]) / 2)
    validation = evaluate(model, [("a", batch(SHORT)), ("b", batch(LONG))],
                          expected_ids=["a", "b"], profile="TOY_CPU", device="cpu")
    assert validation["validation_ce"] == pytest.approx(float(token_weighted.detach()), abs=1e-7)
    with pytest.raises(ValueError, match="coverage_or_order"):
        evaluate(model, [("b", batch(LONG)), ("a", batch(SHORT))], expected_ids=["a", "b"],
                 profile="TOY_CPU", device="cpu")


@pytest.mark.parametrize("tail", [7, 2])
def test_tail_uses_actual_divisor_and_standard_first_adam_update(tail):
    model = Tiny()
    config = load_protocol(ROOT)
    optimizer = make_optimizer(model, config)
    original = model.base.detach().clone()
    parts = [SHORT if i % 2 == 0 else LONG for i in range(tail)]
    record = train_group(model, optimizer, [(str(i), batch(p)) for i, p in enumerate(parts)], device="cpu")
    expected_grad = sum(manual(p)[1] for p in parts) / tail
    expected_parameter = -1e-4 * expected_grad / (expected_grad.abs() + 1e-8)
    torch.testing.assert_close(model.adapter, expected_parameter, atol=3e-10, rtol=2e-5)
    torch.testing.assert_close(optimizer.state[model.adapter]["exp_avg"], expected_grad * 0.1,
                               atol=5e-9, rtol=2e-6)
    assert record["microsteps"] == tail and torch.equal(model.base, original)
    assert [len(g) for g in groups([(str(i), batch(SHORT)) for i in range(8 + tail)])] == [8, tail]


def test_official_peft_qwen_tiny_updates_adapter_and_freezes_base():
    pytest.importorskip("peft")
    from transformers import Qwen3Config, Qwen3ForCausalLM

    config = copy.deepcopy(load_protocol(ROOT))
    config["model"]["layers"] = 1  # Original tensor fixture, never the real loader.
    torch.manual_seed(9)
    base = Qwen3ForCausalLM(Qwen3Config(vocab_size=4, hidden_size=8, intermediate_size=16,
        num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1, head_dim=4,
        max_position_embeddings=16, attention_dropout=0.0, tie_word_embeddings=True,
        pad_token_id=0, eos_token_id=3, use_cache=False, attn_implementation="sdpa")).to(
            device="cpu", dtype=torch.bfloat16)
    model = attach_adapter(base, config)
    assert sum(p.numel() for p in model.parameters()) <= 4096
    frozen = {n: p.detach().clone() for n, p in model.named_parameters() if not p.requires_grad}
    frozen_hash = parameter_hash(model, trainable=False)
    before = parameter_hash(model)
    assert model.is_gradient_checkpointing and model.config.use_cache is False
    assert model.config._attn_implementation == "sdpa"
    assert all(int(torch.count_nonzero(p)) == 0 for n, p in model.named_parameters() if ".lora_B." in n)
    assert all(p.dtype == torch.float32 for p in model.parameters() if p.requires_grad)
    optimizer = make_optimizer(model, config)
    result = train_group(model, optimizer, [("tiny", batch(SHORT))], device="cpu")
    assert math.isfinite(result["loss"]) and parameter_hash(model) != before
    assert all(torch.equal(p, frozen[n]) for n, p in model.named_parameters() if n in frozen)
    assert parameter_hash(model, trainable=False) == frozen_hash


def test_no_cuda_explicitly_fails():
    assert not torch.cuda.is_available(), "This bounded fixture requires the authorized CPU environment"
    with pytest.raises(ValueError, match="CUDA_unavailable_no_fallback"):
        require_cuda()


def test_incomplete_optimizer_state_is_rejected():
    model = Tiny()
    optimizer = make_optimizer(model, load_protocol(ROOT))
    identity = {"fixture": "incomplete-original-checkpoint"}
    # A claimed completed step with fresh (empty) Adam moments must not resume.
    state = capture(model, optimizer, step=1, cursor=8, identity=identity, device="cpu")
    with pytest.raises(ValueError, match="incomplete_optimizer_state"):
        deserialize(serialize(state), identity=identity, train_count=18)


def trajectory(root, resume_path=None):
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    config = load_protocol(ROOT)
    model = Tiny(stochastic=True)
    optimizer = make_optimizer(model, config)
    identity = {"fixture": "ORIGINAL_CPU_ONLY", "parameters": 32, "max_sequence": 8}
    store = CheckpointStore(local=root / "local", persistent=root / "copy", identity=identity,
                            max_bytes=8 * 1024**2)
    step, cursor = 0, 0
    if resume_path:
        manifest, contents = inspect_checkpoint(resume_path, identity=identity)
        state = deserialize(contents["state.pt"], identity=identity, train_count=18, manifest=manifest)
        store.seed(manifest, contents)
        # Prove all RNGs are replaced by restoration after unrelated process work.
        random.random(), np.random.random(), torch.rand(7)
        step, cursor = restore(state, model, optimizer, device="cpu")
    records = [(str(i), batch(SHORT if i % 2 == 0 else LONG)) for i in range(18)]
    results = []
    for group in groups(records, cursor=cursor):
        metric = train_group(model, optimizer, group, device="cpu")
        step, cursor = step + 1, cursor + len(group)
        state = capture(model, optimizer, step=step, cursor=cursor, identity=identity, device="cpu")
        # Fixed original scores exercise carrying a historical best through rollback.
        path = store.save(state, validation_ce={1: 0.1, 2: 0.3, 3: 0.05}[step])
        results.append({"step": step, "cursor": cursor, "losses": metric["per_example_loss"],
                        "adapter": parameter_hash(model), "rng": rng_hash(state), "path": str(path)})
    (root / "result.json").write_text(json.dumps(results))


def test_fresh_process_resume_matches_loss_parameters_all_rng_and_selection(tmp_path):
    continuous, resumed = tmp_path / "continuous", tmp_path / "resumed"
    continuous.mkdir()
    resumed.mkdir()
    environment = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                   "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"}
    subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "trajectory", str(continuous)],
                   check=True, env=environment, timeout=300)
    baseline = json.loads((continuous / "result.json").read_bytes())
    checkpoint = baseline[1]["path"]
    subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "trajectory", str(resumed), checkpoint],
                   check=True, env=environment, timeout=300)
    recovery = json.loads((resumed / "result.json").read_bytes())
    assert [{k: v for k, v in r.items() if k != "path"} for r in recovery] == [
        {k: v for k, v in baseline[2].items() if k != "path"}]
    for root in (continuous, resumed):
        local = json.loads((root / "local/index.json").read_bytes())
        copied = json.loads((root / "copy/index.json").read_bytes())
        assert local == copied and local["best"]["optimizer_step"] == 3
        assert len(local["retained"]) <= 3
        for record in local["retained"]:
            name = f"step-{record['optimizer_step']:06d}-{record['checkpoint_sha256'][:12]}"
            inspect_checkpoint(root / "copy" / name, identity=local["identity"],
                               expected_sha=record["checkpoint_sha256"])
    # Complete-file integrity and lineage checks happen before tensor restoration.
    manifest, contents = inspect_checkpoint(checkpoint, identity={"fixture": "ORIGINAL_CPU_ONLY",
                                                                "parameters": 32, "max_sequence": 8})
    with pytest.raises(ValueError, match="identity_mismatch"):
        deserialize(contents["state.pt"], identity={"wrong": True}, train_count=18)
    with pytest.raises(ValueError, match="checkpoint_cursor"):
        deserialize(contents["state.pt"], identity=manifest["identity"], train_count=2)
    with pytest.raises(ValueError, match="checkpoint_manifest_state_mismatch"):
        deserialize(contents["state.pt"], identity=manifest["identity"], train_count=18,
                    manifest=manifest | {"validation_ce": 999.0})
    with pytest.raises(ValueError, match="checkpoint_selection_mismatch"):
        deserialize(contents["state.pt"], identity=manifest["identity"], train_count=18,
                    manifest=manifest | {"best": manifest["best"] | {"validation_ce": 999.0}})
    state = deserialize(contents["state.pt"], identity=manifest["identity"], train_count=18, manifest=manifest)
    for key, invalid in (("python_rng", ()), ("numpy_rng", ()),
                         ("torch_cpu_rng", torch.zeros(2, dtype=torch.uint8)),
                         ("torch_cuda_rng", [torch.zeros(2, dtype=torch.uint8)])):
        with pytest.raises(ValueError, match="invalid_rng_state"):
            deserialize(serialize(state | {key: invalid}), identity=manifest["identity"], train_count=18)
    # Re-score the three actual original states: a tie keeps the earliest best;
    # a later worse state keeps best/last/the most recent distinct scored rollback.
    first = deserialize(contents["best.pt"], identity=manifest["identity"], train_count=18)
    final_manifest, final_contents = inspect_checkpoint(baseline[2]["path"], identity=manifest["identity"])
    final = deserialize(final_contents["state.pt"], identity=manifest["identity"],
                        train_count=18, manifest=final_manifest)
    selection = CheckpointStore(local=tmp_path / "selection", persistent=tmp_path / "selection-copy",
                                identity=manifest["identity"], max_bytes=8 * 1024**2)
    for original, score in ((first, 1.0), (state, 1.0), (final, 2.0)):
        selection.save(original, validation_ce=score)
    assert selection.best["optimizer_step"] == 1
    assert [r["optimizer_step"] for r in selection.records] == [1, 2, 3]


if __name__ == "__main__":
    assert sys.argv[1] == "trajectory"
    trajectory(Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
