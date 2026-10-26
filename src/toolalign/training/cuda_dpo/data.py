"""Bind D1/Q1 artifacts and preserve the exact original Action JSON strings."""

from __future__ import annotations

import json
from pathlib import Path

from toolalign.contracts import canonical_hash, validate_record
from toolalign.data.preferences.review import apply_review
from toolalign.model_io.format import prompt_messages, validate_action, validate_model_input
from toolalign.training.cuda_sft.protocol import (
    canonical_sha,
    document,
    encoded,
    read_bytes,
    require,
    sha,
    write_bytes,
)

INPUT_FILES = (
    "preferences.jsonl", "lineage.jsonl", "q1-sample.json", "q1-review.json",
    "training-preferences.jsonl", "review-result.json",
)


def reviewed_input(contents):
    require(set(contents) == set(INPUT_FILES), "DPO_review_input_files")
    values = {name: ([json.loads(line) for line in raw.splitlines() if line.strip()]
                     if name.endswith(".jsonl") else json.loads(raw))
              for name, raw in contents.items()}
    packet = values["q1-sample.json"]
    require(packet["synthetic"] is False, "synthetic_preferences_cannot_train")
    result = apply_review(packet, values["preferences.jsonl"], values["lineage.jsonl"],
                          values["q1-review.json"])
    training = result.pop("training_preferences")
    result.pop("remaining_preferences")
    require(result["dpo_quality_gate"] == "PASS" and result["quality_pass"] is True,
            "Q1_preference_quality_gate")
    require(result == values["review-result.json"], "Q1_review_result_mismatch")
    require(training == values["training-preferences.jsonl"] and 0 < len(training) <= 128,
            "Q1_training_list_mismatch_or_empty")
    lineage = {row["preference_id"]: row for row in values["lineage.jsonl"]}
    for record in training:
        row = lineage[record["preference_id"]]
        require(record["split"] == "train" and row["synthetic"] is False
                and row["prompt_hash"] == record["prompt_hash"]
                and row["chosen"]["generation_parameters"] == record["generation_parameters"],
                "DPO_preference_lineage")
        require(all(row["trace_hashes"][side] == record[side + "_validation"]["trace_hash"]
                    for side in ("chosen", "rejected")), "DPO_trace_lineage")
    return training, result


def bind_input(*, extraction, reviewed, review, output):
    """Package an already completed Q1 review; this grants no execution authority."""
    paths = {name: Path(extraction) / name for name in INPUT_FILES[:3]}
    paths.update({"q1-review.json": Path(review),
                  "training-preferences.jsonl": Path(reviewed) / "training-preferences.jsonl",
                  "review-result.json": Path(reviewed) / "review-result.json"})
    contents = {name: read_bytes(path, limit=64 * 1024**2) for name, path in paths.items()}
    training, result = reviewed_input(contents)
    manifest = {"schema": "toolalign.dpo-input.v1", "synthetic": False,
                "is_run_authorization": False, "q1_result": result,
                "training_ids": [p["preference_id"] for p in training],
                "files": {name: {"bytes": len(raw), "sha256": sha(raw)}
                          for name, raw in contents.items()}}
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, raw in contents.items():
        write_bytes(output / name, raw)
    raw = encoded(manifest) + b"\n"
    write_bytes(output / "input-manifest.json", raw)
    return {"input_manifest_sha256": sha(raw), "training_pairs": len(training),
            "q1_reviewer": result["reviewer"], "formal_DPO": "NOT_RUN"}


def read_input(root, expected_sha):
    root = Path(root)
    manifest = document(root / "input-manifest.json", digest=expected_sha, limit=4 * 1024**2)
    require(manifest.get("schema") == "toolalign.dpo-input.v1" and manifest.get("synthetic") is False
            and set(manifest["files"]) == set(INPUT_FILES), "DPO_input_manifest")
    contents = {}
    for name, spec in manifest["files"].items():
        raw = read_bytes(root / name, limit=64 * 1024**2)
        require(len(raw) == spec["bytes"] and sha(raw) == spec["sha256"], "DPO_input_file_identity")
        contents[name] = raw
    training, result = reviewed_input(contents)
    require(result == manifest["q1_result"]
            and manifest["training_ids"] == [p["preference_id"] for p in training],
            "DPO_input_manifest_binding")
    return training, manifest


def prepare_rows(preferences, tokenizer, *, context_cap=2048):
    """Check joint/independent encoding; retain original denominators on overflow."""
    rows, expected, dispositions = [], [], []
    for original in preferences:
        record = validate_record(original, "preference")
        require(record["split"] == "train", "DPO_train_split_required")
        model_input = validate_model_input({"messages": record["messages"], "tools": record["tools"]})
        require(record["prompt_hash"] == canonical_hash(model_input), "DPO_prompt_hash")
        prompt = tokenizer.render(prompt_messages(model_input), tools=None,
                                  add_generation_prompt=True, enable_thinking=False)
        prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
        require(prompt_ids, "DPO_empty_prompt")
        tokenized = {"preference_id": record["preference_id"], "prompt_input_ids": prompt_ids}
        lengths = {}
        for side in ("chosen", "rejected"):
            raw = record[side]
            validate_action(json.loads(raw))
            completion = tokenizer.encode(raw, add_special_tokens=False)
            joined = tokenizer.encode(prompt + raw, add_special_tokens=False)
            require(joined[:len(prompt_ids)] == prompt_ids, "DPO_prompt_completion_boundary")
            require(joined[len(prompt_ids):] == completion, "DPO_separate_completion_encoding")
            require(completion and tokenizer.eos_token_id not in completion,
                    "DPO_empty_or_embedded_EOS")
            require(tokenizer.decode(completion, skip_special_tokens=False) == raw,
                    "DPO_raw_completion_roundtrip")
            tokenized[side + "_input_ids"] = completion + [tokenizer.eos_token_id]
            lengths[side + "_tokens_including_eos"] = len(joined) + 1
        accepted = max(lengths.values()) <= context_cap
        dispositions.append({"preference_id": record["preference_id"], **lengths,
                             "disposition": "accepted" if accepted else "context_overflow",
                             "token_identity": canonical_sha(tokenized)})
        if accepted:
            rows.append({"preference_id": record["preference_id"], "prompt": prompt,
                         "chosen": record["chosen"], "rejected": record["rejected"]})
            expected.append(tokenized)
    return {"rows": rows, "expected": expected, "dispositions": dispositions,
            "original_pairs": len(preferences), "accepted_pairs": len(rows),
            "excluded_pairs": len(preferences) - len(rows)}


def prepare_input(root, input_sha, tokenizer, *, config_sha):
    preferences, manifest = read_input(root, input_sha)
    prepared = prepare_rows(preferences, tokenizer)
    identity = {"input_manifest_sha256": input_sha, "config_sha256": config_sha,
                "tokenizer": tokenizer.identity, "prepared": prepared}
    summary = {key: prepared[key] for key in ("original_pairs", "accepted_pairs", "excluded_pairs")}
    summary.update(prepared_data_sha256=canonical_sha(identity),
                   total_optimizer_steps=(prepared["accepted_pairs"] + 7) // 8,
                   original_review_denominator=manifest["q1_result"]["original_review_denominator"],
                   q1_reviewer=manifest["q1_result"]["reviewer"],
                   dispositions=prepared["dispositions"])
    return prepared, summary
