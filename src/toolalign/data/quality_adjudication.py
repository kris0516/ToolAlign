"""Apply the frozen S0 source dispositions to original data and selection bytes.

This CPU-only producer adopts recorded AI judgments; it does not generate a
semantic verdict. The previous revision, its quarantine and staging stay intact.
Every public entry point pins the policy and all 217 authorized input buffers.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash, contract_digest

from . import quality_revision as q
from .common import DataError, encoded, loads

CONFIG_SHA256 = "7cf53c23568cd06c9543f253d9636b4655b135f0e6daf0eb318ace2100807ccb"
SPLITS = q.SPLITS
PROFILES = q.PROFILES


def same(actual, expected, code):
    """JSON byte comparison preserves bool/int/float and nested value types."""
    q.require(encoded(actual) == encoded(expected), code)


def load_config(path):
    return loads(q.pinned(path, CONFIG_SHA256).decode("utf-8"))


def cpu_only():
    q.require(not q.MODEL_ROOTS & {n.split(".", 1)[0] for n in sys.modules}, "cpu_only_process_required")


def fixed_bundle(input_root, config):
    root = Path(input_root)
    q.require(root.is_dir() and not root.is_symlink(), "input_root_identity")
    raw_manifest = q.pinned(root / "manifest.json", config["input_bindings"]["input_manifest_file_sha256"])
    manifest = loads(raw_manifest.decode("utf-8"))
    q.require(manifest["schema"] == "toolalign.s0.quality-adjudication-inputs.v2"
              and manifest["owner"] == "S0" and manifest["training_authorized"] is False
              and manifest["verified_code_base"] == config["verified_code_base"], "input_manifest_scope")
    same(manifest["expected_counts"], config["expected_counts"], "input_manifest_counts")
    members = manifest["files"]
    q.require(type(members) is dict and len(members) == 217, "fixed_input_set")
    expected = {k for k, v in members.items() if v["kind"] != "immutable_existing_artifact"} | {"manifest.json"}
    q.require(not any(p.is_symlink() for p in root.rglob("*")), "input_symlink")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    q.require(actual == expected, "fixed_input_directory_members")
    # Other metadata and final-split files are hashed, never deserialized here.
    keep = {"parents/data_manifest", "parents/parent_selection_manifest", "parents/raw_source",
            "parents/representation_rows", "parent_data/train.jsonl", "parent_data/validation.jsonl",
            "parent_data/assignments.jsonl", "parent_data/lineage.jsonl",
            "prior_revision/manifest.json", "prior_revision/effective/identities.json",
            "prior_revision/staging/examples.jsonl"}
    buffers = {}
    for name, info in members.items():
        kind = info["kind"]
        q.require(kind in {"exact_copy", "immutable_existing_artifact", "S0_derived_frozen_dispositions"},
                  "input_artifact_kind")
        if kind == "immutable_existing_artifact":
            path = Path(info["path"])
            q.require(path.is_absolute() and path.is_file() and not path.is_symlink(), "immutable_input_path")
        else:
            # original_path in an exact-copy record is provenance, never a read target.
            path = q.child_path(root, name)
        data = q.pinned(path, info["sha256"])
        q.require(type(info["bytes"]) is int and len(data) == info["bytes"], "input_artifact_size")
        if kind != "immutable_existing_artifact" or name in keep or name.startswith("parent_selection/") or (
                name.startswith("prior_revision/selection/") and name.endswith(".examples.jsonl")):
            q.require(info.get("read_mode") != "hash_only_no_deserialization", "forbidden_input_deserialization")
            buffers[name] = data
    return manifest, buffers


def document(buffers, name):
    return loads(buffers[name].decode("utf-8"))


def seal_member(seal, name, data):
    """Verify a copied member; never follow a historical seal's mutable paths."""
    members = seal.get("files", seal.get("artifacts"))
    if type(members) is dict:
        candidates = [v for k, v in members.items() if k == name or k.endswith("/" + name)]
    else:
        candidates = [v for v in members if v["path"].endswith("/" + name)]
    q.require(len(candidates) == 1, "review_seal_member_identity")
    info = candidates[0]
    q.require(info["sha256"] == q.sha(data) and type(info["bytes"]) is int
              and info["bytes"] == len(data), "review_seal_member_bytes")


def verify_review_seals(buffers):
    original = document(buffers, "reviews/original/seal.json")
    q.require(original["status"] == "PASS", "original_review_seal_status")
    for name in buffers:
        if name.startswith("reviews/original/") and name.rsplit("/", 1)[1] in original["artifacts"]:
            seal_member(original, name.rsplit("/", 1)[1], buffers[name])
    for round_name in ("q1-r1", "q1-r2"):
        prefix = "reviews/" + round_name + "/"
        final = document(buffers, prefix + "final-evidence-seal.json")
        core = document(buffers, prefix + "adjudication-seal.json")
        adjudications = document(buffers, prefix + "adjudications.json")
        q.require(final["training_authorized"] is False and core["training_authorized"] is False
                  and adjudications["training_authorized"] is False
                  and adjudications["reviewer"] == "Codex-AI(Q1)"
                  and adjudications["model"] == "gpt-6-astra" and adjudications["thinking"] == "max",
                  "review_identity_or_authorization")
        same(adjudications["input_manifest_sha256"], q.sha(buffers[prefix + "input/manifest.json"]),
             "review_original_input_binding")
        same(final["input_manifest_sha256"], adjudications["input_manifest_sha256"], "final_review_input_binding")
        for name in ("adjudications.json", "review-event-proposals.json"):
            seal_member(core, round_name + "/" + name, buffers[prefix + name])
        for name in ("adjudication-seal.json", "adjudications.json", "input/manifest.json"):
            seal_member(final, round_name + "/" + name, buffers[prefix + name])
        if round_name == "q1-r1":
            seal_member(core, round_name + "/staging-adjudications.json", buffers[prefix + "staging-adjudications.json"])
        else:
            same(final["core_seal_sha256"], q.sha(buffers[prefix + "adjudication-seal.json"]), "review_core_seal_binding")
            seal_member(core, round_name + "/next-version-proposals.json", buffers[prefix + "next-version-proposals.json"])
    e1 = document(buffers, "reviews/e1/final-seal.json")
    q.require(e1["reviewer"] == "Codex-AI(E1)" and e1["training_authorized"] is False,
              "prior_review_identity")
    for name, data in buffers.items():
        if name.startswith("reviews/e1/prior-judgments/"):
            seal_member(e1, "judgments/" + name.rsplit("/", 1)[1], data)


def source_members(index, disposition, packet, raw_source):
    """Bind a complete original source and every valid decision, type faithfully."""
    source = disposition["source_record_hash"]
    q.require(disposition["split"] in SPLITS and disposition["original_bytes_mutated"] is False
              and disposition["new_annotation_promoted"] is False, "disposition_scope")
    fitness = disposition["source_training_fitness"]
    q.require(fitness in {"pass", "fail", "unknown"}, "source_training_fitness")
    expected = "restore_original_source" if fitness == "pass" else "exclude_entire_source"
    q.require(disposition["disposition"] == expected, "disposition_fitness_mismatch")
    indices = disposition["source_indices"]
    q.require(type(indices) is list and indices and all(type(i) is int and i >= 0 for i in indices)
              and len(indices) == len(set(indices)), "disposition_source_indices")
    actual_indices = [i for i, a in index["assignments"].items() if a["source_record_hash"] == source]
    same(sorted(indices), sorted(actual_indices), "disposition_all_source_indices")
    for i in indices:
        q.require(i < len(raw_source) and canonical_hash(raw_source[i]) == source, "raw_source_binding")
        same(packet["source"], raw_source[i], "packet_raw_source_binding")
        same({k: index["assignments"][i][k] for k in ("source_record_hash", "group_id", "split")},
             {k: disposition[k] for k in ("source_record_hash", "group_id", "split")}, "disposition_assignment")
    identity = packet["identity"]
    for key in ("source_record_hash", "source_indices", "group_id", "split", "valid_decision_count"):
        same(identity[key], disposition[key], "packet_disposition_identity")
    members = {i for i, e in index["examples"].items() if e["source_record_hash"] == source}
    ids = disposition["example_ids"]
    q.require(type(ids) is list and len(ids) == len(set(ids)) and set(ids) == members
              and type(disposition["valid_decision_count"]) is int
              and disposition["valid_decision_count"] == len(members) > 0, "disposition_all_decisions")
    same(sorted(identity["example_ids"]), sorted(ids), "packet_all_decisions")
    decisions = packet["valid_decisions"]
    q.require(len(decisions) == len(members) and {r["example"]["example_id"] for r in decisions} == members,
              "packet_decision_members")
    for row in decisions:
        ident = row["example"]["example_id"]
        same(row["example"], index["examples"][ident], "packet_example_type_or_identity")
        same(row["lineage"], index["lineage"][ident], "packet_lineage_type_or_identity")
    expected_bindings = []
    for ident in ids:
        e, line = index["examples"][ident], index["lineage"][ident]
        expected_bindings.append({"example_id": ident, "example_canonical_sha256": canonical_hash(e),
            "lineage_canonical_sha256": canonical_hash(line), "expected_action_sha256": canonical_hash(e["expected_action"]),
            "messages_sha256": canonical_hash(e["messages"]), "source_turn_index": line["source_turn_index"]})
    same(disposition["binding"], expected_bindings, "disposition_decision_binding")
    return members


def reviewed_source(disposition, buffers, index, packet):
    """Join adopted judgments without deriving source fitness from local Action grades."""
    reference = disposition["adjudication"]
    name = reference["file"]
    doc = document(buffers, name)
    source = disposition["source_record_hash"]
    if name.startswith("reviews/e1/prior-judgments/"):
        record = doc
        final = document(buffers, "reviews/e1/final-seal.json")
        same(reference["review_commit"], final["candidate"], "review_commit_binding")
        q.require(reference["original_quarantine_retained"] is True, "legacy_quarantine_preserved")
    else:
        candidates = [s for s in doc["sources"] if s["source_record_hash"] == source]
        q.require(len(candidates) == 1, "adopted_source_record")
        record = candidates[0]
        prefix = "reviews/q1-r2/" if name.endswith("next-version-proposals.json") else "reviews/q1-r1/"
        final = document(buffers, prefix + "final-evidence-seal.json")
        same(reference["review_commit"], final["commit"], "review_commit_binding")
    same(canonical_hash(record), reference["source_record_sha256"], "adopted_record_hash")
    if name.endswith("next-version-proposals.json"):
        proposal = record
        candidates = [s for s in document(buffers, "reviews/q1-r2/adjudications.json")["sources"]
                      if s["identity"]["source_record_hash"] == source]
        q.require(len(candidates) == 1, "q1_proposal_source")
        record = candidates[0]
        same(proposal["source_adjudication_sha256"], canonical_hash(record), "q1_proposal_adjudication_hash")
        for key in ("source_training_fitness", "disposition", "history_coverage"):
            same(proposal[key], record[key], "q1_proposal_adjudication_value")
        same(proposal["source_training_fitness"], disposition["source_training_fitness"], "adopted_training_fitness")
        for key in ("original_split", "proposed_split"):
            same(proposal[key], disposition["split"], "proposal_split_preserved")
        same(sorted(proposal["all_valid_example_ids"]), sorted(disposition["example_ids"]), "proposal_all_decisions")
        q.require(proposal["implemented"] is False and proposal["training_authorized"] is False
                  and proposal["original_bytes_mutated"] is False and record["mutations_applied"] is False,
                  "original_proposal_unmodified")
        same(record["identity"], packet["identity"], "q1_packet_identity")
        same(record["history_coverage"]["whole_source_turn_indices"], list(range(len(packet["source"]["conversations"]))),
             "q1_complete_source_history")
    else:
        for key in ("source_record_hash", "group_id", "split"):
            same(record[key], disposition[key], "adjudication_source_identity")
        same(record["source_verdict"], disposition["source_training_fitness"], "adopted_training_fitness")
        if name == "reviews/q1-r1/adjudications.json":
            q.require(record["data_changes_applied"] is False, "original_adjudication_unmodified")
            if disposition["disposition"] == "restore_original_source":
                q.require(record["recommendation"] == "restore_original_bytes_next_revision"
                          and record["original_bytes_semantically_supported"] is True, "restore_original_bytes_supported")
    q.require(record["reviewer"] == reference["reviewer"]
              and record["complete_source_reviewed"] is True
              and record["all_valid_decisions_reviewed"] is True, "complete_review_required")
    decisions = record["decisions"]
    q.require(len(decisions) == len(disposition["example_ids"])
              and {d["example_id"] for d in decisions} == set(disposition["example_ids"]), "review_all_decisions")
    by_id = {}
    for decision in decisions:
        ident = decision["example_id"]
        e, lineage = index["examples"][ident], index["lineage"][ident]
        turn = lineage["source_turn_index"]
        same(decision.get("source_turn_index", decision.get("turn")), turn, "review_decision_turn")
        same(decision["prefix_turn_end_exclusive"], turn, "review_prefix_boundary")
        q.require(decision["full_prefix_reviewed"] is True and decision["verdict"] in {"pass", "fail", "unknown"},
                  "review_decision_verdict")
        same(decision["source_action_sha256"], q.sha(packet["source"]["conversations"][turn]["value"].encode()),
             "review_raw_action_bytes")
        for key, value in (("example_sha256", e), ("lineage_sha256", lineage), ("action_sha256", e["expected_action"]),
                           ("expected_action_sha256", e["expected_action"]), ("prefix_sha256", e["messages"])):
            if key in decision:
                same(decision[key], canonical_hash(value), "review_decision_hash")
        for call in decision.get("calls", []):
            call_index = call["call_index"]
            q.require(type(call_index) is int and 0 <= call_index < len(e["expected_action"]["tool_calls"]),
                      "review_call_index")
            original = e["expected_action"]["tool_calls"][call_index]
            same({k: call[k] for k in ("call_id", "name", "arguments")}, original, "review_call_type_or_identity")
        by_id[ident] = {"action_verdict": decision["verdict"], "decision_record_sha256": canonical_hash(decision),
                        "adopted_review_record_sha256": reference["source_record_sha256"]}
    return by_id


def bound_inputs(*, config_path, input_root):
    config = load_config(config_path)
    manifest, buffers = fixed_bundle(input_root, config)
    pins = config["input_bindings"]
    pin_names = {"source_dispositions": "dispositions.json", "review_failure_ledger": "coordination/REVIEW_FAILURES.json",
        "prior_quality_policy": "parents/data-quality.v1.json", "prior_quality_manifest": "prior_revision/manifest.json",
        "parent_training_config": "parents/training-data.v1.json", "parent_selection_manifest": "parents/parent_selection_manifest",
        "q1_r1_adjudications": "reviews/q1-r1/adjudications.json", "q1_r2_adjudications": "reviews/q1-r2/adjudications.json",
        "q1_r2_proposals": "reviews/q1-r2/next-version-proposals.json"}
    for key, name in pin_names.items():
        same(q.sha(buffers[name]), pins[key + "_file_sha256"], "policy_input_binding")
    same(q.sha(buffers["parents/representation_rows"]), pins["parent_representation_rows_sha256"], "policy_audit_binding")
    examples, original_bytes = {}, {}
    for split in SPLITS:
        values, lines = q.jsonl(buffers["parent_data/" + split + ".jsonl"])
        examples[split] = values
        original_bytes.update({e["example_id"]: b for e, b in zip(values, lines, strict=True)})
    index = q.original_index(examples, q.jsonl(buffers["parent_data/assignments.jsonl"])[0],
                             q.jsonl(buffers["parent_data/lineage.jsonl"])[0])
    data_manifest = document(buffers, "parents/data_manifest")
    selection_manifest = document(buffers, "parents/parent_selection_manifest")
    parent_config = q.validate_parent_config(document(buffers, "parents/training-data.v1.json"))
    q.require(selection_manifest["manifest_version"] == "toolalign.training-selection.v1"
              and selection_manifest["training_authorized"] is False, "original_selection_kind")
    same(selection_manifest["config"], parent_config, "parent_training_configuration")
    same(selection_manifest["input_binding"]["data_manifest_sha256"], canonical_hash(data_manifest), "parent_data_identity")
    same(selection_manifest["input_binding"]["data_artifacts"], data_manifest["artifacts"], "parent_data_artifacts")
    for prefix, artifact_manifest in (("parent_data/", data_manifest), ("parent_selection/", selection_manifest),
                                     ("prior_revision/", document(buffers, "prior_revision/manifest.json"))):
        for name, info in artifact_manifest["artifacts"].items():
            actual = manifest["files"][prefix + name]
            same(actual["sha256"], info["sha256"] if type(info) is dict else info, "parent_artifact_binding")
    measured = {}
    for row in q.jsonl(buffers["parents/representation_rows"])[0]:
        if row["split"] not in SPLITS:
            continue
        ident = row["example_id"]
        q.require(ident in index["examples"] and ident not in measured, "audit_example_set")
        same(row["example_sha256"], canonical_hash(index["examples"][ident]), "audit_example_binding")
        measured[ident] = row
    q.require(set(measured) == set(index["examples"]), "audit_all_originals")
    parents, parent_lines = {}, {}
    for profile in PROFILES:
        parents[profile] = {}
        for split in SPLITS:
            prefix = profile + "/" + split
            values, lines = q.jsonl(buffers["parent_selection/" + prefix + ".examples.jsonl"])
            sidecars = q.jsonl(buffers["parent_selection/" + prefix + ".sidecars.jsonl"])[0]
            q.require(len(values) == len(sidecars), "parent_sidecar_count")
            for e, line, sidecar in zip(values, lines, sidecars, strict=True):
                ident = e["example_id"]
                same(e, index["examples"][ident], "parent_example_type_or_identity")
                q.require(original_bytes[ident] == line, "parent_original_line_bytes")
                same(sidecar["audit"], measured[ident], "parent_original_audit")
            parents[profile][split] = {"examples": values, "sidecars": sidecars,
                "excluded": document(buffers, "parent_selection/" + prefix + ".excluded.json"),
                "summary": selection_manifest["profiles"][profile][split]}
            parent_lines[prefix] = {e["example_id"]: line for e, line in zip(values, lines, strict=True)}
    verify_review_seals(buffers)
    dispositions = document(buffers, "dispositions.json")
    q.require(dispositions["schema"] == "toolalign.s0.quality-source-dispositions.v2"
              and dispositions["owner"] == "S0" and dispositions["training_authorized"] is False,
              "source_disposition_document")
    rows = dispositions["sources"]
    q.require(len(rows) == config["disposition"]["fixed_sources"], "fixed_source_count")
    raw_source = document(buffers, "parents/raw_source")
    ledger, adoption = document(buffers, "coordination/REVIEW_FAILURES.json"), document(buffers, "coordination/issue-adoption.json")
    same(adoption["ledger_after_sha256"], q.sha(buffers["coordination/REVIEW_FAILURES.json"]), "adopted_issue_ledger")
    q.require(ledger["whole_goal_paused"] is False, "whole_goal_paused")
    issue_index = {r["issue_id"]: r for r in ledger["issues"]}
    sources, decisions = {}, {}
    for row in rows:
        source = row["source_record_hash"]
        q.require(source not in sources and row["packet"] == "packets/" + source + ".json", "source_or_packet_duplicate")
        same(row["packet_sha256"], q.sha(buffers[row["packet"]]), "source_packet_file_hash")
        packet = document(buffers, row["packet"])
        source_members(index, row, packet, raw_source)
        same(row["issue_ids"], adoption["source_to_issues"][source], "adopted_issue_mapping")
        q.require(row["issue_ids"] and all(i in issue_index for i in row["issue_ids"]), "adopted_issue_identity")
        if row["disposition"] == "restore_original_source":
            q.require(all(issue_index[i]["status"] == "CLOSED_ADJUDICATED_PASS" for i in row["issue_ids"]),
                      "restoration_adjudicated_pass")
        decisions.update(reviewed_source(row, buffers, index, packet))
        sources[source] = row
    same(dict(Counter(r["source_training_fitness"] for r in rows)),
         config["disposition"]["source_training_fitness_counts"], "fixed_fitness_counts")
    q.require(len(decisions) == sum(r["valid_decision_count"] for r in rows) == 101, "fixed_decision_count")
    binding = {"quality_config_file_sha256": CONFIG_SHA256, **pins,
        "frozen_artifacts": {k: {"sha256": v["sha256"], "bytes": v["bytes"], "read_mode": v.get("read_mode")}
                             for k, v in manifest["files"].items()},
        "parent_selection_input_binding": selection_manifest["input_binding"],
        "new_full_corpus_tokenization_runs": 0, "final_split_semantic_reading": False,
        "review_seal_members_verified_from_frozen_copies": True}
    return {"config": config, "index": index, "original_bytes": original_bytes, "parents": parents,
        "parent_lines": parent_lines, "parent_config": parent_config, "sources": sources,
        "review_decisions": decisions, "binding": binding, "buffers": buffers}


def adjudicated_view(index, sources, original_bytes, review_decisions):
    retained, excluded, restored, reasons = {s: [] for s in SPLITS}, [], [], []
    for ident, example in index["examples"].items():
        source = sources.get(example["source_record_hash"])
        decision = review_decisions.get(ident)
        disposition = source["disposition"] if source else "retain_original_source_without_new_adjudication"
        if disposition == "exclude_entire_source":
            excluded.append(ident)
        else:
            retained[example["split"]].append(ident)
            if disposition == "restore_original_source":
                restored.append(ident)
        reasons.append({**{k: example[k] for k in q.IDENTITY},
            "source_turn_index": index["lineage"][ident]["source_turn_index"],
            "original_example_sha256": canonical_hash(example), "original_jsonl_line_sha256": q.sha(original_bytes[ident]),
            "original_lineage_sha256": canonical_hash(index["lineage"][ident]), "disposition": disposition,
            "source_training_fitness": source["source_training_fitness"] if source else None,
            "source_disposition_sha256": canonical_hash(source) if source else None,
            "issue_ids": source["issue_ids"] if source else [], "review": source["adjudication"] if source else None,
            "local_action_review": decision, "new_annotation": False,
            "reason": "entire_source_training_fitness" if source else "unaffected_original_source"})
    return {"retained": retained, "excluded": excluded, "restored": restored, "reasons": reasons}


def stable_artifacts(inputs):
    config, index, sources = inputs["config"], inputs["index"], inputs["sources"]
    view = adjudicated_view(index, sources, inputs["original_bytes"], inputs["review_decisions"])
    excluded = {s: {"verdict": r["source_training_fitness"]} for s, r in sources.items()
                if r["disposition"] == "exclude_entire_source"}
    result = {"effective/" + s + ".jsonl": b"".join(inputs["original_bytes"][i] for i in view["retained"][s]) for s in SPLITS}
    revision = {"version": "toolalign.quality-adjudication.v2", "quality_config_file_sha256": CONFIG_SHA256,
        "input_binding_sha256": canonical_hash(inputs["binding"]), "source_dispositions_sha256": canonical_hash(sources),
        "effective_files": {k: q.sha(v) for k, v in result.items()}, "restored_ids_sha256": canonical_hash(view["restored"])}
    revision_id = canonical_hash(revision)
    # Repeat the cheap type-faithful join for direct pure-kernel callers as well.
    for profile in inputs["parents"].values():
        for parent in profile.values():
            for e in parent["examples"]:
                same(e, index["examples"].get(e["example_id"]), "selected_example_type_or_identity")
    selection = q.filter_selection(index, inputs["parents"], excluded, revision_id,
                                   config["input_bindings"]["parent_selection_manifest_file_sha256"])
    counts, delta = {}, {}
    old_ids = document(inputs["buffers"], "prior_revision/effective/identities.json")
    for split in SPLITS:
        removed = Counter(sources[index["examples"][i]["source_record_hash"]]["source_training_fitness"]
                          for i in view["excluded"] if index["examples"][i]["split"] == split)
        counts[split] = {"original": sum(e["split"] == split for e in index["examples"].values()),
            "quarantined_fail": removed["fail"], "quarantined_unknown": removed["unknown"], "effective": len(view["retained"][split])}
        delta[split] = revision_delta(old_ids[split], view["retained"][split])
    for profile in PROFILES:
        for split in SPLITS:
            item = selection[profile][split]
            prefix = profile + "/" + split
            counts[profile + "_" + split] = {"original": item["summary"]["parent_selected_count"],
                "quarantined_fail": len(item["removed"]["fail"]), "quarantined_unknown": len(item["removed"]["unknown"]),
                "effective": len(item["examples"])}
            for sidecar in item["sidecars"]:
                ident = sidecar["audit"]["example_id"]
                sidecar.update(quality_config_file_sha256=CONFIG_SHA256, restored_original_source=ident in view["restored"])
            result["selection/" + prefix + ".examples.jsonl"] = b"".join(inputs["parent_lines"][prefix][e["example_id"]]
                                                                          for e in item["examples"])
            result["selection/" + prefix + ".sidecars.jsonl"] = lines_bytes(item["sidecars"])
            result["selection/" + prefix + ".excluded.json"] = encoded({"source_training_fitness_exclusions": item["removed"],
                "parent_excluded_unchanged": item["parent_excluded"], "refill_count": 0}) + b"\n"
            previous = q.jsonl(inputs["buffers"]["prior_revision/selection/" + prefix + ".examples.jsonl"])[0]
            delta[prefix] = revision_delta([e["example_id"] for e in previous], [e["example_id"] for e in item["examples"]])
    same(counts, config["expected_counts"], "fixed_adjudication_counts")
    staged = q.jsonl(inputs["buffers"]["prior_revision/staging/examples.jsonl"])[0]
    q.require(not {e["example_id"] for e in staged} & set(index["examples"]), "staging_overlaps_originals")
    q.require(len(view["excluded"]) == config["disposition"]["excluded_decisions"]
              and len(excluded) == config["disposition"]["excluded_sources"], "whole_source_exclusion_count")
    q.require(sum(r["disposition"] == "restore_original_source" for r in sources.values())
              == config["disposition"]["restored_original_sources"], "restored_source_count")
    result["effective/identities.json"] = encoded(view["retained"]) + b"\n"
    result["excluded/identities.json"] = encoded(view["excluded"]) + b"\n"
    result["restored/identities.json"] = encoded(view["restored"]) + b"\n"
    result["dispositions/sources.jsonl"] = lines_bytes(sources.values())
    result["dispositions/examples.jsonl"] = lines_bytes(view["reasons"])
    for name, ids in (("effective", set(i for s in SPLITS for i in view["retained"][s])),
                      ("excluded", set(view["excluded"])), ("restored", set(view["restored"]))):
        result[name + "/lineage.jsonl"] = lines_bytes(index["lineage"][i] for i in index["examples"] if i in ids)
        if name != "effective":
            result[name + "/examples.jsonl"] = b"".join(inputs["original_bytes"][i] for i in index["examples"] if i in ids)
    result["delta-from-v1.json"] = encoded({"prior_manifest_file_sha256": config["input_bindings"]["prior_quality_manifest_file_sha256"],
        "sets": delta, "original_quarantine_preserved": True, "original_semantic_judgments_overwritten": False}) + b"\n"
    result["staging-reference.json"] = encoded({"status": "STAGING_NOT_PROMOTED", "new_annotations": 0,
        "enters_effective_training": False, "new_tokenization_runs": 0,
        "frozen_references": {k: v for k, v in inputs["binding"]["frozen_artifacts"].items()
            if k.startswith("prior_revision/staging/") or k in {"reviews/q1-r1/staging-adjudications.json",
                "reviews/original/reannotation_drafts.json", "reviews/original/token_judgments.json",
                "reviews/s0/prior-revision-binding.json", "reviews/e1/material-review/final-seal.json"}}}) + b"\n"
    selected_manifest = {"manifest_version": "toolalign.quality-adjudicated-selection.v2", "training_authorized": False,
        "quality_revision_sha256": revision_id, "quality_config_file_sha256": CONFIG_SHA256,
        "parent_training_config": inputs["parent_config"],
        "parent_selection_manifest_file_sha256": config["input_bindings"]["parent_selection_manifest_file_sha256"],
        "inherited_input_binding": inputs["binding"]["parent_selection_input_binding"],
        "profiles": {p: {s: {k: selection[p][s][k] for k in ("summary", "parent_summary")} for s in SPLITS} for p in PROFILES},
        "artifacts": {k.removeprefix("selection/"): {"sha256": q.sha(v), "size_bytes": len(v)}
                      for k, v in result.items() if k.startswith("selection/")}}
    result["selection/manifest.json"] = encoded(selected_manifest) + b"\n"
    result["training-binding.json"] = encoded({"binding_version": "toolalign.quality-adjudicated-training-binding.v2",
        "quality_revision_sha256": revision_id, "quality_config_file_sha256": CONFIG_SHA256,
        "selection_manifest_file_sha256": q.sha(result["selection/manifest.json"]), "effective_files": revision["effective_files"],
        "parent_training_config_file_sha256": config["input_bindings"]["parent_training_config_file_sha256"],
        "inherited_representation": inputs["binding"]["parent_selection_input_binding"], "profiles": inputs["parent_config"]["profiles"],
        "planning_deviation": config["planning_deviation"], "trainer_consumption": "NOT_RUN_PENDING_SEPARATE_ADAPTATION",
        "status": config["status"], "training_authorized": False, "new_annotations_enter_training": False,
        "pending": config["pending"]}) + b"\n"
    affected_groups = {r["group_id"] for r in sources.values() if r["disposition"] == "exclude_entire_source"}
    manifest = {"manifest_version": "toolalign.quality-adjudication.v2", "status": config["status"], "training_authorized": False,
        "quality_revision": revision, "quality_revision_sha256": revision_id, "input_binding": inputs["binding"], "counts": counts,
        "source_training_fitness_counts": config["disposition"]["source_training_fitness_counts"],
        "restored_original_sources": sum(r["disposition"] == "restore_original_source" for r in sources.values()),
        "restored_original_decisions": len(view["restored"]),
        "other_sources_retained_in_affected_groups": sum(e["group_id"] in affected_groups and e["source_record_hash"] not in excluded
                                                         for e in index["examples"].values()),
        "annotations": {"new_annotations": 0, "promoted": 0, "existing_staging_preserved": True},
        "planning_deviation": config["planning_deviation"], "pending": config["pending"],
        "artifacts": {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in result.items()}}
    result["manifest.json"] = encoded(manifest) + b"\n"
    return result, manifest


def lines_bytes(rows):
    return b"".join(encoded(row) + b"\n" for row in rows)


def revision_delta(previous, current):
    q.require(len(previous) == len(set(previous)) and len(current) == len(set(current)), "revision_duplicate_ids")
    before, after = set(previous), set(current)
    return {"previous": len(previous), "current": len(current), "retained": len(before & after),
            "removed_original_ids": [i for i in previous if i not in after],
            "restored_original_ids": [i for i in current if i not in before]}


def consumer_identity():
    identity = q.consumer_identity()
    name = "data/quality_adjudication.py"
    identity["package_files"][name] = q.sha(files("toolalign").joinpath(name).read_bytes())
    return identity


def verify_artifacts(output, artifacts, consumer=None):
    root = Path(output)
    q.require(root.is_dir() and not root.is_symlink() and ".toolalign-local" in root.resolve().parts,
              "private_output_required")
    q.require(not any(p.is_symlink() for p in root.rglob("*")), "output_symlink")
    same(sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()),
         sorted(set(artifacts) | {"run.json"}), "output_artifact_set")
    for name, data in artifacts.items():
        q.pinned(q.child_path(root, name), q.sha(data))
    run = loads((root / "run.json").read_text(encoding="utf-8"))
    same(run["stable_manifest_sha256"], q.sha(artifacts["manifest.json"]), "output_manifest_binding")
    identity = consumer or consumer_identity()
    same(run["consumer"]["package_files"], identity["package_files"], "output_consumer_binding")
    same(run["consumer"]["contract_sha256"], contract_digest(), "output_contract_binding")
    q.require(run["training_authorized"] is False and run["model_modules_loaded"] == [], "output_authorization_binding")
    return run


def build(*, output, **paths):
    cpu_only()
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    inputs = bound_inputs(**paths)
    artifacts, manifest = stable_artifacts(inputs)
    cpu_only()
    run = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "consumer": consumer_identity(),
        "input_paths": {k: str(Path(v).resolve()) for k, v in paths.items()}, "output_path": str(Path(output).resolve()),
        "stable_manifest_sha256": q.sha(artifacts["manifest.json"]), "model_modules_loaded": [], "training_authorized": False}
    q.publish(output, artifacts, run)
    return manifest


def verify(*, output, **paths):
    cpu_only()
    artifacts, manifest = stable_artifacts(bound_inputs(**paths))
    verify_artifacts(output, artifacts)
    cpu_only()
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        command = sub.add_parser(name)
        for flag in ("config-path", "input-root", "output"):
            command.add_argument("--" + flag, required=True, type=Path)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        manifest = {"build": build, "verify": verify}[command](**args)
    except (DataError, ContractError, OSError, KeyError, TypeError, ValueError, IndexError) as exc:
        print(encoded({"status": "FAIL", "error_type": type(exc).__name__,
                       "error_code": str(exc) if type(exc) is DataError else "invalid_input_or_io"}).decode())
        return 1
    print(encoded({"status": "PASS_STRUCTURAL_" + command.upper(), "counts": manifest["counts"],
                   "quality_revision_sha256": manifest["quality_revision_sha256"], "training_authorized": False}).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
