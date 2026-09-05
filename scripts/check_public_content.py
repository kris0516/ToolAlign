"""Scan both staged blobs and working files; supplement independent privacy review."""

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
MAX_BYTES = 1_048_576


def _content_issue(data):
    if len(data) > MAX_BYTES:
        return "oversized file"
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return "binary file requires separate review"
    if SENSITIVE.search(text):
        return "potential secret, local path, or private task ID (value omitted)"
    return None


def main():
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args])

    staged = {}
    for entry in git("ls-files", "--stage", "-z").split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            mode, oid, stage = metadata.decode().split()
            staged.setdefault(name.decode(), []).append((mode, oid, stage))
    untracked = set(
        git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    ) - {""}
    names = set(staged) | untracked
    failures = []
    blob_issues = {}
    for name in sorted(names):
        relative = PurePosixPath(name)
        path = root / name
        label = "[redacted path]" if SENSITIVE.search(name) else repr(name)

        def fail(source, issue):
            failures.append(f"{label} ({source}): {issue}")

        if (
            relative.parts[0] in FORBIDDEN_ROOTS
            or relative.suffix in FORBIDDEN_SUFFIXES
            or relative.name.startswith(".env")
            and relative.name != ".env.example"
            or relative.parts[:2] in {("data", "raw"), ("data", "processed"), ("data", "private")}
        ):
            fail("path", "forbidden public path")
            continue
        if SENSITIVE.search(name):
            fail("path", "potential private path (value omitted)")
        for mode, oid, stage in staged.get(name, []):
            if stage != "0" or mode not in {"100644", "100755"}:
                fail("index", "unmerged, symlink, or unsupported Git entry")
                continue
            if oid not in blob_issues:
                size = int(git("cat-file", "-s", oid))
                blob_issues[oid] = (
                    "oversized file"
                    if size > MAX_BYTES
                    else _content_issue(git("cat-file", "blob", oid))
                )
            if blob_issues[oid]:
                fail("index", blob_issues[oid])
        # Never follow a working-tree symlink, including a substituted parent directory.
        if any(
            (root.joinpath(*relative.parts[:i])).is_symlink()
            for i in range(1, len(relative.parts) + 1)
        ):
            fail("working tree", "symlink requires separate review")
            continue
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            fail("working tree", "missing or oversized file")
        else:
            issue = _content_issue(path.read_bytes())
            if issue:
                fail("working tree", issue)
    if failures:
        print("\n".join(failures))
        return 1
    print(
        f"PASS: {len(names)} paths scanned in index and working tree; heuristic check, not a privacy guarantee"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
