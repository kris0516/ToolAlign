"""One authorized full reference-tokenizer pass over unchanged 8,228 Examples.

No candidate projection, sequence, AUDIT or CHECKS helper participates in the
expected calculations. Raw outputs use only the unchanged, source-bound P03 parser.
Outputs contain hashes/metrics only and remain in the reviewer's private directory.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
from collections import Counter
from pathlib import Path

from review_support import (
    CANDIDATE, assert_cpu, canonical, cpu_only, measure, read_json, sha,
    source_check, value_sha, write_json,
)

SPLITS = {"train": 7515, "validation": 234, "test": 215, "ood_test": 264}
METRICS = ("prompt_tokens", "completion_tokens", "completion_tokens_including_eos", "total_tokens",
           "completion_utf8_bytes", "action_native_utf8_bytes", "action_nodes", "action_depth")
DATA_SHA = "87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756"


def file_sha(path):
    import hashlib
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream]


def bind_inputs(root, worker, audit_root):
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == CANDIDATE
    private = read_json(audit_root / "manifest.json")
    assert file_sha(audit_root / "manifest.json") == "07daedb35169d6fa4d6eae1c7663387380035971c15c88ae5461ff4e7f617d23"
    public = read_json(root / "data/manifests/model-io-sequences.v1.json")
    assert public["private_measurement_manifest_sha256"] == file_sha(audit_root / "manifest.json")
    for key in private:
        assert private[key] == public[key], key
    assert private["record_count"] == 8228
    common = private["common_binding"]
    assert value_sha(common) == private["common_binding_sha256"]
    for name, digest in common["source"]["files"].items():
        assert file_sha(root / name) == digest
        assert sha(subprocess.check_output(["git", "show", common["source"]["git_commit"] + ":" + name], cwd=root)) == digest
    assert file_sha(root / "src/toolalign/tools/_json.py") == common["parser_sha256"] == "15f67a014fc1f2a044b8a180f425ab2cde1d668939c55a96d937e4a23373211b"
    assert file_sha(root / "configs/protocol.v1.json") == common["protocol_sha256"]
    assert file_sha(root / "configs/model_io.action-json.v1.json") == common["descriptor_sha256"]
    assert common["original_data"]["canonical_sha256"] == DATA_SHA
    for name, identity in private["artifacts"].items():
        path = audit_root / name
        assert file_sha(path) == identity["sha256"] and path.stat().st_size == identity["size_bytes"]
    original_manifests = {}
    for label in ("policy-a", "policy-b"):
        base = worker / ".toolalign-local" / label
        original = read_json(base / "manifest.json")
        assert value_sha(original) == DATA_SHA and len(original["artifacts"]) == 18
        for name, digest in original["artifacts"].items():
            path = base / name
            assert path.resolve().is_relative_to(base.resolve()) and file_sha(path) == digest
        original_manifests[label] = {"manifest_sha256": file_sha(base / "manifest.json"), "artifacts": original["artifacts"]}
    base = worker / ".toolalign-local/policy-a"
    assert file_sha(base / "manifest.json") == common["original_data"]["manifest_file_sha256"]
    examples = load_rows(base / "examples.jsonl")
    assert len(examples) == 8228
    split_records = {}
    for split, count in SPLITS.items():
        rows = load_rows(base / (split + ".jsonl"))
        assert len(rows) == count and all(row["split"] == split for row in rows)
        for row in rows:
            assert row["example_id"] not in split_records
            split_records[row["example_id"]] = value_sha(row)
    expected_records = {e["example_id"]: value_sha(e) for e in examples}
    assert len(expected_records) == 8228 and expected_records == split_records
    assert value_sha(expected_records) == common["original_data"]["example_split_membership_sha256"]
    for name, identity in common["original_data"]["files"].items():
        assert file_sha(base / name) == identity["sha256"]
        assert (base / name).stat().st_size == identity["size_bytes"]
    measured = load_rows(audit_root / "rows.jsonl")
    assert len(measured) == len(examples)
    for index, (example, row) in enumerate(zip(examples, measured, strict=True)):
        assert row["row_index"] == index and row["example_id"] == example["example_id"]
        assert row["example_sha256"] == value_sha(example)
        assert row["model_input_sha256"] == value_sha({k: example[k] for k in ("messages", "tools")})
        assert row["action_sha256"] == value_sha(example["expected_action"])
        for key in ("source", "source_revision", "source_record_hash", "group_id", "split"):
            assert row[key] == example[key]
        assert row["common_binding_sha256"] == private["common_binding_sha256"]
    order = [{k: r[k] for k in ("example_sha256", "model_input_sha256", "action_sha256", "source_record_hash", "group_id", "split")} for r in measured]
    assert value_sha(order) == private["row_identity_order_sha256"]
    return examples, measured, private, original_manifests


def budget(row):
    c, p, total = (row.get(k) for k in ("completion_tokens_including_eos", "prompt_tokens", "total_tokens"))
    return {"response_cap": 256, "response_including_eos_pass": None if c is None else c <= 256,
            "response_excluding_eos_pass": None if c is None else c - 1 <= 256,
            "context": {str(cap): {
                "total_including_eos_pass": None if total is None else total <= cap,
                "context_and_response_pass": None if total is None or c is None else total <= cap and c <= 256,
                "prompt_plus_reserved_response_pass": None if p is None else p + 256 <= cap,
            } for cap in (1024, 1536, 2048)}}


def summary(rows):
    n = len(rows)

    def counts(values):
        assert len(values) == n
        return {"denominator": n, "pass": sum(v is True for v in values),
                "over": sum(v is False for v in values), "unmeasured": sum(v is None for v in values)}

    lengths = {}
    for field in METRICS:
        values = sorted(r[field] for r in rows if r.get(field) is not None)
        m = len(values)
        lengths[field] = {"denominator": n, "measured": m, "missing": n - m,
                          "missing_reasons": dict(Counter(r.get("sequence_error") or "metric_unavailable" for r in rows if r.get(field) is None)),
                          "max": values[-1] if m else None,
                          **{"p" + str(q): values[(m * q + 99) // 100 - 1] if m else None for q in (50, 90, 95, 99)}}
    budgets = {label: counts([r["budgets"][label + "_pass"] for r in rows])
               for label in ("response_including_eos", "response_excluding_eos")}
    for cap in (1024, 1536, 2048):
        for label in ("total_including_eos_pass", "context_and_response_pass", "prompt_plus_reserved_response_pass"):
            budgets[f"context_{cap}_{label}"] = counts([r["budgets"]["context"][str(cap)][label] for r in rows])
    return {"denominator": n, "lengths": lengths, "budgets": budgets,
            "sequence_errors": dict(Counter(r["sequence_error"] for r in rows if r.get("sequence_error"))),
            "parser_errors": dict(Counter(r["parser_error"] for r in rows if r.get("parser_error"))),
            "parser_accepted_exact": sum(r.get("parser_accepted_exact") is True for r in rows),
            "raw_limits": {k: counts([r.get(k) for r in rows]) for k in ("raw_byte_cap_pass", "raw_node_cap_pass", "raw_depth_cap_pass")}}


def independent_row(index, example, measured, common):
    action = example["expected_action"]
    p, joined, seq, mask = (measured[k] for k in ("prompt_ids", "concatenated_ids", "sequence_ids", "loss_mask"))
    pending, nodes, deepest = [(action, 0)], 0, 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        deepest = max(deepest, depth)
        if isinstance(value, dict):
            pending += [(v, depth + 1) for v in value.values()]
        elif isinstance(value, list):
            pending += [(v, depth + 1) for v in value]
    row = {"row_index": index, "example_id": example["example_id"],
           "example_sha256": value_sha(example),
           "model_input_sha256": value_sha({k: example[k] for k in ("messages", "tools")}),
           "action_sha256": value_sha(action), "kind": action["kind"],
           **{k: example[k] for k in ("source", "source_revision", "source_record_hash", "group_id", "split")},
           "common_binding_sha256": value_sha(common), "sequence_error": None,
           **{k: common[k] for k in ("format_id", "descriptor_sha256", "instruction_sha256", "contract_sha256", "template_sha256")},
           "prompt_sha256": sha(measured["prompt_text"].encode()),
           "completion_sha256": sha(measured["completion_text"].encode()),
           "prompt_ids_sha256": value_sha(p), "concatenated_ids_sha256": value_sha(joined),
           "sequence_sha256": value_sha(seq), "loss_mask_sha256": value_sha(mask),
           "causal_loss_mask_sha256": value_sha(mask[1:]),
           "causal_input_ids_sha256": value_sha(seq[:-1]), "causal_target_ids_sha256": value_sha(seq[1:]),
           "role_bindings_sha256": value_sha(measured["roles"]),
           "prompt_tokens": len(p), "completion_tokens": len(joined) - len(p),
           "completion_tokens_including_eos": len(seq) - len(p), "total_tokens": len(seq),
           "completion_utf8_bytes": len(measured["completion_text"].encode()),
           "action_native_utf8_bytes": len(canonical(action)), "action_nodes": nodes, "action_depth": deepest,
           "raw_byte_cap": 131072, "raw_byte_cap_pass": len(measured["completion_text"].encode()) <= 131072,
           "raw_node_cap_pass": nodes <= 8192, "raw_depth_cap_pass": deepest <= 24,
           "parser_accepted_exact": True, "parser_error": None, "parser_action_sha256": value_sha(action),
           "rendered_inverse_exact": True, "prefix_stable": True, "append_eos_count": 1,
           "eos_token_id": 151645, "first_supervised_causal_position": len(p) - 1,
           "last_supervised_causal_position": len(seq) - 2}
    row["budgets"] = budget(row)
    return row


def run(args):
    examples, candidate_rows, manifest, inputs = bind_inputs(args.root, args.worker, args.audit)
    write_json(args.out / "input-binding.json", {"status": "PASS", "original_manifests": inputs,
               "examples": len(examples), "all_row_identities_bound_before_tokenization": True,
               "measurement_manifest_sha256": file_sha(args.audit / "manifest.json")})
    source_check(args.source)
    from transformers import AutoTokenizer
    from toolalign.tools._json import parse_action

    tokenizer = AutoTokenizer.from_pretrained(str(args.source), local_files_only=True, trust_remote_code=False)
    assert tokenizer.chat_template == read_json(args.source / "tokenizer_config.json")["chat_template"]
    descriptor = read_json(args.root / "configs/model_io.action-json.v1.json")
    render = lambda messages: tokenizer.apply_chat_template(messages, tools=None, add_generation_prompt=True, enable_thinking=False, tokenize=False)
    encode = lambda text: tokenizer.encode(text, add_special_tokens=False)
    decode = lambda ids: tokenizer.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
    assert encode("<|im_end|>") == [151645]
    rows, mismatches, errors = [], [], []
    with (args.out / "rows.jsonl").open("xb") as stream:
        for index, (example, candidate) in enumerate(zip(examples, candidate_rows, strict=True)):
            before = value_sha(example)
            try:
                result = measure(example, descriptor, render, encode, decode, parse_action)
                row = independent_row(index, example, result, manifest["common_binding"])
                diff = sorted(k for k in set(row) | set(candidate) if row.get(k) != candidate.get(k) or (k in row) != (k in candidate))
                if diff:
                    mismatches.append({"row_index": index, "fields": diff})
            except Exception as exc:
                # Keep every failed row without exposing input or exception text.
                row = {"row_index": index, "split": example["split"], "sequence_error": "review_" + type(exc).__name__}
                row["budgets"] = budget(row)
                errors.append({"row_index": index, "error_type": type(exc).__name__})
            assert value_sha(example) == before
            stream.write(canonical(row) + b"\n")
            rows.append(row)
            if (index + 1) % 1000 == 0:
                stream.flush()
                print(json.dumps({"reference_rows": index + 1, "mismatches": len(mismatches), "errors": len(errors)}), flush=True)
    summary_all = summary(rows)
    split_summary = {s: summary([r for r in rows if r["split"] == s]) for s in SPLITS}
    summaries_equal = summary_all == manifest["summary"]["all"] and split_summary == manifest["summary"]["by_split"]
    source_check(args.source)
    assert_cpu()
    result = {"status": "PASS" if not (mismatches or errors) and summaries_equal else "FAIL",
              "candidate": CANDIDATE, "rows": len(rows), "full_reference_passes": 1,
              "all": summary_all, "by_split": split_summary, "all_summaries_equal": summaries_equal,
              "mismatches": mismatches, "errors": errors, "model_modules_loaded": [],
              "rows_sha256": file_sha(args.out / "rows.jsonl"),
              "candidate_rows_sha256": file_sha(args.audit / "rows.jsonl"),
              "independent_row_bytes_equal": file_sha(args.out / "rows.jsonl") == file_sha(args.audit / "rows.jsonl"),
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
              "training_selection_or_scoring": "NOT_RUN"}
    write_json(args.out / "result.json", result)
    print(json.dumps({k: result[k] for k in ("status", "rows", "full_reference_passes", "all_summaries_equal", "independent_row_bytes_equal", "rows_sha256")}))
    assert result["status"] == "PASS"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("root", "worker", "source", "audit", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    cpu_only()
    args.out.mkdir(exist_ok=False, parents=True)
    run(args)
