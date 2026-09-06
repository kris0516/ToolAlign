"""Reproduce CPU-only review measurements and compare private full-array evidence."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import encoded, file_hash, read_json
from toolalign.data.training_review import choose_review_cases, write_measurement
from toolalign.data.training_selection import load_config, read_rows, verify


def measure(args):
    for name in ("USE_TORCH", "USE_TF", "USE_FLAX"):
        assert os.environ.get(name) == "0", name
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        assert os.environ.get(name) == "1", name
    from toolalign.model_io.offline import OfflineQwenTokenizer, model_modules_loaded

    assert model_modules_loaded() == []
    inputs = read_json(args.inputs)
    fixed = load_config(inputs["config_path"])
    selection = Path(args.selection).resolve()
    verified = verify(output=selection, **inputs)
    plan = {profile: {"train": {
        "examples": list(read_rows(selection / profile / "train.examples.jsonl")),
        "sidecars": list(read_rows(selection / profile / "train.sidecars.jsonl"))}}
        for profile in ("smoke", "formal")}
    cases, coverage = choose_review_cases(plan, read_json(args.fixtures))
    adapters = {profile: OfflineQwenTokenizer(args.tokenizer_root, engine=args.engine,
        repo_id=config["model_id"], revision=config["model_revision"])
        for profile, config in fixed["profiles"].items()}
    measured = write_measurement(cases, coverage, tokenizers_by_profile=adapters, output=args.output)
    assert model_modules_loaded() == []
    result = {"status": "PASS", "engine": args.engine, "model_modules_loaded": [],
        "selection_manifest_sha256": file_hash(selection / "manifest.json"),
        "selection_canonical_sha256": canonical_hash(verified),
        "measurement_manifest_sha256": file_hash(Path(args.output) / "manifest.json"),
        "fixture_file_sha256": file_hash(args.fixtures), "coverage": coverage,
        "tokenizers": measured["tokenizers"], "full_encodings": len(cases), "independent_examples": 13}
    with (Path(args.output) / "measurement.json").open("xb") as stream:
        stream.write(encoded(result) + b"\n")
    print(json.dumps(result, ensure_ascii=False))


def checked_measurement(root, engine):
    root = Path(root).resolve()
    manifest = read_json(root / "manifest.json")
    expected_names = {f"actual-{i:02d}" for i in range(1, 11)} | {
        "protocol-final", "protocol-clarify", "protocol-refuse"}
    assert set(manifest["artifacts"]) == {n + ext for n in expected_names for ext in (".json", ".html")} | {"review.csv"}
    for name, info in manifest["artifacts"].items():
        path = root / name
        assert path.resolve().is_relative_to(root) and not path.is_symlink()
        assert file_hash(path) == info["sha256"] and path.stat().st_size == info["size_bytes"]
    assert all(t["engine"] == engine for t in manifest["tokenizers"].values())
    records = [read_json(root / (name + ".json")) for name in sorted(expected_names)]
    assert canonical_hash(records) == manifest["records_sha256"]
    assert len(records) == len({r["case"]["example"]["example_id"] for r in records}) == 13
    import csv
    with (root / "review.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 13 and all(not row[k] for row in rows for k in ("reviewer", "verdict", "reviewed_at_utc", "notes"))
    return manifest, records


def compare(args):
    reference, reference_rows = checked_measurement(args.reference, "transformers")
    native, native_rows = checked_measurement(args.native, "tokenizers")
    assert reference_rows == native_rows
    assert reference["coverage"] == native["coverage"]
    assert reference["consumer"]["package_files"] == native["consumer"]["package_files"]
    for profile in ("smoke", "formal"):
        left, right = reference["tokenizers"][profile], native["tokenizers"][profile]
        for key in ("repo_id", "revision", "files", "template_sha256", "eos_token", "eos_token_id",
                    "render_parameters", "encoding_parameters"):
            assert left[key] == right[key]
    actual = [r for r in reference_rows if r["case"]["category"] == "actual_selected_train"]
    assert len(actual) == 10 and {r["case"]["example"]["expected_action"]["kind"] for r in actual} == {"tool_calls"}
    result = {"status": "PASS", "independent_examples": 13, "actual_selected_train": 10,
        "protocol_only": 3, "engine_measurements": 26, "full_record_equality": True,
        "historical_audit_match_actual_examples": 10, "coverage": reference["coverage"],
        "actual_total_token_range": [min(r["sequence"]["total_tokens"] for r in actual), max(r["sequence"]["total_tokens"] for r in actual)],
        "actual_padding_buckets": dict(Counter(str(r["padding"]["bucket"]) for r in actual)),
        "reference_manifest_sha256": file_hash(Path(args.reference) / "manifest.json"),
        "native_manifest_sha256": file_hash(Path(args.native) / "manifest.json"),
        "records_canonical_sha256": reference["records_sha256"], "human_review": "PENDING",
        "trainer_collator_mask_loss": "NOT_RUN", "training_authorized": False}
    with Path(args.output).open("xb") as stream:
        stream.write(encoded(result) + b"\n")
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("measure")
    for name in ("inputs", "selection", "tokenizer-root", "fixtures", "output"):
        command.add_argument("--" + name, required=True, type=Path)
    command.add_argument("--engine", required=True, choices=("transformers", "tokenizers"))
    command = sub.add_parser("compare")
    for name in ("reference", "native", "output"):
        command.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    {"measure": measure, "compare": compare}[args.command](args)


if __name__ == "__main__":
    main()
