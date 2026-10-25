"""Two CPU preparation commands and the portable, tokenizer-free array reader."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from toolalign.data.common import encoded as data_encoded
from toolalign.model_io.format import format_identity
from toolalign.training.sft.collator import Batch, collate_selected
from toolalign.training.sft.data import SelectedRow

from .protocol import (
    CAPACITY_COHORT_SHA256,
    CONFIG_SHA256,
    MAX_BUNDLE_BYTES,
    bounded_request,
    canonical_sha,
    document,
    encoded,
    load_protocol,
    read_bytes,
    require,
    sha,
    source_identity,
    write_bytes,
)

_ARRAY_FIELDS = {"sequence_ids", "attention_mask", "loss_mask", "causal_input_ids",
                 "causal_target_ids", "causal_loss_mask"}


def batch_from_record(value):
    require(type(value) is dict, "batch_record")
    for key in _ARRAY_FIELDS:
        require(type(value.get(key)) is list and all(type(i) is int for i in value[key]),
                "batch_array_type")
    require(all(type(v) is int for k, v in value.items() if k not in _ARRAY_FIELDS), "batch_scalar_type")
    return Batch(**{k: tuple(v) if k in _ARRAY_FIELDS else v for k, v in value.items()})


def cohort_entry(sidecar):
    audit = sidecar["audit"]
    return {"selection_rank": sidecar["selection_rank"], "example_id": audit["example_id"],
            "example_sha256": audit["example_sha256"], "sequence_sha256": audit["sequence_sha256"],
            "total_tokens": audit["total_tokens"],
            "supervised_tokens": audit["completion_tokens_including_eos"],
            "padding_bucket": sidecar["padding_bucket"], "sidecar_sha256": canonical_sha(sidecar)}


def select_rows(prepared, profile, run_kind):
    result = {}
    for split, size in (("train", 18), ("validation", 2)):
        rows = prepared.view(profile, split).rows
        if run_kind == "capacity":
            rows = sorted(rows, key=lambda r: (-r.sidecar["audit"]["total_tokens"],
                                               r.sidecar["selection_rank"]))[:size]
            rows = sorted(rows, key=lambda r: r.sidecar["selection_rank"])
        result[split] = tuple(rows)
    if run_kind == "capacity":
        cohort = {s: [cohort_entry(r.sidecar) for r in rows] for s, rows in result.items()}
        require(canonical_sha(cohort) == CAPACITY_COHORT_SHA256, "capacity_cohort_mismatch")
    return result


def _before_deadline(started, request):
    require(time.monotonic() - started < request["max_wall_seconds"], "preparation_deadline")


def _write_jsonl(root, name, records, remaining):
    total = 0
    with (root / name).open("xb") as stream:
        for record in records:
            data = encoded(record) + b"\n"
            total += len(data)
            require(total <= remaining, "output_byte_budget")
            stream.write(data)
        stream.flush()
    raw = read_bytes(root / name)
    return {"sha256": sha(raw), "bytes": len(raw)}


def _check_manifest(manifest, *, schema, config):
    require(manifest.get("schema") == schema and manifest.get("complete") is True, "incomplete_bundle")
    require(manifest["config_sha256"] == CONFIG_SHA256, "array_config_mismatch")
    require(manifest["view_summaries"] == config["view_summaries"]
            and manifest["data_binding"] == config["data_binding"], "array_data_identity")
    require(manifest["format"] == format_identity(), "array_format_identity")
    profile, kind = manifest["profile"], manifest["run_kind"]
    require(profile in config["profiles"] and kind in ("sft", "capacity"), "array_scope")
    require(kind != "capacity" or profile == "formal", "capacity_profile")
    require(manifest["model"] == config["profiles"][profile], "array_model_identity")
    require(set(manifest["artifacts"]) == {"train.jsonl", "validation.jsonl"}, "array_artifacts")


def _lines(root, manifest, split):
    name = split + ".jsonl"
    expected = manifest["artifacts"][name]
    raw = read_bytes(root / name)
    require(len(raw) == expected["bytes"] and sha(raw) == expected["sha256"], "array_file_identity")
    require(raw.endswith(b"\n"), "array_jsonl_boundary")
    for line in raw.splitlines():
        yield json.loads(line)


def _check_selection(records, manifest, config):
    kind, profile = manifest["run_kind"], manifest["profile"]
    cohort = {}
    for split, values in records.items():
        sidecars = [r["sidecar"] for r in values]
        entries = [cohort_entry(s) for s in sidecars]
        ids = [e["example_id"] for e in entries]
        ranks = [e["selection_rank"] for e in entries]
        require(all(type(r) is int and r > 0 for r in ranks)
                and ranks == sorted(set(ranks)) and len(ids) == len(set(ids)), "array_order_or_duplicate")
        require(all(s["profile"] == profile and s["split"] == split for s in sidecars), "array_split")
        if kind == "sft":
            summary = config["view_summaries"][profile][split]
            require(len(ids) == summary["effective_selected_count"]
                    and canonical_sha(ids) == summary["selected_identity_sha256"]
                    and ranks == list(range(1, len(ids) + 1)), "full_profile_coverage")
        cohort[split] = entries
    require(manifest["cohort_sha256"] == canonical_sha(cohort), "cohort_identity")
    if kind == "capacity":
        require(manifest["cohort_sha256"] == CAPACITY_COHORT_SHA256, "capacity_cohort_mismatch")


def prepare(request):
    """No framework imports: verify v3 and 13 reviewed arrays, stage selected rows."""
    from toolalign.training.sft.data_v3 import (
        _export_manifest,
        export_review_arrays,
        prepare_v3,
        read_review_arrays,
        rebind_review_arrays,
    )

    started = time.monotonic()
    bounded_request(request, schema="toolalign.cuda-sft-prepare.v1")
    require(".toolalign-local" in Path(request["output_dir"]).parts, "v3_private_output_required")
    config = load_protocol(request["repository"])
    source = source_identity(request["repository"], request["source_commit"])
    prepared = prepare_v3(sft_config_path=Path(request["repository"]) / "configs/sft-data-v3.v1.json",
                          input_manifest_path=request["input_manifest"])
    review = rebind_review_arrays(prepared)
    # Reuse the fixed producer's manifest calculation to check its exact bytes
    # before its exclusive export writes anything.
    review_size = len(review.payload_bytes) + len(data_encoded(_export_manifest(review))) + 1
    require(review_size <= request["max_output_bytes"], "output_byte_budget")
    selected = select_rows(prepared, request["profile"], request["run_kind"])
    expected_count = sum(len(v) for v in selected.values())
    require(request.get("max_examples") == expected_count, "exact_encoding_budget_required")
    root = Path(request["output_dir"])
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    export_review_arrays(review, output=root / "review")
    read_review_arrays(output=root / "review", expected=review)
    originals = {(p, s, i): h for p, s, i, h in prepared.original_line_hashes}
    artifacts, remaining = {}, request["max_output_bytes"]
    remaining -= review_size
    for split, rows in selected.items():
        _before_deadline(started, request)
        records = ({"example": r.example, "sidecar": r.sidecar,
                    "original_line_sha256": originals[request["profile"], split, r.example["example_id"]]}
                   for r in rows)
        info = _write_jsonl(root, split + ".jsonl", records, remaining)
        artifacts[split + ".jsonl"] = info
        remaining -= info["bytes"]
    cohort = {s: [cohort_entry(r.sidecar) for r in rows] for s, rows in selected.items()}
    manifest = {"schema": "toolalign.cuda-sft-stage.v1", "complete": True,
        "run_kind": request["run_kind"], "profile": request["profile"],
        "config_sha256": CONFIG_SHA256, "source": source, "view_summaries": config["view_summaries"],
        "data_binding": config["data_binding"], "format": format_identity(),
        "model": config["profiles"][request["profile"]], "cohort_sha256": canonical_sha(cohort),
        "review_arrays_sha256": sha(review.payload_bytes), "review_materials": 13,
        "protocol_only_materials": 3, "new_sequence_calls": 0,
        "preparation_receipt_sha256": sha(prepared.report_bytes), "artifacts": artifacts}
    raw = encoded(manifest) + b"\n"
    require(len(raw) <= remaining, "output_byte_budget")
    _before_deadline(started, request)
    write_bytes(root / "manifest.json", raw)
    return {"status": "PASS", "stage_manifest_sha256": sha(raw), "selected_count": expected_count,
            "new_sequence_calls": 0}


def encode(request):
    """Fresh no-model process: native tokenizer and audited collator only."""
    from toolalign.model_io.offline import OfflineQwenTokenizer, model_modules_loaded

    started = time.monotonic()
    bounded_request(request, schema="toolalign.cuda-sft-encode.v1")
    require(not model_modules_loaded() and "transformers" not in sys.modules, "no_model_encoder_required")
    config = load_protocol(request["repository"])
    source = source_identity(request["repository"], request["source_commit"])
    stage_root = Path(request["stage_dir"])
    stage = document(stage_root / "manifest.json", digest=request["stage_manifest_sha256"])
    _check_manifest(stage, schema="toolalign.cuda-sft-stage.v1", config=config)
    require(stage["source"] == source and stage["profile"] == request["profile"]
            and stage["run_kind"] == request["run_kind"], "stage_request_mismatch")
    rows = {s: list(_lines(stage_root, stage, s)) for s in ("train", "validation")}
    _check_selection(rows, stage, config)
    count = sum(len(v) for v in rows.values())
    require(request.get("max_examples") == count, "exact_encoding_budget_required")
    model = config["profiles"][request["profile"]]
    tokenizer = OfflineQwenTokenizer(request["tokenizer_root"], repo_id=model["model_id"],
                                    revision=model["model_revision"], engine="tokenizers")
    root = Path(request["output_dir"])
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    remaining, artifacts = request["max_output_bytes"], {}

    def records(split):
        for value in rows[split]:
            _before_deadline(started, request)
            row = SelectedRow(encoded(value["example"]), encoded(value["sidecar"]))
            _, batch = collate_selected(row, tokenizer=tokenizer)
            yield {"sidecar": value["sidecar"], "original_line_sha256": value["original_line_sha256"],
                   "batch": batch.record()}

    for split in rows:
        info = _write_jsonl(root, split + ".jsonl", records(split), remaining)
        artifacts[split + ".jsonl"] = info
        remaining -= info["bytes"]
    manifest = {**stage, "schema": "toolalign.cuda-sft-arrays.v1", "artifacts": artifacts,
                "stage_manifest_sha256": request["stage_manifest_sha256"],
                "tokenizer": tokenizer.identity, "new_sequence_calls": count}
    raw = encoded(manifest) + b"\n"
    require(len(raw) <= remaining, "output_byte_budget")
    write_bytes(root / "manifest.json", raw)
    read_bundle(root, expected_digest=sha(raw), config=config)
    return {"status": "PASS", "array_manifest_sha256": sha(raw), "new_sequence_calls": count,
            "run_kind": request["run_kind"], "cohort_sha256": manifest["cohort_sha256"]}


def checked_batch(record, *, config, profile, split):
    batch = batch_from_record(record["batch"])
    sidecar, audit = record["sidecar"], record["sidecar"]["audit"]
    require(sidecar["profile"] == profile and sidecar["split"] == split, "array_split")
    require(batch.pad_token_id == config["training"]["pad_token_id"]
            and batch.bucket == sidecar["padding_bucket"]
            and batch.bucket in config["profiles"][profile]["padding_buckets"], "array_padding")
    n, p = batch.unpadded_length, batch.first_supervised_causal_position + 1
    sequence, loss = list(batch.sequence_ids[:n]), list(batch.loss_mask[:n])
    eos = config["training"]["eos_token_id"]
    require(n > p + 1 and sequence[-1] == eos and sequence[p:].count(eos) == 1, "array_completion_eos")
    bindings = {**format_identity(), "sequence_sha256": canonical_sha(sequence),
        "prompt_ids_sha256": canonical_sha(sequence[:p]),
        "concatenated_ids_sha256": canonical_sha(sequence[:-1]),
        "loss_mask_sha256": canonical_sha(loss), "causal_loss_mask_sha256": canonical_sha(loss[1:]),
        "causal_input_ids_sha256": canonical_sha(sequence[:-1]),
        "causal_target_ids_sha256": canonical_sha(sequence[1:]), "prompt_tokens": p,
        "completion_tokens": n - p - 1, "completion_tokens_including_eos": n - p,
        "total_tokens": n, "eos_token_id": eos, "append_eos_count": 1, "prefix_stable": True,
        "first_supervised_causal_position": p - 1, "last_supervised_causal_position": n - 2}
    require(all(audit.get(k) == v for k, v in bindings.items()), "array_audit_mismatch")
    require(type(record.get("original_line_sha256")) is str
            and len(record["original_line_sha256"]) == 64, "original_line_identity")
    return batch


@dataclass(frozen=True)
class ArrayBundle:
    root: Path
    manifest: dict
    manifest_sha256: str
    config: dict
    ids: dict

    def records(self, split):
        require(split in ("train", "validation"), "forbidden_array_split")
        for record in _lines(self.root, self.manifest, split):
            batch = checked_batch(record, config=self.config, profile=self.manifest["profile"], split=split)
            yield record["sidecar"]["audit"]["example_id"], batch


def read_bundle(root, *, expected_digest, config):
    root = Path(root)
    manifest = document(root / "manifest.json", digest=expected_digest, limit=4 * 1024**2)
    _check_manifest(manifest, schema="toolalign.cuda-sft-arrays.v1", config=config)
    require(sum(v["bytes"] for v in manifest["artifacts"].values()) <= MAX_BUNDLE_BYTES, "array_byte_limit")
    require(manifest["tokenizer"]["repo_id"] == manifest["model"]["model_id"]
            and manifest["tokenizer"]["revision"] == manifest["model"]["model_revision"]
            and manifest["tokenizer"]["engine"] == "tokenizers", "array_tokenizer_identity")
    metadata, ids = {}, {}
    for split in ("train", "validation"):
        metadata[split], ids[split] = [], []
        for record in _lines(root, manifest, split):
            checked_batch(record, config=config, profile=manifest["profile"], split=split)
            metadata[split].append({"sidecar": record["sidecar"]})
            ids[split].append(record["sidecar"]["audit"]["example_id"])
    _check_selection(metadata, manifest, config)
    require(manifest["new_sequence_calls"] == sum(len(v) for v in ids.values()), "encoding_coverage")
    return ArrayBundle(root, manifest, expected_digest, config, ids)
