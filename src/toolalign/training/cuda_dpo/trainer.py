"""Native DPOTrainer, with fixed order and optimizer-boundary observation."""

from __future__ import annotations

import math
from pathlib import Path

import torch
from datasets import Dataset
from torch.utils.data import SequentialSampler
from transformers import TrainerCallback
from trl import DPOConfig, DPOTrainer
from trl.trainer.dpo_trainer import DataCollatorForPreference

from toolalign.training.cuda_sft.checkpoint import parameter_hash
from toolalign.training.cuda_sft.engine import make_optimizer
from toolalign.training.cuda_sft.protocol import encoded, require, write_bytes

from .checkpoint import seal


class OrderedDPOTrainer(DPOTrainer):
    """Observe consumed IDs; all numerical work and state handling remain upstream."""

    def _get_train_sampler(self, train_dataset=None):
        return SequentialSampler(self.train_dataset if train_dataset is None else train_dataset)

    def training_step(self, model, inputs, num_items_in_batch=None):
        inputs = dict(inputs)
        identities = inputs.pop("preference_id")
        loss = super().training_step(model, inputs, num_items_in_batch)
        self.consumed.extend(identities)
        self.step_losses.append(float(loss))
        return loss


class IdentifiedCollator:
    def __init__(self, pad_token_id):
        self.native = DataCollatorForPreference(pad_token_id=pad_token_id)

    def __call__(self, examples):
        result = self.native(examples)
        result["preference_id"] = [row["preference_id"] for row in examples]
        return result


def arguments(config, output, pair_count, *, checkpoint_every, use_cpu=False):
    """The CPU option is for caller-supplied random fixtures; the CLI is CUDA-only."""
    objective = {key: value for key, value in config["objective"].items()
                 if key != "completion_reduction"}
    training, optimizer = config["training"], config["optimizer"]
    return DPOConfig(
        output_dir=str(output), **objective,
        max_length=None, max_prompt_length=None, max_completion_length=None,
        per_device_train_batch_size=1, gradient_accumulation_steps=8,
        max_steps=math.ceil(pair_count / 8), num_train_epochs=1,
        learning_rate=optimizer["learning_rate"], lr_scheduler_type="constant", warmup_steps=0,
        adam_beta1=0.9, adam_beta2=0.999, adam_epsilon=1e-8, weight_decay=0, max_grad_norm=0,
        seed=42, data_seed=42, bf16=not use_cpu, fp16=False, tf32=False, use_cpu=use_cpu,
        gradient_checkpointing=training["gradient_checkpointing"],
        gradient_checkpointing_kwargs={"use_reentrant": False},
        dataloader_num_workers=0, dataloader_drop_last=False, dataloader_pin_memory=not use_cpu,
        remove_unused_columns=False, group_by_length=False, padding_free=False,
        disable_dropout=True, force_use_ref_model=True, dataset_num_proc=None,
        model_adapter_name=None, ref_adapter_name=None,
        eval_strategy="no", save_strategy="steps", save_steps=checkpoint_every,
        save_total_limit=2, save_only_model=False, save_safetensors=True,
        ignore_data_skip=False, load_best_model_at_end=False,
        restore_callback_states_from_checkpoint=False,
        logging_strategy="steps", logging_steps=1, logging_nan_inf_filter=False,
        report_to=[], push_to_hub=False, disable_tqdm=True,
    )


def verify_prepared(trainer, expected):
    require(len(trainer.train_dataset) == len(expected), "DPO_prepared_row_count")
    for actual, wanted in zip(trainer.train_dataset, expected, strict=True):
        require(actual["preference_id"] == wanted["preference_id"], "DPO_prepared_order")
        for key in ("prompt_input_ids", "chosen_input_ids", "rejected_input_ids"):
            require(actual[key] == wanted[key], "DPO_native_token_identity:" + key)
        require(not ({"ref_chosen_logps", "ref_rejected_logps"} & actual.keys()),
                "DPO_reference_cache_forbidden")


def precision_probe(trainer, model, row):
    """Observe Accelerator's actual wrapped outputs without changing training state."""
    result = {"accelerate_mixed_precision": trainer.accelerator.mixed_precision,
              "attention": model.config._attn_implementation}

    def observe_policy(module, args, output):
        result["policy_logits_dtype"] = str(output.logits.dtype)

    def observe_reference(module, args, output):
        result["reference_logits_dtype"] = str(output.logits.dtype)

    hooks = [model.register_forward_hook(observe_policy),
             trainer.ref_model.register_forward_hook(observe_reference)]
    was_training = model.training
    try:
        model.eval()
        batch = DataCollatorForPreference(trainer.pad_token_id)([row])
        batch = {key: value.to(trainer.accelerator.device) for key, value in batch.items()}
        with torch.no_grad(), trainer.compute_loss_context_manager():
            policy = trainer.concatenated_forward(model, batch)
            reference = trainer.concatenated_forward(trainer.ref_model, batch, is_ref_model=True)
            loss, _, _ = trainer.dpo_loss(policy["chosen_logps"], policy["rejected_logps"],
                                          reference["chosen_logps"], reference["rejected_logps"])
        result.update(policy_logps_dtype=str(policy["chosen_logps"].dtype),
                      reference_logps_dtype=str(reference["chosen_logps"].dtype),
                      loss_dtype=str(loss.dtype), first_pair_loss=float(loss.mean()))
        require(bool(torch.isfinite(loss).all()), "nonfinite_DPO_initial_loss")
    finally:
        model.train(was_training)
        for hook in hooks:
            hook.remove()
    return result


class SegmentBoundary(TrainerCallback):
    def __init__(self, *, identity, identities, stop_step, max_bytes):
        self.identity, self.identities = identity, identities
        self.stop_step, self.max_bytes = stop_step, max_bytes
        self.trainer = None
        self.events, self.manifests = [], []

    def on_train_begin(self, args, state, control, model=None, **kwargs):
        require(state.global_step < self.stop_step <= state.max_steps, "DPO_segment_steps")
        self.initial_cursor = min(state.global_step * 8, len(self.identities))
        self.previous_cursor = self.initial_cursor
        row = self.trainer.train_dataset[self.initial_cursor]
        self.precision = precision_probe(self.trainer, model, row)
        if state.global_step == 0:
            require(abs(self.precision["first_pair_loss"] - math.log(2)) <= 1e-6,
                    "DPO_initial_policy_reference_mismatch")
        self.adapter_before = parameter_hash(model)
        write_bytes(Path(args.output_dir) / "precision.json", encoded(self.precision) + b"\n")

    def on_pre_optimizer_step(self, args, state, control, model=None, **kwargs):
        gradients = [p.grad for p in model.parameters() if p.requires_grad]
        require(gradients and all(g is not None and bool(torch.isfinite(g).all())
                                  for g in gradients), "nonfinite_or_missing_DPO_gradient")

    def on_step_end(self, args, state, control, **kwargs):
        trainer = self.trainer
        cursor = min(state.global_step * 8, len(self.identities))
        require(trainer.consumed == self.identities[self.initial_cursor:cursor],
                "DPO_consumed_input_order")
        microsteps = cursor - self.previous_cursor
        require(len(trainer.step_losses) == trainer.current_gradient_accumulation_steps
                == microsteps and 0 < microsteps <= 8, "DPO_tail_divisor")
        event = {"optimizer_step": state.global_step, "data_cursor": cursor,
                 "microsteps": microsteps, "loss": sum(trainer.step_losses)}
        require(math.isfinite(event["loss"]), "nonfinite_DPO_loss")
        self.events.append(event)
        with (Path(args.output_dir) / "events.jsonl").open("ab") as stream:
            stream.write(encoded(event) + b"\n")
            stream.flush()
        trainer.step_losses.clear()
        self.previous_cursor = cursor
        if state.global_step == self.stop_step:
            control.should_save = True
            control.should_training_stop = True
        return control

    def on_save(self, args, state, control, **kwargs):
        root = Path(args.output_dir) / f"checkpoint-{state.global_step}"
        self.manifests.append(seal(root, identity=self.identity, step=state.global_step,
                                   pair_count=len(self.identities), max_bytes=self.max_bytes))


def create_trainer(*, policy, reference, tokenizer, rows, expected, config, output, identity,
                   stop_step, checkpoint_every=1, max_bytes=1024**3, use_cpu=False):
    require(rows and len(rows) <= config["execution"]["max_pairs"], "DPO_pair_count")
    require(all(set(row) == {"preference_id", "prompt", "chosen", "rejected"} for row in rows),
            "DPO_string_input_fields")
    require(reference is not policy and all(not p.requires_grad for p in reference.parameters())
            and not reference.training, "DPO_frozen_reference_required")
    identities = [row["preference_id"] for row in rows]
    require(len(set(identities)) == len(identities), "DPO_duplicate_preference")
    boundary = SegmentBoundary(identity=identity, identities=identities,
                                stop_step=stop_step, max_bytes=max_bytes)
    trainer = OrderedDPOTrainer(
        model=policy, ref_model=reference, peft_config=None, processing_class=tokenizer,
        args=arguments(config, output, len(rows), checkpoint_every=checkpoint_every, use_cpu=use_cpu),
        train_dataset=Dataset.from_list(rows),
        data_collator=IdentifiedCollator(tokenizer.pad_token_id), callbacks=[boundary],
        optimizers=(make_optimizer(policy, config), None),
    )
    trainer.consumed, trainer.step_losses = [], []
    boundary.trainer = trainer
    require(trainer.accelerator.num_processes == 1, "DPO_single_process_required")
    verify_prepared(trainer, expected)
    return trainer, boundary
