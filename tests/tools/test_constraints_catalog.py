"""Original relation checks, separate from D1's final evaluation task set."""

import hashlib
import json
from dataclasses import asdict
from graphlib import TopologicalSorter
from importlib.resources import files
from itertools import combinations, permutations

import pytest
from test_registry_executor import assert_reaped, call, context

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import Rejection, ValidatedCall
from toolalign.tools import LocalToolExecutor, LocalToolRegistry
from toolalign.tools import constraints_catalog as c
from toolalign.tools.catalog import ToolFault


@pytest.mark.parametrize("catalog_id,filename,source,tools,registry_hash", [
    ("local-devops.v1", "catalog.py",
     "8c89c7f2b4a4bc64952791b66954542cf328f814b07a9ba1c3f3e70b5e236792",
     "bbb7b2de3f520880764e7600c7361e757dcdb418c48fd3da50bf78e004164ced",
     "6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8"),
    ("heldout-devops.v1", "heldout_catalog.py",
     "a13735a3cfd1ec5d3f638504d01d500438248d8efe545c97be085999b2046996",
     "dad585965462ac0625c3146c33b8e4807cf99c9b72501d72ad4a00a2f686cc70",
     "66d47196bd207542325c89244a7fbafd2163f14c01e9aeb36e40553e01c7f037"),
])
def test_old_catalog_bytes_specs_and_manifests_match_authorized_base(
    catalog_id, filename, source, tools, registry_hash,
):
    registry = LocalToolRegistry(catalog_id=catalog_id)
    assert hashlib.sha256(files("toolalign.tools").joinpath(filename).read_bytes()).hexdigest() == source
    assert canonical_hash(registry.tools) == tools
    assert canonical_hash(registry.manifest) == registry.registry_hash == registry_hash
    if catalog_id == "local-devops.v1":
        assert LocalToolRegistry().manifest == registry.manifest


def test_new_catalog_is_source_bound_and_exposes_eight_bounded_read_only_tools():
    registry = LocalToolRegistry(catalog_id=c.VERSION)
    source = hashlib.sha256(files("toolalign.tools").joinpath("constraints_catalog.py").read_bytes()).hexdigest()
    assert set(c.DOMAIN_TOOLS) == {"releases", "incidents", "packages", "storage"}
    assert all(len(names) == 2 for names in c.DOMAIN_TOOLS.values())
    assert {row["name"] for row in registry.tools} == set(c.IMPLEMENTATIONS) == {
        name for names in c.DOMAIN_TOOLS.values() for name in names
    }
    assert len(registry.tools) == 8
    for row in registry.manifest["tools"]:
        assert row["source_hash"] == source
        assert row["implementation"] == "toolalign.tools.constraints_catalog:" + row["spec"]["name"]
        assert row["schema_hash"] == canonical_hash(row["spec"]["parameters_json_schema"])
        assert row["spec"]["side_effect_class"] == "read_only"
        assert row["spec"]["tool_version"] == c.VERSION


@pytest.mark.parametrize("domain,first_args", [
    ("releases", {"cluster": "search-ring"}),
    ("incidents", {"calendar": "index-traffic"}),
    ("packages", {"bundle": "delivery-cli"}),
    ("storage", {"stripe": "journal-stripe"}),
])
def test_eight_tools_execute_in_owned_children_with_observation_derived_parameters(
    tmp_path, domain, first_args,
):
    first_name, second_name = c.DOMAIN_TOOLS[domain]
    registry = LocalToolRegistry(c.DOMAIN_TOOLS[domain], catalog_id=c.VERSION)
    executor = LocalToolExecutor(registry)
    first = executor.execute(registry.validate(call(first_name, first_args)), context(tmp_path))
    assert first.status == "completed"
    observed = first.output
    if domain == "releases":
        partition = observed["partitions"][0]
        allowance = len(partition["instances"]) - partition["quorum"]
        second_args = {"layout_id": observed["layout_id"], "removal_stages": [
            partition["instances"][:allowance], [partition["instances"][allowance]]],
        }
        expected = {"all_stages_safe": False, "first_unsafe_stage": 2}
    elif domain == "incidents":
        second_args = {"timeline_id": observed["timeline_id"], "window": {
            "start": observed["events"][0]["end"], "end": observed["events"][3]["start"] + 3,
        }}
        expected = {"covered_units": 9, "uncovered_units": 7}
    elif domain == "packages":
        predecessors = {}
        for edge in observed["dependencies"]:
            predecessors.setdefault(edge["dependent"], []).append(edge["prerequisite"])
        second_args = {"graph_id": observed["graph_id"], "targets": ["client"],
                       "installation_order": list(TopologicalSorter(predecessors).static_order())}
        expected = {"valid": True, "required_nodes": ["client", "crypto", "kernel", "parser", "transport"]}
    else:
        second_args = {"placement_id": observed["placement_id"],
                       "failed_domains": [observed["replicas"][-1]["domain"]]}
        expected = {"recoverable": False, "surviving_unique_count": 2, "surviving_replica_count": 3}
    issued = registry.validate(call(second_name, second_args))
    assert isinstance(issued, ValidatedCall)
    second = executor.execute(issued, context(tmp_path))
    assert second.status == "completed"
    assert all(second.output[key] == value for key, value in expected.items())
    assert len(executor.process_records) == 2
    assert all(row["operation_started"] and row["directory_cleaned"] for row in executor.process_records)
    assert_reaped(executor.process_records)
    assert not list(tmp_path.glob("toolalign-owned-*"))
    (tmp_path / "execution-evidence.json").write_text(json.dumps({
        "catalog": registry.catalog_id, "registry_hash": registry.registry_hash,
        "manifest": registry.manifest, "calls": [call(first_name, first_args), call(second_name, second_args)],
        "results": [asdict(first), asdict(second)], "process_records": executor.process_records,
    }, indent=2) + "\n")


def test_quorum_is_cumulative_per_partition_and_repeated_removals_count_once():
    result = c.check_quorum_removals({"layout_id": "search-layout-1", "removal_stages": [
        ["e1", "e1"], ["e1", "w1", "w2"], ["e2"], [],
    ]})
    assert [stage["safe"] for stage in result["stages"]] == [True, True, False, False]
    assert [[p["remaining"] for p in stage["partitions"]] for stage in result["stages"]] == [
        [2, 4], [2, 2], [1, 2], [1, 2],
    ]
    assert [s["newly_removed"] for s in result["stages"]] == [["e1"], ["w1", "w2"], ["e2"], []]
    assert result["first_unsafe_stage"] == 3 and result["all_stages_safe"] is False
    # The global remaining count is five, yet east is already below its quorum.
    separate = c.check_quorum_removals({"layout_id": "search-layout-1", "removal_stages": [["e1", "e2"]]})
    assert separate["first_unsafe_stage"] == 1
    assert [p["remaining"] for p in separate["stages"][0]["partitions"]] == [1, 4]
    unchanged = c.check_quorum_removals({"layout_id": "session-layout-1", "removal_stages": [[]]})
    assert unchanged["all_stages_safe"] and unchanged["first_unsafe_stage"] is None


@pytest.mark.parametrize("start,end,covered,uncovered", [
    (10, 28, [(10, 18), (25, 28)], [(18, 25)]),
    (18, 25, [], [(18, 25)]),
    (15, 18, [(15, 18)], []),
    (0, 120, [(5, 18), (25, 31), (45, 50)], [(0, 5), (18, 25), (31, 45), (50, 120)]),
])
def test_intervals_clip_then_merge_overlap_and_adjacency(start, end, covered, uncovered):
    result = c.measure_interval_coverage({"timeline_id": "index-timeline-1", "window": {"start": start, "end": end}})
    assert result["covered"] == [{"start": a, "end": b} for a, b in covered]
    assert result["uncovered"] == [{"start": a, "end": b} for a, b in uncovered]
    assert result["covered_units"] == sum(b - a for a, b in covered)
    assert result["uncovered_units"] == sum(b - a for a, b in uncovered)


def test_both_interval_resources_match_independent_integer_tick_sets():
    for resource in c.EVENT_TIMELINES.values():
        occupied = {tick for e in resource["events"] for tick in range(e["start"], e["end"])}
        assert all(0 <= e["start"] < e["end"] <= 120 for e in resource["events"])
        for start, end in combinations(range(51), 2):
            result = c.measure_interval_coverage({"timeline_id": resource["timeline_id"],
                                                  "window": {"start": start, "end": end}})
            window = set(range(start, end))
            for field, expected in (("covered", window & occupied), ("uncovered", window - occupied)):
                intervals = result[field]
                assert {t for row in intervals for t in range(row["start"], row["end"])} == expected
                assert all(a["end"] < b["start"] for a, b in zip(intervals, intervals[1:]))
                assert result[field + "_units"] == len(expected)


@pytest.mark.parametrize("order,valid,missing,extra,duplicates,violations", [
    (["kernel", "crypto", "parser", "transport", "client"], True, [], [], [], []),
    (["kernel", "parser", "crypto", "transport", "client"], True, [], [], [], []),
    (["crypto", "transport", "parser", "client"], False, ["kernel"], [], [], []),
    (["kernel", "crypto", "parser", "transport", "client", "diagnostics"], False, [], ["diagnostics"], [], []),
    (["kernel", "crypto", "parser", "transport", "client", "ghost"], False, [], ["ghost"], [], []),
    (["kernel", "crypto", "parser", "transport", "client", "client"], False, [], [], ["client"], []),
    (["kernel", "transport", "crypto", "parser", "client"], False, [], [], [], [
        {"prerequisite": "crypto", "dependent": "transport"}]),
    ([], False, ["client", "crypto", "kernel", "parser", "transport"], [], [], []),
])
def test_installation_requires_exact_transitive_closure_and_valid_order(
    order, valid, missing, extra, duplicates, violations,
):
    result = c.check_installation_order({"graph_id": "delivery-graph-1", "targets": ["client", "client"],
                                       "installation_order": order})
    assert result == {"graph_id": "delivery-graph-1", "required_nodes": ["client", "crypto", "kernel", "parser", "transport"],
                      "missing_nodes": missing, "extra_nodes": extra, "duplicate_nodes": duplicates,
                      "order_violations": violations, "valid": valid}


def test_fixed_graphs_are_acyclic_and_all_target_orders_match_edge_precedence():
    for graph, target, isolated, expected in [
        (c.DEPENDENCY_GRAPHS["delivery-cli"], "client", "diagnostics", {"kernel", "crypto", "parser", "transport", "client"}),
        (c.DEPENDENCY_GRAPHS["metrics-agent"], "agent", "viewer", {"base", "codec", "collector", "sender", "agent"}),
    ]:
        predecessors = {node: [] for node in graph["nodes"]}
        for edge in graph["dependencies"]:
            predecessors[edge["dependent"]].append(edge["prerequisite"])
        assert set(TopologicalSorter(predecessors).static_order()) == set(graph["nodes"])
        for order in permutations(sorted(expected)):
            result = c.check_installation_order({"graph_id": graph["graph_id"], "targets": [target],
                                               "installation_order": list(order)})
            assert set(result["required_nodes"]) == expected
            assert result["valid"] == all(order.index(e["prerequisite"]) < order.index(e["dependent"])
                                          for e in graph["dependencies"])
        isolated_result = c.check_installation_order({"graph_id": graph["graph_id"], "targets": [isolated],
                                                     "installation_order": [isolated]})
        assert isolated_result["required_nodes"] == [isolated] and isolated_result["valid"]
    multiple = c.check_installation_order({"graph_id": "delivery-graph-1", "targets": ["parser", "diagnostics"],
                                         "installation_order": ["diagnostics", "kernel", "parser"]})
    assert multiple["valid"] and multiple["required_nodes"] == ["diagnostics", "kernel", "parser"]


@pytest.mark.parametrize("placement,failed,alive,copies,recoverable", [
    ("archive-placement-1", [], ["a0", "a1", "a2", "a3", "a4"], 8, True),
    ("archive-placement-1", ["rack-a", "rack-b"], ["a2", "a3", "a4"], 4, True),
    ("archive-placement-1", ["rack-a", "rack-b", "rack-c"], ["a4"], 1, False),
    ("archive-placement-1", ["rack-a", "rack-b", "rack-c", "rack-d"], [], 0, False),
    ("journal-placement-1", ["rack-z", "rack-z"], ["j0", "j1"], 3, False),
    ("journal-placement-1", ["rack-x"], ["j0", "j1", "j2", "j3"], 4, True),
])
def test_shard_failures_count_unique_survivors_and_include_equality_at_k(
    placement, failed, alive, copies, recoverable,
):
    result = c.check_shard_recovery({"placement_id": placement, "failed_domains": failed})
    assert result["surviving_shards"] == alive
    assert result["surviving_unique_count"] == len(alive)
    assert result["surviving_replica_count"] == copies
    assert result["required_shards"] == 3 and result["recoverable"] is recoverable
    assert not set(result["lost_shards"]) & set(alive)
    assert result["failed_domains"] == sorted(set(failed))


@pytest.mark.parametrize("function,selector,resources,field", [
    (c.read_quorum_layout, "cluster", c.QUORUM_LAYOUTS, "partitions"),
    (c.read_event_intervals, "calendar", c.EVENT_TIMELINES, "events"),
    (c.read_dependency_graph, "bundle", c.DEPENDENCY_GRAPHS, "dependencies"),
    (c.read_shard_placement, "stripe", c.SHARD_PLACEMENTS, "replicas"),
])
def test_single_reads_return_complete_relations_without_aliasing_source(function, selector, resources, field):
    for key, expected in resources.items():
        output = function({selector: key})
        assert output == expected and len(output[field]) > 1
        output[field][0].clear()
        output[field].clear()
        assert function({selector: key}) == expected and expected[field][0]


@pytest.mark.parametrize("name,args,code", [
    ("check_quorum_removals", {"layout_id": "search-layout-1", "removal_stages": [["ghost"]]}, "unknown_instance"),
    ("check_quorum_removals", {"layout_id": "absent", "removal_stages": [[]]}, "unknown_layout_id"),
    ("measure_interval_coverage", {"timeline_id": "index-timeline-1", "window": {"start": 10, "end": 10}}, "invalid_coverage_window"),
    ("measure_interval_coverage", {"timeline_id": "index-timeline-1", "window": {"start": 11, "end": 10}}, "invalid_coverage_window"),
    ("measure_interval_coverage", {"timeline_id": "absent", "window": {"start": 0, "end": 1}}, "unknown_timeline_id"),
    ("check_installation_order", {"graph_id": "delivery-graph-1", "targets": ["ghost"], "installation_order": []}, "unknown_target"),
    ("check_installation_order", {"graph_id": "absent", "targets": ["client"], "installation_order": []}, "unknown_graph_id"),
    ("check_shard_recovery", {"placement_id": "journal-placement-1", "failed_domains": ["ghost"]}, "unknown_failure_domain"),
    ("check_shard_recovery", {"placement_id": "absent", "failed_domains": []}, "unknown_placement_id"),
])
def test_relationship_errors_are_explicit(name, args, code):
    assert isinstance(LocalToolRegistry(catalog_id=c.VERSION).validate(call(name, args)), ValidatedCall)
    with pytest.raises(ToolFault, match="^" + code + "$"):
        c.IMPLEMENTATIONS[name](args)


@pytest.mark.parametrize("name,args", [
    ("read_quorum_layout", {"cluster": "unknown"}),
    ("read_event_intervals", {}),
    ("read_dependency_graph", {"bundle": "delivery-cli", "path": "/tmp/graph"}),
    ("read_shard_placement", {"stripe": "journal-stripe", "k": 1}),
    ("check_quorum_removals", {"layout_id": "search-layout-1", "removal_stages": []}),
    ("check_quorum_removals", {"layout_id": "search-layout-1", "removal_stages": [["e1"] * 9]}),
    ("check_quorum_removals", {"layout_id": "search-layout-1", "removal_stages": [[]] * 5}),
    ("measure_interval_coverage", {"timeline_id": "index-timeline-1", "window": {"start": 0, "end": 121}}),
    ("measure_interval_coverage", {"timeline_id": "index-timeline-1", "window": {"start": True, "end": 10}}),
    ("check_installation_order", {"graph_id": "delivery-graph-1", "targets": [], "installation_order": []}),
    ("check_installation_order", {"graph_id": "delivery-graph-1", "targets": ["client"], "installation_order": ["client"] * 13}),
    ("check_shard_recovery", {"placement_id": "journal-placement-1", "failed_domains": ["rack-z"] * 9}),
])
def test_resource_selectors_and_nested_input_bounds_reject_before_execution(name, args):
    rejected = LocalToolRegistry(catalog_id=c.VERSION).validate(call(name, args))
    assert isinstance(rejected, Rejection) and rejected.code == "invalid_arguments"
