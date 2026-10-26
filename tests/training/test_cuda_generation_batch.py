"""Original synthetic CPU tasks exercise the batch journal and owned harness."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import OracleTask
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.model_io.cuda_generation import ADAPTER_SHA256, CHECKPOINT_SHA256
from toolalign.tools import LocalToolRegistry
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend
from toolalign.training.cuda_generate.protocol import (
    RUN_SCHEMA,
    SAMPLING,
    candidate_plan,
    read_tasks,
    validate_run,
)
from toolalign.training.cuda_generate.runner import run_batch
from toolalign.training.cuda_sft.protocol import CONFIG_SHA256, encoded, sha

ROOT = Path(__file__).resolve().parents[2]


def final(value):
    return json.dumps({"kind": "final", "tool_calls": [], "content": json.dumps(value)})


@pytest.fixture
def batch(tmp_path):
    registry = LocalToolRegistry()
    action = json.loads(final(17))
    example = {"schema_version": "toolalign.example.v1", "example_id": "original-cpu-fixture",
        "source": "original-generation-cpu-test", "source_revision": "v1", "license_id": "MIT",
        "source_record_hash": canonical_hash({"original_cpu_fixture": 17}),
        "group_id": "cpu-test-only", "split": "train", "category": "no_tool",
        "messages": [{"role": "user", "content": "Return 17 without using tools.",
                      "tool_calls": [], "tool_call_id": None}], "tools": [], "expected_action": action}
    task = OracleTask(example["example_id"], example["group_id"], "train", action,
        {"version": ORACLE_VERSION, "answers": [{"kind": "final", "value": 17}], "strategies": [[]]})
    entry = {"task_id": task.task_id, "family_id": "original-test-family", "group_id": task.group_id,
             "category": "no_tool", "example": example, "oracle_task": asdict(task), "faults": {}}
    task_document = {"schema_version": "toolalign.preference-tasks.v1",
                     "purpose": "train-candidate-generation", "registry_hash": registry.registry_hash,
                     "tasks": [entry]}
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_bytes(encoded(task_document))
    request = {"schema": RUN_SCHEMA, "authorized_by": "S1", "run_kind": "generation",
        "run_id": "cpu-original-generation", "source_commit": "a" * 40,
        "config_sha256": CONFIG_SHA256, "tasks_path": str(tasks_path),
        "tasks_sha256": sha(tasks_path.read_bytes()), "model_root": "/not-loaded-model",
        "checkpoint_dir": "/not-loaded-checkpoint", "checkpoint_sha256": CHECKPOINT_SHA256,
        "adapter_sha256": ADAPTER_SHA256, "dependency_lock": "/not-loaded-lock",
        "dependency_lock_sha256": "b" * 64, "repository": str(ROOT), "lock_root": str(ROOT),
        "output_dir": str(tmp_path / "first"), "candidate_plan": candidate_plan([entry]),
        "main_seed": 42, "sampling": dict(SAMPLING), "max_trajectories": 4,
        "max_wall_seconds": 30, "max_output_bytes": 64 * 1024**2}
    identity = {"execution_kind": "SCRIPTED_CPU_TEST", "model_identity": SCRIPTED_IDENTITY,
                "checkpoint_sha256": "0" * 64, "tasks_sha256": request["tasks_sha256"],
                "source": "original synthetic fixture, no real model"}
    return request, task_document, registry, identity


def execute_fixture(batch, *, factory=None, **patch):
    request, tasks, registry, identity = batch
    request = request | patch
    summary = run_batch(request, tasks, registry, identity=identity,
        backend_factory=factory or (lambda _: ScriptedCPUModelBackend([final(17)])))
    root = Path(request["output_dir"])
    rows = [json.loads(line) for line in (root / "candidates.jsonl").read_text().splitlines()]
    return summary, rows


def resume_arguments(batch, destination):
    source = Path(batch[0]["output_dir"])
    return {"output_dir": str(destination), "run_id": "cpu-original-resume",
            "resume_from": str(source), "resume_batch_sha256": sha((source / "batch.json").read_bytes())}


def test_fixed_plan_input_validation_and_cpu_cli(batch, tmp_path):
    request, tasks, registry, _ = batch
    read, actual_registry = read_tasks(request["tasks_path"], request["tasks_sha256"])
    assert read == tasks and actual_registry.registry_hash == registry.registry_hash
    assert [item["seed"] for item in candidate_plan(tasks["tasks"])] == [42, 43, 44, 45]
    run_path = tmp_path / "run.json"
    run_path.write_bytes(encoded(request))
    validated = subprocess.run([sys.executable, "-m", "toolalign.training.cuda_generate", "validate",
        "--run-config", str(run_path)], capture_output=True, text=True, timeout=10, check=True)
    assert json.loads(validated.stdout) == {"status": "CPU_VALIDATED", "real_generation": "NOT_RUN"}
    planned = subprocess.run([sys.executable, "-m", "toolalign.training.cuda_generate", "plan",
        "--tasks", request["tasks_path"], "--tasks-sha256", request["tasks_sha256"]],
        capture_output=True, text=True, timeout=10, check=True)
    assert json.loads(planned.stdout) == request["candidate_plan"]
    imported = subprocess.run([sys.executable, "-c",
        "import sys,json; import toolalign.model_io.cuda_generation; "
        "import toolalign.training.cuda_generate.runner; "
        "print(json.dumps(sorted({'torch','transformers','peft','mlx'} & set(sys.modules))))"],
        capture_output=True, text=True, timeout=10, check=True)
    assert json.loads(imported.stdout) == []


@pytest.mark.parametrize("patch,reason", [({"max_trajectories": 5}, "trajectory_ceiling"),
    ({"max_wall_seconds": 21601}, "wall_ceiling"), ({"max_optimizer_steps": 1}, "run_fields"),
    ({"checkpoint_sha256": "0" * 64}, "selected_identity"),
    ({"sampling": SAMPLING | {"max_new_tokens": 512}}, "frozen_plan")])
def test_run_boundaries_are_not_decoding_or_training_overrides(batch, patch, reason):
    request, tasks, _, _ = batch
    with pytest.raises(ValueError, match=reason):
        validate_run(request | patch, tasks)


def test_task_file_hash_and_train_identity_are_required(batch):
    request, tasks, _, _ = batch
    with pytest.raises(ValueError, match="file_identity"):
        read_tasks(request["tasks_path"], "0" * 64)
    changed = copy.deepcopy(tasks)
    changed["tasks"][0]["example"]["split"] = "validation"
    raw = encoded(changed)
    Path(request["tasks_path"]).write_bytes(raw)
    with pytest.raises(ValueError, match="identity_or_split"):
        read_tasks(request["tasks_path"], sha(raw))


def test_noninteger_seed_cannot_consume_a_formal_candidate(batch):
    request, tasks, _, _ = batch
    changed = copy.deepcopy(request)
    changed["candidate_plan"][0]["seed"] = 42.0
    with pytest.raises(ValueError, match="frozen_plan"):
        validate_run(changed, tasks)


def test_resume_skips_both_success_and_failure_with_original_bytes(batch, tmp_path):
    def first(candidate):
        return ScriptedCPUModelBackend([final(18 if candidate["candidate_id"] == "candidate-1" else 17)])

    summary, rows = execute_fixture(batch, factory=first, max_trajectories=2)
    assert [row["status"] for row in rows] == ["success", "failure"]
    assert summary["planned_trajectories"] == 4 and summary["not_started_trajectories"] == 2
    source = Path(batch[0]["output_dir"])
    original = (source / "states/0001.terminal.json").read_bytes()
    called = []

    def rest(candidate):
        called.append(candidate["candidate_id"])
        return ScriptedCPUModelBackend([final(17)])

    summary, resumed = execute_fixture(batch, factory=rest, **resume_arguments(batch, tmp_path / "resumed"))
    assert called == ["candidate-2", "candidate-3"]
    assert resumed[:2] == rows
    assert (tmp_path / "resumed/states/0001.terminal.json").read_bytes() == original
    assert summary["terminal_counts"] == {"success": 3, "failure": 1}
    assert summary["restored_trajectories"] == summary["new_trajectories"] == 2
    assert all(row["execution_kind"] == "SCRIPTED_CPU_TEST" for row in resumed)
    for row in resumed:
        assert row["decision_inputs"] == row["harness_result"]["decision_inputs"]
        assert canonical_hash(row["decision_inputs"][0]) == row["harness_result"]["decisions"][0]["model_input_hash"]


def test_started_without_terminal_becomes_interrupted_and_is_never_retried(batch, tmp_path):
    def disconnect(candidate):
        if candidate["candidate_id"] == "candidate-1":
            raise KeyboardInterrupt("simulated host interruption after durable started record")
        return ScriptedCPUModelBackend([final(17)])

    with pytest.raises(KeyboardInterrupt):
        execute_fixture(batch, factory=disconnect)
    source = Path(batch[0]["output_dir"])
    assert (source / "states/0001.started.json").exists()
    assert not (source / "states/0001.terminal.json").exists()
    calls = []

    def remaining(candidate):
        calls.append(candidate["candidate_id"])
        return ScriptedCPUModelBackend([final(17)])

    summary, rows = execute_fixture(batch, factory=remaining,
                                    **resume_arguments(batch, tmp_path / "after-disconnect"))
    assert calls == ["candidate-2", "candidate-3"]
    assert rows[1]["status"] == "interrupted" and rows[1]["harness_result"] is None
    assert summary["planned_trajectories"] == summary["started_trajectories"] == 4
    assert summary["terminal_counts"] == {"success": 3, "interrupted": 1}
    assert summary["trajectory_time_complete"] is False
    assert summary["peak_allocated_bytes"] is None


def test_output_ceiling_stops_before_starting_and_keeps_denominator(batch):
    def must_not_start(_):
        raise AssertionError("output-limited candidate was started")

    summary, rows = execute_fixture(batch, factory=must_not_start, max_output_bytes=1024**2)
    assert summary["status"] == "output_limit" and rows == []
    assert summary["not_started_trajectories"] == 4
    assert not (Path(batch[0]["output_dir"]) / "states").exists()


def test_batch_deadline_reaps_current_child_and_does_not_start_next_id(batch):
    summary, rows = execute_fixture(batch, max_wall_seconds=1,
        factory=lambda _: ScriptedCPUModelBackend([final(17)], delay_seconds=60))
    assert summary["status"] == "wall_limit"
    assert len(rows) == 1 and summary["not_started_trajectories"] == 3
    result = rows[0]["harness_result"]
    assert result["trace"][-1]["event"] == "timed_out"
    assert result["process_records"][0]["reaped"] and result["process_records"][0]["stopped"]


def test_each_candidate_gets_the_same_fresh_fault_schedule(batch):
    request, tasks, registry, identity = batch
    entry = tasks["tasks"][0]
    args = {"value": 250, "from_unit": "ms", "to_unit": "s"}

    def call(ident):
        return {"kind": "tool_calls", "content": "", "tool_calls": [
            {"call_id": ident, "name": "convert_numeric_units", "arguments": args}]}

    entry["example"].update(tools=[registry.spec("convert_numeric_units")],
                             expected_action=call("first"))
    entry["oracle_task"]["expected_action"] = call("first")
    step = {"name": "convert_numeric_units", "arguments": args, "status": "error", "output": None,
            "error_code": "injected_transient", "retryable": True}
    entry["oracle_task"]["oracle_payload"] = {"version": ORACLE_VERSION,
        "answers": [{"kind": "final", "value": 0.25}],
        "strategies": [[step, step | {"status": "completed", "output": args | {"converted_value": 0.25},
                                      "error_code": None, "retryable": False}]]}
    entry["faults"] = {"convert_numeric_units": ["transient", None]}
    raw = encoded(tasks)
    Path(request["tasks_path"]).write_bytes(raw)
    request["tasks_sha256"] = identity["tasks_sha256"] = sha(raw)
    responses = [json.dumps(call("first")), json.dumps(call("retry-raw-id")), final(0.25)]
    summary, rows = execute_fixture(batch, max_trajectories=2,
        factory=lambda _: ScriptedCPUModelBackend(responses))
    assert summary["terminal_counts"] == {"success": 2}
    for row in rows:
        observations = [event["tool_result"] for event in row["harness_result"]["trace"]
                        if event["event"] == "observing"]
        assert [item["error_code"] for item in observations] == ["injected_transient", None]
        assert row["decision_inputs"][2]["messages"][-1]["tool_call_id"] == "retry-raw-id"
    assert entry["faults"] == {"convert_numeric_units": ["transient", None]}
