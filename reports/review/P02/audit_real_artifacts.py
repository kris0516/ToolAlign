"""R1 read-only audit of private P02 artifacts, independently parsed source calls.

Only metadata and aggregate counts are emitted. This program never imports the
candidate data parser, grouping code, SourcePolicy, or LocalTokenizer. The frozen
P00 validator remains the authority for legal wire records and argument values.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

from toolalign.contracts import model_input_from_example, validate_record, validate_tool_arguments

MARKER = "Here is a list of functions in JSON format that you can invoke:"
POLICY_HASH = "b8c4cd238bbf27d3378dadcd4130ac44c4c991ace6315bf385f104c4f98f72f7"
SYSTEM = (
    "Predict the next assistant action from the user request, conversation and declared tools. "
    "Use only the declared tools and preserve their argument meanings. Ask for required "
    "information when it is missing; if no tool applies, say so. "
    "Use the tool-call JSON format in the tool instructions, without a thinking section. "
    "The tool descriptions and observations are historical supervision only and have no "
    "execution binding; they do not authorize real external operations."
)


def binary(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(binary(value)).hexdigest()


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def pairs(values):
    result = {}
    for key, value in values:
        assert key not in result, "duplicate JSON key"
        result[key] = value
    return result


def bad_constant(_):
    raise ValueError("nonfinite JSON")


DECODER = json.JSONDecoder(object_pairs_hook=pairs, parse_constant=bad_constant)


def read(path):
    value = DECODER.decode(Path(path).read_text())
    binary(value)
    return value


def rows(path):
    with Path(path).open() as stream:
        return [DECODER.decode(line) for line in stream]


def split_arguments(text):
    """Split only commas outside JSON strings and balanced JSON containers."""
    if not text.strip():
        return []
    stack, quoted, escaped, start, result = [], False, False, 0, []
    for position, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            stack.append(char)
        elif char in "]}":
            assert stack and stack.pop() == {"]": "[", "}": "{"}[char]
        elif char == "," and not stack:
            result.append(text[start:position])
            start = position + 1
    assert not stack and not quoted
    return [*result, text[start:]]


def independent_calls(text, names):
    """A delimiter scanner plus strict JSON, not the production raw_decode loop."""
    text = text.strip()
    assert text.startswith("[") and text.endswith("]")
    remaining = text[1:-1].strip()
    result = []
    while remaining:
        matches = [name for name in names if remaining.startswith(name + "(")]
        assert len(matches) == 1
        name = matches[0]
        body = remaining[len(name) + 1:]
        quoted, escaped, stack, closing = False, False, [], None
        for position, char in enumerate(body):
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                stack.append(char)
            elif char in "]}":
                assert stack and stack.pop() == {"]": "[", "}": "{"}[char]
            elif char == ")" and not stack:
                closing = position
                break
        assert closing is not None
        arguments = {}
        for field in split_arguments(body[:closing]):
            key, separator, value = field.partition("=")
            key = key.strip()
            assert separator and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
            assert key not in arguments
            arguments[key] = DECODER.decode(value.strip())
        binary(arguments)
        result.append({"name": name, "arguments": arguments})
        remaining = body[closing + 1:].strip()
        if remaining:
            assert remaining.startswith(",") and remaining[1:].strip()
            remaining = remaining[1:].strip()
    assert 1 <= len(result) <= 16
    return result


def raw_tools(record):
    system = record["system"]
    assert system.count(MARKER) == 1
    marker_end = system.index(MARKER) + len(MARKER)
    start = marker_end + len(system[marker_end:]) - len(system[marker_end:].lstrip())
    tools, stop = DECODER.raw_decode(system, start)
    assert isinstance(tools, list)
    return tools, (start, stop)


def expected_schema(raw):
    """Apply only the published six policy rules, preserving values and names."""
    result = copy.deepcopy(raw)
    result["type"] = {"dict": "object", "int": "integer", "float": "number"}.get(
        raw["type"], raw["type"]
    )
    kind = result["type"]
    if kind == "object":
        result.setdefault("additionalProperties", False)
        result["properties"] = {k: expected_schema(v) for k, v in raw["properties"].items()}
    elif kind == "array":
        result.setdefault("maxItems", 1000)
        result["items"] = expected_schema(raw["items"])
    elif kind == "string":
        result.setdefault("maxLength", 16384)
    if "default" in result:
        note = "Source default annotation (never auto-filled): " + binary(result.pop("default")).decode() + "."
        result["description"] = result.get("description", "") + (
            "\n" if result.get("description") else ""
        ) + note
    return result


def schema_change_counts(node):
    counts = Counter()
    if node["type"] in {"dict", "int", "float"}:
        counts["explicit_type_alias"] += 1
    if node["type"] in {"dict", "object"}:
        if "additionalProperties" not in node:
            counts["project_closed_object"] += 1
        for child in node["properties"].values():
            counts.update(schema_change_counts(child))
    if node["type"] == "array":
        if "maxItems" not in node:
            counts["project_bounded_array"] += 1
        counts.update(schema_change_counts(node["items"]))
    if node["type"] == "string" and "maxLength" not in node:
        counts["project_bounded_string"] += 1
    if "default" in node:
        counts["typed_annotation_not_argument"] += 1
        counts["preserve_default_in_description"] += 1
    return counts


def at_pointer(value, pointer):
    for key in pointer.split("/")[1:]:
        key = key.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            return False, None
        value = value[key]
    return True, value


def validate_changes(row):
    original, converted = row["raw_tool"], row["tool"]
    expected = schema_change_counts(original["parameters"])
    expected.update({name: 1 for name in [
        "wire_schema_field_mapping", "wire_contract_version", "reversible_name_mapping",
        "retain_original_tool_name", "project_limit_not_source_fact",
        "unbound_fixture_project_limit", "bind_source_and_policy",
    ]})
    if "required" in original:
        expected["remove_redundant_outer_null"] += 1
    assert Counter(c["reason"] for c in row["changes"]) == expected
    for change in row["changes"]:
        pointer = change["path"]
        if change["reason"] == "wire_schema_field_mapping":
            assert pointer == "/parameters" and change["destination_path"] == "/parameters_json_schema"
            assert change["before_hash"] == digest(original["parameters"])
            assert change["after_hash"] == digest(converted["parameters_json_schema"])
            continue
        before_exists, before = at_pointer(original, pointer)
        after_pointer = "/parameters_json_schema/" + pointer[len("/parameters/"):] if pointer.startswith("/parameters/") else pointer
        after_exists, after = at_pointer(converted, after_pointer)
        assert before_exists == change["before_exists"] and after_exists == change["after_exists"]
        if before_exists:
            assert binary(before) == binary(change["before"])
        if after_exists:
            assert binary(after) == binary(change["after"])
    return expected


def semantic_schema(node):
    result = {k: copy.deepcopy(v) for k, v in node.items() if k not in {"description", "default"}}
    if node["type"] == "object":
        result["properties"] = {k: semantic_schema(v) for k, v in node["properties"].items()}
        result["required"] = sorted(node.get("required", []))
    if node["type"] == "array":
        result["items"] = semantic_schema(node["items"])
        result.setdefault("minItems", 0)
    if node["type"] == "string":
        result.setdefault("minLength", 0)
    if "enum" in result:
        result["enum"] = sorted(result["enum"], key=digest)
    return result


def original_shape(value):
    # Frozen original-group heuristic; normalized semantics are checked separately.
    if isinstance(value, dict):
        return {k: original_shape(v) for k, v in value.items() if k not in {"description", "default"}}
    if isinstance(value, list):
        return [original_shape(v) for v in value]
    return value


def template(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r'"[^"\n]*"|“[^”\n]*”', " SLOT ", text)
    text = re.sub(r"\b\d+(?:[.:-]\d+)*\b", " NUMBER ", text)
    return " ".join(re.findall(r"[a-z_]+|[\u3400-\u9fff]|[^\W\d_]+", text))


def message(role, content="", calls=None, call_id=None):
    return {"role": role, "content": content, "tool_calls": calls or [], "tool_call_id": call_id}


def source_system(record, conversion):
    _, span = raw_tools(record)
    original = record["system"]
    head = original[:original.index(MARKER)]
    assert hashlib.sha256(head[:341].encode()).hexdigest() == "882452d15b38ddae4e5ac085c48842d92034d84108eed9028dd8fd4aada3eb92"
    remaining = head[341:]
    if hashlib.sha256(remaining[:65].encode()).hexdigest() == "e019cfc401410c019cb312571abe0272dd4e9da5726e8e0971cd6598c705d159":
        remaining = remaining[65:]
    context = remaining.strip()
    tail = original[span[1]:]
    assert hashlib.sha256(tail[:192].encode()).hexdigest() == "6d3f9c4d13f56879d918f5ea317d2adbdd7b140749ce0aac449f3110ea9e6b5a"
    note = tail[192:].strip()
    assert conversion["schema_span"] == list(span)
    assert conversion["preserved_context"] == context
    assert conversion["preserved_syntax_note"] == note
    assert conversion["raw_system_sha256"] == hashlib.sha256(original.encode()).hexdigest()
    assert conversion["raw_head_sha256"] == hashlib.sha256(head.encode()).hexdigest()
    assert conversion["raw_suffix_sha256"] == hashlib.sha256(tail.encode()).hexdigest()
    expected = SYSTEM
    if context:
        assert re.fullmatch(r"(?:Today is \d{4}-\d{2}-\d{2}, (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\.\.?|The current time is \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.?)", context)
        expected += "\n\nPreserved source context:\n" + context
    if note:
        assert note in {
            "Note that the provided function is in Java 8 SDK syntax or JavaScript.",
            "Note that the provided function is in Python.",
        }
        expected += "\n\nPreserved source declaration note:\n" + note
    assert conversion["normalized_system_sha256"] == hashlib.sha256(expected.encode()).hexdigest()
    return expected


def reconstruct_prefix(record, stop, mapping, normalized_system):
    history = [message("system", normalized_system)]
    pending = []
    for index, turn in enumerate(record["conversations"][:stop]):
        role, value = turn["from"], turn["value"]
        if role == "assistant" and value.lstrip().startswith("["):
            calls = independent_calls(value, mapping)
            pending = [
                {"call_id": f"c-{index}-{j}", "name": mapping[c["name"]], "arguments": c["arguments"]}
                for j, c in enumerate(calls)
            ]
            history.append(message(role, calls=pending))
        elif role == "tool":
            observations = DECODER.decode(value)
            lookup = {mapping[o["name"]]: o["results"] for o in observations}
            assert len(lookup) == len(observations) == len(pending)
            assert set(lookup) == {c["name"] for c in pending}
            for call in pending:
                history.append(message(role, binary(lookup[call["name"]]).decode(), call_id=call["call_id"]))
            pending = []
        else:
            assert role in {"assistant", "user"} and not pending
            history.append(message(role, value))
    assert not pending
    return history


class Packet(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pre_blocks, self.current_pre, self.details, self.headings, self.csp = [], None, [], 0, False

    def handle_starttag(self, tag, attrs):
        assert tag in {"html", "meta", "title", "style", "h1", "p", "details", "summary", "h2", "pre"}
        attributes = dict(attrs)
        assert all(not k.startswith("on") and k not in {"src", "href", "srcdoc"} for k in attributes)
        if tag == "meta" and attributes.get("http-equiv") == "Content-Security-Policy":
            assert attributes["content"] == "default-src 'none'; style-src 'unsafe-inline'"
            self.csp = True
        if tag == "details":
            self.details.append(attributes["id"])
        if tag == "h2":
            self.headings += 1
        if tag == "pre":
            assert self.current_pre is None
            self.current_pre = []

    def handle_data(self, data):
        if self.current_pre is not None:
            self.current_pre.append(data)

    def handle_endtag(self, tag):
        if tag == "pre":
            assert self.current_pre is not None
            self.pre_blocks.append("".join(self.current_pre))
            self.current_pre = None


def quantiles(values):
    values = sorted(values)
    return {f"p{p}": values[math.ceil(len(values) * p / 100) - 1] for p in [50, 90, 95, 99]}


def audit(d1, output, tokenizer_root):
    base = Path.cwd()
    first, second = d1 / "policy-a", d1 / "policy-b"
    manifest = read(first / "manifest.json")
    assert manifest == read(second / "manifest.json") == read(base / "data/manifests/toolace-policy-build.v1.json")
    assert digest(manifest) == "87f86783706424553a5c889d51cbbadc33c3c4218e44b3f3ee95058a718b1756"
    artifact_evidence = {}
    for relative, expected in manifest["artifacts"].items():
        assert not Path(relative).is_absolute() and ".." not in Path(relative).parts
        paths = [folder / relative for folder in [first, second]]
        assert all(p.is_file() and not p.is_symlink() and sha(p) == expected for p in paths)
        assert paths[0].read_bytes() == paths[1].read_bytes()
        artifact_evidence[relative] = {"sha256": expected, "bytes": paths[0].stat().st_size}
    assert len(artifact_evidence) == 18
    for name, expected in manifest["module_hashes"].items():
        assert sha(base / "src/toolalign/data" / name) == expected
    assert sha(base / "src/toolalign/contracts/v1.json") == manifest["contract_sha256"]
    assert sha(base / "configs/source_toolace.v1.json") == POLICY_HASH == manifest["source_policy_hash"]
    assert manifest["record_scope"] == "historical_supervision_only"
    assert manifest["execution_binding"] == "none" and manifest["original_side_effect_class"] == "unknown"
    source_manifest = read(base / "data/manifests/toolace-source.v1.json")
    tokenizer_manifest = read(base / "data/manifests/qwen-source.v1.json")
    assert digest(source_manifest) == manifest["source_manifest_hash"]
    assert digest(tokenizer_manifest) == manifest["tokenizer_manifest_hash"]
    for folder, lock in [(d1 / "verified-source/toolace", source_manifest), (tokenizer_root, tokenizer_manifest)]:
        for name, expected in lock["files"].items():
            assert sha(folder / name) == expected["sha256"]
            assert (folder / name).stat().st_size == expected["size_bytes"]
    raw = read(d1 / "verified-source/toolace/data.json")
    raw_hashes = [digest(record) for record in raw]
    raw_by_hash = dict(zip(raw_hashes, raw, strict=True))
    info = rows(first / "source-index.jsonl")
    assignments = rows(first / "assignments.jsonl")
    examples = rows(first / "examples.jsonl")
    lineage = rows(first / "lineage.jsonl")
    tools = {r["raw_tool_hash"]: r for r in rows(first / "tool-lineage.jsonl")}
    quarantined = rows(first / "tool-quarantine.jsonl")
    report = read(first / "report.json")
    assert report == read(base / "reports/data/P02_POLICY_BUILD.json")["report"]
    assert len(raw) == len(info) == len(assignments) == 11300
    assert [r["source_record_hash"] for r in info] == raw_hashes
    assert [r["source_record_hash"] for r in assignments] == raw_hashes
    assert len(tools) == 16650 and len(quarantined) == 1311
    assert not (set(tools) & {r["raw_tool_hash"] for r in quarantined})
    defaults = 0
    unique_fields = Counter()
    for identity, row in tools.items():
        original, tool = row["raw_tool"], row["tool"]
        assert digest(original) == identity and digest(tool) == row["normalized_tool_hash"]
        expected = expected_schema(original["parameters"])
        assert binary(expected) == binary(tool["parameters_json_schema"])
        assert set(tool) == {"schema_version", "name", "description", "parameters_json_schema", "tool_version", "side_effect_class", "timeout_ms"}
        assert tool["description"] == "Original ToolACE name: " + binary(original["name"]).decode() + ".\n" + original["description"]
        slug = original["name"].translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))
        slug = re.sub("[^a-z0-9]+", "_", slug).strip("_")[:47] or "tool"
        assert tool["name"] == row["normalized_name"] == "ta_" + slug + "_" + identity[:12]
        assert tool["tool_version"] == "toolace.v1:" + POLICY_HASH[:12] + ":" + identity
        assert tool["side_effect_class"] == "sandbox_only" and tool["timeout_ms"] == 1000
        assert row["execution_binding"] == "none" and row["original_side_effect_class"] == "unknown"
        assert row["normalized_schema_key"] == digest(semantic_schema(expected))
        unique_fields.update(validate_changes(row))
        for annotation in row["default_annotations"]:
            node = original
            for component in annotation["path"].split("/")[1:]:
                node = node[component.replace("~1", "/").replace("~0", "~")]
            assert binary(node) == binary(annotation["value"])
            assert digest(node) == annotation["value_hash"] and annotation["inserted_into_arguments"] is False
            kind = "null" if node is None else {bool: "boolean", str: "string", int: "integer", float: "number", list: "array", dict: "object"}[type(node)]
            assert annotation["value_type"] == kind
            exists, schema_node = at_pointer(original, annotation["path"].removesuffix("/default"))
            assert exists
            assert annotation["declared_type"] == {"dict": "object", "int": "integer", "float": "number"}.get(schema_node["type"], schema_node["type"])
            defaults += 1
        validate_record(tool, "tool")
    assert defaults == 5282
    policy_report = report["source_policy"]
    assert unique_fields == policy_report["unique_tool_field_changes"]
    occurrence_fields, source_fields, decision_fields = Counter(), Counter(), Counter()
    converted_occurrences = 0
    for data in info:
        changes = [c["reason"] for identity in data.get("raw_tool_hashes", []) if identity in tools for c in tools[identity]["changes"]]
        converted_occurrences += sum(identity in tools for identity in data.get("raw_tool_hashes", []))
        occurrence_fields.update(changes)
        source_fields.update(set(changes))
        decision_fields.update({reason: len(data["decisions"]) for reason in set(changes)})
    assert converted_occurrences == policy_report["converted_tool_occurrences"] == 31822
    assert occurrence_fields == policy_report["tool_occurrence_field_changes"]
    assert source_fields == policy_report["source_records_per_change_reason"]
    assert decision_fields == policy_report["assistant_decisions_per_change_reason"]
    print("PASS: 18 artifacts on both builds, pinned source/tokenizer/policy/modules, 16650 tool transformations", flush=True)

    by_id = {e["example_id"]: e for e in examples}
    valid_lineage = {r["example_id"]: r for r in lineage if r["exclusion_reason"] is None}
    assert len(by_id) == len(examples) == len(valid_lineage) == 8228
    info_by_hash = {r["source_record_hash"]: r for r in info}
    target_count, historical_count, checked_sources = 0, 0, set()
    source_conversion = {}
    for e in examples:
        row = valid_lineage[e["example_id"]]
        record = raw_by_hash[e["source_record_hash"]]
        raw_declarations, _ = raw_tools(record)
        identities = [digest(t) for t in raw_declarations]
        assert identities == row["raw_tool_hashes"]
        assert [tools[h]["tool"] for h in identities] == e["tools"]
        mapping = {tools[h]["raw_name"]: tools[h]["normalized_name"] for h in identities}
        registered = {t["name"]: t for t in e["tools"]}
        target_index = row["source_turn_index"]
        assert target_index == row["prefix_turn_end_exclusive"]
        assert hashlib.sha256(record["conversations"][target_index]["value"].encode()).hexdigest() == row["source_action_sha256"]
        expected_calls = independent_calls(record["conversations"][target_index]["value"], mapping)
        expected_calls = [{"call_id": f"c-{target_index}-{j}", "name": mapping[c["name"]], "arguments": c["arguments"]} for j, c in enumerate(expected_calls)]
        assert binary(expected_calls) == binary(e["expected_action"]["tool_calls"])
        assert e["expected_action"]["kind"] == "tool_calls" and not e["expected_action"]["content"]
        for call, binding in zip(expected_calls, row["call_bindings"], strict=True):
            assert binding["call_id"] == call["call_id"] and binding["normalized_name"] == call["name"]
            assert mapping[binding["raw_name"]] == call["name"]
            assert digest(call["arguments"]) == binding["arguments_hash"]
            assert binding["arguments_filled_or_coerced"] is False
        target_count += len(expected_calls)
        if e["source_record_hash"] not in source_conversion:
            source_conversion[e["source_record_hash"]] = source_system(record, row["system_conversion"])
        expected_messages = reconstruct_prefix(record, target_index, mapping, source_conversion[e["source_record_hash"]])
        assert binary(e["messages"]) == binary(expected_messages)
        historical_count += sum(len(m["tool_calls"]) for m in expected_messages)
        assert binary(model_input_from_example(e)) == binary({"messages": expected_messages, "tools": e["tools"]})
        assert digest({k: v for k, v in e.items() if k not in {"example_id", "group_id", "split"}}) == e["example_id"]
        assert all(row[k] == e[k] for k in ["example_id", "source_record_hash", "group_id", "split"])
        assert row["normalized_hash"] == e["example_id"] and row["augmentation_parent"] is None
        validate_record(e, "example")
        if e["source_record_hash"] not in checked_sources:
            # Include source calls after an accepted decision, not only its prefix.
            for turn in record["conversations"]:
                if turn["from"] == "assistant" and turn["value"].lstrip().startswith("["):
                    for call in independent_calls(turn["value"], mapping):
                        validate_tool_arguments(registered[mapping[call["name"]]], call["arguments"])
            checked_sources.add(e["source_record_hash"])
    assert (target_count, historical_count, len(checked_sources)) == (15073, 632, 7662)
    print("PASS: independently parsed 15073 target calls, 632 prefix calls, full prefixes and all source calls", flush=True)

    groups, owners = defaultdict(set), defaultdict(set)
    normalized_owners = defaultdict(lambda: {"groups": set(), "splits": set(), "sources": set()})
    for index, (record, data, assignment) in enumerate(zip(raw, info, assignments, strict=True)):
        assert assignment["source_index"] == data["source_index"] == index
        groups[assignment["group_id"]].add(raw_hashes[index])
        keys = {"source:" + raw_hashes[index]}
        try:
            declarations, _ = raw_tools(record)
        except (AssertionError, KeyError, ValueError):
            declarations = []
        keys.update("tool:" + digest({"name": t.get("name")}) for t in declarations)
        keys.update("schema:" + digest(original_shape(t.get("parameters"))) for t in declarations)
        keys.update("template:" + digest(template(t["value"])) for t in record["conversations"] if t["from"] == "user" and template(t["value"]))
        assert sorted(keys) == assignment["group_keys"]
        for key in keys:
            owners[key].add(assignment["split"])
        expected_normalized = []
        for declaration in declarations:
            tool = tools.get(digest(declaration))
            if tool:
                key = digest(semantic_schema(tool["tool"]["parameters_json_schema"]))
                expected_normalized.append(key)
                for field, value in [("groups", assignment["group_id"]), ("splits", assignment["split"]), ("sources", raw_hashes[index])]:
                    normalized_owners[key][field].add(value)
        assert sorted(set(expected_normalized)) == sorted(set(data.get("normalized_schema_keys", [])))
    assert len(groups) == 3517 and max(map(len, groups.values())) == 6716
    assert all(len(value) == 1 for value in owners.values())
    for group_id, members in groups.items():
        assert digest(sorted(members)) == group_id
    for assignment in assignments:
        group_id = assignment["group_id"]
        ood = int(digest([17, "ood", group_id])[:16], 16) / 2**64
        split = int(digest([17, "split", group_id])[:16], 16) / 2**64
        expected = "ood_test" if ood < 0.1 else "train" if split < 0.8 else "validation" if split < 0.9 else "test"
        assert assignment["split"] == expected
    conflicts = [{"normalized_schema_key": key, **{k: sorted(v) for k, v in owner.items()}} for key, owner in sorted(normalized_owners.items()) if len(owner["groups"]) > 1]
    assert conflicts == rows(first / "normalized-group-conflicts.jsonl")
    bridge_sources = {s for row in conflicts for s in row["sources"]}
    assert len(conflicts) == 11 and sum(len(r["splits"]) > 1 for r in conflicts) == 4
    assert len(bridge_sources) == 64 and not (bridge_sources & checked_sources)
    effective_owners = defaultdict(set)
    for e in examples:
        row = valid_lineage[e["example_id"]]
        assert row["group_keys"] == assignments[info_by_hash[e["source_record_hash"]]["source_index"]]["group_keys"]
        expected_keys = sorted("normalized_schema:" + digest(semantic_schema(t["parameters_json_schema"])) for t in e["tools"])
        assert expected_keys == row["normalized_group_keys"]
        for key in row["group_keys"] + expected_keys + ["group:" + e["group_id"]]:
            effective_owners[key].add(e["split"])
    assert all(len(value) == 1 for value in effective_owners.values())
    decisions = [d for i in info for d in i["decisions"]]
    assert len(decisions) == sum(t.get("from") == "assistant" for record in raw for t in record["conversations"])
    primary = Counter(d["reasons"][0] for d in decisions if d["reasons"])
    assert len(decisions) == 13819 and sum(primary.values()) == 5505
    assert primary == report["primary_exclusion_counts"]
    assert Counter(r for d in decisions for r in d["reasons"]) == report["overlapping_exclusion_counts"]
    assert len(lineage) == 8314 and len(examples) + sum(bool(r["exclusion_reason"]) for r in lineage) == 8314
    drops = Counter(r["exclusion_reason"] for r in lineage if r["exclusion_reason"])
    assert drops == {"normalized_schema_crosses_original_groups": 53, "exact_example_duplicate": 33}
    assert drops == report["post_normalization_exclusions"]
    assert Counter(e["split"] for e in examples) == report["final_split_counts"] == {"train": 7515, "validation": 234, "test": 215, "ood_test": 264}
    for split in ["train", "validation", "test", "ood_test"]:
        assert rows(first / (split + ".jsonl")) == [e for e in examples if e["split"] == split]
    assert len({digest(t) for e in examples for t in e["tools"]}) == 15105
    final_contents = {digest({k: e[k] for k in ["messages", "tools", "expected_action"]}) for e in examples}
    assert len(final_contents) == len(examples)
    for row in lineage:
        if row["exclusion_reason"] == "exact_example_duplicate":
            source_hash = row["source_record_hash"]
            record = raw_by_hash[source_hash]
            declarations = [tools[h] for h in row["raw_tool_hashes"]]
            mapping = {t["raw_name"]: t["normalized_name"] for t in declarations}
            target = row["source_turn_index"]
            parsed = independent_calls(record["conversations"][target]["value"], mapping)
            calls = [{"call_id": f"c-{target}-{i}", "name": mapping[c["name"]], "arguments": c["arguments"]} for i, c in enumerate(parsed)]
            projection = {
                "messages": reconstruct_prefix(record, target, mapping, source_system(record, row["system_conversion"])),
                "tools": [t["tool"] for t in declarations],
                "expected_action": {"kind": "tool_calls", "tool_calls": calls, "content": ""},
            }
            assert digest(projection) in final_contents
    lengths = [r["length"] for r in valid_lineage.values()]
    for field in ["prompt_tokens", "completion_tokens", "total_tokens", "schema_marginal_tokens", "prompt_without_schema_tokens"]:
        expected = report["accepted_example_lengths"][field]
        assert expected == {"count": 8228, **quantiles([r[field] for r in lengths])}
    assert all(r["total_tokens"] == r["prompt_tokens"] + r["completion_tokens"] for r in lengths)
    assert Counter("le_2048" if r["total_tokens"] <= 2048 else "le_4096" if r["total_tokens"] <= 4096 else "larger" for r in lengths) == {"le_2048": 8115, "le_4096": 113}
    assert all(r["length_basis"] == "qwen3_non_thinking_concat_one_eos_v1" and r["prefix_stable"] is True for r in lengths)
    denominator = sum(r["total_tokens"] for r in lengths)
    for field, share in report["accepted_example_lengths"]["aggregate_token_shares"].items():
        assert share == sum(r[field] for r in lengths) / denominator
    print("PASS: original groups, all normalized bridges, effective split intersections and denominator accounting", flush=True)

    samples = rows(first / "human-review/samples.jsonl")
    review = read(first / "human-review/manifest.json")
    with (first / "human-review/review.csv").open() as stream:
        worksheet = list(csv.DictReader(stream))
    with (d1 / "p02-human-review-submission/review.csv").open() as stream:
        submission = list(csv.DictReader(stream))
    assert worksheet == submission and len(samples) == len(worksheet) == 100
    csv_identity = [{k: r[k] for k in ["source_index", "source_record_hash", "example_ids", "strata"]} for r in worksheet]
    assert digest(csv_identity) == "b7878f5ced14bdaa69f4cbbbffef177e2912625a411858e348cfef6b9b91590c"
    assert all(not r[k] for r in worksheet for k in ["reviewer", "reviewed_at_utc", "verdict", "issue_categories", "notes"])
    assert len({s["source_record_hash"] for s in samples}) == 100
    assert sum(len(s["normalized_examples"]) for s in samples) == 114
    assert review["accepted_examples_reviewed"] == 0 and review["mislabel_rate"] is None
    assert review["status"] == "PENDING_KRIS_REVIEW" and review["pool"] == "final_valid_examples_only"
    assert len(review["strata"]) == 34 and review["examples_artifact_sha256"] == sha(first / "examples.jsonl")
    for sample, csv_row in zip(samples, worksheet, strict=True):
        index = sample["source_index"]
        assert raw[index] == sample["source"] and raw_hashes[index] == sample["source_record_hash"]
        assert csv_row["source_index"] == str(index) and csv_row["source_record_hash"] == sample["source_record_hash"]
        assert csv_row["example_ids"].split(";") == [e["example_id"] for e in sample["normalized_examples"]]
        assert csv_row["strata"].split(";") == sample["strata"]
        assert sample["assignment"] == assignments[index]
        assert all(e == by_id[e["example_id"]] for e in sample["normalized_examples"])
        assert all(r == valid_lineage[r["example_id"]] for r in sample["lineage"])
        assert sample["system_conversion"] == info[index]["system_conversion"]
        assert sample["historical_observation_bindings"] == info[index]["observation_bindings"]
        assert sample["tool_transformations"] == [tools[h] for h in info[index]["raw_tool_hashes"]]
    accepted_by_source = defaultdict(list)
    for e in examples:
        accepted_by_source[e["source_record_hash"]].append(e)
    strata = {}
    rank = sorted(accepted_by_source, key=lambda h: digest([17, h]))
    all_labels = {}
    for source_hash in rank:
        data = info_by_hash[source_hash]
        local = accepted_by_source[source_hash]
        transformations = [tools[h] for h in data["raw_tool_hashes"]]
        labels = {
            "language:" + data["language"], "split:" + local[0]["split"],
            "multiple_valid_decisions:" + str(len(local) > 1),
            "multiple_target_calls:" + str(any(len(e["expected_action"]["tool_calls"]) > 1 for e in local)),
            "multiple_tools:" + str(len(local[0]["tools"]) > 1),
            "historical_observations:" + str(bool(data["observation_bindings"])),
            "preserved_time_context:" + str(bool(data["system_conversion"]["preserved_context"])),
            "default_annotation:" + str(any(t["default_annotations"] for t in transformations)),
        }
        labels.update("transformation:" + c["reason"] for t in transformations for c in t["changes"])
        labels.update("length_bucket:" + valid_lineage[e["example_id"]]["length_bucket"] for e in local)
        all_labels[source_hash] = sorted(labels)
        for label in sorted(labels):
            strata.setdefault(label, source_hash)
    assert strata == review["strata"]
    selected = set(strata.values())
    for source_hash in rank:
        if len(selected) >= 100:
            break
        selected.add(source_hash)
    assert sorted(selected) == [s["source_record_hash"] for s in samples]
    assert all(s["strata"] == all_labels[s["source_record_hash"]] for s in samples)
    packet = Packet()
    html_text = (first / "human-review/index.html").read_text()
    packet.feed(html_text)
    assert packet.csp and packet.current_pre is None
    assert packet.details == ["record-" + str(s["source_index"]) for s in samples]
    assert packet.headings == 500 and len(packet.pre_blocks) == 500
    for i, sample in enumerate(samples):
        contents = [sample["source"], sample["normalized_examples"], sample["tool_transformations"],
                    {"system_conversion": sample["system_conversion"], "historical_observation_bindings": sample["historical_observation_bindings"]},
                    {"strata": sample["strata"], "assignment": sample["assignment"], "lineage": sample["lineage"]}]
        # HTML was rendered before sorted-key JSONL storage. Object display order
        # may differ; every decoded JSON value, including numeric type, must match.
        observed = packet.pre_blocks[i * 5:(i + 1) * 5]
        assert [binary(DECODER.decode(v)) for v in observed] == [binary(v) for v in contents]
    print("PASS: 100 distinct sources / 114 exact examples / 34 strata; 500 escaped HTML sections; human fields blank", flush=True)

    from jinja2.sandbox import ImmutableSandboxedEnvironment
    from tokenizers import Tokenizer

    configuration = read(tokenizer_root / "tokenizer_config.json")
    tokenizer = Tokenizer.from_file(str(tokenizer_root / "tokenizer.json"))
    environment = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    environment.filters["tojson"] = lambda value: json.dumps(value, ensure_ascii=False)
    official = environment.from_string(configuration["chat_template"])
    eos = tokenizer.token_to_id(configuration["eos_token"])
    assert eos == 151645
    selected_ids = {e["example_id"] for sample in samples for e in sample["normalized_examples"]}
    selected_ids.update(e["example_id"] for e in examples if valid_lineage[e["example_id"]]["length"]["total_tokens"] > 2048)
    for identity in sorted(selected_ids):
        e = by_id[identity]
        tool_payload = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters_json_schema"]}} for t in e["tools"]]
        prompt = official.render(messages=e["messages"], tools=tool_payload, add_generation_prompt=True, enable_thinking=False)
        without = official.render(messages=e["messages"], tools=None, add_generation_prompt=True, enable_thinking=False)
        completion = "\n".join("<tool_call>\n" + json.dumps({"name": c["name"], "arguments": c["arguments"]}, ensure_ascii=False) + "\n</tool_call>" for c in e["expected_action"]["tool_calls"])
        prompt_ids = tokenizer.encode(prompt, add_special_tokens=False).ids
        concat_ids = tokenizer.encode(prompt + completion, add_special_tokens=False).ids
        assert concat_ids[:len(prompt_ids)] == prompt_ids
        sequence = concat_ids + [eos]
        length = valid_lineage[identity]["length"]
        assert length["sequence_hash"] == digest(sequence) and length["eos_token_id"] == eos
        assert length["total_tokens"] == len(sequence)
        assert length["prompt_tokens"] == len(prompt_ids)
        assert length["completion_tokens"] == len(sequence) - len(prompt_ids)
        assert length["prompt_without_schema_tokens"] == len(tokenizer.encode(without, add_special_tokens=False).ids)
        assert length["schema_marginal_tokens"] == len(prompt_ids) - length["prompt_without_schema_tokens"]
    print("PASS: independently rendered and tokenized", len(selected_ids), "real decisions, including all 113 over 2048", flush=True)
    result = {
        "status": "R1_INDEPENDENT_AUTOMATED_INTEGRITY_PASS_NOT_HUMAN_SEMANTIC_APPROVAL",
        "manifest_hash": digest(manifest), "artifacts_both_builds": artifact_evidence,
        "verified_tool_transformations": len(tools), "typed_default_annotations": defaults,
        "field_lineage_before_after_values_verified": True,
        "transformation_denominators_verified": ["unique_tool", "tool_occurrence", "source_record", "assistant_decision"],
        "converted_tool_occurrences": converted_occurrences,
        "independently_reconstructed_excluded_exact_duplicates": 33,
        "examples_with_independently_rebuilt_targets_and_prefixes": len(examples),
        "independently_parsed_target_calls": target_count, "independently_parsed_prefix_calls": historical_count,
        "sources_with_all_calls_checked_against_narrowed_schema": len(checked_sources),
        "original_groups": len(groups), "largest_group": max(map(len, groups.values())),
        "normalized_bridge_keys": len(conflicts), "normalized_bridge_sources": len(bridge_sources),
        "effective_key_split_intersections": 0, "near_semantic_recall": "NOT_EXHAUSTIVE",
        "raw_decisions": len(decisions), "pre_excluded": sum(primary.values()), "candidates": len(lineage),
        "post_excluded": dict(drops), "final_examples": len(examples), "final_splits": report["final_split_counts"],
        "real_decisions_independently_retokenized": len(selected_ids), "all_113_over_2048_included": True,
        "length_basis": "qwen3_non_thinking_concat_one_eos_v1", "training": "NOT_RUN",
        "human_review": {"status": "PENDING", "distinct_sources": 100, "decisions": 114, "strata": 34,
                         "identity_hash": digest(csv_identity),
                         "all_human_fields_blank": True, "escaped_pre_sections": 500, "semantic_verdicts_by_kris": 0},
    }
    output.write_bytes(binary(result) + b"\n")
    print(json.dumps({k: v for k, v in result.items() if k != "artifacts_both_builds"}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("private_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tokenizer-root", type=Path)
    args = parser.parse_args()
    assert ".toolalign-local" in args.output.resolve().parts
    audit(args.private_root, args.output, args.tokenizer_root or args.private_root / "verified-source/qwen")
