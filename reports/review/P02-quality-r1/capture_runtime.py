"""Run a CPU entry point and record its actual imported source files."""

import argparse
import hashlib
import importlib.util
import json
import runpy
import sys
from pathlib import Path

BLOCKED = {"torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax"}


def no_model_imports(event, arguments):
    # Availability checks such as find_spec("torch") import no framework.
    # Intercept actual imports, without changing those read-only checks.
    if event == "import" and arguments[0].split(".", 1)[0] in BLOCKED:
        raise AssertionError("model import forbidden in this CPU review: " + arguments[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", required=True, type=Path)
    parser.add_argument("--expected-files", required=True, type=Path)
    parser.add_argument("--proof", required=True, type=Path)
    parser.add_argument("--module", required=True)
    parser.add_argument("--default-only", action="store_true")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    args.package_root = args.package_root.resolve()
    expected = json.loads(args.expected_files.read_text())
    sys.dont_write_bytecode = True
    assert not BLOCKED & {n.split(".", 1)[0] for n in sys.modules}
    sys.addaudithook(no_model_imports)
    entry_spec = importlib.util.find_spec(args.module)
    entry_path = Path(entry_spec.origin).resolve()
    entry_sha = hashlib.sha256(entry_path.read_bytes()).hexdigest()
    if args.module.startswith("toolalign"):
        entry_relative = entry_path.relative_to(args.package_root).as_posix()
        assert expected[entry_relative]["sha256"] == entry_sha
    sys.argv = [args.module, *args.arguments]
    if args.arguments[:1] == ["--"]:
        sys.argv = [args.module, *args.arguments[1:]]
    outcome = "RUNNING"
    try:
        runpy.run_module(args.module, run_name="__main__", alter_sys=True)
        outcome = "RETURNED"
    except SystemExit as exc:
        outcome = {"system_exit": exc.code}
        raise
    except BaseException as exc:
        outcome = {"exception_type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        origins = {}
        failures = []
        for name, module in sorted(sys.modules.items()):
            filename = getattr(module, "__file__", None)
            if not filename or not name.startswith("toolalign"):
                continue
            path = Path(filename).resolve()
            entry = {"path": str(path)}
            if not path.is_relative_to(args.package_root):
                failures.append(name + ": wrong module origin")
            else:
                relative = path.relative_to(args.package_root).as_posix()
                data = path.read_bytes()
                entry.update(relative=relative, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
                if relative not in expected or entry["sha256"] != expected[relative]["sha256"]:
                    failures.append(name + ": wrong source bytes")
            origins[name] = entry
        loaded = {name.split(".", 1)[0] for name in sys.modules}
        engine_origins = {}
        for name, module in sorted(sys.modules.items()):
            if name.split(".", 1)[0] not in {"tokenizers", "transformers", "jinja2", "numpy", "regex"}:
                continue
            filename = getattr(module, "__file__", None)
            if filename and Path(filename).is_file():
                path = Path(filename).resolve()
                engine_origins[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if BLOCKED & loaded:
            failures.append("model modules loaded")
        if args.default_only and {"tokenizers", "transformers"} & loaded:
            failures.append("tokenizer modules loaded in default process")
        assert origins, "no ToolAlign consumer was observed"
        proof = {"outcome": outcome, "python": sys.version, "executable": sys.executable,
                 "entry_module": args.module, "entry_path": str(entry_path),
                 "entry_sha256": entry_sha,
                 "engine_origins": engine_origins,
                 "package_root": str(args.package_root), "origins": origins,
                 "model_modules_loaded": sorted(BLOCKED & loaded),
                 "tokenizer_modules_loaded": sorted({"tokenizers", "transformers"} & loaded),
                 "failures": failures}
        args.proof.parent.mkdir(parents=True, exist_ok=True)
        with args.proof.open("x") as stream:
            json.dump(proof, stream, indent=2, sort_keys=True)
            stream.write("\n")
        assert not failures, failures


if __name__ == "__main__":
    main()
