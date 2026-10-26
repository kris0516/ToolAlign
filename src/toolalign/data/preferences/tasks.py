"""Build bounded train tasks from privately authored recipes.

Prompts, truth, explicit constraints and CPU validation scripts are input data.
No formal training recipe or hidden-test answer is bundled in this module.
"""

from __future__ import annotations

import copy

from toolalign.contracts import canonical_hash, validate_record
from toolalign.data.common import DataError, read_json
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.model_io.format import encode_action, encode_json
from toolalign.tools import LocalToolRegistry
from toolalign.tools._json import parse_action

TASK_SCHEMA = "toolalign.preference-tasks.v1"
SOURCE = "toolalign-original-g4-train"
REVISION = "p05-g4-task-families.v1"
MAX_TASKS = 128


def read_authoring(path):
    value = read_json(path)
    if (value.get("schema_version") != "toolalign.preference-authoring.v1"
            or value.get("purpose") != "train-only-authored-recipes"
            or value.get("source") != SOURCE or value.get("revision") != REVISION):
        raise DataError("authoring_input_identity")
    return value["cases"]


def action(calls=(), *, value=None, kind="final"):
    if calls:
        return {
            "kind": "tool_calls", "content": "",
            "tool_calls": [
                {"call_id": f"c{i + 1}", "name": name, "arguments": args}
                for i, (name, args) in enumerate(calls)
            ],
        }
    return {"kind": kind, "tool_calls": [], "content": encode_json(value)}


def step(name, arguments, output, *, error=None):
    return {
        "name": name, "arguments": arguments,
        "status": "error" if error else "completed", "output": output,
        "error_code": error, "retryable": error == "injected_transient",
    }


def script(strategy, answer, *, separate=False):
    """Explicit CPU authoring check; never a model-generation or mining path."""
    responses = []
    if separate:
        for index, item in enumerate(strategy):
            call = action([(item["name"], item["arguments"])])
            call["tool_calls"][0]["call_id"] = f"c{index + 1}"
            responses.append(encode_action(call))
    elif strategy:
        responses.append(encode_action(action([(s["name"], s["arguments"]) for s in strategy])))
    responses.append(encode_action(action(value=answer["value"], kind=answer["kind"])))
    return responses


def _case(family, category, prompt, answers, strategies, *, separate=False, faults=None,
          explicit_calls=True):
    if explicit_calls:
        prompt += (" The answer content must be a JSON object with exactly the requested fields. "
                   "Use JSON numbers for quantities, booleans for predicates and arrays for lists.")
    answers = copy.deepcopy(answers)
    strategies = copy.deepcopy(strategies)
    positive = [script(s, answers[0], separate=separate) for s in strategies]
    # The counterexample preserves all successful tool calls and changes only
    # the final structured value. Callers may author separate wrong-object probes.
    negative = positive[0][:-1] + [encode_action(action(value={"wrong_answer": True}))]
    return {
        "family_id": family, "category": category, "prompt": prompt,
        "answers": answers, "strategies": strategies, "faults": faults or {},
        "positive_scripts": positive, "negative_script": negative,
        "strategy_scope": "enumerated_known_legal_strategies",
        # These generated prompts expressly constrain the calls and final fields.
        # Open-ended tasks must not opt into this closed request domain.
        "constraints": {
            "evidence": prompt, "explicit_calls": explicit_calls,
            "call_domain": list({canonical_hash({"name": s["name"], "arguments": s["arguments"]}):
                                 {"name": s["name"], "arguments": s["arguments"]}
                                 for strategy in strategies for s in strategy}.values()),
            "required_call_count": len(strategies[0]),
            "observation_dependencies": [[i - 1, i] for i in range(1, len(strategies[0]))]
            if separate else [],
            "closed_answer": True,
        },
    }


def prepare_tasks(cases, registry=None):
    registry = registry or LocalToolRegistry()
    if not 1 <= len(cases) <= MAX_TASKS:
        raise DataError("task_count_outside_1_128")
    tasks, authoring = [], {}
    for case in cases:
        identity = {k: case[k] for k in [
            "family_id", "category", "prompt", "answers", "strategies", "faults", "constraints",
        ]}
        source_hash = canonical_hash(identity)
        task_id = "g4-" + source_hash[:32]
        example = validate_record({
            "schema_version": "toolalign.example.v1", "example_id": task_id,
            "source": SOURCE, "source_revision": REVISION, "license_id": "MIT",
            "source_record_hash": source_hash, "group_id": "pending-group-audit",
            "split": "train", "category": case["category"],
            "messages": [{"role": "user", "content": case["prompt"],
                          "tool_calls": [], "tool_call_id": None}],
            "tools": registry.tools,
            "expected_action": parse_action(case["positive_scripts"][0][0]),
        }, "example")
        oracle = {
            "task_id": task_id, "group_id": example["group_id"], "split": "train",
            "expected_action": example["expected_action"],
            "oracle_payload": {"version": ORACLE_VERSION, "answers": case["answers"],
                               "strategies": case["strategies"]},
        }
        tasks.append({"task_id": task_id, "family_id": case["family_id"],
                      "group_id": example["group_id"], "category": case["category"],
                      "example": example, "oracle_task": oracle, "faults": case["faults"]})
        authoring[task_id] = copy.deepcopy(case)
    if len({task["task_id"] for task in tasks}) != len(tasks):
        raise DataError("duplicate_task_identity")
    return {"schema_version": TASK_SCHEMA, "purpose": "train-candidate-generation",
            "registry_hash": registry.registry_hash, "tasks": tasks}, authoring


def validate_tasks(bundle, registry=None):
    """Check the shared parent-process format without exposing oracle to ModelInput."""
    registry = registry or LocalToolRegistry()
    if (set(bundle) != {"schema_version", "purpose", "registry_hash", "tasks"}
            or bundle.get("schema_version") != TASK_SCHEMA
            or bundle.get("purpose") != "train-candidate-generation"
            or bundle.get("registry_hash") != registry.registry_hash
            or not 0 <= len(bundle.get("tasks", [])) <= MAX_TASKS):
        raise DataError("task_bundle_identity")
    seen = set()
    for task in bundle["tasks"]:
        if set(task) != {"task_id", "family_id", "group_id", "category", "example", "oracle_task", "faults"}:
            raise DataError("task_fields")
        example = validate_record(task["example"], "example")
        oracle = task["oracle_task"]
        ident = task["task_id"]
        if (ident in seen or example["example_id"] != ident or oracle["task_id"] != ident
                or task["group_id"] != example["group_id"]
                or task["group_id"] != oracle["group_id"]
                or example["split"] != "train" or oracle["split"] != "train"
                or example["source"] != SOURCE or example["source_revision"] != REVISION
                or task["category"] != example["category"]
                or canonical_hash(example["tools"]) != canonical_hash(registry.tools)
                or canonical_hash(oracle["expected_action"]) != canonical_hash(example["expected_action"])
                or not isinstance(task["family_id"], str) or not task["family_id"]):
            raise DataError("task_example_oracle_binding")
        seen.add(ident)
    return bundle
