"""Answer-blind first-fifty eligibility and connected-group isolation."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.data.common import file_hash, read_json, write_json
from toolalign.data.grouping import Union, normalized_schema_semantics, schema_shape, task_template
from toolalign.data.preferences.audit import p02_metadata, task_keys
from toolalign.data.training_selection import new_private_directory
from toolalign.evaluation.cuda_eval.protocol import read_inputs
from toolalign.model_io.cuda_generation import prompt_ids
from toolalign.model_io.offline import OfflineQwenTokenizer
from toolalign.tools import LocalToolRegistry
from toolalign.tools._json import INPUT_BYTES, encode

from . import CATEGORIES, CATEGORY_LIMIT, COMMIT, SCAN_LIMIT
from .adapter import Unrepresentable, adapt_prompt, parameter_projection
from .source import first_questions, source_identity

RULES = {
    "version": "toolalign.bfcl-selection.g5.v1", "categories": list(CATEGORIES),
    "scan_limit_per_category": SCAN_LIMIT, "retain_limit_per_category": CATEGORY_LIMIT,
    "order": "official_file_order", "context_tokens": 2048, "reserved_new_tokens": 256,
    "schema": "type_spelling_aliases_only;explicit_closed_objects_and_source_bounds;no_keyword_dropping",
    "names": "collision_free_ordinal_aliases_with_exact_inverse",
    "isolation": "transitive_original_tool_raw_and_normalized_schema_lexical_template_source_keys",
    "excluded_reference_groups": "all_P02_splits_plus_P03_development_plus_G4_train",
    "answer_access": "only_after_selection_is_saved_and_hash_bound",
}


def schema_keys(schema):
    keys = {"schema:" + canonical_hash(schema_shape(schema))}
    projected, _ = parameter_projection(schema)
    keys.add("schema:" + canonical_hash(schema_shape(projected)))
    # The existing normalized helper is not a semantic solver. For unsupported
    # schemas keep their exact structural key instead of inventing a normal form.
    try:
        keys.add("normalized-schema:" + canonical_hash(normalized_schema_semantics(projected)))
    except (KeyError, TypeError, AttributeError):
        pass
    return keys


def prompt_keys(record):
    keys = {"source:" + canonical_hash(record)}
    for function in record["function"]:
        keys.add("tool:" + canonical_hash({"name": function["name"]}))
        keys.update(schema_keys(function["parameters"]))
    for turn in record["question"]:
        for message in turn:
            if message.get("role") == "user" and isinstance(message.get("content"), str):
                keys.add("template:" + canonical_hash(task_template(message["content"])))
    return keys


def reference_groups(p02_manifest, p02_digest, g4_package, development):
    if file_hash(p02_manifest) != p02_digest:
        raise ValueError("p02_manifest_binding")
    p02, provenance = p02_metadata(p02_manifest)
    references = []
    merged = defaultdict(set)
    for row in p02:
        merged[row["group_id"]].update(row["group_keys"])
    references.extend({"origin": "P02", "group_id": group, "keys": keys}
                      for group, keys in sorted(merged.items()))
    g4 = Path(g4_package)
    manifest = read_json(g4 / "manifest.json")
    if file_hash(g4 / "tasks.json") != manifest["artifacts"]["tasks.json"]:
        raise ValueError("g4_task_binding")
    if manifest["p02"] != provenance:
        raise ValueError("g4_p02_metadata_binding")
    tasks = read_json(g4 / "tasks.json")
    if tasks["purpose"] != "train-candidate-generation":
        raise ValueError("g4_train_only_required")
    merged = defaultdict(set)
    for task in tasks["tasks"]:
        merged[task["group_id"]].update(task_keys(task))
    references.extend({"origin": "G4", "group_id": group, "keys": keys}
                      for group, keys in sorted(merged.items()))
    dev = read_json(development)
    if dev.get("purpose") != "public-original-development":
        raise ValueError("public_development_required")
    common = set()
    for tool in LocalToolRegistry().tools:
        common.add("tool:" + canonical_hash({"name": tool["name"]}))
        common.update(schema_keys(tool["parameters_json_schema"]))
    for case in dev["cases"]:
        references.append({"origin": "P03", "group_id": case["group"], "keys": common | {
            "source:" + canonical_hash(case), "template:" + canonical_hash(task_template(case["prompt"]))}})
    return references, {"p02": provenance, "g4_manifest_sha256": file_hash(g4 / "manifest.json"),
                        "g4_tasks_sha256": file_hash(g4 / "tasks.json"),
                        "development_sha256": file_hash(development),
                        "g4_tasks": len(tasks["tasks"]), "development_tasks": len(dev["cases"]),
                        "p02_held_out_content_read": False}


def connected_groups(candidates, references):
    """Include all scanned candidates in bridge detection, even excluded schemas."""
    candidate_keys = [prompt_keys(row["record"]) for row in candidates]
    keys = candidate_keys + [set(reference["keys"]) for reference in references]
    union, owners = Union(len(keys)), {}
    for index, values in enumerate(keys):
        for key in sorted(values):
            if key in owners:
                union.join(index, owners[key])
            else:
                owners[key] = index
    components = defaultdict(lambda: {"task_ids": [], "reference_groups": []})
    for index, row in enumerate(candidates):
        components[union.root(index)]["task_ids"].append(row["record"]["id"])
    for index, reference in enumerate(references, start=len(candidates)):
        component = components[union.root(index)]
        if component["task_ids"]:
            component["reference_groups"].append({k: reference[k] for k in ("origin", "group_id")})
    groups, assignments = [], {}
    for component in components.values():
        if not component["task_ids"]:
            continue
        component["task_ids"].sort()
        component["reference_groups"].sort(key=lambda value: (value["origin"], value["group_id"]))
        group = canonical_hash(component)
        groups.append({"group_id": group, **component})
        for task_id in component["task_ids"]:
            assignments[task_id] = {"group_id": group, "overlap": bool(component["reference_groups"]),
                                    "reference_groups": component["reference_groups"]}
    return {"components": sorted(groups, key=lambda row: row["group_id"]), "assignments": assignments,
            "candidate_keys": {row["record"]["id"]: sorted(key)
                               for row, key in zip(candidates, candidate_keys, strict=True)},
            "method": RULES["isolation"], "lexical_templates_are_not_exhaustive_semantic_deduplication": True}


def choose_subset(candidates, references, token_count):
    """The injected counter is a test seam; the CLI always uses the fixed tokenizer."""
    if any(sum(row["category"] == category for row in candidates) > SCAN_LIMIT for category in CATEGORIES):
        raise ValueError("scan_limit_exceeded")
    ids = [row["record"]["id"] for row in candidates]
    if len(ids) != len(set(ids)) or any(row["category"] not in CATEGORIES for row in candidates):
        raise ValueError("candidate_identity_or_category")
    audit = connected_groups(candidates, references)
    selected, inputs, ledger = [], [], []
    retained = Counter()
    for row in candidates:
        category, record = row["category"], row["record"]
        grouping = audit["assignments"][record["id"]]
        item = {"task_id": record["id"], "category": category, "ordinal": row["ordinal"],
                "record_sha256": canonical_hash(record), **grouping, "issues": [],
                "input_tokens": None, "length_status": "NOT_APPLICABLE_UNREPRESENTABLE"}
        adapted = None
        try:
            adapted = adapt_prompt(record)
            encode(adapted["model_input"], INPUT_BYTES)
        except Unrepresentable as exc:
            item["issues"] = exc.issues
        except ValueError as exc:
            item["issues"] = [{"code": "model_input_transport_limit", "detail": str(exc)}]
        if adapted is not None and not item["issues"]:
            count = token_count(adapted["model_input"])
            if type(count) is not int or count < 0:
                raise ValueError("invalid_input_token_count")
            item.update(input_tokens=count, length_status="PASS" if count + 256 <= 2048 else "EXCEEDS_CONTEXT")
            if count + 256 > 2048:
                item["issues"].append({"code": "context_limit"})
        if grouping["overlap"]:
            item["issues"].append({"code": "known_group_overlap"})
        eligible = not item["issues"]
        keep = eligible and retained[category] < CATEGORY_LIMIT
        item.update(eligible=eligible, selected=keep,
                    disposition="selected" if keep else "category_cap" if eligible else "excluded")
        ledger.append(item)
        if keep:
            retained[category] += 1
            family = "bfcl-" + canonical_hash(sorted(adapted["name_map"]))[:32]
            entry = {"task_id": record["id"], "family_id": family, "group_id": grouping["group_id"],
                     "category": category, "model_input": adapted["model_input"]}
            inputs.append(entry)
            selected.append({**{k: entry[k] for k in entry if k != "model_input"},
                             "ordinal": row["ordinal"], "record": record,
                             "model_input_hash": canonical_hash(entry["model_input"]),
                             **{k: v for k, v in adapted.items() if k != "model_input"}})
    coverage = {category: {"inspected": sum(r["category"] == category for r in ledger),
                            "eligible": sum(r["category"] == category and r["eligible"] for r in ledger),
                            "selected": retained[category], "shortfall": CATEGORY_LIMIT - retained[category],
                            "exclusion_codes": dict(Counter(code for r in ledger if r["category"] == category
                                                            for code in {x["code"] for x in r["issues"]}))}
                for category in CATEGORIES}
    return {"official_commit": COMMIT, "rules": RULES,
            "status": "FROZEN" if selected else "NO_ELIGIBLE_INPUTS", "selected": selected,
            "coverage": coverage, "ledger": ledger,
            "selected_groups": len({row["group_id"] for row in inputs}),
            "official_scoring": "NOT_RUN", "model_evaluation": "NOT_RUN"}, inputs, audit


def freeze_subset(source_root, p02_manifest, p02_digest, g4_package, development, tokenizer_root, output):
    identity = source_identity(source_root)
    references, provenance = reference_groups(p02_manifest, p02_digest, g4_package, development)
    tokenizer = OfflineQwenTokenizer(tokenizer_root, repo_id="Qwen/Qwen3-1.7B",
                                     revision="70d244cc86ccca08cf5af4e1e306ecf908b1ad5e")
    selection, inputs, audit = choose_subset(first_questions(source_root), references,
                                            lambda value: len(prompt_ids(tokenizer, value)))
    root = new_private_directory(output)
    write_json(root / "source.json", identity)
    write_json(root / "isolation.json", {"references": provenance, **audit})
    write_json(root / "tokenizer.json", tokenizer.identity)
    files = ["source.json", "isolation.json", "tokenizer.json"]
    if inputs:
        write_json(root / "inputs.json", {"schema_version": "toolalign.evaluation-inputs.v1",
                                          "purpose": "action-only-model-evaluation", "inputs": inputs})
        read_inputs(root / "inputs.json", file_hash(root / "inputs.json"), "action-only")
        selection["inputs_sha256"] = file_hash(root / "inputs.json")
        files.append("inputs.json")
    else:
        selection["inputs_sha256"] = None
    write_json(root / "selection.json", selection)
    files.append("selection.json")
    manifest = {"schema_version": "toolalign.bfcl-subset.v1", "status": selection["status"],
                "official_commit": COMMIT, "artifacts": {name: file_hash(root / name) for name in files},
                "answers_read": False, "model_evaluation": "NOT_RUN"}
    write_json(root / "manifest.json", manifest)
    return manifest
