"""Fixed-ID started/terminal journal and bounded LocalHarness batch execution."""

from __future__ import annotations

import os
import tempfile
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import OracleTask, SandboxContext
from toolalign.evaluation.harness import LocalHarness, SamplingParameters
from toolalign.model_io.cuda_generation import (
    ADAPTER_SHA256,
    CHECKPOINT_SHA256,
    CUDAGenerationBackend,
    selected_model_identity,
)
from toolalign.tools import CancellationToken, LocalToolExecutor
from toolalign.training.cuda_sft.protocol import (
    CONFIG_SHA256,
    dependency_identity,
    document,
    encoded,
    load_protocol,
    read_bytes,
    require,
    sha,
    source_identity,
)

from .protocol import SAMPLING, read_tasks, validate_run

# The harness caps three 512 KiB inputs, three 128 KiB model responses and
# two rounds of at most 16 calls with 16 KiB arguments/results. 16 MiB also
# covers trace/provenance and the required duplicated decision_inputs fields.
MAX_CANDIDATE_BYTES = 16 * 1024**2
METADATA_RESERVE = 1024**2


def now():
    return datetime.now(timezone.utc).isoformat()


class OutputStore:
    def __init__(self, root, max_bytes):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.max_bytes = max_bytes

    @property
    def size(self):
        return sum(path.stat().st_size for path in self.root.rglob("*") if path.is_file())

    def write(self, name, data):
        path = self.root / name
        require(not path.exists(), "generation_output_already_written")
        require(self.size + len(data) <= self.max_bytes, "generation_output_budget")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def json(self, name, value):
        self.write(name, encoded(value) + b"\n")


def row_header(candidate, ordinal, *, identity, batch_hash):
    return {"task_id": candidate["task_id"], "candidate_id": candidate["candidate_id"],
            "candidate_ordinal": ordinal,
            "generation_parameters": {"seed": candidate["seed"], **SAMPLING},
            "model_identity": identity["model_identity"],
            "checkpoint_sha256": identity["checkpoint_sha256"], "batch_sha256": batch_hash,
            "execution_kind": identity["execution_kind"]}


def interrupted_row(started):
    return {**started, "status": "interrupted", "finished_at_utc": now(),
            "harness_result": None, "decision_inputs": [], "elapsed_seconds": None,
            "error": "started_without_confirmed_terminal_result"}


def recover_progress(request, store, batch, batch_hash):
    """Import an owned recovered snapshot; a started ID is never rerun."""
    if "resume_from" not in request:
        return {}, []
    source = Path(request["resume_from"])
    prior = document(source / "batch.json", digest=request["resume_batch_sha256"])
    require(prior == batch, "generation_resume_batch_mismatch")
    records, recovered_files = {}, []
    states = source / "states"
    if not states.exists():
        return records, recovered_files
    for path in sorted(states.iterdir()):
        raw = read_bytes(path, MAX_CANDIDATE_BYTES)
        # Keep incomplete atomic-write bytes as evidence, never as a terminal.
        require(path.name.startswith(".pending-") or (
            len(path.name.split(".")) == 3
            and path.name.split(".")[0] in {f"{i:04d}" for i in range(len(batch["candidate_plan"]))}
            and path.name.split(".")[1] in ("started", "terminal")
            and path.suffix == ".json"), "generation_resume_file")
        store.write("states/" + path.name, raw)
        recovered_files.append({"file": "states/" + path.name, "sha256": sha(raw), "bytes": len(raw)})
    for ordinal, candidate in enumerate(batch["candidate_plan"]):
        start = store.root / f"states/{ordinal:04d}.started.json"
        terminal = store.root / f"states/{ordinal:04d}.terminal.json"
        require(not terminal.exists() or start.exists(), "terminal_without_started_record")
        if not start.exists():
            continue
        expected = row_header(candidate, ordinal, identity=batch["identity"], batch_hash=batch_hash)
        started = document(start)
        require(all(started.get(k) == v for k, v in expected.items())
                and started.get("status") == "started", "generation_started_identity")
        if terminal.exists():
            row = document(terminal)
            require(all(row.get(k) == v for k, v in expected.items())
                    and row.get("started_at_utc") == started["started_at_utc"]
                    and row.get("status") in ("success", "failure", "unknown", "not_scored",
                                              "interrupted", "infrastructure_error"),
                    "generation_terminal_identity")
        else:
            row = interrupted_row(started)
            store.json(terminal.relative_to(store.root), row)
        records[ordinal] = row
    require(not records or max(records) < request["max_trajectories"],
            "resume_prefix_cannot_shrink")
    return records, recovered_files


def summarize(records, tasks, plan, *, request, reason, segment_seconds, restored, batch_hash):
    counts = Counter(row["status"] for row in records.values())
    failures, events, resources = Counter(), Counter(), []
    for row in records.values():
        result = row["harness_result"]
        if result is None:
            failures[row.get("error", row["status"])] += 1
            continue
        if result["score"]["outcome"] != "success":
            failures[result["score"]["reason"]] += 1
        events[result["trace"][-1]["event"]] += 1
        metric = result["provenance"].get("backend_metrics")
        if metric:
            resources.append(metric)
        for decision in result["decisions"]:
            if decision.get("backend_parse_failure") == "context_overflow":
                failures["context_overflow"] += 1
    return {"schema": "toolalign.cuda-generation-summary.v1", "status": reason,
            "run_id": request["run_id"], "batch_sha256": batch_hash,
            "total_tasks": len(tasks), "planned_trajectories": len(plan),
            "authorized_prefix_trajectories": request["max_trajectories"],
            "started_trajectories": len(records), "terminal_counts": dict(counts),
            "not_started_trajectories": len(plan) - len(records),
            "restored_trajectories": restored, "new_trajectories": len(records) - restored,
            "failure_reasons": dict(failures), "terminal_events": dict(events),
            "segment_wall_seconds": segment_seconds,
            "recorded_trajectory_seconds": sum(row["elapsed_seconds"] or 0 for row in records.values()),
            "trajectory_time_complete": all(row["elapsed_seconds"] is not None for row in records.values()),
            "cold_load_seconds": [r["cold_load_seconds"] for r in resources
                                  if r.get("cold_load_seconds") is not None],
            "incomplete_cold_load_seconds": [r["incomplete_cold_load_seconds"] for r in resources
                                             if "incomplete_cold_load_seconds" in r],
            "peak_allocated_bytes": max((r["peak_allocated_bytes"] for r in resources
                                         if "peak_allocated_bytes" in r), default=None),
            "peak_reserved_bytes": max((r["peak_reserved_bytes"] for r in resources
                                        if "peak_reserved_bytes" in r), default=None),
            "allocation_seconds_and_CU": "recorded_by_S1_Colab_controller_across_all_segments",
            "real_model_benchmark": "NOT_RUN"}


def run_batch(request, task_document, registry, *, identity, backend_factory,
              cancellation=None, started_monotonic=None):
    """Host-side orchestration seam; CPU fixtures supply an explicitly labeled backend.

    The factory receives a plan item only, never Example/oracle/faults. The public
    CLI always supplies CUDAGenerationBackend and the verified real identity.
    """
    validate_run(request, task_document)
    cancellation = cancellation or CancellationToken()
    started = time.monotonic() if started_monotonic is None else started_monotonic
    expiry = started + request["max_wall_seconds"]
    tasks = {entry["task_id"]: entry for entry in task_document["tasks"]}
    plan = request["candidate_plan"]
    batch = {"schema": "toolalign.cuda-generation-batch.v1", "identity": identity,
             "candidate_plan": plan, "seed_policy": "reset_per_decision",
             "registry_hash": registry.registry_hash, "sampling": SAMPLING}
    batch_bytes = encoded(batch) + b"\n"
    batch_hash = sha(batch_bytes)
    store = OutputStore(request["output_dir"], request["max_output_bytes"])
    store.write("batch.json", batch_bytes)
    store.json("run.json", request)
    records, recovered_files = recover_progress(request, store, batch, batch_hash)
    restored = len(records)
    sandbox = store.root / "sandbox"
    sandbox.mkdir(mode=0o700)
    reason = "prefix_complete"
    for ordinal, candidate in enumerate(plan[:request["max_trajectories"]]):
        if ordinal in records:
            continue
        if cancellation.is_cancelled():
            reason = "cancelled"
            break
        if time.monotonic() >= expiry:
            reason = "wall_limit"
            break
        # Reserve space for the full result and its JSONL export before starting.
        export_bytes = sum(len(encoded(row)) + 1 for row in records.values())
        if store.size + export_bytes + 2 * MAX_CANDIDATE_BYTES + METADATA_RESERVE > store.max_bytes:
            reason = "output_limit"
            break
        row = {**row_header(candidate, ordinal, identity=identity, batch_hash=batch_hash),
               "status": "started", "started_at_utc": now(), "started_run_id": request["run_id"]}
        store.json(f"states/{ordinal:04d}.started.json", row)
        trajectory_started = time.monotonic()
        try:
            entry = tasks[candidate["task_id"]]
            # A fresh executor owns a fresh fault deque for EACH candidate.
            executor = LocalToolExecutor(registry, faults=entry["faults"])
            deadline = datetime.now(timezone.utc) + timedelta(seconds=max(0, expiry - time.monotonic()))
            context = SandboxContext(sandbox.resolve(), f"candidate-{ordinal}", deadline.isoformat(),
                                     cancellation)
            result = LocalHarness(registry, executor).run(
                entry["example"], OracleTask(**entry["oracle_task"]), backend_factory(candidate),
                context, model_identity=identity["model_identity"],
                sampling=SamplingParameters(candidate["seed"], SAMPLING["temperature"], SAMPLING["top_p"]))
            row.update(status=result.score.outcome, harness_result=asdict(result),
                       decision_inputs=result.decision_inputs, error=None)
            require(len(result.decisions) <= len(result.decision_inputs)
                    and all(canonical_hash(model_input) == decision["model_input_hash"]
                            for model_input, decision in zip(result.decision_inputs, result.decisions)),
                    "actual_decision_input_hash_mismatch")
        except Exception as error:
            row.update(status="infrastructure_error", error=type(error).__name__ + ": " + str(error)[:1000])
            row.setdefault("harness_result", None)
            row.setdefault("decision_inputs", [])
        row.update(finished_at_utc=now(), elapsed_seconds=time.monotonic() - trajectory_started)
        raw = encoded(row) + b"\n"
        require(len(raw) <= MAX_CANDIDATE_BYTES, "candidate_exceeds_reserved_output_bound")
        store.write(f"states/{ordinal:04d}.terminal.json", raw)
        records[ordinal] = row
    candidates = b"".join(encoded(records[index]) + b"\n" for index in sorted(records))
    store.write("candidates.jsonl", candidates)
    summary = summarize(records, tasks, plan, request=request, reason=reason,
                        segment_seconds=time.monotonic() - started, restored=restored, batch_hash=batch_hash)
    summary.update(identity=identity, recovered_files=recovered_files,
                   candidates_sha256=sha(candidates), max_output_bytes=store.max_bytes,
                   output_bytes_before_summary=store.size)
    store.json("summary.json", summary)
    return summary


def execute(request, *, cancellation=None):
    """Production entry: no user-specified backend/module and no CPU fallback."""
    started = time.monotonic()
    tasks, registry = read_tasks(request["tasks_path"], request["tasks_sha256"])
    validate_run(request, tasks)
    load_protocol(request["repository"])
    source = source_identity(request["repository"], request["source_commit"])
    dependencies = dependency_identity(request["dependency_lock"], request["dependency_lock_sha256"])
    identity = {"execution_kind": "REAL_CUDA_SFT", "source": source,
                "config_sha256": CONFIG_SHA256, "tasks_sha256": request["tasks_sha256"],
                "model_identity": selected_model_identity(request["repository"]),
                "checkpoint_sha256": CHECKPOINT_SHA256, "adapter_sha256": ADAPTER_SHA256,
                "dependencies": dependencies}

    def backend(candidate):
        return CUDAGenerationBackend(repository=request["repository"], model_root=request["model_root"],
                                     checkpoint_dir=request["checkpoint_dir"], run_id=request["run_id"])

    return run_batch(request, tasks, registry, identity=identity, backend_factory=backend,
                     cancellation=cancellation, started_monotonic=started)
