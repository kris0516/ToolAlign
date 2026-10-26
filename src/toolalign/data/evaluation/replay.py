"""A2 requests reuse only already public P03 development prompts and tools."""

from __future__ import annotations

import copy

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError
from toolalign.model_io.cuda_generation import prompt_ids
from toolalign.model_io.format import validate_model_input
from toolalign.tools import LocalToolRegistry


def build_replay(development, pairs, tokenizer):
    if development.get("purpose") != "public-original-development" or len(pairs) != 4:
        raise DataError("replay_public_development_four_pairs_required")
    cases = {c["id"]: c for c in development["cases"]}
    tools = LocalToolRegistry().tools
    sequences, rows = [], []
    for index, (first, other) in enumerate(pairs):
        if first == other:
            raise DataError("replay_requires_alternative_request")
        requests, tokens = [], []
        for order, source in enumerate((first, first, other)):
            value = validate_model_input({
                "messages": [{"role": "user", "content": cases[source]["prompt"],
                              "tool_calls": [], "tool_call_id": None}], "tools": tools,
            })
            ids = prompt_ids(tokenizer, value)
            if len(ids) + 256 > 2048:
                raise DataError("development_replay_context_overflow")
            common = 0
            if tokens:
                for a, b in zip(tokens[-1], ids):
                    if a != b:
                        break
                    common += 1
            requests.append({"request_id": f"a2-{index + 1}-{order + 1}",
                             "model_input": copy.deepcopy(value)})
            tokens.append(ids)
            rows.append({"sequence_id": f"a2-development-{index + 1}", "order": order,
                         "source_development_id": source, "seed": 42 + 3 * index + order,
                         "input_hash": canonical_hash(value), "input_tokens": len(ids),
                         "common_prefix_with_previous_tokens": common})
        sequences.append({"sequence_id": f"a2-development-{index + 1}",
                          "tenant_id": f"g5-development-{index + 1}", "requests": requests})
    return {"schema_version": "toolalign.evaluation-replay.v1",
            "purpose": "development-prefix-replay", "sequences": sequences}, {
                "purpose": "development-replay-provenance-only", "rows": rows,
                "tokenizer": tokenizer.identity, "model_calls": 0,
                "measured_cache_hits": "NOT_RUN", "test_outputs_used": False}
