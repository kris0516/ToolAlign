"""Client checks of the frozen HTTP v1 fields, independent of the service code."""

from __future__ import annotations

import math
from datetime import datetime

from toolalign.contracts import ContractError, canonical_hash
from toolalign.model_io.format import validate_model_input
from toolalign.tools import LocalToolRegistry
from toolalign.tools._json import (
    INPUT_BYTES,
    MODEL_BYTES,
    clone,
    encode,
    parse_action,
    validate_part,
)

SCHEMA = "toolalign.service-http.v1"
CATALOG = "local-devops.v1"
TERMINAL = {"completed", "parse_failure", "budget_exhausted", "cancelled", "timed_out", "infrastructure_error"}
STATUSES = TERMINAL | {"queued", "running", "stopping"}
SAMPLING = {"temperature": 0.7, "top_p": 0.9, "top_k": 0, "max_new_tokens": 256,
            "enable_thinking": False, "seed_policy": "per_request"}
LIMITS = {"context_tokens": 2048, "max_request_ms": 30000, "max_pending": 2,
          "max_records": 64, "max_body_bytes": INPUT_BYTES, "max_service_seconds": 900}
TIMES = "queue_seconds child_generation_seconds ttft_seconds prefill_seconds decode_seconds cleanup_seconds complete_wall_seconds"
STATE_FIELDS = "schema service_run_id request_id input_hash payload_hash status reason accepted_at_utc deadline_utc started_at_utc finished_at_utc worker_epoch worker_cleanup result timing"


class ClientError(ValueError):
    """Stable local code; never expose transport exception text or credentials."""


def require(condition, code):
    if not condition:
        raise ClientError(code)


def fields(value, names, code):
    require(type(value) is dict and set(value) == set(names.split()), code)


def integer(value, minimum=0, maximum=None):
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def text(value):
    return type(value) is str and bool(value)


def utc(value):
    if not text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0
    except ValueError:
        return False


def bound_input(value):
    """Advertise only unmodified specs from the fixed local read-only catalog."""
    value = validate_model_input(value)
    encode(value, INPUT_BYTES)
    registry = LocalToolRegistry([tool["name"] for tool in value["tools"]], catalog_id=CATALOG)
    expected = {tool["name"]: tool for tool in registry.tools}
    require(canonical_hash({tool["name"]: tool for tool in value["tools"]}) == canonical_hash(expected),
            "unbound_tool_schema")
    return value, registry


def model_info(value, run_id, identity):
    fields(value, "schema service_run_id source_commit model_identity checkpoint_sha256 dependency_lock_sha256 catalog_id registry_hash sampling limits cache", "model_info_fields")
    require(value["schema"] == SCHEMA and value["service_run_id"] == run_id, "service_run_mismatch")
    validate_part(value["model_identity"], "model_identity")
    require(canonical_hash(value["model_identity"]) == canonical_hash(identity), "model_identity_mismatch")
    require(value["catalog_id"] == CATALOG
            and value["registry_hash"] == LocalToolRegistry().registry_hash, "registry_identity_mismatch")
    require(canonical_hash(value["sampling"]) == canonical_hash(SAMPLING)
            and canonical_hash(value["limits"]) == canonical_hash(LIMITS), "service_limits_or_sampling_mismatch")
    fields(value["cache"], "enabled max_entries scope", "cache_fields")
    require(type(value["cache"]["enabled"]) is bool and type(value["cache"]["max_entries"]) is int
            and value["cache"]["max_entries"] == 1 and value["cache"]["scope"] == "principal", "cache_contract")
    for key, length in (("source_commit", 40), ("checkpoint_sha256", 64), ("dependency_lock_sha256", 64)):
        require(type(value[key]) is str and len(value[key]) == length
                and all(c in "0123456789abcdef" for c in value[key]), "model_info_identity_fields")
    return value


def readiness(value, run_id, http_status):
    fields(value, "schema service_run_id ready accepting worker_epoch reason", "readiness_fields")
    require(value["schema"] == SCHEMA and value["service_run_id"] == run_id, "service_run_mismatch")
    require(type(value["ready"]) is bool and type(value["accepting"]) is bool
            and (value["worker_epoch"] is None or integer(value["worker_epoch"], 1))
            and (value["reason"] is None or text(value["reason"])), "readiness_values")
    require(http_status == (200 if value["ready"] else 503), "readiness_http_status")
    require(not value["accepting"] or value["ready"], "accepting_without_ready")
    require(not value["ready"] or integer(value["worker_epoch"], 1), "ready_without_worker_epoch")
    return value


def acknowledgement(value, run_id, http_status):
    fields(value, "schema service_run_id request_id status replayed", "acknowledgement_fields")
    require(value["schema"] == SCHEMA and value["service_run_id"] == run_id, "service_run_mismatch")
    require(text(value["request_id"]) and type(value["status"]) is str and value["status"] in STATUSES
            and type(value["replayed"]) is bool, "acknowledgement_values")
    require(http_status == (200 if value["status"] in TERMINAL else 202), "acknowledgement_http_status")
    return value


def result(value, identity):
    fields(value, "raw_text finish_reason raw_action raw_action_valid raw_parse_failure model_identity input_tokens output_tokens token_accounting_complete diagnostic", "result_fields")
    require(value["raw_text"] is None or type(value["raw_text"]) is str, "raw_text_type")
    require(value["finish_reason"] in (None, "stop", "length", "timed_out", "cancelled", "error"), "finish_reason")
    require(type(value["raw_action_valid"]) is bool
            and (value["raw_parse_failure"] is None or text(value["raw_parse_failure"])), "raw_action_fields")
    require(all(value[k] is None or integer(value[k]) for k in ("input_tokens", "output_tokens")), "token_accounting")
    counts_known = all(integer(value[k]) for k in ("input_tokens", "output_tokens"))
    require(type(value["token_accounting_complete"]) is bool
            and value["token_accounting_complete"] == counts_known, "token_accounting")
    if value["model_identity"] is not None:
        validate_part(value["model_identity"], "model_identity")
        require(canonical_hash(value["model_identity"]) == canonical_hash(identity), "model_identity_mismatch")
    diagnostic = value["diagnostic"]
    if diagnostic is not None:
        fields(diagnostic, "raw_sha256 raw_size_bytes raw_truncated", "diagnostic_fields")
        require(type(diagnostic["raw_truncated"]) is bool
                and (diagnostic["raw_size_bytes"] is None or integer(diagnostic["raw_size_bytes"]))
                and (diagnostic["raw_sha256"] is None or (type(diagnostic["raw_sha256"]) is str
                     and len(diagnostic["raw_sha256"]) == 64
                     and all(c in "0123456789abcdef" for c in diagnostic["raw_sha256"]))), "diagnostic_values")
    action = None
    if value["raw_text"] is not None:
        require(len(value["raw_text"].encode("utf-8")) <= MODEL_BYTES, "raw_packet_limit")
        try:
            action = parse_action(value["raw_text"])
        except ContractError:
            pass
    truncated = diagnostic is not None and diagnostic["raw_truncated"]
    if truncated:
        require(not value["raw_action_valid"] and value["raw_action"] is None, "truncated_raw_action")
        action = None
    else:
        require(value["raw_action_valid"] == (action is not None)
                and canonical_hash(value["raw_action"]) == canonical_hash(action), "raw_action_mismatch")
    if action is not None:
        require(value["raw_parse_failure"] is None, "raw_parse_failure_mismatch")
    elif value["raw_text"] is not None and not truncated:
        require(value["raw_parse_failure"] is not None, "raw_parse_failure_mismatch")
    return action


def request_state(value, body, identity, request_id=None):
    fields(value, STATE_FIELDS, "request_state_fields")
    require(value["schema"] == SCHEMA and value["service_run_id"] == body["service_run_id"], "service_run_mismatch")
    require(text(value["request_id"]) and (request_id is None or value["request_id"] == request_id), "request_id_mismatch")
    require(value["input_hash"] == canonical_hash(body["model_input"])
            and value["payload_hash"] == canonical_hash(body), "request_payload_mismatch")
    require(type(value["status"]) is str and value["status"] in STATUSES
            and (value["reason"] is None or text(value["reason"])), "request_status")
    require(all(utc(value[k]) for k in ("accepted_at_utc", "deadline_utc"))
            and all(value[k] is None or utc(value[k]) for k in ("started_at_utc", "finished_at_utc")), "request_timestamps")
    require((value["finished_at_utc"] is not None) == (value["status"] in TERMINAL), "request_finished_time")
    require(value["worker_epoch"] is None or integer(value["worker_epoch"], 1), "worker_epoch")
    require(value["worker_cleanup"] in ("not_started", "live", "reaped", "unconfirmed"), "worker_cleanup")
    if value["status"] in ("cancelled", "timed_out"):
        require(value["worker_cleanup"] in ("not_started", "reaped"), "unconfirmed_terminal_cleanup")
    fields(value["timing"], TIMES + " cache_hit_tokens prefill_tokens", "timing_fields")
    for key in TIMES.split():
        number = value["timing"][key]
        require(number is None or (type(number) in (int, float) and math.isfinite(number) and number >= 0), "timing_values")
    require(all(value["timing"][key] is None or integer(value["timing"][key])
                for key in ("cache_hit_tokens", "prefill_tokens")), "timing_tokens")
    action = None if value["result"] is None else result(value["result"], identity)
    if value["status"] == "completed":
        output = value["result"]
        require(output is not None and action is not None and output["finish_reason"] == "stop"
                and output["token_accounting_complete"] and output["model_identity"] is not None
                and output["output_tokens"] <= 256 and output["input_tokens"] + 256 <= 2048
                and value["worker_cleanup"] in ("live", "reaped")
                and value["started_at_utc"] is not None and integer(value["worker_epoch"], 1), "invalid_completed_state")
    return value, clone(action)
