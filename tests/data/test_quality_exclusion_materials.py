"""Original character records exercise reuse without any real tokenizer call."""

import copy
import json

import pytest
from test_quality_adjudication_materials import materials_fixture
from test_quality_materials import OriginalCharacterAdapter

from toolalign.contracts import canonical_hash
from toolalign.data import quality_adjudication_materials as am
from toolalign.data import quality_exclusion_materials as m
from toolalign.data import quality_revision as q
from toolalign.data.common import DataError, encoded


def reuse_fixture():
    original, coverage = am.choose_cases(*materials_fixture())
    adapter = OriginalCharacterAdapter()
    records = {}
    for case in original:
        record = am.typed_sequence_record(case, adapter.training_sequence(case["example"]))
        record["token_texts"] = [adapter.decode([i]) for i in record["padding"]["sequence_ids"]]
        records[case["example"]["example_id"]] = record
    cases = copy.deepcopy(original)
    for i, case in enumerate(cases):
        old = original[i]
        case.update(quality_revision_sha256="original-v3-fixture", previous_material_case_id=old["case_id"], encoding_mode="reuse_original")
        for profile in case["profiles"].values():
            profile["previous_selection_rank"] = profile["selection_rank"]
            profile["selection_rank"] += 3
        if i in (5, 6):
            case.update(encoding_mode="new_fixed_example", previous_material_case_id=None)
            case["example"]["source_record_hash"] = canonical_hash(["original new source", i])
            case["example"]["example_id"] = q.normalized_id(case["example"])
            for key in q.IDENTITY:
                case["audit"][key] = case["example"][key]
            case["audit"]["example_sha256"] = canonical_hash(case["example"])
    # Reorder two surviving case labels: reuse must follow Example identity.
    cases[7]["case_id"], cases[8]["case_id"] = cases[8]["case_id"], cases[7]["case_id"]
    parent = {"records": records, "provenance": {"original_fixture_encoding": "original-time-and-source"},
        "prefix": "original-parent/", "manifest": {"tokenizers": {p: OriginalCharacterAdapter(p).identity for p in q.PROFILES}, "artifacts": {
            r["case"]["case_id"] + ".json": {"sha256": q.sha(encoded(r) + b"\n"), "size_bytes": len(encoded(r)) + 1}
            for r in records.values()}}}
    policy = {"retained_example_ids": sorted(c["example"]["example_id"] for c in cases if c["encoding_mode"] == "reuse_original"),
              "retained_case_count_per_engine": 11, "new_example_ids": [c["example"]["example_id"] for c in cases if c["encoding_mode"] == "new_fixed_example"]}
    coverage["quality_revision_sha256"] = "original-v3-fixture"
    return cases, parent, policy, coverage


def test_reuse_maps_by_example_preserves_all_arrays_and_makes_zero_adapter_calls(monkeypatch):
    cases, parent, policy, _ = reuse_fixture()
    snapshot = copy.deepcopy(parent)
    monkeypatch.setattr(OriginalCharacterAdapter, "training_sequence", lambda *args: pytest.fail("reused example encoded again"))
    records, proof = m.reused_records(cases, parent, policy)
    assert len(records) == len(proof["records"]) == 11 and parent == snapshot
    assert {r["case"]["example"]["example_id"] for r in records} == set(policy["retained_example_ids"])
    for record in records:
        old = parent["records"][record["case"]["example"]["example_id"]]
        assert encoded({k: record[k] for k in m.ARRAY_FIELDS}) == encoded({k: old[k] for k in m.ARRAY_FIELDS})
        assert record["case"]["quality_revision_sha256"] == "original-v3-fixture"
        assert record["case"]["previous_material_case_id"] == old["case"]["case_id"]
    assert any(r["case"]["case_id"] != r["case"]["previous_material_case_id"] for r in records)
    assert all(row["new_tokenizer_calls"] == 0 for row in proof["records"])
    pages = m.review_artifacts(records)
    assert b"ToolAlign v3" in pages["index.html"]
    assert all(all(row[k] == "" for k in am.CSV_FIELDS[5:]) for row in q.csv_rows(pages["review.csv"]))


@pytest.mark.parametrize("mutation", ["wrong_example", "old_case_id", "array_bool", "padding_bool", "token_text_string", "token_text_type"])
def test_reuse_rejects_replaced_example_arrays_padding_and_tokens(mutation):
    cases, parent, policy, _ = reuse_fixture()
    ident = cases[0]["example"]["example_id"]
    old = parent["records"][ident]
    if mutation == "wrong_example":
        parent["records"][ident] = copy.deepcopy(parent["records"][cases[1]["example"]["example_id"]])
    elif mutation == "old_case_id":
        cases[0]["previous_material_case_id"] = cases[1]["case_id"]
    elif mutation == "array_bool":
        old["sequence"]["loss_mask"][0] = False
    elif mutation == "padding_bool":
        old["padding"]["attention_mask"][0] = True
    elif mutation == "token_text_string":
        old["token_texts"][0] = "different token text"
    else:
        old["token_texts"][0] = 1
    with pytest.raises(DataError):
        m.reused_records(cases, parent, policy)


@pytest.mark.parametrize("field", ["prompt_ids", "concatenated_ids", "sequence_ids", "loss_mask", "causal_loss_mask", "eos_token_id"])
def test_reconstructed_old_record_rejects_numeric_type_substitution(field):
    cases, parent, _, _ = reuse_fixture()
    old = parent["records"][cases[0]["example"]["example_id"]]
    if field == "eos_token_id":
        old["sequence"][field] = float(old["sequence"][field])
    else:
        old["sequence"][field][0] = float(old["sequence"][field][0])
    with pytest.raises(DataError):
        m.reuse_record(cases[0], old)


@pytest.mark.parametrize("mutation", ["count", "identity_set", "case_mode", "different_revision_case"])
def test_reuse_rejects_scope_or_frozen_case_mismatch(mutation):
    cases, parent, policy, _ = reuse_fixture()
    if mutation == "count":
        cases.append(copy.deepcopy(cases[0]))
    elif mutation == "identity_set":
        policy["retained_example_ids"][0] = "another-original-id"
    elif mutation == "case_mode":
        cases[0]["encoding_mode"] = "new_fixed_example"
    else:
        old = parent["records"][cases[0]["example"]["example_id"]]
        old["case"]["quality_revision_sha256"] = "original-v3-fixture"
    with pytest.raises(DataError):
        m.reused_records(cases, parent, policy)


@pytest.mark.parametrize("mutation", ["manifest", "source", "contract", "scope"])
def test_parent_run_binding_rejects_wrong_parent_run(mutation):
    data = b"original-manifest"
    identity = {"package_files": {"original.py": "a" * 64}, "contract_sha256": "b" * 64}
    run = {"stable_manifest_sha256": q.sha(data), "consumer": copy.deepcopy(identity), "training_authorized": False,
        "model_modules_loaded": [], "created_at_utc": "2026-09-07T00:00:00+00:00", "output_path": "original-private-output"}
    buffers = {"old/run.json": encoded(run)}
    assert m.checked_run(buffers, "old/", data, identity) == run
    if mutation == "manifest":
        run["stable_manifest_sha256"] = "0" * 64
    elif mutation == "source":
        run["consumer"]["package_files"]["original.py"] = "0" * 64
    elif mutation == "contract":
        run["consumer"]["contract_sha256"] = "0" * 64
    else:
        run["training_authorized"] = 0
    buffers["old/run.json"] = encoded(run)
    with pytest.raises(DataError):
        m.checked_run(buffers, "old/", data, identity)


def publication_fixture(monkeypatch):
    cases, parent, policy, coverage = reuse_fixture()
    inputs = {"config": {"materials": policy}}
    frozen = {"manifest.json": b"original frozen v3 selection"}
    monkeypatch.setattr(m, "bound_selection", lambda **kw: (inputs, frozen, {}, cases, coverage))
    monkeypatch.setattr(m, "parent_measurement", lambda *args: parent)
    return cases


@pytest.mark.parametrize("mutation", ["revision", "full_sequence", "token_texts", "html", "parent_provenance", "publisher_run"])
def test_published_reuse_rejects_changed_binding_or_payload(tmp_path, monkeypatch, mutation):
    cases = publication_fixture(monkeypatch)
    root = tmp_path / ".toolalign-local" / "reused"
    m.reuse(output=root, engine="tokenizers")
    assert m.verify_reuse(output=root, engine="tokenizers")["new_tokenizer_calls"] == 0
    if mutation == "revision":
        path = root / "manifest.json"
        record = json.loads(path.read_bytes())
        record["quality_revision_sha256"] = "original-v2-fixture"
    elif mutation == "publisher_run":
        path = root / "run.json"
        record = json.loads(path.read_bytes())
        record["consumer"]["package_files"]["data/quality_exclusion_materials.py"] = "0" * 64
    elif mutation == "parent_provenance":
        path = root / "encoding-provenance.json"
        record = json.loads(path.read_bytes())
        record["parent_encoding"]["original_fixture_encoding"] = "replacement-time-and-source"
    elif mutation == "html":
        (root / (cases[0]["case_id"] + ".html")).write_text("replaced original page")
        with pytest.raises(DataError):
            m.verify_reuse(output=root, engine="tokenizers")
        return
    else:
        path = root / (cases[0]["case_id"] + ".json")
        record = json.loads(path.read_bytes())
        if mutation == "full_sequence":
            record["sequence"]["loss_mask"][0] = False
        else:
            record["token_texts"][0] = "changed text"
    path.write_bytes(encoded(record) + b"\n")
    with pytest.raises(DataError):
        m.verify_reuse(output=root, engine="tokenizers")


def test_failed_static_publication_has_no_success_manifest(tmp_path, monkeypatch):
    publication_fixture(monkeypatch)
    root = tmp_path / ".toolalign-local" / "reused"
    root.parent.write_bytes(b"an original file cannot be a directory")
    with pytest.raises(OSError):
        m.reuse(output=root, engine="tokenizers")
    assert not (root / "manifest.json").exists()


def test_two_engine_reuse_comparison_counts_records_without_new_measurements(tmp_path, monkeypatch):
    publication_fixture(monkeypatch)
    left, right = [tmp_path / ".toolalign-local" / name for name in ("reference", "native")]
    m.reuse(output=left, engine="transformers")
    m.reuse(output=right, engine="tokenizers")
    compared = m.compare_reuse(reference=left, native=right)
    assert compared["unique_examples"] == 11 and compared["engine_records"] == 22
    assert compared["new_sequence_calls"] == 0 and compared["semantic_verdicts_filled"] == 0


def encoding_fixture():
    cases, parent, policy, coverage = reuse_fixture()
    original_tokenizer = OriginalCharacterAdapter().identity
    profiles = {p: {"model_id": OriginalCharacterAdapter(p).identity["repo_id"],
                    "model_revision": OriginalCharacterAdapter(p).identity["revision"]} for p in q.PROFILES}
    inputs = {"config": {"materials": policy}, "parent": {"parent_config": {"profiles": profiles},
        "binding": {"parent_selection_input_binding": {"historical_measurement": {"tokenizer": original_tokenizer}}}}}
    release = {"material_example_ids": policy["new_example_ids"], "issued_at_utc": "2026-01-01T00:00:00+00:00",
        "q1_review_commit": "original-review", "q1_source_seal_sha256": "a" * 64, "q1_final_seal_sha256": "b" * 64,
        "q1_adjudications_sha256": "c" * 64, "s0_formal_receipt_proof_sha256": "d" * 64, "review_scope": "SOURCE_SEMANTICS_ONLY"}
    return cases, parent, policy, coverage, inputs, release


def write_original_measurement(tmp_path, *, cases, parent, policy, coverage, inputs, release, fail=False, output_name="complete"):
    calls = []

    class CountingAdapter(OriginalCharacterAdapter):
        def training_sequence(self, example):
            calls.append(example["example_id"])
            if fail:
                raise ValueError("original fixture sequence failure")
            return super().training_sequence(example)

    arguments = dict(parent=parent, policy=policy, frozen={"manifest.json": b"original-frozen"}, release=release,
        tokenizers_by_profile={p: CountingAdapter(p) for p in q.PROFILES},
        expected_tokenizers=am.expected_tokenizer_bindings(inputs["parent"]), engine="tokenizers",
        output=tmp_path / ".toolalign-local" / output_name, budget_root=tmp_path / ".toolalign-local" / "budget",
        release_path=tmp_path / "original-release.json")
    return calls, arguments


def test_exactly_two_new_sequences_are_called_and_a_second_invocation_is_rejected(tmp_path, monkeypatch):
    cases, parent, policy, coverage, inputs, release = encoding_fixture()
    calls, args = write_original_measurement(tmp_path, cases=cases, parent=parent, policy=policy, coverage=coverage, inputs=inputs, release=release)
    manifest = m.write_measurement(cases, coverage, **args)
    assert calls == policy["new_example_ids"] and manifest["new_sequence_calls"] == 2 and manifest["reused_examples"] == 11
    monkeypatch.setattr(m, "parent_measurement", lambda *args: parent)
    checked, records = m.checked_measurement(args["output"], "tokenizers", inputs=inputs, cases=cases, coverage=coverage,
        frozen=args["frozen"], release=release, budget_root=args["budget_root"])
    assert checked == manifest and len(records) == 13
    for record in records:
        ident = record["case"]["example"]["example_id"]
        if ident in parent["records"]:
            assert encoded({k: record[k] for k in m.ARRAY_FIELDS}) == encoded({k: parent["records"][ident][k] for k in m.ARRAY_FIELDS})
    args["output"] = args["output"].with_name("duplicate-attempt")
    with pytest.raises(DataError, match="encoding_engine_budget_already_reserved"):
        m.write_measurement(cases, coverage, **args)
    assert calls == policy["new_example_ids"] and not (args["output"] / "manifest.json").exists()


@pytest.mark.parametrize("mutation", ["third_target", "extra_case", "protocol", "final_split", "different_engine"])
def test_scope_mismatches_fail_before_any_new_sequence_call(tmp_path, mutation):
    cases, parent, policy, coverage, inputs, release = encoding_fixture()
    calls, args = write_original_measurement(tmp_path, cases=cases, parent=parent, policy=policy, coverage=coverage, inputs=inputs, release=release)
    if mutation == "third_target":
        cases[0]["encoding_mode"] = "new_fixed_example"
        policy["new_example_ids"].insert(0, cases[0]["example"]["example_id"])
    elif mutation == "extra_case":
        cases.append(copy.deepcopy(cases[5]))
    elif mutation == "protocol":
        cases[5]["category"] = "original_protocol_only"
    elif mutation == "final_split":
        cases[5]["example"]["split"] = "test"
    else:
        args["engine"] = "transformers"
    with pytest.raises(DataError):
        m.write_measurement(cases, coverage, **args)
    assert calls == [] and not (args["output"] / "manifest.json").exists()


def test_encoding_failure_retains_call_event_and_budget_without_publishing_success(tmp_path):
    cases, parent, policy, coverage, inputs, release = encoding_fixture()
    calls, args = write_original_measurement(tmp_path, cases=cases, parent=parent, policy=policy, coverage=coverage, inputs=inputs, release=release, fail=True)
    with pytest.raises(ValueError, match="original fixture sequence failure"):
        m.write_measurement(cases, coverage, **args)
    assert calls == policy["new_example_ids"][:1]
    events = q.jsonl((args["budget_root"] / "tokenizers.events.jsonl").read_bytes())[0]
    assert [e["event"] for e in events] == ["sequence_call_started", "sequence_call_failed"]
    assert not (args["output"] / "manifest.json").exists()
    with pytest.raises(DataError, match="encoding_engine_budget_already_reserved"):
        m.write_measurement(cases, coverage, **args)
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", ["new_record", "reused_record", "old_revision", "run_count_bool", "release", "events", "original_encoding_time"])
def test_complete_record_verifier_rejects_changed_arrays_run_or_epoch(tmp_path, monkeypatch, mutation):
    cases, parent, policy, coverage, inputs, release = encoding_fixture()
    _, args = write_original_measurement(tmp_path, cases=cases, parent=parent, policy=policy, coverage=coverage, inputs=inputs, release=release)
    m.write_measurement(cases, coverage, **args)
    monkeypatch.setattr(m, "parent_measurement", lambda *args: parent)
    if mutation in {"new_record", "reused_record"}:
        case = cases[5] if mutation == "new_record" else cases[0]
        path = args["output"] / (case["case_id"] + ".json")
        record = json.loads(path.read_bytes())
        record["padding"]["attention_mask"][0] = True
    elif mutation == "old_revision":
        path = args["output"] / "manifest.json"
        record = json.loads(path.read_bytes())
        record["quality_revision_sha256"] = "original-old-revision"
    elif mutation == "events":
        path = args["budget_root"] / "tokenizers.events.jsonl"
        path.write_bytes(b"{}\n")
    elif mutation == "original_encoding_time":
        path = args["output"] / "encoding-provenance.json"
        record = json.loads(path.read_bytes())
        record["parent_encoding"]["original_fixture_encoding"] = "incorrectly claimed current time"
    else:
        path = args["output"] / "run.json"
        record = json.loads(path.read_bytes())
        if mutation == "run_count_bool":
            record["new_sequence_calls"] = True
        else:
            record["encoding_release_file_sha256"] = "0" * 64
    if mutation != "events":
        path.write_bytes(encoded(record) + b"\n")
    with pytest.raises(DataError):
        m.checked_measurement(args["output"], "tokenizers", inputs=inputs, cases=cases, coverage=coverage,
            frozen=args["frozen"], release=release, budget_root=args["budget_root"])


def test_altered_execution_release_is_rejected_before_any_real_tokenizer_load(tmp_path, monkeypatch):
    for name in ("USE_TORCH", "USE_TF", "USE_FLAX"):
        monkeypatch.setenv(name, "0")
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        monkeypatch.setenv(name, "1")
    monkeypatch.setattr(m, "bound_selection", lambda **kw: ({}, {}, {}, [], {}))
    monkeypatch.setattr(m, "parent_measurement", lambda *args: pytest.fail("release was not checked first"))
    path = tmp_path / "changed-release.json"
    path.write_bytes(encoded({"issuer": "S0", "status": "AUTHORIZED_WITHIN_EXISTING_TWO_EXAMPLE_SCOPE"}))
    output = tmp_path / ".toolalign-local" / "rejected"
    with pytest.raises(DataError, match="input_hash_mismatch"):
        m.measure(config_path="original", input_root="original", revision="original", frozen="original",
            release_path=path, tokenizer_root="NEVER_OPEN_THIS_UNAUTHORIZED_TOKENIZER", engine="tokenizers", output=output)
    assert not output.exists()
