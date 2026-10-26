"""Original CPU fixtures for the two data profiles, separate from private L1."""

from __future__ import annotations

import copy

import pytest

from toolalign.contracts import canonical_hash, model_input_from_example
from toolalign.data.common import DataError, file_hash, read_json, write_json
from toolalign.data.evaluation.__main__ import build_relations_package, load_package
from toolalign.data.evaluation.audit import audit_groups
from toolalign.data.evaluation.checks import check_scripts, run_script
from toolalign.data.evaluation.tasks import (
    CATALOG,
    CONSTRAINT_CATALOG,
    CONSTRAINT_REVISION,
    REVISION,
    prepare_tasks,
    validate_tasks,
)
from toolalign.data.preferences.tasks import action, script, step
from toolalign.evaluation.oracles import OBSERVATION_ORACLE_VERSION
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.model_io.format import encode_action
from toolalign.tools.constraints_catalog import SHARD_PLACEMENTS


def supplied_case():
    answer = {"kind": "final", "value": {"remaining": 1}}
    return {"domain": "releases", "family_id": "cpu-supplied-set-removal", "category": "no_tool",
            "prompt": "CPU fixture: initial instances are x and y. Remove x twice, counting each instance once. Without tools, return remaining as a JSON number.",
            "answers": [answer], "strategies": [[]], "after_observation": [[]], "faults": {},
            "positive_scripts": [script([], answer)],
            "negative_scripts": {"double_subtraction": [encode_action(action(value={"remaining": 0}))]}}


def test_explicit_profiles_keep_legacy_identity_and_select_new_truth():
    case = supplied_case()
    old, _ = prepare_tasks([case])
    new, _ = prepare_tasks([case], catalog=CONSTRAINT_CATALOG)
    identity = {key: case[key] for key in (
        "domain", "family_id", "category", "prompt", "answers", "strategies", "faults")}
    assert old["catalog"] == CATALOG
    assert old["tasks"][0]["task_id"] == "g5-" + canonical_hash(identity)[:32]
    assert old["tasks"][0]["oracle_task"]["oracle_payload"]["version"] == ORACLE_VERSION
    assert old["tasks"][0]["example"]["source_revision"] == REVISION
    task = new["tasks"][0]
    assert task["task_id"] != old["tasks"][0]["task_id"]
    assert task["example"]["source_revision"] == CONSTRAINT_REVISION
    assert task["oracle_task"]["oracle_payload"]["version"] == OBSERVATION_ORACLE_VERSION
    assert task["oracle_task"]["oracle_payload"]["after_observation"] == [[]]
    assert set(model_input_from_example(task["example"])) == {"messages", "tools"}
    changed = copy.deepcopy(new)
    changed["tasks"][0]["oracle_task"]["oracle_payload"]["version"] = ORACLE_VERSION
    with pytest.raises(DataError, match="evaluation_observation_truth"):
        validate_tasks(changed)


@pytest.mark.parametrize("edges", [None, [], [[[0, 1]]]])
def test_relation_profile_requires_explicit_valid_edges_per_strategy(edges):
    case = supplied_case()
    case["after_observation"] = edges
    with pytest.raises(DataError, match="evaluation_observation_truth"):
        prepare_tasks([case], catalog=CONSTRAINT_CATALOG)


def test_new_profile_enforces_twenty_eight_and_one_non_recovery_per_domain():
    with pytest.raises(DataError, match="evaluation_task_count"):
        prepare_tasks([supplied_case()] * 29, catalog=CONSTRAINT_CATALOG)
    other = supplied_case()
    other["prompt"] += " This is a second CPU fixture."
    with pytest.raises(DataError, match="evaluation_domain_category_limit"):
        prepare_tasks([supplied_case(), other], catalog=CONSTRAINT_CATALOG)
    assert len(prepare_tasks([supplied_case(), other])[0]["tasks"]) == 2


def dependent_case():
    strategy = [
        step("read_shard_placement", {"stripe": "journal-stripe"}, copy.deepcopy(SHARD_PLACEMENTS["journal-stripe"])),
        step("check_shard_recovery", {"placement_id": "journal-placement-1", "failed_domains": ["rack-x"]}, {
            "placement_id": "journal-placement-1", "failed_domains": ["rack-x"],
            "surviving_shards": ["j0", "j1", "j2", "j3"], "lost_shards": [],
            "surviving_unique_count": 4, "surviving_replica_count": 4,
            "required_shards": 3, "recoverable": True,
        }),
    ]
    answer = {"kind": "final", "value": {"surviving": 4}}
    return {"domain": "storage", "family_id": "cpu-observed-placement", "category": "multi_step",
            "prompt": "CPU fixture: read journal-stripe, then use its observed placement_id to check failure of rack-x. Return surviving as the unique shard count, a JSON number.",
            "answers": [answer], "strategies": [strategy], "after_observation": [[[0, 1]]], "faults": {},
            "positive_scripts": [script(strategy, answer, separate=True)],
            "negative_scripts": {"pre_submitted_dependency": script(strategy, answer)}}


def test_authoring_checks_use_selected_oracle_and_allow_independent_batch(tmp_path):
    case = dependent_case()
    bundle, authoring = prepare_tasks([case], catalog=CONSTRAINT_CATALOG)
    bundle, _ = audit_groups(bundle, [], [], {"tasks": []})
    root = tmp_path / "dependent"
    summary = check_scripts(bundle, authoring, root)
    assert summary["pass"]
    results = [read_json(root / c["path"])["harness_result"] for c in summary["checks"]]
    assert [r["score"]["outcome"] for r in results] == ["success", "failure"]
    assert all(r["score"]["oracle_version"] == OBSERVATION_ORACLE_VERSION for r in results)
    assert "observation" in results[1]["score"]["reason"].lower()
    independent = copy.deepcopy(case)
    independent["prompt"] = "CPU fixture: read journal-stripe and check known journal-placement-1 with rack-x failed; these independent calls may be batched. Return surviving as a JSON number."
    independent["after_observation"] = [[]]
    independent["positive_scripts"] = [case["negative_scripts"]["pre_submitted_dependency"]]
    value, _ = prepare_tasks([independent], catalog=CONSTRAINT_CATALOG)
    row = run_script(value["tasks"][0], independent["positive_scripts"][0], tmp_path / "independent",
                     "cpu-independent", catalog=CONSTRAINT_CATALOG)
    results.append(row["harness_result"])
    assert results[-1]["score"]["outcome"] == "success"
    assert results[-1]["trace"][-1]["budget_consumed"]["tool_rounds"] == 1
    for result in results:
        assert all(p["reaped"] and p["operation_started"] for p in result["process_records"])
        assert all(set(i) == {"messages", "tools"} for i in result["decision_inputs"])


def test_relation_package_consumes_bound_history_and_preserves_old_records(tmp_path):
    root = tmp_path / ".toolalign-local"
    root.mkdir()
    case = supplied_case()
    new, _ = prepare_tasks([case], catalog=CONSTRAINT_CATALOG)
    old_case = supplied_case()
    old_case.update(family_id="cpu-old-equivalent", prompt="CPU fixture: count distinct removed instances.")
    old, _ = prepare_tasks([old_case])
    reference = {"p02_rows": [], "development_cases": [], "g4_bundle": {"tasks": []},
                 "historical_g5_reference": {"tasks": old["tasks"], "edges": []}}
    write_json(root / "reference.json", reference)
    write_json(root / "reference-manifest.json", {
        "schema_version": "toolalign.evaluation-exclusion-reference-manifest.v1",
        "artifacts": {"reference.json": file_hash(root / "reference.json")}})
    write_json(root / "author.json", {"schema_version": "toolalign.evaluation-authoring.v1",
        "purpose": "heldout-cpu-authoring", "catalog": CONSTRAINT_CATALOG, "cases": [case]})
    write_json(root / "semantic.json", {"links": [{"left": "new:" + new["tasks"][0]["task_id"],
        "right": "g5:" + old["tasks"][0]["task_id"],
        "reason": "Original CPU fixture supplies an explicit old program-equivalence bridge."}]})
    summary = build_relations_package(root / "author.json", root / "reference-manifest.json",
                                      root / "semantic.json", root / "package")
    assert summary["retained_tasks"] == 0 and summary["quarantined_tasks"] == 1
    loaded = load_package(root / "package")
    assert loaded["tasks.json"]["catalog"] == CONSTRAINT_CATALOG
    assert loaded["group-audit.json"]["old_g5_tasks"] == 1
    assert read_json(root / "package/manifest.json")["revision"] == CONSTRAINT_REVISION
    assert read_json(root / "reference.json") == reference
    write_json(root / "reference.json", {**reference, "changed": True})
    with pytest.raises(DataError, match="artifact_hash_mismatch"):
        build_relations_package(root / "author.json", root / "reference-manifest.json",
                                root / "semantic.json", root / "corrupt")
