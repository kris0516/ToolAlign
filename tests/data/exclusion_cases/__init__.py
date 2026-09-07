"""Original bounded fixtures for the v3 exclusion and review-record joins."""

import copy
import json
from pathlib import Path

from adjudication_cases import revision_fixture as previous_revision
from adjudication_cases import source_fixture
from quality_cases import example, message

from toolalign.contracts import canonical_hash
from toolalign.data import quality_adjudication as a
from toolalign.data import quality_revision as q
from toolalign.data.common import encoded


def counts(rows, sources):
    failed = sum(sources.get(e["source_record_hash"], {}).get("source_training_fitness") == "fail" for e in rows)
    return {"original": len(rows), "quarantined_fail": failed, "quarantined_unknown": 0, "effective": len(rows) - failed}


def revision_fixture():
    parent = previous_revision()
    values = list(parent["index"]["examples"].values())
    b = values[3]
    later = example("retained-b", 3, history=b["messages"] + [
        message("assistant", calls=b["expected_action"]["tool_calls"]), message("tool", "1", call_id="c-1-0"),
        message("user", "Scale the next original input.")])
    # Put an unaffected source after an excluded target in the original hash
    # order so the fixture exercises a real v2-to-v3 rank change.
    other = next(e for i in range(100) if q.rank_key((e := example("retained-d-" + str(i)))["example_id"])
                 > max(q.rank_key(b["example_id"]), q.rank_key(later["example_id"])))
    values[4:4] = [later, other]
    assignments = list(parent["index"]["assignments"].values())
    assignments.append({"source_index": 4, **{k: other[k] for k in ("source_record_hash", "group_id", "split")}})
    lineage = list(parent["index"]["lineage"].values())
    for e, turn in ((later, 3), (other, 1)):
        lineage.append({**{k: e[k] for k in ("example_id", "source_record_hash", "group_id", "split")},
            "normalized_hash": e["example_id"], "source_turn_index": turn, "exclusion_reason": None})
    parent["index"] = q.original_index({s: [e for e in values if e["split"] == s] for s in q.SPLITS}, assignments, lineage)
    parent["original_bytes"] = {e["example_id"]: json.dumps(e, ensure_ascii=False).encode() + b"\n" for e in values}
    for split in q.SPLITS:
        original = sorted([e for e in values if e["split"] == split], key=lambda e: q.rank_key(e["example_id"]))
        parent["config"]["expected_counts"][split] = counts(original, parent["sources"])
        for profile in q.PROFILES:
            selected = [e for e in original if profile != "smoke" or e["source_record_hash"] != b["source_record_hash"]]
            sidecars = [{"selection_rank": i, "ranking_sha256": q.rank_key(e["example_id"])[0],
                "profile": profile, "split": split, "padding_bucket": 1024,
                "audit": {**{k: e[k] for k in q.IDENTITY}, "example_sha256": canonical_hash(e),
                          "total_tokens": 500 + i, "prompt_tokens": 400, "completion_tokens": 99 + i}}
                for i, e in enumerate(selected, 1)]
            parent["parents"][profile][split] = {"examples": selected, "sidecars": sidecars,
                "summary": {"input_count": len(original), "selected_count": len(selected)},
                "excluded": {"rank_limit": [e["example_id"] for e in original if e not in selected]}}
            prefix = profile + "/" + split
            parent["parent_lines"][prefix] = {e["example_id"]: parent["original_bytes"][e["example_id"]] for e in selected}
            parent["buffers"]["prior_revision/selection/" + prefix + ".examples.jsonl"] = a.lines_bytes(
                e for e in selected if e["source_record_hash"] not in parent["sources"])
            parent["config"]["expected_counts"][profile + "_" + split] = counts(selected, parent["sources"])
    parent["buffers"]["prior_revision/effective/identities.json"] = encoded({s: [e["example_id"] for e in values
        if e["split"] == s and e["source_record_hash"] not in parent["sources"]] for s in q.SPLITS})
    artifacts, manifest = a.stable_artifacts(parent)
    config = json.loads((Path(__file__).resolve().parents[3] / "configs/data-quality.v3.json").read_bytes())
    sources, decisions = copy.deepcopy(parent["sources"]), copy.deepcopy(parent["review_decisions"])
    row = {"source_record_hash": b["source_record_hash"], "group_id": b["group_id"], "split": "train",
        "disposition": "exclude_entire_source", "source_training_fitness": "fail", "example_ids": [b["example_id"], later["example_id"]],
        "issue_ids": ["ORIGINAL-V3-ISSUE"], "adjudication": {"original_fixture": "complete history failure"}}
    sources[row["source_record_hash"]] = row
    decisions.update({e["example_id"]: {"action_verdict": "pass", "prefix_training_fitness": fitness}
                      for e, fitness in ((b, "pass"), (later, "fail"))})
    config["expected_counts"] = {s: counts([e for e in values if e["split"] == s], sources) for s in q.SPLITS}
    for p in q.PROFILES:
        for s in q.SPLITS:
            config["expected_counts"][p + "_" + s] = counts(parent["parents"][p][s]["examples"], sources)
    config["disposition"].update(excluded_sources=2, excluded_decisions=5, restored_original_sources=1,
                                 source_training_fitness_counts={"fail": 2, "pass": 1})
    return {"parent": parent, "parent_artifacts": artifacts, "parent_manifest": manifest, "config": config,
        "sources": sources, "review_decisions": decisions, "delta": {"new_sources": [row]},
        "binding": {"original_selection_manifest_file_sha256": parent["config"]["input_bindings"]["parent_selection_manifest_file_sha256"],
                    "previous_selection_manifest_file_sha256": q.sha(artifacts["selection/manifest.json"])}}


def reviewed_fixture():
    index, row, packet, raw, _ = source_fixture()
    ids = row["example_ids"][:2]
    for key in ("examples", "lineage"):
        index[key] = {i: index[key][i] for i in ids}
    row.update(example_ids=ids, valid_decision_count=2, source_training_fitness="fail", binding=row["binding"][:2])
    packet["identity"].update(example_ids=ids, valid_decision_count=2)
    packet["valid_decisions"] = packet["valid_decisions"][:2]
    row["packet_sha256"] = q.sha(encoded(packet))
    row["adjudication"] = {"reviewer": "Codex-AI(Q1)", "file": "reviews/q1-v2/adjudications.json",
        "proposal_file": "reviews/q1-v2/next-version-proposals.json", "prior_local_action_verdicts_preserved": True}
    identity = {k: row[k] for k in ("source_record_hash", "group_id", "split", "packet_sha256", "source_training_fitness")}
    record = {**identity, "raw_turn_count": len(raw[0]["conversations"]), "all_valid_decision_count": 2,
        "recommended_next_version_disposition": "exclude_entire_source", "decisions": []}
    proposal = {**identity, "raw_turn_count": len(raw[0]["conversations"]), "recommended_disposition": "exclude_entire_source",
        "original_bytes_or_labels_to_mutate": False, "full_source_scope": True, "all_decisions": []}
    previous = {}
    for profile in q.PROFILES:
        for split in q.SPLITS:
            previous[f"selection/{profile}/{split}.sidecars.jsonl"] = a.lines_bytes(
                {"audit": {"example_id": ident}, "selection_rank": i, "parent_selection_rank": i + 2, "padding_bucket": 1024}
                for i, ident in enumerate(ids, 1) if profile == "formal" and split == "train")
    for ordinal, ident in enumerate(ids, 1):
        e, line = index["examples"][ident], index["lineage"][ident]
        fitness = "pass" if ordinal == 1 else "fail"
        record["decisions"].append({"example_id": ident, "source_turn_index": line["source_turn_index"],
            "normalized_prefix_sha256": canonical_hash(e["messages"]), "action_sha256": canonical_hash(e["expected_action"]),
            "action_verdict": "pass", "prefix_training_fitness": fitness, "future_turns_used_to_support_action": False,
            "calls": [{"call_id": c["call_id"], "normalized_name": c["name"], "arguments_sha256": canonical_hash(c["arguments"])}
                      for c in e["expected_action"]["tool_calls"]]})
        proposal["all_decisions"].append({"example_id": ident, "source_turn_index": line["source_turn_index"],
            "current_local_action_verdict": "pass", "current_prefix_training_fitness": fitness,
            "recommended_effective_presence_next_version": False, "current_selection_bindings": {"smoke": None,
                "formal": {"selection_rank": ordinal, "parent_selection_rank": ordinal + 2, "padding_bucket": 1024}}})
    buffers = {row["adjudication"]["file"]: encoded({"sources": [record]}),
               row["adjudication"]["proposal_file"]: encoded({"newly_reviewed_sources": [proposal]})}
    row["adjudication"].update(source_record_sha256=canonical_hash(record), proposal_record_sha256=canonical_hash(proposal))
    return row, packet, {"index": index}, previous, buffers
