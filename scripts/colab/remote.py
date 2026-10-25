"""Instance-local setup and bounded tmux jobs. Invoked by control.py over SSH.

The sibling ``toolalign-staging`` directory is instance-local. Durable recovery
is established by the controller's verified download to the Mac, not its name.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from contextlib import contextmanager
from pathlib import Path

from support import (
    atomic_json,
    digest,
    file_manifest,
    json_bytes,
    read_json,
    time_remaining,
    utc_now,
    validate_payload,
)

REPOSITORY = Path("/content/toolalign")
LOCK_FILE = Path("requirements/cuda-linux-py312.lock.txt")
CUDA_INDEX = "https://download.pytorch.org/whl/cu128"
CONTROL_ALLOWANCE = 1024 * 1024  # Control JSON/logs in addition to trainer output.


def run_directory(repository: Path, payload: dict) -> Path:
    return repository / "runs" / payload["run_id"]


def tmux_name(payload: dict) -> str:
    return "toolalign-" + payload["run_id"]


def tmux_exists(payload: dict) -> bool:
    return subprocess.run(
        ["tmux", "has-session", "-t", "=" + tmux_name(payload)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    ).returncode == 0


@contextmanager
def registry(repository: Path, payload: dict):
    """Serialize short control mutations; the trainer separately owns GPULease."""
    directory = repository / ".toolalign-local/colab"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "session.json"
    with (directory / "control.lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        state = read_json(path) if path.exists() else {
            "session": payload["session"], "endpoint": payload["endpoint"],
            "runs": {}, "stopping": False,
        }
        if any(state[key] != payload[key] for key in ("session", "endpoint")):
            raise ValueError("checkout belongs to a different Colab session endpoint")
        yield state
        atomic_json(path, state)


def verify_source(repository: Path, payload: dict) -> None:
    current = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()
    if current != payload["source_commit"]:
        raise ValueError("source commit mismatch")
    subprocess.run(["git", "-C", str(repository), "diff", "--quiet", "HEAD"], check=True)
    if digest(repository / LOCK_FILE) != payload["dependency_lock_sha256"]:
        raise ValueError("dependency lock hash mismatch")


def setup_commands(repository: Path, python: str) -> list[list[str]]:
    """No framework/model invocation belongs in this installation plan."""
    environment = repository / ".toolalign-local/cuda-env"
    target_python = str(environment / "bin/python")
    return [
        [python, "-m", "venv", str(environment)],
        [target_python, "-m", "pip", "install", "--disable-pip-version-check",
         "--require-hashes", "--only-binary=:all:", "--extra-index-url", CUDA_INDEX,
         "-r", str(repository / LOCK_FILE)],
        [target_python, "-m", "pip", "check"],
    ]


def environment_identity(repository: Path) -> dict:
    code = (
        "import importlib.metadata as m,json,platform,sys; "
        "print(json.dumps({'python':list(sys.version_info[:3]),'platform':platform.platform(),"
        "'packages':{d.metadata['Name']:d.version for d in m.distributions()}}))"
    )
    actual = json.loads(subprocess.check_output(
        [str(repository / ".toolalign-local/cuda-env/bin/python"), "-c", code], text=True
    ))
    if actual["python"][:2] != [3, 12]:
        raise ValueError("CUDA environment requires Python 3.12")
    def normalize(value):
        return re.sub(r"[-_.]+", "-", value).lower()
    packages = {normalize(key): value for key, value in actual["packages"].items()}
    expected = dict(re.findall(
        r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", (repository / LOCK_FILE).read_text(), re.M
    ))
    if not expected or any(packages.get(normalize(key)) != value for key, value in expected.items()):
        raise ValueError("installed versions differ from the CUDA lock")
    extra = set(packages) - {normalize(key) for key in expected} - {"pip", "setuptools"}
    if extra:
        raise ValueError(f"unexpected packages in the dedicated environment: {sorted(extra)}")
    actual["dependency_lock_sha256"] = digest(repository / LOCK_FILE)
    return actual


def _setup(repository: Path, payload: dict) -> dict:
    validate_payload(payload, repository)
    directory = run_directory(repository, payload)
    with registry(repository, payload) as state:
        if state["stopping"]:
            raise ValueError("session is fenced for stop")
        previous = state["runs"].get(payload["run_id"])
        if previous:
            raise ValueError("setup already claimed this run ID; inspect status, do not repeat it")
        directory.mkdir(parents=True, exist_ok=False)
        state["runs"][payload["run_id"]] = {
            "run_config_sha256": payload["run_config_sha256"], "recovered": None,
        }
        atomic_json(directory / "control.json", payload)
        (directory / "run.json").write_text(payload["run_config_text"])
    verify_source(repository, payload)
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("setup requires Linux x86_64; do not install CUDA wheels on this Mac")
    if time_remaining(payload) <= 0:
        raise ValueError("allocation time budget is exhausted before setup")
    environment = repository / ".toolalign-local/cuda-env"
    ready = repository / ".toolalign-local/colab/environment.json"
    if environment.exists() and not ready.exists():
        raise ValueError("partial/unowned environment exists; preserve it and resolve explicitly")
    if ready.exists() and read_json(ready)["dependency_lock_sha256"] != payload["dependency_lock_sha256"]:
        raise ValueError("existing environment uses another lock; no in-place replacement")
    if not environment.exists():
        with (ready.parent / "environment-install.json").open("x") as claim:
            json.dump({"run_id": payload["run_id"], "started_at_utc": utc_now()}, claim)
        python = shutil.which("python3.12")
        if not python:
            raise ValueError("Python 3.12 must be provisioned before setup")
        with (directory / "setup.log").open("x") as log:
            for argv in setup_commands(repository, python):
                remaining = time_remaining(payload)
                if remaining <= 0:
                    raise ValueError("allocation budget exhausted during setup")
                subprocess.run(argv, stdout=log, stderr=log, check=True, timeout=remaining)
        actual = environment_identity(repository)
        actual["setup_completed_at_utc"] = utc_now()
        atomic_json(ready, actual)
    else:
        with (directory / "setup-recheck.log").open("a") as log:
            subprocess.run([str(environment / "bin/python"), "-m", "pip", "check"],
                           stdout=log, stderr=log, check=True)
        actual = environment_identity(repository)
    atomic_json(directory / "environment.json", actual)
    return {"run_id": payload["run_id"], "status": "DEPENDENCIES_INSTALLED", "training_started": False}


def setup(repository: Path, payload: dict) -> dict:
    record = {"started_at_utc": utc_now(), "exit_code": 1}
    directory = run_directory(repository, payload)
    try:
        result = _setup(repository, payload)
        record["exit_code"] = 0
        return result
    except Exception as error:
        record["exit_code"] = error.returncode if isinstance(error, subprocess.CalledProcessError) else 1
        record["error"] = str(error)
        raise
    finally:
        control = directory / "control.json"
        target = directory / "setup-exit.json"
        if control.is_file() and read_json(control) == payload and not target.exists():
            record["finished_at_utc"] = utc_now()
            atomic_json(target, record)


def owned_run(repository: Path, payload: dict) -> Path:
    validate_payload(payload, repository)
    directory = run_directory(repository, payload)
    saved = read_json(directory / "control.json")
    if saved != payload:
        raise ValueError("run control identity mismatch")
    return directory


def launch(repository: Path, payload: dict) -> dict:
    run = validate_payload(payload, repository)
    directory = owned_run(repository, payload)
    verify_source(repository, payload)
    if not (directory / "environment.json").is_file():
        raise ValueError("setup has not completed")
    if time_remaining(payload) < run["max_wall_seconds"]:
        raise ValueError("remaining allocation budget cannot cover the bounded training run")
    with registry(repository, payload) as state:
        if state["stopping"]:
            raise ValueError("session is fenced for stop")
        if state["runs"][payload["run_id"]].get("recovered"):
            raise ValueError("this run is already recovered; training requires a new explicit run ID")
        if tmux_exists(payload):
            raise ValueError("existing tmux job; inspect status instead of resubmitting")
        # An uncertain launch leaves this claim intact. No automatic retry.
        with (directory / "launch.json").open("x") as handle:
            json.dump({"submitted_at_utc": utc_now(), "run_config_sha256": payload["run_config_sha256"]}, handle)
        command = shlex.join([
            "python3", str(repository / "scripts/colab/remote.py"), "worker",
            "--control", str(directory / "control.json"),
        ])
        try:
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", tmux_name(payload), "-c", str(repository), command],
                check=True, capture_output=True, text=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            atomic_json(directory / "launch-error.json", {
                "exit_code": getattr(error, "returncode", 126),
                "stdout": getattr(error, "stdout", None),
                "stderr": getattr(error, "stderr", str(error)),
                "at_utc": utc_now(),
            })
            raise
    return {"run_id": payload["run_id"], "status": "LAUNCH_REQUESTED", "tmux": tmux_name(payload)}


def terminate_owned_group(process: subprocess.Popen) -> None:
    """Popen(start_new_session=True) makes this child's PID its owned PGID."""
    for signum in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            process.wait(timeout=1)
            return
        deadline = time.monotonic() + 10
        while True:
            process.poll()  # Reap the leader; its exit does not end the group.
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                process.wait(timeout=1)
                return
            except PermissionError:
                # An exiting group can be temporarily unsignalable; it is not confirmed absent.
                pass
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))
    raise RuntimeError("owned process group exit is unconfirmed after bounded SIGKILL cleanup")


def worker(repository: Path, payload: dict) -> int:
    run = validate_payload(payload, repository)
    directory = owned_run(repository, payload)
    argv = [str(repository / ".toolalign-local/cuda-env/bin/python"), "-u", "-m",
            "toolalign.training.cuda_sft", "train", "--run-config", str(directory / "run.json")]
    started = utc_now()
    result = {"argv": argv, "started_at_utc": started, "exit_code": 126, "timed_out": False}
    environment = dict(os.environ)
    environment.update(PYTHONPATH=str(repository / "src"), PYTHONNOUSERSITE="1",
                       HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    try:
        verify_source(repository, payload)
        budget = min(run["max_wall_seconds"], time_remaining(payload))
        if budget <= 0:
            raise ValueError("allocation budget exhausted before the worker started")
        with (directory / "console.log").open("x") as log:
            process = subprocess.Popen(argv, cwd=repository, env=environment,
                                       stdout=log, stderr=log, start_new_session=True)
            atomic_json(directory / "process.json", {"pid": process.pid, "started_at_utc": started})
            try:
                result["exit_code"] = process.wait(timeout=budget)
            except subprocess.TimeoutExpired:
                result["timed_out"] = True
                result["exit_code"] = 124
                result["timeout_cleanup_completed"] = False
                terminate_owned_group(process)
                result["timeout_cleanup_completed"] = True
    except Exception as error:
        result["error"] = str(error)
    finally:
        result["finished_at_utc"] = utc_now()
        atomic_json(directory / "exit.json", result)
    return result["exit_code"]


def status(repository: Path, payload: dict) -> dict:
    directory = owned_run(repository, payload)
    result = {"run_id": payload["run_id"], "tmux_alive": tmux_exists(payload)}
    for filename in ("setup-exit.json", "launch.json", "process.json", "exit.json", "launch-error.json"):
        if (directory / filename).is_file():
            result[filename] = read_json(directory / filename)
    return result


def output_manifest(directory: Path, payload: dict) -> dict:
    run = json.loads(payload["run_config_text"])
    max_bytes = run["max_output_bytes"] + CONTROL_ALLOWANCE
    return {"schema": "toolalign.colab-output.v1", "run_id": payload["run_id"],
            "run_config_sha256": payload["run_config_sha256"], "max_bytes": max_bytes,
            "files": file_manifest(directory, max_bytes=max_bytes)}


def export(repository: Path, payload: dict) -> dict:
    """Export a terminal run, including all checkpoint state and failures."""
    directory = owned_run(repository, payload)
    if tmux_exists(payload):
        raise ValueError("job is still active; inspect it before taking a terminal snapshot")
    submitted = (directory / "launch.json").exists()
    terminal = (directory / "exit.json").is_file() or (directory / "launch-error.json").is_file()
    if (submitted and not terminal) or (not submitted and not (directory / "setup-exit.json").is_file()):
        raise ValueError("no terminal job/setup record; do not infer completion from disconnection")
    if (directory / "exit.json").is_file():
        ended = read_json(directory / "exit.json")
        if ended.get("timed_out") and not ended.get("timeout_cleanup_completed"):
            raise ValueError("timed-out process group cleanup is unconfirmed; preserve the instance")
    # Transfer the actual full output tree. T1 validates the checkpoint semantics.
    manifest = output_manifest(directory, payload)
    files = manifest["files"]
    manifest_data = json_bytes(manifest)
    snapshot = hashlib.sha256(manifest_data).hexdigest()
    exports = repository / ".toolalign-local/colab/exports"
    exports.mkdir(parents=True, exist_ok=True)
    archive = exports / f"{payload['run_id']}-{snapshot}.tar"
    if not archive.exists():
        import io

        temporary = archive.with_suffix(".tar.partial")
        with tarfile.open(temporary, "x") as output:
            member = tarfile.TarInfo("MANIFEST.json")
            member.size = len(manifest_data)
            output.addfile(member, io.BytesIO(manifest_data))
            for relative in files:
                output.add(directory / relative, arcname=relative, recursive=False)
        if file_manifest(directory, max_bytes=manifest["max_bytes"]) != files:
            raise ValueError("output changed during snapshot; partial archive retained")
        os.replace(temporary, archive)
    receipt = {"archive_path": str(archive), "archive_bytes": archive.stat().st_size,
               "archive_sha256": digest(archive), "manifest_sha256": snapshot,
               "run_id": payload["run_id"], "endpoint": payload["endpoint"]}
    with registry(repository, payload) as state:
        state["runs"][payload["run_id"]]["export"] = receipt
    return receipt


def acknowledge_recovery(repository: Path, payload: dict, recovered: dict) -> dict:
    owned_run(repository, payload)
    with registry(repository, payload) as state:
        record = state["runs"][payload["run_id"]]
        if recovered != record.get("export"):
            raise ValueError("recovery receipt does not match this run's exported archive")
        record["recovered"] = recovered
    return {"run_id": payload["run_id"], "recovery_acknowledged": True}


def stop_ready(repository: Path, payload: dict) -> dict:
    owned_run(repository, payload)
    # The established GPU lease remains the one shared by the real Git checkout.
    sys.path.insert(0, str(repository / "src"))
    from toolalign.runtime.gpu_lock import inspect_gpu_lock

    recoveries = {}
    with registry(repository, payload) as state:
        if inspect_gpu_lock(repository)["held"]:
            raise ValueError("a shared GPU lease is still held")
        for run_id, record in state["runs"].items():
            other = read_json(repository / "runs" / run_id / "control.json")
            if tmux_exists(other) or not record.get("recovered"):
                raise ValueError(f"run {run_id} is active or has not been recovered to the Mac")
            current = output_manifest(run_directory(repository, other), other)
            if hashlib.sha256(json_bytes(current)).hexdigest() != record["recovered"]["manifest_sha256"]:
                raise ValueError(f"run {run_id} changed since recovery; recover the new snapshot")
            recoveries[run_id] = record["recovered"]
        state["stopping"] = True
    return {"session": payload["session"], "endpoint": payload["endpoint"], "stop_ready": True,
            "recoveries": recoveries}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "launch", "worker", "status", "export", "ack", "stop-ready"))
    parser.add_argument("--control", type=Path)
    args = parser.parse_args()
    request = read_json(args.control) if args.control else json.load(sys.stdin)
    payload = request if args.action == "worker" else request["control"]
    if args.action == "worker":
        return worker(REPOSITORY, payload)
    actions = {"setup": setup, "launch": launch, "status": status, "export": export,
               "stop-ready": stop_ready}
    if args.action == "ack":
        result = acknowledge_recovery(REPOSITORY, payload, request["recovered"])
    else:
        result = actions[args.action](REPOSITORY, payload)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
