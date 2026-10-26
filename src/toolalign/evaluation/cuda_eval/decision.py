"""One-decision calls; no tools, oracle or scoring enter this owned session."""

from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from toolalign.contracts import ContractError, canonical_hash
from toolalign.contracts.interfaces import GenerationConfig
from toolalign.evaluation.harness import _model_child
from toolalign.model_io.format import validate_model_input
from toolalign.tools._json import INPUT_BYTES, clone, parse_action
from toolalign.tools.isolation import OwnedProcess, read_packet, write_packet


class DecisionSession:
    """At most three requests and 90 seconds, with at most 30 seconds per request."""

    def __init__(self, root, backend, *, model_identity, cancellation, expires_monotonic):
        self.identity = model_identity
        self.cancellation = cancellation
        self.expires = min(expires_monotonic, time.monotonic() + 90)
        self._backend = backend
        self._root = root
        self.process = None
        self.calls = 0
        self.closed = False
        self.metrics = {}

    @property
    def process_records(self):
        return [] if self.process is None else [clone(self.process.record)]

    def generate(self, model_input, *, seed):
        if self.closed or self.calls >= 3:
            raise ValueError("decision_session_closed_or_exhausted")
        request = clone(validate_model_input(model_input), INPUT_BYTES)
        started = time.monotonic()
        expires = min(self.expires, started + 30)
        deadline = (datetime.now(timezone.utc) + timedelta(seconds=max(0, expires - started))).isoformat()
        config = GenerationConfig(seed, 0.7, 0.9, 256, deadline)
        result = {"model_input": request, "model_input_hash": canonical_hash(request),
                  "generation_config": asdict(config), "status": "infrastructure_error",
                  "reason": None, "output": None, "raw_text": None, "finish_reason": None,
                  "raw_action": None, "raw_action_valid": False, "raw_parse_failure": "no_output",
                  "token_accounting_complete": False, "timing": None, "diagnostic": None}
        try:
            if self.cancellation.is_cancelled() or started >= expires:
                result.update(status="cancelled" if self.cancellation.is_cancelled() else "timed_out",
                              reason="before_dispatch")
                return result
            if self.process is None:
                self.process = OwnedProcess(self._root, _model_child, (self._backend,), "model")
            index = self.calls
            self.calls += 1
            write_packet(self.process.directory / f"request-{index}.json",
                         {"input": request, "config": asdict(config),
                          "submitted_monotonic": time.monotonic()})
            status, packet = self.process.wait(f"result-{index}.json", expires, self.cancellation)
            if status != "completed":
                result.update(status=status if status in ("cancelled", "timed_out")
                              else "infrastructure_error", reason="owned_child_" + status)
                return result
            result["timing"] = packet.get("timing")
            if packet["error"] is not None:
                result.update(reason=packet["error"], diagnostic=packet["diagnostic"],
                              usage=packet["usage"])
                return result
            output = packet["output"]
            result.update(output=output, raw_text=output["raw_text"], finish_reason=output["finish_reason"])
            # Parse raw text independently even when execution or finish reason failed.
            try:
                result.update(raw_action=clone(parse_action(output["raw_text"])),
                              raw_action_valid=True, raw_parse_failure=None)
            except ContractError:
                result["raw_parse_failure"] = "invalid_raw_action"
            counts_valid = all(type(output[k]) is int and output[k] >= 0
                               for k in ("input_tokens", "output_tokens"))
            result["token_accounting_complete"] = counts_valid
            if canonical_hash(output["model_identity"]) != canonical_hash(self.identity):
                result["reason"] = "model_identity_mismatch"
            elif not counts_valid:
                result["reason"] = "invalid_token_accounting"
            elif output["finish_reason"] in ("timed_out", "cancelled"):
                result.update(status=output["finish_reason"], reason=output["finish_reason"])
            elif output["output_tokens"] > 256 or output["finish_reason"] == "length":
                result.update(status="budget_exhausted", reason="response_token_limit")
            elif output["finish_reason"] != "stop":
                result["reason"] = output.get("parse_failure") or "backend_error"
            elif not result["raw_action_valid"]:
                result.update(status="parse_failure", reason="invalid_raw_action")
            elif self.cancellation.is_cancelled() or time.monotonic() >= expires:
                result.update(status="cancelled" if self.cancellation.is_cancelled() else "timed_out",
                              reason="request_deadline_or_cancellation")
            else:
                result.update(status="completed", reason="completed")
            return result
        except (OSError, ValueError, KeyError, TypeError) as error:
            result["reason"] = type(error).__name__ + ": " + str(error)[:1000]
            return result
        finally:
            result["elapsed_seconds"] = time.monotonic() - started
            if result["status"] != "completed":
                # Every failed/cancelled request destroys its cache and process lifetime.
                self.close()

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.process is None:
            return
        try:
            metric_path = self.process.directory / "backend-metrics.json"
            if metric_path.exists():
                try:
                    self.metrics = read_packet(metric_path)
                    if self.metrics.get("cold_load_seconds") is None:
                        since = self.metrics.get("cold_load_started_monotonic")
                        if type(since) in (int, float):
                            self.metrics["incomplete_cold_load_seconds"] = max(0, time.monotonic() - since)
                except (OSError, ValueError, AttributeError):
                    self.metrics = {"error": "unreadable_backend_metrics"}
            self.process.record["operation_started"] = (self.process.directory / "generating-0.json").exists()
            write_packet(self.process.directory / "stop.json", {})
        finally:
            self.process.close()


def one_decision(model_input, backend, root, *, model_identity, seed, cancellation,
                 expires_monotonic):
    started = time.monotonic()
    session = DecisionSession(root, backend, model_identity=model_identity,
                              cancellation=cancellation, expires_monotonic=expires_monotonic)
    try:
        result = session.generate(model_input, seed=seed)
    finally:
        session.close()
    if result["status"] == "completed" and (cancellation.is_cancelled()
            or time.monotonic() >= min(expires_monotonic, started + 30)):
        result.update(status="cancelled" if cancellation.is_cancelled() else "timed_out",
                      reason="request_deadline_or_cancellation")
    result.update(process_records=session.process_records, backend_metrics=session.metrics,
                  complete_wall_seconds=time.monotonic() - started)
    return result
