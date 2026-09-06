"""Reuse accepted archive checks, then exercise every new module from the new wheel.

Existing pure dependencies are read only; the wheel is installed into a new
target. Report code is trusted repository code, never loaded from data records.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def installed(args):
    target, runtime = Path(args.target).resolve(), Path(args.runtime).resolve()
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    sys.path[:0] = [str(target), str(runtime)]
    from toolalign.training.sft import collate_sequence, epoch_plan, mlx_adapter, validate_plan
    from toolalign.training.sft.config import consumer_identity, load_config
    from toolalign.training.sft.data import view_from_records
    from toolalign.training.sft.validation import ValidationTotals

    values = json.loads(Path(args.inputs).read_text())
    assert load_config(values["sft_config_path"])["training_authorized"] is False
    view = view_from_records(**values["small_view"])
    assert len(view) == 2 and view[0].example == values["small_view"]["examples"][0]
    from toolalign.model_io import Sequence

    sequence = values["small_sequence"]
    for key in ("prompt_ids", "concatenated_ids", "sequence_ids", "loss_mask"):
        sequence[key] = tuple(sequence[key])
    batch = collate_sequence(Sequence(**sequence), bucket=1024, pad_token_id=151643)
    assert batch.record() == values["small_batch"]
    validate_plan(epoch_plan(13), range(1, 14))
    assert epoch_plan(6013).updates == 752
    totals = ValidationTotals(profile="smoke", split="validation", expected_ids=["a", "b"])
    totals.add(example_id="a", profile="smoke", split="validation", ce_sum=2.0, tokens=1)
    totals.add(example_id="b", profile="smoke", split="validation", ce_sum=18.0, tokens=6)
    assert totals.finish() == 20 / 7
    assert callable(mlx_adapter.completion_loss)
    from toolalign.training.sft.__main__ import main

    assert callable(main)
    identities = consumer_identity()
    assert identities == values["consumer"]
    optional = {"mlx", "mlx_lm", "torch", "transformers", "tokenizers", "tensorflow", "flax", "jax",
                "mlx_tune", "mlx_lm_lora", "datasets"}
    assert not optional & {n.split(".")[0] for n in sys.modules}
    assert all(importlib.util.find_spec(n) is None for n in optional)
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            file = Path(module.__file__).resolve()
            assert file.is_relative_to(target), name
            origins[name] = {"path": str(file), "sha256": sha(file.read_bytes())}
    assert len([n for n in origins if n.startswith("toolalign.training.sft")]) == 8
    result = {"status": "PASS", "origins": origins, "new_modules": 8, "source_cwd_imports": 0,
              "optional_imports": [], "no_bytecode": True, "isolated": True, "no_site": True,
              "new_independent_test_denominator": 0}
    save(args.output, result)
    print(json.dumps({"status": "PASS", "new_modules": 8, "total_module_origins": len(origins)}))


def verify(args):
    root, output = Path(args.root).resolve(), Path(args.output).resolve()
    assert ".toolalign-local" in output.parts
    output.mkdir(parents=True, exist_ok=False)
    # Reuse the exact accepted verifier; its own original files remain untouched.
    helper = root / "reports/data/P02_TRAINING_BINDING_PACKAGE.py"
    specification = importlib.util.spec_from_file_location("accepted_package_checks", helper)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    inputs = json.loads(Path(args.inputs).read_text())
    save(output / "bound-inputs.json", inputs["bound_inputs"])
    old_args = SimpleNamespace(root=str(root), archives=str(Path(args.archives).resolve()),
        output=str(output / "accepted-archive-checks"), runtime=args.runtime,
        inputs=str(output / "bound-inputs.json"), selection=inputs["selection_path"])
    module.archives_and_install(old_args)
    target = output / "accepted-archive-checks/installed-wheel"
    sys.path[:0] = [str(root / "src"), str(root / "tests/training/sft")]
    from dataclasses import asdict

    from sft_cases import records, sequence

    from toolalign.contracts import canonical_hash
    from toolalign.data.training_selection import load_config
    from toolalign.training.sft import collate_sequence
    from toolalign.training.sft.config import consumer_identity

    config = load_config(root / "configs/training-data.v1.json")
    examples, sidecars = records(config)
    seq = sequence()
    expected = {"small_view": {"examples": examples, "sidecars": sidecars, "config": config,
        "profile": "smoke", "split": "train", "selection_sha256": "a" * 64, "expected_count": 2,
        "expected_identity": canonical_hash([e["example_id"] for e in examples])},
        "small_sequence": asdict(seq), "small_batch": collate_sequence(seq, bucket=1024, pad_token_id=151643).record(),
        "consumer": consumer_identity(), "sft_config_path": inputs["prepare"]["sft_config_path"]}
    save(output / "original-fixture.json", expected)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    commands = []

    def run(name, argv, expected_exit=0):
        start = datetime.now(timezone.utc).isoformat()
        done = subprocess.run(argv, env=environment, cwd=output, capture_output=True, timeout=180)
        for suffix, data in (("stdout", done.stdout), ("stderr", done.stderr)):
            with (output / (name + "." + suffix)).open("xb") as stream:
                stream.write(data)
        record = {"name": name, "argv": argv, "cwd": str(output), "started_at": start,
            "ended_at": datetime.now(timezone.utc).isoformat(), "exit_code": done.returncode,
            "expected_exit": expected_exit, "stdout_sha256": sha(done.stdout), "stderr_sha256": sha(done.stderr)}
        save(output / (name + ".command.json"), record)
        commands.append(record)
        assert done.returncode == expected_exit, name

    run("sft-installed-original-fixture", [sys.executable, "-B", "-I", "-S", str(Path(__file__).resolve()),
        "installed", "--target", str(target), "--runtime", args.runtime,
        "--inputs", str(output / "original-fixture.json"), "--output", str(output / "installed-origins.json")])
    bootstrap = ("import sys; sys.path[:0]=[sys.argv.pop(1),sys.argv.pop(1)]; "
                 "from toolalign.training.sft.__main__ import main; raise SystemExit(main())")
    base = [sys.executable, "-B", "-I", "-S", "-c", bootstrap, str(target), args.runtime]
    run("sft-installed-help", base + ["--help"])
    flags = [value for key, v in inputs["prepare"].items() for value in ("--" + key.replace("_", "-"), v)]
    prepared = output / "installed-preparation"
    run("sft-installed-prepare", base + [*flags, "--output", str(prepared)])
    original = (prepared / "preparation.json").read_bytes()
    run("sft-installed-reject-existing-output", base + [*flags, "--output", str(prepared)], expected_exit=1)
    assert original == (prepared / "preparation.json").read_bytes()
    invalid = output / "invalid-sft-config.json"
    save(invalid, {"training_authorized": True})
    wrong = flags.copy()
    wrong[wrong.index("--sft-config-path") + 1] = str(invalid)
    run("sft-installed-reject-config", base + [*wrong, "--output", str(output / "rejected-config")], expected_exit=1)
    run("sft-installed-reject-training-command", base + ["--train"], expected_exit=2)
    summary = {"status": "PASS", "accepted_package_verifier_sha256": sha(helper.read_bytes()),
        "archive_and_install_summary_sha256": sha((output / "accepted-archive-checks/summary.json").read_bytes()),
        "new_sft_commands": commands, "new_modules": 8,
        "origins_sha256": sha((output / "installed-origins.json").read_bytes()),
        "preparation_sha256": sha(original), "new_environments": 0, "new_dependencies": 0,
        "direct_source_normal_wheel": "NOT_RUN", "optional_installed_toy_replay": "NOT_RUN"}
    save(output / "summary.json", summary)
    print(json.dumps({"status": "PASS", "summary_sha256": sha((output / "summary.json").read_bytes())}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("verify")
    for name in ("root", "archives", "output", "runtime", "inputs"):
        check.add_argument("--" + name, required=True)
    check = sub.add_parser("installed")
    for name in ("target", "runtime", "inputs", "output"):
        check.add_argument("--" + name, required=True)
    args = parser.parse_args()
    {"verify": verify, "installed": installed}[args.command](args)


if __name__ == "__main__":
    main()
