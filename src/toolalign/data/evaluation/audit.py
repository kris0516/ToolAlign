"""Transitive isolation from P02/P03/G4 and explicitly frozen G5 history."""

from __future__ import annotations

import copy
from collections import defaultdict

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError
from toolalign.data.grouping import Union, _shingles, task_template
from toolalign.data.preferences.audit import task_keys
from toolalign.tools import LocalToolRegistry

from .tasks import retain_tasks


def development_nodes(cases):
    tools = LocalToolRegistry().tools
    return [{"task_id": c["id"], "family_id": c["group"], "group_id": c["group"],
             "example": {"source_record_hash": canonical_hash(c), "tools": tools,
                         "messages": [{"role": "user", "content": c["prompt"]}]}}
            for c in cases]


def audit_groups(bundle, p02_rows, development_cases, g4_bundle, *, semantic_links=(),
                 historical_g5_reference=None):
    """Any old-data bridge excludes every new task in that connected component.

    Exact lexical keys use the frozen P02 helpers. For the small readable sets,
    all trigram pairs are checked at the existing .85 Jaccard threshold instead
    of approximate candidate retrieval. P02 prompts are never read here.
    Caller-authored semantic links are evidence, not a semantic classifier.
    An explicit historical G5 reference contains original ``tasks`` and frozen
    ``edges`` with g5:/p02:/p03:/g4: endpoints. Its old-only edges are inherited,
    including semantic and near-trigram evidence, and the complete graph is
    returned for reference readback. Omitting it preserves the original output.
    """
    bundle = copy.deepcopy(bundle)
    tasks = bundle["tasks"]
    old_groups = {}
    for row in p02_rows:
        if row["split"] not in {"train", "validation", "test", "ood_test"}:
            raise DataError("unknown_p02_split")
        group = old_groups.setdefault(row["group_id"], {"keys": set(), "splits": set()})
        group["keys"].update(row["group_keys"])
        group["splits"].add(row["split"])
    nodes = [{"id": "new:" + t["task_id"], "dataset": "new", "task_id": t["task_id"],
              "keys": task_keys(t), "task": t} for t in tasks]
    for group_id, group in sorted(old_groups.items()):
        nodes.append({"id": "p02:" + group_id, "dataset": "p02", "group_id": group_id,
                      "splits": sorted(group["splits"]), "keys": group["keys"]})
    historical = [] if historical_g5_reference is None else historical_g5_reference["tasks"]
    for dataset, entries in (("p03", development_nodes(development_cases)),
                             ("g4", g4_bundle["tasks"]), ("g5", historical)):
        for task in entries:
            nodes.append({"id": dataset + ":" + task["task_id"], "dataset": dataset,
                          "task_id": task["task_id"], "task": task,
                          "keys": task_keys(task) | {dataset + "-group:" + task["group_id"]}})
    union, owners, edges = Union(len(nodes)), {}, []
    for index, node in enumerate(nodes):
        for key in sorted(node["keys"]):
            if key in owners:
                other = owners[key]
                union.join(index, other)
                edges.append({"left": nodes[other]["id"], "right": node["id"], "key": key})
            else:
                owners[key] = index
    readable = [(i, n, [_shingles(task_template(m["content"]))
                        for m in n["task"]["example"]["messages"] if m["role"] == "user"])
                for i, n in enumerate(nodes) if "task" in n]
    nearest, pairs = {}, 0
    for pos, (i, node, shingles) in enumerate(readable):
        for j, other, other_shingles in readable[pos + 1:]:
            if node["dataset"] != "new" and other["dataset"] != "new":
                continue
            pairs += 1
            similarity = max((len(a & b) / len(a | b) for a in shingles for b in other_shingles
                              if a and b), default=0.0)
            if other["dataset"] != "new":
                previous = nearest.get(node["id"])
                if previous is None or similarity > previous["jaccard"]:
                    nearest[node["id"]] = {"reference": other["id"], "jaccard": similarity}
            if similarity >= 0.85:
                union.join(i, j)
                edges.append({"left": node["id"], "right": other["id"],
                              "key": "near-trigram", "jaccard": similarity})
    indices = {n["id"]: i for i, n in enumerate(nodes)}
    if historical_g5_reference is not None:
        for edge in historical_g5_reference["edges"]:
            if (any(edge[end] not in indices or edge[end].startswith("new:")
                    for end in ("left", "right")) or not edge.get("key")):
                raise DataError("historical_g5_edge_evidence")
            union.join(indices[edge["left"]], indices[edge["right"]])
            edges.append({**copy.deepcopy(edge), "origin": "historical_g5_reference"})
    for link in semantic_links:
        if (link["left"] not in indices or link["right"] not in indices
                or not link.get("reason")):
            raise DataError("semantic_link_evidence")
        union.join(indices[link["left"]], indices[link["right"]])
        edges.append({**link, "key": "authored-semantic-link"})
    members = defaultdict(list)
    for i, node in enumerate(nodes):
        members[union.root(i)].append(node)
    components, dispositions, retained = [], [], set()
    for group in members.values():
        new = [n for n in group if n["dataset"] == "new"]
        if not new:
            continue
        group_id = canonical_hash(sorted(n["id"] for n in group))
        old = [{k: v for k, v in n.items() if k not in {"task", "keys"}}
               for n in group if n["dataset"] != "new"]
        names = {n["id"] for n in group}
        relevant = [e for e in edges if e["left"] in names and e["right"] in names]
        components.append({"group_id": group_id, "task_ids": [n["task_id"] for n in new],
                           "tool_sets": [list(names) for names in
                                         sorted({tuple(n["task"]["tool_names"]) for n in new})],
                           "old_nodes": old, "edges": relevant})
        for node in new:
            task = node["task"]
            task["group_id"] = task["example"]["group_id"] = task["oracle_task"]["group_id"] = group_id
            status = "quarantined" if old else "heldout"
            dispositions.append({"task_id": task["task_id"], "group_id": group_id, "status": status,
                                 "reason": "old_data_component" if old else "isolated_component"})
            if not old:
                retained.add(task["task_id"])
    audit = {
        "schema_version": "toolalign.evaluation-group-audit.v1",
        "components": components, "dispositions": dispositions,
        "nearest_readable_old": nearest, "trigram_pairs_checked": pairs,
        "trigram_threshold": 0.85, "trigram_method": "exhaustive_readable_pairs_frozen_shingles",
        "semantic_links": list(semantic_links), "semantic_review_status": "author_review_pending_Q1",
        "p02_heldout_content_read": False, "p02_assignments_changed": False,
        "p02_semantic_near_duplicate_retrieval": "NOT_RUN_metadata_only",
        "old_p02_groups": len(old_groups), "old_p03_tasks": len(development_cases),
        "old_g4_tasks": len(g4_bundle["tasks"]),
        "node_keys": [{"id": n["id"], "keys": sorted(n["keys"])} for n in nodes],
    }
    if historical_g5_reference is not None:
        audit["old_g5_tasks"] = len(historical)
        audit["reference_graph"] = {
            "nodes": [{**{k: v for k, v in n.items() if k not in {"task", "keys"}},
                       "keys": sorted(n["keys"])} for n in nodes],
            "edges": edges,
            "components": [{"group_id": canonical_hash(sorted(n["id"] for n in group)),
                            "node_ids": sorted(n["id"] for n in group)}
                           for group in members.values()],
        }
    return retain_tasks(bundle, retained), audit
