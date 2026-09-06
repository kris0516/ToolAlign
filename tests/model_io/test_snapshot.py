"""Real engine/file regressions; no loader, return value or identity is mocked.

Filesystem interleavings run in child processes because audit hooks cannot be
removed. Only freshly copied source files and each child's own snapshots change.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FILES = ("tokenizer.json", "tokenizer_config.json", "LICENSE")
REPO = "Qwen/Qwen3-0.6B"
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"


def hashes(root):
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES}


def actual_state(adapter):
    backend = adapter._tokenizer if adapter.identity["engine"] == "tokenizers" else adapter._tokenizer.backend_tokenizer
    raw = json.loads(backend.to_str())
    return {
        "backend_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "template_sha256": adapter.identity["template_sha256"],
        "samples": [adapter.encode(text, add_special_tokens=False) for text in ("!", "?", "新增 café e\u0301 <|im_end|>")],
    }


def interleave(source, out, engine, scenario):
    source, out = source.resolve(), out.resolve()
    for name in ("USE_TORCH", "USE_TF", "USE_FLAX"):
        os.environ[name] = "0"
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        os.environ[name] = "1"
    from toolalign.model_io import ModelIOError
    from toolalign.model_io.offline import OfflineQwenTokenizer, model_modules_loaded

    assert not model_modules_loaded()
    target = out / "source"
    target.mkdir()
    for name in FILES:
        shutil.copyfile(source / name, target / name)
    original = {name: (target / name).read_bytes() for name in FILES}
    before = hashes(target)

    def construct():
        return OfflineQwenTokenizer(target, repo_id=REPO, revision=REVISION, engine=engine)

    baseline = construct()
    original_state = actual_state(baseline)
    snapshots, events, opened_source_extras = [], [], []
    flags = {"inside_hook": False, "changed": False, "active": True}
    snapshot_contents, permissions = [], []

    def audit(event, args):
        if not flags["active"] or flags["inside_hook"]:
            return
        flags["inside_hook"] = True
        try:
            if event == "tempfile.mkdtemp" and Path(args[0]).name.startswith("toolalign-qwen-tokenizer-"):
                snapshots.append(Path(args[0]).resolve())
            if event != "open" or not isinstance(args[0], (str, bytes, os.PathLike)):
                return
            path = Path(os.fsdecode(args[0])).resolve()
            reading = isinstance(args[1], str) and "r" in args[1]
            if path.parent == target and path.name not in FILES and reading:
                opened_source_extras.append(path.name)
            if path == target / "LICENSE" and not flags["changed"] and scenario in ("same_size", "different_size", "config_change", "extra_template"):
                if scenario in ("same_size", "different_size"):
                    changed = original["tokenizer.json"]
                    vocab = json.loads(changed)["model"]["vocab"]
                    values = {"!": vocab["?"], "?": vocab["!"]}
                    for token, ident in values.items():
                        pattern = rb'("' + re.escape(token.encode()) + rb'"\s*:\s*)' + str(vocab[token]).encode() + rb'(?=\s*[,}])'
                        changed, count = re.subn(pattern, lambda match: match[1] + str(ident).encode(), changed)
                        assert count == 1
                    assert len(changed) == len(original["tokenizer.json"])
                    if scenario == "different_size":
                        changed += b"\n"
                    (target / "tokenizer.json").write_bytes(changed)
                elif scenario == "config_change":
                    config = json.loads(original["tokenizer_config.json"])
                    config["chat_template"] = "changed source template"
                    (target / "tokenizer_config.json").write_text(json.dumps(config))
                else:
                    (target / "chat_template.jinja").write_text("unverified override")
                flags["changed"] = True
                events.append("original_directory_changed_after_verified_buffers")
            if path.parent in snapshots and path.name == "tokenizer_config.json":
                if scenario == "write_failure" and not reading and not flags["changed"]:
                    path.mkdir()  # The real exclusive file open raises IsADirectoryError.
                    flags["changed"] = True
                    events.append("snapshot_config_path_is_directory")
                elif reading:
                    snapshot_contents.append(hashes(path.parent))
                    permissions.append({"directory": path.parent.stat().st_mode & 0o777, "files": {n: (path.parent / n).stat().st_mode & 0o777 for n in FILES}})
                    if scenario == "load_failure" and not flags["changed"]:
                        path.chmod(0o600)
                        path.write_bytes(b"{")  # Real HF JSON read fails; loader stays unpatched.
                        path.chmod(0o400)
                        flags["changed"] = True
                        events.append("real_hf_input_made_invalid_for_cleanup_check")
        finally:
            flags["inside_hook"] = False

    sys.addaudithook(audit)
    adapter, error = None, None
    try:
        adapter = construct()
    except ModelIOError as exc:
        error = str(exc)
    finally:
        flags["active"] = False
        for name, data in original.items():
            (target / name).write_bytes(data)
    assert hashes(target) == before
    assert all(not path.exists() for path in snapshots)
    if scenario in ("write_failure", "load_failure"):
        assert flags["changed"] and error == "tokenizer_reference_snapshot_load_failed"
        assert adapter is None and snapshots
    else:
        assert adapter is not None and error is None
        assert adapter.identity == baseline.identity and actual_state(adapter) == original_state
        if scenario != "normal":
            assert flags["changed"]
    if engine == "transformers" and scenario != "write_failure":
        assert snapshots and snapshot_contents
        assert snapshot_contents[0] == before
        assert permissions[0] == {"directory": 0o500, "files": {name: 0o400 for name in FILES}}
    if engine == "tokenizers":
        assert not snapshots
    assert not opened_source_extras and not model_modules_loaded()
    result = {"status": "PASS", "scenario": scenario, "engine": engine, "error": error,
        "events": events, "snapshot_count": len(snapshots), "snapshots_removed": True,
        "snapshot_verified_buffer_hashes": snapshot_contents[:1], "read_permissions": permissions[:1],
        "actual_state_equal": actual_state(adapter) == original_state if adapter else None,
        "declared_identity_equal": adapter.identity == baseline.identity if adapter else None,
        "actual_baseline_state": original_state, "source_before_after_hashes": before,
        "unverified_source_files_opened": opened_source_extras, "model_modules_loaded": []}
    print(json.dumps(result, sort_keys=True))


@pytest.fixture
def real_source():
    source = os.environ.get("TOOLALIGN_TOKENIZER_DIR")
    if not source:
        pytest.skip("fixed real CPU tokenizer source not supplied")
    return Path(source).resolve()


@pytest.fixture
def engine():
    return os.environ.get("TOOLALIGN_SNAPSHOT_ENGINE", "tokenizers")


@pytest.mark.parametrize("scenario", ["normal", "same_size", "different_size", "config_change", "extra_template"])
def test_real_verified_snapshot_survives_original_source_updates(real_source, engine, scenario, tmp_path):
    done = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(real_source), str(tmp_path), engine, scenario], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    result = json.loads(done.stdout.splitlines()[-1])
    assert result["actual_state_equal"] and result["declared_identity_equal"]
    assert result["snapshots_removed"]


@pytest.mark.parametrize("scenario", ["write_failure", "load_failure"])
def test_real_snapshot_resources_removed_on_failure(real_source, engine, scenario, tmp_path):
    if engine != "transformers":
        pytest.skip("HF snapshot cleanup applies only to reference engine")
    done = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(real_source), str(tmp_path), engine, scenario], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    result = json.loads(done.stdout.splitlines()[-1])
    assert result["snapshots_removed"] and result["error"]


@pytest.mark.parametrize("name", FILES)
@pytest.mark.parametrize("different_size", [False, True])
def test_preexisting_source_tampering_rejected(real_source, engine, name, different_size, tmp_path):
    from toolalign.model_io import ModelIOError
    from toolalign.model_io.offline import OfflineQwenTokenizer

    for filename in FILES:
        shutil.copyfile(real_source / filename, tmp_path / filename)
    path = tmp_path / name
    raw = bytearray(path.read_bytes())
    if different_size:
        raw += b"\n"
    else:
        raw[0] ^= 1
    path.write_bytes(raw)
    error = "tokenizer_source_size_mismatch" if different_size else "tokenizer_source_hash_mismatch"
    with pytest.raises(ModelIOError, match=error):
        OfflineQwenTokenizer(tmp_path, repo_id=REPO, revision=REVISION, engine=engine)


if __name__ == "__main__":
    interleave(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4])
