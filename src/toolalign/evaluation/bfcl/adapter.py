"""Lossless schema/name projection and strict Action decoding, independent of answers."""

from __future__ import annotations

import copy
import re

from toolalign.contracts import ContractError, validate_record
from toolalign.model_io.format import validate_model_input
from toolalign.tools._json import parse_action

from . import COMMIT


class Unrepresentable(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__(";".join(sorted({item["code"] for item in issues})))


def parameter_projection(schema, path=()):
    """Translate type spellings only. Never infer closed objects or new bounds."""
    result = copy.deepcopy(schema)
    rewrites = []
    if not isinstance(result, dict):
        return result, rewrites
    kind = result.get("type")
    aliases = {"dict": "object", "float": "number"}
    if isinstance(kind, str) and kind in aliases:
        result["type"] = aliases[kind]
        rewrites.append({"path": list(path) + ["type"], "from": kind, "to": aliases[kind]})
    for name, child in result.get("properties", {}).items():
        result["properties"][name], changes = parameter_projection(child, (*path, "properties", name))
        rewrites.extend(changes)
    if "items" in result:
        result["items"], changes = parameter_projection(result["items"], (*path, "items"))
        rewrites.extend(changes)
    return result, rewrites


def restore_parameters(schema, rewrites):
    restored = copy.deepcopy(schema)
    for change in rewrites:
        target = restored
        for key in change["path"][:-1]:
            target = target[key]
        if target[change["path"][-1]] != change["to"]:
            raise ValueError("parameter_projection_binding")
        target[change["path"][-1]] = change["from"]
    return restored


def schema_issues(schema, path=()):
    """Explain all material frozen-contract exclusions without changing the schema."""
    issues = []

    def issue(code):
        issues.append({"path": list(path), "code": code})

    if type(schema) is not dict:
        issue("schema_not_object")
        return issues
    kind = schema.get("type")
    keywords = {
        "object": {"properties", "required", "additionalProperties"},
        "array": {"items", "minItems", "maxItems"},
        "string": {"minLength", "maxLength"},
        "integer": {"minimum", "maximum"}, "number": {"minimum", "maximum"},
        "boolean": set(), "null": set(),
    }
    if not isinstance(kind, str) or kind not in keywords:
        issue("unsupported_parameter_type")
        return issues
    if set(schema) - ({"type", "description", "enum"} | keywords[kind]):
        issue("unsupported_schema_keyword")
    if kind == "object":
        if schema.get("additionalProperties") is not False:
            issue("object_not_explicitly_closed")
        properties = schema.get("properties")
        if not isinstance(properties, dict) or len(properties) > 128:
            issue("unsupported_object_properties")
        else:
            for name, child in properties.items():
                issues.extend(schema_issues(child, (*path, "properties", name)))
    if kind == "array":
        if type(schema.get("maxItems")) is not int or not 0 <= schema["maxItems"] <= 1000:
            issue("array_without_supported_bound")
        issues.extend(schema_issues(schema.get("items"), (*path, "items")))
    if kind == "string" and (type(schema.get("maxLength")) is not int
                             or not 0 <= schema["maxLength"] <= 16384):
        issue("string_without_supported_bound")
    return issues


def function_names(functions):
    """Readable aliases are collision-free by ordinal; retain the exact inverse."""
    names = [function.get("name") for function in functions]
    if (not all(type(name) is str and re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", name,
                                                 flags=re.ASCII) for name in names)
            or len(names) != len(set(names))):
        raise Unrepresentable([{"path": ["function"], "code": "unsupported_or_duplicate_function_name"}])
    forward = {name: f"bfcl_{i}_" + re.sub(r"[^a-z0-9_]", "_", name.lower())[:48]
               for i, name in enumerate(names)}
    inverse = {alias: name for name, alias in forward.items()}
    if len(inverse) != len(forward) or any(inverse[alias] != name for name, alias in forward.items()):
        raise ValueError("name_projection_not_reversible")
    return forward, inverse


def adapt_prompt(record):
    """No answers accepted here. Every source field is retained or explicitly rejected."""
    if (type(record) is not dict or set(record) != {"id", "question", "function"}
            or type(record["function"]) is not list or not 0 < len(record["function"]) <= 64):
        raise Unrepresentable([{"path": [], "code": "unsupported_prompt_fields_or_tool_count"}])
    forward, inverse = function_names(record["function"])
    tools, rewrites, issues = [], [], []
    for index, function in enumerate(record["function"]):
        if set(function) != {"name", "description", "parameters"}:
            issues.append({"path": ["function", index], "code": "unsupported_function_fields"})
            continue
        parameters, changes = parameter_projection(function["parameters"])
        if restore_parameters(parameters, changes) != function["parameters"]:
            raise ValueError("parameter_projection_not_reversible")
        issues.extend(schema_issues(parameters, ("function", index, "parameters")))
        tool = {
            "schema_version": "toolalign.tool.v1", "name": forward[function["name"]],
            "description": function["description"], "parameters_json_schema": parameters,
            "tool_version": "bfcl-" + COMMIT, "side_effect_class": "sandbox_only", "timeout_ms": 1000,
        }
        try:
            validate_record(tool, "tool")
        except ContractError as exc:
            issues.append({"path": ["function", index], "code": "frozen_tool_contract", "detail": str(exc)})
        tools.append(tool)
        rewrites.append({"function": function["name"], "type_rewrites": changes})
    question = record["question"]
    if (type(question) is not list or len(question) != 1 or type(question[0]) is not list
            or not question[0] or any(type(message) is not dict or set(message) != {"role", "content"}
                                     or message["role"] not in {"system", "user", "assistant"}
                                     or type(message["content"]) is not str for message in question[0])):
        issues.append({"path": ["question"], "code": "unsupported_question_history"})
    if issues:
        raise Unrepresentable(issues)
    messages = [{**message, "tool_calls": [], "tool_call_id": None} for message in question[0]]
    try:
        model_input = validate_model_input({"messages": messages, "tools": tools})
    except ContractError as exc:
        raise Unrepresentable([{"path": [], "code": "frozen_model_input_contract", "detail": str(exc)}]) from exc
    return {"model_input": model_input, "name_map": forward, "inverse_name_map": inverse,
            "schema_type_rewrites": rewrites}


class StrictActionDecoder:
    """Only this local decode interface is supplied to the real official scorer."""

    def __init__(self, name_map):
        self.inverse = {alias: original for original, alias in name_map.items()}
        if len(self.inverse) != len(name_map):
            raise ValueError("non_injective_function_mapping")

    def decode_ast(self, raw_text, language=None, has_tool_call_tag=False):
        action = parse_action(raw_text)
        if action["kind"] != "tool_calls":
            return []
        # Unknown aliases stay calls. Raising here would let official irrelevance
        # interpret an unadvertised tool as a no-tool response.
        return [{self.inverse.get(call["name"], "unadvertised:" + call["name"]): call["arguments"]}
                for call in action["tool_calls"]]
