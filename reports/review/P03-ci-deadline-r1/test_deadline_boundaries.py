"""Independent checks of the deadline test's real cleanup and escape path."""

import json
import multiprocessing
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests/evaluation/harness"))

import deadline_cases  # noqa: E402
from test_harness import run_case  # noqa: E402

from toolalign.evaluation import harness  # noqa: E402
from toolalign.tools import executor, isolation  # noqa: E402


def wait_without_markers(directory, *arguments):
    """Real child withholding the stage marker; only the watchdog can escape."""
    Path(directory, "review-child-entered.json").write_text("{}\n")
    time.sleep(60)


@pytest.mark.parametrize("mode", ["slow-cleanup", "missing-marker-watchdog"])
def test_real_cleanup_and_watchdog_boundaries(tmp_path, monkeypatch, mode):
    original_time = time.monotonic
    original_child = executor._tool_child
    original_owned = isolation.OwnedProcess
    original_cancellation = harness._RequestCancellation.is_cancelled
    original_modules = {module: module.time for module in (harness, executor, isolation)}
    original_timers = set(threading.enumerate())
    observations = []
    created = []

    def capture_owned(root, target, arguments, label):
        if mode == "missing-marker-watchdog" and label == "tool":
            target = wait_without_markers
        child = original_owned(root, target, arguments, label)
        created.append(child)
        close = child.close
        recorded = False

        def observe_close():
            nonlocal recorded
            if not recorded:
                recorded = True
                before = {
                    "pid": child.process.pid,
                    "label": label,
                    "alive": child.process.is_alive(),
                    "executing": (child.directory / "executing.json").exists(),
                    "blocking": (child.directory / "blocking.json").exists(),
                    "custom_marker": (child.directory / "review-child-entered.json").exists(),
                    "result_present": (child.directory / "result.json").exists(),
                    "real_started": original_time(),
                }
                if mode == "slow-cleanup" and label == "tool":
                    time.sleep(0.3)
                close()
                before.update({
                    "real_cleanup_seconds": original_time() - before["real_started"],
                    "process_handle_closed": child.process._closed,
                    "record": dict(child.record),
                    "directory_exists": child.directory.exists(),
                })
                observations.append(before)
            else:
                close()

        child.close = observe_close
        return child

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(isolation, "OwnedProcess", capture_owned)
            result, evidence = deadline_cases.run_deadline_case(
                tmp_path, scoped, run_case, stage="blocking",
                bypass_request=mode == "missing-marker-watchdog",
            )
            if mode == "slow-cleanup":
                deadline_cases.assert_request_deadline(result, evidence)
                observing = next(x for x in result.trace if x["event"] == "observing")
                assert 600 <= observing["latency_ms"] < 1000
                assert evidence["activation"]["elapsed_seconds"] >= 0.8
            else:
                with pytest.raises(AssertionError, match="independent watchdog"):
                    deadline_cases.assert_request_deadline(result, evidence)
                assert evidence["watchdog_fired"] and evidence["activation"] is None
                assert 10 <= evidence["elapsed_seconds"] < 15
                assert result.trace[-1]["event"] == "cancelled"
    finally:
        for child in created:
            child.close()
        (tmp_path / "independent-process-observations.json").write_text(
            json.dumps({"mode": mode, "observations": observations}, indent=2) + "\n"
        )

    assert time.monotonic is original_time
    assert executor._tool_child is original_child
    assert isolation.OwnedProcess is original_owned
    assert harness._RequestCancellation.is_cancelled is original_cancellation
    assert all(module.time is value for module, value in original_modules.items())
    assert not any(
        isinstance(thread, threading.Timer) and thread not in original_timers
        for thread in threading.enumerate()
    )
    assert len(observations) == 2 and len(created) == 2
    live = {child.pid for child in multiprocessing.active_children()}
    for record in observations:
        assert record["process_handle_closed"] and not record["directory_exists"]
        assert record["record"]["reaped"] and record["record"]["directory_cleaned"]
        assert record["record"]["exitcode"] is not None and record["pid"] not in live
    tool = next(record for record in observations if record["label"] == "tool")
    assert tool["alive"] and not tool["result_present"] and tool["record"]["stopped"]
    if mode == "slow-cleanup":
        assert tool["executing"] and tool["blocking"]
        assert tool["real_cleanup_seconds"] >= 0.3
    else:
        assert tool["custom_marker"] and not tool["executing"] and not tool["blocking"]
