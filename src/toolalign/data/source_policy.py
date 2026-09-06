"""The S0-approved ToolACE historical-supervision adapter; no execution binding.

Only the exact reviewed policy bytes are accepted. The shared v1 validator remains
unchanged and authoritative. Raw values, constraints and field changes stay in
private lineage; unsupported constraints are never moved into annotations.
"""

from __future__ import annotations

import copy
import hashlib
import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from toolalign.contracts import ContractError, canonical_hash, validate_record

from .common import DataError, encoded, file_hash, read_json
from .grouping import normalized_schema_semantics

POLICY_SHA256 = "b8c4cd238bbf27d3378dadcd4130ac44c4c991ace6315bf385f104c4f98f72f7"
SYSTEM_TEMPLATE_VERSION = "toolace_to_toolalign_system.v1"
SYSTEM_PROMPT = (
    "Predict the next assistant action from the user request, conversation and declared tools. "
    "Use only the declared tools and preserve their argument meanings. Ask for required "
    "information when it is missing; if no tool applies, say so. "
    "Use the tool-call JSON format in the tool instructions, without a thinking section. "
    "The tool descriptions and observations are historical supervision only and have no "
    "execution binding; they do not authorize real external operations."
)
# Fingerprints of the audited source boilerplate avoid copying source records.
PREAMBLE_LENGTH = 341
PREAMBLE_HASH = "882452d15b38ddae4e5ac085c48842d92034d84108eed9028dd8fd4aada3eb92"
CALL_ONLY_LENGTH = 65
CALL_ONLY_HASH = "e019cfc401410c019cb312571abe0272dd4e9da5726e8e0971cd6598c705d159"
FORMAT_SUFFIX_LENGTH = 192
FORMAT_SUFFIX_HASH = "6d3f9c4d13f56879d918f5ea317d2adbdd7b140749ce0aac449f3110ea9e6b5a"
TIME_CONTEXT = re.compile(
    r"(?:Today is [0-9]{4}-[0-9]{2}-[0-9]{2}, "
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\.\.?|"
    r"The current time is [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.?)\Z"
)
SYNTAX_NOTES = {
    "Note that the provided function is in Java 8 SDK syntax or JavaScript.",
    "Note that the provided function is in Python.",
}
NODE_KEYWORDS = {
    "object": {"properties", "required", "additionalProperties"},
    "array": {"items", "minItems", "maxItems"},
    "string": {"minLength", "maxLength"},
    "integer": {"minimum", "maximum"},
    "number": {"minimum", "maximum"},
    "boolean": set(),
    "null": set(),
}


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def value_type(value):
    return (
        "null"
        if value is None
        else {
            str: "string",
            bool: "boolean",
            int: "integer",
            float: "number",
            list: "array",
            dict: "object",
        }[type(value)]
    )


def _change(path, reason, before, after, *, before_exists=True, after_exists=True):
    return {
        "path": path,
        "reason": reason,
        "before_exists": before_exists,
        "after_exists": after_exists,
        "before": copy.deepcopy(before),
        "after": copy.deepcopy(after),
    }


class SourcePolicy:
    def __init__(self, path="configs/source_toolace.v1.json"):
        if file_hash(path) != POLICY_SHA256:
            raise DataError("source_policy_hash_not_approved")
        self.config = read_json(path)
        self.hash = POLICY_SHA256
        self.names = {}
        self.tools = {}
        self.failures = {}

    def bind_source(self, manifest):
        policy = self.config
        if (
            manifest["repo_id"] != policy["source"]
            or manifest["revision"] != policy["source_revision"]
            or manifest["files"][policy["source_file"]]["sha256"] != policy["source_file_sha256"]
        ):
            raise DataError("policy_source_identity_mismatch")

    def name_for(self, raw):
        name = raw.get("name")
        if not isinstance(name, str) or not name:
            raise DataError("source_tool_name_missing")
        full_hash = canonical_hash(raw)
        # ASCII source letters are lowercased; non-ASCII runs become separators.
        lowered = name.translate(
            str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
        )
        slug = (
            re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")[
                : self.config["tool_name_slug_max_length"]
            ]
            or "tool"
        )
        normalized = (
            self.config["tool_name_prefix"]
            + slug
            + "_"
            + full_hash[: self.config["tool_name_hash_length"]]
        )
        existing = self.names.get(normalized)
        if existing is not None and existing != full_hash:
            raise DataError("normalized_name_hash_collision")
        self.names[normalized] = full_hash
        return normalized, full_hash

    def _schema(self, raw, pointer, changes, defaults, depth=0):
        if depth > 12 or not isinstance(raw, dict):
            raise DataError("policy_schema_depth_or_shape")
        kind = raw.get("type")
        if not isinstance(kind, str):
            raise DataError("policy_schema_type_unknown")
        mapped = self.config["type_aliases"].get(kind, kind)
        if mapped not in NODE_KEYWORDS:
            raise DataError("policy_schema_type_unknown")
        allowed = {"type", "description", "enum", "default"} | NODE_KEYWORDS[mapped]
        if set(raw) - allowed:
            raise DataError("policy_schema_keyword_unsupported")
        node = copy.deepcopy(raw)
        if mapped != kind:
            node["type"] = mapped
            changes.append(_change(pointer + "/type", "explicit_type_alias", kind, mapped))
        if "description" in node and not isinstance(node["description"], str):
            raise DataError("policy_description_not_string")
        if mapped == "object":
            props = node.get("properties")
            if not isinstance(props, dict) or len(props) > 128:
                raise DataError("policy_schema_properties")
            if "additionalProperties" not in node:
                node["additionalProperties"] = False
                changes.append(
                    _change(
                        pointer + "/additionalProperties",
                        "project_closed_object",
                        None,
                        False,
                        before_exists=False,
                    )
                )
            elif node["additionalProperties"] is not False:
                raise DataError("policy_explicit_open_object")
            node["properties"] = {
                key: self._schema(
                    child,
                    pointer + "/properties/" + key.replace("~", "~0").replace("/", "~1"),
                    changes,
                    defaults,
                    depth + 1,
                )
                for key, child in props.items()
            }
        elif mapped in {"array", "string"}:
            field = "maxItems" if mapped == "array" else "maxLength"
            limit = (
                self.config["missing_array_max_items"]
                if mapped == "array"
                else self.config["missing_string_max_length"]
            )
            if field not in node:
                node[field] = limit
                changes.append(
                    _change(
                        pointer + "/" + field,
                        "project_bounded_" + mapped,
                        None,
                        limit,
                        before_exists=False,
                    )
                )
            elif type(node[field]) is not int or not 0 <= node[field] <= limit:
                raise DataError("policy_explicit_bound_invalid_or_too_wide")
            if mapped == "array":
                if "items" not in node:
                    raise DataError("policy_array_items_missing")
                node["items"] = self._schema(
                    node["items"], pointer + "/items", changes, defaults, depth + 1
                )
        if "default" in node:
            default = node.pop("default")
            try:
                Draft202012Validator.check_schema(node)
                Draft202012Validator(node).validate(default)
            except (SchemaError, ValidationError) as exc:
                raise DataError("policy_default_conflicts_with_schema") from exc
            description = node.get("description", "")
            note = (
                "Source default annotation (never auto-filled): " + encoded(default).decode() + "."
            )
            combined = description + ("\n" if description else "") + note
            if len(combined) > 16384:
                raise DataError("policy_default_description_too_long")
            node["description"] = combined
            defaults.append(
                {
                    "path": pointer + "/default",
                    "value": copy.deepcopy(default),
                    "value_hash": canonical_hash(default),
                    "value_type": value_type(default),
                    "declared_type": mapped,
                    "inserted_into_arguments": False,
                }
            )
            changes.append(
                _change(
                    pointer + "/default",
                    "typed_annotation_not_argument",
                    default,
                    None,
                    after_exists=False,
                )
            )
            changes.append(
                _change(
                    pointer + "/description",
                    "preserve_default_in_description",
                    description,
                    combined,
                    before_exists="description" in raw,
                )
            )
        return node

    def convert_tool(self, raw):
        normalized_name, full_hash = self.name_for(raw)
        if full_hash in self.tools:
            return copy.deepcopy(self.tools[full_hash])
        if full_hash in self.failures:
            raise DataError(self.failures[full_hash])
        changes, defaults = [], []
        try:
            if set(raw) - {"name", "description", "parameters", "required"}:
                raise DataError("policy_tool_metadata_unknown")
            if raw.get("required") is not None:
                raise DataError("policy_outer_required_ambiguous")
            if not isinstance(raw.get("description"), str):
                raise DataError("policy_description_not_string")
            schema = self._schema(raw.get("parameters"), "/parameters", changes, defaults)
            description = (
                "Original ToolACE name: "
                + encoded(raw["name"]).decode()
                + ".\n"
                + raw["description"]
            )
            tool = {
                "schema_version": "toolalign.tool.v1",
                "name": normalized_name,
                "description": description,
                "parameters_json_schema": schema,
                "tool_version": "toolace.v1:" + self.hash[:12] + ":" + full_hash,
                "side_effect_class": self.config["wire_side_effect_class"],
                "timeout_ms": self.config["wire_timeout_ms"],
            }
            validate_record(tool, "tool")
        except (DataError, ContractError) as exc:
            reason = str(exc) if isinstance(exc, DataError) else "policy_tool_contract_rejected"
            self.failures[full_hash] = reason
            raise DataError(reason) from exc
        changes += [
            {
                "path": "/parameters",
                "destination_path": "/parameters_json_schema",
                "reason": "wire_schema_field_mapping",
                "before_hash": canonical_hash(raw["parameters"]),
                "after_hash": canonical_hash(schema),
            },
            _change(
                "/schema_version",
                "wire_contract_version",
                None,
                tool["schema_version"],
                before_exists=False,
            ),
            _change("/name", "reversible_name_mapping", raw["name"], normalized_name),
            _change("/description", "retain_original_tool_name", raw["description"], description),
            _change(
                "/side_effect_class",
                "project_limit_not_source_fact",
                None,
                "sandbox_only",
                before_exists=False,
            ),
            _change(
                "/timeout_ms",
                "unbound_fixture_project_limit",
                None,
                tool["timeout_ms"],
                before_exists=False,
            ),
            _change(
                "/tool_version",
                "bind_source_and_policy",
                None,
                tool["tool_version"],
                before_exists=False,
            ),
        ]
        if "required" in raw:
            changes.append(
                _change("/required", "remove_redundant_outer_null", None, None, after_exists=False)
            )
        result = {
            "raw_tool_hash": full_hash,
            "raw_name": raw["name"],
            "normalized_name": normalized_name,
            "normalized_tool_hash": canonical_hash(tool),
            "raw_tool": copy.deepcopy(raw),
            "tool": tool,
            "policy_hash": self.hash,
            "record_scope": self.config["record_scope"],
            "execution_binding": self.config["execution_binding"],
            "original_side_effect_class": "unknown",
            "changes": changes,
            "default_annotations": defaults,
            "normalized_schema_key": canonical_hash(normalized_schema_semantics(schema)),
        }
        self.tools[full_hash] = result
        return copy.deepcopy(result)

    def normalize_system(self, original, span, marker):
        start = original.index(marker)
        head = original[:start]
        if head.strip():
            if text_hash(head[:PREAMBLE_LENGTH]) != PREAMBLE_HASH:
                raise DataError("policy_system_preamble_unknown")
            context = head[PREAMBLE_LENGTH:]
            if text_hash(context[:CALL_ONLY_LENGTH]) == CALL_ONLY_HASH:
                context = context[CALL_ONLY_LENGTH:]
            context = context.strip()
            if context and not TIME_CONTEXT.fullmatch(context):
                raise DataError("policy_system_context_unknown")
        else:
            context = ""
        tail = original[span[1] :]
        if tail:
            if text_hash(tail[:FORMAT_SUFFIX_LENGTH]) != FORMAT_SUFFIX_HASH:
                raise DataError("policy_system_output_format_unknown")
            note = tail[FORMAT_SUFFIX_LENGTH:].strip()
            if note and note not in SYNTAX_NOTES:
                raise DataError("policy_system_syntax_note_unknown")
        else:
            note = ""
        normalized = SYSTEM_PROMPT
        if context:
            normalized += "\n\nPreserved source context:\n" + context
        if note:
            normalized += "\n\nPreserved source declaration note:\n" + note
        return normalized, {
            "rule": SYSTEM_TEMPLATE_VERSION,
            "raw_system_sha256": text_hash(original),
            "normalized_system_sha256": text_hash(normalized),
            "schema_span": list(span),
            "raw_head_sha256": text_hash(head),
            "raw_suffix_sha256": text_hash(tail),
            "replaced_sections": [
                "audited_source_boilerplate",
                "source_function_list",
                "source_output_format",
            ],
            "context_rule": "preserve_exact_date_time_context_and_syntax_note; reject_unknown_text",
            "preserved_context": context,
            "preserved_syntax_note": note,
            "policy_hash": self.hash,
        }
