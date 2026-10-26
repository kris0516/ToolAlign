"""Train grouping against frozen P02 metadata and public development identities."""

from __future__ import annotations

import copy
from collections import Counter, defaultdict
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError, file_hash, loads, read_json
from toolalign.data.grouping import Union, normalized_schema_semantics, schema_shape, task_template
from toolalign.evaluation.oracles.semantic import equivalent


def jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            yield loads(line)


def p02_metadata(manifest_path):
    """Read grouping metadata only; no held-out prompts, answers or oracle."""
    manifest_path = Path(manifest_path)
    manifest = read_json(manifest_path)
    paths = {name: manifest_path.parent / name
             for name in ("assignments.jsonl", "tool-lineage.jsonl")}
    for name, path in paths.items():
        if file_hash(path) != manifest["artifacts"][name]:
            raise DataError("p02_metadata_hash_mismatch")
    normalized = defaultdict(set)
    for row in jsonl(paths["tool-lineage.jsonl"]):
        if row.get("normalized_schema_key"):
            raw = row["raw_tool"]["parameters"]
            normalized["schema:" + canonical_hash(schema_shape(raw))].add(
                "normalized-schema:" + row["normalized_schema_key"])
    rows = list(jsonl(paths["assignments.jsonl"]))
    for row in rows:
        row["group_keys"] = sorted(set(row["group_keys"]) | {
            key for raw_key in row["group_keys"] for key in normalized.get(raw_key, ())})
    return rows, {"manifest_sha256": file_hash(manifest_path),
                  "metadata": {name: manifest["artifacts"][name] for name in paths},
                  "records": len(rows), "splits": dict(Counter(r["split"] for r in rows)),
                  "held_out_content_read": False}


def task_keys(task):
    example = task["example"]
    keys = {"source:" + example["source_record_hash"], "family:" + task["family_id"]}
    for message in example["messages"]:
        if message["role"] == "user":
            keys.add("template:" + canonical_hash(task_template(message["content"])))
    for tool in example["tools"]:
        keys.update({"tool:" + canonical_hash({"name": tool["name"]}),
                     "schema:" + canonical_hash(schema_shape(tool["parameters_json_schema"])),
                     "normalized-schema:" + canonical_hash(
                         normalized_schema_semantics(tool["parameters_json_schema"]))})
    return keys


def audit_groups(bundle, p02_rows, development_cases):
    """Quarantine an entire new component if any bridge reaches a held-out group."""
    bundle = copy.deepcopy(bundle)
    tasks = bundle["tasks"]
    old = {}
    for row in p02_rows:
        if row["split"] not in {"train", "validation", "test", "ood_test"}:
            raise DataError("unknown_p02_split")
        group = old.setdefault(row["group_id"], {"keys": set(), "splits": set()})
        group["keys"].update(row["group_keys"])
        group["splits"].add(row["split"])
    old_items = sorted(old.items())
    keys = [task_keys(task) for task in tasks] + [v["keys"] for _, v in old_items]
    union, owners = Union(len(keys)), {}
    for index, local_keys in enumerate(keys):
        for key in sorted(local_keys):
            if key in owners:
                union.join(index, owners[key])
            else:
                owners[key] = index
    members, existing = defaultdict(list), defaultdict(list)
    for index, task in enumerate(tasks):
        members[union.root(index)].append(task["task_id"])
    for index, (group_id, group) in enumerate(old_items, start=len(tasks)):
        existing[union.root(index)].append({"group_id": group_id, "splits": sorted(group["splits"])})
    components, dispositions, kept = [], [], []
    for root, task_ids in sorted(members.items()):
        overlaps = existing[root]
        bad_splits = sorted({s for group in overlaps for s in group["splits"] if s != "train"})
        group_id = canonical_hash({"g4_tasks": sorted(task_ids), "p02_groups": overlaps})
        components.append({"group_id": group_id, "task_ids": sorted(task_ids),
                           "p02_groups": overlaps, "held_out_splits": bad_splits})
        for task in (t for t in tasks if t["task_id"] in task_ids):
            task["group_id"] = task["example"]["group_id"] = task["oracle_task"]["group_id"] = group_id
            dispositions.append({"task_id": task["task_id"], "group_id": group_id,
                                 "status": "quarantined" if bad_splits else "train",
                                 "reason": "p02_held_out_component" if bad_splits else "train_component"})
            if not bad_splits:
                kept.append(task)
    dev_overlap, clones = [], set()
    for task in tasks:
        names = {tool["name"] for tool in task["example"]["tools"]}
        for case in development_cases:
            # Public diagnostics are deliberately not formal held-out groups.
            clone = (task["task_id"] == case["id"]
                     or task_template(task["example"]["messages"][0]["content"])
                     == task_template(case["prompt"])
                     or (equivalent(task["oracle_task"]["oracle_payload"]["answers"], case["answers"])
                         and equivalent(task["oracle_task"]["oracle_payload"]["strategies"],
                                        case["strategies"])
                         and equivalent(task["faults"], case.get("faults", {}))))
            if clone:
                clones.add(task["task_id"])
            dev_overlap.append({"task_id": task["task_id"], "development_id": case["id"],
                                "shared_prompt_tools": sorted(names),
                                "shared_registry_schemas": len(names), "clone": clone})
    for disposition in dispositions:
        if disposition["task_id"] in clones:
            disposition.update(status="quarantined", reason="public_development_clone")
    bundle["tasks"] = sorted((t for t in kept if t["task_id"] not in clones), key=lambda t: t["task_id"])
    return bundle, {"schema_version": "toolalign.preference-group-audit.v1",
                    "components": components, "dispositions": dispositions,
                    "development_overlap": dev_overlap, "p02_assignments_changed": False,
                    "development_role": "public_validation_diagnostic",
                    "schema_isolation_from_development": False,
                    "template_method": "frozen_lexical_keys_plus_authored_family_not_semantic_recall",
                    "future_same_group_evaluation": "seen-group diagnostic only"}
