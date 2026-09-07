"""Original character-token fixtures; these are not Qwen engine measurements."""

import copy
from dataclasses import replace
from html.parser import HTMLParser

import pytest
from quality_cases import example, inputs
from training_binding_cases import example as protocol_example

from toolalign.contracts import canonical_hash
from toolalign.data import quality_materials as m
from toolalign.data import quality_revision as q
from toolalign.data.common import DataError, encoded
from toolalign.model_io import TEMPLATE_SHA256, training_sequence


class OriginalCharacterAdapter:
    """Trusted fixture injection only; production CLI uses OfflineQwenTokenizer."""

    def __init__(self, profile="smoke", engine="tokenizers"):
        self.profile, self.engine = profile, engine

    @property
    def identity(self):
        return {"repo_id": "Qwen/Qwen3-0.6B" if self.profile == "smoke" else "Qwen/Qwen3-1.7B",
                "revision": "c1899de289a04d12100db370d81485cdf75e47ca" if self.profile == "smoke"
                else "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e", "engine": self.engine,
                "fixture_notice": "Original synthetic character tokens; no real model/tokenizer measurement.",
                "files": {}, "template_sha256": TEMPLATE_SHA256, "eos_token": "<|im_end|>",
                "eos_token_id": 151645, "render_parameters": {}, "encoding_parameters": {}}

    def training_sequence(self, value):
        return training_sequence(value, renderer=lambda *a, **k: "ORIGINAL FIXTURE PROMPT",
            encoder=lambda text, **kw: [151645] if text == "<|im_end|>" else [ord(c) for c in text],
            decoder=self.decode, eos_token_id=151645, template_sha256=TEMPLATE_SHA256)

    def decode(self, ids, **kwargs):
        return "".join("<|im_end|>" if i == 151645 else "<|endoftext|>" if i == 151643 else chr(i) for i in ids)


def case_fixture():
    source = inputs()
    staged = q.stage_annotations(source["index"], source["issues"], source["drafts"], source["source_evidence"], "revision")
    originals = [example("new-effective-" + str(i), i * 2 + 1) for i in range(12)]
    originals = sorted(originals, key=lambda e: q.rank_key(e["example_id"]))
    source["index"]["examples"].update({e["example_id"]: e for e in originals})
    source["index"]["lineage"].update({e["example_id"]: {"original_fixture_lineage": e["example_id"]} for e in originals})
    source["original_bytes"].update({e["example_id"]: encoded(e) + b"\n" for e in originals})
    artifacts = {}
    for p in q.PROFILES:
        values = originals[:7] if p == "smoke" else originals
        sidecars = []
        for rank, value in enumerate(values, 1):
            seq = OriginalCharacterAdapter(p).training_sequence(value)
            audit = {**seq.metadata(), **{k: value[k] for k in q.IDENTITY}, "example_sha256": canonical_hash(value),
                     "causal_input_ids_sha256": canonical_hash(list(seq.causal_input_ids)),
                     "causal_target_ids_sha256": canonical_hash(list(seq.causal_target_ids))}
            sidecars.append({"audit": audit, "selection_rank": rank, "parent_selection_rank": rank + 2, "padding_bucket": 1024})
        artifacts[f"selection/{p}/train.examples.jsonl"] = b"".join(encoded(e) + b"\n" for e in values)
        artifacts[f"selection/{p}/train.sidecars.jsonl"] = b"".join(encoded(r) + b"\n" for r in sidecars)
    artifacts["staging/examples.jsonl"] = b"".join(encoded(e) + b"\n" for e in staged["examples"])
    artifacts["staging/sidecars.jsonl"] = b"".join(encoded(e) + b"\n" for e in staged["sidecars"])
    old = {"old-flagged": {"case": {"example": list(source["index"]["examples"].values())[0],
                                    "category": "actual_selected_train", "case_id": "old-flagged"}}}
    for k in ("final", "clarify", "refuse"):
        old["protocol-" + k] = {"case": {"example": protocol_example("quality-protocol-" + k, kind=k, content="原创协议 " + k),
                                         "category": "original_protocol_only", "case_id": "protocol-" + k}}
    source["old_token_cases"] = old
    manifest = {"quality_revision_sha256": "revision", "annotations": {"direct_action_revisions": 1}}
    return source, artifacts, manifest


def test_effective_rules_use_new_selection_and_separate_all_staged_and_protocol_cases():
    source, artifacts, manifest = case_fixture()
    cases, coverage = m.choose_cases(source, artifacts, manifest)
    assert len(cases) == 15 and coverage["distinct_count"] == 15
    assert [c["case_id"] for c in cases[:10]] == [f"effective-{i:02d}" for i in range(1, 11)]
    assert all(c["example"]["source_record_hash"] not in source["issues"] for c in cases[:10])
    assert all(c["previous_material_case_id"] is None for c in cases[:10])
    assert all(c["semantic_verdict"] is None for c in cases)
    assert all(c["profiles"][p]["parent_selection_rank"] > c["profiles"][p]["selection_rank"]
               for c in cases[:10] for p in c["profiles"])
    assert {c["example"]["expected_action"]["kind"] for c in cases[10:13]} == {"final", "clarify", "refuse"}
    assert all(c["audit"] is None and c["enters_effective_training"] is False for c in cases[13:])
    assert cases[-1]["annotation"]["inherited_observations"][0]["status"] == "UNVERIFIED_AFTER_ACTION_CHANGE"


@pytest.mark.parametrize("mutation", ["staged_identity", "promotion", "quarantine_leak", "case_budget"])
def test_case_preparation_refuses_staged_or_quarantined_effective_inputs(mutation):
    source, artifacts, manifest = case_fixture()
    if mutation in {"staged_identity", "promotion"}:
        rows = q.jsonl(artifacts["staging/sidecars.jsonl"])[0]
        if mutation == "staged_identity":
            rows[0]["example_sha256"] = "0" * 64
        else:
            rows[0]["enters_effective_training"] = True
        artifacts["staging/sidecars.jsonl"] = b"".join(encoded(r) + b"\n" for r in rows)
    elif mutation == "quarantine_leak":
        values = q.jsonl(artifacts["selection/formal/train.examples.jsonl"])[0]
        for e in values:
            source["issues"][e["source_record_hash"]] = {"fixture": "quarantined"}
    else:
        source["config"]["materials"]["new_case_limit_per_engine"] = 14
    with pytest.raises(DataError):
        m.choose_cases(source, artifacts, manifest)


def test_full_staged_arrays_bind_changed_action_and_do_not_promote_on_budget_success():
    cases, _ = m.choose_cases(*case_fixture())
    adapter = OriginalCharacterAdapter("formal")
    case = cases[-1]
    seq = adapter.training_sequence(case["example"])
    record = m.sequence_record(case, seq)
    p, n, pad = len(seq.prompt_ids), len(seq.sequence_ids), record["padding"]
    assert pad["causal_loss_mask"][p - 2:p] == [0, 1]
    assert pad["causal_target_ids"][n - 2] == 151645
    assert pad["causal_loss_mask"][n - 2:n] == [1, 0]
    assert sum(pad["causal_loss_mask"]) == n - p
    assert len(pad["sequence_ids"]) == len(pad["attention_mask"]) == len(pad["loss_mask"])
    assert record["source_binding"]["model_input_sha256"] == canonical_hash({k: case["example"][k] for k in ("messages", "tools")})
    assert record["budget_observations"]["used_to_promote_staged_annotation"] is False
    assert case["annotation"]["downstream_condition_verified"] is False


def test_staged_display_bucket_can_exceed_training_cap_without_claiming_capacity():
    cases, _ = m.choose_cases(*case_fixture())
    case = cases[-2]
    # A long original prompt exercises display-only padding above the 2048 cap.
    seq = OriginalCharacterAdapter("formal").training_sequence(case["example"])
    prefix = (42,) * 3000
    seq = replace(seq, prompt_text="*" * 3000 + seq.prompt_text,
                  prompt_ids=prefix + seq.prompt_ids, concatenated_ids=prefix + seq.concatenated_ids,
                  sequence_ids=prefix + seq.sequence_ids, loss_mask=(0,) * 3000 + seq.loss_mask)
    record = m.sequence_record(case, seq)
    assert record["padding"]["bucket"] > 2048
    assert record["budget_observations"]["context_including_eos"]["2048"] is False
    assert record["budget_observations"]["used_to_promote_staged_annotation"] is False


@pytest.mark.parametrize("mutation", ["eos", "mask", "prefix", "action", "old_audit"])
def test_material_sequence_refuses_replaced_arrays_or_historical_binding(mutation):
    cases, _ = m.choose_cases(*case_fixture())
    case = cases[0] if mutation == "old_audit" else cases[-2]
    seq = OriginalCharacterAdapter().training_sequence(case["example"])
    if mutation == "eos":
        seq = replace(seq, sequence_ids=seq.sequence_ids[:-1] + (151643,))
    elif mutation == "mask":
        seq = replace(seq, loss_mask=(1,) * len(seq.sequence_ids))
    elif mutation == "prefix":
        seq = replace(seq, prompt_ids=(42,) + seq.prompt_ids[1:])
    elif mutation == "action":
        seq = replace(seq, completion_text="{}")
    else:
        case["audit"]["prompt_ids_sha256"] = "0" * 64
    with pytest.raises(DataError):
        m.sequence_record(case, seq)


def test_static_html_contains_every_token_and_unverified_provenance_as_escaped_text():
    cases, _ = m.choose_cases(*case_fixture())
    case = cases[-1]
    case["annotation"]["reason"] = '</pre><script>alert("original-fixture")</script>'
    adapter = OriginalCharacterAdapter()
    record = m.sequence_record(case, adapter.training_sequence(case["example"]))
    record["token_texts"] = [adapter.decode([i]) for i in record["padding"]["sequence_ids"]]
    page = m.render_page(record)

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags, self.text, self.rows = [], [], 0

        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)
            self.rows += tag == "tr"
            assert not any(k.startswith("on") for k, _ in attrs)

        def handle_data(self, text):
            self.text.append(text)

    parser = Parser()
    parser.feed(page)
    assert not {"script", "iframe", "img", "object", "form"} & set(parser.tags)
    assert parser.rows == record["padding"]["bucket"] + 1
    assert "UNVERIFIED_AFTER_ACTION_CHANGE" in "".join(parser.text)
    assert record["sequence"]["completion_text"] in "".join(parser.text)


def test_two_fixture_measurements_compare_complete_records_and_leave_verdicts_blank(tmp_path):
    cases, coverage = m.choose_cases(*case_fixture())
    roots = {}
    for engine in ("transformers", "tokenizers"):
        roots[engine] = tmp_path / ".toolalign-local" / engine
        manifest = m.write_measurement(cases, coverage,
            tokenizers_by_profile={p: OriginalCharacterAdapter(p, engine) for p in q.PROFILES},
            output=roots[engine], revision_manifest_sha256="original-fixture-manifest")
        assert manifest["unique_examples"] == 15
        assert m.checked_measurement(roots[engine], engine)[0] == manifest
    result = m.compare(reference=roots["transformers"], native=roots["tokenizers"])
    assert result["unique_examples"] == 15 and result["engine_measurements"] == 30
    assert result["semantic_verdicts_filled"] == 0 and result["training_authorized"] is False


def test_tokenizer_failure_leaves_no_material_manifest_or_directory(tmp_path):
    cases, coverage = m.choose_cases(*case_fixture())

    class Broken(OriginalCharacterAdapter):
        def training_sequence(self, example):
            raise DataError("original_fixture_encoder_failure")

    output = tmp_path / ".toolalign-local" / "failure"
    with pytest.raises(DataError):
        m.write_measurement(cases, coverage, tokenizers_by_profile={p: Broken(p) for p in q.PROFILES},
                            output=output, revision_manifest_sha256="original-fixture")
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["duplicate", "case_name", "wrong_model"])
def test_material_budget_identity_and_model_guards_precede_publication(tmp_path, mutation):
    cases, coverage = m.choose_cases(*case_fixture())
    adapters = {p: OriginalCharacterAdapter(p) for p in q.PROFILES}
    if mutation == "duplicate":
        cases[-1] = copy.deepcopy(cases[0])
    elif mutation == "case_name":
        cases[0]["case_id"] = "../outside"
    else:
        adapters["formal"] = OriginalCharacterAdapter("smoke")
    output = tmp_path / ".toolalign-local" / "bad"
    with pytest.raises(DataError):
        m.write_measurement(cases, coverage, tokenizers_by_profile=adapters, output=output, revision_manifest_sha256="fixture")
    assert not output.exists()


def test_production_cli_requires_offline_environment_before_loading_or_creating(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_TORCH", "1")
    output = tmp_path / ".toolalign-local" / "never"
    assert m.main(["measure", "--inputs-path", str(tmp_path / "missing"), "--revision", str(tmp_path / "missing"),
                   "--tokenizer-root", str(tmp_path / "missing"), "--engine", "tokenizers", "--output", str(output)]) == 1
    assert not output.exists()
