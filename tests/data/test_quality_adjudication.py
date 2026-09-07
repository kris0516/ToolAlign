"""Meaningful source isolation, restoration and input replacement regressions."""

import copy
import json
from pathlib import Path

import pytest
from adjudication_cases import revision_fixture, source_fixture

from toolalign.contracts import canonical_hash
from toolalign.data import quality_adjudication as a
from toolalign.data import quality_revision as q
from toolalign.data.common import DataError, encoded


def test_whole_source_excludes_preceding_and_later_local_pass_without_rewriting_verdict():
    index, row, packet, raw, buffers = source_fixture()
    a.source_members(index, row, packet, raw)
    decisions = a.reviewed_source(row, buffers, index, packet)
    view = a.adjudicated_view(index, {row["source_record_hash"]: row},
                             {i: encoded(e) + b"\n" for i, e in index["examples"].items()}, decisions)
    assert len(view["excluded"]) == 3 and view["retained"] == {"train": [], "validation": []}
    assert [r["local_action_review"]["action_verdict"] for r in view["reasons"]] == ["pass", "unknown", "pass"]
    assert all(r["source_training_fitness"] == "unknown" for r in view["reasons"])


@pytest.mark.parametrize("mutation", ["missing_decision", "duplicate", "other_source", "final_split", "raw_source", "packet_action",
                                      "bool_action", "bool_lineage", "bool_source_index", "bool_count", "bool_flag", "binding_turn", "restore_unknown"])
def test_source_membership_rejects_identity_type_and_scope_substitution(mutation):
    index, row, packet, raw, _ = source_fixture()
    if mutation == "missing_decision":
        row["example_ids"].pop()
    elif mutation == "duplicate":
        packet["valid_decisions"][1] = copy.deepcopy(packet["valid_decisions"][0])
    elif mutation == "other_source":
        row["source_record_hash"] = "0" * 64
    elif mutation == "final_split":
        row["split"] = "test"
    elif mutation == "raw_source":
        raw[0]["conversations"][0]["value"] = "different original text"
    elif mutation in {"packet_action", "bool_action"}:
        packet["valid_decisions"][0]["example"]["expected_action"]["tool_calls"][0]["arguments"]["value"] = False if mutation == "bool_action" else 2
    elif mutation == "bool_lineage":
        packet["valid_decisions"][0]["lineage"]["source_turn_index"] = True
    elif mutation == "bool_source_index":
        row["source_indices"] = [False]
    elif mutation == "bool_count":
        row["valid_decision_count"] = True
    elif mutation == "bool_flag":
        row["original_bytes_mutated"] = 0
    elif mutation == "binding_turn":
        row["binding"][0]["source_turn_index"] = True
    else:
        row["disposition"] = "restore_original_source"
    with pytest.raises(DataError):
        a.source_members(index, row, packet, raw)


@pytest.mark.parametrize("mutation", ["raw_action", "turn_type", "prefix_flag", "call_type", "review_commit", "local_verdict", "missing_decision"])
def test_adopted_review_rejects_rebound_records_even_with_recomputed_record_hash(mutation):
    index, row, packet, _, buffers = source_fixture()
    name = row["adjudication"]["file"]
    record = json.loads(buffers[name])
    if mutation == "raw_action":
        record["decisions"][0]["source_action_sha256"] = "0" * 64
    elif mutation == "turn_type":
        record["decisions"][0]["turn"] = True
    elif mutation == "prefix_flag":
        record["decisions"][0]["full_prefix_reviewed"] = 1
    elif mutation == "call_type":
        record["decisions"][0]["calls"][0]["arguments"]["value"] = False
    elif mutation == "review_commit":
        row["adjudication"]["review_commit"] = "another"
    elif mutation == "local_verdict":
        record["decisions"][0]["verdict"] = "approved"
    else:
        record["decisions"].pop()
    buffers[name] = encoded(record)
    row["adjudication"]["source_record_sha256"] = canonical_hash(record)
    with pytest.raises(DataError):
        a.reviewed_source(row, buffers, index, packet)


def q1_history_fixture():
    index, row, packet, raw, buffers = source_fixture()
    old = json.loads(buffers[row["adjudication"]["file"]])
    decisions = old["decisions"]
    for d in decisions:
        d["source_turn_index"] = d.pop("turn")
        d["verdict"] = "pass"
    adjudication = {"identity": packet["identity"], "reviewer": "Codex-AI(Q1)", "decisions": decisions,
        "complete_source_reviewed": True, "all_valid_decisions_reviewed": True, "source_action_verdict": "pass",
        "source_training_fitness": "fail", "disposition": "quarantine_entire_source", "mutations_applied": False,
        "history_coverage": {"whole_source_turn_indices": list(range(len(raw[0]["conversations"]))),
                             "original_fixture_problem": "Earlier history is unsupported."}}
    proposal = {"source_record_hash": row["source_record_hash"], "original_split": "train", "proposed_split": "train",
        "source_training_fitness": "fail", "disposition": "quarantine_entire_source", "history_coverage": adjudication["history_coverage"],
        "all_valid_example_ids": row["example_ids"], "implemented": False, "training_authorized": False,
        "original_bytes_mutated": False, "source_adjudication_sha256": canonical_hash(adjudication)}
    row["source_training_fitness"] = "fail"
    row["adjudication"] = {"reviewer": "Codex-AI(Q1)", "review_commit": "original-q1-fixture",
        "file": "reviews/q1-r2/next-version-proposals.json", "source_record_sha256": canonical_hash(proposal)}
    buffers["reviews/q1-r2/adjudications.json"] = encoded({"sources": [adjudication]})
    buffers["reviews/q1-r2/next-version-proposals.json"] = encoded({"sources": [proposal]})
    buffers["reviews/q1-r2/final-evidence-seal.json"] = encoded({"commit": "original-q1-fixture"})
    return index, row, packet, raw, buffers


def test_q1_local_pass_does_not_override_adopted_whole_source_history_failure():
    index, row, packet, raw, buffers = q1_history_fixture()
    a.source_members(index, row, packet, raw)
    decisions = a.reviewed_source(row, buffers, index, packet)
    assert {d["action_verdict"] for d in decisions.values()} == {"pass"}
    view = a.adjudicated_view(index, {row["source_record_hash"]: row},
        {i: encoded(e) + b"\n" for i, e in index["examples"].items()}, decisions)
    assert len(view["excluded"]) == 3 and not view["retained"]["train"]
    assert all(r["source_training_fitness"] == "fail" for r in view["reasons"])


@pytest.mark.parametrize("mutation", ["fitness", "proposed_split", "history_type", "mutation_flag"])
def test_q1_proposal_joins_cannot_replace_fitness_split_or_history_types(mutation):
    index, row, packet, _, buffers = q1_history_fixture()
    proposal = json.loads(buffers[row["adjudication"]["file"]])["sources"][0]
    if mutation == "fitness":
        proposal["source_training_fitness"] = "pass"
    elif mutation == "proposed_split":
        proposal["proposed_split"] = "test"
    elif mutation == "history_type":
        proposal["history_coverage"]["whole_source_turn_indices"][0] = False
    else:
        proposal["original_bytes_mutated"] = 0
    buffers[row["adjudication"]["file"]] = encoded({"sources": [proposal]})
    row["adjudication"]["source_record_sha256"] = canonical_hash(proposal)
    with pytest.raises(DataError):
        a.reviewed_source(row, buffers, index, packet)


def test_restoration_uses_original_bytes_original_rank_and_preserves_same_group_sources():
    source = revision_fixture()
    before = copy.deepcopy(source)
    artifacts, manifest = a.stable_artifacts(source)
    assert artifacts == a.stable_artifacts(source)[0]
    assert manifest["counts"]["train"] == {"original": 5, "quarantined_fail": 3, "quarantined_unknown": 0, "effective": 2}
    restored = json.loads(artifacts["restored/identities.json"])
    assert len(restored) == 1
    for profile in q.PROFILES:
        old = source["parents"][profile]["train"]
        values, lines = q.jsonl(artifacts[f"selection/{profile}/train.examples.jsonl"])
        sidecars = q.jsonl(artifacts[f"selection/{profile}/train.sidecars.jsonl"])[0]
        for e, line, sidecar in zip(values, lines, sidecars, strict=True):
            assert line == source["original_bytes"][e["example_id"]]
            rank = next(i for i, original in enumerate(old["examples"], 1) if original["example_id"] == e["example_id"])
            assert sidecar["parent_selection_rank"] == rank
            assert sidecar["restored_original_source"] is (e["example_id"] in restored)
        assert [e["example_id"] for e in values] == [e["example_id"] for e in old["examples"]
            if source["sources"].get(e["source_record_hash"], {}).get("source_training_fitness") != "fail"]
    assert manifest["other_sources_retained_in_affected_groups"] == 2
    assert manifest["other_decisions_retained_in_affected_groups"] == 2
    delta = json.loads(artifacts["delta-from-v1.json"])
    assert delta["sets"]["train"]["restored_original_ids"] == restored
    assert json.loads(artifacts["training-binding.json"])["training_authorized"] is False
    assert json.loads(artifacts["staging-reference.json"])["new_tokenization_runs"] == 0
    assert source == before


def test_fixed_configuration_rejects_even_semantically_equivalent_byte_replacement(tmp_path):
    config = Path(__file__).resolve().parents[2] / "configs/data-quality.v2.json"
    assert a.load_config(config)["training_authorized"] is False
    changed = tmp_path / "changed.json"
    changed.write_bytes(config.read_bytes() + b" ")
    with pytest.raises(DataError, match="input_hash_mismatch"):
        a.load_config(changed)


def test_other_source_count_deduplicates_multiple_retained_decisions():
    source = revision_fixture()
    first, second = source["sources"].values()
    first.update(source_training_fitness="pass", disposition="restore_original_source")
    second.update(source_training_fitness="fail", disposition="exclude_entire_source")
    counts = source["config"]["expected_counts"]
    counts["train"] = {"original": 5, "quarantined_fail": 1, "quarantined_unknown": 0, "effective": 4}
    source["config"]["disposition"]["excluded_decisions"] = 1
    for profile in q.PROFILES:
        for split in q.SPLITS:
            values = source["parents"][profile][split]["examples"]
            removed = sum(e["source_record_hash"] == second["source_record_hash"] for e in values)
            counts[profile + "_" + split] = {"original": len(values), "quarantined_fail": removed,
                                              "quarantined_unknown": 0, "effective": len(values) - removed}
    _, manifest = a.stable_artifacts(source)
    assert manifest["other_sources_retained_in_affected_groups"] == 2
    assert manifest["other_decisions_retained_in_affected_groups"] == 4


def test_fixed_bundle_hashes_final_split_payload_without_deserializing_it(tmp_path, monkeypatch):
    root = tmp_path / "input"
    root.mkdir()
    final = tmp_path / "test.jsonl"
    final.write_bytes(b"THIS FINAL PAYLOAD MUST NOT BE DESERIALIZED\n")
    members = {}
    for i in range(216):
        name, data = f"copy-{i}.json", b"{}\n"
        (root / name).write_bytes(data)
        members[name] = {"kind": "exact_copy", "sha256": q.sha(data), "bytes": len(data), "read_mode": "full_authorized_input",
                         "original_path": "THIS PROVENANCE MUST NOT BE FOLLOWED"}
    members["parent_data/test.jsonl"] = {"kind": "immutable_existing_artifact", "path": str(final), "sha256": q.sha(final.read_bytes()),
                                         "bytes": final.stat().st_size, "read_mode": "hash_only_no_deserialization"}
    manifest = {"schema": "toolalign.s0.quality-adjudication-inputs.v2", "owner": "S0", "training_authorized": False,
                "verified_code_base": "fixture", "expected_counts": {}, "files": members}
    data = encoded(manifest)
    (root / "manifest.json").write_bytes(data)
    config = {"input_bindings": {"input_manifest_file_sha256": q.sha(data)}, "verified_code_base": "fixture", "expected_counts": {}}
    _, buffers = a.fixed_bundle(root, config)
    assert len(buffers) == 216 and "parent_data/test.jsonl" not in buffers
    final.write_bytes(b"changed")
    with pytest.raises(DataError, match="input_hash_mismatch"):
        a.fixed_bundle(root, config)


@pytest.mark.parametrize("failure", ["input", "write"])
def test_failed_build_has_no_success_manifest(tmp_path, monkeypatch, failure):
    output = tmp_path / ".toolalign-local" / "candidate"
    source = revision_fixture()
    if failure == "input":
        monkeypatch.setattr(a, "bound_inputs", lambda **kw: (_ for _ in ()).throw(DataError("fixture_input_rejected")))
    else:
        monkeypatch.setattr(a, "bound_inputs", lambda **kw: source)
        monkeypatch.setattr(q.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("original fixture write failure")))
    with pytest.raises((DataError, OSError)):
        a.build(output=output, config_path="fixture", input_root="fixture")
    assert not (output / "manifest.json").exists()


def test_fresh_builds_and_verify_detect_replaced_output_and_consumer(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "bound_inputs", lambda **kw: revision_fixture())
    one, two = [tmp_path / ".toolalign-local" / name for name in ("one", "two")]
    for output in (one, two):
        a.build(output=output, config_path="fixture", input_root="fixture")
        a.verify(output=output, config_path="fixture", input_root="fixture")
    assert (one / "manifest.json").read_bytes() == (two / "manifest.json").read_bytes()
    (one / "effective/train.jsonl").write_bytes(b"{}\n")
    with pytest.raises(DataError, match="input_hash_mismatch"):
        a.verify(output=one, config_path="fixture", input_root="fixture")
    run = json.loads((two / "run.json").read_bytes())
    run["consumer"]["package_files"]["data/quality_adjudication.py"] = "0" * 64
    (two / "run.json").write_bytes(encoded(run))
    with pytest.raises(DataError, match="output_consumer_binding"):
        a.verify(output=two, config_path="fixture", input_root="fixture")


def test_seal_member_requires_exact_round_and_never_follows_embedded_paths():
    seal = {"files": {"q1-r2/adjudications.json": {"sha256": q.sha(b"new"), "bytes": 3},
                       "q1-r2/input/prior-q1/adjudications.json": {"sha256": q.sha(b"old"), "bytes": 3}}}
    a.seal_member(seal, "q1-r2/adjudications.json", b"new")
    with pytest.raises(DataError, match="review_seal_member_identity"):
        a.seal_member(seal, "adjudications.json", b"new")
