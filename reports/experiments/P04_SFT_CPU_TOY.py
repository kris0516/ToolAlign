"""Owned, leased, bounded CPU numerical replay of the actual public trainer APIs.

The parent imports no numerical framework. Both success and failure children
retain their actual lease until process exit, following P01's lifetime rule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from P04_SFT_CPU_COMMAND import save

from toolalign.data.common import DataError
from toolalign.runtime.gpu_lock import GPULease, inspect_gpu_lock


def numerics(root, mode, lease):
    import mlx.core as mx

    mx.set_default_device(mx.cpu)
    import mlx.nn as nn
    import mlx.optimizers as optim
    import numpy as np
    import torch
    from mlx.utils import tree_flatten

    from toolalign.model_io import Sequence
    from toolalign.training.compatibility.execution import preserve_wired_limit
    from toolalign.training.sft import collate_sequence
    from toolalign.training.sft.mlx_adapter import (
        OrderedBatches,
        backend,
        completion_loss,
        parameter_hash,
        post_update_score,
        train_toy_segments,
    )
    from toolalign.training.sft.validation import choose_score

    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.set_default_device("cpu")
    torch.manual_seed(42)
    mx.random.seed(42)
    assert mx.default_device() == mx.cpu and torch.get_num_threads() <= 2
    mx, trainer = backend(lease)
    initial = (np.arange(64, dtype=np.float32).reshape(8, 8) - 31.0) / 97.0

    class Table(nn.Module):
        def __init__(self):
            super().__init__()
            self.table = mx.array(initial)

        def __call__(self, ids):
            return self.table[ids]

    cases = []
    for index in range(13):
        p = 2 + index % 3
        prompt = tuple(1 + ((index + j) % 6) for j in range(p))
        completion = tuple(1 + ((index * 3 + j) % 6) for j in range(1 + index % 4))
        joined, eos = prompt + completion, 7
        seq = Sequence("TOY_CPU", "TOY_CPU", prompt, joined, joined + (eos,),
                       (0,) * p + (1,) * (len(completion) + 1), eos)
        cases.append((index + 1, collate_sequence(seq, bucket=16, pad_token_id=0), seq))
    dataset = tuple((rank, batch) for rank, batch, _ in cases)
    save(root / "TOY_CPU-original-cases.json", {"unique_examples": 13,
        "train": [[rank, batch.record()] for rank, batch in dataset],
        "validation": "same 13 original cases solely for parameter/state bookkeeping",
        "initial_table": initial.tolist(), "vocabulary": 8, "parameters": 64})

    def torch_mean(parameter, batch):
        # Independently derive shifted label positions from original prompt/N.
        ids = torch.tensor(batch.sequence_ids, dtype=torch.long, device="cpu")
        losses = torch.nn.functional.cross_entropy(parameter[ids[:-1]], ids[1:], reduction="none")
        start, stop = batch.first_supervised_causal_position, batch.unpadded_length - 1
        return losses[start:stop].sum() / (stop - start)

    def as_inputs(batch):
        return mx.array([batch.sequence_ids], dtype=mx.int32), mx.array([batch.causal_loss_mask], dtype=mx.int32)

    def compare(left, right):
        difference = float(np.max(np.abs(np.asarray(left) - np.asarray(right))))
        assert difference <= 2e-6, difference
        return difference

    metrics, model = [], Table()
    # MLX v0.32.2 array.cpp returns (8, 0) whenever Metal is available,
    # irrespective of the operation stream. DLPack is not execution evidence.
    dlpack_device = tuple(mx.array(0).__dlpack_device__())
    assert dlpack_device == ((8, 0) if mx.metal.is_available() else (1, 0))
    assert mx.default_stream(mx.cpu).device == mx.cpu
    save(root / "device-before-numerics.json", {"default": str(mx.default_device()),
        "operation_stream": str(mx.default_stream(mx.cpu).device), "dlpack": dlpack_device,
        "dlpack_meaning": "hardware interoperability, not operation placement",
        "torch": str(torch.tensor(0).device)})
    assert torch.tensor(0).device.type == "cpu"
    grad_fn = nn.value_and_grad(model, completion_loss)
    for rank, batch, seq in cases:
        value, gradient = grad_fn(model, *as_inputs(batch))
        mx.eval(value, gradient)
        reference = torch.tensor(initial, dtype=torch.float32, requires_grad=True, device="cpu")
        reference_loss = torch_mean(reference, batch)
        reference_loss.backward()
        loss_error = compare(value[0].item(), reference_loss.item())
        grad_error = compare(gradient["table"], reference.grad.numpy())
        unpadded = collate_sequence(seq, bucket=len(seq.sequence_ids), pad_token_id=0)
        short_value, short_gradient = grad_fn(model, *as_inputs(unpadded))
        mx.eval(short_value, short_gradient)
        pad_loss_error = compare(value[0].item(), short_value[0].item())
        pad_grad_error = compare(gradient["table"], short_gradient["table"])
        assert int(value[1].item()) == len(seq.sequence_ids) - len(seq.prompt_ids)
        assert batch.causal_target_ids[batch.last_supervised_causal_position] == 7
        metrics.append({"rank": rank, "loss": value[0].item(), "tokens": int(value[1].item()),
                        "loss_error": loss_error, "gradient_error": grad_error,
                        "right_padding_loss_error": pad_loss_error,
                        "right_padding_gradient_error": pad_grad_error})

    class FixedLogits(nn.Module):
        def __init__(self, logits):
            super().__init__()
            self.logits = logits

        def __call__(self, inputs):
            return self.logits

    batch = dataset[0][1]
    ids, mask = as_inputs(batch)
    logits = model(ids[:, :-1])
    changed = mx.where(mask[:, :, None] == 0, logits + mx.arange(8) * 10, logits)
    ignored_error = compare(completion_loss(FixedLogits(logits), ids, mask)[0].item(),
                            completion_loss(FixedLogits(changed), ids, mask)[0].item())
    default_value, default_tokens = trainer.default_loss(model, ids,
        mx.array([[batch.first_supervised_causal_position + 1, batch.unpadded_length]]))
    assert int(default_tokens.item()) == batch.effective_supervised_targets + 1
    correct_value = completion_loss(model, ids, mask)[0].item()
    assert abs(default_value.item() - correct_value) > 2e-6
    save(root / "TOY_CPU-numerics.json", {"cases": metrics,
        "ignored_prediction_logits_error": ignored_error,
        "upstream_default_padding_negative": {"default_loss": default_value.item(),
            "correct_loss": correct_value, "default_tokens": int(default_tokens.item()),
            "correct_tokens": batch.effective_supervised_targets}})
    events, optimizer = [], optim.SGD(learning_rate=0.07)
    torch_parameter = torch.tensor(initial, dtype=torch.float32, requires_grad=True, device="cpu")
    torch_optimizer = torch.optim.SGD([torch_parameter], lr=0.07)
    torch_states = []
    for start, stop in ((0, 8), (8, 13)):
        torch_optimizer.zero_grad()
        # Equal mean of microstep mean losses, actual divisor 8 then 5.
        objective = torch.stack([torch_mean(torch_parameter, b) for _, b in dataset[start:stop]]).mean()
        objective.backward()
        torch_optimizer.step()
        torch_states.append(torch_parameter.detach().numpy().copy())
    assert sum(v.size for _, v in tree_flatten(model.parameters())) == 64
    if mode == "tail-negative":
        args = trainer.TrainingArgs(batch_size=1, iters=13, grad_accumulation_steps=8,
            steps_per_report=13, steps_per_save=14, max_seq_length=16,
            adapter_file=str(root / "TOY_CPU-upstream-tail.safetensors"))
        iterator = OrderedBatches()
        with mx.stream(mx.cpu), preserve_wired_limit(mx, events):
            trainer.train(model=model, optimizer=optimizer, train_dataset=dataset, val_dataset=None,
                          args=args, loss=completion_loss, iterate_batches=iterator)
        assert iterator.visited == list(range(1, 14)) and int(optimizer.step.item()) == 1
        compare(model.table, torch_states[0])
        tail_error = float(np.max(np.abs(np.array(model.table) - torch_states[1])))
        assert tail_error > 2e-6
        result = {"status": "EXPECTED_NEGATIVE", "scope": "TOY_CPU", "mode": mode,
                  "microsteps_visited": 13, "actual_mlx_optimizer_updates": 1,
                  "reference_optimizer_updates": 2, "lost_tail_microsteps": 5,
                  "final_parameter_error_against_complete_epoch": tail_error}
    else:
        with mx.stream(mx.cpu), preserve_wired_limit(mx, events):
            result = train_toy_segments(lease=lease, model=model, optimizer=optimizer,
                train_dataset=dataset, validation_dataset=dataset, output=root / "TOY_CPU-segments")
        errors = []
        for index, state in enumerate(result["states"]):
            saved = mx.load(str(root / "TOY_CPU-segments" / state["checkpoint"]))
            errors.append(compare(saved["table"], torch_states[index]))
        final_score = result["scores"][-1]
        assert final_score.optimizer_step == 2 and final_score.processed_microsteps == 13
        assert final_score.parameter_content_sha256 == parameter_hash(model)
        checkpoint = root / "TOY_CPU-segments" / result["states"][-1]["checkpoint"]
        reloaded = Table()
        reloaded.load_weights(str(checkpoint))
        assert parameter_hash(reloaded) == parameter_hash(model)
        replay_score = post_update_score(lease=lease, model=reloaded, optimizer=optimizer,
            dataset=dataset, checkpoint=checkpoint, selection_sha256=final_score.selection_sha256,
            processed_microsteps=13, expected_optimizer_step=2)
        assert replay_score == final_score
        # A real final model with the pre-tail checkpoint must fail its binding.
        old_checkpoint = root / "TOY_CPU-segments" / result["states"][0]["checkpoint"]
        try:
            post_update_score(lease=lease, model=model, optimizer=optimizer, dataset=dataset,
                checkpoint=old_checkpoint, selection_sha256=final_score.selection_sha256,
                processed_microsteps=13, expected_optimizer_step=2)
        except DataError as exc:
            assert str(exc) == "checkpoint_parameter_content_mismatch"
        else:
            raise AssertionError("pre-tail checkpoint accepted for post-tail state")
        # Independent Torch token-weighted validation, different from train reduction.
        torch_numerator, denominator = 0.0, 0
        with torch.no_grad():
            for _, b in dataset:
                torch_numerator += torch_mean(torch_parameter, b).item() * b.effective_supervised_targets
                denominator += b.effective_supervised_targets
        validation_error = compare(final_score.validation_ce, torch_numerator / denominator)
        result.update(status="PASS", mode=mode, parameter_errors=errors,
                      torch_validation_error=validation_error,
                      independent_reference_optimizer_updates=2, save_reload_exact=True,
                      wrong_checkpoint_rejected=True, selected=choose_score(result["scores"]).record(),
                      actual_mlx_optimizer_updates=int(optimizer.step.item()))
        result["scores"] = [score.record() for score in result["scores"]]
    result.update(device={"mlx_default": str(mx.default_device()),
                          "mlx_array_dlpack": list(model.table.__dlpack_device__()),
                          "mlx_execution_stream": str(mx.default_stream(mx.cpu).device),
                          "torch": str(torch_parameter.device), "torch_threads": torch.get_num_threads()},
                  wired_limit_events=events, numeric_atol=2e-6,
                  actual_model_parameters=64, unique_original_examples=13,
                  actual_largest_sequence=16, actual_vocabulary=8,
                  parameter_content_sha256=parameter_hash(model),
                  framework_versions={p: __import__("importlib.metadata", fromlist=["version"]).version(p)
                                      for p in ("mlx", "mlx-lm", "torch", "numpy")})
    assert result["device"]["mlx_array_dlpack"] == list(dlpack_device)
    assert mx.default_device() == mx.cpu and mx.default_stream(mx.cpu).device == mx.cpu
    save(root / "TOY_CPU-result.json", result)


def child(root, mode, repository):
    lease = GPULease(task_id="P04-SFT-CPU", worker_alias="T1", run_id=root.name,
                     expected_job="TOY_CPU numeric public API replay", memory_strategy="CPU <=4GiB / <=300s",
                     repository=repository, timeout_seconds=0)
    code = 1
    try:
        lease.__enter__()
        save(root / "lease-acquired.json", {"pid": os.getpid(), "at": datetime.now(timezone.utc).isoformat(),
             "actual_lock": inspect_gpu_lock(repository), "frameworks_loaded_before_lease":
             sorted({n.split(".")[0] for n in sys.modules} & {"mlx", "mlx_lm", "torch"})})
        assert not ({"mlx", "mlx_lm", "torch"} & {n.split(".")[0] for n in sys.modules})
        numerics(root, mode, lease)
        code = 0
    except BaseException as exc:
        traceback.print_exc()
        save(root / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
    finally:
        save(root / "child-terminal.json", {"exit_code": code, "ended_at": datetime.now(timezone.utc).isoformat(),
                                           "lease_held_until_process_exit": lease._handle is not None})
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)


def supervise(args):
    import psutil

    root = args.output.resolve()
    assert ".toolalign-local" in root.parts
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    save(root / "preregistration.json", {"scope": "TOY_CPU", "mode": args.mode, "device": "CPU",
        "wall_seconds_max": 300, "rss_bytes_max": 4 * 1024**3, "optimizer_updates_per_backend_max": 2,
        "examples_max": 13, "sequence_tokens_max": 16, "vocabulary_max": 16,
        "parameter_elements_max": 4096, "atol": 2e-6, "created_at": datetime.now(timezone.utc).isoformat()})
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "child", "--output", str(root),
               "--mode", args.mode, "--repository", str(args.repository.resolve())]
    process, peak, samples, error = None, None, [], None
    start = time.monotonic()
    try:
        with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
            try:
                process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
                own = psutil.Process(process.pid)
                while process.poll() is None:
                    try:
                        rss = own.memory_info().rss
                        peak = max(peak or 0, rss)
                        samples.append({"wall_seconds": time.monotonic() - start, "rss_bytes": rss})
                        if time.monotonic() - start > 300 or rss > 4 * 1024**3:
                            raise TimeoutError("TOY_CPU resource budget exceeded")
                    except psutil.NoSuchProcess:
                        break
                    try:
                        process.wait(timeout=0.1)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    process.wait()
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    actual_exit = None if process is None else process.returncode
    code = 1 if error or actual_exit is None else actual_exit
    result = {"argv": command, "pid": None if process is None else process.pid,
        "actual_child_exit": actual_exit, "exit_code": code, "error": error,
        "wall_seconds": time.monotonic() - start, "peak_rss_bytes": peak, "samples": samples,
        "own_process_reaped": process is not None and process.returncode is not None,
        "own_pid_exists": process is not None and psutil.pid_exists(process.pid),
        "lock_after": inspect_gpu_lock(args.repository),
        "stdout_sha256": hashlib.sha256((root / "stdout.log").read_bytes()).hexdigest(),
        "stderr_sha256": hashlib.sha256((root / "stderr.log").read_bytes()).hexdigest(),
        "ended_at": datetime.now(timezone.utc).isoformat()}
    save(root / "supervision.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "wall_seconds", "peak_rss_bytes", "own_process_reaped", "own_pid_exists")}))
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("supervise", "child"))
    parser.add_argument("--mode", choices=("tail-negative", "segmented"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "child":
        child(args.output, args.mode, args.repository)
    return supervise(args)


if __name__ == "__main__":
    sys.exit(main())
