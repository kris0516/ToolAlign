"""Frozen G6 HTTP fields and bounded, host-only service configuration."""

from __future__ import annotations

import hmac
import re
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash
from toolalign.model_io.cuda_generation import ADAPTER_SHA256, CHECKPOINT_SHA256
from toolalign.model_io.format import validate_model_input
from toolalign.tools import LocalToolRegistry
from toolalign.tools._json import INPUT_BYTES, decode
from toolalign.training.cuda_sft.protocol import CONFIG_SHA256, positive_int, read_bytes, require

HTTP_SCHEMA = "toolalign.service-http.v1"
RUN_SCHEMA = "toolalign.service-run.v1"
STARTUP_SECONDS = 120
CLEANUP_SECONDS = 5
MAX_RECORDS = 64
MAX_PENDING = 2
MAX_GENERATIONS = 12
LIMITS = {"context_tokens": 2048, "max_request_ms": 30000, "max_pending": MAX_PENDING,
          "max_records": MAX_RECORDS, "max_body_bytes": INPUT_BYTES, "max_service_seconds": 900}
SAMPLING = {"temperature": 0.7, "top_p": 0.9, "top_k": 0, "max_new_tokens": 256,
            "enable_thinking": False, "seed_policy": "per_request"}
TERMINAL = frozenset({"completed", "parse_failure", "budget_exhausted", "cancelled",
                      "timed_out", "infrastructure_error"})
TIMINGS = ("queue_seconds", "child_generation_seconds", "ttft_seconds", "prefill_seconds",
           "decode_seconds", "cleanup_seconds", "complete_wall_seconds", "cache_hit_tokens",
           "prefill_tokens")


class APIError(ValueError):
    def __init__(self, status, code):
        super().__init__(code)
        self.status, self.code = status, code


def idempotency_key(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is None:
        raise APIError(400, "invalid_idempotency_key")
    return value


def validate_request(value, run_id, registry):
    if (type(value) is not dict or set(value) != {"schema", "service_run_id", "model_input", "seed", "timeout_ms"}
            or value["schema"] != HTTP_SCHEMA or type(value["service_run_id"]) is not str
            or type(value["seed"]) is not int or not 0 <= value["seed"] < 2**63
            or type(value["timeout_ms"]) is not int or not 1 <= value["timeout_ms"] <= 30000):
        raise APIError(400, "invalid_request")
    if value["service_run_id"] != run_id:
        raise APIError(409, "service_run_mismatch")
    try:
        model_input = validate_model_input(value["model_input"])
    except (ContractError, TypeError, ValueError):
        raise APIError(400, "invalid_model_input") from None
    registered = {tool["name"]: canonical_hash(tool) for tool in registry.tools}
    if any(registered.get(tool["name"]) != canonical_hash(tool) for tool in model_input["tools"]):
        raise APIError(400, "unbound_tool_schema")
    return model_input


def validate_run(request):
    fields = {"schema", "authorized_by", "run_kind", "run_id", "source_commit", "config_sha256",
              "model_root", "checkpoint_dir", "checkpoint_sha256", "adapter_sha256", "dependency_lock",
              "dependency_lock_sha256", "repository", "lock_root", "output_dir", "auth_file",
              "listen_host", "listen_port", "cache_enabled", "max_generations", "max_wall_seconds",
              "max_output_bytes"}
    require(type(request) is dict and set(request) == fields, "service_run_fields")
    require(request["schema"] == RUN_SCHEMA and request["authorized_by"] == "S1"
            and request["run_kind"] == "serving", "separate_S1_service_request_required")
    require(request["config_sha256"] == CONFIG_SHA256 and request["checkpoint_sha256"] == CHECKPOINT_SHA256
            and request["adapter_sha256"] == ADAPTER_SHA256, "service_selected_identity")
    require(type(request["run_id"]) is str
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", request["run_id"]), "service_run_id")
    for key, length in (("source_commit", 40), ("dependency_lock_sha256", 64)):
        require(type(request[key]) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", request[key]), key)
    for key in ("repository", "lock_root", "model_root", "checkpoint_dir", "dependency_lock", "output_dir", "auth_file"):
        require(type(request[key]) is str and Path(request[key]).is_absolute(), "absolute_" + key)
    require(Path(request["repository"]).resolve() == Path(request["lock_root"]).resolve(), "service_shared_lock")
    require(request["listen_host"] == "127.0.0.1" and type(request["listen_port"]) is int
            and 0 <= request["listen_port"] <= 65535, "service_loopback_only")
    require(type(request["cache_enabled"]) is bool, "service_cache_boolean")
    require(positive_int(request["max_generations"], "max_generations") <= MAX_GENERATIONS, "service_generation_ceiling")
    require(CLEANUP_SECONDS < positive_int(request["max_wall_seconds"], "max_wall_seconds") <= 900,
            "service_wall_ceiling")
    require(positive_int(request["max_output_bytes"], "max_output_bytes") <= 256 * 1024**2,
            "service_output_ceiling")
    return request


class TokenAuth:
    """One private startup snapshot. Headers never become request/cache identities."""

    def __init__(self, path):
        path = Path(path)
        require(path.stat().st_mode & 0o077 == 0, "service_auth_file_must_be_private")
        value = decode(read_bytes(path, 8192), 8192)
        require(type(value) is dict and set(value) == {"schema", "tokens"}
                and value["schema"] == "toolalign.service-auth.v1"
                and type(value["tokens"]) is dict and 1 <= len(value["tokens"]) <= 8,
                "service_auth_fields")
        tokens = value["tokens"]
        require(all(type(principal) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", principal)
                    and type(token) is str and re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token)
                    for principal, token in tokens.items()), "service_auth_values")
        require(len(set(tokens.values())) == len(tokens), "service_auth_duplicate_token")
        self._tokens = tokens

    def principal(self, authorization):
        if type(authorization) is not str or not authorization.startswith("Bearer "):
            raise APIError(401, "unauthorized")
        token = authorization[7:]
        if not token.isascii() or not 32 <= len(token) <= 256:
            raise APIError(401, "unauthorized")
        principal = None
        for name, expected in self._tokens.items():
            if hmac.compare_digest(token, expected):
                principal = name
        if principal is None:
            raise APIError(401, "unauthorized")
        return principal


def model_info(request, identity, registry=None):
    registry = registry or LocalToolRegistry(catalog_id="local-devops.v1")
    return {"schema": HTTP_SCHEMA, "service_run_id": request["run_id"],
            "source_commit": request["source_commit"], "model_identity": identity,
            "checkpoint_sha256": request["checkpoint_sha256"],
            "dependency_lock_sha256": request["dependency_lock_sha256"],
            "catalog_id": registry.catalog_id, "registry_hash": registry.registry_hash,
            "sampling": dict(SAMPLING), "limits": dict(LIMITS),
            "cache": {"enabled": request["cache_enabled"], "max_entries": 1, "scope": "principal"}}
