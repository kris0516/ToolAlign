"""Original CPU HTTP fixture for client examples, not the CUDA service.

Each scripted response runs in a real owned CPU child. This fixture has no CUDA,
model loading, GPU lease, prefix cache, production queue or model-quality claim.
Token counts and artifact hashes on its wire are explicitly synthetic.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from toolalign.contracts import ContractError, canonical_hash
from toolalign.tools import CancellationToken, LocalToolRegistry
from toolalign.tools._json import INPUT_BYTES, clone, decode, parse_action
from toolalign.tools.isolation import OwnedProcess, enter_child, write_packet
from toolalign.tools.scripted import SCRIPTED_IDENTITY

from . import protocol as p
from .http import write_record


def now():
    return datetime.now(timezone.utc).isoformat()


def _scripted_child(directory, raw_text, delay_seconds):
    enter_child(directory)
    time.sleep(delay_seconds)
    write_packet(Path(directory) / "raw.json", {"raw_text": raw_text})


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, value):
        data = json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle(self):
        if self.headers.get("Authorization") != "Bearer " + self.server.fixture.token:
            self._send(401, {"schema": p.SCHEMA, "error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= INPUT_BYTES:
                self._send(413, {"schema": p.SCHEMA, "error": "request_too_large"})
                return
            body = decode(self.rfile.read(length), INPUT_BYTES) if length else None
            status, value = self.server.fixture.dispatch(self.command, self.path, self.headers.get("Idempotency-Key"), body)
        except (ContractError, ValueError, KeyError, TypeError):
            status, value = 400, {"schema": p.SCHEMA, "error": "invalid_request"}
        self._send(status, value)

    do_GET = _handle
    do_POST = _handle


class ScriptedHTTPFixture:
    def __init__(self, root, responses, *, delay_seconds=0):
        self.root = root.resolve()
        self.responses = list(responses)
        self.delay = delay_seconds
        self.token = secrets.token_urlsafe(32)
        self.run_id = "original-scripted-" + uuid.uuid4().hex
        self.jobs, self.keys = {}, {}
        self.requests = []
        self.lock = threading.Lock()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.server.fixture = self
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.closed = False

    def __enter__(self):
        self.thread.start()
        return self

    def config(self):
        token_path = self.root / "token.txt"
        descriptor = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(self.token + "\n")
        value = {"schema": "toolalign.mac-client.v1", "url": f"http://127.0.0.1:{self.server.server_port}",
                 "service_run_id": self.run_id, "model_identity": clone(SCRIPTED_IDENTITY),
                 "token_file": str(token_path)}
        write_record(self.root / "client-config.json", value)
        return value

    def dispatch(self, method, path, key, body):
        with self.lock:
            self.requests.append({"method": method, "path": path, "key": key,
                                  "body": body, "at_monotonic": time.monotonic()})
            if method == "GET" and path == "/v1/model-info":
                return 200, {"schema": p.SCHEMA, "service_run_id": self.run_id,
                    "source_commit": "0" * 40, "model_identity": clone(SCRIPTED_IDENTITY),
                    "checkpoint_sha256": "0" * 64, "dependency_lock_sha256": "0" * 64,
                    "catalog_id": p.CATALOG, "registry_hash": LocalToolRegistry().registry_hash,
                    "sampling": p.SAMPLING, "limits": p.LIMITS,
                    "cache": {"enabled": False, "max_entries": 1, "scope": "principal"}}
            if method == "GET" and path == "/readyz":
                return 200, {"schema": p.SCHEMA, "service_run_id": self.run_id, "ready": True,
                             "accepting": not any(j["state"]["status"] not in p.TERMINAL for j in self.jobs.values()),
                             "worker_epoch": max(1, len(self.jobs)), "reason": None}
            if path == "/v1/tool-decisions":
                if method == "GET":
                    request_id = self.keys.get(key)
                    return (404, {"schema": p.SCHEMA, "error": "request_not_found"}) if request_id is None else (200, clone(self.jobs[request_id]["state"], INPUT_BYTES))
                if method == "POST":
                    return self._accept(key, body)
            if path.startswith("/v1/runs/"):
                suffix = path[len("/v1/runs/"):]
                cancelling = suffix.endswith("/cancel") and method == "POST"
                request_id = unquote(suffix[:-7] if cancelling else suffix)
                job = self.jobs.get(request_id)
                if job is None:
                    return 404, {"schema": p.SCHEMA, "error": "request_not_found"}
                if cancelling:
                    p.require(body == {}, "cancel_body")
                    if job["state"]["status"] not in p.TERMINAL:
                        job["stop"].cancel()
                        job["state"].update(status="stopping", reason="cancel_requested")
                    status = 200 if job["state"]["status"] in p.TERMINAL else 202
                    return status, clone(job["state"], INPUT_BYTES)
                if method == "GET":
                    return 200, clone(job["state"], INPUT_BYTES)
            return 404, {"schema": p.SCHEMA, "error": "endpoint_not_found"}

    def _accept(self, key, body):
        p.fields(body, "schema service_run_id model_input seed timeout_ms", "request_fields")
        p.require(body["schema"] == p.SCHEMA and body["service_run_id"] == self.run_id, "request_run")
        p.require(type(key) is str and key and p.integer(body["seed"], 0, 2**63 - 1)
                  and p.integer(body["timeout_ms"], 1, 30000), "request_values")
        p.bound_input(body["model_input"])
        payload_hash = canonical_hash(body)
        replayed = key in self.keys
        if replayed:
            job = self.jobs[self.keys[key]]
            if job["state"]["payload_hash"] != payload_hash:
                return 409, {"schema": p.SCHEMA, "error": "idempotency_conflict"}
        else:
            if len(self.jobs) >= len(self.responses):
                return 429, {"schema": p.SCHEMA, "error": "record_limit"}
            request_id = uuid.uuid4().hex
            start = time.monotonic()
            state = {"schema": p.SCHEMA, "service_run_id": self.run_id, "request_id": request_id,
                     "input_hash": canonical_hash(body["model_input"]), "payload_hash": payload_hash,
                     "status": "queued", "reason": None, "accepted_at_utc": now(),
                     "deadline_utc": (datetime.now(timezone.utc) + timedelta(milliseconds=body["timeout_ms"])).isoformat(),
                     "started_at_utc": None, "finished_at_utc": None, "worker_epoch": None,
                     "worker_cleanup": "not_started", "result": None,
                     "timing": dict.fromkeys((p.TIMES + " cache_hit_tokens prefill_tokens").split())}
            job = {"state": state, "stop": CancellationToken(), "start": start,
                   "expires": start + body["timeout_ms"] / 1000, "process": None,
                   "response": self.responses[len(self.jobs)], "epoch": len(self.jobs) + 1}
            self.jobs[request_id], self.keys[key] = job, request_id
            job["thread"] = threading.Thread(target=self._generate, args=(job,), daemon=True)
            job["thread"].start()
        state = job["state"]
        return (200 if state["status"] in p.TERMINAL else 202), {
            "schema": p.SCHEMA, "service_run_id": self.run_id, "request_id": state["request_id"],
            "status": state["status"], "replayed": replayed,
        }

    def _generate(self, job):
        owned = None
        status, reason, output = "infrastructure_error", "worker_exited", None
        generated_at = time.monotonic()
        try:
            if job["stop"].is_cancelled():
                status, reason = "cancelled", "cancel_requested"
                return
            owned = OwnedProcess(self.root, _scripted_child, (job["response"], self.delay), "scripted-http")
            with self.lock:
                job["process"] = owned.record
                job["state"].update(status="running", started_at_utc=now(),
                                    worker_epoch=job["epoch"], worker_cleanup="live")
            waited, packet = owned.wait("raw.json", job["expires"], job["stop"])
            if waited == "completed":
                raw = packet["raw_text"]
                try:
                    action = parse_action(raw)
                except ContractError:
                    action = None
                output = {"raw_text": raw, "finish_reason": "stop", "raw_action": action,
                          "raw_action_valid": action is not None,
                          "raw_parse_failure": None if action is not None else "invalid_raw_action",
                          "model_identity": clone(SCRIPTED_IDENTITY), "input_tokens": 11, "output_tokens": 7,
                          "token_accounting_complete": True, "diagnostic": None}
                status, reason = ("completed", None) if action is not None else ("parse_failure", "invalid_raw_action")
            elif waited in ("timed_out", "cancelled"):
                status, reason = waited, "request_deadline" if waited == "timed_out" else "cancel_requested"
        finally:
            cleanup_started = time.monotonic()
            if owned is not None:
                owned.close()
            with self.lock:
                job["state"].update(status=status, reason=reason, result=output, finished_at_utc=now(),
                                    worker_cleanup="reaped" if owned is not None else "not_started")
                job["state"]["timing"].update(queue_seconds=generated_at - job["start"],
                    child_generation_seconds=cleanup_started - generated_at,
                    cleanup_seconds=time.monotonic() - cleanup_started,
                    complete_wall_seconds=time.monotonic() - job["start"])

    def close(self):
        if self.closed:
            return
        for job in self.jobs.values():
            job["stop"].cancel()
        for job in self.jobs.values():
            job["thread"].join(timeout=5)
            if job["thread"].is_alive():
                raise RuntimeError("scripted_fixture_cleanup_unconfirmed")
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.closed = True

    def evidence(self):
        return {"purpose": "ORIGINAL_SCRIPTED_CPU_HTTP_FIXTURE", "real_model": "NOT_RUN",
                "synthetic_token_counts": True, "requests": self.requests,
                "states": [clone(job["state"], INPUT_BYTES) for job in self.jobs.values()],
                "process_records": [clone(job["process"]) for job in self.jobs.values() if job["process"] is not None]}

    def __exit__(self, *args):
        self.close()
