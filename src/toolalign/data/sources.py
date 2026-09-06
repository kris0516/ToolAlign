"""Anonymous pinned official downloads with byte/hash checks and no gated login."""

from __future__ import annotations

import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .common import DataError, file_hash, loads, private_directory, write_json

REPOSITORIES = {"Team-ACE/ToolACE": "datasets", "Qwen/Qwen3-0.6B": "models"}


def fetch_source(manifest, destination, ca_file=None):
    destination = private_directory(destination)
    repo, revision = manifest["repo_id"], manifest["revision"]
    if (
        repo not in REPOSITORIES
        or len(revision) != 40
        or any(c not in "0123456789abcdef" for c in revision)
    ):
        raise DataError("unapproved_source")
    kind = REPOSITORIES[repo]
    ctx = ssl.create_default_context(cafile=ca_file)
    api_url = f"https://huggingface.co/api/{kind}/{repo}/revision/{revision}"
    with urllib.request.urlopen(api_url, context=ctx, timeout=60) as response:
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise DataError("source_metadata_budget")
    meta = loads(body.decode())
    if (
        meta.get("sha") != revision
        or meta.get("gated") is not False
        or meta.get("private") is not False
    ):
        raise DataError("source_access_or_revision_mismatch")
    if meta.get("cardData", {}).get("license") != manifest["license_id"].lower():
        raise DataError("source_license_mismatch")
    if sum(f["size_bytes"] for f in manifest["files"].values()) > 512 * 1024 * 1024:
        raise DataError("source_byte_budget")
    prefix = "datasets/" if kind == "datasets" else ""
    allowed_files = (
        {"README.md", "data.json"}
        if kind == "datasets"
        else {"LICENSE", "tokenizer.json", "tokenizer_config.json"}
    )
    for name in {*manifest["files"], "api.json", "access.json"}:
        if (destination / name).is_symlink():
            raise DataError("source_symlink_not_allowed")
    for name, info in manifest["files"].items():
        if name not in allowed_files:
            raise DataError("source_file_not_allowed")
        output = destination / name
        if output.exists():
            if output.stat().st_size != info["size_bytes"] or file_hash(output) != info["sha256"]:
                raise DataError("existing_source_hash_mismatch")
            continue
        url = f"https://huggingface.co/{prefix}{repo}/resolve/{revision}/{name}"
        temporary = Path(str(output) + ".part")
        if temporary.exists():
            raise DataError("partial_download_exists")
        try:
            with (
                urllib.request.urlopen(url, context=ctx, timeout=60) as response,
                temporary.open("xb") as stream,
            ):
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > info["size_bytes"]:
                        raise DataError("source_size_overrun")
                    stream.write(chunk)
            if size != info["size_bytes"] or file_hash(temporary) != info["sha256"]:
                raise DataError("source_hash_mismatch")
            temporary.rename(output)
        finally:
            temporary.unlink(missing_ok=True)
    write_json(destination / "api.json", meta)
    write_json(
        destination / "access.json",
        {
            "api_url": api_url,
            "revision": revision,
            "accessed_at_utc": datetime.now(timezone.utc).isoformat(),
            "api_sha256": file_hash(destination / "api.json"),
            "gated": False,
            "authenticated": False,
            "license_id": manifest["license_id"],
        },
    )
    return {"revision": revision, "verified_files": len(manifest["files"])}
