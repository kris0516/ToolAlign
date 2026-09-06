"""Bind candidate, old evidence, actual command logs and both new fixture engines."""

import argparse
import csv
import json
import subprocess
from pathlib import Path

from review_full_audit import file_sha
from review_support import CANDIDATE, SOURCE_HASHES, read_json, sha, value_sha, write_json


def run(args):
    root, worker, own = args.root.resolve(), args.worker.resolve(), args.private.resolve()
    public_names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", CANDIDATE], cwd=root, text=True).splitlines()
    candidate_files = {}
    for name in public_names:
        digest = sha(subprocess.check_output(["git", "show", CANDIDATE + ":" + name], cwd=root))
        assert file_sha(root / name) == digest
        candidate_files[name] = digest
    assert len(candidate_files) == 235
    baseline = "5212b24c0ef2d5442e190ed791a9b7008d8e0724"
    original_names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", baseline], cwd=root, text=True).splitlines()
    assert len(original_names) == 214
    for name in original_names:
        assert candidate_files[name] == sha(subprocess.check_output(["git", "show", baseline + ":" + name], cwd=root))
    seal = read_json(worker / ".toolalign-local/format-v1-r2/completion.json")
    assert file_sha(worker / ".toolalign-local/format-v1-r2/completion.json") == "8107fcd5b7c5f42bb356342e9744588231cd06de7e61c404b5327270ccaae965"
    assert seal["final_candidate_commit"] == CANDIDATE
    assert len(seal["public_files"]) == 18
    for name, digest in seal["public_files"].items():
        assert candidate_files[name] == digest
    proposals = sorted(set(candidate_files) - set(original_names) - set(seal["public_files"]))
    assert len(proposals) == 3
    for name in proposals:
        assert candidate_files[name] == sha(subprocess.check_output(["git", "show", "6c3d330e4b28be0fbc93c273bb2576f7317c69a8:" + name], cwd=root))
    changed = subprocess.check_output(["git", "diff", "--name-status", CANDIDATE + "^", CANDIDATE], cwd=root, text=True).splitlines()
    assert len(changed) == 4 and all(line.startswith("A\t") for line in changed)
    private = worker / ".toolalign-local/format-v1-r2"
    assert len(seal["private_artifacts"]) == 620
    for name, identity in seal["private_artifacts"].items():
        path = private / name
        assert path.resolve().is_relative_to(private)
        assert path.stat().st_size == identity["size_bytes"] and file_sha(path) == identity["sha256"], name
    commands = {}
    for label, identity in seal["logged_commands"].items():
        metadata = worker / ".toolalign-local/logs" / (label + ".json")
        log = metadata.with_suffix(".log")
        assert file_sha(metadata) == identity["command_metadata_sha256"]
        assert file_sha(log) == identity["log_sha256"]
        value = read_json(metadata)
        assert value["exit_code"] == identity["exit_code"]
        assert value["log_sha256"] == identity["log_sha256"]
        commands[label] = {"exit_code": value["exit_code"], "command_metadata_sha256": file_sha(metadata), "log_sha256": file_sha(log)}
    assert len(commands) == 37
    proof = private / "s0-tokenizer-source-binding.json"
    assert file_sha(proof) == "83bafd8cfeedf25ef82f558ddb23eb5a1a333a2617cbaf2a461b9aadb24b7d3f"
    for model in read_json(proof)["sources"].values():
        assert {k: v["sha256"] for k, v in model["files"].items()} == SOURCE_HASHES
    submission = worker / ".toolalign-local/p02-human-review-submission"
    assert file_sha(submission / "review.csv") == "eee6b377c78eeff7ab82d65dbc0dcf6934013f546e2439a24309b8b847220efb"
    with (submission / "review.csv").open() as stream:
        human = list(csv.DictReader(stream))
    assert len(human) == 100 and all(not row["reviewer"] and not row["verdict"] for row in human)
    assert read_json(submission / "submission.json")["status"] == "PENDING_KRIS_REVIEW"
    human_manifest = read_json(worker / ".toolalign-local/policy-a/human-review/manifest.json")
    own_native = read_json(own / "fixtures-native/result.json")
    own_reference = read_json(own / "fixtures-reference/result.json")
    assert own_native["fixture_sha256"] == own_reference["fixture_sha256"]
    compared = []
    for repo in own_native["models"]:
        native = own_native["models"][repo]["rows"]
        reference = own_reference["models"][repo]["rows"]
        assert len(native) == len(reference) == 12
        assert native == reference
        for engine in ("native", "reference"):
            historical = read_json(private / ("fixtures-" + engine + "-r1/result.json"))["models"][repo]["rows"]
            assert len(historical) == 12
            for actual, original in zip(native, historical, strict=True):
                assert actual["name"] == original["name"]
                assert actual["example_sha256"] == original["example_sha256"]
                assert actual["role_bindings"] == original["role_bindings"]
                assert all(original[key] == value for key, value in actual["actual"].items())
        compared += [{"repo_id": repo, "name": row["name"], "example_sha256": row["example_sha256"],
                      "sequence_sha256": row["actual"]["sequence_sha256"]} for row in native]
    auth = read_json(own / "authorization-binding.json")
    for branch, revision in auth["existing_review_branches"].items():
        assert subprocess.check_output(["git", "rev-parse", branch], cwd=root, text=True).strip() == revision
    for name, digest in auth["files_sha256"].items():
        assert file_sha(own / "authorization" / name) == digest
        assert sha(subprocess.check_output(["git", "show", auth["authorization_commit"] + ":" + name], cwd=root)) == digest
    frozen = read_json(own / "finding-f1-frozen.json")
    for name, digest in frozen.items():
        assert file_sha(root / name) == digest
    result = {"status": "PASS", "candidate": CANDIDATE,
              "candidate_files": candidate_files, "baseline_files_unchanged": len(original_names),
              "old_proposal_files_unchanged": proposals, "new_public_files": seal["public_files"],
              "final_candidate_diff": changed, "private_artifacts_verified": len(seal["private_artifacts"]),
              "private_artifact_inventory_sha256": value_sha(seal["private_artifacts"]),
              "D1_commands": commands, "D1_failed_commands_retained": [k for k, v in commands.items() if v["exit_code"]],
              "source_proof_sha256": file_sha(proof), "human_review_rows": len(human),
              "human_manifest": human_manifest, "human_verdicts_and_reviewers_filled": 0,
              "human_submission_sha256": file_sha(submission / "submission.json"),
              "human_worksheet_sha256": file_sha(submission / "review.csv"),
              "fixture_comparisons": compared, "distinct_fixture_scenarios": 12,
              "all_four_fixture_outputs_equal": True, "existing_review_branches": auth["existing_review_branches"],
              "finding_f1_frozen_sha256": file_sha(own / "finding-f1-frozen.json")}
    write_json(args.out, result)
    print(json.dumps({"status": "PASS", "candidate_files_unchanged": 235, "protected_old_files": 217,
                      "private_artifacts_verified": 620, "D1_commands": 37, "distinct_fixtures": 12,
                      "worksheet_sources": len(human), "human_verdicts_filled": 0,
                      "result_sha256": file_sha(args.out)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("root", "worker", "private", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    run(parser.parse_args())
