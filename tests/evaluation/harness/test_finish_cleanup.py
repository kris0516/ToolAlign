"""Real CPU child counterexamples for result loss during request shutdown."""

import json
import multiprocessing
import threading
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import toolalign.evaluation.harness as harness_module
from toolalign.contracts import validate_record
from toolalign.contracts.interfaces import ModelOutput, SandboxContext
from toolalign.evaluation.harness import LocalHarness, summarize
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools.__main__ import development_case
from toolalign.tools.isolation import OwnedProcess
from toolalign.tools.scripted import SCRIPTED_IDENTITY

FINAL = json.dumps({"kind": "final", "content": '{"value":5}', "tool_calls": []})


class FinishingCPUBackend:
    def __init__(self, mode):
        self.mode = mode

    def generate(self, request, generation_config):
        # This marker is inside generate, beyond the harness's pre-call marker.
        Path("backend-entered.json").write_text('{"entered":true}')
        if self.mode == "crash":
            raise RuntimeError("private backend failure")
        return ModelOutput(
            "invalid raw" if self.mode == "parse" else FINAL,
            None,
            None,
            SCRIPTED_IDENTITY,
            13,
            9,
            "stop",
        )


class BlockingSecondCPUBackend:
    def __init__(self):
        self.index = 0

    def generate(self, request, generation_config):
        self.index += 1
        Path("backend-entered.json").write_text('{"entered":true}')
        if self.index == 2:
            Path("backend-blocking.json").write_text('{"entered":true}')
            time.sleep(60)
        raw = json.dumps(
            {
                "kind": "tool_calls",
                "content": "",
                "tool_calls": [
                    {
                        "call_id": "first-call",
                        "name": "query_build_report",
                        "arguments": {"report_id": "atlas-110"},
                    }
                ],
            }
        )
        return ModelOutput(raw, None, None, SCRIPTED_IDENTITY, 13, 9, "stop")


def run_shutdown(
    tmp_path, monkeypatch, mode, fault=None, *, backend=None, seconds=10, cancellation=None
):
    observed = {"stop_attempts": 0, "close_attempts": 0, "trace": [], "processes": []}
    owned = []
    cleanups = []
    original_write = harness_module.write_packet

    def write(path, value, *args, **kwargs):
        if path.name == "stop.json":
            observed["stop_attempts"] += 1
            if fault == "stop":
                raise OSError("injected stop signal write failure")
        return original_write(path, value, *args, **kwargs)

    def validate(value, kind):
        result = validate_record(value, kind)
        if kind == "trace":
            observed["trace"].append(result)
        return result

    class ObservedProcess(OwnedProcess):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            owned.append(self)
            cleanups.append(self._temporary.cleanup)
            if fault == "temporary":

                def fail_cleanup():
                    raise OSError("injected temporary directory cleanup failure")

                self._temporary.cleanup = fail_cleanup

        def close(self):
            observed["close_attempts"] += 1
            observed["backend_entered"] = (
                self.directory / "backend-entered.json"
            ).exists() or observed.get("backend_entered", False)
            observed["backend_blocking"] = (
                self.directory / "backend-blocking.json"
            ).exists() or observed.get("backend_blocking", False)
            if fault == "unreaped":
                raise RuntimeError("injected inability to reap the owned child")
            super().close()

    monkeypatch.setattr(harness_module, "OwnedProcess", ObservedProcess)
    monkeypatch.setattr(harness_module, "write_packet", write)
    monkeypatch.setattr(harness_module, "validate_record", validate)
    case = next(
        case
        for case in json.loads(
            (Path(__file__).parents[2] / "fixtures/tools/development.json").read_text()
        )["cases"]
        if case["id"] == "dev-no-tool"
    )
    registry = LocalToolRegistry()
    example, task = development_case(case, registry)
    context = SandboxContext(
        tmp_path.resolve(),
        "shutdown-test",
        (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(),
        cancellation or CancellationToken(),
    )
    result = None
    try:
        result = LocalHarness(registry, LocalToolExecutor(registry)).run(
            example,
            task,
            backend or FinishingCPUBackend(mode),
            context,
            model_identity=SCRIPTED_IDENTITY,
        )
    finally:
        live = {process.pid for process in multiprocessing.active_children()}
        observed["processes"] = [dict(process.record) for process in owned]
        observed["owned_live"] = [process.record["pid"] in live for process in owned]
        observed["temporary_remaining"] = [process.directory.exists() for process in owned]
        observed["returned_result"] = result is not None
        print(json.dumps({"mode": mode, "fault": fault, **observed}, sort_keys=True))
        # Only undo this test's injected directory failure after recording actual state.
        for process, cleanup in zip(owned, cleanups):
            process._temporary.cleanup = cleanup
            if fault == "unreaped":
                OwnedProcess.close(process)
            if process.record["reaped"]:
                cleanup()
    return result, observed, owned


def assert_result(result, observed):
    assert observed["backend_entered"]
    assert result.process_records and not any(observed["owned_live"])
    assert all(record["reaped"] for record in result.process_records)
    assert all(record["exitcode"] is not None for record in result.process_records)
    assert result.trace[-1]["task_outcome"] == asdict(result.score)
    assert [event["event_index"] for event in result.trace] == list(range(len(result.trace)))
    assert sum(event["task_outcome"] is not None for event in result.trace) == 1
    for event in result.trace:
        validate_record(event, "trace")


@pytest.mark.parametrize("mode", ["final", "parse", "crash"])
def test_normal_parse_and_backend_crash_controls(tmp_path, monkeypatch, mode):
    result, observed, _ = run_shutdown(tmp_path, monkeypatch, mode)
    assert_result(result, observed)
    assert result.trace[-1]["event"] == ("finalized" if mode == "final" else "rejected")
    assert result.score.outcome == ("success" if mode == "final" else "failure")
    assert not any(observed["temporary_remaining"])
    assert all(record["directory_cleaned"] for record in result.process_records)


@pytest.mark.parametrize("mode", ["final", "parse"])
@pytest.mark.parametrize("fault", ["stop", "temporary"])
def test_shutdown_error_returns_failure_without_losing_original_result(
    tmp_path, monkeypatch, mode, fault
):
    result, observed, owned = run_shutdown(tmp_path, monkeypatch, mode, fault)
    assert_result(result, observed)
    assert observed["stop_attempts"] == observed["close_attempts"] == 1
    assert result.score.outcome == "failure"
    assert result.trace[-1]["event"] == "rejected"
    assert "harness_cleanup_error" in result.trace[-1]["validation_failure"]
    assert result.budget == {
        "model_decisions": 1,
        "tool_rounds": 0,
        "input_tokens": 13,
        "output_tokens": 9,
    }
    assert result.token_accounting_complete
    assert len(result.decisions) == 1
    assert result.decisions[0]["raw_text"] == ("invalid raw" if mode == "parse" else FINAL)
    if mode == "parse":
        assert result.trace[-1]["parse_failure"] == "invalid_raw_action"
        assert "parse_failure" in result.score.reason
        assert result.decisions[0]["raw_parse_failure"] == "invalid_raw_action"
        assert result.final_result is None
    else:
        assert result.final_result == json.loads(FINAL)
    assert summarize([result])["total"] == summarize([result])["failure"] == 1
    assert summarize([result])["excluded"] == 0
    if fault == "temporary":
        assert observed["temporary_remaining"] == [True]
        assert result.process_records[0]["directory_cleaned"] is False
        # Retrying cleanup after restoring filesystem access must not revisit a
        # multiprocessing.Process whose handle has already been closed.
        owned[0].close()
        assert owned[0].record["directory_cleaned"] is True
    else:
        assert observed["temporary_remaining"] == [False]
        assert result.process_records[0]["directory_cleaned"] is True


@pytest.mark.parametrize("mode", ["cancelled", "timed_out"])
def test_stop_failure_during_blocked_retry_preserves_usage_and_unrelated_process(
    tmp_path, monkeypatch, mode
):
    token = CancellationToken()
    separate = multiprocessing.get_context("spawn").Process(target=time.sleep, args=(60,))
    separate.start()
    thread = None
    if mode == "cancelled":

        def cancel_after_entering_backend():
            until = time.monotonic() + 5
            while time.monotonic() < until:
                if list(tmp_path.glob("toolalign-owned-*/backend-blocking.json")):
                    token.cancel()
                    return
                time.sleep(0.01)

        thread = threading.Thread(target=cancel_after_entering_backend)
        thread.start()
    try:
        result, observed, _ = run_shutdown(
            tmp_path,
            monkeypatch,
            mode,
            "stop",
            backend=BlockingSecondCPUBackend(),
            seconds=2 if mode == "timed_out" else 10,
            cancellation=token,
        )
        assert_result(result, observed)
        assert observed["backend_blocking"]
        assert observed["stop_attempts"] == observed["close_attempts"] == 1
        assert result.trace[-1]["event"] == mode
        assert result.trace[-1]["validation_failure"] == "harness_cleanup_error"
        assert mode in result.score.reason and result.score.outcome == "failure"
        assert result.budget == {
            "model_decisions": 2,
            "tool_rounds": 1,
            "input_tokens": 13,
            "output_tokens": 9,
        }
        assert len(result.decisions) == 1
        assert result.token_accounting_complete is False
        assert result.process_records[0]["stopped"]
        assert separate.is_alive()
        assert separate.pid not in {record["pid"] for record in result.process_records}
        assert not list(tmp_path.iterdir())
    finally:
        separate.terminate()
        separate.join(timeout=3)
        separate.close()
        if thread:
            thread.join(timeout=6)
            assert not thread.is_alive()


def test_failed_reaping_is_reported_truthfully_in_returned_result(tmp_path, monkeypatch):
    result, observed, owned = run_shutdown(
        tmp_path,
        monkeypatch,
        "timed_out",
        "unreaped",
        backend=BlockingSecondCPUBackend(),
        seconds=2,
    )
    assert observed["backend_blocking"] and observed["owned_live"] == [True]
    assert result.trace[-1]["event"] == "timed_out"
    assert result.trace[-1]["validation_failure"] == "harness_cleanup_error"
    assert result.score.outcome == "failure"
    assert result.process_records[0]["reaped"] is False
    assert result.process_records[0]["exitcode"] is None
    assert result.process_records[0]["directory_cleaned"] is False
    assert result.process_records[0]["cleanup_errors"] == ["owned_process_close_failed"]
    for event in result.trace:
        validate_record(event, "trace")
    # The helper restores real cleanup only after capturing the failed close.
    assert owned[0].record["reaped"] is True
    assert not list(tmp_path.iterdir())
