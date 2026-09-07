"""R1 negative controls using only the repository's original CPU fixtures."""

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests/data"))

from adjudication_cases import revision_fixture, source_fixture  # noqa: E402
from test_quality_adjudication_materials import materials_fixture  # noqa: E402
from test_quality_materials import OriginalCharacterAdapter  # noqa: E402

from toolalign.contracts import canonical_hash  # noqa: E402
from toolalign.data import quality_adjudication as a  # noqa: E402
from toolalign.data import quality_adjudication_materials as m  # noqa: E402
from toolalign.data.common import DataError, encoded  # noqa: E402


def test_duplicate_physical_sources_require_every_original_index():
    index, row, packet, raw, _ = source_fixture()
    raw.append(copy.deepcopy(raw[0]))
    index["assignments"][1] = dict(index["assignments"][0], source_index=1)
    row["source_indices"] = [0, 1]
    packet["identity"]["source_indices"] = [0, 1]
    assert len(a.source_members(index, row, packet, raw)) == 3
    row["source_indices"] = [0]
    packet["identity"]["source_indices"] = [0]
    with pytest.raises(DataError, match="disposition_all_source_indices"):
        a.source_members(index, row, packet, raw)


@pytest.mark.parametrize("field", ["action_argument", "lineage_turn"])
def test_float_aliases_cannot_replace_original_integer_values(field):
    index, row, packet, raw, _ = source_fixture()
    if field == "action_argument":
        packet["valid_decisions"][0]["example"]["expected_action"]["tool_calls"][0]["arguments"]["value"] = 0.0
    else:
        value = packet["valid_decisions"][0]["lineage"]["source_turn_index"]
        packet["valid_decisions"][0]["lineage"]["source_turn_index"] = float(value)
    with pytest.raises(DataError, match="packet_(example|lineage)_type_or_identity"):
        a.source_members(index, row, packet, raw)


def test_call_index_type_remains_strict_after_rehashing_the_review():
    index, row, packet, _, buffers = source_fixture()
    name = row["adjudication"]["file"]
    record = json.loads(buffers[name])
    record["decisions"][0]["calls"][0]["call_index"] = 0.0
    buffers[name] = encoded(record)
    row["adjudication"]["source_record_sha256"] = canonical_hash(record)
    with pytest.raises(DataError, match="review_call_index"):
        a.reviewed_source(row, buffers, index, packet)


def test_zero_cannot_replace_the_false_training_authorization(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "bound_inputs", lambda **_: revision_fixture())
    output = tmp_path / ".toolalign-local/revision"
    a.build(output=output, config_path="original-fixture", input_root="original-fixture")
    a.verify(output=output, config_path="original-fixture", input_root="original-fixture")
    path = output / "run.json"
    run = json.loads(path.read_bytes())
    run["training_authorized"] = 0
    path.write_bytes(encoded(run))
    with pytest.raises(DataError, match="output_authorization_binding"):
        a.verify(output=output, config_path="original-fixture", input_root="original-fixture")


@pytest.mark.parametrize("addition", ["extra_file", "nested_symlink"])
def test_unlisted_output_and_symlink_members_are_rejected(tmp_path, monkeypatch, addition):
    monkeypatch.setattr(a, "bound_inputs", lambda **_: revision_fixture())
    output = tmp_path / ".toolalign-local/revision"
    a.build(output=output, config_path="original-fixture", input_root="original-fixture")
    if addition == "extra_file":
        (output / "effective/unlisted.json").write_bytes(b"{}\n")
        reason = "output_artifact_set"
    else:
        (output / "effective/linked.json").symlink_to(output / "effective/train.jsonl")
        reason = "output_symlink"
    with pytest.raises(DataError, match=reason):
        a.verify(output=output, config_path="original-fixture", input_root="original-fixture")


@pytest.mark.parametrize("field", ["prompt_tokens", "causal_target_ids"])
def test_full_material_record_rejects_equal_numeric_aliases(field):
    cases, _ = m.choose_cases(*materials_fixture())
    case = cases[0]
    adapter = OriginalCharacterAdapter()
    record = m.typed_sequence_record(case, adapter.training_sequence(case["example"]))
    record["token_texts"] = [adapter.decode([i]) for i in record["padding"]["sequence_ids"]]
    m.checked_record(record, case)
    if field == "prompt_tokens":
        record["sequence"][field] = float(record["sequence"][field])
    else:
        record["padding"][field][0] = float(record["padding"][field][0])
    with pytest.raises(DataError, match="material_complete_record_binding"):
        m.checked_record(record, case)
