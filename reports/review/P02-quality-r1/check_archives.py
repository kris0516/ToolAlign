"""Check existing archive members and RECORD directly against frozen Git bytes."""

import argparse
import base64
import csv
import email.parser
import hashlib
import io
import json
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("repo", "intake", "archives", "output", "worker-installed"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    intake = json.loads(args.intake.read_text())
    frozen = intake["candidate_files"]
    project = tomllib.loads((args.repo / "pyproject.toml").read_text())
    roots = project["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    source = {n for n in frozen if any(n == p or n.startswith(p + "/") for p in roots)} | {".gitignore"}
    payload = {n.removeprefix("src/"): frozen[n] for n in frozen if n.startswith("src/toolalign/")}
    assert len(payload) == 60
    metadata_prefix = "toolalign-0.0.1.dist-info/"
    metadata_names = {metadata_prefix + n for n in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")}
    details = {}
    source_info = None
    for label, path in (("sdist", args.archives / "default/toolalign-0.0.1.tar.gz"),
                        ("default-wheel", args.archives / "default/toolalign-0.0.1-py3-none-any.whl"),
                        ("rebuilt-wheel", args.archives / "rebuilt/toolalign-0.0.1-py3-none-any.whl")):
        content = {}
        if label == "sdist":
            with tarfile.open(path) as archive:
                for member in archive.getmembers():
                    name = PurePosixPath(member.name)
                    assert member.isfile() and not member.issym() and not member.islnk()
                    assert not name.is_absolute() and ".." not in name.parts
                    assert name.parts[0] == "toolalign-0.0.1"
                    relative = PurePosixPath(*name.parts[1:]).as_posix()
                    assert relative not in content
                    content[relative] = archive.extractfile(member).read()
            assert set(content) == source | {"PKG-INFO"} and len(content) == 128
            for name in source:
                assert sha(content[name]) == frozen[name]["sha256"] and len(content[name]) == frozen[name]["bytes"]
            source_info = email.parser.BytesParser().parsebytes(content["PKG-INFO"])
        else:
            with zipfile.ZipFile(path) as archive:
                for entry in archive.infolist():
                    name = PurePosixPath(entry.filename)
                    assert not entry.is_dir() and not name.is_absolute() and ".." not in name.parts
                    assert (entry.external_attr >> 16) & 0o170000 != 0o120000
                    assert entry.filename not in content
                    content[entry.filename] = archive.read(entry.filename)
            assert set(content) == set(payload) | metadata_names and len(content) == 65
            for name, expected in payload.items():
                assert sha(content[name]) == expected["sha256"] and len(content[name]) == expected["bytes"]
            info = email.parser.BytesParser().parsebytes(content[metadata_prefix + "METADATA"])
            assert source_info is not None
            for field in ("Name", "Version", "Requires-Python", "Requires-Dist", "Provides-Extra", "License-Expression", "License-File"):
                assert info.get_all(field) == source_info.get_all(field)
            assert info["Name"] == project["project"]["name"] and info["Version"] == project["project"]["version"]
            assert {v.strip() for v in info["Requires-Python"].split(",")} == {
                v.strip() for v in project["project"]["requires-python"].split(",")
            }
            assert info["License-Expression"] == "MIT"
            assert set(info.get_all("Provides-Extra")) == set(project["project"]["optional-dependencies"])
            assert [r for r in info.get_all("Requires-Dist") if "extra ==" not in r] == ["jsonschema==4.26.0"]
            assert content[metadata_prefix + "licenses/LICENSE"] == (args.repo / "LICENSE").read_bytes()
            assert b"toolalign = toolalign.cli:main" in content[metadata_prefix + "entry_points.txt"]
            assert b"Root-Is-Purelib: true" in content[metadata_prefix + "WHEEL"]
            assert b"Tag: py3-none-any" in content[metadata_prefix + "WHEEL"]
            record = list(csv.reader(io.StringIO(content[metadata_prefix + "RECORD"].decode())))
            assert len(record) == len(content) and {r[0] for r in record} == set(content)
            for name, checksum, size in record:
                if name.endswith(".dist-info/RECORD"):
                    assert checksum == size == ""
                else:
                    raw = content[name]
                    assert checksum == "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
                    assert size == str(len(raw))
        details[label] = {"path": str(path.resolve()), "sha256": sha(path.read_bytes()),
                          "bytes": path.stat().st_size, "members": {k: {"sha256": sha(v), "bytes": len(v)} for k, v in content.items()}}
    assert details["default-wheel"]["sha256"] == details["rebuilt-wheel"]["sha256"] == "7de39c233e46a1bda302e77361ce55ef5a0c5a6f42265d5a5a50ce2dd2e2e95b"
    assert details["sdist"]["sha256"] == "65623012f5046bbc46160c99d384d94532e8d30a5a08e684ca67652d5177b629"
    for name, expected in payload.items():
        assert sha((args.worker_installed / name).read_bytes()) == expected["sha256"]
    result = {"status": "PASS_THREE_EXISTING_ARCHIVES", "candidate": intake["candidate"],
              "archives": details, "package_payload_files": 60, "sdist_git_files": len(source),
              "worker_installed_package_files": 60, "new_archive_builds": 0,
              "default_requirement": "jsonschema==4.26.0", "metadata_and_all_record_entries_verified": True}
    with args.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "archives"}, sort_keys=True))


if __name__ == "__main__":
    main()
