"""Strict JSON validation. No network resolution or execution of dataset content."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from pathlib import PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

KINDS = ("example", "tool", "preference", "run", "trace")


class ContractError(ValueError):
    """A record violates the versioned structural or semantic contract."""


def _json_bytes(value: Any) -> bytes:
    def strict_json(node, depth=0):
        if depth > 64:
            raise ContractError("JSON nesting exceeds 64 levels")
        if type(node) is dict:
            for key, child in node.items():
                if type(key) is not str:
                    raise ContractError("JSON object keys must be strings")
                strict_json(child, depth + 1)
        elif type(node) is list:
            for child in node:
                strict_json(child, depth + 1)
        elif node is not None and type(node) not in (str, int, float, bool):
            raise ContractError("Expected JSON values without coercion")

    strict_json(value)
    try:
        return json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ContractError("Expected finite, serializable JSON") from exc


def canonical_hash(value: Any) -> str:
    """SHA-256 of UTF-8 sorted-key compact JSON; array order remains significant."""
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def contract_digest() -> str:
    return hashlib.sha256(files(__package__).joinpath("v1.json").read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def _bundle() -> dict:
    return json.loads(files(__package__).joinpath("v1.json").read_text(encoding="utf-8"))


def schema_for(kind: str) -> dict:
    if kind not in KINDS:
        raise ContractError("Unknown contract kind")
    return {**copy.deepcopy(_bundle()), "$ref": f"#/$defs/{kind}"}


@lru_cache(maxsize=5)
def _validator(kind: str) -> Draft202012Validator:
    schema = schema_for(kind)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _tool_schema(schema: dict, depth: int = 0) -> None:
    # A deliberately bounded portable subset. In particular, no refs, regex or remote IDs.
    allowed = {
        "type",
        "description",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "enum",
    }
    if depth > 12 or not isinstance(schema, dict) or set(schema) - allowed:
        raise ContractError("Unsupported tool parameter schema")
    kind = schema.get("type")
    if kind not in ("object", "array", "string", "integer", "number", "boolean", "null"):
        raise ContractError("Tool parameter schemas require one explicit primitive type")
    if kind == "object":
        properties = schema.get("properties")
        if not isinstance(properties, dict) or len(properties) > 128:
            raise ContractError("Object schema requires bounded properties")
        if schema.get("additionalProperties") is not False:
            raise ContractError("Tool arguments must reject undeclared properties")
        if not set(schema.get("required", [])) <= set(properties):
            raise ContractError("Required property is not declared")
        for child in properties.values():
            _tool_schema(child, depth + 1)
    elif kind == "array":
        if not isinstance(schema.get("maxItems"), int) or not 0 <= schema["maxItems"] <= 1000:
            raise ContractError("Array parameters require maxItems <= 1000")
        _tool_schema(schema.get("items"), depth + 1)
    elif kind == "string":
        if not isinstance(schema.get("maxLength"), int) or not 0 <= schema["maxLength"] <= 16384:
            raise ContractError("String parameters require maxLength <= 16384")


def _check_tools(tools: list[dict]) -> None:
    names = [tool["name"] for tool in tools]
    if len(names) != len(set(names)):
        raise ContractError("Tool names must be unique within an input")
    for tool in tools:
        try:
            Draft202012Validator.check_schema(tool["parameters_json_schema"])
            _tool_schema(tool["parameters_json_schema"])
            if tool["parameters_json_schema"]["type"] != "object":
                raise ContractError("Tool arguments must be a closed object")
        except (SchemaError, TypeError) as exc:
            raise ContractError("Invalid tool parameter schema") from exc


def _check_messages(messages: list[dict]) -> None:
    pending = set()
    seen = set()
    for message in messages:
        if message["role"] == "tool":
            call_id = message["tool_call_id"]
            if call_id not in pending:
                raise ContractError("Tool observation does not match a pending call")
            pending.remove(call_id)
        elif pending:
            raise ContractError("All pending observations must precede the next turn")
        for call in message["tool_calls"]:
            if call["call_id"] in seen:
                raise ContractError("Call IDs must be unique within a conversation")
            seen.add(call["call_id"])
            pending.add(call["call_id"])
    if pending or messages[-1]["role"] not in ("user", "tool"):
        raise ContractError("Model input must end before the next assistant decision")


def _utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError
        return parsed
    except (ValueError, TypeError) as exc:
        raise ContractError("Timestamp must be valid UTC") from exc


def validate_record(record: dict, kind: str | None = None) -> dict:
    """Validate without coercion and return an isolated copy; labels are not truth proofs."""
    _json_bytes(record)
    if not isinstance(record, dict):
        raise ContractError("Expected a JSON object")
    if kind is None:
        kind = next((k for k in KINDS if record.get("schema_version") == f"toolalign.{k}.v1"), None)
    if kind not in KINDS:
        raise ContractError("Unknown or missing schema_version")
    try:
        _validator(kind).validate(record)
    except ValidationError as exc:
        # Do not echo user data, credentials or private payloads in CLI errors.
        path = "/".join(str(p) for p in exc.absolute_path)
        raise ContractError(f"{kind}: invalid field /{path} ({exc.validator})") from exc
    if kind == "tool":
        _check_tools([record])
    if kind in ("example", "preference"):
        _check_tools(record["tools"])
        _check_messages(record["messages"])
    if kind == "example":
        registered = {tool["name"]: tool for tool in record["tools"]}
        calls = record["expected_action"]["tool_calls"]
        if len({call["call_id"] for call in calls}) != len(calls):
            raise ContractError("Expected action contains duplicate call IDs")
        for call in calls:
            if call["name"] not in registered:
                raise ContractError("Expected action references an undeclared tool")
            validate_tool_arguments(registered[call["name"]], call["arguments"])
    if kind == "preference":
        if record["chosen"] == record["rejected"]:
            raise ContractError("Identical completions cannot form a preference")
        if record["prompt_hash"] != canonical_hash(
            {"messages": record["messages"], "tools": record["tools"]}
        ):
            raise ContractError("Preference prompt_hash does not match the shared input")
    if kind == "run":
        for artifact in record["artifacts"]:
            path = PurePosixPath(artifact["relative_path"])
            if path.is_absolute() or ".." in path.parts or "\\" in str(path) or not path.name:
                raise ContractError("Artifact paths must stay relative to the private run root")
            if artifact["artifact_id"] != artifact["sha256"]:
                raise ContractError("Artifact ID must equal its content SHA-256")
        started = _utc(record["started_at"])
        ended = _utc(record["ended_at"]) if record["ended_at"] else None
        if ended and ended < started:
            raise ContractError("Run ends before it starts")
        completed = record["status"] != "running"
        if completed != (ended is not None and record["exit_code"] is not None):
            raise ContractError(
                "Terminal runs need end time and exit code; running runs need nulls"
            )
        if not completed and (ended is not None or record["exit_code"] is not None):
            raise ContractError("Running runs cannot have terminal fields")
        if (
            record["status"] == "succeeded"
            and record["exit_code"] != 0
            or record["status"] == "failed"
            and record["exit_code"] == 0
        ):
            raise ContractError("Run status and exit code disagree")
    if kind == "trace":
        _utc(record["deadline_utc"])
        if record["event"] in (
            "finalized",
            "rejected",
            "budget_exhausted",
            "timed_out",
            "cancelled",
        ):
            if record["task_outcome"] is None:
                raise ContractError("Terminal trace event requires a task outcome")
        if record["tool_call"] and record["tool_result"]:
            if record["tool_call"]["call_id"] != record["tool_result"]["call_id"]:
                raise ContractError("Tool result refers to a different call")
    return copy.deepcopy(record)


def validate_tool_arguments(tool: dict, arguments: dict) -> None:
    validated = validate_record(tool, "tool")
    _json_bytes(arguments)
    try:
        Draft202012Validator(validated["parameters_json_schema"]).validate(arguments)
    except ValidationError as exc:
        raise ContractError("Tool arguments do not match the registered schema") from exc


def model_input_from_example(example: dict) -> dict:
    """Explicit allowlist projection: no expected_action, split or oracle metadata."""
    value = validate_record(example, "example")
    return {"messages": value["messages"], "tools": value["tools"]}
