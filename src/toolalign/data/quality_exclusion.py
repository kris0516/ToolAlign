"""Apply the frozen v3 source exclusion while retaining the verified v2 history.

The parent producer validates its unchanged inputs and artifacts. This wrapper
adds one adopted source disposition, filters the original selection, and records
both the original and previous ranks. It never creates a semantic judgment.
"""

from __future__ import annotations

import argparse
import copy
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash

from . import quality_adjudication as a
from . import quality_revision as q
from .common import DataError, encoded, loads

CONFIG_SHA256 = "784aa699026ebb149d720745f461a9cfd493036cd0bf09a72702a81e2db45261"
VERSION = "toolalign.quality-exclusion.v3"


def load_config(path):
    return loads(q.pinned(path, CONFIG_SHA256).decode("utf-8"))


def fixed_bundle(input_root, config):
    root = Path(input_root)
    q.require(root.is_dir() and not root.is_symlink(), "input_root_identity")
    manifest = loads(q.pinned(root / "manifest.json", config["input_bindings"]["input_manifest_file_sha256"]).decode())
    q.require(manifest["schema"] == "toolalign.s0.quality-exclusion-inputs.v3" and manifest["owner"] == "S0"
              and manifest["training_authorized"] is False, "exclusion_input_scope")
    a.same(manifest["verified_code_base"], config["verified_code_base"], "exclusion_input_base")
    a.same(manifest["expected_counts"], config["expected_counts"], "exclusion_input_counts")
    members = manifest["files"]
    q.require(type(members) is dict and len(members) == 347, "exclusion_input_members")
    expected = {k for k, v in members.items() if v["kind"] != "immutable_existing_artifact"} | {"manifest.json"}
    q.require(not any(p.is_symlink() for p in root.rglob("*")), "input_symlink")
    a.same(sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()),
           sorted(expected), "exclusion_input_directory_members")
    buffers = {}
    for name, info in members.items():
        q.require(info["kind"] in {"exact_copy", "S0_derived_frozen_metadata", "immutable_existing_artifact"},
                  "exclusion_input_kind")
        path = Path(info["path"]) if info["kind"] == "immutable_existing_artifact" else q.child_path(root, name)
        q.require(path.is_file() and not path.is_symlink(), "exclusion_input_path")
        if info["kind"] == "immutable_existing_artifact":
            q.require(path.is_absolute(), "exclusion_immutable_absolute_path")
        data = q.pinned(path, info["sha256"])
        q.require(type(info["bytes"]) is int and len(data) == info["bytes"], "exclusion_input_size")
        # Parent final-split payloads are only hashed. The unchanged v2 loader
        # applies its own read policy to its original 217 inputs independently.
        if info["kind"] != "immutable_existing_artifact" or name.startswith("parent-revision/"):
            q.require(info.get("read_mode") != "hash_only_no_deserialization", "forbidden_input_deserialization")
            buffers[name] = data
    return manifest, buffers


def verify_q1_seals(buffers, delta):
    prefix = "reviews/q1-v2/"
    core, final = (a.document(buffers, prefix + name + ".json") for name in ("adjudication-seal", "final-evidence-seal"))
    for seal in (core, final):
        q.require(seal["training_authorized"] is False and seal["reviewer"] == "Codex-AI(Q1)"
                  and seal["model"] == "gpt-6-astra" and seal["thinking"] == "max", "q1_exclusion_reviewer")
    a.same(final["public_commit"], delta["review_commit"], "q1_exclusion_commit")
    a.same(core["candidate"], delta["parent_candidate"], "q1_exclusion_candidate")
    a.seal_member(final, "q1-v2-r3/adjudication-seal.json", buffers[prefix + "adjudication-seal.json"])
    for name in ("adjudications.json", "adoption-matrix.json", "next-version-proposals.json",
                 "review-event-proposals.json", "input/manifest.json", "material-validation.json",
                 "source-binding-validation.json", "review-summary.json"):
        for seal in (core, final):
            a.seal_member(seal, "q1-v2-r3/" + name, buffers[prefix + name])
    adjudications = a.document(buffers, prefix + "adjudications.json")
    proposals = a.document(buffers, prefix + "next-version-proposals.json")
    a.same(adjudications["candidate"], delta["parent_candidate"], "q1_adjudication_candidate")
    a.same(proposals["candidate"], delta["parent_candidate"], "q1_proposal_candidate")
    a.same(proposals["adjudications_sha256"], q.sha(buffers[prefix + "adjudications.json"]), "q1_proposal_adjudications")
    a.same(proposals["issue_events_sha256"], q.sha(buffers[prefix + "review-event-proposals.json"]), "q1_proposal_events")
    q.require(proposals["training_authorized"] is False and proposals["no_refill_or_resampling"] is True
              and proposals["no_staging_or_annotation_promotion"] is True, "q1_proposal_limits")


def selection_rows(artifacts):
    return {p: {s: {r["audit"]["example_id"]: r for r in q.jsonl(artifacts[f"selection/{p}/{s}.sidecars.jsonl"])[0]}
                for s in q.SPLITS} for p in q.PROFILES}


def verify_adoption(parent, artifacts, matrix):
    q.require(matrix["status"] == "PASS" and matrix["training_authorized"] is False, "parent_adoption_scope")
    rows = matrix["sources"]
    q.require(len(rows) == len(parent["sources"]) and {r["source_record_hash"] for r in rows} == set(parent["sources"]),
              "parent_adoption_source_set")
    present = {i for values in loads(artifacts["effective/identities.json"].decode()).values() for i in values}
    selected = selection_rows(artifacts)
    for row in rows:
        source = parent["sources"][row["source_record_hash"]]
        for key in ("group_id", "split", "issue_ids"):
            a.same(row[key], source[key], "parent_adoption_identity")
        for key in ("actual_disposition", "expected_disposition"):
            a.same(row[key], source["disposition"], "parent_adoption_disposition")
        a.same(row["historical_adjudication"], source["adjudication"], "parent_adoption_original_review")
        a.same(row["original_source_training_fitness"], source["source_training_fitness"], "parent_adoption_original_fitness")
        q.require(row["adoption_verdict"] == "PASS" and row["source_semantics_rereviewed"] is False, "parent_adoption_verdict")
        ids = source["example_ids"]
        checks = row["all_decision_checks"]
        q.require(len(checks) == len(ids) and {r["example_id"] for r in checks} == set(ids), "parent_adoption_all_decisions")
        for item in checks:
            ident = item["example_id"]
            example, line = parent["index"]["examples"][ident], parent["index"]["lineage"][ident]
            for key, value in (("original_example_sha256", example), ("original_lineage_sha256", line),
                               ("prefix_sha256", example["messages"]), ("action_sha256", example["expected_action"])):
                a.same(item[key], canonical_hash(value), "parent_adoption_decision_bytes")
            a.same(item["original_line_sha256"], q.sha(parent["original_bytes"][ident]), "parent_adoption_line_bytes")
            a.same(item["historical_action_review"], parent["review_decisions"][ident], "parent_adoption_local_review")
            a.same(item["source_turn_index"], line["source_turn_index"], "parent_adoption_turn")
            for key in ("effective_present", "expected_present"):
                a.same(item[key], ident in present, "parent_adoption_effective_presence")
            for profile in q.PROFILES:
                a.same(item["selection_checks"][profile]["actual_present"], ident in selected[profile][example["split"]],
                       "parent_adoption_selected_presence")


def reviewed_exclusion(row, packet, parent, previous_artifacts, buffers):
    reference = row["adjudication"]
    source = row["source_record_hash"]
    q.require(row["disposition"] == "exclude_entire_source" and row["source_training_fitness"] == "fail"
              and reference["reviewer"] == "Codex-AI(Q1)"
              and reference["prior_local_action_verdicts_preserved"] is True, "new_exclusion_scope")
    records = [r for r in a.document(buffers, reference["file"])["sources"] if r["source_record_hash"] == source]
    proposals = [r for r in a.document(buffers, reference["proposal_file"])["newly_reviewed_sources"] if r["source_record_hash"] == source]
    q.require(len(records) == len(proposals) == 1, "new_exclusion_review_record")
    record, proposal = records[0], proposals[0]
    a.same(canonical_hash(record), reference["source_record_sha256"], "new_exclusion_review_hash")
    a.same(canonical_hash(proposal), reference["proposal_record_sha256"], "new_exclusion_proposal_hash")
    for value in (record, proposal):
        for key in ("source_record_hash", "group_id", "split", "packet_sha256", "source_training_fitness"):
            a.same(value[key], row[key], "new_exclusion_review_identity")
        a.same(value["raw_turn_count"], len(packet["source"]["conversations"]), "new_exclusion_complete_history")
    a.same(record["recommended_next_version_disposition"], row["disposition"], "new_exclusion_recommendation")
    a.same(proposal["recommended_disposition"], row["disposition"], "new_exclusion_proposal_disposition")
    q.require(proposal["original_bytes_or_labels_to_mutate"] is False and proposal["full_source_scope"] is True,
              "new_exclusion_no_relabel")
    a.same(record["all_valid_decision_count"], len(row["example_ids"]), "new_exclusion_review_count")
    selected = selection_rows(previous_artifacts)
    proposal_decisions = {d["example_id"]: d for d in proposal["all_decisions"]}
    decisions = record["decisions"]
    q.require(len(decisions) == len(proposal["all_decisions"]) == len(row["example_ids"])
              and set(proposal_decisions) == {d["example_id"] for d in decisions} == set(row["example_ids"]),
              "new_exclusion_review_all_decisions")
    result = {}
    for decision in decisions:
        ident = decision["example_id"]
        example, line = parent["index"]["examples"][ident], parent["index"]["lineage"][ident]
        proposed = proposal_decisions[ident]
        a.same(decision["source_turn_index"], line["source_turn_index"], "new_exclusion_turn_type")
        a.same(proposed["source_turn_index"], line["source_turn_index"], "new_exclusion_proposal_turn")
        a.same(decision["normalized_prefix_sha256"], canonical_hash(example["messages"]), "new_exclusion_prefix")
        a.same(decision["action_sha256"], canonical_hash(example["expected_action"]), "new_exclusion_action")
        q.require(decision["action_verdict"] in {"pass", "fail", "unknown"}
                  and decision["prefix_training_fitness"] in {"pass", "fail", "unknown"}
                  and decision["future_turns_used_to_support_action"] is False, "new_exclusion_local_verdict")
        a.same(proposed["current_local_action_verdict"], decision["action_verdict"], "new_exclusion_local_verdict_preserved")
        a.same(proposed["current_prefix_training_fitness"], decision["prefix_training_fitness"], "new_exclusion_prefix_fitness_preserved")
        q.require(proposed["recommended_effective_presence_next_version"] is False, "new_exclusion_whole_source_presence")
        calls = example["expected_action"]["tool_calls"]
        q.require(len(decision["calls"]) == len(calls), "new_exclusion_call_count")
        for actual, expected in zip(decision["calls"], calls, strict=True):
            a.same({"call_id": actual["call_id"], "name": actual["normalized_name"], "arguments_sha256": actual["arguments_sha256"]},
                   {"call_id": expected["call_id"], "name": expected["name"], "arguments_sha256": canonical_hash(expected["arguments"])},
                   "new_exclusion_call_binding")
        for profile in q.PROFILES:
            sidecar = selected[profile][example["split"]].get(ident)
            expected = {k: sidecar[k] for k in ("selection_rank", "parent_selection_rank", "padding_bucket")} if sidecar else None
            a.same(proposed["current_selection_bindings"][profile], expected, "new_exclusion_previous_rank_binding")
        result[ident] = {"action_verdict": decision["action_verdict"], "prefix_training_fitness": decision["prefix_training_fitness"],
            "decision_record_sha256": canonical_hash(decision), "adopted_review_record_sha256": reference["source_record_sha256"]}
    return result


def verify_issue(row, buffers):
    ledger = a.document(buffers, "s0/review-failures.json")
    adoption = a.document(buffers, "s0/issue-adoption.json")
    finding = a.document(buffers, "reviews/q1-v2/review-event-proposals.json")["new_finding"]
    a.same(adoption["after_sha256"], q.sha(buffers["s0/review-failures.json"]), "new_issue_ledger_binding")
    q.require(ledger["whole_goal_paused"] is False and adoption["whole_goal_paused"] is False, "whole_goal_paused")
    a.same(row["issue_ids"], [adoption["new_issue_id"]], "new_issue_disposition_mapping")
    matches = [i for i in ledger["issues"] if i["issue_id"] == row["issue_ids"][0]]
    q.require(len(matches) == 1, "new_issue_identity")
    issue = matches[0]
    event = issue["events"][-1]
    q.require(issue["status"] == "CHANGES_REQUESTED" and type(issue["consecutive_failed_revisions"]) is int
              and issue["consecutive_failed_revisions"] == 1, "new_issue_status")
    a.same(event["event_record_sha256"], canonical_hash(finding), "new_issue_event_binding")
    for key in ("source_record_hash", "group_id", "split"):
        a.same(finding[key], row[key], "new_issue_source_binding")
    a.same(sorted(finding["affected_example_ids"]), sorted(row["example_ids"]), "new_issue_all_decisions")
    a.same(event["source_judgment_sha256"], row["adjudication"]["source_record_sha256"], "new_issue_judgment_binding")
    a.same(event["review_commit"], row["adjudication"]["review_commit"], "new_issue_review_commit")
    a.same(event["evidence_seal_sha256"], q.sha(buffers["reviews/q1-v2/final-evidence-seal.json"]), "new_issue_review_seal")
    a.same(event["s0_binding_sha256"], q.sha(buffers["s0/q1-receipt.json"]), "new_issue_s0_receipt")


def bound_inputs(*, config_path, input_root):
    a.cpu_only()
    config = load_config(config_path)
    manifest, buffers = fixed_bundle(input_root, config)
    pin_names = {"material_projection": "material-projection.json", "new_material_source_context": "new-material-sources/manifest.json",
        "parent_input_manifest": "parent-inputs/manifest.json", "parent_policy": "parent-policy.v2.json",
        "parent_revision_manifest": "parent-revision/manifest.json", "q1_adjudications": "reviews/q1-v2/adjudications.json",
        "q1_final_seal": "reviews/q1-v2/final-evidence-seal.json", "q1_proposals": "reviews/q1-v2/next-version-proposals.json",
        "review_failure_ledger": "s0/review-failures.json", "source_exclusion_delta": "source-exclusion-delta.json"}
    for key, name in pin_names.items():
        a.same(q.sha(buffers[name]), config["input_bindings"][key + "_file_sha256"], "exclusion_policy_input_binding")
    parent = a.bound_inputs(config_path=Path(input_root) / "parent-policy.v2.json", input_root=Path(input_root) / "parent-inputs")
    artifacts, parent_manifest = a.stable_artifacts(parent)
    for name, data in artifacts.items():
        q.require(buffers["parent-revision/" + name] == data, "verified_parent_artifact_bytes")
    parent_run = a.document(buffers, "parent-revision/run.json")
    a.same(parent_run["stable_manifest_sha256"], q.sha(artifacts["manifest.json"]), "verified_parent_run_manifest")
    a.same(parent_run["consumer"]["package_files"], a.consumer_identity()["package_files"], "verified_parent_run_source")
    q.require(parent_run["training_authorized"] is False and parent_run["model_modules_loaded"] == [], "verified_parent_run_scope")
    delta = a.document(buffers, "source-exclusion-delta.json")
    q.require(delta["schema"] == "toolalign.s0.quality-source-exclusion-delta.v3" and delta["owner"] == "S0"
              and delta["training_authorized"] is False and delta["data_changes_applied"] is False, "source_delta_scope")
    a.same(delta["parent_manifest_file_sha256"], q.sha(artifacts["manifest.json"]), "source_delta_parent_manifest")
    a.same(delta["parent_revision_sha256"], parent_manifest["quality_revision_sha256"], "source_delta_parent_revision")
    a.same(delta["parent_dispositions_file_sha256"], q.sha(parent["buffers"]["dispositions.json"]), "source_delta_parent_dispositions")
    a.same(delta["verified_code_base"], config["verified_code_base"], "source_delta_base")
    verify_q1_seals(buffers, delta)
    verify_adoption(parent, artifacts, a.document(buffers, "reviews/q1-v2/adoption-matrix.json"))
    sources, decisions = copy.deepcopy(parent["sources"]), copy.deepcopy(parent["review_decisions"])
    a.same(len(delta["new_sources"]), config["disposition"]["new_sources"], "source_delta_count")
    for row in delta["new_sources"]:
        source = row["source_record_hash"]
        q.require(source not in sources and row["packet"] == "packets/" + source + ".json", "new_source_duplicate_or_path")
        a.same(row["packet_sha256"], q.sha(buffers[row["packet"]]), "new_source_packet_hash")
        a.same(row["adjudication"]["review_commit"], delta["review_commit"], "new_source_review_commit")
        packet = a.document(buffers, row["packet"])
        a.source_members(parent["index"], row, packet, a.document(parent["buffers"], "parents/raw_source"))
        verify_issue(row, buffers)
        decisions.update(reviewed_exclusion(row, packet, parent, artifacts, buffers))
        sources[source] = row
    a.same(len(sources), config["disposition"]["fixed_sources"], "all_exclusion_source_count")
    a.same(dict(Counter(r["source_training_fitness"] for r in sources.values())),
           config["disposition"]["source_training_fitness_counts"], "all_exclusion_fitness_counts")
    binding = {"quality_config_file_sha256": CONFIG_SHA256, **config["input_bindings"],
        "parent_input_binding_sha256": canonical_hash(parent["binding"]),
        "parent_quality_revision_sha256": parent_manifest["quality_revision_sha256"],
        "original_selection_manifest_file_sha256": parent["config"]["input_bindings"]["parent_selection_manifest_file_sha256"],
        "previous_selection_manifest_file_sha256": q.sha(artifacts["selection/manifest.json"]),
        "frozen_artifacts": {k: {"sha256": v["sha256"], "bytes": v["bytes"], "read_mode": v.get("read_mode")}
                             for k, v in manifest["files"].items()},
        "new_full_corpus_tokenization_runs": 0, "final_split_semantic_reading": False}
    return {"config": config, "parent": parent, "parent_artifacts": artifacts, "parent_manifest": parent_manifest,
            "sources": sources, "review_decisions": decisions, "delta": delta, "binding": binding, "buffers": buffers}


def filtered_selection(inputs, revision_id):
    parent = inputs["parent"]
    for profiles in parent["parents"].values():
        for item in profiles.values():
            for example in item["examples"]:
                a.same(example, parent["index"]["examples"].get(example["example_id"]), "original_selected_example_type")
    excluded = {s: {"verdict": r["source_training_fitness"]} for s, r in inputs["sources"].items()
                if r["disposition"] == "exclude_entire_source"}
    selection = q.filter_selection(parent["index"], parent["parents"], excluded, revision_id,
                                   inputs["binding"]["original_selection_manifest_file_sha256"])
    previous = selection_rows(inputs["parent_artifacts"])
    for profile in q.PROFILES:
        for split in q.SPLITS:
            for sidecar in selection[profile][split]["sidecars"]:
                ident = sidecar["audit"]["example_id"]
                q.require(ident in previous[profile][split], "v3_cannot_refill_previous_selection")
                before = previous[profile][split][ident]
                a.same(sidecar["audit"], before["audit"], "previous_selected_audit_type")
                a.same(sidecar["parent_selection_rank"], before["parent_selection_rank"], "original_rank_preserved")
                q.require(type(before["selection_rank"]) is int and before["selection_rank"] > 0, "previous_rank_integer_type")
                sidecar.update(quality_config_file_sha256=CONFIG_SHA256, previous_selection_rank=before["selection_rank"],
                    previous_selection_sidecar_sha256=canonical_hash(before),
                    previous_selection_manifest_sha256=inputs["binding"]["previous_selection_manifest_file_sha256"],
                    restored_original_source=inputs["sources"].get(sidecar["audit"]["source_record_hash"], {}).get("disposition") == "restore_original_source")
    return selection


def stable_artifacts(inputs):
    parent, sources, config = inputs["parent"], inputs["sources"], inputs["config"]
    old, old_manifest = inputs["parent_artifacts"], inputs["parent_manifest"]
    a.same({s: sources.get(s) for s in parent["sources"]}, parent["sources"], "inherited_dispositions_unchanged")
    a.same({i: inputs["review_decisions"].get(i) for i in parent["review_decisions"]}, parent["review_decisions"], "inherited_local_reviews_unchanged")
    view = a.adjudicated_view(parent["index"], sources, parent["original_bytes"], inputs["review_decisions"])
    result = {"effective/" + s + ".jsonl": b"".join(parent["original_bytes"][i] for i in view["retained"][s]) for s in q.SPLITS}
    revision = {"version": VERSION, "quality_config_file_sha256": CONFIG_SHA256,
        "input_binding_sha256": canonical_hash(inputs["binding"]), "parent_quality_revision_sha256": old_manifest["quality_revision_sha256"],
        "source_dispositions_sha256": canonical_hash(sources), "effective_files": {k: q.sha(v) for k, v in result.items()},
        "restored_ids_sha256": canonical_hash(view["restored"])}
    revision_id = canonical_hash(revision)
    selection = filtered_selection(inputs, revision_id)
    counts, delta = {}, {}
    old_ids = loads(old["effective/identities.json"].decode())
    for split in q.SPLITS:
        removed = Counter(sources[parent["index"]["examples"][i]["source_record_hash"]]["source_training_fitness"]
                          for i in view["excluded"] if parent["index"]["examples"][i]["split"] == split)
        counts[split] = {"original": old_manifest["counts"][split]["original"], "quarantined_fail": removed["fail"],
                         "quarantined_unknown": removed["unknown"], "effective": len(view["retained"][split])}
        delta[split] = a.revision_delta(old_ids[split], view["retained"][split])
    for profile in q.PROFILES:
        for split in q.SPLITS:
            item = selection[profile][split]
            prefix = profile + "/" + split
            counts[profile + "_" + split] = {"original": item["summary"]["parent_selected_count"],
                "quarantined_fail": len(item["removed"]["fail"]), "quarantined_unknown": len(item["removed"]["unknown"]),
                "effective": len(item["examples"])}
            result["selection/" + prefix + ".examples.jsonl"] = b"".join(parent["parent_lines"][prefix][e["example_id"]] for e in item["examples"])
            result["selection/" + prefix + ".sidecars.jsonl"] = a.lines_bytes(item["sidecars"])
            result["selection/" + prefix + ".excluded.json"] = encoded({"source_training_fitness_exclusions": item["removed"],
                "parent_excluded_unchanged": item["parent_excluded"], "refill_count": 0}) + b"\n"
            previous = q.jsonl(old["selection/" + prefix + ".examples.jsonl"])[0]
            delta[prefix] = a.revision_delta([e["example_id"] for e in previous], [e["example_id"] for e in item["examples"]])
    a.same(counts, config["expected_counts"], "v3_effective_counts")
    q.require(all(not d["restored_original_ids"] for d in delta.values()), "v3_no_new_restoration_or_refill")
    a.same(view["restored"], loads(old["restored/identities.json"].decode()), "v2_restorations_preserved")
    for name, ids in (("effective", view["retained"]), ("excluded", view["excluded"]), ("restored", view["restored"])):
        result[name + "/identities.json"] = encoded(ids) + b"\n"
        members = {i for s in q.SPLITS for i in ids[s]} if name == "effective" else set(ids)
        result[name + "/lineage.jsonl"] = a.lines_bytes(parent["index"]["lineage"][i] for i in parent["index"]["examples"] if i in members)
        if name != "effective":
            result[name + "/examples.jsonl"] = b"".join(parent["original_bytes"][i] for i in parent["index"]["examples"] if i in members)
    result["dispositions/sources.jsonl"] = a.lines_bytes(sources.values())
    result["dispositions/examples.jsonl"] = a.lines_bytes(view["reasons"])
    result["delta-from-v2.json"] = encoded({"parent_manifest_file_sha256": q.sha(old["manifest.json"]), "sets": delta,
        "new_source_exclusions": [r["source_record_hash"] for r in inputs["delta"]["new_sources"]],
        "inherited_dispositions_preserved": True, "original_semantic_judgments_overwritten": False}) + b"\n"
    result["staging-reference.json"] = old["staging-reference.json"]
    selected = copy.deepcopy(loads(old["selection/manifest.json"].decode()))
    selected.update(manifest_version="toolalign.quality-excluded-selection.v3", quality_revision_sha256=revision_id,
        quality_config_file_sha256=CONFIG_SHA256, previous_selection_manifest_file_sha256=q.sha(old["selection/manifest.json"]),
        rank_semantics={"selection_rank": "continuous_v3", "parent_selection_rank": "original_v1", "previous_selection_rank": "verified_v2"},
        profiles={p: {s: {k: selection[p][s][k] for k in ("summary", "parent_summary")} for s in q.SPLITS} for p in q.PROFILES},
        artifacts={k.removeprefix("selection/"): {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in result.items() if k.startswith("selection/")})
    result["selection/manifest.json"] = encoded(selected) + b"\n"
    training = copy.deepcopy(loads(old["training-binding.json"].decode()))
    training.update(binding_version="toolalign.quality-excluded-training-binding.v3", quality_revision_sha256=revision_id,
        quality_config_file_sha256=CONFIG_SHA256, selection_manifest_file_sha256=q.sha(result["selection/manifest.json"]),
        effective_files=revision["effective_files"], previous_training_binding_file_sha256=q.sha(old["training-binding.json"]),
        parent_quality_manifest_file_sha256=q.sha(old["manifest.json"]), planning_deviation=config["planning_deviation"],
        status=config["status"], pending=config["pending"])
    result["training-binding.json"] = encoded(training) + b"\n"
    excluded_sources = {s for s, r in sources.items() if r["disposition"] == "exclude_entire_source"}
    q.require(len(excluded_sources) == config["disposition"]["excluded_sources"]
              and len(view["excluded"]) == config["disposition"]["excluded_decisions"], "v3_exclusion_denominator")
    groups = {sources[s]["group_id"] for s in excluded_sources}
    other = [e for e in parent["index"]["examples"].values() if e["group_id"] in groups and e["source_record_hash"] not in excluded_sources]
    manifest = copy.deepcopy(old_manifest)
    manifest.update(manifest_version=VERSION, status=config["status"], quality_revision=revision, quality_revision_sha256=revision_id,
        input_binding=inputs["binding"], counts=counts, source_training_fitness_counts=config["disposition"]["source_training_fitness_counts"],
        source_reference_roots={s: "parent-inputs/" if s in parent["sources"] else "" for s in sources},
        other_sources_retained_in_affected_groups=len({e["source_record_hash"] for e in other}),
        other_decisions_retained_in_affected_groups=len(other), planning_deviation=config["planning_deviation"], pending=config["pending"],
        artifacts={k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in result.items()})
    result["manifest.json"] = encoded(manifest) + b"\n"
    return result, manifest


def consumer_identity():
    identity = a.consumer_identity()
    name = "data/quality_exclusion.py"
    identity["package_files"][name] = q.sha(files("toolalign").joinpath(name).read_bytes())
    return identity


def build(*, output, **paths):
    a.cpu_only()
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    artifacts, manifest = stable_artifacts(bound_inputs(**paths))
    a.cpu_only()
    run = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "consumer": consumer_identity(),
        "input_paths": {k: str(Path(v).resolve()) for k, v in paths.items()}, "output_path": str(Path(output).resolve()),
        "stable_manifest_sha256": q.sha(artifacts["manifest.json"]), "model_modules_loaded": [], "training_authorized": False}
    q.publish(output, artifacts, run)
    return manifest


def verify(*, output, **paths):
    a.cpu_only()
    artifacts, manifest = stable_artifacts(bound_inputs(**paths))
    a.verify_artifacts(output, artifacts, consumer_identity())
    a.cpu_only()
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
