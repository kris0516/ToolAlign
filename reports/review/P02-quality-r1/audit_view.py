"""Independent standard-library derivation of the frozen quality revision.

No ToolAlign producer, tokenizer or model is imported. Final-split content is
only hashed as part of bound bundles; only train/validation targets are parsed.
"""

import argparse
import copy
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

IDENTITY = ("example_id", "source", "source_revision", "source_record_hash", "group_id", "split")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return sha(encoded(value))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    raw = Path(path).read_bytes().splitlines(keepends=True)
    assert all(line.endswith(b"\n") for line in raw)
    return [json.loads(line) for line in raw], raw


def rank(ident):
    return canonical(["toolalign.training-selection.v1", 42, ident]), ident


def bundle(root, manifest):
    for name, info in manifest["artifacts"].items():
        path = Path(root) / name
        assert not path.is_symlink() and path.resolve().is_relative_to(Path(root).resolve())
        assert digest(path) == (info if isinstance(info, str) else info["sha256"])
        if isinstance(info, dict):
            assert path.stat().st_size == info.get("bytes", info.get("size_bytes"))


def features(example):
    return {"multiple_tools": len(example["tools"]) > 1,
            "multiple_target_calls": len(example["expected_action"]["tool_calls"]) > 1,
            "observation_history": any(m["role"] == "tool" for m in example["messages"]),
            "multiple_messages": len(example["messages"]) > 1,
            "non_ascii": not encoded(example).decode().isascii()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "first", "second", "original", "output", "case-plan"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    paths = load(args.inputs)
    config = load(paths["config_path"])
    assert digest(paths["config_path"]) == "ddc7902386c5f00032ec938c8baa7f2f338b9d88c260ed0803e00e797feb83ce"
    pins = config["input_bindings"]
    source_root = Path(paths["data_manifest_path"]).parent
    parent_root = Path(paths["selection_manifest_path"]).parent
    review_root = Path(paths["review_root"])
    source_manifest, parent_manifest = load(paths["data_manifest_path"]), load(paths["selection_manifest_path"])
    assert digest(paths["data_manifest_path"]) == pins["data_manifest_file_sha256"]
    assert canonical(source_manifest) == pins["data_manifest_canonical_sha256"]
    assert digest(paths["selection_manifest_path"]) == pins["parent_selection_manifest_file_sha256"]
    bundle(source_root, source_manifest)
    bundle(parent_root, parent_manifest)
    binding_paths = {"train_sha256": source_root / "train.jsonl", "validation_sha256": source_root / "validation.jsonl",
                     "assignments_sha256": source_root / "assignments.jsonl", "lineage_sha256": source_root / "lineage.jsonl",
                     "raw_source_sha256": Path(paths["raw_source_path"]), "review_seal_sha256": review_root / "seal.json",
                     "semantic_review_sha256": review_root / "semantic_review_ai.csv",
                     "token_review_sha256": review_root / "token_mask_review_ai.csv",
                     "remediation_proposal_sha256": review_root / "remediation_proposal.json",
                     "provenance_sha256": review_root / "provenance.md",
                     "reannotation_drafts_sha256": review_root / "reannotation_drafts.json",
                     "parent_training_config_file_sha256": Path(paths["training_config_path"]),
                     "parent_representation_rows_sha256": Path(paths["audit_path"])}
    assert all(digest(path) == pins[key] for key, path in binding_paths.items())
    bundle(review_root, load(review_root / "seal.json"))
    originals, raw_lines, split_ids = {}, {}, {}
    for split in ("train", "validation"):
        values, lines = rows(source_root / (split + ".jsonl"))
        split_ids[split] = [e["example_id"] for e in values]
        assert len(split_ids[split]) == len(set(split_ids[split]))
        for example, line in zip(values, lines, strict=True):
            ident = example["example_id"]
            assert example["split"] == split and ident not in originals
            assert canonical({k: v for k, v in example.items() if k not in ("example_id", "group_id", "split")}) == ident
            originals[ident], raw_lines[ident] = example, line
    assignments = {a["source_index"]: a for a in rows(source_root / "assignments.jsonl")[0]}
    lineage = {r["example_id"]: r for r in rows(source_root / "lineage.jsonl")[0]
               if r["split"] in split_ids and r["exclusion_reason"] is None}
    assert set(lineage) == set(originals)
    members = defaultdict(list)
    for ident, example in originals.items():
        members[example["source_record_hash"]].append(ident)
        assert all(lineage[ident][k] == example[k] for k in ("example_id", "source_record_hash", "group_id", "split"))
    with (review_root / "semantic_review_ai.csv").open(newline="") as stream:
        semantic = list(csv.DictReader(stream))
    with (review_root / "token_mask_review_ai.csv").open(newline="") as stream:
        tokens = list(csv.DictReader(stream))
    old_cases = {p.stem: load(p) for p in Path(paths["token_review_root"]).glob("*.json")
                 if p.stem.startswith(("actual-", "protocol-"))}
    assert len(semantic) == 100 and len(tokens) == len(old_cases) == 13
    expected_issues = {}
    final_metadata = 0
    for row in semantic:
        assignment = assignments[int(row["source_index"])]
        assert row["source_record_hash"] == assignment["source_record_hash"]
        assert "split:" + assignment["split"] in row["strata"].split(";")
        if assignment["split"] not in split_ids:
            final_metadata += 1
            continue
        assert set(row["example_ids"].split(";")) == set(members[row["source_record_hash"]])
        if row["verdict"] in ("fail", "unknown"):
            expected_issues[("semantic_100", int(row["source_index"]))] = row
    for row in tokens:
        old = old_cases[row["case_id"]]["case"]
        assert row["category"] == old["category"]
        if old["category"] == "actual_selected_train":
            assert originals[old["example"]["example_id"]] == old["example"]
            if row["verdict"] in ("fail", "unknown"):
                expected_issues[("token_13", row["case_id"])] = row
    proposal = load(review_root / "remediation_proposal.json")
    issues, joined = {}, set()
    for issue in proposal["issues"]:
        origin = issue["origin"]
        key = (origin, issue["source_index"] if origin == "semantic_100" else issue["case_id"])
        row = expected_issues[key]
        assert key not in joined and issue["source_record_hash"] not in issues
        joined.add(key)
        assert issue["verdict"] == row["verdict"] and issue["notes"] and issue["notes"] in row["notes"]
        assignment = assignments[issue["source_index"]]
        assert issue["split"] in split_ids and issue["split"] == assignment["split"]
        assert issue["source_record_hash"] == assignment["source_record_hash"]
        assert set(issue["all_sample_example_ids"]) == set(members[issue["source_record_hash"]])
        affected = set(issue["affected_target_example_ids"])
        assert affected and affected <= set(issue["all_sample_example_ids"])
        if origin == "semantic_100":
            assert set(issue["affected_source_turns"]) == {lineage[i]["source_turn_index"] for i in affected}
        else:
            assert affected == {old_cases[issue["case_id"]]["case"]["example"]["example_id"]}
        issues[issue["source_record_hash"]] = issue
    assert joined == set(expected_issues)
    assert Counter(i["verdict"] for i in issues.values()) == {"fail": 20, "unknown": 12}
    roots = [args.first, args.second, args.original / "revision-a", args.original / "revision-b"]
    manifest = load(roots[0] / "manifest.json")
    stable_names = set(manifest["artifacts"]) | {"manifest.json"}
    assert len(stable_names) == 24
    for root in roots:
        assert load(root / "manifest.json") == manifest
        bundle(root, manifest)
        assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == stable_names | {"run.json"}
        assert all((root / n).read_bytes() == (roots[0] / n).read_bytes() for n in stable_names)
    revision = manifest["quality_revision_sha256"]
    assert canonical(manifest["quality_revision"]) == revision
    assert all(manifest["input_binding"][key] == value for key, value in pins.items())
    assert manifest["input_binding"]["original_data_artifacts"] == source_manifest["artifacts"]
    assert manifest["input_binding"]["parent_selection_artifacts"] == parent_manifest["artifacts"]
    assert manifest["input_binding"]["parent_selection_input_binding"] == parent_manifest["input_binding"]
    assert manifest["input_binding"]["historical_measurement"] == parent_manifest["input_binding"]["historical_measurement"]
    assert manifest["input_binding"]["review_summary"]["final_metadata_only"] == final_metadata
    kept, excluded, counts = {}, [], {}
    for split, ids in split_ids.items():
        kept[split] = [i for i in ids if originals[i]["source_record_hash"] not in issues]
        removed = [i for i in ids if originals[i]["source_record_hash"] in issues]
        excluded.extend(removed)
        assert (roots[0] / "effective" / (split + ".jsonl")).read_bytes() == b"".join(raw_lines[i] for i in kept[split])
        verdicts = Counter(issues[originals[i]["source_record_hash"]]["verdict"] for i in removed)
        counts[split] = {"original": len(ids), "effective": len(kept[split]),
                         "quarantined_fail": verdicts["fail"], "quarantined_unknown": verdicts["unknown"]}
    assert load(roots[0] / "effective/identities.json") == kept
    assert (roots[0] / "quarantine/examples.jsonl").read_bytes() == b"".join(raw_lines[i] for i in excluded)
    quarantined = rows(roots[0] / "quarantine/sidecars.jsonl")[0]
    assert [r["example_id"] for r in quarantined] == excluded
    for row in quarantined:
        ident = row["example_id"]
        issue = issues[originals[ident]["source_record_hash"]]
        assert all(row[k] == originals[ident][k] for k in IDENTITY)
        first_flagged = min(lineage[i]["source_turn_index"] for i in issue["affected_target_example_ids"])
        expected_reason = ("review_flagged_target" if ident in issue["affected_target_example_ids"]
                           else "same_source_preceding_decision" if lineage[ident]["source_turn_index"] < first_flagged
                           else "same_source_other_decision_or_prefix")
        assert row["quarantine_reason"] == expected_reason
        assert row["review_issue_sha256"] == canonical(issue)
        assert row["review_verdict"] == issue["verdict"] and row["review_origin"] == issue["origin"]
        assert row["source_turn_index"] == lineage[ident]["source_turn_index"]
        assert row["original_jsonl_line_sha256"] == sha(raw_lines[ident])
        assert row["original_example_sha256"] == canonical(originals[ident])
        assert row["original_lineage_sha256"] == canonical(lineage[ident])
        assert row["decision_itself_semantically_rejected"] == (ident in issue["affected_target_example_ids"] and issue["verdict"] == "fail")
    source_rows = rows(roots[0] / "quarantine/sources.jsonl")[0]
    assert len(source_rows) == 32 and [r["source_index"] for r in source_rows] == sorted(i["source_index"] for i in issues.values())
    for row in source_rows:
        issue = issues[row["source_record_hash"]]
        assert row["original_example_ids"] == members[row["source_record_hash"]]
        assert row["issue_sha256"] == canonical(issue) and row["unit"] == "entire_source_all_decisions"
        assert row["group_id"] == assignments[row["source_index"]]["group_id"]
    retained_lineage = rows(roots[0] / "effective/lineage.jsonl")[0]
    assert [r["example_id"] for r in retained_lineage] == kept["train"] + kept["validation"]
    for row in retained_lineage:
        ident = row["example_id"]
        assert all(row[k] == originals[ident][k] for k in IDENTITY)
        assert row["original_jsonl_line_sha256"] == sha(raw_lines[ident])
        assert row["original_example_sha256"] == canonical(originals[ident])
        assert row["original_lineage_sha256"] == canonical(lineage[ident])
        assert row["disposition"] == "retained_original_bytes"
    selection = {}
    for profile in ("smoke", "formal"):
        for split in split_ids:
            prefix = profile + "/" + split
            values, lines = rows(parent_root / (prefix + ".examples.jsonl"))
            old_sidecars = rows(parent_root / (prefix + ".sidecars.jsonl"))[0]
            ids = [e["example_id"] for e in values]
            assert ids == sorted(ids, key=rank) and len(ids) == len(set(ids))
            selected = [(i, e, line, sidecar) for i, (e, line, sidecar) in enumerate(zip(values, lines, old_sidecars, strict=True), 1)
                        if e["source_record_hash"] not in issues]
            expected_raw = b"".join(line for _, _, line, _ in selected)
            assert (roots[0] / "selection" / (prefix + ".examples.jsonl")).read_bytes() == expected_raw
            sidecars = rows(roots[0] / "selection" / (prefix + ".sidecars.jsonl"))[0]
            assert len(sidecars) == len(selected)
            for current_rank, (row, (old_rank, example, line, old)) in enumerate(zip(sidecars, selected, strict=True), 1):
                assert line == raw_lines[example["example_id"]] and example == originals[example["example_id"]]
                assert row == {**old, "selection_rank": current_rank, "parent_selection_rank": old_rank,
                               "parent_sidecar_sha256": canonical(old),
                               "parent_selection_manifest_sha256": pins["parent_selection_manifest_file_sha256"],
                               "quality_revision_sha256": revision, "sequence_basis": "inherited_unchanged_parent_measurement"}
                assert old["ranking_sha256"] == rank(example["example_id"])[0]
            removed = {verdict: [e["example_id"] for e in values if issues.get(e["source_record_hash"], {}).get("verdict") == verdict]
                       for verdict in ("fail", "unknown")}
            exclusions = load(roots[0] / "selection" / (prefix + ".excluded.json"))
            assert exclusions == {"quality_quarantined": removed, "parent_excluded_unchanged": load(parent_root / (prefix + ".excluded.json")), "refill_count": 0}
            assert proposal["quarantine_example_ids"][prefix] == {"confirmed_fail": removed["fail"], "uncertain": removed["unknown"]}
            for issue in issues.values():
                assert issue["selected_membership"][prefix] == [e["example_id"] for e in values if e["source_record_hash"] == issue["source_record_hash"]]
            counts[profile + "_" + split] = {"original": len(values), "effective": len(selected)}
            if split == "train":
                counts[profile + "_" + split].update({"quarantined_" + k: len(v) for k, v in removed.items()})
            selection[prefix] = {"examples": [e for _, e, _, _ in selected], "sidecars": sidecars}
    assert counts == config["expected_counts"] == manifest["counts"]
    groups = {originals[i]["group_id"] for i in excluded}
    same_group_kept = sum(originals[i]["group_id"] in groups for ids in kept.values() for i in ids)
    assert same_group_kept == manifest["unrelated_examples_retained_in_affected_groups"] == 5586
    staged, _ = rows(roots[0] / "staging/examples.jsonl")
    annotations, _ = rows(roots[0] / "staging/sidecars.jsonl")
    assert len(staged) == len(annotations) == 3
    assert not {e["example_id"] for e in staged} & set(originals)
    drafts = load(review_root / "reannotation_drafts.json")
    raw_source = load(paths["raw_source_path"])
    for issue in issues.values():
        assert canonical(raw_source[issue["source_index"]]) == issue["source_record_hash"]
    by_parent = {s["annotation_parent"]: (e, s) for e, s in zip(staged, annotations, strict=True)}
    expected_parents = set()
    for draft in drafts:
        parent_id = draft["original_example_id"]
        original = originals[parent_id]
        direct, sidecar = by_parent[parent_id]
        expected_parents.add(parent_id)
        expected = copy.deepcopy(original)
        expected["expected_action"] = draft["proposed_action"]
        expected["example_id"] = canonical({k: v for k, v in expected.items() if k not in ("example_id", "group_id", "split")})
        assert direct == expected and sidecar["kind"] == "direct_action_revision"
        assert canonical(original["expected_action"]) == draft["original_action_sha256"]
        source = raw_source[draft["source_index"]]
        end = lineage[parent_id]["source_turn_index"]
        expected_users = [{"source_turn_index": i, "content": turn["value"], "source_turn_sha256": canonical(turn)}
                          for i, turn in enumerate(source["conversations"][:end]) if turn["from"] == "user"]
        assert sidecar["source_evidence"]["user_evidence"] == expected_users
        assert sidecar["source_evidence"]["original_tools_sha256"] == canonical(original["tools"])
        assert sidecar["source_evidence"]["raw_action_text_sha256"] == sha(source["conversations"][end]["value"].encode())
        changes = []
        for i, (old_call, new_call) in enumerate(zip(original["expected_action"]["tool_calls"], direct["expected_action"]["tool_calls"], strict=True)):
            assert old_call["call_id"] == new_call["call_id"] and old_call["name"] == new_call["name"]
            for key in sorted(set(old_call["arguments"]) | set(new_call["arguments"])):
                before, after = old_call["arguments"], new_call["arguments"]
                if (key in before) != (key in after) or before.get(key) != after.get(key):
                    changes.append({"call_index": i, "parameter": key, "before_exists": key in before,
                                    "before": before.get(key), "after_exists": key in after, "after": after.get(key)})
        assert len(changes) == 1 and sidecar["listed_argument_changes"] == changes
        for ident in members[original["source_record_hash"]]:
            if lineage[ident]["source_turn_index"] <= end:
                continue
            expected_parents.add(ident)
            candidate, annotation = by_parent[ident]
            successor = originals[ident]
            expected = copy.deepcopy(successor)
            positions = [i for i, message in enumerate(expected["messages"])
                         if message["role"] == "assistant" and message["tool_calls"] == original["expected_action"]["tool_calls"]
                         and message["content"] == original["expected_action"]["content"]]
            assert len(positions) == 1
            pos = positions[0]
            expected["messages"][pos]["tool_calls"] = direct["expected_action"]["tool_calls"]
            expected["example_id"] = canonical({k: v for k, v in expected.items() if k not in ("example_id", "group_id", "split")})
            assert candidate == expected
            observations = [{"message_index": i, "tool_call_id": message["tool_call_id"],
                             "original_message_sha256": canonical(message), "status": "UNVERIFIED_AFTER_ACTION_CHANGE", "executed_here": False}
                            for i, message in enumerate(successor["messages"]) if i > pos and message["role"] == "tool"]
            assert observations and annotation["inherited_observations"] == observations
    assert expected_parents == set(by_parent)
    for example, annotation in zip(staged, annotations, strict=True):
        parent = originals[annotation["annotation_parent"]]
        assert all(example[k] == parent[k] for k in ("source", "source_revision", "source_record_hash", "license_id", "group_id", "split"))
        assert annotation["example_sha256"] == canonical(example)
        assert annotation["parent_example_sha256"] == canonical(parent)
        assert annotation["parent_lineage_sha256"] == canonical(lineage[parent["example_id"]])
        assert annotation["quality_revision_sha256"] == revision
        assert annotation["status"] == "STAGED_PENDING_INDEPENDENT_REVIEW"
        assert annotation["semantic_verdict"] is None and annotation["enters_effective_training"] is False
        assert annotation["external_execution"] == "NOT_RUN" and annotation["downstream_condition_verified"] is False
    binding = load(roots[0] / "training-binding.json")
    selection_manifest = load(roots[0] / "selection/manifest.json")
    assert binding["selection_manifest_sha256"] == digest(roots[0] / "selection/manifest.json")
    assert binding["profiles"] == load(paths["training_config_path"])["profiles"]
    assert binding["staged_annotations_enter_training"] is False
    for document in (manifest, binding, selection_manifest):
        assert document["training_authorized"] is False and document["quality_revision_sha256"] == revision
    union = {}
    for profile in ("smoke", "formal"):
        for example, sidecar in zip(selection[profile + "/train"]["examples"], selection[profile + "/train"]["sidecars"], strict=True):
            ident = example["example_id"]
            entry = union.setdefault(ident, {"example": example, "audit": sidecar["audit"], "profiles": {}, "features": features(example)})
            entry["profiles"][profile] = {k: sidecar[k] for k in ("padding_bucket", "selection_rank", "parent_selection_rank")}
    ordered = sorted(union, key=rank)
    ordered_rules = [(min(ordered, key=lambda i: (union[i]["audit"]["total_tokens"], rank(i))), "shortest_selected"),
                     (min(ordered, key=lambda i: (-union[i]["audit"]["total_tokens"], rank(i))), "longest_selected"),
                     (min((i for i in ordered if "smoke" in union[i]["profiles"]), key=lambda i: (-union[i]["audit"]["total_tokens"], rank(i))), "longest_smoke")]
    for feature in features(union[ordered[0]]["example"]):
        eligible = [i for i in ordered if union[i]["features"][feature]]
        if eligible:
            ordered_rules.append((eligible[0], feature))
    reasons = {}
    for ident, reason in ordered_rules:
        reasons.setdefault(ident, []).append(reason)
    for ident in ordered:
        if len(reasons) == 10:
            break
        if ident not in reasons:
            reasons[ident] = ["ranking_fill"]
    old_ids = {r["case"]["example"]["example_id"]: name for name, r in old_cases.items()}
    planned = {}
    for i, (ident, why) in enumerate(reasons.items(), 1):
        planned[f"effective-{i:02d}"] = {**union[ident], "selection_reasons": why,
                                          "primary_profile": "smoke" if "smoke" in union[ident]["profiles"] else "formal",
                                          "previous_material_case_id": old_ids.get(ident),
                                          "original_jsonl_line_sha256": sha(raw_lines[ident]),
                                          "original_lineage_sha256": canonical(lineage[ident])}
    for name in sorted(n for n in old_cases if n.startswith("protocol-")):
        planned[name] = {"example": old_cases[name]["case"]["example"], "primary_profile": "smoke"}
    counters = Counter()
    for example, annotation in zip(staged, annotations, strict=True):
        kind = "direct" if annotation["kind"] == "direct_action_revision" else "dependent"
        counters[kind] += 1
        planned[f"staged-{kind}-{counters[kind]:02d}"] = {"example": example, "annotation": annotation, "primary_profile": "formal"}
    assert len(planned) == len({v["example"]["example_id"] for v in planned.values()}) == 16
    for directory in (args.original / "review-reference", args.original / "review-native"):
        for name, expected in planned.items():
            actual = load(directory / (name + ".json"))["case"]
            assert all(actual[k] == v for k, v in expected.items()), name
    plan = {"quality_revision_sha256": revision, "revision_manifest_sha256": digest(roots[0] / "manifest.json"),
            "case_order": list(planned), "cases": planned, "unique_cases_per_engine": 16,
            "training_authorized": False, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    with args.case_plan.open("x") as stream:
        json.dump(plan, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    result = {"status": "PASS_INDEPENDENT_SOURCE_SELECTION_STAGING", "counts": counts,
              "source_counts": dict(Counter(i["verdict"] for i in issues.values())),
              "quarantine_decisions": len(excluded), "stable_files_per_build": 24,
              "four_builds_equal": True, "quality_revision_sha256": revision,
              "manifest_sha256": digest(roots[0] / "manifest.json"), "same_group_others_retained": same_group_kept,
              "source_issue_sha256": canonical(issues), "effective_ids_sha256": canonical(kept),
              "ranked_selection_ids_sha256": {k: canonical([e["example_id"] for e in v["examples"]]) for k, v in selection.items()},
              "staged_identities_sha256": canonical([e["example_id"] for e in staged]),
              "new_case_plan_sha256": digest(args.case_plan), "planned_cases_per_engine": 16,
              "final_split_metadata_only_rows": final_metadata, "new_token_encoding": 0,
              "run_times": [load(root / "run.json")["created_at_utc"] for root in roots], "training_authorized": False}
    assert len(set(result["run_times"])) == 4
    with args.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
