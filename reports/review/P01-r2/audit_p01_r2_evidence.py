"""Bind the repaired candidate to preserved R1 findings and read-only T1 evidence."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

from toolalign.contracts import validate_record

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = "ac8095faa58a98e143a8dc4d63042093e426feb0"
REVIEW = "ac6bdf78d57c6753865a24a1d216b90dc4478646"
IMPLEMENTATION = "5c32e8a72e957df100691e0096d1413eed8ce8f9"
SOURCE = "src/toolalign/training/compatibility/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blob(commit, path):
    return git("show", commit + ":" + path)


def inside(root, relative):
    path = root / relative
    assert not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
    return path


def outside_scope(source, names):
    nodes = ast.parse(source).body
    for name in names:
        selected = next(node for node in nodes if getattr(node, "name", None) == name)
        nodes = selected.body
    lines = source.splitlines(keepends=True)
    return "".join(lines[:selected.lineno - 1] + ["SCOPED_CHANGE\n"] + lines[selected.end_lineno:])


def scope():
    changed = [row.split("\t") for row in git("diff", "--name-status", REVIEW, CANDIDATE).decode().splitlines()]
    assert len(changed) == 11
    final_additions = [row.split("\t") for row in git("diff", "--name-status", IMPLEMENTATION, CANDIDATE).decode().splitlines()]
    assert len(final_additions) == 4 and all(status == "A" for status, _ in final_additions)
    old_paths = git("ls-tree", "-r", "--name-only", REVIEW).decode().splitlines()
    changed_paths = {path for _, path in changed}
    unchanged = {path: sha(blob(REVIEW, path)) for path in old_paths if path not in changed_paths}
    for path, digest in unchanged.items():
        assert sha(blob(CANDIDATE, path)) == file_sha(ROOT / path) == digest
    assert len(unchanged) == 159
    original_review = {path: digest for path, digest in unchanged.items()
                       if path.startswith("reports/review/P01/") or path == "coordination/handoffs/P01-review-r1.md"}
    assert len(original_review) == 8
    modules = {path.relative_to(ROOT).as_posix(): file_sha(path)
               for path in (ROOT / SOURCE).glob("*.py")}
    assert len(modules) == 8
    for path, digest in modules.items():
        assert sha(blob(IMPLEMENTATION, path)) == sha(blob(CANDIDATE, path)) == digest
    assert outside_scope(blob(REVIEW, SOURCE + "fallback_probe.py").decode(), ["run_fallback", "Callback"]) == outside_scope((ROOT / SOURCE / "fallback_probe.py").read_text(), ["run_fallback", "Callback"])
    assert outside_scope(blob(REVIEW, SOURCE + "execution.py").decode(), ["launch"]) == outside_scope((ROOT / SOURCE / "execution.py").read_text(), ["launch"])
    return {
        "changed_from_original_review": changed,
        "last_candidate_commit_additions": final_additions,
        "unchanged_original_files": len(unchanged),
        "unchanged_original_file_map_sha256": sha(json.dumps(unchanged, sort_keys=True).encode()),
        "original_eight_review_files": original_review,
        "p01_modules": modules,
        "fallback_outside_callback_unchanged": True,
        "execution_outside_launch_unchanged": True,
        "core_numerical_model_samples_and_frozen_contracts_unchanged": True,
    }


def history(t1, previous_private):
    published = read(ROOT / "reports/review/P01/evidence.json")
    previous_path = previous_private / "historical-audit-final.json"
    expected = published["private_artifact_hashes"]["historical-audit-final.json"]
    assert file_sha(previous_path) == expected
    prior = read(previous_path)
    assert prior["candidate"] == "59b3802c81aa6eceaf3609af88f288756bcb1581"
    raw_root = t1 / ".toolalign-local/runs"
    by_id = {read(path)["run_id"]: path.parent for path in raw_root.glob("*/config.json")}
    runs, manifest_count = [], 0
    for earlier in prior["historical"]["runs"]:
        directory = by_id[earlier["run_id"]]
        for name, expected_hash in earlier["evidence_hashes"].items():
            assert file_sha(inside(directory, name)) == expected_hash
        artifacts = {}
        manifest_path = directory / "run.json"
        if manifest_path.exists():
            manifest = read(manifest_path)
            validate_record(manifest, "run")
            for artifact in manifest["artifacts"]:
                path = inside(directory, artifact["relative_path"])
                assert path.stat().st_size == artifact["size_bytes"]
                assert file_sha(path) == artifact["sha256"]
                artifacts[artifact["relative_path"]] = artifact["sha256"]
            assert len(artifacts) == earlier["manifest_artifacts_checked"]
        manifest_count += len(artifacts)
        runs.append({
            "run_id": earlier["run_id"], "assessment": earlier["assessment"],
            "exit_code": earlier["exit_code"], "raw_result_status": earlier["raw_result_status"],
            "raw_evidence_hashes_unchanged": earlier["evidence_hashes"],
            "manifest_artifacts_unchanged": artifacts,
        })
    assert len(runs) == 10 and manifest_count == 185
    commands = []
    for item in prior["metadata"]["raw_command_logs"]:
        path = t1 / ".toolalign-local/checks" / (item["name"] + ".log")
        assert file_sha(path) == item["sha256"]
        commands.append(item)
    assert len(commands) == 27
    return {
        "previous_review_commit": REVIEW, "previous_audit_sha256": expected,
        "runs": runs, "run_count": len(runs), "manifest_artifacts_rehashed": manifest_count,
        "old_command_logs_rehashed": commands,
        "prior_token_mask_parameter_and_math_interpretation": "REUSED_ON_UNCHANGED_EVIDENCE",
        "tokenizer_or_model_import": False,
        "new_gpu_or_model_reexecution": "NOT_RUN",
        "original_downloaded_weights_rehashed_again": "NOT_RUN",
    }


def source_mapping(t1):
    mapping = read(ROOT / "reports/hardware/P01_FIX_R3_SOURCES.json")
    config_path = t1 / ".toolalign-local/runs/math-r2/config.json"
    config = read(config_path)
    assert config["git_commit"] == mapping["recorded_git_commit"] == "aaab75ed5d993f9354f11f74b58edb67d0af45c3"
    assert mapping["resolved_source_commit"] == "47c03404bab043e85b417cd8a6d0432dc2f85479"
    canonical = json.dumps(config["source_files"], sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    assert sha(canonical) == config["source_hash"] == mapping["recorded_source_hash"]
    assert len(config["source_files"]) == 8
    mismatches = []
    for name, expected in config["source_files"].items():
        recorded = sha(blob(config["git_commit"], SOURCE + name))
        resolved = sha(blob(mapping["resolved_source_commit"], SOURCE + name))
        assert resolved == expected
        assert mapping["source_files"][name] == {
            "recorded_worktree_sha256": expected,
            "recorded_head_blob_sha256": recorded,
            "resolved_commit_blob_sha256": resolved,
        }
        if recorded != expected:
            mismatches.append(name)
    assert sorted(mismatches) == mapping["recorded_head_mismatches"]
    site = t1 / ".toolalign-local/base-r2/venv-replay/lib/python3.14/site-packages"
    identities = read(ROOT / "reports/hardware/P01_SOURCE_IDENTITIES.json")
    upstream = {}
    for package in identities.values():
        for name, expected in package["files"].items():
            assert file_sha(inside(site, name)) == expected
            upstream[name] = expected
    assert len(upstream) == 11
    trainer = (site / "mlx_lm_lora/trainer/dpo_trainer.py").read_text()
    assert trainer.index("optimizer.update(model, grad)") < trainer.index("training_callback.on_train_loss_report")
    assert trainer.index("mx.eval(state, losses, rewards, n_tokens, grad_accum, *_acc)") < trainer.index("training_callback.on_train_loss_report(train_info)")
    return {
        "math_r2_mapping": mapping, "original_config_sha256": file_sha(config_path),
        "upstream_source_files_rehashed_without_import": upstream,
        "upstream_update_before_callback_order_preserved": True,
    }


def worker_evidence(t1):
    public = read(ROOT / "reports/hardware/P01_FIX_R3_VALIDATION.json")
    commands = []
    for command in public["commands"]:
        path = t1 / ".toolalign-local/checks" / (command["name"] + ".log")
        metadata = read(path.with_suffix(".json"))
        assert metadata == command
        assert file_sha(path) == command["sha256"]
        commands.append(command)
    assert len(commands) == 13
    release = t1 / ".toolalign-local/checks/fix-r3-release-public.json"
    metadata = read(release)
    assert file_sha(release.with_suffix(".log")) == metadata["sha256"]
    commands.append(metadata)
    proof = {}
    for name, expected in public["proof_files_sha256"].items():
        path = inside(t1, name) if name.startswith(".toolalign-local/") else ROOT / name
        assert file_sha(path) == expected
        proof[name] = expected
    outputs = {}
    for name, expected in public["private_output_sha256"].items():
        assert file_sha(t1 / ".toolalign-local/p01-fix-r3" / name) == expected
        outputs[name] = expected
    frozen_summary = (ROOT / "reports/hardware/P01_RESULTS.json").read_bytes()
    assert (t1 / ".toolalign-local/p01-fix-r3/HISTORICAL_RESULTS.json").read_bytes() == frozen_summary
    assert sha(frozen_summary) == public["preservation"]["historical_summary"]["sha256"]
    example_hashes = set()
    for case in public["failure_examples"]["monitor"]:
        example_hashes.update([case["resources_sha256"], case["manifest_sha256"]])
    callback = public["failure_examples"]["callback"]
    example_hashes.update(callback[key] for key in ("before_observation_sha256", "after_observation_sha256", "failed_steps_sha256"))
    candidates = list((t1 / ".toolalign-local/p01-fix-r3").glob("before-r1/**/callback-observation.json"))
    candidates += list((t1 / ".toolalign-local/p01-fix-r3").glob("final-r1/**/*.json"))
    seen = {file_sha(path) for path in candidates}
    assert example_hashes <= seen
    package = read(t1 / ".toolalign-local/p01-fix-r3/PACKAGE.json")
    assert package == public["package_validation"]
    assert len(package["installed_checks"]) == 13
    assert all(item["exit_code"] == 0 for item in package["installed_checks"])
    return {
        "public_validation_sha256": file_sha(ROOT / "reports/hardware/P01_FIX_R3_VALIDATION.json"),
        "commands_rehashed": commands, "proof_files_rehashed": proof,
        "private_outputs_rehashed": outputs, "failure_example_files_rehashed": sorted(example_hashes),
        "historical_summary_sha256": sha(frozen_summary),
        "installed_package_metadata": package,
        "historical_installed_stdout_stderr_rehash": "NOT_RUN: temporary install streams were not retained as separate files; producer metadata is preserved, and R1 performs a new independent installation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-root", type=Path, required=True)
    parser.add_argument("--previous-review-private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.t1_root.resolve() != ROOT
    assert args.output.resolve().is_relative_to((ROOT / ".toolalign-local/review-p01-r2").resolve())
    output = {
        "candidate": CANDIDATE, "scope": scope(),
        "history": history(args.t1_root, args.previous_review_private),
        "source_mapping": source_mapping(args.t1_root),
        "worker_evidence": worker_evidence(args.t1_root),
        "status": "PASS: evidence binding only, independent review verdict is separate",
    }
    encoded = json.dumps(output, indent=2, sort_keys=True) + "\n"
    encoded = encoded.replace(str(args.t1_root.resolve()), "<T1_WORKTREE>").replace(str(ROOT), "<R1_WORKTREE>")
    args.output.write_text(encoded)
    print(json.dumps({
        "candidate": CANDIDATE, "unchanged_original_files": output["scope"]["unchanged_original_files"],
        "runs": 10, "manifest_artifacts_rehashed": 185, "original_review_files": 8,
        "historical_command_logs_rehashed": 27, "repair_command_logs_rehashed": 14,
        "math_r2_sources_mapped": 8, "upstream_source_files_rehashed": 11,
        "output_sha256": file_sha(args.output), "model_or_tokenizer_import": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
