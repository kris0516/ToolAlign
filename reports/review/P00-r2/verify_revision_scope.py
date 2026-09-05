"""Read-only checks for exact review ancestry, preserved evidence and bounded r2 changes."""

import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "0f152e287bbc0e1c3edfb3f6f3794eb8d36c422f"
OLD = "15706079c9516197b67dd59a19a0d0c4aa5adea8"
CANDIDATE = "5d30e1b4bd5e2284abbe59a5f16b2966f85feb87"
FIRST_REVIEW = "66521f8aad1a2ed529660b18aa099208c2e0bb09"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def blob(revision, path):
    return git("show", f"{revision}:{path}")


def without_patterns(node):
    if isinstance(node, dict):
        return {key: without_patterns(value) for key, value in node.items() if key != "pattern"}
    if isinstance(node, list):
        return [without_patterns(value) for value in node]
    return node


def main():
    for ancestor in (BASE, OLD):
        git("merge-base", "--is-ancestor", ancestor, CANDIDATE)
    print("PASS: base and first candidate are ancestors of exact r2 candidate")
    changed = git("diff", "--name-only", OLD, CANDIDATE, "--", "src").decode().splitlines()
    assert set(changed) == {
        "src/toolalign/contracts/validation.py", "src/toolalign/contracts/v1.json"
    }
    for name in ("uv.lock", "pyproject.toml", "configs/protocol.v1.json"):
        assert blob(OLD, name) == blob(CANDIDATE, name)
    schema = "src/toolalign/contracts/v1.json"
    assert without_patterns(json.loads(blob(OLD, schema))) == without_patterns(
        json.loads(blob(CANDIDATE, schema))
    )
    print("PASS: only validator/schema changed under src; wire structure/interfaces/lock/deps intact")
    for name in (
        "coordination/handoffs/P00-review-r1.md", "reports/review/P00/README.md",
        "reports/review/P00/test_independent.py", "reports/review/P00/verify_wheel.py",
    ):
        assert blob(FIRST_REVIEW, name) == blob(CANDIDATE, name)
    tests = "tests/contracts/test_records.py"
    assert blob(CANDIDATE, tests).startswith(blob(OLD, tests))
    print("PASS: original R1 evidence/probes preserved byte-for-byte; existing contract tests retained")
    manifest = json.loads(blob(CANDIDATE, "contracts.v1.lock.json"))
    for name, expected in manifest["files"].items():
        assert hashlib.sha256(blob(CANDIDATE, name)).hexdigest() == expected
        assert (ROOT / name).read_bytes() == blob(CANDIDATE, name)
    packages = tomllib.loads(blob(CANDIDATE, "uv.lock").decode())["package"]
    assert not {p["name"] for p in packages} & {"mlx", "torch", "mlx-lm", "pytorch"}
    for package in packages:
        if "registry" in package["source"]:
            assert package["source"]["registry"] == "https://pypi.org/simple"
        for distribution in ([package["sdist"]] if "sdist" in package else []) + package.get(
            "wheels", []
        ):
            assert distribution["hash"].startswith("sha256:")
            assert len(distribution["hash"]) == 71
    print("PASS: exact candidate freeze hashes and current contract bytes match; PyPI hashes/no ML")
    print("candidate=" + CANDIDATE)
    print("schema_sha256=" + hashlib.sha256(blob(CANDIDATE, schema)).hexdigest())


if __name__ == "__main__":
    main()
