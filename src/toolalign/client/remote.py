"""Durable decision receipts, same-key recovery, and explicit remote cancellation."""

from __future__ import annotations

import time
import uuid
from urllib.parse import quote

from toolalign.contracts import ContractError
from toolalign.tools import CancellationToken

from . import protocol as p
from .http import APIError, LoopbackHTTP, TransportError, write_record


def pause(expires, cancellation):
    end = min(expires, time.monotonic() + 0.05)
    while not cancellation.is_cancelled() and time.monotonic() < end:
        time.sleep(min(0.01, max(0, end - time.monotonic())))


class RemoteClient:
    def __init__(self, config, *, cleanup_ms=5000):
        p.require(p.integer(cleanup_ms, 1, 30000), "cleanup_budget")
        self.config = config
        self.cleanup_ms = cleanup_ms
        self.http = LoopbackHTTP(config["url"], config["token_file"])

    def _exchange(self, receipt, method, path, expires, cancellation, *, body=None, key=None):
        started = time.monotonic()
        event = {"method": method, "path": path, "http_status": None, "error": None}
        receipt["http_events"].append(event)
        try:
            status, value = self.http.request(method, path, expires=expires,
                                            cancellation=cancellation, body=body, key=key)
            event["http_status"] = status
            return status, value
        except p.ClientError as exc:
            event["error"] = str(exc)
            raise
        finally:
            event["seconds"] = time.monotonic() - started

    def _ready(self, receipt, expires, cancellation):
        status, value = self._exchange(receipt, "GET", "/v1/model-info", expires, cancellation)
        if status != 200:
            raise APIError(status, value)
        receipt["model_info"] = p.model_info(value, self.config["service_run_id"], self.config["model_identity"])
        while time.monotonic() < expires and not cancellation.is_cancelled():
            status, value = self._exchange(receipt, "GET", "/readyz", expires, cancellation)
            if status not in (200, 503) or "ready" not in value:
                raise APIError(status, value)
            receipt["readiness"] = p.readiness(value, self.config["service_run_id"], status)
            if value["ready"] and value["accepting"]:
                return
            pause(expires, cancellation)
        raise TransportError("transport_deadline_or_cancelled")

    def _state(self, receipt, expires, cancellation, *, by_key=False):
        path = "/v1/tool-decisions" if by_key else "/v1/runs/" + quote(receipt["request_id"], safe="")
        status, value = self._exchange(receipt, "GET", path, expires, cancellation,
                                       key=receipt["idempotency_key"] if by_key else None)
        if status != 200:
            raise APIError(status, value)
        try:
            state, action = p.request_state(value, receipt["request_body"], self.config["model_identity"],
                                            receipt["request_id"])
        except (p.ClientError, ContractError, KeyError, TypeError):
            if receipt.get("rejected_response") is None:
                receipt["rejected_response"] = value
            raise
        receipt["request_id"] = state["request_id"]
        receipt["state"] = state
        return state, action

    def cleanup(self, receipt):
        """No creation/replay POST here, including when no request ID is known."""
        started = time.monotonic()
        expires = started + self.cleanup_ms / 1000
        cancellation = CancellationToken()
        outcome = {"resolution": "unknown", "request_id": receipt["request_id"],
                   "state": None, "reason": "cleanup_unconfirmed", "seconds": None}
        try:
            while time.monotonic() < expires:
                try:
                    state, _ = self._state(receipt, expires, cancellation, by_key=True)
                    outcome.update(request_id=state["request_id"], state=state)
                    if state["status"] in p.TERMINAL:
                        outcome.update(resolution="terminal_observed", reason=None)
                        break
                    status, value = self._exchange(
                        receipt, "POST", "/v1/runs/" + quote(state["request_id"], safe="") + "/cancel",
                        expires, cancellation, body={},
                    )
                    if status not in (200, 202):
                        raise APIError(status, value)
                    state, _ = p.request_state(value, receipt["request_body"], self.config["model_identity"],
                                                state["request_id"])
                    p.require(status == (200 if state["status"] in p.TERMINAL else 202), "cancel_http_status")
                    receipt["state"] = state
                    outcome["state"] = state
                    if state["status"] in p.TERMINAL:
                        outcome.update(resolution="terminal_observed", reason=None)
                        break
                except (p.ClientError, ContractError, KeyError, TypeError):
                    # A 404 or unreachable network proves neither absence of a
                    # late original POST nor remote reaping. Keep querying only.
                    pass
                pause(expires, cancellation)
        finally:
            outcome["seconds"] = time.monotonic() - started
        return outcome

    def decision(self, model_input, *, seed, expires, cancellation, receipt_path):
        model_input, _ = p.bound_input(model_input)
        p.require(p.integer(seed, 0, 2**63 - 1), "seed")
        started = time.monotonic()
        # A sub-millisecond remainder is still a timeout/cancellation path, not
        # invalid input. Every HTTP attempt checks the original expiry first.
        remaining_ms = max(1, min(30000, int((expires - started) * 1000)))
        body = {"schema": p.SCHEMA, "service_run_id": self.config["service_run_id"],
                "model_input": model_input, "seed": seed, "timeout_ms": remaining_ms}
        receipt = {"schema": "toolalign.client-decision.v1", "idempotency_key": uuid.uuid4().hex,
                   "request_body": body, "request_id": None, "post_attempts": 0,
                   "creation_rejected": False,
                   "model_info": None, "readiness": None, "http_events": [], "state": None,
                   "local_action": None, "status": "unknown", "reason": None, "cleanup": None,
                   "rejected_response": None}
        # The original key and payload exist on disk before any creation attempt.
        write_record(receipt_path, receipt)
        try:
            self._ready(receipt, expires, cancellation)
            submit = True
            while time.monotonic() < expires and not cancellation.is_cancelled():
                if submit:
                    receipt["post_attempts"] += 1
                    write_record(receipt_path, receipt)
                    try:
                        status, value = self._exchange(receipt, "POST", "/v1/tool-decisions", expires,
                                                        cancellation, body=body, key=receipt["idempotency_key"])
                        if status not in (200, 202):
                            raise APIError(status, value)
                        ack = p.acknowledgement(value, self.config["service_run_id"], status)
                        p.require(receipt["request_id"] in (None, ack["request_id"]), "request_id_mismatch")
                        receipt["request_id"] = ack["request_id"]
                        write_record(receipt_path, receipt)
                    except APIError:
                        receipt["creation_rejected"] = receipt["post_attempts"] == 1
                        raise
                    except TransportError:
                        pass
                    submit = False
                if time.monotonic() >= expires or cancellation.is_cancelled():
                    break
                try:
                    state, action = self._state(receipt, expires, cancellation,
                                                by_key=receipt["request_id"] is None)
                    write_record(receipt_path, receipt)
                    if time.monotonic() >= expires or cancellation.is_cancelled():
                        break
                    if state["status"] in p.TERMINAL:
                        receipt.update(status=state["status"], reason=state["reason"], local_action=action)
                        break
                except APIError as exc:
                    if exc.status != 404 or exc.remote_code != "request_not_found" or receipt["request_id"] is not None:
                        raise
                    # Reuse the original body/key only while its local deadline
                    # still permits POST; never increase timeout_ms on a retry.
                    submit = True
                except TransportError:
                    pass
                pause(expires, cancellation)
            if receipt["status"] == "unknown":
                receipt.update(status="cancelled" if cancellation.is_cancelled() else "timed_out",
                               reason="local_cancelled" if cancellation.is_cancelled() else "local_deadline")
        except (p.ClientError, ContractError, KeyError, TypeError, OSError) as exc:
            receipt.update(status="cancelled" if cancellation.is_cancelled() else
                           "timed_out" if time.monotonic() >= expires else "rejected",
                           reason=str(exc) if isinstance(exc, p.ClientError) else "invalid_contract_or_local_io")
        finally:
            receipt["decision_seconds"] = time.monotonic() - started
            state = receipt["state"]
            if receipt["post_attempts"] and not receipt["creation_rejected"] and (state is None or state["status"] not in p.TERMINAL):
                receipt["cleanup"] = self.cleanup(receipt)
            receipt["cleanup_seconds"] = 0 if receipt["cleanup"] is None else receipt["cleanup"]["seconds"]
            receipt["complete_wall_seconds"] = time.monotonic() - started
            write_record(receipt_path, receipt)
        return receipt
