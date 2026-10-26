"""Seal native Trainer checkpoints only after all of its state has been saved."""

from __future__ import annotations

import os
from pathlib import Path

from toolalign.training.cuda_sft.protocol import (
    canonical_sha,
    document,
    encoded,
    read_bytes,
    require,
    sha,
    write_bytes,
)

MANIFEST = "dpo-manifest.json"
REQUIRED = {
    "adapter_config.json", "adapter_model.safetensors", "optimizer.pt", "scheduler.pt",
    "rng_state.pth", "trainer_state.json", "training_args.bin",
}


def inventory(root, max_bytes):
    files, total = {}, 0
    for path in sorted(Path(root).rglob("*")):
        require(not path.is_symlink(), "checkpoint_symlink")
        if path.is_dir() or path.name == MANIFEST:
            continue
        raw = read_bytes(path, limit=max_bytes)
        total += len(raw)
        require(total <= max_bytes, "checkpoint_byte_budget")
        files[path.relative_to(root).as_posix()] = {"bytes": len(raw), "sha256": sha(raw)}
    require(REQUIRED <= set(files), "incomplete_native_checkpoint")
    return files


def seal(root, *, identity, step, pair_count, max_bytes):
    root = Path(root)
    state = document(root / "trainer_state.json")
    total_steps = (pair_count + 7) // 8
    require(state["global_step"] == step and state["max_steps"] == total_steps
            and 0 < step <= total_steps, "native_checkpoint_step")
    manifest = {"schema": "toolalign.cuda-dpo-checkpoint.v1", "complete": True,
                "identity": identity, "optimizer_step": step,
                "data_cursor": min(step * 8, pair_count), "pair_count": pair_count,
                "total_optimizer_steps": total_steps, "files": inventory(root, max_bytes)}
    manifest["checkpoint_sha256"] = canonical_sha(manifest)
    # The manifest is the commit marker. A crash before this rename is incomplete.
    temporary = root / ".dpo-manifest.tmp"
    write_bytes(temporary, encoded(manifest) + b"\n")
    os.replace(temporary, root / MANIFEST)
    descriptor = os.open(root, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return manifest


def inspect(root, *, identity, expected_sha, pair_count, max_bytes):
    root = Path(root)
    manifest = document(root / MANIFEST, limit=4 * 1024**2)
    require(manifest.get("schema") == "toolalign.cuda-dpo-checkpoint.v1"
            and manifest.get("complete") is True, "incomplete_DPO_checkpoint")
    body = {key: value for key, value in manifest.items() if key != "checkpoint_sha256"}
    require(expected_sha == manifest["checkpoint_sha256"] == canonical_sha(body),
            "DPO_checkpoint_hash")
    require(manifest["identity"] == identity and manifest["pair_count"] == pair_count,
            "DPO_checkpoint_identity")
    step = manifest["optimizer_step"]
    require(type(step) is int and 0 < step <= (pair_count + 7) // 8
            and manifest["data_cursor"] == min(step * 8, pair_count)
            and manifest["total_optimizer_steps"] == (pair_count + 7) // 8,
            "DPO_checkpoint_cursor")
    require(inventory(root, max_bytes) == manifest["files"], "DPO_checkpoint_files")
    state = document(root / "trainer_state.json")
    require(state["global_step"] == step and state["max_steps"] == (pair_count + 7) // 8,
            "native_checkpoint_step")
    return manifest


def validate_native_state(root, model, manifest):
    """Reject partial adapter/Adam state before native Trainer resumes it."""
    import torch
    from peft import get_peft_model_state_dict
    from safetensors.torch import load_file
    from transformers.trainer import safe_globals

    root = Path(root)
    adapter = load_file(root / "adapter_model.safetensors")
    expected = get_peft_model_state_dict(model)
    require(set(adapter) == set(expected), "DPO_adapter_keys")
    for key, value in adapter.items():
        require(value.dtype == expected[key].dtype == torch.float32
                and value.shape == expected[key].shape and bool(torch.isfinite(value).all()),
                "DPO_adapter_shape_dtype_or_value")
    optimizer = torch.load(root / "optimizer.pt", map_location="cpu", weights_only=True)
    require(len(optimizer["param_groups"]) == 1, "DPO_optimizer_groups")
    group = optimizer["param_groups"][0]
    require(group["lr"] == 5e-6 and tuple(group["betas"]) == (0.9, 0.999)
            and group["eps"] == 1e-8 and group["weight_decay"] == 0
            and all(group[key] is False for key in (
                "foreach", "fused", "amsgrad", "maximize", "capturable", "differentiable")),
            "DPO_optimizer_settings")
    parameters = [p for p in model.parameters() if p.requires_grad]
    require(len(group["params"]) == len(parameters) == len(optimizer["state"])
            and set(group["params"]) == set(optimizer["state"]), "incomplete_DPO_Adam_state")
    for key, parameter in zip(group["params"], parameters, strict=True):
        moment = optimizer["state"][key]
        require(set(moment) == {"step", "exp_avg", "exp_avg_sq"}
                and float(moment["step"]) == manifest["optimizer_step"], "DPO_Adam_step")
        require(all(moment[name].shape == parameter.shape
                    and moment[name].dtype == torch.float32
                    and bool(torch.isfinite(moment[name]).all())
                    for name in ("exp_avg", "exp_avg_sq")), "DPO_Adam_moments")
    scheduler = torch.load(root / "scheduler.pt", map_location="cpu", weights_only=True)
    require(scheduler["last_epoch"] == manifest["optimizer_step"]
            and scheduler["base_lrs"] == [5e-6] and scheduler["_last_lr"] == [5e-6],
            "DPO_scheduler_state")
    with safe_globals():
        rng = torch.load(root / "rng_state.pth", map_location="cpu", weights_only=True)
    require({"python", "numpy", "cpu"} <= set(rng), "incomplete_DPO_RNG_state")
    if next(model.parameters()).device.type == "cuda":
        require("cuda" in rng, "missing_DPO_CUDA_RNG_state")
