"""Audited ToolACE JSON-list parsing and explicit source-policy conversion.

Unknown dialects and unlabelled prose are quarantined. Only the approved policy
may rewrite tool identities/constraints; historical tools have no execution binding.
"""

from __future__ import annotations

import copy
import re

from toolalign.contracts import (
    ContractError,
    canonical_hash,
    model_input_from_example,
    validate_record,
    validate_tool_arguments,
)

from .common import DECODER, DataError, encoded, loads
from .grouping import schema_shape

MARKER = "Here is a list of functions in JSON format that you can invoke:"
TOOL_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
PARAMETER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def extract_tools(record):
    if not isinstance(record, dict) or set(record) != {"system", "conversations"}:
        raise DataError("record_shape")
    text = record["system"]
    if not isinstance(text, str) or text.count(MARKER) != 1:
        raise DataError("unsupported_tool_format")
    start = text.index(MARKER) + len(MARKER)
    rest = text[start:]
    left = len(rest) - len(rest.lstrip())
    try:
        tools, end = DECODER.raw_decode(rest, left)
        canonical_hash(tools)
    except (ValueError, RecursionError, ContractError) as exc:
        raise DataError("tool_json_invalid") from exc
    if not isinstance(tools, list) or not 0 <= len(tools) <= 64:
        raise DataError("tool_list_shape")
    if any(not isinstance(t, dict) for t in tools):
        raise DataError("tool_list_shape")
    # This span supports exact source length attribution, not prompt rewriting.
    return tools, (start + left, start + end)


def schema_findings(schema, depth=0):
    """Diagnostic flags only; the frozen P00 validator remains authoritative."""
    if depth > 12 or not isinstance(schema, dict):
        return {"schema_depth_or_shape"}
    flags = set()
    kind = schema.get("type")
    if not isinstance(kind, str) or kind not in {
        "object",
        "array",
        "string",
        "number",
        "integer",
        "boolean",
        "null",
    }:
        flags.add("schema_type_unsupported")
    if kind in ("dict", "object"):
        if schema.get("additionalProperties") is not False:
            flags.add("schema_object_unclosed")
        props = schema.get("properties")
        if not isinstance(props, dict):
            flags.add("schema_properties_missing")
        else:
            for child in props.values():
                flags.update(schema_findings(child, depth + 1))
    if kind == "string" and "maxLength" not in schema:
        flags.add("schema_string_unbounded")
    if kind == "array":
        if "maxItems" not in schema:
            flags.add("schema_array_unbounded")
        flags.update(schema_findings(schema.get("items"), depth + 1))
    known = {
        "type",
        "description",
        "enum",
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
    }
    if set(schema) - known:
        flags.add("schema_keyword_unsupported")
    return flags


def tool_findings(raw):
    flags = schema_findings(raw.get("parameters"))
    if not isinstance(raw.get("name"), str) or not TOOL_NAME.fullmatch(raw["name"]):
        flags.add("tool_name_incompatible")
    if not isinstance(raw.get("side_effect_class"), str) or raw["side_effect_class"] not in {
        "read_only",
        "sandbox_only",
    }:
        flags.add("side_effect_unknown_or_forbidden")
    if "tool_version" not in raw or "timeout_ms" not in raw:
        flags.add("tool_runtime_metadata_missing")
    # A diagnostic probe contains fixed metadata only to ask P00 about the original
    # parameter schema. It is never an accepted tool or an emitted training record.
    probe = {
        "schema_version": "toolalign.tool.v1",
        "name": "schema_probe",
        "description": "Parameter-only diagnostic",
        "parameters_json_schema": raw.get("parameters"),
        "tool_version": "probe",
        "side_effect_class": "sandbox_only",
        "timeout_ms": 1,
    }
    try:
        validate_record(probe, "tool")
    except ContractError:
        flags.add("schema_contract_rejected")
    return flags


def convert_tool(raw):
    allowed = {
        "name",
        "description",
        "parameters",
        "required",
        "tool_version",
        "timeout_ms",
        "side_effect_class",
    }
    if set(raw) - allowed or raw.get("required") is not None:
        raise DataError("tool_metadata_ambiguous")
    if tool_findings(raw):
        raise DataError("tool_incompatible")
    tool = {
        "schema_version": "toolalign.tool.v1",
        "name": raw["name"],
        "description": raw.get("description"),
        "parameters_json_schema": raw["parameters"],
        "tool_version": raw["tool_version"],
        "side_effect_class": raw["side_effect_class"],
        "timeout_ms": raw["timeout_ms"],
    }
    try:
        return validate_record(tool, "tool")
    except ContractError as exc:
        raise DataError("tool_contract_rejected") from exc


def parse_calls(text, names):
    """Parse [exact_name(key=JSON, ...), ...] with a bounded literal grammar.

    Names may contain spaces in the source audit. Only convert_tool decides wire
    compatibility. Python expressions, positional args, single quotes, trailing
    text, duplicate keys and non-finite values are rejected, never evaluated.
    """
    if not isinstance(text, str) or len(text) > 131072:
        raise DataError("call_text_budget")
    text = text.strip()
    if not text.startswith("["):
        raise DataError("action_kind_unlabelled")
    if not names or any(not isinstance(n, str) for n in names) or len(set(names)) != len(names):
        raise DataError("ambiguous_tool_names")
    pos = 1
    result = []

    def whitespace():
        nonlocal pos
        while pos < len(text) and text[pos].isspace():
            pos += 1

    def consume(char):
        nonlocal pos
        whitespace()
        if pos >= len(text) or text[pos] != char:
            raise DataError("call_syntax_unsupported")
        pos += 1

    while True:
        whitespace()
        matches = [n for n in names if text.startswith(n + "(", pos)]
        if len(matches) != 1 or len(result) >= 16:
            raise DataError("call_name_or_count")
        name = matches[0]
        pos += len(name) + 1
        arguments = {}
        whitespace()
        if pos < len(text) and text[pos] != ")":
            while True:
                whitespace()
                key = PARAMETER.match(text, pos)
                if key is None or key[0] in arguments:
                    raise DataError("call_parameter_invalid")
                pos = key.end()
                consume("=")
                whitespace()
                try:
                    value, pos = DECODER.raw_decode(text, pos)
                    canonical_hash(value)
                except (ValueError, RecursionError, ContractError) as exc:
                    raise DataError("call_value_not_json") from exc
                arguments[key[0]] = value
                if len(arguments) > 128:
                    raise DataError("call_parameter_budget")
                whitespace()
                if pos >= len(text) or text[pos] != ",":
                    break
                pos += 1
        consume(")")
        result.append({"name": name, "arguments": arguments})
        whitespace()
        if pos < len(text) and text[pos] == ",":
            pos += 1
            continue
        consume("]")
        whitespace()
        if pos != len(text):
            raise DataError("call_trailing_text")
        return result


def message(role, content="", calls=None, call_id=None):
    return {"role": role, "content": content, "tool_calls": calls or [], "tool_call_id": call_id}


def inspect_record(record, source, source_index, policy=None):
    """Return all decision outcomes plus disjoint primary and overlapping reasons."""
    record_hash = canonical_hash(record)
    info = {
        "source_index": source_index,
        "source_record_hash": record_hash,
        "record_reasons": [],
        "tool_findings": {},
        "tool_keys": [],
        "schema_keys": [],
        "decisions": [],
        "schema_span": None,
        "tool_occurrences": 0,
        "tool_occurrence_findings": [],
    }
    try:
        tools, span = extract_tools(record)
        info["schema_span"] = list(span)
    except DataError as exc:
        tools = []
        info["record_reasons"].append(str(exc))
    for tool in tools:
        flags = sorted(tool_findings(tool))
        info["tool_occurrences"] += 1
        info["tool_occurrence_findings"].append(flags)
        info["tool_findings"][canonical_hash(tool)] = flags
        info["record_reasons"].extend(flags)
        info["tool_keys"].append(canonical_hash({"name": tool.get("name")}))
        info["schema_keys"].append(canonical_hash(schema_shape(tool.get("parameters"))))
    info["record_reasons"] = sorted(set(info["record_reasons"]))
    conversations = record.get("conversations", []) if isinstance(record, dict) else []
    if not isinstance(conversations, list) or not conversations:
        info["record_reasons"].append("conversation_shape")
        return info, []
    normalized_tools = []
    name_mapping = {}
    system_text = record.get("system", "") if isinstance(record, dict) else ""
    if policy is not None:
        info["strict_record_reasons"] = list(info["record_reasons"])
        info["record_reasons"] = (
            [] if info["schema_span"] is not None else list(info["record_reasons"])
        )
        info["policy_hash"] = policy.hash
        info["record_scope"] = "historical_supervision_only"
        info["execution_binding"] = "none"
        info["original_side_effect_class"] = "unknown"
        info["raw_tool_hashes"] = [canonical_hash(t) for t in tools]
        info["normalized_schema_keys"] = []
        info["observation_bindings"] = []
        for raw in tools:
            try:
                adapted = policy.convert_tool(raw)
                if adapted["raw_name"] in name_mapping:
                    raise DataError("policy_duplicate_source_tool_name")
                name_mapping[adapted["raw_name"]] = adapted["normalized_name"]
                normalized_tools.append(adapted["tool"])
                info["normalized_schema_keys"].append(adapted["normalized_schema_key"])
            except DataError as exc:
                if str(exc) == "normalized_name_hash_collision":
                    raise
                info["record_reasons"].append(str(exc))
        if info["schema_span"] is not None:
            try:
                system_text, info["system_conversion"] = policy.normalize_system(
                    system_text, info["schema_span"], MARKER
                )
            except DataError as exc:
                info["record_reasons"].append(str(exc))
        info["record_reasons"] = sorted(set(info["record_reasons"]))
    elif not info["record_reasons"]:
        try:
            normalized_tools = [convert_tool(t) for t in tools]
        except DataError as exc:
            info["record_reasons"].append(str(exc))
    history = [message("system", system_text)]
    pending = []
    history_bad = False
    examples = []
    record_policy_failures = set()
    registered = {tool["name"]: tool for tool in normalized_tools}
    for index, turn in enumerate(conversations):
        if (
            not isinstance(turn, dict)
            or set(turn) != {"from", "value"}
            or not isinstance(turn.get("value"), str)
        ):
            history_bad = True
            if isinstance(turn, dict) and turn.get("from") == "assistant":
                info["decisions"].append(
                    {
                        "turn_index": index,
                        "reasons": ["assistant_turn_shape"],
                        "normalized_hash": None,
                    }
                )
            continue
        role, value = turn["from"], turn["value"]
        if role == "assistant":
            reasons = list(info["record_reasons"])
            calls = []
            call_bindings = []
            try:
                parsed = parse_calls(value, [t.get("name") for t in tools])
                calls = [{"call_id": f"c-{index}-{j}", **c} for j, c in enumerate(parsed)]
                if policy is not None and not info["record_reasons"]:
                    for call in calls:
                        raw_name = call["name"]
                        call["name"] = name_mapping[call["name"]]
                        call_bindings.append(
                            {
                                "call_id": call["call_id"],
                                "raw_name": raw_name,
                                "normalized_name": call["name"],
                                "arguments_hash": canonical_hash(call["arguments"]),
                                "arguments_filled_or_coerced": False,
                                "rule": "safe_literal_parse_then_name_mapping_only.v1",
                            }
                        )
                        try:
                            validate_tool_arguments(registered[call["name"]], call["arguments"])
                        except ContractError:
                            reasons.append("out_of_policy_arguments")
                            record_policy_failures.add("out_of_policy_arguments")
            except DataError as exc:
                reasons.append(str(exc))
                if policy is not None and value.lstrip().startswith("["):
                    record_policy_failures.add("policy_source_call_parse_error")
                    history_bad = True
            if history_bad or pending or history[-1]["role"] not in {"user", "tool"}:
                reasons.append("invalid_history_prefix")
            example = None
            if not reasons:
                example = {
                    "schema_version": "toolalign.example.v1",
                    "example_id": "pending",
                    **source,
                    "source_record_hash": record_hash,
                    "group_id": "pending",
                    "split": "train",
                    "messages": copy.deepcopy(history),
                    "tools": normalized_tools,
                    "expected_action": {"kind": "tool_calls", "tool_calls": calls, "content": ""},
                    "category": "tool_calls",
                }
                try:
                    validate_record(example, "example")
                    # Validate historical arguments too; P00 only checks target args.
                    registered = {t["name"]: t for t in normalized_tools}
                    for m in history:
                        for c in m["tool_calls"]:
                            validate_tool_arguments(registered[c["name"]], c["arguments"])
                    model_input_from_example(example)
                except (ContractError, KeyError):
                    reasons.append("example_contract_rejected")
            decision = {
                "turn_index": index,
                "reasons": sorted(set(reasons)),
                "normalized_hash": None,
            }
            if policy is not None:
                from .source_policy import text_hash

                decision["source_action_sha256"] = text_hash(value)
                decision["prefix_turn_end_exclusive"] = index
                decision["call_bindings"] = call_bindings
            if not reasons:
                # split/group/ID assigned after all records have been grouped.
                payload = {
                    k: v for k, v in example.items() if k not in {"example_id", "group_id", "split"}
                }
                decision["normalized_hash"] = canonical_hash(payload)
                example["example_id"] = decision["normalized_hash"]
                examples.append(example)
            info["decisions"].append(decision)
            if calls:
                history.append(message("assistant", calls=calls))
                pending = calls
            else:
                # Prose is retained only as history, not assigned an action kind.
                history.append(message("assistant", value))
        elif role == "tool":
            try:
                observations = loads(value)
                if (
                    not isinstance(observations, list)
                    or len(observations) != len(pending)
                    or not pending
                ):
                    raise DataError("tool_observation_shape")
                if len({c["name"] for c in pending}) != len(pending):
                    raise DataError("tool_observation_ambiguous")
                if any(
                    not isinstance(o, dict) or set(o) != {"name", "results"} for o in observations
                ):
                    raise DataError("tool_observation_shape")
                by_name = {o["name"]: o for o in observations}
                if policy is not None and not info["record_reasons"]:
                    try:
                        by_name = {
                            name_mapping[name]: observation for name, observation in by_name.items()
                        }
                    except KeyError as exc:
                        raise DataError("tool_observation_mismatch") from exc
                if len(by_name) != len(pending) or set(by_name) != {c["name"] for c in pending}:
                    raise DataError("tool_observation_mismatch")
                for call in pending:
                    if policy is not None and not info["record_reasons"]:
                        info["observation_bindings"].append(
                            {
                                "source_turn_index": index,
                                "raw_name": by_name[call["name"]]["name"],
                                "normalized_name": call["name"],
                                "call_id": call["call_id"],
                                "results_hash": canonical_hash(by_name[call["name"]]["results"]),
                                "evidence_kind": "historical_observation_only",
                                "executed_here": False,
                            }
                        )
                    history.append(
                        message(
                            "tool",
                            encoded(by_name[call["name"]]["results"]).decode(),
                            call_id=call["call_id"],
                        )
                    )
                pending = []
            except (DataError, TypeError):
                history_bad = True
                if policy is not None:
                    record_policy_failures.add("policy_history_observation_unreliable")
        elif role == "user":
            if pending:
                history_bad = True
            history.append(message("user", value))
        else:
            history_bad = True
    if policy is not None and record_policy_failures:
        examples = []
        info["record_reasons"] = sorted(set(info["record_reasons"]) | record_policy_failures)
        for decision in info["decisions"]:
            if decision["normalized_hash"] is not None:
                decision["attempted_normalized_hash"] = decision["normalized_hash"]
            decision["normalized_hash"] = None
            decision["reasons"] = sorted(set(decision["reasons"]) | record_policy_failures)
    return info, examples
