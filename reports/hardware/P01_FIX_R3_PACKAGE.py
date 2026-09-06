"""Check newly built archive bytes and an isolated default CPU P01 installation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Reuse only the current tracked-byte checker, not the old snapshot's main
    # routine, dependency audit or expected archive hashes.
    spec = importlib.util.spec_from_file_location(
        "p01_archive_bytes", ROOT / "reports/hardware/P01_BASE_R2_AUDIT.py"
    )
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    archives = audit.archives()
    modules = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / "src/toolalign/training/compatibility").glob("*.py")
    }
    assert len(modules) == 8
    required = set(modules) | {"src/toolalign/contracts/v1.json"}
    for name, record in archives.items():
        if name.endswith(".whl"):
            with zipfile.ZipFile(ROOT / "dist" / name) as archive:
                members = {"src/" + member for member in archive.namelist()}
        else:
            with tarfile.open(ROOT / "dist" / name) as archive:
                members = {member.name.split("/", 1)[1] for member in archive.getmembers()
                           if member.isfile()}
        assert required <= members
        record["all_eight_p01_modules_and_contract_schema_present"] = True
    checks = []

    def run(name, command, cwd):
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60)
        print(f"{name}: exit={result.returncode}", flush=True)
        checks.append({"name": name, "exit_code": result.returncode,
                       "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
                       "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest()})
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout

    with tempfile.TemporaryDirectory(prefix="isolated-core-", dir=args.output.parent) as directory:
        private = Path(directory).resolve()
        requirements, environment = private / "runtime.txt", private / "venv"
        python = environment / "bin/python"
        run("export", ["uv", "export", "--locked", "--no-dev", "--no-emit-project",
                       "--output-file", str(requirements)], ROOT)
        run("venv", ["uv", "venv", "--python", "3.14", str(environment)], private)
        run("dependencies", ["uv", "pip", "install", "--python", str(python),
                             "--require-hashes", "-r", str(requirements)], private)
        run("wheel-install", ["uv", "pip", "install", "--python", str(python), "--no-deps",
                              str(next((ROOT / "dist").glob("*.whl")))], private)
        run("dependency-check", ["uv", "pip", "check", "--python", str(python)], private)
        probe = private / "probe.py"
        probe.write_text('''
import importlib, importlib.util, json, math, pathlib, sys
names=['__init__','__main__','core','execution','fallback_probe','model_probe','numerical','samples']
for name in names:
    module=importlib.import_module('toolalign.training.compatibility.'+name)
    assert pathlib.Path(module.__file__).is_relative_to(sys.prefix)
for name in ('mlx','mlx_lm','mlx_tune','mlx_lm_lora','torch','transformers'):
    assert importlib.util.find_spec(name) is None and name not in sys.modules
from toolalign.training.compatibility.core import EncodedExample,padded_batch,standard_dpo
from toolalign.training.compatibility.samples import smoke_samples
assert len(smoke_samples())==32
assert padded_batch([EncodedExample((1,2,3,9),(0,0,1,1),2,9)],0,8,6)[1]==[[0,0,1,1,0,0]]
assert abs(standard_dpo(-2,-3,-2,-3)-math.log(2))<1e-12
print(json.dumps({'installed_modules':len(names),'ml_packages_available':False}))
''')
        installed = json.loads(run("installed-p01", [str(python), "-I", str(probe)], private))
        run("p01-help", [str(python), "-I", "-m", "toolalign.training.compatibility", "--help"],
            private)
        digest = run("contract-digest", [str(python), "-I", "-m", "toolalign.cli",
                                          "contract-digest"], private).strip()
        assert digest == hashlib.sha256((ROOT / "src/toolalign/contracts/v1.json").read_bytes()).hexdigest()
        for kind in ("example", "tool", "preference", "run", "trace"):
            output = run("validate-" + kind, [str(environment / "bin/toolalign"), "validate",
                         str(ROOT / "tests/fixtures/contracts" / f"{kind}.json")], private)
            assert "VALID: 1 record(s)" in output
    result = {"status": "PASS", "archives": archives, "p01_source_sha256": modules,
              "installed_checks": checks, "installed_probe": installed,
              "default_cpu_only": True, "model_loading": "NOT_RUN"}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
