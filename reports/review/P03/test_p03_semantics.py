"""R1-authored counterexamples over public fictional resources, with real tools.

These are CPU implementation checks, not hidden tasks or model-quality measurements.
The backend receives independently supplied scripts; it never receives OracleTask.
"""

from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from importlib.resources import files

import pytest
from test_p03_lifecycle import context, no_tool_task

from toolalign.contracts import ContractError, canonical_hash, validate_record
from toolalign.contracts.interfaces import ModelOutput, OracleTask, ValidatedCall
from toolalign.evaluation.harness import LocalHarness, summarize
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION, SemanticOracle
from toolalign.tools import LocalToolExecutor, LocalToolRegistry
from toolalign.tools._json import decode
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend

BEACON_DOCUMENT = {
    "resource_id": "beacon-1.1",
    "object": "beacon",
    "version": "1.1",
    "date": "2026-09-01",
    "timeout_ms": 900,
    "minimum_runtime": "3.11",
    "report_id": "beacon-110",
}
BEACON_REPORT = {
    "report_id": "beacon-110",
    "object": "beacon",
    "version": "1.1",
    "date": "2026-09-01",
    "passed": 9,
    "failed": 1,
    "duration_ms": 900,
}

# Explicit independent answers and full tool observations; no calls to catalog functions.
SCENARIOS = [
    {
        "id": "beacon-document",
        "name": "lookup_version_document",
        "prompt": "Read beacon-1.1 and report its object, release date and timeout_ms.",
        "arguments": {"resource_id": "beacon-1.1"},
        "wrong_arguments": {"resource_id": "atlas-1.1"},
        "output": BEACON_DOCUMENT,
        "answer": {"object": "beacon", "date": "2026-09-01", "timeout_ms": 900},
    },
    {
        "id": "old-atlas-report",
        "name": "query_build_report",
        "prompt": "Query atlas-100 and return its version, date and failed test count.",
        "arguments": {"report_id": "atlas-100"},
        "wrong_arguments": {"report_id": "atlas-110"},
        "output": {
            "report_id": "atlas-100",
            "object": "atlas",
            "version": "1.0",
            "date": "2026-08-01",
            "passed": 8,
            "failed": 2,
            "duration_ms": 800,
        },
        "answer": {"version": "1.0", "date": "2026-08-01", "failed": 2},
    },
    {
        "id": "beacon-error-day",
        "name": "filter_build_logs",
        "prompt": "Count beacon-september error entries dated 2026-09-01.",
        "arguments": {"resource_id": "beacon-september", "date": "2026-09-01", "level": "error"},
        "wrong_arguments": {
            "resource_id": "beacon-september",
            "date": "2026-09-02",
            "level": "error",
        },
        "output": {
            "resource_id": "beacon-september",
            "date": "2026-09-01",
            "level": "error",
            "rows": [
                {"date": "2026-09-01", "level": "error", "message": "Build beacon-110 failed"}
            ],
            "count": 1,
        },
        "answer": {"resource_id": "beacon-september", "date": "2026-09-01", "count": 1},
    },
    {
        "id": "atlas-failure-sum",
        "name": "aggregate_run_records",
        "prompt": "Use sum on the failed field for atlas-runs on 2026-09-02; return total_failed.",
        "arguments": {
            "resource_id": "atlas-runs",
            "date": "2026-09-02",
            "field": "failed",
            "operation": "sum",
        },
        "wrong_arguments": {
            "resource_id": "atlas-runs",
            "date": "2026-09-02",
            "field": "failed",
            "operation": "mean",
        },
        "output": {
            "resource_id": "atlas-runs",
            "date": "2026-09-02",
            "field": "failed",
            "operation": "sum",
            "value": 1,
            "count": 1,
        },
        "answer": {"total_failed": 1},
    },
    {
        "id": "beacon-runtime",
        "name": "compare_version_compatibility",
        "prompt": "Check beacon-1.1 against runtime 3.12 and report the runtime and compatible flag.",
        "arguments": {"resource_id": "beacon-1.1", "runtime_version": "3.12"},
        "wrong_arguments": {"resource_id": "beacon-1.1", "runtime_version": "3.11"},
        "output": {
            "resource_id": "beacon-1.1",
            "runtime_version": "3.12",
            "minimum_runtime": "3.11",
            "compatible": True,
        },
        "answer": {"runtime_version": "3.12", "compatible": True},
    },
    {
        "id": "negative-time",
        "name": "convert_numeric_units",
        "prompt": "Use the conversion tool on -2.5 minutes to milliseconds; return value and unit.",
        "arguments": {"value": -2.5, "from_unit": "min", "to_unit": "ms"},
        "wrong_arguments": {"value": -2.5, "from_unit": "s", "to_unit": "ms"},
        "output": {"value": -2.5, "from_unit": "min", "to_unit": "ms", "converted_value": -150000},
        "answer": {"value": -150000, "unit": "ms"},
    },
]


def call_action(name, arguments, call_id="r1-c1"):
    return {
        "kind": "tool_calls",
        "content": "",
        "tool_calls": [
            {"call_id": call_id, "name": name, "arguments": copy.deepcopy(arguments)},
        ],
    }


def answer_action(answer, kind="final"):
    return {"kind": kind, "content": json.dumps(answer), "tool_calls": []}


def expected_step(name, arguments, output, *, status="completed", code=None, retryable=False):
    return {
        "name": name,
        "arguments": copy.deepcopy(arguments),
        "status": status,
        "output": copy.deepcopy(output),
        "error_code": code,
        "retryable": retryable,
    }


def make_task(registry, scenario):
    example, _ = no_tool_task()
    example.update(
        example_id="r1-" + scenario["id"],
        group_id="r1-" + scenario["id"],
        category=scenario["name"],
        tools=registry.tools,
        expected_action=call_action(scenario["name"], scenario["arguments"]),
    )
    example["messages"][0]["content"] = scenario["prompt"]
    task = OracleTask(
        example["example_id"],
        example["group_id"],
        "validation",
        example["expected_action"],
        {
            "version": ORACLE_VERSION,
            "answers": [{"kind": "final", "value": scenario["answer"]}],
            "strategies": [
                [expected_step(scenario["name"], scenario["arguments"], scenario["output"])]
            ],
        },
    )
    return validate_record(example, "example"), task


def run_scenario(tmp_path, scenario, actions, *, task_change=None, faults=None, backend=None):
    registry = LocalToolRegistry()
    example, task = make_task(registry, scenario)
    if task_change:
        task = task_change(task)
    result = LocalHarness(registry, LocalToolExecutor(registry, faults=faults)).run(
        example,
        task,
        backend or ScriptedCPUModelBackend([json.dumps(item) for item in actions]),
        context(tmp_path),
        model_identity=SCRIPTED_IDENTITY,
    )
    assert result.trace[-1]["task_outcome"]["outcome"] == result.score.outcome
    assert all(item["reaped"] and item["exitcode"] is not None for item in result.process_records)
    live = {item.pid for item in multiprocessing.active_children()}
    assert not live.intersection(item["pid"] for item in result.process_records)
    for index, event in enumerate(result.trace):
        validate_record(event, "trace")
        assert event["event_index"] == index
    for before, after in zip(result.trace, result.trace[1:]):
        assert after["latency_ms"] >= before["latency_ms"]
        assert before["deadline_utc"] == after["deadline_utc"]
        assert all(
            after["budget_consumed"][key] >= value
            for key, value in before["budget_consumed"].items()
        )
    return result


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: item["id"])
@pytest.mark.parametrize("wrong_target", [False, True], ids=["correct", "wrong-but-schema-valid"])
def test_full_semantics_distinguish_all_six_tool_categories(tmp_path, scenario, wrong_target):
    arguments = scenario["wrong_arguments"] if wrong_target else scenario["arguments"]
    result = run_scenario(
        tmp_path,
        scenario,
        [
            call_action(scenario["name"], arguments),
            answer_action(scenario["answer"]),
        ],
    )
    observations = [event["tool_result"] for event in result.trace if event["event"] == "observing"]
    assert len(observations) == 1 and observations[0]["status"] == "completed"
    assert result.score.outcome == ("failure" if wrong_target else "success")
    assert result.budget["model_decisions"] == 2 and result.budget["tool_rounds"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", "1.1"),
        ("date", "2026-09-01"),
        ("failed", 0),
        ("failed", True),
    ],
)
def test_correct_execution_cannot_validate_wrong_final_fields(tmp_path, field, value):
    scenario = SCENARIOS[1]
    answer = {**scenario["answer"], field: value}
    result = run_scenario(
        tmp_path,
        scenario,
        [
            call_action(scenario["name"], scenario["arguments"]),
            answer_action(answer),
        ],
    )
    assert result.score.outcome == "failure"


@pytest.mark.parametrize("with_conversion", [False, True])
def test_explicit_alternate_units_and_legal_strategy_both_pass(tmp_path, with_conversion):
    scenario = SCENARIOS[0]
    conversion = {"value": 900, "from_unit": "ms", "to_unit": "s"}
    alternate = {"object": "beacon", "date": "2026-09-01", "timeout_seconds": 0.9}

    def truth(task):
        payload = copy.deepcopy(task.oracle_payload)
        payload["answers"].append({"kind": "final", "value": alternate})
        payload["strategies"].append(
            payload["strategies"][0]
            + [
                expected_step(
                    "convert_numeric_units",
                    conversion,
                    {**conversion, "converted_value": 0.9},
                )
            ]
        )
        return replace(task, oracle_payload=payload)

    actions = [call_action(scenario["name"], scenario["arguments"])]
    if with_conversion:
        actions.append(call_action("convert_numeric_units", conversion, "r1-c2"))
    actions.append(answer_action(alternate))
    assert run_scenario(tmp_path, scenario, actions, task_change=truth).score.outcome == "success"


class ObservationDrivenBackend:
    """Read ordinary tool observations; inspect no host-side truth or labels."""

    def __init__(self):
        self.step = 0

    def generate(self, request, generation_config):
        assert set(request) == {"messages", "tools"}
        assert "R1_HOST_ONLY_TRUTH_SENTINEL" not in json.dumps(request)
        assert generation_config.enable_thinking is False
        observations = [item for item in request["messages"] if item["role"] == "tool"]
        if self.step == 0:
            action = call_action("lookup_version_document", {"resource_id": "beacon-1.1"})
        elif self.step == 1:
            observed = json.loads(observations[-1]["content"])["output"]
            action = call_action(
                "query_build_report", {"report_id": observed["report_id"]}, "r1-c2"
            )
        else:
            observed = json.loads(observations[-1]["content"])["output"]
            action = answer_action(
                {key: observed[key] for key in ("report_id", "passed", "failed")}
            )
        self.step += 1
        return ModelOutput(json.dumps(action), None, None, SCRIPTED_IDENTITY, 17, 19, "stop")


def test_real_multistep_observations_without_oracle_metadata(tmp_path):
    registry = LocalToolRegistry()
    example, task = make_task(registry, SCENARIOS[0])
    example["source_revision"] = "R1_HOST_ONLY_TRUTH_SENTINEL"
    example["expected_action"]["content"] = "R1_HOST_ONLY_TRUTH_SENTINEL"
    task = replace(
        task,
        expected_action=copy.deepcopy(example["expected_action"]),
        oracle_payload={
            "version": ORACLE_VERSION,
            "answers": [
                {"kind": "final", "value": {"report_id": "beacon-110", "passed": 9, "failed": 1}},
                {"kind": "final", "value": {"unused": "R1_HOST_ONLY_TRUTH_SENTINEL"}},
            ],
            "strategies": [
                [
                    expected_step(
                        "lookup_version_document", {"resource_id": "beacon-1.1"}, BEACON_DOCUMENT
                    ),
                    expected_step("query_build_report", {"report_id": "beacon-110"}, BEACON_REPORT),
                ]
            ],
        },
    )
    result = LocalHarness(registry, LocalToolExecutor(registry)).run(
        example,
        task,
        ObservationDrivenBackend(),
        context(tmp_path),
        model_identity=SCRIPTED_IDENTITY,
    )
    assert result.score.outcome == "success"
    assert result.budget == {
        "model_decisions": 3,
        "tool_rounds": 2,
        "input_tokens": 51,
        "output_tokens": 57,
    }
    assert len(result.process_records) == 3 and all(
        item["reaped"] for item in result.process_records
    )
    model_records = [item for item in result.process_records if item["label"] == "model"]
    assert len(model_records) == 1


@pytest.mark.parametrize(
    "kind,value",
    [
        ("clarify", {"missing": ["report_id"]}),
        ("refuse", {"reason": "external_write_not_supported"}),
    ],
)
def test_no_tool_clarification_and_refusal_match_explicit_policy(tmp_path, kind, value):
    registry = LocalToolRegistry()
    example, task = no_tool_task()
    example["messages"][0]["content"] = "No report ID is supplied; do not perform external writes."
    task = replace(
        task,
        oracle_payload={
            "version": ORACLE_VERSION,
            "answers": [{"kind": kind, "value": value}],
            "strategies": [[]],
        },
    )
    result = LocalHarness(registry, LocalToolExecutor(registry)).run(
        example,
        task,
        ScriptedCPUModelBackend([json.dumps(answer_action(value, kind))]),
        context(tmp_path),
        model_identity=SCRIPTED_IDENTITY,
    )
    assert result.score.outcome == "success" and result.budget["tool_rounds"] == 0
    assert len(result.process_records) == 1


@pytest.mark.parametrize("damage", ["missing_truth", "unknown_version", "invalid_status"])
def test_unknown_truth_keeps_the_task_in_the_denominator(tmp_path, damage):
    scenario = SCENARIOS[1]

    def truth(task):
        payload = copy.deepcopy(task.oracle_payload)
        if damage == "missing_truth":
            payload = {}
        elif damage == "unknown_version":
            payload["version"] = "unsupported"
        else:
            payload["strategies"][0][0]["status"] = "unsupported"
        return replace(task, oracle_payload=payload)

    result = run_scenario(
        tmp_path,
        scenario,
        [
            call_action(scenario["name"], scenario["arguments"]),
            answer_action(scenario["answer"]),
        ],
        task_change=truth,
    )
    assert result.score.outcome == "unknown"
    assert summarize([result])["total"] == summarize([result])["unknown"] == 1
    assert summarize([result])["excluded"] == 0


def test_registry_manifest_binds_actual_source_and_selected_names():
    registry = LocalToolRegistry()
    expected_names = {item["name"] for item in SCENARIOS}
    assert {item["spec"]["name"] for item in registry.manifest["tools"]} == expected_names
    actual_source = hashlib.sha256(
        files("toolalign.tools").joinpath("catalog.py").read_bytes()
    ).hexdigest()
    for binding in registry.manifest["tools"]:
        assert binding["source_hash"] == actual_source
        assert binding["schema_hash"] == canonical_hash(binding["spec"]["parameters_json_schema"])
        assert binding["implementation"] == "toolalign.tools.catalog:" + binding["spec"]["name"]
    assert canonical_hash(registry.manifest) == registry.registry_hash
    assert LocalToolRegistry(["convert_numeric_units"]).registry_hash != registry.registry_hash


@pytest.mark.parametrize(
    "fabrication",
    ["constructed", "copied", "cross_registry", "changed_value", "old_version", "old_hash"],
)
def test_issued_call_identity_and_current_snapshot_are_required(tmp_path, fabrication):
    registry = LocalToolRegistry()
    call = call_action("convert_numeric_units", {"value": 2.5, "from_unit": "min", "to_unit": "s"})[
        "tool_calls"
    ][0]
    issued = registry.validate(call)
    if fabrication == "constructed":
        issued = ValidatedCall(
            copy.deepcopy(issued.call), issued.tool_version, issued.registry_hash
        )
    elif fabrication == "copied":
        issued = copy.deepcopy(issued)
    elif fabrication == "cross_registry":
        issued = LocalToolRegistry().validate(call)
    elif fabrication == "changed_value":
        issued.call["arguments"]["value"] = 25
    else:
        object.__setattr__(
            issued, "tool_version" if fabrication == "old_version" else "registry_hash", "old"
        )
    executor = LocalToolExecutor(registry)
    result = executor.execute(issued, context(tmp_path))
    assert result.status == "rejected" and not executor.process_records


def test_post_authorization_mapping_mutation_cannot_change_child_snapshot(tmp_path, monkeypatch):
    registry = LocalToolRegistry()
    issued = registry.validate(
        call_action(
            "convert_numeric_units",
            {"value": 2.5, "from_unit": "min", "to_unit": "s"},
        )["tool_calls"][0]
    )
    authorize = registry.authorize

    def mutate_after_snapshot(value):
        accepted = authorize(value)
        value.call["arguments"]["value"] = 25
        return accepted

    monkeypatch.setattr(registry, "authorize", mutate_after_snapshot)
    executor = LocalToolExecutor(registry)
    result = executor.execute(issued, context(tmp_path))
    assert result.status == "completed" and result.output["converted_value"] == 150
    assert executor.execute(issued, context(tmp_path)).status == "rejected"
    assert len(executor.process_records) == 1


def test_concurrent_replay_has_exactly_one_authorized_execution(tmp_path):
    registry = LocalToolRegistry()
    issued = registry.validate(
        call_action("query_build_report", {"report_id": "beacon-110"})["tool_calls"][0]
    )
    executor = LocalToolExecutor(registry)
    barrier = threading.Barrier(2)

    def attempt():
        barrier.wait(timeout=3)
        return executor.execute(issued, context(tmp_path))

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(attempt), pool.submit(attempt)
        statuses = sorted([first.result(timeout=5).status, second.result(timeout=5).status])
    assert statuses == ["completed", "rejected"]
    assert len(executor.process_records) == 1 and executor.process_records[0]["reaped"]


@pytest.mark.parametrize(
    "raw",
    [
        '{"value":1,"value":2}',
        '{"value":1e10000}',
        '["x",' + "null," * 8191 + "null]",
    ],
)
def test_json_duplicate_nonfinite_and_complexity_inputs_are_rejected(raw):
    with pytest.raises(ContractError):
        decode(raw)


def test_boolean_is_not_semantically_equivalent_to_numeric_one(tmp_path):
    scenario = SCENARIOS[3]
    result = run_scenario(
        tmp_path,
        scenario,
        [
            call_action(scenario["name"], scenario["arguments"]),
            answer_action({"total_failed": True}),
        ],
    )
    assert result.score.outcome == "failure"


@pytest.mark.parametrize("exhaust", [False, True])
def test_retry_budget_is_cumulative_and_no_third_tool_round_starts(tmp_path, exhaust):
    scenario = SCENARIOS[1]
    actions = [
        call_action(scenario["name"], scenario["arguments"], "r1-c1"),
        call_action(scenario["name"], scenario["arguments"], "r1-c2"),
    ]
    actions.append(
        call_action(scenario["name"], scenario["arguments"], "r1-c3")
        if exhaust
        else answer_action(scenario["answer"])
    )

    def truth(task):
        payload = copy.deepcopy(task.oracle_payload)
        payload["strategies"][0].insert(
            0,
            expected_step(
                scenario["name"],
                scenario["arguments"],
                None,
                status="error",
                code="injected_transient",
                retryable=True,
            ),
        )
        return replace(task, oracle_payload=payload)

    result = run_scenario(
        tmp_path,
        scenario,
        actions,
        task_change=truth,
        faults={scenario["name"]: ["transient", "transient" if exhaust else None]},
        backend=ScriptedCPUModelBackend(
            [json.dumps(item) for item in actions], input_tokens=21, output_tokens=256
        ),
    )
    assert result.budget == {
        "model_decisions": 3,
        "tool_rounds": 2,
        "input_tokens": 63,
        "output_tokens": 768,
    }
    assert len(result.process_records) == 3
    assert result.trace[-1]["event"] == ("budget_exhausted" if exhaust else "finalized")
    assert result.score.outcome == ("failure" if exhaust else "success")


def test_257_token_response_consumes_usage_but_never_executes_a_tool(tmp_path):
    scenario = SCENARIOS[1]
    action = call_action(scenario["name"], scenario["arguments"])
    result = run_scenario(
        tmp_path,
        scenario,
        [action],
        backend=ScriptedCPUModelBackend(
            [json.dumps(action)],
            input_tokens=21,
            output_tokens=257,
        ),
    )
    assert result.budget == {
        "model_decisions": 1,
        "tool_rounds": 0,
        "input_tokens": 21,
        "output_tokens": 257,
    }
    assert result.trace[-1]["validation_failure"] == "response_token_limit"
    assert len(result.process_records) == 1


class OversizeUnicodeBackend:
    def generate(self, request, generation_config):
        return ModelOutput("🙂" * 40_000, None, None, SCRIPTED_IDENTITY, 23, 29, "stop")


def test_oversize_multibyte_raw_retains_exact_hash_size_and_known_usage(tmp_path):
    scenario = SCENARIOS[1]
    result = run_scenario(tmp_path, scenario, [], backend=OversizeUnicodeBackend())
    assert result.score.outcome == "failure"
    (decision,) = result.decisions
    assert decision["raw_text"] is None and decision["raw_truncated"]
    assert decision["raw_size_bytes"] == 160_000
    assert decision["raw_sha256"] == hashlib.sha256(("🙂" * 40_000).encode()).hexdigest()
    assert result.budget == {
        "model_decisions": 1,
        "tool_rounds": 0,
        "input_tokens": 23,
        "output_tokens": 29,
    }
    assert result.token_accounting_complete


def test_oracle_marks_observation_before_execution_unknown(tmp_path):
    scenario = SCENARIOS[1]
    result = run_scenario(
        tmp_path,
        scenario,
        [
            call_action(scenario["name"], scenario["arguments"]),
            answer_action(scenario["answer"]),
        ],
    )
    assert result.score.outcome == "success"
    _, task = make_task(LocalToolRegistry(), scenario)
    damaged = copy.deepcopy(result.trace)
    execution = next(i for i, item in enumerate(damaged) if item["event"] == "tool_execution")
    observation = next(i for i, item in enumerate(damaged) if item["event"] == "observing")
    latencies = [item["latency_ms"] for item in damaged]
    damaged[execution], damaged[observation] = damaged[observation], damaged[execution]
    for index, event in enumerate(damaged):
        event["event_index"] = index
        event["latency_ms"] = latencies[index]
        validate_record(event, "trace")
    score = SemanticOracle().score(task, damaged, result.final_result)
    (tmp_path / "invalid-trace-observation.json").write_text(
        json.dumps(
            {
                "events": [event["event"] for event in damaged],
                "all_wire_records_valid": True,
                "outcome": score.outcome,
                "reason": score.reason,
            },
            indent=2,
        )
    )
    assert score.outcome == "unknown", (
        "An observation preceding its execution is not reliable truth"
    )
