"""Restore two independent models from the selected G3 SFT state."""

from __future__ import annotations

from pathlib import Path

from toolalign.model_io.cuda_generation import (
    ADAPTER_SHA256,
    CHECKPOINT_SHA256,
    MODEL_ID,
    MODEL_REVISION,
    SFT_SOURCE_COMMIT,
    restore_adapter,
)
from toolalign.training.cuda_sft.checkpoint import deserialize, inspect_checkpoint
from toolalign.training.cuda_sft.engine import load_model
from toolalign.training.cuda_sft.protocol import CONFIG_SHA256, document, load_protocol, require


def restore_pair(policy, reference, adapter, *, expected_hash):
    require(policy is not reference, "independent_reference_required")
    restore_adapter(policy, adapter, expected_hash=expected_hash)
    restore_adapter(reference, adapter, expected_hash=expected_hash)
    left, right = dict(policy.named_parameters()), dict(reference.named_parameters())
    require(set(left) == set(right), "reference_parameter_names")
    require(all(left[name].shape == right[name].shape and left[name].dtype == right[name].dtype
                and left[name].data_ptr() != right[name].data_ptr() for name in left),
            "reference_parameter_storage")
    reference.requires_grad_(False)
    reference.gradient_checkpointing_disable()
    reference.eval()
    return policy, reference


def load_pair(request, lease):
    root = Path(request["sft_checkpoint_dir"])
    manifest = document(root / "manifest.json")
    identity = manifest["identity"]
    require(identity["source"]["commit"] == SFT_SOURCE_COMMIT
            and identity["config_identity"] == CONFIG_SHA256
            and identity["run_kind"] == "sft" and identity["profile"] == "formal"
            and identity["model_identity"]["model_id"] == MODEL_ID
            and identity["model_identity"]["revision"] == MODEL_REVISION,
            "selected_SFT_identity")
    manifest, contents = inspect_checkpoint(root, identity=identity, expected_sha=CHECKPOINT_SHA256)
    require(manifest["best"]["checkpoint_sha256"] == CHECKPOINT_SHA256,
            "selected_SFT_best_checkpoint")
    state = deserialize(contents["state.pt"], identity=identity, train_count=5938,
                        manifest=manifest, device="cuda:0")
    require(state["optimizer_step"] == 743 and state["data_cursor"] == 5938, "selected_SFT_step")
    spec = load_protocol(request["repository"])
    loader_request = {"repository": request["repository"], "model_root": request["model_root"],
                      "profile": "formal"}
    policy = load_model(loader_request, spec, lease)
    reference = load_model(loader_request, spec, lease)
    # No SFT optimizer is applied. Native DPO Trainer creates fresh Adam state.
    return restore_pair(policy, reference, state["adapter"], expected_hash=ADAPTER_SHA256)
