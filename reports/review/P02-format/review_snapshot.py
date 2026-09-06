"""Deterministic filesystem interleaving; real, unpatched tokenizer loader.

Only private copied source files change. Python audit events coordinate a source
replacement after the adapter reads its verified snapshot, and restoration before
the HF adapter's final path recheck. No tokenizer method, library return value,
identity property or expected hash is mocked. This models a concurrent directory
update without timing-dependent sleeps or races with unrelated work.
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

from review_support import REVISIONS, assert_cpu, cpu_only, read_json, sha, source_check, write_json
from review_tokenizers import loaded_state


def run(args):
    from toolalign.model_io import ModelIOError
    from toolalign.model_io.offline import OfflineQwenTokenizer

    source_check(args.source)
    target = args.out / "source"
    shutil.copytree(args.source, target)
    repo, revision = next(iter(REVISIONS.items()))

    def construct():
        return OfflineQwenTokenizer(target, repo_id=repo, revision=revision, engine=args.engine)

    baseline = construct()
    before = loaded_state(baseline)
    original = (target / "tokenizer.json").read_bytes()
    changed = json.loads(original)
    vocab = changed["model"]["vocab"]
    old_ids = {token: vocab[token] for token in ("!", "?")}
    vocab["!"], vocab["?"] = vocab["?"], vocab["!"]
    # Preserve the exact original serialization and total byte length, so the
    # final stat() remains a valid control for a same-size source replacement.
    changed_bytes = original
    for token, ident in old_ids.items():
        pattern = re.compile(rb'("' + re.escape(token.encode()) + rb'"\s*:\s*)' + str(ident).encode() + rb'(?=\s*[,}])')
        changed_bytes, count = pattern.subn(lambda m: m[1] + str(vocab[token]).encode(), changed_bytes)
        assert count == 1
    assert len(changed_bytes) == len(original) and json.loads(changed_bytes) == changed
    replacement = args.out / "replacement.json"
    restored = args.out / "restored.json"
    replacement.write_bytes(changed_bytes)
    restored.write_bytes(original)
    tokenizer_path = (target / "tokenizer.json").resolve()
    license_path = (target / "LICENSE").resolve()
    events, flags = [], {"active": True, "changed": False, "restored": False, "json_reads": 0}

    def audit(event, values):
        if not flags["active"] or event != "open" or not isinstance(values[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(values[0])).absolute()
        if path == tokenizer_path:
            flags["json_reads"] += 1
            events.append("tokenizer_json_read_" + str(flags["json_reads"]))
            if flags["json_reads"] == 3:
                os.replace(restored, tokenizer_path)
                flags["restored"] = True
                events.append("restore_before_final_hash_read")
        if path == license_path and not flags["changed"]:
            # _source_bytes reads tokenizer JSON/config before LICENSE. Those
            # two verified buffers already exist when this event is emitted.
            os.replace(replacement, tokenizer_path)
            flags["changed"] = True
            events.append("replace_after_verified_json_snapshot")

    sys.addaudithook(audit)
    adapter, rejection = None, None
    try:
        adapter = construct()
    except ModelIOError as exc:
        rejection = str(exc)
    finally:
        flags["active"] = False
        if not flags["restored"]:
            os.replace(restored, tokenizer_path)
            flags["restored"] = True
    assert flags["changed"] and flags["restored"]
    source_check(target)
    actual = loaded_state(adapter) if adapter else None
    wrong_binding = adapter is not None and adapter.identity == baseline.identity and actual != before
    result = {
        "status": "FAIL" if wrong_binding else "PASS", "engine": args.engine,
        "source_before_after_hashes": source_check(target), "filesystem_events": events,
        "original_token_ids": old_ids, "replacement_sha256": sha(changed_bytes),
        "source_restored": True, "rejection": rejection,
        "declared_identity_equal": adapter.identity == baseline.identity if adapter else None,
        "actual_loaded_state_equal": actual == before if adapter else None,
        "baseline_actual_state": before, "observed_actual_state": actual,
        "baseline_exclamation_ids": baseline.encode("!", add_special_tokens=False),
        "observed_exclamation_ids": adapter.encode("!", add_special_tokens=False) if adapter else None,
        "baseline_identity": baseline.identity, "observed_identity": adapter.identity if adapter else None,
        "loader_methods_and_return_values_patched": False, "model_modules_loaded": [],
    }
    assert_cpu()
    write_json(args.out / "result.json", result)
    print(json.dumps({k: result[k] for k in ("status", "engine", "filesystem_events", "rejection", "declared_identity_equal", "actual_loaded_state_equal", "baseline_exclamation_ids", "observed_exclamation_ids")}))
    if wrong_binding:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--engine", choices=("tokenizers", "transformers"), required=True)
    args = parser.parse_args()
    cpu_only()
    args.source = args.source.resolve()
    args.out = args.out.resolve()
    args.out.mkdir(exist_ok=False)
    run(args)
