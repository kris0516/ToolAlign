"""R1: bind existing archives to a precise tree without rebuilding them."""

import argparse
import base64
import csv
import hashlib
import io
import json
import subprocess
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit(root, archives, candidate):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    names = git("ls-tree", "-r", "--name-only", candidate).decode().splitlines()
    project = tomllib.loads(git("show", candidate + ":pyproject.toml").decode())
    includes = project["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    source_names = {n for n in names if any(n == p or n.startswith(p + "/") for p in includes)}
    source_names.add(".gitignore")
    package = {n.removeprefix("src/"): git("show", candidate + ":" + n)
               for n in names if n.startswith("src/toolalign/")}
    assert len(package) == 62
    result = {"candidate": candidate, "package_files": {n: sha(b) for n, b in package.items()},
              "new_archive_builds": 0, "archives": {}}
    source_path = archives / "default/toolalign-0.0.1.tar.gz"
    contents = {}
    with tarfile.open(source_path) as source:
        for member in source.getmembers():
            parts = PurePosixPath(member.name)
            assert member.isfile() and not parts.is_absolute() and ".." not in parts.parts
            assert parts.parts[0] == "toolalign-0.0.1"
            name = PurePosixPath(*parts.parts[1:]).as_posix()
            assert name not in contents
            contents[name] = source.extractfile(member).read()
    assert set(contents) == source_names | {"PKG-INFO"}
    for name in source_names:
        assert contents[name] == git("show", candidate + ":" + name)
    pkg_info = BytesParser().parsebytes(contents["PKG-INFO"])
    result["archives"]["sdist"] = {
        "sha256": sha(source_path.read_bytes()), "bytes": source_path.stat().st_size,
        "members": {n: sha(b) for n, b in contents.items()},
    }
    prefix = "toolalign-0.0.1.dist-info/"
    extras = {prefix + n for n in ("METADATA", "WHEEL", "RECORD", "entry_points.txt", "licenses/LICENSE")}
    for label in ("default", "rebuilt"):
        path = archives / label / "toolalign-0.0.1-py3-none-any.whl"
        with zipfile.ZipFile(path) as wheel:
            members = wheel.infolist()
            assert len({m.filename for m in members}) == len(members)
            assert {m.filename for m in members} == set(package) | extras
            for member in members:
                name = PurePosixPath(member.filename)
                assert not member.is_dir() and not name.is_absolute() and ".." not in name.parts
                assert (member.external_attr >> 16) & 0o170000 != 0o120000
            for name, data in package.items():
                assert wheel.read(name) == data
            metadata = BytesParser().parsebytes(wheel.read(prefix + "METADATA"))
            for key in ("Name", "Version", "Requires-Python", "Requires-Dist", "Provides-Extra", "License-Expression"):
                assert metadata.get_all(key) == pkg_info.get_all(key)
            assert metadata["Name"] == project["project"]["name"]
            assert metadata["Version"] == project["project"]["version"]
            # Hatch normalizes the order of comma-separated version constraints.
            assert sorted(p.strip() for p in metadata["Requires-Python"].split(",")) == sorted(
                p.strip() for p in project["project"]["requires-python"].split(",")
            )
            assert [v for v in metadata.get_all("Requires-Dist") if "extra ==" not in v] == ["jsonschema==4.26.0"]
            assert wheel.read(prefix + "licenses/LICENSE") == git("show", candidate + ":LICENSE")
            assert "toolalign = toolalign.cli:main" in wheel.read(prefix + "entry_points.txt").decode()
            assert b"Root-Is-Purelib: true" in wheel.read(prefix + "WHEEL")
            assert b"Tag: py3-none-any" in wheel.read(prefix + "WHEEL")
            rows = list(csv.reader(io.StringIO(wheel.read(prefix + "RECORD").decode())))
            assert len(rows) == len(members) and {r[0] for r in rows} == {m.filename for m in members}
            for name, digest, size in rows:
                if name == prefix + "RECORD":
                    assert digest == size == ""
                else:
                    data = wheel.read(name)
                    expected = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
                    assert digest == "sha256=" + expected and size == str(len(data))
            result["archives"][label + "_wheel"] = {
                "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size,
                "members": {m.filename: sha(wheel.read(m.filename)) for m in members},
                "record_verified": True, "metadata_verified": True,
            }
    assert len(result["archives"]["sdist"]["members"]) == 134
    assert all(len(result["archives"][n]["members"]) == 67 for n in ("default_wheel", "rebuilt_wheel"))
    assert result["archives"]["default_wheel"]["sha256"] == result["archives"]["rebuilt_wheel"]["sha256"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("root", "archives", "output"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()
    proof = audit(args.root, args.archives, args.candidate)
    with args.output.open("x") as stream:
        json.dump(proof, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"candidate": args.candidate, "package_files": len(proof["package_files"]),
                      "archives": {k: {"sha256": v["sha256"], "members": len(v["members"])}
                                   for k, v in proof["archives"].items()}, "new_archive_builds": 0}))
