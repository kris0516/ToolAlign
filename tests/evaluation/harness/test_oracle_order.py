"""Causal trace checks use actual public CPU runs before perturbing records."""

import copy

import pytest
from test_harness import BY_ID, raw_call, run_case

from toolalign.contracts import validate_record
from toolalign.evaluation.oracles import SemanticOracle
from toolalign.tools import LocalToolRegistry
from toolalign.tools.__main__ import development_case


def task_for(name="dev-report"):
    return development_case(BY_ID[name], LocalToolRegistry())[1]


def normalize(events):
    """Keep wire validity, identity and monotonic latency separate from causality."""
    for index, event in enumerate(events):
        event["event_index"] = index
        event["latency_ms"] = float(index)
        validate_record(event, "trace")
    return events


@pytest.mark.parametrize(
    "damage",
    [
        "observation_first",
        "duplicate_observation",
        "overlapping_execution",
        "changed_observation_call",
        "unmatched_result_id",
        "missing_execution_call",
        "missing_observation_call",
        "missing_observation_result",
    ],
)
def test_unreliable_tool_order_or_binding_is_unknown(tmp_path, damage):
    result = run_case(tmp_path)
    assert result.score.outcome == "success"
    events = copy.deepcopy(result.trace)
    execution = next(i for i, event in enumerate(events) if event["event"] == "tool_execution")
    observation = next(i for i, event in enumerate(events) if event["event"] == "observing")
    if damage == "observation_first":
        events[execution], events[observation] = events[observation], events[execution]
    elif damage == "duplicate_observation":
        events.insert(observation + 1, copy.deepcopy(events[observation]))
    elif damage == "overlapping_execution":
        events.insert(execution + 1, copy.deepcopy(events[execution]))
    elif damage == "changed_observation_call":
        events[observation]["tool_call"]["arguments"]["report_id"] = "beacon-110"
    elif damage == "unmatched_result_id":
        events[observation]["tool_call"]["call_id"] = "unmatched-result"
        events[observation]["tool_result"]["call_id"] = "unmatched-result"
    elif damage == "missing_execution_call":
        events[execution]["tool_call"] = None
    elif damage == "missing_observation_call":
        events[observation]["tool_call"] = None
    else:
        events[observation]["tool_result"] = None
    score = SemanticOracle().score(task_for(), normalize(events), result.final_result)
    assert score.outcome == "unknown"


@pytest.mark.parametrize("name", ["dev-report", "dev-dependent", "dev-recovery", "dev-no-tool"])
def test_successful_trace_is_valid_before_and_after_terminal_event(tmp_path, name):
    result = run_case(tmp_path, name)
    assert result.score.outcome == "success"
    oracle, task = SemanticOracle(), task_for(name)
    assert result.trace[-1]["event"] == "finalized"
    assert oracle.score(task, result.trace, result.final_result).outcome == "success"
    # LocalHarness calls the oracle before appending its own terminal event.
    assert oracle.score(task, result.trace[:-1], result.final_result).outcome == "success"


@pytest.mark.parametrize("mode", ["unadvertised", "duplicate_call", "tool_error"])
def test_real_execution_failure_remains_failure_with_or_without_observation(tmp_path, mode):
    kwargs = {}
    if mode == "unadvertised":
        kwargs["responses"] = [raw_call("unadvertised-tool")]
    elif mode == "duplicate_call":
        kwargs["responses"] = [raw_call(), raw_call()]
    else:
        kwargs["faults"] = {"query_build_report": ["error"]}
    result = run_case(tmp_path, **kwargs)
    assert result.score.outcome == "failure"
    assert result.trace[-1]["event"] == "rejected"
    assert SemanticOracle().score(task_for(), result.trace, result.final_result).outcome == "failure"


def test_unfinished_execution_remains_failure(tmp_path):
    result = run_case(tmp_path)
    execution = next(
        i for i, event in enumerate(result.trace) if event["event"] == "tool_execution"
    )
    assert SemanticOracle().score(
        task_for(), result.trace[: execution + 1], None
    ).outcome == "failure"
