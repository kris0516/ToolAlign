"""Explicit completion-only arrays from the shared model_io sequence implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from toolalign.contracts import canonical_hash
from toolalign.model_io import Sequence, pad_sequence, training_sequence

from .config import require


@dataclass(frozen=True)
class Batch:
    sequence_ids: tuple[int, ...]
    attention_mask: tuple[int, ...]
    loss_mask: tuple[int, ...]
    causal_input_ids: tuple[int, ...]
    causal_target_ids: tuple[int, ...]
    causal_loss_mask: tuple[int, ...]
    bucket: int
    pad_token_id: int
    unpadded_length: int
    effective_supervised_targets: int
    first_supervised_causal_position: int
    last_supervised_causal_position: int

    def __post_init__(self):
        n, p = self.unpadded_length, self.first_supervised_causal_position + 1
        require(all(type(v) is int for v in (n, p, self.bucket, self.pad_token_id,
                    self.effective_supervised_targets, self.last_supervised_causal_position))
                and 0 < p < n <= self.bucket and self.pad_token_id >= 0, "batch_boundaries_mismatch")
        require(type(self.sequence_ids) is tuple and len(self.sequence_ids) == self.bucket
                and all(type(v) is int and v >= 0 for v in self.sequence_ids), "batch_ids_mismatch")
        require(self.attention_mask == (1,) * n + (0,) * (self.bucket - n)
                and self.loss_mask == (0,) * p + (1,) * (n - p) + (0,) * (self.bucket - n)
                and all(type(v) is int for v in self.attention_mask + self.loss_mask), "batch_masks_mismatch")
        require(self.sequence_ids[n:] == (self.pad_token_id,) * (self.bucket - n)
                and self.causal_input_ids == self.sequence_ids[:-1]
                and self.causal_target_ids == self.sequence_ids[1:]
                and self.causal_loss_mask == self.loss_mask[1:]
                and self.effective_supervised_targets == n - p
                and self.last_supervised_causal_position == n - 2, "batch_shift_or_denominator_mismatch")

    def record(self):
        return {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()}


def collate_sequence(sequence: Sequence, *, bucket: int, pad_token_id: int) -> Batch:
    require(type(sequence) is Sequence, "invalid_shared_sequence")
    p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
    require(p > 0 and n > p + 1, "empty_completion_or_prompt")
    require(sequence.sequence_ids[:p] == sequence.prompt_ids
            and sequence.sequence_ids[:-1] == sequence.concatenated_ids, "sequence_prefix_or_append_mismatch")
    require(sequence.sequence_ids[-1] == sequence.eos_token_id
            and sequence.sequence_ids[p:].count(sequence.eos_token_id) == 1, "completion_eos_mismatch")
    require(all(type(t) is int and t >= 0 for t in sequence.sequence_ids), "invalid_sequence_ids")
    require(sequence.loss_mask == (0,) * p + (1,) * (n - p), "completion_mask_mismatch")
    padded = pad_sequence(sequence, length=bucket, pad_token_id=pad_token_id)
    return Batch(padded.sequence_ids, padded.attention_mask, padded.loss_mask,
                 padded.causal_input_ids, padded.causal_target_ids, padded.causal_loss_mask,
                 bucket, pad_token_id, n, sum(padded.causal_loss_mask), p - 1, n - 2)


def collate_selected(row, *, tokenizer):
    """The caller provides an existing OfflineQwenTokenizer, never a data callback."""
    from toolalign.model_io.offline import OfflineQwenTokenizer

    require(type(tokenizer) is OfflineQwenTokenizer, "verified_offline_tokenizer_required")
    example, sidecar = row.example, row.sidecar
    require(example["split"] in ("train", "validation"), "forbidden_collator_split")
    require(sidecar["split"] == example["split"]
            and sidecar["audit"]["example_sha256"] == canonical_hash(example), "collator_example_binding")
    expected_model = {"smoke": "Qwen/Qwen3-0.6B", "formal": "Qwen/Qwen3-1.7B"}
    require(tokenizer.identity["repo_id"] == expected_model.get(sidecar["profile"]),
            "collator_tokenizer_profile_mismatch")
    sequence = training_sequence(example, **tokenizer.callbacks())
    metadata = sequence.metadata() | {
        "causal_input_ids_sha256": canonical_hash(list(sequence.causal_input_ids)),
        "causal_target_ids_sha256": canonical_hash(list(sequence.causal_target_ids))}
    require(all(sidecar["audit"].get(k) == v for k, v in metadata.items()), "collator_audit_mismatch")
    batch = collate_sequence(sequence, bucket=sidecar["padding_bucket"], pad_token_id=151643)
    return sequence, batch
