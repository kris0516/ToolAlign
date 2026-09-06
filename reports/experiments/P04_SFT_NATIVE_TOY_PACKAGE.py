"""Reuse accepted real-archive checks and verify the new native module from wheel.

All commands here are CPU-only. The installed numerical replay is an explicit
separate invocation of the installed native entry and its shared launch ledger.
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


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def installed(args):
    target, runtime = Path(args.target).resolve(), Path(args.runtime).resolve()
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    sys.path[:0] = [str(target), str(runtime)]
    from toolalign.data.common import DataError
    from toolalign.training.sft.config import consumer_identity as cpu_identity
    from toolalign.training.sft.mlx_adapter import backend
    from toolalign.training.sft.native_toy import (
        CONFIG_SHA256,
        SCOPE,
        consumer_identity,
        load_inputs,
        require_current_lease,
    )
    from toolalign.training.sft.validation import Score, choose_score, validate_score

    expected = json.loads(Path(args.expected).read_text())
    values = expected["inputs"]
    config, original, dataset = load_inputs(values["config"], values["cases"], values["repository"])
    assert config["scope"] == SCOPE and config["training_authorized"] is False
    assert CONFIG_SHA256 == sha(values["config"])
    assert len(dataset) == original["unique_examples"] == 13
    assert sum(b.effective_supervised_targets for _, b in dataset) == 44
    assert consumer_identity() == expected["consumer"]
    assert len(cpu_identity()) == 8 and len(consumer_identity()["sft"]) == 9
    for function, args_ in ((backend, (None,)), (require_current_lease, (None, values["repository"]))):
        try:
            function(*args_)
        except DataError:
            pass
        else:
            raise AssertionError("installed_unleased_entry_accepted")
    native = Score(SCOPE, "1" * 64, "2" * 64, "3" * 64, "4" * 64, 1, 8, 4.0, 2, 2.0, scope=SCOPE)
    validate_score(native)
    assert choose_score([native]) == native
    cpu = Score("TOY_CPU", "1" * 64, "2" * 64, "3" * 64, "4" * 64, 1, 8, 4.0, 2, 2.0)
    try:
        choose_score([native, cpu])
    except DataError:
        pass
    else:
        raise AssertionError("installed_mixed_scope_accepted")
    optional = {"mlx", "mlx_lm", "torch", "numpy", "transformers", "tokenizers", "tensorflow", "flax", "jax"}
    assert not optional & {name.split(".")[0] for name in sys.modules}
    assert all(importlib.util.find_spec(name) is None for name in optional)
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(target), name
            origins[name] = {"path": str(path), "sha256": sha(path)}
    assert "toolalign.training.sft.native_toy" in origins
    assert len([name for name in origins if name.startswith("toolalign.training.sft")]) == 9
    save(args.output, {"status": "PASS", "origins": origins, "sft_modules": 9,
        "consumer_identity": consumer_identity(), "optional_imports": [], "source_fallback": False,
        "isolated": True, "no_site": True, "no_bytecode": True,
        "framework_launches": 0, "actual_selected_or_protocol_encodings": 0})
    print(json.dumps({"status": "PASS", "sft_modules": 9, "total_origins": len(origins)}))


def verify(args):
    root, output = Path(args.root).resolve(), Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    helper = root / "reports/experiments/P04_SFT_CPU_PACKAGE.py"
    spec = importlib.util.spec_from_file_location("accepted_cpu_package", helper)
    accepted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(accepted)
    accepted_output = output / "accepted-cpu-package"
    accepted.verify(SimpleNamespace(root=str(root), archives=args.archives, output=str(accepted_output),
                                    runtime=args.runtime, inputs=args.cpu_inputs))
    sys.path.insert(0, str(root / "src"))
    from toolalign.training.sft.config import consumer_identity as cpu_identity
    from toolalign.training.sft.native_toy import consumer_identity

    target = accepted_output / "accepted-archive-checks/installed-wheel"
    expected = {"inputs": json.loads(Path(args.native_inputs).read_text()), "consumer": consumer_identity()}
    save(output / "native-expected.json", expected)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    commands = []

    def run(name, command, exit_code=0):
        start = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(command, cwd=output, env=environment, capture_output=True, timeout=90)
        for suffix, data in (("stdout", result.stdout), ("stderr", result.stderr)):
            with (output / f"{name}.{suffix}").open("xb") as stream:
                stream.write(data)
        record = {"name": name, "argv": command, "cwd": str(output), "started_at": start,
            "ended_at": datetime.now(timezone.utc).isoformat(), "exit_code": result.returncode,
            "expected_exit_code": exit_code, "stdout_sha256": sha(output / f"{name}.stdout"),
            "stderr_sha256": sha(output / f"{name}.stderr")}
        save(output / f"{name}.command.json", record)
        commands.append(record)
        assert result.returncode == exit_code, name

    run("native-installed-pure", [sys.executable, "-B", "-I", "-S", str(Path(__file__).resolve()),
        "installed", "--target", str(target), "--runtime", args.runtime,
        "--expected", str(output / "native-expected.json"), "--output", str(output / "native-origins.json")])
    bootstrap = ("import sys; sys.path[:0]=[sys.argv.pop(1),sys.argv.pop(1)]; "
                 "from toolalign.training.sft.native_toy import main; raise SystemExit(main())")
    base = [sys.executable, "-B", "-I", "-S", "-c", bootstrap, str(target), args.runtime]
    run("native-installed-help", base + ["--help"])
    values = expected["inputs"]
    flags = [v for k in ("config", "cases", "repository") for v in ("--" + k, values[k])]
    existing = Path(values["round_root"]) / "source-segmented-r2"
    run("native-installed-reject-existing", base + [*flags, "--output", str(existing),
        "--mode", "installed_segmented"], exit_code=1)
    invalid = flags.copy()
    invalid[invalid.index("--config") + 1] = str(accepted_output / "invalid-sft-config.json")
    run("native-installed-reject-config", base + [*invalid, "--output", str(Path(values["round_root"]) / "not-created"),
        "--mode", "installed_segmented"], exit_code=1)
    run("native-installed-reject-formal", base + [*flags, "--output", str(Path(values["round_root"]) / "not-created"),
        "--mode", "formal"], exit_code=2)
    prepared = json.loads((accepted_output / "installed-preparation/preparation.json").read_text())
    assert prepared["consumer"] == cpu_identity() and prepared["training_authorized"] is False
    assert not (Path(values["round_root"]) / "not-created").exists()
    save(output / "summary.json", {"status": "PASS", "accepted_helper_sha256": sha(helper),
        "accepted_summary_sha256": sha(accepted_output / "summary.json"),
        "native_origins_sha256": sha(output / "native-origins.json"), "commands": commands,
        "target": str(target), "runtime": args.runtime, "new_environments": 0, "new_dependencies": 0,
        "native_consumer": consumer_identity(), "new_cpu_prepare_consumer": cpu_identity(),
        "framework_launches": 0, "installed_native_numerics": "separate_bounded_invocation_required"})
    print(json.dumps({"status": "PASS", "native_default_commands": len(commands),
                      "summary_sha256": sha(output / "summary.json")}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("verify")
    for name in ("root", "archives", "output", "runtime", "cpu-inputs", "native-inputs"):
        check.add_argument("--" + name, required=True)
    check = sub.add_parser("installed")
    for name in ("target", "runtime", "expected", "output"):
        check.add_argument("--" + name, required=True)
    args = parser.parse_args()
    {"verify": verify, "installed": installed}[args.command](args)


if __name__ == "__main__":
    main()
