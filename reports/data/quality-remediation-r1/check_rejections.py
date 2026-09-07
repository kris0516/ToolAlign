"""Exercise the fixed public build boundary against private input replacements.

Only new copies are altered. Each rejected CLI call retains its exact arguments,
output, timestamps and exit code; neither old inputs nor producers are patched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    original = json.loads(args.inputs.read_text())
    out = args.output.resolve()
    assert ".toolalign-local" in out.parts and not out.exists()
    out.mkdir(parents=True, mode=0o700)
    cases = []
    for key in ("config_path", "data_manifest_path", "selection_manifest_path",
                "training_config_path", "audit_path", "raw_source_path", "source_policy_path"):
        path = out / (key + ".replacement")
        data = Path(original[key]).read_bytes() if key not in {"audit_path", "raw_source_path"} else b"{}\n"
        path.write_bytes(data + b"\n")
        cases.append((key, key, path))
    for name in ("seal.json", "semantic_review_ai.csv", "remediation_proposal.json", "reannotation_drafts.json"):
        root = out / ("review-" + name)
        root.mkdir()
        if name == "seal.json":
            selected = [Path(original["review_root"]) / name]
        else:
            selected = [p for p in Path(original["review_root"]).iterdir() if p.is_file()]
        for source in selected:
            assert not source.is_symlink()
            shutil.copyfile(source, root / source.name)
        path = root / name
        path.write_bytes(path.read_bytes() + b"\n")
        cases.append(("review-" + name, "review_root", root))
    token_root = out / "token-materials"
    shutil.copytree(original["token_review_root"], token_root)
    token_csv = token_root / "review.csv"
    token_csv.write_bytes(token_csv.read_bytes() + b"\n")
    cases.append(("token-review-csv", "token_review_root", token_root))
    results = []
    env = os.environ.copy()
    env.update(USE_TORCH="0", USE_TF="0", USE_FLAX="0", HF_HUB_OFFLINE="1",
               TRANSFORMERS_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    for label, key, path in cases:
        modified = {**original, key: str(path)}
        destination = out / (label + "-must-not-publish")
        argv = [sys.executable, "-B", "-m", "toolalign.data.quality_revision", "build"]
        argv += [v for k, value in modified.items() for v in ("--" + k.replace("_", "-"), value)]
        argv += ["--output", str(destination)]
        start = datetime.now(timezone.utc).isoformat()
        done = subprocess.run(argv, env=env, capture_output=True, timeout=60)
        record = {"label": label, "argv": argv, "started_at_utc": start,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(), "exit_code": done.returncode,
            "stdout_sha256": sha(done.stdout), "stderr_sha256": sha(done.stderr),
            "output_directory_created": destination.exists()}
        for suffix, data in (("stdout", done.stdout), ("stderr", done.stderr)):
            (out / (label + "." + suffix)).write_bytes(data)
        (out / (label + ".command.json")).write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
        assert done.returncode == 1 and not destination.exists(), label
        failure = json.loads(done.stdout)
        assert failure == {"status": "FAIL", "error_type": "DataError", "error_code": "input_hash_mismatch"}, label
        results.append(record)
    result = {"status": "PASS_REPLACEMENTS_REJECTED", "negative_cli_calls": len(results),
              "producer_patches": 0, "old_input_writes": 0, "commands": results}
    (out / "summary.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "commands"}))


if __name__ == "__main__":
    main()
