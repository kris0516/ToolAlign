"""Original CPU cases separate call matching from observation-dependent decisions."""

import copy
import json
import multiprocessing
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from test_cuda_eval import INPUT, request_for, run

from toolalign.contracts import canonical_hash, validate_record
from toolalign.contracts.interfaces import OracleTask
from toolalign.evaluation.cuda_eval.protocol import read_inputs
from toolalign.evaluation.oracles import (
    OBSERVATION_ORACLE_VERSION,
    ObservationOracle,
    SemanticOracle,
    select_oracle,
    validate_observation_task,
)
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.tools import LocalToolRegistry
from toolalign.tools.scripted import ScriptedCPUModelBackend


def action(calls):
    return {"kind": "tool_calls", "content": "", "tool_calls": calls}


def v1_task(task):
    payload = copy.deepcopy(task.oracle_payload)
    payload.pop("after_observation")
    payload["version"] = ORACLE_VERSION
    return replace(task, oracle_payload=payload)


def score(task, result, *, trace=None, final=None):
    return select_oracle(task).score(task, result["trace"] if trace is None else trace,
                                   result["final_result"] if final is None else final)


@pytest.fixture(scope="module")
def owned_cases(tmp_path_factory):
    root = tmp_path_factory.mktemp("observation-owned")
    full = LocalToolRegistry(catalog_id="heldout-devops.v1")
    names = ["read_release_manifest", "read_deployment_snapshot"]
    subset = LocalToolRegistry(names, catalog_id=full.catalog_id)
    calls = [{"call_id": "manifest", "name": names[0],
              "arguments": {"application": "comet-gateway", "release": "4.3.0"}},
             {"call_id": "snapshot", "name": names[1],
              "arguments": {"deployment_id": "comet-green", "snapshot_day": "2026-10-13"}}]
    # Expected values are specified independently of the tool implementation.
    outputs = [{**calls[0]["arguments"], "deployment_id": "comet-green", "artifact_label": "comet-430",
                "desired_replicas": 6, "channel": "canary"},
               {**calls[1]["arguments"], "application": "comet-gateway", "running_release": "4.3.0",
                "ready_replicas": 6, "state": "healthy"}]
    strategy = [{"name": call["name"], "arguments": call["arguments"], "status": "completed",
                 "output": output, "error_code": None, "retryable": False}
                for call, output in zip(calls, outputs)]
    tasks, entries = {}, []
    for name, prompt, edges in [
        ("dependent", "Read comet-gateway release 4.3.0. After observing the manifest, use its deployment_id to read the 2026-10-13 snapshot.", [[0, 1]]),
        ("independent", "Read comet-gateway release 4.3.0 and comet-green's 2026-10-13 snapshot. These two specified reads may be batched.", []),
    ]:
        example = {"schema_version": "toolalign.example.v1", "example_id": name,
            "source": "original-cpu-observation-test", "source_revision": "v1", "license_id": "MIT",
            "source_record_hash": canonical_hash({"original": name}), "group_id": "cpu-only",
            "split": "test", "category": "multi_step", "messages": [{**INPUT["messages"][0],
                "content": prompt + ' Return JSON with keys "desired" and "ready" for the two replica counts.'}],
            "tools": subset.tools, "expected_action": action(calls[:1])}
        task = OracleTask(name, "cpu-only", "test", example["expected_action"],
            {"version": OBSERVATION_ORACLE_VERSION,
             "answers": [{"kind": "final", "value": {"desired": 6, "ready": 6}}],
             "strategies": [copy.deepcopy(strategy)], "after_observation": [edges]})
        validate_observation_task(task)
        tasks[name] = task
        entries.append({"task_id": name, "family_id": "cpu-observation", "group_id": task.group_id,
            "category": "multi_step", "example": example, "oracle_task": asdict(task),
            "faults": {}, "tool_names": names})
    value = {"schema_version": "toolalign.evaluation-tasks.v1", "purpose": "heldout-model-evaluation",
             "catalog": full.catalog_id, "registry_hash": full.registry_hash,
             "tasks": entries, "recovery_task_ids": []}
    request = request_for(root, value, "l1")
    inputs, registries = read_inputs(request["input_path"], request["input_sha256"], "l1")
    final = {"kind": "final", "content": '{"ready":6.0,"desired":6}', "tool_calls": []}

    def backend(unit):
        actions = [action(calls)] if unit["model"] == "M0" else [action([call]) for call in calls]
        return ScriptedCPUModelBackend([json.dumps(item) for item in actions + [final]])

    summary, rows = run(request, inputs, backend, registries)
    return tasks, summary, rows, Path(request["output_dir"])


def test_g5_selects_new_version_keeps_truth_hidden_and_reaps_children(owned_cases):
    tasks, summary, rows, output = owned_cases
    assert summary["terminal_counts"] == {"failure": 1, "success": 3}
    assert len(rows) == 4
    processes = []
    for row in rows:
        task, result = tasks[row["plan"]["task_id"]], row["result"]
        batch = row["plan"]["model"] == "M0"
        assert result["score"]["oracle_version"] == OBSERVATION_ORACLE_VERSION
        assert result["score"]["outcome"] == ("failure" if task.task_id == "dependent" and batch else "success")
        budget = result["trace"][-1]["budget_consumed"]
        assert budget["model_decisions"] == (2 if batch else 3)
        assert budget["tool_rounds"] == (1 if batch else 2)
        assert score(v1_task(task), result).outcome == "success"
        assert score(task, result, trace=result["trace"][:-1]).outcome == result["score"]["outcome"]
        for model_input in result["decision_inputs"]:
            assert set(model_input) == {"messages", "tools"}
            assert "after_observation" not in json.dumps(model_input)
            assert OBSERVATION_ORACLE_VERSION not in json.dumps(model_input)
        processes.extend(result["process_records"])
    assert len(processes) == 12 and all(p["reaped"] and p["exitcode"] is not None for p in processes)
    assert not {p.pid for p in multiprocessing.active_children()} & {p["pid"] for p in processes}
    assert list((output / "sandbox").iterdir()) == []


@pytest.mark.parametrize("damage", ["missing_generation", "missing_parsing", "parsing_before_generation",
                                    "decision_before_observation", "unchanged_decision", "unchanged_round",
                                    "source_observation_counter", "generating_counter", "parsing_counter"])
def test_dependency_requires_events_between_observation_and_successor_with_matching_budgets(owned_cases, damage):
    tasks, _, rows, _ = owned_cases
    task, result = tasks["dependent"], rows[1]["result"]
    events = copy.deepcopy(result["trace"])
    source = next(i for i, e in enumerate(events) if e["event"] == "observing")
    generating, parsing, successor = source + 1, source + 2, source + 3
    assert [events[i]["event"] for i in (generating, parsing, successor)] == ["generating", "parsing", "tool_execution"]
    if damage.startswith("missing_"):
        del events[generating if damage == "missing_generation" else parsing]
    elif damage == "parsing_before_generation":
        events[generating], events[parsing] = events[parsing], events[generating]
    elif damage == "decision_before_observation":
        pair = events[generating:parsing + 1]
        del events[generating:parsing + 1]
        events[source:source] = pair
    elif damage in ("unchanged_decision", "unchanged_round"):
        key = "model_decisions" if damage == "unchanged_decision" else "tool_rounds"
        events[successor]["budget_consumed"][key] = events[source]["budget_consumed"][key]
    else:
        index = {"source_observation_counter": source, "generating_counter": generating,
                 "parsing_counter": parsing}[damage]
        events[index]["budget_consumed"]["model_decisions"] += 1
    for index, event in enumerate(events):
        event["event_index"], event["latency_ms"] = index, float(index)
        validate_record(event, "trace")
    assert score(v1_task(task), result, trace=events).outcome == "success"
    assert score(task, result, trace=events).outcome == "failure"


@pytest.mark.parametrize("damage", ["missing_edges", "wrong_length", "bad_edge", "negative", "reversed",
                                    "boolean", "out_of_range", "unsupported_version", "missing_answers",
                                    "malformed_other_strategy", "malformed_answer"])
def test_incomplete_or_unsupported_truth_is_unknown_even_when_another_strategy_matches(owned_cases, damage):
    tasks, _, rows, _ = owned_cases
    task, result = tasks["dependent"], rows[1]["result"]
    payload = copy.deepcopy(task.oracle_payload)
    if damage == "missing_edges":
        del payload["after_observation"]
    elif damage == "wrong_length":
        payload["after_observation"] = []
    elif damage in ("bad_edge", "negative", "reversed", "boolean", "out_of_range"):
        payload["after_observation"] = [[{"bad_edge": [0], "negative": [-1, 1], "reversed": [1, 0],
                                         "boolean": [False, 1], "out_of_range": [0, 2]}[damage]]]
    elif damage == "unsupported_version":
        payload["version"] = "toolalign.future.v99"
    elif damage == "missing_answers":
        del payload["answers"]
    elif damage == "malformed_answer":
        payload["answers"].append({"kind": "unsupported", "value": 6})
    else:
        payload["strategies"].append([{"name": "incomplete"}])
        payload["after_observation"].append([])
    changed = replace(task, oracle_payload=payload)
    with pytest.raises(ValueError):
        validate_observation_task(changed)
    assert score(changed, result).outcome == "unknown"


def test_alternatives_match_their_own_edges_and_numeric_equivalence_does_not_admit_bool(owned_cases):
    tasks, _, rows, _ = owned_cases
    task, batched, separate = tasks["dependent"], rows[0]["result"], rows[1]["result"]
    payload = copy.deepcopy(task.oracle_payload)
    other = copy.deepcopy(payload["strategies"][0])
    other[0]["arguments"]["release"] = "4.2.0"
    payload["strategies"].insert(0, other)
    payload["after_observation"].insert(0, [])
    changed = replace(task, oracle_payload=payload)
    assert score(changed, batched).outcome == "failure"
    assert score(changed, separate).outcome == "success"
    # An explicitly permitted independent alternative may accept that same batch.
    payload["strategies"].append(copy.deepcopy(payload["strategies"][1]))
    payload["after_observation"].append([])
    assert score(changed, batched).outcome == "success"
    assert score(task, separate, final=separate["final_result"] | {
        "content": '{"ready":true,"desired":6}'}).outcome == "failure"


def test_explicit_selection_retains_v1_and_validation_returns_a_copy(owned_cases):
    tasks, _, rows, _ = owned_cases
    task = tasks["dependent"]
    assert type(select_oracle(v1_task(task))) is SemanticOracle
    assert type(select_oracle(task)) is ObservationOracle
    copied = validate_observation_task(task)
    copied["after_observation"][0].clear()
    assert task.oracle_payload["after_observation"] == [[[0, 1]]]
    for invalid in ({}, None, {"version": "future"}):
        assert score(replace(task, oracle_payload=invalid), rows[0]["result"]).outcome == "unknown"
    events = copy.deepcopy(rows[1]["result"]["trace"])
    events[0]["request_id"] = "mixed"
    assert score(task, rows[1]["result"], trace=events).outcome == "unknown"


@pytest.mark.parametrize("kind", ["final", "clarify", "refuse"])
def test_no_tool_answer_requires_explicit_empty_dependencies(kind):
    final = {"kind": kind, "content": '"original-answer"', "tool_calls": []}
    task = OracleTask("original-no-tool", "cpu-only", "test", final,
        {"version": OBSERVATION_ORACLE_VERSION,
         "answers": [{"kind": kind, "value": "original-answer"}],
         "strategies": [[]], "after_observation": [[]]})
    assert select_oracle(task).score(task, [], final).outcome == "success"
    task.oracle_payload["after_observation"] = [[[0, 1]]]
    assert select_oracle(task).score(task, [], final).outcome == "unknown"
