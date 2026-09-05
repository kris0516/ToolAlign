"""Scan publishable Git paths only; heuristics supplement a human/independent review."""

import re
import subprocess
from pathlib import Path, PurePosixPath

FORBIDDEN_ROOTS = {
    ".toolalign-local",
    ".venv",
    ".codex",
    "models",
    "checkpoints",
    "adapters",
    "artifacts",
    "runs",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".safetensors", ".gguf", ".pt", ".pth", ".bin"}
SENSITIVE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"/Users/[A-Za-z0-9._-]+/|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)


def main():
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    names = set(
        subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
        )
        .decode()
        .split("\0")
    ) - {""}
    failures = []
    for name in sorted(names):
        relative = PurePosixPath(name)
        path = root / name
        if (
            relative.parts[0] in FORBIDDEN_ROOTS
            or relative.suffix in FORBIDDEN_SUFFIXES
            or relative.name.startswith(".env")
            and relative.name != ".env.example"
            or relative.parts[:2] in {("data", "raw"), ("data", "processed"), ("data", "private")}
        ):
            failures.append(f"{name}: forbidden public path")
            continue
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_048_576:
            failures.append(f"{name}: symlink, missing, or oversized file")
            continue
        try:
            data = path.read_text(encoding="utf-8")
        except UnicodeError:
            failures.append(f"{name}: binary file requires separate review")
            continue
        if SENSITIVE.search(data):
            failures.append(
                f"{name}: potential secret, local path, or private task ID (value omitted)"
            )
    if failures:
        print("\n".join(failures))
        return 1
    print(f"PASS: {len(names)} publishable files scanned; heuristic check, not a privacy guarantee")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
