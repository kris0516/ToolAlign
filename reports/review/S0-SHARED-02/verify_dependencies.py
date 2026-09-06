"""Review locked exports and read installed dist-info without importing ML packages."""

import argparse
import importlib.metadata
import json
import subprocess
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[3]
BASE = "97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b"
T1 = "f97bb0de346c220871962a5689014a379fe19c83"
CPU = {
    "attrs", "iniconfig", "jsonschema", "jsonschema-specifications", "packaging", "pluggy",
    "pygments", "pytest", "referencing", "rpds-py", "ruff",
}


def git_file(commit, name):
    return subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT, text=True)


def environment(platform="darwin", machine="arm64", version="3.14.7"):
    return {**default_environment(), "sys_platform": platform, "platform_machine": machine,
            "python_version": ".".join(version.split(".")[:2]), "python_full_version": version,
            "platform_python_implementation": "CPython", "implementation_name": "cpython",
            "os_name": "posix", "platform_system": "Darwin" if platform == "darwin" else "Linux",
            "extra": ""}


def export(extras):
    command = ["uv", "export", "--locked", "--no-hashes", "--no-annotate", "--no-header",
               "--no-emit-project"]
    for extra in extras:
        command += ["--extra", extra]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return [Requirement(line) for line in result.stdout.splitlines() if line.strip()]


def selected(requirements, target):
    result = {}
    for requirement in requirements:
        if requirement.marker and not requirement.marker.evaluate(target):
            continue
        (pin,) = requirement.specifier
        assert pin.operator == "==" and not requirement.url
        name = canonicalize_name(requirement.name)
        assert name not in result or result[name] == pin.version
        result[name] = pin.version
    return result


def installed(path):
    values = {}
    for distribution in importlib.metadata.distributions(path=[str(path)]):
        name = canonicalize_name(distribution.metadata["Name"])
        assert name not in values
        values[name] = distribution
    return values


def check_metadata_closure(distributions, project, extras):
    roots = project["dependencies"] + ["pytest==9.0.2", "ruff==0.15.0"]
    for extra in extras:
        roots += project["optional-dependencies"][extra]
    queue = [Requirement(value) for value in roots]
    seen = set()
    while queue:
        requirement = queue.pop()
        if requirement.marker and not requirement.marker.evaluate(environment()):
            continue
        name = canonicalize_name(requirement.name)
        assert name in distributions, f"Missing {name}"
        distribution = distributions[name]
        assert distribution.version in requirement.specifier, f"Unsatisfied {requirement}"
        key = (name, tuple(sorted(requirement.extras)))
        if key in seen:
            continue
        seen.add(key)
        for raw in distribution.requires or []:
            dependency = Requirement(raw)
            if not dependency.marker or any(
                dependency.marker.evaluate({**environment(), "extra": extra})
                for extra in {"", *requirement.extras}
            ):
                # The parent package's extras have already selected this edge.
                dependency.marker = None
                queue.append(dependency)
    assert {name for name, _ in seen} == distributions.keys() - {"toolalign"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpo-site-packages", type=Path, required=True)
    parser.add_argument("--replay-site-packages", type=Path, required=True)
    args = parser.parse_args()
    before = tomllib.loads(git_file(BASE, "uv.lock"))
    after = tomllib.loads((ROOT / "uv.lock").read_text())
    old_project = tomllib.loads(git_file(BASE, "pyproject.toml"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert len(before["package"]) == 52 and len(after["package"]) == 93
    assert project["project"]["dependencies"] == old_project["project"]["dependencies"]
    assert project["dependency-groups"] == old_project["dependency-groups"]
    assert project["build-system"] == old_project["build-system"]
    assert project["project"]["optional-dependencies"]["compatibility"] == (
        old_project["project"]["optional-dependencies"]["compatibility"]
    )
    for name in CPU:
        assert [p for p in before["package"] if p["name"] == name] == (
            [p for p in after["package"] if p["name"] == name]
        )
    for package in after["package"]:
        if package["name"] == "toolalign":
            continue
        assert package["source"] == {"registry": "https://pypi.org/simple"}
        for artifact in [*package.get("wheels", []), *([package["sdist"]] if "sdist" in package else [])]:
            assert artifact["hash"].startswith("sha256:") and len(artifact["hash"]) == 71
    print("PASS: 11 CPU lock records unchanged; direct CPU/dev/compatibility/build pins preserved")
    print("PASS: 93 lock records; registry sources and SHA-256 artifact pins checked")
    expected = dict(line.split("==") for line in git_file(
        T1, "reports/hardware/P01_EXPLORATION_REQUIREMENTS.txt"
    ).splitlines() if line)
    assert len(expected) == 88
    groups = [(), ("compatibility",), ("compatibility", "dpo"),
              ("compatibility", "dpo", "p01-replay")]
    exports = {group: export(group) for group in groups}
    default = selected(exports[()], environment())
    local = {canonicalize_name(d.metadata["Name"]): d.version
             for d in importlib.metadata.distributions()}
    assert set(default) == CPU and local == {**default, "toolalign": "0.0.1"}
    for group, requirements in exports.items():
        for platform, machine in [("darwin", "arm64"), ("darwin", "x86_64"), ("linux", "x86_64")]:
            choices = selected(requirements, environment(platform, machine))
            if machine == "x86_64":
                assert choices == {**default, **({"psutil": "7.2.2"} if group else {})}
            print(json.dumps({"extras": group, "platform": platform, "machine": machine,
                              "exported_count_with_project": len(choices) + 1}, sort_keys=True))
    for group, path, count in [(groups[2], args.dpo_site_packages, 69),
                              (groups[3], args.replay_site_packages, 90)]:
        values = installed(path)
        versions = {name: distribution.version for name, distribution in values.items()}
        wanted = {**selected(exports[group], environment()), "toolalign": "0.0.1"}
        assert len(values) == count and versions == wanted
        assert all(expected[name] == version for name, version in versions.items()
                   if name not in {"toolalign", "ruff"})
        if group == groups[3]:
            assert versions == {**expected, "ruff": "0.15.0", "toolalign": "0.0.1"}
        check_metadata_closure(values, project["project"], group)
        print(f"PASS: {'+'.join(group)} installed metadata matches locked export and T1; count={count}")
    (wheel,) = (ROOT / "dist").glob("toolalign-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        (member,) = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        metadata = BytesParser().parsebytes(archive.read(member))
    assert set(metadata.get_all("Provides-Extra")) == {"compatibility", "dpo", "p01-replay"}
    requirements = [Requirement(raw) for raw in metadata.get_all("Requires-Dist")]
    for platform, machine in [("darwin", "arm64"), ("darwin", "x86_64"), ("linux", "x86_64")]:
        for extras in [(), ("compatibility", "dpo", "p01-replay")]:
            active = {canonicalize_name(r.name) for r in requirements if not r.marker or any(
                r.marker.evaluate({**environment(platform, machine), "extra": extra})
                for extra in {"", *extras})}
            wanted = {"jsonschema"} | ({"psutil"} if extras else set())
            if machine == "arm64" and extras:
                wanted |= {"mlx", "mlx-lm", "torch", "datasets", "mlx-lm-lora", "mlx-tune"}
            assert active == wanted
    print("PASS: built wheel extras/markers preserve opt-in Darwin arm64 ML roots")


if __name__ == "__main__":
    main()
