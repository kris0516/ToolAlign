"""Independently join existing v1/v2/v3 bytes without importing a producer."""

import argparse
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def rows(data):
    lines = data.splitlines(keepends=True)
    values = [json.loads(line) for line in lines]
    assert len(values) == len({v["example_id"] for v in values})
    return values, {v["example_id"]: line for v, line in zip(values, lines, strict=True)}


def audit(inputs, output, original_outputs):
    input_manifest = json.loads((inputs / "manifest.json").read_bytes())
    assert sha((inputs / "manifest.json").read_bytes()) == "ebbaf56bbb5730b5d31eca195d5ac7772d148ff876fc96be1c1c5dbbadf51e06"

    def original(name):
        item = input_manifest["files"][name]
        assert item.get("read_mode") != "hash_only_no_deserialization"
        path = Path(item["path"]) if item["kind"] == "immutable_existing_artifact" else inputs / name
        data = path.read_bytes()
        assert sha(data) == item["sha256"] and len(data) == item["bytes"]
        return data

    manifest_data = (output / "manifest.json").read_bytes()
    assert sha(manifest_data) == "f4569b8b16a6c42bd500cc7c977561b770435954e42ced177e36e857b9776437"
    manifest = json.loads(manifest_data)
    assert manifest["quality_revision_sha256"] == "919ee616fd11993f39bbab6d38146ea827f4bbc3d7bafc07aae0e2c7dd95e5c8"
    stable = {"manifest.json": manifest_data}
    for name, expected in manifest["artifacts"].items():
        data = (output / name).read_bytes()
        assert sha(data) == expected["sha256"] and len(data) == expected["size_bytes"]
        stable[name] = data
    assert len(stable) == 29
    for directory in (output, *original_outputs):
        names = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
        assert names == set(stable) | {"run.json"}
        assert all((directory / name).read_bytes() == data for name, data in stable.items())
    delta = json.loads(original("source-exclusion-delta.json"))["new_sources"]
    assert len(delta) == 1 and len(delta[0]["example_ids"]) == 2
    removed = set(delta[0]["example_ids"])
    previous, original_lines, previous_values = {}, {}, {}
    for split in ("train", "validation"):
        old, lines = rows(original("parent-revision/effective/" + split + ".jsonl"))
        previous[split] = old
        original_lines.update(lines)
        previous_values.update({r["example_id"]: r for r in old})
    excluded_before, lines = rows(original("parent-revision/excluded/examples.jsonl"))
    original_lines.update(lines)
    original_values = {**previous_values, **{r["example_id"]: r for r in excluded_before}}
    assert len(original_values) == len(original_lines) == 7749
    assert {i for i, r in original_values.items() if r["source_record_hash"] == delta[0]["source_record_hash"]} == removed
    effective_ids = set()
    line_checks, sidecar_checks, rank_changes = 0, 0, {}
    for split in ("train", "validation"):
        current, current_lines = rows(stable["effective/" + split + ".jsonl"])
        assert [v["example_id"] for v in current] == [v["example_id"] for v in previous[split] if v["example_id"] not in removed]
        effective_ids.update(current_lines)
        for ident, line in current_lines.items():
            assert line == original_lines[ident]
            line_checks += 1
        old_lineage = rows(original("parent-revision/effective/lineage.jsonl"))[1]
        for ident, line in rows(stable["effective/lineage.jsonl"])[1].items():
            assert line == old_lineage[ident]
        for profile in ("formal", "smoke"):
            prefix = f"selection/{profile}/{split}"
            old, old_lines = rows(original("parent-revision/" + prefix + ".examples.jsonl"))
            current, current_lines = rows(stable[prefix + ".examples.jsonl"])
            assert [r["example_id"] for r in current] == [r["example_id"] for r in old if r["example_id"] not in removed]
            original_sidecars = [json.loads(line) for line in original(f"parent-inputs/parent_selection/{profile}/{split}.sidecars.jsonl").splitlines()]
            v1 = {r["audit"]["example_id"]: r for r in original_sidecars}
            v2 = {r["audit"]["example_id"]: r for r in [json.loads(line) for line in original("parent-revision/" + prefix + ".sidecars.jsonl").splitlines()]}
            v3 = [json.loads(line) for line in stable[prefix + ".sidecars.jsonl"].splitlines()]
            assert len(v3) == len(current)
            changed = 0
            for ordinal, (value, sidecar) in enumerate(zip(current, v3, strict=True), 1):
                ident = value["example_id"]
                old_row = v2[ident]
                assert current_lines[ident] == old_lines[ident] == original_lines[ident]
                assert all(type(sidecar[k]) is int for k in ("selection_rank", "parent_selection_rank", "previous_selection_rank"))
                assert sidecar["selection_rank"] == ordinal
                assert sidecar["parent_selection_rank"] == v1[ident]["selection_rank"] == old_row["parent_selection_rank"]
                assert sidecar["previous_selection_rank"] == old_row["selection_rank"]
                assert packed(sidecar["audit"]) == packed(old_row["audit"])
                assert sidecar["previous_selection_sidecar_sha256"] == sha(packed(old_row))
                assert sidecar["previous_selection_manifest_sha256"] == sha(original("parent-revision/selection/manifest.json"))
                changed += ordinal != old_row["selection_rank"]
                sidecar_checks += 1
                line_checks += 1
            rank_changes[profile + "/" + split] = changed
    excluded = json.loads(stable["excluded/identities.json"])
    assert set(excluded) == {r["example_id"] for r in excluded_before} | removed
    assert not effective_ids & set(excluded) and len(excluded) == 100
    assert effective_ids | set(excluded) == set(original_values)
    for ident, line in rows(stable["excluded/examples.jsonl"])[1].items():
        assert line == original_lines[ident]
    for name in ("restored/identities.json", "restored/examples.jsonl", "restored/lineage.jsonl", "staging-reference.json"):
        assert stable[name] == original("parent-revision/" + name)
    sources = [json.loads(line) for line in stable["dispositions/sources.jsonl"].splitlines()]
    old_sources = [json.loads(line) for line in original("parent-revision/dispositions/sources.jsonl").splitlines()]
    assert len(sources) == 84 and len(old_sources) == 83
    by_source = {s["source_record_hash"]: s for s in sources}
    assert all(packed(by_source[s["source_record_hash"]]) == packed(s) for s in old_sources)
    excluded_sources = {s["source_record_hash"] for s in sources if s["disposition"] == "exclude_entire_source"}
    restored_sources = {s["source_record_hash"] for s in sources if s["disposition"] == "restore_original_source"}
    assert len(excluded_sources) == 81 and len(restored_sources) == 3
    assert {original_values[i]["source_record_hash"] for i in excluded} == excluded_sources
    groups = {by_source[s]["group_id"] for s in excluded_sources}
    others = {i for i, r in original_values.items() if r["group_id"] in groups and r["source_record_hash"] not in excluded_sources}
    assert others <= effective_ids and len(others) == manifest["other_decisions_retained_in_affected_groups"] == 5551
    assert len({original_values[i]["source_record_hash"] for i in others}) == manifest["other_sources_retained_in_affected_groups"] == 5181
    target_group = {i for i, r in previous_values.items() if r["group_id"] == delta[0]["group_id"] and r["source_record_hash"] != delta[0]["source_record_hash"]}
    assert target_group <= effective_ids and len(target_group) == 5532
    reasons = [json.loads(line) for line in stable["dispositions/examples.jsonl"].splitlines()]
    assert len(reasons) == 7749
    assert sum(row["local_action_review"] is not None for row in reasons) == 103
    assert {r["local_action_review"]["action_verdict"] for r in reasons if r["example_id"] in removed} == {"pass"}
    training = json.loads(stable["training-binding.json"])
    assert training["training_authorized"] is False and training["planning_deviation"]["shortfall"] == 62
    assert training["trainer_consumption"] == "NOT_RUN_PENDING_SEPARATE_ADAPTATION"
    assert line_checks == 15577 and sidecar_checks == 7928 and rank_changes["formal/train"] > 0
    return {"status": "PASS_STDLIB_INDEPENDENT_V3_DATA_JOIN", "stable_files_each": 29,
            "existing_d1_outputs_compared": len(original_outputs), "new_r1_builds": 1,
            "manifest_sha256": sha(manifest_data), "quality_revision_sha256": manifest["quality_revision_sha256"],
            "counts": manifest["counts"], "original_line_checks": line_checks, "three_generation_sidecars": sidecar_checks,
            "rank_changes_from_v2": rank_changes, "excluded_sources": 81, "excluded_decisions": 100,
            "restored_sources": 3, "restored_decisions": 3, "inherited_source_dispositions": 83,
            "new_source_decisions_removed": 2, "same_group_other_previous_decisions_retained": len(target_group),
            "all_affected_groups_other_sources_retained": 5181, "all_affected_groups_other_decisions_retained": 5551,
            "heldout_semantic_reads": 0, "producer_imports": 0, "training_authorized": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("inputs", "revision", "first", "second", "output"):
        parser.add_argument("--" + flag, required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.inputs, args.revision, [args.first, args.second])
    with args.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(result, sort_keys=True))
