"""CPU evidence helpers: independent reconstruction and fixed-budget summaries.

This is an audit probe, not a runtime raw-output parser or training selector.
The parser callback is supplied only by the trusted private driver after its
S0-authorized P03 source hash has been checked. No dataset selects executable code.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter

from toolalign.contracts import ContractError, canonical_hash
from toolalign.model_io import pad_sequence

LENGTH_FIELDS = (
    "prompt_tokens", "completion_tokens", "completion_tokens_including_eos", "total_tokens",
    "completion_utf8_bytes", "action_native_utf8_bytes", "action_nodes", "action_depth",
)
CONTEXT_CAPS = (1024, 1536, 2048)
RESPONSE_CAP = 256


def sha(data):
    return hashlib.sha256(data).hexdigest()


def wire(value):
    # Independent literal implementation of docs16, not the production encoder.
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e")


def independent_messages(model_input, descriptor):
    first = {
        "role": "system",
        "content": descriptor["instruction"] + "\n" + wire({
            "format_version": descriptor["format_id"], "tools": model_input["tools"],
        }),
    }
    return [first] + [
        {"role": message["role"], "content": wire({"message": message, "message_index": i})}
        for i, message in enumerate(model_input["messages"])
    ]


def recover_prompt(prompt, descriptor):
    """Inspect actual pinned-template control segments and recover every value."""
    parts = prompt.split("<|im_start|>")
    assert parts[0] == ""
    segments = []
    for index, part in enumerate(parts[1:]):
        role, body = part.split("\n", 1)
        if body.endswith("<|im_end|>\n"):
            body = body.removesuffix("<|im_end|>\n")
        else:
            assert index == len(parts) - 2 and role == "assistant"
            assert body == "<think>\n\n</think>\n\n"
        segments.append({"role": role, "body": body})
    prefix = descriptor["instruction"] + "\n"
    assert segments[0]["role"] == "system" and segments[0]["body"].startswith(prefix)
    catalog = json.loads(segments[0]["body"][len(prefix):])
    assert set(catalog) == {"format_version", "tools"}
    assert catalog["format_version"] == descriptor["format_id"]
    messages, roles = [], []
    for segment_index, segment in enumerate(segments[1:-1], 1):
        role, body = segment["role"], segment["body"]
        wrapped = role == "user" and body.startswith("<tool_response>\n")
        if wrapped:
            parts = ("\n" + body).split("\n<tool_response>\n")
            assert parts[0] == ""
            records = []
            for part in parts[1:]:
                assert part.endswith("\n</tool_response>")
                records.append(json.loads(part.removesuffix("\n</tool_response>")))
        else:
            records = [json.loads(body)]
        for record in records:
            assert set(record) == {"message", "message_index"}
            assert record["message_index"] == len(messages)
            assert record["message"]["role"] == ("tool" if wrapped else role)
            messages.append(record["message"])
            roles.append({
                "index": record["message_index"], "original_role": record["message"]["role"],
                "control_role": role, "segment_index": segment_index,
                "tool_response_wrapper": wrapped,
            })
    return {"messages": messages, "tools": catalog["tools"]}, roles


def complexity(value):
    # Match P03: root depth zero; one node per value/container, not object key.
    nodes, deepest, pending = 0, 0, [(value, 0)]
    while pending:
        node, depth = pending.pop()
        nodes += 1
        deepest = max(deepest, depth)
        children = node.values() if type(node) is dict else node if type(node) is list else ()
        pending.extend((child, depth + 1) for child in children)
    return nodes, deepest


def raw_metrics(text, action, parse_action):
    nodes, depth = complexity(action)
    native = json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    error, received = None, None
    try:
        received = parse_action(text)
        if canonical_hash(received) != canonical_hash(action):
            error = "parser_value_mismatch"
    except ContractError as exc:
        error = str(exc)
    return {
        "completion_utf8_bytes": len(text.encode()),
        "action_native_utf8_bytes": len(native.encode()),
        "action_nodes": nodes, "action_depth": depth,
        "raw_byte_cap": 131072, "raw_byte_cap_pass": len(text.encode()) <= 131072,
        "raw_node_cap_pass": nodes <= 8192, "raw_depth_cap_pass": depth <= 24,
        "parser_accepted_exact": error is None,
        "parser_error": error,
        "parser_action_sha256": canonical_hash(received) if error is None else None,
    }


def budget_metrics(row):
    completion = row.get("completion_tokens_including_eos")
    total = row.get("total_tokens")
    response = None if completion is None else completion <= RESPONSE_CAP
    return {
        "response_cap": RESPONSE_CAP,
        "response_including_eos_pass": response,
        "response_excluding_eos_pass": None if completion is None else completion - 1 <= RESPONSE_CAP,
        "context": {
            str(cap): {
                "total_including_eos_pass": None if total is None else total <= cap,
                "context_and_response_pass": None if total is None or response is None else total <= cap and response,
                "prompt_plus_reserved_response_pass": None if row.get("prompt_tokens") is None else row["prompt_tokens"] + RESPONSE_CAP <= cap,
            } for cap in CONTEXT_CAPS
        },
    }


def summarize(rows):
    result = {"denominator": len(rows), "lengths": {}}
    for field in LENGTH_FIELDS:
        measured = sorted(row[field] for row in rows if row.get(field) is not None)
        result["lengths"][field] = {
            "denominator": len(rows), "measured": len(measured),
            "missing": len(rows) - len(measured),
            "missing_reasons": dict(Counter(row.get("sequence_error") or "metric_unavailable" for row in rows if row.get(field) is None)),
            "max": max(measured) if measured else None,
            **{f"p{q}": measured[math.ceil(len(measured) * q / 100) - 1] if measured else None for q in (50, 90, 95, 99)},
        }
    result["sequence_errors"] = dict(Counter(row["sequence_error"] for row in rows if row.get("sequence_error")))
    result["parser_errors"] = dict(Counter(row["parser_error"] for row in rows if row.get("parser_error")))
    result["parser_accepted_exact"] = sum(row.get("parser_accepted_exact") is True for row in rows)
    result["budgets"] = {}
    measurements = {"response_including_eos": [r["budgets"]["response_including_eos_pass"] for r in rows]}
    measurements["response_excluding_eos"] = [r["budgets"]["response_excluding_eos_pass"] for r in rows]
    for cap in CONTEXT_CAPS:
        for key in ("total_including_eos_pass", "context_and_response_pass", "prompt_plus_reserved_response_pass"):
            measurements[f"context_{cap}_{key}"] = [r["budgets"]["context"][str(cap)][key] for r in rows]
    for name, values in measurements.items():
        result["budgets"][name] = {
            "denominator": len(rows), "pass": values.count(True),
            "over": values.count(False), "unmeasured": values.count(None),
        }
    result["raw_limits"] = {
        key: {"pass": sum(row.get(key) is True for row in rows), "over": sum(row.get(key) is False for row in rows), "unmeasured": sum(row.get(key) is None for row in rows), "denominator": len(rows)}
        for key in ("raw_byte_cap_pass", "raw_node_cap_pass", "raw_depth_cap_pass")
    }
    return result


def fixture_evidence(tokenizer, cases, descriptor, parse_action):
    rows = []
    for name, example in cases:
        model_input = {"messages": example["messages"], "tools": example["tools"]}
        before = canonical_hash(example)
        sequence = tokenizer.training_sequence(example)
        record = sequence.record()
        projected = independent_messages(model_input, descriptor)
        prompt = tokenizer.render(projected, tools=None, add_generation_prompt=True, enable_thinking=False)
        completion = wire(example["expected_action"])
        pids = tokenizer.encode(prompt, add_special_tokens=False)
        joined = tokenizer.encode(prompt + completion, add_special_tokens=False)
        expected = joined + [tokenizer.eos_token_id]
        mask = [int(i >= len(pids)) for i in range(len(expected))]
        assert record["prompt_text"] == prompt and record["completion_text"] == completion
        assert record["prompt_ids"] == pids and record["concatenated_ids"] == joined
        assert joined[:len(pids)] == pids
        assert record["sequence_ids"] == expected and record["loss_mask"] == mask
        assert record["causal_loss_mask"] == mask[1:]
        assert sequence.causal_input_ids == tuple(expected[:-1])
        assert sequence.causal_target_ids == tuple(expected[1:])
        assert mask[1:].index(1) == len(pids) - 1
        assert expected[len(pids):].count(tokenizer.eos_token_id) == 1
        raw = tokenizer.decode(expected[len(pids):-1], skip_special_tokens=False)
        assert raw == completion
        recovered, roles = recover_prompt(prompt, descriptor)
        assert canonical_hash(recovered) == canonical_hash(model_input)
        assert canonical_hash(parse_action(raw)) == canonical_hash(example["expected_action"])
        padded = pad_sequence(sequence, length=len(expected) + 4, pad_token_id=tokenizer.eos_token_id)
        assert padded.sequence_ids == tuple(expected + [tokenizer.eos_token_id] * 4)
        assert padded.loss_mask == tuple(mask + [0] * 4)
        assert padded.attention_mask == tuple([1] * len(expected) + [0] * 4)
        assert sum(padded.causal_loss_mask) == len(expected) - len(pids)
        repeat = tokenizer.training_sequence(example).record()
        assert repeat == record and canonical_hash(example) == before
        truncated = tokenizer.decode(expected[len(pids):len(pids) + RESPONSE_CAP], skip_special_tokens=False)
        truncated_error = None
        if len(expected) - len(pids) > RESPONSE_CAP:
            try:
                parse_action(truncated)
            except ContractError as exc:
                truncated_error = str(exc)
        record.update({
            "name": name, "example_sha256": before,
            "model_input_sha256": canonical_hash(model_input),
            "action_sha256": canonical_hash(example["expected_action"]),
            "rendered_inverse_exact": True, "role_bindings": roles,
            "deterministic_repeat_record_sha256": canonical_hash(repeat),
            "independent_arrays_exact": True, "right_padding_checked": 4,
            "sequence_error": None,
            **raw_metrics(raw, example["expected_action"], parse_action),
            "truncated_256_parser_error": truncated_error,
            "truncated_256_raw_sha256": sha(truncated.encode()) if len(expected) - len(pids) > RESPONSE_CAP else None,
        })
        record["budgets"] = budget_metrics(record)
        rows.append(record)
    return rows
