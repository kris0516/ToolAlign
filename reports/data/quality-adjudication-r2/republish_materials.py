"""Republish fixed measured bytes after metadata-only verifier/count corrections.

No tokenizer is imported or called. Both original measurements and the original
freeze remain intact. Explicit hashes pin old manifests; Git binds the exact
original producer files, while new manifests name the static publication source.
"""

import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

from toolalign.data import quality_adjudication as a
from toolalign.data import quality_adjudication_materials as m
from toolalign.data import quality_revision as q
from toolalign.data.common import encoded, loads


def original_bundle(root, expected_sha256, source_bytes_commit):
    root = Path(root)
    q.require(not root.is_symlink() and not any(p.is_symlink() for p in root.rglob("*")), "original_output_symlink")
    manifest_data = q.pinned(root / "manifest.json", expected_sha256)
    manifest = loads(manifest_data.decode())
    names = set(manifest["artifacts"])
    q.require({p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == names | {"run.json", "manifest.json"},
              "original_output_members")
    buffers = q.checked_bundle(root, manifest["artifacts"], names)
    buffers["manifest.json"] = manifest_data
    run = loads((root / "run.json").read_text())
    a.same(run["stable_manifest_sha256"], expected_sha256, "original_manifest_run_binding")
    q.require(run["training_authorized"] is False and run["model_modules_loaded"] == [], "original_run_scope")
    identity = run["consumer"]
    if "consumer" in manifest:
        a.same(identity, manifest["consumer"], "original_consumer_run_binding")
    for name, expected in identity["package_files"].items():
        q.require(".." not in Path(name).parts and not Path(name).is_absolute(), "original_source_member")
        data = subprocess.check_output(["git", "show", source_bytes_commit + ":src/toolalign/" + name])
        a.same(q.sha(data), expected, "original_git_source_binding")
    return buffers, manifest, run


def republish(args):
    q.require(re.fullmatch(r"[0-9a-f]{40}", args.original_source_bytes_commit) is not None, "original_commit_format")
    q.require(subprocess.check_output(["git", "cat-file", "-t", args.original_source_bytes_commit]).strip() == b"commit",
              "original_commit_type")
    a.cpu_only()
    paths = loads(Path(args.inputs).read_text())
    inputs = a.bound_inputs(**paths)
    artifacts, revision = a.stable_artifacts(inputs)
    a.verify_artifacts(args.revision, artifacts)
    frozen, selection, cases, coverage = m.freeze_artifacts(inputs, artifacts, revision)
    old_frozen, _, _ = original_bundle(args.original_frozen, args.original_frozen_sha256, args.original_source_bytes_commit)
    # The count correction must not change even one selected identity or case byte.
    for name in ("cases.json", "coverage.json"):
        q.require(old_frozen[name] == frozen[name], "static_republication_changed_case")
    old_revision, _, _ = original_bundle(args.original_revision, args.original_revision_sha256, args.original_source_bytes_commit)
    q.require(set(old_revision) == set(artifacts), "static_republication_changed_dataset_members")
    for name in artifacts:
        if name != "manifest.json":
            q.require(artifacts[name] == old_revision[name], "static_republication_changed_dataset_bytes")
    q.publish(args.frozen, frozen, m.run_record(args.frozen, frozen["manifest.json"]))
    expected = m.expected_tokenizer_bindings(inputs)
    proof = {"status": "PASS_STATIC_REPUBLICATION", "actual_new_tokenizer_calls": 0,
        "unique_fixed_cases": 13, "original_source_bytes_commit": args.original_source_bytes_commit,
        "source_commit_is_byte_equivalence_not_an_execution_time_claim": True,
        "original_revision_manifest_sha256": args.original_revision_sha256,
        "new_revision_manifest_sha256": q.sha(artifacts["manifest.json"]),
        "all_dataset_payload_files_unchanged": len(artifacts) - 1,
        "original_frozen_manifest_sha256": args.original_frozen_sha256,
        "new_frozen_manifest_sha256": q.sha(frozen["manifest.json"]), "cases_and_coverage_bytes_unchanged": True,
        "measurements": {}, "training_authorized": False}
    for engine in ("tokenizers", "transformers"):
        suffix = "native" if engine == "tokenizers" else "reference"
        old_root, new_root = getattr(args, "original_" + suffix), getattr(args, suffix)
        old_sha = getattr(args, "original_" + suffix + "_sha256")
        buffers, old_manifest, run = original_bundle(old_root, old_sha, args.original_source_bytes_commit)
        a.same(old_manifest["quality_revision_sha256"], revision["quality_revision_sha256"], "original_material_revision")
        a.same(old_manifest["coverage"], coverage, "original_material_coverage")
        a.same(old_manifest["case_order"], selection["case_order"], "original_material_case_order")
        a.same(old_manifest["frozen_selection_manifest_file_sha256"], args.original_frozen_sha256, "original_material_freeze")
        for profile in q.PROFILES:
            q.require(old_manifest["tokenizers"][profile]["engine"] == engine, "original_material_engine")
            a.same({k: old_manifest["tokenizers"][profile][k] for k in m.TOKENIZER_IDENTITY_KEYS}, expected[profile],
                   "original_material_tokenizer_binding")
        records = [loads(buffers[c["case_id"] + ".json"].decode()) for c in cases]
        for record, case in zip(records, cases, strict=True):
            m.checked_record(record, case)
        a.same(old_manifest["records_sha256"], q.canonical_hash(records), "original_material_record_hash")
        generated = m.review_artifacts(records)
        q.require(set(generated) == set(old_manifest["artifacts"]), "original_material_payload_set")
        for name, data in generated.items():
            q.require(data == buffers[name], "static_republication_changed_array_or_html")
        new_manifest = copy.deepcopy(old_manifest)
        new_manifest["consumer"] = m.consumer_identity()
        new_manifest["frozen_selection_manifest_file_sha256"] = q.sha(frozen["manifest.json"])
        new_manifest["original_encoding"] = {"manifest_file_sha256": old_sha,
            "run_file_sha256": q.sha((Path(old_root) / "run.json").read_bytes()),
            "actual_original_created_at_utc": run["created_at_utc"], "consumer": run["consumer"],
            "source_bytes_commit": args.original_source_bytes_commit,
            "source_commit_is_byte_equivalence_not_an_execution_time_claim": True}
        new_manifest["static_republication"] = {"actual_new_tokenizer_calls": 0, "all_material_payload_files_byte_identical": True,
            "purpose": "bind_corrected_dataset_metadata_and_stricter_verifier_without_reencoding"}
        generated["manifest.json"] = encoded(new_manifest) + b"\n"
        q.publish(new_root, generated, m.run_record(new_root, generated["manifest.json"]))
        m.checked_measurement(new_root, engine, cases, coverage, frozen, expected_tokenizers=expected)
        proof["measurements"][engine] = {"original_manifest_sha256": old_sha,
            "new_manifest_sha256": q.sha(generated["manifest.json"]), "payload_files_reused_without_encoding": len(generated) - 1,
            "full_records_sha256": old_manifest["records_sha256"], "actual_original_created_at_utc": run["created_at_utc"],
            "original_consumer": run["consumer"], "current_static_publisher": m.consumer_identity()}
    a.cpu_only()
    with Path(args.output).open("x") as stream:
        json.dump(proof, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in proof.items() if k != "measurements"}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("inputs", "revision", "frozen", "native", "reference", "original-revision", "original-frozen",
                 "original-native", "original-reference", "output"):
        parser.add_argument("--" + flag, required=True, type=Path)
    for flag in ("original-source-bytes-commit", "original-revision-sha256", "original-frozen-sha256", "original-native-sha256",
                 "original-reference-sha256"):
        parser.add_argument("--" + flag, required=True)
    republish(parser.parse_args())
