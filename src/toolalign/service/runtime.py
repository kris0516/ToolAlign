"""One scheduler owns every model process; HTTP only changes bounded records."""

from __future__ import annotations

import copy
import threading
import time
import uuid
from collections import Counter, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from toolalign.contracts import ContractError, canonical_hash
from toolalign.contracts.interfaces import GenerationConfig
from toolalign.inference.results import gate_output
from toolalign.inference.worker import service_child
from toolalign.runtime.gpu_lock import inspect_gpu_lock
from toolalign.tools import CancellationToken, LocalToolRegistry
from toolalign.tools._json import INPUT_BYTES, MODEL_BYTES, encode, parse_action
from toolalign.tools.isolation import OwnedProcess, read_packet, write_packet
from toolalign.training.cuda_generate.runner import OutputStore
from toolalign.training.cuda_sft.protocol import require

from .protocol import (
    CLEANUP_SECONDS,
    HTTP_SCHEMA,
    MAX_PENDING,
    MAX_RECORDS,
    STARTUP_SECONDS,
    TERMINAL,
    TIMINGS,
    APIError,
    TokenAuth,
    idempotency_key,
    model_info,
    validate_request,
    validate_run,
)

# Each accepted request reserves its original body, stopping/terminal result,
# and small accepted/started records. Worker reserve includes the one active IPC
# exchange and two bounded metadata snapshots per possible worker lifetime.
REQUEST_RESERVE = 4 * INPUT_BYTES + 16_384


def now():
    return datetime.now(timezone.utc).isoformat()


def metadata_reserve(max_generations):
    return 4 * INPUT_BYTES + (max_generations + 1) * 2 * INPUT_BYTES + 131_072


class _Journal(OutputStore):
    """Count immutable journal writes; the separate reserve covers live child IPC.

    A filesystem rescan would race the warm child's acknowledged IPC deletions.
    The caller serializes writes, and a run always starts in a new directory.
    """

    def __init__(self, root, max_bytes):
        self._bytes = 0
        super().__init__(root, max_bytes)

    @property
    def size(self):
        return self._bytes

    def write(self, name, data):
        super().write(name, data)
        self._bytes += len(data)


@dataclass
class _Job:
    principal: str
    key: str
    payload: dict
    state: dict
    accepted: float
    expires: float
    cancellation: CancellationToken


class _Cancellation:
    def __init__(self, *tokens):
        self.tokens = tokens

    def is_cancelled(self):
        return any(token.is_cancelled() for token in self.tokens)


class Service:
    """CPU seam uses an explicitly identified original backend; CLI fixes CUDA M1."""

    def __init__(self, request, *, identity, backend_factory, cancellation=None, started_monotonic=None):
        self.request = validate_run(request)
        self.identity = copy.deepcopy(identity)
        self.model_identity = self.identity["model_identity"]
        self.backend_factory = backend_factory
        self.cancellation = cancellation or CancellationToken()
        self.started = time.monotonic() if started_monotonic is None else started_monotonic
        self.dispatch_stop = self.started + request["max_wall_seconds"] - CLEANUP_SECONDS
        self.auth = TokenAuth(request["auth_file"])
        self.registry = LocalToolRegistry(catalog_id="local-devops.v1")
        self.info = model_info(request, self.model_identity, self.registry)
        self.reserved_metadata = metadata_reserve(request["max_generations"])
        require(request["max_output_bytes"] >= self.reserved_metadata, "service_metadata_budget")
        self._condition = threading.Condition(threading.RLock())
        self.store = _Journal(request["output_dir"], request["max_output_bytes"])
        self._write("run.json", request)
        self._write("identity.json", self.identity)
        self.sandbox = self.store.root / "sandbox"
        self.sandbox.mkdir(mode=0o700)
        self._pending = deque()
        self._jobs, self._keys = {}, {}
        self._active = self._worker = None
        self._worker_calls = self._epoch = self._generations = 0
        self._loaded = self._stopping = self._cleanup_unconfirmed = False
        self._stop_token = CancellationToken()
        self._reason = None
        self.workers = []
        self.done = threading.Event()
        self.thread = threading.Thread(target=self._run, name="toolalign-service-scheduler")
        self.summary = None

    def _write(self, path, value):
        with self._condition:
            self.store.write(path, encode(value, INPUT_BYTES) + b"\n")

    def start(self):
        self.thread.start()

    def _admission_error(self):
        if self._stopping or self.cancellation.is_cancelled():
            return APIError(503, "service_stopping")
        if time.monotonic() >= self.dispatch_stop:
            return APIError(503, "service_budget_exhausted")
        if len(self._jobs) >= MAX_RECORDS:
            return APIError(429, "record_limit")
        if self._generations + len(self._pending) >= self.request["max_generations"]:
            return APIError(503, "service_budget_exhausted")
        if self.reserved_metadata + (len(self._jobs) + 1) * REQUEST_RESERVE > self.store.max_bytes:
            return APIError(503, "output_budget_exhausted")
        if not self._loaded or self._worker is None or not self._worker.process.is_alive():
            return APIError(503, "not_ready")
        if len(self._pending) >= MAX_PENDING:
            return APIError(429, "queue_full")
        return None

    def readiness(self):
        with self._condition:
            self._poll()
            ready = (self._loaded and self._worker is not None
                     and self._worker.process.is_alive() and not self._stopping)
            error = self._admission_error()
            return {"schema": HTTP_SCHEMA, "service_run_id": self.request["run_id"],
                    "ready": ready, "accepting": ready and error is None,
                    "worker_epoch": self._epoch or None, "reason": None if error is None else error.code}

    def submit(self, principal, key, payload, raw):
        key = idempotency_key(key)
        validate_request(payload, self.request["run_id"], self.registry)
        payload_hash = canonical_hash(payload)
        with self._condition:
            self._poll()
            previous = self._keys.get((principal, key))
            if previous is not None:
                state = self._jobs[previous].state
                if state["payload_hash"] != payload_hash:
                    raise APIError(409, "idempotency_conflict")
                return self._receipt(state, True)
            if error := self._admission_error():
                raise error
            accepted = time.monotonic()
            expires = min(accepted + payload["timeout_ms"] / 1000, self.dispatch_stop)
            ident = uuid.uuid4().hex
            state = {"schema": HTTP_SCHEMA, "service_run_id": self.request["run_id"], "request_id": ident,
                     "input_hash": canonical_hash(payload["model_input"]), "payload_hash": payload_hash,
                     "status": "queued", "reason": None, "accepted_at_utc": now(),
                     "deadline_utc": (datetime.now(timezone.utc) + timedelta(seconds=expires - accepted)).isoformat(),
                     "started_at_utc": None, "finished_at_utc": None, "worker_epoch": None,
                     "worker_cleanup": "not_started", "result": None,
                     "timing": dict.fromkeys(TIMINGS)}
            job = _Job(principal, key, copy.deepcopy(payload), state, accepted, expires, CancellationToken())
            self.store.write(f"requests/{ident}/input.json", raw)
            self._write(f"requests/{ident}/accepted.json", {"principal": principal, "key": key, "state": state})
            self._jobs[ident], self._keys[(principal, key)] = job, ident
            self._pending.append(ident)
            self._condition.notify_all()
            return self._receipt(state, False)

    def _receipt(self, state, replayed):
        return (200 if state["status"] in TERMINAL else 202), {
            "schema": HTTP_SCHEMA, "service_run_id": self.request["run_id"],
            "request_id": state["request_id"], "status": state["status"], "replayed": replayed}

    def _find(self, principal, ident):
        job = self._jobs.get(ident)
        if job is None or job.principal != principal:
            raise APIError(404, "request_not_found")
        return job

    def lookup(self, principal, *, ident=None, key=None):
        if key is not None:
            key = idempotency_key(key)
        with self._condition:
            self._poll()
            if key is not None:
                ident = self._keys.get((principal, key))
            return copy.deepcopy(self._find(principal, ident).state)

    def cancel(self, principal, ident):
        with self._condition:
            self._poll()
            job = self._find(principal, ident)
            if job.state["status"] == "queued":
                self._pending.remove(ident)
                self._finish(job, "cancelled", "cancel_requested")
            elif job.state["status"] == "running":
                self._begin_stop(job, "cancel_requested")
            self._condition.notify_all()
            return (202 if job.state["status"] == "stopping" else 200), copy.deepcopy(job.state)

    def _begin_stop(self, job, reason):
        if job.state["status"] not in TERMINAL and job.state["status"] != "stopping":
            job.cancellation.cancel()
            job.state.update(status="stopping", reason=reason)
            self._write(f"requests/{job.state['request_id']}/stopping.json", job.state)

    def _finish(self, job, status, reason):
        if job.state["status"] in TERMINAL:
            return
        job.state.update(status=status, reason=reason, finished_at_utc=now())
        timing = job.state["timing"]
        if timing["queue_seconds"] is None:
            timing["queue_seconds"] = time.monotonic() - job.accepted
        timing["complete_wall_seconds"] = time.monotonic() - job.accepted
        self._write(f"requests/{job.state['request_id']}/terminal.json", job.state)

    def _poll(self):
        if not self._stopping and (self.cancellation.is_cancelled() or time.monotonic() >= self.dispatch_stop):
            self._stop_locked("signal" if self.cancellation.is_cancelled() else "service_budget_exhausted")
        for ident in list(self._pending):
            job = self._jobs[ident]
            if time.monotonic() >= job.expires:
                self._pending.remove(ident)
                self._finish(job, "timed_out", "queue_deadline")

    def _stop_locked(self, reason):
        if self._stopping:
            return
        self._stopping, self._loaded, self._reason = True, False, reason
        self._stop_token.cancel()
        while self._pending:
            job = self._jobs[self._pending.popleft()]
            self._finish(job, "cancelled", "service_stopping")
        if self._active is not None:
            self._begin_stop(self._jobs[self._active], "service_stopping")
        self._condition.notify_all()

    def request_stop(self, reason="requested"):
        with self._condition:
            self._stop_locked(reason)

    def stop(self, reason="requested"):
        self.request_stop(reason)
        self.thread.join(timeout=CLEANUP_SECONDS)
        if self.thread.is_alive():
            raise RuntimeError("service_cleanup_unconfirmed")
        return self.summary

    def _wait(self, filename, expires, cancellation):
        # Short waits also expire queued work while prepare/reload or decode runs.
        while True:
            with self._condition:
                self._poll()
            status, packet = self._worker.wait(filename, min(expires, time.monotonic() + 0.05), cancellation)
            if status != "timed_out" or time.monotonic() >= expires:
                return status, packet

    def _prepare_worker(self):
        started = time.monotonic()
        with self._condition:
            self._poll()
            if self._stopping:
                return False
            self._epoch += 1
            self._worker_calls = 0
            backend = self.backend_factory()
            self._worker = OwnedProcess(self.sandbox.resolve(), service_child,
                (backend, self._epoch, self.request["max_generations"] - self._generations), "model")
            record = {"epoch": self._epoch, "started_at_utc": now(), "process": self._worker.record}
            self.workers.append(record)
            self._write(f"workers/{self._epoch:04d}.started.json", record)
        # Initial startup includes the parent's file/dependency preflight.
        load_started = self.started if self._epoch == 1 else started
        status, packet = self._wait("ready.json", min(load_started + STARTUP_SECONDS, self.dispatch_stop),
                                    _Cancellation(self._stop_token, self.cancellation))
        with self._condition:
            valid = (status == "completed" and packet["epoch"] == self._epoch and packet["error"] is None
                     and canonical_hash(packet["ready"]["model_identity"]) == canonical_hash(self.model_identity)
                     and self._worker.process.is_alive() and not self._stopping)
            record.update(prepare_seconds=time.monotonic() - started, prepare_status=status,
                          ready=packet, loaded=valid)
            self._write(f"workers/{self._epoch:04d}.ready.json", record)
            self._loaded = valid
        if not valid:
            self._close_worker()
            with self._condition:
                if not self._stopping:
                    while self._pending:
                        self._finish(self._jobs[self._pending.popleft()], "infrastructure_error", "worker_start_failed")
                    self._stop_locked("worker_start_failed")
        return valid

    def _close_worker(self):
        if self._worker is None:
            return True, 0.0
        with self._condition:
            self._loaded = False
        started = time.monotonic()
        record = self.workers[-1]
        try:
            metric_path = self._worker.directory / "backend-metrics.json"
            if metric_path.exists():
                record["backend_metrics"] = read_packet(metric_path, MODEL_BYTES)
        except (OSError, ValueError) as error:
            record["metrics_error"] = type(error).__name__
        try:
            try:
                write_packet(self._worker.directory / "stop.json", {})
            finally:
                self._worker.close()
            observation = inspect_gpu_lock(self.request["repository"])
            record["lease_held_by_worker_after_close"] = (observation["held"]
                and (observation.get("owner") or {}).get("pid") == record["process"]["pid"])
            require(not record["lease_held_by_worker_after_close"], "worker_lease_not_released")
        except (OSError, ValueError, RuntimeError) as error:
            record["cleanup_error"] = type(error).__name__
            self._cleanup_unconfirmed = True
        record.update(closed_at_utc=now(), cleanup_seconds=time.monotonic() - started)
        self._write(f"workers/{self._epoch:04d}.closed.json", record)
        if self._cleanup_unconfirmed:
            with self._condition:
                if self._active is not None:
                    job = self._jobs[self._active]
                    job.state.update(status="stopping", reason="cleanup_unconfirmed", worker_cleanup="unconfirmed")
                    self._write(f"requests/{self._active}/cleanup-unconfirmed.json", job.state)
                self._stop_locked("cleanup_unconfirmed")
            return False, record["cleanup_seconds"]
        with self._condition:
            self._worker = None
        return True, record["cleanup_seconds"]

    def _packet_result(self, packet):
        output = packet["output"]
        if output is None:
            diagnostic = packet.get("diagnostic")
            usage = packet.get("usage") or {}
            result = {
                "raw_text": None if diagnostic is None else diagnostic.get("raw_text"),
                "finish_reason": None, "raw_action": None, "raw_action_valid": False,
                "raw_parse_failure": "no_output", "model_identity": None,
                "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
                "token_accounting_complete": all(type(usage.get(k)) is int and usage[k] >= 0
                                                 for k in ("input_tokens", "output_tokens")),
                "diagnostic": None if diagnostic is None else {k: diagnostic[k]
                    for k in ("raw_sha256", "raw_size_bytes", "raw_truncated")}}
            if result["raw_text"] is not None:
                try:
                    result.update(raw_action=parse_action(result["raw_text"]),
                                  raw_action_valid=True, raw_parse_failure=None)
                except ContractError:
                    result["raw_parse_failure"] = "invalid_raw_action"
            return "infrastructure_error", "backend_error", result
        checked = gate_output(output, self.model_identity)
        allowed = {"completed", "model_identity_mismatch", "invalid_token_accounting", "timed_out",
                   "cancelled", "response_token_limit", "invalid_raw_action", "context_overflow", "backend_error",
                   "deadline_before_tokenization", "deadline_before_load", "deadline_before_forward"}
        reason = checked["reason"] if checked["reason"] in allowed else "backend_error"
        result = {key: checked[key] for key in ("raw_text", "finish_reason", "raw_action", "raw_action_valid",
                                               "raw_parse_failure", "token_accounting_complete")}
        result.update(model_identity=output["model_identity"], diagnostic=None)
        result.update({k: output[k] if type(output[k]) is int and output[k] >= 0 else None
                       for k in ("input_tokens", "output_tokens")})
        return checked["status"], reason, result

    def _perform(self, job):
        index = self._worker_calls
        path = self._worker.directory / f"result-{index}.json"
        config = GenerationConfig(job.payload["seed"], 0.7, 0.9, 256, job.state["deadline_utc"])
        packet = None
        outcome, reason = "infrastructure_error", "backend_error"
        try:
            write_packet(self._worker.directory / f"request-{index}.json",
                         {"input": job.payload["model_input"], "config": asdict(config),
                          "principal": job.principal}, INPUT_BYTES + 4096)
            self._worker_calls += 1
            status, packet = self._wait(path.name, job.expires,
                _Cancellation(job.cancellation, self._stop_token, self.cancellation))
            if packet is None and path.exists():
                packet = read_packet(path)
            if packet is not None:
                outcome, reason, result = self._packet_result(packet)
                with self._condition:
                    job.state["result"] = result
                    timing = job.state["timing"]
                    timing["child_generation_seconds"] = packet["child_generation_seconds"]
                    for key in ("ttft_seconds", "prefill_seconds", "decode_seconds", "cache_hit_tokens", "prefill_tokens"):
                        timing[key] = packet.get("metrics", {}).get(key)
            if status == "error":
                outcome, reason = "infrastructure_error", "worker_exited"
        except (OSError, ValueError, TypeError, KeyError):
            outcome, reason = "infrastructure_error", "backend_error"
        with self._condition:
            self._poll()
            if job.state["status"] == "stopping":
                outcome, reason = "cancelled", job.state["reason"]
            elif time.monotonic() >= job.expires or outcome == "timed_out":
                outcome, reason = "timed_out", "request_deadline"
            if outcome != "completed":
                self._begin_stop(job, reason)
        if outcome != "completed":
            reaped, seconds = self._close_worker()
            with self._condition:
                job.state["timing"]["cleanup_seconds"] = seconds
                if not reaped:
                    return
                job.state["worker_cleanup"] = "reaped"
        with self._condition:
            self._finish(job, outcome, reason)
            if outcome == "completed":
                write_packet(self._worker.directory / f"ack-{index}.json", {})
            self._active = None

    def _run(self):
        try:
            while True:
                with self._condition:
                    self._poll()
                    if self._stopping:
                        break
                    remaining = self._generations < self.request["max_generations"]
                if self._worker is None and remaining:
                    if not self._prepare_worker():
                        break
                if self._worker is not None and not self._worker.process.is_alive():
                    self._close_worker()
                    self.request_stop("worker_exited")
                    break
                if not remaining and self._worker is not None:
                    self._close_worker()
                with self._condition:
                    self._poll()
                    if self._stopping:
                        break
                    if not self._pending:
                        self._condition.wait(timeout=0.05)
                        continue
                    ident = self._pending.popleft()
                    job = self._jobs[ident]
                    self._active = ident
                    self._generations += 1
                    job.state.update(status="running", started_at_utc=now(), worker_epoch=self._epoch,
                                     worker_cleanup="live")
                    job.state["timing"]["queue_seconds"] = time.monotonic() - job.accepted
                    self._write(f"requests/{ident}/started.json", job.state)
                self._perform(job)
        except Exception as error:
            with self._condition:
                self._reason = "scheduler_" + type(error).__name__
                self._stop_locked(self._reason)
        finally:
            if not self._cleanup_unconfirmed:
                reaped, seconds = self._close_worker()
                with self._condition:
                    if self._active is not None and reaped:
                        job = self._jobs[self._active]
                        job.state["worker_cleanup"] = "reaped"
                        job.state["timing"]["cleanup_seconds"] = seconds
                        self._finish(job, "infrastructure_error", "backend_error")
                        self._active = None
            with self._condition:
                self.summary = {"schema": "toolalign.service-summary.v1", "run_id": self.request["run_id"],
                    "execution_kind": self.identity["execution_kind"], "status": self._reason or "stopped",
                    "accepted_requests": len(self._jobs), "generation_attempts": self._generations,
                    "terminal_counts": dict(Counter(job.state["status"] for job in self._jobs.values())),
                    "cleanup_confirmed": not self._cleanup_unconfirmed,
                    "wall_seconds": time.monotonic() - self.started,
                    "workers": [{k: v for k, v in worker.items() if k not in ("ready", "backend_metrics")}
                                for worker in self.workers],
                    "model_task_success": "NOT_SCORED"}
                self._write("summary.json", self.summary)
            self.done.set()
