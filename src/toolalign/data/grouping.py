"""Deterministic connected groups, split assignment, and inherited augmentation."""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from collections import defaultdict

from toolalign.contracts import canonical_hash, model_input_from_example, validate_record

from .common import DataError

SPLITS = ("train", "validation", "test", "ood_test")


def task_template(text):
    """An explicit lexical template heuristic, not a semantic equivalence oracle."""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r'"[^"\n]*"|“[^”\n]*”', " SLOT ", text)
    text = re.sub(r"\b\d+(?:[.:-]\d+)*\b", " NUMBER ", text)
    return " ".join(re.findall(r"[a-z_]+|[\u3400-\u9fff]|[^\W\d_]+", text))


def schema_shape(value):
    if isinstance(value, dict):
        return {k: schema_shape(v) for k, v in value.items() if k not in {"description", "default"}}
    if isinstance(value, list):
        return [schema_shape(v) for v in value]
    return value


def _shingles(text):
    words = text.split()
    if len(words) < 8:
        return set()
    return {" ".join(words[i : i + 3]) for i in range(len(words) - 2)}


def normalized_schema_semantics(schema):
    """Ignore annotations, not property names; set-valued keywords are unordered.

    This additional audit never changes the original source grouping keys.
    It is a structural equivalence check, not a complete logical schema solver.
    """
    result = {k: copy.deepcopy(v) for k, v in schema.items() if k not in {"description", "default"}}
    if "properties" in result:
        result["properties"] = {
            name: normalized_schema_semantics(child) for name, child in result["properties"].items()
        }
        result["required"] = sorted(result.get("required", []))
    if "items" in result:
        result["items"] = normalized_schema_semantics(result["items"])
    if "enum" in result:
        result["enum"] = sorted(result["enum"], key=canonical_hash)
    if result["type"] == "string":
        result.setdefault("minLength", 0)
    if result["type"] == "array":
        result.setdefault("minItems", 0)
    return result


def normalized_group_guard(infos, assignments):
    """Quarantine normalized schema bridges while preserving original groups.

    All convertible source tools participate, including tools in otherwise
    rejected records. No acceptance rate or split target determines retention.
    """
    owners = defaultdict(lambda: {"groups": set(), "splits": set(), "sources": set()})
    for info, assignment in zip(infos, assignments, strict=True):
        for key in info.get("normalized_schema_keys", []):
            owners[key]["groups"].add(assignment["group_id"])
            owners[key]["splits"].add(assignment["split"])
            owners[key]["sources"].add(info["source_record_hash"])
    conflicts = [
        {"normalized_schema_key": key, **{k: sorted(v) for k, v in owner.items()}}
        for key, owner in sorted(owners.items())
        if len(owner["groups"]) > 1
    ]
    excluded = {source for row in conflicts for source in row["sources"]}
    return (
        excluded,
        conflicts,
        {
            "method": "quarantine_all_sources_with_normalized_schema_in_multiple_original_groups.v1",
            "original_assignments_changed": False,
            "normalized_schema_keys": len(owners),
            "bridge_keys": len(conflicts),
            "cross_split_bridge_keys": sum(len(row["splits"]) > 1 for row in conflicts),
            "bridge_unique_source_records": len(excluded),
            "conflicts_hash": canonical_hash(conflicts),
        },
    )


class Union:
    def __init__(self, size):
        self.parents = list(range(size))

    def root(self, i):
        while self.parents[i] != i:
            self.parents[i] = self.parents[self.parents[i]]
            i = self.parents[i]
        return i

    def join(self, a, b):
        a, b = self.root(a), self.root(b)
        self.parents[max(a, b)] = min(a, b)


def build_groups(records, infos, seed, ood_fraction=0.1):
    if type(seed) is not int or not 0 <= ood_fraction < 1:
        raise DataError("split_parameters")
    union = Union(len(infos))
    keys_by_index = []
    templates = []
    inverted = {}
    edge_counts = defaultdict(int)
    for i, (record, info) in enumerate(zip(records, infos, strict=True)):
        keys = {"source:" + info["source_record_hash"]}
        keys.update("tool:" + k for k in info["tool_keys"])
        keys.update("schema:" + k for k in info["schema_keys"])
        turns = record.get("conversations", []) if isinstance(record, dict) else []
        local_templates = []
        for turn in turns if isinstance(turns, list) else []:
            if (
                isinstance(turn, dict)
                and turn.get("from") == "user"
                and isinstance(turn.get("value"), str)
            ):
                template = task_template(turn["value"])
                if template:
                    keys.add("template:" + canonical_hash(template))
                    local_templates.append(template)
        templates.append(local_templates)
        for key in sorted(keys):
            if key in inverted:
                union.join(i, inverted[key])
                edge_counts[key.split(":")[0]] += 1
            else:
                inverted[key] = i
        keys_by_index.append(keys)

    # Deterministic MinHash LSH candidate retrieval, followed by exact trigram
    # Jaccard >= .85. 16 bands x 4 hashes; no claim of exhaustive semantic recall.
    buckets = defaultdict(list)
    shingle_sets = []
    near_edges = set()
    candidate_count = 0
    for record_index, local_templates in enumerate(templates):
        for template in local_templates:
            shingles = _shingles(template)
            if not shingles:
                continue
            signature = [2**64 - 1] * 64
            for s in shingles:
                digest = hashlib.sha256(s.encode()).digest()
                a, b = int.from_bytes(digest[:8], "big"), int.from_bytes(digest[8:16], "big") | 1
                for j in range(64):
                    signature[j] = min(signature[j], (a + j * b) % (2**64))
            candidates = set()
            band_keys = [(b, tuple(signature[b * 4 : b * 4 + 4])) for b in range(16)]
            for key in band_keys:
                candidates.update(buckets[key])
            for old in sorted(candidates):
                old_index, old_shingles = shingle_sets[old]
                if old_index == record_index:
                    continue
                candidate_count += 1
                ratio = len(shingles & old_shingles) / len(shingles | old_shingles)
                if ratio >= 0.85:
                    pair = tuple(
                        sorted(
                            (
                                infos[record_index]["source_record_hash"],
                                infos[old_index]["source_record_hash"],
                            )
                        )
                    )
                    if pair[0] != pair[1]:
                        near_edges.add(pair)
                    union.join(record_index, old_index)
            item = len(shingle_sets)
            shingle_sets.append((record_index, shingles))
            for key in band_keys:
                buckets[key].append(item)
    members = defaultdict(set)
    for i, info in enumerate(infos):
        members[union.root(i)].add(info["source_record_hash"])
    group_ids = {root: canonical_hash(sorted(hashes)) for root, hashes in members.items()}
    assignments = []
    for i, info in enumerate(infos):
        group_id = group_ids[union.root(i)]
        ood_score = int(canonical_hash([seed, "ood", group_id])[:16], 16) / 2**64
        score = int(canonical_hash([seed, "split", group_id])[:16], 16) / 2**64
        split = (
            "ood_test"
            if ood_score < ood_fraction
            else "train"
            if score < 0.8
            else "validation"
            if score < 0.9
            else "test"
        )
        assignments.append(
            {
                "source_index": info["source_index"],
                "source_record_hash": info["source_record_hash"],
                "group_id": group_id,
                "split": split,
                "group_keys": sorted(keys_by_index[i]),
            }
        )
    validate_isolation(assignments)
    return assignments, {
        "groups": len(members),
        "largest_group_unique_records": max(map(len, members.values()), default=0),
        "exact_key_edges": dict(edge_counts),
        "near_candidate_pairs": candidate_count,
        "near_duplicate_edges": len(near_edges),
        "near_edges_hash": canonical_hash([list(p) for p in sorted(near_edges)]),
        "method": "connected keys + MinHash64/16x4/Jaccard-trigram>=0.85-v1",
    }


def validate_isolation(assignments):
    owners = {}
    examples = {r.get("example_id"): r for r in assignments if r.get("example_id")}
    for record in assignments:
        split = record["split"]
        if split not in SPLITS:
            raise DataError("invalid_split")
        keys = ["group:" + record["group_id"], "source:" + record["source_record_hash"]]
        keys += record.get("group_keys", [])
        for key in keys:
            if key in owners and owners[key] != split:
                raise DataError("split_intersection")
            owners[key] = split
        parent_id = record.get("augmentation_parent")
        if parent_id:
            parent = examples.get(parent_id)
            if parent is None or any(
                record[k] != parent[k] for k in ("group_id", "split", "source_record_hash")
            ):
                raise DataError("augmentation_crosses_group")
    return {"group": 0, "source": 0, "tool": 0, "schema": 0, "template": 0, "augmentation": 0}


def augment(parent, messages, parent_lineage):
    """Apply a caller-reviewed rewrite after split; never infer a new group."""
    validate_record(parent, "example")
    if any(
        parent[k] != parent_lineage[k]
        for k in ("example_id", "group_id", "split", "source_record_hash")
    ):
        raise DataError("parent_lineage_mismatch")
    child = copy.deepcopy(parent)
    child["messages"] = copy.deepcopy(messages)
    model_input_from_example(child)
    identity = canonical_hash({"parent": parent["example_id"], "messages": messages})
    if messages == parent["messages"]:
        raise DataError("augmentation_unchanged")
    child["example_id"] = identity
    lineage = {
        **copy.deepcopy(parent_lineage),
        "example_id": identity,
        "normalized_hash": canonical_hash(
            {k: v for k, v in child.items() if k not in {"example_id", "group_id", "split"}}
        ),
        "augmentation_parent": parent["example_id"],
    }
    return validate_record(child), lineage
