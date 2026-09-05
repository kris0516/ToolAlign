import os
import subprocess
import sys
from pathlib import Path

from toolalign.runtime import GPULease


def test_competing_model_entry_does_not_import_or_load(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
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
        repository=tmp_path,
    ):
        result = subprocess.run(
            [sys.executable, "-c", code, str(marker)],
            env=env,
            cwd=tmp_path,
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


def test_worker_holds_lease_until_process_exit(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    code = """
import json, sys
from pathlib import Path
from toolalign.runtime import inspect_gpu_lock
from toolalign.training.compatibility import numerical
from toolalign.training.compatibility.execution import worker
numerical.check_numerics = lambda: {'held_during_operation': inspect_gpu_lock()['held']}
config = {'run_id':'p01-worker-exit','mode':'math','budget':{},'lock_timeout_seconds':0}
worker(config, Path(sys.argv[1]))
raise RuntimeError('dedicated worker must exit inside the lease')
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[3] / "src")
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    import json

    from toolalign.runtime import inspect_gpu_lock

    assert json.loads((tmp_path / "result.json").read_text())["held_during_operation"] is True
    assert inspect_gpu_lock(tmp_path)["held"] is False
