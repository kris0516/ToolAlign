"""CUDA-only execution; the parent bounds wall time and the full output tree."""

from __future__ import annotations

import multiprocessing
import os
import signal
import time
import traceback
from pathlib import Path

from toolalign.model_io.cuda_generation import MODEL_ID, MODEL_REVISION, selected_model_identity
from toolalign.model_io.offline import OfflineQwenTokenizer
from toolalign.runtime.gpu_lock import GPULease, lock_path
from toolalign.training.cuda_sft.checkpoint import parameter_hash
from toolalign.training.cuda_sft.protocol import (
    canonical_sha,
    dependency_identity,
    encoded,
    require,
    source_identity,
    write_bytes,
)
from toolalign.training.cuda_sft.runtime import require_cuda

from .checkpoint import inspect, validate_native_state
from .data import prepare_input
from .protocol import CONFIG_SHA256, load_protocol, select_pairs, validate_run


def memory(config):
    import torch

    torch.cuda.synchronize(0)
    free, total = torch.cuda.mem_get_info(0)
    peak = torch.cuda.max_memory_reserved(0)
    fraction = config["execution"]["memory_headroom_fraction"]
    require(free >= total * fraction and peak <= total * (1 - fraction), "DPO_CUDA_memory_headroom")
    return {"free_bytes": free, "total_bytes": total, "peak_reserved_bytes": peak,
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(0)}


def execute(request):
    """The supervised worker. No download, CPU model fallback, or public service."""
    config = load_protocol(request["repository"])
    source = source_identity(request["repository"], request["source_commit"])
    require("training/cuda_dpo/runtime.py" in source["package_files"], "DPO_source_not_committed")
    dependencies = dependency_identity(request["dependency_lock"], request["dependency_lock_sha256"])
    require(dependencies["versions"].get("trl") == "0.26.2"
            and dependencies["versions"].get("transformers") == "4.57.6", "DPO_native_versions")
    require(lock_path(request["repository"]) == lock_path(request["lock_root"]), "DPO_shared_GPU_lock")
    # The verified tokenizer must be built before model framework imports.
    offline = OfflineQwenTokenizer(request["model_root"], repo_id=MODEL_ID, revision=MODEL_REVISION)
    prepared, preparation = prepare_input(request["input_root"], request["input_manifest_sha256"],
                                          offline, config_sha=CONFIG_SHA256)
    rows, expected = select_pairs(prepared, preparation, request)
    output = Path(request["output_dir"])
    write_bytes(output / "preparation.json", encoded(preparation) + b"\n")
    with GPULease(task_id="P05-G4-DPO", worker_alias="S1", run_id=request["run_id"],
                  expected_job=request["run_kind"], memory_strategy="two_BF16_bases_FP32_QV_LoRA",
                  repository=request["lock_root"], timeout_seconds=0) as lease:
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = config["numerics"]["cublas_workspace_config"]
        import torch
        from transformers import AutoTokenizer, TrainerCallback, set_seed

        from .models import load_pair
        from .trainer import create_trainer

        require_cuda()
        require(torch.cuda.device_count() == 1, "DPO_single_GPU_required")
        torch.use_deterministic_algorithms(True, warn_only=False)
        torch.backends.cuda.matmul.allow_tf32 = False
        set_seed(42)
        torch.cuda.reset_peak_memory_stats(0)
        properties = torch.cuda.get_device_properties(0)
        identity = {"schema": "toolalign.cuda-dpo-identity.v1", "source": source,
                    "config_sha256": CONFIG_SHA256, "run_kind": request["run_kind"],
                    "input_manifest_sha256": request["input_manifest_sha256"],
                    "prepared_data_sha256": preparation["prepared_data_sha256"],
                    "ordered_ids_sha256": canonical_sha([row["preference_id"] for row in rows]),
                    "pair_count": len(rows), "total_optimizer_steps": request["total_optimizer_steps"],
                    "checkpoint_every_steps": request["checkpoint_every_steps"],
                    "model": selected_model_identity(request["repository"]),
                    "initialization": config["initialization"], "dependencies": dependencies,
                    "runtime": {"torch": str(torch.__version__), "cuda": torch.version.cuda,
                        "cudnn": torch.backends.cudnn.version(), "device": properties.name,
                        "capability": [properties.major, properties.minor],
                        "total_memory": properties.total_memory, "bf16_mixed_precision": True,
                        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                        "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
                        "matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
                        "cudnn_allow_tf32": torch.backends.cudnn.allow_tf32}}
        resume = None
        if "resume_from" in request:
            resume = inspect(request["resume_from"], identity=identity,
                             expected_sha=request["resume_checkpoint_sha256"], pair_count=len(rows),
                             max_bytes=request["max_output_bytes"])
            require(resume["optimizer_step"] < request["stop_after_optimizer_step"],
                    "DPO_resume_no_remaining_steps")
        policy, reference = load_pair(request, lease)
        processor = AutoTokenizer.from_pretrained(request["model_root"], local_files_only=True,
                                                  trust_remote_code=False)
        require(processor.eos_token_id == offline.eos_token_id and processor.pad_token_id == 151643,
                "DPO_HF_tokenizer_special_tokens")
        frozen_before = {"policy_base": parameter_hash(policy, trainable=False),
                         "reference_all": parameter_hash(reference, trainable=False)}
        if resume is not None:
            validate_native_state(request["resume_from"], policy, resume)
        trainer, boundary = create_trainer(
            policy=policy, reference=reference, tokenizer=processor, rows=rows, expected=expected,
            config=config, output=output, identity=identity,
            stop_step=request["stop_after_optimizer_step"],
            checkpoint_every=request["checkpoint_every_steps"], max_bytes=request["max_output_bytes"],
        )
        require(trainer.accelerator.device.type == "cuda"
                and trainer.accelerator.mixed_precision == "bf16", "DPO_CUDA_BF16_AMP_required")

        class MemoryCheck(TrainerCallback):
            def on_step_end(self, args, state, control, **kwargs):
                entry = {"optimizer_step": state.global_step, **memory(config)}
                with (output / "memory.jsonl").open("ab") as stream:
                    stream.write(encoded(entry) + b"\n")
                    stream.flush()

        trainer.add_callback(MemoryCheck())
        memory(config)
        trainer.train(resume_from_checkpoint=request.get("resume_from"))
        require(trainer.state.global_step == request["stop_after_optimizer_step"]
                and boundary.manifests[-1]["optimizer_step"] == trainer.state.global_step,
                "DPO_segment_incomplete")
        frozen_after = {"policy_base": parameter_hash(policy, trainable=False),
                        "reference_all": parameter_hash(reference, trainable=False)}
        require(frozen_before == frozen_after, "DPO_frozen_parameters_changed")
        adapter_after = parameter_hash(policy)
        require(boundary.adapter_before != adapter_after, "DPO_adapter_did_not_update")
        return {"status": "PASS", "run_id": request["run_id"], "run_kind": request["run_kind"],
                "identity": identity, "optimizer_step": trainer.state.global_step,
                "data_cursor": boundary.events[-1]["data_cursor"],
                "epoch_complete": request["run_kind"] == "dpo" and trainer.state.epoch == 1.0,
                "diagnostic_only": request["run_kind"] == "dpo_capacity",
                "consumed_preference_ids": trainer.consumed, "precision": boundary.precision,
                "frozen_before": frozen_before, "frozen_after": frozen_after,
                "adapter_before_sha256": boundary.adapter_before,
                "adapter_sha256": adapter_after, "memory": memory(config),
                "checkpoint": f"checkpoint-{trainer.state.global_step}",
                "checkpoint_sha256": boundary.manifests[-1]["checkpoint_sha256"],
                "checkpoint_complete": True, "durability_verified": False}


def _child(request, sender):
    # Keep the outer controller's process group. A controller timeout must also
    # terminate this worker. DataLoader workers and Dataset multiprocessing are off.
    try:
        sender.send(execute(request))
    except BaseException as error:
        traceback.print_exc()
        sender.send({"status": "FAIL", "error": type(error).__name__ + ": " + str(error)[:2000]})
    finally:
        sender.close()


def output_size(root):
    total = 0
    for path in Path(root).rglob("*"):
        require(not path.is_symlink(), "DPO_output_symlink")
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            # Native Trainer rotates old checkpoints while the parent observes.
            continue
    return total


def supervise(request):
    validate_run(request)
    load_protocol(request["repository"])
    output = Path(request["output_dir"])
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    write_bytes(output / "run.json", encoded(request) + b"\n")
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(request, sender), name="toolalign-dpo")
    interrupted = None

    def interrupt(signum, frame):
        nonlocal interrupted
        interrupted = signum

    previous = {sig: signal.signal(sig, interrupt) for sig in (signal.SIGINT, signal.SIGTERM)}
    start = time.monotonic()
    result = {"status": "FAIL", "run_id": request["run_id"]}
    received = False
    try:
        process.start()
        sender.close()
        write_bytes(output / "process.json", encoded({"pid": process.pid}) + b"\n")
        deadline = start + request["max_wall_seconds"]
        while process.is_alive():
            require(interrupted is None, "DPO_interrupted")
            require(time.monotonic() < deadline, "DPO_wall_budget_exceeded")
            require(output_size(output) <= request["max_output_bytes"], "DPO_output_budget_exceeded")
            # Drain the pipe before join: the complete identity can exceed a
            # pipe buffer, and a child sending it must not deadlock on join().
            if receiver.poll(0.1):
                result = receiver.recv()
                received = True
                break
        process.join(timeout=max(0, min(1, deadline - time.monotonic())))
        require(interrupted is None, "DPO_interrupted")
        require(not process.is_alive() and process.exitcode == 0, "DPO_worker_exit")
        if not received and receiver.poll():
            result = receiver.recv()
        require(output_size(output) <= request["max_output_bytes"], "DPO_output_budget_exceeded")
        require(result.get("status") == "PASS", result.get("error", "DPO_worker_missing_result"))
    except (Exception, KeyboardInterrupt) as error:
        result = {"status": "FAIL", "run_id": request["run_id"],
                  "error": type(error).__name__ + ": " + str(error)[:2000]}
    finally:
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        try:
            if process.pid is not None and process.is_alive():
                process.terminate()
                process.join(3)
                if process.is_alive():
                    process.kill()
                    process.join(3)
            result.update(elapsed_seconds=time.monotonic() - start,
                          worker_exit_code=process.exitcode, interrupted_signal=interrupted)
            sender.close()
            receiver.close()
            process.close()
            write_bytes(output / "summary.json", encoded(result) + b"\n")
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    return result
