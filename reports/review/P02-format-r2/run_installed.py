"""Run unchanged F1 or cleanup checks against a verified default-wheel target."""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import sys
from pathlib import Path


def main(args):
    assert sys.flags.isolated
    target, code = args.target.resolve(), args.code.resolve()
    expected = json.loads(args.expected.read_text())["package"]
    for name, digest in expected.items():
        assert hashlib.sha256((target / name).read_bytes()).hexdigest() == digest
    frozen = {
        "review_snapshot.py": "5b3f55d7fdddb2399b5ca7a8d0558dbbc51ce45715a163ec49b806d1ef37f2fc",
        "review_support.py": "3e712ce8358bae5e1f489fc898af7d75f326e37e7d6bb792f7a23cd0e13903a9",
        "review_tokenizers.py": "cd16584169c42861ada99567a89a22f4a59d33a55fd8b20a94df4095320d7ee3",
    }
    for name, digest in frozen.items():
        assert hashlib.sha256((code / name).read_bytes()).hexdigest() == digest
    sys.path.insert(0, str(target))
    sys.path.insert(1, str(code))
    from review_support import assert_cpu, cpu_only

    cpu_only()
    probe = code / "review_snapshot.py" if args.mode == "snapshot" else args.neighbor.resolve()
    sys.argv = [str(probe), "--source", str(args.source.resolve()),
                "--out", str(args.out.resolve()), "--engine", args.engine]
    if args.mode == "post_cleanup":
        sys.argv += ["--root", str(args.root.resolve()), "--scenario", "post_cleanup",
                     "--target", str(target)]
    try:
        runpy.run_path(str(probe), run_name="__main__")
    finally:
        imported = {}
        for name, module in tuple(sys.modules.items()):
            if name == "toolalign" or name.startswith("toolalign."):
                path = Path(module.__file__).resolve()
                assert path.is_relative_to(target), name
                relative = str(path.relative_to(target))
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                assert expected[relative] == digest
                imported[name] = {"path": relative, "sha256": digest}
        assert imported and "toolalign.model_io.offline" in imported
        assert_cpu()
        result = {
            "status": "PASS", "mode": args.mode, "engine": args.engine,
            "python_isolated": True, "no_site": bool(sys.flags.no_site),
            "uses_existing_optional_CPU_environment": True,
            "default_wheel_source_files": len(expected),
            "frozen_probe_hashes": frozen, "toolalign_modules": imported,
            "source_tree_imports": 0, "model_modules_loaded": [],
        }
        with args.binding.open("x") as stream:
            json.dump(result, stream, sort_keys=True, indent=2)
            stream.write("\n")
        print(json.dumps({"installed_modules": imported, "source_tree_imports": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("target", "code", "expected", "source", "out", "binding"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("neighbor", "root"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--engine", choices=("tokenizers", "transformers"), required=True)
    parser.add_argument("--mode", choices=("snapshot", "post_cleanup"), default="snapshot")
    main(parser.parse_args())
