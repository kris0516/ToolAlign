"""Reconstruct rendered audit views and compare every semantic value to packets.

Read-only CPU verification of display coverage, not a semantic quality verdict.
Uses saved views, including cross-packet string and parsed-observation references.
"""

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path


def verify(view_path, packets):
    text = view_path.read_text(encoding="utf-8")
    metadata = json.loads(view_path.with_suffix(".json").read_text())
    assert hashlib.sha256(text.encode()).hexdigest() == metadata["view_sha256"]
    strings, observations, rendered = {}, {}, {}
    current = None

    def resolve(value, label):
        if isinstance(value, dict):
            assert len(value) == 1
            if "exact_string_ref" in value:
                return strings[value["exact_string_ref"]]
            return json.dumps(observations[value["equal_json_value_ref"]], ensure_ascii=False)
        assert isinstance(value, str)
        strings[label] = value
        return value

    for line in text.splitlines():
        if line.startswith("PACKET "):
            _, name, identity = line.split(" ", 2)
            current = {"identity": json.loads(identity), "turns": [], "messages": [],
                       "tools": {}, "targets": []}
            assert name not in rendered
            rendered[name] = current
        elif line.startswith("RAW_SYSTEM_HEAD "):
            current["head"] = resolve(json.loads(line.removeprefix("RAW_SYSTEM_HEAD ")), name + ":raw_head")
        elif line.startswith("RAW_TOOLS "):
            current["raw_tools"] = json.loads(line.removeprefix("RAW_TOOLS "))
        elif line.startswith("RAW_SYSTEM_TAIL "):
            current["tail"] = resolve(json.loads(line.removeprefix("RAW_SYSTEM_TAIL ")), name + ":raw_tail")
        elif line.startswith("RAW_TURN "):
            _, index, value = line.split(" ", 2)
            assert int(index) == len(current["turns"])
            turn = json.loads(value)
            label = f"{name}:turn{index}"
            turn["value"] = resolve(turn["value"], label)
            current["turns"].append(turn)
            if turn["from"] == "tool":
                try:
                    results = json.loads(turn["value"])
                    for offset, item in enumerate(results):
                        if isinstance(item, dict) and "results" in item:
                            observations[f"{label}:json[{offset}].results"] = item["results"]
                except (ValueError, TypeError):
                    pass
        elif line.startswith("NORMALIZED_TOOL "):
            match = re.fullmatch(r"NORMALIZED_TOOL (\d+):(\d+) raw_tool_index=(\d+) DELTA (.*)", line)
            toolset, index, raw_index = map(int, match.groups()[:3])
            tool = {key: copy.deepcopy(current["raw_tools"][raw_index][key])
                    for key in ("name", "description", "parameters")}
            for operation in json.loads(match.group(4)):
                action, pointer, *value = operation
                parts = pointer.removeprefix("/").split("/")
                container = tool
                for part in parts[:-1]:
                    container = container[part]
                if action == "remove":
                    del container[parts[-1]]
                else:
                    assert action in {"replace", "add"}
                    container[parts[-1]] = value[0]
            current["tools"][(toolset, index)] = tool
        elif line.startswith("NORMALIZED_MESSAGE "):
            _, index, value = line.split(" ", 2)
            assert int(index) == len(current["messages"])
            message = json.loads(value)
            message["content"] = resolve(message["content"], f"{name}:normalized_message{index}.content")
            current["messages"].append(message)
        elif line.startswith("TARGET "):
            current["targets"].append(json.loads(line.removeprefix("TARGET ")))
    assert set(rendered) == {item["packet"] for item in metadata["coverage"]}
    totals = {"sources": 0, "decisions": 0, "raw_turns": 0, "prefix_messages": 0}
    for name, actual in rendered.items():
        packet_path = packets / (name + ".json")
        packet = json.loads(packet_path.read_text())
        recorded = next(item for item in metadata["coverage"] if item["packet"] == name)
        assert hashlib.sha256(packet_path.read_bytes()).hexdigest() == recorded["packet_sha256"]
        source = packet["source"]
        span = packet["valid_decisions"][0]["lineage"]["system_conversion"]["schema_span"]
        assert actual["head"] == source["system"][:span[0]]
        assert actual["tail"] == source["system"][span[1]:]
        assert actual["raw_tools"] == json.loads(source["system"][span[0]:span[1]])
        assert actual["turns"] == source["conversations"]
        assert len(actual["targets"]) == len(packet["valid_decisions"])
        for target, decision in zip(actual["targets"], packet["valid_decisions"]):
            example = decision["example"]
            assert target["source_turn_index"] == decision["lineage"]["source_turn_index"]
            assert target["example_id"] == example["example_id"]
            assert target["expected_action"] == example["expected_action"]
            messages = [copy.deepcopy(actual["messages"][index]) for index in target["complete_prefix_message_refs"]]
            expected_messages = copy.deepcopy(example["messages"])
            # Observation references preserve exact JSON values, rather than serialization spacing.
            for sequence in (messages, expected_messages):
                for message in sequence:
                    if message["role"] == "tool":
                        try:
                            message["content"] = json.loads(message["content"])
                        except ValueError:
                            pass
            assert messages == expected_messages
            for index, tool in enumerate(example["tools"]):
                assert actual["tools"][(target["toolset"], index)] == {
                    "name": tool["name"], "description": tool["description"],
                    "parameters": tool["parameters_json_schema"],
                }
            totals["prefix_messages"] += len(messages)
        totals["sources"] += 1
        totals["decisions"] += len(actual["targets"])
        totals["raw_turns"] += len(actual["turns"])
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", type=Path, required=True)
    args = parser.parse_args()
    totals = {"views": 0, "sources": 0, "decisions": 0, "raw_turns": 0, "prefix_messages": 0}
    for root in (args.audit_root, args.audit_root / "material-review"):
        for view_path in sorted((root / "views").glob("*.txt")):
            result = verify(view_path, root / "frozen" / "packets")
            totals["views"] += 1
            for key, value in result.items():
                totals[key] += value
    assert totals["sources"] == 222 and totals["decisions"] == 251
    print(json.dumps({"status": "PASS", "coverage": totals, "semantic_verdicts_computed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
