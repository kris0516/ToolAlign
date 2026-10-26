"""Original CPU-only protocol fixtures; no real data, tokenizer or model loads."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from toolalign.model_io import Sequence
from toolalign.runtime.gpu_lock import GPULease, LockBusy
from toolalign.training.cuda_sft.arrays import batch_from_record, checked_batch
from toolalign.training.cuda_sft.checkpoint import inspect_checkpoint
from toolalign.training.cuda_sft.protocol import (
    CONFIG_SHA256,
    canonical_sha,
    dependency_identity,
    encoded,
    load_protocol,
    parse_dependency_lock,
    read_bytes,
    sha,
    validate_run,
)
from toolalign.training.sft.collator import collate_sequence

ROOT = Path(__file__).resolve().parents[2]


def test_import_and_help_have_no_framework_side_effects():
    script = """
import os, sys
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':16:8'
import toolalign.training.cuda_sft.arrays
import toolalign.training.cuda_sft.runtime
assert not {'torch','transformers','tokenizers','peft','mlx','tensorflow','jax'} & set(sys.modules)
assert os.environ['CUBLAS_WORKSPACE_CONFIG'] == ':16:8'
"""
    subprocess.run([sys.executable, "-B", "-c", script], check=True, timeout=30)
    result = subprocess.run([sys.executable, "-B", "-m", "toolalign.training.cuda_sft", "train", "--help"],
                            capture_output=True, text=True, check=True, timeout=30)
    assert "--run-config" in result.stdout


def test_frozen_config_and_run_bounds():
    config = load_protocol(ROOT)
    assert config["schema"] == "toolalign.sft-cuda.v2"
    assert config["numerics"] == {"deterministic_algorithms": True,
                                  "deterministic_warn_only": False,
                                  "cublas_workspace_config": ":4096:8"}
    request = {"schema": "toolalign.cuda-sft-run.v1", "authorized_by": "S1", "run_id": "original-test",
        "run_kind": "capacity", "profile": "formal", "source_commit": "1" * 40,
        "config_sha256": CONFIG_SHA256, "array_manifest_sha256": "2" * 64,
        "dependency_lock_sha256": "3" * 64, "repository": "/repo", "lock_root": "/repo",
        "array_dir": "/arrays", "dependency_lock": "/lock", "model_root": "/model",
        "output_dir": "/output", "persistent_dir": "/copy", "max_optimizer_steps": 3,
        "validation_every_steps": 2, "checkpoint_every_steps": 2,
        "max_wall_seconds": 300, "max_output_bytes": 4 * 1024**2}
    assert validate_run(request, config) == request
    for patch, reason in [({"config_sha256": "0" * 64}, "config_identity"),
                          ({"config_sha256": sha(read_bytes(ROOT / "configs/sft-cuda.v1.json"))},
                           "config_identity"),
                          ({"max_optimizer_steps": 4}, "step_budget"),
                          ({"max_wall_seconds": True}, "max_wall"),
                          ({"profile": "smoke"}, "capacity_profile"),
                          ({"resume_from": "/checkpoint"}, "resume_identity")]:
        with pytest.raises(ValueError, match=reason):
            validate_run(request | patch, config)


def test_uv_lock_hashes_and_pin_failures(tmp_path):
    raw = ("--index-url https://pypi.org/simple\nPyTest==9.0.2 \\\n"
           "    --hash=sha256:" + "1" * 64 + " \\\n    --hash=sha256:" + "2" * 64 + "\n# via test\n").encode()
    assert parse_dependency_lock(raw) == {"pytest": "9.0.2"}
    for bad in (b"pytest>=9", b"pytest==9.*", b"pytest==9 --extra-flag", b"pytest==9 \\\n"):
        with pytest.raises(ValueError):
            parse_dependency_lock(bad)
    lock = tmp_path / "pins.txt"
    for raw, reason in [(b"pytest==0.0.0\n", "dependency_version_mismatch:pytest"),
                        (b"toolalign-nonexistent-original-test-dependency==1.0\n", "missing_dependency:")]:
        lock.write_bytes(raw)
        with pytest.raises(ValueError, match=reason):
            dependency_identity(lock, sha(raw))
    with pytest.raises(ValueError, match="dependency_lock_mismatch"):
        dependency_identity(lock, "f" * 64)


def test_batch_roundtrip_rejects_second_shift_wrong_mask_and_bool():
    sequence = Sequence("original", "answer", (0, 1), (0, 1, 2), (0, 1, 2, 3), (0, 0, 1, 1), 3)
    batch = collate_sequence(sequence, bucket=8, pad_token_id=0)
    assert batch_from_record(batch.record()) == batch
    for field, value in [("causal_target_ids", [2, 3, 0, 0, 0, 0, 0]),
                         ("loss_mask", [0, 1, 1, 1, 0, 0, 0, 0]),
                         ("sequence_ids", [False, 1, 2, 3, 0, 0, 0, 0])]:
        with pytest.raises(ValueError):
            batch_from_record(batch.record() | {field: value})


def test_portable_batch_binds_original_audit_and_one_eos():
    sequence = Sequence("original", "answer", (0, 1), (0, 1, 2), (0, 1, 2, 3), (0, 0, 1, 1), 3)
    batch = collate_sequence(sequence, bucket=8, pad_token_id=0)
    config = {"training": {"pad_token_id": 0, "eos_token_id": 3},
              "profiles": {"formal": {"padding_buckets": [8]}}}
    audit = sequence.metadata() | {"causal_input_ids_sha256": canonical_sha([0, 1, 2]),
                                   "causal_target_ids_sha256": canonical_sha([1, 2, 3])}
    record = {"batch": batch.record(), "original_line_sha256": "1" * 64,
              "sidecar": {"profile": "formal", "split": "train", "padding_bucket": 8, "audit": audit}}
    assert checked_batch(record, config=config, profile="formal", split="train") == batch
    with pytest.raises(ValueError, match="array_audit_mismatch"):
        checked_batch(record | {"sidecar": record["sidecar"] | {
            "audit": audit | {"sequence_sha256": "2" * 64}}}, config=config, profile="formal", split="train")
    with pytest.raises(ValueError, match="array_split"):
        checked_batch(record, config=config, profile="formal", split="validation")
    for token_position in (2, 3):
        # Preserve all structural shifts while removing or duplicating EOS.
        value = batch.record()
        value["sequence_ids"][token_position] = 3 if token_position == 2 else 2
        value["causal_input_ids"] = value["sequence_ids"][:-1]
        value["causal_target_ids"] = value["sequence_ids"][1:]
        with pytest.raises(ValueError, match="array_completion_eos"):
            checked_batch(record | {"batch": value}, config=config, profile="formal", split="train")


def test_incomplete_or_wrong_identity_checkpoint_is_rejected_without_torch(tmp_path):
    root = tmp_path / "checkpoint"
    root.mkdir()
    with pytest.raises(FileNotFoundError):
        inspect_checkpoint(root, identity={"fixture": "test"})
    (root / "manifest.json").write_bytes(encoded({"schema": "toolalign.cuda-sft-checkpoint.v1",
                                                  "complete": False}))
    with pytest.raises(ValueError, match="incomplete_checkpoint"):
        inspect_checkpoint(root, identity={"fixture": "test"})
    (root / "manifest.json").write_bytes(encoded({"schema": "toolalign.cuda-sft-checkpoint.v1",
        "complete": True, "identity": {"fixture": "different"}}))
    with pytest.raises(ValueError, match="identity_mismatch"):
        inspect_checkpoint(root, identity={"fixture": "test"})


def test_nonregular_input_is_finite_and_duplicate_gpu_lease_rejects(tmp_path):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="nonregular"):
        read_bytes(fifo)
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True, timeout=30)
    args = {"task_id": "CPU-FIXTURE", "worker_alias": "test", "run_id": "no-model",
            "expected_job": "lock-check-only", "memory_strategy": "zero-model", "repository": repository}
    with GPULease(**args):
        with pytest.raises(LockBusy):
            with GPULease(**args):
                pytest.fail("a duplicate lease entered its execution body")
    with GPULease(**args):
        pass
