"""Fixed-source failures plus opt-in real CPU tokenizer integration."""

import os
from pathlib import Path

import pytest
from model_io_cases import cases

from toolalign.model_io import ModelIOError
from toolalign.model_io.offline import OfflineQwenTokenizer, model_modules_loaded

REPO = "Qwen/Qwen3-0.6B"
REV = "c1899de289a04d12100db370d81485cdf75e47ca"


@pytest.mark.parametrize("kwargs", [
    {"repo_id": REPO, "revision": "main"},
    {"repo_id": "unknown", "revision": REV},
    {"repo_id": REPO, "revision": REV, "engine": "model"},
])
def test_identity_fails_before_any_source_read(tmp_path, kwargs):
    with pytest.raises(ModelIOError):
        OfflineQwenTokenizer(tmp_path, **kwargs)


def test_missing_and_wrong_source_bytes_fail_closed(tmp_path):
    with pytest.raises(ModelIOError, match="tokenizer_source_unavailable"):
        OfflineQwenTokenizer(tmp_path, repo_id=REPO, revision=REV)
    path = tmp_path / "tokenizer.json"
    path.write_bytes(b"{}")
    with pytest.raises(ModelIOError, match="tokenizer_source_size_mismatch"):
        OfflineQwenTokenizer(tmp_path, repo_id=REPO, revision=REV)
    with path.open("wb") as stream:
        stream.truncate(11422654)
    with pytest.raises(ModelIOError, match="tokenizer_source_hash_mismatch"):
        OfflineQwenTokenizer(tmp_path, repo_id=REPO, revision=REV)


def test_model_imports_prevent_tokenizer_construction(monkeypatch, tmp_path):
    monkeypatch.setattr("toolalign.model_io.offline.model_modules_loaded", lambda: ["torch"])
    with pytest.raises(ModelIOError, match="tokenizer_only_process_required"):
        OfflineQwenTokenizer(tmp_path, repo_id=REPO, revision=REV)


@pytest.fixture(scope="module")
def real_tokenizer():
    root = os.environ.get("TOOLALIGN_TOKENIZER_DIR")
    if not root:
        pytest.skip("fixed CPU tokenizer directory not supplied")
    return OfflineQwenTokenizer(Path(root), repo_id=REPO, revision=REV)


def test_actual_tokenizer_identity_is_isolated(real_tokenizer):
    identity = real_tokenizer.identity
    identity["files"]["tokenizer.json"]["sha256"] = "changed"
    assert real_tokenizer.identity["files"]["tokenizer.json"]["sha256"] != "changed"
    with pytest.raises(AttributeError):
        real_tokenizer.eos_token_id = 0
    assert not model_modules_loaded()


@pytest.mark.parametrize("name,example", cases(), ids=[n for n, _ in cases()])
def test_real_completion_decode_and_shift(real_tokenizer, name, example):
    sequence = real_tokenizer.training_sequence(example)
    p = len(sequence.prompt_ids)
    assert real_tokenizer.decode(sequence.sequence_ids[p:-1], skip_special_tokens=False) == sequence.completion_text
    assert sequence.sequence_ids[p:].count(real_tokenizer.eos_token_id) == 1
    assert sequence.causal_loss_mask[p - 2:p + 1] == (0, 1, 1)
    assert sequence.causal_target_ids[-1] == real_tokenizer.eos_token_id


@pytest.mark.parametrize("flags", [
    {"tools": [], "add_generation_prompt": True, "enable_thinking": False},
    {"tools": None, "add_generation_prompt": False, "enable_thinking": False},
    {"tools": None, "add_generation_prompt": True, "enable_thinking": True},
])
def test_native_tool_and_thinking_flags_rejected(real_tokenizer, flags):
    with pytest.raises(ModelIOError, match="renderer_parameters_mismatch"):
        real_tokenizer.render([], **flags)


def test_real_encoding_flags_fail_closed(real_tokenizer):
    with pytest.raises(ModelIOError):
        real_tokenizer.encode("data", add_special_tokens=True)
    with pytest.raises(ModelIOError):
        real_tokenizer.decode([151645], skip_special_tokens=True)


def test_reference_environment_flags_checked_before_import(real_tokenizer, monkeypatch):
    monkeypatch.delenv("USE_TORCH", raising=False)
    with pytest.raises(ModelIOError, match="tokenizer_only_environment_required"):
        OfflineQwenTokenizer(os.environ["TOOLALIGN_TOKENIZER_DIR"], repo_id=REPO, revision=REV, engine="transformers")
