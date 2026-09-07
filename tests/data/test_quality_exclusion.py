"""V3 removes a whole source and preserves both earlier selection generations."""

import copy
import json
from pathlib import Path

import pytest
from exclusion_cases import reviewed_fixture, revision_fixture

from toolalign.contracts import canonical_hash
from toolalign.data import quality_adjudication as a
from toolalign.data import quality_exclusion as x
from toolalign.data import quality_revision as q
from toolalign.data.common import DataError, encoded


def test_source_exclusion_keeps_original_bytes_both_ranks_restorations_and_same_group():
    inputs = revision_fixture()
    before = copy.deepcopy(inputs)
    artifacts, manifest = x.stable_artifacts(inputs)
    assert artifacts == x.stable_artifacts(inputs)[0]
    assert inputs == before
    assert manifest["counts"]["train"] == {"original": 7, "quarantined_fail": 5, "quarantined_unknown": 0, "effective": 2}
    delta = json.loads(artifacts["delta-from-v2.json"])["sets"]
    new_ids = inputs["delta"]["new_sources"][0]["example_ids"]
    assert set(delta["train"]["removed_original_ids"]) == set(new_ids)
    assert all(not d["restored_original_ids"] for d in delta.values())
    assert delta["smoke/train"]["removed_original_ids"] == []
    assert delta["formal/train"]["current"] == delta["formal/train"]["previous"] - 2
    assert artifacts["staging-reference.json"] == inputs["parent_artifacts"]["staging-reference.json"]
    assert artifacts["restored/identities.json"] == inputs["parent_artifacts"]["restored/identities.json"]
    reasons = q.jsonl(artifacts["dispositions/examples.jsonl"])[0]
    local = [r for r in reasons if r["example_id"] in new_ids]
    assert len(local) == 2 and {r["local_action_review"]["action_verdict"] for r in local} == {"pass"}
    assert {r["local_action_review"]["prefix_training_fitness"] for r in local} == {"pass", "fail"}
    assert all(r["source_training_fitness"] == "fail" for r in local)
    assert manifest["other_sources_retained_in_affected_groups"] == 2
    previous = x.selection_rows(inputs["parent_artifacts"])
    ranks_changed = []
    for profile in q.PROFILES:
        for split in q.SPLITS:
            prefix = f"selection/{profile}/{split}"
            rows, lines = q.jsonl(artifacts[prefix + ".examples.jsonl"])
            sidecars = q.jsonl(artifacts[prefix + ".sidecars.jsonl"])[0]
            assert [r["selection_rank"] for r in sidecars] == list(range(1, len(rows) + 1))
            for e, line, sidecar in zip(rows, lines, sidecars, strict=True):
                ident = e["example_id"]
                old = previous[profile][split][ident]
                assert line == inputs["parent"]["original_bytes"][ident]
                assert sidecar["parent_selection_rank"] == old["parent_selection_rank"]
                assert sidecar["previous_selection_rank"] == old["selection_rank"]
                assert sidecar["previous_selection_sidecar_sha256"] == canonical_hash(old)
                ranks_changed.append(sidecar["selection_rank"] != sidecar["previous_selection_rank"])
    assert any(ranks_changed)
    binding = json.loads(artifacts["training-binding.json"])
    assert binding["training_authorized"] is False
    assert binding["trainer_consumption"] == "NOT_RUN_PENDING_SEPARATE_ADAPTATION"


@pytest.mark.parametrize("mutation", ["inherited_disposition", "old_local_verdict", "parent_rank", "previous_rank_type", "refill"])
def test_previous_history_or_selection_substitutions_reject(mutation):
    inputs = revision_fixture()
    if mutation == "inherited_disposition":
        next(iter(inputs["sources"].values()))["source_training_fitness"] = "unknown"
    elif mutation == "old_local_verdict":
        next(iter(inputs["review_decisions"].values()))["action_verdict"] = "fail"
    else:
        name = "selection/formal/train.sidecars.jsonl"
        rows = q.jsonl(inputs["parent_artifacts"][name])[0]
        kept = {r["example_id"] for r in q.jsonl(x.stable_artifacts(inputs)[0]["selection/formal/train.examples.jsonl"])[0]}
        row = next(r for r in rows if r["audit"]["example_id"] in kept)
        if mutation == "parent_rank":
            row["parent_selection_rank"] += 1
        elif mutation == "previous_rank_type":
            row["selection_rank"] = True
        else:
            rows.remove(row)
        inputs["parent_artifacts"][name] = a.lines_bytes(rows)
    with pytest.raises(DataError):
        x.stable_artifacts(inputs)


def test_new_review_preserves_both_local_passes_despite_complete_history_failure():
    rows = x.reviewed_exclusion(*reviewed_fixture())
    assert len(rows) == 2 and {r["action_verdict"] for r in rows.values()} == {"pass"}
    assert {r["prefix_training_fitness"] for r in rows.values()} == {"pass", "fail"}


@pytest.mark.parametrize("mutation", ["turn_bool", "arguments", "history_count", "missing_decision", "local_verdict", "prefix_verdict",
                                      "previous_rank_bool", "presence", "future_turn", "relabel"])
def test_new_review_rejects_changed_bindings_even_with_recomputed_record_hash(mutation):
    row, packet, parent, previous, buffers = reviewed_fixture()
    ref = row["adjudication"]
    record = json.loads(buffers[ref["file"]])["sources"][0]
    proposal = json.loads(buffers[ref["proposal_file"]])["newly_reviewed_sources"][0]
    decision, proposed = record["decisions"][0], proposal["all_decisions"][0]
    if mutation == "turn_bool":
        decision["source_turn_index"] = True
    elif mutation == "arguments":
        decision["calls"][0]["arguments_sha256"] = "0" * 64
    elif mutation == "history_count":
        record["raw_turn_count"] -= 1
    elif mutation == "missing_decision":
        record["decisions"].pop()
    elif mutation == "local_verdict":
        proposed["current_local_action_verdict"] = "fail"
    elif mutation == "prefix_verdict":
        proposed["current_prefix_training_fitness"] = "unknown"
    elif mutation == "previous_rank_bool":
        proposed["current_selection_bindings"]["formal"]["selection_rank"] = True
    elif mutation == "presence":
        proposed["recommended_effective_presence_next_version"] = True
    elif mutation == "future_turn":
        decision["future_turns_used_to_support_action"] = 0
    else:
        proposal["original_bytes_or_labels_to_mutate"] = True
    buffers[ref["file"]] = encoded({"sources": [record]})
    buffers[ref["proposal_file"]] = encoded({"newly_reviewed_sources": [proposal]})
    ref.update(source_record_sha256=canonical_hash(record), proposal_record_sha256=canonical_hash(proposal))
    with pytest.raises(DataError):
        x.reviewed_exclusion(row, packet, parent, previous, buffers)


def test_fixed_config_and_final_split_hash_only_boundary(tmp_path):
    config_path = Path(__file__).resolve().parents[2] / "configs/data-quality.v3.json"
    assert x.load_config(config_path)["training_authorized"] is False
    changed = tmp_path / "changed.json"
    changed.write_bytes(config_path.read_bytes() + b" ")
    with pytest.raises(DataError, match="input_hash_mismatch"):
        x.load_config(changed)
    root = tmp_path / "inputs"
    root.mkdir()
    final = tmp_path / "heldout.jsonl"
    final.write_bytes(b"DO NOT PARSE THIS ORIGINAL FIXTURE FINAL PAYLOAD\n")
    members = {}
    for i in range(346):
        name, data = f"copy-{i}.json", b"{}\n"
        (root / name).write_bytes(data)
        members[name] = {"kind": "exact_copy", "sha256": q.sha(data), "bytes": len(data),
            "read_mode": "full_authorized_input", "original_path": "DO NOT FOLLOW THIS PROVENANCE"}
    members["parent_data/test.jsonl"] = {"kind": "immutable_existing_artifact", "path": str(final),
        "sha256": q.sha(final.read_bytes()), "bytes": final.stat().st_size, "read_mode": "hash_only_no_deserialization"}
    manifest = {"schema": "toolalign.s0.quality-exclusion-inputs.v3", "owner": "S0", "training_authorized": False,
        "verified_code_base": "original", "expected_counts": {}, "files": members}
    data = encoded(manifest)
    (root / "manifest.json").write_bytes(data)
    config = {"input_bindings": {"input_manifest_file_sha256": q.sha(data)}, "verified_code_base": "original", "expected_counts": {}}
    _, buffers = x.fixed_bundle(root, config)
    assert len(buffers) == 346 and "parent_data/test.jsonl" not in buffers
    final.write_bytes(b"changed")
    with pytest.raises(DataError, match="input_hash_mismatch"):
        x.fixed_bundle(root, config)


@pytest.mark.parametrize("failure", ["input", "write"])
def test_failed_build_has_no_success_manifest(tmp_path, monkeypatch, failure):
    output = tmp_path / ".toolalign-local" / "candidate"
    if failure == "input":
        monkeypatch.setattr(x, "bound_inputs", lambda **kw: (_ for _ in ()).throw(DataError("original_input_failure")))
    else:
        monkeypatch.setattr(x, "bound_inputs", lambda **kw: revision_fixture())
        output.parent.write_bytes(b"an original file cannot be an output directory")
    with pytest.raises((DataError, OSError)):
        x.build(output=output, config_path="original", input_root="original")
    assert not (output / "manifest.json").exists()


def test_original_fixture_build_verify_detects_artifact_and_run_substitutions(tmp_path, monkeypatch):
    monkeypatch.setattr(x, "bound_inputs", lambda **kw: revision_fixture())
    output = tmp_path / ".toolalign-local" / "candidate"
    x.build(output=output, config_path="original", input_root="original")
    x.verify(output=output, config_path="original", input_root="original")
    original = (output / "effective/train.jsonl").read_bytes()
    (output / "effective/train.jsonl").write_bytes(b"{}\n")
    with pytest.raises(DataError, match="input_hash_mismatch"):
        x.verify(output=output, config_path="original", input_root="original")
    (output / "effective/train.jsonl").write_bytes(original)
    run = json.loads((output / "run.json").read_bytes())
    run["consumer"]["package_files"]["data/quality_exclusion.py"] = "0" * 64
    (output / "run.json").write_bytes(encoded(run))
    with pytest.raises(DataError, match="output_consumer_binding"):
        x.verify(output=output, config_path="original", input_root="original")


@pytest.mark.parametrize("mutation", [None, "counter_bool", "counter_changed", "source", "judgment", "review_commit", "seal", "s0_receipt"])
def test_new_issue_is_bound_to_its_adopted_review_event(mutation):
    row = {"issue_ids": ["ORIGINAL-V3-ISSUE"], "source_record_hash": "original-source", "group_id": "original-group",
        "split": "train", "example_ids": ["original-one", "original-two"],
        "adjudication": {"source_record_sha256": "a" * 64, "review_commit": "original-q1-commit"}}
    finding = {k: row[k] for k in ("source_record_hash", "group_id", "split")}
    finding["affected_example_ids"] = row["example_ids"]
    buffers = {"reviews/q1-v2/review-event-proposals.json": encoded({"new_finding": finding}),
        "reviews/q1-v2/final-evidence-seal.json": b"original Q1 seal", "s0/q1-receipt.json": b"original S0 receipt"}
    event = {"event_record_sha256": canonical_hash(finding), "source_judgment_sha256": row["adjudication"]["source_record_sha256"],
        "review_commit": row["adjudication"]["review_commit"], "evidence_seal_sha256": q.sha(buffers["reviews/q1-v2/final-evidence-seal.json"]),
        "s0_binding_sha256": q.sha(buffers["s0/q1-receipt.json"])}
    issue = {"issue_id": row["issue_ids"][0], "status": "CHANGES_REQUESTED", "consecutive_failed_revisions": 1, "events": [event]}
    if mutation == "counter_bool":
        issue["consecutive_failed_revisions"] = True
    elif mutation == "counter_changed":
        issue["consecutive_failed_revisions"] = 2
    elif mutation == "source":
        row["source_record_hash"] = "different original source"
    elif mutation == "judgment":
        event["source_judgment_sha256"] = "b" * 64
    elif mutation == "review_commit":
        event["review_commit"] = "different-original-review"
    elif mutation == "seal":
        event["evidence_seal_sha256"] = "c" * 64
    elif mutation == "s0_receipt":
        event["s0_binding_sha256"] = "d" * 64
    buffers["s0/review-failures.json"] = encoded({"whole_goal_paused": False, "issues": [issue]})
    buffers["s0/issue-adoption.json"] = encoded({"after_sha256": q.sha(buffers["s0/review-failures.json"]),
        "whole_goal_paused": False, "new_issue_id": row["issue_ids"][0]})
    if mutation:
        with pytest.raises(DataError):
            x.verify_issue(row, buffers)
    else:
        x.verify_issue(row, buffers)
