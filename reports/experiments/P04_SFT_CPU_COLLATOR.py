"""One new native encoding of the frozen 10 selected + 3 original protocol cases."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from P04_SFT_CPU_COMMAND import save, sha

from toolalign.contracts import canonical_hash
from toolalign.data.common import file_hash
from toolalign.data.training_selection import new_private_directory, verify
from toolalign.model_io import training_sequence
from toolalign.model_io.offline import OfflineQwenTokenizer, model_modules_loaded
from toolalign.training.sft import collate_selected, collate_sequence, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = json.loads(args.inputs.read_text())
    out = new_private_directory(args.output)
    roots = {name: Path(inputs[name]) for name in ("selection_path", "selection_b", "native", "reference")}
    frozen = {str(p): file_hash(p) for root in roots.values() for p in root.rglob("*") if p.is_file()}
    save(out / "frozen-before.json", frozen)
    views, preparation = prepare(**inputs["prepare"])
    save(out / "preparation.json", preparation)
    manifest_b = verify(output=roots["selection_b"], **inputs["bound_inputs"])
    assert canonical_hash(manifest_b) == preparation["selection_sha256"]
    adapters = {profile: OfflineQwenTokenizer(inputs["tokenizer_root"], repo_id=repo, revision=rev)
                for profile, repo, rev in (
                    ("smoke", "Qwen/Qwen3-0.6B", "c1899de289a04d12100db370d81485cdf75e47ca"),
                    ("formal", "Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"))}
    names = [f"actual-{n:02d}" for n in range(1, 11)] + ["protocol-clarify", "protocol-final", "protocol-refuse"]
    results, outputs = [], []
    for name in names:
        old = json.loads((roots["native"] / (name + ".json")).read_text())
        reference = json.loads((roots["reference"] / (name + ".json")).read_text())
        case = old["case"]
        assert case == reference["case"]
        tokenizer = adapters[case["primary_profile"]]
        if name.startswith("actual-"):
            view = views[case["primary_profile"]]["train"]
            row = view[case["profiles"][case["primary_profile"]]["selection_rank"] - 1]
            assert row.example == case["example"] and row.sidecar["audit"] == case["audit"]
            sequence, batch = collate_selected(row, tokenizer=tokenizer)
        else:
            # These exact original protocol fixtures stay outside both views.
            assert all(case["example"]["example_id"] != row.example["example_id"]
                       for splits in views.values() for view in splits.values() for row in view.rows)
            sequence = training_sequence(case["example"], **tokenizer.callbacks())
            batch = collate_sequence(sequence, bucket=old["padding"]["bucket"], pad_token_id=151643)
        record = sequence.record() | {"causal_input_ids": list(sequence.causal_input_ids),
            "causal_target_ids": list(sequence.causal_target_ids),
            "causal_input_ids_sha256": canonical_hash(list(sequence.causal_input_ids)),
            "causal_target_ids_sha256": canonical_hash(list(sequence.causal_target_ids))}
        assert record == old["sequence"] == reference["sequence"], name + " sequence"
        assert batch.record() == old["padding"] == reference["padding"], name + " collator arrays"
        current = {"case": case, "sequence": record, "collator": batch.record()}
        save(out / (name + ".json"), current)
        outputs.append(current)
        results.append({"case_id": name, "category": case["category"],
            "native_file_sha256": file_hash(roots["native"] / (name + ".json")),
            "reference_file_sha256": file_hash(roots["reference"] / (name + ".json")),
            "new_file_sha256": file_hash(out / (name + ".json")), "all_arrays_equal": True,
            "bucket": batch.bucket, "supervised_tokens": batch.effective_supervised_targets,
            "first_position": batch.first_supervised_causal_position,
            "last_position": batch.last_supervised_causal_position})
    assert not model_modules_loaded()
    assert {p: file_hash(p) for p in frozen} == frozen
    summary = {"status": "PASS", "actual_selected": 10, "protocol_only": 3,
        "new_native_encodings": 13, "full_selected_encodings": 0, "new_reference_encodings": 0,
        "cases": results, "outputs_canonical_sha256": canonical_hash(outputs),
        "preparation_sha256": file_hash(out / "preparation.json"),
        "frozen_file_count": len(frozen), "frozen_sha256": file_hash(out / "frozen-before.json"),
        "tokenizers": {p: t.identity for p, t in adapters.items()}, "model_modules_loaded": [],
        "formal_train_buckets": dict(Counter(r.sidecar["padding_bucket"] for r in views["formal"]["train"].rows)),
        "human_review": "PENDING", "actual_browser_observation": "NOT_RUN", "formal_training": "NOT_RUN"}
    save(out / "summary.json", summary)
    print(json.dumps({"status": "PASS", "cases": 13, "summary_sha256": sha((out / "summary.json").read_bytes())}))


if __name__ == "__main__":
    main()
