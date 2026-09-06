"""Original small inputs; synthetic lengths are not Qwen measurements."""

import hashlib
import json
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import encoded
from toolalign.model_io.format import encode_action, format_identity


def example(ident="original-a", split="train", *, kind="final", content="Original answer."):
    return {"schema_version": "toolalign.example.v1", "example_id": ident,
        "source": "toolalign-original-training-binding-fixtures", "source_revision": "v1",
        "license_id": "MIT", "source_record_hash": canonical_hash([ident, "original"]),
        "group_id": "group-" + ident, "split": split, "category": "protocol_review",
        "tools": [], "messages": [{"role": "user", "content": "Inspect this original case.",
                                    "tool_calls": [], "tool_call_id": None}],
        "expected_action": {"kind": kind, "content": content, "tool_calls": []}}


def config():
    return json.loads((Path(__file__).resolve().parents[3] / "configs/training-data.v1.json").read_text())


def row(value, *, p=100, c=40):
    action = value["expected_action"]
    completion = encode_action(action)
    # These original fixtures deliberately have a flat Action: root, two string
    # values and one empty array = four value nodes; root depth zero, maximum one.
    assert action["tool_calls"] == []
    mask = [0] * p + [1] * (c + 1)
    return {**{k: value[k] for k in ("example_id", "source", "source_revision", "source_record_hash", "group_id", "split")},
        **format_identity(), "common_binding_sha256": config()["representation_common_binding_sha256"],
        "example_sha256": canonical_hash(value),
        "model_input_sha256": canonical_hash({k: value[k] for k in ("messages", "tools")}),
        "action_sha256": canonical_hash(action), "parser_action_sha256": canonical_hash(action),
        "kind": action["kind"], "sequence_error": None, "parser_error": None,
        "parser_accepted_exact": True, "rendered_inverse_exact": True, "prefix_stable": True,
        "raw_byte_cap_pass": True, "raw_node_cap_pass": True, "raw_depth_cap_pass": True,
        "prompt_tokens": p, "completion_tokens": c, "completion_tokens_including_eos": c + 1,
        "total_tokens": p + c + 1, "append_eos_count": 1, "eos_token_id": 151645,
        "first_supervised_causal_position": p - 1, "last_supervised_causal_position": p + c - 1,
        "raw_byte_cap": 131072, "completion_utf8_bytes": len(completion.encode()),
        "action_native_utf8_bytes": len(encoded(action)), "action_nodes": 4, "action_depth": 1,
        "completion_sha256": hashlib.sha256(completion.encode()).hexdigest(),
        "loss_mask_sha256": canonical_hash(mask), "causal_loss_mask_sha256": canonical_hash(mask[1:]),
        **{k: canonical_hash(["synthetic-fixture", value["example_id"], k]) for k in
           ("prompt_sha256", "prompt_ids_sha256", "concatenated_ids_sha256", "sequence_sha256",
            "causal_input_ids_sha256", "causal_target_ids_sha256", "role_bindings_sha256")}}
