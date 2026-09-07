"""R1: one installed static comparison plus independent full-array/HTML checks.

Run in isolated no-site mode with only the installed wheel and existing CPU
dependencies supplied by the caller. This never imports a tokenizer or encodes.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from html.parser import HTMLParser
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def same(left, right):
    assert packed(left) == packed(right)


def read(path):
    return json.loads(Path(path).read_bytes())


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.rows, self.blocks = [], []
        self.row = self.cell = self.block = None
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        assert tag not in {"script", "iframe", "img", "object", "embed"}
        assert not any(k.lower().startswith("on") for k, _ in attrs)
        if tag == "tr":
            self.row = []
        elif tag == "td":
            self.cell = []
        elif tag == "pre":
            self.block = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
        if self.block is not None:
            self.block.append(data)

    def handle_endtag(self, tag):
        if tag == "td":
            self.row.append("".join(self.cell))
            self.cell = None
        elif tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "pre":
            self.blocks.append("".join(self.block))
            self.block = None


def check_record(record, case, page, token_texts):
    same(record["case"], case)
    seq, pad = record["sequence"], record["padding"]
    assert all(type(seq[k]) is int for k in ("prompt_tokens", "total_tokens", "eos_token_id", "append_eos_count"))
    assert all(type(v) is int for k, v in seq.items() if k.endswith("tokens") or k.endswith("bytes"))
    assert len(record["token_texts"]) == pad["bucket"]
    assert all(type(pad[k]) is int for k in ("first_supervised_causal_position", "last_supervised_causal_position", "effective_supervised_targets"))
    p, n, bucket = seq["prompt_tokens"], seq["total_tokens"], pad["bucket"]
    assert type(bucket) is int and 0 < p < n - 1 <= bucket
    arrays = ("prompt_ids", "concatenated_ids", "sequence_ids", "loss_mask", "causal_input_ids", "causal_target_ids", "causal_loss_mask")
    for key in arrays:
        assert type(seq[key]) is list and all(type(i) is int and i >= 0 for i in seq[key])
    for key in ("sequence_ids", "attention_mask", "loss_mask", "causal_input_ids", "causal_target_ids", "causal_loss_mask"):
        assert type(pad[key]) is list and all(type(i) is int and i >= 0 for i in pad[key])
    assert len(seq["prompt_ids"]) == p and len(seq["sequence_ids"]) == n
    assert seq["concatenated_ids"][:p] == seq["prompt_ids"]
    assert seq["sequence_ids"] == seq["concatenated_ids"] + [151645]
    assert seq["sequence_ids"][p:].count(151645) == seq["append_eos_count"] == 1
    assert seq["eos_token_id"] == 151645 and seq["prefix_stable"] is True
    assert seq["loss_mask"] == [0] * p + [1] * (n - p)
    for data in (seq, pad):
        assert data["causal_input_ids"] == data["sequence_ids"][:-1]
        assert data["causal_target_ids"] == data["sequence_ids"][1:]
        assert data["causal_loss_mask"] == data["loss_mask"][1:]
    assert pad["sequence_ids"] == seq["sequence_ids"] + [151643] * (bucket - n)
    assert pad["attention_mask"] == [1] * n + [0] * (bucket - n)
    assert pad["loss_mask"] == seq["loss_mask"] + [0] * (bucket - n)
    assert pad["first_supervised_causal_position"] == p - 1
    assert pad["last_supervised_causal_position"] == n - 2
    assert pad["effective_supervised_targets"] == sum(pad["causal_loss_mask"]) == n - p
    assert pad["causal_loss_mask"][p - 1] == pad["causal_loss_mask"][n - 2] == 1
    assert not any(pad["causal_loss_mask"][n - 1:])
    assert seq["prompt_sha256"] == sha(seq["prompt_text"].encode())
    assert seq["completion_sha256"] == sha(seq["completion_text"].encode())
    for key in arrays:
        digest_key = "sequence_sha256" if key == "sequence_ids" else key + "_sha256"
        assert seq[digest_key] == sha(packed(seq[key]))
    assert seq["completion_tokens"] == n - p - 1
    assert seq["completion_tokens_including_eos"] == n - p
    assert seq["completion_utf8_bytes"] == len(seq["completion_text"].encode())
    assert seq["format_id"] == "toolalign.action-json.qwen3-message-roles.v1"
    if case["category"] == "effective_selected_train":
        for key, value in seq.items():
            if key in case["audit"]:
                same(value, case["audit"][key])
    else:
        assert case["category"] == "original_protocol_only" and case["enters_effective_training"] is False
        same(seq, case["original_protocol_sequence"])
    assert all(case[k] is None for k in ("reviewer", "semantic_verdict", "token_mask_verdict"))
    assert len(page.blocks) == 8 and len(page.rows) == bucket
    same(json.loads(page.blocks[1]), case["example"])
    same(json.loads(page.blocks[2]), case["audit"])
    assert page.blocks[4] == seq["prompt_text"] and page.blocks[5] == seq["completion_text"]
    same(json.loads(page.blocks[6]), seq)
    same(json.loads(page.blocks[7]), pad)
    for i, token in enumerate(pad["sequence_ids"]):
        text = record["token_texts"][i]
        assert type(text) is str
        if token in token_texts:
            assert token_texts[token] == text
        token_texts[token] = text
        segment = "prompt" if i < p else "completion" if i < n - 1 else "eos" if i == n - 1 else "padding"
        target = pad["causal_target_ids"][i] if i < bucket - 1 else "—"
        loss = pad["causal_loss_mask"][i] if i < bucket - 1 else "—"
        assert page.rows[i] == [str(x) for x in (i, segment, token, text, pad["attention_mask"][i], pad["loss_mask"][i], target, loss)]
    return bucket


def check(args):
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    blocked = {"tokenizers", "transformers", "torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax"}
    assert all(importlib.util.find_spec(name) is None for name in blocked)
    from toolalign.data import quality_exclusion_materials as m

    expected = read(args.archive_proof)
    for name, digest in expected["package_files"].items():
        assert sha((args.target / name).read_bytes()) == digest
    root = args.bundle_root
    comparison = m.compare(config_path=args.config_path, input_root=args.input_root, revision=args.revision,
                           frozen=root / "frozen-materials-r3", reference=root / "review-reference",
                           native=root / "review-native", release_path=root / "encoding-authorization/encoding-release.json")
    assert comparison["unique_examples"] == 13 and comparison["semantic_verdicts_filled"] == 0
    with args.output.with_suffix(".compare.json").open("x") as stream:
        json.dump(comparison, stream, sort_keys=True, indent=2)
        stream.write("\n")
    members = read(args.input_root / "manifest.json")["files"]

    def original(name):
        item = members[name]
        path = Path(item["path"]) if item["kind"] == "immutable_existing_artifact" else args.input_root / name
        data = path.read_bytes()
        assert sha(data) == item["sha256"] and len(data) == item["bytes"]
        return json.loads(data)

    cases = read(root / "frozen-materials-r3/cases.json")
    assert len(cases) == len({c["example"]["example_id"] for c in cases}) == 13
    release = read(root / "encoding-authorization/encoding-release.json")
    assert sha((root / "encoding-authorization/encoding-release.json").read_bytes()) == m.ENCODING_RELEASE_SHA256
    rows, texts, engines = 0, {}, {}
    reference_records = None
    for suffix, engine in (("native", "tokenizers"), ("reference", "transformers")):
        directory = root / ("review-" + suffix)
        manifest = read(directory / "manifest.json")
        provenance = read(directory / "encoding-provenance.json")
        prefix = "parent-materials/review-" + suffix + "-r2/"
        old_manifest = original(prefix + "manifest.json")
        assert len(manifest["artifacts"]) == 29
        for name, artifact in manifest["artifacts"].items():
            data = (directory / name).read_bytes()
            assert len(data) == artifact["size_bytes"] and sha(data) == artifact["sha256"]
        records, reused, fresh = [], [], []
        for case in cases:
            name = case["case_id"]
            record = read(directory / (name + ".json"))
            rows += check_record(record, case, Page((directory / (name + ".html")).read_text()), texts)
            records.append(record)
            if case["encoding_mode"] == "reuse_original":
                old_name = case["previous_material_case_id"] + ".json"
                old = original(prefix + old_name)
                same(old["case"]["example"], case["example"])
                same(old["case"]["audit"], case["audit"])
                same({k: record[k] for k in ("sequence", "padding", "token_texts")},
                     {k: old[k] for k in ("sequence", "padding", "token_texts")})
                prov = next(p for p in provenance["records"] if p["example_id"] == case["example"]["example_id"])
                assert prov["previous_material_case_id"] == old["case"]["case_id"]
                assert prov["original_record_file"] == prefix + old_name
                assert prov["original_record_file_sha256"] == old_manifest["artifacts"][old_name]["sha256"]
                assert prov["sequence_padding_token_texts_sha256"] == sha(packed({k: old[k] for k in ("sequence", "padding", "token_texts")}))
                assert prov["new_record_canonical_sha256"] == sha(packed(record))
                assert type(prov["new_tokenizer_calls"]) is int and prov["new_tokenizer_calls"] == 0
                reused.append(case["example"]["example_id"])
            else:
                assert case["encoding_mode"] == "new_fixed_example" and case["previous_material_case_id"] is None
                assert case["example"]["split"] == "train"
                fresh.append(case["example"]["example_id"])
        assert len(reused) == 11 and fresh == release["material_example_ids"]
        assert len(provenance["records"]) == 11 and len(provenance["new_records"]) == 2
        parent = provenance["parent_encoding"]
        same(parent["parent_run"], original(prefix + "run.json"))
        same(parent["original_encoding"], old_manifest["original_encoding"])
        same(parent["original_run"], original("original-measurements/review-" + suffix + "/run.json"))
        assert parent["original_run"]["created_at_utc"] == old_manifest["original_encoding"]["actual_original_created_at_utc"]
        command_prefix = "original-measurements/logs/quality-adjudication-material-" + suffix + "-r1"
        same(parent["original_encoding_command"], original(command_prefix + ".json"))
        assert parent["original_encoding_command_metadata_file_sha256"] == members[command_prefix + ".json"]["sha256"]
        assert parent["original_encoding_command_log_file_sha256"] == members[command_prefix + ".log"]["sha256"]
        assert parent["new_tokenizer_calls_for_reuse"] == 0
        run = read(directory / "run.json")
        events = [json.loads(line) for line in (root / "encoding-budget" / (engine + ".events.jsonl")).read_bytes().splitlines()]
        assert len(events) == 4 and len(run["new_sequence_events"]) == 2
        same(events[1::2], run["new_sequence_events"])
        for event, prov in zip(run["new_sequence_events"], provenance["new_records"], strict=True):
            record = next(r for r in records if r["case"]["example"]["example_id"] == event["example_id"])
            assert event["record_sha256"] == prov["record_sha256"] == sha(packed(record))
            assert prov["encoding_release_file_sha256"] == m.ENCODING_RELEASE_SHA256
        assert sha(packed(records)) == manifest["records_sha256"] == comparison["records_sha256"]
        if reference_records is not None:
            same(records, reference_records)
        reference_records = records
        with (directory / "review.csv").open(newline="") as stream:
            csv_rows = list(csv.DictReader(stream))
        assert len(csv_rows) == 13
        for row, case in zip(csv_rows, cases, strict=True):
            assert row["case_id"] == case["case_id"] and row["example_id"] == case["example"]["example_id"]
            assert row["quality_revision_sha256"] == case["quality_revision_sha256"]
            assert all(row[k] == "" for k in ("reviewer", "semantic_verdict", "token_mask_verdict", "reviewed_at_utc", "notes"))
        engines[suffix] = {"payload_files": 29, "records_sha256": manifest["records_sha256"],
                           "unchanged_original_sequences": len(reused), "released_new_sequences": len(fresh),
                           "original_encoding_time": parent["original_run"]["created_at_utc"],
                           "actual_new_encoding_time": run["created_at_utc"]}
    assert not blocked & {name.split(".", 1)[0] for name in sys.modules}
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(args.target.resolve())
            origins[name] = sha(path.read_bytes())
    return {"status": "PASS_R1_INSTALLED_STATIC_MATERIALS", "comparison": comparison,
            "unique_examples": 13, "engine_records_checked": 26, "html_token_rows_checked": rows,
            "observed_token_ids_with_consistent_display_text": len(texts), "engines": engines,
            "installed_package_files": len(expected["package_files"]), "installed_module_origins": origins,
            "source_cwd_imports": 0, "new_actual_tokenizer_calls": 0, "new_dependencies": 0,
            "training_authorized": False, "browser_actual_observation": "NOT_RUN"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("config-path", "input-root", "revision", "bundle-root", "target", "archive-proof", "output"):
        parser.add_argument("--" + flag, required=True, type=Path)
    options = parser.parse_args()
    result = check(options)
    with options.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "installed_module_origins"}, sort_keys=True))
