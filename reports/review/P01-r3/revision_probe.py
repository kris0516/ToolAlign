"""Independent launch/report boundary probes; CPU fixtures, no ML dependencies.

Resource values below are deliberately injected fixtures, not machine measurements.
Only the explicitly spawned CPU children are eligible for cleanup.
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import hashlib
import importlib.abc
import importlib.util
import io
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

FORBIDDEN = {"mlx", "mlx_lm", "mlx_tune", "mlx_lm_lora", "torch", "transformers", "tokenizers"}
CANDIDATE = "9fe3cbe3a067725c37dc213bbf38f9c90ceb5066"


class DenyML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise AssertionError("Disallowed import: " + fullname)
        return None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    def reject(value):
        raise AssertionError("Nonstandard JSON: " + value)

    return json.loads(path.read_text(), parse_constant=reject)


CHILD = """
import json,os,signal,sys,time
from pathlib import Path
root=Path(sys.argv[1])
signal.signal(signal.SIGTERM,signal.SIG_IGN)
(root/'ready.tmp').write_text(json.dumps({'pid':os.getpid(),'ppid':os.getppid()}))
(root/'ready.tmp').replace(root/'ready.json')
deadline=time.monotonic()+30
while not (root/'release').exists() and time.monotonic()<deadline:
    time.sleep(0.002)
sys.exit(int(sys.argv[2]))
"""


def wait_ready(root, child):
    deadline = time.monotonic() + 3
    while not (root / "ready.json").exists() and time.monotonic() < deadline:
        time.sleep(0.002)
    assert read_json(root / "ready.json") == {"pid": child.pid, "ppid": os.getpid()}
    assert child.poll() is None


def check_case(case, args, fixture, report, unrelated):
    from toolalign.contracts import validate_record
    from toolalign.training.compatibility import execution
    from toolalign.training.compatibility.core import Budget, write_json

    name, stage, baseline, fault, mode = case
    root = args.output / "runs" / name
    request = {
        "run_id": "r1-r3-cpu-" + name,
        "mode": mode,
        "output_dir": str(root),
        "budget": asdict(Budget(max_wall_seconds=4)),
        "git_commit": CANDIDATE,
        "source_hash": sha(Path(execution.__file__)),
        "data_manifest_hash": fixture["data_manifest_hash"],
        "model_identity": fixture["model"],
        "hardware": fixture["hardware"],
        "dependency_versions": fixture["dependency_versions"],
    }
    config = args.output / (name + "-request.json")
    write_json(config, request)
    children, signals, wait_timeouts, logs = [], [], [], []
    popen_calls = process_calls = rss_calls = swap_calls = pressure_calls = 0
    real_popen, real_open = subprocess.Popen, Path.open
    error = {
        "environment": RuntimeError("R1 synthetic environment copy error"),
        "swap_timeout": subprocess.TimeoutExpired(["R1-swap-fixture"], 0.01),
        "stdout_eacces": PermissionError(errno.EACCES, "R1 stdout fixture"),
        "stdout_emfile": OSError(errno.EMFILE, "R1 stdout fixture"),
        "popen_eagain": BlockingIOError(errno.EAGAIN, "R1 Popen fixture"),
        "popen_eintr": InterruptedError(errno.EINTR, "R1 Popen fixture"),
        "process_factory": RuntimeError("R1 Process factory fixture"),
        "first_rss": OSError(errno.EIO, "R1 first RSS fixture"),
        "cancel": KeyboardInterrupt("R1 CPU cancellation fixture"),
    }.get(fault)

    class Child(real_popen):
        def wait(self, timeout=None):
            actual = 0.04 if timeout in (1, 10) else timeout
            try:
                return super().wait(timeout=actual)
            except subprocess.TimeoutExpired:
                wait_timeouts.append(timeout)
                raise

        def terminate(self):
            signals.append("terminate")
            return super().terminate()

        def kill(self):
            signals.append("kill")
            return super().kill()

    def spawn(command, **kwargs):
        nonlocal popen_calls
        popen_calls += 1
        assert command[1:5] == ["-m", "toolalign.training.compatibility", "_worker", "--config"]
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        if stage == "popen":
            raise error
        native_exit = 7 if fault == "exit7" else 0
        child = Child([sys.executable, "-I", "-c", CHILD, str(root), str(native_exit)], **kwargs)
        children.append(child)
        wait_ready(root, child)
        return child

    def swap():
        nonlocal swap_calls
        swap_calls += 1
        if fault == "swap_timeout":
            raise error
        return SimpleNamespace(used=baseline)

    def process(pid):
        nonlocal process_calls
        process_calls += 1
        assert len(children) == 1 and pid == children[0].pid
        if fault == "process_factory":
            raise error

        def memory_info():
            nonlocal rss_calls
            rss_calls += 1
            if fault in {"first_rss", "cancel"}:
                raise error
            value = request["budget"]["max_rss_bytes"] + 1 if fault == "budget" else 0
            return SimpleNamespace(rss=value)

        return SimpleNamespace(memory_info=memory_info)

    class NoSuchProcess(Exception):
        pass

    def pressure(command, **kwargs):
        nonlocal pressure_calls
        pressure_calls += 1
        assert command == ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]
        if fault in {"exit0", "exit7"} and pressure_calls >= 3:
            (root / "release").touch()
        return "1\n"

    def open_file(path, *positional, **kwargs):
        if path == root / "stdout.log" and positional == ("w",):
            if stage == "stdout_open":
                raise error
            stream = real_open(path, *positional, **kwargs)
            logs.append(stream)
            return stream
        return real_open(path, *positional, **kwargs)

    class BrokenEnvironment:
        def copy(self):
            raise error

    caught, result, already_reaped = None, None, None
    printed = io.StringIO()
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(execution, "prepare_config", lambda value: value))
            stack.enter_context(patch.dict(sys.modules, {"psutil": SimpleNamespace(
                Process=process, swap_memory=swap, NoSuchProcess=NoSuchProcess
            )}))
            stack.enter_context(patch.object(execution.subprocess, "Popen", spawn))
            stack.enter_context(patch.object(execution.subprocess, "check_output", pressure))
            stack.enter_context(patch.object(Path, "open", open_file))
            if fault == "environment":
                stack.enter_context(patch.object(execution.os, "environ", BrokenEnvironment()))
            stack.enter_context(contextlib.redirect_stdout(printed))
            try:
                result = execution.launch(config)
            except Exception as exc:
                caught = exc
        assert unrelated.poll() is None
        assert all(stream.closed for stream in logs)
        if children:
            child = children[0]
            assert child.poll() is not None, "Owned child escaped launch cleanup"
            try:
                os.waitpid(child.pid, os.WNOHANG)
            except ChildProcessError:
                already_reaped = True
            assert already_reaped is True
        resources = read_json(root / "resources.json")
        manifest = read_json(root / "run.json") if mode != "math" else None
        unstarted = stage != "monitor"
        stopping = fault in {"budget", "cancel"}
        normal = fault in {"exit0", "exit7"}
        expected_exit = (7 if fault == "exit7" else 0) if normal else 124 if stopping else 1
        expected_raw = None if unstarted else (7 if fault == "exit7" else 0) if normal else -signal.SIGKILL
        expected_stage = None if normal else stage
        expected_assessment = (
            "UNKNOWN" if fault == "exit0" else "FAILED" if fault == "exit7"
            else "STOPPED_RESOURCE" if stopping
            else "FAILED_INITIALIZATION" if unstarted else "FAILED_MONITOR"
        )
        assert caught is (None if normal or stopping else error)
        assert result == (expected_exit if normal or stopping else None)
        assert resources["exit_code"] == expected_exit
        assert resources["raw_process_exit_code"] == expected_raw
        assert resources["child_started"] is (not unstarted)
        assert resources["failure_stage"] == expected_stage
        assert resources["initial_swap_bytes"] == baseline
        if unstarted or fault in {"process_factory", "first_rss", "cancel"}:
            assert resources["peak_rss_bytes"] is None and resources["samples"] == []
        elif normal:
            assert resources["peak_rss_bytes"] == 0 and len(resources["samples"]) >= 3
        if unstarted:
            assert len(children) == process_calls == rss_calls == pressure_calls == 0
            assert popen_calls == (1 if stage == "popen" else 0)
            assert resources["monitor_error"] is None
            assert resources["initialization_error"] == {"type": type(error).__name__, "message": str(error)}
            assert signals == []
        else:
            assert len(children) == popen_calls == process_calls == 1
            assert resources["initialization_error"] is None
            assert signals == ([] if normal else ["terminate", "kill"])
            if normal:
                assert wait_timeouts.count(1) >= 2
            else:
                assert 10 in wait_timeouts
            if not normal and not stopping:
                assert resources["monitor_error"] == {"type": type(error).__name__, "message": str(error)}
        if manifest:
            validate_record(manifest)
            assert manifest["status"] == ("succeeded" if expected_exit == 0 else "failed")
            assert manifest["ended_at"] is not None and manifest["exit_code"] == expected_exit
            assert manifest["training_tokens"] == manifest["optimizer_steps"] == 0
        records = report.summarize(root.parent)["runs"]
        record = next(item for item in records if item["run_id"] == request["run_id"])
        assert record["assessment"] == expected_assessment
        assert record["raw_process_exit_code"] == expected_raw
        assert record["initial_swap_bytes"] == baseline
        if not resources["samples"]:
            assert record["max_swap_growth_bytes"] is None and record["max_pressure_level"] is None
        elif normal:
            assert record["max_swap_growth_bytes"] == 0 and record["max_pressure_level"] == 1
        assert json.loads(printed.getvalue())["exit_code"] == expected_exit
        return {
            "name": name, "status": "PASS", "failure_stage": resources["failure_stage"],
            "exception_type": type(caught).__name__ if caught else None,
            "original_exception_preserved": caught is error if caught else None,
            "popen_calls": popen_calls, "actual_children": len(children),
            "process_calls": process_calls, "rss_calls": rss_calls, "swap_calls": swap_calls,
            "pressure_calls": pressure_calls, "signals": signals, "wait_timeouts": wait_timeouts,
            "owned_child_reaped_before_test_cleanup": already_reaped,
            "unrelated_child_alive": True, "stdout_closed": all(s.closed for s in logs),
            "resources": resources, "summary": record, "launch_stdout": printed.getvalue(),
            "run_artifact_hashes": {p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file()},
        }
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    assert not any(name.split(".")[0] in FORBIDDEN for name in sys.modules)
    sys.meta_path.insert(0, DenyML())
    from toolalign.training.compatibility import execution

    module_path = Path(execution.__file__).resolve()
    if args.installed:
        assert sys.flags.isolated == 1
        assert module_path.is_relative_to(Path(sys.prefix).resolve())
        for name in FORBIDDEN:
            # The guard is removed briefly only for availability lookup, never import.
            guard = sys.meta_path.pop(0)
            try:
                assert importlib.util.find_spec(name) is None
            finally:
                sys.meta_path.insert(0, guard)
    spec = importlib.util.spec_from_file_location("r1_r3_bound_report", args.report)
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    fixture = read_json(args.fixture)
    cases = [
        ("environment", "environment", None, "environment", "smoke"),
        ("swap-timeout", "initial_swap", None, "swap_timeout", "smoke"),
        ("stdout-zero", "stdout_open", 0, "stdout_eacces", "smoke"),
        ("stdout-nonzero", "stdout_open", 4096, "stdout_emfile", "smoke"),
        ("popen-zero", "popen", 0, "popen_eagain", "smoke"),
        ("popen-nonzero", "popen", 8192, "popen_eintr", "smoke"),
        ("math-popen", "popen", 4096, "popen_eagain", "math"),
        ("process-before-rss", "monitor", 4096, "process_factory", "smoke"),
        ("first-rss", "monitor", 0, "first_rss", "smoke"),
        ("wait-exit-zero", "monitor", 0, "exit0", "smoke"),
        ("wait-exit-seven", "monitor", 4096, "exit7", "smoke"),
        ("budget", "monitor", 0, "budget", "smoke"),
        ("cancel-before-rss", "monitor", 4096, "cancel", "smoke"),
    ]
    unrelated_root = args.output / "unrelated"
    unrelated_root.mkdir()
    unrelated = subprocess.Popen([sys.executable, "-I", "-c", CHILD, str(unrelated_root), "0"])
    try:
        wait_ready(unrelated_root, unrelated)
        results = []
        for case in cases:
            result = check_case(case, args, fixture, report, unrelated)
            results.append(result)
            print(json.dumps({"case": case[0], "status": result["status"]}), flush=True)
        assert not any(name.split(".")[0] in FORBIDDEN for name in sys.modules)
    finally:
        if unrelated.poll() is None:
            unrelated.kill()
        unrelated.wait(timeout=3)
    evidence = {
        "candidate": CANDIDATE, "checks_passed": len(results), "checks": results,
        "execution_sha256": sha(module_path), "report_sha256": sha(args.report),
        "fixture_sha256": sha(args.fixture), "probe_sha256": sha(Path(__file__)),
        "installed_execution": args.installed, "execution_within_environment":
            module_path.is_relative_to(Path(sys.prefix).resolve()),
        "report_origin": "explicit separately bound report source; not part of wheel",
        "all_resource_values_are_injected_fixtures": True,
        "real_owned_cpu_children": 6, "real_unrelated_control_children": 1,
        "model_worker_started": False, "forbidden_modules_loaded": [],
    }
    (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"checks_passed": len(results), "evidence_sha256": sha(args.output / "evidence.json")}))


if __name__ == "__main__":
    main()
