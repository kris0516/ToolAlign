"""Deterministic semantic and strategy matching for versioned local tasks."""

from __future__ import annotations

from decimal import Decimal

from toolalign.contracts import ContractError, validate_record
from toolalign.contracts.interfaces import TaskScore
from toolalign.tools._json import clone, decode, validate_part

ORACLE_VERSION = "toolalign.semantic-local.v1"


def equivalent(actual, expected):
    """Exact structure with mathematical numeric equivalence, never bool-to-number."""
    if type(expected) in (int, float):
        return type(actual) in (int, float) and Decimal(str(actual)) == Decimal(str(expected))
    if type(expected) is dict:
        return (
            type(actual) is dict
            and actual.keys() == expected.keys()
            and all(equivalent(actual[key], value) for key, value in expected.items())
        )
    if type(expected) is list:
        return (
            type(actual) is list
            and len(actual) == len(expected)
            and all(equivalent(a, b) for a, b in zip(actual, expected))
        )
    return type(actual) is type(expected) and actual == expected


class SemanticOracle:
    version = ORACLE_VERSION

    def score(self, task, trace, final_result):
        def score(outcome, reason):
            return TaskScore(outcome, reason, self.version)

        try:
            payload = clone(task.oracle_payload)
            if (
                set(payload) != {"version", "answers", "strategies"}
                or payload["version"] != self.version
                or not payload["answers"]
                or not payload["strategies"]
            ):
                return score("unknown", "Unsupported or missing oracle truth")
            # Validate truth as data. An unsupported task must not silently become failure.
            for answer in payload["answers"]:
                if set(answer) != {"kind", "value"} or answer["kind"] not in (
                    "final",
                    "clarify",
                    "refuse",
                ):
                    return score("unknown", "Unsupported answer truth")
            for strategy in payload["strategies"]:
                if type(strategy) is not list:
                    return score("unknown", "Unsupported strategy truth")
                for step in strategy:
                    if set(step) != {
                        "name",
                        "arguments",
                        "status",
                        "output",
                        "error_code",
                        "retryable",
                    }:
                        return score("unknown", "Unsupported step truth")
                    validate_part(
                        {
                            "call_id": "oracle-step",
                            "name": step["name"],
                            "arguments": step["arguments"],
                        },
                        "call",
                    )
                    validate_part(
                        {
                            "call_id": "oracle-step",
                            "status": step["status"],
                            "output": step["output"],
                            "error_code": step["error_code"],
                            "retryable": step["retryable"],
                        },
                        "tool_result",
                    )
            events = [validate_record(event, "trace") for event in trace]
            if any(event["event_index"] != index for index, event in enumerate(events)):
                return score("unknown", "Discontinuous trace")
            if events and any(
                any(
                    event[key] != events[0][key]
                    for key in ("trace_id", "request_id", "deadline_utc", "model")
                )
                for event in events
            ):
                return score("unknown", "Mixed trace identities")
            if any(
                event["event"] in ("rejected", "budget_exhausted", "timed_out", "cancelled")
                for event in events
            ):
                return score("failure", "Execution terminated unsuccessfully")
            attempts = [
                event["tool_call"]
                for event in events
                if event["event"] == "tool_execution" and event["tool_call"]
            ]
            observations = [event for event in events if event["event"] == "observing"]
            if len(attempts) != len(observations):
                return score("failure", "Incomplete tool execution")
            actual = []
            for call, event in zip(attempts, observations):
                result = event["tool_result"]
                if result is None or result["call_id"] != call["call_id"]:
                    return score("failure", "Missing matching observation")
                actual.append(
                    {
                        "name": call["name"],
                        "arguments": call["arguments"],
                        "status": result["status"],
                        "output": result["output"],
                        "error_code": result["error_code"],
                        "retryable": result["retryable"],
                    }
                )
            if not any(equivalent(actual, strategy) for strategy in payload["strategies"]):
                return score("failure", "Object, date, version or permitted strategy mismatch")
            if final_result is None:
                return score("failure", "No final action")
            try:
                final_result = validate_part(final_result, "action")
                value = decode(final_result["content"])
            except ContractError:
                return score("failure", "Final answer is not a structured semantic value")
            if any(
                final_result["kind"] == answer["kind"] and equivalent(value, answer["value"])
                for answer in payload["answers"]
            ):
                return score("success", "Semantic answer and permitted execution agree")
            return score("failure", "Final semantic value mismatch")
        except (ContractError, KeyError, TypeError, ValueError):
            return score("unknown", "Invalid oracle or trace data")
