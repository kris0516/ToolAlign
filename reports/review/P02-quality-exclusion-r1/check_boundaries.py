"""Independent R1 CPU counterexamples; only repository-original toy fixtures.

Fixtures supply original examples, never corpus rows or real tokenizer adapters.
Mutations refresh local record hashes to reach the semantic binding checks.
"""

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch


def run(args):
    sys.path.insert(0, str(args.fixtures))
    from adjudication_cases import source_fixture
    from exclusion_cases import reviewed_fixture, revision_fixture
    from test_quality_exclusion_materials import encoding_fixture, reuse_fixture

    from toolalign.contracts import canonical_hash
    from toolalign.data import quality_adjudication as a
    from toolalign.data import quality_adjudication_materials as am
    from toolalign.data import quality_exclusion as x
    from toolalign.data import quality_exclusion_materials as m
    from toolalign.data import quality_revision as q
    from toolalign.data.common import DataError, encoded

    blocked = {"tokenizers", "transformers", "torch", "mlx", "mlx_lm", "tensorflow", "jax", "flax"}
    assert all(importlib.util.find_spec(k) is None for k in blocked)
    outcomes = []

    def reject(name, call, expected, exception=DataError):
        try:
            call()
        except exception as exc:
            assert expected in str(exc), (name, type(exc).__name__, str(exc))
            outcomes.append({"case": name, "result": "PASS_EXPECTED_REJECTION", "reason": str(exc), "exception": type(exc).__name__})
        else:
            raise AssertionError("unexpected acceptance: " + name)

    index, row, packet, raw, _ = source_fixture()
    assert a.source_members(index, row, packet, raw) == set(row["example_ids"])
    for omitted in (0, -1):
        r, p = copy.deepcopy(row), copy.deepcopy(packet)
        ident = r["example_ids"].pop(omitted)
        r["valid_decision_count"] -= 1
        r["binding"] = [b for b in r["binding"] if b["example_id"] != ident]
        p["identity"]["example_ids"].remove(ident)
        p["identity"]["valid_decision_count"] -= 1
        p["valid_decisions"] = [d for d in p["valid_decisions"] if d["example"]["example_id"] != ident]
        r["packet_sha256"] = q.sha(encoded(p))
        reject("locally-consistent-source-omission-" + str(omitted), lambda: a.source_members(index, r, p, raw), "disposition_all_decisions")

    row, packet, parent, previous, buffers = reviewed_fixture()
    assert len(x.reviewed_exclusion(row, packet, parent, previous, buffers)) == 2
    for mode in ("all-ranks-swapped", "integer-equal-float-rank", "earliest-decision-omitted"):
        r, p, b = copy.deepcopy(row), copy.deepcopy(packet), copy.deepcopy(buffers)
        ref = r["adjudication"]
        record = json.loads(b[ref["file"]])["sources"][0]
        proposal = json.loads(b[ref["proposal_file"]])["newly_reviewed_sources"][0]
        if mode == "earliest-decision-omitted":
            record["decisions"].pop(0)
            proposal["all_decisions"].pop(0)
            expected = "new_exclusion_review_all_decisions"
        else:
            for d in proposal["all_decisions"]:
                ranks = d["current_selection_bindings"]["formal"]
                if mode == "all-ranks-swapped":
                    ranks["selection_rank"], ranks["parent_selection_rank"] = ranks["parent_selection_rank"], ranks["selection_rank"]
                else:
                    ranks["selection_rank"] = float(ranks["selection_rank"])
            expected = "new_exclusion_previous_rank_binding"
        b[ref["file"]] = encoded({"sources": [record]})
        b[ref["proposal_file"]] = encoded({"newly_reviewed_sources": [proposal]})
        ref.update(source_record_sha256=canonical_hash(record), proposal_record_sha256=canonical_hash(proposal))
        reject(mode, lambda: x.reviewed_exclusion(r, p, parent, previous, b), expected)

    inputs = revision_fixture()
    selection = x.filtered_selection(inputs, "original-r1-revision")
    previous_rows = x.selection_rows(inputs["parent_artifacts"])
    for profile in q.PROFILES:
        for split in q.SPLITS:
            for ordinal, sidecar in enumerate(selection[profile][split]["sidecars"], 1):
                old = previous_rows[profile][split][sidecar["audit"]["example_id"]]
                assert sidecar["selection_rank"] == ordinal
                assert sidecar["parent_selection_rank"] == old["parent_selection_rank"]
                assert sidecar["previous_selection_rank"] == old["selection_rank"]
    for mode in ("float-v2-rank", "v1-rank-rebound", "removed-v2-member"):
        altered = copy.deepcopy(inputs)
        name = "selection/formal/train.sidecars.jsonl"
        rows = q.jsonl(altered["parent_artifacts"][name])[0]
        ident = selection["formal"]["train"]["sidecars"][0]["audit"]["example_id"]
        target = next(r for r in rows if r["audit"]["example_id"] == ident)
        if mode == "float-v2-rank":
            target["selection_rank"] = float(target["selection_rank"])
            expected = "previous_rank_integer_type"
        elif mode == "v1-rank-rebound":
            target["parent_selection_rank"] += 100
            expected = "original_rank_preserved"
        else:
            rows.remove(target)
            expected = "v3_cannot_refill_previous_selection"
        altered["parent_artifacts"][name] = a.lines_bytes(rows)
        reject(mode, lambda: x.filtered_selection(altered, "original-r1-revision"), expected)

    cases, parent, policy, _ = reuse_fixture()
    original = copy.deepcopy(parent)
    reused, _ = m.reused_records(cases, parent, policy)
    assert len(reused) == 11 and parent == original
    ident = cases[0]["example"]["example_id"]
    alternate = cases[1]["example"]["example_id"]
    for mode in ("wrong-example-rehashed", "bool-mask-rehashed", "float-token-rehashed", "padding-float-rehashed"):
        changed = copy.deepcopy(parent)
        old = changed["records"][ident]
        if mode == "wrong-example-rehashed":
            old = changed["records"][ident] = copy.deepcopy(parent["records"][alternate])
            expected = "reuse_example_identity"
        elif mode == "bool-mask-rehashed":
            old["sequence"]["loss_mask"][0] = False
            expected = "material_array_integer_type"
        elif mode == "float-token-rehashed":
            old["sequence"]["sequence_ids"][0] = float(old["sequence"]["sequence_ids"][0])
            expected = "material_array_integer_type"
        else:
            old["padding"]["sequence_ids"][-1] = float(old["padding"]["sequence_ids"][-1])
            expected = "material_complete_record_binding"
        for key in ("sequence_ids", "loss_mask"):
            digest_key = "sequence_sha256" if key == "sequence_ids" else "loss_mask_sha256"
            old["sequence"][digest_key] = canonical_hash(old["sequence"][key])
        data = encoded(old) + b"\n"
        changed["manifest"]["artifacts"][old["case"]["case_id"] + ".json"] = {"sha256": q.sha(data), "size_bytes": len(data)}
        reject(mode, lambda: m.reused_records(cases, changed, policy), expected)

    ecases, eparent, epolicy, coverage, einputs, release = encoding_fixture()
    assert len(m.new_cases(ecases, epolicy)) == 2
    for split in ("validation", "test", "ood"):
        changed = copy.deepcopy(ecases)
        next(c for c in changed if c["encoding_mode"] == "new_fixed_example")["example"]["split"] = split
        reject("new-material-forbidden-split-" + split, lambda: m.new_cases(changed, epolicy), "encoding_new_case_budget")

    # Supply finite original records at the freeze boundary; all run, manifest,
    # record, payload, consumer and original-time checks below remain real.
    records = list(eparent["records"].values())
    old_cases = [r["case"] for r in records]
    frozen = {"manifest.json": b"original R1 frozen material bytes"}
    cov = copy.deepcopy(coverage)
    revision = old_cases[0]["quality_revision_sha256"]
    identity = am.consumer_identity()
    old_artifacts = am.review_artifacts(records)
    artifacts_meta = {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in old_artifacts.items()}
    current_time = "2026-09-01T11:00:00+00:00"
    old_time = "2026-09-01T10:00:01+00:00"
    old_manifest = {"consumer": identity, "artifacts": artifacts_meta, "records_sha256": canonical_hash(records),
                    "frozen_selection_manifest_file_sha256": q.sha(frozen["manifest.json"])}
    old_manifest_bytes = encoded(old_manifest)
    old_run = {"consumer": identity, "stable_manifest_sha256": q.sha(old_manifest_bytes), "training_authorized": False,
               "model_modules_loaded": [], "created_at_utc": old_time, "output_path": "original R1 old publication"}
    command = {"exit_code": 0, "command": ["original-character-fixture", "--engine", "tokenizers"],
               "started_at_utc": "2026-09-01T10:00:00+00:00", "finished_at_utc": "2026-09-01T10:00:02+00:00",
               "log_sha256": q.sha(b"original R1 successful toy observation")}
    manifest = {"training_authorized": False, "model_modules_loaded": [], "manifest_version": "toolalign.quality-adjudication-token-review.v2",
                "coverage": cov, "quality_revision_sha256": revision, "frozen_selection_manifest_file_sha256": q.sha(frozen["manifest.json"]),
                "case_order": [c["case_id"] for c in old_cases], "consumer": identity, "tokenizers": eparent["manifest"]["tokenizers"],
                "records_sha256": canonical_hash(records), "artifacts": artifacts_meta,
                "original_encoding": {"manifest_file_sha256": q.sha(old_manifest_bytes), "run_file_sha256": q.sha(encoded(old_run)),
                    "consumer": identity, "actual_original_created_at_utc": old_time,
                    "source_commit_is_byte_equivalence_not_an_execution_time_claim": True},
                "static_republication": {"actual_new_tokenizer_calls": 0, "all_material_payload_files_byte_identical": True}}
    manifest_bytes = encoded(manifest)
    run_record = {**old_run, "stable_manifest_sha256": q.sha(manifest_bytes), "created_at_utc": current_time}
    prefix = "parent-materials/review-native-r2/"
    origin = "original-measurements/review-native/"
    cmdname = "original-measurements/logs/quality-adjudication-material-native-r1"
    bundle = {prefix + k: v for k, v in old_artifacts.items()}
    bundle.update({prefix + "manifest.json": manifest_bytes, prefix + "run.json": encoded(run_record),
                   origin + "manifest.json": old_manifest_bytes, origin + "run.json": encoded(old_run),
                   "original-measurements/frozen-materials/manifest.json": frozen["manifest.json"],
                   cmdname + ".json": encoded(command), cmdname + ".log": b"original R1 successful toy observation"})
    bound = {"buffers": bundle, "parent_manifest": {"quality_revision_sha256": revision}, "parent": einputs["parent"]}
    with patch.object(m, "parent_selection", return_value=(frozen, {}, old_cases, cov)):
        assert len(m.parent_measurement(bound, "tokenizers")["records"]) == 13
        for mode in ("wrong-parent-run", "republication-time-as-encoding", "wrong-original-consumer", "wrong-parent-revision", "wrong-old-record-revision"):
            altered = copy.deepcopy(bound)
            if mode == "wrong-parent-run":
                run = json.loads(altered["buffers"][prefix + "run.json"])
                run["stable_manifest_sha256"] = q.sha(old_manifest_bytes)
                altered["buffers"][prefix + "run.json"] = encoded(run)
                expected = "material_run_manifest"
            elif mode == "republication-time-as-encoding":
                run = json.loads(altered["buffers"][origin + "run.json"])
                run["created_at_utc"] = current_time
                altered["buffers"][origin + "run.json"] = encoded(run)
                expected = "original_encoding_run"
            elif mode == "wrong-original-consumer":
                record = json.loads(altered["buffers"][origin + "run.json"])
                record["consumer"]["package_files"]["data/quality_adjudication.py"] = "0" * 64
                altered["buffers"][origin + "run.json"] = encoded(record)
                expected = "material_run_consumer"
            elif mode == "wrong-parent-revision":
                altered["parent_manifest"]["quality_revision_sha256"] = "wrong prior revision"
                expected = "parent_material_revision"
            else:
                name = prefix + old_cases[0]["case_id"] + ".json"
                record = json.loads(altered["buffers"][name])
                record["case"]["quality_revision_sha256"] = "a-different-old-revision"
                altered["buffers"][name] = encoded(record) + b"\n"
                meta = json.loads(altered["buffers"][prefix + "manifest.json"])
                meta["artifacts"][old_cases[0]["case_id"] + ".json"] = {"sha256": q.sha(altered["buffers"][name]), "size_bytes": len(altered["buffers"][name])}
                altered["buffers"][prefix + "manifest.json"] = encoded(meta)
                expected = "material_frozen_case_binding"
            reject(mode, lambda: m.parent_measurement(altered, "tokenizers"), expected)

    args.root.mkdir(parents=True, exist_ok=False)
    payload = {"first.bin": b"retained partial original bytes", "second.bin": b"unwritten bytes", "manifest.json": b"success is forbidden"}
    output = args.root / "failed-publication"
    real_open = Path.open

    def failing_open(path, *pos, **kw):
        if path == output / "second.bin" and pos and pos[0] == "xb":
            raise OSError("original injected second-file write failure")
        return real_open(path, *pos, **kw)

    with patch.object(Path, "open", failing_open):
        reject("partial-publish-write-failure", lambda: q.publish(output, payload, {"training_authorized": False}),
               "original injected second-file write failure", OSError)
    assert (output / "first.bin").read_bytes() == payload["first.bin"]
    assert not (output / "manifest.json").exists() and not (output / "second.bin").exists()
    assert not blocked & {n.split('.', 1)[0] for n in sys.modules}
    return {"status": "PASS", "independent_rejections": len(outcomes), "outcomes": outcomes,
            "original_fixture_controls": 6, "actual_corpus_rows_read": 0, "new_actual_tokenizer_calls": 0,
            "new_model_framework_gpu_runs": 0, "new_full_v3_builds": 0, "training_authorized": False,
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixtures", "root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    options = parser.parse_args()
    result = run(options)
    with options.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps(result, sort_keys=True))
