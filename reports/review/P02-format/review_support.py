"""Independent P02 format review helpers; CPU only, no production formatting code."""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.util
import json
import os
import sys
from pathlib import Path

CANDIDATE = "7bada2e451d43dae4b3ed532d5efa310fc8e6a57"
REVISIONS = {
    "Qwen/Qwen3-0.6B": "c1899de289a04d12100db370d81485cdf75e47ca",
    "Qwen/Qwen3-1.7B": "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e",
}
SOURCE_HASHES = {
    "tokenizer.json": "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
    "tokenizer_config.json": "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101",
    "LICENSE": "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
}
MODEL_ROOTS = {"torch", "mlx", "mlx_lm", "mlx_tune", "tensorflow", "flax", "jax"}


def cpu_only():
    for key, value in {
        "USE_TORCH": "0", "USE_TF": "0", "USE_FLAX": "0",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1", "TOKENIZERS_PARALLELISM": "false",
    }.items():
        os.environ[key] = value

    # A metadata availability lookup is not an import. These review environments
    # contain no model packages, and an audit hook also rejects actual imports.
    assert all(importlib.util.find_spec(name) is None for name in MODEL_ROOTS)

    def audit(event, args):
        if event == "import" and args[0].split(".")[0] in MODEL_ROOTS:
            raise AssertionError("Forbidden model import: " + args[0])

    sys.addaudithook(audit)

    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if (
                fullname.startswith("transformers.models.")
                and any(p.startswith("modeling_") for p in fullname.split("."))
            ):
                raise AssertionError("Forbidden model import: " + fullname)
            return None

    sys.meta_path.insert(0, Guard())
    assert_cpu()


def assert_cpu():
    assert not MODEL_ROOTS & {n.split(".")[0] for n in sys.modules}
    assert not any(n.startswith("transformers.models.") and ".modeling_" in n for n in sys.modules)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def value_sha(value):
    return sha(canonical(value))


def wire(value):
    return canonical(value).decode().replace("<", "\\u003c").replace(">", "\\u003e")


def write_json(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def read_json(path):
    return json.loads(Path(path).read_bytes())


def source_check(root):
    actual = {n: sha((Path(root) / n).read_bytes()) for n in SOURCE_HASHES}
    assert actual == SOURCE_HASHES
    return actual


def projection(model_input, descriptor):
    return [{"role": "system", "content": descriptor["instruction"] + "\n" + wire({
        "format_version": descriptor["format_id"], "tools": model_input["tools"],
    })}] + [{"role": m["role"], "content": wire({"message": m, "message_index": i})}
            for i, m in enumerate(model_input["messages"])]


def expected_render(model_input, descriptor):
    """Independent control-segment construction for this pinned non-thinking branch.

    Projection removes native calls and literal angle brackets before rendering;
    completed histories end with user/tool. Therefore assistant histories do not
    require invented reasoning blocks, while consecutive tools share one user block.
    """
    projected = projection(model_input, descriptor)
    pieces, roles, segment = [], [], 0
    for i, message in enumerate(projected):
        role, content = message["role"], message["content"]
        if role != "tool":
            segment += 1
            pieces.append("<|im_start|>" + role + "\n" + content + "<|im_end|>\n")
        else:
            if projected[i - 1]["role"] != "tool":
                segment += 1
                pieces.append("<|im_start|>user")
            pieces.append("\n<tool_response>\n" + content + "\n</tool_response>")
            if i == len(projected) - 1 or projected[i + 1]["role"] != "tool":
                pieces.append("<|im_end|>\n")
        if i:
            roles.append({"index": i - 1, "original_role": role,
                          "control_role": "user" if role == "tool" else role,
                          "segment_index": segment - 1, "tool_response_wrapper": role == "tool"})
            assert json.loads(content) == {"message_index": i - 1, "message": model_input["messages"][i - 1]}
    pieces.append("<|im_start|>assistant\n<think>\n\n</think>\n\n")
    return "".join(pieces), roles


def measure(example, descriptor, render, encode, decode, parse_action):
    """A separately implemented sequence calculation; no candidate sequence helper."""
    model_input = {k: example[k] for k in ("messages", "tools")}
    prompt = render(projection(model_input, descriptor))
    constructed, roles = expected_render(model_input, descriptor)
    assert prompt == constructed, "actual_control_segments_differ"
    completion = wire(example["expected_action"])
    pids, joined = encode(prompt), encode(prompt + completion)
    assert pids and joined[:len(pids)] == pids
    cids = joined[len(pids):]
    assert cids and 151645 not in cids and decode(cids) == completion
    assert parse_action(completion) == example["expected_action"]
    seq = joined + [151645]
    mask = [0] * len(pids) + [1] * (len(cids) + 1)
    assert seq[len(pids):].count(151645) == 1
    assert mask[1:].index(1) == len(pids) - 1
    return {"prompt_text": prompt, "completion_text": completion,
            "prompt_ids": pids, "concatenated_ids": joined, "sequence_ids": seq,
            "loss_mask": mask, "causal_loss_mask": mask[1:], "roles": roles}
