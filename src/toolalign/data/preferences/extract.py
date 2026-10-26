"""Conservative first-divergence decisions, bound to actual complete requests."""

from __future__ import annotations

import copy
from collections import Counter, defaultdict
from dataclasses import asdict
from itertools import combinations

from toolalign.contracts import (
    ContractError,
    canonical_hash,
    model_input_from_example,
    validate_record,
    validate_tool_arguments,
)
from toolalign.contracts.interfaces import OracleTask
from toolalign.data.common import DataError, loads
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION, SemanticOracle, equivalent
from toolalign.model_io import validate_model_input
from toolalign.tools import LocalToolRegistry
from toolalign.tools._json import encode, parse_action, validate_part
from toolalign.tools.scripted import SCRIPTED_IDENTITY

from .tasks import validate_tasks

PARAMETERS = ("seed", "temperature", "top_p", "max_new_tokens")
ERROR_CLASSES = ("tool_confusion", "argument_semantics", "unnecessary_tool",
                 "extra_call", "premature_termination", "final_semantics")
SFT_REVISION = "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
SFT_ADAPTER_HASH = "973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed"


def validate_generation_model(model_identity, *, synthetic):
    validate_part(model_identity, "model_identity")
    if type(synthetic) is not bool:
        raise DataError("synthetic_mode_must_be_boolean")
    if not synthetic and (model_identity == SCRIPTED_IDENTITY
                          or "scripted" in model_identity["quantization"]):
        raise DataError("scripted_is_not_formal")
    if not synthetic and (model_identity["model_id"] != "Qwen/Qwen3-1.7B"
                          or model_identity["model_revision"] != SFT_REVISION
                          or model_identity["adapter_hash"] != SFT_ADAPTER_HASH):
        raise DataError("not_selected_g3_sft")


def validate_authoring(bundle, authoring):
    for task in bundle["tasks"]:
        case = authoring[task["task_id"]]
        identity = {k: case[k] for k in ("family_id", "category", "prompt", "answers",
                                       "strategies", "faults", "constraints")}
        digest = canonical_hash(identity)
        if (task["task_id"] != "g4-" + digest[:32]
                or task["example"]["source_record_hash"] != digest
                or task["family_id"] != case["family_id"] or task["category"] != case["category"]
                or case["prompt"] != task["example"]["messages"][0]["content"]
                or case["constraints"]["evidence"] != case["prompt"]
                or not equivalent(task["faults"], case["faults"])
                or not equivalent(task["oracle_task"]["oracle_payload"],
                                  {"version": ORACLE_VERSION, "answers": case["answers"],
                                   "strategies": case["strategies"]})):
            raise DataError("authoring_task_identity")


def freeze_plan(bundle, model_identity, candidates, *, synthetic=False):
    """P05 sidecar frozen BEFORE execution: IDs and both candidates' sampling facts.

    candidates: task_id -> [{candidate_id, generation_parameters}, ...].  The
    generator's own started/terminal journal remains authoritative for execution.
    """
    validate_tasks(bundle)
    validate_generation_model(model_identity, synthetic=synthetic)
    if set(candidates) != {task["task_id"] for task in bundle["tasks"]}:
        raise DataError("plan_task_set")
    for rows in candidates.values():
        if (not 1 <= len(rows) <= 4 or len({r["candidate_id"] for r in rows}) != len(rows)
                or any(not isinstance(r["candidate_id"], str) or not r["candidate_id"] for r in rows)):
            raise DataError("plan_candidate_ids")
        for row in rows:
            params = row["generation_parameters"]
            if (set(params) != set(PARAMETERS) or type(params["seed"]) is not int
                    or type(params["max_new_tokens"]) is not int
                    or params["max_new_tokens"] != 256
                    or type(params["temperature"]) not in (float, int) or params["temperature"] < 0
                    or type(params["top_p"]) not in (float, int) or not 0 < params["top_p"] <= 1):
                raise DataError("plan_generation_parameters")
    return {"schema_version": "toolalign.preference-plan.v1", "tasks_hash": canonical_hash(bundle),
            "synthetic": synthetic, "model_identity": copy.deepcopy(model_identity),
            "candidates": {k: sorted(copy.deepcopy(v), key=lambda r: r["candidate_id"])
                           for k, v in sorted(candidates.items())},
            "pair_order": "lexicographic_candidate_id_combinations"}


def _call_value(call):
    return {"name": call["name"], "arguments": call["arguments"]}


def semantic_action(action):
    if action["kind"] == "tool_calls":
        return {"kind": "tool_calls", "calls": [_call_value(c) for c in action["tool_calls"]]}
    return {"kind": action["kind"], "value": loads(action["content"])}


def verify_candidate(task, candidate, planned, model, registry):
    """Reconstruct each request from preceding events, never from a normalized prefix."""
    if candidate.get("status") in {"started", "interrupted"}:
        raise DataError("interrupted")
    if (candidate["task_id"] != task["task_id"]
            or candidate["candidate_id"] != planned["candidate_id"]
            or canonical_hash(candidate["model_identity"]) != canonical_hash(model)
            or canonical_hash(candidate["generation_parameters"])
            != canonical_hash(planned["generation_parameters"])):
        raise DataError("candidate_identity")
    result = candidate["harness_result"]
    trace = [validate_record(e, "trace") for e in result["trace"]]
    if not trace or trace[-1]["event"] != "finalized":
        raise DataError("nonsemantic_termination")
    decisions, inputs = result["decisions"], candidate["decision_inputs"]
    if not 1 <= len(decisions) == len(inputs) <= 3 or not result["token_accounting_complete"]:
        raise DataError("decision_accounting")
    prefix = model_input_from_example(task["example"])
    provenance = result["provenance"]
    if (provenance["model_input_hash"] != canonical_hash(prefix)
            or provenance["oracle_payload_hash"] != canonical_hash(task["oracle_task"]["oracle_payload"])
            or provenance["registry_hash"] != registry.registry_hash
            or canonical_hash(result["registry_manifest"]) != registry.registry_hash
            or canonical_hash({k: provenance["generation_config"][k] for k in PARAMETERS})
            != canonical_hash(candidate["generation_parameters"])
            or provenance["generation_config"].get("enable_thinking") is not False):
        raise DataError("harness_provenance")
    for index, event in enumerate(trace):
        if (event["event_index"] != index or event["model"] != model
                or any(event[k] != trace[0][k] for k in ("trace_id", "request_id", "deadline_utc"))):
            raise DataError("mixed_trace_identity")
    if [e["event"] for e in trace[:2]] != ["received", "validated"]:
        raise DataError("trace_start")
    position, observed, call_decisions, before, actions = 2, [], [], [], []
    for index, (decision, actual_input) in enumerate(zip(decisions, inputs, strict=True)):
        validate_model_input(actual_input)
        if (canonical_hash(actual_input) != canonical_hash(prefix)
                or decision["model_input_hash"] != canonical_hash(actual_input)):
            raise DataError("actual_prefix_mismatch")
        if (decision["raw_parse_failure"] is not None or decision["finish_reason"] != "stop"
                or type(decision["output_tokens"]) is not int
                or not 0 <= decision["output_tokens"] <= planned["generation_parameters"]["max_new_tokens"]):
            raise DataError("format_length_or_backend_failure")
        action = parse_action(decision["raw_text"])
        if canonical_hash(action) != canonical_hash(decision["raw_action"]):
            raise DataError("raw_action_binding")
        # An invalid inner JSON answer is a format failure, not a semantic negative.
        semantic_action(action)
        actions.append(action)
        before.append(copy.deepcopy(observed))
        if [e["event"] for e in trace[position:position + 2]] != ["generating", "parsing"]:
            raise DataError("trace_decision_order")
        position += 2
        if action["kind"] != "tool_calls":
            if index != len(decisions) - 1 or canonical_hash(action) != canonical_hash(result["final_result"]):
                raise DataError("final_action_binding")
            continue
        observations = []
        for call in action["tool_calls"]:
            validate_tool_arguments(registry.spec(call["name"]), call["arguments"])
            events = trace[position:position + 2]
            if (len(events) != 2 or [e["event"] for e in events] != ["tool_execution", "observing"]
                    or any(e["tool_call"] != call for e in events)):
                raise DataError("trace_call_order")
            observation = events[1]["tool_result"]
            if (observation["call_id"] != call["call_id"]
                    or (observation["status"] != "completed" and not observation["retryable"])):
                raise DataError("observation_binding_or_infrastructure")
            observed.append({**_call_value(call), **{k: observation[k]
                            for k in ("status", "output", "error_code", "retryable")}})
            call_decisions.append(index)
            observations.append({"role": "tool", "content": encode(observation).decode(),
                                 "tool_calls": [], "tool_call_id": call["call_id"]})
            position += 2
        prefix["messages"].append({"role": "assistant", "content": action["content"],
                                   "tool_calls": action["tool_calls"], "tool_call_id": None})
        prefix["messages"].extend(observations)
    if position != len(trace) - 1 or actions[-1]["kind"] == "tool_calls":
        raise DataError("unconsumed_trace")
    score = asdict(SemanticOracle().score(OracleTask(**task["oracle_task"]), trace, result["final_result"]))
    if score != result["score"] or score != trace[-1]["task_outcome"]:
        raise DataError("oracle_score_binding")
    if score["outcome"] not in ("success", "failure"):
        raise DataError("unknown_oracle")
    return {"candidate": candidate, "actions": actions, "before": before,
            "call_decisions": call_decisions, "outcome": score["outcome"]}


def decision_verdict(case, observed, action):
    remaining = [s[len(observed):] for s in case["strategies"]
                 if equivalent(observed, s[:len(observed)]) and len(s) >= len(observed)]
    if not remaining:
        return "unknown", "invalid_prior_semantics"
    constraints = case["constraints"]
    if action["kind"] == "tool_calls":
        calls = [_call_value(c) for c in action["tool_calls"]]
        if any(len(s) >= len(calls) and equivalent(calls, [_call_value(c) for c in s[:len(calls)]])
               for s in remaining):
            return "legal", "known_permitted_continuation"
        if constraints["explicit_calls"]:
            domain = constraints["call_domain"]
            if not domain:
                return "illegal", "unnecessary_tool"
            for call in calls:
                if not any(call["name"] == c["name"] for c in domain):
                    return "illegal", "tool_confusion"
                if not any(equivalent(call, c) for c in domain):
                    return "illegal", "argument_semantics"
            if len(observed) + len(calls) > constraints["required_call_count"]:
                return "illegal", "extra_call"
        return "unknown", "unenumerated_not_proven_wrong"
    answer = semantic_action(action)
    known_answer = any(equivalent(answer, a) for a in case["answers"])
    if known_answer and any(not s for s in remaining):
        return "legal", "known_permitted_answer"
    if constraints["closed_answer"] and not known_answer:
        return "illegal", "final_semantics"
    if constraints["explicit_calls"] and len(observed) < constraints["required_call_count"]:
        return "illegal", "premature_termination"
    return "unknown", "unenumerated_not_proven_wrong"


def compare_pair(case, left, right):
    if {left["outcome"], right["outcome"]} != {"success", "failure"}:
        return None, "same_outcome"
    chosen, rejected = (left, right) if left["outcome"] == "success" else (right, left)
    for parent, dependent in case["constraints"]["observation_dependencies"]:
        positions = chosen["call_decisions"]
        if dependent >= len(positions) or positions[parent] >= positions[dependent]:
            return None, "chosen_dependency_not_observed"
    for index, (a, b) in enumerate(zip(chosen["actions"], rejected["actions"])):
        if canonical_hash(chosen["candidate"]["decision_inputs"][index]) != canonical_hash(
                rejected["candidate"]["decision_inputs"][index]):
            return None, "different_actual_prefix"
        if equivalent(semantic_action(a), semantic_action(b)):
            continue
        good, _ = decision_verdict(case, chosen["before"][index], a)
        bad, reason = decision_verdict(case, rejected["before"][index], b)
        if good == "legal" and bad == "illegal":
            return (chosen, rejected, index, reason), "selected"
        return None, "legal_alternative_tie" if good == bad == "legal" else "unknown_current_semantics"
    return None, "equivalent_decisions"


def extract_preferences(bundle, authoring, plan, candidates):
    registry = LocalToolRegistry()
    validate_tasks(bundle, registry)
    validate_authoring(bundle, authoring)
    expected_plan = freeze_plan(bundle, plan["model_identity"], plan["candidates"],
                                synthetic=plan["synthetic"])
    if canonical_hash(plan) != canonical_hash(expected_plan):
        raise DataError("plan_binding")
    rows = list(candidates)
    tasks = {t["task_id"]: t for t in bundle["tasks"]}
    planned = {(task, c["candidate_id"]): c for task, values in plan["candidates"].items() for c in values}
    counts = Counter((r.get("task_id"), r.get("candidate_id")) for r in rows)
    verified, dispositions = defaultdict(list), []
    for row in rows:
        key = (row.get("task_id"), row.get("candidate_id"))
        reason, item = "eligible", None
        try:
            if key not in planned:
                raise DataError("unplanned_candidate")
            if counts[key] != 1:
                raise DataError("duplicate_candidate")
            if not plan["synthetic"] and row.get("synthetic"):
                raise DataError("synthetic_candidate_is_not_formal")
            item = verify_candidate(tasks[key[0]], row, planned[key], plan["model_identity"], registry)
            verified[key[0]].append(item)
        except (ContractError, ValueError, KeyError, TypeError, IndexError) as error:
            reason = str(error) if isinstance(error, DataError) else "invalid_candidate_record"
        dispositions.append({"kind": "candidate", "task_id": key[0], "candidate_id": key[1],
                             "candidate_hash": canonical_hash(row), "status": row.get("status"),
                             "disposition": reason, "outcome": item["outcome"] if item else "unknown"})
    missing = sorted(set(planned) - set(counts))
    for task, candidate_id in missing:
        dispositions.append({"kind": "candidate", "task_id": task, "candidate_id": candidate_id,
                             "disposition": "missing_terminal_record", "outcome": "unknown"})
    preferences, lineage = [], []
    for task_id, values in sorted(verified.items()):
        selected = False
        fixed_order = {pair: index for index, pair in enumerate(combinations(
            [row["candidate_id"] for row in plan["candidates"][task_id]], 2))}
        for left, right in combinations(sorted(values, key=lambda v: v["candidate"]["candidate_id"]), 2):
            ids = (left["candidate"]["candidate_id"], right["candidate"]["candidate_id"])
            order = fixed_order[ids]
            pair, reason = compare_pair(authoring[task_id], left, right)
            if pair and selected:
                reason = "valid_pair_after_first"
            dispositions.append({"kind": "pair", "task_id": task_id,
                                 "candidate_ids": list(ids), "pair_order": order,
                                 "disposition": reason})
            if not pair or selected:
                continue
            chosen, rejected, index, error_class = pair
            c, r = chosen["candidate"], rejected["candidate"]
            prefix = c["decision_inputs"][index]
            trace_hashes = {name: canonical_hash(value["harness_result"]["trace"])
                            for name, value in (("chosen", c), ("rejected", r))}
            identity = {"task_id": task_id, "chosen": c["candidate_id"], "rejected": r["candidate_id"],
                        "decision_index": index, "prompt_hash": canonical_hash(prefix),
                        "trace_hashes": trace_hashes}
            preference_id = "g4-pref-" + canonical_hash(identity)[:32]
            record = {"schema_version": "toolalign.preference.v1", "preference_id": preference_id,
                      "source_task_id": task_id, "group_id": tasks[task_id]["group_id"], "split": "train",
                      **copy.deepcopy(prefix), "prompt_hash": canonical_hash(prefix),
                      "chosen": c["harness_result"]["decisions"][index]["raw_text"],
                      "rejected": r["harness_result"]["decisions"][index]["raw_text"],
                      "chosen_validation": {"outcome": "success", "reason": "Complete semantic success and legal current decision",
                                            "trace_hash": trace_hashes["chosen"]},
                      "rejected_validation": {"outcome": "failure", "reason": error_class,
                                              "trace_hash": trace_hashes["rejected"]},
                      "preference_reason": error_class, "generation_model": copy.deepcopy(plan["model_identity"]),
                      "generation_parameters": copy.deepcopy(c["generation_parameters"]),
                      "oracle_version": ORACLE_VERSION}
            preferences.append(validate_record(record, "preference"))
            lineage.append({"preference_id": preference_id, **identity, "error_class": error_class,
                            "pair_order": order, "plan_hash": canonical_hash(plan), "synthetic": plan["synthetic"],
                            **{name: {"candidate_id": value["candidate_id"], "candidate_hash": canonical_hash(value),
                                      "decision_index": index, "generation_parameters": value["generation_parameters"]}
                               for name, value in (("chosen", c), ("rejected", r))}})
            selected = True
    summary = {"schema_version": "toolalign.preference-extraction.v1", "synthetic": plan["synthetic"],
               "training_authorized": False, "q1_review": "NOT_RUN", "plan_hash": canonical_hash(plan),
               "planned_candidates": len(planned), "observed_candidate_rows": len(rows),
               "missing_candidate_records": len(missing), "candidate_denominator": len(set(planned) | set(counts)),
               "preferences": len(preferences), "tasks": len(tasks),
               "dispositions": dict(Counter(d["disposition"] for d in dispositions))}
    return {"preferences": preferences, "lineage": lineage, "dispositions": dispositions, "summary": summary}
