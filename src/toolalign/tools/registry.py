"""Fixed registry, exact source/schema identities, and one-use validated calls."""

from __future__ import annotations

import hashlib
import threading
from importlib.resources import files

from toolalign.contracts import (
    ContractError,
    canonical_hash,
    validate_record,
    validate_tool_arguments,
)
from toolalign.contracts.interfaces import Rejection, ValidatedCall
from toolalign.tools import catalog
from toolalign.tools._json import CALL_BYTES, clone, validate_part

REGISTRY_VERSION = "toolalign.local-registry.v1"


class LocalToolRegistry:
    def __init__(self, names=None):
        definitions = [validate_record(spec, "tool") for spec in catalog.specs()]
        definition_names = [spec["name"] for spec in definitions]
        if len(definition_names) != len(set(definition_names)):
            raise ValueError("Duplicate or conflicting catalog definition")
        if set(definition_names) != set(catalog.IMPLEMENTATIONS):
            raise ValueError("Every catalog tool must have exactly one implementation")
        available = {spec["name"]: spec for spec in definitions}
        selected = list(available) if names is None else list(names)
        if any(type(name) is not str or name not in available for name in selected):
            raise ValueError("Only source-bound local tool names may be selected")
        if len(selected) != len(set(selected)):
            raise ValueError("Duplicate or conflicting tool name")
        self._specs = {name: available[name] for name in sorted(selected)}
        source_hash = hashlib.sha256(
            files("toolalign.tools").joinpath("catalog.py").read_bytes()
        ).hexdigest()
        self._manifest = {
            "registry_version": REGISTRY_VERSION,
            "tools": [
                {
                    "spec": spec,
                    "schema_hash": canonical_hash(spec["parameters_json_schema"]),
                    "implementation": "toolalign.tools.catalog:" + name,
                    "source_hash": source_hash,
                }
                for name, spec in self._specs.items()
            ],
        }
        self._hash = canonical_hash(self._manifest)
        self._issued = {}
        self._lock = threading.Lock()

    @property
    def registry_hash(self):
        return self._hash

    @property
    def manifest(self):
        return clone(self._manifest)

    @property
    def tools(self):
        return clone(list(self._specs.values()))

    def spec(self, name):
        return clone(self._specs[name])

    def validate(self, call):
        call_id = "invalid-call"
        try:
            call = validate_part(call, "call", CALL_BYTES)
            call_id = call["call_id"]
            spec = self._specs.get(call["name"])
            if spec is None:
                return Rejection(call_id, "unknown_tool", "No source-bound implementation")
            validate_tool_arguments(spec, call["arguments"])
            if spec["side_effect_class"] != "read_only":
                return Rejection(call_id, "policy_denied", "Local read-only policy required")
        except (ContractError, RuntimeError):
            return Rejection(call_id, "invalid_arguments", "Call or arguments failed validation")
        value = ValidatedCall(call, spec["tool_version"], self.registry_hash)
        with self._lock:
            if len(self._issued) >= 256:
                return Rejection(call_id, "validation_capacity", "Pending call limit")
            self._issued[id(value)] = (value, canonical_hash(call))
        return value

    def authorize(self, value):
        """Consume the original object and recheck a fresh snapshot before any spawn."""
        if type(value) is not ValidatedCall:
            return Rejection("invalid-call", "unissued_call", "Expected issued call")
        with self._lock:
            issued = self._issued.pop(id(value), None)
        if issued is None or issued[0] is not value:
            return Rejection("invalid-call", "unissued_call", "Call was not issued or was consumed")
        try:
            call = validate_part(value.call, "call", CALL_BYTES)
            spec = self._specs.get(call["name"])
            if (
                spec is None
                or canonical_hash(call) != issued[1]
                or value.registry_hash != self.registry_hash
                or value.tool_version != spec["tool_version"]
                or canonical_hash(self._manifest) != self.registry_hash
                or spec["side_effect_class"] != "read_only"
            ):
                raise ContractError("Stale or modified call")
            validate_tool_arguments(spec, call["arguments"])
            return ValidatedCall(call, spec["tool_version"], self.registry_hash)
        except (ContractError, RuntimeError):
            return Rejection("invalid-call", "stale_or_modified_call", "Binding check failed")
