"""Complete-array and fixed-case binding checks using original character tokens."""

import copy
import json
from dataclasses import replace

import pytest
from test_quality_materials import OriginalCharacterAdapter, case_fixture

from toolalign.data import quality_adjudication_materials as m
from toolalign.data import quality_materials as qm
from toolalign.data import quality_revision as q
from toolalign.data.common import DataError, encoded


def materials_fixture():
    source, artifacts, manifest = case_fixture()
    source["sources"] = {k: {"disposition": "exclude_entire_source"} for k in source["issues"]}
    source["buffers"] = {}
    for name, original in source["old_token_cases"].items():
        if not name.startswith("protocol-"):
            continue
        case = original["case"] | {"audit": None, "profiles": {}, "primary_profile": "smoke"}
        seq = OriginalCharacterAdapter().training_sequence(case["example"])
        record = {"case": case, "sequence": qm.sequence_record(case, seq)["sequence"]}
        source["buffers"]["protocol/" + name + ".json"] = encoded(record)
    return source, artifacts, manifest


def test_thirteen_identities_frozen_before_engine_use_with_no_staging_or_verdicts():
    source, artifacts, manifest = materials_fixture()
    artifacts["manifest.json"] = encoded(manifest)
    frozen, selection, cases, coverage = m.freeze_artifacts(source, artifacts, manifest)
    assert selection["new_tokenization_runs"] == 0 and selection["unique_examples"] == 13
    assert len(cases) == 13 and {c["case_id"] for c in cases} == m.CASE_NAMES
    assert all(c["semantic_verdict"] is None and c["token_mask_verdict"] is None and c["reviewer"] is None for c in cases)
    assert coverage["existing_staging_reencoded"] is False
    assert json.loads(frozen["cases.json"]) == cases
    assert all(c["enters_effective_training"] is False and c["original_protocol_sequence"] for c in cases[10:])


@pytest.mark.parametrize("mutation", ["mask_bool", "ids_bool", "eos_bool", "padding_float", "audit_prefix_int", "protocol_prompt"])
def test_sequence_and_historical_type_substitutions_are_rejected(mutation):
    cases, _ = m.choose_cases(*materials_fixture())
    case = copy.deepcopy(cases[10] if mutation == "protocol_prompt" else cases[0])
    seq = OriginalCharacterAdapter().training_sequence(case["example"])
    if mutation == "mask_bool":
        seq = replace(seq, loss_mask=(False,) + seq.loss_mask[1:])
    elif mutation == "ids_bool":
        seq = replace(seq, prompt_ids=(True,) + seq.prompt_ids[1:])
    elif mutation == "eos_bool":
        seq = replace(seq, eos_token_id=True)
    elif mutation == "padding_float":
        case["profiles"][case["primary_profile"]]["padding_bucket"] = 1024.0
    elif mutation == "audit_prefix_int":
        case["audit"]["prefix_stable"] = 1
    else:
        seq = replace(seq, prompt_text="different prompt")
    with pytest.raises(DataError):
        m.typed_sequence_record(case, seq)


@pytest.mark.parametrize("field", ["case", "causal_loss_mask", "padding_attention", "padding_loss", "source_binding", "budget_bool"])
def test_reconstructed_record_rejects_complete_array_or_binding_tampering(field):
    cases, _ = m.choose_cases(*materials_fixture())
    case = cases[0]
    adapter = OriginalCharacterAdapter()
    record = m.typed_sequence_record(case, adapter.training_sequence(case["example"]))
    record["token_texts"] = [adapter.decode([i]) for i in record["padding"]["sequence_ids"]]
    m.checked_record(record, case)
    if field == "case":
        record["case"]["semantic_verdict"] = "pass"
    elif field == "causal_loss_mask":
        record["sequence"]["causal_loss_mask"][0] = False
    elif field == "padding_attention":
        record["padding"]["attention_mask"][-1] = False
    elif field == "padding_loss":
        record["padding"]["loss_mask"][-1] = 1
    elif field == "source_binding":
        record["source_binding"]["action_sha256"] = "0" * 64
    else:
        record["budget_observations"]["used_to_promote_staged_annotation"] = 0
    with pytest.raises(DataError):
        m.checked_record(record, case)


def test_material_publication_keeps_blank_review_fields_and_detects_forged_html(tmp_path):
    cases, coverage = m.choose_cases(*materials_fixture())
    frozen = {"manifest.json": b"original fixture frozen manifest"}
    out = tmp_path / ".toolalign-local" / "material"
    result = m.write_measurement(cases, coverage, tokenizers_by_profile={p: OriginalCharacterAdapter(p) for p in q.PROFILES},
                                 output=out, selection_manifest_data=frozen["manifest.json"])
    mf, records = m.checked_measurement(out, "tokenizers", cases, coverage, frozen)
    assert result == mf and len(records) == 13
    assert all(all(row[k] == "" for k in m.CSV_FIELDS[5:]) for row in q.csv_rows((out / "review.csv").read_bytes()))
    record = records[0]
    p, n = record["sequence"]["prompt_tokens"], record["sequence"]["total_tokens"]
    assert record["padding"]["causal_loss_mask"][p - 1] == 1
    assert record["padding"]["causal_target_ids"][n - 2] == 151645
    assert not any(record["padding"]["causal_loss_mask"][n - 1:])
    (out / (cases[0]["case_id"] + ".html")).write_text("forged page")
    with pytest.raises(DataError, match="input_hash_mismatch"):
        m.checked_measurement(out, "tokenizers", cases, coverage, frozen)


def test_failed_material_write_does_not_publish_manifest(tmp_path, monkeypatch):
    cases, coverage = m.choose_cases(*materials_fixture())
    out = tmp_path / ".toolalign-local" / "material"
    monkeypatch.setattr(q.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("original fixture failure")))
    with pytest.raises(OSError):
        m.write_measurement(cases, coverage, tokenizers_by_profile={p: OriginalCharacterAdapter(p) for p in q.PROFILES},
                            output=out, selection_manifest_data=b"original fixture frozen manifest")
    assert not (out / "manifest.json").exists()
