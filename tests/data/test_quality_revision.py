"""Quality lineage and fail-closed publication tests on original small families."""

import copy
import json
from pathlib import Path

import pytest
from quality_cases import inputs, semantic_rows

from toolalign.contracts import ContractError, canonical_hash
from toolalign.data import quality_revision as q
from toolalign.data.common import DataError


def test_whole_source_includes_preceding_and_dependent_decisions_keeps_unrelated_group():
    source = inputs()
    before = copy.deepcopy(source)
    view = q.revise_view(source["index"], source["issues"])
    assert len(view["quarantined"]) == 4
    assert {r["quarantine_reason"] for r in view["quarantined"]} == {
        "review_flagged_target", "same_source_preceding_decision", "same_source_other_decision_or_prefix"}
    assert sum(r["decision_itself_semantically_rejected"] for r in view["quarantined"]) == 1
    retained = [source["index"]["examples"][i] for i in view["retained"]["train"]]
    assert len(retained) == 1 and retained[0]["group_id"] == view["quarantined"][0]["group_id"]
    assert len(view["retained"]["validation"]) == 1
    assert source == before


def test_filter_preserves_original_rank_and_measurement_without_refill():
    source = inputs()
    result = q.filter_selection(source["index"], source["parents"], source["issues"], "revision", "parent")
    for p in result:
        for s, item in result[p].items():
            old = source["parents"][p][s]
            expected = [(e, r) for e, r in zip(old["examples"], old["sidecars"], strict=True)
                        if e["source_record_hash"] not in source["issues"]]
            assert item["examples"] == [e for e, _ in expected]
            for new, (_, original) in zip(item["sidecars"], expected, strict=True):
                assert new["audit"] == original["audit"]
                assert new["parent_selection_rank"] == original["selection_rank"]
                assert new["parent_sidecar_sha256"] == canonical_hash(original)
            assert [r["selection_rank"] for r in item["sidecars"]] == list(range(1, len(expected) + 1))
            assert item["summary"]["refill_count"] == 0


@pytest.mark.parametrize("mutation", ["source", "group", "split", "id", "duplicate", "missing_lineage", "cross_group_split"])
def test_original_identity_and_isolation_inputs_fail_closed(mutation):
    source = inputs()
    index = source["index"]
    values = list(index["examples"].values())
    assignments = list(index["assignments"].values())
    lineage = list(index["lineage"].values())
    if mutation == "source":
        values[0]["source_record_hash"] = "0" * 64
    elif mutation == "group":
        values[0]["group_id"] = "wrong"
    elif mutation == "split":
        values[0]["split"] = "test"
    elif mutation == "id":
        values[0]["example_id"] = "unchanged-but-invalid"
    elif mutation == "duplicate":
        values.append(copy.deepcopy(values[0]))
    elif mutation == "missing_lineage":
        lineage.pop()
    else:
        assignments[-1]["group_id"] = assignments[0]["group_id"]
    by_split = {s: [e for e in values if e["split"] == s] for s in q.SPLITS}
    if mutation == "split":
        by_split["train"].append(values[0])
    with pytest.raises(DataError):
        q.original_index(by_split, assignments, lineage)


def test_original_excluded_lineage_is_not_promoted_or_counted_as_retained():
    source = inputs()["index"]
    old = list(source["lineage"].values())
    excluded = {**old[0], "exclusion_reason": "original_length_exclusion"}
    final = {"split": "test", "exclusion_reason": None, "unexpected_semantic_payload": object()}
    result = q.original_index({s: [e for e in source["examples"].values() if e["split"] == s] for s in q.SPLITS},
                              list(source["assignments"].values()), old + [excluded, final])
    assert result == source


@pytest.mark.parametrize("mutation", ["source_index", "source_hash", "sample_id", "affected_id", "source_turn", "verdict", "notes", "missing", "duplicate", "final"])
def test_review_proposal_joins_reject_replaced_or_out_of_scope_identity(mutation):
    source = inputs()
    rows = semantic_rows(source)
    proposal = source["proposal"]
    issue = proposal["issues"][0]
    if mutation == "source_index":
        issue["source_index"] = 1
    elif mutation == "source_hash":
        issue["source_record_hash"] = "0" * 64
    elif mutation == "sample_id":
        issue["all_sample_example_ids"].pop()
    elif mutation == "affected_id":
        issue["affected_target_example_ids"] = ["0" * 64]
    elif mutation == "source_turn":
        issue["affected_source_turns"] = [99]
    elif mutation == "verdict":
        issue["verdict"] = "pass"
    elif mutation == "notes":
        issue["notes"] = "Replaced review text."
    elif mutation == "missing":
        proposal["issues"].pop()
    elif mutation == "duplicate":
        proposal["issues"].append(copy.deepcopy(issue))
    else:
        issue["split"] = "ood_test"
    with pytest.raises(DataError):
        q.review_issues(source["index"], rows, [], {}, proposal)


def test_final_review_rows_only_check_metadata_and_cannot_add_training_issues():
    source = inputs()
    rows = semantic_rows(source)
    assert len(q.review_issues(source["index"], rows, [], {}, source["proposal"])[0]) == 2
    source["index"]["assignments"][99] = {"source_index": 99, "source_record_hash": "9" * 64,
                                         "group_id": "final-only", "split": "test"}
    rows.append({"source_index": "99", "source_record_hash": "9" * 64, "strata": "split:test",
                 "example_ids": "final_metadata", "verdict": "fail", "notes": "Must never influence training."})
    issues, summary = q.review_issues(source["index"], rows, [], {}, source["proposal"])
    assert issues == source["issues"] and summary["final_metadata_only"] == 1


def test_review_attribution_wrapper_keeps_the_exact_nonempty_proposal_reason():
    source = inputs()
    rows = semantic_rows(source)
    for row in rows:
        row["notes"] = "[Original fixture attribution] " + row["notes"] + " Additional structural context."
    assert q.review_issues(source["index"], rows, [], {}, source["proposal"])[0] == source["issues"]
    source["proposal"]["issues"][0]["notes"] = ""
    with pytest.raises(DataError, match="proposal_verdict_binding"):
        q.review_issues(source["index"], rows, [], {}, source["proposal"])


@pytest.mark.parametrize("mutation", ["row_swap", "example_ids", "reviewer", "verdict", "timestamp", "original_filled"])
def test_filled_csv_requires_original_identity_and_explicit_ai_attribution(mutation):
    reviewed = semantic_rows(inputs())
    keys = ("source_index", "source_record_hash", "example_ids", "strata")
    original = [{k: v if k in keys else "" for k, v in r.items()} for r in reviewed]
    q.reviewed_csv(original, reviewed, keys)
    if mutation == "row_swap":
        reviewed.reverse()
    elif mutation == "example_ids":
        reviewed[0]["example_ids"] = "another"
    elif mutation == "reviewer":
        reviewed[0]["reviewer"] = "kris"
    elif mutation == "verdict":
        reviewed[0]["verdict"] = "approved"
    elif mutation == "timestamp":
        reviewed[0]["reviewed_at_utc"] = "2026-09-07T00:00:00"
    else:
        original[0]["verdict"] = "pass"
    with pytest.raises(DataError):
        q.reviewed_csv(original, reviewed, keys)


@pytest.mark.parametrize("mutation", ["duplicate", "reorder", "changed_example", "rank", "audit", "profile", "final"])
def test_parent_selection_cannot_be_refilled_reordered_or_rebound(mutation):
    source = inputs()
    parent = source["parents"]["formal"]["train"]
    if mutation == "duplicate":
        parent["examples"].append(copy.deepcopy(parent["examples"][0]))
        parent["sidecars"].append(copy.deepcopy(parent["sidecars"][0]))
    elif mutation == "reorder":
        parent["examples"].reverse()
        parent["sidecars"].reverse()
    elif mutation == "changed_example":
        parent["examples"][0] = {**parent["examples"][0], "source_revision": "wrong"}
    elif mutation == "rank":
        parent["sidecars"][0]["selection_rank"] = True
    elif mutation == "audit":
        parent["sidecars"][0]["audit"]["example_sha256"] = "0" * 64
    elif mutation == "profile":
        parent["sidecars"][0]["profile"] = "another"
    else:
        source["parents"]["formal"]["test"] = parent
    with pytest.raises(DataError):
        q.filter_selection(source["index"], source["parents"], source["issues"], "r", "p")


def test_annotations_change_ids_preserve_upstream_and_invalidate_downstream_observations():
    source = inputs()
    before = copy.deepcopy(source)
    result = q.stage_annotations(source["index"], source["issues"], source["drafts"], source["source_evidence"], "revision")
    direct, dependent = result["examples"]
    assert direct["expected_action"]["tool_calls"][0]["arguments"]["scale"] == 3
    assert direct["example_id"] == q.normalized_id(direct)
    assert dependent["example_id"] == q.normalized_id(dependent)
    old = source["index"]["examples"][result["sidecars"][1]["annotation_parent"]]
    assert dependent["expected_action"] == old["expected_action"]
    assert dependent["messages"][-1] == old["messages"][-1]
    assert dependent["messages"][-2]["tool_calls"][0]["arguments"]["scale"] == 3
    for candidate, sidecar in zip(result["examples"], result["sidecars"], strict=True):
        parent = source["index"]["examples"][sidecar["annotation_parent"]]
        assert candidate["example_id"] != parent["example_id"]
        assert all(candidate[k] == parent[k] for k in ("source_record_hash", "source_revision", "split", "group_id", "license_id"))
        assert sidecar["semantic_verdict"] is None and sidecar["external_execution"] == "NOT_RUN"
        assert sidecar["enters_effective_training"] is False and sidecar["downstream_condition_verified"] is False
    assert result["sidecars"][1]["inherited_observations"][0]["status"] == "UNVERIFIED_AFTER_ACTION_CHANGE"
    assert source == before


@pytest.mark.parametrize("mutation", ["action_hash", "source_hash", "schema_evidence", "user_evidence", "call_name", "extra_change", "unchanged", "invalid_parameter", "lost_prefix", "duplicate_draft"])
def test_annotation_rejects_unsupported_identity_or_changes(mutation):
    source = inputs()
    draft = source["drafts"][0]
    if mutation == "action_hash":
        draft["original_action_sha256"] = "0" * 64
    elif mutation == "source_hash":
        draft["source_record_hash"] = "0" * 64
    elif mutation == "schema_evidence":
        source["source_evidence"][draft["original_example_id"]]["original_tools_sha256"] = "0" * 64
    elif mutation == "user_evidence":
        source["source_evidence"][draft["original_example_id"]]["original_example_sha256"] = "0" * 64
    elif mutation == "call_name":
        draft["proposed_action"]["tool_calls"][0]["name"] = "another_tool"
    elif mutation == "extra_change":
        draft["proposed_action"]["tool_calls"][0]["arguments"]["value"] = 99
    elif mutation == "unchanged":
        del draft["proposed_action"]["tool_calls"][0]["arguments"]["scale"]
    elif mutation == "invalid_parameter":
        draft["proposed_action"]["tool_calls"][0]["arguments"]["scale"] = "three"
    elif mutation == "lost_prefix":
        candidate = list(source["index"]["examples"].values())[2]
        candidate["messages"][-2]["tool_calls"][0]["arguments"]["value"] = 999
    else:
        source["drafts"].append(copy.deepcopy(draft))
    with pytest.raises((DataError, ContractError)):
        q.stage_annotations(source["index"], source["issues"], source["drafts"], source["source_evidence"], "r")


def test_stable_views_preserve_exact_jsonl_bytes_and_staging_is_disjoint():
    source = inputs()
    # Noncanonical whitespace is part of these original fixture bytes.
    source["original_bytes"] = {i: json.dumps(source["index"]["examples"][i], indent=None, ensure_ascii=False).encode() + b"\n"
                                for i in source["index"]["examples"]}
    for group in source["parent_lines"].values():
        for ident in group:
            group[ident] = source["original_bytes"][ident]
    one, manifest = q.stable_artifacts(source)
    assert q.stable_artifacts(source) == (one, manifest)
    view = q.revise_view(source["index"], source["issues"])
    assert one["effective/train.jsonl"] == b"".join(source["original_bytes"][i] for i in view["retained"]["train"])
    kept = {e["example_id"] for name, b in one.items() if name.startswith("selection/") and name.endswith(".examples.jsonl")
            for e in q.jsonl(b)[0]}
    assert not kept & {e["example_id"] for e in q.jsonl(one["staging/examples.jsonl"])[0]}
    assert manifest["annotations"]["dependent_prefix_revisions"] == 1
    assert manifest["unrelated_examples_retained_in_affected_groups"] == 1
    assert all(m["training_authorized"] is False for m in (manifest, json.loads(one["training-binding.json"]),
                                                         json.loads(one["selection/manifest.json"])))


@pytest.mark.parametrize("mutation", ["example", "sidecar", "manifest", "run", "extra", "missing", "symlink"])
def test_build_and_verify_rederive_original_fixture_bytes(monkeypatch, tmp_path, mutation):
    source = inputs()
    monkeypatch.setattr(q, "bound_inputs", lambda **_: source)
    out = tmp_path / ".toolalign-local" / "revision"
    first = q.build(output=out)
    assert q.verify(output=out) == first
    if mutation in {"example", "sidecar", "manifest"}:
        name = {"example": "effective/train.jsonl", "sidecar": "staging/sidecars.jsonl", "manifest": "manifest.json"}[mutation]
        (out / name).write_text("{}\n")
    elif mutation == "run":
        run = json.loads((out / "run.json").read_text())
        run["training_authorized"] = True
        (out / "run.json").write_text(json.dumps(run))
    elif mutation == "extra":
        (out / "unexpected.json").write_text("{}")
    elif mutation == "missing":
        (out / "effective/validation.jsonl").unlink()
    else:
        (out / "alias").symlink_to(out / "effective")
    with pytest.raises(DataError):
        q.verify(output=out)


def test_failed_inputs_or_writes_never_leave_success_manifest(monkeypatch, tmp_path):
    out = tmp_path / ".toolalign-local" / "failed"
    monkeypatch.setattr(q, "bound_inputs", lambda **_: (_ for _ in ()).throw(DataError("bad_input")))
    with pytest.raises(DataError):
        q.build(output=out)
    assert not out.exists()
    monkeypatch.setattr(q, "bound_inputs", lambda **_: inputs())
    original_open = Path.open

    def fail_open(self, *args, **kwargs):
        if self.name == "run.json":
            raise OSError("original fixture disk-write failure")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_open)
    with pytest.raises(OSError):
        q.build(output=out)
    assert out.exists() and not (out / "manifest.json").exists()


def test_existing_output_public_output_and_wrong_policy_bytes_are_rejected(tmp_path):
    root = tmp_path / ".toolalign-local"
    root.mkdir()
    with pytest.raises(DataError, match="output_already_exists"):
        q.build(output=root)
    with pytest.raises(DataError, match="private_output_required"):
        q.publish(tmp_path / "public", {"manifest.json": b"{}"}, {})
    config = tmp_path / "config.json"
    config.write_text("{}")
    with pytest.raises(DataError, match="input_hash_mismatch"):
        q.load_config(config)
    for name in ("../outside", "/absolute", "a\\b"):
        with pytest.raises(DataError, match="artifact_path_escape"):
            q.child_path(root, name)


def test_pinned_loader_parses_the_checked_buffer_even_when_source_changes(monkeypatch, tmp_path):
    target = tmp_path / "input.json"
    expected = b'{"original":true}'
    target.write_bytes(expected)
    original_read = Path.read_bytes

    def swap_after_read(self):
        data = original_read(self)
        if self == target:
            self.write_bytes(b'{"changed":true}')
        return data

    monkeypatch.setattr(Path, "read_bytes", swap_after_read)
    assert json.loads(q.pinned(target, q.sha(expected))) == {"original": True}
    with pytest.raises(DataError):
        q.pinned(target, q.sha(expected))
