"""One owned, leased CPU child: independent gradients and a single entry counterexample.

No optimizer step, replacement train loop, pretrained data, or checkpoint output
is part of the reference. The upstream call must fail before entering its loop.
All raw arrays, tracebacks, device evidence, and process records remain private.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from toolalign.runtime.gpu_lock import GPULease, inspect_gpu_lock


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def numeric(root, lease):
    import mlx.core as mx

    mx.set_default_device(mx.cpu)
    import torch

    torch.set_default_device("cpu")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    import mlx.nn as nn
    import mlx.optimizers as optim
    import numpy as np
    from mlx.utils import tree_flatten

    from toolalign.model_io import Sequence
    from toolalign.training.compatibility.execution import preserve_wired_limit
    from toolalign.training.sft import collate_sequence
    from toolalign.training.sft.mlx_adapter import (
        OrderedBatches,
        backend,
        completion_loss,
        parameter_hash,
    )

    assert mx.default_device() == mx.cpu and mx.default_stream(mx.cpu).device == mx.cpu
    assert torch.get_default_device().type == "cpu" and torch.get_num_threads() == 2
    mx, trainer = backend(lease)
    versions = {name: importlib.metadata.version(name) for name in ("mlx", "mlx-lm", "torch", "numpy")}
    assert versions["mlx"] == "0.32.2" and versions["mlx-lm"] == "0.31.3" and versions["torch"] == "2.14.0"
    initial = np.asarray([[(((row * 7 + column * 3) % 11) - 5) / 5
                           for column in range(4)] for row in range(4)], dtype=np.float32)

    class Table(nn.Module):
        def __init__(self):
            super().__init__()
            self.table = mx.array(initial, dtype=mx.float32)

        def __call__(self, inputs):
            return self.table[inputs]

    class FixedLogits(nn.Module):
        def __init__(self, logits):
            super().__init__()
            self.logits = logits

        def __call__(self, inputs):
            return self.logits

    def error(left, right):
        value = float(np.max(np.abs(np.asarray(left) - np.asarray(right))))
        assert np.isfinite(value) and value <= 2e-6, value
        return value

    cases = []
    for number in range(13):
        prompt = tuple(1 + (number + offset) % 3 for offset in range(1 + number % 3))
        completion = tuple(1 + (number + offset) % 2 for offset in range(1 + (number // 3) % 3))
        joined = prompt + completion
        sequence = Sequence("original R1 prompt", "original R1 completion", prompt, joined,
                            joined + (3,), (0,) * len(prompt) + (1,) * (len(completion) + 1), 3)
        cases.append((number + 1, sequence, collate_sequence(sequence, bucket=8, pad_token_id=0)))
    save(root / "original-cases.json", {"initial_parameters": initial.tolist(),
                                        "vocabulary": 4, "parameter_elements": 16,
                                        "cases": [{"rank": rank, "prompt_ids": list(seq.prompt_ids),
                                                   "original_unpadded_ids": list(seq.sequence_ids),
                                                   "batch": batch.record()} for rank, seq, batch in cases]})
    model = Table()
    assert sum(value.size for _, value in tree_flatten(model.parameters())) == 16
    gradient = nn.value_and_grad(model, completion_loss)
    device = {"mlx_default": str(mx.default_device()), "mlx_stream": str(mx.default_stream(mx.cpu).device),
              "torch_default": str(torch.get_default_device()), "torch_threads": torch.get_num_threads(),
              "torch_interop_threads": torch.get_num_interop_threads(), "framework_versions": versions,
              "cpu_device_info": dict(mx.device_info()), "metal_available": mx.metal.is_available()}
    save(root / "device.json", device)
    metrics = []
    with mx.stream(mx.cpu):
        for rank, sequence, batch in cases:
            inputs = mx.array([batch.sequence_ids], dtype=mx.int32)
            mask = mx.array([batch.causal_loss_mask], dtype=mx.int32)
            value, grad = gradient(model, inputs, mask)
            mx.eval(value, grad)
            # The reference uses original unpadded IDs and prompt length, not the
            # candidate's shifted mask, target arrays, or reported denominator.
            reference = torch.tensor(initial, dtype=torch.float32, requires_grad=True, device="cpu")
            ids = torch.tensor(sequence.sequence_ids, dtype=torch.long, device="cpu")
            token_ce = torch.nn.functional.cross_entropy(reference[ids[:-1]], ids[1:], reduction="none")
            first, stop = len(sequence.prompt_ids) - 1, len(sequence.sequence_ids) - 1
            reference_loss = token_ce[first:stop].mean()
            reference_loss.backward()
            assert reference.device.type == ids.device.type == "cpu"
            short = collate_sequence(sequence, bucket=len(sequence.sequence_ids), pad_token_id=0)
            short_value, short_grad = gradient(model, mx.array([short.sequence_ids], dtype=mx.int32),
                                               mx.array([short.causal_loss_mask], dtype=mx.int32))
            mx.eval(short_value, short_grad)
            assert int(value[1].item()) == stop - first
            assert list(batch.causal_target_ids[first:stop]).count(3) == 1
            metrics.append({"rank": rank, "supervised_positions": list(range(first, stop)),
                            "supervised_tokens": stop - first, "mlx_tokens": int(value[1].item()),
                            "mlx_loss": float(value[0].item()), "torch_loss": float(reference_loss.item()),
                            "torch_token_ce": token_ce.detach().numpy().tolist(),
                            "mlx_gradient": np.array(grad["table"]).tolist(),
                            "torch_gradient": reference.grad.numpy().tolist(),
                            "unpadded_mlx_gradient": np.array(short_grad["table"]).tolist(),
                            "loss_error": error(value[0].item(), reference_loss.item()),
                            "gradient_error": error(np.array(grad["table"]), reference.grad.numpy()),
                            "padding_loss_error": error(value[0].item(), short_value[0].item()),
                            "padding_gradient_error": error(np.array(grad["table"]), np.array(short_grad["table"]))})

        _, sequence, batch = cases[2]
        inputs = mx.array([batch.sequence_ids], dtype=mx.int32)
        mask = mx.array([batch.causal_loss_mask], dtype=mx.int32)
        logits = model(inputs[:, :-1])
        changed = mx.where(mask[:, :, None] == 0, logits + mx.array([7., -9., 12., -15.]), logits)
        original_loss, _ = completion_loss(FixedLogits(logits), inputs, mask)
        changed_loss, _ = completion_loss(FixedLogits(changed), inputs, mask)
        mx.eval(original_loss, changed_loss, logits, changed)
        ignored_error = error(original_loss.item(), changed_loss.item())
        default_loss, default_tokens = trainer.default_loss(
            model, inputs, mx.array([[len(sequence.prompt_ids), len(sequence.sequence_ids)]], dtype=mx.int32))
        mx.eval(default_loss, default_tokens)
        assert int(default_tokens.item()) == batch.effective_supervised_targets + 1
        assert abs(default_loss.item() - original_loss.item()) > 2e-6
        numbers = {"scope": "TOY_CPU", "unique_original_cases": 13, "atol": 2e-6,
                   "vocabulary": 4, "model_parameters": 16, "largest_bucket": 8, "cases": metrics,
                   "ignored_logits_before": np.array(logits).tolist(), "ignored_logits_after": np.array(changed).tolist(),
                   "ignored_loss_before": float(original_loss.item()), "ignored_loss_after": float(changed_loss.item()),
                   "ignored_loss_error": ignored_error,
                   "default_loss_negative": {"loss": float(default_loss.item()), "tokens": int(default_tokens.item()),
                                               "correct_loss": float(original_loss.item()),
                                               "correct_tokens": batch.effective_supervised_targets},
                   "max_errors": {name: max(item[name] for item in metrics) for name in
                                  ("loss_error", "gradient_error", "padding_loss_error", "padding_gradient_error")},
                   "torch_optimizer_updates": 0, "mlx_optimizer_updates": 0}
        save(root / "numbers.json", numbers)
        optimizer = optim.SGD(learning_rate=0.03)
        iterator = OrderedBatches()
        dataset = tuple((rank, batch) for rank, _, batch in cases)
        before = parameter_hash(model)
        assert int(optimizer.step.item()) == 0
        # Stop without any call if the exact prerequisite for the reported entry
        # failure has changed. Do not explore an unexpectedly working train path.
        assert mx.metal.is_available() and "max_recommended_working_set_size" not in mx.device_info()
        checkpoint = root / "NOT_RUN-entry-checkpoint.safetensors"
        args = trainer.TrainingArgs(batch_size=1, iters=13, grad_accumulation_steps=8,
                                    steps_per_report=13, steps_per_eval=14, steps_per_save=14,
                                    max_seq_length=8, adapter_file=str(checkpoint), grad_checkpoint=False)
        events = []
        original_setter = mx.set_wired_limit
        try:
            with preserve_wired_limit(mx, events):
                trainer.train(model=model, optimizer=optimizer, train_dataset=dataset, val_dataset=None,
                              args=args, loss=completion_loss, iterate_batches=iterator)
        except KeyError as exc:
            assert exc.args == ("max_recommended_working_set_size",)
            trace = traceback.format_exc()
            with (root / "entry-traceback.log").open("x") as stream:
                stream.write(trace)
            assert "trainer.py\", line 229" in trace
            entry = {"status": "EXPECTED_UPSTREAM_CPU_ENTRY_BLOCK", "exception_type": type(exc).__name__,
                     "exception_args": list(exc.args), "trainer_calls": 1,
                     "trainer_source": trainer.train.__code__.co_filename,
                     "trainer_source_sha256": sha(trainer.train.__code__.co_filename),
                     "iterator_visited": iterator.visited, "optimizer_step": int(optimizer.step.item()),
                     "parameter_hash_before": before, "parameter_hash_after": parameter_hash(model),
                     "wired_limit_events": events, "checkpoint_created": checkpoint.exists(),
                     "wired_setter_restored": mx.set_wired_limit is original_setter}
            assert entry["optimizer_step"] == 0 and entry["iterator_visited"] == []
            assert entry["parameter_hash_after"] == before and events == [] and not checkpoint.exists()
            assert entry["wired_setter_restored"]
            save(root / "entry.json", entry)
        else:
            raise AssertionError("the previously blocked entry unexpectedly returned; no retry authorized")
    assert not list(root.glob("*.safetensors"))
    return {"status": "PASS_NUMERICS_WITH_EXPECTED_ENTRY_BLOCK", "numerics": "PASS",
            "native_trainer": "BLOCKED_UPSTREAM_CPU_ENTRY", "native_updates": 0,
            "checkpoint_files": 0, "native_evaluate": "NOT_RUN", "tail_updates": "NOT_RUN",
            "numbers_sha256": sha(root / "numbers.json"), "entry_sha256": sha(root / "entry.json")}


def child(args):
    root = args.output.resolve()
    lease = GPULease(task_id="P04-SFT-CPU-R1", worker_alias="R1", run_id=root.name,
                     expected_job="single original CPU gradient and entry counterexample",
                     memory_strategy="CPU / RSS <=4GiB / wall <=300s", repository=args.repository,
                     timeout_seconds=0)
    code, result = 1, None
    try:
        frameworks = sorted({name.split(".")[0] for name in sys.modules} & {"mlx", "mlx_lm", "torch"})
        assert frameworks == []
        lease.__enter__()
        acquired = inspect_gpu_lock(args.repository)
        assert acquired["held"] and acquired["owner"]["pid"] == os.getpid()
        save(root / "lease-acquired.json", {"at_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(),
                                           "frameworks_before_lease": frameworks, "actual_lock": acquired})
        result = numeric(root, lease)
        save(root / "result.json", result)
        code = 0
    except BaseException as exc:
        traceback.print_exc()
        save(root / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
    finally:
        save(root / "child-terminal.json", {"exit_code": code, "ended_at_utc": datetime.now(timezone.utc).isoformat(),
                                           "lease_held_until_exit": lease._handle is not None,
                                           "result_status": None if result is None else result["status"]})
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)


def supervise(args):
    import psutil

    root = args.output.resolve()
    assert ".toolalign-local" in root.parts
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    argv = [str(args.replay_python), "-B", str(Path(__file__).resolve()), "child",
            "--repository", str(args.repository.resolve()), "--output", str(root)]
    save(root / "preregistration.json", {"argv": argv, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                                        "cpu_child_launches_max": 1, "trainer_calls_max": 1,
                                        "wall_seconds_max": 300, "rss_bytes_max": 4 * 1024**3,
                                        "examples_max": 13, "sequence_tokens_max": 16, "vocabulary_max": 16,
                                        "parameter_elements_max": 4096, "dtype": "float32", "atol": 2e-6,
                                        "planned_optimizer_updates": 0, "planned_checkpoint_files": 0})
    process, error, peak, samples = None, None, 0, []
    started = time.monotonic()
    try:
        with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
            try:
                process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, cwd=args.repository)
                own = psutil.Process(process.pid)
                while process.poll() is None:
                    try:
                        rss = own.memory_info().rss
                        peak = max(peak, rss)
                        elapsed = time.monotonic() - started
                        samples.append({"wall_seconds": elapsed, "rss_bytes": rss})
                        if elapsed > 300 or rss > 4 * 1024**3:
                            raise TimeoutError("R1 CPU numerical budget exceeded")
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
    code = process.returncode if process is not None and error is None else 1
    record = {"argv": argv, "pid": None if process is None else process.pid,
              "actual_child_exit": None if process is None else process.returncode, "exit_code": code,
              "wall_seconds": time.monotonic() - started, "peak_rss_bytes": peak, "samples": samples,
              "own_process_reaped": process is not None and process.returncode is not None,
              "own_pid_exists": process is not None and psutil.pid_exists(process.pid), "error": error,
              "shared_lock_after": inspect_gpu_lock(args.repository),
              "stdout_sha256": sha(root / "stdout.log"), "stderr_sha256": sha(root / "stderr.log"),
              "ended_at_utc": datetime.now(timezone.utc).isoformat(), "cpu_children_launched": int(process is not None)}
    save(root / "supervision.json", record)
    print(json.dumps({key: record[key] for key in ("exit_code", "wall_seconds", "peak_rss_bytes",
                                                   "own_process_reaped", "own_pid_exists")}))
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("supervise", "child"))
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay-python", type=Path)
    args = parser.parse_args()
    if args.mode == "child":
        child(args)
    assert args.replay_python is not None
    return supervise(args)


if __name__ == "__main__":
    sys.exit(main())
