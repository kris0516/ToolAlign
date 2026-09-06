"""Run the new default wheel in a private cwd with isolated Python and no site hooks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "target", "runtime", "wheel", "inputs", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    assert ".toolalign-local" in output.parts
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    working = output / "non-source-cwd"
    working.mkdir(mode=0o700)
    target, runtime = args.target.resolve(), args.runtime.resolve()
    inputs = json.loads(args.inputs.read_text())["prepare"]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["TOOLALIGN_REVIEW_TARGET"] = str(target)
    environment["TOOLALIGN_REVIEW_CONFIG"] = str(root / "configs/training-data.v1.json")
    records = []

    def run(label, argv, expected=0):
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=working, env=environment, capture_output=True, timeout=180)
        for stream, data in (("stdout", result.stdout), ("stderr", result.stderr)):
            with (output / (label + "." + stream)).open("xb") as handle:
                handle.write(data)
        record = {"label": label, "argv": argv, "cwd": str(working), "started_at_utc": started,
                  "ended_at_utc": datetime.now(timezone.utc).isoformat(), "exit_code": result.returncode,
                  "expected_exit_code": expected, "stdout_sha256": sha(result.stdout),
                  "stderr_sha256": sha(result.stderr),
                  "environment": {name: environment[name] for name in (
                      "TOOLALIGN_REVIEW_TARGET", "TOOLALIGN_REVIEW_CONFIG", "PYTHONDONTWRITEBYTECODE",
                      "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "USE_TORCH", "USE_TF", "USE_FLAX")
                                  if name in environment}}
        save(output / (label + ".command.json"), record)
        records.append(record)
        assert result.returncode == expected, label
        return result

    checker = root / "reports/review/P04-sft-native-toy-r1/check_package.py"
    run("origins", [sys.executable, "-B", "-I", "-S", str(checker), "installed",
                    "--target", str(target), "--runtime", str(runtime), "--wheel", str(args.wheel.resolve()),
                    "--output", str(output / "origins.json")])
    bootstrap = "import sys; sys.path[:0]=[sys.argv.pop(1),sys.argv.pop(1)]; "
    pytest_bootstrap = bootstrap + "import pytest; raise SystemExit(pytest.main(sys.argv[1:]))"
    temp = tempfile.mkdtemp(prefix="toolalign-r1-p04-installed-cpu-")
    run("original-probes", [sys.executable, "-B", "-I", "-S", "-c", pytest_bootstrap,
                            str(target), str(runtime), "-q", "-p", "no:cacheprovider",
                            str(root / "reports/review/P04-sft-cpu-r1/probe_cpu.py"), "--basetemp=" + temp])
    cli_bootstrap = bootstrap + "from toolalign.training.sft.__main__ import main; raise SystemExit(main())"
    base = [sys.executable, "-B", "-I", "-S", "-c", cli_bootstrap, str(target), str(runtime)]
    help_result = run("help", base + ["--help"])
    assert b"--train" not in help_result.stdout
    flags = [value for name, path in inputs.items() for value in ("--" + name.replace("_", "-"), str(path))]
    prepared = output / "prepared"
    run("prepare", base + flags + ["--output", str(prepared)])
    original = (prepared / "preparation.json").read_bytes()
    assert json.loads(original)["training_authorized"] is False
    run("reject-existing", base + flags + ["--output", str(prepared)], expected=1)
    assert (prepared / "preparation.json").read_bytes() == original
    invalid = output / "invalid-sft-config.json"
    save(invalid, {"training_authorized": True})
    bad_flags = list(flags)
    bad_flags[bad_flags.index("--sft-config-path") + 1] = str(invalid)
    run("reject-config", base + bad_flags + ["--output", str(output / "rejected-config")], expected=1)
    assert json.loads((output / "rejected-config/preparation.json").read_text())["error"] == "sft_config_file_hash_mismatch"
    train_output = output / "rejected-train"
    rejected = run("reject-training", base + flags + ["--output", str(train_output), "--train"], expected=2)
    assert b"unrecognized arguments: --train" in rejected.stderr and not train_output.exists()
    summary = {"status": "PASS", "commands": records, "count": len(records),
               "expected_rejections": 3, "original_probe_repeat_added_to_count": False,
               "cwd": str(working), "new_default_target": str(target), "read_only_runtime": str(runtime),
               "preparation_sha256": sha(original), "origin_proof_sha256": sha((output / "origins.json").read_bytes()),
               "source_cwd_imports": 0, "new_environments": 0, "new_dependencies": 0}
    save(output / "summary.json", summary)
    print(json.dumps({"status": "PASS", "commands": len(records), "expected_rejections": 3}))


if __name__ == "__main__":
    main()
