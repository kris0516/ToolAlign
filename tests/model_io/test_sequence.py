"""Loss/shift and failure boundaries with a transparent character-token test double."""

import copy

import pytest
from model_io_cases import action, message, public_example

from toolalign.contracts import ContractError, canonical_hash
from toolalign.model_io import (
    TEMPLATE_SHA256,
    ModelIOError,
    build_sequence,
    encode_action,
    pad_sequence,
    training_sequence,
)


def model_input():
    return {"messages": [message("user", "Original request.")], "tools": []}


class CharacterCallbacks:
    """Tests callback mechanics only; never described as Qwen tokenization."""

    def __init__(self):
        self.render_calls = []

    def render(self, messages, **flags):
        self.render_calls.append((copy.deepcopy(messages), flags))
        return "PROMPT"

    def encode(self, text, *, add_special_tokens):
        assert add_special_tokens is False
        return [1] if text == "<|im_end|>" else [ord(c) + 10 for c in text]

    def decode(self, ids, *, skip_special_tokens):
        assert skip_special_tokens is False
        return "".join(chr(i - 10) for i in ids)

    def kwargs(self):
        return {
            "renderer": self.render, "encoder": self.encode, "decoder": self.decode,
            "eos_token_id": 1, "template_sha256": TEMPLATE_SHA256,
        }


def test_first_and_last_target_positions_eos_and_no_newline():
    callbacks = CharacterCallbacks()
    value, target = model_input(), action("final", "\n\nA < B\n")
    before = copy.deepcopy((value, target))
    sequence = build_sequence(value, target, **callbacks.kwargs())
    assert (value, target) == before
    assert sequence.prompt_ids == tuple(ord(c) + 10 for c in "PROMPT")
    assert sequence.sequence_ids[-1] == 1
    assert sequence.sequence_ids[:-1] == sequence.concatenated_ids
    assert sequence.sequence_ids[len(sequence.prompt_ids):].count(1) == 1
    p = len(sequence.prompt_ids)
    assert sequence.loss_mask[:p] == (0,) * p
    assert sequence.causal_loss_mask[p - 2] == 0
    assert sequence.causal_loss_mask[p - 1] == 1
    assert sequence.causal_target_ids[p - 1] == ord("{") + 10
    assert sequence.causal_target_ids[-1] == 1 and sequence.causal_loss_mask[-1] == 1
    assert sum(sequence.causal_loss_mask) == len(encode_action(target)) + 1
    assert callbacks.render_calls[0][1] == {
        "tools": None, "add_generation_prompt": True, "enable_thinking": False,
    }
    record = sequence.record()
    assert record["sequence_sha256"] == canonical_hash(record["sequence_ids"])
    assert record["causal_loss_mask_sha256"] == canonical_hash(record["causal_loss_mask"])
    assert record["first_supervised_causal_position"] == p - 1


def test_padding_eos_value_does_not_create_supervised_eos_targets():
    sequence = build_sequence(model_input(), action("clarify", "Which version?"), **CharacterCallbacks().kwargs())
    n = len(sequence.sequence_ids)
    padded = pad_sequence(sequence, length=n + 3, pad_token_id=1)
    assert padded.sequence_ids == sequence.sequence_ids + (1, 1, 1)
    assert padded.attention_mask == (1,) * n + (0, 0, 0)
    assert padded.loss_mask[-4:] == (1, 0, 0, 0)
    assert sum(padded.causal_loss_mask) == sum(sequence.causal_loss_mask)
    assert padded.causal_loss_mask[-3:] == (0, 0, 0)
    assert padded.unpadded_length == n


@pytest.mark.parametrize("bad_length", [-1, 0, True, 1.5])
def test_padding_never_truncates(bad_length):
    sequence = build_sequence(model_input(), action("final", "Answer."), **CharacterCallbacks().kwargs())
    with pytest.raises(ModelIOError):
        pad_sequence(sequence, length=bad_length, pad_token_id=0)


@pytest.mark.parametrize("key,bad", [
    ("template_sha256", "wrong"), ("eos_token_id", True), ("eos_token_id", -1),
    ("eos_token", "<|im_start|>"),
])
def test_identity_mismatch_prevents_rendering(key, bad):
    callbacks = CharacterCallbacks()
    with pytest.raises(ModelIOError):
        build_sequence(model_input(), action("final", "Answer."), **(callbacks.kwargs() | {key: bad}))
    assert not callbacks.render_calls


@pytest.mark.parametrize("failure", ["boundary", "embedded_eos", "bad_ids", "empty_prompt", "eos_encoding", "decoder", "render_type"])
def test_callbacks_cannot_silently_change_the_sequence(failure):
    callbacks = CharacterCallbacks()
    kwargs = callbacks.kwargs()
    if failure == "boundary":
        kwargs["encoder"] = lambda text, **kw: ([999] + callbacks.encode(text, **kw)[1:]) if text.startswith("PROMPT{") else callbacks.encode(text, **kw)
    elif failure == "embedded_eos":
        kwargs["encoder"] = lambda text, **kw: callbacks.encode(text, **kw) + ([1] if text.startswith("PROMPT{") else [])
    elif failure == "bad_ids":
        kwargs["encoder"] = lambda text, **kw: [True]
    elif failure == "empty_prompt":
        kwargs["renderer"] = lambda *a, **kw: ""
    elif failure == "eos_encoding":
        kwargs["encoder"] = lambda text, **kw: [2] if text == "<|im_end|>" else callbacks.encode(text, **kw)
    elif failure == "decoder":
        kwargs["decoder"] = lambda *a, **kw: "silently changed output"
    else:
        kwargs["renderer"] = lambda *a, **kw: b"bytes not text"
    with pytest.raises(ModelIOError):
        build_sequence(model_input(), action("final", "Answer."), **kwargs)


@pytest.mark.parametrize("failure", ["unknown_tool", "invalid_argument", "history_id_collision"])
def test_training_requires_the_full_target_contract(failure):
    example = public_example()
    call = example["expected_action"]["tool_calls"][0]
    if failure == "unknown_tool":
        call["name"] = "undeclared"
    elif failure == "invalid_argument":
        call["arguments"] = {"build_id": 5}
    else:
        example["messages"] = [
            message("assistant", "", [copy.deepcopy(call)]),
            message("tool", "Earlier result", call_id=call["call_id"]),
        ]
    callbacks = CharacterCallbacks()
    with pytest.raises(ContractError):
        training_sequence(example, **callbacks.kwargs())
    assert not callbacks.render_calls


def test_training_entry_keeps_original_example_isolated():
    example = public_example()
    before = copy.deepcopy(example)
    result = training_sequence(example, **CharacterCallbacks().kwargs())
    assert result.completion_text == encode_action(example["expected_action"])
    assert example == before
