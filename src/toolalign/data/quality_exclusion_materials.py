"""Bind v3 review cases and reuse the eleven unchanged CPU encodings exactly.

The original selection, formatting, sequence, padding and HTML kernels remain
unchanged. New case metadata and publication provenance never replace the actual
encoding time, command or source identity in the parent evidence.
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash
from toolalign.model_io.format import ModelIOError
from toolalign.model_io.sequence import Sequence

from . import quality_adjudication as a
from . import quality_adjudication_materials as am
from . import quality_exclusion as x
from . import quality_revision as q
from .common import DataError, encoded, loads

ENGINES = {"tokenizers": "native", "transformers": "reference"}
ARRAY_FIELDS = ("sequence", "padding", "token_texts")
ENCODING_RELEASE_SHA256 = "1eeea3bd45daa8caf5d2867efa5859a446673888993aaaf9cc3a21b80ca555fd"


def consumer_identity():
    identity = am.consumer_identity()
    for name in ("data/quality_exclusion.py", "data/quality_exclusion_materials.py"):
        identity["package_files"][name] = q.sha(files("toolalign").joinpath(name).read_bytes())
    return identity


def checked_run(buffers, prefix, manifest_data, expected_consumer):
    run = a.document(buffers, prefix + "run.json")
    a.same(run["stable_manifest_sha256"], q.sha(manifest_data), "material_run_manifest")
    a.same(run["consumer"]["package_files"], expected_consumer["package_files"], "material_run_consumer")
    a.same(run["consumer"]["contract_sha256"], expected_consumer["contract_sha256"], "material_run_contract")
    q.require(run["training_authorized"] is False and run["model_modules_loaded"] == [], "material_run_scope")
    q.require(type(run["created_at_utc"]) is str and type(run["output_path"]) is str, "material_run_identity")
    return run


def parent_selection(inputs):
    frozen, manifest, cases, coverage = am.freeze_artifacts(
        inputs["parent"], inputs["parent_artifacts"], inputs["parent_manifest"])
    prefix = "parent-materials/frozen-materials-r2/"
    for name, data in frozen.items():
        q.require(inputs["buffers"][prefix + name] == data, "original_frozen_material_bytes")
    checked_run(inputs["buffers"], prefix, frozen["manifest.json"], am.consumer_identity())
    return frozen, manifest, cases, coverage


def new_source_context(inputs, cases):
    buffers, parent = inputs["buffers"], inputs["parent"]
    context = a.document(buffers, "new-material-sources/manifest.json")
    q.require(context["training_authorized"] is False and context["no_heldout_semantic_content"] is True
              and context["no_resampling"] is True, "new_source_context_scope")
    a.same(context["projection_file_sha256"], q.sha(buffers["material-projection.json"]), "new_source_projection_binding")
    expected = {c["example"]["example_id"]: c for c in cases if c["encoding_mode"] == "new_fixed_example"}
    q.require(len(context["cohort"]) == len(expected) == 2, "new_source_context_count")
    q.require({r["material_example_id"] for r in context["cohort"]} == set(expected), "new_source_material_set")
    raw = a.document(parent["buffers"], "parents/raw_source")
    turns, decisions = 0, 0
    for row in context["cohort"]:
        case = expected[row["material_example_id"]]
        a.same(row["material_case_id"], case["case_id"], "new_source_case_identity")
        data = buffers["new-material-sources/" + row["packet"]]
        a.same(q.sha(data), row["packet_sha256"], "new_source_context_packet_hash")
        a.same(context["files"][row["packet"]]["sha256"], q.sha(data), "new_source_context_manifest_hash")
        packet = loads(data.decode())
        identity = packet["identity"]
        a.same(identity, row["identity"], "new_source_context_identity")
        q.require(identity["split"] == "train", "new_material_final_split_forbidden")
        source = identity["source_record_hash"]
        a.same(source, case["example"]["source_record_hash"], "new_material_source_identity")
        indices = identity["source_indices"]
        q.require(type(indices) is list and indices and all(type(i) is int and i >= 0 for i in indices), "new_source_index_type")
        a.same(indices, [i for i, v in parent["index"]["assignments"].items() if v["source_record_hash"] == source],
               "new_source_all_indices")
        for i in indices:
            a.same(packet["source"], raw[i], "new_source_complete_raw")
            a.same(canonical_hash(raw[i]), source, "new_source_raw_hash")
            a.same({k: parent["index"]["assignments"][i][k] for k in ("source_record_hash", "group_id", "split")},
                   {k: identity[k] for k in ("source_record_hash", "group_id", "split")}, "new_source_assignment")
        ids = {i for i, e in parent["index"]["examples"].items() if e["source_record_hash"] == source}
        a.same(identity["valid_decision_count"], len(ids), "new_source_valid_count")
        q.require(len(identity["example_ids"]) == len(ids) and set(identity["example_ids"]) == ids,
                  "new_source_all_decision_ids")
        a.same(packet["valid_decisions"], [{"example": parent["index"]["examples"][i], "lineage": parent["index"]["lineage"][i]}
                                         for i in identity["example_ids"]], "new_source_original_decision_bytes")
        a.same(row["original_example_line_sha256"], {i: q.sha(parent["original_bytes"][i]) for i in ids}, "new_source_original_lines")
        a.same(row["raw_turns"], len(packet["source"]["conversations"]), "new_source_all_turns")
        turns += row["raw_turns"]
        decisions += len(ids)
    a.same((context["sources"], context["valid_decisions"], context["raw_turns"]), (2, decisions, turns), "new_context_denominators")
    q.require(decisions == 3 and turns == 8, "new_context_fixed_scope")
    return context


def choose_cases(inputs, artifacts, manifest):
    view = {**inputs["parent"], "sources": inputs["sources"]}
    cases, coverage = am.choose_cases(view, artifacts, manifest)
    previous = x.selection_rows(inputs["parent_artifacts"])
    current = x.selection_rows(artifacts)
    policy = inputs["config"]["materials"]
    _, _, old_cases, _ = parent_selection(inputs)
    old_by_id = {c["example"]["example_id"]: c for c in old_cases}
    ids = {c["example"]["example_id"] for c in cases}
    for actual, expected, code in ((ids & set(old_by_id), set(policy["retained_example_ids"]), "retained_material_set"),
        (ids - set(old_by_id), set(policy["new_example_ids"]), "new_material_set"),
        (set(old_by_id) - ids, set(policy["removed_from_materials_example_ids"]), "removed_material_set")):
        a.same(sorted(actual), sorted(expected), code)
    for case in cases:
        ident = case["example"]["example_id"]
        case["encoding_mode"] = "reuse_original" if ident in old_by_id else "new_fixed_example"
        case["previous_material_case_id"] = old_by_id[ident]["case_id"] if ident in old_by_id else None
        for profile, info in case["profiles"].items():
            sidecar = current[profile]["train"][ident]
            a.same(sidecar["previous_selection_rank"], previous[profile]["train"][ident]["selection_rank"], "material_previous_rank")
            info["previous_selection_rank"] = sidecar["previous_selection_rank"]
    projection = a.document(inputs["buffers"], "material-projection.json")
    metadata = [{"case_id": c["case_id"].replace("effective-", "actual-"), "example_id": c["example"]["example_id"],
        "source_record_hash": c["example"]["source_record_hash"], "features": c["features"], "reasons": c["selection_reasons"],
        "total_tokens": c["audit"]["total_tokens"] if c["audit"] else None} for c in cases]
    a.same(metadata, projection["new_cases_metadata"], "fixed_v3_material_projection")
    new_source_context(inputs, cases)
    coverage.update(reused_examples_per_engine=11, new_examples_per_engine=2, existing_staging_reencoded=False,
                    semantic_review="UNFILLED_FOR_INDEPENDENT_AI_REVIEW")
    return cases, coverage


def freeze_artifacts(inputs, artifacts, manifest):
    cases, coverage = choose_cases(inputs, artifacts, manifest)
    result = {"cases.json": encoded(cases) + b"\n", "coverage.json": encoded(coverage) + b"\n"}
    frozen = {"manifest_version": "toolalign.quality-exclusion-material-selection.v3", "training_authorized": False,
        "quality_config_file_sha256": x.CONFIG_SHA256, "quality_revision_sha256": manifest["quality_revision_sha256"],
        "revision_manifest_file_sha256": q.sha(artifacts["manifest.json"]), "case_order": [c["case_id"] for c in cases],
        "unique_examples": 13, "new_tokenization_runs": 0, "new_encodings_planned_per_engine": 2,
        "parent_frozen_manifest_file_sha256": q.sha(inputs["buffers"]["parent-materials/frozen-materials-r2/manifest.json"]),
        "artifacts": {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in result.items()}}
    result["manifest.json"] = encoded(frozen) + b"\n"
    return result, frozen, cases, coverage


def parent_measurement(inputs, engine):
    q.require(engine in ENGINES, "material_engine")
    label, buffers = ENGINES[engine], inputs["buffers"]
    prefix = "parent-materials/review-" + label + "-r2/"
    original = "original-measurements/review-" + label + "/"
    frozen, _, cases, coverage = parent_selection(inputs)
    data = buffers[prefix + "manifest.json"]
    manifest = loads(data.decode())
    q.require(manifest["training_authorized"] is False and manifest["model_modules_loaded"] == []
              and manifest["manifest_version"] == "toolalign.quality-adjudication-token-review.v2", "parent_material_scope")
    a.same(manifest["coverage"], coverage, "parent_material_coverage")
    a.same(manifest["quality_revision_sha256"], inputs["parent_manifest"]["quality_revision_sha256"], "parent_material_revision")
    a.same(manifest["frozen_selection_manifest_file_sha256"], q.sha(frozen["manifest.json"]), "parent_material_selection")
    a.same(manifest["case_order"], [c["case_id"] for c in cases], "parent_material_order")
    a.same(manifest["consumer"]["package_files"], am.consumer_identity()["package_files"], "parent_material_consumer")
    a.same(manifest["consumer"]["contract_sha256"], am.consumer_identity()["contract_sha256"], "parent_material_contract")
    expected = am.expected_tokenizer_bindings(inputs["parent"])
    q.require(set(manifest["tokenizers"]) == set(q.PROFILES), "parent_material_tokenizer_profiles")
    for p in q.PROFILES:
        q.require(manifest["tokenizers"][p]["engine"] == engine, "parent_material_engine")
        a.same({k: manifest["tokenizers"][p][k] for k in am.TOKENIZER_IDENTITY_KEYS}, expected[p], "parent_material_tokenizer")
    records = []
    for case in cases:
        record = a.document(buffers, prefix + case["case_id"] + ".json")
        am.checked_record(record, case)
        records.append(record)
    artifacts = am.review_artifacts(records)
    a.same(manifest["records_sha256"], canonical_hash(records), "parent_material_records")
    a.same(manifest["artifacts"], {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in artifacts.items()}, "parent_material_artifacts")
    for name, value in artifacts.items():
        q.require(buffers[prefix + name] == value, "parent_material_payload_bytes")
    run = checked_run(buffers, prefix, data, am.consumer_identity())
    original_data = buffers[original + "manifest.json"]
    original_manifest = loads(original_data.decode())
    original_run = checked_run(buffers, original, original_data, original_manifest["consumer"])
    origin = manifest["original_encoding"]
    a.same(origin["manifest_file_sha256"], q.sha(original_data), "original_encoding_manifest")
    a.same(origin["run_file_sha256"], q.sha(buffers[original + "run.json"]), "original_encoding_run")
    a.same(origin["consumer"], original_manifest["consumer"], "original_encoding_consumer")
    a.same(origin["actual_original_created_at_utc"], original_run["created_at_utc"], "original_encoding_time")
    a.same(original_manifest["artifacts"], manifest["artifacts"], "original_encoding_payload_identity")
    a.same(original_manifest["records_sha256"], manifest["records_sha256"], "original_encoding_records_identity")
    original_frozen = buffers["original-measurements/frozen-materials/manifest.json"]
    a.same(original_manifest["frozen_selection_manifest_file_sha256"], q.sha(original_frozen), "original_encoding_frozen_selection")
    q.require(origin["source_commit_is_byte_equivalence_not_an_execution_time_claim"] is True
              and manifest["static_republication"]["actual_new_tokenizer_calls"] == 0
              and manifest["static_republication"]["all_material_payload_files_byte_identical"] is True,
              "parent_static_republication_identity")
    command_name = "original-measurements/logs/quality-adjudication-material-" + label + "-r1"
    command = a.document(buffers, command_name + ".json")
    a.same(command["log_sha256"], q.sha(buffers[command_name + ".log"]), "original_encoding_command_log")
    q.require(type(command["exit_code"]) is int and command["exit_code"] == 0, "original_encoding_command_status")
    a.same(command["command"][command["command"].index("--engine") + 1], engine, "original_encoding_command_engine")
    q.require(command["started_at_utc"] <= original_run["created_at_utc"] <= command["finished_at_utc"], "original_encoding_command_time")
    provenance = {"parent_manifest_file_sha256": q.sha(data), "parent_run_file_sha256": q.sha(buffers[prefix + "run.json"]),
        "parent_run": run, "original_encoding": origin, "original_run": original_run,
        "original_encoding_command": command, "original_encoding_command_metadata_file_sha256": q.sha(buffers[command_name + ".json"]),
        "original_encoding_command_log_file_sha256": command["log_sha256"], "new_tokenizer_calls_for_reuse": 0}
    return {"manifest": manifest, "records": {r["case"]["example"]["example_id"]: r for r in records},
            "provenance": provenance, "prefix": prefix}


def sequence_from_record(record):
    data = record["sequence"]
    return Sequence(prompt_text=data["prompt_text"], completion_text=data["completion_text"],
        prompt_ids=tuple(data["prompt_ids"]), concatenated_ids=tuple(data["concatenated_ids"]),
        sequence_ids=tuple(data["sequence_ids"]), loss_mask=tuple(data["loss_mask"]), eos_token_id=data["eos_token_id"])


def reuse_record(case, old):
    q.require(case["encoding_mode"] == "reuse_original", "reuse_case_mode")
    am.checked_record(old, old["case"])
    a.same(case["example"], old["case"]["example"], "reuse_example_identity")
    a.same(case["audit"], old["case"]["audit"], "reuse_original_audit")
    a.same(case["previous_material_case_id"], old["case"]["case_id"], "reuse_original_case_id")
    record = am.typed_sequence_record(case, sequence_from_record(old))
    record["token_texts"] = copy.deepcopy(old["token_texts"])
    for key in ARRAY_FIELDS:
        a.same(record[key], old[key], "reuse_complete_arrays_unchanged")
    am.checked_record(record, case)
    return record


def reused_records(cases, parent, policy):
    q.require(len(cases) == 13 and len({c["example"]["example_id"] for c in cases}) == 13, "fixed_material_case_count")
    retained = [c for c in cases if c["encoding_mode"] == "reuse_original"]
    a.same(sorted(c["example"]["example_id"] for c in retained), policy["retained_example_ids"], "reuse_fixed_example_set")
    q.require(len(retained) == policy["retained_case_count_per_engine"] == 11, "reuse_case_count")
    records, provenance = [], []
    for case in retained:
        ident = case["example"]["example_id"]
        old = parent["records"][ident]
        name = old["case"]["case_id"] + ".json"
        a.same(q.sha(encoded(old) + b"\n"), parent["manifest"]["artifacts"][name]["sha256"], "reuse_frozen_record_file")
        records.append(reuse_record(case, old))
        provenance.append({"case_id": case["case_id"], "example_id": ident, "previous_material_case_id": old["case"]["case_id"],
            "original_record_file": parent["prefix"] + name, "original_record_file_sha256": parent["manifest"]["artifacts"][name]["sha256"],
            "sequence_padding_token_texts_sha256": canonical_hash({k: old[k] for k in ARRAY_FIELDS}),
            "new_record_canonical_sha256": canonical_hash(records[-1]), "new_tokenizer_calls": 0})
    return records, {"parent_encoding": parent["provenance"], "records": provenance}


def review_artifacts(records):
    artifacts = am.review_artifacts(records)
    for name, data in list(artifacts.items()):
        if name.endswith(".html"):
            artifacts[name] = data.replace("<h2>新测序列的身份与预算观察</h2>".encode(),
                                           "<h2>序列身份与预算观察（编码来源见用途）</h2>".encode())
    artifacts["index.html"] = artifacts["index.html"].replace(b"ToolAlign v2", b"ToolAlign v3").replace(
        "10 个有效 train 原例和 3 个原创协议例。".encode(),
        "本目录仅列出 manifest 中的材料。完整选择为 10 个有效 train 原例和 3 个原创协议例；11 个旧例复用原编码。".encode())
    return artifacts


def reuse_artifacts(inputs, frozen, cases, coverage, engine):
    parent = parent_measurement(inputs, engine)
    records, provenance = reused_records(cases, parent, inputs["config"]["materials"])
    artifacts = review_artifacts(records)
    artifacts["encoding-provenance.json"] = encoded(provenance) + b"\n"
    manifest = {"manifest_version": "toolalign.quality-exclusion-reused-materials.v3", "training_authorized": False,
        "status": "ELEVEN_ORIGINAL_RECORDS_REUSED", "quality_config_file_sha256": x.CONFIG_SHA256,
        "quality_revision_sha256": coverage["quality_revision_sha256"], "frozen_selection_manifest_file_sha256": q.sha(frozen["manifest.json"]),
        "coverage": coverage, "case_order": [r["case"]["case_id"] for r in records], "unique_examples": 11,
        "new_tokenizer_calls": 0, "tokenizers": parent["manifest"]["tokenizers"], "consumer": consumer_identity(),
        "records_sha256": canonical_hash(records), "browser_actual_observation": "NOT_RUN", "model_modules_loaded": [],
        "semantic_review": "UNFILLED_FOR_INDEPENDENT_AI_REVIEW", "trainer_consumption": "NOT_RUN",
        "artifacts": {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in artifacts.items()}}
    artifacts["manifest.json"] = encoded(manifest) + b"\n"
    return artifacts, manifest, records, provenance


def run_record(output, data):
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "consumer": consumer_identity(),
        "stable_manifest_sha256": q.sha(data), "model_modules_loaded": [], "training_authorized": False,
        "output_path": str(Path(output).resolve())}


def bound_selection(*, config_path, input_root, revision, frozen=None):
    a.cpu_only()
    inputs = x.bound_inputs(config_path=config_path, input_root=input_root)
    artifacts, manifest = x.stable_artifacts(inputs)
    a.verify_artifacts(revision, artifacts, x.consumer_identity())
    selected, selection, cases, coverage = freeze_artifacts(inputs, artifacts, manifest)
    if frozen is not None:
        a.verify_artifacts(frozen, selected, consumer_identity())
    return inputs, selected, selection, cases, coverage


def freeze(*, output, **paths):
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    _, artifacts, manifest, _, _ = bound_selection(**paths)
    a.cpu_only()
    q.publish(output, artifacts, run_record(output, artifacts["manifest.json"]))
    return manifest


def reuse(*, output, engine, **paths):
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    inputs, frozen, _, cases, coverage = bound_selection(**paths)
    artifacts, manifest, _, _ = reuse_artifacts(inputs, frozen, cases, coverage, engine)
    a.cpu_only()
    q.publish(output, artifacts, run_record(output, artifacts["manifest.json"]))
    return manifest


def verify_reuse(*, output, engine, **paths):
    inputs, frozen, _, cases, coverage = bound_selection(**paths)
    artifacts, manifest, _, _ = reuse_artifacts(inputs, frozen, cases, coverage, engine)
    a.verify_artifacts(output, artifacts, consumer_identity())
    a.cpu_only()
    return manifest


def compare_reuse(*, reference, native, **paths):
    inputs, frozen, _, cases, coverage = bound_selection(**paths)
    results = []
    for engine, root in (("transformers", reference), ("tokenizers", native)):
        artifacts, manifest, records, _ = reuse_artifacts(inputs, frozen, cases, coverage, engine)
        a.verify_artifacts(root, artifacts, consumer_identity())
        results.append((manifest, records, q.sha(artifacts["manifest.json"])))
    a.same(results[0][1], results[1][1], "reused_engine_complete_records_differ")
    a.cpu_only()
    return {"status": "PASS_ELEVEN_REUSED_COMPLETE_RECORDS", "unique_examples": 11, "engine_records": 22,
        "new_sequence_calls": 0, "records_sha256": results[0][0]["records_sha256"],
        "reference_manifest_sha256": results[0][2], "native_manifest_sha256": results[1][2],
        "semantic_verdicts_filled": 0, "browser_actual_observation": "NOT_RUN", "training_authorized": False}


def load_encoding_release(path, inputs):
    release = loads(q.pinned(path, ENCODING_RELEASE_SHA256).decode())
    q.require(release["schema"] == "toolalign.s0.v3-new-material-encoding-release.v1" and release["issuer"] == "S0"
              and release["status"] == "AUTHORIZED_WITHIN_EXISTING_TWO_EXAMPLE_SCOPE"
              and release["review_scope"] == "SOURCE_SEMANTICS_ONLY", "encoding_release_scope")
    a.same(release["config_sha256"], x.CONFIG_SHA256, "encoding_release_policy")
    a.same(release["code_base"], inputs["config"]["verified_code_base"], "encoding_release_base")
    a.same(release["d1_input_manifest_sha256"], inputs["config"]["input_bindings"]["input_manifest_file_sha256"], "encoding_release_inputs")
    a.same(release["source_context_sha256"], inputs["config"]["input_bindings"]["new_material_source_context_file_sha256"], "encoding_release_context")
    a.same(release["material_example_ids"], inputs["config"]["materials"]["new_example_ids"], "encoding_release_examples")
    a.same(release["engines"], inputs["config"]["materials"]["engines"], "encoding_release_engines")
    for key in ("training_authorized", "reencode_retained_eleven", "additional_encoding_for_third_source_target",
                "fixed_347_item_input_manifest_mutation_authorized", "new_source_sampling_or_label_changes_authorized"):
        q.require(release[key] is False, "encoding_release_boundary")
    for key, expected in (("new_material_encodings_per_engine", 2), ("new_sequence_generation_calls_total_limit", 4),
        ("new_dataset_build_authorizations", 0), ("new_dependency_environment_download_authorizations", 0),
        ("new_framework_model_gpu_training_authorizations", 0)):
        a.same(release[key], expected, "encoding_release_budget")
    context = a.document(inputs["buffers"], "new-material-sources/manifest.json")
    expected = [{"material_example_id": c["material_example_id"], "source_record_hash": c["identity"]["source_record_hash"],
                 "split": "train", "all_valid_example_ids": c["identity"]["example_ids"], "verdict": "PASS"} for c in context["cohort"]]
    a.same([{k: row[k] for k in expected[0]} for row in release["sources"]], expected, "encoding_release_reviewed_sources")
    return release


def new_cases(cases, policy):
    q.require(len(cases) == len({c["example"]["example_id"] for c in cases}) == 13
              and {c["case_id"] for c in cases} == am.CASE_NAMES, "encoding_fixed_case_count")
    selected = [c for c in cases if c["encoding_mode"] == "new_fixed_example"]
    a.same([c["example"]["example_id"] for c in selected], policy["new_example_ids"], "encoding_fixed_new_examples")
    q.require(len(selected) == 2 and all(c["category"] == "effective_selected_train" and c["example"]["split"] == "train"
                                      for c in selected), "encoding_new_case_budget")
    return selected


def reserve_sequences(root, engine, selected, output):
    root = Path(root)
    q.require(engine in ENGINES and ".toolalign-local" in root.resolve().parts and not root.is_symlink(), "encoding_budget_scope")
    root.mkdir(parents=True, exist_ok=True)
    path = root / (engine + ".reservation.json")
    reservation = {"status": "TWO_SEQUENCE_CALLS_RESERVED_NO_AUTOMATIC_RETRY", "engine": engine,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "consumer": consumer_identity(),
        "encoding_release_file_sha256": ENCODING_RELEASE_SHA256, "quality_config_file_sha256": x.CONFIG_SHA256,
        "example_ids": [c["example"]["example_id"] for c in selected], "maximum_sequence_calls": 2,
        "output_path": str(Path(output).resolve()), "training_authorized": False}
    try:
        with path.open("xb") as stream:
            stream.write(encoded(reservation) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise DataError("encoding_engine_budget_already_reserved") from exc
    return reservation, path


def complete_artifacts(cases, coverage, records, provenance, *, frozen, tokenizers, release):
    a.same([r["case"] for r in records], cases, "complete_material_case_order")
    for record, case in zip(records, cases, strict=True):
        am.checked_record(record, case)
    artifacts = review_artifacts(records)
    artifacts["encoding-provenance.json"] = encoded(provenance) + b"\n"
    review = {k: release[k] for k in ("q1_review_commit", "q1_source_seal_sha256", "q1_final_seal_sha256",
                                     "q1_adjudications_sha256", "s0_formal_receipt_proof_sha256", "review_scope")}
    manifest = {"manifest_version": "toolalign.quality-exclusion-token-review.v3", "quality_config_file_sha256": x.CONFIG_SHA256,
        "quality_revision_sha256": coverage["quality_revision_sha256"], "coverage": coverage,
        "frozen_selection_manifest_file_sha256": q.sha(frozen["manifest.json"]), "consumer": consumer_identity(),
        "case_order": [c["case_id"] for c in cases], "unique_examples": 13, "reused_examples": 11, "new_sequence_calls": 2,
        "encoding_release_file_sha256": ENCODING_RELEASE_SHA256, "source_only_review": review, "tokenizers": tokenizers,
        "records_sha256": canonical_hash(records), "semantic_review": "UNFILLED_FOR_INDEPENDENT_AI_REVIEW",
        "browser_actual_observation": "NOT_RUN", "external_execution": "NOT_RUN", "trainer_consumption": "NOT_RUN",
        "model_modules_loaded": [], "training_authorized": False,
        "artifacts": {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in artifacts.items()}}
    artifacts["manifest.json"] = encoded(manifest) + b"\n"
    return artifacts, manifest


def write_measurement(cases, coverage, *, parent, policy, frozen, release, tokenizers_by_profile, expected_tokenizers,
                      engine, output, budget_root, release_path):
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    a.cpu_only()
    selected = new_cases(cases, policy)
    a.same([c["example"]["example_id"] for c in selected], release["material_example_ids"], "measurement_release_examples")
    reused, provenance = reused_records(cases, parent, policy)
    q.require(set(tokenizers_by_profile) == set(q.PROFILES), "new_measurement_tokenizer_profiles")
    identities = {p: adapter.identity for p, adapter in tokenizers_by_profile.items()}
    for profile in q.PROFILES:
        q.require(identities[profile]["engine"] == engine, "new_measurement_tokenizer_engine")
        a.same({k: identities[profile][k] for k in am.TOKENIZER_IDENTITY_KEYS}, expected_tokenizers[profile], "new_measurement_fixed_tokenizer")
    reservation, reservation_path = reserve_sequences(budget_root, engine, selected, output)
    event_path = Path(budget_root) / (engine + ".events.jsonl")
    records_by_id = {r["case"]["example"]["example_id"]: r for r in reused}
    events = []
    with event_path.open("xb") as event_stream:
        def record_event(value):
            event_stream.write(encoded(value) + b"\n")
            event_stream.flush()
            os.fsync(event_stream.fileno())

        for ordinal, case in enumerate(selected, 1):
            ident = case["example"]["example_id"]
            started = datetime.now(timezone.utc).isoformat()
            record_event({"event": "sequence_call_started", "ordinal": ordinal, "example_id": ident, "at_utc": started})
            try:
                adapter = tokenizers_by_profile[case["primary_profile"]]
                record = am.typed_sequence_record(case, adapter.training_sequence(case["example"]))
                record["token_texts"] = [adapter.decode([i], skip_special_tokens=False) for i in record["padding"]["sequence_ids"]]
                q.require(adapter.decode(record["sequence"]["concatenated_ids"][record["sequence"]["prompt_tokens"]:],
                    skip_special_tokens=False) == record["sequence"]["completion_text"], "new_measurement_decoded_action")
                am.checked_record(record, case)
            except BaseException as exc:
                record_event({"event": "sequence_call_failed", "ordinal": ordinal, "example_id": ident,
                              "at_utc": datetime.now(timezone.utc).isoformat(), "error_type": type(exc).__name__})
                raise
            event = {"event": "sequence_call_completed", "ordinal": ordinal, "example_id": ident,
                "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "record_sha256": canonical_hash(record)}
            record_event(event)
            events.append(event)
            records_by_id[ident] = record
    records = [records_by_id[c["example"]["example_id"]] for c in cases]
    provenance["new_records"] = [{"case_id": c["case_id"], "example_id": c["example"]["example_id"],
        "record_sha256": canonical_hash(records_by_id[c["example"]["example_id"]]), "encoding_release_file_sha256": ENCODING_RELEASE_SHA256}
        for c in selected]
    artifacts, manifest = complete_artifacts(cases, coverage, records, provenance, frozen=frozen, tokenizers=identities, release=release)
    a.cpu_only()
    run = run_record(output, artifacts["manifest.json"])
    run.update(encoding_release_file_sha256=ENCODING_RELEASE_SHA256, encoding_release_path=str(Path(release_path).resolve()),
        encoding_release_issued_at_utc=release["issued_at_utc"], new_sequence_calls=2, reused_sequence_calls=0,
        sequence_budget_reservation_sha256=q.sha(encoded(reservation) + b"\n"), sequence_events_file_sha256=q.sha(event_path.read_bytes()),
        sequence_budget_reservation_path=str(reservation_path.resolve()), new_sequence_events=events)
    q.publish(output, artifacts, run)
    return manifest


def measure(*, config_path, input_root, revision, frozen, release_path, tokenizer_root, engine, output):
    q.require(all(os.environ.get(n) == "0" for n in ("USE_TORCH", "USE_TF", "USE_FLAX"))
              and all(os.environ.get(n) == "1" for n in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")), "offline_cpu_environment_required")
    a.cpu_only()
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    inputs, selected, _, cases, coverage = bound_selection(config_path=config_path, input_root=input_root, revision=revision, frozen=frozen)
    release = load_encoding_release(release_path, inputs)
    parent = parent_measurement(inputs, engine)
    budget_root = Path(input_root).resolve().parent / "encoding-budget"
    q.require(not (budget_root / (engine + ".reservation.json")).exists(), "encoding_engine_budget_already_reserved")
    from toolalign.model_io.offline import OfflineQwenTokenizer

    adapters = {p: OfflineQwenTokenizer(tokenizer_root, engine=engine, repo_id=spec["model_id"], revision=spec["model_revision"])
                for p, spec in inputs["parent"]["parent_config"]["profiles"].items()}
    return write_measurement(cases, coverage, parent=parent, policy=inputs["config"]["materials"], frozen=selected,
        release=release, tokenizers_by_profile=adapters, expected_tokenizers=am.expected_tokenizer_bindings(inputs["parent"]),
        engine=engine, output=output, budget_root=budget_root, release_path=release_path)


def checked_measurement(root, engine, *, inputs, cases, coverage, frozen, release, budget_root):
    root = Path(root)
    parent = parent_measurement(inputs, engine)
    reused, provenance = reused_records(cases, parent, inputs["config"]["materials"])
    selected = new_cases(cases, inputs["config"]["materials"])
    records = [loads((root / (c["case_id"] + ".json")).read_bytes().decode()) for c in cases]
    by_id = {r["case"]["example"]["example_id"]: r for r in records}
    for record in reused:
        a.same(by_id[record["case"]["example"]["example_id"]], record, "complete_reused_record_changed")
    provenance["new_records"] = [{"case_id": c["case_id"], "example_id": c["example"]["example_id"],
        "record_sha256": canonical_hash(by_id[c["example"]["example_id"]]), "encoding_release_file_sha256": ENCODING_RELEASE_SHA256}
        for c in selected]
    manifest = loads((root / "manifest.json").read_bytes().decode())
    identities = manifest["tokenizers"]
    expected_tokenizers = am.expected_tokenizer_bindings(inputs["parent"])
    q.require(set(identities) == set(q.PROFILES), "complete_material_tokenizer_profiles")
    for p in q.PROFILES:
        q.require(identities[p]["engine"] == engine, "complete_material_engine")
        a.same({k: identities[p][k] for k in am.TOKENIZER_IDENTITY_KEYS}, expected_tokenizers[p], "complete_material_tokenizer_binding")
    artifacts, expected = complete_artifacts(cases, coverage, records, provenance, frozen=frozen, tokenizers=identities, release=release)
    a.same(manifest, expected, "complete_measurement_manifest")
    run = a.verify_artifacts(root, artifacts, consumer_identity())
    q.require(run["new_sequence_calls"] == 2 and type(run["new_sequence_calls"]) is int and run["reused_sequence_calls"] == 0
              and type(run["reused_sequence_calls"]) is int, "complete_measurement_run_counts")
    a.same(run["encoding_release_file_sha256"], ENCODING_RELEASE_SHA256, "complete_measurement_release")
    a.same(run["encoding_release_issued_at_utc"], release["issued_at_utc"], "complete_measurement_release_time")
    reservation_path = Path(budget_root) / (engine + ".reservation.json")
    reservation = loads(q.pinned(reservation_path, run["sequence_budget_reservation_sha256"]).decode())
    a.same(reservation["example_ids"], [c["example"]["example_id"] for c in selected], "complete_measurement_reserved_examples")
    a.same(reservation["encoding_release_file_sha256"], ENCODING_RELEASE_SHA256, "complete_measurement_reserved_release")
    q.require(reservation["maximum_sequence_calls"] == 2 and type(reservation["maximum_sequence_calls"]) is int
              and reservation["training_authorized"] is False and reservation["engine"] == engine, "complete_measurement_reserved_scope")
    a.same(reservation["consumer"]["package_files"], consumer_identity()["package_files"], "complete_measurement_reserved_consumer")
    events = q.jsonl(q.pinned(Path(budget_root) / (engine + ".events.jsonl"), run["sequence_events_file_sha256"]))[0]
    q.require(len(events) == 4, "complete_measurement_event_count")
    a.same(events[1::2], run["new_sequence_events"], "complete_measurement_event_run")
    for ordinal, case in enumerate(selected, 1):
        start, end = events[(ordinal - 1) * 2:ordinal * 2]
        ident = case["example"]["example_id"]
        a.same({k: start[k] for k in ("event", "ordinal", "example_id")},
            {"event": "sequence_call_started", "ordinal": ordinal, "example_id": ident}, "complete_measurement_start_event")
        a.same({k: end[k] for k in ("event", "ordinal", "example_id", "record_sha256")},
            {"event": "sequence_call_completed", "ordinal": ordinal, "example_id": ident,
             "record_sha256": canonical_hash(by_id[ident])}, "complete_measurement_end_event")
        a.same(start["at_utc"], end["started_at_utc"], "complete_measurement_event_time")
        q.require(release["issued_at_utc"] <= reservation["created_at_utc"] <= start["at_utc"] <= end["finished_at_utc"] <= run["created_at_utc"],
                  "complete_measurement_execution_order")
    return manifest, records


def compare(*, reference, native, release_path, **paths):
    inputs, frozen, _, cases, coverage = bound_selection(**paths)
    release = load_encoding_release(release_path, inputs)
    results = [checked_measurement(root, engine, inputs=inputs, cases=cases, coverage=coverage, frozen=frozen, release=release,
        budget_root=Path(paths["input_root"]).resolve().parent / "encoding-budget")
        for engine, root in (("transformers", reference), ("tokenizers", native))]
    a.same(results[0][1], results[1][1], "complete_engine_records_differ")
    a.cpu_only()
    return {"status": "PASS_THIRTEEN_COMPLETE_RECORDS", "unique_examples": 13, "engine_records": 26,
        "reused_engine_records": 22, "actual_new_sequence_calls_total": 4, "records_sha256": results[0][0]["records_sha256"],
        "reference_manifest_sha256": q.sha((Path(reference) / "manifest.json").read_bytes()),
        "native_manifest_sha256": q.sha((Path(native) / "manifest.json").read_bytes()), "encoding_release_file_sha256": ENCODING_RELEASE_SHA256,
        "static_html_exact": True, "semantic_verdicts_filled": 0, "browser_actual_observation": "NOT_RUN", "training_authorized": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("freeze", "reuse", "verify-reuse", "compare-reuse", "measure", "compare"):
        command = sub.add_parser(name)
        flags = ["config-path", "input-root", "revision"]
        flags += ["reference", "native"] if name in {"compare-reuse", "compare"} else ["output"]
        flags += ["release-path"] if name in {"measure", "compare"} else []
        flags += ["tokenizer-root"] if name == "measure" else []
        for flag in flags:
            command.add_argument("--" + flag, required=True, type=Path)
        if name != "freeze":
            command.add_argument("--frozen", required=True, type=Path)
        if name in {"reuse", "verify-reuse", "measure"}:
            command.add_argument("--engine", required=True, choices=tuple(ENGINES))
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        result = {"freeze": freeze, "reuse": reuse, "verify-reuse": verify_reuse, "compare-reuse": compare_reuse,
                  "measure": measure, "compare": compare}[command](**args)
    except (DataError, ContractError, ModelIOError, OSError, KeyError, TypeError, ValueError, IndexError) as exc:
        print(encoded({"status": "FAIL", "error_type": type(exc).__name__,
            "error_code": str(exc) if isinstance(exc, (DataError, ModelIOError)) else "invalid_input_or_io"}).decode())
        return 1
    print(encoded({k: v for k, v in result.items() if k not in {"artifacts", "consumer", "tokenizers"}}).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
