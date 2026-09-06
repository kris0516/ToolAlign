"""Read original P04 receipts and immutable files without executing worker helpers.

All supplied paths and raw proof maps stay in the new private output. Git epoch
checks are distinct from current files and from independently executed tests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

CANDIDATE = "33d6248e2c518ea777618224382bd30a3cc3433d"
BASE = "42eaa50a9519efe96d60b49f07cfbd106b36778c"
INDEX_SHA = "ba93450f6dcd5a8aaff1f21d68499e1b3cdca45aa83fe78fc6229edfd3514a2a"
COMPLETION_SHA = "7cc60a30519b6f6011b33616b40a8b24a3712d813e48051ec6b04d33c823e151"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-private", type=Path, required=True)
    parser.add_argument("--s0-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, private = Path.cwd(), args.t1_private.resolve()
    worker_root = private.parents[1]
    checked, epochs = {}, {}

    def check(path, digest=None, size=None):
        path = Path(path)
        assert path.is_file() and not path.is_symlink(), str(path)
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        actual_size = path.stat().st_size
        assert digest is None or digest == actual, str(path)
        assert size is None or size == actual_size, str(path)
        checked[str(path)] = {"sha256": actual, "size_bytes": actual_size}
        return actual

    def git_files(commit):
        if commit not in epochs:
            archive = subprocess.check_output(["git", "archive", "--format=tar", commit])
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                epochs[commit] = {item.name: sha(tar.extractfile(item).read())
                                  for item in tar.getmembers() if item.isfile()}
        return epochs[commit]

    check(private / "completion.json", COMPLETION_SHA)
    completion = read(private / "completion.json")
    assert completion["candidate"] == CANDIDATE
    assert len(completion["files"]) == completion["file_count_before_this_seal"] == 248
    assert set(completion["files"]) | {"completion.json"} == {
        str(path.relative_to(private)) for path in private.rglob("*") if path.is_file()}
    for name, expected in completion["files"].items():
        check(private / name, expected["sha256"], expected["size_bytes"])
    assert sum(value["size_bytes"] for value in completion["files"].values()) == 6684876

    candidate_files, base_files = git_files(CANDIDATE), git_files(BASE)
    assert len(candidate_files) == 384 and len(base_files) == 364
    assert all(candidate_files[name] == value for name, value in base_files.items())
    for name, expected in candidate_files.items():
        check(root / name, expected)
        check(worker_root / name, expected)
    index_path = root / "reports/experiments/P04_SFT_CPU_VALIDATION.json"
    check(index_path, INDEX_SHA)
    index = read(index_path)
    indexed = {item["label"]: item for item in index["commands"]}
    assert len(indexed) == 14
    commands = []
    for receipt_path in sorted((private / "commands").glob("*/receipt.json")):
        record, started = read(receipt_path), read(receipt_path.parent / "started.json")
        assert all(record[key] == value for key, value in started.items())
        assert record["source_files_before"] == record["source_files_after"]
        assert record["source_unchanged_during_command"]
        assert record["source_files_before"] == git_files(record["source_head"])
        tree = subprocess.check_output(["git", "rev-parse", record["source_head"] + "^{tree}"], text=True).strip()
        assert tree == record["source_tree"]
        assert datetime.fromisoformat(record["ended_at_utc"]) >= datetime.fromisoformat(record["started_at_utc"])
        for stream in ("stdout", "stderr"):
            check(receipt_path.parent / (stream + ".log"), record[stream + "_sha256"])
        label = receipt_path.parent.name
        if label in indexed:
            item = indexed[label]
            assert check(receipt_path) == item["original_receipt_sha256"]
            for key in ("source_head", "source_tree", "started_at_utc", "ended_at_utc",
                        "exit_code", "wall_seconds", "stdout_sha256", "stderr_sha256"):
                assert record[key] == item[key], (label, key)
        commands.append({"label": label, **{key: value for key, value in record.items()
                                             if key not in ("source_files_before", "source_files_after")},
                         "receipt_sha256": check(receipt_path)})
    assert len(commands) == 18
    assert {item["label"] for item in commands if item["exit_code"]} == {"toy-segmented", "toy-segmented-r2"}
    for label, expected in (("cpu-combined", "895 passed, 2 skipped"), ("original-format-review", "60 passed"),
                            ("independent-deadline-review", "2 passed"),
                            ("independent-training-binding-review", "13 passed"), ("new-cpu", "51 passed")):
        assert expected in (private / "commands" / label / "stdout.log").read_text()
    for label in ("evidence-generation", "push"):
        record = read(private / (label + ".json"))
        assert record["exit_code"] == 0
        for stream in ("stdout", "stderr"):
            check(private / (label + "." + stream), record[stream + "_sha256"])
    generator = read(private / "evidence-generation.json")
    assert generator["generator_sha256"] == git_files(generator["source_head"])["reports/experiments/P04_SFT_CPU_EVIDENCE.py"]
    remote = read(private / "remote-readback.json")
    assert remote["exit_code"] == 0 and remote["stdout"] == CANDIDATE + "\trefs/heads/work/p04-sft-cpu"

    measured = git_files("eefc142ce159c1564076dff7d3f17156412de699")
    measured_core = {name: value for name, value in measured.items()
                     if name.startswith(("src/", "tests/", "configs/"))}
    assert len(measured_core) == 108
    assert all(candidate_files[name] == value for name, value in measured_core.items())
    before = read(private / "preservation-before.json")
    assert git_files(before["head"]) == before["tracked"] and len(before["tracked"]) == 183
    assert len(before["p01_fix_r4_files"]) == 1310
    for name, expected in before["p01_fix_r4_files"].items():
        check(worker_root / name, expected)
    frozen = read(private / "collator/frozen-before.json")
    assert len(frozen) == 86
    for name, expected in frozen.items():
        check(name, expected)

    trials = []
    for label, expected_type in (("toy-segmented", "AssertionError"), ("toy-segmented-r2", "KeyError")):
        trial = private / label
        supervision, terminal, acquired = (read(trial / name) for name in
                                            ("supervision.json", "child-terminal.json", "lease-acquired.json"))
        failure = read(trial / "failure.json")
        assert failure["type"] == expected_type
        assert supervision["actual_child_exit"] == terminal["exit_code"] == 1
        assert acquired["frameworks_loaded_before_lease"] == []
        assert acquired["actual_lock"]["held"] and acquired["actual_lock"]["owner"]["pid"] == acquired["pid"]
        assert terminal["lease_held_until_process_exit"] and supervision["own_process_reaped"]
        assert not supervision["own_pid_exists"] and not supervision["lock_after"]["held"]
        assert supervision["wall_seconds"] <= 300 and supervision["peak_rss_bytes"] <= 4 * 1024**3
        for stream in ("stdout", "stderr"):
            check(trial / (stream + ".log"), supervision[stream + "_sha256"])
        if label.endswith("r2"):
            assert failure["message"] == "'max_recommended_working_set_size'"
            assert "trainer.py\", line 229" in (trial / "stderr.log").read_text()
            device = read(trial / "device-before-numerics.json")
            assert device["default"] == device["operation_stream"] == "Device(cpu, 0)"
            assert device["torch"] == "cpu"
        try:
            os.kill(supervision["pid"], 0)
            pid_exists = True
        except ProcessLookupError:
            pid_exists = False
        trials.append({"label": label, "failure": failure, "original_supervision": supervision,
                       "pid_exists_at_review": pid_exists})
    assert not any(item["pid_exists_at_review"] for item in trials)
    numerics = read(private / "toy-segmented-r2/TOY_CPU-numerics.json")
    check(private / "toy-segmented-r2/TOY_CPU-numerics.json", index["numerics"]["numerics_file_sha256"])
    assert len(numerics["cases"]) == 13
    for name, expected in index["numerics"]["max_errors"].items():
        assert max(item[name] for item in numerics["cases"]) == expected <= 2e-6
    assert numerics["ignored_prediction_logits_error"] == index["numerics"]["ignored_prediction_logits_error"] == 0
    assert numerics["upstream_default_padding_negative"] == index["numerics"]["default_padding_negative"]

    s0_proofs = {
        "p04-sft-cpu-handoff-r1/handoff-proof.json": "f59023785bc7888806ea053015c30d43ecee27cc7046a211867d9daeb2e878b3",
        "p04-sft-cpu-handoff-r1/archive-proof.json": "c2abc373dc6b55e5fbd2bd2215361a5da8d241d52bb182929e5a3785f4a8f946",
        "p04-sft-cpu/s0-intermediate-proof.json": "42d0eb64846943c440f6f468aceea55f56af264701bcb226c037d39dd852960d",
    }
    for name, expected in s0_proofs.items():
        check(args.s0_evidence / name, expected)
    human = []
    for name, previous in read(private / "preservation-after.json")["human"].items():
        with Path(name).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        human.append({"path": name, "rows": len(rows), "sha256": check(name),
                      "reviewer_filled": sum(bool(row["reviewer"]) for row in rows),
                      "verdict_filled": sum(bool(row["verdict"]) for row in rows),
                      "prior_sha256": previous["sha256"],
                      "human_fields_are_allowed_to_change": True})
    result = {"status": "PASS", "candidate": CANDIDATE, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "current_files": checked, "distinct_current_paths": len(checked),
              "original_commands": commands, "git_epochs": epochs, "measured_core_count": 108,
              "t1_sealed_files": 248, "candidate_file_count": 384, "unchanged_base_count": 364,
              "old_p01_files": 1310, "old_selection_review_files": 86, "original_trials": trials,
              "human": human, "new_original_numeric_replays": 0, "new_tokenizations": 0,
              "new_builds": 0, "new_installs": 0, "browser_pages_observed": 0}
    save(args.output, result)
    print(json.dumps({key: result[key] for key in ("status", "distinct_current_paths", "t1_sealed_files",
                                                  "candidate_file_count", "old_p01_files")}))


if __name__ == "__main__":
    main()
