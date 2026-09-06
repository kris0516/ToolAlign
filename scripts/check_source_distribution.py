"""Check real sdist and wheel bytes from an App-style synthetic Git worktree."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CANARY = b"TOOLALIGN_PRIVATE_BUILD_CANARY_" + os.urandom(16)
PRIVATE_PATHS = (
    ".toolalign-local/source/record.json",
    ".toolalign-local/models/weights.safetensors",
    ".venv/private-build-marker.txt",
    "models/private-build-marker.txt",
    "data/raw/private-build-marker.json",
    "unlisted-private-build-marker.txt",
    "src/toolalign/__pycache__/private-build-marker.pyc",
) + tuple(
    f"{directory}/{relative}"
    for directory in ("configs", "tests", "src/toolalign")
    for relative in (
        "private-build-marker.key", "private-build-marker.pem",
        "private-service-account.json", ".env", ".env.private-build-marker",
        "private-build-marker.safetensors", "private-build-marker.gguf",
        "private-build-marker.pt", "private-build-marker.pth", "private-build-marker.bin",
        "private-build-marker.onnx", "private-build-marker.log",
        "private-build-marker.mlpackage/record.json",
        "private-build-marker.mlmodelc/record.json",
        ".toolalign-local/private-build-marker.json", "models/private-build-marker.json",
        "checkpoints/private-build-marker.json", "adapters/private-build-marker.json",
        "artifacts/private-build-marker.json", "runs/private-build-marker.json",
        ".venv/private-build-marker.json", "venv/private-build-marker.json",
        "node_modules/private-build-marker.json", "build/private-build-marker.json",
        "dist/private-build-marker.json", "nested/.env.private-build-marker",
    )
)


def run(args: list[str], cwd: Path) -> bytes:
    env = os.environ | {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    result = subprocess.run(
        args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=60, check=False,
    )
    if result.returncode:
        # Build logs may contain local paths; report the command class and hash only.
        raise RuntimeError(
            f"{args[0]} failed: exit={result.returncode}, "
            f"output_sha256={hashlib.sha256(result.stdout).hexdigest()}"
        )
    return result.stdout


def main() -> None:
    tracked = run(["git", "ls-files", "-z"], ROOT).decode().split("\0")
    with tempfile.TemporaryDirectory(prefix="toolalign-sdist-check-") as temporary:
        parent = Path(temporary)
        repository = parent / "repository"
        # App-managed worktrees live under .codex. Hatchling 1.27 drops VCS
        # exclusions when a project's absolute root matches its own .codex/ rule.
        checkout = parent / ".codex" / "worktrees" / "checkout"
        repository.mkdir()
        for relative in filter(None, tracked):
            source, destination = ROOT / relative, repository / relative
            if source.is_symlink():
                raise AssertionError("Tracked symlink cannot enter the packaging fixture")
            if source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
        run(["git", "init", "-q"], repository)
        run(["git", "add", "."], repository)
        run([
            "git", "-c", "user.name=ToolAlign Packaging Check",
            "-c", "user.email=packaging-check@example.invalid",
            "commit", "--no-gpg-sign", "-qm", "Packaging fixture",
        ], repository)
        checkout.parent.mkdir(parents=True)
        run(["git", "worktree", "add", "--detach", "-q", str(checkout), "HEAD"], repository)
        assert (checkout / ".git").is_file(), "The regression requires a Git worktree"
        for relative in PRIVATE_PATHS:
            path = checkout / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(CANARY)

        archives = parent / "archives"
        run(["uv", "build", "--sdist", "--out-dir", str(archives)], checkout)
        (sdist,) = archives.glob("toolalign-*.tar.gz")
        assert sdist.stat().st_size < 10 * 1024**2, "Unexpected source archive size"
        files: dict[str, bytes] = {}
        leaked: list[str] = []
        with tarfile.open(sdist, "r:gz") as archive:
            members = archive.getmembers()
            assert sum(member.size for member in members) < 25 * 1024**2
            for member in members:
                path = PurePosixPath(member.name)
                assert not path.is_absolute() and ".." not in path.parts
                assert not member.issym() and not member.islnk()
                if not member.isfile():
                    continue
                relative = str(PurePosixPath(*path.parts[1:]))
                stream = archive.extractfile(member)
                assert stream is not None
                content = stream.read()
                if CANARY in content or relative in PRIVATE_PATHS:
                    leaked.append(relative)
                files[relative] = content

        assert not leaked, f"Source archive contains private build canaries: {sorted(leaked)}"

        frozen_schema = (ROOT / "src/toolalign/contracts/v1.json").read_bytes()
        assert files["src/toolalign/contracts/v1.json"] == frozen_schema
        for required in ("pyproject.toml", "LICENSE", "README.md", "configs/protocol.v1.json"):
            assert required in files
        # A clean sdist alone cannot prove a direct wheel build excludes ignored
        # files inside src/toolalign; exercise both build inputs independently.
        for label, source in (("from-sdist", str(sdist)), ("from-worktree", ".")):
            destination = archives / label
            run(["uv", "build", "--wheel", "--out-dir", str(destination), source], checkout)
            (wheel,) = destination.glob("toolalign-*.whl")
            assert wheel.stat().st_size < 10 * 1024**2
            with zipfile.ZipFile(wheel) as archive:
                assert sum(item.file_size for item in archive.infolist()) < 25 * 1024**2
                for name in archive.namelist():
                    assert CANARY not in archive.read(name), (
                        f"{label} wheel contains a private build canary"
                    )
                assert archive.read("toolalign/contracts/v1.json") == frozen_schema
        print(
            f"PASS: App-style .codex Git-worktree archives exclude {len(PRIVATE_PATHS)} "
            "private canaries, including files inside allowed trees; "
            f"files={len(files)}, compressed_bytes={sdist.stat().st_size}; "
            "direct and rebuilt wheels preserve the frozen schema"
        )


if __name__ == "__main__":
    main()
