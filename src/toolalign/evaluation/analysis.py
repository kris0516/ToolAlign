"""Frozen G5 paired/group analysis of host-side T1 outputs; no model calls."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash
from toolalign.data.common import file_hash, loads, read_json, write_json
from toolalign.data.training_selection import new_private_directory
from toolalign.evaluation.bfcl import COMMIT as BFCL_COMMIT
from toolalign.evaluation.cuda_eval.protocol import evaluation_plan, read_inputs
from toolalign.evaluation.oracles.semantic import equivalent
from toolalign.tools._json import parse_action

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 42
TERMINAL = {"success", "failure", "unknown", "not_scored", "completed", "parse_failure", "incomplete",
            "timed_out", "cancelled", "budget_exhausted", "infrastructure_error", "interrupted", "not_started"}


def align_rows(inputs, mode, rows, batch, batch_sha256, started_ids=()):
    plan = evaluation_plan(inputs, mode)
    if batch["plan"] != plan or batch["mode"] != mode:
        raise ValueError("analysis_frozen_plan_mismatch")
    found = {}
    for row in rows:
        index = row["plan"]["unit_id"]
        if (type(index) is not int or index not in range(len(plan)) or index in found
                or row["plan"] != plan[index] or row["batch_sha256"] != batch_sha256
                or row["status"] not in TERMINAL or (row["status"] == "not_started" and index in started_ids)):
            raise ValueError("analysis_row_identity_or_status")
        found[index] = row
    return [found.get(i, {"plan": unit, "batch_sha256": batch_sha256,
                         "status": "interrupted" if i in started_ids else "not_started",
                         "reason": "started_without_terminal" if i in started_ids else "missing_terminal",
                         "result": None, "elapsed_seconds": None}) for i, unit in enumerate(plan)]


def load_batch(input_path, run_root):
    root = Path(run_root)
    batch = read_json(root / "batch.json")
    if batch["schema"] != "toolalign.cuda-evaluation-batch.v1" or batch["mode"] == "capacity":
        raise ValueError("analysis_evaluation_batch_required")
    digest = file_hash(input_path)
    if digest != batch["input_sha256"]:
        raise ValueError("analysis_input_identity")
    inputs, _ = read_inputs(input_path, digest, batch["mode"])
    batch_hash = file_hash(root / "batch.json")
    result_path, summary_path = root / "results.jsonl", root / "summary.json"
    rows = [loads(line) for line in result_path.read_text().splitlines()] if result_path.exists() else []
    started = set()
    for unit in batch["plan"]:
        index = unit["unit_id"]
        start = root / f"states/{index:04d}.started.json"
        terminal = root / f"states/{index:04d}.terminal.json"
        if start.exists():
            record = read_json(start)
            if record["plan"] != unit or record["batch_sha256"] != batch_hash or record["status"] != "started":
                raise ValueError("analysis_started_identity")
            started.add(index)
        if terminal.exists():
            record = read_json(terminal)
            present = [r for r in rows if r["plan"]["unit_id"] == index]
            if present and present != [record]:
                raise ValueError("analysis_export_terminal_disagreement")
            if not present:
                rows.append(record)
    rows = align_rows(inputs, batch["mode"], rows, batch, batch_hash, started)
    if batch["mode"] == "replay":
        sequences = {s["sequence_id"]: s for s in inputs["sequences"]}
        for row in rows:
            if row.get("result") is not None:
                continue
            unit, calls = row["plan"], []
            for position, request in enumerate(sequences[unit["task_id"]]["requests"]):
                expected = {"request_id": request["request_id"], "model_input_hash": canonical_hash(request["model_input"]),
                            "seed": unit["seed"] + position, "batch_sha256": batch_hash}
                start = root / f"requests/{unit['unit_id']:04d}-{position}.started.json"
                terminal = root / f"requests/{unit['unit_id']:04d}-{position}.terminal.json"
                for path in (start, terminal):
                    if path.exists():
                        saved = read_json(path)
                        if any(saved.get(k) != v for k, v in expected.items()):
                            raise ValueError("analysis_replay_saved_request_binding")
                if terminal.exists():
                    calls.append(read_json(terminal))
                else:
                    calls.append({**expected, "status": "interrupted" if start.exists() else "not_started",
                                  "reason": "started_without_terminal" if start.exists() else "missing_request",
                                  "raw_text": None})
            row["result"] = {"requests": calls, "backend_metrics": {}}
    if batch["mode"] == "action-only":
        expected_inputs = {e["task_id"]: e["model_input"] for e in inputs["inputs"]}
        for row in rows:
            result = row.get("result")
            if result is None:
                continue
            expected = expected_inputs[row["plan"]["task_id"]]
            if (result.get("model_input") != expected or result.get("model_input_hash") != canonical_hash(expected)
                    or result.get("status") != row["status"]):
                raise ValueError("analysis_actual_model_input_or_status_binding")
    summary = read_json(summary_path) if summary_path.exists() else None
    if summary is not None and (summary["batch_sha256"] != batch_hash or not result_path.exists()
                                or summary["results_sha256"] != file_hash(result_path)):
        raise ValueError("analysis_summary_binding")
    return {"mode": batch["mode"], "inputs": inputs, "batch": batch, "rows": rows,
            "input_sha256": digest, "batch_sha256": batch_hash, "summary": summary,
            "provenance": {"batch_sha256": batch_hash, "input_sha256": digest,
                           "results_sha256": file_hash(result_path) if result_path.exists() else None,
                           "summary_sha256": file_hash(summary_path) if summary is not None else None}}


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * q
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def success_count(values):
    known = [value for value in values if value is not None]
    complete = len(known) == len(values)
    return {"successes": sum(known) if complete else None, "known_successes": sum(known),
            "planned": len(values), "unknown": len(values) - len(known),
            "rate": sum(known) / len(values) if complete and values else None}


def paired_effect(pairs):
    """Resample complete groups; task-weighted paired differences within each draw."""
    left = success_count([row["left"] for row in pairs])
    right = success_count([row["right"] for row in pairs])
    groups = defaultdict(list)
    for row in pairs:
        groups[row["group_id"]].append(row)
    result = {"left": left, "right": right, "delta": None, "groups": len(groups),
              "group_effects": [], "bootstrap": {"status": "NOT_ESTIMABLE", "replicates": BOOTSTRAP_REPLICATES,
                  "seed": BOOTSTRAP_SEED, "ci95": None, "resampling_unit": "complete_connected_group"},
              "leave_one_group_out": {"status": "NOT_ESTIMABLE", "values": []}}
    if not pairs or left["unknown"] or right["unknown"]:
        result["status"] = "NO_DATA" if not pairs else "INCOMPLETE_SCORING"
        return result
    result.update(status="CALCULATED", delta=right["rate"] - left["rate"])
    sums = []
    for group, values in sorted(groups.items()):
        total = sum(int(v["right"]) - int(v["left"]) for v in values)
        sums.append((total, len(values)))
        result["group_effects"].append({"group_id": group, "n": len(values), "delta": total / len(values),
                                       "left_successes": sum(v["left"] for v in values),
                                       "right_successes": sum(v["right"] for v in values)})
    if len(groups) < 2:
        return result
    rng, draws = random.Random(BOOTSTRAP_SEED), []
    for _ in range(BOOTSTRAP_REPLICATES):
        sample = [sums[rng.randrange(len(sums))] for _ in sums]
        draws.append(sum(value for value, _ in sample) / sum(n for _, n in sample))
    result["bootstrap"].update(status="CALCULATED", ci95=[percentile(draws, .025), percentile(draws, .975)])
    total = sum(value for value, _ in sums)
    result["leave_one_group_out"] = {"status": "CALCULATED", "values": [
        {"omitted_group_id": item["group_id"], "remaining_n": len(pairs) - n,
         "delta": (total - value) / (len(pairs) - n)}
        for item, (value, n) in zip(result["group_effects"], sums, strict=True)]}
    return result


def tally(values, denominator):
    return {"true": values.count(True), "false": values.count(False), "unknown": values.count(None),
            "n": len(values), "denominator": denominator,
            "status": "COUNTED" if values else "N/A"}


def raw_valid(raw):
    try:
        parse_action(raw)
        return True
    except ContractError:
        return False


def l1_diagnostics(entry, row):
    """Read trace/oracle facts without modifying the registered task success score."""
    result = row.get("result") or {}
    trace = result.get("trace", [])
    calls = [event["tool_call"] for event in trace if event["event"] == "tool_execution"]
    observations = [event for event in trace if event["event"] == "observing"]
    strategies = entry["oracle_task"]["oracle_payload"].get("strategies", [])
    selection, arguments, unnecessary = [], [], []
    for index, call in enumerate(calls):
        prefix = calls[:index + 1]
        selection.append(any(len(s) > index and all(c["name"] == s[i]["name"] for i, c in enumerate(prefix))
                             for s in strategies) if strategies else None)
        arguments.append(any(len(s) > index and all(c["name"] == s[i]["name"]
                         and equivalent(c["arguments"], s[i]["arguments"]) for i, c in enumerate(prefix))
                             for s in strategies) if strategies else None)
        # A call within the maximum strategy length can still be redundant; that
        # judgment is unavailable here unless the entire semantic prefix matches.
        unnecessary.append(True if strategies and index >= max(map(len, strategies))
                           else False if arguments[-1] else None)
    retryable = [e for e in observations if e["tool_result"]["status"] != "completed"
                 and e["tool_result"]["retryable"]]
    recovered = [any(later["event_index"] > event["event_index"]
                     and later["tool_result"]["status"] == "completed"
                     and later["tool_call"]["name"] == event["tool_call"]["name"]
                     and equivalent(later["tool_call"]["arguments"], event["tool_call"]["arguments"])
                     for later in observations) for event in retryable]
    observed_calls = {event["tool_call"]["call_id"]: event["tool_result"] for event in observations}
    budget = trace[-1]["budget_consumed"]["model_decisions"] if trace else 0
    raw = [raw_valid(d.get("raw_text")) for d in result.get("decisions", [])]
    raw.extend([False] * max(0, budget - len(raw)))
    return {"raw_format": tally(raw, "attempted model decisions; no raw output fails format"),
            "tool_selection": tally(selection, "attempted call prefixes matching a permitted strategy's names"),
            "argument_semantic": tally(arguments, "attempted call prefixes matching permitted names and semantic arguments"),
            "execution_completed": tally([observed_calls[c["call_id"]]["status"] == "completed"
                if c["call_id"] in observed_calls else False for c in calls], "attempted tool calls"),
            "invalid_tool": tally([c["name"] not in entry["tool_names"] for c in calls], "attempted tool calls"),
            "unnecessary_call": tally(unnecessary, "attempted calls; excess length true, permitted semantic prefix false, otherwise unknown"),
            "recovery": tally(recovered, "observed retryable errors followed by a completed same-tool/same-arguments call"),
            "budget_exhaustion": tally([any(e["event"] == "budget_exhausted" for e in trace) if trace else None],
                                       "planned trajectories; missing traces unknown"),
            "task_success": tally([row["status"] == "success"], "all planned trajectories")}


def numeric_summary(values):
    known = [v for v in values if type(v) in (int, float) and math.isfinite(v) and v >= 0]
    return {"known": len(known), "missing": len(values) - len(known), "planned": len(values),
            "known_sum": sum(known) if known else None, "mean_known": sum(known) / len(known) if known else None,
            "maximum": max(known) if known else None, "p50": percentile(known, .5),
            "p95": percentile(known, .95), "p99": percentile(known, .99),
            "tail_scope": "EXPLORATORY_LT_100" if len(known) < 100 else "EMPIRICAL",
            "missing_policy": "unknown; all statuses retained; statistics use available measurements"}


def requests_and_resources(loaded):
    requests, resources = [], []
    mode = loaded["mode"]
    sequences = {s["sequence_id"]: s for s in loaded["inputs"].get("sequences", [])}
    for row in loaded["rows"]:
        unit, result = row["plan"], row.get("result") or {}
        metrics = result.get("provenance", {}).get("backend_metrics", {}) if mode == "l1" else result.get("backend_metrics", {})
        resources.append({"unit_id": unit["unit_id"], "condition": unit["condition"], "status": row["status"],
                          "unit_wall_seconds": row.get("elapsed_seconds"), **metrics})
        if mode == "replay":
            planned = sequences[unit["task_id"]]["requests"]
            by_id = {r["request_id"]: r for r in result.get("requests", [])}
            if len(by_id) != len(result.get("requests", [])) or set(by_id) - {r["request_id"] for r in planned}:
                raise ValueError("analysis_replay_request_ids")
            calls = []
            for position, request in enumerate(planned):
                expected = {"request_id": request["request_id"], "model_input_hash": canonical_hash(request["model_input"]),
                            "seed": unit["seed"] + position, "batch_sha256": loaded["batch_sha256"]}
                call = by_id.get(request["request_id"])
                if call is not None and any(call.get(k) != v for k, v in expected.items()):
                    raise ValueError("analysis_replay_request_binding")
                calls.append(call or {**expected, "status": "not_started" if row["status"] == "not_started"
                                       else "interrupted", "raw_text": None})
        elif mode == "l1":
            calls = result.get("decisions", []).copy()
            attempted = result["trace"][-1]["budget_consumed"]["model_decisions"] if result.get("trace") else 0
            calls.extend({"status": "missing_output"} for _ in range(max(0, attempted - len(calls))))
        else:
            calls = [result or {"status": row["status"], "raw_text": None}]
        generation = metrics.get("decisions", [])
        for position, call in enumerate(calls):
            output = call.get("output") or (call if mode == "l1" else {})
            timing = call.get("timing") or {}
            gen = generation[position] if position < len(generation) else {}
            requests.append({"unit_id": unit["unit_id"], "task_id": unit["task_id"], "condition": unit["condition"],
                "position": position + 1, "request_id": call.get("request_id"),
                "status": call.get("status", call.get("finish_reason", "unknown")),
                "reason": call.get("reason"), "raw_text": call.get("raw_text"),
                "raw_action_valid": raw_valid(call.get("raw_text")),
                "input_tokens": output.get("input_tokens"), "output_tokens": output.get("output_tokens"),
                "request_wall_seconds": call.get("complete_wall_seconds", call.get("elapsed_seconds")),
                **{key: timing.get(key) for key in ("queue_seconds", "child_generation_seconds", "child_host_peak_rss_bytes")},
                **{key: gen.get(key) for key in ("cache_hit_tokens", "prompt_tokens", "prefill_tokens", "prefill_seconds",
                                                "ttft_seconds", "decode_seconds", "generation_seconds")}})
    return requests, resources


def costs(loaded, requests, resources):
    result = {}
    for condition in sorted({row["plan"]["condition"] for row in loaded["rows"]}):
        units = [r for r in resources if r["condition"] == condition]
        calls = [r for r in requests if r["condition"] == condition]
        result[condition] = {"planned_units": len(units), "request_rows": len(calls),
            "units_without_request_evidence": sum(not any(c["unit_id"] == u["unit_id"] for c in calls) for u in units),
            "unit_status_counts": dict(Counter(r["status"] for r in units)),
            "request_status_counts": dict(Counter(r["status"] for r in calls)),
            "units": {key: numeric_summary([r.get(key) for r in units]) for key in (
                "unit_wall_seconds", "cold_load_seconds", "incomplete_cold_load_seconds",
                "peak_allocated_bytes", "peak_reserved_bytes")},
            "requests": {key: numeric_summary([r.get(key) for r in calls]) for key in (
                "input_tokens", "output_tokens", "request_wall_seconds", "queue_seconds", "child_generation_seconds",
                "child_host_peak_rss_bytes", "cache_hit_tokens", "prefill_tokens", "prefill_seconds", "ttft_seconds",
                "decode_seconds", "generation_seconds")}}
    summary = loaded.get("summary") or {}
    return {"conditions": result, "segment": {key: summary.get(key) for key in (
        "run_id", "segment_wall_seconds", "model_file_preflight_seconds", "host_peak_rss_bytes", "child_host_peak_rss_bytes",
        "tool_execution_seconds", "tool_timing_scope", "allocation_seconds_and_CU")},
        "scope": "unit times include failures; segment includes preflight; allocation/CU requires S1 controller ledger; resumed rows may precede this segment",
        "memory_units": "bytes; host RSS separate from CUDA allocated/reserved"}


def l2_diagnostics(entry, row, score):
    raw = (row.get("result") or {}).get("raw_text")
    try:
        action = parse_action(raw)
    except ContractError:
        action = None
    calls = action["tool_calls"] if action else []
    advertised = {t["name"] for t in entry["model_input"]["tools"]}
    matched = score.get("official_raw_valid")
    call_match = [True if matched is True else None for _ in calls]
    return {"raw_format": tally([raw_valid(raw)], "all planned requests"),
        "tool_selection": tally(call_match, "decoded calls; official AST pass confirms match; failures retain combined official reason"),
        "argument_semantic": tally(call_match, "decoded calls; official AST pass confirms match; failure components otherwise unknown"),
        "execution_completed": {"status": "N/A", "reason": "AST scoring does not execute APIs"},
        "invalid_tool": tally([c["name"] not in advertised for c in calls], "decoded tool calls"),
        "unnecessary_call": tally([True if entry["category"] == "irrelevance" else None for _ in calls],
                                   "decoded calls; irrelevance calls unnecessary, other cases use official combined result"),
        "recovery": {"status": "N/A", "reason": "single-decision evaluation"},
        "budget_exhaustion": tally([row["status"] == "budget_exhausted" if row["status"] != "not_started" else None],
                                   "all planned requests; unstarted unknown"),
        "task_success": tally([score.get("strict_success")], "all planned requests; unrun scorer unknown"),
        "official_detail": score.get("official_result")}


def analyze(loaded, bfcl_scores=None):
    mode, inputs, rows = loaded["mode"], loaded["inputs"], loaded["rows"]
    requests, resources = requests_and_resources(loaded)
    report = {"schema_version": "toolalign.g5-analysis.v1", "mode": mode, "provenance": loaded.get("provenance", {}),
              "execution_kind": loaded["batch"]["identity"].get("execution_kind", "MODEL_EVALUATION"),
              "M2": "NOT_RUN", "primary": None, "categories": {}, "A1": None, "A2": None,
              "diagnostics": [], "cost": costs(loaded, requests, resources),
              "uncertainty_scope": "Current connected-group empirical stability; few groups give coarse intervals; no population coverage or training-seed variance claim."}
    units = {(r["plan"]["task_id"], r["plan"]["condition"]): r for r in rows}
    outcomes, raw_outcomes, scored = {}, {}, {}
    if mode == "l1":
        entries = inputs["tasks"]
        for entry in entries:
            for condition in ("M0", "M1") + (("M1-recovery-off",) if entry["task_id"] in inputs["recovery_task_ids"] else ()):
                row = units[entry["task_id"], condition]
                outcomes[entry["task_id"], condition] = row["status"] == "success"
                report["diagnostics"].append({"task_id": entry["task_id"], "condition": condition,
                                              **l1_diagnostics(entry, row)})
    elif mode == "action-only":
        entries = inputs["inputs"]
        if bfcl_scores is not None:
            if (bfcl_scores["schema_version"] != "toolalign.bfcl-scores.v1" or bfcl_scores["official_commit"] != BFCL_COMMIT
                    or bfcl_scores["batch_sha256"] != loaded["batch_sha256"] or bfcl_scores["input_sha256"] != loaded["input_sha256"]):
                raise ValueError("analysis_bfcl_score_binding")
            report["bfcl_provenance"] = {key: bfcl_scores[key] for key in ("official_commit", "selection_sha256", "source_identity")}
            for row in bfcl_scores["rows"]:
                key = (row["task_id"], row["plan"]["condition"])
                if key in scored or key not in units or row["plan"] != units[key]["plan"]:
                    raise ValueError("analysis_bfcl_score_ids")
                original = units[key]
                entry = next(e for e in entries if e["task_id"] == row["task_id"])
                if (row["status"] != original["status"] or row["raw_text"] != (original.get("result") or {}).get("raw_text")
                        or row["group_id"] != entry["group_id"] or row["category"] != entry["category"]
                        or row["batch_sha256"] != loaded["batch_sha256"]):
                    raise ValueError("analysis_bfcl_score_row_binding")
                expected_strict = (row["status"] == "completed" and raw_valid(row["raw_text"])
                                   and row["official_raw_valid"] is True) if row["official_status"] == "RUN" else None
                if row["strict_success"] is not expected_strict or row["raw_action_valid"] != raw_valid(row["raw_text"]):
                    raise ValueError("analysis_bfcl_strict_gate_binding")
                scored[key] = row
        for key, row in units.items():
            score = scored.get(key, {})
            outcomes[key] = score.get("strict_success")
            raw_outcomes[key] = score.get("official_raw_valid")
        report["official_scoring"] = "NOT_RUN" if not scored else "RUN" if all(r["official_status"] == "RUN" for r in scored.values()) and len(scored) == len(units) else "INCOMPLETE"
        report["diagnostics"] = [{"task_id": e["task_id"], "condition": model,
            **l2_diagnostics(e, units[e["task_id"], model], scored.get((e["task_id"], model), {}))}
            for e in entries for model in ("M0", "M1")]
    else:
        pairs = []
        by_request = {(r["task_id"], r["condition"], r["position"]): r for r in requests}
        for sequence in inputs["sequences"]:
            for position in range(1, 4):
                off = by_request[sequence["sequence_id"], "M1-cache-off", position]
                on = by_request[sequence["sequence_id"], "M1-cache-on", position]
                pairs.append({"sequence_id": sequence["sequence_id"], "position": position,
                    "off_status": off["status"], "on_status": on["status"],
                    "raw_equal": off["raw_text"] == on["raw_text"] if off["raw_text"] is not None and on["raw_text"] is not None else None,
                    "off_cache_hit_tokens": off["cache_hit_tokens"], "on_cache_hit_tokens": on["cache_hit_tokens"],
                    **{key + "_on_minus_off": on[key] - off[key] if on[key] is not None and off[key] is not None else None
                       for key in ("request_wall_seconds", "prefill_seconds", "ttft_seconds", "decode_seconds")}})
        report["A2"] = {"pairs": pairs, "raw_equality": tally([p["raw_equal"] for p in pairs], "all fixed request pairs"),
                        "scope": "development request replay performance; no task quality score"}
        entries = []
    if entries:
        def pair(entry, left="M0", right="M1", values=None):
            values = outcomes if values is None else values
            return {"task_id": entry["task_id"], "group_id": entry["group_id"], "category": entry["category"],
                    "left": values[entry["task_id"], left], "right": values[entry["task_id"], right]}
        pairs = [pair(e) for e in entries]
        report["primary"] = {"contrast": "M1_minus_M0", **paired_effect(pairs)}
        report["categories"] = {category: paired_effect([p for p in pairs if p["category"] == category])
                                for category in sorted({e["category"] for e in entries})}
        if mode == "action-only":
            report["official_raw"] = paired_effect([pair(e, values=raw_outcomes) for e in entries])
        else:
            report["A1"] = {"contrast": "M1_recovery_on_minus_off", **paired_effect([
                pair(e, "M1-recovery-off", "M1") for e in entries if e["task_id"] in inputs["recovery_task_ids"]])}
    entry_by_id = {e["task_id"]: e for e in entries}
    failures = []
    for row in rows:
        key = row["plan"]["task_id"], row["plan"]["condition"]
        if (mode == "replay" and row["status"] == "completed") or (mode != "replay" and outcomes[key] is True):
            continue
        official = scored.get(key, {})
        failures.append({"task_id": key[0], "condition": key[1], "unit_id": row["plan"]["unit_id"],
            "category": entry_by_id.get(key[0], {}).get("category", "development_replay"), "status": row["status"],
            "reason": ";".join(official["gate_reasons"]) if official.get("gate_reasons") else row.get("reason"),
            "runtime_reason": row.get("reason"), "official_detail": official.get("official_result"), "outcome": outcomes.get(key),
            "evidence": (f"results.jsonl#unit_id={row['plan']['unit_id']}" if loaded.get("provenance", {}).get("results_sha256")
                         else f"batch.json#plan[{row['plan']['unit_id']}]")})
    report["failure_index"] = {"count": len(failures), "selection": "all_unsuccessful_or_unscored_units",
        "failed_count": sum(r["outcome"] is False or (mode == "replay" and r["status"] != "completed") for r in failures),
        "unscored_count": sum(r["outcome"] is None for r in failures) if mode != "replay" else 0,
        "distinct_category_reason_pairs": len({(r["category"], r["reason"]) for r in failures}),
        "rows": sorted(failures, key=lambda r: (r["category"], str(r["reason"]), r["unit_id"]))}
    return report, requests, resources


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v
                         for k, v in row.items()} for row in rows)


def export_analysis(report, requests, resources, output, *, plot=False):
    root = new_private_directory(output)
    write_json(root / "analysis.json", report)
    write_csv(root / "requests.csv", requests)
    write_csv(root / "resources.csv", resources)
    write_csv(root / "failures.csv", report["failure_index"]["rows"])
    write_csv(root / "categories.csv", [{"category": k, **v} for k, v in report["categories"].items()])
    write_csv(root / "group-effects.csv", (report["primary"] or {}).get("group_effects", []))
    write_csv(root / "a2-pairs.csv", (report["A2"] or {}).get("pairs", []))
    if plot:
        quality_cost_plot(report, root / "quality-cost.png")


def quality_cost_plot(report, path):
    """Costs cover every planned unit with measured time, including failures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5))
    primary = report["primary"] or {}
    plotted = False
    for condition, field in (("M0", "left"), ("M1", "right")):
        quality = primary.get(field, {})
        cost = report["cost"]["conditions"].get(condition, {}).get("units", {}).get("unit_wall_seconds", {})
        if quality.get("rate") is not None and cost.get("known_sum") is not None:
            ax.scatter(cost["known_sum"], quality["rate"])
            ax.annotate(f"{condition}: n={quality['planned']}; timed={cost['known']}/{cost['planned']}",
                        (cost["known_sum"], quality["rate"]), xytext=(4, 5), textcoords="offset points")
            plotted = True
    if not plotted:
        ax.text(.5, .5, "No measured quality/cost pair", ha="center", transform=ax.transAxes)
    ax.set(xlabel="Sum of recorded unit wall seconds (all statuses)", ylabel="Successes / all planned tasks", ylim=(-.05, 1.12))
    ax.set_title(report["execution_kind"] + " | " + report["mode"])
    fig.text(.02, .01, "Unit cost excludes batch preflight/allocation overhead; missing time remains unknown.", fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--bfcl-scores")
    parser.add_argument("--output", required=True)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    report, requests, resources = analyze(load_batch(args.inputs, args.run_root),
                                         read_json(args.bfcl_scores) if args.bfcl_scores else None)
    if args.bfcl_scores:
        report["provenance"]["bfcl_scores_sha256"] = file_hash(args.bfcl_scores)
    export_analysis(report, requests, resources, args.output, plot=args.plot)
    print(json.dumps({"status": "ANALYZED", "mode": report["mode"], "output": args.output}))


if __name__ == "__main__":
    main()
