"""Read-only R1 preservation and independent selection/material identity audit.

Machine paths and real per-example evidence are written only to a new private
output. This does not tokenize, rebuild the corpus, or modify human CSV fields.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from toolalign.contracts import validate_record
from toolalign.data.training_review import choose_review_cases


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    with Path(path).open() as stream:
        for line in stream:
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser()
    for flag in ("root", "worker", "supervisor-evidence", "output"):
        parser.add_argument("--" + flag, required=True, type=Path)
    args = parser.parse_args()
    root, worker, supervisor, out = (p.resolve() for p in (
        args.root, args.worker, args.supervisor_evidence, args.output))
    assert out.is_relative_to(root / ".toolalign-local")
    out.mkdir(exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    private = worker / ".toolalign-local/training-binding-r1"
    checked = {}

    def check(path, digest=None, size=None):
        path = Path(path)
        assert path.is_file() and not path.is_symlink()
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        assert digest is None or actual == digest, (str(path), actual, digest)
        assert size is None or path.stat().st_size == size, str(path)
        checked[str(path)] = {"sha256": actual, "size_bytes": path.stat().st_size}
        return actual

    check(supervisor / "handoff-r1/proof.json", "b3b42cbc64c61590487acbcb4d738cce2dcc493c187e7ffe0860b07aaf1e7cf8")
    check(private / "completion.json", "4b6467b2ddc97abdbc7684db28bf7e6a8f31252e132f568d8a756db3810b419c")
    proof, completion = read(supervisor / "handoff-r1/proof.json"), read(private / "completion.json")
    cache = Path(read(private / "psutil-cache.json")["cache_root"]).resolve()
    humans = {
        private / "human-review/review.csv": private / "review-reference/review.csv",
        worker / ".toolalign-local/p02-human-review-submission/review.csv":
            worker / ".toolalign-local/policy-a/human-review/review.csv"}
    mutable = {"reviewer", "verdict", "reviewed_at_utc", "notes"}
    human_results = {}
    for name, info in proof["checked_files"].items():
        path = Path(name)
        assert path.is_relative_to(worker) or path.is_relative_to(supervisor) or path.is_relative_to(cache)
        check(path, None if path in humans else info["sha256"], None if path in humans else info["size_bytes"])
    for path, frozen in humans.items():
        with path.open(newline="") as stream:
            actual = list(csv.DictReader(stream))
        with frozen.open(newline="") as stream:
            expected = list(csv.DictReader(stream))
        assert len(actual) == len(expected)
        for a, b in zip(actual, expected, strict=True):
            assert set(a) == set(b)
            assert {k: v for k, v in a.items() if k not in mutable} == {
                k: v for k, v in b.items() if k not in mutable}
        human_results[str(path)] = {"rows": len(actual), "reviewers_filled": sum(bool(r["reviewer"]) for r in actual),
                                   "verdicts_filled": sum(bool(r["verdict"]) for r in actual),
                                   "current_sha256": check(path), "mutable_fields": sorted(mutable)}
    candidate = "f4f73c9ac8e004b48a74a80ac00617a01c4da324"
    assert completion["candidate_commit"] == candidate
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == candidate
    for name, digest in completion["public_files"].items():
        check(root / name, digest)
    changes = subprocess.check_output(["git", "diff", "--name-status", completion["code_base"], candidate],
                                      cwd=root, text=True).splitlines()
    assert len(changes) == 13 and all(line.startswith("A\t") for line in changes)
    measured_names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", completion["parent_commit"]],
                                            cwd=root, text=True).splitlines()
    assert len(measured_names) == 346
    for name in measured_names:
        assert sha(subprocess.check_output(["git", "show", completion["parent_commit"] + ":" + name], cwd=root)) == completion["public_files"][name]
    config_path = root / "configs/training-data.v1.json"
    check(config_path, "579d3d9d9436f4374e7e808dc5b787213157d7ee477bfffd48dac02d35e70a4c")
    config = read(config_path)
    assert config["training_authorized"] is False and config["status"] == "CPU_PREPARATION_ONLY"
    original_manifest = read(worker / ".toolalign-local/policy-a/manifest.json")
    assert sha(canonical(original_manifest)) == config["data_manifest_sha256"]
    assert len(original_manifest["artifacts"]) == 18
    for relative, digest in original_manifest["artifacts"].items():
        check(worker / ".toolalign-local/policy-a" / relative, digest)
    check(root / "configs/protocol.v1.json", config["protocol_sha256"])
    check(root / "src/toolalign/model_io/descriptor.v1.json", config["descriptor_sha256"])
    representation = root / "data/manifests/model-io-sequences.v1.json"
    check(representation, config["representation_manifest_file_sha256"])
    common = read(representation)["common_binding"]
    assert sha(canonical(common)) == config["representation_common_binding_sha256"]
    audit_path = worker / ".toolalign-local/format-v1-r2/sequences-v1-r1/rows.jsonl"
    check(audit_path, config["representation_rows_sha256"])
    examples, by_split, groups = {}, {}, {}
    for split, count in (("train", 7515), ("validation", 234)):
        values = list(lines(worker / ".toolalign-local/policy-a" / (split + ".jsonl")))
        assert len(values) == count
        by_split[split] = values
        for value in values:
            assert validate_record(value, "example") == value and value["split"] == split
            ident, group = value["example_id"], value["group_id"]
            assert ident not in examples and groups.get(group, split) == split
            examples[ident], groups[group] = value, split
    audit = {}
    for row in lines(audit_path):
        if row.get("split") in ("test", "ood_test"):
            continue  # Do not inspect, count, or use final-split payloads.
        ident = row["example_id"]
        assert ident in examples and ident not in audit
        value = examples[ident]
        assert all(row[k] == value[k] for k in (
            "example_id", "source", "source_revision", "source_record_hash", "group_id", "split"))
        assert row["example_sha256"] == sha(canonical(value))
        assert row["model_input_sha256"] == sha(canonical({k: value[k] for k in ("messages", "tools")}))
        assert row["action_sha256"] == row["parser_action_sha256"] == sha(canonical(value["expected_action"]))
        assert row["sequence_error"] is None and row["parser_error"] is None
        assert all(row[k] is True for k in ("parser_accepted_exact", "rendered_inverse_exact", "prefix_stable",
                                            "raw_byte_cap_pass", "raw_node_cap_pass", "raw_depth_cap_pass"))
        p, c, n = (row[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
        assert all(type(v) is int for v in (p, c, n)) and p > 0 and c > 0 and p + c + 1 == n
        assert row["completion_tokens_including_eos"] == c + 1 and row["append_eos_count"] == 1
        assert row["eos_token_id"] == 151645
        assert row["loss_mask_sha256"] == sha(canonical([0] * p + [1] * (c + 1)))
        audit[ident] = row
    assert set(audit) == set(examples)
    reference = supervisor / "s0-selection-reference-r1"
    check(reference / "reference-summary.json", "0f82eac7f0b20a9a7d64168a2368952a349a944a1a741807b0c4c94148633f69")
    check(reference / "expected-selection-identities.private.json", "e7e95f70d029a19867f44342d51cc6de80b36f46cdf684c92da19c23a6737bc2")
    expectations = read(reference / "expected-selection-identities.private.json")
    prior = read(reference / "reference-summary.json")
    summaries, plan = {}, {}
    for profile, cap in (("smoke", 1536), ("formal", 2048)):
        plan[profile], summaries[profile] = {}, {}
        for split, values in by_split.items():
            def rank(e):
                return (sha(canonical(["toolalign.training-selection.v1", 42, e["example_id"]])), e["example_id"])
            ordered = sorted(values, key=rank)
            excluded = {k: [] for k in ("context_only", "response_only", "both", "rank_limit")}
            eligible = []
            for value in ordered:
                row = audit[value["example_id"]]
                context, response = row["total_tokens"] > cap, row["completion_tokens_including_eos"] > 256
                reason = "both" if context and response else "context_only" if context else "response_only" if response else None
                if reason:
                    excluded[reason].append(value["example_id"])
                else:
                    eligible.append(value)
            selected = eligible[:1600] if profile == "smoke" and split == "train" else eligible
            excluded["rank_limit"] = [e["example_id"] for e in eligible[len(selected):]]
            identities = [{"example_id": e["example_id"], "example_sha256": sha(canonical(e)),
                           "ranking_sha256": rank(e)[0], "padding_bucket": min(b for b in (1024, 1536, 2048)
                               if b >= audit[e["example_id"]]["total_tokens"])} for e in selected]
            assert identities == expectations[profile][split]["selected"]
            assert excluded["rank_limit"] == expectations[profile][split]["eligible_but_not_selected_ids"]
            summary = prior["profiles"][profile][split]
            assert len(eligible) == summary["length_partitions"]["eligible"] and len(selected) == summary["selected"]
            assert len(values) == summary["denominator"]
            for key, mapped in (("context_only", "context_only"), ("response_only", "response_only"), ("both", "context_and_response")):
                assert len(excluded[key]) == summary["length_partitions"][mapped]
            assert sha(canonical([v["example_id"] for v in selected])) == summary["selected_id_order_sha256"]
            assert dict(Counter(str(v["padding_bucket"]) for v in identities)) == summary["selected_padding_buckets"]
            assert sum(audit[e["example_id"]]["prompt_tokens"] + 256 <= cap for e in values) == summary["prompt_plus_reserved_256_pass_all_candidates"]
            assert sum(audit[e["example_id"]]["prompt_tokens"] + 256 <= cap for e in selected) == summary["prompt_plus_reserved_256_pass_selected"]
            for build in ("selection-a", "selection-b"):
                directory = private / build / profile
                actual = list(lines(directory / (split + ".examples.jsonl")))
                sidecars = list(lines(directory / (split + ".sidecars.jsonl")))
                assert canonical(actual) == canonical(selected) and len(sidecars) == len(selected)
                assert read(directory / (split + ".excluded.json")) == excluded
                for index, (sidecar, identity) in enumerate(zip(sidecars, identities, strict=True), 1):
                    assert sidecar == {"selection_rank": index, "ranking_sha256": identity["ranking_sha256"],
                                       "profile": profile, "split": split, "padding_bucket": identity["padding_bucket"],
                                       "audit": audit[identity["example_id"]]}
                if build == "selection-a":
                    plan[profile][split] = {"examples": actual, "sidecars": sidecars}
            summaries[profile][split] = summary
    left, right = private / "selection-a", private / "selection-b"
    stable = read(left / "manifest.json")
    stable_names = set(stable["artifacts"]) | {"manifest.json"}
    assert len(stable_names) == 13
    for name in stable_names:
        assert (left / name).read_bytes() == (right / name).read_bytes()
    for profile in plan:
        for split in by_split:
            assert {e["example_id"] for e in plan["smoke"][split]["examples"]} <= {
                e["example_id"] for e in plan["formal"][split]["examples"]}
    runs = [read(p / "run.json") for p in (left, right)]
    assert runs[0]["created_at_utc"] != runs[1]["created_at_utc"] and runs[0]["output_path"] != runs[1]["output_path"]
    for run in runs:
        assert run["stable_manifest_sha256"] == "eb4bbfe66966d95fb3a77126e4b3ee248faa66db587422846421e25b7a8242bd"
        for name, digest in run["consumer"]["package_files"].items():
            check(root / "src/toolalign" / name, digest)
    protocols = read(root / "tests/data/training_binding_cases/protocol_examples.json")
    cases, coverage = choose_review_cases(plan, protocols)
    assert len(cases) == len({c["example"]["example_id"] for c in cases}) == 13
    assert coverage["actual_count"] == 10 and coverage["protocol_only_count"] == 3
    for case in cases:
        assert read(private / "review-reference" / (case["case_id"] + ".json"))["case"] == case
        if case["category"] == "actual_selected_train":
            assert case["example"] == examples[case["example"]["example_id"]]
            assert case["audit"] == audit[case["example"]["example_id"]]
        else:
            assert case["example"]["example_id"] not in examples and case["audit"] is None
    for name, value in (("cases.private.json", {"cases": cases, "coverage": coverage}),
                        ("proof.json", {"status": "PASS", "candidate": candidate, "started_at_utc": started,
                                        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                                        "checked_files": checked, "human_copies": human_results,
                                        "profiles": summaries, "coverage": coverage,
                                        "candidate_files": 350, "base_unchanged": 337, "measured_unchanged": 346,
                                        "new_materializations": 0, "new_tokenizations": 0,
                                        "actual_browser_pages": 0, "training_authorized": False})):
        with (out / name).open("x") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": "PASS", "checked_paths": len(checked), "profiles": summaries,
                      "materials": coverage, "proof_sha256": sha((out / "proof.json").read_bytes())}))


if __name__ == "__main__":
    main()
