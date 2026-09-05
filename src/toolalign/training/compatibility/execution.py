"""Private run records, cooperative GPU lease and owned-process resource supervision."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from toolalign.contracts import validate_record
from toolalign.runtime import GPULease

from .core import Budget, BudgetExceeded, digest, file_hash, write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hardware_audit() -> dict:
    def output(args):
        return subprocess.check_output(args, text=True).strip()

    raw = json.loads(
        output(["system_profiler", "SPHardwareDataType", "SPDisplaysDataType", "-json"])
    )
    hw, gpu = raw["SPHardwareDataType"][0], raw["SPDisplaysDataType"][0]
    return {
        "platform": f"macOS {output(['sw_vers', '-productVersion'])}",
        "machine": platform.machine(),
        "memory_bytes": int(output(["sysctl", "-n", "hw.memsize"])),
        "accelerator": gpu["sppci_model"],
        "gpu_cores": int(gpu["sppci_cores"]),
        "model": hw["machine_model"],
        "cpu_description": hw["number_processors"],
        "python": platform.python_version(),
        "macos_build": output(["sw_vers", "-buildVersion"]),
    }


def dependency_versions() -> dict:
    names = [
        "mlx",
        "mlx-metal",
        "mlx-lm",
        "mlx-tune",
        "mlx-lm-lora",
        "torch",
        "transformers",
        "huggingface-hub",
        "numpy",
        "psutil",
        "jsonschema",
    ]
    result = {"python": platform.python_version()}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return result


def model_files(directory: Path, revision: str | None = None) -> dict:
    # Only explicit public-model files; never include cache credentials or hidden files.
    paths = [p for p in directory.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not any(p.suffix == ".safetensors" for p in paths):
        raise ValueError("No local weights; model entry points do not download")
    records = {
        p.name: {"sha256": file_hash(p), "size_bytes": p.stat().st_size} for p in sorted(paths)
    }
    if revision is not None:
        for name, record in records.items():
            metadata = directory / ".cache" / "huggingface" / "download" / (name + ".metadata")
            lines = metadata.read_text().splitlines()
            if lines[0] != revision:
                raise ValueError("Downloaded model metadata revision mismatch")
            if name.endswith(".safetensors") and record["sha256"] != lines[1]:
                raise ValueError("Model weight hash differs from Hub LFS SHA-256")
    return records


def prepare_config(config: dict) -> dict:
    config = dict(config)
    budget = Budget(**config["budget"])
    budget.validate()
    private_root = (Path.cwd() / ".toolalign-local").resolve()
    if not Path(config["output_dir"]).resolve().is_relative_to(private_root):
        raise ValueError("Run output must remain in this worktree private directory")
    disk_bytes = sum(
        p.stat().st_size for p in private_root.rglob("*") if p.is_file() and not p.is_symlink()
    )
    if disk_bytes > budget.max_disk_bytes:
        raise BudgetExceeded("private_disk_budget")
    config["private_disk_bytes_before"] = disk_bytes
    if config["mode"] not in {"math", "smoke", "calibrate"}:
        raise ValueError("Only bounded P01 probes are implemented")
    config["git_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source = {p.name: file_hash(p) for p in Path(__file__).parent.glob("*.py")}
    config["source_files"] = source
    config["source_hash"] = digest(source)
    config["hardware"] = hardware_audit()
    config["dependency_versions"] = dependency_versions()
    if config["mode"] != "math":
        from .samples import smoke_samples

        sft_steps, dpo_steps = config["sft_steps"], config.get("dpo_steps", 0)
        if type(sft_steps) is not int or type(dpo_steps) is not int:
            raise ValueError("Microstep counts must be integers")
        if not 0 < sft_steps <= 112 or not 0 <= dpo_steps <= 8:
            raise ValueError("P01 does not authorize formal training")
        if sft_steps + dpo_steps > budget.max_microsteps:
            raise ValueError("Planned microsteps exceed declared stop budget")
        if config["sequence_length"] not in {1024, 1536, 2048}:
            raise ValueError("Unregistered sequence bucket")
        if config["mode"] == "smoke" and (sft_steps > 32 or config["sequence_length"] != 1024):
            raise ValueError("0.6B smoke exceeds preregistration")

        if config["model_id"] not in {"Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B"}:
            raise ValueError("P01 only authorizes these original public checkpoints")
        expected_revisions = {
            "Qwen/Qwen3-0.6B": "c1899de289a04d12100db370d81485cdf75e47ca",
            "Qwen/Qwen3-1.7B": "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e",
        }
        if config["model_revision"] != expected_revisions[config["model_id"]]:
            raise ValueError("Model revision differs from preregistered source")
        files = model_files(Path(config["model_dir"]), config["model_revision"])
        config["model_files"] = files
        config["data_manifest_hash"] = digest(smoke_samples())
        config["model_identity"] = {
            "model_id": config["model_id"],
            "model_revision": config["model_revision"],
            "model_hash": digest(
                {k: v for k, v in files.items() if k.endswith(".safetensors") or k == "config.json"}
            ),
            "adapter_hash": None,
            "tokenizer_hash": digest(
                {
                    k: v
                    for k, v in files.items()
                    if "tokenizer" in k or k in ("vocab.json", "merges.txt")
                }
            ),
            "template_hash": digest(
                {
                    "template": json.loads(
                        (Path(config["model_dir"]) / "tokenizer_config.json").read_text()
                    )["chat_template"],
                    "enable_thinking": False,
                    "add_generation_prompt": True,
                }
            ),
            "quantization": "none; original bfloat16 weights",
        }
    return config


def new_manifest(config: dict) -> dict:
    hw = config["hardware"]
    record = {
        "schema_version": "toolalign.run.v1",
        "run_id": config["run_id"],
        "git_commit": config["git_commit"],
        "purpose": "compatibility",
        "data_manifest_hash": config["data_manifest_hash"],
        "model": config["model_identity"],
        "reference_model_hash": None,
        "backend": "mlx-lm SFT / " + config.get("dpo_backend", "mlx-tune") + " DPO compatibility",
        "dependency_versions": config["dependency_versions"],
        "seed": 42,
        "hardware": {k: hw[k] for k in ("platform", "machine", "memory_bytes", "accelerator")},
        "resource_policy": {
            "gpu_lock": "gpu0",
            "max_memory_bytes": config["budget"]["max_mlx_bytes"],
            "max_wall_seconds": config["budget"]["max_wall_seconds"],
        },
        "training_tokens": 0,
        "optimizer_steps": 0,
        "resume_semantics": "weights_only_restart",
        "started_at": utc_now(),
        "ended_at": None,
        "status": "running",
        "exit_code": None,
        "artifacts": [],
    }
    validate_record(record)
    return record


def collect_artifacts(root: Path) -> list[dict]:
    root = root.resolve()
    result = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Artifact symlinks are forbidden")
        if not path.is_file() or path.name == "run.json" or path.suffix == ".tmp":
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError("Artifact escaped private root")
        sha = file_hash(path)
        result.append(
            {
                "artifact_id": sha,
                "relative_path": path.relative_to(root).as_posix(),
                "sha256": sha,
                "size_bytes": path.stat().st_size,
                "media_type": "application/octet-stream",
            }
        )
    return result


def leased_call(config: dict, operation):
    """The callback (including ALL model imports) cannot execute before flock succeeds."""
    with GPULease(
        task_id="P01",
        worker_alias="T1",
        run_id=config["run_id"],
        expected_job=f"P01 {config['mode']}",
        memory_strategy=json.dumps(config["budget"]),
        timeout_seconds=config.get("lock_timeout_seconds", 0),
    ):
        try:
            return operation()
        finally:
            # At a successful return the operation frame has dropped its model references.
            # A failing process exits immediately; the OS also releases Metal state/flock.
            import gc

            gc.collect()
            if "mlx.core" in sys.modules:
                mx = sys.modules["mlx.core"]
                mx.synchronize()
                mx.clear_cache()


@contextmanager
def preserve_wired_limit(mx, events: list):
    """Suppress upstream process wired-limit setters; do not invoke the OS setter.

    This narrow adapter is scoped to a single dedicated leased process. Restore
    original API objects afterwards. Never change allocator/system limits here.
    """
    original = mx.set_wired_limit

    def record_only(limit):
        events.append({"event": "wired_limit_request_suppressed", "requested_bytes": int(limit)})
        return 0

    mx.set_wired_limit = record_only
    try:
        yield
    finally:
        mx.set_wired_limit = original


def worker(config: dict, root: Path) -> int:
    import traceback

    def operation():
        # Keep flock held until this dedicated worker process actually exits. In
        # particular, exception tracebacks may retain model tensors; releasing the
        # lease while unwinding would admit another model before those tensors die.
        code = 2
        try:
            write_json(root / "lease-acquired.json", {"acquired": True, "time": utc_now()})
            if config["mode"] == "math":
                from .numerical import check_numerics

                result = check_numerics()
            else:
                from .model_probe import run_model_probe

                result = run_model_probe(config, root)
            write_json(root / "result.json", result)
            code = 0
        except Exception as exc:
            traceback.print_exc()
            write_json(root / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
        os._exit(code)  # OS releases GPU residency and the leased descriptor together.

    try:
        return leased_call(config, operation)
    except Exception as exc:
        traceback.print_exc()
        write_json(root / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
        return 2


def launch(config_path: Path) -> int:
    """Watch only our own subprocess. Keep raw records private; no telemetry upload."""
    import psutil

    config = prepare_config(json.loads(config_path.read_text()))
    root = Path(config["output_dir"]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    prepared = root / "config.json"
    write_json(prepared, config)
    if config["mode"] != "math":
        write_json(root / "run.json", new_manifest(config))
    budget = Budget(**config["budget"])
    env = os.environ.copy()
    env.update(
        {
            "HF_HUB_OFFLINE": "1",
            "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "WANDB_MODE": "disabled",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    initial_swap = psutil.swap_memory().used
    started = time.monotonic()
    stop_reason = None
    peak_rss = 0
    samples = []
    with (root / "stdout.log").open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "toolalign.training.compatibility",
                "_worker",
                "--config",
                str(prepared),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        try:
            own = psutil.Process(process.pid)
            while process.poll() is None:
                try:
                    rss = own.memory_info().rss
                    swap = max(0, psutil.swap_memory().used - initial_swap)
                    pressure = int(
                        subprocess.check_output(
                            ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], text=True
                        ).strip()
                    )
                    wall = time.monotonic() - started
                    peak_rss = max(peak_rss, rss)
                    samples.append(
                        {
                            "wall_seconds": wall,
                            "rss_bytes": rss,
                            "swap_growth_bytes": swap,
                            "pressure": pressure,
                        }
                    )
                    budget.check(
                        wall=wall, rss_bytes=rss, swap_growth_bytes=swap, pressure=pressure
                    )
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
                except psutil.NoSuchProcess:
                    break
        except (BudgetExceeded, KeyboardInterrupt) as exc:
            stop_reason = str(exc) or type(exc).__name__
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    exit_code = process.returncode
    if stop_reason:
        exit_code = 124
    write_json(
        root / "resources.json",
        {
            "wall_seconds": time.monotonic() - started,
            "peak_rss_bytes": peak_rss,
            "initial_swap_bytes": initial_swap,
            "stop_reason": stop_reason,
            "samples": samples,
            "budget": asdict(budget),
            "raw_process_exit_code": process.returncode,
            "exit_code": exit_code,
        },
    )
    if config["mode"] != "math":
        record = json.loads((root / "run.json").read_text())
        if (root / "progress.json").exists():
            progress = json.loads((root / "progress.json").read_text())
            record["training_tokens"] = progress["training_tokens"]
            record["optimizer_steps"] = progress["optimizer_steps"]
            record["reference_model_hash"] = progress.get("reference_model_hash")
        record.update(
            {
                "ended_at": utc_now(),
                "exit_code": exit_code,
                "status": "succeeded" if exit_code == 0 else "failed",
                "artifacts": collect_artifacts(root),
            }
        )
        validate_record(record)
        write_json(root / "run.json", record)
    print(
        json.dumps(
            {
                "run_id": config["run_id"],
                "exit_code": exit_code,
                "peak_rss_bytes": peak_rss,
                "stop_reason": stop_reason,
            }
        )
    )
    return exit_code


@contextmanager
def measure_checkpoint_io(mx, events: list, phase: str):
    """Time real upstream safetensors writes separately from model compute."""
    original = mx.save_safetensors

    def measured(path, weights, *args, **kwargs):
        mx.synchronize()
        begin = time.perf_counter()
        result = original(path, weights, *args, **kwargs)
        mx.synchronize()
        events.append(
            {
                "event": "checkpoint_write",
                "phase": phase,
                "file": Path(path).name,
                "seconds": time.perf_counter() - begin,
            }
        )
        return result

    mx.save_safetensors = measured
    try:
        yield
    finally:
        mx.save_safetensors = original
