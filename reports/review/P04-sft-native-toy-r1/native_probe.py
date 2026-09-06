"""R1 process/lease wrapper around the frozen installed numerical entry point.

No training loop is implemented here. The separate R1 ledger permits at most
two framework subprocess launches, including failed launches.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

CANDIDATE = "f7326d1823c4cf132ae44525f4755c96c88ec159"
AUTHORIZATION = "482f8991c97c33678583aa6c853a75c41fda0f0f"
WHEEL_SHA = "0373c1adb1ae784391e82b06f6c93ab1519f593e68fec4c14c629829f83b5d3b"


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "target", "runtime", "wheel", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--mode", choices=("installed_segmented", "source_unsegmented_negative"), required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    inputs = json.loads(args.inputs.read_text())
    assert inputs["review_authorization"] == AUTHORIZATION
    assert inputs["review_task"] == "P04-SFT-NATIVE-TOY-R1" and inputs["review_framework_launch_limit"] == 2
    root, repository = Path(inputs["round_root"]).resolve(), Path(inputs["repository"]).resolve()
    output, target, runtime = args.output.absolute(), args.target.resolve(), args.runtime.resolve()
    assert root.name == "review-p04-sft-native-toy-r1" and root.parent == repository / ".toolalign-local"
    assert output.parent == root and all(not path.is_symlink() for path in (root, output, *root.parents))
    assert target.parent == root and not target.is_symlink()
    assert not Path.cwd().is_relative_to(repository / "src")
    sys.path[:0] = [str(target), str(runtime)]
    assert str(repository / "src") not in sys.path and str(Path.cwd()) not in sys.path
    assert sha(args.wheel) == WHEEL_SHA
    with zipfile.ZipFile(args.wheel) as archive:
        package = [name for name in archive.namelist() if name.startswith("toolalign/")]
        assert len(package) == 58
        assert all((target / name).read_bytes() == archive.read(name) for name in package)
    from toolalign.contracts import canonical_hash
    from toolalign.runtime.gpu_lock import GPULease, inspect_gpu_lock, lock_path
    from toolalign.training.sft import native_toy as native

    assert Path(native.__file__).resolve() == target / "toolalign/training/sft/native_toy.py"
    assert not native.NUMERICAL_MODULES & {name.split(".")[0] for name in sys.modules}
    config, original, dataset = native.load_inputs(inputs["config"], inputs["cases"], repository)
    versions = native._versions(config)
    assert config["training_authorized"] is False
    identities = native.consumer_identity()
    wrapper_sha = sha(__file__)
    if args.child:
        lease, code = None, 1
        try:
            registration = json.loads((output / "preregistration.json").read_text())
            assert registration["wrapper_sha256"] == wrapper_sha
            assert registration["consumer_identity"] == identities and registration["environment"] == versions
            assert registration["mode"] == args.mode
            lease = GPULease(task_id="P04-SFT-NATIVE-TOY", worker_alias="R1", run_id=output.name,
                expected_job=args.mode, memory_strategy="R1 fixed 13 cases; wall300s/RSS4GiB/MLX1GiB",
                repository=repository, timeout_seconds=0)
            lease.__enter__()
            before = native.require_current_lease(lease, repository)
            assert before["owner"]["worker_alias"] == "R1"
            descriptor = os.fstat(lease._handle.fileno())
            physical = lock_path(repository).stat()
            assert (descriptor.st_dev, descriptor.st_ino) == (physical.st_dev, physical.st_ino)
            save(output / "lease-acquired.json", {"at": utc(), "pid": os.getpid(), "actual_lock": before,
                "lock_path": str(lock_path(repository)), "fd_device": descriptor.st_dev, "fd_inode": descriptor.st_ino,
                "process_started_at": subprocess.check_output(["ps", "-p", str(os.getpid()), "-o", "lstart="], text=True).strip(),
                "numerical_modules_before_import": sorted(native.NUMERICAL_MODULES & {n.split(".")[0] for n in sys.modules}),
                "review_task": inputs["review_task"], "review_authorization": AUTHORIZATION})
            native._numerics(root=output, mode=args.mode, config=config, original=original, dataset=dataset,
                             lease=lease, repository=repository)
            observed = {}
            for name, module in sorted(tuple(sys.modules.items())):
                file = getattr(module, "__file__", None)
                if file is not None and Path(file).is_file():
                    path = Path(file).resolve()
                    if name == "toolalign" or name.startswith("toolalign."):
                        assert path.is_relative_to(target)
                    observed[name] = {"path": str(path), "sha256": sha(path)}
            save(output / "all-module-origins.json", {"at": utc(), "modules": observed, "sys_path": sys.path,
                "executable": sys.executable, "python": sys.version, "framework_loaded_under_lease": True,
                "lease_after_numerics": native.require_current_lease(lease, repository), "wrapper_sha256": wrapper_sha})
            code = 0
        except BaseException as exc:
            traceback.print_exc()
            try:
                save(output / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
            except BaseException:
                traceback.print_exc()
        finally:
            try:
                held = lease is not None and lease._handle is not None and not lease._handle.closed
                save(output / "child-terminal.json", {"at": utc(), "exit_code": code,
                    "pid": os.getpid(), "lease_held_until_process_exit": held, "wrapper_sha256": wrapper_sha})
            except BaseException:
                code = 1
                traceback.print_exc()
            finally:
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                finally:
                    os._exit(code)
    assert not output.exists()
    assert subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip() == CANDIDATE
    assert not inspect_gpu_lock(repository)["held"]
    native._disk_bytes(root)
    import psutil

    assert not native.NUMERICAL_MODULES & {name.split(".")[0] for name in sys.modules}
    output.mkdir(mode=0o700)
    ledger = root / "r1-framework-launches"
    ledger.mkdir(mode=0o700, exist_ok=True)
    with (ledger / "reservation.lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        prior = [json.loads(p.read_text()) for p in sorted(ledger.glob("launch-*.json"))]
        assert len(prior) < 2, "R1 launch limit includes failures"
        for record in prior:
            if record["mode"] == args.mode:
                assert json.loads((Path(record["output"]) / "supervision.json").read_text())["exit_code"] != 0
        if prior and args.mode == "source_unsegmented_negative":
            reason = "Directly observe the distinct single-segment 8-accumulation path losing five tail microsteps."
        else:
            reason = "Independently execute the frozen segmented path from a newly installed wheel."
        registration = {"at": utc(), "launch_number": len(prior) + 1, "launch_limit": 2,
            "mode": args.mode, "reason": reason, "scope": "TOY_NATIVE_GPU", "output": str(output),
            "review_task": inputs["review_task"], "review_authorization": AUTHORIZATION,
            "candidate": CANDIDATE, "config_sha256": sha(inputs["config"]), "cases_sha256": sha(inputs["cases"]),
            "wrapper_sha256": wrapper_sha, "consumer_identity": identities, "consumer_sha256": canonical_hash(identities),
            "limits": {**config["limits"], "review_framework_launches_max": 2}, "environment": versions,
            "wheel_sha256": WHEEL_SHA, "installed_target": str(target), "read_only_runtime": str(runtime),
            "parent_origins": native._origins(), "parent_argv": sys.argv, "parent_cwd": str(Path.cwd()),
            "parent_numerical_modules": [], "isolated": True, "no_site": True, "no_bytecode": True,
            "training_authorized": False}
        save(ledger / f"launch-{len(prior) + 1:02d}.json", registration)
    save(output / "preregistration.json", registration)
    command = [sys.executable, "-B", "-I", "-S", str(Path(__file__).resolve()), *sys.argv[1:], "--child"]
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "USE_TORCH", "USE_TF", "USE_FLAX"):
        environment.pop(name, None)
    environment.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
        HF_HUB_DISABLE_IMPLICIT_TOKEN="1", WANDB_MODE="disabled", TOKENIZERS_PARALLELISM="false",
        OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", PYTHONDONTWRITEBYTECODE="1")
    code = native._supervise_process(root=root, output=output, repository=repository,
        command=command, environment=environment, identities=identities, reservation=registration, monitor=psutil)
    save(output / "wrapper-terminal.json", {"at": utc(), "exit_code": code,
        "wrapper_sha256": sha(__file__), "wrapper_unchanged": sha(__file__) == wrapper_sha,
        "lock_after": inspect_gpu_lock(repository), "review_task": inputs["review_task"]})
    return code


if __name__ == "__main__":
    raise SystemExit(main())
