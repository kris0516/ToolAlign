"""CPU L0/L1 harness over frozen interfaces; not a Qwen or BFCL benchmark.

The owned model process receives only ModelInput and GenerationConfig. The oracle
stays in the caller. Limits are the existing protocol.v1 defaults, not new knobs.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from toolalign.contracts import (
    ContractError,
    canonical_hash,
    model_input_from_example,
    validate_record,
)
from toolalign.contracts.interfaces import (
    GenerationConfig,
    ModelOutput,
    Rejection,
    SandboxContext,
    TaskScore,
    ToolResult,
)
from toolalign.evaluation.oracles import SemanticOracle
from toolalign.tools._json import (
    INPUT_BYTES,
    MODEL_BYTES,
    clone,
    encode,
    parse_action,
    validate_part,
)
from toolalign.tools.isolation import (
    OwnedProcess,
    enter_child,
    read_packet,
    utc_remaining,
    write_packet,
)

MAX_DECISIONS = 3
MAX_TOOL_ROUNDS = 2
MAX_NEW_TOKENS = 256
DEADLINE_SECONDS = 30


def _output_packet(output):
    wire = asdict(output)
    try:
        encode(wire, MODEL_BYTES)
        return {"output": wire, "error": None, "usage": None, "diagnostic": None}
    except ContractError:
        usage = {
            key: getattr(output, key)
            if type(getattr(output, key)) is int and getattr(output, key) >= 0
            else None
            for key in ("input_tokens", "output_tokens")
        }
        diagnostic = {
            "raw_text": None,
            "raw_sha256": None,
            "raw_size_bytes": None,
            "raw_truncated": True,
        }
        if type(output.raw_text) is str:
            digest, size = hashlib.sha256(), 0
            try:
                for index in range(0, len(output.raw_text), 4096):
                    chunk = output.raw_text[index : index + 4096].encode("utf-8")
                    digest.update(chunk)
                    size += len(chunk)
                diagnostic.update(raw_sha256=digest.hexdigest(), raw_size_bytes=size)
                if size <= MODEL_BYTES // 2:
                    diagnostic.update(raw_text=output.raw_text, raw_truncated=False)
            except UnicodeError:
                pass
        return {
            "output": None,
            "error": "backend_error_or_output_limit",
            "usage": usage,
            "diagnostic": diagnostic,
        }


def _model_child(directory, backend):
    enter_child(directory)
    directory = Path(directory)
    for index in range(MAX_DECISIONS):
        request_path = directory / f"request-{index}.json"
        while not request_path.exists():
            if (directory / "stop.json").exists():
                return
            time.sleep(0.01)
        try:
            packet = read_packet(request_path)
            write_packet(directory / f"generating-{index}.json", {"started": True})
            output = backend.generate(packet["input"], GenerationConfig(**packet["config"]))
            if type(output) is not ModelOutput:
                raise ValueError("Backend must return ModelOutput")
            # The backend's parsed/repaired view is recorded, never substituted for raw text.
            result = _output_packet(output)
        except Exception:
            result = {
                "output": None,
                "error": "backend_error_or_output_limit",
                "usage": None,
                "diagnostic": None,
            }
        write_packet(directory / f"result-{index}.json", result)


class _RequestCancellation:
    def __init__(self, cancellation, expires):
        self.cancellation = cancellation
        self.expires = expires

    def is_cancelled(self):
        return self.cancellation.is_cancelled() or time.monotonic() >= self.expires


@dataclass(frozen=True)
class HarnessResult:
    trace: list[dict]
    decisions: list[dict]
    final_result: dict | None
    score: TaskScore
    registry_manifest: dict
    process_records: list[dict]
    token_accounting_complete: bool
    provenance: dict

    @property
    def budget(self):
        return clone(self.trace[-1]["budget_consumed"])


class LocalHarness:
    def __init__(self, registry, executor, oracle=None):
        self.registry = registry
        self.executor = executor
        self.oracle = oracle or SemanticOracle()

    def run(self, example, task, backend, sandbox_context, *, model_identity):
        started = time.monotonic()
        model = validate_part(model_identity, "model_identity")
        deadline = datetime.now(timezone.utc) + timedelta(seconds=DEADLINE_SECONDS)
        context_error = False
        try:
            remaining = min(DEADLINE_SECONDS, utc_remaining(sandbox_context.deadline_utc))
            supplied = datetime.fromisoformat(sandbox_context.deadline_utc.replace("Z", "+00:00"))
            deadline = min(deadline, supplied)
            validate_part(
                {"call_id": sandbox_context.request_id, "name": "context", "arguments": {}}, "call"
            )
            request_id = sandbox_context.request_id
        except (ValueError, ContractError):
            remaining, request_id, context_error = 0, "invalid-request", True
        expiry = started + remaining
        deadline_utc = deadline.isoformat().replace("+00:00", "Z")
        cancellation = _RequestCancellation(sandbox_context.cancellation, expiry)
        context = SandboxContext(sandbox_context.root, request_id, deadline_utc, cancellation)
        config = GenerationConfig(0, 0.0, 1.0, MAX_NEW_TOKENS, deadline_utc)
        provenance = {
            "protocol_version": "toolalign.protocol.v1",
            "model_input_hash": None,
            "oracle_payload_hash": None,
            "generation_config": asdict(config),
            "registry_hash": self.registry.registry_hash,
        }
        try:
            provenance["oracle_payload_hash"] = canonical_hash(clone(task.oracle_payload))
        except ContractError:
            pass
        budget = {"model_decisions": 0, "tool_rounds": 0, "input_tokens": 0, "output_tokens": 0}
        trace, decisions, processes = [], [], []
        trace_id = uuid.uuid4().hex
        final = None
        session = None
        session_cleanup_attempted = False
        cleanup_errors = []
        accounting_complete = True
        tool_process_start = len(self.executor.process_records)

        def emit(
            event,
            *,
            call=None,
            result=None,
            parse_failure=None,
            validation_failure=None,
            outcome=None,
        ):
            value = {
                "schema_version": "toolalign.trace.v1",
                "trace_id": trace_id,
                "request_id": request_id,
                "event_index": len(trace),
                "event": event,
                "model": model,
                "tool_call": call,
                "tool_result": result,
                "parse_failure": parse_failure,
                "validation_failure": validation_failure,
                "budget_consumed": budget,
                "deadline_utc": deadline_utc,
                "latency_ms": max(0, (time.monotonic() - started) * 1000),
                "task_outcome": asdict(outcome) if outcome else None,
            }
            trace.append(validate_record(value, "trace"))

        def interrupted():
            if sandbox_context.cancellation.is_cancelled():
                return "cancelled"
            if time.monotonic() >= expiry:
                return "timed_out"
            return None

        def finish(event, reason, *, parse_failure=None):
            nonlocal session_cleanup_attempted
            if session is not None and not session_cleanup_attempted:
                # A failed signal must neither bypass close nor re-enter shutdown.
                # Attempted cleanup is separate from the child's actual reaped record.
                session_cleanup_attempted = True
                try:
                    session.record["operation_started"] = (
                        session.directory / "generating-0.json"
                    ).exists()
                    write_packet(session.directory / "stop.json", {})
                except OSError:
                    cleanup_errors.append("stop_signal_write_failed")
                finally:
                    try:
                        session.close()
                    except (OSError, RuntimeError, ValueError):
                        cleanup_errors.append("owned_process_close_failed")
                    if cleanup_errors:
                        session.record["cleanup_errors"] = list(cleanup_errors)
            if event == "finalized" and (interruption := interrupted()):
                event, reason = interruption, interruption
            failure = None if event == "finalized" else reason
            if cleanup_errors:
                failure = "harness_cleanup_error"
                if event == "finalized":
                    event, reason = "rejected", failure
                else:
                    reason = f"{reason}; {failure}"
            if event == "finalized":
                score = self.oracle.score(task, trace, final)
            else:
                score = TaskScore("failure", reason, getattr(self.oracle, "version", "external"))
            emit(
                event,
                parse_failure=parse_failure,
                validation_failure=failure,
                outcome=score,
            )
            records = processes + self.executor.process_records[tool_process_start:]
            return HarnessResult(
                trace,
                decisions,
                final,
                score,
                self.registry.manifest,
                clone(records),
                accounting_complete,
                clone(provenance),
            )

        emit("received")
        if context_error:
            return finish("rejected", "invalid_context")
        try:
            prefix = model_input_from_example(example)
            encode(prefix, INPUT_BYTES)
            provenance["model_input_hash"] = canonical_hash(prefix)
            if (
                example["example_id"] != task.task_id
                or example["group_id"] != task.group_id
                or example["split"] != task.split
            ):
                raise ContractError("Task identity mismatch")
            registered = {tool["name"]: tool for tool in self.registry.tools}
            for tool in prefix["tools"]:
                if tool["name"] in registered and tool != registered[tool["name"]]:
                    raise ContractError("Input changed a bound tool schema")
        except (ContractError, KeyError, TypeError):
            return finish("rejected", "invalid_model_input")
        allowed_names = {tool["name"] for tool in prefix["tools"]}
        seen_calls = {call["call_id"] for msg in prefix["messages"] for call in msg["tool_calls"]}
        emit("validated")
        try:
            while budget["model_decisions"] < MAX_DECISIONS:
                if reason := interrupted():
                    return finish(reason, reason)
                emit("generating")
                budget["model_decisions"] += 1
                if session is None:
                    session = OwnedProcess(context.root, _model_child, (backend,), "model")
                    processes.append(session.record)
                index = budget["model_decisions"] - 1
                input_hash = canonical_hash(prefix)
                write_packet(
                    session.directory / f"request-{index}.json",
                    {"input": prefix, "config": asdict(config)},
                )
                status, packet = session.wait(f"result-{index}.json", expiry, cancellation)
                if status != "completed":
                    accounting_complete = False
                    reason = interrupted() or "backend_error"
                    return finish(
                        reason if reason in ("cancelled", "timed_out") else "rejected", reason
                    )
                if packet["error"] is not None:
                    usage = packet["usage"] or {}
                    accounting_complete = all(
                        usage.get(key) is not None for key in ("input_tokens", "output_tokens")
                    )
                    for key in ("input_tokens", "output_tokens"):
                        if usage.get(key) is not None:
                            budget[key] += usage[key]
                    if packet["diagnostic"] is not None:
                        decisions.append(
                            {
                                **packet["diagnostic"],
                                "model_input_hash": input_hash,
                                "raw_action": None,
                                "raw_parse_failure": "payload_limit",
                                "repaired_output": None,
                                "backend_parsed_action": None,
                                "backend_parse_failure": "payload_limit",
                                "input_tokens": usage.get("input_tokens"),
                                "output_tokens": usage.get("output_tokens"),
                                "finish_reason": "error",
                            }
                        )
                    return finish("rejected", "backend_error_or_output_limit")
                output = packet["output"]
                for key in ("input_tokens", "output_tokens"):
                    if type(output[key]) is not int or output[key] < 0:
                        accounting_complete = False
                        return finish("rejected", "invalid_token_accounting")
                    budget[key] += output[key]
                decision = {
                    "model_input_hash": input_hash,
                    "raw_text": output["raw_text"],
                    "raw_action": None,
                    "raw_parse_failure": None,
                    "repaired_output": None,
                    "backend_parsed_action": output["parsed_action"],
                    "backend_parse_failure": output["parse_failure"],
                    "input_tokens": output["input_tokens"],
                    "output_tokens": output["output_tokens"],
                    "finish_reason": output["finish_reason"],
                }
                decisions.append(decision)
                emit("parsing")
                if canonical_hash(output["model_identity"]) != canonical_hash(model):
                    return finish("rejected", "model_identity_mismatch")
                if output["output_tokens"] > MAX_NEW_TOKENS or output["finish_reason"] == "length":
                    return finish("budget_exhausted", "response_token_limit")
                if output["finish_reason"] in ("timed_out", "cancelled"):
                    return finish(output["finish_reason"], output["finish_reason"])
                if output["finish_reason"] != "stop":
                    return finish("rejected", "backend_error")
                try:
                    action = parse_action(output["raw_text"])
                    decision["raw_action"] = clone(action)
                except ContractError:
                    decision["raw_parse_failure"] = "invalid_raw_action"
                    return finish("rejected", "parse_failure", parse_failure="invalid_raw_action")
                if reason := interrupted():
                    return finish(reason, reason)
                if action["kind"] != "tool_calls":
                    final = action
                    return finish("finalized", "finalized")
                if budget["tool_rounds"] >= MAX_TOOL_ROUNDS:
                    return finish("budget_exhausted", "tool_round_limit")
                budget["tool_rounds"] += 1
                observations = []
                for call in action["tool_calls"]:
                    if reason := interrupted():
                        return finish(reason, reason)
                    emit("tool_execution", call=call)
                    if call["call_id"] in seen_calls:
                        return finish("rejected", "duplicate_call_id")
                    seen_calls.add(call["call_id"])
                    if call["name"] not in allowed_names:
                        return finish("rejected", "unadvertised_tool")
                    validated = self.registry.validate(call)
                    if isinstance(validated, Rejection):
                        return finish("rejected", validated.code)
                    result = self.executor.execute(validated, context)
                    if result.call_id != call["call_id"]:
                        result = ToolResult(
                            call["call_id"], "rejected", None, "executor_binding_failure", False
                        )
                    emit("observing", call=call, result=asdict(result))
                    observations.append(
                        {
                            "role": "tool",
                            "content": encode(asdict(result)).decode(),
                            "tool_calls": [],
                            "tool_call_id": call["call_id"],
                        }
                    )
                    if reason := interrupted():
                        return finish(reason, reason)
                    if result.status != "completed" and not result.retryable:
                        event = (
                            result.status
                            if result.status in ("cancelled", "timed_out")
                            else "rejected"
                        )
                        return finish(event, result.error_code or "execution_error")
                prefix["messages"].append(
                    {
                        "role": "assistant",
                        "content": action["content"],
                        "tool_calls": action["tool_calls"],
                        "tool_call_id": None,
                    }
                )
                prefix["messages"].extend(observations)
                encode(prefix, INPUT_BYTES)
            return finish("budget_exhausted", "model_decision_limit")
        except (OSError, ValueError, ContractError, KeyError, TypeError):
            return finish("rejected", "harness_input_or_backend_error")
        finally:
            if session is not None and not session_cleanup_attempted:
                session.close()


def summarize(results):
    """Every supplied task remains in the denominator, including unknown truth."""
    results = list(results)
    counts = {
        key: sum(result.score.outcome == key for result in results)
        for key in ("success", "failure", "unknown", "not_scored")
    }
    return {
        "evaluation_level": "L0_L1_scripted_development",
        "total": len(results),
        **counts,
        "success_rate": counts["success"] / len(results) if results else None,
        "excluded": 0,
        "real_model_benchmark": "NOT_RUN",
    }
