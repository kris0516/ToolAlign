"""Build the fixed L1 consumer format from private, explicitly authored recipes."""

from __future__ import annotations

import copy
from collections import Counter

from toolalign.contracts import canonical_hash, model_input_from_example, validate_record
from toolalign.contracts.interfaces import OracleTask
from toolalign.data.common import DataError
from toolalign.evaluation.oracles import OBSERVATION_ORACLE_VERSION, validate_observation_task
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.tools import LocalToolExecutor, LocalToolRegistry
from toolalign.tools._json import parse_action
from toolalign.tools.constraints_catalog import DOMAIN_TOOLS as CONSTRAINT_DOMAIN_TOOLS
from toolalign.tools.constraints_catalog import VERSION as CONSTRAINT_CATALOG
from toolalign.tools.heldout_catalog import DOMAIN_TOOLS

CATALOG = "heldout-devops.v1"
TASK_SCHEMA = "toolalign.evaluation-tasks.v1"
SOURCE = "toolalign-original-g5-heldout"
REVISION = "p06-g5-corpus.v1"
CONSTRAINT_REVISION = "p06-g5-corpus.v2"
CATEGORIES = (
    "single_tool", "multi_step", "tool_confusion", "no_tool",
    "clarify_or_refuse", "fault_recovery",
)


def catalog_profile(catalog):
    if catalog == CATALOG:
        return DOMAIN_TOOLS, REVISION, 48
    if catalog == CONSTRAINT_CATALOG:
        return CONSTRAINT_DOMAIN_TOOLS, CONSTRAINT_REVISION, 28
    raise DataError("evaluation_catalog")


def prepare_tasks(cases, *, catalog=CATALOG):
    """Answers, scripts and constraints are author input, not generated truth."""
    domain_tools, revision, maximum = catalog_profile(catalog)
    if not 1 <= len(cases) <= maximum:
        raise DataError("evaluation_task_count")
    counts, tasks, authoring = Counter(), [], {}
    for case in cases:
        domain, category = case["domain"], case["category"]
        if domain not in domain_tools or category not in CATEGORIES:
            raise DataError("evaluation_domain_or_category")
        counts[domain, category] += 1
        limit = 2 if catalog == CATALOG or category == "fault_recovery" else 1
        if counts[domain, category] > limit:
            raise DataError("evaluation_domain_category_limit")
        if not case["positive_scripts"] or not case["negative_scripts"]:
            raise DataError("evaluation_authoring_scripts_required")
        identity = {key: case[key] for key in (
            "domain", "family_id", "category", "prompt", "answers", "strategies", "faults",
        )}
        payload = {"version": ORACLE_VERSION, "answers": case["answers"],
                   "strategies": case["strategies"]}
        if catalog == CONSTRAINT_CATALOG:
            identity.update(catalog=catalog, after_observation=case.get("after_observation"))
            payload.update(version=OBSERVATION_ORACLE_VERSION,
                           after_observation=case.get("after_observation"))
        source_hash = canonical_hash(identity)
        task_id = "g5-" + source_hash[:32]
        registry = LocalToolRegistry(domain_tools[domain], catalog_id=catalog)
        example = validate_record({
            "schema_version": "toolalign.example.v1", "example_id": task_id,
            "source": SOURCE, "source_revision": revision, "license_id": "MIT",
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
                "oracle_payload": payload,
            },
            "faults": case["faults"], "tool_names": sorted(domain_tools[domain]),
        })
        authoring[task_id] = copy.deepcopy(case)
    bundle = {"schema_version": TASK_SCHEMA, "purpose": "heldout-model-evaluation",
              "catalog": catalog,
              "registry_hash": LocalToolRegistry(catalog_id=catalog).registry_hash,
              "tasks": tasks,
              "recovery_task_ids": [t["task_id"] for t in tasks
                                    if t["category"] == "fault_recovery"]}
    validate_tasks(bundle)
    return bundle, authoring


def validate_tasks(bundle):
    """Mirror the agreed storage identity; model projection stays messages/tools."""
    catalog = bundle.get("catalog")
    domain_tools, revision, maximum = catalog_profile(catalog)
    if (set(bundle) != {"schema_version", "purpose", "catalog", "registry_hash", "tasks",
                       "recovery_task_ids"}
            or bundle["schema_version"] != TASK_SCHEMA
            or bundle["purpose"] != "heldout-model-evaluation"
            or bundle["registry_hash"] != LocalToolRegistry(catalog_id=catalog).registry_hash
            or not 0 <= len(bundle["tasks"]) <= maximum):
        raise DataError("evaluation_bundle_identity")
    seen, counts = set(), Counter()
    for task in bundle["tasks"]:
        if set(task) != {"task_id", "family_id", "group_id", "category", "example", "oracle_task",
                         "faults", "tool_names"}:
            raise DataError("evaluation_task_fields")
        example, oracle = validate_record(task["example"], "example"), task["oracle_task"]
        registry = LocalToolRegistry(task["tool_names"], catalog_id=catalog)
        domains = [name for name, tools in domain_tools.items()
                   if set(tools) == set(task["tool_names"])]
        if (len(domains) != 1 or example["tools"] != registry.tools
                or example["source"] != SOURCE or example["source_revision"] != revision
                or task["task_id"] in seen
                or task["task_id"] != example["example_id"] or task["task_id"] != oracle["task_id"]
                or task["group_id"] != example["group_id"] or task["group_id"] != oracle["group_id"]
                or example["split"] != "test" or oracle["split"] != "test"
                or task["category"] not in CATEGORIES or example["category"] != task["category"]
                or oracle["expected_action"] != example["expected_action"]
                or not isinstance(task["family_id"], str) or not task["family_id"]):
            raise DataError("evaluation_task_binding")
        counts[domains[0], task["category"]] += 1
        limit = 2 if catalog == CATALOG or task["category"] == "fault_recovery" else 1
        if counts[domains[0], task["category"]] > limit:
            raise DataError("evaluation_domain_category_limit")
        if catalog == CONSTRAINT_CATALOG:
            try:
                validate_observation_task(OracleTask(**oracle))
            except (TypeError, ValueError) as error:
                raise DataError("evaluation_observation_truth") from error
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
