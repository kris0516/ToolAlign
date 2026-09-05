"""Real CPU tokenizer tests; opt in with the pinned local tokenizer directory."""

import hashlib
import os
from pathlib import Path

import pytest
from tokenizer_cases import cases

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError, read_json
from toolalign.data.lengths import TRAINING_LENGTH_BASIS, LocalTokenizer

REFERENCE = read_json(Path(__file__).with_name("tokenizer_reference.v1.json"))
BY_ID = {r["id"]: r for r in REFERENCE["cases"]}


@pytest.fixture(scope="module")
def tokenizer():
    root = os.environ.get("TOOLALIGN_TOKENIZER_DIR")
    if not root:
        pytest.skip(
            "Real CPU tokenizer check needs TOOLALIGN_TOKENIZER_DIR and pinned private dependencies"
        )
    pytest.importorskip("tokenizers")
    lock = read_json("data/manifests/qwen-source.v1.json")
    assert canonical_hash(lock) == REFERENCE["tokenizer_lock_hash"]
    return LocalTokenizer(root, lock)


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["id"])
def test_real_sequence_against_independent_hf_reference(tokenizer, case):
    ref = BY_ID[case["id"]]
    observed = tokenizer.training_sequence(case["example"], require_stable_prefix=False)
    # The JSONL writer's key sorting cannot change the training serialization.
    stored = tokenizer.training_sequence(case["wire_roundtrip"], require_stable_prefix=False)
    assert observed == stored
    assert hashlib.sha256(observed["prompt_text"].encode()).hexdigest() == ref["prompt_text_sha256"]
    assert (
        hashlib.sha256(observed["completion_text"].encode()).hexdigest()
        == ref["completion_text_sha256"]
    )
    for field in ("prompt_ids", "concatenated_ids", "sequence_ids"):
        assert canonical_hash(observed[field]) == ref[field + "_hash"]
    assert observed["prefix_stable"] == ref["prefix_stable"]
    assert len(observed["sequence_ids"]) == ref["total_tokens"]
    assert observed["sequence_ids"][-1] == ref["eos_token_id"] == 151645
    assert observed["sequence_ids"][:-1] == observed["concatenated_ids"]
    if ref["prefix_stable"]:
        measured = tokenizer.normalized(case["example"])
        assert measured["length_basis"] == TRAINING_LENGTH_BASIS
        assert measured["total_tokens"] == ref["total_tokens"]
        assert measured["prompt_tokens"] == ref["prompt_tokens"]
        assert measured["completion_tokens"] == ref["total_tokens"] - ref["prompt_tokens"]
        assert measured["sequence_hash"] == ref["sequence_ids_hash"]
    else:
        with pytest.raises(DataError, match="prompt_completion_boundary_changed"):
            tokenizer.normalized(case["example"])


def test_tool_call_action_keeps_its_accompanying_text(tokenizer):
    example = cases()[0]["example"]
    example["expected_action"]["content"] = "Checking the original note."
    sequence = tokenizer.training_sequence(example)
    assert sequence["completion_text"].startswith("Checking the original note.\n<tool_call>")
    assert sequence["sequence_ids"][:-1] == tokenizer.encode(
        sequence["prompt_text"] + sequence["completion_text"]
    )
