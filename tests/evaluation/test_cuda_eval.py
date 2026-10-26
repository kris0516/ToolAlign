"""Original CPU tasks and owned processes, explicitly separate from model evidence."""

import copy
import json
import subprocess
import sys
import time
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import OracleTask, SandboxContext
from toolalign.evaluation.cuda_eval.decision import one_decision
from toolalign.evaluation.cuda_eval.protocol import (
    RUN_SCHEMA,
    evaluation_plan,
    read_inputs,
    validate_run,
)
from toolalign.evaluation.cuda_eval.runner import run_batch
from toolalign.evaluation.harness import LocalHarness
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.model_io.cuda_generation import ADAPTER_SHA256, CHECKPOINT_SHA256
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend
from toolalign.training.cuda_generate.protocol import SAMPLING
from toolalign.training.cuda_sft.protocol import CONFIG_SHA256, encoded, sha

ROOT = Path(__file__).resolve().parents[2]
FINAL = json.dumps({"kind": "final", "content": "17", "tool_calls": []})
INPUT = {"messages": [{"role": "user", "content": "Return 17.", "tool_calls": [], "tool_call_id": None}], "tools": []}


def request_for(tmp_path, value, mode):
    path = tmp_path / "inputs.json"
    path.write_bytes(encoded(value))
    plan = evaluation_plan(value, mode)
    return {"schema": RUN_SCHEMA, "authorized_by": "S1", "run_kind": "evaluation", "mode": mode,
        "run_id": "original-cpu-evaluation", "source_commit": "a" * 40, "config_sha256": CONFIG_SHA256,
        "input_path": str(path), "input_sha256": sha(path.read_bytes()), "model_root": "/not-loaded-model",
        "checkpoint_dir": "/not-loaded-checkpoint", "checkpoint_sha256": CHECKPOINT_SHA256,
        "adapter_sha256": ADAPTER_SHA256, "dependency_lock": "/not-loaded-lock", "dependency_lock_sha256": "b" * 64,
        "repository": str(ROOT), "lock_root": str(ROOT), "output_dir": str(tmp_path / "output"),
        "plan": plan, "main_seed": 42, "sampling": SAMPLING, "stop_after_unit": len(plan),
        "max_wall_seconds": 30, "max_output_bytes": 128 * 1024**2}


@pytest.fixture
def action_batch(tmp_path):
    value = {"schema_version": "toolalign.evaluation-inputs.v1", "purpose": "action-only-model-evaluation",
             "inputs": [{"task_id": f"original-{i}", "family_id": "original-cpu", "group_id": "one-cpu-group",
                         "category": "irrelevance", "model_input": copy.deepcopy(INPUT)} for i in range(2)]}
    return request_for(tmp_path, value, "action-only"), value


def run(request, value, factory=None, registries=None, **kwargs):
    identity = {"execution_kind": "ORIGINAL_SCRIPTED_CPU_FIXTURE", "models": {"M0": SCRIPTED_IDENTITY, "M1": SCRIPTED_IDENTITY}}
    summary = run_batch(request, value, registries or {}, identity=identity,
                         backend_factory=factory or (lambda _: ScriptedCPUModelBackend([FINAL] * 3)), **kwargs)
    rows = [json.loads(line) for line in (Path(request["output_dir"]) / "results.jsonl").read_text().splitlines()]
    return summary, rows


def resume(request, path):
    return request | {"output_dir": str(path), "run_id": "original-resume", "resume_from": request["output_dir"],
                       "resume_batch_sha256": sha((Path(request["output_dir"]) / "batch.json").read_bytes())}


def test_fixed_alternating_paired_plan_and_cpu_cli(action_batch, tmp_path):
    request, value = action_batch
    assert [(u["model"], u["seed"]) for u in request["plan"]] == [("M0", 42), ("M1", 42), ("M1", 43), ("M0", 43)]
    assert read_inputs(request["input_path"], request["input_sha256"], "action-only")[0] == value
    path = tmp_path / "run.json"
    path.write_bytes(encoded(request))
    result = subprocess.run([sys.executable, "-m", "toolalign.evaluation.cuda_eval", "validate", "--run-config", str(path)],
                            capture_output=True, text=True, check=True, timeout=10)
    assert json.loads(result.stdout) == {"status": "CPU_VALIDATED", "real_evaluation": "NOT_RUN"}
    changed = copy.deepcopy(request)
    changed["plan"][0], changed["plan"][1] = changed["plan"][1], changed["plan"][0]
    with pytest.raises(ValueError, match="frozen_plan"):
        validate_run(changed, value)


@pytest.mark.parametrize("patch", [{"max_wall_seconds": 14401}, {"max_output_bytes": 1024**3 + 1},
    {"authorized_by": "T1"}, {"max_optimizer_steps": 1}, {"stop_after_unit": 225},
    {"sampling": SAMPLING | {"temperature": 0.0}}, {"checkpoint_sha256": "0" * 64}])
def test_run_bounds_and_frozen_settings(action_batch, patch):
    request, value = action_batch
    with pytest.raises(ValueError):
        validate_run(request | patch, value)


def test_action_input_rejects_oracle_fields_and_never_executes_raw_tool_calls(action_batch, monkeypatch):
    request, value = action_batch
    extra = copy.deepcopy(value)
    extra["inputs"][0]["oracle_task"] = {"hidden": "must not be projected"}
    Path(request["input_path"]).write_bytes(encoded(extra))
    with pytest.raises(ValueError, match="input_entry"):
        read_inputs(request["input_path"], sha(encoded(extra)), "action-only")
    raw = json.dumps({"kind": "tool_calls", "content": "", "tool_calls": [
        {"call_id": "not-executed", "name": "unadvertised_tool", "arguments": {}}]})
    def no_tools(*args, **kwargs):
        raise AssertionError("action-only invoked a tool executor")
    monkeypatch.setattr("toolalign.evaluation.cuda_eval.runner.LocalToolExecutor", no_tools)
    summary, rows = run(request, value, lambda _: ScriptedCPUModelBackend([raw]))
    assert summary["terminal_counts"] == {"completed": 4}
    assert summary["official_bfcl_scorer"] == "NOT_RUN"
    for row in rows:
        result = row["result"]
        assert result["raw_text"] == raw and result["raw_action_valid"]
        assert result["model_input"] == INPUT
        assert all(p["label"] == "model" and p["reaped"] for p in result["process_records"])


def test_raw_invalid_empty_and_valid_no_tool_remain_distinct_in_full_denominator(action_batch):
    request, value = action_batch
    raw = ["{broken", "", FINAL, FINAL]
    summary, rows = run(request, value, lambda unit: ScriptedCPUModelBackend([raw[unit["unit_id"]]]))
    assert summary["planned_units"] == 4
    assert summary["terminal_counts"] == {"parse_failure": 2, "completed": 2}
    assert [r["result"]["raw_text"] for r in rows] == raw
    assert [r["result"]["raw_action_valid"] for r in rows] == [False, False, True, True]
    assert all(r["result"]["finish_reason"] == "stop" for r in rows)
    assert all(r["result"]["raw_action"] is None for r in rows[:2])
    assert summary["token_accounting_complete"]


class ContradictoryBackend(ScriptedCPUModelBackend):
    def generate(self, request, generation_config):
        output = super().generate(request, generation_config)
        return replace(output, parsed_action=json.loads(FINAL), finish_reason="timed_out")


def test_raw_gate_does_not_trust_backend_repair_or_timeout(tmp_path):
    result = one_decision(INPUT, ContradictoryBackend(["broken"]), tmp_path.resolve(), model_identity=SCRIPTED_IDENTITY,
                         seed=42, cancellation=CancellationToken(), expires_monotonic=time.monotonic() + 5)
    assert result["status"] == "timed_out" and not result["raw_action_valid"]
    assert result["raw_text"] == "broken" and result["output"]["parsed_action"] == json.loads(FINAL)
    assert result["process_records"][0]["reaped"]


def test_resume_preserves_rows_and_consumes_started_without_terminal(action_batch, tmp_path):
    request, value = action_batch
    def interrupted(unit):
        if unit["unit_id"] == 1:
            raise KeyboardInterrupt("original host interruption")
        return ScriptedCPUModelBackend(["broken"])
    with pytest.raises(KeyboardInterrupt):
        run(request, value, interrupted)
    original = (Path(request["output_dir"]) / "states/0000.terminal.json").read_bytes()
    called = []
    def remaining(unit):
        called.append(unit["unit_id"])
        return ScriptedCPUModelBackend([FINAL])
    summary, rows = run(resume(request, tmp_path / "resumed"), value, remaining)
    assert called == [2, 3]
    assert [row["status"] for row in rows] == ["parse_failure", "interrupted", "completed", "completed"]
    assert (tmp_path / "resumed/states/0000.terminal.json").read_bytes() == original
    assert summary["restored_units"] == 2 and not summary["token_accounting_complete"]


@pytest.mark.parametrize("cause", ["output", "preflight", "cancel"])
def test_unstarted_rows_preserve_all_denominators_and_summary_budget(action_batch, cause):
    request, value = action_batch
    options = {}
    if cause == "output":
        request = request | {"max_output_bytes": 1024**2}
    elif cause == "preflight":
        request = request | {"max_wall_seconds": 1}
        options.update(started_monotonic=time.monotonic() - 2, model_file_preflight_seconds=2)
    else:
        token = CancellationToken()
        token.cancel()
        options["cancellation"] = token
    def must_not_start(_):
        raise AssertionError("started beyond budget")
    summary, rows = run(request, value, must_not_start, **options)
    assert len(rows) == summary["not_started_units"] == 4
    assert all(row["status"] == "not_started" for row in rows)
    assert sum(p.stat().st_size for p in Path(request["output_dir"]).rglob("*") if p.is_file()) <= request["max_output_bytes"]
    assert not summary["token_accounting_complete"]


def test_deadline_reaps_owned_child_and_keeps_unknown_usage(action_batch):
    request, value = action_batch
    summary, rows = run(request | {"max_wall_seconds": 1}, value,
                        lambda _: ScriptedCPUModelBackend([FINAL], delay_seconds=60))
    assert summary["terminal_counts"] == {"timed_out": 1, "not_started": 3}
    result = rows[0]["result"]
    assert result["output"] is None and not result["token_accounting_complete"]
    assert result["process_records"][0]["reaped"] and result["process_records"][0]["stopped"]
    assert list((Path(request["output_dir"]) / "sandbox").iterdir()) == []


def test_replay_uses_one_owned_child_three_requests_and_alternating_order(tmp_path):
    value = {"schema_version": "toolalign.evaluation-replay.v1", "purpose": "development-prefix-replay",
             "sequences": [{"sequence_id": f"sequence-{i}", "tenant_id": "original-cpu-tenant",
                 "requests": [{"request_id": f"request-{j}", "model_input": INPUT} for j in range(3)]} for i in range(2)]}
    request = request_for(tmp_path, value, "replay")
    read_inputs(request["input_path"], request["input_sha256"], "replay")
    assert [u["cache_enabled"] for u in request["plan"]] == [False, True, True, False]
    summary, rows = run(request, value)
    assert summary["planned_requests"] == 12 and summary["terminal_counts"] == {"completed": 4}
    assert summary["request_status_counts"] == {"completed": 12}
    for row in rows:
        result = row["result"]
        assert len(result["process_records"]) == 1 and result["process_records"][0]["reaped"]
        assert [r["generation_config"]["seed"] for r in result["requests"]] == list(range(row["plan"]["seed"], row["plan"]["seed"] + 3))


def test_replay_failure_closes_lifetime_and_does_not_dispatch_remaining_requests(tmp_path):
    value = {"schema_version": "toolalign.evaluation-replay.v1", "purpose": "development-prefix-replay",
             "sequences": [{"sequence_id": "sequence", "tenant_id": "original",
                            "requests": [{"request_id": str(i), "model_input": INPUT} for i in range(3)]}]}
    request = request_for(tmp_path, value, "replay")
    summary, rows = run(request, value, lambda _: ScriptedCPUModelBackend(["broken", FINAL, FINAL]))
    assert summary["planned_requests"] == 6
    assert summary["request_status_counts"] == {"parse_failure": 2, "not_started": 4}
    assert all(row["result"]["process_records"][0]["reaped"] for row in rows)


@pytest.mark.parametrize("fault,error_code,status", [("transient", "injected_transient", "error"), ("block", "tool_timeout", "timed_out")])
def test_l1_recovery_switch_stops_first_retryable_error_with_same_budget(tmp_path, fault, error_code, status):
    registry = LocalToolRegistry(["convert_numeric_units"])
    args = {"value": 250, "from_unit": "ms", "to_unit": "s"}
    def call(ident):
        return {"kind": "tool_calls", "content": "", "tool_calls": [{"call_id": ident,
                "name": "convert_numeric_units", "arguments": args}]}
    example = {"schema_version": "toolalign.example.v1", "example_id": "original-recovery", "source": "cpu-original",
        "source_revision": "v1", "license_id": "MIT", "source_record_hash": canonical_hash({"original": 17}),
        "group_id": "cpu-only", "split": "test", "category": "recovery", "messages": INPUT["messages"],
        "tools": registry.tools, "expected_action": call("first")}
    step = {"name": "convert_numeric_units", "arguments": args, "status": status, "output": None,
            "error_code": error_code, "retryable": True}
    task = OracleTask("original-recovery", "cpu-only", "test", call("first"),
        {"version": ORACLE_VERSION, "answers": [{"kind": "final", "value": 0.25}],
         "strategies": [[step, step | {"status": "completed", "output": args | {"converted_value": 0.25},
                                      "error_code": None, "retryable": False}]]})
    responses = [json.dumps(call("first")), json.dumps(call("retry")),
                 json.dumps({"kind": "final", "content": "0.25", "tool_calls": []})]
    results = []
    for enabled in (True, False):
        context = SandboxContext(tmp_path.resolve(), "original-recovery", (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat(), CancellationToken())
        executor = LocalToolExecutor(registry, faults={"convert_numeric_units": [fault, None]})
        results.append(LocalHarness(registry, executor).run(example, task, ScriptedCPUModelBackend(responses),
            context, model_identity=SCRIPTED_IDENTITY, recovery_enabled=enabled))
    assert [r.score.outcome for r in results] == ["success", "failure"]
    assert [r.budget["model_decisions"] for r in results] == [3, 1]
    assert [r.budget["tool_rounds"] for r in results] == [2, 1]
    assert results[1].score.reason == "recovery_disabled:" + error_code
    assert all(p["reaped"] for r in results for p in r.process_records)


def test_replay_interrupt_preserves_completed_request_and_never_restarts_owned_sequence(tmp_path, monkeypatch):
    from toolalign.evaluation.cuda_eval.decision import DecisionSession

    value = {"schema_version": "toolalign.evaluation-replay.v1", "purpose": "development-prefix-replay",
             "sequences": [{"sequence_id": "sequence", "tenant_id": "original",
                            "requests": [{"request_id": str(i), "model_input": INPUT} for i in range(3)]}]}
    request = request_for(tmp_path, value, "replay")
    original_generate = DecisionSession.generate
    def interrupt_second(session, model_input, *, seed):
        if session.calls == 1:
            raise KeyboardInterrupt("original interruption after request start")
        return original_generate(session, model_input, seed=seed)
    with monkeypatch.context() as patch:
        patch.setattr(DecisionSession, "generate", interrupt_second)
        with pytest.raises(KeyboardInterrupt):
            run(request, value)
    raw = (Path(request["output_dir"]) / "requests/0000-0.terminal.json").read_bytes()
    called = []
    def factory(unit):
        called.append(unit["unit_id"])
        return ScriptedCPUModelBackend([FINAL] * 3)
    summary, rows = run(resume(request, tmp_path / "resumed"), value, factory)
    assert called == [1] and summary["restored_units"] == 1
    assert [r["status"] for r in rows[0]["result"]["requests"]] == ["completed", "interrupted", "not_started"]
    assert (tmp_path / "resumed/requests/0000-0.terminal.json").read_bytes() == raw


def test_capacity_is_separate_from_formal_counts_and_capped_at_two_inputs(tmp_path):
    value = {"schema_version": "toolalign.evaluation-inputs.v1", "purpose": "original-capacity-probe",
             "inputs": [{"task_id": f"probe-{i}", "family_id": "original", "group_id": "original", "category": "capacity",
                         "model_input": INPUT, "model": model} for i, model in enumerate(("M0", "M1"))]}
    request = request_for(tmp_path, value, "capacity")
    read_inputs(request["input_path"], request["input_sha256"], "capacity")
    validate_run(request | {"max_wall_seconds": 60}, value)
    with pytest.raises(ValueError, match="wall_ceiling"):
        validate_run(request | {"max_wall_seconds": 61}, value)
    assert len(request["plan"]) == 2


def test_heldout_reader_and_l1_plan_with_explicit_original_catalog_fixture(tmp_path, monkeypatch):
    """Interface fixture ONLY: E1's heldout catalog is not present in this base commit."""
    from toolalign.evaluation.cuda_eval import protocol
    class OriginalCatalogFixture(LocalToolRegistry):
        def __init__(self, names=None, *, catalog_id="local-devops.v1"):
            assert catalog_id == "heldout-devops.v1"
            super().__init__(names)
        @property
        def catalog_id(self):
            return "heldout-devops.v1"
    monkeypatch.setattr(protocol, "LocalToolRegistry", OriginalCatalogFixture)
    registry = LocalToolRegistry()
    action = json.loads(FINAL)
    example = {"schema_version": "toolalign.example.v1", "example_id": "cpu-heldout-interface", "source": "cpu-original",
        "source_revision": "v1", "license_id": "MIT", "source_record_hash": canonical_hash({"original": 18}),
        "group_id": "cpu-only", "split": "test", "category": "no_tool", **INPUT, "expected_action": action}
    task = OracleTask(example["example_id"], example["group_id"], "test", action,
        {"version": ORACLE_VERSION, "answers": [{"kind": "final", "value": 17}], "strategies": [[]]})
    entry = {"task_id": task.task_id, "family_id": "cpu-only", "group_id": task.group_id, "category": "no_tool",
             "example": example, "oracle_task": asdict(task), "faults": {}, "tool_names": []}
    value = {"schema_version": "toolalign.evaluation-tasks.v1", "purpose": "heldout-model-evaluation",
             "catalog": "heldout-devops.v1", "registry_hash": registry.registry_hash,
             "tasks": [entry], "recovery_task_ids": [task.task_id]}
    request = request_for(tmp_path, value, "l1")
    read, registries = read_inputs(request["input_path"], request["input_sha256"], "l1")
    assert [u["condition"] for u in request["plan"]] == ["M0", "M1", "M1-recovery-off"]
    summary, rows = run(request, read, registries=registries)
    assert summary["terminal_counts"] == {"success": 3}
    assert all(row["result"]["score"]["outcome"] == "success" for row in rows)
    value["tasks"][0]["example"]["split"] = value["tasks"][0]["oracle_task"]["split"] = "train"
    Path(request["input_path"]).write_bytes(encoded(value))
    with pytest.raises(ValueError, match="identity_or_split"):
        read_inputs(request["input_path"], sha(encoded(value)), "l1")
