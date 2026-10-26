"""Frozen protocol, finite requests and portable identities (stdlib only)."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import re
import shlex
import stat
import subprocess
from pathlib import Path

CONFIG_SHA256 = "ee235d612b2552be5927b4ff790887a34b088ab842f78a15fcb8212323b60045"
CAPACITY_COHORT_SHA256 = "48d66f48010dc0d0ce6db5bc64ac5e7223aa79fe7824f7ca623e6449f4adedeb"
MAX_BUNDLE_BYTES = 1024**3


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_sha(value):
    return sha(encoded(value))


def read_bytes(path, limit=MAX_BUNDLE_BYTES):
    """Finite regular files only; rejected descriptors close on every path."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, "nonregular_or_large_file")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            data = stream.read(limit + 1)
        require(len(data) <= limit, "large_file")
        return data
    finally:
        if descriptor is not None:
            os.close(descriptor)


def document(path, *, digest=None, limit=MAX_BUNDLE_BYTES):
    data = read_bytes(path, limit)
    require(digest is None or sha(data) == digest, "file_identity_mismatch")
    return json.loads(data)


def write_bytes(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def load_protocol(repository):
    root = Path(repository)
    config = document(root / "configs/sft-cuda.v2.json", digest=CONFIG_SHA256)
    for name, digest in config["bindings"].items():
        require(sha(read_bytes(root / name)) == digest, "protocol_binding_mismatch")
    return config


def source_identity(repository, expected_commit):
    root = Path(repository).resolve()
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    require(re.fullmatch(r"[0-9a-f]{40}", expected_commit) and head == expected_commit,
            "source_commit_mismatch")
    names = subprocess.check_output(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", "HEAD", "src/toolalign"],
        text=True).splitlines()
    package = Path(__file__).resolve().parents[2]
    hashes = {}
    for name in names:
        original = subprocess.check_output(["git", "-C", str(root), "show", "HEAD:" + name])
        relative = Path(name).relative_to("src/toolalign")
        require(read_bytes(package / relative) == original, "executing_source_mismatch")
        hashes[str(relative)] = sha(original)
    require("training/cuda_sft/protocol.py" in hashes, "cuda_source_not_committed")
    return {"commit": head, "package_files": hashes}


def positive_int(value, name):
    require(type(value) is int and value > 0, "invalid_" + name)
    return value


def bounded_request(request, *, schema):
    require(type(request) is dict and request.get("schema") == schema, "request_schema")
    require(request.get("authorized_by") == "S1", "separate_S1_request_required")
    require(request.get("config_sha256") == CONFIG_SHA256, "config_identity_mismatch")
    require(request.get("run_kind") in ("capacity", "sft"), "run_kind")
    require(request.get("profile") in ("smoke", "formal"), "profile")
    if request["run_kind"] == "capacity":
        require(request["profile"] == "formal", "capacity_profile")
    for key in ("max_wall_seconds", "max_output_bytes"):
        positive_int(request.get(key), key)
    require(request["max_output_bytes"] <= MAX_BUNDLE_BYTES, "output_ceiling")
    require(type(request.get("source_commit")) is str
            and re.fullmatch(r"[0-9a-f]{40}", request["source_commit"]), "source_commit")
    for key in ("repository", "output_dir"):
        require(type(request.get(key)) is str and Path(request[key]).is_absolute(), "absolute_" + key)
    return request


def validate_run(request, config):
    bounded_request(request, schema="toolalign.cuda-sft-run.v1")
    require(all(k in request for k in config["execution"]["required_run_fields"]), "missing_run_field")
    require(type(request["run_id"]) is str
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", request["run_id"]), "run_id")
    for key in ("array_manifest_sha256", "dependency_lock_sha256"):
        require(type(request[key]) is str and re.fullmatch(r"[0-9a-f]{64}", request[key]), key)
    for key in ("model_root", "lock_root", "array_dir", "dependency_lock", "persistent_dir"):
        require(type(request.get(key)) is str and Path(request[key]).is_absolute(), "absolute_" + key)
    require(Path(request["output_dir"]).resolve() != Path(request["persistent_dir"]).resolve(),
            "persistent_copy_requires_distinct_directory")
    for key in ("max_optimizer_steps", "validation_every_steps", "checkpoint_every_steps"):
        positive_int(request.get(key), key)
    maximum = 3 if request["run_kind"] == "capacity" else config["training"]["expected_updates"][request["profile"]]
    require(request["max_optimizer_steps"] <= maximum, "step_budget_exceeds_epoch")
    if request["run_kind"] == "capacity":
        require(request["checkpoint_every_steps"] == 2 and request["validation_every_steps"] == 2,
                "capacity_cadence")
    if "resume_from" in request:
        require(type(request["resume_from"]) is str and Path(request["resume_from"]).is_absolute(),
                "resume_path")
        require(type(request.get("resume_checkpoint_sha256")) is str
                and re.fullmatch(r"[0-9a-f]{64}", request["resume_checkpoint_sha256"]), "resume_identity")
    return request


def parse_dependency_lock(raw):
    """Read this project's uv lock format, including continuations and hashes."""
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    pins = {}
    pending = ""
    for line in raw.decode().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        parts = shlex.split(pending + line)
        pending = ""
        if parts[0] in ("--index-url", "--extra-index-url"):
            require(len(parts) == 2, "dependency_index_option")
            continue
        require(all(re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", p) for p in parts[1:]),
                "unsupported_dependency_option")
        requirement = Requirement(parts[0])
        specs = list(requirement.specifier)
        require(not requirement.url and not requirement.extras and requirement.marker is None
                and len(specs) == 1 and specs[0].operator == "==" and "*" not in specs[0].version,
                "fully_pinned_dependency_lock_required")
        name = canonicalize_name(requirement.name)
        require(name not in pins, "duplicate_dependency_pin")
        pins[name] = specs[0].version
    require(not pending and pins, "incomplete_dependency_lock")
    return pins


def dependency_identity(lock_path, expected_digest):
    """Bind the complete hashed lock and require each installed pin to match."""
    raw = read_bytes(lock_path, 1024 * 1024)
    require(sha(raw) == expected_digest, "dependency_lock_mismatch")
    pins = parse_dependency_lock(raw)
    for name, expected in pins.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            raise ValueError("missing_dependency:" + name) from None
        require(actual == expected, "dependency_version_mismatch:" + name)
    require({"torch", "transformers", "peft", "numpy", "safetensors"} <= set(pins), "missing_runtime_pins")
    return {"lock_sha256": expected_digest, "versions": pins}


def finite_score(ce, step, checkpoint_sha):
    require(type(ce) in (int, float) and math.isfinite(ce) and ce >= 0, "invalid_validation_ce")
    return ce, positive_int(step, "optimizer_step"), checkpoint_sha
