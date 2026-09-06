"""Independent CPU scope, score and real-process terminal probes.

Lifecycle scenarios use fresh Git fixtures and small owned CPU processes.
Fault injection is explicit; no framework, production limit or T1 ledger is changed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import replace
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolalign.data.common import DataError
from toolalign.runtime.gpu_lock import GPULease, inspect_gpu_lock, lock_path
from toolalign.training.sft import native_toy as native
from toolalign.training.sft.mlx_adapter import _profile_device
from toolalign.training.sft.validation import Score, ValidationTotals, choose_score, validate_score

ROOT = Path(__file__).resolve().parents[3]


def score(**changes):
    return replace(Score("TOY_NATIVE_GPU", "1" * 64, "2" * 64, "3" * 64, "4" * 64,
                         2, 13, 88.0, 44, 2.0, scope="TOY_NATIVE_GPU"), **changes)


def test_complete_native_token_weighting_and_required_last_rank():
    totals = ValidationTotals(profile="TOY_NATIVE_GPU", split="validation", expected_ids=range(1, 14))
    records = [(rank, 2 + (rank - 1) % 4, rank / 7) for rank in range(1, 14)]
    for rank, tokens, mean in records[:-1]:
        totals.add(example_id=rank, profile="TOY_NATIVE_GPU", split="validation", ce_sum=mean * tokens, tokens=tokens)
    with pytest.raises(DataError, match="incomplete_validation"):
        totals.finish()
    rank, tokens, mean = records[-1]
    totals.add(example_id=rank, profile="TOY_NATIVE_GPU", split="validation", ce_sum=mean * tokens, tokens=tokens)
    assert totals.denominator == 44 and totals.count == 13
    assert totals.finish() == sum(mean * tokens for _, tokens, mean in records) / 44
    assert totals.finish() != sum(mean for _, _, mean in records) / 13


@pytest.mark.parametrize("changes", [
    {"profile": "formal"}, {"scope": "FORMAL"}, {"profile": "TOY_CPU"},
    {"scope": "TOY_CPU"}, {"profile": "unknown", "scope": "unknown"},
    {"selection_sha256": "G" * 64}, {"validation_identity_sha256": "a" * 63},
    {"parameter_content_sha256": "3" * 63 + "/"}, {"checkpoint_file_sha256": None},
    {"optimizer_step": 0}, {"optimizer_step": True}, {"processed_microsteps": 1},
    {"processed_microsteps": True}, {"supervised_tokens": 0}, {"supervised_tokens": True},
    {"supervised_tokens": 44.0}, {"ce_sum": math.inf}, {"ce_sum": -1.0},
    {"validation_ce": math.nan}, {"validation_ce": 88.0 / 43},
])
def test_native_scores_reject_invalid_scope_identity_counters_and_denominator(changes):
    with pytest.raises(DataError):
        validate_score(score(**changes))


@pytest.mark.parametrize("changes", [
    {"profile": "TOY_CPU", "scope": "TOY_CPU"}, {"selection_sha256": "5" * 64},
    {"validation_identity_sha256": "6" * 64},
])
def test_score_selection_cannot_compare_different_scopes_or_input_identities(changes):
    with pytest.raises(DataError, match="incomparable_validation_scores"):
        choose_score([score(), score(**changes)])


def test_native_score_tie_order_is_deterministic():
    earlier = score(optimizer_step=1, processed_microsteps=8, checkpoint_file_sha256="f" * 64)
    lower_hash = replace(earlier, checkpoint_file_sha256="a" * 64)
    for values in ([score(), earlier, lower_hash], [lower_hash, earlier, score()]):
        assert choose_score(values) == lower_hash


def test_profile_device_rejects_formal_and_cpu_gpu_mismatch_before_backend_use():
    fake = SimpleNamespace(cpu="cpu", gpu="gpu", default_device=lambda: "gpu")
    _profile_device(fake, "TOY_NATIVE_GPU")
    with pytest.raises(DataError, match="toy_profile_device_mismatch"):
        _profile_device(fake, "TOY_CPU")
    with pytest.raises(DataError, match="only_toy_score_authorized"):
        _profile_device(fake, "formal")


def test_no_lease_rejects_before_metadata_or_any_framework_import(monkeypatch, tmp_path):
    def forbidden(_):
        raise AssertionError("metadata must not be reached without lease")
    monkeypatch.setattr(native, "_versions", forbidden)
    before = set(sys.modules)
    with pytest.raises(DataError, match="active_current_native_lease_required"):
        native._numerics(root=tmp_path, mode="installed_segmented", config={}, original={}, dataset=(),
                         lease=None, repository=tmp_path)
    assert not native.NUMERICAL_MODULES & {name.split(".")[0] for name in set(sys.modules) - before}
    assert not list(tmp_path.iterdir())


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / "synthetic-repository"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=R1 CPU fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "--allow-empty",
                    "-m", "original CPU-only fixture"], check=True, capture_output=True)
    return repo


def test_real_current_cpu_fixture_lease_checks_inode_and_live_owner(repository, tmp_path):
    lease = GPULease(task_id="P04-SFT-NATIVE-TOY", worker_alias="R1", run_id="cpu-owner-check",
        expected_job="CPU guard only", memory_strategy="no frameworks", repository=repository)
    with lease:
        observation = native.require_current_lease(lease, repository)
        assert observation["owner"]["pid"] == os.getpid() and observation["owner"]["worker_alias"] == "R1"
        assert os.fstat(lease._handle.fileno()).st_ino == lock_path(repository).stat().st_ino
        original_handle = lease._handle
        with (tmp_path / "unrelated-descriptor").open("w+") as foreign:
            try:
                lease._handle = foreign
                with pytest.raises(DataError, match="native_lease_descriptor_mismatch"):
                    native.require_current_lease(lease, repository)
            finally:
                lease._handle = original_handle
        lease.metadata["worker_alias"] = "changed fixture claim"
        try:
            with pytest.raises(DataError, match="native_lease_owner_mismatch"):
                native.require_current_lease(lease, repository)
        finally:
            lease.metadata["worker_alias"] = "R1"
    assert inspect_gpu_lock(repository)["held"] is False


class OSMonitor:
    NoSuchProcess = ProcessLookupError

    class Process:
        def __init__(self, pid):
            self.pid = pid

        def memory_info(self):
            result = subprocess.run(["ps", "-p", str(self.pid), "-o", "rss="],
                                    capture_output=True, text=True, check=False)
            if result.returncode or not result.stdout.strip():
                raise ProcessLookupError(self.pid)
            return SimpleNamespace(rss=int(result.stdout.strip()) * 1024)

    @staticmethod
    def pid_exists(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True


CHILD = """
import json, os, sys, time
from pathlib import Path
from toolalign.runtime.gpu_lock import GPULease
repository, output, action = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
with GPULease(task_id='R1-CPU-TERMINAL-FIXTURE', worker_alias='R1', run_id=output.name,
              expected_job='small CPU process', memory_strategy='no frameworks', repository=repository):
    (output / 'ready.json').write_text(json.dumps({'pid': os.getpid(), 'frameworks':
        sorted({'mlx','mlx_lm','torch','numpy'} & {n.split('.')[0] for n in sys.modules})}))
    if action == 'disk':
        (output / 'actual-9000-byte-file').write_bytes(b'x' * 9000)
    if action != 'exit':
        time.sleep(20)
"""


def fail_diagnostic(_):
    raise OSError("explicit independent final diagnostic fault")


@pytest.mark.parametrize("scenario", ["disk_and_identity", "monitor", "final_stdout", "launch", "rss"])
def test_actual_cpu_process_failure_preserves_terminal_and_retry(repository, tmp_path, monkeypatch, scenario):
    root, output = tmp_path / "owned-round", tmp_path / "owned-round/run-one"
    output.mkdir(parents=True)
    identities = native.consumer_identity()
    reservation = native._reserve(root, output, "source_segmented", {"fixture": "R1_CPU_ONLY", "scenario": scenario})
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(native.__file__).resolve().parents[3])
    action = "disk" if scenario == "disk_and_identity" else "exit" if scenario == "final_stdout" else "sleep"
    command = [sys.executable, "-B", "-c", CHILD, str(repository), str(output), action]
    monitor = OSMonitor
    if scenario == "disk_and_identity":
        monkeypatch.setattr(native, "_disk_bytes", partial(native._disk_bytes, limit=8192))
        monkeypatch.setattr(native, "consumer_identity", lambda: fail_diagnostic(None))
    elif scenario in ("monitor", "rss"):
        class FaultMonitor(OSMonitor):
            class Process(OSMonitor.Process):
                def memory_info(self):
                    # Wait for the actual child to hold its fixture lease before injecting failure.
                    deadline = time.monotonic() + 5
                    while not (output / "ready.json").is_file() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    assert (output / "ready.json").is_file()
                    if scenario == "monitor":
                        raise OSError("explicit independent monitor fault")
                    return SimpleNamespace(rss=4 * 1024**3 + 1)  # Injected, never a measured RSS claim.
        monitor = FaultMonitor
    elif scenario == "final_stdout":
        original_sha = native._sha
        monkeypatch.setattr(native, "_sha", lambda p: fail_diagnostic(p) if Path(p).name == "stdout.log" else original_sha(p))
    elif scenario == "launch":
        command = [str(output / "absent-executable")]
    code = native._supervise_process(root=root, output=output, repository=repository,
        command=command, environment=environment, identities=identities, reservation=reservation, monitor=monitor)
    assert code == 1
    terminal = json.loads((output / "supervision.json").read_text())
    assert terminal["own_pid_exists"] is False and inspect_gpu_lock(repository)["held"] is False
    if scenario == "launch":
        assert terminal["pid"] is None and terminal["actual_child_exit"] is None
        assert terminal["error"]["stage"] == "launch" and terminal["own_process_reaped"] is False
    else:
        ready = json.loads((output / "ready.json").read_text())
        assert ready["frameworks"] == [] and ready["pid"] == terminal["pid"]
        assert not OSMonitor.pid_exists(ready["pid"]) and terminal["own_process_reaped"] is True
        assert inspect_gpu_lock(repository)["last_owner"]["pid"] == ready["pid"]
    stages = {item["stage"] for item in terminal["diagnostic_errors"]}
    if scenario == "disk_and_identity":
        assert terminal["error"]["message"] == "native_private_disk_budget"
        assert terminal["consumer_unchanged"] is None and terminal["private_disk_bytes"] is None
        assert stages == {"consumer_identity", "private_disk_bytes"}
    elif scenario == "final_stdout":
        assert terminal["actual_child_exit"] == 0 and terminal["error"] is None
        assert terminal["stdout_sha256"] is None and stages == {"stdout_hash"}
    elif scenario in ("monitor", "rss"):
        assert terminal["error"]["stage"] == "monitor" and terminal["actual_child_exit"] != 0
        assert stages == set() and terminal["consumer_unchanged"] is True
    for stream in ("stdout", "stderr"):
        digest = terminal[stream + "_sha256"]
        if digest is not None:
            assert hashlib.sha256((output / (stream + ".log")).read_bytes()).hexdigest() == digest
    assert native._reserve(root, root / "authorized-fixture-retry", "source_segmented", {"fixture": "CPU_ONLY"})["launch_number"] == 2


def test_original_controller_loses_terminal_on_final_disk_failure(repository, tmp_path, monkeypatch):
    # Import the exact historical file; substitute only preflight metadata and
    # the child command with a tiny CPU sleeper. Never execute its framework child.
    raw = subprocess.check_output(["git", "show", "534445bb8eecd600b65e90e541cd30601b4fd07c:src/toolalign/training/sft/native_toy.py"], cwd=ROOT)
    assert hashlib.sha256(raw).hexdigest() == "64bb9d357ebf089e24cdda20907cb9bba81f8ed3dd04d254acdae6d5b96490dd"
    old_path = tmp_path / "preserved-original-native.py"
    old_path.write_bytes(raw)
    name = "toolalign.training.sft.r1_original_cpu_fixture"
    spec = importlib.util.spec_from_file_location(name, old_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root, output = tmp_path / "old-round", tmp_path / "old-round/original-disk"
    root.mkdir()
    owned, calls, discarded = [], [], []
    real_popen = subprocess.Popen

    def spawn_cpu(command, **kwargs):
        discarded.append(command)
        process = real_popen([sys.executable, "-B", "-I", "-S", "-c", "import time; time.sleep(20)"], **kwargs)
        owned.append(process)
        return process

    def disk_fault(_):
        calls.append(time.monotonic())
        if len(calls) >= 2:
            raise DataError("native_private_disk_budget")
        return 0

    monkeypatch.setattr(module, "sys", SimpleNamespace(flags=SimpleNamespace(isolated=True, no_site=True),
        dont_write_bytecode=True, modules=sys.modules, executable=sys.executable, path=sys.path[:], argv=["CPU-only original controller probe"]))
    monkeypatch.setattr(module, "subprocess", SimpleNamespace(Popen=spawn_cpu, check_output=subprocess.check_output,
                                                             TimeoutExpired=subprocess.TimeoutExpired))
    monkeypatch.setitem(sys.modules, "psutil", OSMonitor)
    monkeypatch.setattr(module, "load_inputs", lambda *args: ({"limits": {}}, None, None))
    monkeypatch.setattr(module, "_validate_output", lambda *args: (root, output))
    monkeypatch.setattr(module, "_versions", lambda _: {})
    monkeypatch.setattr(module, "_origins", lambda: {})
    monkeypatch.setattr(module, "_disk_bytes", disk_fault)
    args = SimpleNamespace(repository=repository, output=output, mode="source_segmented",
                           config=tmp_path / "not-consumed-config", cases=tmp_path / "not-consumed-cases")
    try:
        with pytest.raises(DataError, match="native_private_disk_budget"):
            module.supervise(args)
        assert len(owned) == 1 and owned[0].returncode is not None and not OSMonitor.pid_exists(owned[0].pid)
        assert len(calls) == 3 and not (output / "supervision.json").exists()
        assert (root / "framework-launches/launch-01.json").is_file()
        with pytest.raises(DataError, match="native_success_or_active_mode_must_not_repeat"):
            module._reserve(root, root / "unavailable-retry", "source_segmented", {})
        proof = {"scope": "CPU_ONLY_FAULT_INJECTION", "old_source_sha256": hashlib.sha256(raw).hexdigest(),
                 "pid": owned[0].pid, "actual_exit": owned[0].returncode, "reaped": True,
                 "framework_command_discarded": discarded, "actual_command": owned[0].args,
                 "terminal_written": False, "retry_blocked": True, "new_framework_launches": 0}
        (root / "independent-original-reproduction.json").write_text(json.dumps(proof, indent=2) + "\n")
    finally:
        for process in owned:
            if process.poll() is None:
                process.kill()
                process.wait()
