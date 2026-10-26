"""Original CPU fixtures; these are not the private L1 questions or answers."""

from __future__ import annotations

import copy

import pytest

from toolalign.contracts import canonical_hash, model_input_from_example
from toolalign.data.common import DataError, file_hash, read_json, write_json
from toolalign.data.evaluation.__main__ import build_package, load_package
from toolalign.data.evaluation.audit import audit_groups
from toolalign.data.evaluation.checks import check_scripts, measure_lengths, run_script
from toolalign.data.evaluation.replay import build_replay
from toolalign.data.evaluation.tasks import CATALOG, prepare_tasks, validate_tasks
from toolalign.data.preferences.audit import task_keys
from toolalign.data.preferences.tasks import action, script, step
from toolalign.model_io.format import encode_action
from toolalign.tools import LocalToolRegistry


def fixture_case(domain="releases", family="cpu-supplied-label", prompt="CPU fixture: use no tools; return label=offline as a JSON string."):
    answer = {"kind": "final", "value": {"label": "offline"}}
    return {"domain": domain, "family_id": family, "category": "no_tool", "prompt": prompt,
            "answers": [answer], "strategies": [[]], "faults": {},
            "positive_scripts": [script([], answer)],
            "negative_scripts": {"wrong_value": [encode_action(action(value={"label": "online"}))]}}


def isolated(cases):
    bundle, authoring = prepare_tasks(cases)
    bundle, audit = audit_groups(bundle, [], [], {"tasks": []})
    return bundle, authoring, audit


def test_consumer_identity_and_model_projection():
    bundle, _, _ = isolated([fixture_case()])
    task = bundle["tasks"][0]
    assert set(bundle) == {"schema_version", "purpose", "catalog", "registry_hash", "tasks", "recovery_task_ids"}
    assert bundle["registry_hash"] == LocalToolRegistry(catalog_id=CATALOG).registry_hash
    assert task["example"]["split"] == task["oracle_task"]["split"] == "test"
    value = model_input_from_example(task["example"])
    assert set(value) == {"messages", "tools"}
    assert len(value["tools"]) == 2
    assert task["group_id"] == task["example"]["group_id"] == task["oracle_task"]["group_id"]


@pytest.mark.parametrize("field,value", [("purpose", "train-candidate-generation"), ("catalog", "local-devops.v1"), ("registry_hash", "0" * 64)])
def test_bundle_rejects_other_identity(field, value):
    bundle, _, _ = isolated([fixture_case()])
    bundle[field] = value
    with pytest.raises(DataError):
        validate_tasks(bundle)


def test_task_rejects_train_split_schema_change_and_duplicate():
    bundle, _, _ = isolated([fixture_case()])
    for alteration in ("split", "schema", "duplicate"):
        changed = copy.deepcopy(bundle)
        task = changed["tasks"][0]
        if alteration == "split":
            task["example"]["split"] = task["oracle_task"]["split"] = "train"
        elif alteration == "schema":
            task["example"]["tools"][0]["description"] = "Different meaning"
        else:
            changed["tasks"].append(copy.deepcopy(task))
        with pytest.raises(DataError):
            validate_tasks(changed)


def test_per_domain_category_ceiling():
    with pytest.raises(DataError, match="domain_category_limit"):
        prepare_tasks([fixture_case(prompt=f"CPU fixture option {i}") for i in range(3)])


@pytest.mark.parametrize("old_split", ["train", "validation", "test", "ood_test"])
def test_old_component_bridge_quarantines_whole_new_family(old_split):
    cases = [fixture_case(), fixture_case("packages", prompt="CPU fixture: preserve this supplied package label."),
             fixture_case("storage", "cpu-other", "CPU fixture: classify the provided quota annotation.")]
    bundle, _ = prepare_tasks(cases)
    key = next(k for k in task_keys(bundle["tasks"][0]) if k.startswith("tool:"))
    old = [{"group_id": "old-a", "split": "train", "group_keys": [key, "family:old-bridge"]},
           {"group_id": "old-b", "split": old_split, "group_keys": ["family:old-bridge"]}]
    saved = copy.deepcopy(old)
    retained, audit = audit_groups(bundle, old, [], {"tasks": []})
    assert len(retained["tasks"]) == 1
    assert retained["tasks"][0]["family_id"] == "cpu-other"
    excluded = next(c for c in audit["components"] if c["old_nodes"])
    assert len(excluded["task_ids"]) == 2 and len(excluded["old_nodes"]) == 2
    assert old == saved


def test_cross_domain_family_is_one_actual_component():
    bundle, _, audit = isolated([fixture_case(), fixture_case("packages", prompt="CPU fixture: supplied package label.")])
    assert len({t["group_id"] for t in bundle["tasks"]}) == 1
    assert len(audit["components"][0]["tool_sets"]) == 2


def test_shared_category_alone_does_not_merge_domains():
    bundle, _, audit = isolated([fixture_case(), fixture_case("storage", "cpu-quota-rule", "CPU fixture: evaluate supplied quota rules.")])
    assert len(audit["components"]) == len({t["group_id"] for t in bundle["tasks"]}) == 2


def test_readable_near_duplicate_and_old_group_bridge():
    prompt = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega prepare independent fixed audit evidence here"
    bundle, _ = prepare_tasks([fixture_case(prompt=prompt)])
    old = {"task_id": "old-near", "family_id": "different-family", "group_id": "old-component",
           "example": {"source_record_hash": "0" * 64, "tools": [],
                       "messages": [{"role": "user", "content": prompt + " now"}]}}
    retained, audit = audit_groups(bundle, [], [], {"tasks": [old]})
    assert retained["tasks"] == []
    assert any(e["key"] == "near-trigram" for e in audit["components"][0]["edges"])
    assert audit["trigram_pairs_checked"] == 1
    assert not audit["p02_heldout_content_read"]


def test_authored_semantic_edge_excludes_entire_new_component():
    bundle, _ = prepare_tasks([fixture_case()])
    development = [{"id": "old-rephrased", "group": "old-other", "prompt": "A different lexical statement."}]
    links = [{"left": "new:" + bundle["tasks"][0]["task_id"], "right": "p03:old-rephrased",
              "reason": "CPU fixture records a semantic equivalence despite different lexical keys."}]
    retained, audit = audit_groups(bundle, [], development, {"tasks": []}, semantic_links=links)
    assert not retained["tasks"] and audit["semantic_links"] == links


def test_historical_g5_keeps_old_only_edges_and_complete_components():
    historical, _ = prepare_tasks([
        fixture_case("releases", "cpu-archived-quartz", "Archived CPU marker quartz."),
        fixture_case("packages", "cpu-archived-copper", "Past CPU label copper."),
        fixture_case("incidents", "cpu-archived-tundra", "Historical CPU flag tundra."),
    ])
    for task in historical["tasks"]:
        group = "historical-" + task["task_id"]
        task["group_id"] = task["example"]["group_id"] = task["oracle_task"]["group_id"] = group
    first, second, unrelated = ["g5:" + t["task_id"] for t in historical["tasks"]]
    old = {"task_id": "old-cpu-gate", "family_id": "cpu-legacy-gate", "group_id": "legacy-gate",
           "example": {"source_record_hash": "a" * 64, "tools": [],
                       "messages": [{"role": "user", "content": "Legacy CPU gate."}]}}
    edges = [{"left": first, "right": second, "key": "near-trigram", "jaccard": .9},
             {"left": second, "right": "g4:old-cpu-gate", "key": "authored-semantic-link",
              "reason": "Original CPU fixture records the archived gate-equivalence edge."}]
    reference = {"tasks": historical["tasks"], "edges": edges}
    bundle, _ = prepare_tasks([
        fixture_case("releases", "cpu-current-pair", "Candidate CPU result lilac."),
        fixture_case("storage", "cpu-current-pair", "Candidate CPU result amber."),
    ])
    p02 = [{"group_id": "disconnected-old", "split": "test", "group_keys": ["family:old-only"]}]
    inputs = copy.deepcopy((bundle, reference, p02, old))
    before, original_audit = audit_groups(bundle, p02, [], {"tasks": [old]})
    assert len(before["tasks"]) == 2 and "reference_graph" not in original_audit
    assert (before, original_audit) == audit_groups(
        bundle, p02, [], {"tasks": [old]}, historical_g5_reference=None)
    retained, audit = audit_groups(bundle, p02, [], {"tasks": [old]},
                                  historical_g5_reference=reference)
    assert not retained["tasks"] and audit["old_g5_tasks"] == 3
    component = audit["components"][0]
    assert len(component["task_ids"]) == 2
    assert {n["id"] for n in component["old_nodes"]} == {first, second, "g4:old-cpu-gate"}
    assert [e for e in component["edges"] if e.get("origin")] == [
        {**edge, "origin": "historical_g5_reference"} for edge in edges]
    graph = audit["reference_graph"]
    assert len(graph["nodes"]) == 7 and len(graph["components"]) == 3
    assert {tuple(c["node_ids"]) for c in graph["components"] if len(c["node_ids"]) == 1} == {
        (unrelated,), ("p02:disconnected-old",)}
    assert (bundle, reference, p02, old) == inputs


@pytest.mark.parametrize("bridge", ["schema", "normalized-schema"])
def test_historical_function_and_catalog_rename_does_not_reset_isolation(bridge):
    historical, _ = prepare_tasks([fixture_case(family="cpu-archived-layout", prompt="Old CPU oval.")])
    for tool in historical["tasks"][0]["example"]["tools"]:
        tool["name"] = "archived_" + tool["name"]
        tool["tool_version"] = "cpu-renamed-catalog.v9"
        if bridge == "normalized-schema":
            schema = tool["parameters_json_schema"]
            schema["required"].reverse()
            for field in schema["properties"].values():
                field["enum"].reverse()
                field["minLength"] = 0
    bundle, _ = prepare_tasks([fixture_case(family="cpu-current-layout", prompt="New CPU triangle.")])
    common = task_keys(bundle["tasks"][0]) & task_keys(historical["tasks"][0])
    assert not any(k.startswith("tool:") for k in common)
    assert any(k.startswith(bridge + ":") for k in common)
    if bridge == "normalized-schema":
        assert not any(k.startswith("schema:") for k in common)
    assert len(audit_groups(bundle, [], [], {"tasks": []})[0]["tasks"]) == 1
    retained, audit = audit_groups(bundle, [], [], {"tasks": []},
                                  historical_g5_reference={"tasks": historical["tasks"], "edges": []})
    assert not retained["tasks"]
    assert any(e["key"].startswith(bridge + ":") for e in audit["components"][0]["edges"])


@pytest.mark.parametrize("endpoint", ["g5:missing-history-node", "new"])
def test_historical_edge_requires_present_old_endpoints(endpoint):
    bundle, _ = prepare_tasks([fixture_case()])
    task_id = bundle["tasks"][0]["task_id"]
    reference = {"tasks": bundle["tasks"], "edges": [{"left": "g5:" + task_id,
                 "right": "new:" + task_id if endpoint == "new" else endpoint,
                 "key": "authored-semantic-link", "reason": "CPU malformed historical edge."}]}
    with pytest.raises(DataError, match="historical_g5_edge_evidence"):
        audit_groups(bundle, [], [], {"tasks": []}, historical_g5_reference=reference)


def tool_case(fault=None):
    args = {"deployment_id": "comet-green", "snapshot_day": "2026-10-12"}
    output = {**args, "application": "comet-gateway", "running_release": "4.2.0",
              "ready_replicas": 2, "state": "rolling"}
    strategy = [step("read_deployment_snapshot", args, output)]
    if fault:
        strategy.insert(0, {"name": "read_deployment_snapshot", "arguments": args,
                            "status": "timed_out" if fault == "block" else "error", "output": None,
                            "error_code": "tool_timeout" if fault == "block" else "injected_transient",
                            "retryable": True})
    answer = {"kind": "final", "value": {"snapshot_state": "rolling"}}
    case = fixture_case()
    case.update(category="fault_recovery" if fault else "single_tool", family_id="cpu-snapshot-state",
                prompt="CPU fixture: read the comet-green snapshot on 2026-10-12; retry once if needed. Return snapshot_state as a JSON string; no other calls.",
                answers=[answer], strategies=[strategy],
                faults={"read_deployment_snapshot": [fault, None]} if fault else {},
                positive_scripts=[script(strategy, answer, separate=True)])
    case["negative_scripts"] = {"fabricated_success": [encode_action(action(value=answer["value"]))]}
    return case


@pytest.mark.parametrize("fault", [None, "transient", "block"])
def test_real_owned_scripted_tools_faults_and_cleanup(tmp_path, fault):
    bundle, authoring, _ = isolated([tool_case(fault)])
    root = tmp_path / "runs"
    root.mkdir()
    summary = check_scripts(bundle, authoring, root)
    assert summary["pass"] and len(summary["checks"]) == 2
    positive = read_json(root / summary["checks"][0]["path"])["harness_result"]
    assert all(set(value) == {"messages", "tools"} for value in positive["decision_inputs"])
    assert all(p["reaped"] and p["operation_started"] for p in positive["process_records"])
    if fault:
        assert positive["trace"][-1]["budget_consumed"]["model_decisions"] == 3
        errors = [e["tool_result"] for e in positive["trace"] if e["event"] == "observing"]
        assert errors[0]["error_code"] == ("tool_timeout" if fault == "block" else "injected_transient")
        assert errors[1]["status"] == "completed"


def test_wrong_object_and_unneeded_call_are_rejected_by_semantics(tmp_path):
    case = tool_case()
    bundle, _, _ = isolated([case])
    wrong = copy.deepcopy(case["strategies"][0])
    wrong[0]["arguments"]["deployment_id"] = "lattice-green"
    row = run_script(bundle["tasks"][0], script(wrong, case["answers"][0]), tmp_path / "wrong", "wrong-object")
    assert row["harness_result"]["score"]["outcome"] == "failure"
    no_tool, _, _ = isolated([fixture_case()])
    row = run_script(no_tool["tasks"][0], case["positive_scripts"][0][:-1] + no_tool_answer(),
                     tmp_path / "unneeded", "unneeded-call")
    assert row["harness_result"]["score"]["outcome"] == "failure"


def no_tool_answer():
    return [encode_action(action(value={"label": "offline"}))]


class BoundaryTokenizer:
    """Length-boundary fixture, not a real tokenizer measurement."""
    identity = {"fixture": "length-boundary"}

    def __init__(self, count):
        self.count = count

    def render(self, messages, **kwargs):
        return "fixture-prompt"

    def encode(self, text, **kwargs):
        return list(range(self.count if text == "fixture-prompt" else 20))


@pytest.mark.parametrize("count,excluded", [(1792, False), (1793, True)])
def test_length_limit_reserves_full_256_and_preserves_rows(tmp_path, count, excluded):
    bundle, _, _ = isolated([fixture_case()])
    task = bundle["tasks"][0]
    write_json(tmp_path / "summary.json", {"pass": True, "task_list_hash": canonical_hash(bundle), "checks": [{
        "task_id": task["task_id"], "kind": "positive", "label": "0", "path": "positive.json"}]})
    write_json(tmp_path / "positive.json", {"harness_result": {
        "decision_inputs": [model_input_from_example(task["example"])],
        "decisions": [{"raw_text": no_tool_answer()[0]}]}})
    audit = measure_lengths(bundle, tmp_path, BoundaryTokenizer(count))
    assert bool(audit["quarantined_task_ids"]) is excluded
    assert len(audit["rows"]) == 2
    assert all(r["input_with_reserve"] == count + 256 for r in audit["rows"])


def test_package_keeps_private_authoring_and_verifies_bytes(tmp_path):
    root = tmp_path / ".toolalign-local"
    root.mkdir()
    author = root / "recipes.json"
    write_json(author, {"schema_version": "toolalign.evaluation-authoring.v1", "purpose": "heldout-cpu-authoring",
                        "cases": [fixture_case()]})
    for name in ("assignments.jsonl", "tool-lineage.jsonl"):
        (root / name).write_text("")
    write_json(root / "manifest.json", {"artifacts": {name: file_hash(root / name)
               for name in ("assignments.jsonl", "tool-lineage.jsonl")}})
    write_json(root / "dev.json", {"purpose": "public-original-development", "cases": []})
    write_json(root / "g4.json", {"schema_version": "toolalign.preference-tasks.v1", "purpose": "train-candidate-generation",
                                  "registry_hash": LocalToolRegistry().registry_hash, "tasks": []})
    write_json(root / "semantic.json", {"links": []})
    summary = build_package(author, root / "manifest.json", root / "dev.json", root / "g4.json",
                            root / "semantic.json", root / "package")
    assert summary["retained_tasks"] == 1
    load_package(root / "package")
    (root / "package/tasks.json").write_text("{}")
    with pytest.raises(DataError, match="hash_mismatch"):
        load_package(root / "package")


def test_replay_has_only_model_inputs_and_frozen_order():
    development = {"purpose": "public-original-development", "cases": [
        {"id": "one", "prompt": "Original CPU replay request one."},
        {"id": "two", "prompt": "Original CPU replay request two."}]}
    value, provenance = build_replay(development, [("one", "two")] * 4, BoundaryTokenizer(100))
    assert set(value) == {"schema_version", "purpose", "sequences"}
    for sequence in value["sequences"]:
        requests = sequence["requests"]
        assert len(requests) == 3
        assert requests[0]["model_input"] == requests[1]["model_input"] != requests[2]["model_input"]
        assert all(set(r) == {"request_id", "model_input"} and set(r["model_input"]) == {"messages", "tools"}
                   for r in requests)
    assert [r["seed"] for r in provenance["rows"]] == list(range(42, 54))
    assert not provenance["test_outputs_used"] and provenance["model_calls"] == 0
