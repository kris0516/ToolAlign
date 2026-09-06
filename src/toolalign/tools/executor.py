"""Source-bound local tools executed in individually owned CPU processes."""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path

from toolalign.contracts import ContractError
from toolalign.contracts.interfaces import Rejection, ToolResult
from toolalign.tools import catalog
from toolalign.tools._json import RESULT_BYTES, clone, encode, validate_part
from toolalign.tools.isolation import OwnedProcess, enter_child, utc_remaining, write_packet
from toolalign.tools.registry import LocalToolRegistry


def _tool_child(directory, names, registry_hash, call, fault):
    enter_child(directory)
    result = ToolResult(call["call_id"], "error", None, "execution_error", False)
    try:
        registry = LocalToolRegistry(names)
        validated = registry.validate(call)
        if isinstance(validated, Rejection) or registry.registry_hash != registry_hash:
            result = ToolResult(call["call_id"], "rejected", None, "child_binding_mismatch", False)
        else:
            write_packet(Path(directory) / "executing.json", {"started": True})
            if fault == "block":
                while True:
                    time.sleep(60)
            if fault == "transient":
                raise catalog.ToolFault("injected_transient", retryable=True)
            if fault == "error":
                raise catalog.ToolFault("injected_permanent")
            output = catalog.IMPLEMENTATIONS[call["name"]](validated.call["arguments"])
            if fault == "oversize":
                output = "x" * (RESULT_BYTES + 1)
            output = clone(output, RESULT_BYTES)
            result = ToolResult(call["call_id"], "completed", output, None, False)
    except catalog.ToolFault as exc:
        result = ToolResult(call["call_id"], "error", None, exc.code, exc.retryable)
    except ContractError:
        result = ToolResult(call["call_id"], "error", None, "output_limit", False)
    except Exception:
        pass
    write_packet(Path(directory) / "result.json", result.__dict__)


class LocalToolExecutor:
    def __init__(self, registry, *, faults=None, timeout_cap_ms=None):
        self.registry = registry
        self.process_records = []
        self._faults = {}
        for name, sequence in (faults or {}).items():
            if name not in {tool["name"] for tool in registry.tools}:
                raise ValueError("Fault target is not registered")
            sequence = list(sequence)
            if len(sequence) > 32 or any(
                x not in (None, "block", "transient", "error", "oversize") for x in sequence
            ):
                raise ValueError("Unsupported host-only fault schedule")
            self._faults[name] = deque(sequence)
        if timeout_cap_ms is not None and (
            type(timeout_cap_ms) is not int or not 1 <= timeout_cap_ms <= 1000
        ):
            raise ValueError("Timeout cap may only tighten the tool limit")
        self.timeout_cap_ms = timeout_cap_ms

    def execute(self, validated_call, sandbox_context):
        started = time.monotonic()
        accepted = self.registry.authorize(validated_call)
        if isinstance(accepted, Rejection):
            return ToolResult(accepted.call_id, "rejected", None, accepted.code, False)
        call = accepted.call
        call_id = call["call_id"]
        if sandbox_context.cancellation.is_cancelled():
            return ToolResult(call_id, "cancelled", None, "cancelled", False)
        try:
            remaining = utc_remaining(sandbox_context.deadline_utc)
        except ValueError:
            return ToolResult(call_id, "rejected", None, "invalid_deadline", False)
        if remaining <= 0:
            return ToolResult(call_id, "timed_out", None, "request_deadline", False)
        spec = self.registry.spec(call["name"])
        timeout = min(spec["timeout_ms"], self.timeout_cap_ms or spec["timeout_ms"]) / 1000
        expires = started + min(remaining, timeout)
        schedule = self._faults.get(call["name"])
        fault = schedule.popleft() if schedule else None
        owned = None
        try:
            owned = OwnedProcess(
                sandbox_context.root,
                _tool_child,
                (
                    [tool["name"] for tool in self.registry.tools],
                    self.registry.registry_hash,
                    call,
                    fault,
                ),
                "tool",
            )
            self.process_records.append(owned.record)
            status, packet = owned.wait("result.json", expires, sandbox_context.cancellation)
            if status == "completed":
                packet = validate_part(packet, "tool_result")
                encode(packet["output"], RESULT_BYTES)
                if packet["call_id"] != call_id:
                    raise ContractError("Mismatched result")
                return ToolResult(**packet)
            if status == "timed_out":
                retryable = remaining > timeout
                code = "tool_timeout" if retryable else "request_deadline"
                return ToolResult(call_id, status, None, code, retryable)
            return ToolResult(call_id, status, None, status, False)
        except (ContractError, OSError, ValueError):
            return ToolResult(call_id, "error", None, "isolation_error", False)
        finally:
            if owned is not None:
                owned.record["operation_started"] = (owned.directory / "executing.json").exists()
                owned.close()
