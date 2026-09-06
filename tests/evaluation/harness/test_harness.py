import copy
import json
import multiprocessing
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from toolalign.contracts import canonical_hash, validate_record
from toolalign.contracts.interfaces import ModelOutput, SandboxContext
from toolalign.evaluation.harness import (
    DEADLINE_SECONDS,
    MAX_DECISIONS,
    MAX_NEW_TOKENS,
    MAX_TOOL_ROUNDS,
    LocalHarness,
    summarize,
)
from toolalign.evaluation.oracles import SemanticOracle
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools.__main__ import development_case
from toolalign.tools._json import ContractError, decode, encode, parse_action
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend

CASES = json.loads((Path(__file__).parents[2] / "fixtures/tools/development.json").read_text())[
    "cases"
]
BY_ID = {case["id"]: case for case in CASES}


def run_case(
    tmp_path,
    name="dev-report",
    *,
    responses=None,
    faults=None,
    backend=None,
    seconds=10,
    cancellation=None,
    example_change=None,
    task_change=None,
    context_change=None,
):
    registry = LocalToolRegistry()
    case = copy.deepcopy(BY_ID[name])
    example, task = development_case(case, registry)
    if example_change:
        example_change(example)
    if task_change:
        task = task_change(task)
    executor = LocalToolExecutor(registry, faults=case.get("faults") if faults is None else faults)
    context = SandboxContext(
        tmp_path.resolve(),
        "harness-test",
        (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(),
        cancellation or CancellationToken(),
    )
    if context_change:
        context = context_change(context)
    if backend is None:
        backend = ScriptedCPUModelBackend(
            case["scripted_responses"] if responses is None else responses
        )
    result = LocalHarness(registry, executor).run(
        example, task, backend, context, model_identity=SCRIPTED_IDENTITY
    )
    assert_trace(result)
    return result


def assert_trace(result):
    assert result.trace[-1]["task_outcome"]["outcome"] == result.score.outcome
    assert [event["event_index"] for event in result.trace] == list(range(len(result.trace)))
    deadlines = {event["deadline_utc"] for event in result.trace}
    assert len(deadlines) == 1
    assert next(iter(deadlines)).endswith("Z")
    for event in result.trace:
        validate_record(event, "trace")
    for before, after in zip(result.trace, result.trace[1:]):
        assert after["latency_ms"] >= before["latency_ms"]
        for key in before["budget_consumed"]:
            assert after["budget_consumed"][key] >= before["budget_consumed"][key]
    assert all(
        record["reaped"] and record["exitcode"] is not None for record in result.process_records
    )
    live = {process.pid for process in multiprocessing.active_children()}
    assert not live.intersection(record["pid"] for record in result.process_records)


def raw_call(name="query_build_report", arguments=None, call_id="c1"):
    return json.dumps(
        {
            "kind": "tool_calls",
            "content": "",
            "tool_calls": [
                {
                    "call_id": call_id,
                    "name": name,
                    "arguments": {"report_id": "atlas-110"} if arguments is None else arguments,
                }
            ],
        }
    )


def raw_final(value, kind="final"):
    return json.dumps({"kind": kind, "content": json.dumps(value), "tool_calls": []})


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_ten_original_development_scenarios(tmp_path, case):
    result = run_case(tmp_path, case["id"])
    assert result.score.outcome == "success"
    assert result.trace[-1]["event"] == "finalized"
    assert result.token_accounting_complete
    assert all(decision["repaired_output"] is None for decision in result.decisions)


@pytest.mark.parametrize("variant", ["alternate_unit", "extra_conversion"])
def test_all_explicit_equivalent_strategies_and_units_pass(tmp_path, variant):
    case = BY_ID["dev-document"]
    responses = [case["scripted_responses"][0]]
    if variant == "extra_conversion":
        responses.append(
            raw_call(
                "convert_numeric_units", {"value": 1200, "from_unit": "ms", "to_unit": "s"}, "c2"
            )
        )
    responses.append(raw_final(case["answers"][1]["value"]))
    assert run_case(tmp_path, "dev-document", responses=responses).score.outcome == "success"


@pytest.mark.parametrize(
    "case_id,name,args",
    [
        ("dev-report", "query_build_report", {"report_id": "beacon-110"}),
        ("dev-document", "lookup_version_document", {"resource_id": "atlas-1.0"}),
        (
            "dev-logs",
            "filter_build_logs",
            {"resource_id": "atlas-september", "date": "2026-09-02", "level": "error"},
        ),
        (
            "dev-aggregate",
            "aggregate_run_records",
            {
                "resource_id": "atlas-runs",
                "date": "2026-09-01",
                "field": "duration_ms",
                "operation": "sum",
            },
        ),
        (
            "dev-compatibility",
            "compare_version_compatibility",
            {"resource_id": "atlas-1.0", "runtime_version": "3.11"},
        ),
        (
            "dev-conversion",
            "convert_numeric_units",
            {"value": 1536, "from_unit": "B", "to_unit": "MiB"},
        ),
        ("dev-report", "lookup_version_document", {"resource_id": "atlas-1.1"}),
    ],
)
def test_schema_valid_wrong_object_version_date_or_tool_fails(tmp_path, case_id, name, args):
    responses = [raw_call(name, args), BY_ID[case_id]["scripted_responses"][-1]]
    result = run_case(tmp_path, case_id, responses=responses)
    observations = [event["tool_result"] for event in result.trace if event["event"] == "observing"]
    assert observations and all(result["status"] == "completed" for result in observations)
    assert result.score.outcome == "failure"


@pytest.mark.parametrize(
    "bad_value",
    [
        {"object": "atlas", "version": "1.1", "date": "2026-09-01", "passed": 11, "failed": 0},
        {"object": "atlas", "version": "1.1", "date": "2026-08-01", "passed": 12, "failed": 0},
        {"success": True},
    ],
)
def test_successful_tool_does_not_validate_false_final_claims(tmp_path, bad_value):
    result = run_case(tmp_path, responses=[raw_call(), raw_final(bad_value)])
    assert result.score.outcome == "failure"


def test_unstructured_success_claim_is_failure_not_unknown(tmp_path):
    final = json.dumps({"kind": "final", "content": "The task succeeded!", "tool_calls": []})
    result = run_case(tmp_path, responses=[raw_call(), final])
    assert result.score.outcome == "failure"


def test_no_tool_task_rejects_unnecessary_call(tmp_path):
    result = run_case(tmp_path, "dev-no-tool", responses=[raw_call(), raw_final({"value": 5})])
    assert result.score.outcome == "failure"
    assert result.budget["tool_rounds"] == 1


def test_missing_information_must_clarify_before_any_call(tmp_path):
    result = run_case(
        tmp_path,
        "dev-clarify",
        responses=[
            raw_call("lookup_version_document", {"resource_id": "atlas-1.1"}),
            BY_ID["dev-clarify"]["scripted_responses"][0],
        ],
    )
    assert result.score.outcome == "failure"


@pytest.mark.parametrize(
    "raw",
    [
        "Not JSON",
        "{}",
        '{"kind":"final","kind":"clarify","content":"x","tool_calls":[]}',
        '{"kind":"final","content":"x","tool_calls":[],"hidden":true}',
        '{"kind":"tool_calls","content":"","tool_calls":[{"call_id":"c1","name":"query_build_report","arguments":{"report_id":NaN}}]}',
        "[" * 100 + "0" + "]" * 100,
    ],
)
def test_raw_parser_failures_remain_in_denominator(tmp_path, raw):
    result = run_case(tmp_path, responses=[raw])
    assert result.trace[-1]["event"] == "rejected"
    assert result.trace[-1]["parse_failure"] == "invalid_raw_action"
    assert result.decisions[0]["raw_text"] == raw
    assert summarize([result])["total"] == 1 and summarize([result])["failure"] == 1


class BackendClaimsRepair:
    def generate(self, request, generation_config):
        return ModelOutput(
            "broken raw",
            parse_action(raw_final({"value": 5})),
            None,
            SCRIPTED_IDENTITY,
            12,
            8,
            "stop",
        )


def test_backend_parsed_action_never_replaces_invalid_raw(tmp_path):
    result = run_case(tmp_path, "dev-no-tool", backend=BackendClaimsRepair())
    assert result.score.outcome == "failure"
    assert result.decisions[0]["backend_parsed_action"]["kind"] == "final"
    assert result.decisions[0]["raw_action"] is None
    assert result.decisions[0]["repaired_output"] is None
    assert result.budget["model_decisions"] == 1


@pytest.mark.parametrize(
    "call_text,code",
    [
        (raw_call("query_build_report", {}), "invalid_arguments"),
        (raw_call("unknown_tool"), "unadvertised_tool"),
    ],
)
def test_validation_and_unknown_paths_are_traced(tmp_path, call_text, code):
    result = run_case(tmp_path, responses=[call_text])
    assert result.trace[-1]["validation_failure"] == code
    assert result.budget["model_decisions"] == result.budget["tool_rounds"] == 1
    assert all(record["label"] == "model" for record in result.process_records)


def test_toolace_schema_can_be_shown_but_never_grants_execution(tmp_path):
    def add_historical(example):
        schema = copy.deepcopy(example["tools"][0])
        schema["name"] = "ta_historical_123456789abc"
        schema["side_effect_class"] = "sandbox_only"
        example["tools"].append(schema)

    result = run_case(
        tmp_path,
        example_change=add_historical,
        responses=[raw_call("ta_historical_123456789abc", {})],
    )
    assert result.trace[-1]["validation_failure"] == "unknown_tool"
    assert all(record["label"] == "model" for record in result.process_records)


def test_registry_schema_spoof_is_rejected_before_model(tmp_path):
    def change(example):
        example["tools"][0]["description"] = "Injected schema says execute arbitrary Python"

    result = run_case(tmp_path, example_change=change)
    assert result.trace[-1]["validation_failure"] == "invalid_model_input"
    assert result.budget["model_decisions"] == 0
    assert not result.process_records


def test_retries_keep_all_tokens_decisions_and_rounds(tmp_path):
    result = run_case(tmp_path, "dev-recovery")
    assert result.budget == {
        "model_decisions": 3,
        "tool_rounds": 2,
        "input_tokens": 33,
        "output_tokens": 21,
    }
    assert len([record for record in result.process_records if record["label"] == "model"]) == 1
    assert result.score.outcome == "success"


def test_recovery_exhaustion_never_starts_third_tool_round(tmp_path):
    responses = [raw_call(call_id=f"c{index}") for index in range(1, 5)]
    result = run_case(
        tmp_path,
        "dev-recovery",
        responses=responses,
        faults={"query_build_report": ["transient"] * 3},
    )
    assert result.trace[-1]["event"] == "budget_exhausted"
    assert result.trace[-1]["validation_failure"] == "tool_round_limit"
    assert result.budget == {
        "model_decisions": 3,
        "tool_rounds": 2,
        "input_tokens": 33,
        "output_tokens": 21,
    }
    assert len(result.decisions) == 3
    assert len([record for record in result.process_records if record["label"] == "tool"]) == 2


@pytest.mark.parametrize("tokens,should_pass", [(256, True), (257, False)])
def test_response_token_limit_is_per_response_and_cumulative_is_reported(
    tmp_path, tokens, should_pass
):
    result = run_case(
        tmp_path,
        "dev-dependent",
        backend=ScriptedCPUModelBackend(
            BY_ID["dev-dependent"]["scripted_responses"], output_tokens=tokens
        ),
    )
    if should_pass:
        assert result.score.outcome == "success"
        assert result.budget["output_tokens"] == 768
    else:
        assert result.trace[-1]["event"] == "budget_exhausted"
        assert result.budget["output_tokens"] == 257
        assert result.budget["tool_rounds"] == 0


def test_permanent_tool_error_does_not_get_free_recovery(tmp_path):
    result = run_case(tmp_path, faults={"query_build_report": ["error"]})
    assert result.trace[-1]["validation_failure"] == "injected_permanent"
    assert len(result.decisions) == 1 and result.budget["tool_rounds"] == 1


def test_tool_output_limit_is_a_real_failure(tmp_path):
    result = run_case(tmp_path, faults={"query_build_report": ["oversize"]})
    assert result.score.outcome == "failure"
    assert result.trace[-1]["validation_failure"] == "output_limit"


class InputProjectionSentinel:
    def generate(self, request, generation_config):
        assert set(request) == {"messages", "tools"}
        assert "HIDDEN_ORACLE_SENTINEL" not in json.dumps(request)
        assert generation_config.max_new_tokens == 256
        assert generation_config.enable_thinking is False
        return ModelOutput(raw_final({"value": 5}), None, None, SCRIPTED_IDENTITY, 3, 2, "stop")


def test_oracle_labels_metadata_and_expected_action_never_enter_model_input(tmp_path):
    def example_change(example):
        example["expected_action"]["content"] = "HIDDEN_ORACLE_SENTINEL"
        example["source_revision"] = "HIDDEN_ORACLE_SENTINEL"

    def task_change(task):
        expected = copy.deepcopy(task.expected_action)
        expected["content"] = "HIDDEN_ORACLE_SENTINEL"
        return replace(task, expected_action=expected)

    result = run_case(
        tmp_path,
        "dev-no-tool",
        backend=InputProjectionSentinel(),
        example_change=example_change,
        task_change=task_change,
    )
    assert result.score.outcome == "success"


def test_unknown_truth_stays_in_total(tmp_path):
    result = run_case(
        tmp_path, "dev-no-tool", task_change=lambda task: replace(task, oracle_payload={})
    )
    assert result.score.outcome == "unknown"
    assert summarize([result]) == {
        "evaluation_level": "L0_L1_scripted_development",
        "total": 1,
        "success": 0,
        "failure": 0,
        "unknown": 1,
        "not_scored": 0,
        "success_rate": 0,
        "excluded": 0,
        "real_model_benchmark": "NOT_RUN",
    }


@pytest.mark.parametrize("mode", ["expired", "cancelled", "invalid_deadline", "task_mismatch"])
def test_preflight_terminal_paths_emit_valid_trace(tmp_path, mode):
    token = CancellationToken()
    if mode == "cancelled":
        token.cancel()
    result = run_case(
        tmp_path,
        seconds=-1 if mode == "expired" else 10,
        cancellation=token,
        context_change=(lambda ctx: replace(ctx, deadline_utc="bad"))
        if mode == "invalid_deadline"
        else None,
        task_change=(lambda task: replace(task, task_id="wrong-task"))
        if mode == "task_mismatch"
        else None,
    )
    assert result.score.outcome == "failure" and not result.process_records


def test_blocking_model_timeout_ends_the_owned_process(tmp_path):
    result = run_case(
        tmp_path,
        "dev-no-tool",
        seconds=0.8,
        backend=ScriptedCPUModelBackend([raw_final({"value": 5})], delay_seconds=60),
    )
    assert result.trace[-1]["event"] == "timed_out"
    assert result.budget["model_decisions"] == 1
    assert not result.token_accounting_complete
    assert result.process_records[0]["operation_started"]
    assert result.process_records[0]["stopped"]
    assert result.trace[-1]["latency_ms"] < 3000


def test_blocking_model_cancellation_ends_the_owned_process(tmp_path):
    token = CancellationToken()

    def cancel_when_started():
        limit = time.monotonic() + 5
        while time.monotonic() < limit:
            if list(tmp_path.glob("toolalign-owned-*/generating-0.json")):
                token.cancel()
                return
            time.sleep(0.01)

    thread = threading.Thread(target=cancel_when_started)
    thread.start()
    result = run_case(
        tmp_path,
        "dev-no-tool",
        cancellation=token,
        backend=ScriptedCPUModelBackend([raw_final({"value": 5})], delay_seconds=60),
    )
    thread.join(timeout=6)
    assert not thread.is_alive()
    assert result.trace[-1]["event"] == "cancelled"
    assert result.budget["model_decisions"] == 1
    assert not result.token_accounting_complete
    assert result.process_records[0]["operation_started"]


def test_tool_timeout_can_recover_only_with_remaining_shared_budget(tmp_path):
    def change(task):
        payload = copy.deepcopy(task.oracle_payload)
        payload["strategies"][0][0]["status"] = "timed_out"
        payload["strategies"][0][0]["error_code"] = "tool_timeout"
        return replace(task, oracle_payload=payload)

    result = run_case(
        tmp_path, "dev-recovery", task_change=change, faults={"query_build_report": ["block", None]}
    )
    assert result.score.outcome == "success"
    assert result.budget["model_decisions"] == 3 and result.budget["tool_rounds"] == 2
    assert any(record["stopped"] for record in result.process_records if record["label"] == "tool")


def test_cumulative_deadline_is_not_reset_by_retry(tmp_path):
    result = run_case(
        tmp_path, "dev-recovery", seconds=0.8, faults={"query_build_report": ["transient", "block"]}
    )
    assert result.trace[-1]["event"] == "timed_out"
    assert result.budget["model_decisions"] == 2 and result.budget["tool_rounds"] == 2
    assert result.budget["output_tokens"] == 14
    assert result.trace[-1]["latency_ms"] < 3000


def test_same_call_id_across_rounds_is_rejected(tmp_path):
    result = run_case(tmp_path, responses=[raw_call(), raw_call()])
    assert result.trace[-1]["validation_failure"] == "duplicate_call_id"
    assert result.budget["model_decisions"] == 2


def test_empty_summary_has_no_fabricated_success_rate():
    assert summarize([])["success_rate"] is None


def test_protocol_defaults_match_frozen_config():
    protocol = json.loads((Path(__file__).parents[3] / "configs/protocol.v1.json").read_text())
    assert MAX_DECISIONS == protocol["max_model_decisions"] == 3
    assert MAX_TOOL_ROUNDS == protocol["max_tool_rounds"] == 2
    assert MAX_NEW_TOKENS == protocol["generation_defaults"]["max_new_tokens"] == 256
    assert DEADLINE_SECONDS == protocol["generation_defaults"]["deadline_seconds"] == 30


def test_no_coercion_or_nonfinite_action_parser():
    with pytest.raises(ContractError):
        decode('{"n": Infinity}')
    with pytest.raises(ContractError):
        encode({"n": float("nan")})
    with pytest.raises(ContractError):
        parse_action('{"kind":"final","tool_calls":[],"content":"x","kind":"refuse"}')


def test_oracle_rejects_boolean_numeric_equivalence(tmp_path):
    result = run_case(tmp_path, "dev-no-tool", responses=[raw_final({"value": True})])
    assert result.score.outcome == "failure"


def test_oracle_refuses_mixed_or_discontinuous_trace(tmp_path):
    result = run_case(tmp_path, "dev-no-tool")
    registry = LocalToolRegistry()
    _, task = development_case(BY_ID["dev-no-tool"], registry)
    mixed = copy.deepcopy(result.trace)
    mixed[-1]["request_id"] = "different-request"
    assert SemanticOracle().score(task, mixed, result.final_result).outcome == "unknown"
    mixed[-1]["request_id"] = mixed[0]["request_id"]
    mixed[-1]["event_index"] += 1
    assert SemanticOracle().score(task, mixed, result.final_result).outcome == "unknown"
    assert canonical_hash(result.registry_manifest) == registry.registry_hash


class BackendFinishes:
    def __init__(self, mode):
        self.mode = mode

    def generate(self, request, generation_config):
        if self.mode == "raises":
            raise RuntimeError("Internal private diagnostic must not leave the backend")
        identity = copy.deepcopy(SCRIPTED_IDENTITY)
        raw = raw_final({"value": 5})
        tokens = 7
        if self.mode == "identity":
            identity["model_hash"] = "0" * 64
        if self.mode == "oversize":
            raw = "x" * 140_000
        if self.mode == "invalid_tokens":
            tokens = True
        finish = self.mode if self.mode in ("length", "error", "timed_out", "cancelled") else "stop"
        return ModelOutput(raw, None, None, identity, 11, tokens, finish)


@pytest.mark.parametrize(
    "mode,event,code",
    [
        ("raises", "rejected", "backend_error_or_output_limit"),
        ("identity", "rejected", "model_identity_mismatch"),
        ("oversize", "rejected", "backend_error_or_output_limit"),
        ("invalid_tokens", "rejected", "invalid_token_accounting"),
        ("length", "budget_exhausted", "response_token_limit"),
        ("error", "rejected", "backend_error"),
        ("timed_out", "timed_out", "timed_out"),
        ("cancelled", "cancelled", "cancelled"),
    ],
)
def test_backend_failures_terminate_with_valid_trace(tmp_path, mode, event, code):
    result = run_case(tmp_path, "dev-no-tool", backend=BackendFinishes(mode))
    assert result.trace[-1]["event"] == event
    assert result.trace[-1]["validation_failure"] == code
    assert result.budget["model_decisions"] == 1
    assert result.score.outcome == "failure"
    assert "Internal private diagnostic" not in json.dumps(result.decisions)


class SecondGenerationBlocks:
    def __init__(self):
        self.index = 0

    def generate(self, request, generation_config):
        self.index += 1
        if self.index == 2:
            time.sleep(60)
        return ModelOutput(raw_call(), None, None, SCRIPTED_IDENTITY, 4, 5, "stop")


@pytest.mark.parametrize("mode", ["cancelled", "timed_out"])
def test_blocked_retry_preserves_prior_usage_and_is_reaped(tmp_path, mode):
    token = CancellationToken()
    thread = None
    if mode == "cancelled":

        def cancel_second_generation():
            end = time.monotonic() + 5
            while time.monotonic() < end:
                if list(tmp_path.glob("toolalign-owned-*/generating-1.json")):
                    token.cancel()
                    return
                time.sleep(0.01)

        thread = threading.Thread(target=cancel_second_generation)
        thread.start()
    result = run_case(
        tmp_path,
        "dev-recovery",
        backend=SecondGenerationBlocks(),
        seconds=0.8 if mode == "timed_out" else 10,
        cancellation=token,
    )
    if thread is not None:
        thread.join(timeout=6)
        assert not thread.is_alive()
    assert result.trace[-1]["event"] == mode
    assert result.budget == {
        "model_decisions": 2,
        "tool_rounds": 1,
        "input_tokens": 4,
        "output_tokens": 5,
    }
    assert not result.token_accounting_complete


def test_budget_counts_one_round_for_a_bounded_batch(tmp_path):
    actions = [parse_action(raw_call(call_id=f"c{i}"))["tool_calls"][0] for i in range(16)]
    raw = json.dumps({"kind": "tool_calls", "content": "", "tool_calls": actions})
    result = run_case(tmp_path, responses=[raw, BY_ID["dev-report"]["scripted_responses"][-1]])
    assert result.budget["tool_rounds"] == 1 and result.budget["model_decisions"] == 2
    assert len([event for event in result.trace if event["event"] == "observing"]) == 16
    assert result.score.outcome == "failure"


def test_duplicate_call_ids_in_a_single_response_never_execute(tmp_path):
    item = parse_action(raw_call())["tool_calls"][0]
    raw = json.dumps({"kind": "tool_calls", "content": "", "tool_calls": [item, item]})
    result = run_case(tmp_path, responses=[raw])
    assert result.trace[-1]["parse_failure"] == "invalid_raw_action"
    assert result.budget["tool_rounds"] == 0


def test_explicit_allowed_refusal_can_succeed(tmp_path):
    answer = {"reason": "unsupported_external_write"}

    def truth(task):
        payload = copy.deepcopy(task.oracle_payload)
        payload["answers"] = [{"kind": "refuse", "value": answer}]
        return replace(task, oracle_payload=payload)

    result = run_case(
        tmp_path, "dev-no-tool", responses=[raw_final(answer, "refuse")], task_change=truth
    )
    assert result.score.outcome == "success"


def test_oversize_raw_keeps_hash_size_and_reported_usage(tmp_path):
    import hashlib

    result = run_case(tmp_path, "dev-no-tool", backend=BackendFinishes("oversize"))
    decision = result.decisions[0]
    assert decision["raw_text"] is None and decision["raw_truncated"]
    assert decision["raw_sha256"] == hashlib.sha256(b"x" * 140_000).hexdigest()
    assert decision["raw_size_bytes"] == 140_000
    assert result.budget["input_tokens"] == 11 and result.budget["output_tokens"] == 7
    assert result.token_accounting_complete
    assert result.provenance["generation_config"]["deadline_utc"] == result.trace[0]["deadline_utc"]


def test_nonretryable_fault_is_not_an_equivalent_recovery_strategy(tmp_path):
    result = run_case(tmp_path, "dev-recovery")
    _, task = development_case(BY_ID["dev-recovery"], LocalToolRegistry())
    trace = copy.deepcopy(result.trace)
    event = next(event for event in trace if event["event"] == "observing")
    event["tool_result"]["retryable"] = False
    event["tool_result"]["error_code"] = "permanent_error"
    assert SemanticOracle().score(task, trace, result.final_result).outcome == "failure"


def test_invalid_oracle_status_is_unknown(tmp_path):
    def truth(task):
        payload = copy.deepcopy(task.oracle_payload)
        payload["strategies"][0][0]["status"] = "unsupported_status"
        return replace(task, oracle_payload=payload)

    result = run_case(tmp_path, task_change=truth)
    assert result.score.outcome == "unknown"


def test_hidden_payload_truth_is_not_supplied_to_backend(tmp_path):
    def truth(task):
        payload = copy.deepcopy(task.oracle_payload)
        payload["answers"] = [{"kind": "final", "value": {"secret": "HIDDEN_ORACLE_SENTINEL"}}]
        return replace(task, oracle_payload=payload)

    result = run_case(tmp_path, "dev-no-tool", backend=InputProjectionSentinel(), task_change=truth)
    assert result.trace[-1]["event"] == "finalized"
    assert result.score.outcome == "failure"
    assert result.decisions[0]["raw_action"] is not None


def test_monotonic_request_deadline_survives_tool_wall_clock_jump(tmp_path, monkeypatch):
    monkeypatch.setattr("toolalign.tools.executor.utc_remaining", lambda expiry: 10_000)
    result = run_case(tmp_path, seconds=0.6, faults={"query_build_report": ["block"]})
    assert result.trace[-1]["event"] == "timed_out"
    assert result.trace[-1]["latency_ms"] < 1500
    assert result.budget["tool_rounds"] == result.budget["model_decisions"] == 1
    tool = next(record for record in result.process_records if record["label"] == "tool")
    assert tool["operation_started"] and tool["stopped"] and tool["reaped"]
