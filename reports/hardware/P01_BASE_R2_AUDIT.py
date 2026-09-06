"""Read installed metadata and built archive bytes without importing ML libraries."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = "f97bb0de346c220871962a5689014a379fe19c83"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def environment_inventory(site: Path, extras: tuple[str, ...], project: dict) -> dict:
    distributions = {
        canonicalize_name(d.metadata["Name"]): d
        for d in importlib.metadata.distributions(path=[str(site)])
    }
    versions = {name: d.version for name, d in distributions.items()}
    runtime = list(project["dependencies"])
    for extra in extras:
        runtime += project["optional-dependencies"][extra]
    queue = [Requirement(value) for value in runtime]
    seen = set()
    env = default_environment() | {"extra": ""}
    while queue:
        requirement = queue.pop()
        if requirement.marker and not requirement.marker.evaluate(env):
            continue
        name = canonicalize_name(requirement.name)
        distribution = distributions[name]
        assert distribution.version in requirement.specifier
        key = (name, tuple(sorted(requirement.extras)))
        if key in seen:
            continue
        seen.add(key)
        for raw in distribution.requires or []:
            dependency = Requirement(raw)
            if not dependency.marker or any(
                dependency.marker.evaluate(env | {"extra": extra})
                for extra in {"", *requirement.extras}
            ):
                dependency.marker = None
                queue.append(dependency)
    runtime_names = {name for name, _ in seen}
    previous = dict(line.split("==") for line in (
        ROOT / "reports/hardware/P01_EXPLORATION_REQUIREMENTS.txt"
    ).read_text().splitlines() if line)
    differences = {
        name: {"recorded": previous.get(name), "installed": version}
        for name, version in versions.items()
        if name != "toolalign" and previous.get(name) != version
    }
    identities = json.loads((ROOT / "reports/hardware/P01_SOURCE_IDENTITIES.json").read_text())
    source_checks = {}
    for package, record in identities.items():
        if package not in distributions:
            continue
        checked = {
            name: sha(distributions[package].locate_file(name).read_bytes())
            for name in record["files"]
        }
        assert checked == record["files"]
        source_checks[package] = checked
    return {
        "extras": extras, "installed_count_with_project": len(versions),
        "runtime_versions": {name: versions[name] for name in sorted(runtime_names)},
        "dev_only_versions": {name: versions[name] for name in sorted(
            versions.keys() - runtime_names - {"toolalign"}
        )},
        "project": {"toolalign": versions["toolalign"]},
        "differences_from_exploration": differences,
        "absent_from_subset": sorted(previous.keys() - versions.keys()),
        "unchanged_installed_candidate_source_hashes": source_checks,
    }


def archives() -> dict:
    tracked = set(git("ls-files", "-z").decode().split("\0")) - {""}
    result = {}
    for path in sorted((ROOT / "dist").glob("toolalign-*")):
        assert path.stat().st_size < 10 * 1024**2
        files = {}
        wheel = path.suffix == ".whl"
        if wheel:
            with zipfile.ZipFile(path) as archive:
                assert sum(item.file_size for item in archive.infolist()) < 25 * 1024**2
                files = {name: archive.read(name) for name in archive.namelist()}
        else:
            with tarfile.open(path) as archive:
                assert sum(member.size for member in archive.getmembers()) < 25 * 1024**2
                for member in archive.getmembers():
                    parts = PurePosixPath(member.name)
                    assert not parts.is_absolute() and ".." not in parts.parts
                    assert not member.issym() and not member.islnk()
                    if member.isfile():
                        files[str(PurePosixPath(*parts.parts[1:]))] = (
                            archive.extractfile(member).read()
                        )
        checked, generated = [], []
        for name, content in files.items():
            if (wheel and ".dist-info/" in name) or (not wheel and name == "PKG-INFO"):
                generated.append(name)
                continue
            source = "src/" + name if wheel else name
            assert source in tracked, f"Archive includes untracked payload: {source}"
            assert content == (ROOT / source).read_bytes(), f"Archive byte mismatch: {source}"
            checked.append(source)
        result[path.name] = {
            "size_bytes": path.stat().st_size, "sha256": sha(path.read_bytes()),
            "archive_files": len(files), "tracked_files_byte_identical": len(checked),
            "generated_metadata": generated, "untracked_payload_files": 0,
        }
    assert len(result) == 2
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpo-site-packages", type=Path, required=True)
    parser.add_argument("--replay-site-packages", type=Path, required=True)
    args = parser.parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    paths = ["src/toolalign/training/compatibility", "tests/training/compatibility",
             "reports/hardware", "coordination/handoffs/P01-r1.md"]
    preserved = {}
    for path in git("ls-tree", "-r", "--name-only", PREVIOUS, "--", *paths).decode().splitlines():
        data = (ROOT / path).read_bytes()
        assert data == git("show", PREVIOUS + ":" + path)
        preserved[path] = sha(data)
    output = {
        "scope": "P01-base-r2 metadata/archive audit; no ML imports",
        "previous_candidate": PREVIOUS,
        "checked_commit": git("rev-parse", "HEAD").decode().strip(),
        "audit_script_sha256": sha(Path(__file__).read_bytes()),
        "preserved_previous_files": preserved,
        "environments": [environment_inventory(site, extras, project) for site, extras in (
            (args.dpo_site_packages, ("compatibility", "dpo")),
            (args.replay_site_packages, ("compatibility", "dpo", "p01-replay")),
        )],
        "artifacts": archives(),
    }
    assert not any(name.split(".")[0] in {"mlx", "mlx_lm", "torch", "mlx_tune", "mlx_lm_lora"}
                   for name in sys.modules)
    output["ml_packages_imported"] = False
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
