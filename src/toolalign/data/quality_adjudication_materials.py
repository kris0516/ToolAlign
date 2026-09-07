"""Freeze and measure thirteen v2 review cases through the existing CPU engines.

Formatting, encoding, masks, padding and static HTML use the verified shared
kernels. This wrapper binds the new dataset and keeps AI judgment columns empty.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash
from toolalign.model_io.format import ModelIOError
from toolalign.model_io.sequence import Sequence

from . import quality_adjudication as a
from . import quality_materials as qm
from . import quality_revision as q
from .common import DataError, encoded, loads
from .training_review import choose_review_cases

CASE_NAMES = {f"effective-{i:02d}" for i in range(1, 11)} | {"protocol-" + k for k in ("final", "clarify", "refuse")}
CSV_FIELDS = ("case_id", "category", "example_id", "example_sha256", "quality_revision_sha256",
              "reviewer", "semantic_verdict", "token_mask_verdict", "reviewed_at_utc", "notes")
TOKENIZER_IDENTITY_KEYS = ("repo_id", "revision", "files", "template_sha256", "eos_token", "eos_token_id",
                           "render_parameters", "encoding_parameters")


def consumer_identity():
    identity = qm.consumer_identity()
    for name in ("data/quality_adjudication.py", "data/quality_adjudication_materials.py"):
        identity["package_files"][name] = q.sha(files("toolalign").joinpath(name).read_bytes())
    return identity


def choose_cases(inputs, artifacts, manifest):
    plan = {p: {"train": {k: q.jsonl(artifacts[f"selection/{p}/train.{k}.jsonl"])[0]
                          for k in ("examples", "sidecars")}} for p in q.PROFILES}
    protocols = {k: a.document(inputs["buffers"], "protocol/protocol-" + k + ".json")
                 for k in ("final", "clarify", "refuse")}
    cases, coverage = choose_review_cases(plan, [r["case"]["example"] for r in protocols.values()])
    for case in cases:
        ident = case["example"]["example_id"]
        case.update(quality_revision_sha256=manifest["quality_revision_sha256"], semantic_verdict=None,
                    token_mask_verdict=None, reviewer=None)
        if case["category"] == "actual_selected_train":
            source = inputs["sources"].get(case["example"]["source_record_hash"])
            q.require(source is None or source["disposition"] == "restore_original_source", "excluded_review_example")
            case["category"] = "effective_selected_train"
            case["case_id"] = case["case_id"].replace("actual-", "effective-")
            case["original_jsonl_line_sha256"] = q.sha(inputs["original_bytes"][ident])
            case["original_lineage_sha256"] = canonical_hash(inputs["index"]["lineage"][ident])
            for profile, info in case["profiles"].items():
                sidecar = next(r for r in plan[profile]["train"]["sidecars"] if r["audit"]["example_id"] == ident)
                a.same(case["audit"], sidecar["audit"], "case_profile_audit_type")
                info["parent_selection_rank"] = sidecar["parent_selection_rank"]
        else:
            case["enters_effective_training"] = False
            original = protocols[case["example"]["expected_action"]["kind"]]
            # The original protocol arrays are frozen references, with no new encoding here.
            case["original_protocol_sequence"] = original["sequence"]
    a.same({c["case_id"] for c in cases} == CASE_NAMES, True, "case_identity_set")
    q.require(len(cases) == len({c["example"]["example_id"] for c in cases}) == 13, "fixed_material_count")
    coverage.pop("human_review", None)
    coverage.update(quality_revision_sha256=manifest["quality_revision_sha256"],
                    semantic_review="UNFILLED_FOR_INDEPENDENT_AI_REVIEW", browser_actual_observation="NOT_RUN",
                    new_annotations_enter_training=False, existing_staging_reencoded=False)
    return cases, coverage


def freeze_artifacts(inputs, revision_artifacts, revision_manifest):
    cases, coverage = choose_cases(inputs, revision_artifacts, revision_manifest)
    artifacts = {"cases.json": encoded(cases) + b"\n", "coverage.json": encoded(coverage) + b"\n"}
    manifest = {"manifest_version": "toolalign.quality-adjudication-material-selection.v2", "training_authorized": False,
        "quality_config_file_sha256": a.CONFIG_SHA256, "quality_revision_sha256": revision_manifest["quality_revision_sha256"],
        "revision_manifest_file_sha256": q.sha(revision_artifacts["manifest.json"]),
        "case_order": [c["case_id"] for c in cases], "unique_examples": 13, "new_tokenization_runs": 0,
        "artifacts": {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in artifacts.items()}}
    artifacts["manifest.json"] = encoded(manifest) + b"\n"
    return artifacts, manifest, cases, coverage


def run_record(output, manifest_data):
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "consumer": consumer_identity(),
            "stable_manifest_sha256": q.sha(manifest_data), "model_modules_loaded": [],
            "training_authorized": False, "output_path": str(Path(output).resolve())}


def freeze(*, config_path, input_root, revision, output):
    a.cpu_only()
    inputs = a.bound_inputs(config_path=config_path, input_root=input_root)
    artifacts, manifest = a.stable_artifacts(inputs)
    a.verify_artifacts(revision, artifacts)
    frozen, selection, _, _ = freeze_artifacts(inputs, artifacts, manifest)
    a.cpu_only()
    q.publish(output, frozen, run_record(output, frozen["manifest.json"]))
    return selection


def typed_sequence_record(case, sequence):
    for key in ("prompt_ids", "concatenated_ids", "sequence_ids", "loss_mask"):
        value = getattr(sequence, key)
        q.require(type(value) is tuple and value and all(type(i) is int and i >= 0 for i in value),
                  "material_array_integer_type")
    q.require(type(sequence.eos_token_id) is int, "material_eos_integer_type")
    for profile in case["profiles"].values():
        q.require(type(profile["padding_bucket"]) is int, "material_padding_integer_type")
    record = qm.sequence_record(case, sequence)
    if case["category"] == "effective_selected_train":
        measured = sequence.metadata() | {k: record["sequence"][k]
                    for k in ("causal_input_ids_sha256", "causal_target_ids_sha256")}
        a.same({k: case["audit"].get(k) for k in measured}, measured, "historical_metadata_type_or_identity")
    else:
        a.same(record["sequence"], case["original_protocol_sequence"], "original_protocol_sequence_binding")
    return record


def checked_record(record, case):
    a.same(record["case"], case, "material_frozen_case_binding")
    data = record["sequence"]
    sequence = Sequence(prompt_text=data["prompt_text"], completion_text=data["completion_text"],
        prompt_ids=tuple(data["prompt_ids"]), concatenated_ids=tuple(data["concatenated_ids"]),
        sequence_ids=tuple(data["sequence_ids"]), loss_mask=tuple(data["loss_mask"]), eos_token_id=data["eos_token_id"])
    expected = typed_sequence_record(case, sequence)
    a.same({k: v for k, v in record.items() if k != "token_texts"}, expected, "material_complete_record_binding")
    q.require(type(record["token_texts"]) is list and len(record["token_texts"]) == expected["padding"]["bucket"]
              and all(type(t) is str for t in record["token_texts"]), "material_token_texts")


def review_artifacts(records):
    artifacts = {}
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(CSV_FIELDS)
    for record in records:
        case = record["case"]
        checked_record(record, case)
        name = case["case_id"]
        artifacts[name + ".json"] = encoded(record) + b"\n"
        artifacts[name + ".html"] = qm.render_page(record).encode("utf-8")
        writer.writerow((name, case["category"], case["example"]["example_id"], canonical_hash(case["example"]),
                         case["quality_revision_sha256"], "", "", "", "", ""))
    artifacts["review.csv"] = stream.getvalue().encode("utf-8")
    artifacts["index.html"] = ('<!doctype html><html lang="zh"><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; base-uri \'none\'; form-action \'none\'">'
        '<title>ToolAlign v2 质量裁定材料</title><h1>新版有效选择的独立 AI 复核材料</h1>'
        '<p>10 个有效 train 原例和 3 个原创协议例。协议例不进入训练；旧 staging 保持冻结引用。'
        '语义与 token/mask 判定列为空；浏览器实显 NOT_RUN。</p><ul>'
        + "".join(f'<li><a href="{r["case"]["case_id"]}.html">{html.escape(r["case"]["case_id"])}</a></li>' for r in records)
        + '</ul></html>').encode("utf-8")
    return artifacts


def write_measurement(cases, coverage, *, tokenizers_by_profile, output, selection_manifest_data):
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    a.cpu_only()
    q.require(len(cases) == len({c["example"]["example_id"] for c in cases}) == 13
              and {c["case_id"] for c in cases} == CASE_NAMES, "fixed_material_count")
    q.require(set(tokenizers_by_profile) == set(q.PROFILES), "material_tokenizer_profiles")
    identities = {k: v.identity for k, v in tokenizers_by_profile.items()}
    records = []
    for case in cases:
        adapter = tokenizers_by_profile[case["primary_profile"]]
        record = typed_sequence_record(case, adapter.training_sequence(case["example"]))
        record["token_texts"] = [adapter.decode([i], skip_special_tokens=False) for i in record["padding"]["sequence_ids"]]
        q.require(adapter.decode(record["sequence"]["concatenated_ids"][record["sequence"]["prompt_tokens"]:],
                                 skip_special_tokens=False) == record["sequence"]["completion_text"], "material_decoded_action")
        records.append(record)
    artifacts = review_artifacts(records)
    a.cpu_only()
    manifest = {"manifest_version": "toolalign.quality-adjudication-token-review.v2", "coverage": coverage,
        "frozen_selection_manifest_file_sha256": q.sha(selection_manifest_data), "quality_revision_sha256": coverage["quality_revision_sha256"],
        "tokenizers": identities, "consumer": consumer_identity(), "case_order": [c["case_id"] for c in cases],
        "categories": dict(Counter(c["category"] for c in cases)), "unique_examples": 13, "records_sha256": canonical_hash(records),
        "artifacts": {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in artifacts.items()},
        "model_modules_loaded": [], "external_execution": "NOT_RUN", "browser_actual_observation": "NOT_RUN",
        "semantic_review": "UNFILLED_FOR_INDEPENDENT_AI_REVIEW", "trainer_consumption": "NOT_RUN", "training_authorized": False}
    artifacts["manifest.json"] = encoded(manifest) + b"\n"
    q.publish(output, artifacts, run_record(output, artifacts["manifest.json"]))
    return manifest


def bound_selection(*, config_path, input_root, revision, frozen):
    inputs = a.bound_inputs(config_path=config_path, input_root=input_root)
    artifacts, manifest = a.stable_artifacts(inputs)
    a.verify_artifacts(revision, artifacts)
    frozen_artifacts, selection, cases, coverage = freeze_artifacts(inputs, artifacts, manifest)
    a.verify_artifacts(frozen, frozen_artifacts, consumer_identity())
    return inputs, frozen_artifacts, selection, cases, coverage


def measure(*, config_path, input_root, revision, frozen, tokenizer_root, engine, output):
    q.require(all(os.environ.get(n) == "0" for n in ("USE_TORCH", "USE_TF", "USE_FLAX"))
              and all(os.environ.get(n) == "1" for n in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")),
              "offline_cpu_environment_required")
    a.cpu_only()
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    inputs, frozen_artifacts, _, cases, coverage = bound_selection(
        config_path=config_path, input_root=input_root, revision=revision, frozen=frozen)
    from toolalign.model_io.offline import OfflineQwenTokenizer

    adapters = {p: OfflineQwenTokenizer(tokenizer_root, engine=engine, repo_id=spec["model_id"], revision=spec["model_revision"])
                for p, spec in inputs["parent_config"]["profiles"].items()}
    return write_measurement(cases, coverage, tokenizers_by_profile=adapters, output=output,
                             selection_manifest_data=frozen_artifacts["manifest.json"])


def expected_tokenizer_bindings(inputs):
    original = inputs["binding"]["parent_selection_input_binding"]["historical_measurement"]["tokenizer"]
    return {p: {**{k: original[k] for k in TOKENIZER_IDENTITY_KEYS},
                "repo_id": spec["model_id"], "revision": spec["model_revision"]}
            for p, spec in inputs["parent_config"]["profiles"].items()}


def checked_measurement(root, engine, cases, coverage, frozen_artifacts, *, expected_tokenizers):
    root = Path(root)
    manifest_data = (root / "manifest.json").read_bytes()
    manifest = loads(manifest_data.decode())
    q.require(manifest["manifest_version"] == "toolalign.quality-adjudication-token-review.v2"
              and manifest["training_authorized"] is False and manifest["model_modules_loaded"] == []
              and manifest["semantic_review"] == "UNFILLED_FOR_INDEPENDENT_AI_REVIEW"
              and manifest["browser_actual_observation"] == "NOT_RUN"
              and manifest["external_execution"] == "NOT_RUN" and manifest["trainer_consumption"] == "NOT_RUN",
              "measurement_scope")
    a.same(manifest["coverage"], coverage, "measurement_coverage_binding")
    a.same(manifest["quality_revision_sha256"], coverage["quality_revision_sha256"], "measurement_revision_binding")
    a.same(manifest["frozen_selection_manifest_file_sha256"], q.sha(frozen_artifacts["manifest.json"]), "measurement_selection_binding")
    a.same(manifest["case_order"], [c["case_id"] for c in cases], "measurement_case_order")
    q.require(set(manifest["tokenizers"]) == set(q.PROFILES)
              and all(t["engine"] == engine for t in manifest["tokenizers"].values()), "measurement_engine")
    q.require(set(expected_tokenizers) == set(q.PROFILES), "measurement_expected_profiles")
    for profile in q.PROFILES:
        a.same({k: manifest["tokenizers"][profile][k] for k in TOKENIZER_IDENTITY_KEYS}, expected_tokenizers[profile],
               "measurement_fixed_tokenizer_binding")
    records = []
    for case in cases:
        name = case["case_id"] + ".json"
        record = loads(q.pinned(q.child_path(root, name), manifest["artifacts"][name]["sha256"]).decode())
        checked_record(record, case)
        records.append(record)
    a.same(manifest["records_sha256"], canonical_hash(records), "measurement_records_hash")
    a.same(manifest["unique_examples"], len(records), "measurement_denominator")
    a.same(manifest["categories"], dict(Counter(c["category"] for c in cases)), "measurement_categories")
    artifacts = review_artifacts(records)
    a.same(manifest["artifacts"], {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in artifacts.items()},
           "measurement_artifact_binding")
    artifacts["manifest.json"] = manifest_data
    a.verify_artifacts(root, artifacts, consumer_identity())
    a.same(manifest["consumer"]["package_files"], consumer_identity()["package_files"], "measurement_consumer_binding")
    return manifest, records


def compare(*, config_path, input_root, revision, frozen, reference, native):
    a.cpu_only()
    inputs, frozen_artifacts, _, cases, coverage = bound_selection(
        config_path=config_path, input_root=input_root, revision=revision, frozen=frozen)
    expected = expected_tokenizer_bindings(inputs)
    left, left_records = checked_measurement(reference, "transformers", cases, coverage, frozen_artifacts, expected_tokenizers=expected)
    right, right_records = checked_measurement(native, "tokenizers", cases, coverage, frozen_artifacts, expected_tokenizers=expected)
    a.same(left_records, right_records, "engine_complete_records_differ")
    for profile in q.PROFILES:
        for key in TOKENIZER_IDENTITY_KEYS:
            a.same(left["tokenizers"][profile][key], right["tokenizers"][profile][key], "engine_tokenizer_identity_differ")
    a.cpu_only()
    return {"status": "PASS_COMPLETE_RECORD_EQUALITY", "unique_examples": 13, "engine_measurements": 26,
        "records_sha256": left["records_sha256"], "reference_manifest_sha256": q.sha((Path(reference) / "manifest.json").read_bytes()),
        "native_manifest_sha256": q.sha((Path(native) / "manifest.json").read_bytes()), "static_html_exact": True,
        "browser_actual_observation": "NOT_RUN", "semantic_verdicts_filled": 0, "training_authorized": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("freeze", "measure", "compare"):
        command = sub.add_parser(name)
        flags = ["config-path", "input-root", "revision"]
        flags += ["output"] if name == "freeze" else ["frozen"]
        flags += ["tokenizer-root", "output"] if name == "measure" else []
        flags += ["reference", "native"] if name == "compare" else []
        for flag in flags:
            command.add_argument("--" + flag, required=True, type=Path)
        if name == "measure":
            command.add_argument("--engine", required=True, choices=("transformers", "tokenizers"))
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        result = {"freeze": freeze, "measure": measure, "compare": compare}[command](**args)
    except (DataError, ContractError, ModelIOError, OSError, KeyError, TypeError, ValueError, IndexError) as exc:
        print(encoded({"status": "FAIL", "error_type": type(exc).__name__,
                       "error_code": str(exc) if isinstance(exc, (DataError, ModelIOError)) else "invalid_input_or_io"}).decode())
        return 1
    print(encoded({k: v for k, v in result.items() if k not in {"artifacts", "consumer", "tokenizers"}}).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
