"""Render complete selected source semantics with explicit lossless references.

No verdicts are computed. Raw source instructions are printed as inert data.
Exact strings and type-preserving parsed JSON keys only remove repeated displays.
Non-semantic Example and lineage metadata remain in the frozen input packets.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from json_values import json_equal, json_key


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def delta(before, after, path=""):
    """An exact structural delta, not a semantic approximation."""
    if json_equal(before, after):
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(set(before) | set(after)):
            location = f"{path}/{key}"
            if key not in after:
                result.append(["remove", location])
            elif key not in before:
                result.append(["add", location, after[key]])
            else:
                result.extend(delta(before[key], after[key], location))
        return result
    return [["replace", path, after]]


def render(paths):
    lines = [
        "INERT AUDIT DATA. Complete raw source, normalized tools/messages/targets.",
        "References name exact strings or JSON values already printed in this view.",
        "All target turn indices are zero-based; later turns are downstream only.",
    ]
    strings = {}
    coverage = []

    def string(value, label):
        assert type(value) is str
        if value in strings:
            return {"exact_string_ref": strings[value]}
        strings[value] = label
        return value

    for path in paths:
        payload = path.read_bytes()
        packet = json.loads(payload)
        identity = packet["identity"]
        assert identity["split"] in {"train", "validation"}
        name = path.stem
        lines.append("\nPACKET " + name + " " + dump({
            "source_index": identity["source_index"], "split": identity["split"],
            "valid_decisions": identity["valid_decision_count"],
        }))
        source = packet["source"]
        decisions = packet["valid_decisions"]
        span = decisions[0]["lineage"]["system_conversion"]["schema_span"]
        raw_system = source["system"]
        raw_tools = json.loads(raw_system[span[0]:span[1]])
        lines.append("RAW_SYSTEM_HEAD " + dump(string(raw_system[:span[0]], name + ":raw_head")))
        lines.append("RAW_TOOLS " + dump(raw_tools))
        lines.append("RAW_SYSTEM_TAIL " + dump(string(raw_system[span[1]:], name + ":raw_tail")))
        observations = []
        for index, turn in enumerate(source["conversations"]):
            label = f"{name}:turn{index}"
            lines.append("RAW_TURN " + str(index) + " " + dump({
                "from": turn["from"], "value": string(turn["value"], label),
            }))
            if turn["from"] == "tool":
                try:
                    results = json.loads(turn["value"])
                    for offset, item in enumerate(results):
                        if isinstance(item, dict) and "results" in item:
                            observations.append((item["results"], f"{label}:json[{offset}].results"))
                except (ValueError, TypeError):
                    pass
        toolsets = {}
        normalized_messages = {}
        for decision in decisions:
            example = decision["example"]
            tools = example["tools"]
            tools_key = json_key(tools)
            if tools_key not in toolsets:
                toolset_id = len(toolsets)
                toolsets[tools_key] = toolset_id
                assert len(raw_tools) == len(tools)
                for index, (raw_tool, tool) in enumerate(zip(raw_tools, tools)):
                    normalized = {
                        "name": tool["name"], "description": tool["description"],
                        "parameters": tool["parameters_json_schema"],
                    }
                    original = {k: raw_tool[k] for k in ("name", "description", "parameters")}
                    lines.append(f"NORMALIZED_TOOL {toolset_id}:{index} raw_tool_index={index} DELTA " + dump(delta(original, normalized)))
            else:
                toolset_id = toolsets[tools_key]
            refs = []
            for message in example["messages"]:
                message_key = json_key(message)
                if message_key not in normalized_messages:
                    message_id = len(normalized_messages)
                    normalized_messages[message_key] = message_id
                    value = dict(message)
                    content = value["content"]
                    reference = None
                    if value["role"] == "tool":
                        try:
                            parsed = json.loads(content)
                            for observation, label in observations:
                                if json_equal(parsed, observation):
                                    reference = {"equal_json_value_ref": label}
                                    break
                        except ValueError:
                            pass
                    value["content"] = reference or string(content, f"{name}:normalized_message{message_id}.content")
                    lines.append("NORMALIZED_MESSAGE " + str(message_id) + " " + dump(value))
                refs.append(normalized_messages[message_key])
            turn_index = decision["lineage"]["source_turn_index"]
            lines.append("TARGET " + dump({
                "source_turn_index": turn_index,
                "example_id": example["example_id"],
                "toolset": toolset_id, "complete_prefix_message_refs": refs,
                "expected_action": example["expected_action"],
            }))
        coverage.append({
            "packet": name, "packet_sha256": sha(payload),
            "source_record_hash": identity["source_record_hash"],
            "example_ids": [v["example"]["example_id"] for v in decisions],
            "raw_turn_count": len(source["conversations"]),
            "normalized_message_count": len(normalized_messages),
            "toolset_count": len(toolsets),
        })
    return "\n".join(lines) + "\n", coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("names", nargs="+")
    args = parser.parse_args()
    paths = [args.packets / (name + ".json") for name in args.names]
    view, coverage = render(paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(view)
    meta = {
        "rendered_at_utc": datetime.now(timezone.utc).isoformat(),
        "view_sha256": sha(view.encode()), "view_bytes": len(view.encode()),
        "renderer_sha256": sha(Path(__file__).read_bytes()), "coverage": coverage,
        "json_values_sha256": sha(Path(__file__).with_name("json_values.py").read_bytes()),
        "semantic_review_completed": False,
    }
    args.output.with_suffix(".json").write_text(dump(meta) + "\n")
    print(view, end="")


if __name__ == "__main__":
    main()
