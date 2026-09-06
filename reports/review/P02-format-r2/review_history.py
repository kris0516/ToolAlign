"""Verify retained full measurements and compare new small fixtures, without encoding data."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from review_bindings import CANDIDATE, LOADER, ORIGINAL, file_sha, read, sha

DATA_SHA = "87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756"
ROWS_SHA = "36b8cbfe6773c08f7a28521a99ed8783723a8f7fa3b2a3fa87915d8d1d871aff"
METRICS = (
    "prompt_tokens", "completion_tokens", "completion_tokens_including_eos", "total_tokens",
    "completion_utf8_bytes", "action_native_utf8_bytes", "action_nodes", "action_depth",
)
SPLITS = {"train": 7515, "validation": 234, "test": 215, "ood_test": 264}


def canonical_sha(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def check_statistics(rows, expected):
    """Only arithmetic over previously measured, immutable rows; no tokenizer call."""
    count = len(rows)
    assert expected["denominator"] == count
    assert all(r["sequence_error"] is None and r["parser_error"] is None for r in rows)
    assert expected["sequence_errors"] == expected["parser_errors"] == {}
    assert all(r["parser_accepted_exact"] is True for r in rows)
    assert expected["parser_accepted_exact"] == count
    for metric in METRICS:
        values = sorted(r[metric] for r in rows)
        assert all(type(v) is int for v in values)
        actual = {
            "denominator": count, "measured": count, "missing": 0, "missing_reasons": {},
            "max": values[-1],
            **{"p" + str(p): values[(count * p + 99) // 100 - 1] for p in (50, 90, 95, 99)},
        }
        assert expected["lengths"][metric] == actual, metric
    functions = {
        "response_excluding_eos": lambda r: r["completion_tokens"] <= 256,
        "response_including_eos": lambda r: r["completion_tokens_including_eos"] <= 256,
    }
    for cap in (1024, 1536, 2048):
        functions[f"context_{cap}_total_including_eos_pass"] = lambda r, c=cap: r["total_tokens"] <= c
        functions[f"context_{cap}_context_and_response_pass"] = lambda r, c=cap: (
            r["total_tokens"] <= c and r["completion_tokens_including_eos"] <= 256
        )
        functions[f"context_{cap}_prompt_plus_reserved_response_pass"] = lambda r, c=cap: r["prompt_tokens"] + 256 <= c
    assert set(functions) == set(expected["budgets"])
    for label, predicate in functions.items():
        passed = sum(predicate(row) for row in rows)
        assert expected["budgets"][label] == {
            "denominator": count, "pass": passed, "over": count - passed, "unmeasured": 0,
        }, label
    for field in ("raw_byte_cap_pass", "raw_node_cap_pass", "raw_depth_cap_pass"):
        assert all(row[field] is True for row in rows)
        assert expected["raw_limits"][field] == {
            "denominator": count, "pass": count, "over": 0, "unmeasured": 0,
        }


def main(args):
    root, worker = args.root.resolve(), args.worker.resolve()
    current, previous = args.current.resolve(), args.previous.resolve()
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == CANDIDATE
    old_audit = worker / ".toolalign-local/format-v1-r2/sequences-v1-r1"
    original_reference = previous / "full-reference-once"
    manifest = read(old_audit / "manifest.json")
    public = read(root / "data/manifests/model-io-sequences.v1.json")
    assert file_sha(root / "data/manifests/model-io-sequences.v1.json") == "69bfa651bf8db9b2c77c11c4f8d55419a8af4196aba8ff6a69b5b3b0982e0f47"
    assert file_sha(old_audit / "manifest.json") == public["private_measurement_manifest_sha256"] == "07daedb35169d6fa4d6eae1c7663387380035971c15c88ae5461ff4e7f617d23"
    assert all(public[k] == v for k, v in manifest.items())
    for name, identity in manifest["artifacts"].items():
        path = old_audit / name
        assert path.stat().st_size == identity["size_bytes"] and file_sha(path) == identity["sha256"]
    common = manifest["common_binding"]
    assert canonical_sha(common) == manifest["common_binding_sha256"]
    mapping = {}
    for name, digest in common["source"]["files"].items():
        historical = subprocess.check_output(["git", "show", common["source"]["git_commit"] + ":" + name], cwd=root)
        assert sha(historical) == digest
        actual = file_sha(root / name)
        mapping[name] = {"original_measurement_sha256": digest, "current_sha256": actual}
    assert [name for name, pair in mapping.items() if pair["original_measurement_sha256"] != pair["current_sha256"]] == [LOADER]
    assert file_sha(root / "src/toolalign/tools/_json.py") == common["parser_sha256"]
    assert file_sha(root / "configs/protocol.v1.json") == common["protocol_sha256"]
    assert file_sha(root / "configs/model_io.action-json.v1.json") == common["descriptor_sha256"]

    input_binding = read(original_reference / "input-binding.json")
    build_proofs = {}
    for label, identity in input_binding["original_manifests"].items():
        base = worker / ".toolalign-local" / label
        original = read(base / "manifest.json")
        assert file_sha(base / "manifest.json") == identity["manifest_sha256"]
        assert canonical_sha(original) == DATA_SHA
        assert original["artifacts"] == identity["artifacts"] and len(original["artifacts"]) == 18
        for name, digest in original["artifacts"].items():
            path = base / name
            assert path.resolve().is_relative_to(base) and file_sha(path) == digest
        build_proofs[label] = identity
    assert common["original_data"]["canonical_sha256"] == DATA_SHA
    assert input_binding["examples"] == 8228 and input_binding["all_row_identities_bound_before_tokenization"]
    for name, identity in common["original_data"]["files"].items():
        path = worker / ".toolalign-local/policy-a" / name
        assert path.stat().st_size == identity["size_bytes"] and file_sha(path) == identity["sha256"]

    reference = read(original_reference / "result.json")
    summary = read(old_audit / "summary.json")
    assert reference["candidate"] == ORIGINAL and reference["full_reference_passes"] == 1
    assert reference["status"] == "PASS" and not reference["errors"] and not reference["mismatches"]
    assert file_sha(original_reference / "rows.jsonl") == file_sha(old_audit / "rows.jsonl") == ROWS_SHA
    assert manifest["record_count"] == reference["rows"] == 8228
    with (original_reference / "rows.jsonl").open() as stream:
        rows = [json.loads(line) for line in stream]
    assert len(rows) == 8228 and Counter(r["split"] for r in rows) == SPLITS
    assert all(r["common_binding_sha256"] == manifest["common_binding_sha256"] for r in rows)
    for key in ("all", "by_split"):
        assert reference[key] == summary[key] == manifest["summary"][key]
    check_statistics(rows, reference["all"])
    for split in SPLITS:
        check_statistics([row for row in rows if row["split"] == split], reference["by_split"][split])
    old_commands = read(previous / "completion.json")["validation_commands"]
    full_commands = [c for c in old_commands if c["name"] == "full-reference-once"]
    assert len(full_commands) == 1 and full_commands[0]["exit_code"] == 0
    assert file_sha(previous / "logs" / full_commands[0]["log"]) == full_commands[0]["sha256"]

    comparisons = {}
    for engine in ("native", "reference"):
        path = current / ("fixtures-" + engine) / "result.json"
        actual = read(path)
        old = read(previous / ("fixtures-" + engine) / "result.json")
        assert actual == old
        fixed_d1 = read(worker / ".toolalign-local/format-fix-r3" / ("fixtures-" + engine + "-r1") / "result.json")
        assert actual["fixture_sha256"] == fixed_d1["fixture_sha256"]
        assert actual["models"] == fixed_d1["models"]
        legacy_d1 = read(worker / ".toolalign-local/format-v1-r2" / ("fixtures-" + engine + "-r1") / "result.json")
        for repo in actual["models"]:
            new_rows = actual["models"][repo]["rows"]
            old_rows = legacy_d1["models"][repo]["rows"]
            assert len(new_rows) == len(old_rows) == 12
            for new, legacy in zip(new_rows, old_rows, strict=True):
                assert new["name"] == legacy["name"] and new["example_sha256"] == legacy["example_sha256"]
                assert new["role_bindings"] == legacy["role_bindings"]
                assert all(legacy[k] == value for k, value in new["actual"].items())
        comparisons[engine] = {
            "new_result_sha256": file_sha(path), "original_R1_bytes_equal": True,
            "D1_original_and_fixed_rows_equal": True,
            "own_packages": actual["packages"], "D1_fixed_packages": fixed_d1["packages"],
            "distinct_fixtures": 12, "shared_source_model_identities": 2,
        }
    native = read(current / "fixtures-native/result.json")
    reference_fixtures = read(current / "fixtures-reference/result.json")
    for repo in native["models"]:
        assert native["models"][repo]["rows"] == reference_fixtures["models"][repo]["rows"]
    old_public = read(root / "reports/review/P02-format/evidence.json")
    submission = worker / ".toolalign-local/p02-human-review-submission/submission.json"
    assert file_sha(submission) == old_public["preservation"]["human_submission_sha256"]
    assert not {"tokenizers", "transformers", "torch", "mlx", "tensorflow", "flax", "jax"} & set(sys.modules)
    result = {
        "status": "PASS", "candidate": CANDIDATE, "new_full_measurements": 0,
        "normal_representation_changed": False, "source_mapping": mapping,
        "new_fixture_comparisons": comparisons,
        "old_native_measurement_commit": common["source"]["git_commit"],
        "old_reference_measurement_commit": reference["candidate"],
        "old_reference_run": {k: full_commands[0][k] for k in ("started_at", "ended_at", "exit_code", "sha256")},
        "old_reference_packages": reference["packages"],
        "old_input_binding_sha256": file_sha(original_reference / "input-binding.json"),
        "old_manifest_sha256": file_sha(old_audit / "manifest.json"),
        "old_public_manifest_sha256": file_sha(root / "data/manifests/model-io-sequences.v1.json"),
        "old_reference_result_sha256": file_sha(original_reference / "result.json"),
        "old_rows_sha256": ROWS_SHA, "retained_rows": len(rows),
        "retained_splits": SPLITS, "all": reference["all"], "by_split": reference["by_split"],
        "original_builds": build_proofs, "old_human_submission_sha256": file_sha(submission),
        "new_builds_or_tokenization_or_scoring_of_original_dataset": 0,
    }
    with args.out.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({
        "status": "PASS", "retained_full_rows": len(rows), "old_build_artifacts_each": 18,
        "all_and_split_statistics_verified": True, "new_full_measurements": 0,
        "both_engine_12_fixture_rows_unchanged": True, "result_sha256": file_sha(args.out),
    }))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("root", "worker", "previous", "current", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(parser.parse_args())
