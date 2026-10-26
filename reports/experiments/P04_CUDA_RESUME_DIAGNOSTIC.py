"""Bounded, zero-update G2 gradient probe; run only under a separate S1 release.

The driver must also enforce an external deadline, e.g. GNU timeout with a
10-second kill grace. This single process owns the GPU lease and model.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import signal
import subprocess
from pathlib import Path

from toolalign.runtime.gpu_lock import GPULease, lock_path
from toolalign.training.cuda_sft.arrays import read_bundle
from toolalign.training.cuda_sft.checkpoint import (
    capture,
    deserialize,
    inspect_checkpoint,
    parameter_hash,
    restore,
    restore_rng,
    rng_state,
    serialize,
)
from toolalign.training.cuda_sft.engine import completion_ce, groups, load_model, make_optimizer
from toolalign.training.cuda_sft.protocol import (
    bounded_request,
    dependency_identity,
    document,
    encoded,
    load_protocol,
    require,
    sha,
    source_identity,
    write_bytes,
)
from toolalign.training.cuda_sft.runtime import _memory, require_cuda, rng_hash, runtime_identity

CASES = ("checkpoint_on_a", "checkpoint_on_b", "checkpoint_off_a", "checkpoint_off_b")
STATE_FIELDS = ("adapter", "optimizer", "constant_lr", "optimizer_step", "data_cursor",
                "python_rng", "numpy_rng", "torch_cpu_rng", "torch_cuda_rng")


def exact(left, right):
    import torch

    if isinstance(left, torch.Tensor):
        return (isinstance(right, torch.Tensor) and left.dtype == right.dtype
                and left.shape == right.shape and torch.equal(left.cpu(), right.cpu()))
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return list(left) == list(right) and all(exact(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(exact(a, b) for a, b in zip(left, right))
    return left == right


def compare_gradients(left, right):
    """Descriptive gradient differences, not a new numerical acceptance rule."""
    require(list(left) == list(right), "probe_gradient_order")
    rows, reference_sq, difference_sq = [], 0.0, 0.0
    for name, original in left.items():
        candidate = right[name]
        require(original.shape == candidate.shape and original.dtype == candidate.dtype,
                "probe_gradient_shape_dtype")
        reference, difference = original.double(), candidate.double() - original.double()
        ref_sq, diff_sq = float(reference.square().sum()), float(difference.square().sum())
        reference_sq += ref_sq
        difference_sq += diff_sq
        rows.append({"name": name, "exact": exact(original, candidate),
                     "max_abs": float(difference.abs().max()),
                     "relative_l2": math.sqrt(diff_sq / ref_sq) if ref_sq else None})
    return {"exact_tensor_count": sum(row["exact"] for row in rows), "tensor_count": len(rows),
            "max_abs": max(row["max_abs"] for row in rows),
            "relative_l2": math.sqrt(difference_sq / reference_sq) if reference_sq else None,
            "parameters": rows}


def backward_only(model, group, *, device):
    """The production CE and mean reduction, with no optimizer.step call."""
    import torch

    require(len(group) == 2, "probe_exact_two_examples")
    model.train()
    model.zero_grad(set_to_none=True)
    losses = []
    # Identical instrumentation in all four cases; record dispatch, not a large trace.
    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU]) as profile:
        for _, batch in group:
            total, count = completion_ce(model, batch, device=device)
            loss = total / count
            losses.append(float(loss.detach()))
            (loss / len(group)).backward()
    gradients = {}
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            require(parameter.grad is not None and bool(torch.isfinite(parameter.grad).all()),
                    "probe_missing_or_nonfinite_gradient")
            gradients[name] = parameter.grad.detach().cpu().clone()
    operators = {item.key: item.count for item in profile.key_averages()
                 if any(part in item.key for part in ("scaled_dot_product", "flash_attention",
                                                     "efficient_attention", "cudnn_attention"))}
    return gradients, {"per_example_loss": losses, "attention_operators": operators}


def validate_request(request):
    bounded_request(request, schema="toolalign.cuda-sft-resume-diagnostic.v1")
    require(request["run_kind"] == "capacity" and request["profile"] == "formal", "probe_profile")
    require(request.get("diagnostic_passes") == list(CASES)
            and request.get("max_optimizer_updates") == 0
            and request.get("max_backward_groups") == 4, "probe_fixed_scope")
    require(request["max_wall_seconds"] <= 300 and request["max_output_bytes"] <= 128 * 1024**2,
            "probe_resource_ceiling")
    require(request.get("validation_every_steps") == 2 and request.get("checkpoint_every_steps") == 2,
            "probe_original_cadence")
    for key in ("lock_root", "array_dir", "dependency_lock", "model_root", "checkpoint_dir"):
        require(type(request.get(key)) is str and Path(request[key]).is_absolute(), "probe_path:" + key)
    require(request.get("training_source_commit") == "97637f336df4299a4bfd59b06f9716bb3c104796",
            "probe_original_source")
    return request


def run(request):
    config = load_protocol(request["repository"])
    executing = source_identity(request["repository"], request["source_commit"])
    script = Path(__file__).read_bytes()
    require(script == subprocess.check_output(["git", "-C", request["repository"], "show",
            request["source_commit"] + ":reports/experiments/P04_CUDA_RESUME_DIAGNOSTIC.py"]),
            "probe_script_not_committed")
    checkpoint_path = Path(request["checkpoint_dir"])
    original_identity = document(checkpoint_path / "manifest.json")["identity"]
    original_source = original_identity["source"]
    require(original_source["commit"] == request["training_source_commit"]
            and executing["package_files"] == original_source["package_files"], "probe_training_source_changed")
    manifest, contents = inspect_checkpoint(checkpoint_path, identity=original_identity,
                                          expected_sha=request["checkpoint_sha256"])
    require(manifest["optimizer_step"] == 2 and manifest["data_cursor"] == 16, "probe_step2_required")
    dependencies = dependency_identity(request["dependency_lock"], request["dependency_lock_sha256"])
    bundle = read_bundle(request["array_dir"], expected_digest=request["array_manifest_sha256"], config=config)
    require(bundle.manifest["source"] == original_source and len(bundle.ids["train"]) == 18
            and len(bundle.ids["validation"]) == 2, "probe_original_capacity_arrays")
    group = next(groups(bundle.records("train"), cursor=16))
    require([name for name, _ in group] == bundle.ids["train"][16:], "probe_final_group")
    require(lock_path(request["lock_root"]) == lock_path(request["repository"]), "probe_shared_lock")
    root = Path(request["output_dir"])
    require(not root.exists(), "probe_output_exists")
    root.mkdir(mode=0o700, parents=False)

    def save(name, raw):
        size = sum(p.stat().st_size for p in root.iterdir() if p.is_file())
        require(size + len(raw) <= request["max_output_bytes"], "probe_output_budget")
        write_bytes(root / name, raw)
        return {"file": name, "bytes": len(raw), "sha256": sha(raw)}

    save("request.json", encoded(request) + b"\n")
    with GPULease(task_id="P04-CUDA-RESUME-001-DIAGNOSTIC", worker_alias="S1",
                  run_id=request["run_id"], expected_job="four_backward_groups_zero_updates",
                  memory_strategy="BF16_base_FP32_LoRA_20pct_headroom",
                  repository=request["lock_root"], timeout_seconds=0) as lease:
        require_cuda()
        import numpy as np
        import torch

        identity = runtime_identity(request, config, bundle, original_source, dependencies)
        require(identity == original_identity, "probe_runtime_identity_changed")
        state = deserialize(contents["state.pt"], identity=identity, train_count=18,
                            manifest=manifest, device="cuda:0")
        random.seed(config["training"]["seed"])
        np.random.seed(config["training"]["seed"])
        torch.manual_seed(config["training"]["seed"])
        torch.cuda.manual_seed(config["training"]["seed"])
        model = load_model(request, config, lease)
        optimizer = make_optimizer(model, config)
        step, cursor = restore(state, model, optimizer, device="cuda:0")
        restored = capture(model, optimizer, step=step, cursor=cursor, identity=identity, device="cuda:0")
        restoration = {key: exact(state[key], restored[key]) for key in STATE_FIELDS}
        names = [n for n, p in model.named_parameters() if p.requires_grad]
        restoration["parameter_order"] = names == list(state["adapter"])
        restored_artifact = save("restored-state.pt", serialize(restored))
        save("restoration.json", encoded({"checks": restoration, "parameter_order": names,
                                          "artifact": restored_artifact}) + b"\n")
        require(all(restoration.values()), "probe_physical_restore_mismatch:" +
                ",".join(key for key, ok in restoration.items() if not ok))
        adapter_before = parameter_hash(model)
        frozen_before = parameter_hash(model, trainable=False)
        require(frozen_before == request["frozen_base_sha256"], "probe_frozen_base_identity")
        records, gradients_by_case = [], {}
        for case in CASES:
            if case == "checkpoint_off_a":
                model.gradient_checkpointing_disable()
            require(model.is_gradient_checkpointing == case.startswith("checkpoint_on"), "probe_checkpoint_mode")
            restore_rng(state, device="cuda:0")
            rng_before = rng_hash(rng_state(device="cuda:0"))
            require(rng_before == rng_hash(state), "probe_rng_before_backward")
            torch.cuda.reset_peak_memory_stats(0)
            _memory(config)
            gradients, record = backward_only(model, group, device="cuda:0")
            torch.cuda.synchronize(0)
            artifact = save(case + ".pt", serialize({"gradients": gradients, "case": case,
                            "diagnostic_only": True, "optimizer_updates": 0}))
            record.update({"case": case, "gradient_checkpointing": model.is_gradient_checkpointing,
                           "artifact": artifact, "memory": _memory(config),
                           "rng_before": rng_before, "rng_after": rng_hash(rng_state(device="cuda:0"))})
            gradients_by_case[case] = gradients
            records.append(record)
            save(case + ".json", encoded(record) + b"\n")
            print(json.dumps({"case": case, "diagnostic_only": True, "optimizer_updates": 0}), flush=True)
        final = capture(model, optimizer, step=step, cursor=cursor, identity=identity, device="cuda:0")
        require(exact(final["adapter"], state["adapter"]) and exact(final["optimizer"], state["optimizer"]),
                "probe_state_mutated")
        require(parameter_hash(model) == adapter_before
                and parameter_hash(model, trainable=False) == frozen_before, "probe_weights_mutated")
        comparisons = {}
        for left, right in ((CASES[0], CASES[1]), (CASES[2], CASES[3]), (CASES[0], CASES[2])):
            comparisons[left + "__" + right] = compare_gradients(gradients_by_case[left], gradients_by_case[right])
        result = {"status": "COMPLETE", "diagnostic_only": True, "recovery_acceptance": "NOT_EVALUATED",
                  "optimizer_updates": 0, "backward_groups": 4, "microsteps": 8,
                  "source": executing, "diagnostic_script_sha256": sha(script), "original_identity": identity,
                  "checkpoint_sha256": manifest["checkpoint_sha256"], "example_ids": [n for n, _ in group],
                  "restoration": restoration, "restored_state": restored_artifact,
                  "parameter_order": names, "adapter_sha256": adapter_before, "frozen_base_sha256": frozen_before,
                  "state_unchanged": True, "cases": records, "comparisons": comparisons}
        save("summary.json", encoded(result) + b"\n")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    request = validate_request(document(args.request, limit=1024 * 1024))

    def expired(signum, frame):
        raise TimeoutError("probe_wall_budget")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(request["max_wall_seconds"])
    try:
        run(request)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


if __name__ == "__main__":
    main()
