"""Explicit trusted renderer/encoder callbacks; no model or dataset-driven code."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from toolalign.contracts import canonical_hash, validate_record

from .format import TEMPLATE_SHA256, ModelIOError, encode_action, format_identity, prompt_messages


def _token_ids(value) -> tuple[int, ...]:
    if type(value) not in (list, tuple) or any(type(v) is not int or v < 0 for v in value):
        raise ModelIOError("invalid_token_ids")
    return tuple(value)


@dataclass(frozen=True)
class Sequence:
    prompt_text: str
    completion_text: str
    prompt_ids: tuple[int, ...]
    concatenated_ids: tuple[int, ...]
    sequence_ids: tuple[int, ...]
    loss_mask: tuple[int, ...]
    eos_token_id: int

    @property
    def causal_input_ids(self):
        return self.sequence_ids[:-1]

    @property
    def causal_target_ids(self):
        return self.sequence_ids[1:]

    @property
    def causal_loss_mask(self):
        return self.loss_mask[1:]

    def metadata(self) -> dict:
        p, n = len(self.prompt_ids), len(self.sequence_ids)
        return {
            **format_identity(),
            "prompt_sha256": hashlib.sha256(self.prompt_text.encode()).hexdigest(),
            "completion_sha256": hashlib.sha256(self.completion_text.encode()).hexdigest(),
            "prompt_ids_sha256": canonical_hash(list(self.prompt_ids)),
            "concatenated_ids_sha256": canonical_hash(list(self.concatenated_ids)),
            "sequence_sha256": canonical_hash(list(self.sequence_ids)),
            "loss_mask_sha256": canonical_hash(list(self.loss_mask)),
            "causal_loss_mask_sha256": canonical_hash(list(self.causal_loss_mask)),
            "prompt_tokens": p,
            "completion_tokens": n - p - 1,
            "completion_tokens_including_eos": n - p,
            "total_tokens": n,
            "completion_utf8_bytes": len(self.completion_text.encode()),
            "eos_token_id": self.eos_token_id,
            "prefix_stable": True,
            "append_eos_count": 1,
            "first_supervised_causal_position": p - 1,
            "last_supervised_causal_position": n - 2,
        }

    def record(self) -> dict:
        return {
            **self.metadata(), "prompt_text": self.prompt_text,
            "completion_text": self.completion_text, "prompt_ids": list(self.prompt_ids),
            "concatenated_ids": list(self.concatenated_ids),
            "sequence_ids": list(self.sequence_ids), "loss_mask": list(self.loss_mask),
            "causal_loss_mask": list(self.causal_loss_mask),
        }


def build_sequence(
    model_input: dict, action: dict, *, renderer, encoder, decoder,
    eos_token_id: int, template_sha256: str, eos_token: str = "<|im_end|>",
) -> Sequence:
    """Build an unpadded sequence using trusted application-supplied callbacks.

    A template hash here is the caller's declared binding. The optional offline
    adapter verifies actual local source bytes before supplying these callbacks.
    Neither callbacks nor template selection can come from ModelInput data.
    """
    if type(template_sha256) is not str or template_sha256 != TEMPLATE_SHA256:
        raise ModelIOError("template_identity_mismatch")
    if (
        type(eos_token_id) is not int or eos_token_id < 0
        or type(eos_token) is not str or eos_token != "<|im_end|>"
    ):
        raise ModelIOError("invalid_eos_identity")
    messages = prompt_messages(model_input)
    completion = encode_action(action)
    prompt = renderer(
        messages, tools=None, add_generation_prompt=True, enable_thinking=False
    )
    if type(prompt) is not str:
        raise ModelIOError("invalid_rendered_prompt")
    if _token_ids(encoder(eos_token, add_special_tokens=False)) != (eos_token_id,):
        raise ModelIOError("eos_encoding_mismatch")
    prompt_ids = _token_ids(encoder(prompt, add_special_tokens=False))
    joined = _token_ids(encoder(prompt + completion, add_special_tokens=False))
    if not prompt_ids:
        raise ModelIOError("empty_encoded_prompt")
    if joined[:len(prompt_ids)] != prompt_ids:
        raise ModelIOError("prompt_completion_boundary_changed")
    completion_ids = joined[len(prompt_ids):]
    if not completion_ids or eos_token_id in completion_ids:
        raise ModelIOError("unexpected_completion_eos_or_empty")
    if decoder(completion_ids, skip_special_tokens=False) != completion:
        raise ModelIOError("completion_decode_mismatch")
    sequence = joined + (eos_token_id,)
    mask = (0,) * len(prompt_ids) + (1,) * (len(completion_ids) + 1)
    return Sequence(prompt, completion, prompt_ids, joined, sequence, mask, eos_token_id)


def training_sequence(example: dict, **callbacks) -> Sequence:
    """Validate a real complete Example, including target/catalog/history rules."""
    value = validate_record(example, "example")
    return build_sequence(
        {"messages": value["messages"], "tools": value["tools"]}, value["expected_action"],
        **callbacks,
    )


@dataclass(frozen=True)
class PaddedSequence:
    sequence_ids: tuple[int, ...]
    attention_mask: tuple[int, ...]
    loss_mask: tuple[int, ...]
    unpadded_length: int

    @property
    def causal_input_ids(self):
        return self.sequence_ids[:-1]

    @property
    def causal_target_ids(self):
        return self.sequence_ids[1:]

    @property
    def causal_loss_mask(self):
        return self.loss_mask[1:]


def pad_sequence(sequence: Sequence, *, length: int, pad_token_id: int) -> PaddedSequence:
    """Explicit right padding with no truncation; padding never contributes loss."""
    if type(length) is not int or length < len(sequence.sequence_ids):
        raise ModelIOError("padding_cannot_truncate")
    if type(pad_token_id) is not int or pad_token_id < 0:
        raise ModelIOError("invalid_padding_token")
    n = len(sequence.sequence_ids)
    extra = length - n
    return PaddedSequence(
        sequence.sequence_ids + (pad_token_id,) * extra,
        (1,) * n + (0,) * extra,
        sequence.loss_mask + (0,) * extra,
        n,
    )
