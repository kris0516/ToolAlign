"""Independent synthetic archive probes for the Mac's detected Git case behavior."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from hatchling.builders.sdist import SdistBuilder

ROOT = Path(__file__).resolve().parents[3]
OLD = "55a330b6a1c10d14959895f2a3617597962569f3"
DIRECTORIES = ("configs", "tests", "src/toolalign")
LOWER = (
    "synthetic.key", "synthetic.pem", "synthetic.pt", "synthetic.safetensors", ".env",
    "private-service-account.json", "fixture/models/private.json",
)
CASE_VARIANTS = (
    "synthetic.KEY", "synthetic.PEM", "synthetic.PT", "synthetic.SAFETENSORS", ".ENV",
    "private-SERVICE-ACCOUNT.JSON", "fixture/MODELS/private.json",
)
PUBLIC = {
    "configs/review-public-r2.json": b'{"synthetic_public": true}\n',
    "tests/review-public-r2.json": b'{"synthetic_public": true}\n',
    "src/toolalign/review_public_r2.py": b'SYNTHETIC_PUBLIC = True\n',
}


def run(args, cwd):
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f"{args[0]} exit={result.returncode}; output_sha256=" + hashlib.sha256(
            result.stdout + result.stderr
        ).hexdigest())
    return result.stdout


def archive_files(path, wheel=False):
    files = {}
    assert path.stat().st_size < 5 * 1024**2
    if wheel:
        with zipfile.ZipFile(path) as archive:
            assert sum(item.file_size for item in archive.infolist()) < 10 * 1024**2
            for name in archive.namelist():
                relative = PurePosixPath(name)
                assert not relative.is_absolute() and ".." not in relative.parts
                files[name] = archive.read(name)
    else:
        with tarfile.open(path, "r:gz") as archive:
            assert sum(item.size for item in archive.getmembers()) < 10 * 1024**2
            for item in archive.getmembers():
                relative = PurePosixPath(item.name)
                assert not relative.is_absolute() and ".." not in relative.parts
                assert not item.issym() and not item.islnk()
                if item.isfile():
                    files[str(PurePosixPath(*relative.parts[1:]))] = archive.extractfile(item).read()
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=("lowercase", "case-variants", "old-control"))
    args = parser.parse_args()
    tracked = run(["git", "ls-files", "-z"], ROOT).decode().split("\0")
    with tempfile.TemporaryDirectory(prefix="r2-case-archives-") as temporary:
        parent = Path(temporary)
        repository = parent / "repository"
        repository.mkdir()
        for name in filter(None, tracked):
            source, destination = ROOT / name, repository / name
            assert source.is_file() and not source.is_symlink()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        run(["git", "init", "-q"], repository)
        run(["git", "add", "."], repository)
        run(["git", "-c", "user.name=Review Fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "--no-gpg-sign", "-qm", "Public synthetic fixture"], repository)
        checkout = parent / ".codex/worktrees/fixture"
        checkout.parent.mkdir(parents=True)
        run(["git", "worktree", "add", "--detach", "-q", str(checkout), "HEAD"], repository)
        assert (checkout / ".git").is_file()
        # Observe the setting detected by Git on this filesystem; never force it.
        ignorecase = run(["git", "config", "--get", "core.ignorecase"], checkout).strip()
        assert ignorecase == b"true", "This probe requires the Mac's case-insensitive filesystem"
        if args.scenario == "old-control":
            (checkout / "pyproject.toml").write_bytes(
                run(["git", "show", f"{OLD}:pyproject.toml"], ROOT)
            )
        marker = b"R2_SYNTHETIC_PRIVATE_" + os.urandom(24)
        names = CASE_VARIANTS if args.scenario == "case-variants" else LOWER
        private = [f"{directory}/{name}" for directory in DIRECTORIES for name in names]
        for name in private:
            path = checkout / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(marker)
            assert run(["git", "check-ignore", "--", name], checkout).strip()
        public = dict(PUBLIC)
        if args.scenario != "old-control":
            public["configs/.env.example"] = b"PUBLIC_DEMO_R2=example\n"
        for name, content in public.items():
            (checkout / name).write_bytes(content)
        # Include every existing public source/config/test file, not just the schema.
        expected = {
            name: (checkout / name).read_bytes() for name in filter(None, tracked)
            if any(name.startswith(directory + "/") for directory in DIRECTORIES)
        } | public
        vcs_count = len(SdistBuilder(str(checkout)).config.load_vcs_exclusion_patterns())
        assert vcs_count == 0
        run(["uv", "run", "--locked", "python", "scripts/check_public_content.py"], checkout)
        artifacts = parent / "artifacts"
        run(["uv", "build", "--sdist", "--out-dir", str(artifacts)], checkout)
        (sdist,) = artifacts.glob("toolalign-*.tar.gz")
        outputs = {"sdist": archive_files(sdist)}
        for route, source in [("wheel-from-sdist", str(sdist)), ("wheel-direct", ".")]:
            destination = artifacts / route
            run(["uv", "build", "--wheel", "--out-dir", str(destination), source], checkout)
            (wheel,) = destination.glob("toolalign-*.whl")
            outputs[route] = archive_files(wheel, wheel=True)
        leaked = {}
        for route, files in outputs.items():
            leaked[route] = sorted(name for name, data in files.items() if marker in data)
            wanted = expected if route == "sdist" else {
                name.removeprefix("src/"): data for name, data in expected.items()
                if name.startswith("src/toolalign/")
            }
            assert all(files.get(name) == data for name, data in wanted.items())
            print(json.dumps({"scenario": args.scenario, "route": route,
                              "git_core_ignorecase": True, "hatch_vcs_rule_count": vcs_count,
                              "ignored_synthetic_inputs": len(private), "public_scan_passed": True,
                              "preserved_public_files": len(wanted), "archive_files": len(files),
                              "synthetic_leaks": leaked[route]}, sort_keys=True), flush=True)
        if args.scenario == "old-control":
            assert "configs/synthetic.key" in leaked["sdist"]
            assert "toolalign/synthetic.pt" in leaked["wheel-direct"]
            print("PASS: original candidate defect reproduced in both archive formats")
        else:
            assert not any(leaked.values()), "Git-ignored synthetic contents entered release archives"
            print("PASS: all three archive routes exclude private probes and preserve public files")


if __name__ == "__main__":
    main()
