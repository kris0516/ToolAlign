"""The sole fallback: upstream mlx-lm-lora trainer with an explicit label collator.

The upstream loop, optimizer and sigmoid DPO loss are used unchanged. Its module
iterator has no injection parameter, so replace only that function in this
single leased process and restore it in finally. No sequence chunking/QAT is used.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict

from .core import (
    Budget,
    assert_initial_dpo_loss,
    digest,
    file_hash,
    padded_batch,
    verify_adapter_metadata,
    verify_reload,
    write_json,
)
from .execution import measure_checkpoint_io, preserve_wired_limit
from .numerical import mlx_completion_logps


def fallback_masks(token_masks: list[list[int]]) -> list[list[int]]:
    """Upstream scores position i with mask[i] although the label is token[i+1]."""
    return [mask[1:] + [0] for mask in token_masks]


def run_fallback(
    config,
    root,
    reference,
    pairs,
    refs,
    identity,
    adapter_config,
    reference_hashes,
    parameter_hashes,
    progress,
    events,
    check,
    timed,
):
    import mlx.core as mx
    import mlx.optimizers as optim
    import numpy as np
    from mlx.utils import tree_flatten
    from mlx_lm_lora.trainer import dpo_trainer as backend
    from mlx_lm_lora.utils import from_pretrained

    if config.get("fallback_disable_compile", False):
        # Documented MLX diagnostic switch; confined to this leased process.
        mx.disable_compile()
        events.append(
            {"event": "mlx_compilation_disabled_for_fallback", "api": "mx.disable_compile"}
        )
    budget = Budget(**config["budget"])
    start = time.monotonic()
    limit = config["sequence_length"]
    adapter_root = root / "sft-adapter"
    loaded, load_seconds = timed(
        "fallback_load_sft",
        lambda: from_pretrained(config["model_dir"], adapter_path=str(adapter_root)),
    )
    policy, tokenizer, _ = loaded
    # The convenience loader doesn't freeze the original weights. Explicitly do so.
    policy.freeze()
    for _, module in policy.named_modules():
        if hasattr(module, "lora_a"):
            module.unfreeze(keys=["lora_a", "lora_b"], recurse=False)
    declared = set(dict(tree_flatten(policy.trainable_parameters())))
    expected_declared = {key for key in reference_hashes if key.endswith(("lora_a", "lora_b"))}
    if declared != expected_declared:
        raise ValueError("Fallback has unexpected trainable parameters")
    initial_hashes, _ = timed("fallback_import_hashes", lambda: parameter_hashes(policy))
    if initial_hashes != reference_hashes:
        raise ValueError("Fallback did not import the exact SFT checkpoint")
    for _, module in policy.named_modules():
        if hasattr(module, "lora_a"):
            if (
                module.scale != adapter_config["lora_parameters"]["scale"]
                or module.lora_a.shape[1] != 8
            ):
                raise ValueError("Fallback adapter scaling or rank mismatch")

    def forward_vector(model):
        row = pairs[0][0]
        value = model(mx.array([row.token_ids[: row.prompt_length]]))[:, -1, :].astype(mx.float32)
        mx.eval(value)
        return np.array(value).reshape(-1).tolist()

    reference_vector, _ = timed("fallback_reference_forward", lambda: forward_vector(reference))
    policy.eval()
    imported_vector, _ = timed("fallback_import_forward", lambda: forward_vector(policy))
    import_error = verify_reload(reference_vector, imported_vector, 1e-5)

    # Actual upstream loss/get_token_scores, including differing response lengths/padding.
    def batch_for(pair):
        chosen, rejected = pair
        if chosen.prompt_length != rejected.prompt_length or (
            chosen.token_ids[: chosen.prompt_length] != rejected.token_ids[: rejected.prompt_length]
        ):
            raise ValueError("Preference pair prompts differ")
        # Microbatch 1 permits separate chosen/rejected lengths, avoiding unnecessary
        # padding and shape-dependent BF16 rounding in the frozen reference cache.
        ci, cm = padded_batch([chosen], tokenizer.pad_token_id, limit)
        ri, rm = padded_batch([rejected], tokenizer.pad_token_id, limit)
        return (
            mx.array(ci),
            mx.array(ri),
            mx.array(fallback_masks(cm)),
            mx.array(fallback_masks(rm)),
        )

    def score_pair(actual, pair):
        ci, ri, cm, rm = batch_for(pair)
        cs = backend.get_token_scores(actual, ci, cm).sum(-1)
        rs = backend.get_token_scores(actual, ri, rm).sum(-1)
        mx.eval(cs, rs)
        return cs, rs, cm, rm

    initial_losses = []
    score_errors = []
    for pair, ref in zip(pairs, refs):
        cs, rs, cm, rm = score_pair(policy, pair)
        rc, rr, _, _ = score_pair(reference, pair)
        value = backend.dpo_loss(cs, rs, rc, rr, cm, rm, 0.1, 50.0, "sigmoid")[0]
        mx.eval(value)
        initial_losses.append(value.item())
        score_errors.append(max(abs(rc.item() - ref[0]), abs(rr.item() - ref[1])))
    write_json(
        root / "fallback-initial-gates.json",
        {
            "initial_losses": initial_losses,
            "reference_score_errors": score_errors,
            "compilation_disabled": config.get("fallback_disable_compile", False),
        },
    )
    if any(abs(v - math.log(2)) > 2e-6 for v in initial_losses):
        raise ValueError("Fallback initial DPO loss violates ln2 gate")
    # Padding can change BF16 kernel rounding; compare equal-shape policy/reference strictly,
    # and explicit unpadded cache using a separately declared 0.02 score tolerance.
    if max(score_errors) > 0.02:
        raise ValueError("Fallback scoring differs from explicit completion-only reference")
    steps = config["dpo_steps"]
    accumulation = config.get("fallback_accumulation", 8)
    if steps % accumulation:
        raise ValueError("Incomplete DPO gradient accumulation is forbidden")
    dpo_root = root / "fallback-dpo"
    dpo_root.mkdir()
    write_json(dpo_root / "adapter_config.json", adapter_config)
    optimizer = optim.AdamW(learning_rate=5e-6)
    sft_optimizer_steps = progress["optimizer_steps"]
    reports = []
    batch_index = 0
    active_pair = None
    iteration_start = 0.0

    def batches(dataset, batch_size, max_seq_length, train=False):
        nonlocal batch_index, active_pair, iteration_start
        if batch_size != 1 or max_seq_length != limit or not train:
            raise ValueError("Unexpected fallback batch invocation")
        active_pair = pairs[batch_index % len(pairs)]
        batch_index += 1
        budget.check(
            wall=time.monotonic() - start,
            microsteps=progress["microsteps"] + 1,
            processed_tokens=progress["processed_tokens"]
            + sum(len(x.token_ids) - 1 for x in active_pair),
        )
        iteration_start = time.perf_counter()
        yield batch_for(active_pair)

    class Callback:
        def on_train_loss_report(self, info):
            mx.synchronize()
            record = {k: v.item() if hasattr(v, "item") else v for k, v in info.items()}
            failure = None
            try:
                if not math.isfinite(record["train_loss"]):
                    raise ValueError("Nonfinite fallback loss")
                if record["iteration"] <= accumulation:
                    assert_initial_dpo_loss(record["train_loss"])
            except ValueError as exc:
                failure = exc
            # The loss describes pre-update scoring, but upstream has already
            # evaluated this microstep and applied any boundary optimizer update
            # before calling us. A failed gate must not erase completed work.
            c, r = active_pair
            progress["microsteps"] += 1
            progress["training_tokens"] += sum(c.completion_mask) + sum(r.completion_mask)
            progress["processed_tokens"] += sum(len(x.token_ids) - 1 for x in active_pair)
            progress["processed_nonpadding_tokens"] += len(c.token_ids) + len(r.token_ids) - 2
            optimizer_steps = int(optimizer.step.item())
            progress["optimizer_steps"] = sft_optimizer_steps + optimizer_steps
            record.update(
                {
                    "synchronized_seconds": time.perf_counter() - iteration_start,
                    "optimizer_steps": optimizer_steps,
                    "processed_tokens": sum(len(x.token_ids) - 1 for x in active_pair),
                    "nonpadding_tokens": len(c.token_ids) + len(r.token_ids) - 2,
                    "supervised_tokens": sum(c.completion_mask) + sum(r.completion_mask),
                }
            )
            nonfinite = {
                key: repr(value) for key, value in record.items()
                if isinstance(value, float) and not math.isfinite(value)
            }
            if nonfinite:
                # JSON has no numeric NaN/Infinity. Retain their exact categories
                # separately, rather than losing the whole failure record.
                for key in nonfinite:
                    record[key] = None
                record["nonfinite_values"] = nonfinite
                if failure is None:
                    failure = ValueError("Nonfinite fallback report metric")
            if failure is not None:
                record["status"] = "failed"
                record["failure"] = {"type": type(failure).__name__, "message": str(failure)}
            reports.append(record)
            write_json(root / "fallback-dpo-steps.json", reports)
            write_json(root / "progress.json", progress)
            if failure is not None:
                raise failure
            check()

    args = backend.DPOTrainingArgs(
        batch_size=1,
        iters=steps,
        gradient_accumulation_steps=accumulation,
        steps_per_report=1,
        steps_per_save=steps,
        val_batches=0,
        max_seq_length=limit,
        adapter_file=str(dpo_root / "adapters.safetensors"),
        beta=0.1,
        grad_checkpoint=config.get("fallback_grad_checkpoint", False),
        seq_step_size=None,
        qat_enable=False,
    )
    original_iterator = backend.iterate_dpo_batches
    backend.iterate_dpo_batches = batches
    try:
        with preserve_wired_limit(mx, events), measure_checkpoint_io(mx, events, "dpo"):
            _, train_seconds = timed(
                "fallback_native_dpo_train",
                lambda: backend.train_dpo(
                    model=policy,
                    ref_model=reference,
                    optimizer=optimizer,
                    train_dataset=pairs,
                    args=args,
                    training_callback=Callback(),
                    loss_type="sigmoid",
                ),
            )
    finally:
        backend.iterate_dpo_batches = original_iterator
    if int(optimizer.step.item()) != steps // accumulation:
        raise ValueError("Fallback actual optimizer count differs from accumulation")
    after_hashes, _ = timed("fallback_policy_hashes_after", lambda: parameter_hashes(policy))
    changed = {k for k in initial_hashes if after_hashes[k] != initial_hashes[k]}
    if not changed or changed - declared:
        raise ValueError("Fallback changed frozen weights or did not update any adapter")
    frozen_after, _ = timed("fallback_reference_hashes_after", lambda: parameter_hashes(reference))
    if frozen_after != reference_hashes:
        raise ValueError("Fallback changed the SFT reference")
    identity.assert_unchanged(
        type(identity)(
            identity.base_hash,
            file_hash(adapter_root / "adapters.safetensors"),
            identity.tokenizer_hash,
            identity.template_hash,
            identity.quantization,
            identity.code_hash,
            identity.stage,
        )
    )
    policy.eval()
    after_losses = []
    for pair, ref in zip(pairs, refs):
        cs, rs, cm, rm = score_pair(policy, pair)
        rc, rr, _, _ = score_pair(reference, pair)
        value = backend.dpo_loss(cs, rs, rc, rr, cm, rm, 0.1, 50.0, "sigmoid")[0]
        mx.eval(value)
        after_losses.append(value.item())
        for row, cached in zip(pair, ref):
            ids, masks = padded_batch([row], tokenizer.pad_token_id, limit)
            actual = mlx_completion_logps(reference, mx.array(ids), mx.array(masks)).item()
            if actual != cached:
                raise ValueError("Reference logprobs drifted after optimization")
    post_vector, _ = timed("fallback_dpo_forward", lambda: forward_vector(policy))
    reloaded, reload_seconds = timed(
        "fallback_dpo_reload",
        lambda: from_pretrained(config["model_dir"], adapter_path=str(dpo_root)),
    )
    reloaded_model, reloaded_tokenizer, _ = reloaded
    reloaded_model.eval()
    reloaded_hashes, _ = timed(
        "fallback_dpo_reload_hashes", lambda: parameter_hashes(reloaded_model)
    )
    if reloaded_hashes != after_hashes:
        raise ValueError("Fallback save/reload parameters changed")
    vec2, _ = timed("fallback_dpo_reload_forward", lambda: forward_vector(reloaded_model))
    reload_error = verify_reload(post_vector, vec2, 1e-5)
    metadata = json.loads((dpo_root / "adapter_config.json").read_text())
    verify_adapter_metadata(
        {**adapter_config["lora_parameters"], "num_layers": adapter_config["num_layers"]},
        {**metadata["lora_parameters"], "num_layers": metadata["num_layers"]},
    )
    write_json(root / "fallback-reference-identity.json", asdict(identity))
    mx.synchronize()
    return {
        "status": "PASS",
        "backend": "mlx-lm-lora 3.1.2 train_dpo with explicit collator",
        "microsteps": len(reports),
        "optimizer_steps": int(optimizer.step.item()),
        "configured_accumulation": accumulation,
        "compilation_disabled": config.get("fallback_disable_compile", False),
        "gradient_checkpointing": config.get("fallback_grad_checkpoint", False),
        "training_path_initial_losses": [r["train_loss"] for r in reports[:accumulation]],
        "initial_ln2": initial_losses,
        "loss_after": after_losses,
        "wall_seconds": train_seconds,
        "measured_microsteps_after_first_warmup": max(0, len(reports) - 1),
        "measured_seconds_after_first_warmup": sum(r["synchronized_seconds"] for r in reports[1:]),
        "warmup_seconds": reports[0]["synchronized_seconds"] if reports else None,
        "reference_hash_and_outputs_unchanged": True,
        "reference_stage": "sft_smoke",
        "only_adapter_updated": True,
        "changed_parameters": len(changed),
        "import_max_logit_abs_error": import_error,
        "reload_max_logit_abs_error": reload_error,
        "reload_parameters_identical": True,
        "reload_atol": 1e-5,
        "ln2_atol": 2e-6,
        "unpadded_reference_score_abs_errors": score_errors,
        "score_atol": 0.02,
        "reference_identity_hash": digest(asdict(identity)),
        "formal_training": False,
        "loader": "mlx_lm_lora.utils.from_pretrained",
        "import_seconds": load_seconds,
        "reload_seconds": reload_seconds,
        "partial_accumulation": "rejected",
    }
