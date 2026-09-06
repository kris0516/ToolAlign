"""Optional, finite public MLX-LM injection; execution in this release is TOY_CPU only.

No framework is imported until a leased caller invokes these functions. This
does not patch the trainer or implement its optimization loop. Each train call
ends on an actual accumulation boundary and shares model/optimizer/RNG state.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.runtime.gpu_lock import GPULease

from .collator import Batch
from .config import require
from .plan import epoch_plan, validate_plan
from .validation import Score, ValidationTotals, parameter_content_hash, validate_score


def backend(lease):
    require(type(lease) is GPULease and lease._handle is not None, "active_shared_lease_required")
    distribution = importlib.metadata.distribution("mlx-lm")
    require(distribution.version == "0.31.3", "mlx_lm_version_mismatch")
    for name, digest in {
        "trainer.py": "ee33ebdbd20a184108541cb490d08085485e71a82ffd6d68d7d216029ecd28fe",
        "datasets.py": "fa112840e6ea98a4ff18428792fe2ab023999c2da51ea64b3ebdf8657a152f17",
    }.items():
        source = distribution.locate_file("mlx_lm/tuner/" + name)
        require(hashlib.sha256(source.read_bytes()).hexdigest() == digest, "mlx_lm_source_mismatch")
    import mlx.core as mx

    require(mx.default_device() == mx.cpu, "cpu_default_device_required")
    from mlx_lm.tuner import trainer

    return mx, trainer


def completion_loss(model, batch, mask):
    """Microbatch 1: mean CE on explicit shifted completion/EOS positions."""
    import mlx.core as mx
    import mlx.nn as nn

    require(batch.ndim == mask.ndim == 2 and batch.shape[0] == mask.shape[0] == 1
            and batch.shape[1] - 1 == mask.shape[1], "native_batch_shape_mismatch")
    logits = model(batch[:, :-1])
    ce = nn.losses.cross_entropy(logits, batch[:, 1:]).astype(mx.float32)
    tokens = mask.sum()
    return (ce * mask).sum() / tokens, tokens


class OrderedBatches:
    """A finite iterator, including when the trainer requests loop=True."""

    def __init__(self):
        self.visited = []

    def __call__(self, dataset, batch_size, max_seq_length, loop=False, seed=None, comm_group=None):
        import mlx.core as mx

        require(batch_size == 1 and seed in (None, 42), "fixed_batch_or_seed_required")
        require(comm_group is None or comm_group.size() == 1, "single_process_only")
        require(dataset, "empty_native_dataset")
        for rank, batch in dataset:
            require(type(batch) is Batch and batch.bucket <= max_seq_length, "native_no_truncation")
            require(batch.effective_supervised_targets > 0, "empty_native_supervision")
            self.visited.append(rank)
            yield mx.array([batch.sequence_ids], dtype=mx.int32), mx.array([batch.causal_loss_mask], dtype=mx.int32)


def parameter_hash(model):
    import mlx.core as mx
    import numpy as np
    from mlx.utils import tree_flatten

    values = tree_flatten(model.parameters())
    mx.eval(model.parameters())
    return parameter_content_hash((name, str(v.dtype), tuple(v.shape), np.array(v).tobytes(order="C"))
                                  for name, v in values)


def _toy_bounds(model, dataset):
    from mlx.utils import tree_flatten

    require(0 < len(dataset) <= 13 and sum(v.size for _, v in tree_flatten(model.parameters())) <= 4096,
            "toy_example_or_parameter_budget")
    for _, batch in dataset:
        require(type(batch) is Batch and batch.bucket <= 16
                and all(0 <= t < 16 for t in batch.sequence_ids), "toy_token_budget")


def post_update_score(*, lease, model, optimizer, dataset, checkpoint, selection_sha256,
                      processed_microsteps, expected_optimizer_step):
    """Evaluate exactly the saved post-update state; validate each actual numerator."""
    mx, trainer = backend(lease)
    _toy_bounds(model, dataset)
    actual_step = int(optimizer.step.item())
    require(actual_step == expected_optimizer_step > 0, "actual_optimizer_step_mismatch")
    before = parameter_hash(model)
    checkpoint = Path(checkpoint)
    require(checkpoint.is_file() and not checkpoint.is_symlink(), "saved_checkpoint_required")
    file_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    # Compare actual saved trainable tensors to actual model tensors; do not
    # associate a filename with a claimed state supplied in metadata.
    from mlx.utils import tree_flatten

    saved = mx.load(str(checkpoint))
    current = dict(tree_flatten(model.trainable_parameters()))
    require(set(saved) == set(current), "checkpoint_parameter_keys_mismatch")
    for name, value in saved.items():
        require(value.dtype == current[name].dtype and value.shape == current[name].shape
                and bool(mx.array_equal(value, current[name]).item()), "checkpoint_parameter_content_mismatch")
    ids = tuple(rank for rank, _ in dataset)
    totals = ValidationTotals(profile="TOY_CPU", split="validation", expected_ids=ids)
    batches = OrderedBatches()

    def validation_loss(m, batch, mask):
        mean, tokens = completion_loss(m, batch, mask)
        mx.eval(mean, tokens)
        totals.add(example_id=batches.visited[-1], profile="TOY_CPU", split="validation",
                   ce_sum=float(mean.item()) * int(tokens.item()), tokens=int(tokens.item()))
        return mean, tokens

    native = trainer.evaluate(model=model, dataset=dataset, batch_size=1, num_batches=-1,
                              max_seq_length=16, loss=validation_loss, iterate_batches=batches)
    score = totals.finish()
    require(abs(native - score) <= 2e-6, "native_validation_reduction_mismatch")
    require(tuple(batches.visited) == ids and parameter_hash(model) == before
            and hashlib.sha256(checkpoint.read_bytes()).hexdigest() == file_hash,
            "validation_state_or_coverage_changed")
    value = Score("TOY_CPU", selection_sha256, canonical_hash(list(ids)), before, file_hash,
                  actual_step, processed_microsteps, totals.numerator, totals.denominator, score)
    validate_score(value)
    return value


def train_toy_segments(*, lease, model, optimizer, train_dataset, validation_dataset, output):
    """At most two real optimizer updates on original tiny inputs; no real-data API."""
    mx, trainer = backend(lease)
    _toy_bounds(model, train_dataset)
    _toy_bounds(model, validation_dataset)
    plan = epoch_plan(len(train_dataset))
    require(plan.updates <= 2 and int(optimizer.step.item()) == 0, "toy_update_budget_or_nonfresh_optimizer")
    validate_plan(plan, (rank for rank, _ in train_dataset))
    # Validation reuses these same original toy cases solely to verify state
    # bookkeeping. It is not a generalization or model-quality measurement.
    require(all(item in train_dataset for item in validation_dataset), "toy_validation_must_reuse_original_cases")
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), "toy_output_exists")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    selection = canonical_hash([[rank, batch.record()] for rank, batch in train_dataset])
    scores, states, visited, updates = [], [], [], 0
    mx.random.seed(42)  # Seed once, never restart the RNG between segments.
    for number, segment in enumerate(plan.segments, 1):
        checkpoint = output / f"TOY_CPU-segment-{number}.safetensors"
        args = trainer.TrainingArgs(batch_size=1, iters=segment.microsteps,
            grad_accumulation_steps=segment.divisor, val_batches=-1,
            steps_per_report=segment.microsteps, steps_per_eval=segment.microsteps + 1,
            steps_per_save=segment.microsteps + 1, max_seq_length=16, adapter_file=str(checkpoint),
            grad_checkpoint=False)
        iterator = OrderedBatches()
        trainer.train(model=model, optimizer=optimizer,
                      train_dataset=train_dataset[segment.start:segment.stop], val_dataset=None,
                      args=args, loss=completion_loss, iterate_batches=iterator)
        visited.extend(iterator.visited)
        require(iterator.visited == list(range(segment.start + 1, segment.stop + 1)), "native_segment_coverage")
        updates += segment.updates
        require(int(optimizer.step.item()) == updates, "native_update_count")
        scores.append(post_update_score(lease=lease, model=model, optimizer=optimizer,
            dataset=validation_dataset, checkpoint=checkpoint, selection_sha256=selection,
            processed_microsteps=segment.stop, expected_optimizer_step=updates))
        states.append({"segment": number, "start": segment.start, "stop": segment.stop,
                       "actual_divisor": segment.divisor, "optimizer_step": updates,
                       "parameter_content_sha256": parameter_hash(model),
                       "checkpoint": checkpoint.name})
    require(visited == list(range(1, len(train_dataset) + 1)), "native_epoch_coverage")
    return {"scope": "TOY_CPU", "scores": scores, "states": states,
            "visited": visited, "actual_optimizer_updates": updates}
