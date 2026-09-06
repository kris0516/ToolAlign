"""Read-only binding of the exact fix, new raw records, and prior R1 evidence."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = "9fe3cbe3a067725c37dc213bbf38f9c90ceb5066"
PRIOR_REVIEW = "aaae5a4395dbdd73fd487f80174599ffd3ef9be3"
IMPLEMENTATION = "2efc7a55ea0dcc77a97cd7f5a82e95515c32de00"
MERGE = "65437ea2323f21e6c4c1d7e5b916282209dbd25a"
PREFIX = "src/toolalign/training/compatibility/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size < 2 * 1024**2
    return path.read_bytes()


def load(path):
    return json.loads(read(path))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def source_without_launch(data):
    tree = ast.parse(data)
    tree.body = [n for n in tree.body if not isinstance(n, ast.FunctionDef) or n.name != "launch"]
    return ast.dump(tree, include_attributes=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    worker = args.worker_root.resolve()
    private = worker / ".toolalign-local/p01-fix-r4"
    assert git("rev-parse", "HEAD").decode().strip() == CANDIDATE
    assert args.output.resolve().is_relative_to(ROOT / ".toolalign-local/review-p01-r3")
    assert not args.output.exists()
    parents = git("show", "-s", "--format=%P", MERGE).decode().split()
    assert parents == ["ac8095faa58a98e143a8dc4d63042093e426feb0", PRIOR_REVIEW]
    assert git("rev-parse", CANDIDATE + "^").decode().strip() == IMPLEMENTATION
    tracked = git("ls-tree", "-r", "--name-only", CANDIDATE).decode().splitlines()
    previous = git("ls-tree", "-r", "--name-only", PRIOR_REVIEW).decode().splitlines()
    unchanged = {}
    for name in tracked:
        assert read(ROOT / name) == git("show", CANDIDATE + ":" + name)
    changes = [line.split("\t") for line in git("diff", "--name-status", PRIOR_REVIEW, CANDIDATE).decode().splitlines()]
    expected_modified = {PREFIX + "execution.py", "reports/hardware/P01_BUILD_REPORT.py"}
    assert {name for status, name in changes if status == "M"} == expected_modified
    assert len(changes) == 9 and sum(status == "A" for status, _ in changes) == 7
    changed_names = {name for _, name in changes}
    for name in previous:
        if name not in changed_names:
            data = git("show", PRIOR_REVIEW + ":" + name)
            assert data == read(ROOT / name)
            unchanged[name] = sha(data)
    assert len(tracked) == 183 and len(previous) == 176 and len(unchanged) == 174
    assert source_without_launch(read(ROOT / PREFIX / "execution.py")) == source_without_launch(
        git("show", PRIOR_REVIEW + ":" + PREFIX + "execution.py")
    )
    validation_path = ROOT / "reports/hardware/P01_FIX_R4_VALIDATION.json"
    validation = load(validation_path)
    worker_records = {}
    for item in validation["commands"]:
        name = item["name"]
        metadata_path, log_path = private / "checks" / (name + ".json"), private / "checks" / (name + ".log")
        assert sha(read(metadata_path)) == item["original_metadata_sha256"]
        metadata = load(metadata_path)
        assert sha(read(log_path)) == item["sha256"] == metadata["sha256"]
        for key in ["command", "head", "exit_code", "started_at", "ended_at"]:
            assert metadata[key] == item[key]
        bundle = metadata["source_sha256"]
        assert sha(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()) == item["recorded_source_bundle_sha256"]
        assert bundle == validation["recorded_source_bundles"][item["recorded_source_bundle_sha256"]]
        binding = PRIOR_REVIEW if name == "before-init" else IMPLEMENTATION
        for path, digest in bundle.items():
            assert sha(git("show", binding + ":" + path)) == digest
        worker_records[name] = {"exit_code": item["exit_code"], "log_sha256": item["sha256"],
            "metadata_sha256": item["original_metadata_sha256"], "source_bytes_bound_to": binding}
    proof_hashes = {}
    for name, digest in validation["proof_files_sha256"].items():
        assert sha(read(worker / name)) == digest
        if not name.startswith(".toolalign-local/"):
            assert read(worker / name) == read(ROOT / name)
        proof_hashes[name] = digest
    for name, digest in validation["private_outputs_sha256"].items():
        assert sha(read(private / name)) == digest
    package = load(private / "package-check/evidence.json")
    assert package == validation["new_package"]
    install_log_hashes = {}
    for item in package["commands"]:
        assert item["exit_code"] == 0
        for stream in ["stdout", "stderr"]:
            name = item["name"] + "." + stream
            assert sha(read(private / "package-check" / name)) == item[stream + "_sha256"]
            install_log_hashes[name] = item[stream + "_sha256"]
    for key, filename in [("sdist", "toolalign-0.0.1.tar.gz"), ("wheel_from_sdist", "toolalign-0.0.1-py3-none-any.whl")]:
        assert sha(read(private / "build" / filename)) == package["archives"][key]["sha256"]
    spec = importlib.util.spec_from_file_location("r1_r3_actual_report", ROOT / "reports/hardware/P01_BUILD_REPORT.py")
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    examples = []
    for index, expected in enumerate(validation["initialization_before_after"]):
        stages = {}
        for label, directory in [("before", "before-init"), ("after", "final-r1")]:
            attempt = private / directory / ("test_initialization_failure_le" + str(index))
            observation = load(attempt / "initialization-observation.json")
            assert observation == expected[label]
            assert sha(read(attempt / "initialization-observation.json")) == expected[label + "_sha256"]
            config = load(attempt / "request.json")
            run = Path(config["output_dir"])
            assert run.resolve().is_relative_to(attempt.resolve())
            assert load(run / "config.json") == config
            manifest = load(run / "run.json")
            records = report.summarize(run.parent)["runs"]
            if label == "before":
                assert manifest["status"] == "running" and manifest["ended_at"] is None
                assert not (run / "resources.json").exists() and records == []
            else:
                assert sha(read(run / "run.json")) == expected["manifest_sha256"]
                assert sha(read(run / "resources.json")) == expected["resources_sha256"]
                resources = load(run / "resources.json")
                assert {k: resources[k] for k in expected["resource_fields"]} == expected["resource_fields"]
                assert manifest["status"] == "failed" and manifest["ended_at"]
                assert manifest["training_tokens"] == manifest["optimizer_steps"] == 0
                assert len(records) == 1 and records[0]["assessment"] == "FAILED_INITIALIZATION"
                assert records[0]["raw_process_exit_code"] is None
            stages[label] = {"observation": observation, "summary": records,
                "files_sha256": {p.name: sha(read(p)) for p in run.iterdir() if p.is_file()}}
        examples.append(stages)
    old_evidence_path = ROOT / "reports/review/P01-r2/evidence.json"
    old_evidence = load(old_evidence_path)
    assert sha(read(old_evidence_path)) == "e1abbf4c4f149a527774fe761da3e5bebd653ef4cade899ff72fdaaf54e59dac"
    prior_private_path = ROOT / ".toolalign-local/review-p01-r2/preserved-evidence.json"
    assert sha(read(prior_private_path)) == old_evidence["private_artifact_hashes"]["preserved-evidence.json"]
    prior_private = load(prior_private_path)
    math_log = next(c for c in old_evidence["commands"] if c["name"] == "independent-cpu-math")
    assert sha(read(ROOT / ".toolalign-local/review-p01-r2/logs" / math_log["log"])) == math_log["sha256"]
    assert old_evidence["independent_cpu_math"] == validation["preservation"]["prior_independent_math"]
    summary_path = ROOT / "reports/hardware/P01_RESULTS.json"
    assert sha(read(summary_path)) == validation["preservation"]["historical_summary_sha256"]
    assert read(summary_path) == git("show", PRIOR_REVIEW + ":reports/hardware/P01_RESULTS.json")
    old_runs = {r["run_id"]: r for r in prior_private["history"]["runs"]}
    historical = []
    for item in validation["preservation"]["historical_run_identity_files"]:
        old = old_runs[item["run_id"]]
        assert item["files_sha256"] == old["raw_evidence_hashes_unchanged"]
        root = worker / ".toolalign-local/runs" / item["run_id"].removeprefix("p01-")
        for name, digest in item["files_sha256"].items():
            assert Path(name).name == name
            assert sha(read(root / name)) == digest
        config = load(root / "config.json")
        assert config["source_hash"] == item["source_hash"]
        historical.append({"run_id": item["run_id"], "assessment_preserved": old["assessment"],
            "source_hash": item["source_hash"], "identity_files_sha256": item["files_sha256"]})
    mapping = prior_private["source_mapping"]["math_r2_mapping"]
    for name, identity in mapping["source_files"].items():
        assert sha(git("show", mapping["resolved_source_commit"] + ":" + PREFIX + name)) == identity["recorded_worktree_sha256"]
    assert len(historical) == 10 and sum(len(r["identity_files_sha256"]) for r in historical) == 92
    assert prior_private["history"]["manifest_artifacts_rehashed"] == 185
    out = {
        "status": "PASS: evidence binding", "candidate": CANDIDATE, "candidate_tracked_files": len(tracked),
        "candidate_tree": git("rev-parse", CANDIDATE + "^{tree}").decode().strip(),
        "original_review": PRIOR_REVIEW, "original_review_merge": MERGE, "merge_parents": parents,
        "implementation_commit": IMPLEMENTATION, "changes_from_original_review": changes,
        "production_base_diff": git("diff", "--name-status", "37c00de9abe92e6fb24a0c0e0b7361aa4bb90385", CANDIDATE).decode().splitlines(),
        "unchanged_original_files": len(unchanged), "unchanged_original_file_map_sha256": sha(json.dumps(unchanged, sort_keys=True).encode()),
        "execution_outside_launch_unchanged": True,
        "seven_unchanged_modules": [name for name in unchanged if name.startswith(PREFIX)],
        "worker_validation_sha256": sha(read(validation_path)), "worker_commands": worker_records,
        "worker_proof_files_sha256": proof_hashes, "worker_private_outputs_sha256": validation["private_outputs_sha256"],
        "worker_install_stdout_stderr_sha256": install_log_hashes, "worker_initialization_before_after": examples,
        "historical_runs": historical, "historical_identity_files_rehashed": 92,
        "prior_independent_review_evidence_sha256": sha(read(old_evidence_path)),
        "prior_private_evidence_sha256": sha(read(prior_private_path)), "historical_summary_sha256": sha(read(summary_path)),
        "math_source_mapping": mapping, "prior_independent_math": old_evidence["independent_cpu_math"],
        "prior_independent_math_log_sha256": math_log["sha256"],
        "math_this_round": "NOT_RERUN; prior 17 cases bound to unchanged source",
        "historical_payloads": "185 previously independently rehashed; full payload rehash NOT_RERUN",
        "model_or_tokenizer_import": False, "model_or_gpu_reexecution": "NOT_RUN",
    }
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": out["status"], "candidate": CANDIDATE,
        "current_candidate_files_verified": len(tracked), "unchanged_original_files": len(unchanged),
        "worker_command_logs_and_metadata": len(worker_records), "historical_identity_files": 92,
        "evidence_sha256": sha(read(args.output))}))


if __name__ == "__main__":
    main()
