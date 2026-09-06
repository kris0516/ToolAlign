"""Offline integration checks use original records, never a redistributed corpus."""

import copy
import csv
import json
from pathlib import Path

from toolalign.data.common import file_hash, read_json, verified_build_manifest, write_json
from toolalign.data.pipeline import build
from toolalign.data.source_policy import POLICY_SHA256, SourcePolicy


def _rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_policy_build_real_outputs_and_final_only_review(tmp_path, record_factory, monkeypatch):
    from test_pipeline import setup_source

    config = setup_source(tmp_path, record_factory)
    raw_tool = {
        "name": "Original Test Tool",
        "description": "Read an original local fixture.",
        "parameters": {
            "type": "dict",
            "properties": {
                "build_id": {"type": "string"},
                "limit": {"type": "int", "default": 3},
            },
            "required": ["build_id"],
        },
        "required": None,
    }
    valid = record_factory(tool=raw_tool, second=True)
    invalid = record_factory(tool=raw_tool, value="invalid-record", second=True)
    invalid["conversations"][-1]["value"] = '[Original Test Tool(build_id="bad", extra=1)]'
    valid["conversations"][0]["value"] += " </pre><script>not_executable()</script>"
    raw = Path(config["source_dir"]) / "data.json"
    write_json(raw, [valid, copy.deepcopy(valid), invalid])
    source_manifest = read_json(config["source_manifest"])
    source_manifest["files"]["data.json"] = {
        "size_bytes": raw.stat().st_size,
        "sha256": file_hash(raw),
    }
    write_json(config["source_manifest"], source_manifest)
    # Only source identity is substituted for this original fixture. The policy
    # bytes, normalizer and frozen v1 validation are real production paths.
    monkeypatch.setattr(SourcePolicy, "bind_source", lambda self, manifest: None)
    config["source_policy"] = "configs/source_toolace.v1.json"
    fake = Path(config["source_dir"]).parent / "tokenizer.json"
    write_json(fake, {"original_test_only": True})
    config["tokenizer_manifest"] = str(fake)

    class FixedTokenizer:
        def __init__(self, *_):
            pass

        def normalized(self, _):
            return {
                "prompt_tokens": 20,
                "schema_marginal_tokens": 5,
                "prompt_without_schema_tokens": 15,
                "completion_tokens": 10,
                "total_tokens": 30,
            }

        def raw_decision(self, *_):
            return self.normalized(None)

    monkeypatch.setattr("toolalign.data.pipeline.LocalTokenizer", FixedTokenizer)
    report, manifest = build(config)
    output = Path(config["output_dir"])
    assert verified_build_manifest(output / "manifest.json") == manifest
    assert manifest["source_policy_hash"] == POLICY_SHA256
    assert (
        manifest["execution_binding"] == "none"
        and manifest["original_side_effect_class"] == "unknown"
    )
    assert report["raw_assistant_decisions"] == 6
    assert report["normalization_excluded_decisions"] == 2
    assert report["normalization_candidates"] == 4 and report["final_examples"] == 2
    assert report["post_normalization_exclusions"] == {"exact_example_duplicate": 2}
    examples = _rows(output / "examples.jsonl")
    assert all(
        set(e["expected_action"]["tool_calls"][0]["arguments"]) == {"build_id"} for e in examples
    )
    review_manifest = read_json(output / "human-review" / "manifest.json")
    assert review_manifest["pool"] == "final_valid_examples_only"
    assert review_manifest["sample_records"] == 1 and review_manifest["sample_examples"] == 2
    assert review_manifest["examples_artifact_sha256"] == file_hash(output / "examples.jsonl")
    assert (
        review_manifest["accepted_examples_reviewed"] == 0
        and review_manifest["mislabel_rate"] is None
    )
    samples = _rows(output / "human-review" / "samples.jsonl")
    assert samples[0]["normalized_examples"] == examples
    assert (
        samples[0]["tool_transformations"][0]["default_annotations"][0]["inserted_into_arguments"]
        is False
    )
    assert all(row["policy_hash"] == POLICY_SHA256 for row in _rows(output / "lineage.jsonl"))
    with (output / "human-review" / "review.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1 and not rows[0]["reviewer"] and not rows[0]["verdict"]
    rendered = (output / "human-review" / "index.html").read_text()
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered
    assert "default-src 'none'" in rendered
    assert "invalid-record" not in rendered
    assert (
        "out_of_policy_arguments"
        in (output / "human-review" / "exclusion-samples.jsonl").read_text()
    )
    config["output_dir"] = str(output.parent / "second-build")
    second_report, second_manifest = build(config)
    assert second_report == report and second_manifest == manifest
