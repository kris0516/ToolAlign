"""Inspect current frozen archive payloads and a new isolated default CPU install."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import stat
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = "ac8095faa58a98e143a8dc4d63042093e426feb0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def archive_record(path, tracked, project):
    assert path.stat().st_size < 2 * 1024**2
    wheel, files = path.suffix == ".whl", {}
    if wheel:
        with zipfile.ZipFile(path) as archive:
            assert sum(item.file_size for item in archive.infolist()) < 8 * 1024**2
            for item in archive.infolist():
                name = PurePosixPath(item.filename)
                assert not name.is_absolute() and ".." not in name.parts
                assert not stat.S_ISLNK(item.external_attr >> 16)
                assert item.filename not in files
                files[item.filename] = archive.read(item)
    else:
        with tarfile.open(path) as archive:
            assert sum(item.size for item in archive.getmembers()) < 8 * 1024**2
            for item in archive.getmembers():
                name = PurePosixPath(item.name)
                assert not name.is_absolute() and ".." not in name.parts
                assert not item.issym() and not item.islnk()
                if item.isfile():
                    assert name.parts[0] == "toolalign-0.0.1"
                    relative = PurePosixPath(*name.parts[1:]).as_posix()
                    assert relative not in files
                    files[relative] = archive.extractfile(item).read()
    if wheel:
        expected = {name for name in tracked if name.startswith("src/toolalign/")}
        prefix = "toolalign-0.0.1.dist-info/"
        metadata = {prefix + name for name in ("METADATA", "WHEEL", "entry_points.txt", "RECORD", "licenses/LICENSE")}
    else:
        includes = project["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
        expected = {name for name in tracked
                    if any(name == entry or name.startswith(entry + "/") for entry in includes)}
        expected.add(".gitignore")  # Hatchling's tracked VCS metadata file.
        metadata = {"PKG-INFO"}
    generated, payloads = {}, {}
    for name, data in files.items():
        if name in metadata:
            generated[name] = sha(data)
            continue
        source = "src/" + name if wheel else name
        assert source in tracked, source
        assert data == git("show", CANDIDATE + ":" + source) == (ROOT / source).read_bytes()
        payloads[source] = sha(data)
    assert set(generated) == metadata and set(payloads) == expected
    return {
        "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size,
        "archive_files": len(files), "tracked_files": len(payloads),
        "tracked_payload_hashes": payloads, "generated_metadata_hashes": generated,
        "untracked_payloads": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    private = args.private_root.resolve()
    assert private.is_relative_to((ROOT / ".toolalign-local/review-p01-r2").resolve())
    assert git("rev-parse", "HEAD").decode().strip() == CANDIDATE
    tracked = set(git("ls-tree", "-r", "--name-only", CANDIDATE).decode().splitlines())
    project = tomllib.loads(git("show", CANDIDATE + ":pyproject.toml").decode())
    wheel_name = "toolalign-0.0.1-py3-none-any.whl"
    paths = {
        "sdist": private / "build/toolalign-0.0.1.tar.gz",
        "default-wheel": private / "build" / wheel_name,
        "rebuilt-wheel": private / "rebuilt" / wheel_name,
        "direct-wheel": private / "direct-wheel" / wheel_name,
    }
    archives = {name: archive_record(path, tracked, project) for name, path in paths.items()}
    assert len({archives[name]["sha256"] for name in paths if name != "sdist"}) == 1
    workspace = private / "package-check"
    workspace.mkdir()
    away = workspace / "away-from-source"
    away.mkdir()
    environment, checks = workspace / "venv", []
    python = environment / "bin/python"
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)

    def clean(value):
        return value.replace(str(ROOT), "<R1_WORKTREE>")

    def run(name, command, cwd):
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=60)
        (workspace / (name + ".stdout")).write_bytes(result.stdout)
        (workspace / (name + ".stderr")).write_bytes(result.stderr)
        item = {
            "name": name, "command": [clean(value) for value in command], "cwd": clean(str(cwd)),
            "started_at": started, "ended_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "exit_code": result.returncode,
            "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr),
        }
        checks.append(item)
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        return result.stdout

    requirements = workspace / "runtime-requirements.txt"
    run("export-default", ["uv", "export", "--locked", "--no-dev", "--no-emit-project", "--output-file", str(requirements)], ROOT)
    run("new-environment", ["uv", "venv", "--python", "3.14", str(environment)], away)
    run("install-hashed-default-dependencies", ["uv", "pip", "install", "--python", str(python), "--require-hashes", "-r", str(requirements)], away)
    run("install-rebuilt-wheel", ["uv", "pip", "install", "--python", str(python), "--no-deps", str(paths["rebuilt-wheel"])], away)
    run("dependency-consistency", ["uv", "pip", "check", "--python", str(python)], away)
    modules = {name.removeprefix("src/").removesuffix(".py").replace("/", "."): sha(git("show", CANDIDATE + ":" + name))
               for name in tracked if name.startswith("src/toolalign/training/compatibility/") and name.endswith(".py")}
    assert len(modules) == 8
    expected = away / "module-hashes.json"
    expected.write_text(json.dumps(modules))
    probe = away / "installed_probe.py"
    probe.write_text('''
import hashlib,importlib,importlib.metadata,importlib.util,json,math,pathlib,sys
assert sys.flags.isolated==1
expected=json.loads(pathlib.Path(sys.argv[1]).read_text())
for name,digest in expected.items():
    module=importlib.import_module(name)
    path=pathlib.Path(module.__file__).resolve()
    assert path.is_relative_to(pathlib.Path(sys.prefix).resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
for name in ('mlx','mlx_lm','mlx_tune','mlx_lm_lora','torch','transformers','tokenizers'):
    assert importlib.util.find_spec(name) is None and name not in sys.modules
from toolalign.training.compatibility.core import EncodedExample,padded_batch,standard_dpo
from toolalign.training.compatibility.samples import smoke_samples
assert len(smoke_samples())==32
assert padded_batch([EncodedExample((1,2,3,9),(0,0,1,1),2,9)],0,8,6)[1]==[[0,0,1,1,0,0]]
assert abs(standard_dpo(-2,-3,-2,-3)-math.log(2))<1e-12
versions={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
assert set(versions)=={'attrs','jsonschema','jsonschema-specifications','referencing','rpds-py','toolalign'}
print(json.dumps({'python':sys.version.split()[0],'module_hashes':expected,
                 'all_modules_inside_installed_prefix':True,'isolated_flag':sys.flags.isolated,
                 'distributions':versions,'model_or_tokenizer_packages_available':False},sort_keys=True))
''')
    installed = json.loads(run("installed-p01-module-bytes", [str(python), "-I", str(probe), str(expected)], away))
    run("installed-p01-help", [str(python), "-I", "-m", "toolalign.training.compatibility", "--help"], away)
    digest = run("installed-contract-digest", [str(python), "-I", "-m", "toolalign.cli", "contract-digest"], away).decode().strip()
    assert digest == sha(git("show", CANDIDATE + ":src/toolalign/contracts/v1.json"))
    for kind in ("example", "tool", "preference", "run", "trace"):
        fixture = away / (kind + ".json")
        fixture.write_bytes(git("show", CANDIDATE + ":tests/fixtures/contracts/" + kind + ".json"))
        output = run("installed-" + kind, [str(python), "-I", "-m", "toolalign.cli", "validate", str(fixture)], away)
        assert b"VALID: 1 record(s)" in output
    assert len(checks) == 13
    output = {
        "candidate": CANDIDATE, "archives": archives, "commands": checks,
        "installed": installed, "contract_digest": digest,
        "source_tree_imported_by_installed_commands": False,
        "ml_or_model_execution": "NOT_RUN",
    }
    (workspace / "evidence.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "candidate": CANDIDATE, "commands_passed": len(checks), "p01_modules_verified": len(modules),
        "archive_hashes": {name: item["sha256"] for name, item in archives.items()},
        "evidence_sha256": sha((workspace / "evidence.json").read_bytes()),
        "model_or_tokenizer_import": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
