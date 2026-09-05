"""Inspect metadata and evidence bytes only; never import optional ML distributions."""

import argparse
import hashlib
import importlib.metadata as metadata
import json
import sys
import tomllib
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[3]
PINS = {"mlx": "0.32.2", "mlx-lm": "0.31.3", "torch": "2.14.0", "psutil": "7.2.2"}


def distributions(path=None):
    items = metadata.distributions(path=[str(path)]) if path else metadata.distributions()
    return {canonicalize_name(d.metadata["Name"]): d for d in items}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pypi-dir", type=Path, required=True)
    parser.add_argument("--compat-site", type=Path, required=True)
    parser.add_argument("--s0-verification", type=Path, required=True)
    args = parser.parse_args()
    assert args.compat_site.is_dir()
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    installed = distributions()
    optional = {*PINS, "mlx-metal", "mlx-tune"}
    assert not (set(installed) & optional)
    assert installed["jsonschema"].version == "4.26.0"
    print("default_distributions=" + json.dumps({k: d.version for k, d in installed.items()}, sort_keys=True))
    compat = distributions(args.compat_site)
    assert "mlx-tune" not in compat
    for name, version in {**PINS, "mlx-metal": "0.32.2"}.items():
        assert compat[name].version == version
    env = {**default_environment(), "extra": ""}
    for name, distribution in compat.items():
        python_requirement = distribution.metadata.get("Requires-Python")
        if python_requirement:
            assert SpecifierSet(python_requirement).contains(env["python_full_version"])
        for raw in distribution.requires or []:
            requirement = Requirement(raw)
            if requirement.marker and not requirement.marker.evaluate(env):
                continue
            dependency = compat[canonicalize_name(requirement.name)]
            assert requirement.specifier.contains(dependency.version), (name, requirement.name)
    print("compat_metadata_only_count=" + str(len(compat)))
    print("compat_direct_versions=" + json.dumps({k: compat[k].version for k in sorted(optional) if k in compat}))
    pypi_evidence = {}
    for name, version in PINS.items():
        file = args.pypi_dir / f"{name}.json"
        payload = json.loads(file.read_text())
        info = payload["info"]
        assert canonicalize_name(info["name"]) == name and info["version"] == version
        assert SpecifierSet(info["requires_python"]).contains(env["python_full_version"])
        (package,) = [p for p in lock["package"] if p["name"] == name]
        upstream = {item["url"]: item for item in payload["urls"]}
        artifacts = package.get("wheels", []) + ([package["sdist"]] if "sdist" in package else [])
        for artifact in artifacts:
            release_file = upstream[artifact["url"]]
            assert not release_file["yanked"]
            assert artifact["hash"] == "sha256:" + release_file["digests"]["sha256"]
            assert artifact["size"] == release_file["size"]
        if name == "torch":
            assert info["license_expression"] == (
                "Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause "
                "AND BSD-3-Clause AND BSL-1.0 AND MIT"
            )
        else:
            assert info["license"] == ("BSD-3-Clause" if name == "psutil" else "MIT")
        pypi_evidence[name] = {
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            "version": version, "locked_artifacts_checked": len(artifacts),
        }
    print("independent_pypi_evidence=" + json.dumps(pypi_evidence, sort_keys=True))
    summary = json.loads((args.s0_verification / "summary.json").read_text())
    verified = []
    for entry in summary:
        file = args.s0_verification / (entry["name"] + ".log")
        assert hashlib.sha256(file.read_bytes()).hexdigest() == entry["sha256"]
        assert entry["exit_code"] == 0
        verified.append(entry["name"])
    print("s0_raw_log_hashes_checked=" + json.dumps(verified))
    assert "mlx" not in sys.modules and "torch" not in sys.modules and "mlx_lm" not in sys.modules
    print("PASS: default isolation; read-only compatibility metadata/dependency closure; upstream hashes; raw evidence")


if __name__ == "__main__":
    main()
