"""Read the frozen handoff, original receipts and source snapshots directly."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CANDIDATE = "9b7cf019b1d55501a7e656dbfb79b13bc7369fa0"
BASE = "86b80bada50ac7c8f4b3910e3831a397ed65a853"
PAYLOAD = "1c90ce0ba5f505e4ca4e7118012c351c5e9dff2e"
COMPLETION = "dad346e0be874749d7dd2c3af28051d6a9e59aff8578c1747780a47ea0242782"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def utc(value):
    result = datetime.fromisoformat(value)
    assert result.utcoffset() is not None and result.utcoffset().total_seconds() == 0
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("worker", "original", "repo", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.worker, args.original, args.repo = (
        p.resolve() for p in (args.worker, args.original, args.repo)
    )
    checked, links = {}, {}

    def bind(path, declaration):
        path = Path(path)
        assert path.is_file() and not path.is_symlink(), path
        expected = declaration if isinstance(declaration, str) else declaration["sha256"]
        size = path.stat().st_size
        actual = digest(path)
        assert actual == expected, path
        if isinstance(declaration, dict):
            expected_size = declaration.get("bytes", declaration.get("size_bytes"))
            assert expected_size is None or size == expected_size, path
        entry = {"sha256": actual, "bytes": size}
        key = str(path)
        assert key not in checked or checked[key] == entry
        checked[key] = entry
        return entry

    def git(*argv):
        return subprocess.check_output(["git", *argv], cwd=args.repo)

    bind(args.original / "completion.json", COMPLETION)
    completion = load(args.original / "completion.json")
    assert completion["candidate_commit"] == CANDIDATE and completion["code_base"] == BASE
    assert completion["training_authorized"] is False
    for name, key in (("final-checks.json", "final_checks_sha256"),
                      ("publication.json", "publication_sha256")):
        bind(args.original / name, completion[key])
    final = load(args.original / "final-checks.json")
    publication = load(args.original / "publication.json")
    assert publication["candidate_commit"] == CANDIDATE
    assert publication["ordinary_push"] and publication["git_clean"]
    assert publication["remote_ref_line"].split()[0] == CANDIDATE
    assert len(completion["candidate_public_files"]) == 440
    original_names = set(git("ls-tree", "-r", "--name-only", BASE).decode().splitlines())
    assert len(original_names) == 428
    candidate_names = set(git("ls-tree", "-r", "--name-only", CANDIDATE).decode().splitlines())
    assert candidate_names == set(completion["candidate_public_files"])
    assert candidate_names - original_names == set(publication["changed_files"])
    assert len(candidate_names - original_names) == 12
    for name, sha in completion["candidate_public_files"].items():
        data = git("show", CANDIDATE + ":" + name)
        assert hashlib.sha256(data).hexdigest() == sha
        assert publication["candidate_tracked_files"][name] == sha
        bind(args.worker / name, sha)
        assert (args.repo / name).read_bytes() == data
        if name in original_names:
            assert git("show", BASE + ":" + name) == data
        if name.startswith(("src/", "tests/", "configs/")):
            assert git("show", PAYLOAD + ":" + name) == data
    for name, info in completion["private_artifacts"].items():
        path = args.original / name
        assert path.resolve().is_relative_to(args.original)
        bind(path, info)
    for name, info in completion["retained_test_artifacts"].items():
        path = Path(name)
        assert any(part.startswith("toolalign-quality-remediation-cpu-") for part in path.parts)
        bind(path, info)
    for name, declaration in completion["retained_test_symlinks"].items():
        assert declaration["dereferenced"] is False
        target = declaration["target"]
        assert Path(name).is_symlink() and os.readlink(name) == target
        links[name] = declaration
    for name, info in final["preserved_originals"].items():
        bind(name, info)
    commands = {}
    epochs = {}
    git_trees = {}
    for label, declared in completion["logged_commands"].items():
        meta = args.worker / ".toolalign-local/logs" / (label + ".json")
        log = meta.with_suffix(".log")
        bind(meta, declared["command_metadata_sha256"])
        bind(log, declared["log_sha256"])
        record = load(meta)
        assert record["label"] == label
        assert utc(record["started_at_utc"]) <= utc(record["finished_at_utc"])
        for key in ("exit_code", "git_head", "git_head_after", "log_sha256", "source_epoch"):
            assert record[key] == declared[key]
        assert isinstance(record["command"], list) and record["command"]
        assert record["elapsed_seconds"] >= 0
        # The original wrapper has no cwd field; preserve that omission. Its
        # frozen source establishes that it ran in the worker repository.
        bind(args.original / "record.py", record["wrapper_sha256"])
        epoch = record["source_epoch"]
        if epoch not in epochs:
            root = args.original / "source-epochs" / epoch
            files = load(root / "files.json")
            compact = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
            assert hashlib.sha256(compact).hexdigest() == epoch
            head = record["git_head"]
            if head not in git_trees:
                entries = {}
                for line in git("ls-tree", "-r", head).decode().splitlines():
                    metadata, name = line.split("\t")
                    entries[name] = metadata.split()[2]
                git_trees[head] = entries
            head_files = git_trees[head]
            assert set(head_files) <= set(files) <= candidate_names
            for name, sha in files.items():
                bind(root / name, sha)
                if name in original_names and name in head_files:
                    data = (root / name).read_bytes()
                    header = b"blob " + str(len(data)).encode() + b"\0"
                    assert hashlib.sha1(header + data).hexdigest() == head_files[name]
            epochs[epoch] = {"files": len(files), "manifest_sha256": digest(root / "files.json"),
                             "recorded_git_head": head,
                             "baseline_files_bound_to_recorded_head": len(set(head_files) & original_names),
                             "quality_revision_sha256": files.get("src/toolalign/data/quality_revision.py"),
                             "quality_materials_sha256": files.get("src/toolalign/data/quality_materials.py")}
        commands[label] = {**record, "original_cwd_field_present": "cwd" in record,
                           "source_snapshot": epochs[epoch]}
    assert len(commands) == 32
    assert sum(c["exit_code"] != 0 for c in commands.values()) == 3
    assert len(epochs) == 11
    race = load(args.original / "wrapper-race-r1.json")
    assert race["command_started"] is False
    nested = {}
    for folder, count, code in (("input-replacements", 12, 1), ("package-verification", 4, 0)):
        receipts = sorted((args.original / folder).glob("*.command.json"))
        assert len(receipts) == count
        for path in receipts:
            receipt = load(path)
            assert receipt["exit_code"] == code
            assert utc(receipt["started_at_utc"]) <= utc(receipt["finished_at_utc"])
            for channel in ("stdout", "stderr"):
                raw = path.with_name(path.name.removesuffix(".command.json") + "." + channel)
                bind(raw, receipt[channel + "_sha256"])
            if folder == "input-replacements":
                raw = path.with_name(path.name.removesuffix(".command.json") + ".stdout")
                assert load(raw) == {"status": "FAIL", "error_type": "DataError", "error_code": "input_hash_mismatch"}
                assert receipt["output_directory_created"] is False
                destination = Path(receipt["argv"][receipt["argv"].index("--output") + 1])
                assert not destination.exists() and not destination.is_symlink()
            nested[str(path.relative_to(args.original))] = receipt
    evidence_path = args.repo / "reports/data/quality-remediation-r1/evidence.v1.json"
    bind(evidence_path, completion["public_evidence_sha256"])
    public = load(evidence_path)
    assert public["raw_command_count_at_report_snapshot"] == len(public["command_records"]) == 26
    for row in public["command_records"]:
        original = commands[row["label"]]
        for key in ("elapsed_seconds", "exit_code", "finished_at_utc", "git_head", "git_head_after",
                    "git_status", "label", "log_sha256", "source_epoch", "started_at_utc", "wrapper_sha256"):
            assert row[key] == original[key]
        assert row["command_metadata_sha256"] == completion["logged_commands"][row["label"]]["command_metadata_sha256"]
        assert row["source_snapshot_files"] == epochs[row["source_epoch"]]["files"]
        assert row["source_snapshot_manifest_sha256"] == epochs[row["source_epoch"]]["manifest_sha256"]
    result = {"status": "PASS_ORIGINAL_HANDOFF_BINDING", "candidate": CANDIDATE,
              "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "candidate_files": 440, "unchanged_base_files": 428,
              "candidate_changes": sorted(candidate_names - original_names),
              "payload_to_final_diff": git("diff", "--name-status", PAYLOAD, CANDIDATE).decode(),
              "checked_paths": checked, "checked_path_count": len(checked),
              "preserved_symlinks": links, "commands": commands, "source_epochs": epochs,
              "nested_receipts": nested, "public_receipts": len(public["command_records"]),
              "failures_preserved": {k: v for k, v in commands.items() if v["exit_code"]},
              "wrapper_before_command_failure": race, "training_authorized": False}
    with args.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "candidate_files", "unchanged_base_files",
                                           "checked_path_count", "public_receipts")}))


if __name__ == "__main__":
    main()
