"""R1 read-only audit of the exact P01 historical evidence and installed metadata.

Uses standard-library byte/JSON checks and independent tokenizer rendering.
Never imports a model package, materializes weight arrays, or changes T1 files.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.metadata
import json
import math
import statistics
import struct
import subprocess
import sys
import tomllib
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = "59b3802c81aa6eceaf3609af88f288756bcb1581"
PREVIOUS = "f97bb0de346c220871962a5689014a379fe19c83"


class RejectModelImports(importlib.abc.MetaPathFinder):
    forbidden = {"mlx", "mlx_lm", "mlx_lm_lora", "mlx_tune", "transformers", "torch"}

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in self.forbidden:
            raise AssertionError("Model packages are forbidden in the evidence audit")
        return None


def read_json(path):
    return json.loads(path.read_text())


def sha_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def inside(path, root):
    assert not path.is_symlink()
    assert path.resolve().is_relative_to(root.resolve())
    return path


def tensor_digests(path):
    """Stream raw safetensors byte ranges without importing any tensor backend."""
    with path.open("rb") as stream:
        prefix = stream.read(8)
        assert len(prefix) == 8
        header_bytes = struct.unpack("<Q", prefix)[0]
        assert header_bytes < 8 * 1024**2
        header = json.loads(stream.read(header_bytes))
        data_start = 8 + header_bytes
        ranges = []
        result = {}
        for name, info in header.items():
            if name == "__metadata__":
                continue
            first, last = info["data_offsets"]
            assert 0 <= first <= last <= path.stat().st_size - data_start
            item_size = {"BF16": 2, "F32": 4}[info["dtype"]]
            assert math.prod(info["shape"]) * item_size == last - first
            ranges.append((first, last))
            stream.seek(data_start + first)
            hasher = hashlib.sha256()
            remaining = last - first
            while remaining:
                block = stream.read(min(remaining, 1024**2))
                assert block
                hasher.update(block)
                remaining -= len(block)
            result[name] = {"sha256": hasher.hexdigest(), "shape": info["shape"],
                            "dtype": info["dtype"]}
        ordered = sorted(ranges)
        assert ordered[0][0] == 0
        assert all(a[1] == b[0] for a, b in zip(ordered, ordered[1:]))
        assert ordered[-1][1] == path.stat().st_size - data_start
        return result


class LocalTokenizer:
    def __init__(self, directory):
        from jinja2.sandbox import ImmutableSandboxedEnvironment
        from tokenizers import Tokenizer

        self.config = read_json(directory / "tokenizer_config.json")
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.eos = self.config["eos_token"]
        self.eos_id = self.tokenizer.token_to_id(self.eos)
        env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True,
                                           extensions=["jinja2.ext.loopcontrols"])
        env.filters["tojson"] = lambda value, **kwargs: json.dumps(value, ensure_ascii=False, **kwargs)
        env.globals["raise_exception"] = lambda message: (_ for _ in ()).throw(ValueError(message))
        self.template = env.from_string(self.config["chat_template"])

    def prefix(self, sample):
        return self.template.render(messages=sample["messages"], tools=sample["tools"],
                                    add_generation_prompt=True, enable_thinking=False,
                                    eos_token=self.eos, bos_token=self.config.get("bos_token"))

    def encode(self, text):
        return self.tokenizer.encode(text, add_special_tokens=False).ids

    def row(self, sample):
        prompt = self.prefix(sample)
        prefix_ids = self.encode(prompt)
        joined_ids = self.encode(prompt + sample["completion"])
        assert joined_ids[:len(prefix_ids)] == prefix_ids
        assert self.eos_id not in joined_ids[len(prefix_ids):]
        ids = joined_ids + [self.eos_id]
        masks = [int(index >= len(prefix_ids)) for index in range(len(ids))]
        return {"token_ids": ids, "completion_mask": masks,
                "prompt_length": len(prefix_ids), "eos_id": self.eos_id}


def validate_samples(samples, tokenizer, config, audits):
    assert len(samples) == len(audits) == 32
    assert Counter(sample["kind"] for sample in samples) == {
        "call": 8, "observation": 8, "no_tool": 8, "clarify": 8}
    assert len({sample["id"] for sample in samples}) == 32
    for index, (sample, audit) in enumerate(zip(samples, audits)):
        assert sample["id"] == f"p01-smoke-{index:02d}" and sample["split"] == "train"
        kind = ("call", "observation", "no_tool", "clarify")[index % 4]
        assert sample["kind"] == kind
        expected = (
            f'<tool_call>\n{{"name":"add","arguments":{{"a":{index},"b":2}}}}\n</tool_call>'
            if kind == "call" else str(index + 2) if kind == "observation"
            else f"smoke-{index}" if kind == "no_tool" else "Which number should I add?"
        )
        assert sample["completion"] == expected
        assert sample["messages"][-1]["role"] in {"user", "tool"}
        if kind == "observation":
            assert sample["messages"][-1] == {"role": "tool", "content": str(index + 2)}
            assert sample["messages"][-2]["tool_calls"][0]["function"] == {
                "name": "add", "arguments": {"a": index, "b": 2}}
        independent = tokenizer.row(sample)
        for key, value in independent.items():
            assert canonical(audit[key]) == canonical(value), (config["run_id"], index, key)
        boundary = independent["prompt_length"]
        assert sum(independent["completion_mask"][:boundary]) == 0
        assert independent["token_ids"][boundary:].count(tokenizer.eos_id) == 1
        assert len(independent["token_ids"]) <= config["sequence_length"]
        if config["mode"] == "calibrate":
            assert len(independent["token_ids"]) <= config["sequence_length"] - 64
            grown = json.loads(json.dumps(sample))
            grown["messages"][1]["content"] += " neutral"
            assert len(tokenizer.row(grown)["token_ids"]) > config["sequence_length"] - 64
    pairs = []
    for sample, chosen in zip(samples[:2], audits[:2]):
        rejected = tokenizer.row({**sample, "completion": "I cannot determine the result."})
        assert rejected["prompt_length"] == chosen["prompt_length"]
        boundary = chosen["prompt_length"]
        assert rejected["token_ids"][:boundary] == chosen["token_ids"][:boundary]
        pairs.append((chosen, rejected))
    return pairs


def model_inventory(config, t1_private):
    directory = inside(Path(config["model_dir"]), t1_private)
    actual = {}
    tensors = {}
    for name, expected in config["model_files"].items():
        assert Path(name).name == name
        path = inside(directory / name, directory)
        actual[name] = {"sha256": sha_file(path), "size_bytes": path.stat().st_size}
        assert actual[name] == expected
        metadata = directory / ".cache/huggingface/download" / (name + ".metadata")
        lines = metadata.read_text().splitlines()
        assert lines[0] == config["model_revision"]
        if name.endswith(".safetensors"):
            assert lines[1] == expected["sha256"]
            subset = tensor_digests(path)
            assert not tensors.keys() & subset.keys()
            tensors.update(subset)
    identity = config["model_identity"]
    assert digest({key: value for key, value in actual.items()
                   if key.endswith(".safetensors") or key == "config.json"}) == identity["model_hash"]
    assert digest({key: value for key, value in actual.items()
                   if "tokenizer" in key or key in {"vocab.json", "merges.txt"}}) == identity["tokenizer_hash"]
    tokenizer = LocalTokenizer(directory)
    assert digest({"template": tokenizer.config["chat_template"], "enable_thinking": False,
                   "add_generation_prompt": True}) == identity["template_hash"]
    return actual, tensors, tokenizer


def check_parameters(directory, config, tensors, raw_result):
    before = read_json(directory / "parameter-identities-before.json")
    after = read_json(directory / "parameter-identities-after.json")
    assert before.keys() == after.keys()
    adapter_keys = {name for name in before if name.endswith((".lora_a", ".lora_b"))}
    expected_keys = {f"model.layers.{layer}.self_attn.{projection}.lora_{suffix}"
                     for layer in range(28) for projection in ("q_proj", "v_proj")
                     for suffix in ("a", "b")}
    assert adapter_keys == expected_keys
    for name in before.keys() - adapter_keys:
        source = name.replace(".q_proj.linear.", ".q_proj.").replace(".v_proj.linear.", ".v_proj.")
        assert before[name] == after[name] == tensors[source]["sha256"]
    changed = {name for name in before if before[name] != after[name]}
    assert changed and changed <= adapter_keys
    assert len(changed) == raw_result["sft"]["changed_parameter_count"]
    saved = tensor_digests(directory / "sft-adapter/adapters.safetensors")
    assert saved.keys() == adapter_keys
    assert all(record["sha256"] == after[name] for name, record in saved.items())
    metadata = read_json(directory / "sft-adapter/adapter_config.json")
    assert metadata == raw_result["sft"]["adapter_metadata"]
    assert metadata["num_layers"] == 28
    assert metadata["lora_parameters"] == {"rank": 8, "scale": 2.0, "dropout": 0.0,
                                          "keys": ["self_attn.q_proj", "self_attn.v_proj"]}
    sft_file = directory / "sft-adapter/adapters.safetensors"
    assert sha_file(sft_file) == sha_file(directory / f'sft-adapter/{config["sft_steps"]:07d}_adapters.safetensors')
    dpo_path = directory / "fallback-dpo/adapters.safetensors"
    dpo_changed = None
    if dpo_path.exists():
        dpo = tensor_digests(dpo_path)
        assert dpo.keys() == adapter_keys
        dpo_changed = sum(dpo[name]["sha256"] != saved[name]["sha256"] for name in adapter_keys)
        assert dpo_changed == raw_result["dpo"]["changed_parameters"]
        assert sha_file(dpo_path) == sha_file(directory / f'fallback-dpo/{config["dpo_steps"]:07d}_adapters.safetensors')
        assert read_json(directory / "fallback-dpo/adapter_config.json") == metadata
    return {"base_arrays_bound_to_original_bytes": len(before) - len(adapter_keys),
            "declared_adapter_arrays": len(adapter_keys), "sft_changed_arrays": len(changed),
            "dpo_changed_arrays": dpo_changed, "saved_adapter_arrays_match_logged_hashes": True}


def audit_runs(t1_root):
    from toolalign.contracts import validate_record

    public = read_json(ROOT / "reports/hardware/P01_RESULTS.json")
    runs = t1_root / ".toolalign-local/runs"
    output, models = [], {}
    for published in public["runs"]:
        directory = inside(runs / published["run_id"].removeprefix("p01-"), runs)
        config = read_json(directory / "config.json")
        resources = read_json(directory / "resources.json")
        assert config["run_id"] == published["run_id"]
        assert config["git_commit"] == published["git_commit"]
        assert digest(config["source_files"]) == config["source_hash"] == published["source_hash"]
        source_matches = 0
        source_commit = config["git_commit"]
        source_mismatches = []
        if config["run_id"] != "p01-math-r1":
            for name, expected in config["source_files"].items():
                content = git("show", config["git_commit"] + ":src/toolalign/training/compatibility/" + name)
                if hashlib.sha256(content).hexdigest() == expected:
                    source_matches += 1
                else:
                    source_mismatches.append(name)
            if source_mismatches:
                # Preserve the discovered provenance discrepancy; independently resolve
                # every recorded byte to a later commit instead of changing raw evidence.
                assert config["run_id"] == "p01-math-r2"
                assert set(source_mismatches) == {"numerical.py", "model_probe.py"}
                source_commit = "47c03404bab043e85b417cd8a6d0432dc2f85479"
                for name, expected in config["source_files"].items():
                    content = git("show", source_commit + ":src/toolalign/training/compatibility/" + name)
                    assert hashlib.sha256(content).hexdigest() == expected
        evidence = {}
        for name, expected in published["evidence_hashes"].items():
            path = inside(directory / name, directory)
            assert sha_file(path) == expected
            evidence[name] = expected
        assert resources["exit_code"] == published["exit_code"]
        assert resources["stop_reason"] == published["stop_reason"]
        assert resources["peak_rss_bytes"] == max(sample["rss_bytes"] for sample in resources["samples"])
        assert resources["peak_rss_bytes"] == published["peak_rss_bytes"]
        assert resources["wall_seconds"] == published["wall_seconds"]
        assert resources["budget"] == config["budget"]
        assert published["hardware"] == config["hardware"]
        assert published["dependency_versions"] == config["dependency_versions"]
        assert published["compile_disabled"] == config.get("fallback_disable_compile", False)
        assert published["dpo_checkpointing"] == config.get("fallback_grad_checkpoint", False)
        assert published["sft_checkpointing"] == config.get("grad_checkpoint", False)
        assert published["max_swap_growth_bytes"] == max(sample["swap_growth_bytes"] for sample in resources["samples"])
        assert published["max_pressure_level"] == max(sample["pressure"] for sample in resources["samples"])
        lease = read_json(directory / "lease-acquired.json")
        assert lease["acquired"] is True
        result_path = directory / "result.json"
        raw = read_json(result_path if result_path.exists() else directory / "partial-result.json")
        assert raw["status"] == published["raw_result_status"]
        item = {"run_id": config["run_id"], "source_hash": config["source_hash"],
                "source_files_matched_to_commit": source_matches,
                "recorded_head_source_mismatches": source_mismatches,
                "resolved_source_commit": source_commit if config["run_id"] != "p01-math-r1" else None,
                "evidence_hashes": evidence, "raw_result_status": raw["status"],
                "assessment": published["assessment"], "exit_code": resources["exit_code"]}
        if config["mode"] == "math":
            assert raw == published["math"]
            item["math"] = raw
            output.append(item)
            continue
        manifest = read_json(directory / "run.json")
        validate_record(manifest)
        assert manifest["status"] in {"succeeded", "failed"}
        assert manifest["exit_code"] == resources["exit_code"]
        assert datetime.fromisoformat(manifest["started_at"]) <= datetime.fromisoformat(lease["time"])
        assert datetime.fromisoformat(lease["time"]) <= datetime.fromisoformat(manifest["ended_at"])
        for artifact in manifest["artifacts"]:
            path = inside(directory / artifact["relative_path"], directory)
            assert path.stat().st_size == artifact["size_bytes"]
            assert sha_file(path) == artifact["sha256"] == artifact["artifact_id"]
        assert len(manifest["artifacts"]) == published["manifest_artifacts_verified"]
        if config["model_id"] not in models:
            models[config["model_id"]] = model_inventory(config, t1_root / ".toolalign-local")
        model_files, tensors, tokenizer = models[config["model_id"]]
        assert config["model_files"] == model_files
        assert manifest["model"] == config["model_identity"] == published["model_identity"]
        samples = read_json(directory / "samples.json")
        audits = read_json(directory / "token-audit.json")
        pairs = validate_samples(samples, tokenizer, config, audits)
        assert digest(samples) == manifest["data_manifest_hash"] == raw["data_hash"]
        params = check_parameters(directory, config, tensors, raw)
        reference = read_json(directory / "sft-reference.json")
        assert reference["stage"] == "sft_smoke"
        assert reference["adapter_hash"] == sha_file(directory / "sft-adapter/adapters.safetensors")
        for key in ("base_hash", "tokenizer_hash", "template_hash"):
            assert reference[key] == config["model_identity"]["model_hash" if key == "base_hash" else key]
        assert digest(reference) == manifest["reference_model_hash"] == published["reference_model_hash"]
        execution_identity = {"source_hash": config["source_hash"],
                              "dependencies": config["dependency_versions"],
                              "compile_disabled": config.get("fallback_disable_compile", False)}
        if config["run_id"] in {"p01-smoke06-r1", "p01-smoke06-r2", "p01-smoke06-r3"}:
            expected_code_hash = config["source_hash"]
            identity_rule = "historical_source_hash_only"
        elif config["run_id"] in {"p01-calibrate17-1536-r2", "p01-calibrate17-2048-r1"}:
            execution_identity.update(sft_grad_checkpoint=config.get("grad_checkpoint", False),
                                      dpo_grad_checkpoint=config.get("fallback_grad_checkpoint", False))
            expected_code_hash = digest(execution_identity)
            identity_rule = "source_dependencies_compile_and_checkpointing"
        else:
            expected_code_hash = digest(execution_identity)
            identity_rule = "source_dependencies_and_compile"
        assert reference["code_hash"] == expected_code_hash
        cache = read_json(directory / "reference-cache.json")
        for cached, pair in zip(cache, pairs):
            c, r = pair
            columns = ["token_ids", "completion_mask", "prompt_length", "eos_id"]
            key = digest({"identity": reference, "chosen": {key: c[key] for key in columns},
                          "rejected": {key: r[key] for key in columns}})
            assert key == cached["key"]
            assert all(math.isfinite(cached[key]) for key in ("chosen_logp", "rejected_logp"))
        steps = read_json(directory / "sft-steps.json")
        assert len(steps) == config["sft_steps"] == raw["sft"]["microsteps"]
        for index, step in enumerate(steps):
            row = audits[index % 32]
            assert step["iteration"] == index + 1
            assert step["optimizer_steps"] == (index + 1) // config["sft_accumulation"]
            assert step["supervised_tokens"] == sum(row["completion_mask"])
            assert step["nonpadding_tokens"] == len(row["token_ids"]) - 1
            width = config["sequence_length"] if config["mode"] == "calibrate" else len(row["token_ids"])
            assert step["processed_tokens"] == width - 1
        warmup = config["warmup_steps"]
        measured = [step["synchronized_seconds"] for step in steps[warmup:]]
        assert raw["sft"]["warmup_microsteps"] == warmup
        assert raw["sft"]["measured_microsteps"] == len(measured)
        assert raw["sft"]["measured_seconds"] == sum(measured)
        assert raw["sft"]["step_seconds_mean"] == statistics.mean(measured)
        assert raw["sft"]["step_seconds_stdev"] == statistics.stdev(measured)
        dpo_path = directory / "fallback-dpo-steps.json"
        dpo_steps = read_json(dpo_path) if dpo_path.exists() else []
        for index, step in enumerate(dpo_steps):
            assert step["iteration"] == index + 1
            assert step["optimizer_steps"] == (index + 1) // config["fallback_accumulation"]
            pair = pairs[index % 2]
            assert step["supervised_tokens"] == sum(sum(row["completion_mask"]) for row in pair)
            unpadded = sum(len(row["token_ids"]) - 1 for row in pair)
            # The retained invalid r2 used a common chosen/rejected padded shape;
            # final passing runs deliberately use separate unpadded lengths.
            processed = (2 * (max(len(row["token_ids"]) for row in pair) - 1)
                         if config["run_id"] == "p01-smoke06-r2" else unpadded)
            assert step["processed_tokens"] == processed
            assert step["nonpadding_tokens"] == unpadded
        progress = read_json(directory / "progress.json")
        all_steps = steps + dpo_steps
        assert progress["microsteps"] == len(all_steps)
        assert progress["training_tokens"] == sum(step["supervised_tokens"] for step in all_steps)
        assert progress["processed_tokens"] == sum(step["processed_tokens"] for step in all_steps)
        assert progress["processed_nonpadding_tokens"] == sum(step["nonpadding_tokens"] for step in all_steps)
        assert progress["optimizer_steps"] == steps[-1]["optimizer_steps"] + (dpo_steps[-1]["optimizer_steps"] if dpo_steps else 0)
        assert manifest["training_tokens"] == progress["training_tokens"]
        assert manifest["optimizer_steps"] == progress["optimizer_steps"]
        assert published["progress"] == progress
        for key in ("sft", "dpo", "primary_dpo", "cross_library", "reference", "generation",
                    "checkpoint_io", "phase_seconds", "token_audit", "complete_task_inference"):
            if key in raw:
                assert canonical(raw[key]) == canonical(published[key])
        if dpo_steps:
            maximum = max(abs(step["train_loss"] - math.log(2)) for step in dpo_steps[:config["fallback_accumulation"]])
            assert maximum == published["actual_initial_training_loss_max_abs_error"]
            if config["run_id"] == "p01-smoke06-r2":
                assert raw["dpo"]["status"] == "PASS" and maximum > 2e-6
                assert published["assessment"] == "FAIL_TRAINING_PATH_LN2"
            else:
                assert maximum < 2e-6
                assert raw["dpo"]["training_path_initial_losses"] == [step["train_loss"] for step in dpo_steps]
                assert raw["dpo"]["reference_hash_and_outputs_unchanged"] is True
        events = read_json(directory / "events.json")
        if "checkpoint_io" in raw:
            for phase in ("sft", "dpo"):
                assert raw["checkpoint_io"][phase] == sum(event["seconds"] for event in events
                    if event["event"] == "checkpoint_write" and event["phase"] == phase)
        assert raw["cross_library"]["all_parameter_hashes_identical"] is True
        assert raw["cross_library"]["max_logit_abs_error"] <= 1e-5
        assert raw["cross_library"]["max_logp_abs_error"] <= 1e-5
        assert raw["complete_task_inference"]["status"] == "NOT_RUN"
        for generation in raw["generation"]:
            assert generation["generated_tokens"] <= 32 and generation["wall_seconds"] < 30
        item.update({"manifest_artifacts_checked": len(manifest["artifacts"]),
                     "samples_retokenized": len(samples), "pair_prefixes_checked": len(pairs),
                     "parameter_bytes": params, "progress": progress,
                     "sft_warmup_microsteps": warmup, "sft_measured_microsteps": len(measured),
                     "sft_measured_seconds": sum(measured), "dpo_recorded_microsteps": len(dpo_steps),
                     "reference_code_identity_rule": identity_rule,
                     "reference_stage": reference["stage"], "stop_reason": resources["stop_reason"]})
        output.append(item)
    return {"runs": output, "model_files": {name: value[0] for name, value in models.items()},
            "run_count": len(output), "raw_weights_loaded_as_models": False,
            "model_tensor_arrays_materialized": False}


def audit_metadata(t1_root):
    from packaging.markers import default_environment
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    expected = read_json(ROOT / "reports/hardware/P01_BASE_R2_METADATA.json")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    original_versions = dict(line.split("==") for line in
        (ROOT / "reports/hardware/P01_EXPLORATION_REQUIREMENTS.txt").read_text().splitlines() if line)
    identities = read_json(ROOT / "reports/hardware/P01_SOURCE_IDENTITIES.json")
    environments = []
    for subdir, public in zip(("venv-dpo", "venv-replay"), expected["environments"]):
        site = t1_root / ".toolalign-local/base-r2" / subdir / "lib/python3.14/site-packages"
        distributions = {canonicalize_name(item.metadata["Name"]): item for item in
                         importlib.metadata.distributions(path=[str(site)])}
        versions = {name: item.version for name, item in distributions.items()}
        queue = [Requirement(text) for text in project["dependencies"]]
        for extra in public["extras"]:
            queue.extend(Requirement(text) for text in project["optional-dependencies"][extra])
        environment = default_environment()
        runtime, visited = set(), set()
        while queue:
            req = queue.pop()
            if req.marker and not req.marker.evaluate(environment | {"extra": ""}):
                continue
            name = canonicalize_name(req.name)
            distribution = distributions[name]
            assert distribution.version in req.specifier
            key = name, frozenset(req.extras)
            if key in visited:
                continue
            visited.add(key)
            runtime.add(name)
            for raw in distribution.requires or []:
                child = Requirement(raw)
                if child.marker is None or any(child.marker.evaluate(environment | {"extra": extra})
                                               for extra in {"", *req.extras}):
                    child.marker = None
                    queue.append(child)
        runtime_versions = {name: versions[name] for name in runtime}
        dev = {name: versions[name] for name in versions.keys() - runtime - {"toolalign"}}
        assert runtime_versions == public["runtime_versions"]
        assert dev == public["dev_only_versions"]
        assert len(versions) == public["installed_count_with_project"]
        assert all(version == original_versions[name] for name, version in runtime_versions.items())
        checked_sources = 0
        for package, data in identities.items():
            if package not in distributions:
                continue
            assert distributions[package].version == data["version"]
            for name, sha in data["files"].items():
                assert sha_file(site / name) == sha
                checked_sources += 1
        environments.append({"extras": public["extras"], "installed_distributions": len(versions),
                             "runtime_count": len(runtime_versions), "dev_only": dev,
                             "runtime_versions_match_exploration": True,
                             "upstream_source_files_verified": checked_sources})
    preserved = {}
    for name, expected_sha in expected["preserved_previous_files"].items():
        data = (ROOT / name).read_bytes()
        assert data == git("show", PREVIOUS + ":" + name)
        assert hashlib.sha256(data).hexdigest() == expected_sha
        preserved[name] = expected_sha
    for name in ("uv.lock", "pyproject.toml", "contracts.v1.lock.json"):
        assert (ROOT / name).read_bytes() == git("show", "37c00de9abe92e6fb24a0c0e0b7361aa4bb90385:" + name)
    checks = []
    for filename in ("P01_VALIDATION.json", "P01_BASE_R2_VALIDATION.json"):
        for public in read_json(ROOT / "reports/hardware" / filename)["checks"]:
            path = t1_root / ".toolalign-local/checks" / (public["name"] + ".log")
            metadata = read_json(path.with_suffix(".json"))
            assert sha_file(path) == public["sha256"] == metadata["sha256"]
            for field in ("command", "started_at", "exit_code"):
                assert metadata[field] == public[field]
            checks.append({"name": public["name"], "exit_code": public["exit_code"],
                           "sha256": public["sha256"]})
    return {"environments": environments, "preserved_previous_files": preserved,
            "raw_command_logs": checks, "raw_command_log_count": len(checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.t1_root.resolve() != ROOT.resolve()
    assert args.output.resolve().is_relative_to((ROOT / ".toolalign-local/review-p01").resolve())
    sys.meta_path.insert(0, RejectModelImports())
    output = {"candidate": CANDIDATE, "status": "PASS", "metadata": audit_metadata(args.t1_root),
              "historical": audit_runs(args.t1_root), "gpu_reexecution": "NOT_RUN",
              "model_import": False}
    assert not any(name.split(".")[0] in RejectModelImports.forbidden for name in sys.modules)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "run_count": output["historical"]["run_count"],
                      "model_count": len(output["historical"]["model_files"]),
                      "retokenized_samples": sum(item.get("samples_retokenized", 0)
                                                   for item in output["historical"]["runs"]),
                      "raw_command_logs": output["metadata"]["raw_command_log_count"],
                      "upstream_source_files": 11, "output_sha256": sha_file(args.output),
                      "gpu_reexecution": "NOT_RUN", "model_import": False}, sort_keys=True))


if __name__ == "__main__":
    main()
