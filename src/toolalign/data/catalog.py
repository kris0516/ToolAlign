"""Aggregate schema dialect evidence and private source pointers for S0 review."""

from collections import Counter, defaultdict

from .common import DataError
from .toolace import extract_tools

KNOWN_TYPES = {
    "dict",
    "object",
    "array",
    "string",
    "int",
    "integer",
    "float",
    "number",
    "bool",
    "boolean",
    "null",
}
KEYWORDS = {
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
    "default",
    "pattern",
    "format",
    "$ref",
    "$id",
    "anyOf",
    "oneOf",
    "allOf",
    "examples",
    "title",
}


def schema_catalog(records):
    counts = Counter()
    types = Counter()
    keywords = Counter()
    defaults = Counter()
    representatives = defaultdict(list)
    root_types = Counter()

    def visit(node, index, pointer, depth=0):
        if depth > 32 or not isinstance(node, dict):
            counts["invalid_or_excessively_deep_node"] += 1
            return
        counts["schema_nodes"] += 1
        raw_type = node.get("type")
        kind = (
            raw_type
            if isinstance(raw_type, str) and raw_type in KNOWN_TYPES
            else "union"
            if isinstance(raw_type, list)
            else "other_or_missing"
        )
        types[kind] += 1
        for key in node:
            category = key if key in KEYWORDS else "other"
            keywords[category] += 1
            if (
                key
                in {
                    "default",
                    "pattern",
                    "format",
                    "enum",
                    "$ref",
                    "$id",
                    "oneOf",
                    "anyOf",
                    "allOf",
                }
                and len(representatives[category]) < 3
            ):
                representatives[category].append(
                    {"source_index": index, "pointer": pointer, "schema": node}
                )
        if "default" in node:
            default = node["default"]
            dtype = (
                "null"
                if default is None
                else "boolean"
                if isinstance(default, bool)
                else "number"
                if isinstance(default, (float, int))
                else "string"
                if isinstance(default, str)
                else "object"
                if isinstance(default, dict)
                else "array"
            )
            defaults[f"{kind}:{dtype}"] += 1
        props = node.get("properties")
        if isinstance(props, dict):
            for key, child in props.items():
                escaped = key.replace("~", "~0").replace("/", "~1")
                visit(child, index, pointer + "/properties/" + escaped, depth + 1)
        if "items" in node:
            visit(node["items"], index, pointer + "/items", depth + 1)

    for i, record in enumerate(records):
        try:
            tools, _ = extract_tools(record)
        except DataError:
            counts["unparsed_tool_format_records"] += 1
            continue
        counts["parsed_tool_format_records"] += 1
        for j, tool in enumerate(tools):
            counts["tool_occurrences"] += 1
            if tool.get("required") is not None:
                counts["outer_required_non_null"] += 1
            node = tool.get("parameters")
            raw_type = node.get("type") if isinstance(node, dict) else None
            root_types[
                raw_type if isinstance(raw_type, str) and raw_type in KNOWN_TYPES else "other"
            ] += 1
            visit(node, i, f"tools/{j}/parameters")
    return {
        "counts": dict(sorted(counts.items())),
        "root_types": dict(sorted(root_types.items())),
        "node_types": dict(sorted(types.items())),
        "keyword_occurrences": dict(sorted(keywords.items())),
        "default_declared_type_to_value_type": dict(sorted(defaults.items())),
    }, dict(representatives)
