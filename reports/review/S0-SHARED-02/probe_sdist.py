"""Build only small synthetic worktrees; never enumerate or archive private ML inputs."""

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
BASE = "97466a20f599f68c511b9c8a71fe5f2cdfd9ad4b"
ROOT_PRIVATE = (
    ".toolalign-local/source/synthetic.json", "models/synthetic.safetensors",
    "data/raw/synthetic.json", ".venv/synthetic.txt", "unlisted-synthetic.txt",
)
NESTED_PRIVATE = (
    "configs/synthetic.key", "configs/synthetic.pem",
    "tests/synthetic.safetensors", "src/toolalign/synthetic.pt",
)


def run(args, cwd):
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f"{args[0]} exit={result.returncode}; output_sha256=" + hashlib.sha256(
            result.stdout + result.stderr
        ).hexdigest())
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=("plain-old", "app-old", "app-new", "app-new-nested"))
    args = parser.parse_args()
    names = run(["git", "ls-files", "-z"], ROOT).decode().split("\0")
    with tempfile.TemporaryDirectory(prefix="r1-shared02-sdist-") as temporary:
        parent = Path(temporary)
        repository = parent / "repository"
        repository.mkdir()
        # Use only tracked public files. No source weights, environments or raw logs are copied.
        for name in filter(None, names):
            source = ROOT / name
            assert not source.is_symlink()
            destination = repository / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        run(["git", "init", "-q"], repository)
        run(["git", "add", "."], repository)
        run(["git", "-c", "user.name=Review Fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "--no-gpg-sign", "-qm", "Synthetic review"], repository)
        checkout = parent / ("plain" if args.scenario == "plain-old" else ".codex/worktrees/app")
        checkout.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "worktree", "add", "--detach", "-q", str(checkout), "HEAD"], repository)
        assert (checkout / ".git").is_file()
        if args.scenario.endswith("old"):
            for name in ("pyproject.toml", "uv.lock"):
                (checkout / name).write_bytes(run(["git", "show", f"{BASE}:{name}"], ROOT))
        private = NESTED_PRIVATE if args.scenario.endswith("nested") else ROOT_PRIVATE
        marker = b"R1_SYNTHETIC_PRIVATE_" + os.urandom(24)
        for name in private:
            path = checkout / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(marker)
        builder = SdistBuilder(str(checkout))
        pattern_count = len(builder.config.load_vcs_exclusion_patterns())
        if args.scenario.startswith("app"):
            assert pattern_count == 0
        else:
            assert pattern_count > 0
        public_result = None
        if args.scenario.endswith("nested"):
            for name in private:
                assert run(["git", "check-ignore", "--", name], checkout)
            # Ignored nested secrets are absent from the public scanner's candidate list.
            public_result = run(["uv", "run", "--locked", "python", "scripts/check_public_content.py"], checkout)
        archives = parent / "archives"
        run(["uv", "build", "--sdist", "--out-dir", str(archives)], checkout)
        (sdist,) = archives.glob("toolalign-*.tar.gz")
        files, leaked = {}, []
        with tarfile.open(sdist, "r:gz") as archive:
            assert sum(item.size for item in archive.getmembers()) < 5 * 1024**2
            for member in archive.getmembers():
                path = PurePosixPath(member.name)
                assert not path.is_absolute() and ".." not in path.parts
                if not member.isfile():
                    continue
                relative = str(PurePosixPath(*path.parts[1:]))
                data = archive.extractfile(member).read()
                files[relative] = data
                if marker in data:
                    leaked.append(relative)
        result = {
            "scenario": args.scenario, "hatchling_vcs_pattern_count": pattern_count,
            "sdist_files": len(files), "compressed_bytes": sdist.stat().st_size,
            "synthetic_leaks": sorted(leaked),
            "source_scan_passed": public_result is not None,
        }
        print(json.dumps(result, sort_keys=True), flush=True)
        if args.scenario == "plain-old":
            assert leaked == ["unlisted-synthetic.txt"]
        elif args.scenario == "app-old":
            # Hatchling has a built-in .venv exclusion independent of VCS patterns.
            assert set(private) - {".venv/synthetic.txt"} <= set(leaked)
        else:
            assert not leaked, "Private ignored synthetic content entered candidate sdist"
            run(["uv", "build", "--wheel", "--out-dir", str(archives), str(sdist)], checkout)
            (wheel,) = archives.glob("toolalign-*.whl")
            with zipfile.ZipFile(wheel) as archive:
                assert archive.read("toolalign/contracts/v1.json") == files["src/toolalign/contracts/v1.json"]
                assert not any(marker in archive.read(name) for name in archive.namelist())
            print("PASS: rebuilt wheel from synthetic source archive preserves frozen schema")


if __name__ == "__main__":
    main()
