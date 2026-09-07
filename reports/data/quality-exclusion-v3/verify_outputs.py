"""Check the two existing v3 outputs; this command never creates another build."""

import argparse
import json
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data import quality_adjudication as a
from toolalign.data import quality_exclusion as x
from toolalign.data import quality_revision as q


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("config", "inputs", "first", "second", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    args = parser.parse_args()
    inputs = x.bound_inputs(config_path=args.config, input_root=args.inputs)
    expected, manifest = x.stable_artifacts(inputs)
    runs = [a.verify_artifacts(root, expected, x.consumer_identity()) for root in (args.first, args.second)]
    assert runs[0]["created_at_utc"] != runs[1]["created_at_utc"]
    for name in expected:
        assert (args.first / name).read_bytes() == (args.second / name).read_bytes()
    original = inputs["parent"]
    sources = inputs["sources"]
    assert len(sources) == 84 and len(inputs["review_decisions"]) == 103
    assert {s: sources[s] for s in original["sources"]} == original["sources"]
    assert {i: inputs["review_decisions"][i] for i in original["review_decisions"]} == original["review_decisions"]
    new = inputs["delta"]["new_sources"][0]
    assert new["source_training_fitness"] == "fail" and new["disposition"] == "exclude_entire_source"
    new_ids = set(new["example_ids"])
    assert len(new_ids) == 2
    for ident in new_ids:
        assert inputs["review_decisions"][ident]["action_verdict"] == "pass"
    effective = json.loads(expected["effective/identities.json"])
    previous = json.loads(inputs["parent_artifacts"]["effective/identities.json"])
    excluded = json.loads(expected["excluded/identities.json"])
    restored = json.loads(expected["restored/identities.json"])
    assert len(excluded) == 100 and len(restored) == 3
    assert len({original["index"]["examples"][i]["source_record_hash"] for i in excluded}) == 81
    assert expected["restored/identities.json"] == inputs["parent_artifacts"]["restored/identities.json"]
    assert expected["staging-reference.json"] == inputs["parent_artifacts"]["staging-reference.json"]
    assert set(effective["train"]) == set(previous["train"]) - new_ids
    assert effective["validation"] == previous["validation"]
    same_group = {i for i in previous["train"] if original["index"]["examples"][i]["group_id"] == new["group_id"]
                  and original["index"]["examples"][i]["source_record_hash"] != new["source_record_hash"]}
    assert same_group <= set(effective["train"])
    delta = json.loads(expected["delta-from-v2.json"])["sets"]
    assert set(delta["formal/train"]["removed_original_ids"]) == new_ids
    assert delta["smoke/train"]["removed_original_ids"] == []
    assert all(not entry["restored_original_ids"] for entry in delta.values())
    previous_rows = x.selection_rows(inputs["parent_artifacts"])
    rank_changes, rows_checked, byte_checks = {}, 0, 0
    for split in q.SPLITS:
        values, lines = q.jsonl(expected["effective/" + split + ".jsonl"])
        for e, line in zip(values, lines, strict=True):
            assert line == original["original_bytes"][e["example_id"]]
            byte_checks += 1
        for profile in q.PROFILES:
            prefix = f"selection/{profile}/{split}"
            values, lines = q.jsonl(expected[prefix + ".examples.jsonl"])
            sidecars = q.jsonl(expected[prefix + ".sidecars.jsonl"])[0]
            assert [r["selection_rank"] for r in sidecars] == list(range(1, len(sidecars) + 1))
            changes = 0
            for e, line, row in zip(values, lines, sidecars, strict=True):
                ident = e["example_id"]
                old = previous_rows[profile][split][ident]
                assert line == original["parent_lines"][profile + "/" + split][ident]
                assert all(type(row[k]) is int for k in ("selection_rank", "parent_selection_rank", "previous_selection_rank"))
                assert row["previous_selection_rank"] == old["selection_rank"]
                assert row["parent_selection_rank"] == old["parent_selection_rank"]
                assert row["previous_selection_sidecar_sha256"] == canonical_hash(old)
                a.same(row["audit"], old["audit"], "verification_previous_audit")
                changes += row["selection_rank"] != row["previous_selection_rank"]
                rows_checked += 1
                byte_checks += 1
            rank_changes[profile + "/" + split] = changes
    assert rank_changes["formal/train"] > 0
    training = json.loads(expected["training-binding.json"])
    assert training["planning_deviation"]["shortfall"] == 62
    assert training["training_authorized"] is False and training["trainer_consumption"] == "NOT_RUN_PENDING_SEPARATE_ADAPTATION"
    result = {"status": "PASS", "full_data_builds": 2, "additional_output_builds": 0, "stable_artifacts_per_build": len(expected),
        "stable_manifest_sha256": q.sha(expected["manifest.json"]), "quality_revision_sha256": manifest["quality_revision_sha256"],
        "counts": manifest["counts"], "sources": len(sources), "local_decisions": len(inputs["review_decisions"]),
        "excluded_sources": 81, "excluded_decisions": 100, "restored_sources": 3, "restored_decisions": 3,
        "previously_effective_same_group_decisions_preserved": len(same_group), "selection_sidecars_checked": rows_checked,
        "original_jsonl_line_checks": byte_checks, "continuous_rank_changes_from_v2": rank_changes,
        "stable_artifacts": {k: q.sha(v) for k, v in expected.items()}, "training_authorized": False}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "stable_artifacts"}))


if __name__ == "__main__":
    main()
