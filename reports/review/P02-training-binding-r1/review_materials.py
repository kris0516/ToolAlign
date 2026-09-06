"""Exactly the approved 13 cases per engine; static HTML is not page observation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def read(path):
    return json.loads(Path(path).read_text())


def measure(args):
    for key in ("USE_TORCH", "USE_TF", "USE_FLAX"):
        assert os.environ[key] == "0"
    for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        assert os.environ[key] == "1"
    from toolalign.data.training_review import write_measurement
    from toolalign.model_io.offline import OfflineQwenTokenizer, model_modules_loaded

    assert sys.dont_write_bytecode and model_modules_loaded() == []
    prepared = read(args.cases)
    config = read(args.config)
    counts = Counter()

    class Counted:
        def __init__(self, profile, adapter):
            self.profile, self.adapter = profile, adapter
            self.identity = adapter.identity

        def training_sequence(self, example):
            counts[self.profile] += 1
            assert sum(counts.values()) <= 13
            return self.adapter.training_sequence(example)

        def decode(self, *values, **kw):
            return self.adapter.decode(*values, **kw)

    adapters = {name: Counted(name, OfflineQwenTokenizer(
        args.tokenizer_root, repo_id=profile["model_id"], revision=profile["model_revision"], engine=args.engine))
        for name, profile in config["profiles"].items()}
    result = write_measurement(prepared["cases"], prepared["coverage"],
                               tokenizers_by_profile=adapters, output=args.output)
    assert sum(counts.values()) == 13 and model_modules_loaded() == []
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(Path(args.root).resolve() / "src/toolalign")
            origins[name] = {"path": str(path), "sha256": sha(path.read_bytes())}
    proof = {"status": "PASS", "engine": args.engine, "material_encodings_by_profile": dict(counts),
             "independent_examples": 13, "model_modules_loaded": [], "origins": origins,
             "manifest_sha256": sha((args.output / "manifest.json").read_bytes()),
             "records_sha256": result["records_sha256"], "tokenizers": result["tokenizers"],
             "actual_browser_pages": 0, "human_review": "PENDING"}
    with (args.output / "r1-measurement.json").open("x") as stream:
        json.dump(proof, stream, indent=2)
        stream.write("\n")
    print(json.dumps(proof))


class StaticPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks, self.rows, self.tags = [], [], []
        self.block, self.row, self.cell = None, None, None

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        assert not any(k.startswith("on") for k, _ in attrs)
        assert not {"src", "href", "action"} & {k for k, _ in attrs}
        if tag == "pre":
            self.block = []
        elif tag == "tr":
            self.row = []
        elif tag == "td":
            self.cell = []

    def handle_endtag(self, tag):
        if tag == "pre":
            self.blocks.append("".join(self.block))
            self.block = None
        elif tag == "td":
            self.row.append("".join(self.cell))
            self.cell = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.block is not None:
            self.block.append(data)
        if self.cell is not None:
            self.cell.append(data)


def compare(args):
    directories = [args.reference, args.native, args.worker_reference, args.worker_native]
    names = [f"actual-{i:02d}" for i in range(1, 11)] + ["protocol-clarify", "protocol-final", "protocol-refuse"]
    originals = [read(args.reference / (name + ".json")) for name in names]
    token_rows = 0
    for index, directory in enumerate(directories):
        manifest = read(directory / "manifest.json")
        assert manifest["unique_examples"] == 13 and manifest["training_authorized"] is False
        assert all(t["engine"] == ("transformers" if index % 2 == 0 else "tokenizers")
                   for t in manifest["tokenizers"].values())
        assert manifest["records_sha256"] == sha(canonical(originals))
        for name, info in manifest["artifacts"].items():
            path = directory / name
            assert path.is_relative_to(directory) and not path.is_symlink()
            assert sha(path.read_bytes()) == info["sha256"] and path.stat().st_size == info["size_bytes"]
        with (directory / "review.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 13 and all(not row[k] for row in rows for k in ("reviewer", "verdict", "reviewed_at_utc", "notes"))
        for name, expected in zip(names, originals, strict=True):
            value = read(directory / (name + ".json"))
            assert value == expected
            case, seq, pad = value["case"], value["sequence"], value["padding"]
            p, n, bucket = seq["prompt_tokens"], seq["total_tokens"], pad["bucket"]
            assert seq["sequence_ids"] == seq["concatenated_ids"] + [151645]
            assert seq["sequence_ids"][:p] == seq["prompt_ids"]
            assert seq["sequence_ids"][p:].count(151645) == 1
            assert seq["loss_mask"] == [0] * p + [1] * (n - p)
            assert seq["causal_input_ids"] == seq["sequence_ids"][:-1]
            assert seq["causal_target_ids"] == seq["sequence_ids"][1:]
            assert pad["sequence_ids"] == seq["sequence_ids"] + [151643] * (bucket - n)
            assert pad["attention_mask"] == [1] * n + [0] * (bucket - n)
            assert pad["loss_mask"] == [0] * p + [1] * (n - p) + [0] * (bucket - n)
            assert pad["causal_input_ids"] == pad["sequence_ids"][:-1]
            assert pad["causal_target_ids"] == pad["sequence_ids"][1:]
            assert pad["causal_loss_mask"] == pad["loss_mask"][1:]
            assert sum(pad["causal_loss_mask"]) == pad["effective_supervised_targets"] == n - p
            assert pad["causal_target_ids"][n - 2] == 151645 and pad["causal_loss_mask"][p - 1] == 1
            page = StaticPage()
            rendered = (directory / (name + ".html")).read_text()
            page.feed(rendered)
            assert "default-src 'none'" in rendered and "单 token 解码仅供辅助阅读" in rendered
            assert not {"script", "iframe", "a", "img", "object", "form"} & set(page.tags)
            assert len(page.blocks) == 8 and len(page.rows) == bucket
            assert json.loads(page.blocks[1]) == {k: case["example"][k] for k in ("messages", "tools")}
            assert json.loads(page.blocks[2]) == case["example"]["expected_action"]
            assert page.blocks[3:5] == [seq["prompt_text"], seq["completion_text"]]
            assert json.loads(page.blocks[6]) == seq and json.loads(page.blocks[7]) == pad
            for i, cells in enumerate(page.rows):
                segment = "prompt" if i < p else "completion" if i < n - 1 else "eos" if i == n - 1 else "padding"
                target = pad["causal_target_ids"][i] if i < bucket - 1 else "—"
                loss = pad["causal_loss_mask"][i] if i < bucket - 1 else "—"
                assert cells == list(map(str, (i, segment, pad["sequence_ids"][i], value["token_texts"][i],
                                               pad["attention_mask"][i], pad["loss_mask"][i], target, loss)))
            if index == 0:
                token_rows += len(page.rows)
    assert len({r["case"]["example"]["example_id"] for r in originals}) == 13
    result = {"status": "PASS", "independent_examples": 13, "r1_material_encodings": 26,
              "actual_selected_train": 10, "original_protocol_only": 3,
              "full_record_pairs_equal": 13, "historical_actual_matches": 10,
              "static_token_rows_per_copy": token_rows, "static_copies_checked": 4,
              "records_sha256": sha(canonical(originals)), "actual_browser_pages": 0,
              "browser_observation": "NOT_RUN", "human_review": "PENDING", "training_authorized": False}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    measured = sub.add_parser("measure")
    measured.add_argument("--engine", choices=("tokenizers", "transformers"), required=True)
    for key in ("root", "cases", "config", "tokenizer-root", "output"):
        measured.add_argument("--" + key, type=Path, required=True)
    compared = sub.add_parser("compare")
    for key in ("reference", "native", "worker-reference", "worker-native", "output"):
        compared.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    {"measure": measure, "compare": compare}[args.command](args)


if __name__ == "__main__":
    main()
