"""Bounded single-GPU execution with an external parent deadline."""

from __future__ import annotations

import json
import multiprocessing
import os
import random
import signal
import time
import traceback
from pathlib import Path

from toolalign.runtime.gpu_lock import GPULease, lock_path

from .arrays import encode, prepare, read_bundle
from .checkpoint import (
    CheckpointStore,
    capture,
    deserialize,
    inspect_checkpoint,
    parameter_hash,
    restore,
)
from .engine import evaluate, groups, load_model, make_optimizer, train_group
from .protocol import (
    CONFIG_SHA256,
    bounded_request,
    canonical_sha,
    dependency_identity,
    document,
    encoded,
    load_protocol,
    require,
    source_identity,
    validate_run,
    write_bytes,
)


def require_cuda():
    import torch

    require(torch.cuda.is_available(), "CUDA_unavailable_no_fallback")
    require(torch.cuda.is_bf16_supported(), "CUDA_BF16_unavailable")


def runtime_identity(request, config, bundle, source, dependencies):
    """Path-independent continuation identity; capacity and SFT cannot mix."""
    import torch

    properties = torch.cuda.get_device_properties(0)
    return {"schema": "toolalign.cuda-sft-identity.v1", "source": source,
        "config_identity": CONFIG_SHA256, "run_kind": request["run_kind"], "profile": request["profile"],
        "data_identity": {"array_manifest_sha256": bundle.manifest_sha256,
                          "cohort_sha256": bundle.manifest["cohort_sha256"]},
        "model_identity": {"model_id": bundle.manifest["model"]["model_id"],
                           "revision": bundle.manifest["model"]["model_revision"],
                           "metadata_sha256": config["bindings"]["configs/qwen-models.v1.json"]},
        "dependency_identity": dependencies,
        "validation_every_steps": request["validation_every_steps"],
        "checkpoint_every_steps": request["checkpoint_every_steps"],
        "runtime": {"torch": str(torch.__version__), "cuda": torch.version.cuda,
                    "cudnn": torch.backends.cudnn.version(), "device": properties.name,
                    "capability": [properties.major, properties.minor],
                    "total_memory": properties.total_memory,
                    "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                    "matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
                    "cudnn_allow_tf32": torch.backends.cudnn.allow_tf32}}


def rng_hash(state):
    return canonical_sha({"python": state["python_rng"], "numpy": state["numpy_rng"],
                          "torch_cpu": state["torch_cpu_rng"].tolist(),
                          "torch_cuda": [s.tolist() for s in state["torch_cuda_rng"]]})


def _memory(config):
    import torch

    torch.cuda.synchronize(0)
    free, total = torch.cuda.mem_get_info(0)
    peak = torch.cuda.max_memory_reserved(0)
    fraction = config["execution"]["memory_headroom_fraction"]
    require(free >= total * fraction and peak <= total * (1 - fraction), "CUDA_memory_headroom")
    return {"free_bytes": free, "total_bytes": total, "peak_reserved_bytes": peak,
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(0)}


def execute(request):
    """Called by the supervised child. No real-model CPU or Mac fallback."""
    started = time.monotonic()
    config = load_protocol(request["repository"])
    validate_run(request, config)
    source = source_identity(request["repository"], request["source_commit"])
    require(lock_path(request["repository"]) == lock_path(request["lock_root"]), "nonshared_GPU_lock")
    dependencies = dependency_identity(request["dependency_lock"], request["dependency_lock_sha256"])
    bundle = read_bundle(request["array_dir"], expected_digest=request["array_manifest_sha256"], config=config)
    require(bundle.manifest["source"] == source and bundle.manifest["run_kind"] == request["run_kind"]
            and bundle.manifest["profile"] == request["profile"], "run_array_identity")
    root = Path(request["output_dir"])
    require(not root.exists() and not Path(request["persistent_dir"]).exists(), "run_output_already_exists")
    with GPULease(task_id="P04-CUDA-SFT", worker_alias="S1", run_id=request["run_id"],
                  expected_job=request["run_kind"], memory_strategy="BF16_base_FP32_LoRA_20pct_headroom",
                  repository=request["lock_root"], timeout_seconds=0) as lease:
        require_cuda()
        import numpy as np
        import torch

        identity = runtime_identity(request, config, bundle, source, dependencies)
        resume = None
        if "resume_from" in request:
            manifest, contents = inspect_checkpoint(request["resume_from"], identity=identity,
                                                   expected_sha=request["resume_checkpoint_sha256"])
            state = deserialize(contents["state.pt"], identity=identity,
                                train_count=len(bundle.ids["train"]), manifest=manifest, device="cuda:0")
            require(state["optimizer_step"] < request["max_optimizer_steps"], "resume_no_remaining_steps")
            resume = manifest, contents, state
        root.mkdir(mode=0o700, parents=False, exist_ok=False)
        write_bytes(root / "run.json", encoded(request) + b"\n")
        store = CheckpointStore(local=root / "checkpoints", persistent=request["persistent_dir"],
                                identity=identity, max_bytes=request["max_output_bytes"])
        random.seed(config["training"]["seed"])
        np.random.seed(config["training"]["seed"])
        torch.manual_seed(config["training"]["seed"])
        torch.cuda.manual_seed(config["training"]["seed"])
        torch.cuda.reset_peak_memory_stats(0)
        model = load_model(request, config, lease)
        initial_b = [p for n, p in model.named_parameters() if ".lora_B." in n]
        require(initial_b and all(int(torch.count_nonzero(p)) == 0 for p in initial_b), "initial_LoRA_B_nonzero")
        optimizer = make_optimizer(model, config)
        step, cursor = 0, 0
        if resume is not None:
            manifest, contents, state = resume
            store.seed(manifest, contents)
            step, cursor = restore(state, model, optimizer, device="cuda:0")
        adapter_before = parameter_hash(model)
        frozen_before = parameter_hash(model, trainable=False) if request["run_kind"] == "capacity" else None
        _memory(config)
        last_checkpoint = None
        with (root / "events.jsonl").open("x", encoding="utf-8") as events:
            for group in groups(bundle.records("train"), cursor=cursor):
                require(time.monotonic() - started < request["max_wall_seconds"], "run_deadline")
                torch.cuda.synchronize(0)
                step_started = time.perf_counter()
                result = train_group(model, optimizer, group, device="cuda:0")
                torch.cuda.synchronize(0)
                step_seconds = time.perf_counter() - step_started
                step, cursor = step + 1, cursor + len(group)
                final = step == request["max_optimizer_steps"] or cursor == len(bundle.ids["train"])
                validation = None
                if final or step % request["validation_every_steps"] == 0:
                    validation = evaluate(model, bundle.records("validation"), expected_ids=bundle.ids["validation"],
                                          profile=request["profile"], device="cuda:0")
                event = {"optimizer_step": step, "data_cursor": cursor, **result,
                         "optimizer_step_seconds": step_seconds,
                         "validation": validation, "memory": _memory(config)}
                if final or validation is not None or step % request["checkpoint_every_steps"] == 0:
                    state = capture(model, optimizer, step=step, cursor=cursor, identity=identity, device="cuda:0")
                    path = store.save(state, validation_ce=None if validation is None else validation["validation_ce"])
                    checkpoint = document(path / "manifest.json")
                    last_checkpoint = path.name
                    event.update({"checkpoint": path.name, "checkpoint_sha256": checkpoint["checkpoint_sha256"],
                                  "adapter_sha256": parameter_hash(model), "rng_sha256": rng_hash(state)})
                events.write(json.dumps(event, allow_nan=False, sort_keys=True) + "\n")
                events.flush()
                if final:
                    break
        adapter_after = parameter_hash(model)
        require(adapter_before != adapter_after, "adapter_did_not_update")
        frozen_after = parameter_hash(model, trainable=False) if frozen_before is not None else None
        require(frozen_before == frozen_after, "frozen_weights_changed")
        summary = {"status": "PASS", "run_id": request["run_id"], "run_kind": request["run_kind"],
            "profile": request["profile"], "optimizer_step": step, "data_cursor": cursor,
            "epoch_complete": request["run_kind"] == "sft" and cursor == len(bundle.ids["train"]),
            "selected_rows_complete": cursor == len(bundle.ids["train"]),
            "validation_scope": "capacity_cohort" if request["run_kind"] == "capacity" else "full_frozen_profile",
            "diagnostic_only": request["run_kind"] == "capacity", "checkpoint": last_checkpoint,
            "remote_copy_verified": True, "durability_verified": False,
            "initialized_LoRA_B_zero": True, "adapter_before_sha256": adapter_before,
            "adapter_after_sha256": adapter_after, "adapter_changed": True,
            "frozen_before_sha256": frozen_before, "frozen_after_sha256": frozen_after,
            "frozen_content_check": "PASS" if frozen_before is not None else "NOT_RUN",
            "best": store.best, "identity": identity, "memory": _memory(config),
            "elapsed_seconds": time.monotonic() - started}
        write_bytes(root / "summary.json", encoded(summary) + b"\n")
        return summary


def _child(command, request, connection):
    os.setsid()
    try:
        result = {"train": execute, "prepare": prepare, "encode": encode}[command](request)
        if command == "train":
            result = {k: result[k] for k in ("status", "run_id", "optimizer_step", "checkpoint")}
        connection.send(result)
    except BaseException as exc:
        traceback.print_exc()
        connection.send({"status": "FAIL", "error": type(exc).__name__ + ": " + str(exc)})
    finally:
        connection.close()


def _signal_child(process, sig):
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        # An interrupt can precede the child's first setsid(). It is still ours.
        if sig == signal.SIGKILL:
            process.kill()
        else:
            process.terminate()


def supervise(request, *, command="train"):
    """Deadlines and external SIGTERM reap the owned child before returning."""
    config = load_protocol(request["repository"])
    require(command in ("train", "prepare", "encode"), "unknown_command")
    if command == "train":
        validate_run(request, config)
    else:
        bounded_request(request, schema=f"toolalign.cuda-sft-{command}.v1")
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(command, request, sender))
    started = False
    terminate_requested = False

    def terminate(signum, frame):
        nonlocal terminate_requested
        terminate_requested = True
        # Do not interrupt spawn before Process has retained its child's PID.
        if started:
            raise SystemExit(128 + signum)

    previous_handler = signal.signal(signal.SIGTERM, terminate)
    try:
        process.start()
        started = True
        if terminate_requested:
            raise SystemExit(128 + signal.SIGTERM)
        sender.close()
        process.join(request["max_wall_seconds"])
        if process.is_alive():
            _signal_child(process, signal.SIGTERM)
            process.join(3)
            if process.is_alive():
                _signal_child(process, signal.SIGKILL)
                process.join(3)
            raise TimeoutError("CUDA_run_wall_budget_exceeded")
        require(process.exitcode == 0 and receiver.poll(), "CUDA_worker_missing_terminal_result")
        result = receiver.recv()
        require(result["status"] == "PASS", result.get("error", "CUDA_worker_failed"))
        return result
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            if process.pid is not None and process.is_alive():
                _signal_child(process, signal.SIGKILL)
                process.join(3)
            sender.close()
            receiver.close()
            process.close()
        finally:
            signal.signal(signal.SIGTERM, previous_handler)
