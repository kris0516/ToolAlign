"""Shared tensor kernels for the real trainer and bounded original CPU fixtures."""

from __future__ import annotations

from itertools import islice

from toolalign.training.sft.collator import Batch
from toolalign.training.sft.validation import ValidationTotals

from .protocol import require


def groups(records, *, cursor=0, accumulation=8):
    require(type(cursor) is int and cursor >= 0 and accumulation == 8, "group_plan")
    iterator = iter(records)
    for _ in range(cursor):
        require(next(iterator, None) is not None, "cursor_past_data")
    while group := tuple(islice(iterator, accumulation)):
        yield group


def completion_ce(model, batch, *, device):
    """The Batch already shifts once. Never pass labels to an HF loss function."""
    import torch
    from torch.nn import functional as F

    require(type(batch) is Batch, "validated_batch_required")
    inputs = torch.tensor([batch.causal_input_ids], dtype=torch.long, device=device)
    attention = torch.tensor([batch.attention_mask[:-1]], dtype=torch.long, device=device)
    targets = torch.tensor(batch.causal_target_ids, dtype=torch.long, device=device)
    supervised = torch.tensor(batch.causal_loss_mask, dtype=torch.bool, device=device)
    logits = model(input_ids=inputs, attention_mask=attention, use_cache=False).logits
    require(logits.ndim == 3 and tuple(logits.shape[:2]) == (1, batch.bucket - 1), "logits_shape")
    # FP32 reduction; selecting supervised rows avoids a full-vocabulary FP32
    # copy for every prompt and padded token, with the same CE objective.
    ce_sum = F.cross_entropy(logits[0, supervised].float(), targets[supervised], reduction="sum")
    require(bool(torch.isfinite(ce_sum)), "nonfinite_training_loss")
    return ce_sum, batch.effective_supervised_targets


def make_optimizer(model, config):
    import torch

    optimizer = config["optimizer"]
    return torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=optimizer["learning_rate"], betas=tuple(optimizer["betas"]),
        eps=optimizer["eps"], weight_decay=optimizer["weight_decay"],
        foreach=optimizer["foreach"], fused=optimizer["fused"],
    )


def train_group(model, optimizer, group, *, device):
    import torch

    require(0 < len(group) <= 8, "accumulation_group_size")
    model.train()
    optimizer.zero_grad(set_to_none=True)
    losses = []
    for _, batch in group:
        total, tokens = completion_ce(model, batch, device=device)
        loss = total / tokens
        losses.append(float(loss.detach()))
        (loss / len(group)).backward()
    require(all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in model.parameters()),
            "nonfinite_gradient")
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    return {"microsteps": len(group), "per_example_loss": losses, "loss": sum(losses) / len(losses)}


def evaluate(model, records, *, expected_ids, profile, device):
    import torch

    totals = ValidationTotals(profile=profile, split="validation", expected_ids=expected_ids)
    training_modes = [(module, module.training) for module in model.modules()]
    model.eval()
    try:
        with torch.no_grad():
            for ident, batch in records:
                total, tokens = completion_ce(model, batch, device=device)
                totals.add(example_id=ident, profile=profile, split="validation",
                           ce_sum=float(total), tokens=tokens)
        return {"ce_sum": totals.numerator, "supervised_tokens": totals.denominator,
                "examples": totals.count, "validation_ce": totals.finish()}
    finally:
        for module, was_training in training_modes:
            module.training = was_training


def attach_adapter(base, config):
    """Official PEFT LoRA; exact production shape checks belong to the loader."""
    import torch
    from peft import LoraConfig, get_peft_model

    spec = config["model"]
    base.config.use_cache = False
    lora = LoraConfig(
        task_type="CAUSAL_LM", r=spec["rank"], lora_alpha=spec["lora_alpha"],
        target_modules=spec["targets"], layers_to_transform=list(range(spec["layers"])),
        layers_pattern="layers", lora_dropout=spec["lora_dropout"],
        use_rslora=spec["use_rslora"], bias="none", init_lora_weights=True,
    )
    model = get_peft_model(base, lora, autocast_adapter_dtype=True)
    for parameter in model.parameters():
        if parameter.requires_grad:
            parameter.data = parameter.data.to(dtype=torch.float32)
    model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": spec["gradient_checkpointing_use_reentrant"]})
    return model


def load_model(request, config, lease):
    """The sole real model loader, called inside the bounded leased process."""
    import torch
    from transformers import AutoModelForCausalLM

    from toolalign.model_io.qwen_model import require_current_lease, validate_model_files

    require_current_lease(lease, request["repository"])
    require(torch.cuda.is_available(), "CUDA_unavailable_no_fallback")
    require(torch.cuda.is_bf16_supported(), "CUDA_BF16_unavailable")
    spec = config["profiles"][request["profile"]]
    files = validate_model_files(request["model_root"], model_id=spec["model_id"],
                                 revision=spec["model_revision"],
                                 config_path=request["repository"] + "/configs/qwen-models.v1.json")
    base = AutoModelForCausalLM.from_pretrained(
        str(files.root), local_files_only=True, trust_remote_code=False,
        torch_dtype=torch.bfloat16, attn_implementation="sdpa", use_cache=False,
    )
    require(sum(p.numel() for p in base.parameters()) == files.expected_base_parameter_count,
            "base_parameter_count")
    model = attach_adapter(base, config)
    expected = {f"base_model.model.model.layers.{i}.self_attn.{target}"
                for i in range(config["model"]["layers"]) for target in config["model"]["targets"]}
    actual = {name for name, module in model.named_modules() if hasattr(module, "lora_A")}
    require(actual == expected and len(actual) == config["model"]["module_count"], "adapter_module_set")
    trainable = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
    require(sum(p.numel() for _, p in trainable)
            == config["model"]["expected_trainable_parameters"][request["profile"]], "adapter_parameter_count")
    require(all(".lora_A." in name or ".lora_B." in name for name, _ in trainable), "unintended_trainable_weight")
    require(all(p.dtype == (torch.float32 if p.requires_grad else torch.bfloat16)
                for p in model.parameters()), "model_dtype_mismatch")
    return model.to(device="cuda:0")
