"""Optional local tokenizer audit; imports neither transformers nor model weights."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

from toolalign.contracts import canonical_hash, model_input_from_example

from .common import DataError, encoded, file_hash, read_json

TRAINING_LENGTH_BASIS = "qwen3_non_thinking_concat_one_eos_v1"


def quantiles(values):
    values = sorted(values)
    return {
        f"p{p}": values[max(0, math.ceil(len(values) * p / 100) - 1)] if values else None
        for p in (50, 90, 95, 99)
    }


class LocalTokenizer:
    def __init__(self, root, manifest):
        if (
            manifest.get("repo_id") != "Qwen/Qwen3-0.6B"
            or manifest.get("enable_thinking") is not False
        ):
            raise DataError("tokenizer_identity_or_thinking_mismatch")
        from jinja2.sandbox import ImmutableSandboxedEnvironment
        from tokenizers import Tokenizer

        for package, version in manifest["packages"].items():
            if importlib.metadata.version(package) != version:
                raise DataError("tokenizer_package_version_mismatch")
        root = Path(root)
        for name, info in manifest["files"].items():
            if name not in {"tokenizer.json", "tokenizer_config.json", "LICENSE"}:
                raise DataError("tokenizer_file_not_allowed")
            if file_hash(root / name) != info["sha256"]:
                raise DataError("tokenizer_file_hash_mismatch")
        config = read_json(root / "tokenizer_config.json")
        template = config["chat_template"]
        if hashlib.sha256(template.encode()).hexdigest() != manifest["template_sha256"]:
            raise DataError("tokenizer_template_mismatch")
        # Reviewed official immutable template, not a template from a data record.
        environment = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
        environment.filters["tojson"] = lambda value: json.dumps(value, ensure_ascii=False)
        self.template = environment.from_string(template)
        self.tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))
        self.eos_token_id = self.tokenizer.token_to_id(config["eos_token"])
        if self.eos_token_id is None or self.encode(config["eos_token"]) != [self.eos_token_id]:
            raise DataError("tokenizer_eos_not_single_token")
        self.manifest = manifest

    def encode(self, text):
        return list(self.tokenizer.encode(text, add_special_tokens=False).ids)

    def count(self, text):
        return len(self.encode(text))

    def render(self, messages, tools=None):
        return self.template.render(
            messages=messages, tools=tools, add_generation_prompt=True, enable_thinking=False
        )

    def raw_decision(self, record, turn_index, schema_span):
        messages = [{"role": "system", "content": record["system"]}]
        messages += [
            {"role": t["from"], "content": t["value"]} for t in record["conversations"][:turn_index]
        ]
        rendered = self.render(messages)
        total_prompt = self.count(rendered)
        if schema_span:
            a, b = schema_span
            messages[0]["content"] = record["system"][:a] + record["system"][b:]
            prompt_without_schema = self.count(self.render(messages))
            schema = total_prompt - prompt_without_schema
        else:
            prompt_without_schema, schema = None, None
        completion = self.count(record["conversations"][turn_index]["value"] + "<|im_end|>\n")
        return {
            "prompt_tokens": total_prompt,
            "schema_marginal_tokens": schema,
            "prompt_without_schema_tokens": prompt_without_schema,
            "completion_tokens": completion,
            "total_tokens": total_prompt + completion,
        }

    def training_sequence(self, example, *, require_stable_prefix=True):
        """Render and encode a storage-stable sequence with exactly one appended EOS.

        The diagnostic opt-out exposes boundary failures to the independent CPU
        comparison. Production length measurement always requires a stable prefix.
        No EOS newline is appended, and existing literal EOS tokens are retained.
        """
        # examples.jsonl sorts all object keys. Bind in-memory measurement to the
        # same ordering that a downstream trainer will see after reading the file.
        projection = json.loads(encoded(model_input_from_example(example)))
        tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters_json_schema"],
                },
            }
            for t in projection["tools"]
        ]
        prompt_text = self.render(projection["messages"], tools)
        action = json.loads(encoded(example["expected_action"]))
        if action["kind"] == "tool_calls":
            completion = "\n".join(
                "<tool_call>\n"
                + json.dumps({"name": c["name"], "arguments": c["arguments"]}, ensure_ascii=False)
                + "\n</tool_call>"
                for c in action["tool_calls"]
            )
        else:
            completion = action["content"]
        prompt_ids = self.encode(prompt_text)
        concatenated = self.encode(prompt_text + completion)
        stable = concatenated[: len(prompt_ids)] == prompt_ids
        if require_stable_prefix and not stable:
            raise DataError("prompt_completion_boundary_changed")
        return {
            "prompt_text": prompt_text,
            "prompt_without_tools_text": self.render(projection["messages"]),
            "completion_text": completion,
            "prompt_ids": prompt_ids,
            "concatenated_ids": concatenated,
            "sequence_ids": [*concatenated, self.eos_token_id],
            "prefix_stable": stable,
            "eos_token_id": self.eos_token_id,
            "length_basis": TRAINING_LENGTH_BASIS,
        }

    def normalized(self, example):
        sequence = self.training_sequence(example)
        prompt = len(sequence["prompt_ids"])
        full = len(sequence["sequence_ids"])
        without = self.count(sequence["prompt_without_tools_text"])
        return {
            "prompt_tokens": prompt,
            "schema_marginal_tokens": prompt - without,
            "prompt_without_schema_tokens": without,
            "completion_tokens": full - prompt,
            "total_tokens": full,
            "length_basis": TRAINING_LENGTH_BASIS,
            "prefix_stable": True,
            "eos_token_id": self.eos_token_id,
            "sequence_hash": canonical_hash(sequence["sequence_ids"]),
        }


def summarize_lengths(rows):
    fields = (
        "prompt_tokens",
        "schema_marginal_tokens",
        "prompt_without_schema_tokens",
        "completion_tokens",
        "total_tokens",
    )
    result = {
        k: {
            "count": sum(r[k] is not None for r in rows),
            **quantiles([r[k] for r in rows if r[k] is not None]),
        }
        for k in fields
    }
    attributable = [r for r in rows if r["schema_marginal_tokens"] is not None]
    denominator = sum(r["total_tokens"] for r in attributable)
    result["aggregate_token_shares"] = {
        k: sum(r[k] for r in attributable) / denominator if denominator else None
        for k in ("prompt_without_schema_tokens", "schema_marginal_tokens", "completion_tokens")
    }
    result["attribution_decisions"] = len(attributable)
    return result
