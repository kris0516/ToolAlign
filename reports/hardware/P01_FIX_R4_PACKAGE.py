"""Bind new sdist/wheel bytes to Git and exercise installed startup/report behavior."""

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

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def archive_record(path, candidate, tracked, project):
    wheel, files = path.suffix == ".whl", {}
    assert path.stat().st_size < 2 * 1024**2
    if wheel:
        with zipfile.ZipFile(path) as archive:
            assert sum(item.file_size for item in archive.infolist()) < 8 * 1024**2
            for item in archive.infolist():
                name = PurePosixPath(item.filename)
                assert not name.is_absolute() and ".." not in name.parts
                assert not stat.S_ISLNK(item.external_attr >> 16) and item.filename not in files
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
        metadata = {prefix + name for name in ("METADATA", "WHEEL", "entry_points.txt",
                                                "RECORD", "licenses/LICENSE")}
    else:
        includes = project["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
        expected = {name for name in tracked if any(name == entry or name.startswith(entry + "/")
                                                   for entry in includes)} | {".gitignore"}
        metadata = {"PKG-INFO"}
    generated, payloads = {}, {}
    for name, content in files.items():
        if name in metadata:
            generated[name] = sha(content)
            continue
        source = "src/" + name if wheel else name
        assert source in tracked
        assert content == git("show", candidate + ":" + source) == (ROOT / source).read_bytes()
        payloads[source] = sha(content)
    assert set(payloads) == expected and set(generated) == metadata
    return {"sha256": sha(path.read_bytes()), "bytes": path.stat().st_size,
            "archive_files": len(files), "tracked_payload_hashes": payloads,
            "generated_metadata_hashes": generated, "untracked_payloads": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args()
    private = args.private_root.resolve()
    assert private.is_relative_to((ROOT / ".toolalign-local/p01-fix-r4").resolve())
    candidate = git("rev-parse", "HEAD").decode().strip()
    tracked = set(git("ls-tree", "-r", "--name-only", candidate).decode().splitlines())
    project = tomllib.loads(git("show", candidate + ":pyproject.toml").decode())
    paths = {"sdist": private / "build/toolalign-0.0.1.tar.gz",
             "wheel_from_sdist": private / "build/toolalign-0.0.1-py3-none-any.whl"}
    archives = {name: archive_record(path, candidate, tracked, project)
                for name, path in paths.items()}
    workspace = private / "package-check"
    workspace.mkdir(exist_ok=False)
    away = workspace / "away-from-source"
    away.mkdir()
    environment, commands = workspace / "venv", []
    python = environment / "bin/python"
    env = dict(os.environ, UV_OFFLINE="1")
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)

    def clean(value):
        return str(value).replace(str(ROOT), "<WORKTREE>")

    def run(name, command, cwd):
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=60)
        (workspace / (name + ".stdout")).write_bytes(result.stdout)
        (workspace / (name + ".stderr")).write_bytes(result.stderr)
        commands.append({"name": name, "command": [clean(value) for value in command],
                         "cwd": clean(cwd), "started_at": started,
                         "ended_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         "exit_code": result.returncode,
                         "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr)})
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        return result.stdout

    requirements = workspace / "runtime.txt"
    run("export", ["uv", "export", "--locked", "--no-dev", "--no-emit-project",
                   "--output-file", str(requirements)], ROOT)
    run("venv", ["uv", "venv", "--python", "3.14", str(environment)], away)
    run("dependencies", ["uv", "pip", "install", "--python", str(python), "--require-hashes",
                         "-r", str(requirements)], away)
    run("wheel", ["uv", "pip", "install", "--python", str(python), "--no-deps",
                  str(paths["wheel_from_sdist"])], away)
    run("dependency-check", ["uv", "pip", "check", "--python", str(python)], away)
    modules = {name.removeprefix("src/").removesuffix(".py").replace("/", "."):
               sha(git("show", candidate + ":" + name)) for name in tracked
               if name.startswith("src/toolalign/training/compatibility/") and name.endswith(".py")}
    assert len(modules) == 8
    expected = away / "expected.json"
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
print(json.dumps({'modules':8,'module_hashes':expected,'isolated':True,'distributions':versions},sort_keys=True))
''')
    installed = json.loads(run("installed-modules", [str(python), "-I", str(probe), str(expected)], away))
    run("installed-help", [str(python), "-I", "-m", "toolalign.training.compatibility", "--help"], away)
    digest = run("contract-digest", [str(python), "-I", "-m", "toolalign.cli", "contract-digest"], away).decode().strip()
    assert digest == sha(git("show", candidate + ":src/toolalign/contracts/v1.json"))
    for kind in ("example", "tool", "preference", "run", "trace"):
        fixture = away / (kind + ".json")
        fixture.write_bytes(git("show", candidate + ":tests/fixtures/contracts/" + kind + ".json"))
        output = run("validate-" + kind, [str(python), "-I", "-m", "toolalign.cli",
                                         "validate", str(fixture)], away)
        assert b"VALID: 1 record(s)" in output
    report_path = ROOT / "reports/hardware/P01_BUILD_REPORT.py"
    assert report_path.read_bytes() == git("show", candidate + ":reports/hardware/P01_BUILD_REPORT.py")
    startup_probe = Path(__file__).with_name("P01_FIX_R4_INSTALLED_PROBE.py")
    startup = json.loads(run("installed-startup-report", [str(python), "-I", str(startup_probe),
                           str(away / "run.json"), str(report_path), str(away)], away).splitlines()[-1])
    assert len(commands) == 14
    result = {"candidate": candidate, "archives": archives, "commands": commands,
              "installed": installed, "startup_report": startup, "contract_digest": digest,
              "offline": True, "all_stdout_stderr_retained": True,
              "report_source_sha256": sha(report_path.read_bytes()),
              "source_package_imported_by_isolated_probe": False,
              "model_or_gpu_execution": "NOT_RUN"}
    output = workspace / "evidence.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"candidate": candidate, "commands_passed": len(commands),
                      "archives": {name: item["sha256"] for name, item in archives.items()},
                      "evidence_sha256": sha(output.read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
