"""Original bounded CPU fixtures, with a character encoder distinct from Qwen."""

from toolalign.contracts import canonical_hash
from toolalign.data.common import encoded
from toolalign.data.training_selection import rank_key
from toolalign.model_io import TEMPLATE_SHA256, training_sequence


def example(ident="sft-original", split="train"):
    return {"schema_version": "toolalign.example.v1", "example_id": ident,
            "source": "toolalign-original-sft-cpu", "source_revision": "v1", "license_id": "MIT",
            "source_record_hash": canonical_hash(["sft-original", ident]), "group_id": "group-" + ident,
            "split": split, "category": "original_cpu", "tools": [],
            "messages": [{"role": "user", "content": "Check the original lamp.",
                          "tool_calls": [], "tool_call_id": None}],
            "expected_action": {"kind": "final", "content": "The lamp is blue. 蓝色", "tool_calls": []}}


def sequence(value=None):
    return training_sequence(value or example(), renderer=lambda *args, **kwargs: "Original prompt.",
        encoder=lambda text, **kwargs: [151645] if text == "<|im_end|>" else [ord(c) for c in text],
        decoder=lambda ids, **kwargs: "".join(chr(i) for i in ids),
        template_sha256=TEMPLATE_SHA256, eos_token_id=151645)


def records(config):
    examples = sorted([example("sft-a"), example("sft-b")], key=lambda e: rank_key(e["example_id"]))
    sidecars = []
    for index, value in enumerate(examples, 1):
        seq = sequence(value)
        action = value["expected_action"]
        audit = {**seq.metadata(),
            **{k: value[k] for k in ("example_id", "source", "source_revision", "source_record_hash", "group_id", "split")},
            "common_binding_sha256": config["representation_common_binding_sha256"],
            "example_sha256": canonical_hash(value),
            "model_input_sha256": canonical_hash({k: value[k] for k in ("messages", "tools")}),
            "action_sha256": canonical_hash(action), "parser_action_sha256": canonical_hash(action),
            "kind": "final", "sequence_error": None, "parser_error": None,
            "parser_accepted_exact": True, "rendered_inverse_exact": True,
            "raw_byte_cap_pass": True, "raw_node_cap_pass": True, "raw_depth_cap_pass": True,
            "raw_byte_cap": 131072, "action_native_utf8_bytes": len(encoded(action)),
            "action_nodes": 4, "action_depth": 1,
            "causal_input_ids_sha256": canonical_hash(list(seq.causal_input_ids)),
            "causal_target_ids_sha256": canonical_hash(list(seq.causal_target_ids)),
            "role_bindings_sha256": canonical_hash(["original-character-fixture"])}
        sidecars.append({"profile": "smoke", "split": "train", "selection_rank": index,
                         "ranking_sha256": rank_key(value["example_id"])[0], "padding_bucket": 1024,
                         "audit": audit})
    return examples, sidecars
