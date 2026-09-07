"""Run the installed CLI with site/cwd imports disabled and verified dependencies."""

import argparse
import hashlib
import importlib.util
import json
import runpy
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("target", "dependencies", "expected", "capture", "proof", "bootstrap-proof"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--module", required=True)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    target, dependencies = args.target.resolve(), args.dependencies.resolve()
    assert target != dependencies and target.is_dir() and dependencies.is_dir()
    sys.path[:0] = [str(target), str(dependencies)]
    expected = json.loads(args.expected.read_text())
    assert len(expected) == 60
    for name, info in expected.items():
        path = target / name
        assert path.is_file() and not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == info["sha256"]
    unavailable = {}
    for name in ("tokenizers", "transformers", "torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax"):
        unavailable[name] = importlib.util.find_spec(name) is None
    assert all(unavailable.values())
    bootstrap = {"isolated": True, "no_site": True, "no_bytecode": True,
                 "target": str(target), "dependency_root": str(dependencies), "cwd": str(Path.cwd()),
                 "installed_payload_files": 60, "optional_packages_unavailable": unavailable,
                 "module": args.module}
    with args.bootstrap_proof.open("x") as stream:
        json.dump(bootstrap, stream, sort_keys=True, indent=2)
        stream.write("\n")
    rest = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    sys.argv = [str(args.capture), "--package-root", str(target), "--expected-files", str(args.expected),
                "--proof", str(args.proof), "--module", args.module, "--default-only", "--", *rest]
    runpy.run_path(str(args.capture), run_name="__main__")


if __name__ == "__main__":
    main()
