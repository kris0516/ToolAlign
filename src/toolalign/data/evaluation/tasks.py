"""Build the fixed L1 consumer format from private, explicitly authored recipes."""

from __future__ import annotations

import copy
from collections import Counter

from toolalign.contracts import canonical_hash, model_input_from_example, validate_record
from toolalign.data.common import DataError
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.tools import LocalToolExecutor, LocalToolRegistry
from toolalign.tools._json import parse_action
from toolalign.tools.heldout_catalog import DOMAIN_TOOLS

CATALOG = "heldout-devops.v1"
TASK_SCHEMA = "toolalign.evaluation-tasks.v1"
SOURCE = "toolalign-original-g5-heldout"
REVISION = "p06-g5-corpus.v1"
CATEGORIES = (
    "single_tool", "multi_step", "tool_confusion", "no_tool",
    "clarify_or_refuse", "fault_recovery",
)


def prepare_tasks(cases):
    """Answers, scripts and constraints are author input, not generated truth."""
    if not 1 <= len(cases) <= 48:
        raise DataError("evaluation_task_count")
    counts, tasks, authoring = Counter(), [], {}
    for case in cases:
        domain, category = case["domain"], case["category"]
        if domain not in DOMAIN_TOOLS or category not in CATEGORIES:
            raise DataError("evaluation_domain_or_category")
        counts[domain, category] += 1
        if counts[domain, category] > 2:
            raise DataError("evaluation_domain_category_limit")
        if not case["positive_scripts"] or not case["negative_scripts"]:
            raise DataError("evaluation_authoring_scripts_required")
        identity = {key: case[key] for key in (
            "domain", "family_id", "category", "prompt", "answers", "strategies", "faults",
        )}
        source_hash = canonical_hash(identity)
        task_id = "g5-" + source_hash[:32]
        registry = LocalToolRegistry(DOMAIN_TOOLS[domain], catalog_id=CATALOG)
        example = validate_record({
            "schema_version": "toolalign.example.v1", "example_id": task_id,
            "source": SOURCE, "source_revision": REVISION, "license_id": "MIT",
            "source_record_hash": source_hash, "group_id": "pending-group-audit",
            "split": "test", "category": category,
            "messages": [{"role": "user", "content": case["prompt"],
                          "tool_calls": [], "tool_call_id": None}],
            "tools": registry.tools,
            "expected_action": parse_action(case["positive_scripts"][0][0]),
        }, "example")
        tasks.append({
            "task_id": task_id, "family_id": case["family_id"],
            "group_id": example["group_id"], "category": category, "example": example,
            "oracle_task": {
                "task_id": task_id, "group_id": example["group_id"], "split": "test",
                "expected_action": example["expected_action"],
                "oracle_payload": {"version": ORACLE_VERSION, "answers": case["answers"],
                                   "strategies": case["strategies"]},
            },
            "faults": case["faults"], "tool_names": sorted(DOMAIN_TOOLS[domain]),
        })
        authoring[task_id] = copy.deepcopy(case)
    bundle = {"schema_version": TASK_SCHEMA, "purpose": "heldout-model-evaluation",
              "catalog": CATALOG,
              "registry_hash": LocalToolRegistry(catalog_id=CATALOG).registry_hash,
              "tasks": tasks,
              "recovery_task_ids": [t["task_id"] for t in tasks
                                    if t["category"] == "fault_recovery"]}
    validate_tasks(bundle)
    return bundle, authoring


def validate_tasks(bundle):
    """Mirror the agreed storage identity; model projection stays messages/tools."""
    if (set(bundle) != {"schema_version", "purpose", "catalog", "registry_hash", "tasks",
                       "recovery_task_ids"}
            or bundle["schema_version"] != TASK_SCHEMA
            or bundle["purpose"] != "heldout-model-evaluation" or bundle["catalog"] != CATALOG
            or bundle["registry_hash"] != LocalToolRegistry(catalog_id=CATALOG).registry_hash
            or not 0 <= len(bundle["tasks"]) <= 48):
        raise DataError("evaluation_bundle_identity")
    seen, counts = set(), Counter()
    for task in bundle["tasks"]:
        if set(task) != {"task_id", "family_id", "group_id", "category", "example", "oracle_task",
                         "faults", "tool_names"}:
            raise DataError("evaluation_task_fields")
        example, oracle = validate_record(task["example"], "example"), task["oracle_task"]
        registry = LocalToolRegistry(task["tool_names"], catalog_id=CATALOG)
        domains = [name for name, tools in DOMAIN_TOOLS.items()
                   if set(tools) == set(task["tool_names"])]
        if (len(domains) != 1 or example["tools"] != registry.tools
                or example["source"] != SOURCE or example["source_revision"] != REVISION
                or task["task_id"] in seen
                or task["task_id"] != example["example_id"] or task["task_id"] != oracle["task_id"]
                or task["group_id"] != example["group_id"] or task["group_id"] != oracle["group_id"]
                or example["split"] != "test" or oracle["split"] != "test"
                or task["category"] not in CATEGORIES or example["category"] != task["category"]
                or oracle["expected_action"] != example["expected_action"]
                or not isinstance(task["family_id"], str) or not task["family_id"]):
            raise DataError("evaluation_task_binding")
        counts[domains[0], task["category"]] += 1
        if counts[domains[0], task["category"]] > 2:
            raise DataError("evaluation_domain_category_limit")
        model_input_from_example(example)
        LocalToolExecutor(registry, faults=task["faults"])
        seen.add(task["task_id"])
    expected = [t["task_id"] for t in bundle["tasks"] if t["category"] == "fault_recovery"]
    if bundle["recovery_task_ids"] != expected or len(expected) > 8:
        raise DataError("evaluation_recovery_subset")
    return bundle


def retain_tasks(bundle, retained_ids):
    result = copy.deepcopy(bundle)
    result["tasks"] = [t for t in result["tasks"] if t["task_id"] in retained_ids]
    result["recovery_task_ids"] = [t["task_id"] for t in result["tasks"]
                                   if t["category"] == "fault_recovery"]
    return validate_tasks(result)
