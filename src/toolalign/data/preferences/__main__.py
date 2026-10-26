"""Private G4 task preparation, CPU authoring checks, extraction and Q1 materials."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import (
    DataError,
    file_hash,
    private_directory,
    read_json,
    write_json,
    write_jsonl,
)

from .audit import audit_groups, jsonl, p02_metadata
from .extract import extract_preferences, validate_authoring
from .review import apply_review, freeze_review, review_html
from .synthetic import authoring_validation
from .tasks import REVISION, prepare_tasks, read_authoring, validate_tasks


def build_package(authoring_input, p02_manifest, development, output):
    root = private_directory(output, empty=True)
    bundle, authoring = prepare_tasks(read_authoring(authoring_input))
    metadata, provenance = p02_metadata(p02_manifest)
    dev = read_json(development)
    if dev.get("purpose") != "public-original-development":
        raise DataError("not_public_development")
    bundle, audit = audit_groups(bundle, metadata, dev["cases"])
    validate_tasks(bundle)
    validate_authoring(bundle, authoring)
    summary = {"generator_revision": REVISION, "authored_tasks": len(authoring),
               "retained_tasks": len(bundle["tasks"]),
               "quarantined_tasks": len(authoring) - len(bundle["tasks"]),
               "sources": dict(Counter(t["example"]["source"] for t in bundle["tasks"])),
               "families": len({t["family_id"] for t in bundle["tasks"]}),
               "groups": len({t["group_id"] for t in bundle["tasks"]}),
               "categories": dict(Counter(t["category"] for t in bundle["tasks"])),
               "development_tasks": len(dev["cases"]), "real_model_candidates": 0,
               "formal_preference_quality": "NOT_RUN", "task_list_hash": canonical_hash(bundle)}
    files = {"tasks.json": bundle, "authoring.json": authoring,
             "group-audit.json": audit, "summary.json": summary}
    for name, value in files.items():
        write_json(root / name, value)
    manifest = {"schema_version": "toolalign.preference-package.v1", "generator_revision": REVISION,
                "authoring_input_sha256": file_hash(authoring_input),
                "p02": provenance, "development_sha256": file_hash(development),
                "task_list_hash": canonical_hash(bundle),
                "artifacts": {name: file_hash(root / name) for name in files}}
    write_json(root / "manifest.json", manifest)
    return summary


def load_package(root):
    root = Path(root)
    manifest = read_json(root / "manifest.json")
    for name in ("tasks.json", "authoring.json", "group-audit.json", "summary.json"):
        if file_hash(root / name) != manifest["artifacts"][name]:
            raise DataError("package_hash_mismatch")
    bundle = read_json(root / "tasks.json")
    authoring = read_json(root / "authoring.json")
    validate_tasks(bundle)
    validate_authoring(bundle, authoring)
    audit = read_json(root / "group-audit.json")
    kept = {d["task_id"]: d for d in audit["dispositions"] if d["status"] == "train"}
    if (manifest["task_list_hash"] != canonical_hash(bundle)
            or {t["task_id"] for t in bundle["tasks"]} != set(kept)
            or any(t["group_id"] != kept[t["task_id"]]["group_id"] for t in bundle["tasks"])):
        raise DataError("package_group_binding")
    return bundle, authoring


def write_extraction(output, result):
    root = private_directory(output, empty=True)
    for name in ("preferences", "lineage", "dispositions"):
        write_jsonl(root / f"{name}.jsonl", result[name])
    write_json(root / "summary.json", result["summary"])
    packet = freeze_review(result["preferences"], result["lineage"], synthetic=result["summary"]["synthetic"])
    write_json(root / "q1-sample.json", packet)
    (root / "q1-review.html").write_text(review_html(packet, result["preferences"], result["lineage"]), encoding="utf-8")
    write_json(root / "manifest.json", {"schema_version": "toolalign.preference-extraction-files.v1",
                                        "artifacts": {p.name: file_hash(p) for p in sorted(root.iterdir()) if p.is_file()}})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--authoring", type=Path, required=True)
    build.add_argument("--p02-manifest", type=Path, required=True)
    build.add_argument("--development", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("validate-cpu")
    check.add_argument("--package", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    extract = commands.add_parser("extract")
    extract.add_argument("--package", type=Path, required=True)
    extract.add_argument("--plan", type=Path, required=True)
    extract.add_argument("--candidates", type=Path, required=True)
    extract.add_argument("--output", type=Path, required=True)
    review = commands.add_parser("apply-review")
    review.add_argument("--extraction", type=Path, required=True)
    review.add_argument("--review", type=Path, required=True)
    review.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        summary = build_package(args.authoring, args.p02_manifest, args.development, args.output)
    elif args.command == "validate-cpu":
        bundle, authoring = load_package(args.package)
        root = private_directory(args.output, empty=True)
        plan, candidates, summary = authoring_validation(bundle, authoring, root / "runs")
        write_json(root / "plan.json", plan)
        write_jsonl(root / "candidates.jsonl", candidates)
        result = extract_preferences(bundle, authoring, plan, candidates)
        write_extraction(root / "extraction", result)
        write_json(root / "summary.json", summary)
        print({"pass": summary["pass"], "synthetic_checks": len(summary["checks"]),
               "real_model_candidates": 0, "extracted_synthetic_pairs": len(result["preferences"])})
        return 0 if summary["pass"] else 1
    elif args.command == "extract":
        bundle, authoring = load_package(args.package)
        result = extract_preferences(bundle, authoring, read_json(args.plan), jsonl(args.candidates))
        write_extraction(args.output, result)
        summary = result["summary"]
    else:
        root = args.extraction
        summary = apply_review(read_json(root / "q1-sample.json"), list(jsonl(root / "preferences.jsonl")),
                               list(jsonl(root / "lineage.jsonl")), read_json(args.review))
        output = private_directory(args.output, empty=True)
        training = summary.pop("training_preferences")
        summary.pop("remaining_preferences")
        write_jsonl(output / "training-preferences.jsonl", training)
        write_json(output / "review-result.json", summary)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
