"""Read-only, stdlib cross-check of two actual quality-view materializations.

Inputs are explicit private paths. This checker imports no ToolAlign producer,
tokenizer or model; its success is a worker check, not independent R1 acceptance.
"""

import argparse
import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def canonical(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    lines = Path(path).read_bytes().splitlines(keepends=True)
    assert all(line.endswith(b"\n") for line in lines)
    return [json.loads(line) for line in lines], lines


def bundle(root, manifest):
    for name, info in manifest["artifacts"].items():
        path = root / name
        assert not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
        assert digest(path) == (info if isinstance(info, str) else info["sha256"])
        if isinstance(info, dict):
            assert path.stat().st_size == info["size_bytes"]


def check(args):
    paths = read(args.inputs)
    cfg = read(paths["config_path"])
    assert digest(paths["config_path"]) == "ddc7902386c5f00032ec938c8baa7f2f338b9d88c260ed0803e00e797feb83ce"
    pins = cfg["input_bindings"]
    original_root = Path(paths["data_manifest_path"]).parent
    original_manifest = read(paths["data_manifest_path"])
    assert digest(paths["data_manifest_path"]) == pins["data_manifest_file_sha256"]
    assert canonical(original_manifest) == pins["data_manifest_canonical_sha256"]
    bundle(original_root, original_manifest)
    parent_root = Path(paths["selection_manifest_path"]).parent
    parent_manifest = read(paths["selection_manifest_path"])
    assert digest(paths["selection_manifest_path"]) == pins["parent_selection_manifest_file_sha256"]
    bundle(parent_root, parent_manifest)
    first, second = Path(args.first), Path(args.second)
    left, right = read(first / "manifest.json"), read(second / "manifest.json")
    assert left == right and left["counts"] == cfg["expected_counts"]
    assert left["training_authorized"] is False
    assert canonical(left["quality_revision"]) == left["quality_revision_sha256"]
    for root in (first, second):
        bundle(root, left)
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        assert actual == set(left["artifacts"]) | {"manifest.json", "run.json"}
    for name in set(left["artifacts"]) | {"manifest.json"}:
        assert (first / name).read_bytes() == (second / name).read_bytes()
    runs = [read(root / "run.json") for root in (first, second)]
    assert runs[0]["created_at_utc"] != runs[1]["created_at_utc"]
    assert all(r["stable_manifest_sha256"] == digest(first / "manifest.json") for r in runs)
    review_root = Path(paths["review_root"])
    proposal = read(review_root / "remediation_proposal.json")
    assert digest(review_root / "remediation_proposal.json") == pins["remediation_proposal_sha256"]
    issues = {i["source_record_hash"]: i for i in proposal["issues"]}
    assert Counter(i["verdict"] for i in issues.values()) == {"fail": 20, "unknown": 12}
    assert all(i["split"] == "train" for i in issues.values())
    originals, bytes_by_id, quarantine_ids, retained_ids = {}, {}, [], []
    for split in ("train", "validation"):
        values, lines = rows(original_root / (split + ".jsonl"))
        assert all(e["split"] == split for e in values)
        originals.update({e["example_id"]: e for e in values})
        bytes_by_id.update({e["example_id"]: line for e, line in zip(values, lines, strict=True)})
        retained = [(e, line) for e, line in zip(values, lines, strict=True) if e["source_record_hash"] not in issues]
        excluded = [e for e in values if e["source_record_hash"] in issues]
        assert (first / "effective" / (split + ".jsonl")).read_bytes() == b"".join(line for _, line in retained)
        retained_ids.extend(e["example_id"] for e, _ in retained)
        quarantine_ids.extend(e["example_id"] for e in excluded)
    assert len(originals) == 7749 and len(retained_ids) == 7709 and len(quarantine_ids) == 40
    actual_quarantine, actual_lines = rows(first / "quarantine/examples.jsonl")
    assert [e["example_id"] for e in actual_quarantine] == quarantine_ids
    assert actual_lines == [bytes_by_id[i] for i in quarantine_ids]
    original_lineage = {r["example_id"]: r for r in rows(original_root / "lineage.jsonl")[0]
                        if r["split"] in ("train", "validation") and r["exclusion_reason"] is None}
    retained_lineage = rows(first / "effective/lineage.jsonl")[0]
    assert [r["example_id"] for r in retained_lineage] == retained_ids
    for r in retained_lineage:
        ident = r["example_id"]
        assert r["original_lineage_sha256"] == canonical(original_lineage[ident])
        assert r["original_jsonl_line_sha256"] == hashlib.sha256(bytes_by_id[ident]).hexdigest()
    quarantined_sidecars = rows(first / "quarantine/sidecars.jsonl")[0]
    assert [r["example_id"] for r in quarantined_sidecars] == quarantine_ids
    for r in quarantined_sidecars:
        ident = r["example_id"]
        issue = issues[originals[ident]["source_record_hash"]]
        assert r["review_verdict"] == issue["verdict"]
        assert r["original_lineage_sha256"] == canonical(original_lineage[ident])
        assert r["original_example_sha256"] == canonical(originals[ident])
        assert r["review_issue_sha256"] == canonical(issue)
    groups = {originals[i]["group_id"] for i in quarantine_ids}
    same_group_kept = [i for i in retained_ids if originals[i]["group_id"] in groups]
    assert len(same_group_kept) == left["unrelated_examples_retained_in_affected_groups"] > 0
    selected_counts = {}
    for p in ("smoke", "formal"):
        for split in ("train", "validation"):
            prefix = p + "/" + split
            old, old_lines = rows(parent_root / (prefix + ".examples.jsonl"))
            old_sidecars = rows(parent_root / (prefix + ".sidecars.jsonl"))[0]
            kept = [(rank, e, line, s) for rank, (e, line, s) in enumerate(zip(old, old_lines, old_sidecars, strict=True), 1)
                    if e["source_record_hash"] not in issues]
            output = first / "selection" / prefix
            assert Path(str(output) + ".examples.jsonl").read_bytes() == b"".join(line for _, _, line, _ in kept)
            new_sidecars = rows(Path(str(output) + ".sidecars.jsonl"))[0]
            assert len(new_sidecars) == len(kept)
            for new_rank, (sidecar, (old_rank, e, _, parent)) in enumerate(zip(new_sidecars, kept, strict=True), 1):
                assert sidecar["selection_rank"] == new_rank and sidecar["parent_selection_rank"] == old_rank
                assert sidecar["parent_sidecar_sha256"] == canonical(parent)
                assert {k: sidecar[k] for k in parent if k != "selection_rank"} == {k: v for k, v in parent.items() if k != "selection_rank"}
                assert sidecar["quality_revision_sha256"] == left["quality_revision_sha256"]
                assert e["example_id"] in retained_ids
            selected_counts[prefix] = len(kept)
    assert selected_counts == {"smoke/train": 1593, "smoke/validation": 197, "formal/train": 5980, "formal/validation": 217}
    staged = rows(first / "staging/examples.jsonl")[0]
    annotations = rows(first / "staging/sidecars.jsonl")[0]
    assert len(staged) == len(annotations) == 3
    assert not {e["example_id"] for e in staged} & set(originals)
    assert digest(review_root / "reannotation_drafts.json") == pins["reannotation_drafts_sha256"]
    drafts = {d["original_example_id"]: d for d in read(review_root / "reannotation_drafts.json")}
    raw = read(paths["raw_source_path"])
    assert digest(paths["raw_source_path"]) == pins["raw_source_sha256"]
    by_parent = {s["annotation_parent"]: (e, s) for e, s in zip(staged, annotations, strict=True)}
    for parent_id, draft in drafts.items():
        original = originals[parent_id]
        direct, sidecar = by_parent[parent_id]
        assert direct["expected_action"] == draft["proposed_action"]
        source = raw[draft["source_index"]]
        assert canonical(source) == original["source_record_hash"] == draft["source_record_hash"]
        assert canonical(original["expected_action"]) == draft["original_action_sha256"]
        end = original_lineage[parent_id]["source_turn_index"]
        evidence = sidecar["source_evidence"]
        expected_users = [{"source_turn_index": i, "content": t["value"], "source_turn_sha256": canonical(t)}
                          for i, t in enumerate(source["conversations"][:end]) if t["from"] == "user"]
        assert evidence["user_evidence"] == expected_users
        assert evidence["original_tools_sha256"] == canonical(original["tools"])
        assert evidence["raw_action_text_sha256"] == hashlib.sha256(source["conversations"][end]["value"].encode()).hexdigest()
        expected = copy.deepcopy(original)
        expected["expected_action"] = copy.deepcopy(draft["proposed_action"])
        expected["example_id"] = canonical({k: v for k, v in expected.items() if k not in ("example_id", "group_id", "split")})
        assert direct == expected
        for descendant in originals.values():
            d_id = descendant["example_id"]
            if descendant["source_record_hash"] != original["source_record_hash"] or original_lineage[d_id]["source_turn_index"] <= end:
                continue
            candidate, derived = by_parent[d_id]
            expected = copy.deepcopy(descendant)
            positions = [i for i, msg in enumerate(expected["messages"]) if msg["role"] == "assistant"
                         and msg["tool_calls"] == original["expected_action"]["tool_calls"]]
            assert len(positions) == 1
            pos = positions[0]
            expected["messages"][pos]["tool_calls"] = copy.deepcopy(draft["proposed_action"]["tool_calls"])
            expected["example_id"] = canonical({k: v for k, v in expected.items() if k not in ("example_id", "group_id", "split")})
            assert expected == candidate
            observation_positions = {i for i, msg in enumerate(candidate["messages"]) if i > pos and msg["role"] == "tool"}
            assert observation_positions == {o["message_index"] for o in derived["inherited_observations"]}
            assert all(o["status"] == "UNVERIFIED_AFTER_ACTION_CHANGE" and o["executed_here"] is False
                       and o["original_message_sha256"] == canonical(descendant["messages"][o["message_index"]])
                       for o in derived["inherited_observations"])
    assert all(s["enters_effective_training"] is False and s["semantic_verdict"] is None
               and s["external_execution"] == "NOT_RUN" and s["downstream_condition_verified"] is False for s in annotations)
    binding = read(first / "training-binding.json")
    assert binding["training_authorized"] is False and binding["staged_annotations_enter_training"] is False
    assert binding["selection_manifest_sha256"] == digest(first / "selection/manifest.json")
    assert binding["parent_training_config_file_sha256"] == digest(paths["training_config_path"])
    result = {"status": "PASS_WORKER_STDLIB_CROSSCHECK", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "quality_revision_sha256": left["quality_revision_sha256"], "counts": left["counts"],
              "stable_files_per_build": len(left["artifacts"]) + 1, "two_actual_builds_identical": True,
              "stable_manifest_sha256": digest(first / "manifest.json"), "run_created_at_utc": [r["created_at_utc"] for r in runs],
              "unchanged_other_sources_in_affected_groups": len(same_group_kept), "staged_direct": 2, "staged_dependent": 1,
              "quarantine_all_source_decisions": 40, "effective_example_bytes_preserved": 7709,
              "training_authorized": False, "semantic_acceptance": "PENDING_INDEPENDENT_REVIEW"}
    with Path(args.output).open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "first", "second", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    check(parser.parse_args())
