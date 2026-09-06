"""CPU-only native-entry boundaries; these fixtures are never optimized.

The thirteen numerical cases remain a separate hash-bound private input.
These deliberately different records exercise only the pre-import guards.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from toolalign.data.common import DataError
from toolalign.runtime.gpu_lock import GPULease
from toolalign.training.sft.config import consumer_identity as cpu_identity
from toolalign.training.sft.mlx_adapter import backend
from toolalign.training.sft.native_toy import (
    CASES_SHA256,
    CONFIG_SHA256,
    NUMERICAL_MODULES,
    ROUND,
    SCOPE,
    _case_bounds,
    _disk_bytes,
    _exact_json,
    _reserve,
    _validate_output,
    consumer_identity,
    load_inputs,
    require_current_lease,
)
from toolalign.training.sft.validation import Score, ValidationTotals, choose_score, validate_score

ROOT = Path(__file__).resolve().parents[3]


def guard_records():
    ids = [1, 2, 3, 7] + [0] * 12
    loss = [0, 0, 1, 1] + [0] * 12
    record = {"sequence_ids": ids, "attention_mask": [1] * 4 + [0] * 12, "loss_mask": loss,
        "causal_input_ids": ids[:-1], "causal_target_ids": ids[1:], "causal_loss_mask": loss[1:],
        "bucket": 16, "pad_token_id": 0, "unpadded_length": 4, "effective_supervised_targets": 2,
        "first_supervised_causal_position": 1, "last_supervised_causal_position": 2}
    return {"train": [[rank, copy.deepcopy(record)] for rank in range(1, 14)],
            "unique_examples": 13, "parameters": 64, "vocabulary": 8,
            "initial_table": [[0.0] * 8 for _ in range(8)]}


def score(scope=SCOPE, **changes):
    value = Score(scope, "1" * 64, "2" * 64, "3" * 64, "4" * 64,
                  1, 8, 16.0, 8, 2.0, scope=scope)
    return replace(value, **changes)


def test_default_imports_and_native_identity_include_real_new_source():
    assert not NUMERICAL_MODULES & {n.split(".")[0] for n in sys.modules}
    with pytest.raises(DataError, match="active_shared_lease_required"):
        backend(None)
    with pytest.raises(DataError, match="active_current_native_lease_required"):
        require_current_lease(None, ROOT)
    cpu, native = cpu_identity(), consumer_identity()
    assert len(cpu) == 8 and len(native["sft"]) == 9
    assert {k: v for k, v in native["sft"].items() if k != "native_toy.py"} == cpu
    import toolalign.training.sft.native_toy as module

    assert native["sft"]["native_toy.py"] == hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
    assert "runtime/gpu_lock.py" in native["support"]
    assert "training/compatibility/execution.py" in native["support"]
    assert not NUMERICAL_MODULES & {n.split(".")[0] for n in sys.modules}


def test_config_bytes_and_changed_original_input_fail_before_import(tmp_path):
    config = ROOT / "configs/sft-native-toy.v1.json"
    value = _exact_json(config, CONFIG_SHA256, "bad_config")
    assert value["scope"] == SCOPE and value["training_authorized"] is False
    assert value["original_cpu_cases_file_sha256"] == CASES_SHA256
    cases = tmp_path / "substitute.json"
    cases.write_text(json.dumps(guard_records()))
    with pytest.raises(DataError, match="native_cases_hash_mismatch"):
        load_inputs(config, cases, ROOT)
    changed = tmp_path / "changed-config.json"
    changed.write_bytes(config.read_bytes() + b"\n")
    with pytest.raises(DataError, match="native_config_hash_mismatch"):
        load_inputs(changed, cases, ROOT)
    assert not NUMERICAL_MODULES & {n.split(".")[0] for n in sys.modules}


def test_existing_file_symlink_is_not_an_exact_input(tmp_path):
    path, link = tmp_path / "file", tmp_path / "link"
    path.write_bytes(b"{}")
    link.symlink_to(path)
    with pytest.raises(DataError, match="untrusted"):
        _exact_json(link, hashlib.sha256(b"{}").hexdigest(), "untrusted")


@pytest.mark.parametrize(("field", "bad", "error"), [
    ("unique_examples", 14, "native_example_budget"),
    ("parameters", 4097, "native_parameter_budget"),
    ("parameters", True, "native_parameter_budget"),
    ("vocabulary", 17, "native_vocabulary_budget"),
    ("vocabulary", 0, "native_vocabulary_budget"),
    ("vocabulary", 9, "native_fixed_model_shape"),
    ("initial_table", [[0.0] * 9 for _ in range(8)], "native_fixed_model_shape"),
    ("initial_table", [[float("nan")] * 8 for _ in range(8)], "native_nonfinite_initial_state"),
])
def test_model_and_example_preimport_bounds(field, bad, error):
    value = guard_records()
    value[field] = bad
    with pytest.raises(DataError, match=error):
        _case_bounds(value)


@pytest.mark.parametrize(("field", "bad", "error"), [
    ("bucket", 17, "native_sequence_budget"),
    ("effective_supervised_targets", 0, "empty_native_supervision"),
    ("causal_loss_mask", [0] * 15, "batch_shift_or_denominator_mismatch"),
    ("attention_mask", [1] * 16, "batch_masks_mismatch"),
    ("first_supervised_causal_position", 15, "batch_boundaries_mismatch"),
])
def test_sequence_supervision_preimport_bounds(field, bad, error):
    value = guard_records()
    value["train"][0][1][field] = bad
    with pytest.raises(DataError, match=error):
        _case_bounds(value)


def test_guard_fixture_order_shift_eos_and_token_range():
    value = guard_records()
    dataset = _case_bounds(value)
    assert [rank for rank, _ in dataset] == list(range(1, 14))
    assert all(b.causal_target_ids[b.last_supervised_causal_position] == 7 for _, b in dataset)
    value["train"][0][0] = 2
    with pytest.raises(DataError, match="native_original_order"):
        _case_bounds(value)
    for token, error in ((8, "native_fixed_token_bounds"), (6, "native_original_eos")):
        value = guard_records()
        batch = value["train"][0][1]
        batch["sequence_ids"][3] = token
        batch["causal_input_ids"] = batch["sequence_ids"][:-1]
        batch["causal_target_ids"] = batch["sequence_ids"][1:]
        with pytest.raises(DataError, match=error):
            _case_bounds(value)


@pytest.mark.parametrize(("profile", "scope"), [
    ("formal", "formal"), ("smoke", "TOY_CPU"), ("TOY_NATIVE_GPU", "TOY_CPU"),
    ("TOY_CPU", "TOY_NATIVE_GPU"), ("unknown", "unknown"), ("TOY_NATIVE", "TOY_NATIVE_GPU"),
])
def test_score_rejects_unauthorized_or_mismatched_scope(profile, scope):
    with pytest.raises(DataError, match="only_toy_score_authorized"):
        validate_score(replace(score(), profile=profile, scope=scope))


def test_native_score_selection_and_cpu_gpu_partition():
    first, second = score(), score(optimizer_step=2, processed_microsteps=13, ce_sum=8.0, validation_ce=1.0)
    assert choose_score([first, second]) == second
    assert choose_score([first, replace(first, optimizer_step=2)]) == first
    lower_hash = replace(first, checkpoint_file_sha256="0" * 64)
    assert choose_score([first, lower_hash]) == lower_hash
    with pytest.raises(DataError, match="incomparable_validation_scores"):
        choose_score([first, score(scope="TOY_CPU")])
    with pytest.raises(DataError, match="invalid_score_loss"):
        validate_score(replace(first, supervised_tokens=0))


def test_native_totals_token_weighted_coverage_and_profile():
    totals = ValidationTotals(profile=SCOPE, split="validation", expected_ids=[1, 2])
    totals.add(example_id=1, profile=SCOPE, split="validation", ce_sum=2.0, tokens=1)
    with pytest.raises(DataError, match="validation_scope_mismatch"):
        totals.add(example_id=2, profile="TOY_CPU", split="validation", ce_sum=6.0, tokens=3)
    with pytest.raises(DataError, match="invalid_validation_denominator_or_loss"):
        totals.add(example_id=2, profile=SCOPE, split="validation", ce_sum=0.0, tokens=0)
    totals.add(example_id=2, profile=SCOPE, split="validation", ce_sum=9.0, tokens=3)
    assert totals.finish() == 11 / 4


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / "repository"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    return repo


def lease_for(repo):
    return GPULease(task_id="P04-SFT-NATIVE-TOY", worker_alias="T1", run_id="cpu-guard-only",
                    expected_job="pure CPU lease guard", memory_strategy="no frameworks", repository=repo)


def test_current_actual_lease_then_released_handle(repository):
    lease = lease_for(repository)
    with lease:
        observed = require_current_lease(lease, repository)
        assert observed["held"] and observed["owner"]["pid"] == os.getpid()
    with pytest.raises(DataError, match="active_current_native_lease_required"):
        require_current_lease(lease, repository)


def test_lease_from_different_physical_repository(repository, tmp_path):
    other = tmp_path / "other"
    subprocess.run(["git", "init", "-q", str(other)], check=True, capture_output=True)
    with lease_for(repository) as lease:
        with pytest.raises(DataError, match="native_lease_repository_mismatch"):
            require_current_lease(lease, other)


def test_noncurrent_pid_and_unlocked_descriptor_reject(repository):
    with lease_for(repository) as lease:
        handle = lease._handle
        handle.seek(0)
        record = json.load(handle)
        record["pid"] = os.getpid() + 1
        handle.seek(0)
        handle.truncate()
        json.dump(record, handle)
        handle.flush()
        with pytest.raises(DataError, match="active_current_native_lease_required"):
            require_current_lease(lease, repository)
        fcntl.flock(handle, fcntl.LOCK_UN)
        with pytest.raises(DataError, match="active_current_native_lease_required"):
            require_current_lease(lease, repository)


def test_wrong_file_descriptor_reject(repository, tmp_path):
    with lease_for(repository) as lease:
        actual = lease._handle
        with (tmp_path / "wrong-file").open("w+") as wrong:
            lease._handle = wrong
            try:
                with pytest.raises(DataError, match="native_lease_descriptor_mismatch"):
                    require_current_lease(lease, repository)
            finally:
                lease._handle = actual


def test_existing_output_and_outside_round_reject(repository):
    root = repository / ".toolalign-local" / ROUND
    root.mkdir(parents=True)
    existing = root / "preserved"
    existing.mkdir()
    for output in (existing, repository / "outside"):
        with pytest.raises(DataError, match="native_output_exists_or_outside_round"):
            _validate_output(repository, output)
    assert _validate_output(repository, root / "new")[1] == root / "new"


def test_disk_count_does_not_follow_cpu_guard_fixture_links(tmp_path):
    root = tmp_path / "round"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"x" * 1024)
    link = root / "rejection-fixture-link"
    link.symlink_to(outside)
    assert _disk_bytes(root) == link.lstat().st_size < 1024


def test_launch_ledger_counts_failures_and_refuses_sixth(repository):
    root = repository / ".toolalign-local" / ROUND
    root.mkdir(parents=True)
    for index in range(5):
        output = root / f"failure-{index}"
        output.mkdir()
        reservation = _reserve(root, output, "source_segmented", {"original": True})
        assert reservation["launch_number"] == index + 1
        (output / "supervision.json").write_text(json.dumps({"exit_code": 1}))
    with pytest.raises(DataError, match="native_framework_launch_budget"):
        _reserve(root, root / "sixth", "source_segmented", {})
    assert len(list((root / "framework-launches").glob("launch-*.json"))) == 5


@pytest.mark.parametrize("terminal", [None, {"exit_code": 0}])
def test_success_or_running_mode_never_replayed(repository, terminal):
    root = repository / ".toolalign-local" / ROUND
    output = root / "first"
    output.mkdir(parents=True)
    _reserve(root, output, "source_segmented", {})
    if terminal is not None:
        (output / "supervision.json").write_text(json.dumps(terminal))
    with pytest.raises(DataError, match="native_success_or_active_mode_must_not_repeat"):
        _reserve(root, root / "second", "source_segmented", {})
