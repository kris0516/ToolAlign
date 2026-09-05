import hashlib
import io
import json

import pytest

from toolalign.data.common import DataError
from toolalign.data.sources import fetch_source


def manifest_for(body=b"fixture"):
    return {
        "repo_id": "Team-ACE/ToolACE",
        "revision": "a" * 40,
        "license_id": "Apache-2.0",
        "files": {
            "data.json": {"size_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        },
    }


def mock_open(monkeypatch, *, gated=False, license_id="apache-2.0", body=b"fixture"):
    calls = []

    def open_url(url, **_kwargs):
        calls.append(url)
        if "/api/" in url:
            return io.BytesIO(
                json.dumps(
                    {
                        "sha": "a" * 40,
                        "gated": gated,
                        "private": False,
                        "cardData": {"license": license_id},
                    }
                ).encode()
            )
        return io.BytesIO(body)

    monkeypatch.setattr("toolalign.data.sources.urllib.request.urlopen", open_url)
    return calls


@pytest.mark.parametrize("gated", [True, "manual", None])
def test_gated_never_downloads_or_accepts_terms(tmp_path, monkeypatch, gated):
    calls = mock_open(monkeypatch, gated=gated)
    with pytest.raises(DataError, match="source_access_or_revision_mismatch"):
        fetch_source(manifest_for(), tmp_path / ".toolalign-local" / "source")
    assert len(calls) == 1
    assert "/api/" in calls[0]


def test_wrong_license_never_downloads(tmp_path, monkeypatch):
    calls = mock_open(monkeypatch, license_id="unknown")
    with pytest.raises(DataError, match="source_license_mismatch"):
        fetch_source(manifest_for(), tmp_path / ".toolalign-local" / "source")
    assert len(calls) == 1


def test_corrupt_download_removed_and_no_success_marker(tmp_path, monkeypatch):
    mock_open(monkeypatch, body=b"changed")
    path = tmp_path / ".toolalign-local" / "source"
    with pytest.raises(DataError, match="source_hash_mismatch"):
        fetch_source(manifest_for(), path)
    assert not list(path.iterdir())


def test_streaming_size_limit(tmp_path, monkeypatch):
    mock_open(monkeypatch, body=b"a" * 100)
    path = tmp_path / ".toolalign-local" / "source"
    with pytest.raises(DataError, match="source_size_overrun"):
        fetch_source(manifest_for(), path)
    assert not list(path.iterdir())


def test_source_file_symlink_not_followed(tmp_path, monkeypatch):
    mock_open(monkeypatch)
    path = tmp_path / ".toolalign-local" / "source"
    path.mkdir(parents=True)
    victim = tmp_path / "victim.json"
    victim.write_text("unchanged")
    (path / "api.json").symlink_to(victim)
    with pytest.raises(DataError, match="source_symlink_not_allowed"):
        fetch_source(manifest_for(), path)
    assert victim.read_text() == "unchanged"
