"""Actual Torch policy on CPU; CUDA metadata is an explicit fixture."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolalign.runtime.gpu_lock import GPULease, LockBusy
from toolalign.training.cuda_sft import runtime
from toolalign.training.cuda_sft.checkpoint import inspect_checkpoint
from toolalign.training.cuda_sft.protocol import CONFIG_SHA256, encoded, load_protocol

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def numeric_state(monkeypatch):
    torch = pytest.importorskip("torch")
    original = (torch.are_deterministic_algorithms_enabled(),
                torch.is_deterministic_algorithms_warn_only_enabled())
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":16:8")
    torch.use_deterministic_algorithms(False, warn_only=True)
    try:
        yield torch
    finally:
        torch.use_deterministic_algorithms(original[0], warn_only=original[1])


def test_execute_applies_policy_under_lease_before_first_cuda_check(tmp_path, monkeypatch, numeric_state):
    torch = numeric_state
    config = load_protocol(ROOT)
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True, timeout=30)
    request = {"schema": "toolalign.cuda-sft-run.v1", "authorized_by": "S1", "run_id": "policy-cpu",
        "run_kind": "capacity", "profile": "formal", "source_commit": "1" * 40,
        "config_sha256": CONFIG_SHA256, "array_manifest_sha256": "2" * 64,
        "dependency_lock_sha256": "3" * 64, "repository": str(repository), "lock_root": str(repository),
        "array_dir": str(tmp_path / "arrays"), "dependency_lock": str(tmp_path / "lock"),
        "model_root": str(tmp_path / "model"), "output_dir": str(tmp_path / "output"),
        "persistent_dir": str(tmp_path / "copy"), "max_optimizer_steps": 3,
        "validation_every_steps": 2, "checkpoint_every_steps": 2,
        "max_wall_seconds": 300, "max_output_bytes": 4096}
    # Replace only input I/O; execute(), validation, policy and GPULease are real.
    source = {"fixture": "no-real-model-or-data"}
    bundle = SimpleNamespace(manifest={"source": source, "run_kind": "capacity", "profile": "formal"})
    monkeypatch.setattr(runtime, "load_protocol", lambda _: config)
    monkeypatch.setattr(runtime, "source_identity", lambda *_: source)
    monkeypatch.setattr(runtime, "dependency_identity", lambda *_: {})
    monkeypatch.setattr(runtime, "read_bundle", lambda *_, **__: bundle)
    precision = (torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32)
    lease_args = dict(task_id="CPU-POLICY", worker_alias="test", run_id="no-model",
        expected_job="lock-check-only", memory_strategy="zero-model", repository=repository)
    calls = []

    def first_cuda_check():
        calls.append("cuda_boundary")
        assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == ":4096:8"
        assert torch.are_deterministic_algorithms_enabled()
        assert not torch.is_deterministic_algorithms_warn_only_enabled()
        assert (torch.backends.cuda.matmul.allow_tf32, torch.backends.cudnn.allow_tf32) == precision
        with pytest.raises(LockBusy), GPULease(**lease_args):
            pytest.fail("policy was applied outside the GPU lease")
        raise RuntimeError("CPU_fixture_stops_before_CUDA")

    monkeypatch.setattr(runtime, "require_cuda", first_cuda_check)
    with pytest.raises(RuntimeError, match="CPU_fixture_stops_before_CUDA"):
        runtime.execute(request)
    assert calls == ["cuda_boundary"]
    assert not Path(request["output_dir"]).exists()
    with GPULease(**lease_args):
        pass


@pytest.mark.parametrize("changed", ["strict", "warn_only", "workspace"])
def test_real_numeric_identity_changes_reject_checkpoint(tmp_path, monkeypatch, numeric_state, changed):
    torch = numeric_state
    config = load_protocol(ROOT)
    torch.use_deterministic_algorithms(True, warn_only=False)
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    monkeypatch.setattr(torch.cuda, "get_device_properties", lambda _: SimpleNamespace(
        name="CPU_METADATA_FIXTURE", major=0, minor=0, total_memory=0))
    request = {"run_kind": "capacity", "profile": "formal",
               "validation_every_steps": 2, "checkpoint_every_steps": 2}
    bundle = SimpleNamespace(manifest_sha256="1" * 64, manifest={"cohort_sha256": "2" * 64,
        "model": {"model_id": "ORIGINAL_CPU_FIXTURE", "model_revision": "3" * 40}})

    def identity():
        return runtime.runtime_identity(request, config, bundle, {"fixture": "source"}, {})

    saved = identity()
    assert saved["config_identity"] == CONFIG_SHA256
    assert saved["runtime"]["deterministic_algorithms"] is True
    assert saved["runtime"]["deterministic_warn_only"] is False
    assert saved["runtime"]["cublas_workspace_config"] == ":4096:8"
    (tmp_path / "manifest.json").write_bytes(encoded({"schema": "toolalign.cuda-sft-checkpoint.v1",
                                                     "complete": True, "identity": saved}))
    if changed == "workspace":
        monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":16:8")
    else:
        torch.use_deterministic_algorithms(changed != "strict", warn_only=changed == "warn_only")
    actual = identity()
    field = {"strict": "deterministic_algorithms", "warn_only": "deterministic_warn_only",
             "workspace": "cublas_workspace_config"}[changed]
    assert actual["runtime"][field] != saved["runtime"][field]
    # Reject at identity comparison, before looking for any tensor bytes.
    with pytest.raises(ValueError, match="checkpoint_identity_mismatch"):
        inspect_checkpoint(tmp_path, identity=actual)
