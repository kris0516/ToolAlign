"""Bounded G5 host orchestration; started IDs are never retried."""

from __future__ import annotations

import resource
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import OracleTask, SandboxContext
from toolalign.evaluation.harness import LocalHarness, SamplingParameters
from toolalign.model_io.cuda_evaluation import CUDAEvaluationBackend, evaluation_model_identity
from toolalign.model_io.cuda_generation import BATCH_FILE_VALIDATION, MODEL_ID, MODEL_REVISION
from toolalign.model_io.qwen_model import validate_model_files
from toolalign.tools import CancellationToken, LocalToolExecutor
from toolalign.training.cuda_generate.runner import (
    MAX_CANDIDATE_BYTES,
    METADATA_RESERVE,
    OutputStore,
    now,
)
from toolalign.training.cuda_sft.protocol import (
    dependency_identity,
    document,
    encoded,
    load_protocol,
    read_bytes,
    require,
    sha,
    source_identity,
)

from .decision import DecisionSession, one_decision
from .protocol import SAMPLING, read_inputs, validate_run


def header(unit, batch_hash):
    return {"plan": unit, "batch_sha256": batch_hash}


def placeholder(status, reason):
    return {"status": status, "reason": reason, "raw_text": None, "finish_reason": None,
            "raw_action": None, "raw_action_valid": False, "raw_parse_failure": "no_output",
            "output": None, "token_accounting_complete": False}


def replay_rows(store, ordinal, sequence, unit, batch_hash):
    """Keep every request's result, or its explicit started/not-started state."""
    rows = []
    for index, request in enumerate(sequence["requests"]):
        base = f"requests/{ordinal:04d}-{index}"
        start, terminal = store.root / (base + ".started.json"), store.root / (base + ".terminal.json")
        require(not terminal.exists() or start.exists(), "evaluation_request_terminal_without_start")
        expected = {"request_id": request["request_id"], "model_input_hash": canonical_hash(request["model_input"]),
                    "seed": unit["seed"] + index, "batch_sha256": batch_hash}
        if start.exists():
            started = document(start)
            require(all(started.get(k) == v for k, v in expected.items()), "evaluation_replay_request_identity")
        if terminal.exists():
            result = document(terminal)
            require(all(result.get(k) == v for k, v in expected.items()), "evaluation_replay_terminal_identity")
        else:
            result = {**expected, **placeholder("interrupted" if start.exists() else "not_started",
                       "started_without_terminal" if start.exists() else "session_not_completed")}
        rows.append(result)
    return rows


def recover(request, store, batch, batch_hash, entries):
    records = {}
    if "resume_from" not in request:
        return records
    source = Path(request["resume_from"])
    require(document(source / "batch.json", digest=request["resume_batch_sha256"]) == batch,
            "evaluation_resume_batch_mismatch")
    names = {f"{i:04d}.{state}.json" for i in range(len(batch["plan"])) for state in ("started", "terminal")}
    request_names = {f"{i:04d}-{j}.{state}.json" for i in range(len(batch["plan"]))
                     for j in range(3) for state in ("started", "terminal")}
    for directory, allowed in (("states", names), ("requests", request_names)):
        path = source / directory
        if path.exists():
            for file in sorted(path.iterdir()):
                require(file.name in allowed or file.name.startswith(".pending-"), "evaluation_resume_file")
                store.write(directory + "/" + file.name, read_bytes(file, MAX_CANDIDATE_BYTES))
    for ordinal, unit in enumerate(batch["plan"]):
        base = f"states/{ordinal:04d}"
        start, terminal = store.root / (base + ".started.json"), store.root / (base + ".terminal.json")
        require(not terminal.exists() or start.exists(), "evaluation_terminal_without_started")
        if not start.exists():
            continue
        started = document(start)
        expected = header(unit, batch_hash)
        require(all(started.get(k) == v for k, v in expected.items()) and started["status"] == "started",
                "evaluation_started_identity")
        if terminal.exists():
            row = document(terminal)
            require(all(row.get(k) == v for k, v in expected.items())
                    and row["started_at_utc"] == started["started_at_utc"]
                    and row["status"] in ("success", "failure", "unknown", "not_scored", "completed", "parse_failure",
                                          "incomplete", "timed_out", "cancelled", "budget_exhausted",
                                          "infrastructure_error", "interrupted"),
                    "evaluation_terminal_identity")
        else:
            row = {**started, "status": "interrupted", "reason": "started_without_terminal",
                   "elapsed_seconds": None, "finished_at_utc": now(), "result": None}
            if request["mode"] == "replay":
                row["result"] = {"requests": replay_rows(store, ordinal, entries[unit["task_id"]], unit, batch_hash),
                                 "process_records": [], "backend_metrics": {},
                                 "cleanup_confirmation": "unknown_after_host_interruption"}
            store.json(base + ".terminal.json", row)
        records[ordinal] = row
    require(not records or max(records) < request["stop_after_unit"], "evaluation_resume_prefix_cannot_shrink")
    return records


def summarize(rows, request, *, restored, reason, elapsed, preflight, identity):
    conditions = {}
    calls, resources, actual_identities, tool_seconds = [], [], [], []
    for row in rows:
        condition = row["plan"]["condition"]
        counts = conditions.setdefault(condition, Counter())
        counts["planned"] += 1
        counts[row["status"]] += 1
        result = row.get("result")
        if result is None:
            if request["mode"] != "l1":
                calls.extend([placeholder(row["status"], row["reason"])] * (3 if request["mode"] == "replay" else 1))
            continue
        if request["mode"] == "l1":
            resources.append(result["provenance"].get("backend_metrics", {}))
            calls.extend({"output": {k: d[k] for k in ("input_tokens", "output_tokens")}, "timing": d.get("timing"),
                          "token_accounting_complete": d["input_tokens"] is not None and d["output_tokens"] is not None}
                         for d in result["decisions"])
            trace = result["trace"]
            tool_seconds.extend((after["latency_ms"] - before["latency_ms"]) / 1000
                                for before, after in zip(trace, trace[1:])
                                if before["event"] == "tool_execution" and after["event"] == "observing")
            if not result["token_accounting_complete"]:
                calls.append(placeholder("unknown", "no_completed_usage"))
        else:
            calls.extend(result["requests"] if request["mode"] == "replay" else [result])
            resources.append(result.get("backend_metrics", {}))
    for item in resources:
        if item.get("actual_model_identity") is not None:
            actual_identities.append(item["actual_model_identity"])
    known = [c["output"] for c in calls if c.get("token_accounting_complete") and c.get("output")]
    timings = [c["timing"] for c in calls if c.get("timing")]
    return {"schema": "toolalign.cuda-evaluation-summary.v1", "status": reason, "mode": request["mode"],
            "run_id": request["run_id"], "identity": identity, "M2": "NOT_RUN",
            "planned_units": len(rows), "planned_trajectories": len(rows) if request["mode"] == "l1" else None,
            "planned_requests": None if request["mode"] == "l1" else (3 * len(rows) if request["mode"] == "replay" else len(rows)),
            "max_planned_model_decisions": len(rows) * (3 if request["mode"] in ("l1", "replay") else 1),
            "started_units": sum(row["status"] != "not_started" for row in rows),
            "restored_units": restored, "not_started_units": sum(row["status"] == "not_started" for row in rows),
            "terminal_counts": dict(Counter(row["status"] for row in rows)),
            "terminal_reasons": dict(Counter(row["reason"] for row in rows)),
            "conditions": {k: dict(v) for k, v in conditions.items()},
            "request_status_counts": dict(Counter(c.get("status", "harness_decision") for c in calls)),
            "known_input_tokens": sum(c["input_tokens"] for c in known),
            "known_output_tokens": sum(c["output_tokens"] for c in known),
            "token_accounting_complete": all(c["token_accounting_complete"] for c in calls)
                and all(row["status"] != "interrupted" and row.get("result") is not None for row in rows),
            "missing_token_usage": "unknown", "segment_wall_seconds": elapsed,
            "model_file_preflight_seconds": preflight, "resources": resources,
            "queue_seconds": [t["queue_seconds"] for t in timings],
            "child_generation_seconds": [t["child_generation_seconds"] for t in timings],
            "child_host_peak_rss_bytes": max((t["child_host_peak_rss_bytes"] for t in timings), default=None),
            "tool_execution_seconds": tool_seconds,
            "tool_timing_scope": "tool_execution_event_to_observing_event",
            "actual_model_identities": actual_identities,
            "host_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024),
            "allocation_seconds_and_CU": "recorded_by_S1_controller_across_segments",
            "official_bfcl_scorer": "NOT_RUN", "statistical_analysis": "NOT_RUN"}


def run_batch(request, inputs, registries, *, identity, backend_factory, cancellation=None,
              started_monotonic=None, model_file_preflight_seconds=None):
    """CPU seam labels its own identity; production supplies only the fixed CUDA backend."""
    validate_run(request, inputs)
    started = time.monotonic() if started_monotonic is None else started_monotonic
    expiry = started + request["max_wall_seconds"]
    cancellation = cancellation or CancellationToken()
    mode, plan = request["mode"], request["plan"]
    entries = {e["sequence_id" if mode == "replay" else "task_id"]: e
               for e in inputs[{"l1": "tasks", "replay": "sequences"}.get(mode, "inputs")]}
    batch = {"schema": "toolalign.cuda-evaluation-batch.v1", "mode": mode, "identity": identity,
             "input_sha256": request["input_sha256"], "plan": plan, "sampling": SAMPLING,
             "seed_policy": "42_plus_input_ordinal_reset_per_decision"}
    raw = encoded(batch) + b"\n"
    batch_hash = sha(raw)
    store = OutputStore(request["output_dir"], request["max_output_bytes"])
    store.write("batch.json", raw)
    store.json("run.json", request)
    records = recover(request, store, batch, batch_hash, entries)
    restored = len(records)
    sandbox = store.root / "sandbox"
    sandbox.mkdir(mode=0o700)
    reason = "prefix_complete"
    for ordinal, unit in enumerate(plan[:request["stop_after_unit"]]):
        if ordinal in records:
            continue
        if cancellation.is_cancelled() or time.monotonic() >= expiry:
            reason = "cancelled" if cancellation.is_cancelled() else "wall_limit"
            break
        export_bytes = sum(len(encoded(row)) + 1 for row in records.values())
        if store.size + export_bytes + 3 * MAX_CANDIDATE_BYTES + METADATA_RESERVE > store.max_bytes:
            reason = "output_limit"
            break
        row = {**header(unit, batch_hash), "status": "started", "started_at_utc": now(),
               "started_run_id": request["run_id"]}
        store.json(f"states/{ordinal:04d}.started.json", row)
        unit_start = time.monotonic()
        session = None
        try:
            entry = entries[unit["task_id"]]
            backend = backend_factory(unit)  # No oracle, faults or expected answers passed.
            model_identity = identity["models"][unit["model"]]
            if mode == "l1":
                registry = registries[unit["task_id"]]
                executor = LocalToolExecutor(registry, faults=entry["faults"])
                deadline = datetime.now(timezone.utc) + timedelta(seconds=max(0, min(expiry, unit_start + 30) - time.monotonic()))
                context = SandboxContext(sandbox.resolve(), f"evaluation-{ordinal}", deadline.isoformat(), cancellation)
                result = LocalHarness(registry, executor).run(entry["example"], OracleTask(**entry["oracle_task"]),
                    backend, context, model_identity=model_identity,
                    sampling=SamplingParameters(unit["seed"], 0.7, 0.9), recovery_enabled=unit["recovery_enabled"])
                row.update(status=result.score.outcome, reason=result.score.reason, result=asdict(result))
            elif mode in ("action-only", "capacity"):
                result = one_decision(entry["model_input"], backend, sandbox.resolve(), model_identity=model_identity,
                    seed=unit["seed"], cancellation=cancellation, expires_monotonic=min(expiry, unit_start + 30))
                row.update(status=result["status"], reason=result["reason"], result=result)
            else:
                session = DecisionSession(sandbox.resolve(), backend, model_identity=model_identity,
                                           cancellation=cancellation, expires_monotonic=min(expiry, unit_start + 90))
                for index, item in enumerate(entry["requests"]):
                    if session.closed or cancellation.is_cancelled() or time.monotonic() >= session.expires:
                        break
                    base = f"requests/{ordinal:04d}-{index}"
                    store.json(base + ".started.json", {"request_id": item["request_id"],
                        "model_input_hash": canonical_hash(item["model_input"]), "seed": unit["seed"] + index,
                        "started_at_utc": now(), "batch_sha256": batch_hash})
                    result = session.generate(item["model_input"], seed=unit["seed"] + index)
                    result.update(request_id=item["request_id"], seed=unit["seed"] + index, batch_sha256=batch_hash)
                    store.json(base + ".terminal.json", result)
                session.close()
                results = replay_rows(store, ordinal, entry, unit, batch_hash)
                status = "completed" if all(r["status"] == "completed" for r in results) else "incomplete"
                row.update(status=status, reason=status, result={"requests": results,
                    "process_records": session.process_records, "backend_metrics": session.metrics})
        except Exception as error:
            row.update(status="infrastructure_error", reason=type(error).__name__ + ": " + str(error)[:1000], result=None)
        finally:
            if session is not None:
                session.close()
        row.update(finished_at_utc=now(), elapsed_seconds=time.monotonic() - unit_start)
        raw = encoded(row) + b"\n"
        require(len(raw) <= MAX_CANDIDATE_BYTES, "evaluation_result_exceeds_reserved_bound")
        store.write(f"states/{ordinal:04d}.terminal.json", raw)
        records[ordinal] = row
    rows = [records.get(i, {**header(unit, batch_hash), "status": "not_started", "reason": reason,
                            "result": None, "elapsed_seconds": None}) for i, unit in enumerate(plan)]
    exported = b"".join(encoded(row) + b"\n" for row in rows)
    store.write("results.jsonl", exported)
    summary = summarize(rows, request, restored=restored, reason=reason, elapsed=time.monotonic() - started,
                        preflight=model_file_preflight_seconds, identity=identity)
    summary.update(batch_sha256=batch_hash, results_sha256=sha(exported), max_output_bytes=store.max_bytes,
                   output_bytes_before_summary=store.size)
    store.json("summary.json", summary)
    return summary


def execute(request, *, cancellation=None):
    started = time.monotonic()
    inputs, registries = read_inputs(request["input_path"], request["input_sha256"], request["mode"])
    validate_run(request, inputs)
    load_protocol(request["repository"])
    source = source_identity(request["repository"], request["source_commit"])
    dependencies = dependency_identity(request["dependency_lock"], request["dependency_lock_sha256"])
    preflight = time.monotonic()
    verified = validate_model_files(request["model_root"], model_id=MODEL_ID, revision=MODEL_REVISION,
                                     config_path=Path(request["repository"]) / "configs/qwen-models.v1.json")
    preflight = time.monotonic() - preflight
    identity = {"execution_kind": "REAL_CUDA_EVALUATION", "source": source, "dependencies": dependencies,
                "models": {model: evaluation_model_identity(request["repository"], model) for model in ("M0", "M1")},
                "checkpoints": {"M0": None, "M1": request["checkpoint_sha256"]},
                "model_file_validation": BATCH_FILE_VALIDATION}
    tenants = {e["sequence_id"]: e["tenant_id"] for e in inputs.get("sequences", [])}

    def backend(unit):
        return CUDAEvaluationBackend(model=unit["model"], cache_enabled=unit["cache_enabled"],
            tenant_id=tenants.get(unit["task_id"], "evaluation"), repository=request["repository"],
            model_root=request["model_root"], checkpoint_dir=request["checkpoint_dir"], run_id=request["run_id"],
            verified_files=verified)

    return run_batch(request, inputs, registries, identity=identity, backend_factory=backend,
                     cancellation=cancellation, started_monotonic=started, model_file_preflight_seconds=preflight)
