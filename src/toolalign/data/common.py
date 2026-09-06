"""Deterministic, bounded private data I/O; no source text is executable."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash

MAX_INPUT_BYTES = 512 * 1024 * 1024


class DataError(ValueError):
    """A data operation failed closed. Messages never contain source contents."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DataError("duplicate_json_key")
        result[key] = value
    return result


def _constant(_value):
    raise DataError("nonfinite_json")


DECODER = json.JSONDecoder(object_pairs_hook=_pairs, parse_constant=_constant)


def loads(text):
    try:
        value = DECODER.decode(text)
        canonical_hash(value)
        return value
    except (ValueError, RecursionError, ContractError, UnicodeError) as exc:
        raise DataError("invalid_json") from exc


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise DataError("input_byte_budget")
    return loads(path.read_text(encoding="utf-8"))


def encoded(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_bytes(encoded(value) + b"\n")


def write_jsonl(path, values):
    with Path(path).open("wb") as stream:
        for value in values:
            stream.write(encoded(value) + b"\n")


def private_directory(path, *, empty=False):
    """Resolve all symlinks before checking the caller's private output namespace."""
    path = Path(path).resolve()
    if ".toolalign-local" not in path.parts:
        raise DataError("output_must_be_private")
    path.mkdir(parents=True, exist_ok=True)
    if empty and any(path.iterdir()):
        raise DataError("output_must_be_empty")
    return path


def verified_build_manifest(path):
    """Read a build only after verifying every declared artifact on disk."""
    path = Path(path).resolve()
    manifest = read_json(path)
    root = path.parent
    for relative, expected in manifest["artifacts"].items():
        part = Path(relative)
        if part.is_absolute() or ".." in part.parts or "\\" in relative:
            raise DataError("artifact_path_escape")
        artifact = (root / part).resolve()
        if not artifact.is_relative_to(root) or not artifact.is_file():
            raise DataError("artifact_missing_or_escape")
        if file_hash(artifact) != expected:
            raise DataError("artifact_hash_mismatch")
    return manifest
