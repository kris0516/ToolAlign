"""Verify actual P01 archive bytes and all installed lazy-import modules on CPU."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = ROOT / ".toolalign-local/review-p01/package-check"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(name, args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
    record = {"name": name, "exit_code": result.returncode,
              "stdout_sha256": sha(result.stdout.encode()),
              "stderr_sha256": sha(result.stderr.encode())}
    (PRIVATE / (name + ".stdout.log")).write_text(result.stdout)
    (PRIVATE / (name + ".stderr.log")).write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    return record, result.stdout


def main():
    PRIVATE.mkdir(exist_ok=True)
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")) - {""}
    archive_records = {}
    modules = {path.relative_to(ROOT).as_posix() for path in
               (ROOT / "src/toolalign/training/compatibility").glob("*.py")}
    expected = json.loads((ROOT / "reports/hardware/P01_BASE_R2_METADATA.json").read_text())["artifacts"]
    for path in sorted((ROOT / "dist").glob("toolalign-*")):
        assert path.stat().st_size < 1024**2
        files = {}
        is_wheel = path.suffix == ".whl"
        if is_wheel:
            with zipfile.ZipFile(path) as archive:
                for item in archive.infolist():
                    assert item.file_size < 8 * 1024**2
                    name = PurePosixPath(item.filename)
                    assert not name.is_absolute() and ".." not in name.parts
                    assert item.filename not in files
                    files[item.filename] = archive.read(item.filename)
        else:
            with tarfile.open(path) as archive:
                for item in archive.getmembers():
                    name = PurePosixPath(item.name)
                    assert not name.is_absolute() and ".." not in name.parts
                    assert not item.issym() and not item.islnk()
                    assert item.size < 8 * 1024**2
                    if item.isfile():
                        relative = PurePosixPath(*name.parts[1:]).as_posix()
                        assert relative not in files
                        files[relative] = archive.extractfile(item).read()
        checked, generated = {}, []
        for name, data in files.items():
            if (is_wheel and ".dist-info/" in name) or (not is_wheel and name == "PKG-INFO"):
                generated.append(name)
                continue
            source = "src/" + name if is_wheel else name
            assert source in tracked and data == (ROOT / source).read_bytes()
            checked[source] = sha(data)
        assert modules <= checked.keys()
        assert "src/toolalign/contracts/v1.json" in checked
        actual_sha = sha(path.read_bytes())
        assert actual_sha == expected[path.name]["sha256"]
        archive_records[path.name] = {"sha256": actual_sha, "bytes": path.stat().st_size,
                                     "tracked_files": len(checked), "all_archive_files": len(files),
                                     "generated_metadata": generated, "untracked_payload": 0,
                                     "p01_modules": {name: checked[name] for name in sorted(modules)}}
    assert len(archive_records) == 2
    checks = []
    export = PRIVATE / "requirements.txt"
    environment = PRIVATE / "venv"
    python = environment / "bin/python"
    commands = [
        ("export", ["uv", "export", "--locked", "--no-dev", "--no-emit-project", "--output-file", str(export)], ROOT),
        ("venv", ["uv", "venv", "--python", "3.14", str(environment)], PRIVATE),
        ("dependencies", ["uv", "pip", "install", "--python", str(python), "--require-hashes", "-r", str(export)], PRIVATE),
        ("wheel", ["uv", "pip", "install", "--python", str(python), "--no-deps",
                   str(next((ROOT / "dist").glob("*.whl")))], PRIVATE),
    ]
    for name, args, cwd in commands:
        record, _ = command(name, args, cwd)
        checks.append(record)
    probe = PRIVATE / "installed_probe.py"
    probe.write_text('''
import importlib, importlib.util, json, pathlib, sys
names=['core','execution','numerical','samples','model_probe','fallback_probe','__main__']
for name in names:
    module=importlib.import_module('toolalign.training.compatibility.'+name)
    assert pathlib.Path(module.__file__).is_relative_to(sys.prefix)
for root in ('mlx','mlx_lm','mlx_tune','mlx_lm_lora','torch','transformers'):
    assert importlib.util.find_spec(root) is None
    assert root not in sys.modules
from toolalign.training.compatibility.core import EncodedExample,padded_batch,standard_dpo
from toolalign.training.compatibility.samples import smoke_samples
assert len(smoke_samples())==32
assert padded_batch([EncodedExample((1,2,3,9),(0,0,1,1),2,9)],0,8,6)[1]==[[0,0,1,1,0,0]]
assert abs(standard_dpo(-2,-3,-2,-3)-0.6931471805599453)<1e-12
print(json.dumps({'modules':len(names)+1,'all_inside_installed_prefix':True,'ml_packages_available':False}))
''')
    for name, args in [
        ("p01-imports", [str(python), "-I", str(probe)]),
        ("p01-help", [str(python), "-I", "-m", "toolalign.training.compatibility", "--help"]),
    ]:
        record, _ = command(name, args, PRIVATE)
        checks.append(record)
    assert "PYTHONPATH" not in os.environ or os.environ["PYTHONPATH"] != str(environment)
    output = {"status": "PASS", "archives": archive_records, "installed_checks": checks,
              "model_loading": "NOT_RUN"}
    (PRIVATE / "evidence.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
