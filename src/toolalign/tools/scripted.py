"""Deterministic CPU interface exercise. Tokens are synthetic, not tokenizer counts."""

from __future__ import annotations

import time

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import ModelOutput
from toolalign.tools._json import clone

_IDENTITY_HASH = canonical_hash({"backend": "scripted-cpu", "version": "1"})
SCRIPTED_IDENTITY = {
    "model_id": "toolalign/scripted-cpu-demo",
    "model_revision": "scripted-cpu.v1",
    "model_hash": _IDENTITY_HASH,
    "adapter_hash": None,
    "tokenizer_hash": _IDENTITY_HASH,
    "template_hash": _IDENTITY_HASH,
    "quantization": "none-scripted-no-model",
}


class ScriptedCPUModelBackend:
    """State persists in one owned process; each generate consumes one response.

    Only explicit public development scripts belong here. Never construct scripts by
    reading hidden oracle truth or use this backend as a learned-model baseline.
    """

    def __init__(self, responses, *, input_tokens=11, output_tokens=7, delay_seconds=0):
        self.responses = clone(list(responses))
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.delay_seconds = delay_seconds
        self.index = 0

    def generate(self, request, generation_config):
        if set(request) != {"messages", "tools"}:
            raise ValueError("ModelInput projection violated")
        if generation_config.enable_thinking is not False:
            raise ValueError("Thinking is disabled by protocol")
        time.sleep(self.delay_seconds)
        raw_text = self.responses[self.index]
        self.index += 1
        return ModelOutput(
            raw_text,
            None,
            None,
            clone(SCRIPTED_IDENTITY),
            self.input_tokens,
            self.output_tokens,
            "stop",
        )
