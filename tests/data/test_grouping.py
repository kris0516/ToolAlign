import copy

import pytest

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError
from toolalign.data.grouping import augment, build_groups, task_template, validate_isolation
from toolalign.data.toolace import inspect_record


def audit_records(records, source):
    return [inspect_record(r, source, i)[0] for i, r in enumerate(records)]


def test_same_record_multiturn_same_group_and_rebuild(record_factory, source):
    records = [record_factory(second=True), record_factory(value="build-777")]
    infos = audit_records(records, source)
    first, _ = build_groups(records, infos, 17)
    second, _ = build_groups(records, infos, 17)
    assert first == second
    assert len({a["group_id"] for a in first}) == 1
    assert len({a["split"] for a in first}) == 1


def test_schema_overlap_bridges_different_tool_names_and_tasks(
    record_factory, original_tool, source
):
    a = record_factory()
    tool = copy.deepcopy(original_tool)
    tool["name"] = "another_tool"
    b = record_factory(tool)
    b["conversations"][0]["value"] = "Obtain distinct fixture metadata now."
    groups, _ = build_groups([a, b], audit_records([a, b], source), 8)
    assert groups[0]["group_id"] == groups[1]["group_id"]


def test_source_order_does_not_change_group_or_split(record_factory, source):
    records = [record_factory(value="build-111"), record_factory(value="build-222")]
    first, _ = build_groups(records, audit_records(records, source), 17)
    records.reverse()
    second, _ = build_groups(records, audit_records(records, source), 17)
    assert {(r["source_record_hash"], r["group_id"], r["split"]) for r in first} == {
        (r["source_record_hash"], r["group_id"], r["split"]) for r in second
    }


def test_template_recognizes_slot_rewrites():
    assert task_template('Look up "first" on 2026-01-01.') == task_template(
        'Look up "second" on 2025-02-02!'
    )


@pytest.mark.parametrize("shared_key", ["tool:a", "schema:b", "template:c"])
def test_intersections_detected(shared_key):
    records = [
        {"source_record_hash": "a", "group_id": "a", "split": "train", "group_keys": [shared_key]},
        {
            "source_record_hash": "b",
            "group_id": "b",
            "split": "ood_test",
            "group_keys": [shared_key],
        },
    ]
    with pytest.raises(DataError, match="split_intersection"):
        validate_isolation(records)


def test_augmentation_inherits_all_and_detects_tampering(example, lineage):
    messages = copy.deepcopy(example["messages"])
    messages[-1]["content"] = "Please read original build build-001."
    child, trace = augment(example, messages, lineage)
    assert child["group_id"] == example["group_id"]
    assert trace["augmentation_parent"] == example["example_id"]
    validate_isolation([lineage, trace])
    trace["split"] = "test"
    with pytest.raises(DataError):
        validate_isolation([lineage, trace])


def test_augmentation_missing_parent_rejected(example, lineage):
    messages = copy.deepcopy(example["messages"])
    messages[-1]["content"] += " Please."
    _, trace = augment(example, messages, lineage)
    with pytest.raises(DataError, match="augmentation_crosses_group"):
        validate_isolation([trace])


def test_model_projection_copies_labels_not_in_input(example):
    from toolalign.contracts import model_input_from_example

    projection = model_input_from_example(example)
    assert "expected_action" not in projection
    projection["messages"][-1]["content"] = "changed"
    assert projection["messages"] != example["messages"]
    assert canonical_hash(projection) != canonical_hash(model_input_from_example(example))


def test_near_duplicate_edges_hash_accepts_only_json(record_factory, source):
    records = [record_factory(value="build-111"), record_factory(value="build-222")]
    text = " ".join(f"word{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(80))
    records[0]["conversations"][0]["value"] = text + " blue"
    records[1]["conversations"][0]["value"] = text + " green"
    first, report = build_groups(records, audit_records(records, source), 17)
    assert report["near_duplicate_edges"] == 1
    assert first[0]["group_id"] == first[1]["group_id"]
    assert len(report["near_edges_hash"]) == 64


def test_ood_whole_groups_and_multiple_splits():
    records = [{"conversations": []} for _ in range(100)]
    infos = [
        {
            "source_record_hash": canonical_hash(i),
            "source_index": i,
            "tool_keys": [],
            "schema_keys": [],
        }
        for i in range(100)
    ]
    assignments, _ = build_groups(records, infos, 17)
    assert {r["split"] for r in assignments} == {"train", "validation", "test", "ood_test"}
    assert validate_isolation(assignments)["schema"] == 0
