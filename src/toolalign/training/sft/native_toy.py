"""Explicit bounded ORIGINAL toy replay; never a pretrained-model training API.

The isolated parent imports no numerical framework. The child acquires the
repository's actual GPU lease before imports and retains it until OS exit.
Only the byte-exact authorized configuration and original CPU cases are read.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError
from toolalign.runtime.gpu_lock import GPULease, inspect_gpu_lock, lock_path

from .collator import Batch
from .config import consumer_identity as cpu_consumer_identity
from .config import require

CONFIG_SHA256 = "fb06634d00b0565a60dc22ea829ac509732b3b6429b9bbbc2ff6207c974850cb"
CASES_SHA256 = "df4b87001074e9fab6c3a330cf516dca17cfab1bb7505d97025ceeb31d3b5b47"
SCOPE = "TOY_NATIVE_GPU"
ROUND = "p04-sft-native-toy-r1"
MODES = ("source_segmented", "source_unsegmented_negative", "installed_segmented")
NUMERICAL_MODULES = {"mlx", "mlx_lm", "torch", "numpy"}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _utc():
    return datetime.now(timezone.utc).isoformat()


def consumer_identity():
    """Include this new consumer and package support bytes in the native epoch."""
    root = Path(str(files("toolalign")))
    sft = cpu_consumer_identity()
    sft["native_toy.py"] = _sha(Path(__file__))
    support = {p.relative_to(root).as_posix(): _sha(p) for p in sorted(root.rglob("*.py"))
               if not p.is_relative_to(root / "training/sft")}
    return {"sft": sft, "support": support}


def _exact_json(path, digest, error):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size < 131072, error)
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == digest, error)
    return json.loads(data)


def _case_bounds(value):
    """Pure pre-import structural bounds, in addition to the original file hash."""
    require(type(value) is dict and type(value.get("train")) is list
            and len(value["train"]) == value.get("unique_examples") == 13,
            "native_example_budget")
    require(type(value.get("vocabulary")) is int and 0 < value["vocabulary"] <= 16,
            "native_vocabulary_budget")
    require(type(value.get("parameters")) is int and 0 < value["parameters"] <= 4096,
            "native_parameter_budget")
    initial = value.get("initial_table")
    require(type(initial) is list and len(initial) == 8
            and all(type(row) is list and len(row) == 8 for row in initial)
            and value["parameters"] == 64 and value["vocabulary"] == 8,
            "native_fixed_model_shape")
    require(all(type(v) is float and math.isfinite(v) for row in initial for v in row),
            "native_nonfinite_initial_state")
    batches = []
    arrays = ("sequence_ids", "attention_mask", "loss_mask", "causal_input_ids",
              "causal_target_ids", "causal_loss_mask")
    for expected, item in enumerate(value["train"], 1):
        require(type(item) is list and len(item) == 2 and type(item[0]) is int
                and item[0] == expected and type(item[1]) is dict, "native_original_order")
        record = dict(item[1])
        require(type(record.get("bucket")) is int and 0 < record["bucket"] <= 16,
                "native_sequence_budget")
        require(type(record.get("effective_supervised_targets")) is int
                and record["effective_supervised_targets"] > 0, "empty_native_supervision")
        for name in arrays:
            require(type(record.get(name)) is list, "native_original_arrays")
            record[name] = tuple(record[name])
        batch = Batch(**record)
        require(batch.bucket == 16 and batch.pad_token_id == 0
                and all(0 <= token < value["vocabulary"] for token in batch.sequence_ids),
                "native_fixed_token_bounds")
        require(batch.causal_target_ids[batch.last_supervised_causal_position] == 7,
                "native_original_eos")
        batches.append((expected, batch))
    return tuple(batches)


def load_inputs(config_path, cases_path, repository):
    config = _exact_json(config_path, CONFIG_SHA256, "native_config_hash_mismatch")
    value = _exact_json(cases_path, CASES_SHA256, "native_cases_hash_mismatch")
    repository = Path(repository).resolve()
    require(_sha(repository / "configs/sft-cpu.v1.json")
            == config["preserved_cpu_config_sha256"], "native_cpu_config_changed")
    require(_sha(repository / "reports/experiments/P04_SFT_CPU_TOY.py")
            == config["original_cpu_case_generator_sha256"], "native_original_generator_changed")
    return config, value, _case_bounds(value)


def require_current_lease(lease, repository):
    """A live current-PID flock on the same physical repository is required."""
    require(type(lease) is GPULease and lease._handle is not None
            and not lease._handle.closed, "active_current_native_lease_required")
    path = lock_path(repository)
    require(lock_path(lease.repository) == path, "native_lease_repository_mismatch")
    actual, expected = os.fstat(lease._handle.fileno()), path.stat()
    require((actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino),
            "native_lease_descriptor_mismatch")
    observation = inspect_gpu_lock(repository)
    owner = observation.get("owner") or {}
    require(observation["held"] and owner.get("pid") == os.getpid(),
            "active_current_native_lease_required")
    started = subprocess.check_output(["ps", "-p", str(os.getpid()), "-o", "lstart="], text=True).strip()
    require(owner.get("process_started_at") == started
            and all(owner.get(k) == v for k, v in lease.metadata.items())
            and owner.get("task_id") == "P04-SFT-NATIVE-TOY", "native_lease_owner_mismatch")
    return observation


def _versions(config):
    expected = {"mlx": "mlx_version", "mlx-lm": "version", "torch": "torch_version",
                "numpy": "numpy_version", "psutil": "psutil_version"}
    actual = {name: importlib.metadata.version(name) for name in expected}
    require(all(actual[name] == config["backend"][key] for name, key in expected.items()),
            "native_backend_version_mismatch")
    distribution = importlib.metadata.distribution("mlx-lm")
    sources = {name: _sha(distribution.locate_file("mlx_lm/tuner/" + name + ".py"))
               for name in ("trainer", "datasets")}
    require(all(sources[name] == config["backend"][name + "_source_sha256"] for name in sources),
            "native_upstream_source_mismatch")
    return {"versions": actual, "upstream_sources": sources}


def _origins():
    root = Path(__file__).resolve().parents[3]
    result = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(root), "native_source_path_fallback")
            result[name] = {"path": str(path), "sha256": _sha(path)}
    return result


def _numerics(*, root, mode, config, original, dataset, lease, repository):
    require_current_lease(lease, repository)
    require(not NUMERICAL_MODULES & {n.split(".")[0] for n in sys.modules},
            "native_framework_loaded_before_lease")
    environment = _versions(config)
    _save(root / "environment-before-import.json", environment)
    import mlx.core as mx

    mx.set_default_device(mx.gpu)  # Before model/array creation, never CPU fallback.
    require(mx.default_device() == mx.gpu and mx.metal.is_available(), "native_gpu_required")
    with mx.stream(mx.gpu):
        _numeric_body(mx, root, mode, config, original, dataset, environment)
    require_current_lease(lease, repository)


def _numeric_body(mx, root, mode, config, original, dataset, environment):
    import mlx.nn as nn
    import mlx.optimizers as optim
    import numpy as np
    import torch
    from mlx_lm.tuner import trainer

    from toolalign.training.compatibility.execution import preserve_wired_limit

    from .mlx_adapter import (
        OrderedBatches,
        _post_update_score,
        _train_toy_segments,
        completion_loss,
        parameter_hash,
    )
    from .validation import choose_score

    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.set_default_device("cpu")
    torch.manual_seed(42)
    initial = np.asarray(original["initial_table"], dtype=np.float32)
    require(initial.shape == (8, 8) and initial.size == 64, "native_fixed_model_shape")
    atol = config["limits"]["numeric_absolute_tolerance"]
    memory = []

    def checkpoint_memory(phase):
        mx.synchronize()
        record = {"phase": phase, "at": _utc(), "mlx_peak_bytes": mx.get_peak_memory(),
                  "mlx_active_bytes": mx.get_active_memory(), "mlx_cache_bytes": mx.get_cache_memory()}
        memory.append(record)
        _save(root / f"memory-{len(memory):02d}.json", record)
        require(record["mlx_peak_bytes"] <= config["limits"]["mlx_peak_memory_bytes_max"],
                "native_mlx_memory_budget")

    class Table(nn.Module):
        def __init__(self):
            super().__init__()
            self.table = mx.array(initial)

        def __call__(self, ids):
            return self.table[ids]

    class FixedLogits(nn.Module):
        def __init__(self, logits):
            super().__init__()
            self.logits = logits

        def __call__(self, ids):
            return self.logits

    def torch_mean(parameter, batch):
        # Derive supervision independently from the original unpadded/prompt
        # boundaries; never copy the MLX loss mask into the reference reduction.
        ids = torch.tensor(batch.sequence_ids, dtype=torch.long, device="cpu")
        losses = torch.nn.functional.cross_entropy(parameter[ids[:-1]], ids[1:], reduction="none")
        start, stop = batch.first_supervised_causal_position, batch.unpadded_length - 1
        return losses[start:stop].sum() / (stop - start)

    def validation(parameter):
        cases, numerator, denominator = [], 0.0, 0
        with torch.no_grad():
            for rank, batch in dataset:
                loss = torch_mean(parameter, batch).item()
                count = batch.effective_supervised_targets
                cases.append({"rank": rank, "mean_ce": loss, "tokens": count})
                numerator += loss * count
                denominator += count
        return {"cases": cases, "ce_sum": numerator, "tokens": denominator,
                "validation_ce": numerator / denominator}

    def arrays(batch, unpadded=False):
        stop = batch.unpadded_length if unpadded else batch.bucket
        return (mx.array([batch.sequence_ids[:stop]], dtype=mx.int32),
                mx.array([batch.causal_loss_mask[:stop - 1]], dtype=mx.int32))

    def compare(left, right):
        a, b = np.asarray(left), np.asarray(right)
        require(a.shape == b.shape and bool(np.isfinite(a).all()) and bool(np.isfinite(b).all()),
                "native_numeric_shape_or_finiteness")
        error = float(np.max(np.abs(a - b)))
        require(error <= atol, "native_numeric_tolerance")
        return error

    model = Table()
    device = {"mlx_default": str(mx.default_device()),
              "mlx_execution_stream": str(mx.default_stream(mx.gpu).device),
              "mlx_array_dlpack": list(model.table.__dlpack_device__()),
              "dlpack_meaning": "hardware interoperability label, not execution placement",
              "torch": str(torch.tensor(0, device="cpu").device),
              "torch_intra_threads": torch.get_num_threads(),
              "torch_inter_threads": torch.get_num_interop_threads()}
    require(mx.default_device() == mx.gpu and mx.default_stream(mx.gpu).device == mx.gpu
            and device["torch"] == "cpu" and device["torch_intra_threads"] <= 2
            and device["torch_inter_threads"] <= 2, "native_device_or_thread_mismatch")
    _save(root / "device-before-numerics.json", device)
    _save(root / "original-input-copy.json", original)
    metrics = []
    gradient_fn = nn.value_and_grad(model, completion_loss)
    for rank, batch in dataset:
        (mean, count), gradient = gradient_fn(model, *arrays(batch))
        (short_mean, short_count), short_gradient = gradient_fn(model, *arrays(batch, unpadded=True))
        mx.eval(mean, count, gradient, short_mean, short_count, short_gradient)
        reference = torch.tensor(initial, dtype=torch.float32, requires_grad=True, device="cpu")
        reference_loss = torch_mean(reference, batch)
        reference_loss.backward()
        raw = {"rank": rank, "batch": batch.record(), "mlx_ce": mean.item(),
               "mlx_denominator": count.item(), "mlx_gradient": np.array(gradient["table"]).tolist(),
               "torch_ce": reference_loss.item(), "torch_denominator": batch.effective_supervised_targets,
               "torch_gradient": reference.grad.numpy().tolist(),
               "unpadded_mlx_ce": short_mean.item(), "unpadded_mlx_denominator": short_count.item(),
               "unpadded_mlx_gradient": np.array(short_gradient["table"]).tolist()}
        ids, mask = arrays(batch)
        logits = model(ids[:, :-1])
        changed = mx.where(mask[:, :, None] == 0, logits + mx.arange(8) * 10, logits)
        ignored_loss = completion_loss(FixedLogits(changed), ids, mask)[0]
        raw.update(ignored_original_logits=np.array(logits).tolist(),
                   ignored_changed_logits=np.array(changed).tolist(), ignored_changed_ce=ignored_loss.item())
        _save(root / f"case-{rank:02d}-arrays.json", raw)  # Preserve before assertions.
        require(raw["mlx_denominator"] == raw["unpadded_mlx_denominator"]
                == raw["torch_denominator"], "native_effective_denominator_mismatch")
        metrics.append({"rank": rank, "loss_error": compare(mean.item(), reference_loss.item()),
            "gradient_error": compare(gradient["table"], reference.grad.numpy()),
            "padding_loss_error": compare(mean.item(), short_mean.item()),
            "padding_gradient_error": compare(gradient["table"], short_gradient["table"]),
            "ignored_logits_error": compare(mean.item(), ignored_loss.item())})
    first = dataset[0][1]
    ids, mask = arrays(first)
    default_ce, default_tokens = trainer.default_loss(model, ids,
        mx.array([[first.first_supervised_causal_position + 1, first.unpadded_length]]))
    correct_ce, correct_tokens = completion_loss(model, ids, mask)
    default_negative = {"default_ce": default_ce.item(), "default_tokens": default_tokens.item(),
                        "correct_ce": correct_ce.item(), "correct_tokens": correct_tokens.item()}
    _save(root / "default-padding-negative.json", default_negative)
    require(default_negative["default_tokens"] == 3 and default_negative["correct_tokens"] == 2
            and abs(default_negative["default_ce"] - default_negative["correct_ce"]) > atol,
            "native_default_padding_negative_missing")
    checkpoint_memory("per-example-numerics")

    parameter = torch.tensor(initial, dtype=torch.float32, requires_grad=True, device="cpu")
    torch_optimizer = torch.optim.SGD([parameter], lr=0.07, momentum=0, weight_decay=0)
    torch_states, torch_scores = [], []
    for step, (start, stop) in enumerate(((0, 8), (8, 13)), 1):
        torch_optimizer.zero_grad()
        objective = torch.stack([torch_mean(parameter, b) for _, b in dataset[start:stop]]).mean()
        objective.backward()
        gradient = parameter.grad.numpy().copy()
        torch_optimizer.step()
        state = parameter.detach().numpy().copy()
        score = validation(parameter)
        torch_states.append(state)
        torch_scores.append(score)
        _save(root / f"torch-update-{step}.json", {"optimizer_step": step, "processed_microsteps": stop,
            "divisor": stop - start, "objective": objective.item(), "gradient": gradient.tolist(),
            "parameter": state.tolist(), "validation": score})
    optimizer, events = optim.SGD(learning_rate=0.07), []
    original_setter, original_compile = mx.set_wired_limit, mx.compile
    compile_identity = {"module": getattr(original_compile, "__module__", None),
                        "name": getattr(original_compile, "__name__", None)}
    try:
        with preserve_wired_limit(mx, events):
            if mode == "source_unsegmented_negative":
                checkpoint = root / "TOY_NATIVE_GPU-unsegmented.safetensors"
                iterator = OrderedBatches()
                args = trainer.TrainingArgs(batch_size=1, iters=13, grad_accumulation_steps=8,
                    steps_per_report=13, steps_per_eval=14, steps_per_save=14,
                    max_seq_length=16, adapter_file=str(checkpoint), grad_checkpoint=False)
                mx.random.seed(42)
                trainer.train(model=model, optimizer=optimizer, train_dataset=dataset, val_dataset=None,
                              args=args, loss=completion_loss, iterate_batches=iterator)
                actual = np.array(model.table)
                tail_error = float(np.max(np.abs(actual - torch_states[1])))
                _save(root / "unsegmented-actual-arrays.json", {"parameter": actual.tolist(),
                    "complete_reference_parameter": torch_states[1].tolist(),
                    "difference": (actual - torch_states[1]).tolist(),
                    "optimizer_step": int(optimizer.step.item()), "visited": iterator.visited})
                require(iterator.visited == list(range(1, 14)) and int(optimizer.step.item()) == 1
                        and tail_error > atol, "native_tail_negative_missing")
                first_error = compare(actual, torch_states[0])
                result = {"status": "EXPECTED_NEGATIVE", "actual_optimizer_updates": 1,
                          "lost_tail_microsteps": 5, "visited": iterator.visited,
                          "first_state_error": first_error, "complete_epoch_error": tail_error,
                          "checkpoint_file_sha256": _sha(checkpoint)}
            else:
                result = _train_toy_segments(mx=mx, trainer=trainer, profile=SCOPE, model=model,
                    optimizer=optimizer, train_dataset=dataset, validation_dataset=dataset,
                    output=root / "segments")
                errors = []
                for index, state in enumerate(result["states"]):
                    checkpoint = root / "segments" / state["checkpoint"]
                    saved = mx.load(str(checkpoint))
                    raw = {"state": state, "score": result["scores"][index].record(),
                           "parameter": np.array(saved["table"]).tolist(),
                           "torch_parameter": torch_states[index].tolist(),
                           "torch_validation": torch_scores[index],
                           "difference": (np.array(saved["table"]) - torch_states[index]).tolist()}
                    _save(root / f"native-update-{index + 1}-arrays.json", raw)
                    require(result["scores"][index].supervised_tokens == torch_scores[index]["tokens"],
                            "native_validation_denominator_mismatch")
                    errors.append({"step": index + 1, "parameter_error": compare(saved["table"], torch_states[index]),
                        "validation_error": compare(result["scores"][index].validation_ce,
                                                    torch_scores[index]["validation_ce"])})
                final = result["scores"][-1]
                checkpoint = root / "segments" / result["states"][-1]["checkpoint"]
                reloaded = Table()
                reloaded.load_weights(str(checkpoint))
                require(parameter_hash(reloaded) == parameter_hash(model) == final.parameter_content_sha256,
                        "native_reload_state_mismatch")
                replay = _post_update_score(mx=mx, trainer=trainer, profile=SCOPE, model=reloaded,
                    optimizer=optimizer, dataset=dataset, checkpoint=checkpoint,
                    selection_sha256=final.selection_sha256, processed_microsteps=13, expected_optimizer_step=2)
                _save(root / "reload-arrays.json", {"parameter": np.array(reloaded.table).tolist(),
                      "score": replay.record(), "checkpoint_sha256": _sha(checkpoint)})
                require(replay == final, "native_reload_score_mismatch")
                try:
                    _post_update_score(mx=mx, trainer=trainer, profile=SCOPE, model=model,
                        optimizer=optimizer, dataset=dataset,
                        checkpoint=root / "segments" / result["states"][0]["checkpoint"],
                        selection_sha256=final.selection_sha256, processed_microsteps=13,
                        expected_optimizer_step=2)
                except DataError as exc:
                    require(str(exc) == "checkpoint_parameter_content_mismatch", "native_wrong_checkpoint_error")
                    rejected = str(exc)
                else:
                    raise DataError("native_wrong_checkpoint_accepted")
                result.update(status="PASS", errors=errors, selected=choose_score(result["scores"]).record(),
                              save_reload_exact=True, wrong_checkpoint_rejected=rejected)
                result["scores"] = [score.record() for score in result["scores"]]
    finally:
        restored = mx.set_wired_limit is original_setter
        compile_preserved = mx.compile is original_compile
        _save(root / "wired-limit-and-compile.json", {"events": events, "setter_restored": restored,
              "compile_preserved": compile_preserved, "compile_identity": compile_identity})
        require(restored and compile_preserved, "native_upstream_api_not_restored")
    checkpoint_memory("after-native-training-and-validation")
    require(mx.default_device() == mx.gpu and mx.default_stream(mx.gpu).device == mx.gpu,
            "native_final_device_mismatch")
    require(environment == _versions(config), "native_dependency_bytes_changed")
    result.update(scope=SCOPE, mode=mode, config_sha256=CONFIG_SHA256, original_cases_sha256=CASES_SHA256,
                  metrics=metrics, device=device, memory=memory, numeric_atol=atol,
                  independent_reference_optimizer_updates=2, actual_model_parameters=64,
                  unique_original_examples=13, actual_largest_sequence=16, actual_vocabulary=8,
                  parameter_content_sha256=parameter_hash(model), environment=environment,
                  consumer_identity=consumer_identity(), origins=_origins(), training_authorized=False)
    _save(root / "result.json", result)


def _validate_output(repository, output):
    root = Path(repository).resolve() / ".toolalign-local" / ROUND
    output = Path(output).absolute()
    require(output.parent.resolve() == root.resolve() and output.name not in ("", ".", "..")
            and not output.exists() and not output.is_symlink(), "native_output_exists_or_outside_round")
    require(all(not p.is_symlink() for p in (root, *root.parents)), "native_output_symlink")
    return root, output


def _disk_bytes(root):
    total = 0
    for path in root.rglob("*"):
        # CPU rejection tests intentionally create links. Count the stored link
        # bytes without following its target; numerical input/output guards
        # separately reject links where they would be consumed or written.
        if path.is_symlink() or path.is_file():
            total += path.lstat().st_size
    require(total <= 2 * 1024**3, "native_private_disk_budget")
    return total


def _reserve(root, output, mode, preregistration):
    """One immutable reservation per launch; only actual failed modes may retry."""
    ledger = root / "framework-launches"
    ledger.mkdir(mode=0o700, exist_ok=True)
    with (ledger / "reservation.lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        records = [json.loads(p.read_text()) for p in sorted(ledger.glob("launch-*.json"))]
        require(len(records) < 5, "native_framework_launch_budget")
        for record in records:
            if record["mode"] == mode:
                terminal = Path(record["output"]) / "supervision.json"
                require(terminal.is_file() and json.loads(terminal.read_text())["exit_code"] != 0,
                        "native_success_or_active_mode_must_not_repeat")
        value = {**preregistration, "launch_number": len(records) + 1,
                 "mode": mode, "output": str(output), "reserved_at": _utc()}
        _save(ledger / f"launch-{len(records) + 1:02d}.json", value)
        return value


def _parse(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "cases", "repository", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    return parser.parse_args(argv)


def _child():
    args = _parse()
    root, lease, code = args.output.resolve(), None, 1
    try:
        config, original, dataset = load_inputs(args.config, args.cases, args.repository)
        lease = GPULease(task_id="P04-SFT-NATIVE-TOY", worker_alias="T1", run_id=root.name,
            expected_job=args.mode, memory_strategy="native toy <=300s / RSS4GiB / MLX1GiB",
            repository=args.repository, timeout_seconds=0)
        lease.__enter__()
        _save(root / "lease-acquired.json", {"at": _utc(), "pid": os.getpid(),
              "actual_lock": require_current_lease(lease, args.repository),
              "numerical_modules_before_import": sorted(NUMERICAL_MODULES & {n.split(".")[0] for n in sys.modules})})
        _numerics(root=root, mode=args.mode, config=config, original=original, dataset=dataset,
                  lease=lease, repository=args.repository)
        code = 0
    except BaseException as exc:
        traceback.print_exc()
        _save(root / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
    finally:
        _save(root / "child-terminal.json", {"ended_at": _utc(), "exit_code": code,
            "lease_held_until_process_exit": lease is not None and lease._handle is not None})
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)  # The OS releases Metal state and the leased fd together.


def supervise(args):
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            "native_isolated_no_site_no_bytecode_required")
    require(not NUMERICAL_MODULES & {n.split(".")[0] for n in sys.modules},
            "native_parent_framework_import")
    config, _, _ = load_inputs(args.config, args.cases, args.repository)
    root, output = _validate_output(args.repository, args.output)
    require(args.mode in MODES, "native_mode_not_authorized")
    versions = _versions(config)
    require(not inspect_gpu_lock(args.repository)["held"], "native_gpu_busy_before_launch")
    _disk_bytes(root)
    import psutil

    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    identities = consumer_identity()
    preregistration = {"scope": SCOPE, "config_sha256": CONFIG_SHA256, "cases_sha256": CASES_SHA256,
        "limits": config["limits"], "consumer_identity": identities,
        "consumer_sha256": canonical_hash(identities), "environment": versions,
        "source_head": subprocess.check_output(["git", "-C", str(args.repository), "rev-parse", "HEAD"], text=True).strip(),
        "parent_origins": _origins(), "parent_argv": sys.argv, "parent_cwd": str(Path.cwd()),
        "isolated": True, "no_site": True, "no_bytecode": True}
    reservation = _reserve(root, output, args.mode, preregistration)
    _save(output / "preregistration.json", reservation)
    bootstrap = ("import json,sys; sys.path[:]=json.loads(sys.argv.pop(1)); "
                 "from toolalign.training.sft.native_toy import _child; _child()")
    command = [sys.executable, "-B", "-I", "-S", "-c", bootstrap, json.dumps(sys.path),
        "--config", str(args.config.resolve()), "--cases", str(args.cases.resolve()),
        "--repository", str(args.repository.resolve()), "--output", str(output), "--mode", args.mode]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                       HF_HUB_DISABLE_IMPLICIT_TOKEN="1", WANDB_MODE="disabled", TOKENIZERS_PARALLELISM="false",
                       OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    process, peak, samples, error = None, 0, [], None
    start, started_at = time.monotonic(), _utc()
    try:
        with (output / "stdout.log").open("xb") as stdout, (output / "stderr.log").open("xb") as stderr:
            try:
                process = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=output, env=environment)
                own = psutil.Process(process.pid)
                while process.poll() is None:
                    try:
                        rss = own.memory_info().rss
                        peak = max(peak, rss)
                        elapsed = time.monotonic() - start
                        samples.append({"elapsed_seconds": elapsed, "rss_bytes": rss})
                        require(elapsed <= 300 and rss <= 4 * 1024**3, "native_wall_or_rss_budget")
                        _disk_bytes(root)
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
    code = 1 if error or process is None else process.returncode
    unchanged = identities == consumer_identity()
    if not unchanged:
        code = 1
    result = {"argv": command, "cwd": str(output), "started_at": started_at, "ended_at": _utc(),
        "environment_overrides": {key: environment[key] for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE",
            "HF_HUB_DISABLE_TELEMETRY", "HF_HUB_DISABLE_IMPLICIT_TOKEN", "WANDB_MODE",
            "TOKENIZERS_PARALLELISM", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        "pid": None if process is None else process.pid, "actual_child_exit": None if process is None else process.returncode,
        "exit_code": code, "error": error, "wall_seconds": time.monotonic() - start,
        "peak_rss_bytes": peak, "samples": samples,
        "own_process_reaped": process is not None and process.returncode is not None,
        "own_pid_exists": process is not None and psutil.pid_exists(process.pid),
        "lock_after": inspect_gpu_lock(args.repository), "consumer_unchanged": unchanged,
        "private_disk_bytes": _disk_bytes(root), "stdout_sha256": _sha(output / "stdout.log"),
        "stderr_sha256": _sha(output / "stderr.log"), "launch_number": reservation["launch_number"]}
    _save(output / "supervision.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "wall_seconds", "peak_rss_bytes",
        "own_process_reaped", "own_pid_exists", "launch_number")}))
    return code


def main(argv=None):
    try:
        return supervise(_parse(argv))
    except (OSError, ValueError, KeyError, ImportError) as exc:
        print(json.dumps({"status": "FAIL", "scope": SCOPE, "error_type": type(exc).__name__,
                          "error": str(exc) if isinstance(exc, DataError) else "invalid_input_or_io"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
