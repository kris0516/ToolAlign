"""One fixed representation audit; emits hashes/metrics, never a training subset.

Trusted callers pass an already byte-verified offline tokenizer and authorized
parser callback. Input manifest identity and all 18 artifacts are checked before
measurement. Failures remain rows; no truncation, regrouping or label rewriting.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

from P02_FORMAT_V1_CHECKS import budget_metrics, raw_metrics, recover_prompt, summarize

from toolalign.contracts import ContractError, canonical_hash
from toolalign.data.common import encoded, file_hash, loads, verified_build_manifest
from toolalign.model_io import encode_action, format_descriptor, format_identity
from toolalign.model_io.offline import model_modules_loaded

DATA_HASH = "87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756"
SPLITS = {"train": 7515, "validation": 234, "test": 215, "ood_test": 264}


def source_identity(root):
    root = Path(root)
    names = [str(p.relative_to(root)) for p in sorted((root / "src/toolalign/model_io").iterdir()) if p.is_file()]
    names += [str(p.relative_to(root)) for p in sorted((root / "reports/data").glob("P02_FORMAT_V1*.py"))]
    names += [str(p.relative_to(root)) for p in sorted((root / "tests/model_io").glob("*.py"))]
    return {
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "files": {name: file_hash(root / name) for name in names},
    }


def verify_inputs(build_root):
    build_root = Path(build_root)
    manifest = verified_build_manifest(build_root / "manifest.json")
    if canonical_hash(manifest) != DATA_HASH:
        raise ValueError("original_data_manifest_identity_mismatch")
    split_rows = {}
    for split, count in SPLITS.items():
        rows = [loads(line) for line in (build_root / (split + ".jsonl")).read_text().splitlines()]
        if len(rows) != count:
            raise ValueError("original_split_count_mismatch")
        for row in rows:
            if row["split"] != split or row["example_id"] in split_rows:
                raise ValueError("original_split_identity_mismatch")
            split_rows[row["example_id"]] = canonical_hash(row)
    rows = [loads(line) for line in (build_root / "examples.jsonl").read_text().splitlines()]
    if len(rows) != 8228 or len(split_rows) != 8228:
        raise ValueError("original_count_mismatch")
    identities = {row["example_id"]: canonical_hash(row) for row in rows}
    if len(identities) != 8228 or identities != split_rows:
        raise ValueError("original_example_split_bytes_mismatch")
    return rows, {
        "canonical_sha256": DATA_HASH,
        "manifest_file_sha256": file_hash(build_root / "manifest.json"),
        "verified_artifact_count": len(manifest["artifacts"]),
        "files": {
            name: {"sha256": file_hash(build_root / name), "size_bytes": (build_root / name).stat().st_size}
            for name in ("examples.jsonl", "train.jsonl", "validation.jsonl", "test.jsonl", "ood_test.jsonl")
        },
        "example_split_membership_sha256": canonical_hash(identities),
        "expected_split_counts": SPLITS,
    }


def audit(build_root, out, tokenizer, parse_action, binding):
    """Caller supplies a fresh, private output directory; existing files fail."""
    out = Path(out)
    if ".toolalign-local" not in out.resolve().parts:
        raise ValueError("private_output_required")
    examples, input_identity = verify_inputs(build_root)
    if any(out.iterdir()):
        raise ValueError("new_empty_output_required")
    descriptor = format_descriptor()
    common = {**binding, **format_identity(), "tokenizer": tokenizer.identity, "original_data": input_identity}
    common_hash = canonical_hash(common)
    rows = []
    with (out / "rows.jsonl").open("xb") as stream:
        for index, example in enumerate(examples):
            before = canonical_hash(example)
            model_input = {"messages": example["messages"], "tools": example["tools"]}
            action = example["expected_action"]
            row = {
                "row_index": index, "example_id": example["example_id"],
                "example_sha256": before, "model_input_sha256": canonical_hash(model_input),
                "action_sha256": canonical_hash(action), "kind": action["kind"],
                **{key: example[key] for key in ("source", "source_revision", "source_record_hash", "group_id", "split")},
                "common_binding_sha256": common_hash, "sequence_error": None,
            }
            try:
                raw = encode_action(action)
                row.update(raw_metrics(raw, action, parse_action))
                sequence = tokenizer.training_sequence(example)
                row.update(sequence.metadata())
                recovered, roles = recover_prompt(sequence.prompt_text, descriptor)
                if canonical_hash(recovered) != row["model_input_sha256"]:
                    raise ContractError("rendered_prompt_inverse_mismatch")
                row["rendered_inverse_exact"] = True
                row["role_bindings_sha256"] = canonical_hash(roles)
                row["causal_input_ids_sha256"] = canonical_hash(list(sequence.causal_input_ids))
                row["causal_target_ids_sha256"] = canonical_hash(list(sequence.causal_target_ids))
            except ContractError as exc:
                row["sequence_error"] = str(exc)
            except Exception as exc:
                # An unexpected row-level failure is visible and never removed
                # from the denominator. The exception text might contain data.
                row["sequence_error"] = "unexpected_" + type(exc).__name__
            if canonical_hash(example) != before:
                raise ValueError("input_mutated_during_audit")
            row["budgets"] = budget_metrics(row)
            stream.write(encoded(row) + b"\n")
            rows.append(row)
            if (index + 1) % 1000 == 0:
                stream.flush()
                print(json.dumps({"measured_rows": index + 1, "sequence_errors": sum(bool(r["sequence_error"]) for r in rows)}), flush=True)
    if Counter(row["split"] for row in rows) != Counter(SPLITS):
        raise ValueError("audit_split_count_mismatch")
    if model_modules_loaded():
        raise ValueError("model_dependency_imported")
    report = {
        "status": "CPU_REPRESENTATION_AUDIT_ONLY_NOT_TRAINING_ACCEPTANCE",
        "all": summarize(rows),
        "by_split": {split: summarize([r for r in rows if r["split"] == split]) for split in SPLITS},
        "split_counts": dict(Counter(r["split"] for r in rows)),
        "kind_counts": dict(Counter(r["kind"] for r in rows)),
        "fixed_original_examples": 8228, "rows_written": len(rows),
        "examples_regrouped_filtered_truncated_or_relabelled": 0,
        "rendered_inverse_exact": sum(r.get("rendered_inverse_exact") is True for r in rows),
        "model_modules_loaded": model_modules_loaded(),
        "raw_parser_mode": "exact_original_text_str_no_repair",
        "raw_parser_byte_note": "P03 str precheck counts characters; UTF-8 bytes are also audited separately against 131072. No limit is changed.",
        "quantile_method": "nearest_rank_ceil_n_p_root_depth_0_value_nodes_no_object_keys",
        "response_budget_basis": "completion_tokens_including_one_eos; excluding_eos_also_reported",
        "not_run": ["training", "model_generation", "BFCL_scoring", "human_token_mask_acceptance", "G_DATA_acceptance", "training_subset_selection"],
    }
    (out / "summary.json").write_bytes(encoded(report) + b"\n")
    manifest = {
        "manifest_version": "toolalign.model-io-sequences.v1",
        "common_binding": common, "common_binding_sha256": common_hash,
        "record_count": len(rows), "summary": report,
        "artifacts": {name: {"sha256": file_hash(out / name), "size_bytes": (out / name).stat().st_size} for name in ("rows.jsonl", "summary.json")},
        "row_identity_order_sha256": canonical_hash([{key: row[key] for key in ("example_sha256", "model_input_sha256", "action_sha256", "source_record_hash", "group_id", "split")} for row in rows]),
    }
    (out / "manifest.json").write_bytes(encoded(manifest) + b"\n")
    return manifest
