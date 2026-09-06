"""Independent original boundary cases, separate from production measurements."""

import copy

import pytest
from training_binding_cases import config, example, row

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError
from toolalign.data.training_selection import (
    build,
    load_config,
    new_private_directory,
    rank_key,
    select_examples,
    stable_artifacts,
)


def select(values, rows=None):
    return select_examples({s: [e for e in values if e["split"] == s] for s in ("train", "validation")},
                           rows if rows is not None else [row(e) for e in values], config())


def test_shuffle_and_seed_are_stable_and_original_records_are_unchanged():
    values = [example("c"), example("a"), example("b"), example("v", "validation")]
    before = copy.deepcopy(values)
    measured = [row(e) for e in values]
    one = select(values, measured)
    two = select(list(reversed(values)), [measured[i] for i in (2, 0, 3, 1)])
    assert one == two and values == before
    assert [e["example_id"] for e in one["smoke"]["train"]["examples"]] == sorted(
        ["c", "a", "b"], key=lambda i: (canonical_hash(["toolalign.training-selection.v1", 42, i]), i))
    assert rank_key("a")[0] == canonical_hash(["toolalign.training-selection.v1", 42, "a"])
    assert stable_artifacts(config(), one, {}) == stable_artifacts(config(), two, {})


def test_exclusions_boundaries_buckets_and_reserved_capacity_have_separate_denominators():
    specs = [("at-smoke", 1280, 255), ("at-formal", 1792, 255),
             ("context-only", 2048, 40), ("response-only", 100, 256),
             ("both", 2048, 256), ("reserved-fails", 1480, 40), ("small", 700, 40)]
    values = [example(i) for i, _, _ in specs]
    result = select(values, [row(e, p=p, c=c) for e, (_, p, c) in zip(values, specs, strict=True)])
    smoke, formal = result["smoke"]["train"], result["formal"]["train"]
    assert smoke["summary"]["excluded_counts"] == {
        "context_only": 2, "response_only": 1, "both": 1, "rank_limit": 0}
    assert formal["summary"]["excluded_counts"] == {
        "context_only": 1, "response_only": 1, "both": 1, "rank_limit": 0}
    assert smoke["summary"]["input_count"] == 7
    assert smoke["summary"]["selected_count"] == 3
    assert smoke["summary"]["prompt_plus_reserved_256"]["selected_fits"] == 2
    assert {s["audit"]["example_id"]: s["padding_bucket"] for s in smoke["sidecars"]} == {
        "at-smoke": 1536, "reserved-fails": 1536, "small": 1024}
    assert next(s for s in formal["sidecars"] if s["audit"]["example_id"] == "at-formal")["padding_bucket"] == 2048


def test_smoke_limit_is_unique_fixed_rank_and_formal_retains_remaining():
    values = [example(f"rank-{i:04d}") for i in range(1602)]
    result = select(values)
    smoke = result["smoke"]["train"]
    expected = sorted([e["example_id"] for e in values], key=rank_key)
    assert [e["example_id"] for e in smoke["examples"]] == expected[:1600]
    assert smoke["excluded"]["rank_limit"] == expected[1600:]
    assert result["formal"]["train"]["summary"]["selected_count"] == 1602


@pytest.mark.parametrize("field,bad", [
    ("source", "different"), ("source_record_hash", "f" * 64), ("source_revision", "wrong"),
    ("group_id", "wrong"), ("split", "validation"), ("example_sha256", "f" * 64),
    ("model_input_sha256", "f" * 64), ("action_sha256", "f" * 64),
    ("common_binding_sha256", "f" * 64), ("descriptor_sha256", "f" * 64),
    ("sequence_error", "failed"), ("parser_error", "failed"), ("parser_accepted_exact", 1),
    ("rendered_inverse_exact", False), ("prefix_stable", False), ("raw_byte_cap_pass", False),
    ("raw_node_cap_pass", False), ("raw_depth_cap_pass", False), ("eos_token_id", True),
    ("append_eos_count", 2), ("prompt_tokens", True), ("completion_tokens", -1),
    ("total_tokens", 142), ("completion_tokens_including_eos", 40),
    ("first_supervised_causal_position", 100), ("last_supervised_causal_position", 140),
    ("loss_mask_sha256", "0" * 64), ("causal_loss_mask_sha256", "0" * 64),
    ("action_nodes", 5), ("action_depth", 2), ("completion_utf8_bytes", 1),
    ("prompt_ids_sha256", "bad"), ("completion_sha256", "0" * 64),
])
def test_bad_binding_or_structure_fails_instead_of_length_exclusion(field, bad):
    value = example()
    measured = row(value)
    measured[field] = bad
    with pytest.raises(DataError):
        select([value], [measured])


@pytest.mark.parametrize("field", ["sequence_error", "parser_error", "append_eos_count", "source_record_hash"])
def test_explicit_fields_cannot_be_missing(field):
    value = example()
    measured = row(value)
    del measured[field]
    with pytest.raises(DataError):
        select([value], [measured])


def test_missing_extra_and_duplicate_rows_and_duplicate_examples():
    a, b = example("a"), example("b")
    for values, rows in [([a], []), ([a], [row(a), row(b)]), ([a], [row(a), row(a)]), ([a, a], [row(a)])]:
        with pytest.raises(DataError):
            select(values, rows)


@pytest.mark.parametrize("split", ["test", "ood_test"])
def test_final_splits_rejected_as_example_inputs_and_audit_content_is_ignored(split):
    value = example()
    forbidden = example("final", split)
    with pytest.raises(DataError):
        select_examples({"train": [forbidden], "validation": []}, [], config())
    with pytest.raises(DataError):
        select_examples({"train": [], "validation": [], split: [forbidden]}, [], config())
    assert select([value], [row(value), {"split": split, "unused_malformed_payload": True}]) == select([value])


def test_misplaced_split_and_shared_group_across_splits_fail():
    a, b = example("a"), example("b", "validation")
    with pytest.raises(DataError):
        select_examples({"train": [b], "validation": [a]}, [row(a), row(b)], config())
    b["group_id"] = a["group_id"]
    with pytest.raises(DataError):
        select([a, b])


def test_nested_budget_flags_are_not_a_source_of_truth():
    a = example()
    r = row(a, p=2048)
    r["budgets"] = {"context": {"1536": True, "2048": True}, "response_cap": False}
    assert select([a], [r])["formal"]["train"]["summary"]["selected_count"] == 0


def test_fixed_config_cannot_change_seed_or_training_authorization(tmp_path):
    for key, bad in [("seed", 43), ("training_authorized", True)]:
        changed = config()
        changed[key] = bad
        with pytest.raises(DataError):
            select_examples({"train": [], "validation": []}, [], changed)
    file = tmp_path / "config.json"
    file.write_text("{}")
    with pytest.raises(DataError, match="config_file_hash"):
        load_config(file)


def test_existing_empty_nonempty_and_symlink_outputs_are_never_overwritten(tmp_path):
    root = tmp_path / ".toolalign-local"
    root.mkdir()
    existing = root / "exists"
    existing.mkdir()
    for contents in (False, True):
        if contents:
            (existing / "keep").write_text("unchanged")
        with pytest.raises(DataError, match="output_already_exists"):
            build(output=existing)
        with pytest.raises(DataError):
            new_private_directory(existing)
    assert (existing / "keep").read_text() == "unchanged"
    alias = root / "alias"
    alias.symlink_to(root / "absent")
    with pytest.raises(DataError):
        new_private_directory(alias)
    with pytest.raises(DataError, match="output_must_be_private"):
        new_private_directory(tmp_path / "public")
    fresh = new_private_directory(root / "new")
    assert fresh.is_dir()


@pytest.mark.parametrize("tamper", ["example", "sidecar", "missing", "extra", "run"])
def test_verifier_recomputes_small_original_fixture_outputs(monkeypatch, tmp_path, tamper):
    from toolalign.data import training_selection as module

    # Fixture-only binding replaces production input loading, not its selector.
    # The real pinned build is exercised separately on the original private data.
    selected = select([example()])
    monkeypatch.setattr(module, "bound_inputs", lambda **kw: (config(), selected, {}))
    output = tmp_path / ".toolalign-local" / "fresh"
    module.build(output=output)
    assert module.verify(output=output)["profiles"]["smoke"]["train"]["selected_count"] == 1
    if tamper == "example":
        (output / "smoke/train.examples.jsonl").write_text("{}\n")
    elif tamper == "sidecar":
        (output / "formal/train.sidecars.jsonl").write_text("{}\n")
    elif tamper == "missing":
        (output / "formal/validation.examples.jsonl").unlink()
    elif tamper == "extra":
        (output / "unexpected.json").write_text("{}")
    else:
        (output / "run.json").write_text('{"stable_manifest_sha256":"incorrect"}')
    with pytest.raises(DataError):
        module.verify(output=output)
