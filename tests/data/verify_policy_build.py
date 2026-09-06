"""Check actual private artifacts and raw argument lineage, without re-converting.

This is a worker integrity check, not independent R1 or human semantic approval.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import file_hash, loads, read_json, verified_build_manifest, write_json
from toolalign.data.source_policy import POLICY_SHA256
from toolalign.data.toolace import extract_tools, parse_calls


def rows(path):
    with path.open(encoding="utf-8") as stream:
        return [loads(line) for line in stream]


class PacketHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details = 0
        self.headings = 0
        self.csp = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        assert tag not in {"script", "iframe", "object", "embed"}
        assert not ({"src", "href"} & attrs.keys())
        assert not any(name.startswith("on") for name in attrs)
        self.details += tag == "details"
        self.headings += tag == "h2"
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
            assert attrs["content"] == "default-src 'none'; style-src 'unsafe-inline'"
            self.csp = True


def verify(root, source_path):
    manifest = verified_build_manifest(root / "manifest.json")
    assert manifest["source_policy_hash"] == POLICY_SHA256
    assert manifest["execution_binding"] == "none"
    source_lock = read_json("data/manifests/toolace-source.v1.json")
    assert file_hash(source_path) == source_lock["files"]["data.json"]["sha256"]
    raw = {canonical_hash(record): record for record in read_json(source_path)}
    tools = {t["raw_tool_hash"]: t for t in rows(root / "tool-lineage.jsonl")}
    for identity, tool in tools.items():
        assert canonical_hash(tool["raw_tool"]) == identity
        assert canonical_hash(tool["tool"]) == tool["normalized_tool_hash"]
        assert tool["policy_hash"] == POLICY_SHA256
        assert (
            tool["execution_binding"] == "none" and tool["original_side_effect_class"] == "unknown"
        )
        assert all(
            not annotation["inserted_into_arguments"] for annotation in tool["default_annotations"]
        )
    examples = rows(root / "examples.jsonl")
    lineage = [r for r in rows(root / "lineage.jsonl") if r["exclusion_reason"] is None]
    by_id = {e["example_id"]: e for e in examples}
    assert len(examples) == len(by_id) == len(lineage)
    target_calls, historical_calls = 0, 0
    for row in lineage:
        example = by_id[row["example_id"]]
        record = raw[row["source_record_hash"]]
        assert example["source_record_hash"] == row["source_record_hash"]
        assert example["group_id"] == row["group_id"] and example["split"] == row["split"]
        assert (
            canonical_hash(
                {k: v for k, v in example.items() if k not in {"example_id", "group_id", "split"}}
            )
            == example["example_id"]
        )
        assert [canonical_hash(t) for t in example["tools"]] == row["normalized_tool_hashes"]
        assert [tools[h]["tool"] for h in row["raw_tool_hashes"]] == example["tools"]
        raw_tools, _ = extract_tools(record)
        assert [canonical_hash(t) for t in raw_tools] == row["raw_tool_hashes"]
        mapping = {
            t["raw_name"]: t["normalized_name"] for t in (tools[h] for h in row["raw_tool_hashes"])
        }
        index = row["source_turn_index"]
        assert row["prefix_turn_end_exclusive"] == index
        action = record["conversations"][index]["value"]
        assert hashlib.sha256(action.encode()).hexdigest() == row["source_action_sha256"]
        parsed = parse_calls(action, list(mapping))
        expected = example["expected_action"]["tool_calls"]
        assert len(parsed) == len(expected) == len(row["call_bindings"])
        for before, after, binding in zip(parsed, expected, row["call_bindings"], strict=True):
            assert mapping[before["name"]] == after["name"] == binding["normalized_name"]
            assert (
                canonical_hash(before["arguments"])
                == canonical_hash(after["arguments"])
                == binding["arguments_hash"]
            )
            assert binding["arguments_filled_or_coerced"] is False
            target_calls += 1
        for message in example["messages"]:
            for call in message["tool_calls"]:
                _, raw_index, call_index = call["call_id"].split("-")
                assert int(raw_index) < index
                previous = parse_calls(
                    record["conversations"][int(raw_index)]["value"], list(mapping)
                )[int(call_index)]
                assert mapping[previous["name"]] == call["name"]
                assert canonical_hash(previous["arguments"]) == canonical_hash(call["arguments"])
                historical_calls += 1
        assert row["length"]["prefix_stable"] is True
        assert row["length"]["length_basis"] == "qwen3_non_thinking_concat_one_eos_v1"
    samples = rows(root / "human-review" / "samples.jsonl")
    sample_examples = [e for sample in samples for e in sample["normalized_examples"]]
    assert all(e == by_id[e["example_id"]] for e in sample_examples)
    assert len(samples) == len({s["source_record_hash"] for s in samples})
    review = read_json(root / "human-review" / "manifest.json")
    assert review["examples_artifact_sha256"] == file_hash(root / "examples.jsonl")
    assert review["sample_examples"] == len(sample_examples)
    assert review["accepted_examples_reviewed"] == 0 and review["mislabel_rate"] is None
    with (root / "human-review" / "review.csv").open() as stream:
        worksheet = list(csv.DictReader(stream))
    assert len(worksheet) == len(samples)
    assert all(
        not r["reviewer"] and not r["verdict"] and not r["reviewed_at_utc"] for r in worksheet
    )
    html = PacketHTML()
    html.feed((root / "human-review" / "index.html").read_text())
    assert html.csp and html.details == len(samples) and html.headings == len(samples) * 5
    return {
        "status": "WORKER_INTEGRITY_PASS_NOT_SEMANTIC_APPROVAL",
        "build_manifest_hash": canonical_hash(manifest),
        "verified_artifacts": len(manifest["artifacts"]),
        "verified_examples": len(examples),
        "target_calls_with_raw_arguments_unchanged": target_calls,
        "historical_calls_with_raw_arguments_unchanged": historical_calls,
        "verified_tool_lineage_objects": len(tools),
        "review_records": len(samples),
        "review_examples": len(sample_examples),
        "html_static_structure_and_no_external_content": "PASS",
        "browser_rendering": "NOT_VERIFIED_LOCAL_FILE_URL_BLOCKED",
        "human_review": "PENDING",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = verify(args.build, args.source)
    write_json(args.output, result)
    print(result)
