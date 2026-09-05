import copy
import json
from pathlib import Path

import pytest

from toolalign.data.common import (
    DataError,
    file_hash,
    private_directory,
    read_json,
    write_json,
)
from toolalign.data.lengths import quantiles, summarize_lengths
from toolalign.data.pipeline import build, length_bucket


def setup_source(tmp_path, record_factory):
    root = tmp_path / ".toolalign-local"
    raw = root / "raw"
    raw.mkdir(parents=True)
    record = record_factory(second=True)
    # Original synthetic fixture exercises the source-lock mechanism offline. It
    # is not represented as an actual observation of the external corpus.
    write_json(raw / "data.json", [record, copy.deepcopy(record)])
    (raw / "README.md").write_text("Original test-only fixture; no upstream text.")
    source_manifest = {
        "repo_id": "Team-ACE/ToolACE",
        "revision": "a" * 40,
        "license_id": "Apache-2.0",
        "access": {"gated": False},
        "files": {
            p.name: {"size_bytes": p.stat().st_size, "sha256": file_hash(p)} for p in raw.iterdir()
        },
    }
    lock = root / "source.json"
    write_json(lock, source_manifest)
    return {
        "source_manifest": str(lock),
        "source_dir": str(raw),
        "output_dir": str(root / "build1"),
        "seed": 17,
        "ood_fraction": 0.1,
        "length_buckets": [128, 256],
        "max_tokens": 256,
        "review_sample_records": 2,
        "tokenizer_manifest": None,
        "tokenizer_dir": None,
    }


def test_independent_builds_identical_and_accounting_complete(tmp_path, record_factory):
    config = setup_source(tmp_path, record_factory)
    first_report, first = build(config)
    config["output_dir"] = str(tmp_path / ".toolalign-local" / "build2")
    second_report, second = build(config)
    assert first == second
    assert first_report == second_report
    assert first_report["raw_records"] == 2
    assert first_report["raw_assistant_decisions"] == 4
    assert first_report["normalization_candidates"] == 4
    assert first_report["final_examples"] == 0
    assert first_report["post_normalization_exclusions"] == {"length_not_measured": 4}
    assert first_report["exact_duplicate_source_records"] == 1
    assert first_report["human_review"]["status"] == "CANDIDATES_ONLY_NOT_REQUESTED"
    assert (Path(config["output_dir"]) / "human-review" / "review.csv").read_text().count(
        "kris"
    ) == 0


def test_source_hash_tampering_rejected(tmp_path, record_factory):
    config = setup_source(tmp_path, record_factory)
    (Path(config["source_dir"]) / "data.json").write_text("[]")
    with pytest.raises(DataError, match="source_hash_mismatch"):
        build(config)


@pytest.mark.parametrize("change", ["license", "gated"])
def test_unapproved_license_and_gated_fail_closed(tmp_path, record_factory, change):
    config = setup_source(tmp_path, record_factory)
    manifest = read_json(config["source_manifest"])
    if change == "license":
        manifest["license_id"] = "unknown"
    else:
        manifest["access"]["gated"] = "manual"
    write_json(config["source_manifest"], manifest)
    with pytest.raises(DataError):
        build(config)


def test_public_or_symlink_output_rejected(tmp_path):
    with pytest.raises(DataError):
        private_directory(tmp_path / "public")
    (tmp_path / ".toolalign-local").mkdir()
    (tmp_path / ".toolalign-local" / "escape").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(DataError):
        private_directory(tmp_path / ".toolalign-local" / "escape" / "public")


def test_existing_build_not_overwritten(tmp_path, record_factory):
    config = setup_source(tmp_path, record_factory)
    build(config)
    with pytest.raises(DataError, match="output_must_be_empty"):
        build(config)


def test_length_quantiles_and_empty_denominators():
    assert quantiles(list(range(1, 101))) == {"p50": 50, "p90": 90, "p95": 95, "p99": 99}
    assert summarize_lengths([])["total_tokens"] == {
        "count": 0,
        "p50": None,
        "p90": None,
        "p95": None,
        "p99": None,
    }
    assert length_bucket(256, [128, 256]) == "le_256"
    assert length_bucket(257, [128, 256]) == "over_limit"


def test_long_examples_excluded_whole_with_lineage(tmp_path, record_factory, monkeypatch):
    config = setup_source(tmp_path, record_factory)
    fake = tmp_path / ".toolalign-local" / "fake-tokenizer.json"
    write_json(fake, {"test_only": True})
    config["tokenizer_manifest"] = str(fake)

    class FixedTestTokenizer:
        def __init__(self, *_):
            pass

        def normalized(self, example):
            return {
                "prompt_tokens": 250,
                "schema_marginal_tokens": 50,
                "prompt_without_schema_tokens": 200,
                "completion_tokens": 20,
                "total_tokens": 270,
            }

        def raw_decision(self, *_):
            return self.normalized(None)

    monkeypatch.setattr("toolalign.data.pipeline.LocalTokenizer", FixedTestTokenizer)
    report, _ = build(config)
    assert report["final_examples"] == 0
    assert report["post_normalization_exclusions"] == {"length_over_limit": 4}
    lineage = [
        json.loads(line)
        for line in (Path(config["output_dir"]) / "lineage.jsonl").read_text().splitlines()
    ]
    assert len(lineage) == 4
    assert all(row["length"]["total_tokens"] == 270 and row["normalized_hash"] for row in lineage)


def test_compare_checks_actual_artifacts(tmp_path, record_factory):
    from toolalign.data.common import verified_build_manifest

    config = setup_source(tmp_path, record_factory)
    _, manifest = build(config)
    path = Path(config["output_dir"]) / "manifest.json"
    assert verified_build_manifest(path) == manifest
    (path.parent / "examples.jsonl").write_text("tampered")
    with pytest.raises(DataError, match="artifact_hash_mismatch"):
        verified_build_manifest(path)


def test_manifest_artifact_escape_rejected(tmp_path):
    from toolalign.data.common import verified_build_manifest

    p = tmp_path / "manifest.json"
    write_json(p, {"artifacts": {"../outside": "0" * 64}})
    with pytest.raises(DataError, match="artifact_path_escape"):
        verified_build_manifest(p)


def test_accepted_flow_deduplicates_and_retains_denominator(tmp_path, record_factory, monkeypatch):
    config = setup_source(tmp_path, record_factory)
    fake = tmp_path / ".toolalign-local" / "fake-tokenizer.json"
    write_json(fake, {"test_only": True})
    config["tokenizer_manifest"] = str(fake)

    class FixedTestTokenizer:
        def __init__(self, *_):
            pass

        def normalized(self, example):
            return {
                "prompt_tokens": 20,
                "schema_marginal_tokens": 5,
                "prompt_without_schema_tokens": 15,
                "completion_tokens": 10,
                "total_tokens": 30,
            }

        def raw_decision(self, *_):
            return self.normalized(None)

    monkeypatch.setattr("toolalign.data.pipeline.LocalTokenizer", FixedTestTokenizer)
    report, _ = build(config)
    assert report["raw_assistant_decisions"] == 4
    assert report["final_examples"] == 2
    assert report["post_normalization_exclusions"] == {"exact_example_duplicate": 2}
    assert sum(report["final_split_counts"].values()) == 2
    examples = [
        json.loads(line)
        for line in (Path(config["output_dir"]) / "examples.jsonl").read_text().splitlines()
    ]
    assert len({e["group_id"] for e in examples}) == 1
    assert all("build-002" not in json.dumps(e["messages"]) for e in examples)


def test_review_html_escapes_dataset_script(tmp_path, record_factory):
    config = setup_source(tmp_path, record_factory)
    raw = Path(config["source_dir"]) / "data.json"
    records = read_json(raw)
    records[0]["conversations"][0]["value"] = '</pre><script>alert("sample")</script>'
    write_json(raw, records)
    manifest = read_json(config["source_manifest"])
    manifest["files"]["data.json"] = {"sha256": file_hash(raw), "size_bytes": raw.stat().st_size}
    write_json(config["source_manifest"], manifest)
    build(config)
    rendered = (Path(config["output_dir"]) / "human-review" / "index.html").read_text()
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "default-src 'none'" in rendered


def test_unstable_token_boundary_is_counted_and_excluded(tmp_path, record_factory, monkeypatch):
    config = setup_source(tmp_path, record_factory)
    fake = tmp_path / ".toolalign-local" / "fake-tokenizer.json"
    write_json(fake, {"test_only": True})
    config["tokenizer_manifest"] = str(fake)

    class BoundaryFailureTokenizer:
        def __init__(self, *_):
            pass

        def normalized(self, example):
            raise DataError("prompt_completion_boundary_changed")

        def raw_decision(self, *_):
            return {
                "prompt_tokens": 20,
                "schema_marginal_tokens": 5,
                "prompt_without_schema_tokens": 15,
                "completion_tokens": 10,
                "total_tokens": 30,
            }

    monkeypatch.setattr("toolalign.data.pipeline.LocalTokenizer", BoundaryFailureTokenizer)
    report, _ = build(config)
    assert report["normalization_candidates"] == 4
    assert report["post_normalization_exclusions"] == {"prompt_completion_boundary_changed": 4}
    assert report["final_examples"] == 0
