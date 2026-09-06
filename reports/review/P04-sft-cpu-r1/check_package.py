"""Independently inspect existing archives and origins of a newly installed wheel."""

from __future__ import annotations

import argparse
import base64
import csv
import email.parser
import hashlib
import importlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

CANDIDATE = "33d6248e2c518ea777618224382bd30a3cc3433d"
SDIST_SHA = "54ca695f640014ac03128e5dd33534d913f097c8a22019af7fae90f746183655"
WHEEL_SHA = "936256e277cdf3ae7c43668dc4ad358c4249de24a17273e721936f7584cbee33"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def safe_name(name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and ".." not in path.parts and "\\" not in name
    return path


def archives(args):
    root = Path.cwd()
    tracked = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", CANDIDATE], text=True).splitlines()
    project = tomllib.loads((root / "pyproject.toml").read_text())
    includes = project["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    expected_source = {name for name in tracked if any(name == rule or name.startswith(rule + "/")
                                                      for rule in includes)} | {".gitignore"}
    expected_package = {name[4:] for name in tracked if name.startswith("src/toolalign/")}
    assert len(expected_source) == 118 and len(expected_package) == 57
    sdist = args.t1_private / "packages/default/toolalign-0.0.1.tar.gz"
    assert sha(sdist.read_bytes()) == SDIST_SHA and sdist.stat().st_size == 243688
    tar_contents = {}
    with tarfile.open(sdist) as archive:
        members = archive.getmembers()
        assert len(members) == len({item.name for item in members}) == 119
        for item in members:
            path = safe_name(item.name)
            assert item.isfile() and not item.issym() and not item.islnk()
            assert path.parts[0] == "toolalign-0.0.1"
            name = PurePosixPath(*path.parts[1:]).as_posix()
            tar_contents[name] = archive.extractfile(item).read()
    assert set(tar_contents) == expected_source | {"PKG-INFO"}
    for name in expected_source:
        actual_git = subprocess.check_output(["git", "show", CANDIDATE + ":" + name])
        assert tar_contents[name] == (root / name).read_bytes() == actual_git
    metadata = email.parser.BytesParser().parsebytes(tar_contents["PKG-INFO"])
    results = {"sdist": {"path": str(sdist), "sha256": SDIST_SHA, "size_bytes": 243688,
                          "members": {name: sha(data) for name, data in tar_contents.items()}}}
    prefix = "toolalign-0.0.1.dist-info/"
    meta_names = {prefix + name for name in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")}
    for label in ("default", "rebuilt"):
        wheel = args.t1_private / ("packages/" + label + "/toolalign-0.0.1-py3-none-any.whl")
        assert sha(wheel.read_bytes()) == WHEEL_SHA and wheel.stat().st_size == 129868
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) == 62
            assert set(names) == expected_package | meta_names
            for info in archive.infolist():
                safe_name(info.filename)
                assert not info.is_dir() and (info.external_attr >> 16) & 0o170000 != 0o120000
                if info.filename in expected_package:
                    assert archive.read(info.filename) == tar_contents["src/" + info.filename]
            wheel_metadata = email.parser.BytesParser().parsebytes(archive.read(prefix + "METADATA"))
            for field in ("Name", "Version", "Requires-Python", "Requires-Dist", "Provides-Extra", "License-Expression"):
                assert wheel_metadata.get_all(field) == metadata.get_all(field)
            assert wheel_metadata["Name"] == "toolalign" and wheel_metadata["Version"] == "0.0.1"
            assert set(wheel_metadata["Requires-Python"].split(",")) == {">=3.11", "<3.15"}
            assert wheel_metadata["License-Expression"] == "MIT"
            assert [value for value in wheel_metadata.get_all("Requires-Dist") if "extra ==" not in value] == ["jsonschema==4.26.0"]
            assert archive.read(prefix + "licenses/LICENSE") == tar_contents["LICENSE"]
            wheel_info = archive.read(prefix + "WHEEL").decode()
            assert "Root-Is-Purelib: true" in wheel_info and "Tag: py3-none-any" in wheel_info
            assert "toolalign = toolalign.cli:main" in archive.read(prefix + "entry_points.txt").decode()
            record = list(csv.reader(io.StringIO(archive.read(prefix + "RECORD").decode())))
            assert len(record) == len(names) and {row[0] for row in record} == set(names)
            for name, checksum, size in record:
                if name == prefix + "RECORD":
                    assert checksum == size == ""
                else:
                    raw = archive.read(name)
                    expected = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
                    assert checksum == "sha256=" + expected and size == str(len(raw))
            results[label + "_wheel"] = {"path": str(wheel), "sha256": WHEEL_SHA, "size_bytes": 129868,
                                           "members": {name: sha(archive.read(name)) for name in names},
                                           "metadata_and_record_verified": True}
    result = {"status": "PASS", "candidate": CANDIDATE, "archives": results,
              "sdist_git_files": 118, "package_files": 57, "new_builds": 0, "new_installs": 0,
              "direct_source_wheel": "NOT_RUN", "existing_archives_parsed": 3}
    save(args.output, result)
    print(json.dumps({"status": "PASS", "archives": 3, "sdist_git_files": 118, "package_files": 57}))


def installed(args):
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    target, runtime = args.target.resolve(), args.runtime.resolve()
    sys.path[:0] = [str(target), str(runtime)]
    names = ("__init__", "__main__", "config", "data", "collator", "plan", "validation", "mlx_adapter")
    for name in names:
        importlib.import_module("toolalign.training.sft" + ("" if name == "__init__" else "." + name))
    from toolalign.training.sft.config import consumer_identity

    assert sha(args.wheel.read_bytes()) == WHEEL_SHA
    origins = {}
    with zipfile.ZipFile(args.wheel) as archive:
        package_files = [name for name in archive.namelist() if name.startswith("toolalign/")]
        assert len(package_files) == 57
        for name in package_files:
            assert (target / name).read_bytes() == archive.read(name)
        for name, module in tuple(sys.modules.items()):
            if name == "toolalign" or name.startswith("toolalign."):
                path = Path(module.__file__).resolve()
                assert path.is_relative_to(target)
                relative = path.relative_to(target).as_posix()
                assert path.read_bytes() == archive.read(relative)
                origins[name] = {"path": str(path), "sha256": sha(path.read_bytes())}
    optional = {"mlx", "mlx_lm", "torch", "transformers", "tokenizers", "tensorflow", "flax", "jax",
                "datasets", "mlx_tune", "mlx_lm_lora"}
    assert not optional & {name.split(".")[0] for name in sys.modules}
    assert all(importlib.util.find_spec(name) is None for name in optional)
    assert len([name for name in origins if name.startswith("toolalign.training.sft")]) == 8
    result = {"status": "PASS", "candidate": CANDIDATE, "wheel_sha256": WHEEL_SHA,
              "target": str(target), "read_only_default_runtime": str(runtime), "origins": origins,
              "new_sft_modules": 8, "package_files": 57, "consumer": consumer_identity(),
              "optional_modules_loaded": [], "source_cwd_imports": 0,
              "isolated": True, "no_site": True, "no_bytecode": True}
    save(args.output, result)
    print(json.dumps({"status": "PASS", "new_sft_modules": 8, "loaded_toolalign_modules": len(origins)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    check = sub.add_parser("archives")
    check.add_argument("--t1-private", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("installed")
    for flag in ("target", "runtime", "wheel", "output"):
        check.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    {"archives": archives, "installed": installed}[args.mode](args)


if __name__ == "__main__":
    main()
