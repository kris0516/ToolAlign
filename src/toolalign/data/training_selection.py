"""Fixed v1 CPU selection from bound historical measurements, without tokenization.

``select_examples`` is a pure structural kernel for independently constructed
fixtures. Production build/verify additionally pin every input's actual bytes.
Neither interface authorizes training or accepts executable configuration.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import platform
import sys
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash, validate_record
from toolalign.model_io.format import encode_action, format_identity
from toolalign.tools._json import parse_action

from .common import DataError, encoded, file_hash, loads, read_json, verified_build_manifest

CONFIG_FILE_SHA256 = "579d3d9d9436f4374e7e808dc5b787213157d7ee477bfffd48dac02d35e70a4c"
CONFIG_CANONICAL_SHA256 = "2d8cfd053ce352e822aca3b8d95af7b7f1ac123636b274ef41bb9b8d52e2693d"
SPLITS = ("train", "validation")
EXPECTED_COUNTS = {"train": 7515, "validation": 234}
EXPECTED_ELIGIBLE = {"smoke": {"train": 3618, "validation": 197},
                     "formal": {"train": 6013, "validation": 217}}
_IDENTITY = ("example_id", "source", "source_revision", "source_record_hash", "group_id", "split")
_SEQUENCE_HASHES = ("prompt_sha256", "prompt_ids_sha256", "concatenated_ids_sha256",
                    "sequence_sha256", "causal_input_ids_sha256", "causal_target_ids_sha256",
                    "role_bindings_sha256")


def _require(condition, code):
    if not condition:
        raise DataError(code)


def validate_config(config):
    _require(canonical_hash(config) == CONFIG_CANONICAL_SHA256, "fixed_config_mismatch")
    return copy.deepcopy(config)


def load_config(path):
    _require(file_hash(path) == CONFIG_FILE_SHA256, "config_file_hash_mismatch")
    return validate_config(read_json(path))


def rank_key(example_id):
    return canonical_hash(["toolalign.training-selection.v1", 42, example_id]), example_id


def _integer(row, key, maximum=1_000_000):
    value = row.get(key)
    _require(type(value) is int and 0 <= value <= maximum, "invalid_" + key)
    return value


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def validate_pair(example, row, config):
    """Check frozen identities, explicit success, raw Action and length arithmetic.

    This does not reconstruct tokenizer IDs: their authority comes from the
    production input file hashes, and the separately measured review samples.
    """
    _require(type(row) is dict, "invalid_audit_row")
    _require(example.get("split") in SPLITS, "forbidden_example_split")
    try:
        value = validate_record(example, "example")
    except ContractError as exc:
        raise DataError("invalid_example") from exc
    _require(all(row.get(k) == value[k] for k in _IDENTITY), "audit_identity_mismatch")
    model_input = {k: value[k] for k in ("messages", "tools")}
    action = value["expected_action"]
    expected = {
        **format_identity(), "common_binding_sha256": config["representation_common_binding_sha256"],
        "example_sha256": canonical_hash(value), "model_input_sha256": canonical_hash(model_input),
        "action_sha256": canonical_hash(action), "parser_action_sha256": canonical_hash(action),
        "kind": action["kind"],
    }
    _require(all(row.get(k) == v for k, v in expected.items()), "audit_binding_mismatch")
    for key in ("sequence_error", "parser_error"):
        _require(key in row and row[key] is None, "representation_error")
    for key in ("parser_accepted_exact", "rendered_inverse_exact", "prefix_stable",
                "raw_byte_cap_pass", "raw_node_cap_pass", "raw_depth_cap_pass"):
        _require(row.get(key) is True, "representation_not_successful")
    for key in _SEQUENCE_HASHES:
        h = row.get(key)
        _require(type(h) is str and len(h) == 64 and all(c in "0123456789abcdef" for c in h),
                 "invalid_sequence_hash")
    p = _integer(row, "prompt_tokens")
    c = _integer(row, "completion_tokens")
    n = _integer(row, "total_tokens")
    _require(p > 0 and c > 0 and p + c + 1 == n, "inconsistent_sequence_lengths")
    for key, expected_number in {
        "completion_tokens_including_eos": c + 1, "append_eos_count": 1,
        "eos_token_id": 151645, "first_supervised_causal_position": p - 1,
        "last_supervised_causal_position": n - 2, "raw_byte_cap": 131072,
    }.items():
        _require(_integer(row, key) == expected_number, "inconsistent_" + key)
    mask = [0] * p + [1] * (c + 1)
    _require(row.get("loss_mask_sha256") == canonical_hash(mask)
             and row.get("causal_loss_mask_sha256") == canonical_hash(mask[1:]), "mask_hash_mismatch")
    completion = encode_action(action)
    _require(parse_action(completion) == action, "current_parser_mismatch")
    nodes, depth, pending = 0, 0, [(action, 0)]
    while pending:
        node, level = pending.pop()
        nodes, depth = nodes + 1, max(depth, level)
        children = node.values() if type(node) is dict else node if type(node) is list else ()
        pending.extend((child, level + 1) for child in children)
    for key, v in {"completion_utf8_bytes": len(completion.encode()), "action_nodes": nodes,
                   "action_depth": depth, "action_native_utf8_bytes": len(encoded(action))}.items():
        _require(_integer(row, key) == v, "inconsistent_" + key)
    _require(row.get("completion_sha256") == _sha(completion.encode()), "completion_hash_mismatch")
    _require(len(completion.encode()) <= 131072 and nodes <= 8192 and depth <= 24, "raw_limit_failure")
    return value


def select_examples(examples_by_split, audit_rows, config):
    """Return deterministic original records plus sidecars and exclusion IDs.

    Small fixtures may use this kernel; only ``build`` certifies fixed input bytes
    and production counts. Final split rows are identified and immediately skipped.
    """
    config = validate_config(config)
    _require(type(examples_by_split) is dict and set(examples_by_split) == set(SPLITS),
             "only_train_validation_inputs")
    examples, groups = {}, {}
    for split in SPLITS:
        for example in examples_by_split[split]:
            _require(type(example) is dict and example.get("split") == split, "example_split_mismatch")
            ident = example.get("example_id")
            _require(type(ident) is str and ident not in examples, "duplicate_or_invalid_example_id")
            value = validate_record(example, "example")
            group = value["group_id"]
            _require(groups.get(group, split) == split, "group_split_leakage")
            groups[group] = split
            examples[ident] = value
    measured = {}
    for row in audit_rows:
        _require(type(row) is dict, "invalid_audit_row")
        split = row.get("split")
        if split in ("test", "ood_test"):
            continue
        _require(split in SPLITS, "invalid_audit_split")
        ident = row.get("example_id")
        _require(type(ident) is str and ident in examples, "extra_or_invalid_audit_row")
        _require(ident not in measured, "duplicate_audit_row")
        validate_pair(examples[ident], row, config)
        measured[ident] = copy.deepcopy(row)
    _require(set(measured) == set(examples), "missing_audit_row")
    profiles = {}
    for name, profile in config["profiles"].items():
        splits = {}
        for split in SPLITS:
            ordered = sorted((e for e in examples.values() if e["split"] == split),
                             key=lambda e: rank_key(e["example_id"]))
            excluded = {reason: [] for reason in ("context_only", "response_only", "both", "rank_limit")}
            eligible = []
            reserved_full = 0
            for example in ordered:
                ident = example["example_id"]
                row = measured[ident]
                context = row["total_tokens"] > profile["context_tokens_including_eos_cap"]
                response = row["completion_tokens_including_eos"] > 256
                reserved_full += row["prompt_tokens"] + 256 <= profile["context_tokens_including_eos_cap"]
                if context or response:
                    reason = "both" if context and response else "context_only" if context else "response_only"
                    excluded[reason].append(ident)
                else:
                    eligible.append(example)
            limit = profile[split + "_limit"]
            selected = eligible if limit is None else eligible[:limit]
            if limit is not None:
                excluded["rank_limit"] = [e["example_id"] for e in eligible[limit:]]
            sidecars = []
            for i, example in enumerate(selected):
                row = measured[example["example_id"]]
                sidecars.append({"selection_rank": i + 1, "ranking_sha256": rank_key(example["example_id"])[0],
                    "profile": name, "split": split,
                    "padding_bucket": next(b for b in profile["padding_buckets"] if b >= row["total_tokens"]),
                    "audit": row})
            summary = {"input_count": len(ordered), "eligible_count": len(eligible),
                "selected_count": len(selected), "excluded_counts": {k: len(v) for k, v in excluded.items()},
                "prompt_plus_reserved_256": {"input_fits": reserved_full,
                    "selected_fits": sum(measured[e["example_id"]]["prompt_tokens"] + 256
                                         <= profile["context_tokens_including_eos_cap"] for e in selected),
                    "used_as_filter": False, "capacity_preflight": "NOT_RUN"},
                "selected_identity_sha256": canonical_hash([e["example_id"] for e in selected])}
            splits[split] = {"examples": selected, "sidecars": sidecars, "excluded": excluded, "summary": summary}
        profiles[name] = splits
    for split in SPLITS:
        _require({e["example_id"] for e in profiles["smoke"][split]["examples"]}
                 <= {e["example_id"] for e in profiles["formal"][split]["examples"]}, "smoke_not_subset")
    return profiles


def read_rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            _require(len(line.encode()) <= 2 * 1024 * 1024, "row_byte_budget")
            yield loads(line)


def consumer_identity():
    names = ("data/training_selection.py", "data/training_review.py", "data/common.py", "model_io/format.py", "model_io/sequence.py",
             "model_io/offline.py", "model_io/descriptor.v1.json", "tools/_json.py", "contracts/validation.py")
    try:
        package_version = importlib.metadata.version("toolalign")
    except importlib.metadata.PackageNotFoundError:
        package_version = None  # Explicit source-tree use in existing tokenizer environments.
    return {"package_version": package_version, "python": platform.python_version(),
            "package_files": {n: _sha(files("toolalign").joinpath(n).read_bytes()) for n in names},
            "packages": {p: importlib.metadata.version(p) for p in ("jsonschema",)}}


def bound_inputs(*, config_path, data_manifest_path, representation_path, audit_path, protocol_path):
    config = load_config(config_path)
    _require(file_hash(protocol_path) == config["protocol_sha256"], "protocol_hash_mismatch")
    manifest = verified_build_manifest(data_manifest_path)
    _require(canonical_hash(manifest) == config["data_manifest_sha256"], "data_manifest_hash_mismatch")
    _require(file_hash(representation_path) == config["representation_manifest_file_sha256"],
             "representation_manifest_hash_mismatch")
    _require(file_hash(audit_path) == config["representation_rows_sha256"], "audit_file_hash_mismatch")
    representation = read_json(representation_path)
    common = representation["common_binding"]
    _require(canonical_hash(common) == config["representation_common_binding_sha256"], "common_binding_mismatch")
    _require(all(common.get(k) == v for k, v in format_identity().items()), "current_format_mismatch")
    _require(common["original_data"]["canonical_sha256"] == canonical_hash(manifest), "original_data_binding_mismatch")
    root = Path(data_manifest_path).resolve().parent
    inputs = {split: list(read_rows(root / (split + ".jsonl"))) for split in SPLITS}
    _require({k: len(v) for k, v in inputs.items()} == EXPECTED_COUNTS, "fixed_input_counts_mismatch")
    plan = select_examples(inputs, read_rows(audit_path), config)
    for profile in plan:
        _require({s: plan[profile][s]["summary"]["eligible_count"] for s in SPLITS}
                 == EXPECTED_ELIGIBLE[profile], "fixed_eligible_counts_mismatch")
    binding = {"config_file_sha256": CONFIG_FILE_SHA256, "config_canonical_sha256": CONFIG_CANONICAL_SHA256,
        "data_manifest_sha256": canonical_hash(manifest), "data_artifacts": manifest["artifacts"],
        "representation_manifest_file_sha256": file_hash(representation_path),
        "representation_rows_sha256": file_hash(audit_path),
        "representation_common_binding_sha256": canonical_hash(common),
        "historical_measurement": {"source": common["source"], "tokenizer": common["tokenizer"]},
        "format": format_identity(), "protocol_sha256": file_hash(protocol_path)}
    return config, plan, binding


def new_private_directory(path):
    requested = Path(path)
    _require(not requested.exists() and not requested.is_symlink(), "output_already_exists")
    resolved = requested.resolve()
    _require(".toolalign-local" in resolved.parts, "output_must_be_private")
    resolved.mkdir(parents=True, exist_ok=False)
    resolved.chmod(0o700)
    return resolved


def stable_artifacts(config, plan, binding):
    result = {}
    summaries = {}
    for profile, splits in plan.items():
        summaries[profile] = {}
        for split, values in splits.items():
            prefix = profile + "/" + split
            for kind in ("examples", "sidecars"):
                result[prefix + "." + kind + ".jsonl"] = b"".join(encoded(x) + b"\n" for x in values[kind])
            result[prefix + ".excluded.json"] = encoded(values["excluded"]) + b"\n"
            summaries[profile][split] = values["summary"]
    stable = {"manifest_version": "toolalign.training-selection.v1", "training_authorized": False,
              "config": config, "input_binding": binding, "profiles": summaries,
              "artifacts": {k: {"sha256": _sha(v), "size_bytes": len(v)} for k, v in result.items()}}
    result["manifest.json"] = encoded(stable) + b"\n"
    return result, stable


def build(*, output, **paths):
    # Check the namespace before expensive input verification. Reserve it only
    # after validation; a concurrent creator is rejected by mkdir(exist_ok=False).
    _require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    config, plan, binding = bound_inputs(**paths)
    artifacts, manifest = stable_artifacts(config, plan, binding)
    out = new_private_directory(output)
    for relative, data in artifacts.items():
        target = out / relative
        target.parent.mkdir(exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        target.chmod(0o600)
    run = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "consumer": consumer_identity(),
           "input_paths": {k: str(Path(v).resolve()) for k, v in paths.items()},
           "output_path": str(out), "stable_manifest_sha256": file_hash(out / "manifest.json")}
    with (out / "run.json").open("xb") as stream:
        stream.write(encoded(run) + b"\n")
    (out / "run.json").chmod(0o600)
    return manifest


def verify(*, output, **paths):
    """Recompute selection from the fixed originals and compare every output byte."""
    config, plan, binding = bound_inputs(**paths)
    artifacts, manifest = stable_artifacts(config, plan, binding)
    out = Path(output).resolve()
    _require(out.is_dir() and ".toolalign-local" in out.parts, "private_output_required")
    actual = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    _require(actual == set(artifacts) | {"run.json"}, "selection_artifact_set_mismatch")
    for name, expected in artifacts.items():
        path = out / name
        _require(not path.is_symlink() and path.resolve().is_relative_to(out), "selection_path_escape")
        _require(file_hash(path) == _sha(expected), "selection_artifact_mismatch")
    run = read_json(out / "run.json")
    _require(run["stable_manifest_sha256"] == file_hash(out / "manifest.json"), "run_binding_mismatch")
    _require(run["consumer"]["package_files"] == consumer_identity()["package_files"], "consumer_source_changed")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        command = sub.add_parser(name)
        for flag in ("config-path", "data-manifest-path", "representation-path", "audit-path", "protocol-path", "output"):
            command.add_argument("--" + flag, required=True, type=Path)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        manifest = {"build": build, "verify": verify}[command](**args)
    except (DataError, ContractError, OSError, KeyError, TypeError, ValueError) as exc:
        print(encoded({"status": "FAIL", "error_type": type(exc).__name__,
                       "error_code": str(exc) if type(exc) is DataError else "invalid_input_or_io"}).decode())
        return 1
    print(encoded({"status": "PASS", "profiles": manifest["profiles"], "training_authorized": False}).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
