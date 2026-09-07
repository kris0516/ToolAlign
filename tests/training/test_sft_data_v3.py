"""Original tiny fixtures. No production corpus, tokenizer or model is opened."""

import copy
import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from toolalign.contracts import canonical_hash
from toolalign.data import quality_materials as qm
from toolalign.data.common import DataError, encoded
from toolalign.data.training_selection import rank_key
from toolalign.model_io import Sequence
from toolalign.model_io.format import encode_action
from toolalign.training.sft import data_v3 as v
from toolalign.training.sft.collator import collate_sequence
from toolalign.training.sft.data import SelectedRow, SelectionView


@pytest.fixture(autouse=True)
def no_production_encoding(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No fixture or consumer may encode, load a tokenizer or build a corpus")

    import toolalign.model_io as model_io
    import toolalign.model_io.sequence as sequence
    from toolalign.model_io.offline import OfflineQwenTokenizer
    from toolalign.training.sft import collator

    for module in (model_io, sequence, collator):
        monkeypatch.setattr(module, "training_sequence", forbidden)
    monkeypatch.setattr(sequence, "build_sequence", forbidden)
    monkeypatch.setattr(OfflineQwenTokenizer, "__init__", forbidden)
    monkeypatch.setattr(v.quality_exclusion, "build", forbidden)


def example(ident="v3-original", split="train"):
    return {"schema_version": "toolalign.example.v1", "example_id": ident,
        "source": "toolalign-original-v3-fixture", "source_revision": "v1", "license_id": "MIT",
        "source_record_hash": canonical_hash(["source", ident]), "group_id": "original-shared-group-" + split,
        "split": split, "category": "original_cpu", "tools": [],
        "messages": [{"role": "user", "content": "Describe the paper square.", "tool_calls": [], "tool_call_id": None}],
        "expected_action": {"kind": "final", "content": "The paper square is green.", "tool_calls": []}}


def original_sequence(value):
    # Literal invented IDs: these are deliberately not a tokenizer or a decode.
    return Sequence("Original fixture prompt.", encode_action(value["expected_action"]),
                    (11, 12), (11, 12, 21, 22), (11, 12, 21, 22, 151645), (0, 0, 1, 1, 1), 151645)


def audit(value, config):
    seq = original_sequence(value)
    action = value["expected_action"]
    return {**seq.metadata(),
        **{k: value[k] for k in ("example_id", "source", "source_revision", "source_record_hash", "group_id", "split")},
        "common_binding_sha256": config["representation_common_binding_sha256"],
        "example_sha256": canonical_hash(value),
        "model_input_sha256": canonical_hash({k: value[k] for k in ("messages", "tools")}),
        "action_sha256": canonical_hash(action), "parser_action_sha256": canonical_hash(action),
        "kind": "final", "sequence_error": None, "parser_error": None,
        "parser_accepted_exact": True, "rendered_inverse_exact": True,
        "raw_byte_cap_pass": True, "raw_node_cap_pass": True, "raw_depth_cap_pass": True,
        "raw_byte_cap": 131072, "action_native_utf8_bytes": len(encoded(action)),
        "action_nodes": 4, "action_depth": 1,
        "causal_input_ids_sha256": canonical_hash(list(seq.causal_input_ids)),
        "causal_target_ids_sha256": canonical_hash(list(seq.causal_target_ids)),
        "role_bindings_sha256": canonical_hash(["invented-v3-fixture"])}


@pytest.fixture
def generations():
    parent_config = json.loads((Path(__file__).parents[2] / "configs/training-data.v1.json").read_bytes())
    values = sorted([example("v3-" + str(i)) for i in range(4)], key=lambda e: rank_key(e["example_id"]))
    original = {}
    for rank, value in enumerate(values, 1):
        sidecar = {"profile": "smoke", "split": "train", "selection_rank": rank,
            "ranking_sha256": rank_key(value["example_id"])[0], "padding_bucket": 1024,
            "audit": audit(value, parent_config)}
        # Spaces are intentional: canonical view buffers must not claim raw-line identity.
        line = json.dumps(value, ensure_ascii=False).encode() + b"\n"
        original[value["example_id"]] = (value, sidecar, line)
    previous = {}
    for rank, value in enumerate(values[1:], 1):
        e, side, line = original[value["example_id"]]
        before = copy.deepcopy(side) | {"selection_rank": rank, "parent_selection_rank": side["selection_rank"]}
        previous[e["example_id"]] = (e, before, line)
    current = {}
    selected = {"quality_revision_sha256": "3" * 64, "quality_config_file_sha256": "4" * 64,
        "parent_selection_manifest_file_sha256": "1" * 64, "previous_selection_manifest_file_sha256": "2" * 64,
        "parent_training_config": parent_config}
    for rank, value in enumerate(values[2:], 1):
        ident = value["example_id"]
        e, parent, line = original[ident]
        before = previous[ident][1]
        current[ident] = (e, copy.deepcopy(parent) | {
            "selection_rank": rank, "parent_selection_rank": parent["selection_rank"],
            "previous_selection_rank": before["selection_rank"], "parent_sidecar_sha256": canonical_hash(parent),
            "previous_selection_sidecar_sha256": canonical_hash(before),
            "parent_selection_manifest_sha256": "1" * 64, "previous_selection_manifest_sha256": "2" * 64,
            "quality_revision_sha256": "3" * 64, "quality_config_file_sha256": "4" * 64}, line)
    summary = {"effective_selected_count": 2, "selected_identity_sha256": canonical_hash(list(current)),
        "parent_selected_count": 4, "quarantined_counts": {"fail": 1, "unknown": 1}, "refill_count": 0}
    selected["profiles"] = {"smoke": {"train": {"summary": summary}}}
    config = {"view_summaries": {"smoke": {"train": summary}},
              "data_binding": {"selection_manifest_file_sha256": "5" * 64}}
    return {"current": current, "original": original, "previous": previous,
        "excluded_sources": {e["source_record_hash"] for e in values[:2]},
        "selection": selected, "config": config, "profile": "smoke", "split": "train"}


def test_three_generations_preserve_other_sources_in_same_group_and_raw_lines(generations):
    view, lines = v._linked_view(**generations)
    assert len(view) == 2
    assert [r.sidecar["selection_rank"] for r in view.rows] == [1, 2]
    assert [r.sidecar["previous_selection_rank"] for r in view.rows] == [2, 3]
    assert [r.sidecar["parent_selection_rank"] for r in view.rows] == [3, 4]
    assert len({r.example["group_id"] for r in view.rows}) == 1
    assert lines[0][3] == v._sha(next(iter(generations["current"].values()))[2])
    assert view[0].example_bytes != next(iter(generations["current"].values()))[2]
    changed = view[0].example
    changed["messages"][0]["content"] = "edited copy"
    assert view[0].example != changed
    with pytest.raises(FrozenInstanceError):
        view.rows = ()


@pytest.mark.parametrize("field", v._RANKS)
@pytest.mark.parametrize("replacement", [True, 1.0, -1, 99])
def test_rank_types_and_ancestry(generations, field, replacement):
    next(iter(generations["current"].values()))[1][field] = replacement
    with pytest.raises(DataError):
        v._linked_view(**generations)


@pytest.mark.parametrize("mutation", ["drop", "reflow", "old_exclusion", "line", "example", "parent_hash", "previous_hash", "group_filter", "split"])
def test_selection_corruption(generations, mutation):
    current, original, previous = (generations[k] for k in ("current", "original", "previous"))
    ident = next(iter(current))
    e, side, line = current[ident]
    if mutation == "drop":
        current.pop(ident)
    elif mutation == "reflow":
        generations["current"] = dict(reversed(list(current.items())))
    elif mutation == "old_exclusion":
        previous.pop(ident)
    elif mutation == "line":
        current[ident] = (e, side, encoded(e) + b"\n")
    elif mutation == "example":
        e["expected_action"]["content"] = "A changed label"
    elif mutation == "parent_hash":
        side["parent_sidecar_sha256"] = "0" * 64
    elif mutation == "previous_hash":
        side["previous_selection_sidecar_sha256"] = "0" * 64
    elif mutation == "group_filter":
        generations["excluded_sources"].add(original[ident][0]["source_record_hash"])
    else:
        e["split"] = "test"
        side["split"] = "test"
    with pytest.raises(DataError):
        v._linked_view(**generations)


def protocol_record(ident="protocol-final"):
    value = example(ident)
    case = {"case_id": ident, "category": "original_protocol_only", "example": value, "audit": None,
        "profiles": {}, "primary_profile": "smoke", "encoding_mode": "reuse_original",
        "quality_revision_sha256": "3" * 64, "reviewer": None, "semantic_verdict": None,
        "token_mask_verdict": None, "enters_effective_training": False}
    seq = original_sequence(value)
    record = qm.sequence_record(case, seq)
    case["original_protocol_sequence"] = copy.deepcopy(record["sequence"])
    record["case"] = copy.deepcopy(case)
    record["token_texts"] = ["original token"] * record["padding"]["bucket"]
    return record


def test_array_conversion_is_exact_and_immutable():
    record = protocol_record()
    sequence, batch = v._batch_record(record, record["case"])
    assert batch.record() == record["padding"]
    assert batch.effective_supervised_targets == 3
    assert batch.causal_loss_mask[1:4] == (1, 1, 1)
    assert batch.causal_loss_mask[4:] == (0,) * (batch.bucket - 5)
    with pytest.raises(FrozenInstanceError):
        sequence.prompt_ids = (99,)
    with pytest.raises(FrozenInstanceError):
        batch.loss_mask = (1,)


@pytest.mark.parametrize("section,field", [("sequence", k) for k in v._UNPADDED] + [("padding", k) for k in v._ARRAYS])
@pytest.mark.parametrize("numeric", [True, 1.0])
def test_every_array_rejects_bool_and_float(section, field, numeric):
    record = protocol_record()
    record[section][field][0] = numeric
    with pytest.raises(DataError, match="integer_array"):
        v._batch_record(record, record["case"])


@pytest.mark.parametrize("mutation", ["eos", "shift", "mask", "pad", "token_texts", "prompt", "action", "scalar", "extra"])
def test_eos_shift_mask_padding_and_complete_record(mutation):
    record = protocol_record()
    if mutation == "eos":
        record["sequence"]["sequence_ids"][-1] = 151643
    elif mutation == "shift":
        record["padding"]["causal_target_ids"][0] = 99
    elif mutation == "mask":
        record["padding"]["causal_loss_mask"][1] = 0
    elif mutation == "pad":
        record["padding"]["sequence_ids"][-1] = 7
    elif mutation == "token_texts":
        record["token_texts"].pop()
    elif mutation == "prompt":
        record["sequence"]["prompt_text"] += "Changed"
    elif mutation == "action":
        record["case"]["example"]["expected_action"]["content"] = "Changed"
    elif mutation == "scalar":
        record["padding"]["bucket"] = float(record["padding"]["bucket"])
    else:
        record["unexpected"] = 1
    with pytest.raises(DataError):
        v._batch_record(record, record["case"])


@pytest.fixture
def material_binding(generations):
    view, lines = v._linked_view(**generations)
    row = view[0]
    case = {"case_id": "effective-01", "category": "effective_selected_train", "example": row.example,
        "audit": row.sidecar["audit"], "profiles": {"smoke": {k: row.sidecar[k] for k in v._RANKS}},
        "quality_revision_sha256": "3" * 64, "reviewer": None, "semantic_verdict": None,
        "token_mask_verdict": None, "original_jsonl_line_sha256": lines[0][3]}
    judgment = {k: case[k] for k in ("case_id", "quality_revision_sha256")}
    judgment.update(example_id=row.example["example_id"], source_record_hash=row.example["source_record_hash"],
        current_profiles=copy.deepcopy(case["profiles"]), semantic_verdict="pass", token_mask_verdict="pass", enters_effective_train=True)
    prepared = v.PreparedV3((view,), lines, b"{}", b"{}", None)
    return case, judgment, prepared, {"data_binding": {"quality_revision_sha256": "3" * 64}}


def test_material_binds_current_example_line_profiles_and_ranks(material_binding):
    result = v._case_binding(*material_binding)
    assert result["enters_training_view"] is True


@pytest.mark.parametrize("mutation", ["wrong_example", "rank", "line", "quality", "judge", "staging", "final", "protocol_in_view"])
def test_material_selection_boundaries(material_binding, mutation):
    case, judgment, prepared, config = material_binding
    if mutation == "wrong_example":
        case["example"]["messages"][0]["content"] = "A different example with the same ID"
    elif mutation == "rank":
        case["profiles"]["smoke"]["selection_rank"] = True
    elif mutation == "line":
        case["original_jsonl_line_sha256"] = "0" * 64
    elif mutation == "quality":
        case["quality_revision_sha256"] = "0" * 64
    elif mutation == "judge":
        judgment["token_mask_verdict"] = "unknown"
    elif mutation == "staging":
        case["category"] = "staged_direct_annotation"
    elif mutation == "final":
        case["example"]["split"] = "test"
    else:
        case.update(case_id="protocol-final", category="original_protocol_only", profiles={}, audit=None,
                    enters_effective_training=False)
        judgment.update(case_id="protocol-final", current_profiles={}, enters_effective_train=False)
    with pytest.raises(DataError):
        v._case_binding(case, judgment, prepared, config)


def test_protocol_material_remains_diagnostic_only(material_binding):
    _, _, prepared, config = material_binding
    case = protocol_record()["case"]
    judgment = {"case_id": case["case_id"], "example_id": case["example"]["example_id"],
        "source_record_hash": case["example"]["source_record_hash"], "quality_revision_sha256": "3" * 64,
        "current_profiles": {}, "semantic_verdict": "pass", "token_mask_verdict": "pass", "enters_effective_train": False}
    assert v._case_binding(case, judgment, prepared, config)["enters_training_view"] is False


@pytest.fixture
def review(monkeypatch):
    originals = [protocol_record("original-array-" + str(i)) for i in range(13)]
    monkeypatch.setattr(v, "MATERIALS_SHA256", canonical_hash(originals))
    items, sequences, batches = [], [], []
    for record in originals:
        sequence, batch = v._batch_record(record, record["case"])
        sequences.append(sequence)
        batches.append(batch)
        items.append({"original_record": record, "batch": batch.record()})
    payload = {"scope": v.SCOPE, "config_file_sha256": v.CONFIG_SHA256, "input_manifest_file_sha256": v.INPUT_SHA256,
        "consumer": v.consumer_identity(), "new_sequence_calls": 0, "optimization_authorized": False,
        "training_authorized": False, "items": items}
    return v._review_arrays(encoded(payload) + b"\n", batches, sequences)


def output_dir(tmp_path):
    parent = tmp_path / ".toolalign-local"
    parent.mkdir(exist_ok=True)
    return parent / "export"


def test_finite_export_roundtrip_and_immutable_expected(review, tmp_path):
    root = output_dir(tmp_path)
    v.export_review_arrays(review, output=root)
    assert v.read_review_arrays(output=root, expected=review) == review.batches
    assert type(v.read_review_arrays(output=root, expected=review)) is tuple
    payload = review.payload
    payload["items"][0]["batch"]["sequence_ids"][0] = 99
    assert review.payload != payload
    with pytest.raises(FrozenInstanceError):
        review.payload_bytes = b"{}"
    with pytest.raises(TypeError):
        v.ReviewArrays(b"{}", (), ())


@pytest.mark.parametrize("mutation", ["consumer", "self_consistent", "duplicate", "nonfinite", "float", "incomplete", "extra", "link"])
def test_modified_rehashed_output_cannot_replace_expected_source(review, tmp_path, mutation):
    root = output_dir(tmp_path)
    v.export_review_arrays(review, output=root)
    target = root / "review-arrays.json"
    payload = review.payload
    if mutation == "consumer":
        payload["consumer"] = {"wrong": "consumer"}
    elif mutation == "self_consistent":
        payload["items"][0]["batch"]["sequence_ids"][0] = 99
    elif mutation == "float":
        payload["items"][0]["batch"]["causal_input_ids"][0] = 11.0
    elif mutation == "duplicate":
        target.write_bytes(b'{"items":[],"items":[]}')
    elif mutation == "nonfinite":
        target.write_bytes(b'{"invalid":NaN}')
    elif mutation == "incomplete":
        (root / "manifest.json").unlink()
    elif mutation == "extra":
        (root / ".manifest.pending").write_bytes(b"unfinished")
    else:
        target.rename(root / "saved.json")
        target.symlink_to(root / "saved.json")
    if mutation in ("consumer", "self_consistent", "float"):
        target.write_bytes(encoded(payload) + b"\n")
        manifest = json.loads((root / "manifest.json").read_bytes())
        manifest["artifacts"]["review-arrays.json"] = {"sha256": v._sha(target.read_bytes()), "bytes": target.stat().st_size}
        (root / "manifest.json").write_bytes(encoded(manifest))
    with pytest.raises(DataError):
        v.read_review_arrays(output=root, expected=review)


def test_no_overwrite_and_unfinished_publication_is_not_success(review, tmp_path, monkeypatch):
    root = output_dir(tmp_path)
    root.mkdir()
    marker = root / "preserve"
    marker.write_bytes(b"original")
    with pytest.raises(DataError, match="already_exists"):
        v.export_review_arrays(review, output=root)
    assert marker.read_bytes() == b"original"
    original_write = v._exclusive_write

    def fail_manifest(path, data):
        if path.name == ".manifest.pending":
            raise OSError("original simulated publication failure")
        original_write(path, data)

    monkeypatch.setattr(v, "_exclusive_write", fail_manifest)
    other = root.with_name("incomplete")
    with pytest.raises(OSError):
        v.export_review_arrays(review, output=other)
    assert not (other / "manifest.json").exists()
    with pytest.raises(DataError, match="incomplete"):
        v.read_review_arrays(output=other, expected=review)


def test_private_output_path_and_symlink_ancestors(review, tmp_path):
    public = Path(__file__).parents[2] / "v3-public-fixture-must-never-exist"
    with pytest.raises(DataError, match="private_output"):
        v.export_review_arrays(review, output=public)
    assert not public.exists()
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / ".toolalign-local"
    link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(DataError, match="symlink"):
        v.export_review_arrays(review, output=link / "export")
    with pytest.raises(DataError, match="escape"):
        v.export_review_arrays(review, output=str(tmp_path) + "/.toolalign-local/../escape")


@pytest.mark.parametrize("data", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}', b'{"a":1e999}', b'\xff'])
def test_strict_native_json(data):
    with pytest.raises(DataError):
        v._json(data)


@pytest.mark.parametrize("bad", [b"{}", b'{"config_version":"toolalign.sft-cpu.v1"}', b'{"input_manifest_file_sha256":"wrong"}'])
def test_public_prepare_rejects_wrong_or_old_configuration_before_verifier(tmp_path, monkeypatch, bad):
    config = tmp_path / "config.json"
    config.write_bytes(bad)
    monkeypatch.setattr(v.quality_exclusion, "verify", lambda **k: pytest.fail("must reject before corpus access"))
    with pytest.raises(DataError, match="hash"):
        v.prepare_v3(sft_config_path=config, input_manifest_path=tmp_path / "never-opened.json")


def test_bundle_hash_only_descriptor_type_and_no_arbitrary_path(tmp_path, monkeypatch):
    data = tmp_path / "opaque.jsonl"
    data.write_bytes(b"This fixture is intentionally not JSON.\n")
    manifest = {"files": {"heldout": {"kind": "read_only_reference", "path": str(data),
        "sha256": v._sha(data.read_bytes()), "bytes": data.stat().st_size, "read_mode": "hash_only_no_deserialization"}}}
    raw = encoded(manifest)
    monkeypatch.setattr(v, "INPUT_SHA256", v._sha(raw))
    bundle = v._Bundle(tmp_path, raw)
    assert bundle.read("heldout", content=False) is None
    with pytest.raises(DataError, match="hash_only"):
        bundle.document("heldout")
    with pytest.raises(DataError, match="unlisted"):
        bundle.read("anything-else")
    returned = bundle.descriptor("heldout")
    returned["sha256"] = "0" * 64
    assert bundle.descriptor("heldout")["sha256"] != returned["sha256"]
    with pytest.raises(TypeError):
        bundle._members["heldout"] = b"{}"
    with pytest.raises(DataError, match="size_type"):
        v._read(data, size=True)
    data.write_bytes(b"modified")
    with pytest.raises(DataError):
        bundle.read("heldout", content=False)


def test_framework_presence_rejected_before_any_data_read(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "tokenizers", object())
    with pytest.raises(DataError, match="preframework"):
        v.prepare_v3(sft_config_path=tmp_path / "absent", input_manifest_path=tmp_path / "absent")


def test_prepared_forbidden_views(generations):
    view, lines = v._linked_view(**generations)
    prepared = v.PreparedV3((view,), lines, b'{"status":"original"}', b"{}", None)
    for forbidden in ("test", "ood_test", "staging", "BFCL"):
        with pytest.raises(DataError, match="forbidden_view"):
            prepared.view("smoke", forbidden)
    copy_of_report = prepared.report
    copy_of_report["status"] = "changed"
    assert prepared.report["status"] == "original"
    with pytest.raises(FrozenInstanceError):
        prepared.views = ()
    with pytest.raises(DataError):
        v.rebind_review_arrays(replace(prepared, _config_bytes=b"{}"))


def test_batch_rejects_causal_integer_substitution_even_when_python_equality_matches():
    # The old Batch kernel compares some causal tuples by equality. The new
    # boundary must additionally reject bool/float before invoking that kernel.
    record = protocol_record()
    seq = original_sequence(record["case"]["example"])
    original = collate_sequence(seq, bucket=1024, pad_token_id=151643)
    assert float(original.causal_target_ids[0]) == original.causal_target_ids[0]
    record["padding"]["causal_target_ids"][0] = float(original.causal_target_ids[0])
    with pytest.raises(DataError, match="padded_integer_array"):
        v._batch_record(record, record["case"])


def test_selected_rows_keep_nested_json_private():
    selected = SelectedRow(encoded(example()), encoded({"rank": 1}))
    view = SelectionView("smoke", "train", "0" * 64, "1" * 64, (selected,))
    value = view[0].sidecar
    value["rank"] = 8
    assert view[0].sidecar == {"rank": 1}


def validation_record(record):
    seq, batch = record["sequence"], record["padding"]
    digest = v._sha(encoded(record) + b"\n")
    checked = {"status": "PASS", "record_file_sha256": digest, "record_canonical_sha256": canonical_hash(record),
        "all_7_unpadded_array_hashes": {k: canonical_hash(seq[k]) for k in v._UNPADDED},
        "full_padded_arrays_sha256": canonical_hash(batch), "token_texts_sha256": canonical_hash(record["token_texts"]),
        "P": 2, "N_including_eos": 5, "C_without_eos": 2, "padding_bucket": 1024,
        "supervised_target_count": 3, "first_supervised_causal_position": 1, "last_supervised_causal_position": 3,
        "right_padding_tokens": 1019}
    judgment = {"validation_record_sha256": canonical_hash(checked), "record_file_sha256": digest}
    return checked, judgment, digest


def test_Q1_complete_arrays_and_validation_record_are_bound():
    record = protocol_record()
    v._validation(record, *validation_record(record))


@pytest.mark.parametrize("field", ["P", "N_including_eos", "padding_bucket", "supervised_target_count",
                                  "first_supervised_causal_position", "last_supervised_causal_position"])
def test_Q1_validation_numeric_types_are_not_python_coercions(field):
    record = protocol_record()
    checked, judgment, digest = validation_record(record)
    checked[field] = float(checked[field])
    judgment["validation_record_sha256"] = canonical_hash(checked)
    with pytest.raises(DataError):
        v._validation(record, checked, judgment, digest)


def test_prepare_control_flow_uses_one_readonly_verify_and_four_fixture_views(generations, monkeypatch):
    data = {}
    config = copy.deepcopy(generations["config"])
    config["data_binding"].update(quality_revision_sha256="3" * 64, quality_config_file_sha256="4" * 64,
                                 effective_files={"effective/train.jsonl": "f" * 64, "effective/validation.jsonl": "e" * 64})
    config.update(independent_quality_review={"reviewer": "Codex-AI(Q1)"}, independent_technical_review={"verdict": "PASS"},
                  plan={p: {"updates": 1} for p in v._PROFILES})
    selection = copy.deepcopy(generations["selection"])
    selection.update(manifest_version="toolalign.quality-excluded-selection.v3", training_authorized=False)
    config["view_summaries"] = {}
    selection["profiles"] = {}
    for profile in v._PROFILES:
        config["view_summaries"][profile] = {}
        selection["profiles"][profile] = {}
        for split in v._SPLITS:
            current = copy.deepcopy(generations["current"])
            original = copy.deepcopy(generations["original"])
            previous = copy.deepcopy(generations["previous"])
            for group in (original, previous, current):
                for ident, (e, side, _) in group.items():
                    e["split"] = split
                    side.update(profile=profile, split=split, audit=audit(e, selection["parent_training_config"]))
                    group[ident] = (e, side, encoded(e) + b"\n")
            for ident, (_, side, _) in current.items():
                side["parent_sidecar_sha256"] = canonical_hash(original[ident][1])
                side["previous_selection_sidecar_sha256"] = canonical_hash(previous[ident][1])
            for prefix, group in (("revision-v3/selection", current), ("d1-inputs/parent-inputs/parent_selection", original),
                                  ("d1-inputs/parent-revision/selection", previous)):
                data[f"{prefix}/{profile}/{split}.examples.jsonl"] = b"".join(r[2] for r in group.values())
                data[f"{prefix}/{profile}/{split}.sidecars.jsonl"] = b"".join(encoded(r[1]) + b"\n" for r in group.values())
            summary = copy.deepcopy(generations["selection"]["profiles"]["smoke"]["train"]["summary"])
            config["view_summaries"][profile][split] = summary
            selection["profiles"][profile][split] = {"summary": summary}
    data["revision-v3/dispositions/sources.jsonl"] = b"".join(encoded({"source_record_hash": s, "disposition": "exclude_entire_source"})
        + b"\n" for s in sorted(generations["excluded_sources"]))
    verified = {"quality_revision_sha256": "3" * 64, "counts": {"original_fixture": 2}}
    binding = {k: config["data_binding"][k] for k in ("quality_revision_sha256", "quality_config_file_sha256", "effective_files", "selection_manifest_file_sha256")}
    binding.update(binding_version="toolalign.quality-excluded-training-binding.v3", training_authorized=False)
    for name, document in (("revision-v3/manifest.json", verified), ("revision-v3/selection/manifest.json", selection),
                           ("revision-v3/training-binding.json", binding), ("configuration/training-data.v1.json", selection["parent_training_config"])):
        data[name] = encoded(document)

    class FixtureBundle:
        manifest = {"roots": {"revision_v3": "original-output", "d1_verifier_inputs": "original-inputs"}}

        def path(self, name):
            return name

        def read(self, name):
            return data[name]

        def document(self, name):
            return v._json(data[name])

        def pin(self, name, digest):
            assert name in {"revision-v3/effective/train.jsonl", "revision-v3/effective/validation.jsonl"}
            return b"original-fixture-only"

    calls = []

    def verify(**paths):
        calls.append(paths)
        return copy.deepcopy(verified)

    monkeypatch.setattr(v, "_open_bundle", lambda *args: (encoded(config), FixtureBundle()))
    monkeypatch.setattr(v, "_approval", lambda *args: {"counts": {"original_fixture": 2}, "G_DATA": "PASS_FROZEN_V3_SCOPE"})
    monkeypatch.setattr(v.quality_exclusion, "verify", verify)
    result = v.prepare_v3(sft_config_path="original-fixture", input_manifest_path="original-fixture")
    assert calls == [{"output": "original-output", "config_path": "configuration/data-quality.v3.json", "input_root": "original-inputs"}]
    assert len(result.views) == 4 and all(len(view) == 2 for view in result.views)
    assert result.report["plans"]["formal"]["optimizer_updates_executed"] == 0
    assert result.report["training_authorized"] is False


@pytest.fixture
def approval_inputs():
    class TinyBundle:
        def __init__(self):
            self.raw = {}
            self.manifest = {}

        def put(self, name, document):
            self.raw[name] = encoded(document)

        def descriptor(self, name):
            return {"sha256": v._sha(self.raw[name]), "bytes": len(self.raw[name])}

        def pin(self, name, expected):
            if v._sha(self.raw[name]) != expected:
                raise DataError("original_fixture_pin_mismatch")
            return self.raw[name]

        def document(self, name):
            return v._json(self.raw[name])

    bundle = TinyBundle()
    names = ("d1-inputs/manifest.json", "configuration/data-quality.v3.json", "configuration/training-data.v1.json",
        "revision-v3/manifest.json", "revision-v3/selection/manifest.json", "revision-v3/training-binding.json",
        "s0/q1-receipt.json", "s0/r1-receipt.json", "s0/main-verification.json", "s0/quality-adoption.json",
        "q1-review/adjudications.json", "q1-review/material-validation.json")
    for name in names:
        bundle.put(name, {"original_fixture_member": name})
    bundle.put("s0/review-failures.json", {"whole_goal_paused": False, "issues": [
        {"issue_id": "original-" + str(i), "status": "CLOSED_FIXED_FIXTURE", "consecutive_failed_revisions": 0}
        for i in range(82)]})

    def digest(name):
        return bundle.descriptor(name)["sha256"]

    common_seal = {"candidate_commit": "a" * 40, "reviewer": "Codex-AI(Q1)", "model": "gpt-6-astra",
                   "thinking": "max", "status": "PASS_WITHIN_FIXED_Q1_SCOPE", "training_authorized": False}
    members = [{"relative_path": n.removeprefix("q1-review/"), **bundle.descriptor(n)}
               for n in names if n.startswith("q1-review/")]
    bundle.put("q1-review/adjudication-seal.json", common_seal | {"files": members})
    bundle.put("q1-review/final-evidence-seal.json", common_seal | {"commit": "b" * 40,
        "files": members + [{"relative_path": "adjudication-seal.json", **bundle.descriptor("q1-review/adjudication-seal.json")},
            {"kind": "public_at_commit", "repository_path": "reports/review/fixed/README.md", "commit": "b" * 40,
             "sha256": "f" * 64, "bytes": 3, "path": "/nonexistent-historical-checkout/README.md"}]})
    config = {"data_binding": {
        "quality_config_file_sha256": digest("configuration/data-quality.v3.json"),
        "parent_training_config_file_sha256": digest("configuration/training-data.v1.json"),
        "manifest_file_sha256": digest("revision-v3/manifest.json"),
        "selection_manifest_file_sha256": digest("revision-v3/selection/manifest.json"),
        "training_binding_file_sha256": digest("revision-v3/training-binding.json")},
        "independent_quality_review": {"commit": "b" * 40, "s0_receipt_sha256": digest("s0/q1-receipt.json"),
            "adjudication_seal_sha256": digest("q1-review/adjudication-seal.json"),
            "final_seal_sha256": digest("q1-review/final-evidence-seal.json")},
        "independent_technical_review": {"commit": "c" * 40, "s0_receipt_sha256": digest("s0/r1-receipt.json")},
        "issue_ledger_file_sha256": digest("s0/review-failures.json"), "G_DATA": "PASS_FROZEN_V3_SCOPE",
        "training_authorized": False, "optimization_authorized": False, "view_summaries": {},
        "d1_input_manifest_file_sha256": digest("d1-inputs/manifest.json"),
        "q1_adjudications_file_sha256": digest("q1-review/adjudications.json"),
        "q1_material_validation_file_sha256": digest("q1-review/material-validation.json")}
    approval = {k: config[k] for k in ("data_binding", "independent_quality_review", "independent_technical_review",
        "issue_ledger_file_sha256", "G_DATA", "training_authorized", "optimization_authorized")}
    approval.update(candidate_commit="a" * 40, s0_main_verification_sha256=digest("s0/main-verification.json"),
                    s0_quality_adoption_sha256=digest("s0/quality-adoption.json"))
    bundle.put("s0/data-approval.json", approval)
    config["s0_data_approval_file_sha256"] = digest("s0/data-approval.json")
    bundle.manifest = {"candidate_commit": "a" * 40, "q1_review_commit": "b" * 40, "r1_review_commit": "c" * 40,
        "view_summaries": {}, "files": {n: bundle.descriptor(n) for n in bundle.raw}}
    return bundle, config


def test_approval_and_two_levels_of_Q1_seal_are_bound(approval_inputs):
    bundle, config = approval_inputs
    approval = v._approval(bundle, config)
    assert approval["G_DATA"] == "PASS_FROZEN_V3_SCOPE"
    assert approval["optimization_authorized"] is False


@pytest.mark.parametrize("name", ["configuration/data-quality.v3.json", "revision-v3/manifest.json",
    "revision-v3/selection/manifest.json", "revision-v3/training-binding.json", "q1-review/adjudication-seal.json",
    "q1-review/final-evidence-seal.json", "q1-review/adjudications.json", "q1-review/material-validation.json",
    "s0/data-approval.json", "s0/review-failures.json", "s0/r1-receipt.json", "s0/q1-receipt.json"])
def test_corrupted_data_or_approval_bindings_fail(approval_inputs, name):
    bundle, config = approval_inputs
    bundle.raw[name] += b" "
    with pytest.raises(DataError, match="pin"):
        v._approval(bundle, config)


def test_wrong_review_commit_or_missing_seal_member_is_rejected(approval_inputs):
    bundle, config = approval_inputs
    bundle.manifest["q1_review_commit"] = "d" * 40
    with pytest.raises(DataError, match="review_commit"):
        v._approval(bundle, config)
    bundle.manifest["q1_review_commit"] = "b" * 40
    bundle.manifest["files"]["q1-review/not-in-the-seal.json"] = {"sha256": "f" * 64, "bytes": 2}
    with pytest.raises(DataError, match="seal_mismatch"):
        v._approval(bundle, config)


@pytest.mark.parametrize("mutation", ["commit", "kind", "duplicate", "bool_size", "escape", "ambiguous"])
def test_mixed_public_and_private_Q1_seal_entries_fail_closed(approval_inputs, mutation):
    bundle, _ = approval_inputs
    seal = bundle.document("q1-review/final-evidence-seal.json")
    public = seal["files"][-1]
    if mutation == "commit":
        public["commit"] = "a" * 40
    elif mutation == "kind":
        public["kind"] = "untrusted_path"
    elif mutation == "duplicate":
        seal["files"].append(copy.deepcopy(public))
    elif mutation == "bool_size":
        public["bytes"] = True
    elif mutation == "escape":
        public["repository_path"] = "../outside"
    else:
        public["relative_path"] = "ambiguous.json"
    with pytest.raises(DataError):
        v._seal_members(seal, "b" * 40)


@pytest.fixture
def file_bundle(tmp_path, monkeypatch):
    root = tmp_path / "input"
    root.mkdir()
    verifier_root = tmp_path / "verifier"
    verifier_root.mkdir()
    manifest = {"files": {}, "roots": {"revision_v3": str(tmp_path), "d1_verifier_inputs": str(verifier_root)}}
    for i in range(6):
        name = "original-copy-" + str(i) + ".json"
        (root / name).write_bytes(b"{}")
        manifest["files"][name] = {"kind": "exact_copy", "relative_path": name, "sha256": v._sha(b"{}"),
                                   "bytes": 2, "read_mode": "original_fixture"}
    reference = tmp_path / "original-reference.json"
    reference.write_bytes(b"{}")
    declared = {}
    for i in range(347):
        name = "original-ancestor-" + str(i)
        declared[name] = {"kind": "immutable_existing_artifact", "path": str(reference),
                          "sha256": v._sha(b"{}"), "bytes": 2}
        manifest["files"]["d1-inputs/" + name] = {"kind": "read_only_reference", "path": str(reference),
            "sha256": v._sha(b"{}"), "bytes": 2, "read_mode": "original_fixture"}
    d1_raw = encoded({"files": declared})
    (verifier_root / "manifest.json").write_bytes(d1_raw)
    manifest["files"]["d1-inputs/manifest.json"] = {"kind": "read_only_reference", "path": str(verifier_root / "manifest.json"),
        "sha256": v._sha(d1_raw), "bytes": len(d1_raw), "read_mode": "original_fixture"}
    for i in range(255):
        manifest["files"]["original-reference-" + str(i)] = {"kind": "read_only_reference", "path": str(reference),
            "sha256": v._sha(b"{}"), "bytes": 2, "read_mode": "original_fixture"}

    def publish():
        raw = encoded(manifest)
        (root / "manifest.json").write_bytes(raw)
        monkeypatch.setattr(v, "INPUT_SHA256", v._sha(raw))
        config = encoded({"input_manifest_file_sha256": v.INPUT_SHA256})
        path = tmp_path / "config.json"
        path.write_bytes(config)
        monkeypatch.setattr(v, "CONFIG_SHA256", v._sha(config))
        return path, root / "manifest.json"

    return root, manifest, reference, publish


def test_all_manifest_members_verified_before_opening_json_views(file_bundle):
    _, _, _, publish = file_bundle
    config_path, manifest_path = publish()
    _, bundle = v._open_bundle(config_path, manifest_path)
    assert len(bundle.manifest["files"]) == 609
    # Regression: accepted ancestor references stay outside the verifier root.
    assert bundle.path("d1-inputs/original-ancestor-0").parent != Path(bundle.manifest["roots"]["d1_verifier_inputs"])


@pytest.mark.parametrize("mutation", ["missing", "extra", "bool_size", "link_file", "link_parent", "escape", "wrong_root", "bad_hash", "manifest_hash"])
def test_fixed_input_coverage_types_and_paths(file_bundle, mutation):
    root, manifest, reference, publish = file_bundle
    name = "original-copy-0.json"
    if mutation == "bool_size":
        manifest["files"][name]["bytes"] = True
    elif mutation == "escape":
        manifest["files"][name]["relative_path"] = "../escape"
    elif mutation == "wrong_root":
        row = manifest["files"].pop("original-reference-0")
        manifest["files"]["d1-inputs/wrong-root.json"] = row
    elif mutation == "bad_hash":
        manifest["files"][name]["sha256"] = "f" * 64
    config_path, manifest_path = publish()
    if mutation == "missing":
        (root / name).unlink()
    elif mutation == "extra":
        (root / "unlisted").write_bytes(b"{}")
    elif mutation == "link_file":
        (root / name).unlink()
        (root / name).symlink_to(reference)
    elif mutation == "link_parent":
        root.rename(root.with_name("original-directory"))
        root.symlink_to(root.with_name("original-directory"), target_is_directory=True)
    elif mutation == "manifest_hash":
        manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
    with pytest.raises(DataError):
        v._open_bundle(config_path, manifest_path)


@pytest.mark.parametrize("kind", ["fifo", "directory", "symlink"])
def test_nonregular_read_is_rejected_before_open(tmp_path, monkeypatch, kind):
    path = tmp_path / "original-nonregular-input"
    if kind == "fifo":
        os.mkfifo(path, 0o600)
    elif kind == "directory":
        path.mkdir()
    else:
        target = tmp_path / "original-regular-target"
        target.write_bytes(b"original target")
        path.symlink_to(target)

    def unexpected_open(*args, **kwargs):
        pytest.fail("A known nonregular input must be rejected before opening it")

    with monkeypatch.context() as context:
        context.setattr(v.os, "open", unexpected_open)
        expected = "v3_symlink_forbidden" if kind == "symlink" else "v3_regular_file_budget"
        with pytest.raises(DataError, match=expected):
            v._read(path, size=0)


_ORIGINAL_READ_REPLACEMENT = r'''
import json
import os
import stat
import sys
from pathlib import Path
from toolalign.data.common import DataError
from toolalign.training.sft import data_v3 as v

target, replacement = Path(sys.argv[1]), sys.argv[2]
original_open = os.open
opened = 0

def replace_before_open(path, flags, *args, **kwargs):
    global opened
    if Path(path) == target:
        opened += 1
        assert opened == 1
        target.unlink()
        if replacement == "fifo":
            os.mkfifo(target, 0o600)
        else:
            target.symlink_to(target.with_name("original-link-target"))
    return original_open(path, flags, *args, **kwargs)

v.os.open = replace_before_open
try:
    v._read(target, size=0)
except DataError as error:
    expected = "v3_regular_file_budget" if replacement == "fifo" else "v3_input_io_failure"
    assert str(error) == expected
    info = target.lstat()
    print(json.dumps({"error": str(error), "open_calls": opened, "writer_calls": 0,
                      "replacement_is_fifo": stat.S_ISFIFO(info.st_mode),
                      "replacement_is_symlink": stat.S_ISLNK(info.st_mode),
                      "mode": stat.S_IMODE(info.st_mode), "module_origin": v.__file__}))
else:
    raise AssertionError("replacement accepted")
'''


@pytest.mark.parametrize("replacement", ["fifo", "symlink"])
def test_nonregular_replacement_after_precheck_cannot_block_or_follow(tmp_path, replacement):
    path = tmp_path / "original-regular-input"
    path.write_bytes(b"")
    (tmp_path / "original-link-target").write_bytes(b"original link target")
    script = tmp_path / "original-replacement-probe.py"
    script.write_text(_ORIGINAL_READ_REPLACEMENT)
    argv = [sys.executable, "-B", str(script), str(path), replacement]
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    (tmp_path / "child-stdout.log").write_bytes(stdout)
    (tmp_path / "child-stderr.log").write_bytes(stderr)
    (tmp_path / "child-result.json").write_text(json.dumps({
        "argv": argv, "pid": process.pid, "exit_code": process.returncode,
        "child_reaped": process.poll() is not None, "timed_out": timed_out,
        "source": "original_IO_fixture", "real_data_API_calls": 0,
    }, sort_keys=True) + "\n")
    assert not timed_out, "Replaced input must reject without any FIFO writer"
    assert process.returncode == 0, stderr.decode(errors="replace")
    result = json.loads(stdout)
    assert result["open_calls"] == 1 and result["writer_calls"] == 0
    assert result["replacement_is_fifo"] is (replacement == "fifo")
    assert result["replacement_is_symlink"] is (replacement == "symlink")


@pytest.mark.parametrize("content", [True, False])
@pytest.mark.parametrize("payload", [b"", b"original binary I/O fixture\x00\xff\n"])
def test_regular_read_and_hash_only_semantics_unchanged(tmp_path, content, payload):
    path = tmp_path / "original-regular-input"
    path.write_bytes(payload)
    actual = v._read(path, digest=v._sha(payload), size=len(payload), content=content)
    assert actual == (payload if content else None)


@pytest.mark.parametrize("kwargs, error", [
    ({"size": 1}, "v3_input_size_mismatch"),
    ({"digest": "0" * 64}, "v3_input_hash_mismatch"),
    ({"limit": 1}, "v3_regular_file_budget"),
])
def test_regular_read_keeps_size_hash_and_budget_errors(tmp_path, kwargs, error):
    path = tmp_path / "original-regular-input"
    path.write_bytes(b"original I/O fixture")
    with pytest.raises(DataError, match=error):
        v._read(path, **kwargs)
