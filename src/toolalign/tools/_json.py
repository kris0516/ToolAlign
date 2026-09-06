"""Bounded native JSON and frozen subschemas; no evaluation or schema fetching."""

from __future__ import annotations

import json
from functools import lru_cache

from jsonschema import Draft202012Validator, ValidationError

from toolalign.contracts import ContractError, schema_for

CALL_BYTES = 16_384
RESULT_BYTES = 16_384
MODEL_BYTES = 131_072
INPUT_BYTES = 524_288


def encode(value, limit=MODEL_BYTES) -> bytes:
    remaining = 8192

    def check(node, depth=0):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 24:
            raise ContractError("JSON complexity limit")
        if type(node) is dict:
            for key, child in node.items():
                if type(key) is not str or len(key) > limit:
                    raise ContractError("Invalid JSON key")
                check(child, depth + 1)
        elif type(node) is list:
            for child in node:
                check(child, depth + 1)
        elif type(node) is str:
            if len(node) > limit:
                raise ContractError("JSON string limit")
        elif node is not None and type(node) not in (int, float, bool):
            raise ContractError("Expected native JSON")

    check(value)
    try:
        result = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("Invalid JSON value") from exc
    if len(result) > limit:
        raise ContractError("JSON byte limit")
    return result


def decode(raw: str | bytes, limit=MODEL_BYTES):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError("Duplicate JSON key")
            result[key] = value
        return result

    if type(raw) not in (str, bytes) or len(raw) > limit:
        raise ContractError("JSON byte limit")
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        encode(value, limit)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("Invalid JSON") from exc


def clone(value, limit=MODEL_BYTES):
    return decode(encode(value, limit), limit)


@lru_cache(maxsize=8)
def _validator(definition):
    schema = schema_for("trace")
    schema["$ref"] = f"#/$defs/{definition}"
    return Draft202012Validator(schema)


def validate_part(value, definition, limit=MODEL_BYTES):
    value = clone(value, limit)
    try:
        _validator(definition).validate(value)
    except ValidationError as exc:
        raise ContractError("Invalid frozen " + definition) from exc
    return value


def parse_action(raw):
    action = validate_part(decode(raw), "action")
    ids = [call["call_id"] for call in action["tool_calls"]]
    if len(ids) != len(set(ids)):
        raise ContractError("Duplicate call ID")
    return action
