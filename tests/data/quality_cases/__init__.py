"""Small original source families; no third-party samples or measured Qwen IDs."""

import copy
import json
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import encoded
from toolalign.data.quality_revision import (
    IDENTITY,
    argument_changes,
    normalized_id,
    original_index,
    rank_key,
)


def message(role, text="", calls=None, call_id=None):
    return {"role": role, "content": text, "tool_calls": calls or [], "tool_call_id": call_id}


def example(source, turn=1, split="train", history=None):
    tool = {"name": "fixture_scale", "description": "Scale an original number.",
            "parameters_json_schema": {"type": "object", "properties": {
                "value": {"type": "integer"}, "scale": {"type": "integer"}},
                "required": ["value"], "additionalProperties": False},
            "timeout_ms": 1000, "side_effect_class": "read_only",
            "tool_version": "original.v1", "schema_version": "toolalign.tool.v1"}
    value = {"schema_version": "toolalign.example.v1", "source": "toolalign-original-quality-fixtures",
             "source_revision": "original.v1", "license_id": "MIT", "source_record_hash": canonical_hash([source, "raw"]),
             "group_id": "original-common-group" if split == "train" else "original-validation-group",
             "split": split, "messages": history or [message("user", "Use multiplier three on this original input.")],
             "tools": [tool], "expected_action": {"kind": "tool_calls", "content": "", "tool_calls": [
                 {"call_id": f"c-{turn}-0", "name": "fixture_scale", "arguments": {"value": turn}}]},
             "category": "tool_calls"}
    value["example_id"] = normalized_id(value)
    return value


def inputs():
    a0 = example("flagged-a", 1)
    a1 = example("flagged-a", 3, history=a0["messages"] + [
        message("assistant", calls=a0["expected_action"]["tool_calls"]), message("tool", "1", call_id="c-1-0"),
        message("user", "Use multiplier three again.")])
    a2 = example("flagged-a", 5, history=a1["messages"] + [
        message("assistant", calls=a1["expected_action"]["tool_calls"]), message("tool", "3", call_id="c-3-0")])
    b, u, v = example("retained-b"), example("unknown-c"), example("validation", split="validation")
    values = [a0, a1, a2, b, u, v]
    assignments = [{"source_index": i, **{k: e[k] for k in ("source_record_hash", "group_id", "split")}}
                   for i, e in enumerate((a0, b, u, v))]
    lineage = [{**{k: e[k] for k in ("example_id", "source_record_hash", "group_id", "split")},
                "normalized_hash": e["example_id"], "source_turn_index": int(e["expected_action"]["tool_calls"][0]["call_id"].split("-")[1]),
                "exclusion_reason": None} for e in values]
    index = original_index({s: [e for e in values if e["split"] == s] for s in ("train", "validation")}, assignments, lineage)
    issues = {}
    for i, (sample, affected, verdict) in enumerate(((a0, a1, "fail"), (u, u, "unknown"))):
        members = [e["example_id"] for e in values if e["source_record_hash"] == sample["source_record_hash"]]
        issues[sample["source_record_hash"]] = {"source_index": 0 if i == 0 else 2,
            "source_record_hash": sample["source_record_hash"], "split": "train", "verdict": verdict,
            "all_sample_example_ids": members, "affected_target_example_ids": [affected["example_id"]],
            "affected_source_turns": [3 if i == 0 else 1], "origin": "semantic_100",
            "notes": "Original review fixture.", "selected_membership": {}}
    parents, parent_lines = {}, {}
    for profile in ("smoke", "formal"):
        parents[profile] = {}
        for split in ("train", "validation"):
            ordered = sorted([e for e in values if e["split"] == split], key=lambda e: rank_key(e["example_id"]))
            # At least one retained example was not selected originally in smoke.
            selected = ordered[:-1] if profile == "smoke" and split == "train" else ordered
            sidecars = [{"selection_rank": i, "ranking_sha256": rank_key(e["example_id"])[0],
                         "profile": profile, "split": split, "padding_bucket": 1024,
                         "audit": {**{k: e[k] for k in IDENTITY}, "example_sha256": canonical_hash(e),
                                   "total_tokens": 500 + i, "prompt_tokens": 400, "completion_tokens": 99 + i}}
                        for i, e in enumerate(selected, 1)]
            parents[profile][split] = {"examples": selected, "sidecars": sidecars,
                "summary": {"input_count": len(ordered), "selected_count": len(selected)},
                "excluded": {"rank_limit": [e["example_id"] for e in ordered[len(selected):]]}}
            parent_lines[profile + "/" + split] = {e["example_id"]: encoded(e) + b"\n" for e in selected}
            for source, issue in issues.items():
                issue["selected_membership"][profile + "/" + split] = [e["example_id"] for e in selected if e["source_record_hash"] == source]
    proposed = copy.deepcopy(a1["expected_action"])
    proposed["tool_calls"][0]["arguments"]["scale"] = 3
    draft = {"status": "DRAFT_NOT_APPLIED", "source_index": 0, "source_record_hash": a1["source_record_hash"],
             "original_example_id": a1["example_id"], "original_action_sha256": canonical_hash(a1["expected_action"]),
             "proposed_action": proposed, "reason": "Restore the original explicit multiplier."}
    argument_changes(a1["expected_action"], proposed)
    proof = {"source_record_hash": a1["source_record_hash"], "original_example_sha256": canonical_hash(a1),
             "original_tools_sha256": canonical_hash(a1["tools"]), "original_action_sha256": canonical_hash(a1["expected_action"]),
             "support_scope": "original_fixture_only"}
    config = json.loads((Path(__file__).resolve().parents[3] / "configs/data-quality.v1.json").read_text())
    config["expected_counts"] = {s: {"original": sum(e["split"] == s for e in values),
        "quarantined_fail": sum(e["split"] == s and e["source_record_hash"] == a0["source_record_hash"] for e in values),
        "quarantined_unknown": sum(e["split"] == s and e["source_record_hash"] == u["source_record_hash"] for e in values),
        "effective": sum(e["split"] == s and e["source_record_hash"] not in issues for e in values)} for s in ("train", "validation")}
    proposal = {"status": "PROPOSED_NOT_APPLIED", "review_kind": "delegated_ai_not_human",
                "no_final_test_based_training_changes": True, "issues": list(issues.values()), "quarantine_example_ids": {}}
    for p in parents:
        for s in parents[p]:
            selected = parents[p][s]["examples"]
            removed = {v: [e["example_id"] for e in selected if issues.get(e["source_record_hash"], {}).get("verdict") == v]
                       for v in ("fail", "unknown")}
            counts = {"original": len(selected), "effective": len(selected) - sum(map(len, removed.values()))}
            if s == "train":
                counts.update({"quarantined_" + k: len(v) for k, v in removed.items()})
            config["expected_counts"][p + "_" + s] = counts
            proposal["quarantine_example_ids"][p + "/" + s] = {"confirmed_fail": removed["fail"], "uncertain": removed["unknown"]}
    return {"config": config, "index": index, "issues": issues, "drafts": [draft], "source_evidence": {a1["example_id"]: proof},
            "parents": parents, "parent_lines": parent_lines, "parent_config": {"profiles": {p: {} for p in parents}},
            "original_bytes": {e["example_id"]: encoded(e) + b"\n" for e in values}, "proposal": proposal,
            "binding": {"parent_selection_input_binding": {}, "fixture_scope": "not_production_input_authorization"}}


def semantic_rows(source):
    return [{"source_index": str(a["source_index"]), "source_record_hash": a["source_record_hash"],
             "example_ids": ";".join(e["example_id"] for e in source["index"]["examples"].values() if e["source_record_hash"] == a["source_record_hash"]),
             "strata": "split:" + a["split"], "reviewer": "Codex-AI (delegated by kris; not human)",
             "verdict": source["issues"].get(a["source_record_hash"], {}).get("verdict", "pass"),
             "notes": "Original review fixture.", "reviewed_at_utc": "2026-09-07T00:00:00+00:00", "issue_categories": ""}
            for a in source["index"]["assignments"].values()]
