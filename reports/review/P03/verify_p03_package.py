"""Bind fresh P03 archives to Git and exercise the installed default CPU package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from audit_p03_evidence import CANDIDATE, archive_check, audit_demo, blob, package_expectations

ROOT = Path(__file__).resolve().parents[3]
PRIVATE = ROOT / ".toolalign-local/review-p03"


def main():
    expected, wheel_expected, generated = package_expectations()
    historical = json.loads((PRIVATE / "historical-audit.json").read_text())["archives"]
    package_name = "toolalign-0.0.1-py3-none-any.whl"
    archives = {}
    for name, path in (
        ("sdist", PRIVATE / "build/toolalign-0.0.1.tar.gz"),
        ("default-wheel", PRIVATE / "build" / package_name),
        ("rebuilt-wheel", PRIVATE / "rebuilt" / package_name),
        ("direct-wheel", PRIVATE / "direct-wheel" / package_name),
    ):
        archives[name] = archive_check(
            path,
            expected if name == "sdist" else wheel_expected,
            {"PKG-INFO"} if name == "sdist" else generated,
        )
        reference = historical[name if name != "direct-wheel" else "default-wheel"]
        assert archives[name] == reference
    workspace = PRIVATE / "package-check"
    workspace.mkdir(exist_ok=False)
    cwd = workspace / "away-from-source"
    cwd.mkdir()
    environment = workspace / "venv"
    python = environment / "bin/python"
    requirements = workspace / "runtime-requirements.txt"
    records = []
    env = {
        key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "PYTHONHOME")
    }

    def run(name, arguments, *, location=cwd):
        command = list(map(str, arguments))
        completed = subprocess.run(
            command,
            cwd=location,
            env=env,
            capture_output=True,
            timeout=60,
        )
        (workspace / (name + ".stdout")).write_bytes(completed.stdout)
        (workspace / (name + ".stderr")).write_bytes(completed.stderr)
        records.append(
            {
                "name": name,
                "command": command,
                "exit_code": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
            }
        )
        print(f"{name}: exit={completed.returncode}", flush=True)
        assert completed.returncode == 0, completed.stderr.decode(errors="replace")
        return completed.stdout.decode()

    run(
        "export-default",
        [
            "uv",
            "export",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--output-file",
            requirements,
        ],
        location=ROOT,
    )
    run("new-environment", ["uv", "venv", "--python", "3.14", environment])
    run(
        "install-hashed-default-dependencies",
        ["uv", "pip", "install", "--python", python, "--require-hashes", "-r", requirements],
    )
    run(
        "install-rebuilt-wheel",
        [
            "uv",
            "pip",
            "install",
            "--python",
            python,
            "--no-deps",
            PRIVATE / "rebuilt" / package_name,
        ],
    )
    run("dependency-consistency", ["uv", "pip", "check", "--python", python])
    assert run(
        "installed-contract", [python, "-I", "-m", "toolalign.cli", "contract-digest"]
    ).strip() == ("ce17b0a5bc4e8363e1d67bf125212444bab1103ddfc0c4e390bef82afce881cb")
    for kind in ("example", "tool", "preference", "run", "trace"):
        fixture = cwd / (kind + ".json")
        fixture.write_bytes(blob(CANDIDATE, "tests/fixtures/contracts/" + kind + ".json"))
        assert "VALID: 1 record(s)" in run(
            "installed-" + kind,
            [python, "-I", "-m", "toolalign.cli", "validate", fixture],
        )
    run("installed-tools-help", [python, "-I", "-m", "toolalign.tools", "--help"])
    registry = json.loads(
        run("installed-registry", [python, "-I", "-m", "toolalign.tools", "registry"])
    )
    assert (
        registry["registry_hash"]
        == "6cf0ff5e0b775068ddd9690e66414eee97725865d520e8df37072bc53d4085b8"
    )
    fixture = cwd / "development.json"
    shutil.copyfile(ROOT / "tests/fixtures/tools/development.json", fixture)
    demo = json.loads(
        run(
            "installed-scripted-demo",
            [
                python,
                "-I",
                "-m",
                "toolalign.tools",
                "demo",
                "--cases",
                fixture,
                "--output",
                workspace / "demo",
            ],
        )
    )
    assert demo["total"] == demo["success"] == 10
    source_hash = hashlib.sha256(blob(CANDIDATE, "src/toolalign/tools/catalog.py")).hexdigest()
    demo_evidence = audit_demo(
        workspace / "demo", json.loads(fixture.read_text())["cases"], source_hash
    )
    code = """
import importlib,importlib.metadata,importlib.util,json,sys
from pathlib import Path
names=['toolalign.tools','toolalign.tools.__main__','toolalign.tools._json',
       'toolalign.tools.catalog','toolalign.tools.executor','toolalign.tools.isolation',
       'toolalign.tools.registry','toolalign.tools.scripted','toolalign.evaluation.harness',
       'toolalign.evaluation.oracles','toolalign.evaluation.oracles.semantic']
for name in names:
    module=importlib.import_module(name)
    assert Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
for name in ('mlx','mlx_lm','torch','transformers'):
    assert name not in sys.modules and importlib.util.find_spec(name) is None
print(json.dumps({'python_version':sys.version.split()[0], 'isolated_flag':sys.flags.isolated,
                  'p03_modules_inside_installed_prefix':names,'model_packages_available':[],
                  'distributions':{p.metadata['Name']:p.version for p in importlib.metadata.distributions()}},sort_keys=True))
"""
    module_evidence = json.loads(run("installed-module-origins", [python, "-I", "-c", code]))
    assert module_evidence["isolated_flag"] == 1
    record = {
        "candidate": CANDIDATE,
        "archives": archives,
        "commands": records,
        "installed_demo": demo_evidence,
        "module_evidence": module_evidence,
        "source_tree_imported_by_installed_commands": False,
        "real_model_backend": "NOT_RUN",
    }
    encoded = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True)
    encoded = encoded.replace(str(ROOT), "<R1_WORKTREE>")
    (workspace / "evidence.json").write_text(encoded + "\n")
    print(
        json.dumps(
            {
                "result": "PASS",
                "subcommands": len(records),
                "archives": archives,
                "installed_demo_counts": demo_evidence["counts"],
                "module_evidence": module_evidence,
                "evidence_sha256": hashlib.sha256((encoded + "\n").encode()).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
