"""Independently check retained measurements using only JSON, HTML and byte decoding.

This performs no token encoding, imports no ToolAlign producer or tokenizer, and
does not assign semantic verdicts. All paths are supplied in a private job file.
"""

import argparse
import csv
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return sha(encoded(value))


def escaped(value):
    return encoded(value).decode().replace("<", "\\u003c").replace(">", "\\u003e")


def render(example, descriptor):
    # The frozen template's tools=None, no-thinking branch on projected messages.
    # Projected history is JSON text: it contains no native template tool_calls
    # property or literal think tags, and always ends in a user/tool message.
    result = "<|im_start|>system\n" + descriptor["instruction"] + "\n"
    result += escaped({"format_version": descriptor["format_id"], "tools": example["tools"]})
    result += "<|im_end|>\n"
    messages = example["messages"]
    assert messages[-1]["role"] in {"user", "tool"}
    for i, message in enumerate(messages):
        role = message["role"]
        content = escaped({"message_index": i, "message": message})
        if role == "tool":
            if i == 0 or messages[i - 1]["role"] != "tool":
                result += "<|im_start|>user"
            result += "\n<tool_response>\n" + content + "\n</tool_response>"
            if i == len(messages) - 1 or messages[i + 1]["role"] != "tool":
                result += "<|im_end|>\n"
        else:
            result += "<|im_start|>" + role + "\n" + content + "<|im_end|>\n"
    return result + "<|im_start|>assistant\n<think>\n\n</think>\n\n"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.pre, self.links = [], [], []
        self.row = self.cell = self.block = None

    def handle_starttag(self, tag, attributes):
        assert tag not in {"script", "iframe", "img", "object", "embed", "form", "input"}
        attrs = dict(attributes)
        assert not any(k.startswith("on") for k in attrs)
        assert "src" not in attrs
        if "href" in attrs:
            assert tag == "a" and ":" not in attrs["href"] and "/" not in attrs["href"]
            self.links.append(attrs["href"])
        if tag == "tr":
            self.row = []
        if tag == "td":
            self.cell = ""
        if tag == "pre":
            self.block = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data
        if self.block is not None:
            self.block += data

    def handle_endtag(self, tag):
        if tag == "td":
            self.row.append(self.cell)
            self.cell = None
        if tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = None
        if tag == "pre":
            self.pre.append(self.block)
            self.block = None


def byte_decoder(tokenizer):
    assert tokenizer["decoder"] == {"type": "ByteLevel", "add_prefix_space": False,
                                    "trim_offsets": False, "use_regex": False}
    base = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    missing = [i for i in range(256) if i not in base]
    inverse = dict(zip(map(chr, base + list(range(256, 256 + len(missing)))), base + missing, strict=True))
    vocab = {ident: bytes(inverse[c] for c in token) for token, ident in tokenizer["model"]["vocab"].items()}
    vocab.update({item["id"]: item["content"].encode() for item in tokenizer["added_tokens"]})

    def decode(ids):
        return b"".join(vocab[i] for i in ids).decode("utf-8", errors="replace")

    return decode


def check_record(record, expected, plan, descriptor, decode):
    case, sequence, pad = record["case"], record["sequence"], record["padding"]
    example = case["example"]
    for key, value in expected.items():
        assert case[key] == value, (case["case_id"], key)
    assert case["semantic_verdict"] is None
    assert case["quality_revision_sha256"] == plan["quality_revision_sha256"]
    category = ("effective_selected_train" if case["case_id"].startswith("effective-") else
                "original_protocol_only" if case["case_id"].startswith("protocol-") else
                "staged_direct_annotation" if case["case_id"].startswith("staged-direct-") else "staged_dependent_prefix")
    assert case["category"] == category
    if category != "effective_selected_train":
        assert case["audit"] is None and case["enters_effective_training"] is False
    prompt, completion = render(example, descriptor), escaped(example["expected_action"])
    assert sequence["prompt_text"] == prompt and sequence["completion_text"] == completion
    ids, prefix = sequence["sequence_ids"], sequence["prompt_ids"]
    p, n, bucket = len(prefix), len(ids), pad["bucket"]
    assert 0 < p < n - 1 <= 32767 and all(type(i) is int and i >= 0 for i in ids)
    assert ids[:p] == prefix and sequence["concatenated_ids"] == ids[:-1]
    assert ids[-1] == sequence["eos_token_id"] == 151645 and ids[p:].count(151645) == 1
    assert decode(prefix) == prompt and decode(ids[:-1]) == prompt + completion
    assert decode(ids[p:-1]) == completion and decode(ids) == prompt + completion + "<|im_end|>"
    mask = [0] * p + [1] * (n - p)
    assert sequence["loss_mask"] == mask
    assert sequence["causal_input_ids"] == ids[:-1] and sequence["causal_target_ids"] == ids[1:]
    assert sequence["causal_loss_mask"] == mask[1:]
    for array, digest_key in (("sequence_ids", "sequence_sha256"), ("prompt_ids", "prompt_ids_sha256"),
                              ("concatenated_ids", "concatenated_ids_sha256"), ("loss_mask", "loss_mask_sha256"),
                              ("causal_input_ids", "causal_input_ids_sha256"), ("causal_target_ids", "causal_target_ids_sha256"),
                              ("causal_loss_mask", "causal_loss_mask_sha256")):
        assert canonical(sequence[array]) == sequence[digest_key]
    metadata = {"prompt_sha256": sha(prompt.encode()), "completion_sha256": sha(completion.encode()),
                "prompt_tokens": p, "total_tokens": n, "completion_tokens": n - p - 1,
                "completion_tokens_including_eos": n - p, "completion_utf8_bytes": len(completion.encode()),
                "prefix_stable": True, "append_eos_count": 1, "first_supervised_causal_position": p - 1,
                "last_supervised_causal_position": n - 2, "format_id": descriptor["format_id"],
                "instruction_sha256": descriptor["instruction_sha256"], "contract_sha256": descriptor["contract_schema_sha256"],
                "template_sha256": descriptor["template"]["utf8_sha256"]}
    assert all(sequence[k] == v for k, v in metadata.items())
    assert sha(descriptor["instruction"].encode()) == metadata["instruction_sha256"]
    if case["audit"] is not None:
        assert all(case["audit"][k] == v for k, v in sequence.items() if k.endswith("sha256") or k in metadata)
        assert bucket == case["profiles"][case["primary_profile"]]["padding_bucket"]
    else:
        assert bucket == max(1024, ((n + 511) // 512) * 512)
    padded, padded_mask = ids + [151643] * (bucket - n), mask + [0] * (bucket - n)
    assert bucket >= n and pad["sequence_ids"] == padded and pad["loss_mask"] == padded_mask
    assert pad["attention_mask"] == [1] * n + [0] * (bucket - n)
    assert pad["causal_input_ids"] == padded[:-1] and pad["causal_target_ids"] == padded[1:]
    assert pad["causal_loss_mask"] == padded_mask[1:]
    assert pad["effective_supervised_targets"] == sum(padded_mask[1:]) == n - p
    assert pad["first_supervised_causal_position"] == p - 1 and pad["last_supervised_causal_position"] == n - 2
    assert pad["unpadded_length"] == n and pad["pad_token_id"] == 151643
    assert record["token_texts"] == [decode([i]) for i in padded]
    expected_binding = {k: example[k] for k in ("example_id", "source", "source_revision", "source_record_hash", "group_id", "split")}
    expected_binding.update(example_sha256=canonical(example), action_sha256=canonical(example["expected_action"]),
                            model_input_sha256=canonical({k: example[k] for k in ("messages", "tools")}))
    assert record["source_binding"] == expected_binding
    assert record["budget_observations"] == {"context_including_eos": {str(cap): n <= cap for cap in (1024, 1536, 2048)},
        "response_256_including_eos": n - p <= 256, "used_to_promote_staged_annotation": False}
    return {"case_id": case["case_id"], "category": category, "prompt_tokens": p, "total_tokens": n,
            "completion_including_eos": n - p, "padding_bucket": bucket, "full_record_sha256": canonical(record)}


def check_html(data, record):
    page = Page()
    page.feed(data.decode())
    case, seq, pad = record["case"], record["sequence"], record["padding"]
    assert json.loads(page.pre[0]) == {k: v for k, v in case.items() if k not in {"example", "audit"}}
    assert json.loads(page.pre[1]) == case["example"] and json.loads(page.pre[2]) == case["audit"]
    assert json.loads(page.pre[3]) == {k: record[k] for k in ("source_binding", "budget_observations")}
    assert page.pre[4:6] == [seq["prompt_text"], seq["completion_text"]]
    assert json.loads(page.pre[6]) == seq and json.loads(page.pre[7]) == pad and len(page.pre) == 8
    assert len(page.rows) == pad["bucket"]
    for i, cells in enumerate(page.rows):
        p, n = seq["prompt_tokens"], seq["total_tokens"]
        segment = "prompt" if i < p else "completion" if i < n - 1 else "eos" if i == n - 1 else "padding"
        target, mask = (pad["causal_target_ids"][i], pad["causal_loss_mask"][i]) if i < pad["bucket"] - 1 else ("—", "—")
        assert cells == list(map(str, (i, segment, pad["sequence_ids"][i], record["token_texts"][i],
                                      pad["attention_mask"][i], pad["loss_mask"][i], target, mask)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    repo = Path(job["repo"])
    expected_files = json.loads(Path(job["intake"]).read_text())["candidate_files"]
    plan = json.loads(Path(job["plan"]).read_text())
    descriptor_path = repo / "src/toolalign/model_io/descriptor.v1.json"
    descriptor = json.loads(descriptor_path.read_text())
    assert sha(descriptor_path.read_bytes()) == expected_files[str(descriptor_path.relative_to(repo))]["sha256"]
    tokenizer_root = Path(job["tokenizer_root"])
    tokenizer = json.loads((tokenizer_root / "tokenizer.json").read_text())
    decode = byte_decoder(tokenizer)
    results, first_records = {}, None
    for label, material in job["materials"].items():
        root, engine = Path(material["root"]), material["engine"]
        manifest = json.loads((root / "manifest.json").read_text())
        assert manifest["case_order"] == plan["case_order"] and manifest["unique_examples"] == 16
        assert manifest["revision_manifest_sha256"] == plan["revision_manifest_sha256"]
        assert manifest["quality_revision_sha256"] == plan["quality_revision_sha256"]
        assert manifest["training_authorized"] is False and manifest["model_modules_loaded"] == []
        assert manifest["semantic_review"] == "UNFILLED_FOR_DELEGATED_AI_REVIEW"
        assert all(manifest[k] == "NOT_RUN" for k in ("external_execution", "browser_actual_observation", "trainer_collator"))
        for name, digest in manifest["consumer"]["package_files"].items():
            assert digest == expected_files["src/toolalign/" + name]["sha256"]
        for profile, identity in manifest["tokenizers"].items():
            assert identity["engine"] == engine and identity["template_sha256"] == descriptor["template"]["utf8_sha256"]
            assert identity["repo_id"] == "Qwen/Qwen3-" + ("0.6B" if profile == "smoke" else "1.7B")
            assert identity["eos_token_id"] == 151645 and identity["eos_token"] == "<|im_end|>"
            assert identity["encoding_parameters"] == {"add_special_tokens": False}
            assert identity["render_parameters"] == {"add_generation_prompt": True, "enable_thinking": False, "tools": None}
            for name, info in identity["files"].items():
                data = (tokenizer_root / name).read_bytes()
                assert {"sha256": sha(data), "size_bytes": len(data)} == info
        assert sha(json.loads((tokenizer_root / "tokenizer_config.json").read_text())["chat_template"].encode()) == descriptor["template"]["utf8_sha256"]
        assert not any(p.is_symlink() for p in root.rglob("*"))
        assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == set(manifest["artifacts"]) | {"manifest.json", "run.json"}
        for name, info in manifest["artifacts"].items():
            data = (root / name).read_bytes()
            assert {"sha256": sha(data), "size_bytes": len(data)} == info
        records = [json.loads((root / (name + ".json")).read_text()) for name in plan["case_order"]]
        assert canonical(records) == manifest["records_sha256"]
        if first_records is None:
            first_records = records
        assert records == first_records
        checks = []
        rows = list(csv.DictReader(io.StringIO((root / "review.csv").read_text())))
        assert len(rows) == len(records) == 16
        for record, row in zip(records, rows, strict=True):
            case = record["case"]
            checks.append(check_record(record, plan["cases"][case["case_id"]], plan, descriptor, decode))
            assert record["sequence"]["descriptor_sha256"] == sha(descriptor_path.read_bytes())
            check_html((root / (case["case_id"] + ".html")).read_bytes(), record)
            assert row == {"case_id": case["case_id"], "category": case["category"], "example_id": case["example"]["example_id"],
                           "example_sha256": canonical(case["example"]), "quality_revision_sha256": plan["quality_revision_sha256"],
                           "reviewer": "", "semantic_verdict": "", "token_mask_verdict": "", "reviewed_at_utc": "", "notes": ""}
        page = Page()
        page.feed((root / "index.html").read_text())
        assert page.links == [name + ".html" for name in plan["case_order"]]
        run = json.loads((root / "run.json").read_text())
        assert run["stable_manifest_sha256"] == sha((root / "manifest.json").read_bytes())
        assert run["consumer"] == manifest["consumer"] and run["model_modules_loaded"] == [] and run["training_authorized"] is False
        results[label] = {"manifest_sha256": sha((root / "manifest.json").read_bytes()), "records_sha256": canonical(records),
                          "cases": checks, "html_rows": sum(c["padding_bucket"] for c in checks)}
    assert not {"toolalign", "tokenizers", "transformers", "torch", "mlx", "mlx_lm"} & {k.split(".")[0] for k in sys.modules}
    proof = {"status": "PASS", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "results": results,
             "unique_examples": 16, "new_token_encodings": 0, "production_imports": 0,
             "semantic_verdicts_assigned": 0, "browser_observation": "NOT_RUN", "training_authorized": False}
    Path(job["output"]).write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in proof.items() if k != "results"}))


if __name__ == "__main__":
    main()
