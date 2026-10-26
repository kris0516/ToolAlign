"""Real CPU subprocesses exercise wall/output bounds and failure preservation."""

import hashlib
import json
import os

import pytest
from dpo_process_cases import (
    failed,
    fills_receipt_reserve,
    large_receipt,
    oversized_output,
    terminal_receipt,
    unicode_terminal_receipt,
    waiting,
)
from test_cuda_dpo_protocol import request

from toolalign.training.cuda_dpo import runtime
from toolalign.training.cuda_dpo.checkpoint import REQUIRED, inspect, seal
from toolalign.training.cuda_sft.protocol import encoded


@pytest.mark.parametrize("worker, wall, budget, status, reason", [
    (large_receipt, 10, 1024**2, "PASS", None),
    (waiting, 1, 1024**2, "FAIL", "wall_budget_exceeded"),
    (oversized_output, 10, 8192, "FAIL", "output_budget_exceeded"),
    (failed, 10, 1024**2, "FAIL", "original synthetic worker failure"),
])
def test_external_bounds_reap_the_owned_cpu_worker(tmp_path, monkeypatch, worker, wall, budget, status, reason):
    output = tmp_path / "output"
    run = request(output) | {"max_wall_seconds": wall, "max_output_bytes": budget}
    # Replace the process target with a picklable CPU fixture. The parent,
    # spawn/Pipe, actual signaling, file accounting, and terminal writes run normally.
    monkeypatch.setattr(runtime, "_child", worker)
    result = runtime.supervise(run)
    assert result["status"] == status
    if reason:
        assert reason in result["error"]
    assert json.loads((output / "summary.json").read_text()) == result
    if status == "PASS":
        assert runtime.output_size(output) <= budget
    if worker is oversized_output:
        assert (output / "synthetic-partial.txt").read_bytes() == b"x" * 32768
    with pytest.raises(ProcessLookupError):
        os.kill(json.loads((output / "process.json").read_text())["pid"], 0)


@pytest.mark.parametrize("worker, metadata", [
    (terminal_receipt, "s" * 8192), (unicode_terminal_receipt, "界" * 2048),
], ids=["r1-counterexample", "utf8-byte-accounting"])
def test_terminal_summary_counts_toward_complete_output(tmp_path, monkeypatch, worker, metadata):
    output = tmp_path / "output"
    run = request(output) | {"max_wall_seconds": 10, "max_output_bytes": 65536}
    monkeypatch.setattr(runtime, "_child", worker)
    result = runtime.supervise(run)
    summary = (output / "summary.json").read_bytes()
    actual_bytes = runtime.output_size(output)
    before_summary = actual_bytes - len(summary)
    proposed = {"status": "PASS", "synthetic": True,
                "identity": {"diagnostic_fixture_metadata": metadata},
                **{key: result[key] for key in (
                    "elapsed_seconds", "worker_exit_code", "interrupted_signal")}}
    proposed_bytes = encoded(proposed) + b"\n"
    (tmp_path / "observation.json").write_text(json.dumps({
        "authorized_bytes": run["max_output_bytes"], "without_final_summary": before_summary,
        "attempted_summary_bytes": len(proposed_bytes), "final_summary_bytes": len(summary),
        "actual_output_bytes": actual_bytes, "returned_status": result["status"],
        "summary_status": json.loads(summary)["status"],
    }, indent=2) + "\n")
    assert before_summary < run["max_output_bytes"] < before_summary + len(proposed_bytes)
    assert result["status"] == json.loads(summary)["status"] == "FAIL"
    assert result["error"] == "DPO_output_budget_exceeded"
    assert result["output_bytes_before_summary"] == before_summary
    assert result["attempted_summary_bytes"] == len(proposed_bytes)
    assert result["attempted_summary_sha256"] == hashlib.sha256(proposed_bytes).hexdigest()
    assert actual_bytes <= run["max_output_bytes"] and len(summary) <= 4096
    assert (output / "synthetic-output.bin").read_bytes() == b"x" * 60000
    assert json.loads(summary) == result
    with pytest.raises(ProcessLookupError):
        os.kill(json.loads((output / "process.json").read_text())["pid"], 0)


def test_running_worker_leaves_space_for_failure_receipt(tmp_path, monkeypatch):
    output = tmp_path / "output"
    run = request(output) | {"max_wall_seconds": 10, "max_output_bytes": 65536}
    monkeypatch.setattr(runtime, "_child", fills_receipt_reserve)
    result = runtime.supervise(run)
    assert result["status"] == "FAIL" and "output_budget_exceeded" in result["error"]
    assert runtime.output_size(output) <= run["max_output_bytes"]
    assert (output / "synthetic-output.bin").read_bytes() == b"x" * 62400
    assert json.loads((output / "summary.json").read_text()) == result
    with pytest.raises(ProcessLookupError):
        os.kill(json.loads((output / "process.json").read_text())["pid"], 0)


def test_too_small_budget_is_rejected_before_creating_output(tmp_path):
    output = tmp_path / "output"
    run = request(output) | {"max_output_bytes": 4096}
    with pytest.raises(ValueError, match="output_budget_has_no_receipt_space"):
        runtime.supervise(run)
    assert not output.exists()


def test_resume_rejects_unsealed_missing_changed_and_different_identity(tmp_path):
    root = tmp_path / "synthetic-checkpoint"
    root.mkdir()
    identity = {"synthetic": True, "run_kind": "dpo_capacity"}
    for name in REQUIRED - {"optimizer.pt"}:
        (root / name).write_bytes(b"synthetic file inventory fixture")
    (root / "trainer_state.json").write_bytes(encoded({"global_step": 1, "max_steps": 2}))
    with pytest.raises(ValueError, match="incomplete_native_checkpoint"):
        seal(root, identity=identity, step=1, pair_count=10, max_bytes=1024**2)
    (root / "optimizer.pt").write_bytes(b"synthetic Adam inventory fixture")
    with pytest.raises(FileNotFoundError):
        inspect(root, identity=identity, expected_sha="a" * 64, pair_count=10, max_bytes=1024**2)
    manifest = seal(root, identity=identity, step=1, pair_count=10, max_bytes=1024**2)
    arguments = {"identity": identity, "expected_sha": manifest["checkpoint_sha256"],
                 "pair_count": 10, "max_bytes": 1024**2}
    assert inspect(root, **arguments)["data_cursor"] == 8
    with pytest.raises(ValueError, match="checkpoint_identity"):
        inspect(root, **(arguments | {"identity": identity | {"run_kind": "dpo"}}))
    (root / "optimizer.pt").write_bytes(b"changed synthetic Adam fixture")
    with pytest.raises(ValueError, match="checkpoint_files"):
        inspect(root, **arguments)
