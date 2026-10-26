"""Finite original relations and read-only checks for four constraint domains.

Reads return every row needed for reasoning over the selected resource. Checks
use that same fixed relation; no function reads paths, networks or environment.
These are component resources, not evaluation tasks or independent task groups.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy

from .catalog import ToolFault

VERSION = "heldout-constraints.v1"
DOMAIN_TOOLS = {
    "releases": ("read_quorum_layout", "check_quorum_removals"),
    "incidents": ("read_event_intervals", "measure_interval_coverage"),
    "packages": ("read_dependency_graph", "check_installation_order"),
    "storage": ("read_shard_placement", "check_shard_recovery"),
}

# Every listed instance initially serves its partition. Removals accumulate
# across stages, including empty stages; a repeated instance is removed once.
QUORUM_LAYOUTS = {
    "search-ring": {"layout_id": "search-layout-1", "partitions": [
        {"partition": "east", "instances": ["e1", "e2", "e3"], "quorum": 2},
        {"partition": "west", "instances": ["w1", "w2", "w3", "w4"], "quorum": 2},
    ]},
    "session-ring": {"layout_id": "session-layout-1", "partitions": [
        {"partition": "north", "instances": ["n1", "n2"], "quorum": 1},
        {"partition": "south", "instances": ["s1", "s2", "s3"], "quorum": 2},
    ]},
}

# Integer minutes on the local timeline, with left-closed/right-open intervals.
# Overlapping and adjacent intervals are both present in each resource.
EVENT_TIMELINES = {
    "index-traffic": {"timeline_id": "index-timeline-1", "time_unit": "minute", "events": [
        {"event_id": "index-a", "start": 5, "end": 12},
        {"event_id": "index-b", "start": 9, "end": 15},
        {"event_id": "index-c", "start": 15, "end": 18},
        {"event_id": "index-d", "start": 25, "end": 31},
        {"event_id": "index-e", "start": 45, "end": 50},
    ]},
    "snapshot-traffic": {"timeline_id": "snapshot-timeline-1", "time_unit": "minute", "events": [
        {"event_id": "snapshot-a", "start": 0, "end": 4},
        {"event_id": "snapshot-b", "start": 3, "end": 7},
        {"event_id": "snapshot-c", "start": 20, "end": 24},
        {"event_id": "snapshot-d", "start": 24, "end": 26},
        {"event_id": "snapshot-e", "start": 40, "end": 44},
    ]},
}

# Edges point from prerequisite to dependent. Both graphs are DAGs. Nodes also
# name isolated packages, which are required only when explicitly targeted.
DEPENDENCY_GRAPHS = {
    "delivery-cli": {"graph_id": "delivery-graph-1",
                     "nodes": ["kernel", "crypto", "transport", "parser", "client", "diagnostics"],
                     "dependencies": [
                         {"prerequisite": "kernel", "dependent": "crypto"},
                         {"prerequisite": "crypto", "dependent": "transport"},
                         {"prerequisite": "kernel", "dependent": "parser"},
                         {"prerequisite": "transport", "dependent": "client"},
                         {"prerequisite": "parser", "dependent": "client"},
                     ]},
    "metrics-agent": {"graph_id": "metrics-graph-1",
                      "nodes": ["base", "codec", "collector", "sender", "agent", "viewer"],
                      "dependencies": [
                          {"prerequisite": "base", "dependent": "codec"},
                          {"prerequisite": "base", "dependent": "collector"},
                          {"prerequisite": "codec", "dependent": "sender"},
                          {"prerequisite": "collector", "dependent": "agent"},
                          {"prerequisite": "sender", "dependent": "agent"},
                      ]},
}

# A failure removes every replica in that domain. A shard is alive if any copy
# survives; counting replicas rather than unique shard IDs can overstate quorum.
SHARD_PLACEMENTS = {
    "archive-stripe": {"placement_id": "archive-placement-1", "k": 3,
                       "domains": ["rack-a", "rack-b", "rack-c", "rack-d"], "replicas": [
                           {"shard_id": "a0", "domain": "rack-a"},
                           {"shard_id": "a0", "domain": "rack-b"},
                           {"shard_id": "a1", "domain": "rack-a"},
                           {"shard_id": "a2", "domain": "rack-b"},
                           {"shard_id": "a2", "domain": "rack-c"},
                           {"shard_id": "a3", "domain": "rack-c"},
                           {"shard_id": "a4", "domain": "rack-c"},
                           {"shard_id": "a4", "domain": "rack-d"},
                       ]},
    "journal-stripe": {"placement_id": "journal-placement-1", "k": 3,
                       "domains": ["rack-x", "rack-y", "rack-z"], "replicas": [
                           {"shard_id": "j0", "domain": "rack-x"},
                           {"shard_id": "j0", "domain": "rack-y"},
                           {"shard_id": "j1", "domain": "rack-y"},
                           {"shard_id": "j2", "domain": "rack-z"},
                           {"shard_id": "j3", "domain": "rack-z"},
                       ]},
}


def _string(maximum):
    return {"type": "string", "minLength": 1, "maxLength": maximum}


def _enum(values):
    return {**_string(64), "enum": list(values)}


def _array(items, minimum, maximum):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def _spec(name, description, properties):
    return {"schema_version": "toolalign.tool.v1", "name": name, "description": description,
            "parameters_json_schema": _object(properties), "tool_version": VERSION,
            "side_effect_class": "read_only", "timeout_ms": 1000}


def specs():
    """Fresh bounded schemas; relationship semantics are visible to callers."""
    return [
        _spec("read_quorum_layout",
              "Read layout_id and ALL partitions with instance IDs and quorum. All instances initially serve. Removals are cumulative across stages; repeats count once. Each partition must retain at least its own quorum at every stage.",
              {"cluster": _enum(QUORUM_LAYOUTS)}),
        _spec("check_quorum_removals",
              "Check a layout_id and removal_stages (ordered arrays of instance IDs). Removals accumulate; repeats count once and empty stages preserve state. Check each partition's remaining count >= quorum at EVERY stage. Unknown IDs are errors; no instances are changed.",
              {"layout_id": _string(64),
               "removal_stages": _array(_array(_string(32), 0, 8), 1, 4)}),
        _spec("read_event_intervals",
              "Read timeline_id and ALL event intervals in integer minutes. Every interval is [start,end). Coverage in a chosen window clips events to that window, then merges overlaps AND adjacent intervals; the complement is uncovered time.",
              {"calendar": _enum(EVENT_TIMELINES)}),
        _spec("measure_interval_coverage",
              "For a timeline_id, measure event union and complement inside integer-minute window [start,end), requiring start < end. Clip first, then merge overlaps and adjacency. Return sorted disjoint covered/uncovered intervals and their lengths; unknown timeline IDs are errors.",
              {"timeline_id": _string(64), "window": _object({
                  "start": {"type": "integer", "minimum": 0, "maximum": 120},
                  "end": {"type": "integer", "minimum": 0, "maximum": 120},
              })}),
        _spec("read_dependency_graph",
              "Read graph_id, ALL nodes (including isolated ones) and DAG edges prerequisite -> dependent. Targets require their transitive prerequisites. A valid installation order contains exactly this required set once each, with prerequisites first; extra nodes are invalid.",
              {"bundle": _enum(DEPENDENCY_GRAPHS)}),
        _spec("check_installation_order",
              "Check targets and installation_order for a graph_id. Required nodes are the targets (repeats ignored) plus transitive prerequisites. Order must cover exactly that set without duplicates and put prerequisites before dependents; extras, including unknown order nodes, are invalid. Unknown graph/target IDs are errors. No packages are installed.",
              {"graph_id": _string(64), "targets": _array(_string(32), 1, 6),
               "installation_order": _array(_string(32), 0, 12)}),
        _spec("read_shard_placement",
              "Read placement_id, k, ALL failure domains and shard replicas. Each failed domain loses all its replicas. A unique shard survives if any copy is in an unfailed domain; recovery requires at least k surviving UNIQUE shard IDs, not k replicas.",
              {"stripe": _enum(SHARD_PLACEMENTS)}),
        _spec("check_shard_recovery",
              "For a placement_id and failed_domains, remove all replicas in those domains and count surviving UNIQUE shard IDs. Any surviving copy keeps a shard alive; recovery holds iff that count >= k. Repeated failures count once, an empty list means no failure, and unknown IDs are errors. No storage is changed.",
              {"placement_id": _string(64), "failed_domains": _array(_string(32), 0, 8)}),
    ]


def _by_id(resources, field, identity):
    for resource in resources.values():
        if resource[field] == identity:
            return resource
    raise ToolFault("unknown_" + field)


def read_quorum_layout(args):
    return deepcopy(QUORUM_LAYOUTS[args["cluster"]])


def check_quorum_removals(args):
    layout = _by_id(QUORUM_LAYOUTS, "layout_id", args["layout_id"])
    known = {instance for row in layout["partitions"] for instance in row["instances"]}
    removed = set()
    stages = []
    for number, stage in enumerate(args["removal_stages"], start=1):
        requested = set(stage)
        if requested - known:
            raise ToolFault("unknown_instance")
        newly_removed = sorted(requested - removed)
        removed.update(requested)
        partitions = []
        for row in layout["partitions"]:
            remaining = len(set(row["instances"]) - removed)
            partitions.append({"partition": row["partition"], "remaining": remaining,
                               "quorum": row["quorum"], "meets_quorum": remaining >= row["quorum"]})
        stages.append({"stage": number, "newly_removed": newly_removed,
                       "removed_total": sorted(removed), "partitions": partitions,
                       "safe": all(row["meets_quorum"] for row in partitions)})
    first_unsafe = next((row["stage"] for row in stages if not row["safe"]), None)
    return {"layout_id": args["layout_id"], "stages": stages,
            "all_stages_safe": first_unsafe is None, "first_unsafe_stage": first_unsafe}


def read_event_intervals(args):
    return deepcopy(EVENT_TIMELINES[args["calendar"]])


def measure_interval_coverage(args):
    timeline = _by_id(EVENT_TIMELINES, "timeline_id", args["timeline_id"])
    start, end = args["window"]["start"], args["window"]["end"]
    if start >= end:
        raise ToolFault("invalid_coverage_window")
    clipped = sorted((max(start, row["start"]), min(end, row["end"]))
                     for row in timeline["events"] if row["start"] < end and row["end"] > start)
    covered = []
    for left, right in clipped:
        if covered and left <= covered[-1]["end"]:
            covered[-1]["end"] = max(covered[-1]["end"], right)
        else:
            covered.append({"start": left, "end": right})
    uncovered = []
    cursor = start
    for interval in covered:
        if cursor < interval["start"]:
            uncovered.append({"start": cursor, "end": interval["start"]})
        cursor = interval["end"]
    if cursor < end:
        uncovered.append({"start": cursor, "end": end})
    covered_units = sum(row["end"] - row["start"] for row in covered)
    return {"timeline_id": args["timeline_id"], "window": dict(args["window"]),
            "covered": covered, "uncovered": uncovered, "covered_units": covered_units,
            "uncovered_units": end - start - covered_units}


def read_dependency_graph(args):
    return deepcopy(DEPENDENCY_GRAPHS[args["bundle"]])


def check_installation_order(args):
    graph = _by_id(DEPENDENCY_GRAPHS, "graph_id", args["graph_id"])
    required = set(args["targets"])
    if required - set(graph["nodes"]):
        raise ToolFault("unknown_target")
    prerequisites = {node: [] for node in graph["nodes"]}
    for edge in graph["dependencies"]:
        prerequisites[edge["dependent"]].append(edge["prerequisite"])
    pending = list(required)
    while pending:
        for prerequisite in prerequisites[pending.pop()]:
            if prerequisite not in required:
                required.add(prerequisite)
                pending.append(prerequisite)
    order = args["installation_order"]
    counts = Counter(order)
    positions = {}
    for index, node in enumerate(order):
        positions.setdefault(node, index)
    missing = sorted(required - counts.keys())
    extra = sorted(counts.keys() - required)
    duplicates = sorted(node for node, count in counts.items() if count > 1)
    violations = [dict(edge) for edge in graph["dependencies"]
                  if edge["dependent"] in required
                  and edge["prerequisite"] in positions and edge["dependent"] in positions
                  and positions[edge["prerequisite"]] >= positions[edge["dependent"]]]
    return {"graph_id": args["graph_id"], "required_nodes": sorted(required),
            "missing_nodes": missing, "extra_nodes": extra, "duplicate_nodes": duplicates,
            "order_violations": violations, "valid": not (missing or extra or duplicates or violations)}


def read_shard_placement(args):
    return deepcopy(SHARD_PLACEMENTS[args["stripe"]])


def check_shard_recovery(args):
    placement = _by_id(SHARD_PLACEMENTS, "placement_id", args["placement_id"])
    failed = set(args["failed_domains"])
    if failed - set(placement["domains"]):
        raise ToolFault("unknown_failure_domain")
    replicas = [row for row in placement["replicas"] if row["domain"] not in failed]
    surviving = {row["shard_id"] for row in replicas}
    all_shards = {row["shard_id"] for row in placement["replicas"]}
    return {"placement_id": args["placement_id"], "failed_domains": sorted(failed),
            "surviving_shards": sorted(surviving), "lost_shards": sorted(all_shards - surviving),
            "surviving_unique_count": len(surviving), "surviving_replica_count": len(replicas),
            "required_shards": placement["k"], "recoverable": len(surviving) >= placement["k"]}


IMPLEMENTATIONS = {
    "read_quorum_layout": read_quorum_layout,
    "check_quorum_removals": check_quorum_removals,
    "read_event_intervals": read_event_intervals,
    "measure_interval_coverage": measure_interval_coverage,
    "read_dependency_graph": read_dependency_graph,
    "check_installation_order": check_installation_order,
    "read_shard_placement": read_shard_placement,
    "check_shard_recovery": check_shard_recovery,
}
