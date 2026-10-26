"""Real CPU subprocesses exercise wall/output bounds and failure preservation."""

import json
import os

import pytest
from dpo_process_cases import failed, large_receipt, oversized_output, waiting
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
    with pytest.raises(ProcessLookupError):
        os.kill(json.loads((output / "process.json").read_text())["pid"], 0)


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
