"""Independent original source families and failure probes; no real tokenizer."""

import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolalign.data import quality_materials as materials
from toolalign.data import quality_revision as quality
from toolalign.data.common import DataError


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(packed(value)).hexdigest()


def identifier(value):
    return digest({k: v for k, v in value.items() if k not in {"example_id", "group_id", "split"}})


def message(role, content="", calls=None, call_id=None):
    return {"role": role, "content": content, "tool_calls": calls or [], "tool_call_id": call_id}


def make_example(source, turn, history=None, split="train"):
    value = {"schema_version": "toolalign.example.v1", "source": "r1-original-quality-family",
        "source_revision": "r1.v1", "license_id": "MIT", "source_record_hash": digest(["original source", source]),
        "group_id": "same-original-group" if split == "train" else "separate-validation-group", "split": split,
        "messages": history or [message("user", "Repeat this original text three times.")],
        "tools": [{"schema_version": "toolalign.tool.v1", "name": "original_repeat", "description": "Repeat original text.",
                   "parameters_json_schema": {"type": "object", "properties": {"text": {"type": "string", "maxLength": 128},
                    "times": {"type": "integer"}}, "required": ["text"], "additionalProperties": False},
                   "tool_version": "r1.v1", "side_effect_class": "read_only", "timeout_ms": 100}],
        "expected_action": {"kind": "tool_calls", "content": "", "tool_calls": [
            {"call_id": f"original-{turn}", "name": "original_repeat", "arguments": {"text": f"original {turn}"}}]},
        "category": "tool_calls"}
    value["example_id"] = identifier(value)
    return value


def family():
    chain, history = [], None
    for turn in (1, 3, 5, 7):
        value = make_example("flagged", turn, history)
        chain.append(value)
        history = copy.deepcopy(value["messages"]) + [
            message("assistant", calls=copy.deepcopy(value["expected_action"]["tool_calls"])),
            message("tool", f"old observation {turn}", call_id=f"original-{turn}"),
            message("user", "Continue this original sequence with three repeats.")]
    values = chain + [make_example("kept", 1), make_example("unknown", 1), make_example("validation", 1, split="validation")]
    assignments = [{"source_index": i, **{k: e[k] for k in ("source_record_hash", "group_id", "split")}}
                   for i, e in enumerate([values[0], *values[4:]])]
    lineage = [{**{k: e[k] for k in ("example_id", "source_record_hash", "group_id", "split")},
                "normalized_hash": e["example_id"], "source_turn_index": int(e["expected_action"]["tool_calls"][0]["call_id"].split("-")[-1]),
                "exclusion_reason": None} for e in values]
    by_split = {s: [e for e in values if e["split"] == s] for s in ("train", "validation")}
    index = quality.original_index(by_split, assignments, lineage)
    issues, semantic = {}, []
    for assignment in assignments:
        source = assignment["source_record_hash"]
        members = [e for e in values if e["source_record_hash"] == source]
        verdict = "fail" if assignment["source_index"] == 0 else "unknown" if assignment["source_index"] == 2 else "pass"
        semantic.append({"source_index": str(assignment["source_index"]), "source_record_hash": source,
            "strata": "split:" + assignment["split"], "example_ids": ";".join(e["example_id"] for e in members),
            "verdict": verdict, "notes": "Original independent evidence."})
        if verdict == "pass":
            continue
        affected = members[1] if verdict == "fail" else members[0]
        issues[source] = {**{k: assignment[k] for k in ("source_index", "source_record_hash", "split")},
            "verdict": verdict, "origin": "semantic_100", "notes": "Original independent evidence.",
            "all_sample_example_ids": [e["example_id"] for e in members],
            "affected_target_example_ids": [affected["example_id"]],
            "affected_source_turns": [3 if verdict == "fail" else 1], "selected_membership": {}}
    parents, lines, removed = {}, {}, {}
    for profile in ("smoke", "formal"):
        parents[profile] = {}
        for split in ("train", "validation"):
            chosen = chain if profile == "smoke" and split == "train" else by_split[split]
            chosen = sorted(chosen, key=lambda e: quality.rank_key(e["example_id"]))
            sidecars = [{"selection_rank": rank, "ranking_sha256": quality.rank_key(e["example_id"])[0],
                "profile": profile, "split": split, "padding_bucket": 1024,
                "audit": {**{k: e[k] for k in quality.IDENTITY}, "example_sha256": digest(e)}} for rank, e in enumerate(chosen, 1)]
            parents[profile][split] = {"examples": chosen, "sidecars": sidecars,
                "summary": {"selected_count": len(chosen)}, "excluded": {"original_unselected": [
                    e["example_id"] for e in by_split[split] if e not in chosen]}}
            key = profile + "/" + split
            lines[key] = {e["example_id"]: json.dumps(e, ensure_ascii=False).encode() + b"\n" for e in chosen}
            for source, issue in issues.items():
                issue["selected_membership"][key] = [e["example_id"] for e in chosen if e["source_record_hash"] == source]
            removed[key] = {label: [e["example_id"] for e in chosen if issues.get(e["source_record_hash"], {}).get("verdict") == verdict]
                            for label, verdict in (("confirmed_fail", "fail"), ("uncertain", "unknown"))}
    parent = chain[1]
    action = copy.deepcopy(parent["expected_action"])
    action["tool_calls"][0]["arguments"]["times"] = 3
    draft = {"status": "DRAFT_NOT_APPLIED", "source_index": 0, "source_record_hash": parent["source_record_hash"],
             "original_example_id": parent["example_id"], "original_action_sha256": digest(parent["expected_action"]),
             "proposed_action": action, "reason": "Original fixture requests three repeats."}
    proof = {"source_record_hash": parent["source_record_hash"], "original_example_sha256": digest(parent),
             "original_tools_sha256": digest(parent["tools"]), "original_action_sha256": digest(parent["expected_action"])}
    counts = {"train": {"original": 6, "quarantined_fail": 4, "quarantined_unknown": 1, "effective": 1},
              "validation": {"original": 1, "quarantined_fail": 0, "quarantined_unknown": 0, "effective": 1},
              "formal_train": {"original": 6, "quarantined_fail": 4, "quarantined_unknown": 1, "effective": 1},
              "smoke_train": {"original": 4, "quarantined_fail": 4, "quarantined_unknown": 0, "effective": 0},
              "formal_validation": {"original": 1, "effective": 1}, "smoke_validation": {"original": 1, "effective": 1}}
    return {"index": index, "issues": issues, "drafts": [draft], "source_evidence": {parent["example_id"]: proof},
            "parents": parents, "parent_lines": lines, "parent_config": {"profiles": {"smoke": {}, "formal": {}}},
            "original_bytes": {e["example_id"]: json.dumps(e, ensure_ascii=False).encode() + b"\n" for e in values},
            "config": {"expected_counts": counts, "input_bindings": {"parent_selection_manifest_file_sha256": "original fixture",
                      "parent_training_config_file_sha256": "original fixture"}, "pending": ["independent_fixture_only"]},
            "proposal": {"status": "PROPOSED_NOT_APPLIED", "review_kind": "delegated_ai_not_human",
                "no_final_test_based_training_changes": True, "issues": list(issues.values()), "quarantine_example_ids": removed},
            "binding": {"parent_selection_input_binding": {}, "fixture_only": True}, "semantic": semantic,
            "original_rows": (by_split, assignments, lineage), "chain": chain}


def test_middle_revision_rebuilds_both_successors_and_keeps_all_observations_unverified():
    source = family()
    before = copy.deepcopy(source)
    stage = quality.stage_annotations(source["index"], source["issues"], source["drafts"], source["source_evidence"], "original-revision")
    assert len(stage["examples"]) == len(stage["sidecars"]) == 3
    assert [len(s["inherited_observations"]) for s in stage["sidecars"]] == [0, 1, 2]
    for candidate, sidecar, old in zip(stage["examples"], stage["sidecars"], source["chain"][1:], strict=True):
        assert candidate["example_id"] == identifier(candidate) != old["example_id"]
        assert sidecar["annotation_parent"] == old["example_id"] and sidecar["parent_example_sha256"] == digest(old)
        assert sidecar["direct_annotation_parent"] == source["chain"][1]["example_id"]
        assert sidecar["downstream_condition_verified"] is False and sidecar["enters_effective_training"] is False
        expected = copy.deepcopy(old)
        if sidecar["kind"] == "direct_action_revision":
            expected["expected_action"] = source["drafts"][0]["proposed_action"]
        else:
            for msg in expected["messages"]:
                if msg["role"] == "assistant" and msg["tool_calls"][0]["call_id"] == "original-3":
                    msg["tool_calls"] = source["drafts"][0]["proposed_action"]["tool_calls"]
            for observation in sidecar["inherited_observations"]:
                assert observation["status"] == "UNVERIFIED_AFTER_ACTION_CHANGE" and observation["executed_here"] is False
                assert observation["original_message_sha256"] == digest(old["messages"][observation["message_index"]])
        expected["example_id"] = identifier(expected)
        assert candidate == expected
    assert source == before


def test_whole_family_quarantine_and_zero_smoke_do_not_refill_from_same_group():
    source = family()
    artifacts, manifest = quality.stable_artifacts(source)
    assert manifest["counts"] == source["config"]["expected_counts"]
    assert artifacts["selection/smoke/train.examples.jsonl"] == b""
    kept = list(source["index"]["examples"].values())[4]
    assert artifacts["effective/train.jsonl"] == artifacts["selection/formal/train.examples.jsonl"] == source["original_bytes"][kept["example_id"]]
    assert manifest["unrelated_examples_retained_in_affected_groups"] == 1
    assert manifest["annotations"]["dependent_prefix_revisions"] == 2
    assert not manifest["training_authorized"]
    stage_ids = {json.loads(line)["example_id"] for line in artifacts["staging/examples.jsonl"].splitlines()}
    assert not stage_ids & set(source["index"]["examples"])


@pytest.mark.parametrize("fault", ["lineage_missing", "source_mismatch", "group_leak", "decision_missing", "noninteger_turn"])
def test_original_join_rejects_missing_and_cross_source_relations(fault):
    by_split, assignments, lineage = copy.deepcopy(family()["original_rows"])
    if fault == "lineage_missing":
        lineage.pop(1)
    elif fault == "source_mismatch":
        lineage[1]["source_record_hash"] = assignments[1]["source_record_hash"]
    elif fault == "group_leak":
        assignments[-1]["group_id"] = assignments[0]["group_id"]
    elif fault == "decision_missing":
        by_split["train"].pop(1)
    else:
        lineage[1]["source_turn_index"] = True
    with pytest.raises(DataError):
        quality.original_index(by_split, assignments, lineage)


@pytest.mark.parametrize("fault", ["missing_issue", "extra_target", "wrong_turn", "wrong_source", "wrong_verdict"])
def test_sealed_review_relation_rejects_incomplete_or_mismatched_proposal(fault):
    source = family()
    issue = source["proposal"]["issues"][0]
    if fault == "missing_issue":
        source["proposal"]["issues"].pop()
    elif fault == "extra_target":
        issue["affected_target_example_ids"].append(list(source["index"]["examples"])[4])
    elif fault == "wrong_turn":
        issue["affected_source_turns"] = [7]
    elif fault == "wrong_source":
        issue["source_index"] = 1
    else:
        issue["verdict"] = "unknown"
    with pytest.raises(DataError):
        quality.review_issues(source["index"], source["semantic"], [], {}, source["proposal"])


@pytest.mark.parametrize("fault", ["membership", "denominator", "removed"])
def test_stable_publication_rejects_selection_and_count_disagreements(fault):
    source = family()
    if fault == "membership":
        next(iter(source["issues"].values()))["selected_membership"]["formal/train"] = []
    elif fault == "denominator":
        source["config"]["expected_counts"]["formal_train"]["effective"] += 1
    else:
        source["proposal"]["quarantine_example_ids"]["formal/train"]["confirmed_fail"] = []
    with pytest.raises(DataError):
        quality.stable_artifacts(source)


@pytest.mark.parametrize("fault", ["root_chmod", "file_chmod", "manifest_chmod", "write", "before_rename", "after_rename"])
def test_publication_failure_never_exposes_accepted_manifest(tmp_path, monkeypatch, fault):
    out = tmp_path / ".toolalign-local" / "original-failure"
    original_chmod, original_replace, original_open = Path.chmod, quality.os.replace, Path.open

    def chmod(path, *args, **kwargs):
        if (fault == "root_chmod" and path == out or fault == "file_chmod" and path.name == "payload.json"
                or fault == "manifest_chmod" and path.name == ".manifest.pending"):
            raise OSError("original injected permission failure")
        return original_chmod(path, *args, **kwargs)

    def replace(src, dest):
        if fault == "before_rename":
            raise OSError("original failure before rename")
        result = original_replace(src, dest)
        if fault == "after_rename":
            raise OSError("original interruption after rename")
        return result

    def open_file(path, *args, **kwargs):
        if fault == "write" and path.name == ".manifest.pending":
            raise OSError("original manifest write failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "chmod", chmod)
    monkeypatch.setattr(Path, "open", open_file)
    monkeypatch.setattr(quality.os, "replace", replace)
    with pytest.raises(OSError):
        quality.publish(out, {"payload.json": b"original payload", "manifest.json": b"original manifest"}, {})
    assert not (out / "manifest.json").exists()


@pytest.mark.parametrize("fault", ["self_consistent_forgery", "consumer", "training", "model"])
def test_verifier_rederives_fixture_bytes_and_run_claims(tmp_path, monkeypatch, fault):
    source = family()
    monkeypatch.setattr(quality, "bound_inputs", lambda **_: source)
    out = tmp_path / ".toolalign-local" / "original-verified"
    quality.build(output=out)
    run = json.loads((out / "run.json").read_text())
    if fault == "self_consistent_forgery":
        manifest = json.loads((out / "manifest.json").read_text())
        (out / "effective/train.jsonl").write_bytes(b"")
        manifest["artifacts"]["effective/train.jsonl"] = {"sha256": hashlib.sha256(b"").hexdigest(), "size_bytes": 0}
        (out / "manifest.json").write_bytes(packed(manifest) + b"\n")
        run["stable_manifest_sha256"] = hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest()
    elif fault == "consumer":
        run["consumer"]["package_files"]["data/quality_revision.py"] = "0" * 64
    elif fault == "training":
        run["training_authorized"] = True
    else:
        run["model_modules_loaded"] = ["original forbidden claim"]
    (out / "run.json").write_bytes(packed(run))
    with pytest.raises(DataError):
        quality.verify(output=out)


def test_cpu_guards_run_before_input_reads_or_tokenizer_callbacks(tmp_path, monkeypatch):
    # A module-table sentinel is a fixture, not a framework import or run.
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(original_fixture=True))
    monkeypatch.setattr(quality, "bound_inputs", lambda **_: pytest.fail("input reader must not be reached"))
    with pytest.raises(DataError, match="cpu_only_process_required"):
        quality.build(output=tmp_path / ".toolalign-local" / "never-built")
    with pytest.raises(DataError, match="cpu_only_process_required"):
        quality.verify(output=tmp_path / ".toolalign-local" / "never-verified")
    with pytest.raises(DataError, match="cpu_only_process_required"):
        materials.write_measurement([], {}, tokenizers_by_profile={}, output=tmp_path / ".toolalign-local" / "never-tokenized",
                                    revision_manifest_sha256="original fixture")
    assert not (tmp_path / ".toolalign-local").exists()
