"""Original fixed-denominator, cluster and missing-cost counterexamples."""

import copy
import csv
import json

import pytest

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError, file_hash, write_json
from toolalign.evaluation.analysis import (
    align_rows,
    analyze,
    export_analysis,
    l1_diagnostics,
    load_batch,
    numeric_summary,
    paired_effect,
    requests_and_resources,
)
from toolalign.evaluation.bfcl import COMMIT
from toolalign.evaluation.bfcl.source import fetch_source
from toolalign.evaluation.cuda_eval.protocol import evaluation_plan

INPUT = {"messages": [{"role": "user", "content": "Original CPU request.", "tool_calls": [], "tool_call_id": None}], "tools": []}
FINAL = json.dumps({"kind": "final", "content": "17", "tool_calls": []})


def loaded_fixture(mode="l1"):
    if mode == "l1":
        inputs = {"tasks": [{"task_id": str(i), "group_id": "large" if i < 3 else "small",
            "category": "original", "family_id": "fixture", "tool_names": ["read_version"],
            "oracle_task": {"oracle_payload": {"strategies": [[]]}}} for i in range(4)],
            "recovery_task_ids": ["0", "3"]}
    elif mode == "action-only":
        inputs = {"schema_version": "toolalign.evaluation-inputs.v1", "purpose": "action-only-model-evaluation",
            "inputs": [{"task_id": str(i), "group_id": "original", "category": "irrelevance", "family_id": "fixture",
                        "model_input": copy.deepcopy(INPUT)} for i in range(2)]}
    else:
        inputs = {"schema_version": "toolalign.evaluation-replay.v1", "purpose": "development-prefix-replay",
            "sequences": [{"sequence_id": "original-sequence", "tenant_id": "original", "requests": [
                {"request_id": str(i), "model_input": copy.deepcopy(INPUT)} for i in range(3)]}]}
    plan = evaluation_plan(inputs, mode)
    batch = {"schema": "toolalign.cuda-evaluation-batch.v1", "mode": mode, "plan": plan,
             "identity": {"execution_kind": "ORIGINAL_CPU_FIXTURE"}}
    rows = [{"plan": unit, "batch_sha256": "original-batch", "status": "not_started", "reason": "missing",
             "result": None, "elapsed_seconds": None} for unit in plan]
    return {"mode": mode, "inputs": inputs, "batch": batch, "rows": rows,
            "batch_sha256": "original-batch", "input_sha256": "original-input", "summary": None}


def test_cluster_resampling_preserves_unequal_cluster_size_and_pairing():
    pairs = [{"group_id": "large", "left": False, "right": True} for _ in range(3)]
    pairs.append({"group_id": "small", "left": True, "right": False})
    result = paired_effect(pairs)
    assert result["left"]["successes"] == 1 and result["right"]["successes"] == 3
    assert result["delta"] == .5
    assert result["bootstrap"]["replicates"] == 10000 and result["bootstrap"]["seed"] == 42
    assert result["bootstrap"]["ci95"] == [-1, 1]
    assert result["leave_one_group_out"]["values"] == [
        {"omitted_group_id": "large", "remaining_n": 1, "delta": -1},
        {"omitted_group_id": "small", "remaining_n": 3, "delta": 1}]
    assert paired_effect(pairs) == result


def test_single_group_and_unknown_scorer_do_not_create_intervals():
    one = paired_effect([{"group_id": "one", "left": False, "right": True}])
    assert one["delta"] == 1 and one["bootstrap"]["status"] == "NOT_ESTIMABLE"
    assert one["leave_one_group_out"] == {"status": "NOT_ESTIMABLE", "values": []}
    unknown = paired_effect([{"group_id": "one", "left": False, "right": None}])
    assert unknown["delta"] is None and unknown["right"]["rate"] is None
    assert unknown["status"] == "INCOMPLETE_SCORING"


def test_missing_units_remain_paired_and_started_missing_is_interrupted():
    loaded = loaded_fixture()
    row = loaded["rows"][0] | {"status": "success", "reason": "original-success"}
    rows = align_rows(loaded["inputs"], "l1", [row], loaded["batch"], "original-batch", {1})
    assert len(rows) == 10 and rows[1]["status"] == "interrupted" and rows[2]["status"] == "not_started"
    loaded["rows"] = rows
    report, requests, _ = analyze(loaded)
    assert report["primary"]["left"]["successes"] == 1 and report["primary"]["left"]["planned"] == 4
    assert report["primary"]["right"]["successes"] == 0 and report["primary"]["delta"] == -.25
    assert report["A1"]["left"]["planned"] == report["A1"]["right"]["planned"] == 2
    assert report["failure_index"]["count"] == 9 and not requests
    assert report["cost"]["conditions"]["M1"]["units_without_request_evidence"] == 4


@pytest.mark.parametrize("change", ["duplicate", "foreign", "plan", "batch", "order"])
def test_denominator_identity_rejects_duplicates_foreign_units_and_plan_edits(change):
    loaded = loaded_fixture()
    rows = copy.deepcopy(loaded["rows"])
    batch = copy.deepcopy(loaded["batch"])
    if change == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif change == "foreign":
        rows[0]["plan"]["unit_id"] = 100
    elif change == "plan":
        rows[0]["plan"]["seed"] = 55
    elif change == "batch":
        rows[0]["batch_sha256"] = "other"
    else:
        batch["plan"][0], batch["plan"][1] = batch["plan"][1], batch["plan"][0]
    with pytest.raises(ValueError):
        align_rows(loaded["inputs"], "l1", rows, batch, "original-batch")


def test_absent_tokens_are_unknown_and_failed_latency_is_included():
    result = numeric_summary([2, 30, None])
    assert result["mean_known"] == 16 and result["known_sum"] == 32 and result["missing"] == 1
    assert result["tail_scope"] == "EXPLORATORY_LT_100"
    assert numeric_summary([None])["known_sum"] is None
    loaded = loaded_fixture("action-only")
    loaded["rows"][0].update(status="completed", elapsed_seconds=2, result={"status": "completed", "raw_text": FINAL,
        "output": {"input_tokens": 10, "output_tokens": 5}, "backend_metrics": {"cold_load_seconds": 1, "peak_allocated_bytes": 20},
        "timing": {"child_host_peak_rss_bytes": 100}})
    # Unit 3 is M0 in the alternating plan, so both timings belong to M0.
    loaded["rows"][3].update(status="timed_out", elapsed_seconds=30)
    report, _, _ = analyze(loaded)
    m0 = report["cost"]["conditions"]["M0"]
    assert m0["units"]["unit_wall_seconds"]["mean_known"] == 16
    assert m0["requests"]["input_tokens"]["known_sum"] == 10 and m0["requests"]["input_tokens"]["missing"] == 1
    assert m0["units"]["peak_allocated_bytes"]["maximum"] == 20
    assert m0["requests"]["child_host_peak_rss_bytes"]["maximum"] == 100
    assert report["official_scoring"] == "NOT_RUN" and report["primary"]["delta"] is None
    assert report["official_raw"]["left"]["successes"] is None


def test_l2_raw_and_strict_denominators_cannot_be_conflated():
    # Synthetic analysis table, matching the separately exercised official
    # irrelevance behavior. This test does not claim to run the official scorer.
    loaded = loaded_fixture("action-only")
    scores = {"schema_version": "toolalign.bfcl-scores.v1", "official_commit": COMMIT,
              "batch_sha256": loaded["batch_sha256"], "input_sha256": loaded["input_sha256"],
              "selection_sha256": "original-selection", "source_identity": "ORIGINAL_ANALYSIS_FIXTURE", "rows": []}
    for row in loaded["rows"]:
        scores["rows"].append({"plan": row["plan"], "batch_sha256": row["batch_sha256"],
            "task_id": row["plan"]["task_id"], "category": "irrelevance", "group_id": "original",
            "status": "not_started", "raw_text": None, "raw_action_valid": False,
            "official_status": "RUN", "official_raw_valid": True, "strict_success": False,
            "gate_reasons": ["runtime:not_started", "invalid_raw_action"], "official_result": {"valid": True}})
    report, _, _ = analyze(loaded, scores)
    assert report["primary"]["left"]["successes"] == 0 and report["official_raw"]["left"]["successes"] == 2
    assert report["primary"]["left"]["planned"] == report["official_raw"]["left"]["planned"] == 2
    assert report["failure_index"]["failed_count"] == 4
    changed = copy.deepcopy(scores)
    changed["rows"][0]["strict_success"] = True
    with pytest.raises(ValueError, match="strict_gate_binding"):
        analyze(loaded, changed)
    changed = copy.deepcopy(scores)
    changed["input_sha256"] = "another-input"
    with pytest.raises(ValueError, match="score_binding"):
        analyze(loaded, changed)


def replay_results(loaded):
    for row in loaded["rows"]:
        unit = row["plan"]
        calls = [{"request_id": str(i), "model_input_hash": canonical_hash(INPUT), "seed": unit["seed"] + i,
                  "batch_sha256": loaded["batch_sha256"], "status": "completed", "raw_text": FINAL,
                  "elapsed_seconds": i + 1, "output": {"input_tokens": 20, "output_tokens": 4}}
                 for i in range(3)]
        metrics = {"cold_load_seconds": 1, "decisions": [{"cache_hit_tokens": 19 if unit["cache_enabled"] and i else 0,
                   "ttft_seconds": .1, "prefill_seconds": .05, "decode_seconds": .2} for i in range(3)]}
        row.update(status="completed", reason="completed", elapsed_seconds=7,
                   result={"requests": calls, "backend_metrics": metrics})


def test_a2_preserves_positions_cache_metrics_missing_outputs_and_failed_requests():
    loaded = loaded_fixture("replay")
    replay_results(loaded)
    on = loaded["rows"][1]
    on["result"]["requests"][1].update(raw_text="bad-but-real", status="parse_failure", elapsed_seconds=30)
    on["result"]["requests"].pop()
    on["result"]["backend_metrics"]["decisions"].pop()
    on.update(status="incomplete", reason="parse_failure")
    report, requests, resources = analyze(loaded)
    assert len(requests) == 6 and len(resources) == 2
    assert [r["raw_equal"] for r in report["A2"]["pairs"]] == [True, False, None]
    assert report["A2"]["pairs"][1]["on_cache_hit_tokens"] == 19
    assert report["cost"]["conditions"]["M1-cache-on"]["requests"]["request_wall_seconds"]["known_sum"] == 31
    assert report["cost"]["conditions"]["M1-cache-on"]["requests"]["request_wall_seconds"]["missing"] == 1
    assert report["A2"]["raw_equality"]["unknown"] == 1
    assert report["primary"] is None


def test_a2_rejects_changed_request_seed_or_input():
    loaded = loaded_fixture("replay")
    replay_results(loaded)
    loaded["rows"][0]["result"]["requests"][1]["seed"] += 1
    with pytest.raises(ValueError, match="replay_request_binding"):
        requests_and_resources(loaded)


def test_trace_counts_arguments_recovery_and_extra_calls_without_inventing_api_success():
    entry = loaded_fixture()["inputs"]["tasks"][0]
    call = {"call_id": "first", "name": "read_version", "arguments": {"revision": 17}}
    retried = call | {"call_id": "second"}
    extra = call | {"call_id": "third", "name": "unadvertised"}
    entry["oracle_task"]["oracle_payload"]["strategies"] = [[call, retried]]
    trace = [
        {"event_index": 0, "event": "tool_execution", "tool_call": call},
        {"event_index": 1, "event": "observing", "tool_call": call, "tool_result": {"status": "error", "retryable": True}},
        {"event_index": 2, "event": "tool_execution", "tool_call": retried},
        {"event_index": 3, "event": "observing", "tool_call": retried, "tool_result": {"status": "completed", "retryable": False}},
        {"event_index": 4, "event": "tool_execution", "tool_call": extra},
        {"event_index": 5, "event": "budget_exhausted", "budget_consumed": {"model_decisions": 3}}]
    row = {"status": "failure", "result": {"trace": trace, "decisions": [{"raw_text": FINAL}]}}
    count = l1_diagnostics(entry, row)
    assert count["raw_format"]["true"] == 1 and count["raw_format"]["false"] == 2
    assert count["tool_selection"]["true"] == count["argument_semantic"]["true"] == 2
    assert count["execution_completed"]["true"] == 1 and count["execution_completed"]["false"] == 2
    assert count["invalid_tool"]["true"] == count["unnecessary_call"]["true"] == 1
    assert count["recovery"]["true"] == count["budget_exhaustion"]["true"] == 1
    assert count["task_success"]["false"] == 1


def test_host_crash_state_recovery_and_source_hash_binding(tmp_path):
    loaded = loaded_fixture("action-only")
    input_path = tmp_path / "inputs.json"
    write_json(input_path, loaded["inputs"])
    batch = loaded["batch"] | {"input_sha256": file_hash(input_path)}
    run = tmp_path / "run"
    run.mkdir()
    write_json(run / "batch.json", batch)
    (run / "states").mkdir()
    write_json(run / "states/0000.started.json", {"plan": batch["plan"][0], "batch_sha256": file_hash(run / "batch.json"), "status": "started"})
    restored = load_batch(input_path, run)
    assert len(restored["rows"]) == 4 and restored["rows"][0]["status"] == "interrupted"
    assert all(r["status"] == "not_started" for r in restored["rows"][1:])
    changed = copy.deepcopy(loaded["inputs"])
    changed["inputs"][0]["group_id"] = "invented-independent-group"
    write_json(input_path, changed)
    with pytest.raises(ValueError, match="input_identity"):
        load_batch(input_path, run)


def test_replay_host_crash_preserves_completed_request_and_started_request(tmp_path):
    loaded = loaded_fixture("replay")
    input_path = tmp_path / "inputs.json"
    write_json(input_path, loaded["inputs"])
    batch = loaded["batch"] | {"input_sha256": file_hash(input_path)}
    run = tmp_path / "run"
    run.mkdir()
    write_json(run / "batch.json", batch)
    digest = file_hash(run / "batch.json")
    (run / "states").mkdir()
    (run / "requests").mkdir()
    write_json(run / "states/0000.started.json", {"plan": batch["plan"][0], "batch_sha256": digest, "status": "started"})
    for i in (0, 1):
        expected = {"request_id": str(i), "model_input_hash": canonical_hash(INPUT), "seed": 42 + i, "batch_sha256": digest}
        write_json(run / f"requests/0000-{i}.started.json", expected)
        if i == 0:
            write_json(run / "requests/0000-0.terminal.json", {**expected, "status": "completed", "raw_text": FINAL})
    report, requests, _ = analyze(load_batch(input_path, run))
    assert [row["status"] for row in requests[:3]] == ["completed", "interrupted", "not_started"]
    assert requests[0]["raw_text"] == FINAL
    assert report["A2"]["raw_equality"]["unknown"] == 3


def test_actual_t1_cpu_output_reader_and_csv_export(tmp_path):
    from test_cuda_eval import request_for, run

    value = loaded_fixture("action-only")["inputs"]
    request = request_for(tmp_path, value, "action-only")
    summary, _ = run(request, value)
    loaded = load_batch(request["input_path"], request["output_dir"])
    report, requests, resources = analyze(loaded)
    assert len(loaded["rows"]) == 4 and report["cost"]["segment"]["segment_wall_seconds"] == summary["segment_wall_seconds"]
    assert all(row["raw_action_valid"] for row in requests)
    exported_root = tmp_path / ".toolalign-local/analysis"
    export_analysis(report, requests, resources, exported_root)
    with (exported_root / "requests.csv").open() as stream:
        exported = list(csv.DictReader(stream))
    assert len(exported) == 4 and all(row["status"] == "completed" for row in exported)
    assert json.loads((exported_root / "analysis.json").read_text())["official_scoring"] == "NOT_RUN"


def test_raw_source_and_analysis_outputs_require_private_namespace(tmp_path):
    loaded = loaded_fixture("action-only")
    report, requests, resources = analyze(loaded)
    public = tmp_path / "public"
    with pytest.raises(DataError, match="output_must_be_private"):
        export_analysis(report, requests, resources, public)
    with pytest.raises(DataError, match="output_must_be_private"):
        fetch_source(public)  # Rejects before starting any Git/network operation.
    assert not public.exists()


def test_score_cli_rejects_public_or_symlink_output_before_official_import(tmp_path, monkeypatch):
    from toolalign.evaluation.bfcl.__main__ import main

    selection = tmp_path / "original-selection.json"
    write_json(selection, {})
    private = tmp_path / ".toolalign-local"
    private.mkdir()
    link = private / "score-link.json"
    link.symlink_to(tmp_path / "outside.json")
    for output, reason in ((tmp_path / "public-score.json", "output_must_be_private"),
                           (link, "score_output_already_exists")):
        monkeypatch.setattr("sys.argv", ["bfcl", "score", "--source-root", "not-read", "--selection", str(selection),
            "--selection-sha256", file_hash(selection), "--inputs", "not-read", "--run-root", "not-read", "--output", str(output)])
        with pytest.raises(ValueError, match=reason):
            main()
    assert not (tmp_path / "outside.json").exists()


def test_failure_index_retains_all_real_cases_even_below_twenty():
    loaded = loaded_fixture()
    report, _, _ = analyze(loaded)
    assert report["failure_index"]["count"] == len(loaded["rows"]) == 10
    assert report["failure_index"]["distinct_category_reason_pairs"] == 1
