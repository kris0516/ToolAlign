"""Inspect newly built archives against exact Git blobs and the input baseline."""

import argparse
import base64
import csv
import hashlib
import io
import json
import stat
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

CANDIDATE = "947144fa2dd248113f6db412f120cdae5483c9b8"
BASE = "4a1fa84d2d367ed037a1e39b1d4033f54a385e6a"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and ".." not in path.parts
    assert not any(part.lower() in {".toolalign-local", ".venv", "__pycache__"}
                   for part in path.parts)
    assert not name.lower().endswith((".pyc", ".log", ".safetensors", ".pt"))


def main():
    parser = argparse.ArgumentParser()
    for name in ("repo", "sdist", "wheel", "rebuilt", "baseline", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()

    def git(*argv):
        return subprocess.check_output(["git", *argv], cwd=args.repo)

    tracked = git("ls-tree", "-r", "--name-only", CANDIDATE).decode().splitlines()
    config = tomllib.loads(git("show", CANDIDATE + ":pyproject.toml").decode())
    include = config["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    expected = {name for name in tracked
                if any(name == root or name.startswith(root + "/") for root in include)}
    # This build also includes the tracked VCS ignore file; bind its exact bytes.
    expected.add(".gitignore")
    archive_rows = {}
    with tarfile.open(args.sdist) as archive:
        members = archive.getmembers()
        assert all(member.isfile() for member in members)
        values = {}
        for member in members:
            safe(member.name)
            root, name = member.name.split("/", 1)
            assert root == "toolalign-0.0.1" and name not in values
            values[name] = archive.extractfile(member).read()
    assert set(values) == expected | {"PKG-INFO"}
    for name in expected:
        assert values[name] == git("show", CANDIDATE + ":" + name), name
    assert "tests/evaluation/harness/deadline_cases.py" in expected
    archive_rows["sdist"] = {
        "path": str(args.sdist.resolve()), "sha256": sha(args.sdist.read_bytes()),
        "bytes": args.sdist.stat().st_size, "members": len(values),
        "git_payload_members": len(expected),
        "member_sha256": {name: sha(raw) for name, raw in values.items()},
    }

    production = {name.removeprefix("src/"): name for name in tracked
                  if name.startswith("src/toolalign/")}
    for source_name in production.values():
        assert git("show", BASE + ":" + source_name) == git(
            "show", CANDIDATE + ":" + source_name
        )
    payloads = []
    for role in ("wheel", "rebuilt", "baseline"):
        path = getattr(args, role)
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            assert len({info.filename for info in infos}) == len(infos)
            for info in infos:
                safe(info.filename)
                assert stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
            payload = {info.filename: archive.read(info) for info in infos}
        metadata = set(payload) - set(production)
        prefix = "toolalign-0.0.1.dist-info/"
        assert metadata == {prefix + name for name in (
            "METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD"
        )}
        for name, source_name in production.items():
            assert payload[name] == git("show", CANDIDATE + ":" + source_name)
        assert payload[prefix + "METADATA"] == values["PKG-INFO"]
        assert payload[prefix + "licenses/LICENSE"] == git("show", CANDIDATE + ":LICENSE")
        rows = list(csv.reader(io.StringIO(payload[prefix + "RECORD"].decode())))
        assert len(rows) == len(payload) and {row[0] for row in rows} == set(payload)
        for name, digest, size in rows:
            if name == prefix + "RECORD":
                assert not digest and not size
            else:
                actual = base64.urlsafe_b64encode(hashlib.sha256(payload[name]).digest())
                assert digest == "sha256=" + actual.decode().rstrip("=")
                assert int(size) == len(payload[name])
        archive_rows[role] = {
            "path": str(path.resolve()), "sha256": sha(path.read_bytes()),
            "bytes": path.stat().st_size, "members": len(payload),
            "git_payload_members": len(production), "metadata_members": len(metadata),
            "member_sha256": {name: sha(raw) for name, raw in payload.items()},
        }
        payloads.append(payload)
    assert payloads[0] == payloads[1] == payloads[2]
    assert args.wheel.read_bytes() == args.rebuilt.read_bytes() == args.baseline.read_bytes()
    result = {
        "candidate": CANDIDATE, "baseline": BASE, "archives": archive_rows,
        "three_wheels_byte_equal": True, "default_route": "sdist then wheel",
        "explicit_route": "same new sdist to wheel",
        "baseline_route": "direct wheel from exact baseline package inputs",
        "candidate_direct_source_wheel": "NOT_RUN",
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({role: {key: value for key, value in row.items()
                             if key not in ("member_sha256", "path")}
                      for role, row in archive_rows.items()}, indent=2))


if __name__ == "__main__":
    main()
