"""Compare independently collected tokenizer evidence and emit aggregate metadata."""

import argparse
import json

from toolalign.contracts import canonical_hash
from toolalign.data.common import file_hash, read_json, write_json


def compare(local, reference):
    local_by_id = {r["id"]: r for r in local["results"]}
    reference_by_id = {r["id"]: r for r in reference["results"]}
    if set(local_by_id) != set(reference_by_id):
        raise ValueError("fixture_set_mismatch")
    rows = []
    fields = (
        "example_hash",
        "prompt_text",
        "completion_text",
        "prompt_ids",
        "concatenated_ids",
        "sequence_ids",
        "eos_token_id",
        "prefix_stable",
    )
    for name in sorted(local_by_id):
        observed, expected = local_by_id[name], reference_by_id[name]
        differences = [field for field in fields if observed[field] != expected[field]]
        measurement = observed["local_normalized_measurement"]
        if expected["prefix_stable"]:
            length_matches = (
                measurement.get("total_tokens") == expected["sequence_length"]
                and measurement.get("prompt_tokens") == len(expected["prompt_ids"])
                and measurement.get("completion_tokens") == expected["completion_length_if_stable"]
            )
        else:
            length_matches = measurement == {"rejection": "prompt_completion_boundary_changed"}
        if differences or not length_matches:
            raise ValueError("tokenizer_or_sequence_policy_mismatch")
        rows.append(
            {
                "id": name,
                "exact_fields_match": True,
                "length_policy_matches": True,
                "prefix_stable": expected["prefix_stable"],
                "prompt_tokens": len(expected["prompt_ids"]),
                "concatenated_tokens": len(expected["concatenated_ids"]),
                "total_tokens_including_appended_eos": expected["sequence_length"],
                "completion_tokens_if_stable": expected["completion_length_if_stable"],
                "terminal_eos_run": expected["terminal_eos_run"],
                "sequence_ids_hash": canonical_hash(expected["sequence_ids"]),
            }
        )
    return {
        "case_count": len(rows),
        "stable_case_count": sum(r["prefix_stable"] for r in rows),
        "local_packages": local["packages"],
        "reference_packages": reference["packages"],
        "results": rows,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    from pathlib import Path

    target = Path(args.output).resolve()
    if ".toolalign-local" not in target.parts or target.exists():
        raise ValueError("Use a new private output path")
    result = compare(read_json(args.local), read_json(args.reference))
    result.update(
        local_evidence_sha256=file_hash(args.local),
        reference_evidence_sha256=file_hash(args.reference),
    )
    write_json(target, result)
    print(
        json.dumps(
            {
                "case_count": result["case_count"],
                "stable_case_count": result["stable_case_count"],
                "comparison": "PASS",
                "evidence_sha256": file_hash(target),
            }
        )
    )


if __name__ == "__main__":
    main()
