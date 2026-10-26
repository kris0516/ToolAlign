"""Numerical and native save/resume acceptance on small random CPU models."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("trl", minversion="0.26.2")
torch.set_num_threads(2)

from dpo_cases import (  # noqa: E402
    ATOL,
    ROOT,
    RTOL,
    config,
    expected_tokens,
    manual_loss,
    pair,
    rows,
    tokenizer,
    trainer_at,
)
from transformers.trainer import safe_globals  # noqa: E402

from toolalign.training.cuda_dpo.checkpoint import inspect, validate_native_state  # noqa: E402
from toolalign.training.cuda_sft.engine import make_optimizer  # noqa: E402


def close(left, right):
    if isinstance(left, torch.Tensor):
        torch.testing.assert_close(left, right, atol=ATOL, rtol=RTOL)
    elif isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            close(left[key], right[key])
    elif isinstance(left, (list, tuple)):
        assert len(left) == len(right)
        for a, b in zip(left, right, strict=True):
            close(a, b)
    else:
        assert left == right


def tensor_state(path):
    return torch.load(path, weights_only=True, map_location="cpu")


def test_independent_sum_eos_masks_gradients_and_logits_to_keep(tmp_path):
    trainer, _, expected, _ = trainer_at(tmp_path / "numerics", count=2, stop=1)
    policy, reference = trainer.model, trainer.ref_model
    policy.eval()
    # Exercise a nonzero log-ratio, in addition to the separate ln(2) check.
    with torch.no_grad():
        for name, value in policy.named_parameters():
            if ".lora_B." in name:
                value.add_(0.02)
    oracle_loss, oracle_terms = manual_loss(policy, reference, expected)
    oracle_loss.backward()
    oracle_gradients = {name: p.grad.clone() for name, p in policy.named_parameters() if p.requires_grad}
    policy.zero_grad(set_to_none=True)
    batch = trainer.data_collator.native([trainer.train_dataset[i] for i in range(2)])
    results = []
    for keep in (False, True):
        trainer.use_logits_to_keep = keep
        capture = {}

        def observe(module, args, kwargs, output):
            capture["input_ids"] = args[0].detach().clone()
            capture["attention"] = kwargs["attention_mask"].detach().clone()
            capture["logits"] = output.logits
            output.logits.retain_grad()

        hook = policy.register_forward_hook(observe, with_kwargs=True)
        prediction = trainer.concatenated_forward(policy, batch)
        hook.remove()
        ref_c, ref_r = trainer.compute_ref_log_probs(batch)
        loss = trainer.dpo_loss(prediction["chosen_logps"], prediction["rejected_logps"], ref_c, ref_r)[0].mean()
        loss.backward()
        torch.testing.assert_close(loss.double(), oracle_loss.detach(), atol=ATOL, rtol=RTOL)
        for side_index, side in enumerate(("chosen", "rejected")):
            for index, row in enumerate(expected):
                sequence = row["prompt_input_ids"] + row[side + "_input_ids"]
                observed = side_index * len(expected) + index
                assert capture["input_ids"][observed, :len(sequence)].tolist() == sequence
                assert capture["attention"][observed].tolist() == (
                    [1] * len(sequence) + [0] * (capture["input_ids"].shape[1] - len(sequence)))
                assert row[side + "_input_ids"][-1] == trainer.processing_class.eos_token_id
                terms = oracle_terms[index][side_index].detach()
                torch.testing.assert_close(prediction[side + "_logps"][index].double(),
                                           terms.sum(), atol=ATOL, rtol=RTOL)
                # Gradients directly identify the native supervised positions. Prompt,
                # padding, and the final unlabelled logit must receive exactly zero.
                offset = capture["input_ids"].shape[1] - capture["logits"].shape[1]
                wanted_mask = [len(row["prompt_input_ids"]) - 1 <= position < len(sequence) - 1
                               for position in range(offset, capture["input_ids"].shape[1])]
                actual_mask = capture["logits"].grad[observed].abs().sum(-1).ne(0).tolist()
                assert actual_mask == wanted_mask
                # Independently recover each target log-probability from the actual
                # native logits, including EOS and excluding prompt/pad positions.
                logits = capture["logits"][observed]
                actual_terms = torch.stack([
                    logits[position - 1 - offset, token].double()
                    - torch.logsumexp(logits[position - 1 - offset].double(), 0)
                    for position, token in enumerate(sequence) if position >= len(row["prompt_input_ids"])])
                torch.testing.assert_close(actual_terms, terms, atol=ATOL, rtol=RTOL)
        grads = {name: p.grad.clone() for name, p in policy.named_parameters() if p.requires_grad}
        close(grads, oracle_gradients)
        results.append((prediction, loss.detach(), grads))
        policy.zero_grad(set_to_none=True)
    close(results[0], results[1])


def test_selected_adapter_forward_independence_ln2_and_policy_only_update(tmp_path):
    trainer, _, _, original = trainer_at(tmp_path / "initialization", count=2, stop=1)
    policy, reference = trainer.model, trainer.ref_model
    ids = torch.tensor([[3, 4, 9, 1]])
    policy.eval()
    original.eval()
    with torch.no_grad():
        expected = original(ids).logits
        assert torch.equal(policy(ids).logits, expected)
        assert torch.equal(reference(ids).logits, expected)
    left, right = dict(policy.named_parameters()), dict(reference.named_parameters())
    assert left.keys() == right.keys()
    assert all(left[name].data_ptr() != right[name].data_ptr() for name in left)
    assert all(torch.equal(left[name], right[name]) for name in left)
    batch = trainer.data_collator.native([trainer.train_dataset[0]])
    loss, _ = trainer.get_batch_loss_metrics(policy, batch)
    assert abs(float(loss.detach()) - math.log(2)) < 1e-7
    policy_before = {name: value.detach().clone() for name, value in policy.named_parameters()}
    ref_before = {name: value.detach().clone() for name, value in reference.named_parameters()}
    loss.backward()
    trainer.optimizer.step()
    assert all(torch.equal(ref_before[name], value) for name, value in reference.named_parameters())
    assert all(torch.equal(policy_before[name], value) for name, value in policy.named_parameters()
               if not value.requires_grad)
    changed = [name for name, value in policy.named_parameters()
               if not torch.equal(policy_before[name], value)]
    assert changed and all(".lora_A." in name or ".lora_B." in name for name in changed)


def test_ten_pairs_tail_and_new_process_native_resume(tmp_path):
    runs = {}
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"), HF_HUB_OFFLINE="1",
                       TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1", TOKENIZERS_PARALLELISM="false",
                       OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    for name, stop, resume in (("full", 2, None), ("segment", 1, None),
                               ("resumed", 2, tmp_path / "segment/checkpoint-1")):
        output = tmp_path / name
        command = [sys.executable, str(Path(__file__).with_name("dpo_cases.py")), str(output), str(stop)]
        if resume is not None:
            command.append(str(resume))
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=90)
        (tmp_path / f"{name}.stdout.txt").write_text(result.stdout)
        (tmp_path / f"{name}.stderr.txt").write_text(result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        runs[name] = json.loads((output / "fixture-result.json").read_text())
    ids = [row["preference_id"] for row in rows()]
    assert runs["full"]["consumed"] == ids
    assert runs["segment"]["consumed"] == ids[:8]
    assert runs["resumed"]["consumed"] == ids[8:]
    assert [row["microsteps"] for row in runs["full"]["events"]] == [8, 2]
    assert [row["microsteps"] for row in runs["resumed"]["events"]] == [2]
    for value in runs.values():
        assert value["total_steps"] == 2
        assert value["before"]["policy_base"] == value["after"]["policy_base"]
        assert value["before"]["reference_all"] == value["after"]["reference_all"]
        assert value["before"]["policy_adapter"] != value["after"]["policy_adapter"]
    assert runs["full"]["epoch"] == runs["resumed"]["epoch"] == 1.0
    assert runs["full"]["events"][-1]["data_cursor"] == runs["resumed"]["events"][-1]["data_cursor"] == 10
    from safetensors.torch import load_file

    full, resumed = tmp_path / "full/checkpoint-2", tmp_path / "resumed/checkpoint-2"
    close(load_file(full / "adapter_model.safetensors"), load_file(resumed / "adapter_model.safetensors"))
    close(tensor_state(full / "optimizer.pt"), tensor_state(resumed / "optimizer.pt"))
    close(tensor_state(full / "scheduler.pt"), tensor_state(resumed / "scheduler.pt"))
    with safe_globals():
        a, b = tensor_state(full / "rng_state.pth"), tensor_state(resumed / "rng_state.pth")
    assert a.keys() == b.keys()
    assert a["python"] == b["python"]
    assert a["numpy"][0] == b["numpy"][0] and (a["numpy"][1] == b["numpy"][1]).all()
    assert a["numpy"][2:] == b["numpy"][2:]
    assert torch.equal(a["cpu"], b["cpu"])
    # Independent mean-per-pair gradients also distinguish division by 2 from
    # an incorrect fixed division by 8 in the final update.
    policy, reference, _ = pair()
    optimizer = make_optimizer(policy, config())
    from transformers import get_constant_schedule

    scheduler = get_constant_schedule(optimizer)
    expected = expected_tokens(rows(), tokenizer())
    gradients = []
    for group in (expected[:8], expected[8:]):
        optimizer.zero_grad(set_to_none=True)
        loss, _ = manual_loss(policy, reference, group)
        loss.backward()
        gradients.append({name: p.grad.clone() for name, p in policy.named_parameters() if p.requires_grad})
        optimizer.step()
        scheduler.step()
    actual = tensor_state(tmp_path / "full/gradient-audit.pt")["gradients"]
    close(actual, gradients)
    close(tensor_state(tmp_path / "resumed/gradient-audit.pt")["gradients"], actual[1:])
    close(tensor_state(full / "optimizer.pt"), optimizer.state_dict())
    close(tensor_state(full / "scheduler.pt"), scheduler.state_dict())
    identity = {"synthetic": True, "fixture": "v1"}
    manifest = json.loads((resumed / "dpo-manifest.json").read_text())
    checked = inspect(resumed, identity=identity, expected_sha=manifest["checkpoint_sha256"],
                      pair_count=10, max_bytes=1024**3)
    validate_native_state(resumed, policy, checked)
