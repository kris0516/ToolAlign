"""Read-only R1 checks of provenance, recorded runs and real package members.

Run with the R1 CPU tokenizer environment. D1 environments and archives are never
executed or extracted. Private paths and source records are omitted from output.
"""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import re
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

CANDIDATE = "b0d8d83750c48cd951c16b50cfa28a7898976e72"
SYNC_AUTHORIZATION = "f2a271be616cdb53c01e8d671029f31ae140c037"
REVIEW_AUTHORIZATION = "c44739ac1e2fe282f5f51f80c5ea099687051ff3"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def git(*arguments):
    return subprocess.check_output(["git", *arguments])


def run(d1, output):
    assert git("rev-parse", "HEAD").decode().strip() == CANDIDATE
    assert git("branch", "--show-current").decode().strip() == "review/p02-r1"
    tracked = git("ls-tree", "-rz", "--name-only", CANDIDATE).decode().split("\0")[:-1]
    for name in tracked:
        assert Path(name).read_bytes() == git("show", CANDIDATE + ":" + name)
    changed = git("diff", "--name-only", SYNC_AUTHORIZATION, CANDIDATE).decode().splitlines()
    allowed = ("src/toolalign/data/", "tests/data/", "data/manifests/", "reports/data/")
    assert len(changed) == 40
    assert all(name.startswith(allowed) or name in {"coordination/handoffs/P02-r1.md", "coordination/handoffs/P02-base-r2.md"} for name in changed)
    assert git("merge-base", SYNC_AUTHORIZATION, CANDIDATE).decode().strip() == SYNC_AUTHORIZATION
    actual_packages = {re.sub(r"[-_.]+", "-", d.metadata["Name"].lower()): d.version for d in importlib.metadata.distributions()}
    expected_packages = dict(line.strip().split("==") for line in Path("reports/data/tokenizer-audit-environment.txt").read_text().splitlines())
    assert actual_packages == expected_packages and len(actual_packages) == 27
    assert importlib.util.find_spec("torch") is None and importlib.util.find_spec("mlx") is None
    assert not ({"torch", "mlx", "transformers"} & set(sys.modules))
    provenance = []
    for folder_name, lock_name in [("toolace", "toolace-source.v1.json"), ("qwen", "qwen-source.v1.json")]:
        folder = d1 / "verified-source" / folder_name
        lock = read(Path("data/manifests") / lock_name)
        api, access = read(folder / "api.json"), read(folder / "access.json")
        assert sha(folder / "api.json") == access["api_sha256"]
        assert api["id"] == lock["repo_id"]
        assert api["sha"] == access["revision"] == lock["revision"]
        assert api["gated"] is False and api["private"] is False
        assert access["authenticated"] is False and access["gated"] is False
        assert api["cardData"]["license"] == "apache-2.0"
        assert access["license_id"] == lock["license_id"] == "Apache-2.0"
        for name, spec in lock["files"].items():
            assert sha(folder / name) == spec["sha256"]
            assert (folder / name).stat().st_size == spec["size_bytes"]
        if folder_name == "toolace":
            assert "license: apache-2.0" in (folder / "README.md").read_text()
            assert not any(row["rfilename"].casefold() == "license" for row in api["siblings"])
        else:
            assert "Apache License" in (folder / "LICENSE").read_text()
            assert "Version 2.0, January 2004" in (folder / "LICENSE").read_text()
        provenance.append({"repo_id": lock["repo_id"], "revision": lock["revision"],
                           "license_id": lock["license_id"], "api_sha256": sha(folder / "api.json"),
                           "access_sha256": sha(folder / "access.json"),
                           "observed_at_utc_by_downloader": access["accessed_at_utc"],
                           "gated_at_recorded_access": False, "authenticated": False,
                           "files": lock["files"], "fresh_upstream_http_check": "BLOCKED_BY_WEB_URL_POLICY_NOT_RETRIED"})
    recorded = {}
    for report_name in ["P02_STRICT_CHECKPOINT.json", "P02_TOKENIZER_ALIGNMENT.json", "P02_POLICY_BUILD.json", "P02_BASE_R2.json"]:
        report = read(Path("reports/data") / report_name)
        for entry in report["commands"] + report.get("resolved_or_contained_failures", []):
            label = entry["label"]
            assert re.fullmatch(r"[a-z0-9-]+", label)
            if label == "policy-wheel":
                # The failed private-content archive and its detailed failure log
                # remain outside this review's inspection; retain declared status.
                recorded[label] = {"label": label, "exit_code": entry["exit_code"],
                                   "log_sha256": entry["log_sha256"], "raw_log_verified_here": False,
                                   "reason": "prior restricted failed-archive evidence; not read or extracted"}
                continue
            log, metadata = d1 / "logs" / (label + ".log"), d1 / "logs" / (label + ".json")
            assert sha(log) == entry["log_sha256"]
            raw_metadata = read(metadata)
            for key in ["label", "command", "extra_environment", "started_at_utc", "elapsed_seconds", "exit_code", "log_sha256", "git_head"]:
                if key in entry:
                    assert raw_metadata[key] == entry[key]
            recorded[label] = {"label": label, "exit_code": entry["exit_code"], "log_sha256": sha(log),
                               "metadata_sha256": sha(metadata), "raw_log_verified_here": True}
    a, b = [read(d1 / "logs" / ("policy-build-" + suffix + ".json")) for suffix in ["a", "b"]]
    assert a["command"][-1] != b["command"][-1]
    assert a["started_at_utc"] != b["started_at_utc"] and a["elapsed_seconds"] > 0 and b["elapsed_seconds"] > 0
    for entry in [a, b]:
        assert entry["exit_code"] == 0 and entry["git_head"] == "9be07a5b88d1dac1a6e1fea30358af1049b1119a"
    configs = [read(d1 / ("config-policy-" + suffix + ".json")) for suffix in ["a", "b"]]
    assert configs[0]["output_dir"] != configs[1]["output_dir"]
    assert {k: v for k, v in configs[0].items() if k != "output_dir"} == {k: v for k, v in configs[1].items() if k != "output_dir"}
    strict = read("reports/data/P02_STRICT_CHECKPOINT.json")
    assert strict["audit"]["final_examples"] == 0
    assert strict["build_manifest"]["artifacts"]["assignments.jsonl"] == sha(d1 / "policy-a/assignments.jsonl")
    for label, expected in [("exploratory-build.log", strict["known_exploratory_failure"]["log_sha256"]),
                            ("exploratory-trace.log", strict["known_exploratory_failure"]["trace_log_sha256"])]:
        assert sha(d1 / "logs" / label) == expected
    alignment = read("reports/data/P02_TOKENIZER_ALIGNMENT.json")
    golden = read("tests/data/tokenizer_reference.v1.json")
    # Reference strings and IDs are original public fixtures, not source samples.
    reference = read(d1 / "tokenizer-final-hf.json")
    local = read(d1 / "tokenizer-final-local.json")
    assert golden["tokenizer_lock_hash"] == reference["tokenizer_lock_hash"] == local["tokenizer_lock_hash"]
    assert not reference["model_libraries_loaded"] and not local["model_libraries_loaded"]
    assert reference["fixture_file_sha256"] == sha("tests/data/tokenizer_cases.py")
    assert local["fixture_file_sha256"] == reference["fixture_file_sha256"]
    fields = ["example_hash", "prompt_text", "completion_text", "prompt_ids", "concatenated_ids", "sequence_ids", "eos_token_id", "prefix_stable"]
    assert len(reference["results"]) == len(local["results"]) == len(golden["cases"]) == 16
    for one, other in zip(reference["results"], local["results"], strict=True):
        assert one["id"] == other["id"]
        assert all(one[key] == other[key] for key in fields)
    assert sha(d1 / "tokenizer-final-hf.json") == alignment["comparison"]["reference_evidence_sha256"]
    assert sha(d1 / "tokenizer-final-local.json") == alignment["comparison"]["local_evidence_sha256"]

    tar_path = Path("dist/toolalign-0.0.1.tar.gz")
    wheel_path = Path("dist/toolalign-0.0.1-py3-none-any.whl")
    archives = []
    with tarfile.open(tar_path, "r:gz") as archive:
        members = archive.getmembers()
        assert len(members) == 60 and all(m.isfile() for m in members)
        for member in members:
            part = PurePosixPath(member.name)
            assert not part.is_absolute() and ".." not in part.parts
            relative = str(PurePosixPath(*part.parts[1:]))
            if relative != "PKG-INFO":
                assert relative in tracked
                assert archive.extractfile(member).read() == Path(relative).read_bytes()
        archives.append({"type": "sdist", "bytes": tar_path.stat().st_size, "sha256": sha(tar_path), "members": len(members), "only_tracked_files_plus_pkg_info": True})
    with zipfile.ZipFile(wheel_path) as archive:
        source_count = 0
        for name in archive.namelist():
            if name.startswith("toolalign/"):
                assert archive.read(name) == (Path("src") / name).read_bytes()
                source_count += 1
            else:
                assert name.startswith("toolalign-0.0.1.dist-info/")
        assert source_count == 24 and len(archive.namelist()) == 29
        archives.append({"type": "wheel", "bytes": wheel_path.stat().st_size, "sha256": sha(wheel_path), "members": len(archive.namelist()), "source_members_equal_candidate": source_count})
    expected_archives = read("reports/data/P02_BASE_R2.json")["archives"]
    assert sha(wheel_path) == "78ad37239a3d1023295d2e7a73be19583bcd335a8f50b47ca1cefb61f86b4672"
    assert sha(tar_path) == "d7ee2db8d9ce257db9a035adbee389316f4a89d91832494117336e859c84a241"
    assert expected_archives
    disk_kib = int(subprocess.check_output(["du", "-sk", ".toolalign-local/review-p02"]).split()[0])
    assert disk_kib * 1024 < 2 * 1024**3
    result = {
        "status": "PASS", "candidate": CANDIDATE, "review_authorization": REVIEW_AUTHORIZATION,
        "sync_authorization": SYNC_AUTHORIZATION, "candidate_tracked_files_unchanged": len(tracked),
        "complete_p02_diff_files": len(changed), "python": sys.version.split()[0],
        "packages_exactly_pinned": actual_packages, "package_count": len(actual_packages),
        "model_libraries_available_or_loaded": [], "provenance": provenance,
        "worker_log_records": list(recorded.values()),
        "verified_worker_logs": sum(r["raw_log_verified_here"] for r in recorded.values()),
        "prior_private_archive_and_detailed_log": "NOT_READ_NOT_EXTRACTED",
        "two_worker_builds": [{k: row[k] for k in ["label", "started_at_utc", "elapsed_seconds", "exit_code", "git_head", "log_sha256"]} for row in [a, b]],
        "reviewer_full_corpus_builds": 0, "strict_zero_checkpoint_preserved": True,
        "original_assignment_bytes_preserved": True,
        "worker_reference_tokenizer_evidence": {"cases": 16, "exact_compared_fields": fields,
                                                "reference_packages": reference["packages"],
                                                "reference_reexecuted_by_r1": False},
        "real_archives": archives, "private_review_disk_kib": disk_kib,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"worker_log_records", "packages_exactly_pinned"}}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("private_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    assert ".toolalign-local" in args.output.resolve().parts
    run(args.private_root, args.output)
