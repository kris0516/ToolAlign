"""Read fixed selections and compare all 13 existing arrays without re-encoding.

No original selected record is written. Small negative inputs and summaries go
only to the new private output. The existing verifier recomputes in memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import fields
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError
from toolalign.data.training_selection import new_private_directory
from toolalign.model_io import Sequence
from toolalign.training.sft import collate_sequence, prepare


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def rows(path):
    with Path(path).open() as stream:
        for line in stream:
            yield json.loads(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--t1-private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = read(args.inputs)
    output = new_private_directory(args.output)
    frozen = read(args.t1_private / "collator/frozen-before.json")
    assert all(sha(name) == expected for name, expected in frozen.items())
    data_manifest = Path(inputs["prepare"]["data_manifest_path"])
    original_artifacts = {str(data_manifest.parent / name): expected
                          for name, expected in read(data_manifest)["artifacts"].items()}
    assert len(original_artifacts) == 18
    assert all(sha(name) == expected for name, expected in original_artifacts.items())
    views, report = prepare(**inputs["prepare"])
    save(output / "preparation.json", report)
    manifest = read(Path(inputs["selection_path"]) / "manifest.json")
    expected_counts = {"smoke": {"train": 1600, "validation": 197},
                       "formal": {"train": 6013, "validation": 217}}
    view_results = {}
    all_ids = set()
    for profile, splits in expected_counts.items():
        view_results[profile] = {}
        for split, count in splits.items():
            view = views[profile][split]
            assert len(view) == count
            directory = Path(inputs["selection_path"]) / profile
            original_examples = list(rows(directory / (split + ".examples.jsonl")))
            original_sidecars = list(rows(directory / (split + ".sidecars.jsonl")))
            assert len(original_examples) == len(original_sidecars) == count
            ids, keys, buckets = [], [], Counter()
            for position, (row, example, sidecar) in enumerate(zip(view.rows, original_examples,
                                                                   original_sidecars, strict=True), 1):
                assert row.example == example and row.sidecar == sidecar
                assert example["split"] == sidecar["split"] == split
                assert sidecar["profile"] == profile and sidecar["selection_rank"] == position
                key = (canonical_hash(["toolalign.training-selection.v1", 42, example["example_id"]]),
                       example["example_id"])
                assert sidecar["ranking_sha256"] == key[0]
                allowed = manifest["config"]["profiles"][profile]["padding_buckets"]
                assert sidecar["padding_bucket"] == min(bucket for bucket in allowed
                                                        if bucket >= sidecar["audit"]["total_tokens"])
                assert sidecar["audit"]["example_sha256"] == canonical_hash(example)
                row.example["messages"][0]["content"] = "R1 transient returned-copy mutation"
                row.sidecar["audit"]["source"] = "R1 transient returned-copy mutation"
                assert row.example == example and row.sidecar == sidecar
                ids.append(example["example_id"])
                keys.append(key)
                buckets[sidecar["padding_bucket"]] += 1
            assert len(set(ids)) == count and keys == sorted(keys)
            assert canonical_hash(ids) == view.identity_sha256
            assert view.selection_sha256 == canonical_hash(manifest)
            all_ids.update(ids)
            view_results[profile][split] = {"count": count, "identity_sha256": canonical_hash(ids),
                                            "buckets": dict(buckets), "all_original_values_equal": True}

    cases = []
    names = [f"actual-{number:02d}" for number in range(1, 11)] + [
        "protocol-clarify", "protocol-final", "protocol-refuse"]
    for name in names:
        native_path = Path(inputs["native"]) / (name + ".json")
        reference_path = Path(inputs["reference"]) / (name + ".json")
        old, reference = read(native_path), read(reference_path)
        current_path = args.t1_private / "collator" / (name + ".json")
        current = read(current_path)
        assert old["case"] == reference["case"] == current["case"]
        old_sequence = old["sequence"]
        values = {field.name: old_sequence[field.name] for field in fields(Sequence)}
        for key in ("prompt_ids", "concatenated_ids", "sequence_ids", "loss_mask"):
            values[key] = tuple(values[key])
        sequence = Sequence(**values)
        derived = sequence.record() | {
            "causal_input_ids": list(sequence.sequence_ids[:-1]),
            "causal_target_ids": list(sequence.sequence_ids[1:]),
            "causal_input_ids_sha256": canonical_hash(list(sequence.sequence_ids[:-1])),
            "causal_target_ids_sha256": canonical_hash(list(sequence.sequence_ids[1:])),
        }
        assert derived == old_sequence == reference["sequence"] == current["sequence"]
        batch = collate_sequence(sequence, bucket=old["padding"]["bucket"], pad_token_id=151643)
        assert batch.record() == old["padding"] == reference["padding"] == current["collator"]
        p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
        positions = [i for i, mask in enumerate(batch.causal_loss_mask) if mask]
        assert positions == list(range(p - 1, n - 1))
        assert sum(batch.causal_loss_mask) == n - p
        assert sequence.sequence_ids[p:].count(151645) == 1
        assert sequence.sequence_ids[-1] == batch.causal_target_ids[n - 2] == 151645
        case = old["case"]
        if name.startswith("actual-"):
            profile = case["primary_profile"]
            row = views[profile]["train"][case["profiles"][profile]["selection_rank"] - 1]
            assert row.example == case["example"] and row.sidecar["audit"] == case["audit"]
        else:
            assert case["example"]["example_id"] not in all_ids
        cases.append({"case_id": name, "native_sha256": sha(native_path),
                      "reference_sha256": sha(reference_path), "t1_collator_sha256": sha(current_path),
                      "full_sequence_equal": True, "all_collator_arrays_equal": True,
                      "first": p - 1, "last": n - 2, "tokens": n - p, "bucket": batch.bucket})

    rejections = []
    for key in ("sft_config_path", "public_selection_manifest_path", "config_path", "data_manifest_path", "protocol_path",
                "representation_path", "audit_path"):
        changed = output / ("changed-" + key + ".json")
        save(changed, {"artifacts": {}} if key == "data_manifest_path" else {"original_r1_rejection": key})
        altered = dict(inputs["prepare"], **{key: str(changed)})
        try:
            prepare(**altered)
        except DataError as exc:
            rejections.append({"kind": key, "error": str(exc), "input_sha256": sha(changed)})
        else:
            raise AssertionError(key + " accepted")
    # Only the original small manifest is copied. No selected Example, sidecar,
    # or whole corpus is copied/materialized to exercise this output failure.
    missing = new_private_directory(output / "missing-selected-output")
    with (missing / "manifest.json").open("xb") as stream:
        stream.write((Path(inputs["selection_path"]) / "manifest.json").read_bytes())
    try:
        prepare(**dict(inputs["prepare"], selection_path=str(missing)))
    except DataError as exc:
        assert str(exc) == "selection_artifact_set_mismatch"
        rejections.append({"kind": "missing_selected_output", "error": str(exc)})
    else:
        raise AssertionError("missing selected output accepted")
    assert all(sha(name) == expected for name, expected in frozen.items())
    assert all(sha(name) == expected for name, expected in original_artifacts.items())
    forbidden = {"mlx", "mlx_lm", "torch", "transformers", "tokenizers"}
    assert not forbidden & {name.split(".")[0] for name in sys.modules}
    result = {"status": "PASS", "views": view_results, "cases": cases, "rejections": rejections,
              "new_real_case_tokenizations": 0, "new_selection_materializations": 0,
              "model_frameworks_loaded": [], "source_inputs": inputs["prepare"],
              "source_input_hashes": {name: sha(path) for name, path in inputs["prepare"].items()
                                      if name != "selection_path"},
              "old_frozen_files_unchanged": len(frozen), "human_review": "PENDING"}
    result["original_artifacts_hashes_only"] = original_artifacts
    save(output / "summary.json", result)
    print(json.dumps({"status": "PASS", "views": 4, "cases": len(cases),
                      "fixed_input_output_rejections": len(rejections), "new_tokenizations": 0}))


if __name__ == "__main__":
    main()
