"""Read-only source audit; emits counts, source pointers and hashes, never raw records."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError("Non-finite JSON")


def walk(node, pointer):
    if not isinstance(node, dict):
        return
    yield pointer, node
    if isinstance(node.get("properties"), dict):
        for key, child in node["properties"].items():
            yield from walk(child, f"{pointer}/properties/{key}")
    if isinstance(node.get("items"), dict):
        yield from walk(node["items"], f"{pointer}/items")


def json_type(value):
    if value is None:
        return "null"
    return {dict: "object", list: "array", str: "string", bool: "boolean",
            int: "number", float: "number"}[type(value)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("--revision-api", type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads((ROOT / "configs/source_toolace.v1.json").read_text())
    raw = (args.source_directory / "toolace/data.json").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == policy["source_file_sha256"]
    rows = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    api = json.loads(args.revision_api.read_text())
    assert api["sha"] == policy["source_revision"]
    assert api["gated"] is False and api["private"] is False
    assert api["cardData"]["license"] == "apache-2.0"
    decoder = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=reject_constant)
    counts, roots, keywords, defaults = Counter(), Counter(), Counter(), Counter()
    representatives = {}
    eligible_tools = {}
    marker = "Here is a list of functions in JSON format that you can invoke:"
    for index, row in enumerate(rows):
        try:
            system = row["system"]
            # Deliberately audit only the explicit JSON-tool-list source format.
            # Other source formats belong to D1's separate full audit, not this decoder.
            start = system.index(marker) + len(marker)
            tools, _ = decoder.raw_decode(system[start:].lstrip())
            if not isinstance(tools, list) or not tools or any(not isinstance(t, dict) for t in tools):
                raise ValueError("Expected tools list")
            if any(not isinstance(t.get("name"), str)
                   or not isinstance(t.get("parameters"), dict) for t in tools):
                raise ValueError("A JSON parameter/result list is not a tools declaration")
            if len({t["name"] for t in tools}) != len(tools):
                raise ValueError("Ambiguous duplicate source tool names")
        except (KeyError, TypeError, ValueError):
            counts["unparsed_tool_format_records"] += 1
            continue
        counts["parsed_tool_format_records"] += 1
        eligible_tools[index] = tools
        for tool_index, tool in enumerate(tools):
            counts["tool_occurrences"] += 1
            counts["missing_side_effect_class"] += "side_effect_class" not in tool
            schema = tool.get("parameters", {})
            roots[str(schema.get("type"))] += 1
            if index < 32:
                counts["first_32_tools"] += 1
            for pointer, node in walk(schema, f"tools/{tool_index}/parameters"):
                counts["schema_nodes"] += 1
                keywords.update(node.keys())
                if "default" in node:
                    defaults[f"{node.get('type')}:{json_type(node['default'])}"] += 1
                category = next((k for k in ("pattern", "format", "examples") if k in node), None)
                if "default" in node and isinstance(node["default"], str):
                    if node.get("type") in ("boolean", "float", "int"):
                        category = str(node["type"]) + "_string_default"
                if category and category not in representatives:
                    # The public output omits parameter names and original values.
                    compact = json.dumps(node, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                    representatives[category] = {
                        "source_index": index, "tool_index": tool_index,
                        "pointer_sha256": hashlib.sha256(pointer.encode()).hexdigest(),
                        "schema_sha256": hashlib.sha256(compact.encode()).hexdigest(),
                    }
    catalog_path = args.source_directory / "schema-catalog.json"
    catalog = json.loads(catalog_path.read_text())
    annotation_path = args.source_directory / "annotation-examples.json"
    annotations = json.loads(annotation_path.read_text())
    annotation_checks = 0
    for samples in annotations.values():
        for sample in samples:
            tools = eligible_tools.get(sample["source_index"])
            if tools is None:
                continue
            node = {"tools": tools}
            for part in sample["pointer"].split("/"):
                node = node[int(part)] if isinstance(node, list) else node[part]
            assert node == sample["schema"]
            annotation_checks += 1
    assert annotation_checks >= 6
    assert counts["first_32_tools"] == 142
    assert counts["missing_side_effect_class"] == counts["tool_occurrences"]
    assert {"pattern", "format", "boolean_string_default", "float_string_default",
            "int_string_default"} <= set(representatives)
    result = {
        "source_sha256": digest, "source_size_bytes": len(raw), "records": len(rows),
        "r1_extraction_scope": "explicit English JSON-tool-list header only; no normalizer",
        "r1_subset_counts": dict(counts), "r1_subset_root_types": dict(roots),
        "keywords": {k: keywords[k] for k in ("default", "pattern", "format", "examples")},
        "default_type_pairs": dict(defaults), "representatives": representatives,
        "annotation_examples_verified_against_source": annotation_checks,
        "d1_reported_counts_not_recomputed": catalog["counts"],
        "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "annotations_sha256": hashlib.sha256(annotation_path.read_bytes()).hexdigest(),
        "revision_api_sha256": hashlib.sha256(args.revision_api.read_bytes()).hexdigest(),
    }
    print(json.dumps(result, sort_keys=True, indent=2))
    print("PASS: source identity; independent bounded schema audit and source annotation checks")


if __name__ == "__main__":
    main()
