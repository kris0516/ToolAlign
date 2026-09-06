"""R1 full archive membership/RECORD checks and default-wheel API verification."""

from __future__ import annotations

import argparse
import base64
import csv
import email.parser
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tomllib
import unittest
import zipfile
from pathlib import Path, PurePosixPath

from review_materials import sha


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def inspect(args):
    root = args.root.resolve()
    names = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=root, text=True).splitlines())
    project = tomllib.loads((root / "pyproject.toml").read_text())
    includes = project["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    source = {n for n in names if any(n == p or n.startswith(p + "/") for p in includes)} | {".gitignore"}
    package = {n[4:] for n in names if n.startswith("src/toolalign/")}
    assert len(source) == 107 and len(package) == 49
    results = {}
    for owner, directory in (("r1", args.archives), ("d1", args.worker_archives)):
        sdist = directory / "default/toolalign-0.0.1.tar.gz"
        with tarfile.open(sdist) as archive:
            contents = {}
            for member in archive.getmembers():
                path = PurePosixPath(member.name)
                assert member.isfile() and not path.is_absolute() and ".." not in path.parts
                assert path.parts[0] == "toolalign-0.0.1"
                name = str(PurePosixPath(*path.parts[1:]))
                assert name not in contents
                contents[name] = archive.extractfile(member).read()
            assert set(contents) == source | {"PKG-INFO"}
            for name in source:
                assert contents[name] == (root / name).read_bytes()
            metadata = email.parser.BytesParser().parsebytes(contents["PKG-INFO"])
            results[owner + "_sdist"] = {"sha256": sha(sdist.read_bytes()), "size_bytes": sdist.stat().st_size,
                                        "members": {n: sha(v) for n, v in contents.items()}}
        prefix = "toolalign-0.0.1.dist-info/"
        meta_names = {prefix + n for n in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")}
        for label in ("default", "rebuilt"):
            wheel = directory / label / "toolalign-0.0.1-py3-none-any.whl"
            with zipfile.ZipFile(wheel) as archive:
                members = archive.namelist()
                assert len(members) == len(set(members)) and set(members) == package | meta_names
                for entry in archive.infolist():
                    path = PurePosixPath(entry.filename)
                    assert not path.is_absolute() and ".." not in path.parts
                    assert not entry.is_dir() and (entry.external_attr >> 16) & 0o170000 != 0o120000
                for name in package:
                    assert archive.read(name) == (root / "src" / name).read_bytes()
                wheel_meta = email.parser.BytesParser().parsebytes(archive.read(prefix + "METADATA"))
                for key in ("Name", "Version", "Requires-Python", "Requires-Dist", "Provides-Extra", "License-Expression"):
                    assert metadata.get_all(key) == wheel_meta.get_all(key)
                assert wheel_meta["Name"] == "toolalign" and wheel_meta["Version"] == "0.0.1"
                assert wheel_meta["Requires-Python"] == "<3.15,>=3.11"
                assert [d for d in wheel_meta.get_all("Requires-Dist") if "extra ==" not in d] == ["jsonschema==4.26.0"]
                assert set(wheel_meta.get_all("Provides-Extra")) == {"compatibility", "dpo", "p01-replay"}
                assert archive.read(prefix + "licenses/LICENSE") == (root / "LICENSE").read_bytes()
                assert archive.read(prefix + "entry_points.txt").decode() == "[console_scripts]\ntoolalign = toolalign.cli:main\n"
                wheel_text = archive.read(prefix + "WHEEL").decode()
                assert "Root-Is-Purelib: true" in wheel_text and "Tag: py3-none-any" in wheel_text
                rows = list(csv.reader(io.StringIO(archive.read(prefix + "RECORD").decode())))
                assert len(rows) == len(members) and {r[0] for r in rows} == set(members)
                for name, digest, size in rows:
                    if name == prefix + "RECORD":
                        assert digest == size == ""
                    else:
                        data = archive.read(name)
                        expected = "sha256=" + base64.urlsafe_b64encode(bytes.fromhex(sha(data))).decode().rstrip("=")
                        assert digest == expected and int(size) == len(data)
                results[owner + "_" + label + "_wheel"] = {"sha256": sha(wheel.read_bytes()),
                    "size_bytes": wheel.stat().st_size, "members": {n: sha(archive.read(n)) for n in members},
                    "full_record_checked": True, "metadata_checked": True}
    assert len({v["sha256"] for k, v in results.items() if k.endswith("wheel")}) == 1
    assert results["r1_sdist"] == results["d1_sdist"]
    result = {"status": "PASS", "candidate_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "archives": results, "package_files": {n: sha((root / "src" / n).read_bytes()) for n in package},
              "new_r1_builds": 3, "old_archives_reparsed": 3, "sdist_git_members": 107,
              "wheel_package_members": 49, "direct_source_wheel": "NOT_RUN"}
    save(args.output, result)
    print(json.dumps({"status": "PASS", "archives": {k: {"sha256": v["sha256"], "bytes": v["size_bytes"],
                                                          "members": len(v["members"])} for k, v in results.items()}}))


def installed(args):
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    target, runtime = args.target.resolve(), args.runtime.resolve()
    sys.path[:0] = [str(target), str(runtime)]
    expected = read(args.expected)
    for name, digest in expected["package_files"].items():
        assert sha((target / name).read_bytes()) == digest
    inputs = read(args.inputs)
    os.environ["TOOLALIGN_REVIEW_CONFIG"] = inputs["config_path"]
    spec = importlib.util.spec_from_file_location("r1_binding_cases", args.probe.resolve())
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    suite = unittest.defaultTestLoader.loadTestsFromModule(probe)
    outcome = unittest.TextTestRunner(stream=sys.stdout).run(suite)
    assert outcome.wasSuccessful() and outcome.testsRun == 13
    from toolalign.data.common import DataError
    from toolalign.data.training_selection import bound_inputs, verify

    checked = verify(output=args.selection.resolve(), **inputs)
    assert checked["profiles"]["smoke"]["train"]["selected_count"] == 1600
    assert checked["profiles"]["formal"]["train"]["selected_count"] == 6013
    # Production pinning, without editing any original input or rebuilding its corpus.
    bad = args.output.resolve().parent / "r1-bad-input.json"
    with bad.open("x") as stream:
        stream.write('{"artifacts":{}}\n')
    errors = {}
    for name in ("config_path", "protocol_path", "representation_path", "audit_path", "data_manifest_path"):
        try:
            bound_inputs(**(inputs | {name: str(bad)}))
        except DataError as exc:
            errors[name] = str(exc)
        else:
            raise AssertionError("accepted modified pinned input: " + name)
    unavailable = ("tokenizers", "transformers", "torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax",
                   "jinja2", "huggingface_hub", "psutil")
    assert all(importlib.util.find_spec(name) is None for name in unavailable)
    assert not set(unavailable) & {name.split(".")[0] for name in sys.modules}
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(target)
            digest = sha(path.read_bytes())
            assert digest == expected["package_files"][path.relative_to(target).as_posix()]
            origins[name] = {"path": str(path), "sha256": digest}
    result = {"status": "PASS", "repeated_original_tests": outcome.testsRun,
              "production_input_tamper_errors": errors, "actual_selection_verified": True,
              "profiles": checked["profiles"], "module_origins": origins,
              "package_files_checked": 49, "optional_packages_unavailable": list(unavailable),
              "isolated": True, "no_site": True, "bytecode_disabled": True, "source_cwd_imports": 0}
    save(args.output, result)
    print(json.dumps({"status": "PASS", "repeated_original_tests": 13, "production_pinned_input_failures": errors,
                      "installed_modules": len(origins), "source_cwd_imports": 0, "optional_imports": []}))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    archive = sub.add_parser("inspect")
    for key in ("root", "archives", "worker-archives", "output"):
        archive.add_argument("--" + key, type=Path, required=True)
    install = sub.add_parser("installed")
    for key in ("target", "runtime", "expected", "inputs", "selection", "probe", "output"):
        install.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    {"inspect": inspect, "installed": installed}[args.command](args)


if __name__ == "__main__":
    main()
