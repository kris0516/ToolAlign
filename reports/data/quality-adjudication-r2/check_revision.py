"""Stdlib cross-check of two real v2 builds; no producer or tokenizer imports.

This worker verification reads authorized train/validation and frozen metadata.
Final test/ood payloads are hashed only. It does not sign independent acceptance.
"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def canonical(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def rows(path):
    lines = Path(path).read_bytes().splitlines(keepends=True)
    assert all(line.endswith(b"\n") for line in lines)
    return [json.loads(line) for line in lines], lines


def same(actual, expected):
    assert encoded(actual) == encoded(expected)


def check(args):
    paths = read(args.inputs)
    cfg = read(paths["config_path"])
    assert digest(paths["config_path"]) == "7cf53c23568cd06c9543f253d9636b4655b135f0e6daf0eb318ace2100807ccb"
    input_root = Path(paths["input_root"])
    fixed = read(input_root / "manifest.json")
    assert digest(input_root / "manifest.json") == cfg["input_bindings"]["input_manifest_file_sha256"]
    files = {}
    for name, info in fixed["files"].items():
        path = Path(info["path"]) if info["kind"] == "immutable_existing_artifact" else input_root / name
        assert digest(path) == info["sha256"] and path.stat().st_size == info["bytes"] and not path.is_symlink()
        files[name] = path
    sources = {r["source_record_hash"]: r for r in read(files["dispositions.json"])["sources"]}
    excluded_sources = {s for s, r in sources.items() if r["disposition"] == "exclude_entire_source"}
    restored_sources = set(sources) - excluded_sources
    assert len(excluded_sources) == 80 and len(restored_sources) == 3
    assert Counter(s["source_training_fitness"] for s in sources.values()) == {"fail": 24, "unknown": 56, "pass": 3}
    first, second = Path(args.first), Path(args.second)
    left, right = read(first / "manifest.json"), read(second / "manifest.json")
    same(left, right)
    same(left["counts"], cfg["expected_counts"])
    assert left["training_authorized"] is False and canonical(left["quality_revision"]) == left["quality_revision_sha256"]
    for root in (first, second):
        assert not any(p.is_symlink() for p in root.rglob("*"))
        assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == set(left["artifacts"]) | {"manifest.json", "run.json"}
        for name, info in left["artifacts"].items():
            assert digest(root / name) == info["sha256"] and (root / name).stat().st_size == info["size_bytes"]
    for name in set(left["artifacts"]) | {"manifest.json"}:
        assert (first / name).read_bytes() == (second / name).read_bytes()
    runs = [read(root / "run.json") for root in (first, second)]
    assert runs[0]["created_at_utc"] != runs[1]["created_at_utc"]
    assert all(r["stable_manifest_sha256"] == digest(first / "manifest.json") for r in runs)
    originals, bytes_by_id, excluded_ids, restored_ids, retained_ids = {}, {}, [], [], []
    retained_by_split = {}
    for split in ("train", "validation"):
        values, lines = rows(files["parent_data/" + split + ".jsonl"])
        assert all(e["split"] == split for e in values)
        originals.update({e["example_id"]: e for e in values})
        bytes_by_id.update({e["example_id"]: line for e, line in zip(values, lines, strict=True)})
        retained = [(e, line) for e, line in zip(values, lines, strict=True) if e["source_record_hash"] not in excluded_sources]
        assert (first / "effective" / (split + ".jsonl")).read_bytes() == b"".join(line for _, line in retained)
        retained_by_split[split] = [e["example_id"] for e, _ in retained]
        retained_ids.extend(retained_by_split[split])
        excluded_ids.extend(e["example_id"] for e in values if e["source_record_hash"] in excluded_sources)
        restored_ids.extend(e["example_id"] for e in values if e["source_record_hash"] in restored_sources)
    assert len(originals) == 7749 and len(retained_ids) == 7651 and len(excluded_ids) == 98 and len(restored_ids) == 3
    same(read(first / "effective/identities.json"), retained_by_split)
    same(read(first / "excluded/identities.json"), excluded_ids)
    same(read(first / "restored/identities.json"), restored_ids)
    lineage = {r["example_id"]: r for r in rows(files["parent_data/lineage.jsonl"])[0]
               if r["split"] in ("train", "validation") and r["exclusion_reason"] is None}
    for kind, ids in (("effective", retained_ids), ("excluded", excluded_ids), ("restored", restored_ids)):
        same(rows(first / kind / "lineage.jsonl")[0], [lineage[i] for i in ids])
        if kind != "effective":
            assert (first / kind / "examples.jsonl").read_bytes() == b"".join(bytes_by_id[i] for i in ids)
    reasons = rows(first / "dispositions/examples.jsonl")[0]
    assert [r["example_id"] for r in reasons] == list(originals)
    for reason in reasons:
        ident = reason["example_id"]
        e = originals[ident]
        assert reason["original_example_sha256"] == canonical(e)
        assert reason["original_lineage_sha256"] == canonical(lineage[ident])
        assert reason["original_jsonl_line_sha256"] == hashlib.sha256(bytes_by_id[ident]).hexdigest()
        source = sources.get(e["source_record_hash"])
        if source:
            same(reason["review"], source["adjudication"])
            same(reason["issue_ids"], source["issue_ids"])
            assert reason["disposition"] == source["disposition"] and reason["source_training_fitness"] == source["source_training_fitness"]
            assert reason["source_disposition_sha256"] == canonical(source)
        else:
            assert reason["source_training_fitness"] is None and reason["local_action_review"] is None
    for source, row in sources.items():
        members = {i for i, e in originals.items() if e["source_record_hash"] == source}
        assert members == set(row["example_ids"])
        assert members <= (set(excluded_ids) if source in excluded_sources else set(restored_ids))
    groups = {originals[i]["group_id"] for i in excluded_ids}
    same_group_kept = [i for i in retained_ids if originals[i]["group_id"] in groups]
    same_group_sources = {originals[i]["source_record_hash"] for i in same_group_kept}
    assert len(same_group_kept) == left["other_decisions_retained_in_affected_groups"] == 5553
    assert len(same_group_sources) == left["other_sources_retained_in_affected_groups"] == 5182
    selected_counts, selected_restored, delta = {}, {}, read(first / "delta-from-v1.json")["sets"]
    prior_ids = read(files["prior_revision/effective/identities.json"])
    sets = {s: (prior_ids[s], retained_by_split[s]) for s in ("train", "validation")}
    for profile in ("smoke", "formal"):
        for split in ("train", "validation"):
            prefix = profile + "/" + split
            old, old_lines = rows(files["parent_selection/" + prefix + ".examples.jsonl"])
            sidecars = rows(files["parent_selection/" + prefix + ".sidecars.jsonl"])[0]
            kept = [(rank, e, line, sidecar) for rank, (e, line, sidecar) in enumerate(zip(old, old_lines, sidecars, strict=True), 1)
                    if e["source_record_hash"] not in excluded_sources]
            output_prefix = "selection/" + prefix
            assert (first / (output_prefix + ".examples.jsonl")).read_bytes() == b"".join(line for _, _, line, _ in kept)
            new = rows(first / (output_prefix + ".sidecars.jsonl"))[0]
            assert len(new) == len(kept)
            for new_rank, (row, (rank, e, line, parent)) in enumerate(zip(new, kept, strict=True), 1):
                same(row["selection_rank"], new_rank)
                same(row["parent_selection_rank"], rank)
                same(row["restored_original_source"], e["source_record_hash"] in restored_sources)
                assert row["parent_sidecar_sha256"] == canonical(parent) and line == bytes_by_id[e["example_id"]]
                same({k: row[k] for k in parent if k != "selection_rank"}, {k: v for k, v in parent.items() if k != "selection_rank"})
                assert row["quality_revision_sha256"] == left["quality_revision_sha256"] and e["example_id"] in retained_ids
            current_ids = [e["example_id"] for _, e, _, _ in kept]
            assert len(current_ids) == len(set(current_ids))
            previous = [e["example_id"] for e in rows(files["prior_revision/selection/" + prefix + ".examples.jsonl"])[0]]
            sets[prefix] = (previous, current_ids)
            selected_counts[prefix] = len(kept)
            selected_restored[prefix] = sum(i in restored_ids for i in current_ids)
    same(selected_counts, {"smoke/train": 1583, "smoke/validation": 194, "formal/train": 5940, "formal/validation": 213})
    for name, (previous, current) in sets.items():
        same(delta[name], {"previous": len(previous), "current": len(current), "retained": len(set(previous) & set(current)),
            "removed_original_ids": [i for i in previous if i not in set(current)],
            "restored_original_ids": [i for i in current if i not in set(previous)]})
    staging = rows(files["prior_revision/staging/examples.jsonl"])[0]
    assert len(staging) == 3 and not {e["example_id"] for e in staging} & set(originals)
    staging_reference = read(first / "staging-reference.json")
    assert staging_reference["enters_effective_training"] is False and staging_reference["new_tokenization_runs"] == 0
    binding = read(first / "training-binding.json")
    assert binding["training_authorized"] is False and binding["new_annotations_enter_training"] is False
    assert binding["selection_manifest_file_sha256"] == digest(first / "selection/manifest.json")
    assert binding["parent_training_config_file_sha256"] == digest(files["parents/training-data.v1.json"])
    result = {"status": "PASS_WORKER_STDLIB_CROSSCHECK", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "quality_revision_sha256": left["quality_revision_sha256"], "counts": left["counts"],
        "stable_files_per_build": len(left["artifacts"]) + 1, "two_actual_builds_identical": True,
        "manifest_file_sha256": digest(first / "manifest.json"), "run_created_at_utc": [r["created_at_utc"] for r in runs],
        "fixed_input_files_verified": len(files), "whole_source_exclusions": 80, "excluded_decisions": 98,
        "restored_original_sources": 3, "restored_original_decisions": 3, "effective_original_line_bytes_preserved": 7651,
        "other_sources_retained_in_affected_groups": len(same_group_sources),
        "other_decisions_retained_in_affected_groups": len(same_group_kept), "restored_profile_members": selected_restored,
        "training_authorized": False, "semantic_acceptance": "PENDING_INDEPENDENT_REVIEW"}
    with Path(args.output).open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("inputs", "first", "second", "output"):
        parser.add_argument("--" + flag, required=True, type=Path)
    check(parser.parse_args())
