"""Independent real-process failure probes, using only original CPU fixtures."""

from __future__ import annotations

import errno
import json
import multiprocessing
import os
import signal
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from toolalign.contracts import canonical_hash, validate_record
from toolalign.contracts.interfaces import ModelOutput, OracleTask, SandboxContext
from toolalign.evaluation import harness as harness_module
from toolalign.evaluation.harness import LocalHarness
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools import executor as executor_module
from toolalign.tools.isolation import OwnedProcess
from toolalign.tools.scripted import SCRIPTED_IDENTITY


def final_action(value=7):
    return {"kind": "final", "content": json.dumps({"value": value}), "tool_calls": []}


def no_tool_task():
    """The script and the hand-written evaluation truth are separate inputs."""
    example = {
        "schema_version": "toolalign.example.v1",
        "example_id": "r1-supplied-addition",
        "source": "toolalign-original-review",
        "source_revision": "p03-review.v1",
        "license_id": "MIT",
        "source_record_hash": canonical_hash({"review_case": 1}),
        "group_id": "r1-supplied-values",
        "split": "validation",
        "messages": [
            {
                "role": "user",
                "content": "Add the supplied 3 and 4 without tools.",
                "tool_calls": [],
                "tool_call_id": None,
            }
        ],
        "tools": [],
        "expected_action": final_action(),
        "category": "no_tool",
    }
    return validate_record(example, "example"), OracleTask(
        example["example_id"],
        example["group_id"],
        example["split"],
        final_action(),
        {
            "version": ORACLE_VERSION,
            "answers": [{"kind": "final", "value": {"value": 7}}],
            "strategies": [[]],
        },
    )


def context(root, token=None, seconds=5):
    return SandboxContext(
        root.resolve(),
        "r1-p03-request",
        (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(),
        token or CancellationToken(),
    )


class OriginalCPUBackend:
    def __init__(self, evidence_path, mode="final"):
        self.evidence_path = str(evidence_path)
        self.mode = mode

    def generate(self, request, generation_config):
        assert set(request) == {"messages", "tools"}
        assert generation_config.max_new_tokens == 256
        if self.mode == "stubborn":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        Path(self.evidence_path).write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "ppid": os.getppid(),
                    "entered_generate": True,
                }
            )
        )
        if self.mode == "crash":
            os._exit(17)
        if self.mode in ("block", "stubborn"):
            time.sleep(30)
        raw = "not-json" if self.mode == "parse_error" else json.dumps(final_action())
        if self.mode == "tool":
            raw = json.dumps(
                {
                    "kind": "tool_calls",
                    "content": "",
                    "tool_calls": [
                        {
                            "call_id": "r1-tool",
                            "name": "query_build_report",
                            "arguments": {"report_id": "beacon-110"},
                        },
                    ],
                }
            )
        return ModelOutput(raw, None, None, SCRIPTED_IDENTITY, 13, 9, "stop")


@pytest.fixture
def observed_processes(monkeypatch):
    """Observe the actual Process immediately before its real close(), after join."""
    evidence = []

    class ObservedOwnedProcess(OwnedProcess):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            record = {
                "pid": self.process.pid,
                "label": self.record["label"],
                "handle_identity": id(self.process),
                "parent_pid": os.getpid(),
                "directory": str(self.directory),
            }
            evidence.append(record)
            original_close = self.process.close

            def before_handle_close():
                record.update(
                    is_alive_before_handle_close=self.process.is_alive(),
                    actual_exitcode=self.process.exitcode,
                    active_child_pids=[p.pid for p in multiprocessing.active_children()],
                )
                original_close()

            self.process.close = before_handle_close

    monkeypatch.setattr(harness_module, "OwnedProcess", ObservedOwnedProcess)
    monkeypatch.setattr(executor_module, "OwnedProcess", ObservedOwnedProcess)
    return evidence


def assert_actual_reaping(evidence):
    assert evidence
    for item in evidence:
        assert item["is_alive_before_handle_close"] is False
        assert item["actual_exitcode"] is not None
        assert item["pid"] not in item["active_child_pids"]
        assert not Path(item["directory"]).exists()


class CancelAfterMarker:
    """Cancellation is impossible until the real operation writes its marker."""

    def __init__(self, root, pattern):
        self.root, self.pattern = root, pattern
        self.observed_marker = False

    def is_cancelled(self):
        if list(self.root.glob(self.pattern)):
            self.observed_marker = True
        return self.observed_marker


def separate_sleeper(marker):
    Path(marker).write_text(json.dumps({"pid": os.getpid(), "ppid": os.getppid()}))
    time.sleep(30)


@pytest.mark.parametrize(
    "operation,mode",
    [
        ("tool", "timed_out"),
        ("tool", "cancelled"),
        ("model", "timed_out"),
        ("model", "cancelled"),
    ],
)
def test_real_blocking_operations_reap_only_the_owned_process(
    tmp_path,
    observed_processes,
    operation,
    mode,
):
    separate_marker = tmp_path / "separate-entered.json"
    separate = multiprocessing.get_context("spawn").Process(
        target=separate_sleeper,
        args=(str(separate_marker),),
    )
    separate.start()
    try:
        until = time.monotonic() + 3
        while not separate_marker.exists() and time.monotonic() < until:
            time.sleep(0.005)
        separate_identity = json.loads(separate_marker.read_text())
        assert separate_identity == {"pid": separate.pid, "ppid": os.getpid()}
        registry = LocalToolRegistry()
        marker = tmp_path / "backend-entered.json"
        pattern = "toolalign-owned-*/executing.json" if operation == "tool" else marker.name
        token = CancelAfterMarker(tmp_path, pattern) if mode == "cancelled" else CancellationToken()
        if operation == "tool":
            executor = LocalToolExecutor(registry, faults={"query_build_report": ["block"]})
            validated = registry.validate(
                {
                    "call_id": "r1-blocking-call",
                    "name": "query_build_report",
                    "arguments": {"report_id": "beacon-110"},
                }
            )
            outcome = executor.execute(validated, context(tmp_path, token))
            assert outcome.status == mode
            records = executor.process_records
        else:
            example, task = no_tool_task()
            outcome = LocalHarness(registry, LocalToolExecutor(registry)).run(
                example,
                task,
                OriginalCPUBackend(marker, "stubborn"),
                context(tmp_path, token, seconds=0.8 if mode == "timed_out" else 5),
                model_identity=SCRIPTED_IDENTITY,
            )
            assert outcome.trace[-1]["event"] == mode
            assert outcome.budget["model_decisions"] == 1
            assert outcome.token_accounting_complete is False
            entered = json.loads(marker.read_text())
            assert entered["pid"] == observed_processes[0]["pid"]
            assert entered["ppid"] == os.getpid()
            records = outcome.process_records
        assert_actual_reaping(observed_processes)
        assert len(records) == 1 and records[0]["operation_started"]
        assert records[0]["stopped"] and records[0]["reaped"]
        expected_exit = -signal.SIGKILL if operation == "model" else -signal.SIGTERM
        assert observed_processes[0]["actual_exitcode"] == expected_exit
        assert records[0]["exitcode"] == expected_exit
        assert separate.is_alive()
        assert separate.pid not in {item["pid"] for item in records}
        if mode == "cancelled":
            assert token.observed_marker
        (tmp_path / "blocking-observation.json").write_text(
            json.dumps(
                {
                    "operation": operation,
                    "mode": mode,
                    "records": records,
                    "observed_handles": observed_processes,
                    "separate_process_remained_alive": separate.is_alive(),
                },
                indent=2,
            )
        )
    finally:
        if separate.is_alive():
            separate.terminate()
        separate.join(timeout=3)
        if separate.is_alive():
            separate.kill()
            separate.join(timeout=3)
        assert not separate.is_alive()
        separate.close()


@pytest.mark.parametrize("mode", ["final", "parse_error", "crash"])
def test_real_child_normal_parse_and_crash_paths_have_terminal_result(
    tmp_path,
    observed_processes,
    mode,
):
    example, task = no_tool_task()
    registry = LocalToolRegistry()
    marker = tmp_path / "backend-entered.json"
    result = LocalHarness(registry, LocalToolExecutor(registry)).run(
        example,
        task,
        OriginalCPUBackend(marker, mode),
        context(tmp_path),
        model_identity=SCRIPTED_IDENTITY,
    )
    assert_actual_reaping(observed_processes)
    entered = json.loads(marker.read_text())
    assert entered["pid"] == observed_processes[0]["pid"]
    assert entered["ppid"] == os.getpid()
    assert result.score.outcome == ("success" if mode == "final" else "failure")
    assert result.budget["model_decisions"] == 1
    assert result.token_accounting_complete is (mode != "crash")
    if mode == "crash":
        assert observed_processes[0]["actual_exitcode"] == 17
    for event in result.trace:
        validate_record(event, "trace")


@pytest.mark.parametrize("mode", ["final", "parse_error"])
def test_stop_packet_write_failure_still_returns_terminal_result(
    tmp_path,
    monkeypatch,
    observed_processes,
    mode,
):
    example, task = no_tool_task()
    registry = LocalToolRegistry()
    marker = tmp_path / "backend-entered.json"
    write_packet = harness_module.write_packet
    failures = []

    def stop_write_failure(path, value, *args, **kwargs):
        if path.name == "stop.json":
            failures.append(path.name)
            raise OSError(errno.EIO, "R1 injected stop-control I/O failure")
        return write_packet(path, value, *args, **kwargs)

    monkeypatch.setattr(harness_module, "write_packet", stop_write_failure)
    result, error = None, None
    try:
        result = LocalHarness(registry, LocalToolExecutor(registry)).run(
            example,
            task,
            OriginalCPUBackend(marker, mode),
            context(tmp_path),
            model_identity=SCRIPTED_IDENTITY,
        )
    except OSError as exc:
        error = type(exc).__name__
    assert_actual_reaping(observed_processes)
    assert json.loads(marker.read_text())["pid"] == observed_processes[0]["pid"]
    assert failures
    (tmp_path / "stop-failure-observation.json").write_text(
        json.dumps(
            {
                "mode": mode,
                "stop_write_attempts": len(failures),
                "raised_exception": error,
                "returned_harness_result": result is not None,
                "processes": observed_processes,
            },
            indent=2,
        )
    )
    assert result is not None, "A reaped request vanished instead of returning terminal evidence"
    assert result.trace[-1]["task_outcome"] is not None
    assert result.budget["input_tokens"] == 13 and result.budget["output_tokens"] == 9


def test_shared_monotonic_expiry_wins_after_tool_clock_rollback(
    tmp_path,
    monkeypatch,
    observed_processes,
):
    registry = LocalToolRegistry()
    example, task = no_tool_task()
    example["tools"] = registry.tools
    executor = LocalToolExecutor(registry, faults={"query_build_report": ["block"]})
    monkeypatch.setattr(executor_module, "utc_remaining", lambda expiry: 3600)
    result = LocalHarness(registry, executor).run(
        example,
        task,
        OriginalCPUBackend(tmp_path / "model-entered.json", "tool"),
        context(tmp_path, seconds=0.7),
        model_identity=SCRIPTED_IDENTITY,
    )
    assert result.trace[-1]["event"] == "timed_out"
    assert 650 <= result.trace[-1]["latency_ms"] < 1800
    assert result.budget == {
        "model_decisions": 1,
        "tool_rounds": 1,
        "input_tokens": 13,
        "output_tokens": 9,
    }
    assert len(result.process_records) == 2
    assert all(item["operation_started"] and item["reaped"] for item in result.process_records)
    assert_actual_reaping(observed_processes)


@pytest.mark.parametrize("mode", ["final", "parse_error"])
def test_directory_cleanup_failure_does_not_reenter_a_closed_process(
    tmp_path,
    monkeypatch,
    observed_processes,
    mode,
):
    example, task = no_tool_task()
    registry = LocalToolRegistry()
    create_owned = harness_module.OwnedProcess
    affected = []

    def create_with_cleanup_failure(*args, **kwargs):
        owned = create_owned(*args, **kwargs)
        original_cleanup = owned._temporary.cleanup

        def cleanup_failure():
            raise OSError(errno.EIO, "R1 injected owned temporary-directory cleanup failure")

        owned._temporary.cleanup = cleanup_failure
        affected.append((owned, original_cleanup))
        return owned

    monkeypatch.setattr(harness_module, "OwnedProcess", create_with_cleanup_failure)
    result, error, cleanup_observations = None, None, []
    try:
        result = LocalHarness(registry, LocalToolExecutor(registry)).run(
            example,
            task,
            OriginalCPUBackend(tmp_path / "backend-entered.json", mode),
            context(tmp_path),
            model_identity=SCRIPTED_IDENTITY,
        )
    except (OSError, ValueError) as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        for owned, original_cleanup in affected:
            # Do not credit the following test safety cleanup to the candidate.
            cleanup_observations.append(
                {
                    "candidate_close_completed": owned._closed,
                    "directory_remained_after_candidate": owned.directory.exists(),
                    "actual_process_handle_closed": owned.process._closed,
                }
            )
            owned._temporary.cleanup = original_cleanup
            original_cleanup()
    assert_actual_reaping(observed_processes)
    assert (
        json.loads((tmp_path / "backend-entered.json").read_text())["pid"]
        == observed_processes[0]["pid"]
    )
    (tmp_path / "cleanup-failure-observation.json").write_text(
        json.dumps(
            {
                "mode": mode,
                "raised_exception": error,
                "returned_harness_result": result is not None,
                "processes": observed_processes,
                "cleanup_observations": cleanup_observations,
                "remaining_owned_directory_removed_by_review_safety_cleanup": True,
            },
            indent=2,
        )
    )
    assert result is not None, (
        "Cleanup failure re-entered a closed Process and erased terminal evidence"
    )
    assert result.trace[-1]["task_outcome"] is not None
