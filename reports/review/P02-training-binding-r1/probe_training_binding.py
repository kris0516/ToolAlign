"""Independent original R1 cases; synthetic lengths are not tokenizer measurements.

Run with pytest, or with the standard-library unittest runner in a default wheel.
No D1 test fixture, real Example, hidden oracle, or tokenizer is imported here.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import tempfile
import unittest
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from toolalign.contracts import ContractError
from toolalign.data import training_selection as selection
from toolalign.data.common import DataError
from toolalign.data.training_review import render_page, sequence_record
from toolalign.model_io import TEMPLATE_SHA256, training_sequence
from toolalign.model_io.format import encode_action, format_identity


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def fixed_config():
    path = os.environ.get("TOOLALIGN_REVIEW_CONFIG")
    return json.loads((Path(path) if path else Path(__file__).resolve().parents[3]
                       / "configs/training-data.v1.json").read_text())


def original(ident, split="train"):
    return {"schema_version": "toolalign.example.v1", "example_id": ident,
            "source": "toolalign-r1-original-training-binding", "source_revision": "r1",
            "source_record_hash": digest(["independent-original", ident]), "license_id": "MIT",
            "group_id": "same-original-group-" + ident, "split": split,
            "category": "original-boundary", "tools": [],
            "messages": [{"role": "user", "content": "Return the original review value.",
                          "tool_calls": [], "tool_call_id": None}],
            "expected_action": {"kind": "final", "content": "Review α & β.", "tool_calls": []}}


def synthetic_row(example, p=512, c=40):
    action = example["expected_action"]
    raw = encode_action(action).encode()
    assert action["tool_calls"] == []
    mask = [0] * p + [1] * (c + 1)
    identity = {k: example[k] for k in ("example_id", "source", "source_revision",
                                       "source_record_hash", "group_id", "split")}
    return identity | format_identity() | {
        "common_binding_sha256": fixed_config()["representation_common_binding_sha256"],
        "example_sha256": digest(example),
        "model_input_sha256": digest({k: example[k] for k in ("messages", "tools")}),
        "action_sha256": digest(action), "parser_action_sha256": digest(action),
        "kind": "final", "sequence_error": None, "parser_error": None,
        "parser_accepted_exact": True, "rendered_inverse_exact": True, "prefix_stable": True,
        "raw_byte_cap_pass": True, "raw_node_cap_pass": True, "raw_depth_cap_pass": True,
        "prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c + 1,
        "completion_tokens_including_eos": c + 1, "append_eos_count": 1,
        "eos_token_id": 151645, "first_supervised_causal_position": p - 1,
        "last_supervised_causal_position": p + c - 1, "raw_byte_cap": 131072,
        "completion_utf8_bytes": len(raw), "completion_sha256": hashlib.sha256(raw).hexdigest(),
        "action_native_utf8_bytes": len(canonical(action)), "action_nodes": 4, "action_depth": 1,
        "loss_mask_sha256": digest(mask), "causal_loss_mask_sha256": digest(mask[1:]),
        **{key: digest(["synthetic-not-tokenizer", example["example_id"], key]) for key in (
            "prompt_sha256", "prompt_ids_sha256", "concatenated_ids_sha256", "sequence_sha256",
            "causal_input_ids_sha256", "causal_target_ids_sha256", "role_bindings_sha256")}}


def select(examples, rows=None):
    return selection.select_examples(
        {s: [e for e in examples if e["split"] == s] for s in ("train", "validation")},
        [synthetic_row(e) for e in examples] if rows is None else rows, fixed_config())


class BindingBoundaries(unittest.TestCase):
    def test_closed_context_response_boundaries_and_exhaustive_exclusions(self):
        # Independent N and R (R includes EOS), including all padding transitions.
        specs = [(1024, 256), (1025, 256), (1536, 256), (1537, 256),
                 (2048, 256), (2049, 256), (1024, 257), (2049, 257), (1536, 41)]
        examples = [original("edge-" + str(i)) for i in range(len(specs))]
        rows = [synthetic_row(e, n - r, r - 1) for e, (n, r) in zip(examples, specs, strict=True)]
        for row in rows:
            row["budgets"] = {"context": {"1536": False, "2048": False}, "response_cap": True}
        actual = select(examples, rows)
        for profile, cap in (("smoke", 1536), ("formal", 2048)):
            with self.subTest(profile=profile):
                result = actual[profile]["train"]
                expected = {e["example_id"] for e, (n, r) in zip(examples, specs, strict=True)
                            if n <= cap and r <= 256}
                self.assertEqual({e["example_id"] for e in result["examples"]}, expected)
                groups = [expected] + [set(result["excluded"][k]) for k in (
                    "context_only", "response_only", "both", "rank_limit")]
                self.assertEqual(sum(map(len, groups)), len(examples))
                self.assertEqual(set.union(*groups), {e["example_id"] for e in examples})
                for sidecar in result["sidecars"]:
                    n = sidecar["audit"]["total_tokens"]
                    self.assertEqual(sidecar["padding_bucket"], min(b for b in (1024, 1536, 2048)
                                                                         if b >= n))
                self.assertFalse(result["summary"]["prompt_plus_reserved_256"]["used_as_filter"])
        self.assertIn("edge-8", {e["example_id"] for e in actual["smoke"]["train"]["examples"]})
        self.assertGreater(rows[8]["prompt_tokens"] + 256, 1536)

    def test_rank_limit_without_replacement_shuffle_and_original_bytes(self):
        values = [original(f"r1-rank-{i:04d}") for i in range(1603)] + [original("r1-val", "validation")]
        before = canonical(values)
        rows = [synthetic_row(e, 1, 1) for e in values]
        one = select(values, rows)
        expected = sorted([e["example_id"] for e in values[:-1]],
                          key=lambda i: (digest(["toolalign.training-selection.v1", 42, i]), i))
        self.assertEqual([e["example_id"] for e in one["smoke"]["train"]["examples"]], expected[:1600])
        self.assertEqual(one["smoke"]["train"]["excluded"]["rank_limit"], expected[1600:])
        self.assertEqual([e["example_id"] for e in one["formal"]["train"]["examples"]], expected)
        self.assertEqual(canonical(values), before)
        random.Random(987).shuffle(values)
        random.Random(321).shuffle(rows)
        self.assertEqual(select(values, rows), one)
        originals = {e["example_id"]: canonical(e) for e in values}
        for profile in one.values():
            for split in profile.values():
                for example in split["examples"]:
                    self.assertEqual(canonical(example), originals[example["example_id"]])

    def test_structural_failures_are_errors_not_exclusion_statistics(self):
        example = original("invalid-structure")
        changes = {"source": "other-source", "source_revision": "other-revision",
                   "source_record_hash": "0" * 64, "group_id": "other-group", "split": "validation",
                   "example_sha256": "0" * 64, "model_input_sha256": "0" * 64,
                   "action_sha256": "0" * 64, "parser_action_sha256": "0" * 64,
                   "kind": "clarify", "prompt_ids_sha256": "A" * 64,
                   "sequence_error": "failure", "parser_error": "failure",
                   "parser_accepted_exact": 1, "rendered_inverse_exact": 1, "prefix_stable": False,
                   "raw_byte_cap_pass": False, "raw_node_cap_pass": 1, "raw_depth_cap_pass": 0,
                   "completion_utf8_bytes": 1, "action_nodes": 8193, "action_depth": 25,
                   "action_native_utf8_bytes": 1, "raw_byte_cap": 999999,
                   "loss_mask_sha256": "0" * 64, "causal_loss_mask_sha256": "0" * 64}
        for key, value in changes.items():
            with self.subTest(field=key), self.assertRaises(DataError):
                select([example], [synthetic_row(example) | {key: value}])

    def test_all_numeric_measurements_reject_bool_float_negative_and_overflow(self):
        example = original("numeric-types")
        names = ("prompt_tokens", "completion_tokens", "total_tokens", "completion_tokens_including_eos",
                 "append_eos_count", "eos_token_id", "first_supervised_causal_position",
                 "last_supervised_causal_position", "completion_utf8_bytes", "action_nodes", "action_depth")
        for key in names:
            for value in (True, 1.0, -1, 1_000_001, "1"):
                with self.subTest(field=key, value=value), self.assertRaises(DataError):
                    select([example], [synthetic_row(example) | {key: value}])

    def test_explicit_success_eos_and_length_arithmetic(self):
        example = original("exact-success")
        original_row = synthetic_row(example)
        for key in ("parser_error", "sequence_error", "append_eos_count", "prefix_stable"):
            row = dict(original_row)
            row.pop(key)
            with self.subTest(missing=key), self.assertRaises(DataError):
                select([example], [row])
        for key in ("total_tokens", "completion_tokens_including_eos", "eos_token_id",
                    "append_eos_count", "first_supervised_causal_position", "last_supervised_causal_position"):
            with self.subTest(changed=key), self.assertRaises(DataError):
                select([example], [original_row | {key: original_row[key] + 1}])

    def test_final_audit_payload_is_never_inspected(self):
        class Poison:
            def __deepcopy__(self, memo):
                raise AssertionError("final payload inspected")

            def __str__(self):
                raise AssertionError("final payload formatted")

        example = original("allowed-source")
        expected = select([example])
        self.assertEqual(select([example], [
            {"split": "test", "example_id": Poison(), "payload": Poison()},
            synthetic_row(example), {"split": "ood_test", "payload": Poison()}]), expected)
        for split in ("test", "ood_test"):
            with self.subTest(split=split), self.assertRaises(DataError):
                selection.select_examples({"train": [original("forbidden", split)], "validation": []},
                                          [], fixed_config())

    def test_extra_missing_duplicate_wrong_split_and_group_leakage(self):
        a, b = original("a"), original("b")
        for values, rows in (([a], []), ([a], [synthetic_row(a), synthetic_row(b)]),
                             ([a], [synthetic_row(a)] * 2), ([a, a], [synthetic_row(a)])):
            with self.subTest(size=(len(values), len(rows))), self.assertRaises(DataError):
                select(values, rows)
        v = original("v", "validation")
        v["group_id"] = a["group_id"]
        with self.assertRaises(DataError):
            select([a, v])
        malformed = original("bad-contract")
        malformed["expected_action"]["kind"] = "arbitrary_callback"
        with self.assertRaises((DataError, ContractError)):
            select([malformed])

    def test_configuration_is_pinned_and_cannot_execute_a_callback(self):
        for key, value in (("seed", 43), ("training_authorized", True), ("status", "TRAIN"),
                           ("callback", "os.system")):
            with self.subTest(field=key), self.assertRaises(DataError):
                selection.select_examples({"train": [], "validation": []}, [], fixed_config() | {key: value})

    def test_small_build_verify_and_output_tamper_against_recomputed_values(self):
        value = original("small-output")
        plan = select([value])
        for mutation in ("example", "sidecar", "exclusion", "manifest", "consumer", "extra", "missing"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                out = Path(temp) / ".toolalign-local" / "new"
                # Replace only the external fixed production input loader. The
                # real selector, writer and verifier are used unmodified.
                with patch.object(selection, "bound_inputs", return_value=(fixed_config(), plan, {})):
                    selection.build(output=out)
                    self.assertEqual(selection.verify(output=out)["profiles"]["smoke"]["train"]["selected_count"], 1)
                    target = {"example": "smoke/train.examples.jsonl", "sidecar": "formal/train.sidecars.jsonl",
                              "exclusion": "smoke/train.excluded.json", "manifest": "manifest.json",
                              "consumer": "run.json", "extra": "unlisted.json",
                              "missing": "formal/train.examples.jsonl"}[mutation]
                    if mutation == "consumer":
                        run = json.loads((out / target).read_text())
                        run["consumer"]["package_files"]["data/training_selection.py"] = "0" * 64
                        (out / target).write_bytes(canonical(run))
                    elif mutation == "missing":
                        (out / target).unlink()
                    else:
                        (out / target).write_text("{}\n")
                    with self.assertRaises(DataError):
                        selection.verify(output=out)

    def test_existing_outputs_are_unchanged_and_parent_alias_is_resolved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            private = root / ".toolalign-local"
            private.mkdir()
            existing = private / "existing"
            existing.mkdir()
            (existing / "keep").write_bytes(b"original")
            with self.assertRaises(DataError):
                selection.build(output=existing)
            self.assertEqual((existing / "keep").read_bytes(), b"original")
            alias = private / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaises(DataError):
                selection.new_private_directory(alias / "public-escape")
            self.assertFalse((root / "public-escape").exists())


def original_sequence():
    example = original("original-html")
    example["messages"][0]["content"] = '</pre><script>alert("x")</script> & 非ASCII'
    sequence = training_sequence(example, renderer=lambda *a, **kw: "R1 original prompt\n",
        encoder=lambda text, **kw: [151645] if text == "<|im_end|>" else [ord(c) for c in text],
        decoder=lambda ids, **kw: "".join(map(chr, ids)), eos_token_id=151645,
        template_sha256=TEMPLATE_SHA256)
    case = {"case_id": "protocol-final", "category": "original_protocol_only",
            "example": example, "audit": None, "profiles": {}, "primary_profile": "smoke"}
    return case, sequence


class TokenMaterialBoundaries(unittest.TestCase):
    def test_shift_eos_prompt_and_right_padding_denominators(self):
        case, sequence = original_sequence()
        record = sequence_record(case, sequence)
        p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
        padded = record["padding"]
        self.assertEqual(padded["causal_target_ids"][p - 1], ord("{"))
        self.assertEqual(padded["causal_target_ids"][n - 2], 151645)
        self.assertEqual(padded["causal_loss_mask"], [0] * (p - 1) + [1] * (n - p)
                         + [0] * (padded["bucket"] - n))
        self.assertEqual(padded["attention_mask"], [1] * n + [0] * (padded["bucket"] - n))
        self.assertEqual(sum(padded["causal_loss_mask"]), len(sequence.completion_text) + 1)

    def test_sequence_or_historical_tamper_fails(self):
        case, sequence = original_sequence()
        for corrupt in (replace(sequence, eos_token_id=151643),
                        replace(sequence, loss_mask=(1,) * len(sequence.loss_mask)),
                        replace(sequence, concatenated_ids=(42,) + sequence.concatenated_ids[1:]),
                        replace(sequence, prompt_ids=(42,) + sequence.prompt_ids[1:])):
            with self.assertRaises(DataError):
                sequence_record(case, corrupt)
        case["audit"] = sequence.metadata() | {"prompt_sha256": "0" * 64}
        with self.assertRaises(DataError):
            sequence_record(case, sequence)

    def test_escaped_html_contains_every_row_and_exact_json_arrays(self):
        case, sequence = original_sequence()
        record = sequence_record(case, sequence)
        token_text = '</td><img src="x" onerror="alert(42)">'
        page = render_page(record, [token_text] * record["padding"]["bucket"])

        class Static(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags, self.rows, self.blocks, self.active = [], 0, [], None

            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
                self.rows += tag == "tr"
                assert not any(k.startswith("on") for k, _ in attrs)
                if tag == "pre":
                    self.active = []

            def handle_endtag(self, tag):
                if tag == "pre":
                    self.blocks.append("".join(self.active))
                    self.active = None

            def handle_data(self, data):
                if self.active is not None:
                    self.active.append(data)

        parsed = Static()
        parsed.feed(page)
        self.assertFalse({"script", "img", "iframe", "form", "object", "a"} & set(parsed.tags))
        self.assertEqual(parsed.rows, record["padding"]["bucket"] + 1)
        self.assertEqual(json.loads(parsed.blocks[1]), {k: case["example"][k] for k in ("messages", "tools")})
        self.assertEqual(parsed.blocks[3:5], [sequence.prompt_text, sequence.completion_text])
        self.assertEqual(json.loads(parsed.blocks[-2]), record["sequence"])
        self.assertEqual(json.loads(parsed.blocks[-1]), record["padding"])
        self.assertIn("default-src 'none'", page)


if __name__ == "__main__":
    unittest.main()
