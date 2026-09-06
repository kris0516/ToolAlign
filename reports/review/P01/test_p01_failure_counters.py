"""Exercise the candidate's exact callback body without a model/backend import."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import math
import textwrap
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolalign.training.compatibility import fallback_probe
from toolalign.training.compatibility.core import assert_initial_dpo_loss, write_json


def callback_unit(tmp_path):
    """Extract a trusted source class verbatim to isolate its original callback.

    Dependency names that normally live in the enclosing function are supplied as
    module globals. This tests callback bookkeeping, not the native MLX trainer.
    The upstream trainer's update-before-callback order is separately source-audited.
    """
    source = Path(fallback_probe.__file__).read_text()
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "run_fallback")
    cls = next(node for node in function.body
               if isinstance(node, ast.ClassDef) and node.name == "Callback")
    segment = "".join(source.splitlines(keepends=True)[cls.lineno - 1:cls.end_lineno])
    isolated = textwrap.dedent(segment)
    path = tmp_path / "original_callback_unit.py"
    path.write_text(isolated)
    spec = importlib.util.spec_from_file_location("p01_original_callback_unit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.original_callback_sha256 = hashlib.sha256(isolated.encode()).hexdigest()
    return module


@pytest.mark.parametrize("last_loss", [math.log(2), 0.6945998072624207])
def test_first_accumulation_boundary_records_actual_update_even_when_gate_fails(tmp_path, last_loss):
    unit = callback_unit(tmp_path)
    row = SimpleNamespace(completion_mask=(0, 0, 1, 1), token_ids=(1, 2, 3, 9))
    progress = {"microsteps": 39, "training_tokens": 400, "processed_tokens": 1000,
                "processed_nonpadding_tokens": 1000, "optimizer_steps": 4}
    unit.mx = SimpleNamespace(synchronize=lambda: None)
    unit.math = math
    unit.time = time
    unit.accumulation = 8
    unit.assert_initial_dpo_loss = assert_initial_dpo_loss
    unit.active_pair = row, row
    unit.progress = progress
    # Native upstream step() has already performed the boundary optimizer update.
    unit.optimizer = SimpleNamespace(step=SimpleNamespace(item=lambda: 1))
    unit.sft_optimizer_steps = 4
    unit.iteration_start = time.perf_counter()
    unit.reports = []
    unit.root = tmp_path
    unit.write_json = write_json
    unit.check = lambda: write_json(tmp_path / "progress.json", progress)
    info = {"iteration": 8, "train_loss": last_loss}
    if abs(last_loss - math.log(2)) <= 2e-6:
        unit.Callback().on_train_loss_report(info)
    else:
        with pytest.raises(ValueError, match="Training-path"):
            unit.Callback().on_train_loss_report(info)
    write_json(tmp_path / "callback-observation.json", {
        "callback_sha256": unit.original_callback_sha256,
        "upstream_optimizer_step_before_callback": 1,
        "reported_progress_after_callback": progress,
        "bad_initial_loss": abs(last_loss - math.log(2)) > 2e-6,
    })
    assert progress["optimizer_steps"] == 5, "A completed native update disappeared from failure counters"
    assert progress["microsteps"] == 40
    assert progress["training_tokens"] == 404
    assert json.loads((tmp_path / "progress.json").read_text())["optimizer_steps"] == 5
