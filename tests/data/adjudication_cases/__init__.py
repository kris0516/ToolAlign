"""Original CPU fixtures for source dispositions; no third-party sample content."""

import copy
import json
from pathlib import Path

from quality_cases import example
from quality_cases import inputs as previous_fixture

from toolalign.contracts import canonical_hash
from toolalign.data import quality_adjudication as a
from toolalign.data import quality_revision as q
from toolalign.data.common import encoded


def source_fixture():
    """One three-decision source with a locally PASS target on either side."""
    old = previous_fixture()
    index = old["index"]
    values = list(index["examples"].values())[:3]
    raw = {"system": "Original fixture tool declarations.", "conversations": [
        {"from": "user" if i % 2 == 0 else "assistant", "value": "Original turn " + str(i)} for i in range(6)]}
    source = canonical_hash(raw)
    examples, lineage = {}, {}
    for original in values:
        e = copy.deepcopy(original)
        e["source_record_hash"] = source
        e["expected_action"]["tool_calls"][0]["arguments"]["value"] = 0
        e["example_id"] = q.normalized_id(e)
        line = {**copy.deepcopy(index["lineage"][original["example_id"]]), "example_id": e["example_id"],
                "source_record_hash": source, "normalized_hash": e["example_id"]}
        examples[e["example_id"]], lineage[e["example_id"]] = e, line
    ids = list(examples)
    assignment = {"source_index": 0, "source_record_hash": source, "group_id": values[0]["group_id"], "split": "train"}
    index = {"examples": examples, "lineage": lineage, "assignments": {0: assignment}}
    row = {"source_record_hash": source, "source_indices": [0], "group_id": assignment["group_id"],
        "split": "train", "example_ids": ids, "valid_decision_count": 3, "source_training_fitness": "unknown",
        "disposition": "exclude_entire_source", "issue_ids": ["ORIGINAL-ISSUE"], "original_bytes_mutated": False,
        "new_annotation_promoted": False, "binding": [], "adjudication": {"reviewer": "Codex-AI(E1)",
            "review_commit": "original-fixture-commit", "file": "reviews/e1/prior-judgments/prior-001.json",
            "original_quarantine_retained": True}}
    for ident in ids:
        e, line = examples[ident], lineage[ident]
        row["binding"].append({"example_id": ident, "example_canonical_sha256": canonical_hash(e),
            "lineage_canonical_sha256": canonical_hash(line), "expected_action_sha256": canonical_hash(e["expected_action"]),
            "messages_sha256": canonical_hash(e["messages"]), "source_turn_index": line["source_turn_index"]})
    packet = {"source": raw, "identity": {k: copy.deepcopy(row[k]) for k in (
        "source_record_hash", "source_indices", "group_id", "split", "example_ids", "valid_decision_count")},
        "valid_decisions": [{"example": copy.deepcopy(examples[i]), "lineage": copy.deepcopy(lineage[i])} for i in ids]}
    record = {**assignment, "source_verdict": "unknown", "reviewer": "Codex-AI(E1)",
              "complete_source_reviewed": True, "all_valid_decisions_reviewed": True, "decisions": []}
    for ordinal, ident in enumerate(ids):
        turn = lineage[ident]["source_turn_index"]
        record["decisions"].append({"example_id": ident, "turn": turn, "prefix_turn_end_exclusive": turn,
            "full_prefix_reviewed": True, "verdict": "unknown" if ordinal == 1 else "pass",
            "source_action_sha256": q.sha(raw["conversations"][turn]["value"].encode()),
            "calls": [{"call_index": 0, **copy.deepcopy(examples[ident]["expected_action"]["tool_calls"][0])}]})
    row["adjudication"]["source_record_sha256"] = canonical_hash(record)
    buffers = {row["adjudication"]["file"]: encoded(record), "reviews/e1/final-seal.json": encoded({"candidate": "original-fixture-commit"})}
    return index, row, packet, [raw], buffers


def revision_fixture():
    old = previous_fixture()
    config = json.loads((Path(__file__).resolve().parents[3] / "configs/data-quality.v2.json").read_bytes())
    old["config"] = config
    sources, decisions = {}, {}
    # Original source A: exclude every decision. Original C: restore original bytes.
    for ordinal, (source, issue) in enumerate(old["issues"].items()):
        verdict = "fail" if ordinal == 0 else "pass"
        sources[source] = {"source_record_hash": source, "group_id": old["index"]["assignments"][issue["source_index"]]["group_id"],
            "source_training_fitness": verdict, "disposition": "exclude_entire_source" if ordinal == 0 else "restore_original_source",
            "issue_ids": ["ORIGINAL-ISSUE-" + str(ordinal)], "adjudication": {"original_fixture_review": str(ordinal)}}
        for ident in issue["all_sample_example_ids"]:
            decisions[ident] = {"action_verdict": "pass", "original_fixture_local_action": True}
    old["sources"], old["review_decisions"] = sources, decisions
    old["original_bytes"] = {i: json.dumps(e, ensure_ascii=False).encode() + b"\n" for i, e in old["index"]["examples"].items()}
    buffers = {}
    prior_ids = {s: [i for i, e in old["index"]["examples"].items() if e["split"] == s and e["source_record_hash"] not in old["issues"]]
                 for s in q.SPLITS}
    buffers["prior_revision/effective/identities.json"] = encoded(prior_ids)
    buffers["prior_revision/staging/examples.jsonl"] = encoded(example("original-unchanged-stage")) + b"\n"
    expected = {}
    for split in q.SPLITS:
        rows = [e for e in old["index"]["examples"].values() if e["split"] == split]
        removed = sum(sources.get(e["source_record_hash"], {}).get("source_training_fitness") == "fail" for e in rows)
        expected[split] = {"original": len(rows), "quarantined_fail": removed, "quarantined_unknown": 0, "effective": len(rows) - removed}
        for profile in q.PROFILES:
            prefix = profile + "/" + split
            rows = old["parents"][profile][split]["examples"]
            removed = sum(sources.get(e["source_record_hash"], {}).get("source_training_fitness") == "fail" for e in rows)
            expected[profile + "_" + split] = {"original": len(rows), "quarantined_fail": removed, "quarantined_unknown": 0,
                                               "effective": len(rows) - removed}
            buffers["prior_revision/selection/" + prefix + ".examples.jsonl"] = a.lines_bytes(
                e for e in rows if e["source_record_hash"] not in old["issues"])
            old["parent_lines"][prefix] = {e["example_id"]: old["original_bytes"][e["example_id"]] for e in rows}
    config["expected_counts"] = expected
    config["disposition"].update(excluded_sources=1, excluded_decisions=3, restored_original_sources=1)
    old["binding"]["frozen_artifacts"] = {}
    old["buffers"] = buffers
    return old
