"""Original tiny PEFT model exercises the production baseline on CPU."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("peft")

from test_cuda_sft_tensors import LONG, SHORT, batch  # noqa: E402
from transformers import Qwen3Config, Qwen3ForCausalLM  # noqa: E402

from toolalign.training.cuda_sft import runtime  # noqa: E402
from toolalign.training.cuda_sft.checkpoint import CheckpointStore, capture, rng_state  # noqa: E402
from toolalign.training.cuda_sft.engine import (  # noqa: E402
    attach_adapter,
    evaluate,
    make_optimizer,
    train_group,
)
from toolalign.training.cuda_sft.protocol import load_protocol  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RECORDS = [("short", batch(SHORT)), ("long", batch(LONG))]
IDS = [name for name, _ in RECORDS]
REQUEST = {"run_id": "original-cpu-baseline", "run_kind": "sft", "profile": "TOY_CPU"}
IDENTITY = {"fixture": "ORIGINAL_CPU_ONLY"}


@pytest.fixture
def tiny():
    config = copy.deepcopy(load_protocol(ROOT))
    config["model"]["layers"] = 1
    torch.manual_seed(9)
    base = Qwen3ForCausalLM(Qwen3Config(vocab_size=4, hidden_size=8, intermediate_size=16,
        num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1, head_dim=4,
        max_position_embeddings=16, attention_dropout=0.0, tie_word_embeddings=True,
        pad_token_id=0, eos_token_id=3, use_cache=False, attn_implementation="sdpa")).to(
            device="cpu", dtype=torch.bfloat16).eval()
    raw = evaluate(base, RECORDS, expected_ids=IDS, profile="TOY_CPU", device="cpu")
    model = attach_adapter(base, config)
    assert sum(p.numel() for p in model.parameters()) <= 4096
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if ".lora_B." in name:
                parameter.fill_(0.25)
    bundle = SimpleNamespace(ids={"validation": IDS}, records=lambda _: iter(RECORDS))
    return model, config, raw, bundle


def modes(model):
    return {name: module.training for name, module in model.named_modules()}


def test_evaluate_preserves_loaded_peft_module_modes(tiny):
    model, _, _, _ = tiny
    before = modes(model)
    # from_pretrained() leaves the base in eval mode; PEFT's new wrapper is training.
    assert set(before.values()) == {True, False}
    evaluate(model, RECORDS, expected_ids=IDS, profile="TOY_CPU", device="cpu")
    assert modes(model) == before


def test_original_baseline_matches_raw_model_and_preserves_training_state(tmp_path, tiny):
    model, config, raw, bundle = tiny
    active = evaluate(model, RECORDS, expected_ids=IDS, profile="TOY_CPU", device="cpu")
    assert abs(active["validation_ce"] - raw["validation_ce"]) > 1e-5
    with model.disable_adapter():
        disabled = evaluate(model, RECORDS, expected_ids=IDS, profile="TOY_CPU", device="cpu")
    assert disabled == raw
    output = tmp_path / "output"
    output.mkdir()
    store = CheckpointStore(local=output / "checkpoints", persistent=tmp_path / "copy",
                            identity=IDENTITY, max_bytes=4 * 1024**2)
    optimizer = make_optimizer(model, config)
    control = copy.deepcopy(model)
    control_optimizer = make_optimizer(control, config)
    weights = {name: value.detach().clone() for name, value in model.state_dict().items()}
    flags = {name: value.requires_grad for name, value in model.named_parameters()}
    training_modes = modes(model)
    rng_before = runtime.rng_hash(rng_state(device="cpu"))
    optimizer_before = copy.deepcopy(optimizer.state_dict())
    reference = runtime.original_validation(model, bundle, request=REQUEST, identity=IDENTITY,
                                            output_dir=output, device="cpu")
    assert reference == {"status": "PASS", "file": "original-validation.json"}
    record = json.loads((output / reference["file"]).read_text())
    assert {key: record[key] for key in raw} == raw
    assert record["supervised_tokens"] == 7 and record["examples"] == 2
    assert record["profile"] == "TOY_CPU" and record["identity"] == IDENTITY
    assert record["optimizer_step"] == record["data_cursor"] == 0
    assert record["adapter_disabled"] is True and record["run_id"] == REQUEST["run_id"]
    assert model.get_model_status().enabled is True
    assert modes(model) == training_modes
    assert {name: value.requires_grad for name, value in model.named_parameters()} == flags
    assert all(torch.equal(value, weights[name]) for name, value in model.state_dict().items())
    assert all(parameter.grad is None for parameter in model.parameters())
    assert optimizer.state_dict() == optimizer_before
    assert runtime.rng_hash(rng_state(device="cpu")) == rng_before
    assert store.best is None and store.records == []
    assert list((output / "checkpoints").iterdir()) == []

    # The next real tiny update matches a control without the baseline call.
    actual = train_group(model, optimizer, RECORDS, device="cpu")
    expected = train_group(control, control_optimizer, RECORDS, device="cpu")
    assert actual == expected
    assert all(torch.equal(value, control.state_dict()[name]) for name, value in model.state_dict().items())
    state = capture(model, optimizer, step=1, cursor=2, identity=IDENTITY, device="cpu")
    # Even a synthetic score worse than step0 is eligible; step0 is not a candidate.
    store.save(state, validation_ce=record["validation_ce"] + 1)
    assert store.best["optimizer_step"] == 1
    assert [entry["optimizer_step"] for entry in store.records] == [1]


@pytest.mark.parametrize("patch,reason", [({"run_kind": "capacity"}, "capacity_run"),
                                         ({"resume_from": "/fixture/step2"}, "resume_segment")])
def test_capacity_and_resume_do_not_evaluate_original(tmp_path, patch, reason):
    # No model or array access is possible on these skipped branches.
    result = runtime.original_validation(None, None, request=REQUEST | patch, identity=IDENTITY,
                                         output_dir=tmp_path, device="cpu")
    assert result == {"status": "NOT_RUN", "reason": reason}
    assert list(tmp_path.iterdir()) == []


def test_failed_original_validation_restores_adapter_and_modes_without_result(tmp_path, tiny):
    model, _, _, bundle = tiny
    before_modes = modes(model)
    before_flags = {name: value.requires_grad for name, value in model.named_parameters()}
    before_rng = runtime.rng_hash(rng_state(device="cpu"))
    bundle.records = lambda _: iter(RECORDS[:1])
    with pytest.raises(ValueError, match="incomplete_validation"):
        runtime.original_validation(model, bundle, request=REQUEST, identity=IDENTITY,
                                    output_dir=tmp_path, device="cpu")
    assert model.get_model_status().enabled is True
    assert modes(model) == before_modes
    assert {name: value.requires_grad for name, value in model.named_parameters()} == before_flags
    assert runtime.rng_hash(rng_state(device="cpu")) == before_rng
    assert list(tmp_path.iterdir()) == []
