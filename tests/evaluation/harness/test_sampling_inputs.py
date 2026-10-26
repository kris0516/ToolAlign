"""Actual owned-process requests keep sampling and complete unmodified prefixes."""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from test_harness import BY_ID, assert_trace, raw_final, run_case

from toolalign.contracts import canonical_hash, model_input_from_example
from toolalign.contracts.interfaces import ModelOutput, SandboxContext
from toolalign.evaluation.harness import LocalHarness, SamplingParameters
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools.__main__ import development_case
from toolalign.tools.isolation import write_packet
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend


class SamplingSentinel:
    def __init__(self, expected):
        self.expected = expected

    def generate(self, request, config):
        assert set(request) == {"messages", "tools"}
        assert "HIDDEN_SAMPLING_ORACLE" not in json.dumps(request)
        assert (config.seed, config.temperature, config.top_p) == self.expected
        assert config.max_new_tokens == 256 and config.enable_thinking is False
        return ModelOutput(raw_final({"value": 5}), None, None, SCRIPTED_IDENTITY, 9, 4, "stop")


@pytest.mark.parametrize("sampling,expected", [(None, (0, 0.0, 1.0)),
    (SamplingParameters(47, 0.7, 0.9), (47, 0.7, 0.9))])
def test_opt_in_sampling_never_exposes_truth_or_changes_budgets(tmp_path, sampling, expected):
    registry = LocalToolRegistry()
    example, task = development_case(BY_ID["dev-no-tool"], registry)
    example["source_revision"] = "HIDDEN_SAMPLING_ORACLE"
    example["expected_action"]["content"] = "HIDDEN_SAMPLING_ORACLE"
    task = replace(task, expected_action=example["expected_action"])
    context = SandboxContext(tmp_path.resolve(), "sampling-test",
        (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat(), CancellationToken())
    result = LocalHarness(registry, LocalToolExecutor(registry)).run(
        example, task, SamplingSentinel(expected), context,
        model_identity=SCRIPTED_IDENTITY, sampling=sampling)
    assert_trace(result)
    assert result.score.outcome == "success"
    assert result.decision_inputs == [model_input_from_example(example)]
    assert canonical_hash(result.decision_inputs[0]) == result.decisions[0]["model_input_hash"]


def test_actual_observations_and_call_ids_remain_in_successive_inputs(tmp_path):
    registry = LocalToolRegistry()
    case = BY_ID["dev-recovery"]
    example, task = development_case(case, registry)
    context = SandboxContext(tmp_path.resolve(), "sampling-prefix",
        (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat(), CancellationToken())
    result = LocalHarness(registry, LocalToolExecutor(registry, faults=case["faults"])).run(
        example, task, ScriptedCPUModelBackend(case["scripted_responses"]), context,
        model_identity=SCRIPTED_IDENTITY, sampling=SamplingParameters(42, 0.7, 0.9))
    assert_trace(result)
    assert result.score.outcome == "success"
    assert len(result.decision_inputs) == len(result.decisions) == 3
    assert len([p for p in result.process_records if p["label"] == "model"]) == 1
    for index, (request, decision) in enumerate(zip(result.decision_inputs, result.decisions)):
        assert canonical_hash(request) == decision["model_input_hash"]
        assert request["tools"] == example["tools"]
        assert len(request["messages"]) == 1 + 2 * index
    second, third = result.decision_inputs[1:]
    assert second["messages"][-1]["tool_call_id"] == result.decisions[0]["raw_action"]["tool_calls"][0]["call_id"]
    assert json.loads(second["messages"][-1]["content"])["error_code"] == "injected_transient"
    assert json.loads(third["messages"][-1]["content"])["status"] == "completed"


@pytest.mark.parametrize("parameters", [{"seed": -1}, {"temperature": float("nan")}, {"top_p": 0}])
def test_invalid_sampling_is_rejected(parameters):
    with pytest.raises(ValueError, match="invalid_sampling"):
        SamplingParameters(**parameters)


class MalformedTelemetryBackend:
    def generate(self, request, config):
        write_packet(Path("backend-metrics.json"), [])
        return ModelOutput(raw_final({"value": 5}), None, None, SCRIPTED_IDENTITY, 3, 2, "stop")


def test_optional_telemetry_failure_cannot_bypass_owned_child_cleanup(tmp_path):
    result = run_case(tmp_path, "dev-no-tool", backend=MalformedTelemetryBackend())
    assert result.score.outcome == "success"
    assert result.provenance["backend_metrics_error"] == "unreadable_backend_metrics"
    assert not list(tmp_path.iterdir())
