"""Original synthetic CPU cases; no learned-model or held-out quality claims."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from toolalign.contracts import ContractError, canonical_hash
from toolalign.data.common import DataError, file_hash, read_json, write_json
from toolalign.data.preferences.__main__ import load_package, main
from toolalign.data.preferences.audit import audit_groups, task_keys
from toolalign.data.preferences.extract import (
    decision_verdict,
    extract_preferences,
    freeze_plan,
)
from toolalign.data.preferences.review import apply_review, freeze_review, review_html
from toolalign.data.preferences.synthetic import run_script
from toolalign.data.preferences.tasks import (
    REVISION,
    SOURCE,
    _case,
    action,
    prepare_tasks,
    step,
    validate_tasks,
)
from toolalign.model_io import encode_action
from toolalign.tools import catalog
from toolalign.tools._json import parse_action
from toolalign.tools.scripted import SCRIPTED_IDENTITY

DEV = Path(__file__).parents[2] / "fixtures/tools/development.json"


def small_cases():
    """Five public CPU fixtures, distinct from the private formal task recipes."""
    def report(resource):
        return step("query_build_report", {"report_id": resource},
                    {"report_id": resource, **catalog.REPORTS[resource]})

    simple = _case("report-health", "test", "Synthetic fixture: query atlas-100 once with no other "
                   "calls and return passed_count.", [{"kind": "final", "value": {"passed_count": 8}}],
                   [[report("atlas-100")]])
    wrong = parse_action(simple["negative_script"][0])
    wrong["tool_calls"][0]["arguments"]["report_id"] = "beacon-110"
    simple["negative_script"] = [encode_action(wrong), simple["positive_scripts"][0][-1]]
    strategies = []
    for operation, value in [("sum", 2400), ("mean", 1200)]:
        args = {"resource_id": "atlas-runs", "date": "2026-09-01", "field": "duration_ms", "operation": operation}
        strategies.append([step("aggregate_run_records", args, {**args, "value": value, "count": 2})])
    aggregate = _case("run-failures", "test", "Synthetic fixture: aggregate duration_ms of atlas-runs "
                      "on 2026-09-01 once, using sum or mean with count, no other calls. Return duration_total_ms.",
                      [{"kind": "final", "value": {"duration_total_ms": 2400}}], strategies)
    no_tool = _case("supplied-health", "no_tool", "Synthetic fixture: no tools; add 5 and 7 and return sum.",
                    [{"kind": "final", "value": {"sum": 12}}], [[]])
    document = step("lookup_version_document", {"resource_id": "atlas-1.1"},
                    {"resource_id": "atlas-1.1", **catalog.DOCUMENTS["atlas-1.1"]})
    conversion = {"value": 1200, "from_unit": "ms", "to_unit": "s"}
    dependent = _case("timeout-seconds", "test", "Synthetic fixture: read atlas-1.1 document then convert "
                      "its timeout_ms to s, exactly these two calls in order after reading the observation. "
                      "Return milliseconds and seconds.",
                      [{"kind": "final", "value": {"milliseconds": 1200, "seconds": 1.2}}],
                      [[document, step("convert_numeric_units", conversion, {**conversion, "converted_value": 1.2})]],
                      separate=True)
    transient = step("query_build_report", {"report_id": "beacon-110"}, None, error="injected_transient")
    recovery = _case("report-recovery", "test", "Synthetic fixture: query beacon-110 and retry the same "
                     "call once after its temporary retryable error; no other calls. Return passed_count.",
                     [{"kind": "final", "value": {"passed_count": 9}}], [[transient, report("beacon-110")]],
                     separate=True, faults={"query_build_report": ["transient", None]})
    return [simple, aggregate, no_tool, dependent, recovery]


def authored(family):
    case = next(case for case in small_cases() if case["family_id"] == family)
    bundle, authoring = prepare_tasks([case])
    bundle, _ = audit_groups(bundle, [], [])
    return bundle, authoring, case


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    root = tmp_path_factory.mktemp("preference-executions")
    cache = {}

    def execute(family, scripts=None):
        bundle, authoring, case = authored(family)
        scripts = scripts or [case["positive_scripts"][0], case["negative_script"]]
        key = canonical_hash([family, scripts])
        if key not in cache:
            rows = [run_script(bundle["tasks"][0], values, root / key / str(index), f"candidate-{index}")
                    for index, values in enumerate(scripts)]
            plan = freeze_plan(bundle, SCRIPTED_IDENTITY, {bundle["tasks"][0]["task_id"]: [
                {"candidate_id": row["candidate_id"], "generation_parameters": row["generation_parameters"]}
                for row in rows]}, synthetic=True)
            cache[key] = (bundle, authoring, plan, rows)
        return copy.deepcopy(cache[key])

    return execute


def test_task_scope_counts_and_public_development_identity():
    bundle, authoring = prepare_tasks(small_cases())
    bundle, audit = audit_groups(bundle, [], read_json(DEV)["cases"])
    validate_tasks(bundle)
    assert len(bundle["tasks"]) == 5
    assert len(authoring) == 5
    assert len({task["family_id"] for task in bundle["tasks"]}) == 5
    assert len({task["group_id"] for task in bundle["tasks"]}) == 1
    assert len(audit["development_overlap"]) == 50
    assert all(row["shared_registry_schemas"] == 6 and not row["clone"]
               for row in audit["development_overlap"])
    assert audit["schema_isolation_from_development"] is False


@pytest.mark.parametrize("split", ["train", "validation", "test", "ood_test"])
def test_unused_prompt_tool_bridges_quarantine_whole_new_component(split):
    bundle, _ = prepare_tasks(small_cases())
    original = copy.deepcopy(bundle)
    tool_key = next(key for key in sorted(task_keys(bundle["tasks"][0])) if key.startswith("schema:"))
    rows = [{"group_id": "frozen-old-group", "group_keys": [tool_key], "split": split}]
    saved = copy.deepcopy(rows)
    kept, audit = audit_groups(bundle, rows, [])
    assert rows == saved and bundle == original
    assert len(kept["tasks"]) == (5 if split == "train" else 0)
    assert len(audit["components"]) == 1
    assert any(t["category"] == "no_tool" for t in bundle["tasks"])


def test_renamed_development_task_is_excluded():
    dev = read_json(DEV)["cases"][0]
    case = _case("new-name", "test", "Paraphrased development prompt", dev["answers"], dev["strategies"])
    bundle, _ = prepare_tasks([case])
    kept, audit = audit_groups(bundle, [], [dev])
    assert not kept["tasks"]
    assert audit["dispositions"][0]["reason"] == "public_development_clone"


def test_build_cli_requires_private_authoring_and_preserves_input_binding(tmp_path):
    private = tmp_path / ".toolalign-local"
    private.mkdir()
    recipes = private / "recipes.json"
    write_json(recipes, {"schema_version": "toolalign.preference-authoring.v1",
                        "purpose": "train-only-authored-recipes", "source": SOURCE,
                        "revision": REVISION, "cases": small_cases()})
    for name in ("assignments.jsonl", "tool-lineage.jsonl"):
        (private / name).write_text("")
    p02 = private / "p02.json"
    write_json(p02, {"artifacts": {name: file_hash(private / name)
                                   for name in ("assignments.jsonl", "tool-lineage.jsonl")}})
    output = private / "package"
    argv = ["build", "--authoring", str(recipes), "--p02-manifest", str(p02),
            "--development", str(DEV), "--output", str(output)]
    assert main(argv) == 0
    bundle, _ = load_package(output)
    assert len(bundle["tasks"]) == 5
    assert read_json(output / "manifest.json")["authoring_input_sha256"] == file_hash(recipes)
    argv[-1] = str(tmp_path / "public-output")
    with pytest.raises(DataError, match="output_must_be_private"):
        main(argv)


@pytest.mark.parametrize("split", ["validation", "test", "ood_test"])
def test_nontrain_tasks_are_rejected(split):
    bundle, _, _ = authored("supplied-health")
    bundle["tasks"][0]["example"]["split"] = split
    with pytest.raises((DataError, ContractError)):
        validate_tasks(bundle)


def test_wrong_object_with_completed_tools_is_semantic_negative(run):
    values = run("report-health")
    bundle, authoring, plan, rows = values
    assert all(e["tool_result"]["status"] == "completed" for e in rows[1]["harness_result"]["trace"]
               if e["event"] == "observing")
    result = extract_preferences(*values)
    assert result["lineage"][0]["decision_index"] == 0
    assert result["lineage"][0]["error_class"] == "argument_semantics"
    assert result["preferences"][0]["chosen"] == rows[0]["harness_result"]["decisions"][0]["raw_text"]
    assert result["summary"]["synthetic"] and not result["summary"]["training_authorized"]


def test_correct_first_call_wrong_later_answer_pairs_only_at_final(run):
    _, _, case = authored("report-health")
    negative = case["positive_scripts"][0][:-1] + [encode_action(action(value={"total_tests": 999, "all_passed": True}))]
    values = run("report-health", [case["positive_scripts"][0], negative])
    result = extract_preferences(*values)
    assert len(result["preferences"]) == 1
    assert result["lineage"][0]["decision_index"] == 1
    assert result["lineage"][0]["error_class"] == "final_semantics"
    assert result["preferences"][0]["messages"][-1]["role"] == "tool"


def test_valid_alternative_first_call_never_becomes_negative_for_later_failure(run):
    _, _, case = authored("run-failures")
    negative = case["positive_scripts"][1][:-1] + [encode_action(action(value={"wrong": 1}))]
    result = extract_preferences(*run("run-failures", [case["positive_scripts"][0], negative]))
    assert not result["preferences"]
    assert result["dispositions"][-1]["disposition"] == "legal_alternative_tie"


def test_key_order_whitespace_and_call_ids_are_not_a_preference(run):
    _, _, case = authored("report-health")
    alternative = [json.dumps(parse_action(raw), indent=2, sort_keys=False) for raw in case["positive_scripts"][0]]
    a = parse_action(alternative[0])
    a["tool_calls"][0]["call_id"] = "renamed"
    alternative[0] = json.dumps(a, indent=2)
    result = extract_preferences(*run("report-health", [case["positive_scripts"][0], alternative]))
    assert not result["preferences"]
    assert result["dispositions"][-1]["disposition"] == "same_outcome"


def test_different_call_ids_do_not_manufacture_shared_later_prefix(run):
    _, _, case = authored("report-health")
    wrong = copy.deepcopy(case["positive_scripts"][0])
    a = parse_action(wrong[0])
    a["tool_calls"][0]["call_id"] = "renamed"
    wrong[0] = encode_action(a)
    wrong[-1] = encode_action(action(value={"wrong": True}))
    result = extract_preferences(*run("report-health", [case["positive_scripts"][0], wrong]))
    assert not result["preferences"]
    assert result["dispositions"][-1]["disposition"] == "different_actual_prefix"


def test_no_tool_unnecessary_call_is_attributed(run):
    _, _, case = authored("supplied-health")
    wrong = [encode_action(action([("query_build_report", {"report_id": "atlas-100"})])),
             case["positive_scripts"][0][-1]]
    result = extract_preferences(*run("supplied-health", [case["positive_scripts"][0], wrong]))
    assert result["lineage"][0]["error_class"] == "unnecessary_tool"


def test_shared_prefix_retry_wrong_report_is_attributed(run):
    _, _, case = authored("report-recovery")
    wrong = copy.deepcopy(case["positive_scripts"][0])
    action2 = parse_action(wrong[1])
    action2["tool_calls"][0]["arguments"]["report_id"] = "atlas-100"
    wrong[1] = encode_action(action2)
    result = extract_preferences(*run("report-recovery", [case["positive_scripts"][0], wrong]))
    assert result["lineage"][0]["decision_index"] == 1
    assert result["lineage"][0]["error_class"] == "argument_semantics"


def test_same_decision_dependency_is_not_success_evidence(run):
    _, _, case = authored("timeout-seconds")
    a, b = (parse_action(raw) for raw in case["positive_scripts"][0][:2])
    a["tool_calls"].extend(b["tool_calls"])
    batched = [encode_action(a), case["positive_scripts"][0][-1]]
    values = run("timeout-seconds", [batched, case["negative_script"]])
    assert values[3][0]["harness_result"]["score"]["outcome"] == "success"
    result = extract_preferences(*values)
    assert not result["preferences"]
    assert result["dispositions"][-1]["disposition"] == "chosen_dependency_not_observed"


def test_unenumerated_legal_conversion_is_unknown_not_negative():
    dev = read_json(DEV)["cases"][0]
    case = _case("open-document", "test", dev["prompt"], dev["answers"], dev["strategies"], explicit_calls=False)
    case["constraints"]["closed_answer"] = False
    observed = dev["strategies"][0]
    legal_minutes = action([("convert_numeric_units", {"value": 1200, "from_unit": "ms", "to_unit": "min"})])
    assert decision_verdict(case, observed, legal_minutes) == ("unknown", "unenumerated_not_proven_wrong")
    minutes_answer = copy.deepcopy(dev["answers"][0]["value"])
    minutes_answer["timeout"] = {"value": 0.02, "unit": "min"}
    assert decision_verdict(case, observed, action(value=minutes_answer))[0] == "unknown"


@pytest.mark.parametrize("mutation,reason", [
    ("future_input", "actual_prefix_mismatch"),
    ("mixed_trace", "mixed_trace_identity"),
    ("raw_action", "raw_action_binding"),
    ("oracle_leak", "invalid_candidate_record"),
    ("model", "candidate_identity"),
    ("seed", "candidate_identity"),
    ("length", "format_length_or_backend_failure"),
    ("interrupted", "interrupted"),
])
def test_unusable_candidates_remain_in_denominator(run, mutation, reason):
    bundle, authoring, plan, rows = run("report-health")
    candidate = rows[1]
    if mutation == "future_input":
        candidate["decision_inputs"][0] = copy.deepcopy(candidate["decision_inputs"][1])
        candidate["harness_result"]["decisions"][0]["model_input_hash"] = canonical_hash(candidate["decision_inputs"][0])
    elif mutation == "mixed_trace":
        candidate["harness_result"]["trace"][2]["request_id"] = "different"
    elif mutation == "raw_action":
        candidate["harness_result"]["decisions"][0]["raw_action"] = action(value={"wrong": 1})
    elif mutation == "oracle_leak":
        candidate["decision_inputs"][0]["oracle_payload"] = bundle["tasks"][0]["oracle_task"]["oracle_payload"]
    elif mutation == "model":
        candidate["model_identity"]["model_hash"] = "0" * 64
    elif mutation == "seed":
        candidate["generation_parameters"]["seed"] = 100
    elif mutation == "length":
        candidate["harness_result"]["decisions"][0]["finish_reason"] = "length"
    elif mutation == "interrupted":
        candidate["status"] = "interrupted"
    result = extract_preferences(bundle, authoring, plan, rows)
    assert not result["preferences"]
    assert result["dispositions"][1]["disposition"] == reason
    assert result["summary"]["planned_candidates"] == result["summary"]["candidate_denominator"] == 2
    assert result["summary"]["observed_candidate_rows"] == 2


def test_first_candidate_order_not_input_order_and_both_parameter_sides_saved(run):
    bundle, authoring, plan, rows = run("report-health")
    # Explicit synthetic record variant for the parameter-sidecar contract.
    # This is not an additional executed seeded model run.
    rows[1]["generation_parameters"]["seed"] = 99
    rows[1]["harness_result"]["provenance"]["generation_config"]["seed"] = 99
    plan["candidates"][bundle["tasks"][0]["task_id"]][1]["generation_parameters"]["seed"] = 99
    result = extract_preferences(bundle, authoring, plan, list(reversed(rows)))
    assert result["preferences"][0]["generation_parameters"]["seed"] == 0
    assert result["lineage"][0]["rejected"]["generation_parameters"]["seed"] == 99
    assert result["lineage"][0]["pair_order"] == 0


def test_missing_duplicate_unplanned_and_interrupted_records_are_not_dropped(run):
    bundle, authoring, plan, rows = run("report-health")
    unknown = copy.deepcopy(rows[0])
    unknown["candidate_id"] = "unplanned"
    result = extract_preferences(bundle, authoring, plan, [rows[0], rows[0], unknown])
    assert not result["preferences"]
    assert result["summary"]["planned_candidates"] == 2
    assert result["summary"]["candidate_denominator"] == 3
    assert result["summary"]["observed_candidate_rows"] == 3
    assert result["summary"]["missing_candidate_records"] == 1
    assert result["summary"]["dispositions"]["duplicate_candidate"] == 2


def test_first_pair_order_includes_unusable_planned_candidates(run):
    bundle, authoring, plan, rows = run("report-health")
    planned = plan["candidates"][bundle["tasks"][0]["task_id"]]
    extra = {"task_id": rows[0]["task_id"], "candidate_id": "candidate-0-interrupted", "status": "interrupted"}
    planned.insert(1, {"candidate_id": extra["candidate_id"],
                       "generation_parameters": copy.deepcopy(planned[0]["generation_parameters"])})
    result = extract_preferences(bundle, authoring, plan, rows + [extra])
    assert result["lineage"][0]["pair_order"] == 1
    assert result["summary"]["candidate_denominator"] == 3


def test_scripted_identity_cannot_be_formal(run):
    bundle, _, plan, _ = run("report-health")
    with pytest.raises(DataError, match="scripted_is_not_formal"):
        freeze_plan(bundle, SCRIPTED_IDENTITY, plan["candidates"], synthetic=False)


@pytest.fixture(scope="module")
def pool(run):
    result = extract_preferences(*run("report-health"))
    return result["preferences"][0], result["lineage"][0]


def expanded_pool(pool, count):
    preferences, lineage = [], []
    classes = ("argument_semantics", "unnecessary_tool", "final_semantics")
    for index in range(count):
        pref, line = copy.deepcopy(pool)
        pref["preference_id"] = line["preference_id"] = f"synthetic-review-{index:03d}"
        line["error_class"] = classes[index % 3]
        preferences.append(pref)
        lineage.append(line)
    return preferences, lineage


@pytest.mark.parametrize("total,expected", [(0, 0), (1, 1), (100, 100), (101, 100), (128, 100)])
def test_q1_sampling_size_order_and_blank_verdicts(pool, total, expected):
    preferences, lineage = expanded_pool(pool, total)
    packet = freeze_review(preferences, lineage, synthetic=True)
    assert packet["sample_size"] == expected
    assert len(packet["sample_ids"]) == expected
    assert all(row["verdict"] is None for row in packet["judgments"])
    assert all(quota > 0 for quota in packet["quotas"].values())
    assert packet == freeze_review(list(reversed(preferences)), list(reversed(lineage)), synthetic=True)


@pytest.mark.parametrize("errors,blocked", [(0, False), (5, False), (6, True)])
def test_q1_strict_threshold_original_denominator_and_unknown_exclusion(pool, errors, blocked):
    preferences, lineage = expanded_pool(pool, 128)
    packet = freeze_review(preferences, lineage, synthetic=True)
    judgments = [{"preference_id": identity, "verdict": "unknown" if i < errors else "pass",
                  "reason": "Synthetic review policy test only"}
                 for i, identity in enumerate(packet["sample_ids"])]
    # A confirmed error outside the sample is excluded too, without replacing a sampled row.
    extra = next(p["preference_id"] for p in preferences if p["preference_id"] not in packet["sample_ids"])
    judgments.append({"preference_id": extra, "verdict": "fail", "reason": "Extra synthetic finding"})
    result = apply_review(packet, preferences, lineage,
                          {"sample_hash": canonical_hash(packet), "reviewer": "synthetic-test-Q1",
                           "judgments": judgments})
    assert result["quality_pass"] is not blocked
    assert result["original_review_denominator"] == 100
    assert result["sample_errors_including_unknown"] == errors
    assert len(result["excluded_ids"]) == errors + 1
    assert len(result["remaining_preferences"]) == 128 - errors - 1
    assert not result["training_preferences"]  # Synthetic can never become formal training data.
    assert not result["replacement_sampling"]


def test_q1_zero_incomplete_and_changed_pool_cannot_pass(pool):
    packet = freeze_review([], [], synthetic=True)
    result = apply_review(packet, [], [], {"sample_hash": canonical_hash(packet),
                                          "reviewer": "synthetic-test", "judgments": []})
    assert result["dpo_quality_gate"] == "BLOCKED"
    preferences, lineage = expanded_pool(pool, 1)
    packet = freeze_review(preferences, lineage, synthetic=True)
    result = apply_review(packet, preferences, lineage, {"sample_hash": canonical_hash(packet),
                                                         "reviewer": "synthetic-test", "judgments": []})
    assert not result["quality_pass"]
    assert "PENDING" in review_html(packet, preferences, lineage)
    preferences[0]["preference_reason"] = "altered"
    with pytest.raises(DataError, match="review_sample_changed"):
        apply_review(packet, preferences, lineage, {})


def test_synthetic_pool_cannot_be_relabelled_as_formal(pool):
    preferences, lineage = expanded_pool(pool, 1)
    lineage[0]["synthetic"] = False
    with pytest.raises(DataError, match="scripted_is_not_formal"):
        freeze_review(preferences, lineage, synthetic=False)


def test_sampling_represents_rare_error_class(pool):
    preferences, lineage = expanded_pool(pool, 128)
    for row in lineage:
        row["error_class"] = "argument_semantics"
    lineage[-1]["error_class"] = "premature_termination"
    packet = freeze_review(preferences, lineage, synthetic=True)
    assert packet["quotas"] == {"argument_semantics": 99, "premature_termination": 1}
    assert lineage[-1]["preference_id"] in packet["sample_ids"]
