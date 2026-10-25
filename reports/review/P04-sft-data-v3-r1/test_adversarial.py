"""R1 original CPU fixtures; no production data, callbacks, or T1 test helpers."""

import copy
import hashlib
import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from toolalign.contracts import canonical_hash
from toolalign.data.common import DataError, encoded
from toolalign.data.training_selection import rank_key
from toolalign.model_io import Sequence
from toolalign.training.sft import data_v3 as v

ROOT = Path(__file__).resolve().parents[3]
IDENTITY = ("example_id", "source", "source_revision", "source_record_hash", "group_id", "split")


@pytest.fixture(autouse=True)
def no_encoding_or_corpus(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Original R1 fixtures must never consume a corpus or encode")

    import toolalign.model_io as model_io
    import toolalign.model_io.sequence as sequences
    from toolalign.model_io.offline import OfflineQwenTokenizer
    from toolalign.training.sft import collator

    monkeypatch.setattr(v.quality_exclusion, "verify", forbidden)
    monkeypatch.setattr(v.quality_exclusion, "build", forbidden)
    monkeypatch.setattr(OfflineQwenTokenizer, "__init__", forbidden)
    for module in (model_io, sequences, collator):
        monkeypatch.setattr(module, "training_sequence", forbidden)
    monkeypatch.setattr(sequences, "build_sequence", forbidden)
    monkeypatch.setattr(collator, "collate_selected", forbidden)


def original_example(ident):
    return {
        "schema_version": "toolalign.example.v1", "example_id": ident,
        "source": "r1-original-ring-fixture", "source_revision": "r1", "license_id": "MIT",
        "source_record_hash": canonical_hash(["r1-source", ident]), "group_id": "r1-one-group",
        "split": "train", "category": "original_cpu",
        "tools": [], "messages": [{"role": "user", "content": "Describe the drawn ring.",
                                    "tool_calls": [], "tool_call_id": None}],
        "expected_action": {"kind": "final", "content": "The ring is blue.", "tool_calls": []},
    }


def literal_sequence(example):
    # The prompt deliberately includes an earlier message EOS. These literal
    # IDs and their labels are invented; no tokenizer or renderer is involved.
    return Sequence("R1 literal prompt.", encoded(example["expected_action"]).decode(),
                    (47, 151645, 48), (47, 151645, 48, 71, 72),
                    (47, 151645, 48, 71, 72, 151645), (0, 0, 0, 1, 1, 1), 151645)


def manual_record(ident):
    example = original_example(ident)
    seq = literal_sequence(example)
    data = seq.record() | {
        "causal_input_ids": [47, 151645, 48, 71, 72],
        "causal_target_ids": [151645, 48, 71, 72, 151645],
    }
    for key in ("causal_input_ids", "causal_target_ids"):
        data[key + "_sha256"] = canonical_hash(data[key])
    case = {
        "case_id": ident, "category": "original_protocol_only", "example": example,
        "audit": None, "profiles": {}, "primary_profile": "smoke", "encoding_mode": "reuse_original",
        "quality_revision_sha256": "e" * 64, "reviewer": None, "semantic_verdict": None,
        "token_mask_verdict": None, "enters_effective_training": False,
        "original_protocol_sequence": copy.deepcopy(data),
    }
    ids = [47, 151645, 48, 71, 72, 151645] + [151643] * 1018
    mask = [0, 0, 0, 1, 1, 1] + [0] * 1018
    padding = {
        "sequence_ids": ids, "attention_mask": [1] * 6 + [0] * 1018, "loss_mask": mask,
        "causal_input_ids": ids[:-1], "causal_target_ids": ids[1:], "causal_loss_mask": mask[1:],
        "bucket": 1024, "pad_token_id": 151643, "unpadded_length": 6,
        "effective_supervised_targets": 3, "first_supervised_causal_position": 2,
        "last_supervised_causal_position": 4,
    }
    return {
        "case": case, "sequence": data, "padding": padding,
        "source_binding": {**{k: example[k] for k in IDENTITY},
            "example_sha256": canonical_hash(example),
            "model_input_sha256": canonical_hash({k: example[k] for k in ("messages", "tools")}),
            "action_sha256": canonical_hash(example["expected_action"])},
        "budget_observations": {"context_including_eos": {str(c): True for c in (1024, 1536, 2048)},
            "response_256_including_eos": True, "used_to_promote_staged_annotation": False},
        "token_texts": ["invented token label"] * 6 + ["invented padding label"] * 1018,
    }


def test_prompt_eos_does_not_remove_completion_eos_or_shift_target():
    record = manual_record("protocol-r1-positive")
    seq, batch = v._batch_record(record, record["case"])
    assert seq.sequence_ids.count(151645) == 2
    assert batch.causal_target_ids[4] == 151645
    assert batch.causal_loss_mask[2:5] == (1, 1, 1)
    assert batch.causal_loss_mask[5:] == (0,) * 1018
    assert batch.record() == record["padding"]


@pytest.mark.parametrize("mutation", ["second_completion_eos", "prompt_float", "attention_bool",
                                      "causal_float", "missing_eos_loss", "padding_label_type"])
def test_original_record_rejects_numeric_and_boundary_changes(mutation):
    record = manual_record("protocol-r1-mutation")
    if mutation == "second_completion_eos":
        record["sequence"]["sequence_ids"][3] = 151645
    elif mutation == "prompt_float":
        record["sequence"]["prompt_ids"][1] = 151645.0
    elif mutation == "attention_bool":
        record["padding"]["attention_mask"][9] = False
    elif mutation == "causal_float":
        record["padding"]["causal_loss_mask"][7] = 0.0
    elif mutation == "missing_eos_loss":
        record["padding"]["causal_loss_mask"][4] = 0
    else:
        record["token_texts"][-1] = 151643
    with pytest.raises(DataError):
        v._batch_record(record, record["case"])


def array_validation(record):
    sequence, batch = record["sequence"], record["padding"]
    digest = hashlib.sha256(encoded(record) + b"\n").hexdigest()
    validation = {
        "status": "PASS", "record_file_sha256": digest, "record_canonical_sha256": canonical_hash(record),
        "all_7_unpadded_array_hashes": {k: canonical_hash(sequence[k]) for k in v._UNPADDED},
        "full_padded_arrays_sha256": canonical_hash(batch), "token_texts_sha256": canonical_hash(record["token_texts"]),
        "P": 3, "C_without_eos": 2, "N_including_eos": 6, "padding_bucket": 1024,
        "supervised_target_count": 3, "first_supervised_causal_position": 2,
        "last_supervised_causal_position": 4, "right_padding_tokens": 1018,
    }
    return validation, {"validation_record_sha256": canonical_hash(validation), "record_file_sha256": digest}, digest


def test_same_length_token_text_change_cannot_inherit_Q1_array_verdict():
    record = manual_record("protocol-r1-token-label")
    validation, judgment, digest = array_validation(record)
    v._validation(record, validation, judgment, digest)
    record["token_texts"][-1] = "changed padding label"
    with pytest.raises(DataError, match="validation_binding"):
        v._validation(record, validation, judgment, digest)


@pytest.fixture
def history_rows():
    config = json.loads((ROOT / "configs/training-data.v1.json").read_bytes())
    examples = sorted([original_example("r1-ring-" + str(i)) for i in range(5)],
                      key=lambda e: rank_key(e["example_id"]))
    source_a, source_b = canonical_hash(["retired-source-A"]), canonical_hash(["retired-source-B"])
    examples[0]["source_record_hash"] = examples[2]["source_record_hash"] = source_a
    examples[1]["source_record_hash"] = source_b
    original = {}
    for rank, example in enumerate(examples, 1):
        seq = literal_sequence(example)
        audit = seq.metadata() | {k: example[k] for k in IDENTITY}
        audit.update(common_binding_sha256=config["representation_common_binding_sha256"],
            example_sha256=canonical_hash(example), model_input_sha256=canonical_hash({k: example[k] for k in ("messages", "tools")}),
            action_sha256=canonical_hash(example["expected_action"]), parser_action_sha256=canonical_hash(example["expected_action"]),
            kind="final", sequence_error=None, parser_error=None, parser_accepted_exact=True,
            rendered_inverse_exact=True, raw_byte_cap_pass=True, raw_node_cap_pass=True, raw_depth_cap_pass=True,
            raw_byte_cap=131072, action_native_utf8_bytes=len(encoded(example["expected_action"])), action_nodes=4, action_depth=1,
            causal_input_ids_sha256=canonical_hash(list(seq.causal_input_ids)),
            causal_target_ids_sha256=canonical_hash(list(seq.causal_target_ids)),
            role_bindings_sha256=canonical_hash(["r1-original-literal-role-metadata"]))
        sidecar = {"profile": "smoke", "split": "train", "selection_rank": rank,
                   "ranking_sha256": rank_key(example["example_id"])[0], "padding_bucket": 1024, "audit": audit}
        line = json.dumps(example, ensure_ascii=False).encode() + b"\n"
        original[example["example_id"]] = (example, sidecar, line)
    previous = {}
    for ident, entry in original.items():
        if entry[0]["source_record_hash"] == source_a:
            continue
        e, s, line = copy.deepcopy(entry)
        s["selection_rank"] = len(previous) + 1
        previous[ident] = (e, s, line)
    current = {}
    for ident, entry in previous.items():
        if entry[0]["source_record_hash"] == source_b:
            continue
        e, s, line = copy.deepcopy(entry)
        parent = original[ident][1]
        s.update(selection_rank=len(current) + 1, parent_selection_rank=parent["selection_rank"],
            previous_selection_rank=entry[1]["selection_rank"], parent_sidecar_sha256=canonical_hash(parent),
            previous_selection_sidecar_sha256=canonical_hash(entry[1]), parent_selection_manifest_sha256="1" * 64,
            previous_selection_manifest_sha256="2" * 64, quality_revision_sha256="e" * 64,
            quality_config_file_sha256="4" * 64)
        current[ident] = (e, s, line)
    summary = {"effective_selected_count": 2, "selected_identity_sha256": canonical_hash(list(current)),
               "parent_selected_count": 5, "quarantined_counts": {"fail": 2, "unknown": 1}, "refill_count": 0}
    selection = {"parent_selection_manifest_file_sha256": "1" * 64,
        "previous_selection_manifest_file_sha256": "2" * 64, "quality_revision_sha256": "e" * 64,
        "quality_config_file_sha256": "4" * 64, "parent_training_config": config,
        "profiles": {"smoke": {"train": {"summary": copy.deepcopy(summary)}}}}
    return dict(current=current, original=original, previous=previous, excluded_sources={source_a, source_b},
        selection=selection, config={"data_binding": {"selection_manifest_file_sha256": "5" * 64},
            "view_summaries": {"smoke": {"train": copy.deepcopy(summary)}}}, profile="smoke", split="train")


def test_complete_source_removal_keeps_other_sources_in_same_group(history_rows):
    view, lines = v._linked_view(**history_rows)
    assert len(view) == 2
    assert {r.example["group_id"] for r in view.rows} == {"r1-one-group"}
    assert [(r.sidecar["parent_selection_rank"], r.sidecar["previous_selection_rank"], r.sidecar["selection_rank"])
            for r in view.rows] == [(4, 2, 1), (5, 3, 2)]
    assert view[0].example_bytes != next(iter(history_rows["current"].values()))[2]
    assert lines[0][-1] == hashlib.sha256(next(iter(history_rows["current"].values()))[2]).hexdigest()
    value = view[0].example
    value["messages"][0]["content"] = "external edit"
    assert view[0].example["messages"][0]["content"] == "Describe the drawn ring."
    with pytest.raises(FrozenInstanceError):
        view.rows = ()


@pytest.mark.parametrize("mutation", ["old_rank_epoch", "normalized_original_line", "source_reentry",
                                      "same_group_overdeletion", "changed_example", "staging_split"])
def test_three_generation_guards_are_not_replaced_by_recomputed_counts(history_rows, mutation):
    current = history_rows["current"]
    ident = next(iter(current))
    e, s, line = current[ident]
    if mutation == "old_rank_epoch":
        s["previous_selection_rank"] = s["parent_selection_rank"]
    elif mutation == "normalized_original_line":
        current[ident] = (e, s, encoded(e) + b"\n")
    elif mutation == "source_reentry":
        missing = next(i for i in history_rows["previous"] if i not in current)
        current[missing] = copy.deepcopy(history_rows["previous"][missing])
    elif mutation == "same_group_overdeletion":
        current.pop(ident)
    elif mutation == "changed_example":
        e["messages"][0]["content"] = "Same ID, different input"
    else:
        e["split"] = s["split"] = "staging"
    for summary in (history_rows["config"]["view_summaries"]["smoke"]["train"],
                    history_rows["selection"]["profiles"]["smoke"]["train"]["summary"]):
        summary.update(effective_selected_count=len(current), selected_identity_sha256=canonical_hash(list(current)))
    with pytest.raises(DataError):
        v._linked_view(**history_rows)


@pytest.fixture
def finite_review(monkeypatch):
    records = [manual_record("protocol-r1-export-" + str(i)) for i in range(13)]
    assert all(r["case"]["example"]["source"] == "r1-original-ring-fixture" for r in records)
    # This pin is replaced only for these invented private-kernel inputs. No
    # real record, manifest, or production prepare input is used by this fixture.
    monkeypatch.setattr(v, "MATERIALS_SHA256", canonical_hash(records))
    sequences, batches, items = [], [], []
    for record in records:
        seq, batch = v._batch_record(record, record["case"])
        sequences.append(seq)
        batches.append(batch)
        items.append({"original_record": record, "batch": copy.deepcopy(record["padding"]),
                      "Q1_judgment": {"fixture_only": True}, "original_producers": [{"fixture_epoch": 1}]})
    payload = {"scope": v.SCOPE, "config_file_sha256": v.CONFIG_SHA256, "input_manifest_file_sha256": v.INPUT_SHA256,
        "consumer": v.consumer_identity(), "new_sequence_calls": 0, "optimization_authorized": False,
        "training_authorized": False, "items": items}
    return v._review_arrays(encoded(payload) + b"\n", batches, sequences)


def private_output(tmp_path):
    root = tmp_path / ".toolalign-local"
    root.mkdir()
    return root / "export"


@pytest.mark.parametrize("stage", ["link", "remove_pending"])
def test_partial_publication_after_container_write_is_rejected(finite_review, tmp_path, monkeypatch, stage):
    output = private_output(tmp_path)
    if stage == "link":
        def fail_link(*args, **kwargs):
            raise OSError("R1 original link failure")
        monkeypatch.setattr(v.os, "link", fail_link)
    else:
        unlink = Path.unlink
        def fail_pending(path, *args, **kwargs):
            if path.name == ".manifest.pending":
                raise OSError("R1 original pending cleanup failure")
            return unlink(path, *args, **kwargs)
        monkeypatch.setattr(Path, "unlink", fail_pending)
    with pytest.raises(OSError, match="R1 original"):
        v.export_review_arrays(finite_review, output=output)
    assert (output / "review-arrays.json").is_file() and (output / ".manifest.pending").is_file()
    with pytest.raises(DataError, match="incomplete_export"):
        v.read_review_arrays(output=output, expected=finite_review)


@pytest.mark.parametrize("key", ["Q1_judgment", "original_producers"])
def test_rehashed_review_or_epoch_change_does_not_replace_expected(finite_review, tmp_path, key):
    output = private_output(tmp_path)
    manifest = v.export_review_arrays(finite_review, output=output)
    payload = finite_review.payload
    payload["items"][0][key] = {"counterfeit": True}
    raw = encoded(payload) + b"\n"
    (output / "review-arrays.json").write_bytes(raw)
    manifest["artifacts"]["review-arrays.json"] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    (output / "manifest.json").write_bytes(encoded(manifest) + b"\n")
    with pytest.raises(DataError, match="manifest_binding"):
        v.read_review_arrays(output=output, expected=finite_review)


def test_wrong_expected_consumer_is_rejected_before_output_creation(finite_review, tmp_path):
    payload = finite_review.payload
    payload["consumer"]["package_files"]["training/sft/data_v3.py"] = "0" * 64
    altered = v._review_arrays(encoded(payload), finite_review.batches, finite_review.sequences)
    output = private_output(tmp_path)
    with pytest.raises(DataError, match="export_consumer"):
        v.export_review_arrays(altered, output=output)
    assert not output.exists()


@pytest.mark.parametrize("payload", [b'{"n":1,"n":2}\n', b'{"n":1e999}\n', b'{"n":NaN}\n', b'{}'])
def test_json_lines_reject_ambiguous_values_and_missing_line_boundary(payload):
    with pytest.raises(DataError):
        v._rows(payload)


def test_old_configuration_rejected_before_manifest_access(tmp_path):
    config = tmp_path / "old-config.json"
    config.write_bytes(b'{"config_version":"toolalign.sft-cpu.v1"}')
    with pytest.raises(DataError, match="hash_mismatch"):
        v.prepare_v3(sft_config_path=config, input_manifest_path=tmp_path / "never-created")


def test_foreign_framework_rejected_before_path_access(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "mlx", object())
    with pytest.raises(DataError, match="cpu_only_process_required"):
        v.prepare_v3(sft_config_path=tmp_path / "never-created", input_manifest_path=tmp_path / "never-created")


def test_mixed_Q1_seal_uses_public_git_identity_without_opening_historical_path():
    private = {"relative_path": "small.json", "bytes": 2, "sha256": "b" * 64}
    public = {"kind": "public_at_commit", "repository_path": "reports/original.md", "bytes": 3,
              "sha256": "c" * 64, "commit": "a" * 40, "path": "/never-open-this-historical-path"}
    assert v._seal_members({"files": [private, public]}, "a" * 40) == {"small.json": private}
    public["commit"] = "d" * 40
    with pytest.raises(DataError, match="public_commit"):
        v._seal_members({"files": [private, public]}, "a" * 40)
