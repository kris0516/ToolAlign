"""Three remote decisions, two local tool rounds, and an explicit final Action."""

from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from toolalign.contracts import ContractError, canonical_hash
from toolalign.contracts.interfaces import Rejection, SandboxContext
from toolalign.tools import CancellationToken, LocalToolExecutor
from toolalign.tools._json import INPUT_BYTES, clone, encode
from toolalign.tools.scripted import SCRIPTED_IDENTITY

from . import protocol as p
from .http import write_record


class ClientCancellation(CancellationToken):
    def __init__(self):
        super().__init__()
        self.cancelled_at = None

    def cancel(self):
        if self.cancelled_at is None:
            self.cancelled_at = time.monotonic()
        super().cancel()


def run_trajectory(client, model_input, root, *, seed=42, timeout_ms=30000,
                   cancellation=None, faults=None):
    p.require(p.integer(timeout_ms, 1, 30000), "trajectory_budget")
    prefix, registry = p.bound_input(model_input)
    cancellation = cancellation or ClientCancellation()
    executor = LocalToolExecutor(registry, faults=faults)
    seen = {call["call_id"] for message in prefix["messages"] for call in message["tool_calls"]}
    started = time.monotonic()
    expires = started + timeout_ms / 1000
    summary = {"schema": "toolalign.client-trajectory.v1",
               "execution_kind": "ORIGINAL_SCRIPTED_CPU" if client.config["model_identity"] == SCRIPTED_IDENTITY else "REMOTE_PINNED_MODEL",
               "service_run_id": client.config["service_run_id"], "model_identity": client.config["model_identity"],
               "registry_hash": registry.registry_hash, "registry_manifest": registry.manifest,
               "status": "unknown", "reason": None, "semantic_outcome": "not_scored",
               "final_action": None, "decisions": [], "tool_steps": [], "process_records": [],
               "budget": {"max_model_decisions": 3, "max_tool_rounds": 2, "timeout_ms": timeout_ms,
                          "model_decisions": 0, "tool_rounds": 0, "input_tokens": 0, "output_tokens": 0},
               "repairs": "DISABLED"}
    remote_cleanup = 0.0

    def interrupted():
        if cancellation.is_cancelled():
            return "cancelled", "local_cancelled"
        if time.monotonic() >= expires:
            return "timed_out", "local_deadline"
        return None

    def stop(status, reason):
        summary.update(status=status, reason=reason)

    try:
        for index in range(3):
            if interruption := interrupted():
                stop(*interruption)
                break
            receipt_name = f"decision-{index:02d}.json"
            summary["budget"]["model_decisions"] += 1
            decision = client.decision(prefix, seed=seed, expires=expires, cancellation=cancellation,
                                       receipt_path=root / receipt_name)
            remote_cleanup += decision["cleanup_seconds"]
            summary["decisions"].append({"receipt": receipt_name, "request_id": decision["request_id"],
                                         "status": decision["status"], "reason": decision["reason"],
                                         "cleanup": decision["cleanup"]})
            state = decision["state"]
            output = None if state is None else state["result"]
            for key in ("input_tokens", "output_tokens"):
                count = None if output is None else output[key]
                if count is None or summary["budget"][key] is None:
                    summary["budget"][key] = None
                else:
                    summary["budget"][key] += count
            if decision["status"] != "completed":
                stop(decision["status"], decision["reason"])
                break
            if interruption := interrupted():
                stop(*interruption)
                break
            # This Action came from local parse/cross-check, never a returned
            # ValidatedCall, backend repair, executable path or module name.
            action = decision["local_action"]
            if action["kind"] != "tool_calls":
                summary["final_action"] = action
                stop("finalized", action["kind"])
                break
            if summary["budget"]["tool_rounds"] >= 2:
                stop("budget_exhausted", "tool_round_limit")
                break
            issued = []
            for call in action["tool_calls"]:
                if call["call_id"] in seen:
                    raise p.ClientError("duplicate_call_id")
                if call["name"] not in {tool["name"] for tool in prefix["tools"]}:
                    raise p.ClientError("unadvertised_tool")
                validated = registry.validate(call)
                if isinstance(validated, Rejection):
                    raise p.ClientError(validated.code)
                issued.append(validated)
            seen.update(call["call_id"] for call in action["tool_calls"])
            summary["budget"]["tool_rounds"] += 1
            observations = []
            for validated in issued:
                if interruption := interrupted():
                    stop(*interruption)
                    break
                remaining = max(0, expires - time.monotonic())
                context = SandboxContext(root, "mac-client",
                    (datetime.now(timezone.utc) + timedelta(seconds=remaining)).isoformat(), cancellation)
                tool_started = time.monotonic()
                result = executor.execute(validated, context)
                summary["tool_steps"].append({"call": validated.call, "result": asdict(result),
                                               "call_seconds_including_cleanup": time.monotonic() - tool_started})
                p.require(result.call_id == validated.call["call_id"], "executor_binding_mismatch")
                observations.append({"role": "tool", "content": encode(asdict(result)).decode("utf-8"),
                                     "tool_calls": [], "tool_call_id": result.call_id})
                if result.status != "completed" and not result.retryable:
                    stop(result.status if result.status in ("cancelled", "timed_out") else "rejected",
                         result.error_code or "tool_execution_failed")
                    break
            if summary["status"] != "unknown":
                break
            prefix["messages"].append({"role": "assistant", "content": action["content"],
                                        "tool_calls": action["tool_calls"], "tool_call_id": None})
            prefix["messages"].extend(observations)
            prefix, _ = p.bound_input(prefix)
            encode(prefix, INPUT_BYTES)
        else:
            stop("budget_exhausted", "model_decision_limit")
    except (p.ClientError, ContractError, OSError, ValueError, RuntimeError) as exc:
        stop("rejected", str(exc) if isinstance(exc, p.ClientError) else "client_or_tool_error")
    finally:
        elapsed = time.monotonic() - started
        decision_seconds = min(timeout_ms / 1000, max(0, elapsed - remote_cleanup))
        cancelled_at = getattr(cancellation, "cancelled_at", None)
        if cancelled_at is not None:
            decision_seconds = min(decision_seconds, max(0, cancelled_at - started))
        summary.update(decision_seconds=decision_seconds, cleanup_seconds=elapsed - decision_seconds,
                       remote_cleanup_seconds=remote_cleanup, complete_wall_seconds=elapsed,
                       process_records=clone(executor.process_records),
                       local_children_reaped=all(row["reaped"] and row["directory_cleaned"]
                                                for row in executor.process_records),
                       final_history_hash=canonical_hash(prefix))
        write_record(root / "trajectory.json", summary)
    return summary
