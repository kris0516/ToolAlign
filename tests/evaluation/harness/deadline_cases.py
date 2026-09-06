"""Stage control for one request-deadline regression; all children remain real."""

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from toolalign.evaluation import harness
from toolalign.tools import CancellationToken, executor, isolation
from toolalign.tools.executor import _tool_child as production_tool_child

STARTUP_DELAY = 0.8  # Deliberately longer than the original 0.6s total request.
REQUEST_SECONDS = 0.6
ORIGIN = 100.0


def delayed_tool_child(directory, *arguments):
    directory = Path(directory)
    (directory / "starting.json").touch()
    time.sleep(STARTUP_DELAY)
    (directory / "ready.json").touch()
    while not (directory / "release.json").exists():
        time.sleep(0.01)

    def blocking_sleep(seconds):
        # This is called by the unchanged production fault="block" branch.
        (directory / "blocking.json").write_text(json.dumps({"seconds": seconds}))
        time.sleep(seconds)

    executor.time = SimpleNamespace(monotonic=time.monotonic, sleep=blocking_sleep)
    production_tool_child(str(directory), *arguments)


def run_deadline_case(tmp_path, monkeypatch, run_case, *, stage, bypass_request=False):
    """Freeze parent clocks during spawn, then cross request and tool deadlines.

    The clock is test-only: 0 -> 0.7 -> 1.1 seconds. The request expires at
    0.6, the unchanged tool cap at 1.0. After the selected real child marker,
    0.7 tests request cancellation; an independent 0.2s real wait advances to
    1.1 so even a bypassed request constraint reaches the tool cap. A separate
    10s real timer cancels the caller token if setup/markers fail.
    """
    owned_process = isolation.OwnedProcess
    owned = []
    started = time.monotonic()
    activated = None
    activation = None
    tool_waiting = False
    clock_offset = 0.0
    cancellation = CancellationToken()
    watchdog_fired = threading.Event()

    def watchdog():
        watchdog_fired.set()
        cancellation.cancel()

    def capture_owned(*args, **kwargs):
        child = owned_process(*args, **kwargs)
        owned.append(child)
        if child.record["label"] == "tool":
            original_wait = child.wait

            def wait(*args, **kwargs):
                nonlocal tool_waiting
                tool_waiting = True
                try:
                    return original_wait(*args, **kwargs)
                finally:
                    tool_waiting = False

            child.wait = wait
        return child

    def monotonic(*, tool_poll=False):
        nonlocal activated, activation, clock_offset
        tool = next((child for child in owned if child.record["label"] == "tool"), None)
        if tool is not None and activated is None:
            directory = tool.directory
            if stage == "blocking" and (directory / "ready.json").exists():
                (directory / "release.json").touch()
            marker = "ready.json" if stage == "startup" else "blocking.json"
            if (directory / marker).exists():
                activated = time.monotonic()
                clock_offset = 0.7
                activation = {
                    "pid": tool.record["pid"],
                    "alive": tool.process.is_alive(),
                    "executing": (directory / "executing.json").exists(),
                    "blocking": (directory / "blocking.json").exists(),
                    "result_present": (directory / "result.json").exists(),
                    "elapsed_seconds": activated - started,
                }
        if (
            tool_poll and tool_waiting and activated is not None
            and time.monotonic() - activated >= 0.2
        ):
            clock_offset = 1.1
        return ORIGIN + clock_offset

    clock = SimpleNamespace(monotonic=monotonic, sleep=time.sleep)
    for module in (harness, executor):
        monkeypatch.setattr(module, "time", clock)
    monkeypatch.setattr(
        isolation, "time",
        SimpleNamespace(monotonic=lambda: monotonic(tool_poll=True), sleep=time.sleep),
    )
    monkeypatch.setattr(harness, "utc_remaining", lambda expiry: REQUEST_SECONDS)
    monkeypatch.setattr(executor, "utc_remaining", lambda expiry: 10_000)
    monkeypatch.setattr(executor, "_tool_child", delayed_tool_child)
    monkeypatch.setattr(harness, "OwnedProcess", capture_owned)
    monkeypatch.setattr(executor, "OwnedProcess", capture_owned)
    if bypass_request:
        monkeypatch.setattr(
            harness._RequestCancellation,
            "is_cancelled",
            lambda self: self.cancellation.is_cancelled(),
        )
    timer = threading.Timer(10, watchdog)
    timer.start()
    try:
        result = run_case(
            tmp_path,
            seconds=REQUEST_SECONDS,
            faults={"query_build_report": ["block"]},
            cancellation=cancellation,
        )
    finally:
        timer.cancel()
        timer.join()
        for child in owned:
            child.close()
    evidence = {
        "stage": stage,
        "bypass_request": bypass_request,
        "parent_clock_offsets": [0, 0.7, 1.1],
        "utc_remaining_double": 10_000,
        "watchdog_fired": watchdog_fired.is_set(),
        "activation": activation,
        "elapsed_seconds": time.monotonic() - started,
        "trace": result.trace,
        "process_records": result.process_records,
        "remaining_owned_directories": [
            str(child.directory) for child in owned if child.directory.exists()
        ],
    }
    (tmp_path / "deadline-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return result, evidence


def assert_request_deadline(result, evidence):
    assert not evidence["watchdog_fired"], "stage setup reached the independent watchdog"
    activation = evidence["activation"]
    assert activation and activation["alive"] and not activation["result_present"]
    executing = evidence["stage"] == "blocking"
    assert activation["executing"] is activation["blocking"] is executing
    assert result.trace[-1]["event"] == "timed_out"
    assert result.budget["tool_rounds"] == result.budget["model_decisions"] == 1
    assert len(result.decisions) == 1 and result.token_accounting_complete
    tool = next(record for record in result.process_records if record["label"] == "tool")
    assert tool["pid"] == activation["pid"] and tool["operation_started"] is executing
    assert tool["stopped"] and tool["reaped"] and tool["exitcode"] is not None
    assert all(record["directory_cleaned"] for record in result.process_records)
    assert not evidence["remaining_owned_directories"]
    observation = next(event for event in result.trace if event["event"] == "observing")
    observed = observation["tool_result"]
    assert (observed["status"], observed["error_code"], observed["retryable"]) == (
        "cancelled", "cancelled", False
    ), "request monotonic deadline did not interrupt the tool wait"
    assert 600 <= observation["latency_ms"] < 1000
