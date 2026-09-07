"""CPU revision of a frozen data build after a separately authorized AI review.

Build/verify pin the actual input buffers. The pure kernels below are useful for
small original tests; they do not accept a new policy or authorize training.
Unchanged records retain their original JSONL bytes. Draft annotations and their
dependent prefixes remain staged, with no claim of externally executed results.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import os
import platform
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash, contract_digest, validate_record

from .common import MAX_INPUT_BYTES, DataError, encoded, loads
from .source_policy import POLICY_SHA256, SourcePolicy
from .toolace import extract_tools, inspect_record
from .training_selection import rank_key
from .training_selection import validate_config as validate_parent_config

CONFIG_SHA256 = "ddc7902386c5f00032ec938c8baa7f2f338b9d88c260ed0803e00e797feb83ce"
SPLITS = ("train", "validation")
PROFILES = ("smoke", "formal")
REVIEWER = "Codex-AI (delegated by kris; not human)"
IDENTITY = ("example_id", "source", "source_revision", "source_record_hash", "group_id", "split")
MODEL_ROOTS = {"torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax"}


def require(condition, code):
    if not condition:
        raise DataError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(path, expected):
    """Use the same verified buffer for parsing, never a second unbound read."""
    path = Path(path)
    require(path.stat().st_size <= MAX_INPUT_BYTES, "input_byte_budget")
    data = path.read_bytes()
    require(len(data) <= MAX_INPUT_BYTES and sha(data) == expected, "input_hash_mismatch")
    return data


def load_config(path):
    return loads(pinned(path, CONFIG_SHA256).decode("utf-8"))


def child_path(root, name):
    relative = Path(name)
    require(type(name) is str and not relative.is_absolute() and ".." not in relative.parts
            and "\\" not in name and bool(relative.parts), "artifact_path_escape")
    path = Path(root) / relative
    require(not path.is_symlink() and path.resolve().is_relative_to(Path(root).resolve()),
            "artifact_path_escape")
    return path


def checked_bundle(root, artifacts, keep):
    result = {}
    for name, value in artifacts.items():
        digest = value if type(value) is str else value["sha256"]
        data = pinned(child_path(root, name), digest)
        if type(value) is dict:
            size = value.get("size_bytes", value.get("bytes"))
            require(type(size) is int and len(data) == size, "artifact_size_mismatch")
        if name in keep:
            result[name] = data
    require(set(result) == set(keep), "missing_input_artifact")
    return result


def jsonl(data):
    rows, raw = [], []
    for line in data.splitlines(keepends=True):
        require(line.endswith(b"\n") and len(line) <= 2 * 1024 * 1024, "invalid_jsonl_line")
        rows.append(loads(line.decode("utf-8")))
        raw.append(line)
    return rows, raw


def normalized_id(example):
    return canonical_hash({k: v for k, v in example.items()
                           if k not in {"example_id", "group_id", "split"}})


def original_index(examples_by_split, assignments, lineage):
    """Index retained train/validation only; excluded lineage is not new data."""
    require(set(examples_by_split) == set(SPLITS), "only_train_validation_inputs")
    by_index, by_source, group_splits = {}, {}, {}
    for assignment in assignments:
        index = assignment["source_index"]
        require(type(index) is int and index >= 0 and index not in by_index, "source_index_identity")
        split, group = assignment["split"], assignment["group_id"]
        require(split in (*SPLITS, "test", "ood_test"), "assignment_split")
        require(group_splits.get(group, split) == split, "group_split_leakage")
        group_splits[group] = split
        source = assignment["source_record_hash"]
        if source in by_source:
            require(all(by_source[source][k] == assignment[k] for k in ("split", "group_id")),
                    "source_split_leakage")
        by_index[index], by_source[source] = copy.deepcopy(assignment), copy.deepcopy(assignment)
    included = {}
    for row in lineage:
        # Final splits and originally excluded rows contribute no target content.
        if row["split"] not in SPLITS or row["exclusion_reason"] is not None:
            continue
        ident = row["example_id"]
        require(ident not in included, "duplicate_retained_lineage")
        included[ident] = copy.deepcopy(row)
    examples = {}
    for split, values in examples_by_split.items():
        for example in values:
            require(example.get("split") == split, "example_split_mismatch")
            ident = example["example_id"]
            require(ident not in examples and ident == normalized_id(example), "example_identity")
            validate_record(example, "example")
            require(ident in included and example["source_record_hash"] in by_source, "missing_lineage")
            row, assignment = included[ident], by_source[example["source_record_hash"]]
            require(all(row[k] == example[k] for k in ("example_id", "source_record_hash", "group_id", "split"))
                    and all(assignment[k] == example[k] for k in ("source_record_hash", "group_id", "split")),
                    "source_example_lineage_mismatch")
            require(row["normalized_hash"] == ident
                    and type(row["source_turn_index"]) is int and row["source_turn_index"] >= 0,
                    "lineage_decision_identity")
            examples[ident] = copy.deepcopy(example)
    require(set(examples) == set(included), "retained_lineage_set_mismatch")
    return {"examples": examples, "lineage": included, "assignments": by_index}


def csv_rows(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""))
    header = reader.fieldnames
    require(header and len(header) == len(set(header)), "csv_header")
    rows = list(reader)
    require(all(set(row) == set(header) and all(type(v) is str for v in row.values())
                for row in rows), "csv_shape")
    return rows


def reviewed_csv(original, reviewed, identity_columns):
    require(len(original) == len(reviewed), "review_count_mismatch")
    seen = set()
    for old, new in zip(original, reviewed, strict=True):
        require(set(old) == set(new), "review_columns_mismatch")
        key = tuple(new[k] for k in identity_columns)
        require(key not in seen and all(old[k] == new[k] for k in identity_columns),
                "review_identity_mismatch")
        seen.add(key)
        require(not any(old[k] for k in old if k not in identity_columns), "original_review_not_blank")
        require(new["reviewer"] == REVIEWER and new["verdict"] in {"pass", "fail", "unknown"}
                and bool(new["notes"]), "reviewer_or_verdict_mismatch")
        when = datetime.fromisoformat(new["reviewed_at_utc"])
        require(when.utcoffset() is not None and when.utcoffset().total_seconds() == 0,
                "review_timestamp_not_utc")


def review_issues(index, semantic, token_rows, token_cases, proposal):
    """Join every review identity before using an in-scope disposition."""
    examples, assignments = index["examples"], index["assignments"]
    lineage = index["lineage"]
    members = defaultdict(set)
    for example in examples.values():
        members[example["source_record_hash"]].add(example["example_id"])
    expected, final_metadata = {}, 0
    for row in semantic:
        source_index = int(row["source_index"])
        require(source_index in assignments, "review_source_index")
        assignment = assignments[source_index]
        splits = [v.removeprefix("split:") for v in row["strata"].split(";") if v.startswith("split:")]
        require(splits == [assignment["split"]] and row["source_record_hash"] == assignment["source_record_hash"],
                "review_source_identity")
        if assignment["split"] not in SPLITS:
            final_metadata += 1
            continue
        ids = row["example_ids"].split(";")
        require(len(ids) == len(set(ids)) and set(ids) == members[assignment["source_record_hash"]],
                "review_example_identity")
        if row["verdict"] in {"fail", "unknown"}:
            expected[("semantic_100", source_index)] = row
    require(set(token_cases) == {r["case_id"] for r in token_rows}, "token_case_set")
    for row in token_rows:
        case = token_cases[row["case_id"]]["case"]
        require(case["case_id"] == row["case_id"] and case["category"] == row["category"], "token_case_identity")
        if row["category"] == "original_protocol_only":
            continue
        value = case["example"]
        require(row["category"] == "actual_selected_train" and value["split"] == "train"
                and examples.get(value["example_id"]) == value, "token_example_identity")
        if row["verdict"] in {"fail", "unknown"}:
            expected[("token_13", row["case_id"])] = row
    require(proposal["status"] == "PROPOSED_NOT_APPLIED"
            and proposal["review_kind"] == "delegated_ai_not_human"
            and proposal["no_final_test_based_training_changes"] is True, "proposal_scope")
    issues, seen = {}, set()
    for issue in proposal["issues"]:
        origin, source_index = issue["origin"], issue["source_index"]
        require(type(source_index) is int and source_index in assignments, "proposal_source_index")
        assignment = assignments[source_index]
        require(issue["split"] in SPLITS and issue["split"] == assignment["split"]
                and issue["source_record_hash"] == assignment["source_record_hash"], "proposal_source_identity")
        key = (origin, source_index if origin == "semantic_100" else issue.get("case_id"))
        require(key in expected and key not in seen, "proposal_review_identity")
        seen.add(key)
        row = expected[key]
        # The sealed CSV wraps the proposal's verbatim reason in attribution and
        # structural-check context; the two complete files are pinned separately.
        require(issue["verdict"] == row["verdict"] and bool(issue["notes"])
                and issue["notes"] in row["notes"], "proposal_verdict_binding")
        source = issue["source_record_hash"]
        require(source not in issues, "duplicate_issue_source")
        ids = issue["all_sample_example_ids"]
        affected = issue["affected_target_example_ids"]
        require(len(ids) == len(set(ids)) and set(ids) == members[source]
                and bool(affected) and len(affected) == len(set(affected)) and set(affected) <= set(ids),
                "proposal_example_identity")
        if origin == "semantic_100":
            require(set(ids) == set(row["example_ids"].split(";")), "proposal_sample_identity")
            require(set(issue["affected_source_turns"]) == {lineage[i]["source_turn_index"] for i in affected},
                    "proposal_turn_identity")
        else:
            value = token_cases[issue["case_id"]]["case"]["example"]
            require(value["source_record_hash"] == source and affected == [value["example_id"]],
                    "proposal_token_identity")
        issues[source] = copy.deepcopy(issue)
    require(seen == set(expected), "proposal_missing_review_issue")
    return issues, {"semantic_rows": len(semantic), "token_rows": len(token_rows),
                    "final_metadata_only": final_metadata, "review_kind": "kris_delegated_ai_not_human"}


def revise_view(index, issues):
    examples, lineage = index["examples"], index["lineage"]
    retained, quarantined, sources = {s: [] for s in SPLITS}, [], []
    for source, issue in issues.items():
        require(issue["source_record_hash"] == source and issue["verdict"] in {"fail", "unknown"}
                and issue["split"] in SPLITS, "quarantine_scope")
        assignment = index["assignments"].get(issue["source_index"])
        require(assignment is not None and all(issue[k] == assignment[k] for k in ("source_record_hash", "split")),
                "quarantine_source_identity")
        members = [e for e in examples.values() if e["source_record_hash"] == source]
        require(members and set(issue["all_sample_example_ids"]) == {e["example_id"] for e in members},
                "quarantine_source_members")
        sources.append({"source_index": issue["source_index"], "source_record_hash": source,
                        "group_id": assignment["group_id"], "split": assignment["split"],
                        "verdict": issue["verdict"], "issue_sha256": canonical_hash(issue),
                        "original_example_ids": [e["example_id"] for e in members],
                        "unit": "entire_source_all_decisions"})
    for ident, value in examples.items():
        source = value["source_record_hash"]
        if source not in issues:
            retained[value["split"]].append(ident)
            continue
        issue, row = issues[source], lineage[ident]
        affected = set(issue["affected_target_example_ids"])
        turns = [lineage[i]["source_turn_index"] for i in affected]
        reason = ("review_flagged_target" if ident in affected else "same_source_preceding_decision"
                  if row["source_turn_index"] < min(turns) else "same_source_other_decision_or_prefix")
        quarantined.append({**{k: value[k] for k in IDENTITY},
            "source_index": issue["source_index"], "source_turn_index": row["source_turn_index"],
            "original_example_sha256": canonical_hash(value), "original_lineage_sha256": canonical_hash(row),
            "review_verdict": issue["verdict"], "review_origin": issue["origin"],
            "review_issue_sha256": canonical_hash(issue), "quarantine_reason": reason,
            "decision_itself_semantically_rejected": ident in affected and issue["verdict"] == "fail"})
    return {"retained": retained, "quarantined": quarantined,
            "sources": sorted(sources, key=lambda x: x["source_index"])}


def filter_selection(index, parents, issues, revision_sha256, parent_manifest_sha256):
    """Filter only the already selected records; retain each original rank."""
    require(set(parents) == set(PROFILES), "parent_profiles")
    result = {}
    for profile in PROFILES:
        require(set(parents[profile]) == set(SPLITS), "parent_splits")
        result[profile] = {}
        for split in SPLITS:
            parent = parents[profile][split]
            values, sidecars = parent["examples"], parent["sidecars"]
            require(len(values) == len(sidecars), "parent_sidecar_count")
            ids = [e["example_id"] for e in values]
            require(len(ids) == len(set(ids)) and ids == sorted(ids, key=rank_key), "parent_rank_order")
            kept, kept_sidecars, removed = [], [], {"fail": [], "unknown": []}
            for rank, (example, sidecar) in enumerate(zip(values, sidecars, strict=True), 1):
                ident = example["example_id"]
                require(example.get("split") == split and index["examples"].get(ident) == example,
                        "selected_example_identity")
                require(type(sidecar["selection_rank"]) is int and sidecar["selection_rank"] == rank
                        and sidecar["ranking_sha256"] == rank_key(ident)[0]
                        and sidecar["profile"] == profile and sidecar["split"] == split
                        and sidecar["audit"]["example_sha256"] == canonical_hash(example)
                        and all(sidecar["audit"][k] == example[k] for k in IDENTITY), "selected_sidecar_identity")
                source = example["source_record_hash"]
                if source in issues:
                    removed[issues[source]["verdict"]].append(ident)
                    continue
                kept.append(copy.deepcopy(example))
                kept_sidecars.append({**copy.deepcopy(sidecar), "selection_rank": len(kept),
                    "parent_selection_rank": rank, "parent_sidecar_sha256": canonical_hash(sidecar),
                    "parent_selection_manifest_sha256": parent_manifest_sha256,
                    "quality_revision_sha256": revision_sha256,
                    "sequence_basis": "inherited_unchanged_parent_measurement"})
            result[profile][split] = {"examples": kept, "sidecars": kept_sidecars, "removed": removed,
                "parent_summary": copy.deepcopy(parent["summary"]),
                "parent_excluded": copy.deepcopy(parent["excluded"]),
                "summary": {"parent_selected_count": len(values), "effective_selected_count": len(kept),
                    "quarantined_counts": {k: len(v) for k, v in removed.items()},
                    "selected_identity_sha256": canonical_hash([e["example_id"] for e in kept]),
                    "refill_count": 0}}
    for split in SPLITS:
        require({e["example_id"] for e in result["smoke"][split]["examples"]}
                <= {e["example_id"] for e in result["formal"][split]["examples"]}, "smoke_not_subset")
    return result


def argument_changes(before, after):
    require(before["kind"] == after["kind"] == "tool_calls" and before["content"] == after["content"]
            and len(before["tool_calls"]) == len(after["tool_calls"]), "annotation_action_scope")
    changes = []
    for i, (old, new) in enumerate(zip(before["tool_calls"], after["tool_calls"], strict=True)):
        require(set(old) == set(new) == {"call_id", "name", "arguments"}
                and all(old[k] == new[k] for k in ("call_id", "name")), "annotation_call_identity")
        for key in sorted(set(old["arguments"]) | set(new["arguments"])):
            a, b = old["arguments"], new["arguments"]
            if key not in a or key not in b or canonical_hash(a[key]) != canonical_hash(b[key]):
                changes.append({"call_index": i, "parameter": key,
                    "before_exists": key in a, "before": a.get(key),
                    "after_exists": key in b, "after": b.get(key)})
    require(len(changes) == 1 and changes[0]["after_exists"], "annotation_requires_one_listed_change")
    return changes


def stage_annotations(index, issues, drafts, source_evidence, revision_sha256):
    """Apply the pinned draft Action only; inherited observations never gain PASS."""
    examples, lineage = index["examples"], index["lineage"]
    staged, sidecars, seen_sources = [], [], set()
    for draft in drafts:
        ident, source = draft["original_example_id"], draft["source_record_hash"]
        require(draft["status"] == "DRAFT_NOT_APPLIED" and ident in examples and source in issues
                and source not in seen_sources, "annotation_scope")
        seen_sources.add(source)
        parent = examples[ident]
        require(parent["source_record_hash"] == source and parent["split"] in SPLITS
                and issues[source]["source_index"] == draft["source_index"]
                and canonical_hash(parent["expected_action"]) == draft["original_action_sha256"],
                "annotation_parent_identity")
        proof = source_evidence[ident]
        require(proof["source_record_hash"] == source and proof["original_example_sha256"] == canonical_hash(parent)
                and proof["original_tools_sha256"] == canonical_hash(parent["tools"])
                and proof["original_action_sha256"] == draft["original_action_sha256"], "annotation_source_evidence")
        changes = argument_changes(parent["expected_action"], draft["proposed_action"])
        direct = copy.deepcopy(parent)
        direct["expected_action"] = copy.deepcopy(draft["proposed_action"])
        direct["example_id"] = normalized_id(direct)
        validate_record(direct, "example")
        require(direct["example_id"] not in examples, "annotation_identity_unchanged_or_collision")
        candidates = [(direct, parent, "direct_action_revision", [])]
        prior_turn = lineage[ident]["source_turn_index"]
        for successor in sorted(examples.values(), key=lambda e: (lineage[e["example_id"]]["source_turn_index"], e["example_id"])):
            if successor["source_record_hash"] != source or lineage[successor["example_id"]]["source_turn_index"] <= prior_turn:
                continue
            positions = [i for i, m in enumerate(successor["messages"])
                         if m["role"] == "assistant" and m["tool_calls"] == parent["expected_action"]["tool_calls"]
                         and m["content"] == parent["expected_action"]["content"]]
            require(len(positions) == 1, "dependent_prefix_parent_missing")
            position = positions[0]
            candidate = copy.deepcopy(successor)
            candidate["messages"][position]["tool_calls"] = copy.deepcopy(direct["expected_action"]["tool_calls"])
            observations = [{"message_index": i, "tool_call_id": m["tool_call_id"],
                             "original_message_sha256": canonical_hash(m),
                             "status": "UNVERIFIED_AFTER_ACTION_CHANGE", "executed_here": False}
                            for i, m in enumerate(candidate["messages"]) if i > position and m["role"] == "tool"]
            require(bool(observations), "dependent_prefix_missing_observation")
            candidate["example_id"] = normalized_id(candidate)
            validate_record(candidate, "example")
            candidates.append((candidate, successor, "dependent_prefix_revision", observations))
        for candidate, original, kind, observations in candidates:
            require(candidate["example_id"] not in examples
                    and candidate["example_id"] not in {e["example_id"] for e in staged}, "staged_identity_collision")
            require(all(candidate[k] == original[k] for k in ("source", "source_revision", "source_record_hash", "license_id", "group_id", "split")),
                    "annotation_upstream_identity_changed")
            staged.append(candidate)
            sidecars.append({"annotation_version": "toolalign.quality-annotation.v1", "kind": kind,
                "example_id": candidate["example_id"], "example_sha256": canonical_hash(candidate),
                "annotation_parent": original["example_id"], "parent_example_sha256": canonical_hash(original),
                "parent_lineage_sha256": canonical_hash(lineage[original["example_id"]]),
                "source_index": draft["source_index"], "source_turn_index": lineage[original["example_id"]]["source_turn_index"],
                "source_record_hash": source, "source_revision": original["source_revision"],
                "group_id": original["group_id"], "split": original["split"],
                "direct_annotation_parent": ident, "direct_candidate_id": direct["example_id"],
                "original_action_sha256": canonical_hash(original["expected_action"]),
                "candidate_action_sha256": canonical_hash(candidate["expected_action"]),
                "candidate_model_input_sha256": canonical_hash({k: candidate[k] for k in ("messages", "tools")}),
                "quality_revision_sha256": revision_sha256, "draft_sha256": canonical_hash(draft),
                "listed_argument_changes": changes, "reason": draft["reason"],
                "annotation_author": "D1 applying the frozen delegated-AI draft", "source_evidence": proof,
                "status": "STAGED_PENDING_INDEPENDENT_REVIEW", "semantic_verdict": None,
                "inherited_observations": observations, "external_execution": "NOT_RUN",
                "downstream_condition_verified": False, "enters_effective_training": False})
    return {"examples": staged, "sidecars": sidecars}


def annotation_source_evidence(index, drafts, raw, policy):
    proofs = {}
    for draft in drafts:
        assignment = index["assignments"][draft["source_index"]]
        require(assignment["split"] in SPLITS and assignment["source_record_hash"] == draft["source_record_hash"],
                "annotation_final_source_forbidden")
        parent = index["examples"][draft["original_example_id"]]
        source = raw[draft["source_index"]]
        require(canonical_hash(source) == draft["source_record_hash"], "raw_source_identity")
        metadata = {k: parent[k] for k in ("source", "source_revision", "license_id")}
        _, reconstructed = inspect_record(source, metadata, draft["source_index"], policy=policy)
        originals = {e["example_id"]: e for e in reconstructed}
        require(parent["example_id"] in originals, "source_parent_reconstruction")
        for original in index["examples"].values():
            if original["source_record_hash"] != draft["source_record_hash"]:
                continue
            rebuilt = originals.get(original["example_id"])
            require(rebuilt is not None, "source_successor_reconstruction")
            rebuilt = {**rebuilt, "group_id": original["group_id"], "split": original["split"]}
            require(rebuilt == original, "source_normalized_example_changed")
        end = index["lineage"][parent["example_id"]]["source_turn_index"]
        users = [{"source_turn_index": i, "content": t["value"], "source_turn_sha256": canonical_hash(t)}
                 for i, t in enumerate(source["conversations"][:end]) if t["from"] == "user"]
        require(users and [u["content"] for u in users] == [m["content"] for m in parent["messages"] if m["role"] == "user"],
                "annotation_user_source_mismatch")
        proofs[parent["example_id"]] = {"source_index": draft["source_index"],
            "source_record_hash": canonical_hash(source), "original_example_sha256": canonical_hash(parent),
            "original_tools_sha256": canonical_hash(parent["tools"]),
            "raw_tools_sha256": canonical_hash(extract_tools(source)[0]),
            "original_action_sha256": canonical_hash(parent["expected_action"]),
            "raw_action_text_sha256": sha(source["conversations"][end]["value"].encode()),
            "user_evidence": users, "source_reconstruction_exact": True,
            "support_scope": "frozen_reviewer_draft_and_original_user_schema_not_new_semantic_acceptance"}
    return proofs


def _old_token_materials(root, intake):
    declared = intake["inputs"]
    anchors = [Path(p).parent for p in declared if Path(p).name == "actual-01.json"]
    require(len(anchors) == 1, "original_token_root_identity")
    relative = {Path(p).name: info for p, info in declared.items() if Path(p).parent == anchors[0]}
    names = {f"actual-{i:02d}" for i in range(1, 11)} | {"protocol-final", "protocol-clarify", "protocol-refuse"}
    wanted = {n + ".json" for n in names} | {"review.csv", "manifest.json"}
    data = checked_bundle(root, relative, wanted)
    cases = {n: loads(data[n + ".json"].decode()) for n in names}
    return data, cases


def bound_inputs(*, config_path, data_manifest_path, selection_manifest_path, training_config_path,
                 audit_path, review_root, token_review_root, raw_source_path, source_policy_path):
    config = load_config(config_path)
    pins = config["input_bindings"]
    data_manifest = loads(pinned(data_manifest_path, pins["data_manifest_file_sha256"]).decode())
    require(canonical_hash(data_manifest) == pins["data_manifest_canonical_sha256"], "data_manifest_identity")
    data = checked_bundle(Path(data_manifest_path).resolve().parent, data_manifest["artifacts"],
                          {"train.jsonl", "validation.jsonl", "assignments.jsonl", "lineage.jsonl", "human-review/review.csv"})
    for name, key in (("train.jsonl", "train_sha256"), ("validation.jsonl", "validation_sha256"),
                      ("assignments.jsonl", "assignments_sha256"), ("lineage.jsonl", "lineage_sha256")):
        require(sha(data[name]) == pins[key], "data_artifact_binding")
    examples, original_bytes = {}, {}
    for split in SPLITS:
        values, lines = jsonl(data[split + ".jsonl"])
        examples[split] = values
        original_bytes.update({e["example_id"]: line for e, line in zip(values, lines, strict=True)})
    index = original_index(examples, jsonl(data["assignments.jsonl"])[0], jsonl(data["lineage.jsonl"])[0])
    selection_manifest = loads(pinned(selection_manifest_path, pins["parent_selection_manifest_file_sha256"]).decode())
    require(selection_manifest["manifest_version"] == "toolalign.training-selection.v1"
            and selection_manifest["training_authorized"] is False, "parent_selection_kind")
    parent_config = validate_parent_config(loads(pinned(training_config_path, pins["parent_training_config_file_sha256"]).decode()))
    require(selection_manifest["config"] == parent_config
            and selection_manifest["input_binding"]["data_manifest_sha256"] == canonical_hash(data_manifest)
            and selection_manifest["input_binding"]["data_artifacts"] == data_manifest["artifacts"], "parent_selection_binding")
    names = {f"{p}/{s}.{kind}.{ext}" for p in PROFILES for s in SPLITS
             for kind, ext in (("examples", "jsonl"), ("sidecars", "jsonl"), ("excluded", "json"))}
    require(set(selection_manifest["artifacts"]) == names, "parent_artifact_set")
    selected_data = checked_bundle(Path(selection_manifest_path).resolve().parent, selection_manifest["artifacts"], names)
    measured = {}
    audit_data = pinned(audit_path, pins["parent_representation_rows_sha256"])
    for row in jsonl(audit_data)[0]:
        if row["split"] not in SPLITS:
            continue
        ident = row["example_id"]
        require(ident in index["examples"] and ident not in measured, "audit_identity_set")
        require(row["example_sha256"] == canonical_hash(index["examples"][ident]), "audit_example_identity")
        measured[ident] = row
    require(set(measured) == set(index["examples"]), "audit_missing_example")
    parents, parent_lines = {}, {}
    for profile in PROFILES:
        parents[profile] = {}
        for split in SPLITS:
            prefix = profile + "/" + split
            values, lines = jsonl(selected_data[prefix + ".examples.jsonl"])
            sidecars = jsonl(selected_data[prefix + ".sidecars.jsonl"])[0]
            require(len(values) == len(sidecars), "parent_sidecar_count")
            for value, line, sidecar in zip(values, lines, sidecars, strict=True):
                ident = value["example_id"]
                require(original_bytes.get(ident) == line and sidecar["audit"] == measured.get(ident),
                        "parent_bytes_or_measurement_changed")
            parent_lines[prefix] = {e["example_id"]: line for e, line in zip(values, lines, strict=True)}
            parents[profile][split] = {"examples": values, "sidecars": sidecars,
                "excluded": loads(selected_data[prefix + ".excluded.json"].decode()),
                "summary": selection_manifest["profiles"][profile][split]}
    review_root = Path(review_root).resolve()
    seal = loads(pinned(review_root / "seal.json", pins["review_seal_sha256"]).decode())
    require(seal["status"] == "PASS" and seal["head_unchanged"] == config["verified_code_base"], "review_seal_scope")
    reviewed = checked_bundle(review_root, seal["artifacts"], {"semantic_review_ai.csv", "token_mask_review_ai.csv",
                             "remediation_proposal.json", "reannotation_drafts.json", "intake.json"})
    for name, key in (("semantic_review_ai.csv", "semantic_review_sha256"), ("token_mask_review_ai.csv", "token_review_sha256"),
                      ("remediation_proposal.json", "remediation_proposal_sha256"), ("reannotation_drafts.json", "reannotation_drafts_sha256")):
        require(sha(reviewed[name]) == pins[key], "review_artifact_binding")
    pinned(review_root / "provenance.md", pins["provenance_sha256"])
    intake = loads(reviewed["intake.json"].decode())
    old_token_data, token_cases = _old_token_materials(token_review_root, intake)
    semantic, tokens = csv_rows(reviewed["semantic_review_ai.csv"]), csv_rows(reviewed["token_mask_review_ai.csv"])
    reviewed_csv(csv_rows(data["human-review/review.csv"]), semantic,
                 ("source_index", "source_record_hash", "example_ids", "strata"))
    reviewed_csv(csv_rows(old_token_data["review.csv"]), tokens, ("case_id", "category"))
    proposal = loads(reviewed["remediation_proposal.json"].decode())
    issues, review_summary = review_issues(index, semantic, tokens, token_cases, proposal)
    require(Counter(i["verdict"] for i in issues.values()) == config["quarantine"]["expected_source_counts"], "fixed_source_counts")
    raw = loads(pinned(raw_source_path, pins["raw_source_sha256"]).decode())
    for issue in issues.values():
        require(0 <= issue["source_index"] < len(raw)
                and canonical_hash(raw[issue["source_index"]]) == issue["source_record_hash"], "raw_issue_source_identity")
    drafts = loads(reviewed["reannotation_drafts.json"].decode())
    require(len(drafts) == config["annotations"]["direct_action_revisions"], "fixed_draft_count")
    policy_bytes = pinned(source_policy_path, POLICY_SHA256)
    policy = SourcePolicy(source_policy_path)
    require(policy.config == loads(policy_bytes.decode()), "source_policy_consumed_bytes")
    source_proofs = annotation_source_evidence(index, drafts, raw, policy)
    binding = {"config_file_sha256": CONFIG_SHA256, **pins, "source_policy_sha256": POLICY_SHA256,
        "original_data_artifacts": data_manifest["artifacts"],
        "parent_selection_artifacts": selection_manifest["artifacts"],
        "parent_selection_input_binding": selection_manifest["input_binding"],
        "original_token_material_manifest_sha256": sha(old_token_data["manifest.json"]),
        "review_summary": review_summary, "new_full_corpus_tokenization": 0,
        "historical_measurement": selection_manifest["input_binding"]["historical_measurement"]}
    return {"config": config, "index": index, "original_bytes": original_bytes, "parents": parents,
            "parent_lines": parent_lines, "parent_config": parent_config, "issues": issues,
            "proposal": proposal, "drafts": drafts, "source_evidence": source_proofs,
            "old_token_cases": token_cases, "binding": binding}


def stable_artifacts(inputs):
    config, index, issues = inputs["config"], inputs["index"], inputs["issues"]
    view = revise_view(index, issues)
    result = {"effective/" + split + ".jsonl": b"".join(inputs["original_bytes"][i] for i in view["retained"][split])
              for split in SPLITS}
    revision = {"version": "toolalign.quality-revision.v1", "config_file_sha256": CONFIG_SHA256,
        "input_binding_sha256": canonical_hash(inputs["binding"]),
        "effective_files": {k: sha(v) for k, v in result.items()},
        "quarantine_source_sha256": canonical_hash(view["sources"]),
        "quarantine_ids_sha256": canonical_hash([r["example_id"] for r in view["quarantined"]]),
        "drafts_sha256": canonical_hash(inputs["drafts"])}
    revision_id = canonical_hash(revision)
    selection = filter_selection(index, inputs["parents"], issues, revision_id,
                                 config["input_bindings"]["parent_selection_manifest_file_sha256"])
    staged = stage_annotations(index, issues, inputs["drafts"], inputs["source_evidence"], revision_id)
    actual_counts = {}
    for split in SPLITS:
        quarantined = Counter(r["review_verdict"] for r in view["quarantined"] if r["split"] == split)
        actual_counts[split] = {"original": sum(e["split"] == split for e in index["examples"].values()),
            "quarantined_fail": quarantined["fail"], "quarantined_unknown": quarantined["unknown"],
            "effective": len(view["retained"][split])}
    for profile in PROFILES:
        for split in SPLITS:
            item = selection[profile][split]
            counts = {"original": item["summary"]["parent_selected_count"], "effective": len(item["examples"])}
            if split == "train":
                counts.update({"quarantined_" + k: len(v) for k, v in item["removed"].items()})
            actual_counts[profile + "_" + split] = counts
            # The sealed proposal's selected membership is independently joined.
            for issue in issues.values():
                expected = [e["example_id"] for e in inputs["parents"][profile][split]["examples"]
                            if e["source_record_hash"] == issue["source_record_hash"]]
                require(issue["selected_membership"][profile + "/" + split] == expected, "proposal_selection_membership")
            old_removed = inputs["proposal"]["quarantine_example_ids"][profile + "/" + split]
            require(old_removed["confirmed_fail"] == item["removed"]["fail"]
                    and old_removed["uncertain"] == item["removed"]["unknown"], "proposal_selection_removed")
            prefix = "selection/" + profile + "/" + split
            result[prefix + ".examples.jsonl"] = b"".join(inputs["parent_lines"][profile + "/" + split][e["example_id"]]
                                                         for e in item["examples"])
            result[prefix + ".sidecars.jsonl"] = b"".join(encoded(v) + b"\n" for v in item["sidecars"])
            result[prefix + ".excluded.json"] = encoded({"quality_quarantined": item["removed"],
                "parent_excluded_unchanged": item["parent_excluded"], "refill_count": 0}) + b"\n"
    require(actual_counts == config["expected_counts"], "fixed_revision_counts")
    staged_ids = {e["example_id"] for e in staged["examples"]}
    effective_ids = {i for values in view["retained"].values() for i in values}
    require(not staged_ids & effective_ids, "staged_example_leaked_into_effective")
    for row in view["quarantined"]:
        row["original_jsonl_line_sha256"] = sha(inputs["original_bytes"][row["example_id"]])
    result["quarantine/examples.jsonl"] = b"".join(inputs["original_bytes"][r["example_id"]] for r in view["quarantined"])
    result["quarantine/sidecars.jsonl"] = b"".join(encoded(r) + b"\n" for r in view["quarantined"])
    result["quarantine/sources.jsonl"] = b"".join(encoded(r) + b"\n" for r in view["sources"])
    retained_lineage = [{**{k: index["examples"][i][k] for k in IDENTITY},
        "original_example_sha256": canonical_hash(index["examples"][i]),
        "original_jsonl_line_sha256": sha(inputs["original_bytes"][i]),
        "original_lineage_sha256": canonical_hash(index["lineage"][i]),
        "disposition": "retained_original_bytes"} for split in SPLITS for i in view["retained"][split]]
    result["effective/lineage.jsonl"] = b"".join(encoded(r) + b"\n" for r in retained_lineage)
    result["effective/identities.json"] = encoded(view["retained"]) + b"\n"
    for kind in ("examples", "sidecars"):
        result["staging/" + kind + ".jsonl"] = b"".join(encoded(r) + b"\n" for r in staged[kind])
    selection_manifest = {"manifest_version": "toolalign.quality-selection.v1", "training_authorized": False,
        "quality_revision_sha256": revision_id, "quality_config_sha256": CONFIG_SHA256,
        "parent_training_config": inputs["parent_config"],
        "parent_training_config_file_sha256": config["input_bindings"]["parent_training_config_file_sha256"],
        "parent_selection_manifest_file_sha256": config["input_bindings"]["parent_selection_manifest_file_sha256"],
        "inherited_input_binding": inputs["binding"]["parent_selection_input_binding"],
        "profiles": {p: {s: {k: selection[p][s][k] for k in ("parent_summary", "summary")}
                          for s in SPLITS} for p in PROFILES},
        "artifacts": {k.removeprefix("selection/"): {"sha256": sha(v), "size_bytes": len(v)}
                      for k, v in result.items() if k.startswith("selection/")}}
    result["selection/manifest.json"] = encoded(selection_manifest) + b"\n"
    result["training-binding.json"] = encoded({"binding_version": "toolalign.quality-training-binding.v1",
        "quality_revision_sha256": revision_id, "quality_config_sha256": CONFIG_SHA256,
        "effective_files": revision["effective_files"], "selection_manifest_sha256": sha(result["selection/manifest.json"]),
        "parent_training_config_file_sha256": config["input_bindings"]["parent_training_config_file_sha256"],
        "profiles": inputs["parent_config"]["profiles"], "status": "CPU_REMEDIATION_CANDIDATE",
        "training_authorized": False, "staged_annotations_enter_training": False, "pending": config["pending"]}) + b"\n"
    affected_groups = {r["group_id"] for r in view["quarantined"]}
    manifest = {"manifest_version": "toolalign.quality-revision.v1", "status": "CPU_REMEDIATION_CANDIDATE",
        "training_authorized": False, "quality_revision": revision, "quality_revision_sha256": revision_id,
        "input_binding": inputs["binding"], "counts": actual_counts,
        "quarantine_source_counts": dict(Counter(i["verdict"] for i in issues.values())),
        "unrelated_examples_retained_in_affected_groups": sum(index["examples"][i]["group_id"] in affected_groups for i in effective_ids),
        "annotations": {"status": "STAGED_PENDING_INDEPENDENT_REVIEW",
            "direct_action_revisions": len(inputs["drafts"]), "dependent_prefix_revisions": len(staged_ids) - len(inputs["drafts"]),
            "enters_effective_training": False, "external_execution": "NOT_RUN", "semantic_verdict": None},
        "artifacts": {k: {"sha256": sha(v), "size_bytes": len(v)} for k, v in result.items()},
        "new_full_corpus_tokenization": 0, "pending": config["pending"]}
    result["manifest.json"] = encoded(manifest) + b"\n"
    return result, manifest


def consumer_identity():
    names = ("data/quality_revision.py", "data/common.py", "data/training_selection.py",
             "data/source_policy.py", "data/toolace.py", "data/grouping.py", "contracts/validation.py",
             "model_io/format.py", "model_io/descriptor.v1.json", "tools/_json.py")
    return {"python": platform.python_version(), "contract_sha256": contract_digest(),
            "package_files": {n: sha(files("toolalign").joinpath(n).read_bytes()) for n in names}}


def publish(output, artifacts, run):
    """Expose the success manifest only after every other file is written."""
    requested = Path(output)
    require(not requested.exists() and not requested.is_symlink(), "output_already_exists")
    root = requested.resolve()
    require(".toolalign-local" in root.parts, "private_output_required")
    require(sum(len(v) for v in artifacts.values()) <= 2 * 1024**3, "output_byte_budget")
    root.mkdir(parents=True, exist_ok=False)
    root.chmod(0o700)
    try:
        for name, data in {**{k: v for k, v in artifacts.items() if k != "manifest.json"},
                           "run.json": encoded(run) + b"\n", ".manifest.pending": artifacts["manifest.json"]}.items():
            path = child_path(root, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
            path.chmod(0o600)
        os.replace(root / ".manifest.pending", root / "manifest.json")
    except BaseException:
        # Preserve partial artifacts for diagnosis, without an accepted manifest.
        (root / "manifest.json").unlink(missing_ok=True)
        raise
    return root


def build(*, output, **paths):
    require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    require(not MODEL_ROOTS & {n.split(".", 1)[0] for n in sys.modules}, "cpu_only_process_required")
    inputs = bound_inputs(**paths)
    artifacts, manifest = stable_artifacts(inputs)
    run = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "consumer": consumer_identity(),
           "input_paths": {k: str(Path(v).resolve()) for k, v in paths.items()},
           "output_path": str(Path(output).resolve()), "stable_manifest_sha256": sha(artifacts["manifest.json"]),
           "model_modules_loaded": [], "training_authorized": False}
    publish(output, artifacts, run)
    return manifest


def verify_artifacts(output, artifacts):
    """Check a publication against independently re-derived in-memory buffers."""
    requested = Path(output)
    require(not requested.is_symlink(), "output_symlink")
    root = requested.resolve()
    require(root.is_dir() and ".toolalign-local" in root.parts, "private_output_required")
    require(not any(p.is_symlink() for p in root.rglob("*")), "output_symlink")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    require(actual == set(artifacts) | {"run.json"}, "revision_artifact_set_mismatch")
    for name, data in artifacts.items():
        pinned(child_path(root, name), sha(data))
    run = loads((root / "run.json").read_text(encoding="utf-8"))
    require(run["stable_manifest_sha256"] == sha(artifacts["manifest.json"])
            and run["consumer"]["package_files"] == consumer_identity()["package_files"]
            and run["consumer"]["contract_sha256"] == contract_digest()
            and run["training_authorized"] is False and run["model_modules_loaded"] == [], "run_binding_mismatch")
    return run


def verify(*, output, **paths):
    """Re-derive the new view from the exact frozen inputs and compare its bytes."""
    require(not MODEL_ROOTS & {n.split(".", 1)[0] for n in sys.modules}, "cpu_only_process_required")
    inputs = bound_inputs(**paths)
    artifacts, manifest = stable_artifacts(inputs)
    verify_artifacts(output, artifacts)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        command = sub.add_parser(name)
        for flag in ("config-path", "data-manifest-path", "selection-manifest-path", "training-config-path",
                     "audit-path", "review-root", "token-review-root", "raw-source-path", "source-policy-path", "output"):
            command.add_argument("--" + flag, required=True, type=Path)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        manifest = {"build": build, "verify": verify}[command](**args)
    except (DataError, ContractError, OSError, KeyError, TypeError, ValueError, IndexError) as exc:
        print(encoded({"status": "FAIL", "error_type": type(exc).__name__,
                       "error_code": str(exc) if type(exc) is DataError else "invalid_input_or_io"}).decode())
        return 1
    print(encoded({"status": "PASS_STRUCTURAL_BUILD" if command == "build" else "PASS_STRUCTURAL_VERIFY",
                   "counts": manifest["counts"], "quality_revision_sha256": manifest["quality_revision_sha256"],
                   "annotations": manifest["annotations"], "training_authorized": False}).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
