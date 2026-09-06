"""Independent CPU revision probes; also runnable with the installed default wheel.

All fixtures are fictional. Raw process identities stay in the supplied private output.
No worker test helpers, oracle truth, or model libraries are passed to the backend.
"""

from __future__ import annotations

import argparse
import copy
import errno
import hashlib
import json
import multiprocessing
import os
import signal
import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from toolalign.contracts import canonical_hash, validate_record
from toolalign.contracts.interfaces import ModelOutput, OracleTask, SandboxContext
from toolalign.evaluation import harness as harness_module
from toolalign.evaluation.harness import LocalHarness, summarize
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION, SemanticOracle
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools import executor as executor_module
from toolalign.tools.isolation import OwnedProcess
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend


def final(value):
    return {"kind": "final", "content": json.dumps(value), "tool_calls": []}


def call(name, arguments, call_id):
    return {"name": name, "arguments": arguments, "call_id": call_id}


def action(*calls):
    return {"kind": "tool_calls", "content": "", "tool_calls": list(calls)}


def step(name, arguments, output, *, status="completed", error=None, retryable=False):
    return dict(
        name=name,
        arguments=arguments,
        status=status,
        output=output,
        error_code=error,
        retryable=retryable,
    )


def fixture(registry, name, answers, strategies):
    example = {
        "schema_version": "toolalign.example.v1",
        "example_id": name,
        "source": "toolalign-original-review",
        "source_revision": "p03-r2-review.v1",
        "license_id": "MIT",
        "source_record_hash": canonical_hash({"fixture": name}),
        "group_id": name,
        "split": "validation",
        "category": "review-cpu",
        "messages": [
            {
                "role": "user",
                "content": "Check the supplied fictional values.",
                "tool_calls": [],
                "tool_call_id": None,
            }
        ],
        "tools": registry.tools,
        "expected_action": final(answers[0]),
    }
    task = OracleTask(
        name,
        name,
        "validation",
        example["expected_action"],
        {
            "version": ORACLE_VERSION,
            "answers": [{"kind": "final", "value": value} for value in answers],
            "strategies": strategies,
        },
    )
    return validate_record(example, "example"), task


def context(root, token=None, seconds=8):
    return SandboxContext(
        root.resolve(),
        "r1-revision-request",
        (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(),
        token or CancellationToken(),
    )


def sleeper(directory, marker):
    Path(marker).write_text(json.dumps({"pid": os.getpid(), "ppid": os.getppid()}))
    time.sleep(30)


def wait_marker(path):
    until = time.monotonic() + 4
    while not path.exists() and time.monotonic() < until:
        time.sleep(0.005)
    return json.loads(path.read_text())


class MarkerCancellation:
    def __init__(self, marker):
        self.marker = marker
        self.observed = False

    def is_cancelled(self):
        self.observed = self.observed or self.marker.exists()
        return self.observed


class RevisionBackend:
    def __init__(self, root, mode):
        self.root, self.mode, self.index = str(root), mode, 0

    def generate(self, request, generation_config):
        assert set(request) == {"messages", "tools"}
        assert generation_config.max_new_tokens == 256
        index = self.index
        self.index += 1
        root = Path(self.root)
        if self.mode.startswith("block") and index == 1:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        (root / f"entered-{index}.json").write_text(
            json.dumps({"pid": os.getpid(), "ppid": os.getppid()})
        )
        if self.mode == "crash":
            os._exit(23)
        if self.mode.startswith("block"):
            if index == 1:
                time.sleep(30)
            raw = json.dumps(
                action(
                    call(
                        "convert_numeric_units",
                        {"value": 2, "from_unit": "min", "to_unit": "s"},
                        "r2-first",
                    )
                )
            )
        else:
            raw = (
                "malformed-original-raw" if self.mode == "parse" else json.dumps(final({"sum": 11}))
            )
        return ModelOutput(
            raw, None, None, SCRIPTED_IDENTITY, 31, 257 if self.mode == "length" else 17, "stop"
        )


class Observations:
    def __init__(self, cleanup_fault=False):
        self.owned, self.proofs = [], []
        self.cleanup_fault = cleanup_fault
        self.failure = OSError(errno.EIO, "independent directory cleanup failure")

    def create(self, *args, **kwargs):
        owned = OwnedProcess(*args, **kwargs)
        proof = {
            "pid": owned.process.pid,
            "label": owned.record["label"],
            "handle_close_calls": 0,
            "cleanup_attempts": 0,
        }
        process_close = owned.process.close
        cleanup = owned._temporary.cleanup

        def close_handle():
            proof["handle_close_calls"] += 1
            proof.update(
                alive=owned.process.is_alive(),
                exitcode=owned.process.exitcode,
                present_in_active_children=owned.process in multiprocessing.active_children(),
            )
            process_close()

        def cleanup_directory():
            proof["cleanup_attempts"] += 1
            raise self.failure

        owned.process.close = close_handle
        if self.cleanup_fault and owned.record["label"] == "model":
            owned._temporary.cleanup = cleanup_directory
        self.owned.append((owned, cleanup))
        self.proofs.append(proof)
        return owned

    def restore(self):
        for owned, cleanup in self.owned:
            owned._temporary.cleanup = cleanup
            owned.close()


def close_retry(root, failures):
    observed = Observations(cleanup_fault=True)
    marker = root / "direct-entered.json"
    owned = observed.create(root.resolve(), sleeper, (str(marker),), "model")
    try:
        assert wait_marker(marker) == {"pid": owned.process.pid, "ppid": os.getpid()}
        for _ in range(failures):
            try:
                owned.close()
            except OSError as exc:
                assert exc is observed.failure
            else:
                raise AssertionError("Injected cleanup error was erased")
            assert owned.process._closed and owned._process_closed and not owned._closed
            assert owned.directory.exists() and not owned.record["directory_cleaned"]
        proof = observed.proofs[0]
        assert proof["handle_close_calls"] == 1 and proof["cleanup_attempts"] == failures
        assert proof["alive"] is False and not proof["present_in_active_children"]
        assert proof["exitcode"] == -signal.SIGTERM
        observed.restore()
        owned.close()
        assert owned._closed and owned.record["directory_cleaned"]
        assert not owned.directory.exists() and proof["handle_close_calls"] == 1
        return {
            "proof": proof,
            "original_error_identity_preserved": True,
            "directory_retry_succeeded": True,
            "later_close_noop": True,
        }
    finally:
        observed.restore()


def shutdown(root, mode, both_faults):
    observed = Observations(cleanup_fault=both_faults)
    original_owned, original_tool = harness_module.OwnedProcess, executor_module.OwnedProcess
    original_write = harness_module.write_packet
    counts = {"stop_attempts": 0}

    def stop_write(path, value, *args, **kwargs):
        if path.name == "stop.json":
            counts["stop_attempts"] += 1
            if both_faults:
                raise OSError(errno.EIO, "independent stop write failure")
        return original_write(path, value, *args, **kwargs)

    separate_marker = root / "separate-entered.json"
    separate = multiprocessing.get_context("spawn").Process(
        target=sleeper, args=(str(root), str(separate_marker))
    )
    separate.start()
    harness_module.OwnedProcess = executor_module.OwnedProcess = observed.create
    harness_module.write_packet = stop_write
    try:
        assert wait_marker(separate_marker) == {"pid": separate.pid, "ppid": os.getpid()}
        registry = LocalToolRegistry()
        example, task = fixture(registry, "r2-shutdown", [{"sum": 11}], [[]])
        token = MarkerCancellation(root / "entered-1.json") if mode == "block_cancel" else None
        result = LocalHarness(registry, LocalToolExecutor(registry)).run(
            example,
            task,
            RevisionBackend(root, mode),
            context(root, token, seconds=1.2 if mode == "block_timeout" else 8),
            model_identity=SCRIPTED_IDENTITY,
        )
        model, cleanup = observed.owned[0]
        assert wait_marker(root / "entered-0.json") == {
            "pid": observed.proofs[0]["pid"],
            "ppid": os.getpid(),
        }
        assert counts["stop_attempts"] == 1
        assert all(
            not p["alive"]
            and not p["present_in_active_children"]
            and p["exitcode"] is not None
            and p["handle_close_calls"] == 1
            for p in observed.proofs
        )
        assert separate.is_alive() and separate.pid not in {p["pid"] for p in observed.proofs}
        if mode.startswith("block"):
            assert wait_marker(root / "entered-1.json")["pid"] == observed.proofs[0]["pid"]
            assert observed.proofs[0]["exitcode"] == -signal.SIGKILL
            assert result.budget == {
                "model_decisions": 2,
                "tool_rounds": 1,
                "input_tokens": 31,
                "output_tokens": 17,
            }
            assert result.token_accounting_complete is False and len(result.decisions) == 1
            if token:
                assert token.observed
        elif mode == "crash":
            assert observed.proofs[0]["exitcode"] == 23
            assert result.budget == {
                "model_decisions": 1,
                "tool_rounds": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            }
            assert not result.token_accounting_complete and not result.decisions
        else:
            assert result.budget == {
                "model_decisions": 1,
                "tool_rounds": 0,
                "input_tokens": 31,
                "output_tokens": 257 if mode == "length" else 17,
            }
            assert result.token_accounting_complete and len(result.decisions) == 1
            expected_raw = (
                "malformed-original-raw" if mode == "parse" else json.dumps(final({"sum": 11}))
            )
            assert result.decisions[0]["raw_text"] == expected_raw
            assert result.decisions[0]["repaired_output"] is None
        terminal = result.trace[-1]
        expected_event = {
            "block_cancel": "cancelled",
            "block_timeout": "timed_out",
            "length": "budget_exhausted",
        }.get(mode, "rejected")
        if mode == "final" and not both_faults:
            expected_event = "finalized"
        assert terminal["event"] == expected_event
        assert terminal["task_outcome"] == asdict(result.score)
        for i, event in enumerate(result.trace):
            validate_record(event, "trace")
            assert event["event_index"] == i
        assert sum(e["task_outcome"] is not None for e in result.trace) == 1
        if mode == "parse":
            assert terminal["parse_failure"] == "invalid_raw_action"
            assert result.decisions[0]["raw_parse_failure"] == "invalid_raw_action"
            assert "parse_failure" in result.score.reason
        if mode == "final":
            assert result.final_result == final({"sum": 11})
        if both_faults:
            assert terminal["validation_failure"] == "harness_cleanup_error"
            assert result.process_records[0]["cleanup_errors"] == [
                "stop_signal_write_failed",
                "owned_process_close_failed",
            ]
            assert not result.process_records[0]["directory_cleaned"] and model.directory.exists()
            assert model.process._closed
            try:
                model.close()
            except OSError as exc:
                assert exc is observed.failure
            else:
                raise AssertionError("Repeated cleanup did not preserve original error")
            assert observed.proofs[0]["handle_close_calls"] == 1
            model._temporary.cleanup = cleanup
            model.close()
            model.close()
            assert not model.directory.exists() and model.record["directory_cleaned"]
            assert result.process_records[0]["directory_cleaned"] is False
        else:
            assert all(p["directory_cleaned"] for p in result.process_records)
        summary = summarize([result])
        assert summary["total"] == 1 and summary["excluded"] == 0
        assert summary["failure"] == int(both_faults or mode != "final")
        return {
            "mode": mode,
            "both_faults": both_faults,
            "counts": counts,
            "actual_processes": observed.proofs,
            "budget": result.budget,
            "terminal": terminal["event"],
            "parse_failure": terminal["parse_failure"],
            "process_records_at_return": result.process_records,
            "summary": summary,
            "unrelated_process_remained_alive": True,
            "returned_snapshot_not_rewritten_by_retry": True,
        }
    finally:
        harness_module.OwnedProcess, executor_module.OwnedProcess = original_owned, original_tool
        harness_module.write_packet = original_write
        observed.restore()
        if separate.is_alive():
            separate.terminate()
        separate.join(timeout=3)
        if separate.is_alive():
            separate.kill()
            separate.join(timeout=3)
        assert not separate.is_alive()
        separate.close()


class TimingOracle(SemanticOracle):
    def __init__(self):
        self.called_before_finalized = False

    def score(self, task, trace, final_result):
        assert not any(e["event"] == "finalized" for e in trace)
        self.called_before_finalized = True
        return super().score(task, trace, final_result)


def causal_baseline(root, kind):
    registry = LocalToolRegistry()
    if kind == "multi":
        a = {"value": 2, "from_unit": "min", "to_unit": "s"}
        b = {"resource_id": "beacon-1.1", "runtime_version": "3.12"}
        first = call("convert_numeric_units", a, "multi-first")
        second = call("compare_version_compatibility", b, "multi-second")
        expected = [
            step(first["name"], a, {**a, "converted_value": 120}),
            step(second["name"], b, {**b, "minimum_runtime": "3.11", "compatible": True}),
        ]
        answers = [
            {"seconds": 120, "compatible": True},
            {"milliseconds": 120000, "compatible": True},
        ]
        strategies, actions, faults = (
            [expected, list(reversed(expected))],
            [action(first, second)],
            None,
        )
    else:
        a = {"report_id": "beacon-110"}
        first, second = (
            call("query_build_report", a, "try-first"),
            call("query_build_report", a, "try-second"),
        )
        output = {
            "report_id": "beacon-110",
            "object": "beacon",
            "version": "1.1",
            "date": "2026-09-01",
            "passed": 9,
            "failed": 1,
            "duration_ms": 900,
        }
        strategies = [
            [
                step(
                    first["name"],
                    a,
                    None,
                    status="error",
                    error="injected_transient",
                    retryable=True,
                ),
                step(second["name"], a, output),
            ]
        ]
        answers, actions = [{"passed": 9, "failed": 1}], [action(first), action(second)]
        faults = {"query_build_report": ["transient", None]}
    example, task = fixture(registry, "r2-" + kind, answers, strategies)
    actions.append(final(answers[-1]))
    oracle = TimingOracle()
    result = LocalHarness(registry, LocalToolExecutor(registry, faults=faults), oracle).run(
        example,
        task,
        ScriptedCPUModelBackend([json.dumps(a) for a in actions]),
        context(root),
        model_identity=SCRIPTED_IDENTITY,
    )
    assert result.score.outcome == "success" and oracle.called_before_finalized
    assert result.budget["model_decisions"] == (2 if kind == "multi" else 3)
    assert result.budget["tool_rounds"] == (1 if kind == "multi" else 2)
    assert len(result.process_records) == 3 and all(
        p["reaped"] and p["directory_cleaned"] for p in result.process_records
    )
    return task, result


def causal_check(task, result, damage):
    trace, answer = copy.deepcopy(result.trace), copy.deepcopy(result.final_result)
    executions = [i for i, e in enumerate(trace) if e["event"] == "tool_execution"]
    observations = [i for i, e in enumerate(trace) if e["event"] == "observing"]
    expected = "unknown"
    if damage in ("legal-before", "legal-after", "wrong-answer-before", "wrong-answer-after"):
        if damage.endswith("before"):
            trace.pop()
        expected = "failure" if damage.startswith("wrong") else "success"
        if damage.startswith("wrong"):
            answer = final({"wrong_value": True})
    elif damage == "cross-observations":
        trace[observations[0]], trace[observations[1]] = (
            trace[observations[1]],
            trace[observations[0]],
        )
    elif damage == "replay-consumed-observation":
        trace[observations[1]] = copy.deepcopy(trace[observations[0]])
    elif damage == "changed-arguments":
        trace[observations[1]]["tool_call"]["arguments"]["unexpected"] = "r2-change"
    elif damage == "old-call-id":
        old = trace[executions[0]]["tool_call"]["call_id"]
        trace[observations[1]]["tool_call"]["call_id"] = old
        trace[observations[1]]["tool_result"]["call_id"] = old
    elif damage == "missing-second-execution":
        trace.pop(executions[1])
    elif damage == "overlap-second-execution":
        trace.insert(observations[0], copy.deepcopy(trace[executions[1]]))
    else:
        raise AssertionError(damage)
    for i, event in enumerate(trace):
        event["event_index"], event["latency_ms"] = i, float(i)
        validate_record(event, "trace")
    score = SemanticOracle().score(task, trace, answer)
    assert score.outcome == expected, (damage, score)
    return {
        "damage": damage,
        "wire_records": len(trace),
        "outcome": score.outcome,
        "trace_sha256": hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    if args.installed:
        assert sys.flags.isolated
        for module in (harness_module, executor_module, sys.modules[SemanticOracle.__module__]):
            assert Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
    assert not {"torch", "mlx", "mlx_lm", "transformers", "tokenizers"}.intersection(sys.modules)
    checks = []

    def run(name, function):
        directory = root / name
        directory.mkdir()
        try:
            proof = function(directory)
            record = {"name": name, "status": "PASS", "proof": proof}
        except Exception as exc:
            record = {"name": name, "status": "FAIL", "error": repr(exc)}
        checks.append(record)
        (directory / "observation.json").write_text(json.dumps(record, indent=2) + "\n")
        print(name, record["status"], flush=True)

    for failures in (1, 2):
        run(f"close-retry-{failures}", lambda p, n=failures: close_retry(p, n))
    for mode in ("final", "parse", "length", "crash", "block_cancel", "block_timeout"):
        run("combined-" + mode, lambda p, m=mode: shutdown(p, m, True))
    for mode in ("final", "parse", "crash"):
        run("control-" + mode, lambda p, m=mode: shutdown(p, m, False))
    for kind in ("multi", "retry"):
        base_root = root / (kind + "-baseline")
        base_root.mkdir()
        task, result = causal_baseline(base_root, kind)
        (base_root / "harness-result.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
        for damage in (
            "legal-before",
            "legal-after",
            "wrong-answer-before",
            "wrong-answer-after",
            "cross-observations",
            "replay-consumed-observation",
            "changed-arguments",
            "old-call-id",
            "missing-second-execution",
            "overlap-second-execution",
        ):
            run(kind + "-" + damage, lambda p, d=damage, t=task, r=result: causal_check(t, r, d))
    summary = {
        "checks": len(checks),
        "passed": sum(c["status"] == "PASS" for c in checks),
        "failed": sum(c["status"] == "FAIL" for c in checks),
        "causal_actual_baseline_runs": 2,
        "causal_score_checks": 20,
        "scripted_only": True,
        "real_model": "NOT_RUN",
        "installed": args.installed,
    }
    (root / "results.json").write_text(
        json.dumps({"summary": summary, "checks": checks}, indent=2) + "\n"
    )
    print(json.dumps(summary, sort_keys=True))
    return int(summary["failed"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
