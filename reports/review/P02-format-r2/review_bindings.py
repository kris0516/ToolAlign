"""Read-only provenance checks for the fixed candidate and preserved evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

CANDIDATE = "8c439f683b9d6b04919ff1f7184d8924ccf82f9f"
ORIGINAL = "7bada2e451d43dae4b3ed532d5efa310fc8e6a57"
REVIEW = "2942e568eae91d0292ad9691af133bbd8c33dd02"
LOCAL_ONLY = "f7086413a9fedd9e2a473ac6d2869efff74ddad5"
FIX = "b4dc1cf5c7d8c551506a7015bca2400573e16857"
CHECKPOINT = "7b8ef310db214845ef5ac1fabfef1e37e9e05ab0"
MERGE = "6c82d29ddaade349d3e2a15f50d35214dbc7bf8d"
LOADER = "src/toolalign/model_io/offline.py"
TEST = "tests/model_io/test_snapshot.py"
FIX_REPORTS = {
    "coordination/handoffs/P02-format-fix-r3.md",
    "reports/data/P02_FORMAT_FIX_R3_EVIDENCE.json",
    "reports/data/P02_FORMAT_FIX_R3_VERIFICATION.md",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def tree(root, revision):
    return {
        name: sha(git(root, "show", revision + ":" + name))
        for name in git(root, "ls-tree", "-r", "--name-only", revision).decode().splitlines()
    }


def sealed_worker(worker, directory, expected_hash, expected_artifacts, expected_commands):
    private = worker / ".toolalign-local" / directory
    assert file_sha(private / "completion.json") == expected_hash
    seal = read(private / "completion.json")
    assert len(seal["private_artifacts"]) == expected_artifacts
    for name, identity in seal["private_artifacts"].items():
        path = private / name
        assert path.resolve().is_relative_to(private)
        assert path.stat().st_size == identity["size_bytes"]
        assert file_sha(path) == identity["sha256"], name
    commands = {}
    assert len(seal["logged_commands"]) == expected_commands
    for label, identity in seal["logged_commands"].items():
        metadata = worker / ".toolalign-local/logs" / (label + ".json")
        log = metadata.with_suffix(".log")
        assert file_sha(metadata) == identity["command_metadata_sha256"], label
        assert file_sha(log) == identity["log_sha256"], label
        value = read(metadata)
        assert value["exit_code"] == identity["exit_code"]
        assert value["log_sha256"] == identity["log_sha256"]
        commands[label] = identity
    return seal, {
        "completion_sha256": expected_hash,
        "private_artifacts_verified": expected_artifacts,
        "commands": commands,
        "failed_commands_retained": [k for k, v in commands.items() if v["exit_code"]],
        "artifact_inventory_sha256": sha(json.dumps(seal["private_artifacts"], sort_keys=True).encode()),
    }


def main(args):
    root, worker, previous = args.root.resolve(), args.worker.resolve(), args.previous.resolve()
    assert git(root, "rev-parse", "HEAD").decode().strip() == CANDIDATE
    parents = {
        revision: git(root, "show", "-s", "--format=%P", revision).decode().strip().split()
        for revision in (CANDIDATE, MERGE, CHECKPOINT, FIX, REVIEW)
    }
    assert parents == {
        CANDIDATE: [MERGE], MERGE: [CHECKPOINT, REVIEW],
        CHECKPOINT: [FIX], FIX: [ORIGINAL], REVIEW: [ORIGINAL],
    }
    assert subprocess.run(
        ["git", "merge-base", "--is-ancestor", LOCAL_ONLY, CANDIDATE], cwd=root,
        check=False, capture_output=True,
    ).returncode == 1
    candidate, original, review = (tree(root, rev) for rev in (CANDIDATE, ORIGINAL, REVIEW))
    assert len(original) == 235
    assert set(candidate) - set(original) == FIX_REPORTS | {TEST} | (set(review) - set(original))
    unchanged = [name for name, digest in original.items() if candidate[name] == digest]
    assert len(unchanged) == 234 and set(original) - set(unchanged) == {LOADER}
    review_files = set(review) - set(original)
    assert len(review_files) == 12
    assert all(candidate[name] == review[name] for name in review_files)
    assert set(git(root, "diff", "--name-only", FIX + "^", FIX).decode().splitlines()) == {LOADER, TEST}
    assert set(git(root, "diff", "--name-only", CANDIDATE + "^", CANDIDATE).decode().splitlines()) == FIX_REPORTS
    for name, digest in candidate.items():
        assert file_sha(root / name) == digest, name
    assert candidate[LOADER] == "f1354c349708c09e82661fbde3d7b9b96df16a5f9634b28097b66973bbe4ddf3"
    assert original[LOADER] == "6d1a4474cf6cdc747de53b365426367e825ea844d3ebf0b1f36e54629a8b1d30"

    old_seal, old_worker = sealed_worker(
        worker, "format-v1-r2",
        "8107fcd5b7c5f42bb356342e9744588231cd06de7e61c404b5327270ccaae965", 620, 37,
    )
    new_seal, fixed_worker = sealed_worker(
        worker, "format-fix-r3",
        "61891c8d9ce12f9768498759f24db2218370a6d67c36e8a1362aedead438ce30", 542, 39,
    )
    assert old_seal["final_candidate_commit"] == ORIGINAL
    assert new_seal["final_candidate_commit"] == CANDIDATE
    assert len(old_seal["public_files"]) == 18 and len(new_seal["public_files"]) == 3
    assert all(original[k] == v for k, v in old_seal["public_files"].items())
    assert all(candidate[k] == v for k, v in new_seal["public_files"].items())

    assert file_sha(previous / "completion.json") == "eef5c9c57cdc1855eacf8ec19179aaa27d78f142307b01148deb49c4a7d64512"
    assert file_sha(previous / "completion-public.json") == "b6f302563e57646f4b10fa819035a5245e38a8befd6db8962bcf8e616ee796d0"
    old_review = read(root / "reports/review/P02-format/evidence.json")
    for name, identity in old_review["private_artifact_identities"].items():
        path = previous / name
        assert path.stat().st_size == identity["size_bytes"] and file_sha(path) == identity["sha256"], name
    commands = read(previous / "completion.json")["validation_commands"]
    commands += read(previous / "completion-public.json")["publication_validation_commands"]
    assert len(commands) == 42 and len({c["name"] for c in commands}) == 42
    for item in commands:
        assert file_sha(previous / "logs" / item["log"]) == item["sha256"]

    before = {}
    for engine in ("native", "reference"):
        d1 = read(worker / ".toolalign-local/format-fix-r3" / ("before-" + engine) / "result.json")
        r1 = read(previous / ("snapshot-same-size-" + engine) / "result.json")
        installed = read(previous / ("snapshot-installed-" + engine) / "result.json")
        assert d1 == r1 == installed
        assert d1["declared_identity_equal"] and not d1["loader_methods_and_return_values_patched"]
        assert d1["baseline_exclamation_ids"] == [0]
        assert d1["observed_exclamation_ids"] == ([30] if engine == "reference" else [0])
        assert d1["status"] == ("FAIL" if engine == "reference" else "PASS")
        label = "format-fix-r3-before-" + engine
        metadata = read(worker / ".toolalign-local/logs" / (label + ".json"))
        assert metadata["git_head"] == ORIGINAL
        assert metadata["exit_code"] == (1 if engine == "reference" else 0)
        before[engine] = {
            "result_sha256": file_sha(previous / ("snapshot-same-size-" + engine) / "result.json"),
            "D1_log_sha256": metadata["log_sha256"], "actual_result": d1,
        }

    worksheet = worker / ".toolalign-local/p02-human-review-submission/review.csv"
    assert file_sha(worksheet) == old_review["preservation"]["human_worksheet_sha256"]
    with worksheet.open() as stream:
        human = list(csv.DictReader(stream))
    assert len(human) == 100 and all(not row["reviewer"] and not row["verdict"] for row in human)
    assert read(worker / ".toolalign-local/p02-human-review-submission/submission.json")["status"] == "PENDING_KRIS_REVIEW"

    result = {
        "status": "PASS", "candidate": CANDIDATE, "parents": parents,
        "tree": git(root, "rev-parse", CANDIDATE + "^{tree}").decode().strip(),
        "candidate_file_hashes": candidate, "candidate_files_verified": len(candidate),
        "unchanged_original_files": len(unchanged), "preserved_review_files": len(review_files),
        "local_only_review_is_ancestor": False,
        "old_D1": old_worker, "fixed_D1": fixed_worker,
        "original_R1_private_artifacts_verified": len(old_review["private_artifact_identities"]),
        "original_R1_logs_verified": len(commands),
        "original_R1_command_log_hashes": {c["name"]: c["sha256"] for c in commands},
        "original_before_results": before,
        "human_sources": len(human), "human_verdicts_and_reviewers_filled": 0,
        "human_worksheet_sha256": file_sha(worksheet),
    }
    with args.out.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({
        "status": "PASS", "candidate_files": len(candidate),
        "unchanged_original_files": len(unchanged), "original_review_files": len(review_files),
        "D1_old_artifacts_commands": [620, 37], "D1_fixed_artifacts_commands": [542, 39],
        "R1_old_artifacts_commands": [len(old_review["private_artifact_identities"]), len(commands)],
        "original_reference_FAIL_native_PASS_verified": True,
        "result_sha256": file_sha(args.out),
    }))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("root", "worker", "previous", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(parser.parse_args())
