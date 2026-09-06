"""Versioned, model-independent Action JSON projection and sequence interfaces."""

from .format import (
    DESCRIPTOR_SHA256,
    FORMAT_ID,
    INSTRUCTION_SHA256,
    TEMPLATE_SHA256,
    ModelIOError,
    encode_action,
    encode_json,
    format_descriptor,
    format_identity,
    prompt_messages,
    validate_action,
    validate_model_input,
)
from .sequence import PaddedSequence, Sequence, build_sequence, pad_sequence, training_sequence

__all__ = [
    "DESCRIPTOR_SHA256", "FORMAT_ID", "INSTRUCTION_SHA256", "TEMPLATE_SHA256",
    "ModelIOError", "PaddedSequence", "Sequence", "build_sequence", "encode_action",
    "encode_json", "format_descriptor", "format_identity", "pad_sequence",
    "prompt_messages", "training_sequence", "validate_action", "validate_model_input",
]
