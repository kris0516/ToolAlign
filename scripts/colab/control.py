"""Control an explicitly allocated ToolAlign Colab session using the existing CLI.

No action allocates a VM, uploads a dataset, or runs an arbitrary shell command.
The internal ``proxy`` action checks the named endpoint before opening SSH.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from support import (
    atomic_json,
    digest,
    name,
    read_json,
    time_remaining,
    utc_now,
    validate_payload,
    verify_manifest,
)

REPOSITORY = Path("/content/toolalign")


def session_status(cli: str, session: str) -> dict | None:
    name(session)
    if not session.startswith("toolalign-"):
        raise ValueError("only toolalign-* sessions can be controlled")
    result = subprocess.run([cli, "status", "-s", session], capture_output=True,
                            text=True, check=True, timeout=60)
    pattern = rf"^\[{re.escape(session)}\] (\S+) \| Hardware: ([^|]+) \|.* \| Status: (.+)$"
    matches = re.findall(pattern, result.stdout, flags=re.M)
    if len(matches) == 1:
        endpoint, hardware, status = matches[0]
        return {"session": session, "endpoint": endpoint,
                "hardware": hardware.strip(), "status": status.strip()}
    if f"[colab] Session '{session}' not found." in result.stdout and not matches:
        return None
    raise ValueError("unrecognized CLI status; refusing to open SSH or stop a session")


def load_spec(path: Path) -> tuple[dict, Path]:
    spec = read_json(path)
    if spec["schema"] != "toolalign.colab-control.v1":
        raise ValueError("unknown control schema")
    root = Path(spec["local_root"]).expanduser().resolve()
    if ".toolalign-local" not in root.parts:
        raise ValueError("local_root must be an explicitly private .toolalign-local directory")
    run_id = name(spec["run_id"])
    for field in ("cli", "ssh_identity", "run_config_file"):
        if not Path(spec[field]).expanduser().is_absolute():
            raise ValueError(f"{field} must be an absolute local path")
        spec[field] = str(Path(spec[field]).expanduser())
    return spec, root / run_id


def make_payload(spec: dict, endpoint: str) -> dict:
    data = Path(spec["run_config_file"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != spec["run_config_sha256"]:
        raise ValueError("local run configuration hash mismatch")
    run = json.loads(data)
    if run["schema"] != "toolalign.cuda-sft-run.v1" or run["authorized_by"] != "S1":
        raise ValueError("expected S1's frozen CUDA run configuration")
    payload = {
        "session": spec["session"], "endpoint": endpoint, "run_id": spec["run_id"],
        "source_commit": run["source_commit"],
        "dependency_lock_sha256": run["dependency_lock_sha256"],
        "run_config_text": data.decode(), "run_config_sha256": spec["run_config_sha256"],
        "allocated_at_utc": spec["allocated_at_utc"],
        "max_allocation_seconds": spec["max_allocation_seconds"],
    }
    validate_payload(payload, REPOSITORY)
    return payload


def owner(spec: dict, directory: Path, current: dict | None, *, create: bool = False) -> dict:
    path = directory / "owner.json"
    if path.exists():
        saved = read_json(path)
        if saved["session"] != spec["session"] or saved["run_config_sha256"] != spec["run_config_sha256"]:
            raise ValueError("local run ID is owned by another session/configuration")
        if current and saved["endpoint"] != current["endpoint"]:
            raise ValueError("session name now refers to a different instance; do not reconnect blindly")
        if make_payload(spec, saved["endpoint"]) != saved:
            raise ValueError("control configuration changed; use a new explicit run")
        return saved
    if not create or not current:
        raise ValueError("no checked ownership receipt; run setup for the explicitly allocated session")
    payload = make_payload(spec, current["endpoint"])
    directory.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    return payload


def ssh_argv(spec_path: Path, spec: dict, directory: Path, action: str) -> list[str]:
    proxy = shlex.join([sys.executable, str(Path(__file__).resolve()),
                        "--spec", str(spec_path.resolve()), "proxy"])
    remote = shlex.join(["python3", str(REPOSITORY / "scripts/colab/remote.py"), action])
    return [
        "ssh", "-F", "/dev/null", "-i", spec["ssh_identity"],
        "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"UserKnownHostsFile={directory / 'known_hosts'}",
        "-o", f"HostKeyAlias={spec['session']}",
        "-o", f"ProxyCommand={proxy}", "root@colab", remote,
    ]


def remote_call(spec_path: Path, spec: dict, directory: Path, payload: dict,
                action: str, *, recovered: dict | None = None) -> dict:
    current = session_status(spec["cli"], spec["session"])
    owner(spec, directory, current)
    if not current:
        raise ValueError("session is absent; no SSH or implicit allocation attempted")
    timeout = max(1, time_remaining(payload)) if action == "setup" else 120
    request = {"control": payload}
    if recovered is not None:
        request["recovered"] = recovered
    started = utc_now()
    argv = ssh_argv(spec_path, spec, directory, action)
    try:
        result = subprocess.run(argv, input=json.dumps(request), capture_output=True,
                                text=True, timeout=timeout, check=False)
        record = {"exit_code": result.returncode, "stdout": result.stdout,
                  "stderr": result.stderr, "timed_out": False}
    except subprocess.TimeoutExpired as error:
        def decoded(value):
            return value.decode(errors="replace") if isinstance(value, bytes) else value
        record = {"exit_code": None, "stdout": decoded(error.stdout),
                  "stderr": decoded(error.stderr), "timed_out": True}
    event_dir = directory / "events"
    event_dir.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", prefix=action + "-", suffix=".json",
                                     dir=event_dir, delete=False) as event:
        json.dump({"action": action, "argv": argv, "started_at_utc": started,
                   "finished_at_utc": utc_now(), **record}, event, indent=2)
    if record["timed_out"] or record["exit_code"]:
        raise RuntimeError(f"remote {action} did not complete cleanly; inspect status and {event_dir}")
    return json.loads(record["stdout"])


def extract_verified(archive: Path, target: Path, expected: dict, payload: dict) -> dict:
    if archive.stat().st_size != expected["archive_bytes"] or digest(archive) != expected["archive_sha256"]:
        raise ValueError("downloaded archive differs from the instance export")
    target.mkdir()
    with tarfile.open(archive, "r:") as source:
        members = source.getmembers()
        names = [item.name for item in members]
        if len(set(names)) != len(names) or "MANIFEST.json" not in names:
            raise ValueError("archive has duplicate members or no manifest")
        for member in members:
            relative = PurePosixPath(member.name)
            if not member.isfile() or relative.is_absolute() or ".." in relative.parts:
                raise ValueError("archive contains a non-file or escaping member")
        manifest_data = source.extractfile("MANIFEST.json").read()
        if hashlib.sha256(manifest_data).hexdigest() != expected["manifest_sha256"]:
            raise ValueError("archive manifest hash mismatch")
        manifest = json.loads(manifest_data)
        if manifest["run_id"] != payload["run_id"] or manifest["run_config_sha256"] != payload["run_config_sha256"]:
            raise ValueError("archive belongs to a different run/configuration")
        if set(names) != set(manifest["files"]) | {"MANIFEST.json"}:
            raise ValueError("archive member inventory differs from the manifest")
        if sum(item.size for item in members) > manifest["max_bytes"] + len(manifest_data):
            raise ValueError("archive exceeds its declared byte budget")
        source.extractall(target, filter="data")
    verify_manifest(target, manifest)
    return manifest


def recover(spec_path: Path, spec: dict, directory: Path, payload: dict) -> dict:
    exported = remote_call(spec_path, spec, directory, payload, "export")
    if exported["run_id"] != payload["run_id"] or exported["endpoint"] != payload["endpoint"]:
        raise ValueError("export ownership mismatch")
    remote_path = PurePosixPath(exported["archive_path"])
    if remote_path.parent != PurePosixPath("/content/toolalign/.toolalign-local/colab/exports"):
        raise ValueError("unexpected remote export location")
    recovered_root = directory / "recovered"
    recovered_root.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="download-", dir=recovered_root))
    archive = attempt / "run.tar"
    current = session_status(spec["cli"], spec["session"])
    owner(spec, directory, current)
    if not current:
        raise ValueError("instance disappeared before recovery; no automatic replacement")
    subprocess.run([spec["cli"], "download", "-s", spec["session"],
                    str(remote_path), str(archive)], check=True, timeout=300,
                   stdout=sys.stderr, stderr=sys.stderr)
    manifest = extract_verified(archive, attempt / "files", exported, payload)
    receipt = {"recovered_at_utc": utc_now(), "export": exported, "archive": str(archive),
               "directory": str(attempt / "files"), "manifest": manifest}
    atomic_json(attempt / "receipt.json", receipt)
    # A failed acknowledgement retains verified Mac bytes; inspect before retrying.
    remote_call(spec_path, spec, directory, payload, "ack", recovered=exported)
    atomic_json(directory / "recovered.json", receipt)
    return {"run_id": payload["run_id"], "status": "VERIFIED_ON_MAC",
            "directory": receipt["directory"], "files": len(manifest["files"])}


def stop(spec_path: Path, spec: dict, directory: Path, payload: dict) -> dict:
    receipt = read_json(directory / "recovered.json")
    if receipt["export"]["run_id"] != payload["run_id"] or receipt["export"]["endpoint"] != payload["endpoint"]:
        raise ValueError("recovery receipt does not own this endpoint")
    # Recheck the durable copy immediately before the destructive action.
    verify_manifest(Path(receipt["directory"]), receipt["manifest"])
    current = session_status(spec["cli"], spec["session"])
    owner(spec, directory, current)
    if current:
        ready = remote_call(spec_path, spec, directory, payload, "stop-ready")
        if ready != {"session": payload["session"], "endpoint": payload["endpoint"], "stop_ready": True}:
            raise ValueError("remote stop ownership check failed")
        owner(spec, directory, session_status(spec["cli"], spec["session"]))
        subprocess.run([spec["cli"], "stop", "-s", spec["session"]], check=True, timeout=60,
                       stdout=sys.stderr, stderr=sys.stderr)
    if session_status(spec["cli"], spec["session"]) is not None:
        raise ValueError("session remains active after stop; keep the existing receipt")
    result = {"run_id": payload["run_id"], "session": spec["session"], "endpoint": payload["endpoint"],
              "status": "STOPPED_AND_ABSENCE_VERIFIED", "at_utc": utc_now(),
              "allocation_started_at_utc": payload["allocated_at_utc"],
              "allocation_elapsed_seconds": payload["max_allocation_seconds"] - time_remaining(payload)}
    atomic_json(directory / "stopped.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("action", choices=("setup", "launch", "status", "recover", "stop", "proxy"))
    args = parser.parse_args()
    spec, directory = load_spec(args.spec)
    current = session_status(spec["cli"], spec["session"])
    if args.action == "status" and not (directory / "owner.json").exists():
        print(json.dumps({"session": current, "run_status": "NO_LOCAL_OWNERSHIP_RECEIPT"}))
        return 0
    payload = owner(spec, directory, current, create=args.action == "setup")
    if args.action == "proxy":
        if not current:
            raise ValueError("named session is absent; refusing the auto-creating SSH proxy")
        os.execv(spec["cli"], [spec["cli"], "ssh", "--proxy-mode", "-s", spec["session"],
                               "--identity", spec["ssh_identity"]])
    if args.action == "status":
        result = {"session": current, "remote": None}
        if current:
            result["remote"] = remote_call(args.spec, spec, directory, payload, "status")
    elif args.action == "recover":
        result = recover(args.spec, spec, directory, payload)
    elif args.action == "stop":
        result = stop(args.spec, spec, directory, payload)
    else:
        result = remote_call(args.spec, spec, directory, payload, args.action)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
