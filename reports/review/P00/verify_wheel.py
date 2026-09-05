"""Install the already built candidate wheel into a temporary, isolated CPU venv."""

import hashlib
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run(name, args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
    print(f"{name}: exit={result.returncode}", flush=True)
    if result.returncode:
        print(result.stdout + result.stderr, flush=True)
        raise SystemExit(result.returncode)
    return result.stdout


def main():
    (wheel,) = (ROOT / "dist").glob("toolalign-*.whl")
    schema_digest = hashlib.sha256(
        (ROOT / "src/toolalign/contracts/v1.json").read_bytes()
    ).hexdigest()
    with zipfile.ZipFile(wheel) as package:
        assert hashlib.sha256(package.read("toolalign/contracts/v1.json")).hexdigest() == (
            schema_digest
        )
        assert all(
            not name.startswith(("tests/", "reports/", ".toolalign-local/"))
            for name in package.namelist()
        )
    print("wheel_sha256=" + hashlib.sha256(wheel.read_bytes()).hexdigest(), flush=True)
    with tempfile.TemporaryDirectory(prefix="toolalign-wheel-review-") as directory:
        temporary = Path(directory)
        requirements = temporary / "runtime.txt"
        environment = temporary / "venv"
        python = environment / "bin/python"
        run(
            "export",
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--output-file",
                str(requirements),
            ],
            ROOT,
        )
        run("venv", ["uv", "venv", "--python", "3.14", str(environment)], temporary)
        run(
            "dependencies",
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--require-hashes",
                "-r",
                str(requirements),
            ],
            temporary,
        )
        run(
            "wheel-install",
            ["uv", "pip", "install", "--python", str(python), "--no-deps", str(wheel)],
            temporary,
        )
        run("dependency-check", ["uv", "pip", "check", "--python", str(python)], temporary)
        digest = run(
            "installed-digest",
            [str(python), "-I", "-m", "toolalign.cli", "contract-digest"],
            temporary,
        ).strip()
        assert digest == schema_digest
        for kind in ("example", "tool", "preference", "run", "trace"):
            result = run(
                "validate-" + kind,
                [
                    str(environment / "bin/toolalign"),
                    "validate",
                    str(ROOT / "tests/fixtures/contracts" / f"{kind}.json"),
                ],
                temporary,
            )
            assert "VALID: 1 record(s)" in result
        output = run(
            "no-source-no-ml",
            [
                str(python),
                "-I",
                "-c",
                "import importlib.util, pathlib, sys, toolalign; "
                "assert pathlib.Path(toolalign.__file__).is_relative_to(sys.prefix); "
                "assert importlib.util.find_spec('mlx') is None; "
                "assert importlib.util.find_spec('torch') is None; "
                "print(sys.version.split()[0])",
            ],
            temporary,
        )
        print("isolated_python=" + output.strip(), flush=True)
    print("PASS: wheel schema, console CLI, dependency closure, isolated imports, no ML backends")


if __name__ == "__main__":
    main()
