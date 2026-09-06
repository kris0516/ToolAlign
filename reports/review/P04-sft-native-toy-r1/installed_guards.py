"""Exercise the native import and rejection boundaries in a default-only target."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.abc
import io
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("target", "runtime", "inputs", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    target, output = args.target.resolve(), args.output.resolve()
    output.mkdir(mode=0o700)
    sys.path[:0] = [str(target), str(args.runtime.resolve())]
    optional = {"mlx", "mlx_lm", "torch", "numpy", "transformers", "tokenizers", "datasets"}

    class RejectFrameworks(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in optional:
                raise AssertionError("Unexpected optional import: " + fullname)
            return None

    sys.meta_path.insert(0, RejectFrameworks())
    from toolalign.data.common import DataError
    from toolalign.training.sft import native_toy as native

    inputs = json.loads(args.inputs.read_text())
    assert str(Path(inputs["repository"]) / "src") not in sys.path
    config, original, dataset = native.load_inputs(inputs["config"], inputs["cases"], inputs["repository"])
    assert config["training_authorized"] is False and len(dataset) == 13
    assert sum(batch.effective_supervised_targets for _, batch in dataset) == 44
    cases = []

    def run(label, argv, expected):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = native.main(argv)
            except SystemExit as exc:
                code = exc.code
        assert code == expected, (label, code, stdout.getvalue(), stderr.getvalue())
        for stream, text in (("stdout", stdout.getvalue()), ("stderr", stderr.getvalue())):
            with (output / (label + "." + stream)).open("x") as handle:
                handle.write(text)
        cases.append({"label": label, "argv": argv, "exit_code": code,
            "stdout_sha256": hashlib.sha256(stdout.getvalue().encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr.getvalue().encode()).hexdigest()})
        return stdout.getvalue(), stderr.getvalue()

    base = ["--config", inputs["config"], "--cases", inputs["cases"], "--repository", inputs["repository"],
            "--output", str(output / "unauthorized-child")]
    run("native-help", ["--help"], 0)
    _, invalid = run("native-formal-mode", base + ["--mode", "formal"], 2)
    assert "invalid choice" in invalid
    rejected, _ = run("native-output-scope", base + ["--mode", "installed_segmented"], 1)
    assert json.loads(rejected)["error"] == "native_output_exists_or_outside_round"
    bad_config = output / "changed-config.json"
    changed = dict(config, training_authorized=True)
    bad_config.write_text(json.dumps(changed))
    bad = base[:]
    bad[bad.index("--config") + 1] = str(bad_config)
    rejected, _ = run("native-config-hash", bad + ["--mode", "installed_segmented"], 1)
    assert json.loads(rejected)["error"] == "native_config_hash_mismatch"
    try:
        native._numerics(root=output / "no-lease", mode="installed_segmented", config=config,
            original=original, dataset=dataset, lease=None, repository=inputs["repository"])
    except DataError as exc:
        assert str(exc) == "active_current_native_lease_required"
        lease_rejection = str(exc)
    else:
        raise AssertionError("missing lease was accepted")
    assert not (output / "no-lease").exists() and not (output / "unauthorized-child").exists()
    assert not optional & {name.split(".")[0] for name in sys.modules}
    origins = native._origins()
    assert all(Path(value["path"]).is_relative_to(target) for value in origins.values())
    result = {"status": "PASS", "cli_cases": cases, "lease_rejection": lease_rejection,
              "installed_origins": origins, "cwd": str(Path.cwd()), "sys_path": sys.path,
              "new_framework_launches": 0, "optional_imports": [], "training_authorized": False}
    with (output / "result.json").open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "cli_cases": len(cases), "framework_launches": 0}))


if __name__ == "__main__":
    main()
