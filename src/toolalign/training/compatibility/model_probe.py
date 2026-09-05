"""Bounded adapters around upstream trainers; no standalone training framework.

This module is imported only inside the leased worker. It provides diagnostics,
not a P04/P05 TrainingBackend and never interprets or executes model output.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from dataclasses import asdict
from pathlib import Path

from .core import (
    Budget,
    BudgetExceeded,
    ReferenceIdentity,
    digest,
    file_hash,
    padded_batch,
    verify_adapter_metadata,
    verify_reload,
    write_json,
)
from .execution import measure_checkpoint_io, preserve_wired_limit
from .numerical import mlx_completion_ce, mlx_completion_logps, mlx_standard_dpo
from .samples import encode_sample, smoke_samples


def run_model_probe(config: dict, root: Path) -> dict:
    # Every optional/model import is deliberately below the GPULease boundary.
    import mlx.core as mx
    import mlx.optimizers as optim
    import numpy as np
    from mlx.utils import tree_flatten
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    from mlx_lm.tuner.trainer import TrainingArgs, train
    from mlx_lm.tuner.utils import linear_to_lora_layers

    budget = Budget(**config["budget"])
    budget.validate()
    started = time.monotonic()
    mx.set_default_device(mx.gpu)
    if not mx.metal.is_available():
        raise RuntimeError("Metal is unavailable")
    if config.get("fallback_disable_compile", False):
        # Reference and policy must share this execution mode from load through reload.
        mx.disable_compile()
    mx.random.seed(42)
    np.random.seed(42)
    mx.reset_peak_memory()
    events = []
    progress = {
        "training_tokens": 0,
        "optimizer_steps": 0,
        "microsteps": 0,
        "processed_tokens": 0,
        "processed_nonpadding_tokens": 0,
        "reference_model_hash": None,
    }
    result = {
        "status": "RUNNING",
        "metal_available": True,
        "phases": {},
        "complete_task_inference": {
            "status": "NOT_RUN",
            "reason": "P03 harness not merged",
            "future_entry": "ModelBackend.generate + TaskOracle.score",
        },
    }

    def flush():
        write_json(root / "progress.json", progress)
        write_json(root / "events.json", events)
        write_json(root / "partial-result.json", result)

    def check():
        mx.synchronize()
        budget.check(
            wall=time.monotonic() - started,
            microsteps=progress["microsteps"],
            processed_tokens=progress["processed_tokens"],
            mlx_bytes=mx.get_peak_memory(),
        )
        flush()

    def timed(name, operation):
        check()
        begin = time.perf_counter()
        value = operation()
        mx.synchronize()
        elapsed = time.perf_counter() - begin
        events.append({"event": name, "seconds": elapsed, "mlx_peak_bytes": mx.get_peak_memory()})
        check()
        return value, elapsed

    def parameter_hashes(model):
        hashes = {}
        for name, value in tree_flatten(model.parameters()):
            mx.eval(value)
            raw = np.array(value.view(mx.uint8)).tobytes()
            hashes[name] = hashlib.sha256(raw).hexdigest()
        return hashes

    def score(model, row):
        ids, masks = padded_batch([row], pad_id=tokenizer.pad_token_id, limit=limit)
        lp = mlx_completion_logps(model, mx.array(ids), mx.array(masks))
        mx.eval(lp)
        return lp.item()

    def forward_vector(model, row):
        logits = model(mx.array([row.token_ids[: row.prompt_length]]))[:, -1, :].astype(mx.float32)
        mx.eval(logits)
        return np.array(logits).reshape(-1).tolist()

    def generate(model, row, max_tokens=32):
        model.eval()
        begin = time.perf_counter()
        tokens = []
        final = None
        for response in stream_generate(
            model,
            tokenizer,
            prompt=list(row.token_ids[: row.prompt_length]),
            max_tokens=max_tokens,
            sampler=make_sampler(temp=0),
        ):
            mx.eval(response.logprobs)
            tokens.append(response.token)
            final = response
            if time.perf_counter() - begin > 30:
                raise BudgetExceeded("generation_request_wall")
            check()
        mx.synchronize()
        if final is None:
            raise RuntimeError("Generation produced no response")
        return {
            "tokens": tokens,
            "text": tokenizer.decode(tokens),
            "wall_seconds": time.perf_counter() - begin,
            "prompt_tokens": final.prompt_tokens,
            "generated_tokens": final.generation_tokens,
            "prompt_tps": final.prompt_tps,
            "generation_tps": final.generation_tps,
            "finish_reason": final.finish_reason,
        }

    model, load_seconds = timed(
        "load_original",
        lambda: load(config["model_dir"], tokenizer_config={"trust_remote_code": False}),
    )
    model, tokenizer = model
    limit = config["sequence_length"]
    if limit not in {1024, 1536, 2048}:
        raise ValueError("Sequence bucket not preregistered")
    samples = smoke_samples()
    if config["mode"] == "calibrate":
        # Deterministic synthetic context padding, NOT a claim about P02 length distribution.
        # Binary search fills user context near the bucket while preserving schemas/output.
        for sample in samples:
            original = sample["messages"][1]["content"]
            low, high = 0, limit
            while low < high:
                middle = (low + high + 1) // 2
                sample["messages"][1]["content"] = original + " Context:" + " neutral" * middle
                try:
                    encode_sample(tokenizer, sample, limit - 64)
                    low = middle
                except ValueError as exc:
                    if "exceeds budget" not in str(exc):
                        raise
                    high = middle - 1
            sample["messages"][1]["content"] = original + " Context:" + " neutral" * low
    rows = [encode_sample(tokenizer, sample, limit) for sample in samples]
    write_json(root / "samples.json", samples)
    write_json(
        root / "token-audit.json",
        [
            dict(
                asdict(row),
                id=sample["id"],
                kind=sample["kind"],
                supervised_text=tokenizer.decode(list(row.token_ids[row.prompt_length :])),
                prompt_tail=tokenizer.decode(
                    list(row.token_ids[max(0, row.prompt_length - 16) : row.prompt_length])
                ),
            )
            for sample, row in zip(samples, rows)
        ],
    )
    result["data_hash"] = digest(samples)
    # The actual calibrated data, not the unextended smoke fixture, binds the run.
    run_record = json.loads((root / "run.json").read_text())
    run_record["data_manifest_hash"] = result["data_hash"]
    write_json(root / "run.json", run_record)
    result["token_audit"] = {
        "samples": len(rows),
        "min_length": min(len(x.token_ids) for x in rows),
        "max_length": max(len(x.token_ids) for x in rows),
        "supervised_tokens": sum(sum(x.completion_mask) for x in rows),
        "thinking": False,
        "eos_supervised": True,
        "history_assistant_supervised": False,
        "length_distribution": "synthetic capacity fixture"
        if config["mode"] == "calibrate"
        else "32 original training smoke cases",
    }
    result["phases"]["load_seconds"] = load_seconds
    lora = {
        "rank": 8,
        "scale": 2.0,
        "dropout": 0.0,
        "keys": ["self_attn.q_proj", "self_attn.v_proj"],
    }
    model.freeze()
    linear_to_lora_layers(model, len(model.layers), lora)
    model.eval()
    adapter_config = {
        "fine_tune_type": "lora",
        "num_layers": len(model.layers),
        "lora_parameters": lora,
    }
    adapter_root = root / "sft-adapter"
    adapter_root.mkdir()
    write_json(adapter_root / "adapter_config.json", adapter_config)
    initial_hashes, _ = timed("hash_parameters_before", lambda: parameter_hashes(model))
    declared = set(dict(tree_flatten(model.trainable_parameters())))
    if not declared or any(
        not (key.endswith("lora_a") or key.endswith("lora_b")) for key in declared
    ):
        raise ValueError("Unexpected trainable parameters")
    write_json(root / "parameter-identities-before.json", initial_hashes)
    base_vector, _ = timed("original_forward", lambda: forward_vector(model, rows[0]))
    before, before_seconds = timed(
        "sft_validation_before", lambda: [score(model, row) for row in rows]
    )
    steps = config["sft_steps"]
    accumulation = config.get("sft_accumulation", 8)
    if steps % accumulation:
        raise ValueError("Do not silently drop the final accumulation remainder")
    reports = []
    iteration_start = 0.0
    active_row = None
    optimizer = optim.Adam(learning_rate=1e-4)

    def batches(dataset, batch_size, max_seq_length, loop, comm_group):
        nonlocal iteration_start, active_row
        if batch_size != 1 or comm_group.size() != 1:
            raise ValueError("P01 only supports one local microbatch")
        for i in range(steps):
            active_row = dataset[i % len(dataset)]
            ids, masks = padded_batch(
                [active_row],
                pad_id=tokenizer.pad_token_id,
                limit=max_seq_length,
                pad_to=limit if config["mode"] == "calibrate" else None,
            )
            # Check the NEXT complete work unit before yielding, not after an overshoot.
            budget.check(
                wall=time.monotonic() - started,
                microsteps=progress["microsteps"] + 1,
                processed_tokens=progress["processed_tokens"] + len(ids[0]) - 1,
            )
            iteration_start = time.perf_counter()
            yield mx.array(ids), mx.array(masks)

    def loss(actual_model, ids, masks):
        return mlx_completion_ce(actual_model(ids[:, :-1]), ids, masks), masks[:, 1:].sum()

    class Callback:
        def on_train_loss_report(self, info):
            mx.synchronize()
            seconds = time.perf_counter() - iteration_start
            if not math.isfinite(info["train_loss"]):
                raise ValueError("Nonfinite training loss")
            progress["microsteps"] += 1
            progress["training_tokens"] += sum(active_row.completion_mask)
            progress["processed_tokens"] += (
                limit if config["mode"] == "calibrate" else len(active_row.token_ids)
            ) - 1
            progress["processed_nonpadding_tokens"] += len(active_row.token_ids) - 1
            progress["optimizer_steps"] = int(optimizer.step.item())
            reports.append(
                {
                    **info,
                    "synchronized_seconds": seconds,
                    "processed_tokens": (
                        limit if config["mode"] == "calibrate" else len(active_row.token_ids)
                    )
                    - 1,
                    "nonpadding_tokens": len(active_row.token_ids) - 1,
                    "supervised_tokens": sum(active_row.completion_mask),
                    "optimizer_steps": progress["optimizer_steps"],
                }
            )
            write_json(root / "sft-steps.json", reports)
            check()

    args = TrainingArgs(
        batch_size=1,
        iters=steps,
        val_batches=0,
        steps_per_report=1,
        steps_per_save=max(steps, 1),
        max_seq_length=limit,
        adapter_file=str(adapter_root / "adapters.safetensors"),
        grad_checkpoint=config.get("grad_checkpoint", False),
        grad_accumulation_steps=accumulation,
        clear_cache_threshold=1024**3,
    )
    with preserve_wired_limit(mx, events), measure_checkpoint_io(mx, events, "sft"):
        _, train_seconds = timed(
            "sft_trainer_total",
            lambda: train(
                model,
                optimizer,
                train_dataset=rows,
                args=args,
                loss=loss,
                iterate_batches=batches,
                training_callback=Callback(),
            ),
        )
    model.eval()
    after, after_seconds = timed(
        "sft_validation_after", lambda: [score(model, row) for row in rows]
    )
    final_hashes, _ = timed("hash_parameters_after", lambda: parameter_hashes(model))
    changed = {key for key in initial_hashes if initial_hashes[key] != final_hashes[key]}
    if not changed or changed - declared:
        raise ValueError("Adapter did not update or frozen base was modified")
    write_json(root / "parameter-identities-after.json", final_hashes)
    denominator = sum(sum(row.completion_mask) for row in rows)
    before_loss, after_loss = -sum(before) / denominator, -sum(after) / denominator
    warmup = config.get("warmup_steps", 8)
    measured = reports[warmup:]
    durations = [r["synchronized_seconds"] for r in measured]
    result["sft"] = {
        "status": "PASS",
        "backend": "mlx-lm.train with explicit masks",
        "loss_before": before_loss,
        "loss_after": after_loss,
        "loss_decreased": after_loss < before_loss,
        "microsteps": len(reports),
        "optimizer_steps": int(optimizer.step.item()),
        "warmup_microsteps": min(warmup, len(reports)),
        "measured_microsteps": len(measured),
        "measured_seconds": sum(durations),
        "warmup_seconds": sum(r["synchronized_seconds"] for r in reports[:warmup]),
        "step_seconds_min": min(durations) if durations else None,
        "step_seconds_median": statistics.median(durations) if durations else None,
        "step_seconds_max": max(durations) if durations else None,
        "step_seconds_mean": statistics.mean(durations) if durations else None,
        "step_seconds_stdev": statistics.stdev(durations) if len(durations) > 1 else None,
        "trainer_wall_seconds": train_seconds,
        "validation_before_seconds": before_seconds,
        "validation_after_seconds": after_seconds,
        "changed_parameter_count": len(changed),
        "declared_trainable_count": len(declared),
        "frozen_parameters_unchanged": True,
        "adapter_metadata": adapter_config,
        "optimizer": "Adam",
        "learning_rate": 1e-4,
        "gradient_accumulation": accumulation,
        "grad_checkpoint": args.grad_checkpoint,
    }
    post_vector, _ = timed("sft_forward", lambda: forward_vector(model, rows[0]))
    result["sft"]["base_forward_max_abs_change"] = max(
        abs(a - b) for a, b in zip(base_vector, post_vector)
    )
    generated_before_reload, _ = timed("sft_generate", lambda: generate(model, rows[0]))
    write_json(root / "generation-before-reload.json", generated_before_reload)
    # Frozen reference is this exact local SFT smoke snapshot, never the original model.
    identity = ReferenceIdentity(
        config["model_identity"]["model_hash"],
        file_hash(adapter_root / "adapters.safetensors"),
        config["model_identity"]["tokenizer_hash"],
        config["model_identity"]["template_hash"],
        config["model_identity"]["quantization"],
        digest(
            {
                "source_hash": config["source_hash"],
                "dependencies": config["dependency_versions"],
                "compile_disabled": config.get("fallback_disable_compile", False),
            }
        ),
        "sft_smoke",
    )
    identity.validate(smoke_only=True)
    progress["reference_model_hash"] = digest(asdict(identity))
    write_json(root / "sft-reference.json", asdict(identity))
    # Load using the actual second library, not by assigning the old object.
    from mlx_tune.model import MLXModelWrapper

    fresh, reload_seconds = timed(
        "cross_library_base_load",
        lambda: load(config["model_dir"], tokenizer_config={"trust_remote_code": False}),
    )
    fresh_model, second_tokenizer = fresh
    fresh_model.freeze()
    wrapper = MLXModelWrapper(
        fresh_model,
        second_tokenizer,
        max_seq_length=limit,
        model_name=config["model_dir"],
        config=asdict(model.args),
    )
    wrapper.configure_lora(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"], lora_dropout=0)
    _, adapter_load_seconds = timed(
        "cross_library_adapter_load", lambda: wrapper.load_adapter(str(adapter_root))
    )
    policy = wrapper.model
    policy.eval()
    second_rows = [encode_sample(second_tokenizer, sample, limit) for sample in samples]
    if second_rows != rows:
        raise ValueError("Cross-library tokenizer/template changed")
    paths2 = set(dict(tree_flatten(policy.trainable_parameters())))
    if paths2 != declared:
        raise ValueError("Cross-library trainable targets changed")
    policy_hashes, _ = timed("cross_library_hash", lambda: parameter_hashes(policy))
    if policy_hashes != final_hashes:
        raise ValueError("Cross-library parameters differ after load")
    for path, module in policy.named_modules():
        if hasattr(module, "lora_a"):
            verify_adapter_metadata(
                {**lora, "num_layers": len(model.layers)},
                {
                    **lora,
                    "scale": module.scale,
                    "rank": module.lora_a.shape[1],
                    "num_layers": len(policy.layers),
                },
            )
    vector2, _ = timed("cross_library_forward", lambda: forward_vector(policy, rows[0]))
    forward_error = verify_reload(post_vector, vector2, 1e-5)
    scores2, _ = timed("cross_library_logps", lambda: [score(policy, row) for row in rows[:4]])
    lp_error = verify_reload(after[:4], scores2, 1e-5)
    generated_after_reload, _ = timed("cross_library_generate", lambda: generate(policy, rows[0]))
    if generated_after_reload["tokens"] != generated_before_reload["tokens"]:
        raise ValueError("Greedy generation changed after adapter reload")
    result["cross_library"] = {
        "status": "PASS",
        "loader": "mlx_tune.MLXModelWrapper.load_adapter",
        "max_logit_abs_error": forward_error,
        "max_logp_abs_error": lp_error,
        "atol": 1e-5,
        "tokenizer_template_identical": True,
        "trainable_paths_identical": True,
        "all_parameter_hashes_identical": True,
        "greedy_tokens_identical": True,
        "base_reload_seconds": reload_seconds,
        "adapter_load_seconds": adapter_load_seconds,
    }
    result["generation"] = [
        {k: v for k, v in x.items() if k not in {"tokens", "text"}}
        for x in [generated_before_reload, generated_after_reload]
    ]
    # Freeze the separately held SFT model; precompute explicit completion-only cache.
    model.freeze()
    preference_samples = []
    preference_rows = []
    for sample, row in zip(samples[:2], rows[:2]):
        rejected_sample = {**sample, "completion": "I cannot determine the result."}
        rejected_row = encode_sample(tokenizer, rejected_sample, limit)
        preference_samples.append(
            {
                "prompt": tokenizer.decode(list(row.token_ids[: row.prompt_length])),
                "chosen": sample["completion"] + tokenizer.eos_token,
                "rejected": rejected_sample["completion"] + tokenizer.eos_token,
            }
        )
        preference_rows.append((row, rejected_row))
    refs, reference_seconds = timed(
        "reference_precompute",
        lambda: [(score(model, c), score(model, r)) for c, r in preference_rows],
    )
    write_json(
        root / "reference-cache.json",
        [
            {"key": identity.cache_key(c, r), "chosen_logp": pair[0], "rejected_logp": pair[1]}
            for (c, r), pair in zip(preference_rows, refs)
        ],
    )
    # Diagnose the actual primary candidate's initial objective before any DPO update.
    from mlx_tune.losses import compute_log_probs_with_lengths, dpo_loss

    margins = []
    backend_ln2 = []
    correct_ln2 = []
    for (c, r), ref in zip(preference_rows, refs):
        ci, cm = padded_batch([c], tokenizer.pad_token_id, limit)
        ri, rm = padded_batch([r], tokenizer.pad_token_id, limit)
        cids, rids = mx.array(ci), mx.array(ri)
        fullc = compute_log_probs_with_lengths(policy, cids, mx.array([len(c.token_ids)]))
        fullr = compute_log_probs_with_lengths(policy, rids, mx.array([len(r.token_ids)]))
        native_loss = dpo_loss(
            policy,
            cids,
            rids,
            mx.array([len(c.token_ids)]),
            mx.array([len(r.token_ids)]),
            reference_chosen_logprobs=fullc,
            reference_rejected_logprobs=fullr,
            prompt_length=c.prompt_length,
            chosen_length_py=len(c.token_ids),
            rejected_length_py=len(r.token_ids),
        )[0]
        pc = mlx_completion_logps(policy, cids, mx.array(cm))
        pr = mlx_completion_logps(policy, rids, mx.array(rm))
        loss0 = mlx_standard_dpo(pc, pr, mx.array([ref[0]]), mx.array([ref[1]]))
        mx.eval(native_loss, loss0, fullc, fullr)
        backend_ln2.append(native_loss.item())
        correct_ln2.append(loss0.item())
        margins.append(
            {
                "full_cache_margin": (fullc - fullr).item(),
                "completion_cache_margin": ref[0] - ref[1],
                "upstream_logp_dtype": str(fullc.dtype),
            }
        )
    if any(abs(x - math.log(2)) > 2e-6 for x in correct_ln2):
        raise ValueError("Policy differs from explicit SFT reference at DPO initialization")
    result["reference"] = {
        "status": "PASS",
        "stage": "sft_smoke",
        "formal_sft_accepted": False,
        "precompute_seconds": reference_seconds,
        "pairs": len(refs),
        "initial_ln2": correct_ln2,
        "primary_native_initial_losses": backend_ln2,
        "native_margin_diagnostics": margins,
        "identity_hash": digest(asdict(identity)),
        "full_reference_parameters_frozen": True,
    }
    native_tolerance = 0.02  # model BF16 path; stricter CPU formula tolerance is 2e-6
    result["dpo"] = {
        "status": "NOT_RUN",
        "reason": "Awaiting native initialization gate",
        "native_initial_loss_atol": native_tolerance,
    }
    if any(abs(x - math.log(2)) > native_tolerance for x in backend_ln2):
        result["dpo"] = {
            "status": "FAIL",
            "microsteps": 0,
            "optimizer_steps": 0,
            "reason": "Native full-reference/shared-completion BF16 path fails initial ln2 gate",
            "native_initial_loss_atol": native_tolerance,
        }
    result["primary_dpo"] = dict(result["dpo"])
    if config.get("dpo_backend") == "mlx-lm-lora":
        # Free the first migration's policy before loading the sole fallback policy.
        import gc

        from .fallback_probe import run_fallback

        wrapper.model = None
        policy = None
        fresh_model = None
        fresh = None
        gc.collect()
        mx.clear_cache()
        result["dpo"] = run_fallback(
            config,
            root,
            model,
            preference_rows,
            refs,
            identity,
            adapter_config,
            final_hashes,
            parameter_hashes,
            progress,
            events,
            check,
            timed,
        )
    result["checkpoint_io"] = {
        phase: sum(
            event["seconds"]
            for event in events
            if event.get("event") == "checkpoint_write" and event.get("phase") == phase
        )
        for phase in ("sft", "dpo")
    }
    result["phase_seconds"] = {
        event["event"]: event["seconds"]
        for event in events
        if "seconds" in event and event["event"] != "checkpoint_write"
    }
    result["mlx_peak_bytes"] = mx.get_peak_memory()
    result["progress"] = progress
    result["status"] = "PASS" if result["dpo"]["status"] != "FAIL" else "PARTIAL"
    check()
    # Release tensor/model references and allocator cache before the leased callback returns.
    mx.synchronize()
    return result
