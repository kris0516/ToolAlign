"""Bind preserved failure evidence and current archives without running worker code."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

# Reuse the unchanged R1 archive reader; all commit selection is explicit here.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "P03"))
from audit_p03_evidence import archive_check, audit_demo, safe_file, sha  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = "3598cef2efb99e2990e384812a028902964cf494"
ORIGINAL = "79a15d990fc27a9a33d033983c94eb92cccfb268"
REVIEW = "f34f7c5a4eac54b18a2b092495f4ce8eaa334f98"
CHECKPOINT = "2195b2e4ea3219884c3a8c1eed26d413141daa65"
MERGE = "5fe4e905cf43af04e744d3801b19472bd839c67a"
IMPLEMENTATION = "8d11225861214141de3da77c2b5eaf1752fc43b2"
PRIVATE = ROOT / ".toolalign-local/review-p03-r2"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blob(commit, name):
    return git("show", commit + ":" + name)


def read(directory, name):
    return json.loads(safe_file(directory, name).read_bytes())


def package_expectations(commit=CANDIDATE):
    config = tomllib.loads(blob(commit, "pyproject.toml").decode())
    roots = config["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    names = git("ls-tree", "-r", "--name-only", commit).decode().splitlines()
    expected = {
        name: blob(commit, name)
        for name in names
        if name == ".gitignore"
        or any(name == root or name.startswith(root + "/") for root in roots)
    }
    wheel = {
        name.removeprefix("src/"): data
        for name, data in expected.items()
        if name.startswith("src/toolalign/")
    }
    metadata = {
        "toolalign-0.0.1.dist-info/" + name
        for name in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")
    }
    return expected, wheel, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e1-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    e1 = args.e1_root.resolve(strict=True)
    old = e1 / ".toolalign-local/p03-fix-r3"
    new = old / "final"
    original_review = ROOT / ".toolalign-local/review-p03"
    manifest = read(new, "handoff-manifest.json")
    assert manifest["candidate"] == CANDIDATE
    assert manifest["implementation_commit"] == IMPLEMENTATION
    assert git("show", "-s", "--format=%P", MERGE).decode().split() == [CHECKPOINT, REVIEW]
    assert git("show", "-s", "--format=%P", REVIEW).decode().split() == [ORIGINAL]
    review_files = read(new, "original-review-files.json")["files"]
    for name, digest in review_files.items():
        assert sha(blob(REVIEW, name)) == sha(blob(CANDIDATE, name)) == digest
        assert sha((ROOT / name).read_bytes()) == digest
    assert len(review_files) == 7
    changed = git("diff", "--name-only", ORIGINAL, CANDIDATE).decode().splitlines()
    assert set(changed) == set(review_files) | set(manifest["self_files"])
    assert len(changed) == 15
    assert git("diff", "--name-only", IMPLEMENTATION, CANDIDATE).decode().splitlines() == [
        "coordination/handoffs/P03-fix-r3.md",
        "reports/harness/P03_FIX_R3_VERIFICATION.md",
    ]
    candidate_hashes = {}
    for name in git("ls-tree", "-r", "--name-only", CANDIDATE).decode().splitlines():
        data = blob(CANDIDATE, name)
        assert (ROOT / name).read_bytes() == data
        candidate_hashes[name] = sha(data)
    unchanged_original = 0
    for name in git("ls-tree", "-r", "--name-only", ORIGINAL).decode().splitlines():
        if name not in changed:
            assert blob(ORIGINAL, name) == blob(CANDIDATE, name)
            unchanged_original += 1

    # This includes all earlier raw files and archives, never other worktree writes.
    protected = read(new, "preservation-before.json")
    checkpoint_names = set(git("ls-tree", "-r", "--name-only", CHECKPOINT).decode().splitlines())
    private_count, tracked_count = 0, 0
    interpreter_links = {
        f".toolalign-local/{group}/isolated/venv/bin/{name}"
        for group in ("p03-base-r2", "p03-fix-r3")
        for name in ("python", "python3", "python3.14")
    }
    interpreter = Path(sys.executable).resolve(strict=True)
    interpreter_bytes = interpreter.read_bytes()
    for name, metadata in protected.items():
        digest = metadata["sha256"]
        if name not in checkpoint_names:
            assert name.startswith((".toolalign-local/", "dist/"))
            if name in interpreter_links:
                path = e1 / name
                assert path.is_symlink() and path.resolve(strict=True) == interpreter
                data = interpreter_bytes
            else:
                data = safe_file(e1, name).read_bytes()
            assert sha(data) == digest and len(data) == metadata["bytes"]
            private_count += 1
        else:
            data = blob(CHECKPOINT, name)
            assert sha(data) == digest and len(data) == metadata["bytes"]
            if name != "src/toolalign/evaluation/oracles/semantic.py":
                assert sha(blob(CANDIDATE, name)) == digest
            tracked_count += 1
    assert private_count == 741 and tracked_count == 148
    initial = read(e1 / ".toolalign-local/p03-base-r2", "preserved-r1.json")
    assert len(initial["public_files"]) == 17 and len(initial["prior_private_files"]) == 63
    for name, digest in initial["public_files"].items():
        assert sha(blob(ORIGINAL, name)) == digest
    for name, digest in initial["prior_private_files"].items():
        assert sha(safe_file(e1 / ".toolalign-local/p03", name).read_bytes()) == digest

    previous = json.loads(blob(REVIEW, "reports/review/P03/evidence.json"))
    assert previous["verdict"] == "FAIL" and previous["findings_counts"] == {
        "P0": 0,
        "P1": 2,
        "P2": 1,
    }
    for entry in previous["commands"]:
        assert (
            sha(safe_file(original_review, "logs/" + entry["log"]).read_bytes()) == entry["sha256"]
        )
    for name, digest in previous["private_artifact_hashes"].items():
        assert sha(safe_file(original_review, name).read_bytes()) == digest
    for entries in previous["observations"].values():
        for entry in entries:
            assert (
                sha(safe_file(original_review, entry["artifact"]).read_bytes())
                == entry["raw_sha256"]
            )
    for entry in previous["package_evidence"]["commands"]:
        for suffix in ("stdout", "stderr"):
            assert (
                sha(
                    safe_file(
                        original_review, "package-check/" + entry["name"] + "." + suffix
                    ).read_bytes()
                )
                == entry[suffix + "_sha256"]
            )
    previous_audit = read(original_review, "historical-audit-final.json")
    for name, value in previous_audit["demos"].items():
        directory = (
            e1 / ".toolalign-local/p03/demo-candidate"
            if name == "original-candidate"
            else e1 / ".toolalign-local/p03-base-r2/isolated/demo"
        )
        for filename, digest in value["artifact_sha256"].items():
            assert sha(safe_file(directory, filename).read_bytes()) == digest

    commands, installed_commands, helper_hashes = [], [], {}
    for label, directory in (("checkpoint", old), ("final", new)):
        for name, digest in read(directory, "evidence-files.json").items():
            assert sha(safe_file(directory, name).read_bytes()) == digest
            helper_hashes[label + "/" + name] = digest
        for path in sorted((directory / "checks").glob("*.json")):
            entry = read(directory, "checks/" + path.name)
            assert entry["label"] == path.stem
            assert (
                sha(safe_file(directory, "checks/" + path.stem + ".log").read_bytes())
                == entry["log_sha256"]
            )
            commands.append({**entry, "group": label})
        installed = read(directory, "isolated-verification.json")
        for entry in installed["commands"]:
            assert entry["exit_code"] == 0
            assert (
                sha(safe_file(directory, "isolated/" + entry["label"] + ".log").read_bytes())
                == entry["log_sha256"]
            )
            installed_commands.append({**entry, "group": label})
    for label, expected in (
        ("r1-before", "1 failed, 53 passed"),
        ("cpu-full", "389 passed"),
        ("oracle-before", "8 failed, 8 passed"),
        ("oracle-after", "1 failed, 16 passed"),
    ):
        assert expected in safe_file(new, "checks/" + label + ".log").read_text()
    for directory, filename in (
        (old, "cleanup-regression-worktree.json"),
        (new, "oracle-final-worktree.json"),
    ):
        for name, digest in read(directory, filename)["files"].items():
            assert sha(blob(CANDIDATE, name)) == digest
    initial_oracle = read(new, "oracle-before-source.json")
    assert (
        sha(blob(MERGE, "src/toolalign/evaluation/oracles/semantic.py"))
        == initial_oracle["source_sha256"]
    )
    assert (
        sha(safe_file(new, "test_oracle_order.before.py").read_bytes())
        == initial_oracle["test_sha256"]
    )
    assert manifest["check_records"] == {
        e["label"]: {k: v for k, v in e.items() if k != "group"}
        for e in commands
        if e["group"] == "final"
    }

    archives = {}
    for label, directory, commit in (("checkpoint", old, CHECKPOINT), ("final", new, CANDIDATE)):
        sdist, wheel, metadata = package_expectations(commit)
        for item in read(directory, "artifact-verification.json")["archives"]:
            path = (
                directory
                / ("rebuilt" if item["route"] == "rebuilt-wheel" else "dist")
                / item["filename"]
            )
            checked = archive_check(
                path,
                sdist if item["route"] == "sdist" else wheel,
                {"PKG-INFO"} if item["route"] == "sdist" else metadata,
            )
            assert all(item[key] == value for key, value in checked.items())
            archives[label + "/" + item["route"]] = checked
    cases = json.loads(blob(CANDIDATE, "tests/fixtures/tools/development.json"))["cases"]
    final_demo = audit_demo(
        new / "isolated/demo", cases, sha(blob(CANDIDATE, "src/toolalign/tools/catalog.py"))
    )
    result = {
        "candidate": CANDIDATE,
        "candidate_tree": git("rev-parse", CANDIDATE + "^{tree}").decode().strip(),
        "candidate_files_unchanged": candidate_hashes,
        "unchanged_original_files": unchanged_original,
        "candidate_changed_paths": changed,
        "original_review_files": review_files,
        "preserved_checkpoint_private_files": private_count,
        "preserved_interpreter_symlinks": len(interpreter_links),
        "checkpoint_tracked_files_bound": tracked_count,
        "original_public_sources_bound": 17,
        "original_private_files_bound": 63,
        "original_review_verdict_unchanged": "FAIL",
        "original_review_commands_verified": len(previous["commands"]),
        "original_review_observations_verified": sum(map(len, previous["observations"].values())),
        "original_review_private_results_verified": len(previous["private_artifact_hashes"]),
        "original_review_installed_commands_verified": len(
            previous["package_evidence"]["commands"]
        ),
        "original_historical_demo_artifacts_rehashed": 22,
        "commands": commands,
        "installed_commands": installed_commands,
        "helper_and_metadata_hashes": helper_hashes,
        "archives": archives,
        "final_installed_demo": final_demo,
        "worker_source_or_scripts_executed": False,
        "worker_worktree_modified": False,
        "old_shared_canaries_new_execution": "NOT_RUN_UNCHANGED_PREVIOUSLY_VERIFIED",
    }
    encoded = (
        json.dumps(result, indent=2, sort_keys=True)
        .replace(str(e1), "<E1_WORKTREE>")
        .replace(str(ROOT), "<R1_WORKTREE>")
        + "\n"
    )
    args.output.write_text(encoded)
    print(
        json.dumps(
            {
                "result": "PASS",
                "candidate_files": len(candidate_hashes),
                "unchanged_original_files": unchanged_original,
                "preserved_private_files": private_count,
                "original_review_files": 7,
                "worker_commands": len(commands),
                "final_worker_commands": len(manifest["check_records"]),
                "worker_installed_commands": len(installed_commands),
                "archive_count": len(archives),
                "new_demo_counts": final_demo["counts"],
                "output_sha256": sha(encoded.encode()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
