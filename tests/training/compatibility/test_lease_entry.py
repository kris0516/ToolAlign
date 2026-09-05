import os
import subprocess
import sys
from pathlib import Path

from toolalign.runtime import GPULease


def test_competing_model_entry_does_not_import_or_load(tmp_path):
    marker = tmp_path / "model-loaded"
    code = """
from pathlib import Path
from toolalign.training.compatibility.execution import leased_call
from toolalign.runtime import LockBusy
import sys
config = {'run_id':'p01-contender','mode':'smoke','budget':{},'lock_timeout_seconds':0.05}
try:
    leased_call(config, lambda: Path(sys.argv[1]).write_text('MODEL LOADED'))
except LockBusy:
    assert 'mlx.core' not in sys.modules
    raise SystemExit(23)
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[3] / "src")
    with GPULease(
        task_id="P01",
        worker_alias="test",
        run_id="p01-test-owner",
        expected_job="CPU contention test",
        memory_strategy="no model imports",
    ):
        result = subprocess.run(
            [sys.executable, "-c", code, str(marker)],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
    assert result.returncode == 23, result.stderr
    assert not marker.exists()


def test_package_and_help_do_not_import_model_backends():
    code = """
import sys
import toolalign.training.compatibility
from toolalign.training.compatibility import execution
assert not any(name in sys.modules for name in ('mlx.core', 'mlx_lm', 'torch', 'mlx_tune'))
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
