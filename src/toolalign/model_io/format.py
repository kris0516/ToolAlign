"""Pure v1 projection. No tokenizer, model, execution registry or invented target."""

from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft202012Validator, ValidationError

from toolalign.contracts import (
    ContractError,
    canonical_hash,
    contract_digest,
    schema_for,
    validate_record,
)

FORMAT_ID = "toolalign.action-json.qwen3-message-roles.v1"
DESCRIPTOR_SHA256 = "e985dd734a6e3478eb14f80d702e1c79817e955d488e6a37ceeab857b4a79207"
INSTRUCTION_SHA256 = "294d8540bd3ff8de84293d5d8b0f7e8f2537ee9cf1c81b95e81b6415f1039cee"
TEMPLATE_SHA256 = "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8"
CONTRACT_SHA256 = "ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb"


class ModelIOError(ContractError):
    """A stable error code without private input text or dictionary paths."""


@lru_cache(maxsize=1)
def _descriptor():
    raw = files(__package__).joinpath("descriptor.v1.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != DESCRIPTOR_SHA256:
        raise ModelIOError("format_descriptor_hash_mismatch")
    value = json.loads(raw)
    if (
        value["format_id"] != FORMAT_ID
        or value["instruction_sha256"] != INSTRUCTION_SHA256
        or hashlib.sha256(value["instruction"].encode()).hexdigest() != INSTRUCTION_SHA256
        or value["template"]["utf8_sha256"] != TEMPLATE_SHA256
        or value["contract_schema_sha256"] != CONTRACT_SHA256
        or contract_digest() != CONTRACT_SHA256
    ):
        raise ModelIOError("format_identity_mismatch")
    return value


def format_descriptor() -> dict:
    """Return an isolated copy of the byte-verified installed package resource."""
    return copy.deepcopy(_descriptor())


def format_identity() -> dict:
    _descriptor()
    return {
        "format_id": FORMAT_ID,
        "descriptor_sha256": DESCRIPTOR_SHA256,
        "instruction_sha256": INSTRUCTION_SHA256,
        "contract_sha256": CONTRACT_SHA256,
        "template_sha256": TEMPLATE_SHA256,
    }


def _native_json(value) -> None:
    # The public frozen helper checks native types, finite values and its existing
    # depth boundary. Do not add the P03 raw limits to the frozen input contract.
    try:
        canonical_hash(value)
    except (UnicodeError, OverflowError) as exc:
        raise ModelIOError("invalid_utf8_json") from exc


def encode_json(value) -> str:
    """Finite native JSON with reversible angle escaping in both keys and values."""
    descriptor = _descriptor()
    _native_json(value)
    text = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    replacements = descriptor["json_encoding"]["escape_after_serialization"]
    return text.replace("<", replacements["U+003C"]).replace(">", replacements["U+003E"])


@lru_cache(maxsize=2)
def _validator(kind: str):
    _descriptor()
    schema = schema_for("example")
    if kind == "model_input":
        original = schema["$defs"]["example"]["properties"]
        # Derive the actual frozen array bounds/subschemas without fabricating
        # any example metadata or expected_action, or altering the frozen bundle.
        schema["$defs"]["model_input"] = {
            "type": "object", "additionalProperties": False,
            "required": ["messages", "tools"],
            "properties": {name: copy.deepcopy(original[name]) for name in ("messages", "tools")},
        }
    schema["$ref"] = "#/$defs/" + kind
    return Draft202012Validator(schema)


def _validated(value, kind: str):
    _native_json(value)
    try:
        _validator(kind).validate(value)
    except ValidationError as exc:
        raise ModelIOError("invalid_" + kind + "_structure") from exc
    return copy.deepcopy(value)


def validate_model_input(model_input: dict) -> dict:
    """Validate standalone ModelInput with exactly the frozen history semantics.

    Historical calls need not name today's tools or satisfy today's parameter
    schemas. Only a full training Example validates its target against the catalog.
    """
    value = _validated(model_input, "model_input")
    names = set()
    for tool in value["tools"]:
        validate_record(tool, "tool")
        if tool["name"] in names:
            raise ModelIOError("duplicate_tool_name")
        names.add(tool["name"])
    pending, seen = set(), set()
    for message in value["messages"]:
        if message["role"] == "tool":
            call_id = message["tool_call_id"]
            if call_id not in pending:
                raise ModelIOError("observation_without_pending_call")
            pending.remove(call_id)
        elif pending:
            raise ModelIOError("pending_observations_before_next_turn")
        for call in message["tool_calls"]:
            if call["call_id"] in seen:
                raise ModelIOError("duplicate_history_call_id")
            seen.add(call["call_id"])
            pending.add(call["call_id"])
    if pending or value["messages"][-1]["role"] not in ("user", "tool"):
        raise ModelIOError("unfinished_model_input_history")
    return value


def validate_action(action: dict) -> dict:
    """Validate the frozen Action shape and local call-ID uniqueness, independently."""
    value = _validated(action, "action")
    ids = [call["call_id"] for call in value["tool_calls"]]
    if len(ids) != len(set(ids)):
        raise ModelIOError("duplicate_action_call_id")
    return value


def prompt_messages(model_input: dict) -> list[dict[str, str]]:
    value = validate_model_input(model_input)
    catalog = {"format_version": FORMAT_ID, "tools": value["tools"]}
    return [
        {"role": "system", "content": _descriptor()["instruction"] + "\n" + encode_json(catalog)}
    ] + [
        {"role": message["role"], "content": encode_json({"message_index": i, "message": message})}
        for i, message in enumerate(value["messages"])
    ]


def encode_action(action: dict) -> str:
    return encode_json(validate_action(action))
