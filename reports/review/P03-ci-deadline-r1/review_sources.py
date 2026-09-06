"""Bind the exact candidate, immutable worker evidence, and replay inputs."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

BASE = "4a1fa84d2d367ed037a1e39b1d4033f54a385e6a"
CODE = "f69c6a309ff45980c21c2119016f4c5cf8acf8b7"
CANDIDATE = "947144fa2dd248113f6db412f120cdae5483c9b8"
PROOF_SHA = "dc09b0aa83cd74e57bae7d8b2641a503b26561f2217398afc750a34011e79c06"
MANIFEST_SHA = "a7f4e1a3bfcde88ce9d94a4bae79d5ff6a218d6e9dbc754f0f3ee9f055ff104b"
TEST = "tests/evaluation/harness/test_harness.py"
HELPER = "tests/evaluation/harness/deadline_cases.py"
DOCS = {
    "coordination/handoffs/P03-ci-deadline-r1.md",
    "reports/harness/P03_CI_DEADLINE_VERIFICATION.md",
    "reports/harness/P03_CI_DEADLINE_EVIDENCE.json",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    for name in ("repo", "worker", "proof", "tokenizer", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir()

    def git(*argv):
        return subprocess.check_output(["git", *argv], cwd=args.repo)

    def blob(commit, name):
        return git("show", f"{commit}:{name}")

    def files(commit):
        return git("ls-tree", "-r", "--name-only", commit).decode().splitlines()

    changed = set(git("diff", "--name-only", BASE, CANDIDATE).decode().splitlines())
    assert changed == DOCS | {TEST, HELPER}
    assert set(git("diff", "--name-only", CODE, CANDIDATE).decode().splitlines()) == DOCS
    assert git("show", "-s", "--format=%P", CANDIDATE).decode().strip() == CODE
    assert git("show", "-s", "--format=%P", CODE).decode().strip() == BASE
    assert subprocess.run(
        ["git", "merge-base", "--is-ancestor",
         "f7086413a9fedd9e2a473ac6d2869efff74ddad5", CANDIDATE],
        cwd=args.repo, check=False,
    ).returncode == 1
    candidate_files = {}
    for name in files(CANDIDATE):
        raw = blob(CANDIDATE, name)
        assert (args.repo / name).read_bytes() == raw
        assert (args.worker / name).read_bytes() == raw
        candidate_files[name] = {"sha256": sha(raw), "bytes": len(raw)}
    unchanged = files(BASE)
    unchanged.remove(TEST)
    for name in unchanged:
        assert blob(BASE, name) == blob(CANDIDATE, name)

    worker_private = args.worker / ".toolalign-local/p03-ci-deadline"
    manifest_raw = (worker_private / "handoff-manifest.json").read_bytes()
    proof_raw = args.proof.read_bytes()
    assert sha(manifest_raw) == MANIFEST_SHA and sha(proof_raw) == PROOF_SHA
    manifest, proof = json.loads(manifest_raw), json.loads(proof_raw)
    assert manifest["candidate"] == proof["candidate"] == CANDIDATE
    allowed = [args.worker.resolve(), args.tokenizer.resolve(),
               Path(manifest["system_test_temp"]).resolve()]
    symlinks = {}
    for name, expected in proof["file_checks"].items():
        path = Path(name)
        assert ".." not in path.parts
        assert any(path.is_relative_to(root) for root in allowed), name
        if path.is_symlink():
            symlinks[name] = str(path.resolve(strict=True))
        raw = path.read_bytes()
        assert sha(raw) == expected["sha256"] and len(raw) == expected["bytes"], name

    published = json.loads(blob(CANDIDATE, "reports/harness/P03_CI_DEADLINE_EVIDENCE.json"))
    for section in ("private_evidence_sha256", "verification_helpers"):
        for name, expected in published[section].items():
            assert sha((worker_private / name).read_bytes()) == expected
    for name, expected in published["environment"]["borrowed_source_sha256"].items():
        assert sha((args.tokenizer / name).read_bytes()) == expected
    for label, command in manifest["checks"].items():
        raw = (worker_private / "checks" / (label + ".log")).read_bytes()
        assert sha(raw) == command["log_sha256"]
        actual = json.loads((worker_private / "checks" / (label + ".json")).read_text())
        assert actual == command
    for command in published["checks"]:
        actual = manifest["checks"][command["label"]]
        for key in ("exit_code", "head", "index_tree", "started_at",
                    "elapsed_seconds", "log_sha256"):
            assert command[key] == actual[key]
        replacements = {
            "${P03_TOKENIZER_DIR}": str(args.tokenizer),
            "${P03_CPU_PYTHON}": manifest["checks"]["full-cpu-r3"]["command"][4],
            "${P03_PYTEST_TEMP}": manifest["system_test_temp"],
        }
        restored = []
        for argument in command["command"]:
            for placeholder, real_path in replacements.items():
                argument = argument.replace(placeholder, real_path)
            restored.append(argument)
        assert restored == actual["command"]

    originals = published["original_reproduction"]
    original_test = blob(BASE, TEST)
    assert sha(original_test) == originals["original_test_sha256"]
    assert (worker_private / "test_harness.original.py").read_bytes() == original_test
    fixture = "tests/fixtures/tools/development.json"
    replays = {}
    for mode, test_raw, helper_name, launcher in (
        ("original", original_test, "deadline_cases.before.py", "test_original_deadline.py"),
        ("negative", blob(CANDIDATE, TEST), None, "test_negative_control.py"),
    ):
        root = output / (mode + "-replay")
        helper = ((worker_private / helper_name).read_bytes() if helper_name
                  else blob(CANDIDATE, HELPER))
        sources = {
            TEST: test_raw, HELPER: helper, fixture: blob(BASE, fixture),
            ".toolalign-local/p03-ci-deadline/" + launcher:
                (worker_private / launcher).read_bytes(),
        }
        for name, raw in sources.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        replays[mode] = {"root": str(root), "files": {
            name: {"sha256": sha(raw), "bytes": len(raw)} for name, raw in sources.items()
        }}

    package_inputs = [name for name in files(BASE) if name.startswith("src/toolalign/")]
    package_inputs += ["LICENSE", "README.md", "pyproject.toml"]
    for name in package_inputs:
        raw = blob(BASE, name)
        assert raw == blob(CANDIDATE, name)
        path = output / "baseline-package" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    result = {
        "candidate": CANDIDATE, "candidate_parent": CODE, "base": BASE,
        "candidate_tree": git("rev-parse", CANDIDATE + "^{tree}").decode().strip(),
        "candidate_files": candidate_files, "unchanged_base_files": unchanged,
        "changed_files": sorted(changed), "after_code_only_documents": sorted(DOCS),
        "proof_sha256": PROOF_SHA, "manifest_sha256": MANIFEST_SHA,
        "independently_rehashed_proof_paths": len(proof["file_checks"]),
        "approved_historical_symlink_targets": symlinks,
        "worker_command_logs_verified": len(manifest["checks"]),
        "public_command_metadata_verified": len(published["checks"]),
        "source_hashes": published["environment"]["borrowed_source_sha256"],
        "replays": replays, "baseline_package_inputs": package_inputs,
        "baseline_package_input_count": len(package_inputs),
        "known_missing_inline_output_log": published["preserved_failures"][-1],
    }
    (output / "sources.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "candidate_files": len(candidate_files), "unchanged": len(unchanged),
        "proof_paths_rehashed": len(proof["file_checks"]),
        "worker_logs": len(manifest["checks"]), "baseline_inputs": len(package_inputs),
        "replays_prepared": list(replays),
    }))


if __name__ == "__main__":
    main()
