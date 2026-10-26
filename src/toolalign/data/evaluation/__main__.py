"""Build, exercise and measure private G5 inputs using CPU and an offline tokenizer."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError, file_hash, private_directory, read_json, write_json
from toolalign.data.preferences.audit import p02_metadata
from toolalign.data.preferences.tasks import validate_tasks as validate_g4_tasks
from toolalign.model_io.offline import OfflineQwenTokenizer, model_modules_loaded

from .audit import audit_groups
from .checks import check_scripts, measure_lengths
from .replay import build_replay
from .tasks import REVISION, prepare_tasks, retain_tasks, validate_tasks


def coverage(bundle, authoring):
    tasks = bundle["tasks"]
    return {"authored_tasks": len(authoring), "retained_tasks": len(tasks),
            "quarantined_tasks": len(authoring) - len(tasks),
            "families": len({t["family_id"] for t in tasks}),
            "groups": len({t["group_id"] for t in tasks}),
            "categories": dict(Counter(t["category"] for t in tasks)),
            "domains": dict(Counter(authoring[t["task_id"]]["domain"] for t in tasks)),
            "recovery_tasks": len(bundle["recovery_task_ids"]),
            "task_list_hash": canonical_hash(bundle),
            "real_model_evaluation": "NOT_RUN", "independent_Q1_review": "PENDING"}


def save_package(root, files, inputs):
    for name, value in files.items():
        write_json(root / name, value)
    write_json(root / "manifest.json", {
        "schema_version": "toolalign.evaluation-package.v1", "revision": REVISION,
        "inputs": inputs, "artifacts": {name: file_hash(root / name) for name in files},
    })


def load_package(root):
    root = Path(root)
    manifest = read_json(root / "manifest.json")
    values = {}
    for name in ("tasks.json", "authoring.json", "group-audit.json", "semantic-review.json"):
        if file_hash(root / name) != manifest["artifacts"][name]:
            raise DataError("evaluation_package_hash_mismatch")
        values[name] = read_json(root / name)
    validate_tasks(values["tasks.json"])
    return values


def build_package(authoring_path, p02_manifest, development_path, g4_path, semantic_path, output):
    root = private_directory(output, empty=True)
    authored = read_json(authoring_path)
    if (authored.get("schema_version") != "toolalign.evaluation-authoring.v1"
            or authored.get("purpose") != "heldout-cpu-authoring"):
        raise DataError("evaluation_authoring_identity")
    bundle, authoring = prepare_tasks(authored["cases"])
    p02, provenance = p02_metadata(p02_manifest)
    development = read_json(development_path)
    if development.get("purpose") != "public-original-development":
        raise DataError("not_public_development")
    g4 = validate_g4_tasks(read_json(g4_path))
    semantic = read_json(semantic_path)
    bundle, audit = audit_groups(bundle, p02, development["cases"], g4,
                                 semantic_links=semantic["links"])
    summary = coverage(bundle, authoring)
    save_package(root, {"tasks.json": bundle, "authoring.json": authoring,
                        "group-audit.json": audit, "semantic-review.json": semantic,
                        "summary.json": summary}, {
                            "authoring_sha256": file_hash(authoring_path), "p02": provenance,
                            "development_sha256": file_hash(development_path),
                            "g4_tasks_sha256": file_hash(g4_path),
                            "semantic_review_sha256": file_hash(semantic_path),
                        })
    return summary


def finalize_package(package, checks_root, tokenizer, output):
    root = private_directory(output, empty=True)
    files = load_package(package)
    lengths = measure_lengths(files["tasks.json"], checks_root, tokenizer)
    excluded = set(lengths["quarantined_task_ids"])
    files["tasks.json"] = retain_tasks(files["tasks.json"], {
        t["task_id"] for t in files["tasks.json"]["tasks"] if t["task_id"] not in excluded})
    files["length-audit.json"] = lengths
    summary = files["summary.json"] = coverage(files["tasks.json"], files["authoring.json"])
    summary["length_quarantined_tasks"] = len(excluded)
    summary["maximum_input_tokens_before_quarantine"] = lengths["maximum_input_tokens"]
    save_package(root, files, {"package_manifest_sha256": file_hash(Path(package) / "manifest.json"),
                               "cpu_summary_sha256": file_hash(Path(checks_root) / "summary.json")})
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    for name in ("authoring", "p02-manifest", "development", "g4-tasks", "semantic-review", "output"):
        build.add_argument("--" + name, type=Path, required=True)
    check = commands.add_parser("validate-cpu")
    for name in ("package", "output"):
        check.add_argument("--" + name, type=Path, required=True)
    finalize = commands.add_parser("finalize-lengths")
    for name in ("package", "checks", "tokenizer-root", "output"):
        finalize.add_argument("--" + name, type=Path, required=True)
    replay = commands.add_parser("replay")
    for name in ("development", "pairs", "tokenizer-root", "output"):
        replay.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        summary = build_package(args.authoring, args.p02_manifest, args.development,
                                args.g4_tasks, args.semantic_review, args.output)
    elif args.command == "validate-cpu":
        files = load_package(args.package)
        root = private_directory(args.output, empty=True)
        result = check_scripts(files["tasks.json"], files["authoring.json"], root)
        summary = {"pass": result["pass"], "checks": len(result["checks"]),
                   "real_model_evaluation": "NOT_RUN"}
        print(summary)
        return 0 if result["pass"] else 1
    else:
        tokenizer = OfflineQwenTokenizer(args.tokenizer_root, repo_id="Qwen/Qwen3-1.7B",
                                         revision="70d244cc86ccca08cf5af4e1e306ecf908b1ad5e")
        if args.command == "finalize-lengths":
            summary = finalize_package(args.package, args.checks, tokenizer, args.output)
        else:
            root = private_directory(args.output, empty=True)
            value, provenance = build_replay(read_json(args.development), read_json(args.pairs), tokenizer)
            provenance["development_sha256"] = file_hash(args.development)
            provenance["pairs_sha256"] = file_hash(args.pairs)
            write_json(root / "inputs.json", value)
            write_json(root / "provenance.json", provenance)
            summary = {"sequences": len(value["sequences"]), "requests": len(provenance["rows"]),
                       "maximum_input_tokens": max(r["input_tokens"] for r in provenance["rows"]),
                       "model_calls": 0}
        if model_modules_loaded():
            raise DataError("tokenizer_only_process_required")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
