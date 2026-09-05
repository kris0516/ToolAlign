"""Check the exact schema, validator, interface and config bytes in the frozen bundle."""

import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "contracts.v1.lock.json").read_text())
    failures = [
        name
        for name, digest in manifest["files"].items()
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest
    ]
    if failures:
        print("FAIL: frozen contract changed: " + ", ".join(failures))
        return 1
    print(f"PASS: {manifest['contract_version']} ({len(manifest['files'])} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
