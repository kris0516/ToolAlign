"""Bounded source probes and the same 12 original fixtures, with real CPU engines."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

from review_support import (
    REVISIONS, assert_cpu, cpu_only, measure, read_json, sha, source_check,
    value_sha, write_json,
)


def loaded_state(adapter):
    tokenizer = adapter._tokenizer
    backend = tokenizer if adapter.identity["engine"] == "tokenizers" else tokenizer.backend_tokenizer
    raw = json.loads(backend.to_str())
    # IDs/merges and all execution settings, excluding name_or_path bookkeeping.
    return {"backend_state_sha256": value_sha(raw), "vocab_size": backend.get_vocab_size(),
            "normalizer": raw.get("normalizer"), "pre_tokenizer": raw.get("pre_tokenizer"),
            "decoder": raw.get("decoder"), "padding": raw.get("padding"),
            "truncation": raw.get("truncation"),
            "eos": adapter.encode("<|im_end|>", add_special_tokens=False),
            "sample_ids": adapter.encode("ReviewExtraSentinel57 café e\u0301 <|im_start|>", add_special_tokens=False)}


def source_probes(source, out, engine):
    from toolalign.model_io import ModelIOError
    from toolalign.model_io.offline import OfflineQwenTokenizer

    source_check(source)
    repo_id, revision = next(iter(REVISIONS.items()))

    def build(path):
        return OfflineQwenTokenizer(path, repo_id=repo_id, revision=revision, engine=engine)

    baseline = build(source)
    state = loaded_state(baseline)
    template = read_json(source / "tokenizer_config.json")["chat_template"]
    variants = {
        "added_tokens": {"added_tokens.json": json.dumps({"ReviewExtraSentinel57": 151669})},
        "special_tokens_map": {"special_tokens_map.json": json.dumps({"extra_special_tokens": ["ReviewExtraSentinel57"], "pad_token": "ReviewExtraSentinel57"})},
        "vocab_merges": {"vocab.json": '{"ReviewExtraSentinel57":0}', "merges.txt": "#version: 0.2\n"},
        "same_template": {"chat_template.jinja": template},
        "changed_template": {"chat_template.jinja": template + "REVIEW_TEMPLATE_CHANGED"},
        "named_template": {"additional_chat_templates/review.jinja": template},
        "model_config": {"config.json": '{"model_type":"bert","tokenizer_class":"BertTokenizer"}'},
    }
    results = []
    for label, extras in variants.items():
        root = out / label
        root.mkdir()
        for path in source.iterdir():
            if path.is_file():
                shutil.copyfile(path, root / path.name)
        for name, value in extras.items():
            destination = root / name
            destination.parent.mkdir(exist_ok=True)
            destination.write_text(value)
        record = {"case": label, "extra_file_sha256": {k: sha(v.encode()) for k, v in extras.items()}}
        try:
            adapter = build(root)
        except ModelIOError as exc:
            record.update(outcome="rejected", error=str(exc))
            assert engine == "transformers" and label in {"changed_template", "named_template"}
        else:
            actual = loaded_state(adapter)
            record.update(outcome="accepted", identity_equal=adapter.identity == baseline.identity,
                          actual_state_equal=actual == state, state=actual)
            assert adapter.identity == baseline.identity
            assert actual == state, "accepted_extra_file_changed_actual_tokenizer_state"
        source_check(root)
        results.append(record)
    for name in ("tokenizer.json", "tokenizer_config.json", "LICENSE"):
        root = out / ("tamper_" + name.replace(".", "_"))
        shutil.copytree(source, root)
        data = bytearray((root / name).read_bytes())
        data[0] ^= 1
        (root / name).write_bytes(data)
        try:
            build(root)
        except ModelIOError as exc:
            assert str(exc) == "tokenizer_source_hash_mismatch"
            results.append({"case": "same_size_tamper_" + name, "outcome": "rejected", "error": str(exc)})
        else:
            raise AssertionError("source_tamper_accepted")
    assert_cpu()
    result = {"status": "PASS", "engine": engine, "baseline_identity": baseline.identity,
              "baseline_actual_state": state, "cases": results, "model_modules_loaded": []}
    write_json(out / "result.json", result)
    print(json.dumps({"status": "PASS", "source_scenarios": len(results), "engine": engine,
                      "result_sha256": sha((out / "result.json").read_bytes())}))


def fixtures(root, source, out, engine):
    from toolalign.model_io import pad_sequence
    from toolalign.model_io.offline import OfflineQwenTokenizer
    from toolalign.tools._json import parse_action

    sys.path.insert(0, str(root / "tests/model_io"))
    from model_io_cases import cases

    originals = cases()
    assert len(originals) == 12
    source_check(source)
    descriptor = read_json(root / "configs/model_io.action-json.v1.json")
    template = read_json(source / "tokenizer_config.json")["chat_template"]
    if engine == "transformers":
        from transformers import AutoTokenizer
        reference = AutoTokenizer.from_pretrained(str(source), local_files_only=True, trust_remote_code=False)
        assert reference.chat_template == template
        render = lambda messages: reference.apply_chat_template(messages, tools=None, add_generation_prompt=True, enable_thinking=False, tokenize=False)
        encode = lambda text: reference.encode(text, add_special_tokens=False)
        decode = lambda ids: reference.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
    else:
        from jinja2.sandbox import ImmutableSandboxedEnvironment
        from tokenizers import Tokenizer
        environment = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
        environment.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)
        compiled = environment.from_string(template)
        reference = Tokenizer.from_str((source / "tokenizer.json").read_text())
        render = lambda messages: compiled.render(messages=messages, tools=None, add_generation_prompt=True, enable_thinking=False)
        encode = lambda text: reference.encode(text, add_special_tokens=False).ids
        decode = lambda ids: reference.decode(ids, skip_special_tokens=False)
    models = {}
    for repo, revision in REVISIONS.items():
        adapter = OfflineQwenTokenizer(source, repo_id=repo, revision=revision, engine=engine)
        rows = []
        for name, example in originals:
            before = value_sha(example)
            expected = measure(example, descriptor, render, encode, decode, parse_action)
            actual = adapter.training_sequence(example)
            record = actual.record()
            for field, value in expected.items():
                if field != "roles":
                    assert record[field] == value, (name, field)
            assert list(actual.causal_input_ids) == expected["sequence_ids"][:-1]
            assert list(actual.causal_target_ids) == expected["sequence_ids"][1:]
            padded = pad_sequence(actual, length=len(actual.sequence_ids) + 5, pad_token_id=151645)
            assert list(padded.sequence_ids) == expected["sequence_ids"] + [151645] * 5
            assert list(padded.loss_mask) == expected["loss_mask"] + [0] * 5
            assert list(padded.attention_mask) == [1] * len(actual.sequence_ids) + [0] * 5
            assert sum(padded.causal_loss_mask) == len(actual.sequence_ids) - len(actual.prompt_ids)
            assert before == value_sha(example)
            rows.append({"name": name, "example_sha256": before, "actual": record,
                         "role_bindings": expected["roles"]})
        models[repo] = {"identity": adapter.identity, "state": loaded_state(adapter), "rows": rows}
    source_check(source)
    assert_cpu()
    result = {"status": "PASS", "distinct_scenarios": 12, "identity_rows": 24,
              "fixture_sha256": value_sha(originals), "engine": engine,
              "models": models, "model_modules_loaded": [],
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}}
    write_json(out / "result.json", result)
    print(json.dumps({"status": "PASS", "distinct_scenarios": 12, "identity_rows": 24,
                      "engine": engine, "result_sha256": sha((out / "result.json").read_bytes())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("sources", "fixtures"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--engine", choices=("tokenizers", "transformers"), required=True)
    args = parser.parse_args()
    cpu_only()
    args.out.mkdir(exist_ok=False, parents=True)
    if args.mode == "sources":
        source_probes(args.source, args.out, args.engine)
    else:
        fixtures(args.root, args.source, args.out, args.engine)
