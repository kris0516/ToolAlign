"""Run an offline tokenizer evidence collector in either isolated environment.

Usage: python tests/data/tokenizer_crosscheck.py --engine local|hf --output PRIVATE.json
No imports from the T1 implementation; HF reference calls its own public APIs.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from tokenizer_cases import cases

from toolalign.contracts import canonical_hash
from toolalign.data.common import file_hash, read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["local", "hf"], required=True)
    parser.add_argument("--tokenizer-dir", default=".toolalign-local/verified-source/qwen")
    parser.add_argument("--manifest", default="data/manifests/qwen-source.v1.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    for name in (
        "HF_HUB_OFFLINE",
        "HF_HUB_DISABLE_TELEMETRY",
        "HF_HUB_DISABLE_IMPLICIT_TOKEN",
        "TRANSFORMERS_OFFLINE",
    ):
        os.environ[name] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    destination = Path(args.output).resolve()
    if ".toolalign-local" not in destination.parts or destination.exists():
        raise ValueError("Use a new private evidence path")
    root = Path(args.tokenizer_dir)
    lock = read_json(args.manifest)
    for name, spec in lock["files"].items():
        assert file_hash(root / name) == spec["sha256"]
    results = []
    if args.engine == "hf":
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            root, local_files_only=True, trust_remote_code=False
        )
        eos_id = tokenizer.eos_token_id
    else:
        from toolalign.data.lengths import LocalTokenizer

        local = LocalTokenizer(root, lock)
        eos_id = local.tokenizer.token_to_id(read_json(root / "tokenizer_config.json")["eos_token"])
    for case in cases():
        if args.engine == "hf":
            prompt = tokenizer.apply_chat_template(
                case["reference_messages"],
                tools=case["reference_tools"],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            # Independent tokenizing template entry point is checked against direct encoding.
            prompt_ids = tokenizer.apply_chat_template(
                case["reference_messages"],
                tools=case["reference_tools"],
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            if isinstance(prompt_ids, Mapping):
                prompt_ids = prompt_ids["input_ids"]
            assert list(prompt_ids) == tokenizer(prompt, add_special_tokens=False)["input_ids"]
            completion = case["reference_completion"]
            full_ids = tokenizer(prompt + completion, add_special_tokens=False)["input_ids"]
            measured = None
        else:
            if hasattr(local, "training_sequence"):
                view = local.training_sequence(case["example"], require_stable_prefix=False)
                prompt, completion = view["prompt_text"], view["completion_text"]
                prompt_ids, full_ids = view["prompt_ids"], view["concatenated_ids"]
            else:
                prompt = local.render(case["wire_roundtrip"]["messages"], case["reference_tools"])
                completion = case["reference_completion"]
                prompt_ids = local.tokenizer.encode(prompt, add_special_tokens=False).ids
                full_ids = local.tokenizer.encode(prompt + completion, add_special_tokens=False).ids
            try:
                measured = local.normalized(case["example"])
            except ValueError as exc:
                measured = {"rejection": str(exc)}
        stable = list(full_ids[: len(prompt_ids)]) == list(prompt_ids)
        sequence = [*full_ids, eos_id]
        item = {
            "id": case["id"],
            "example_hash": canonical_hash(case["wire_roundtrip"]),
            "prompt_text": prompt,
            "completion_text": completion,
            "prompt_ids": list(prompt_ids),
            "concatenated_ids": list(full_ids),
            "sequence_ids": sequence,
            "eos_token_id": eos_id,
            "prefix_stable": stable,
            "sequence_length": len(sequence),
            "completion_length_if_stable": len(sequence) - len(prompt_ids) if stable else None,
            "terminal_eos_run": None,
            "local_normalized_measurement": measured,
        }
        n = 0
        for token in reversed(sequence):
            if token != eos_id:
                break
            n += 1
        item["terminal_eos_run"] = n
        results.append(item)
    versions = {p: importlib.metadata.version(p) for p in ("tokenizers", "Jinja2")}
    if args.engine == "hf":
        versions["transformers"] = importlib.metadata.version("transformers")
    output = {
        "engine": args.engine,
        "packages": versions,
        "tokenizer_lock_hash": canonical_hash(lock),
        "fixture_file_sha256": file_hash(Path(__file__).with_name("tokenizer_cases.py")),
        "tokenizer_files": lock["files"],
        "results": results,
        "model_libraries_loaded": [name for name in ("torch", "mlx") if name in sys.modules],
    }
    write_json(destination, output)
    print(
        json.dumps(
            {
                "cases": len(results),
                "stable": sum(r["prefix_stable"] for r in results),
                "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "packages": versions,
                "model_libraries_loaded": output["model_libraries_loaded"],
            }
        )
    )


if __name__ == "__main__":
    main()
