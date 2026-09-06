"""Real filesystem neighbors of F1; no tokenizer method or identity replacement.

Cleanup faults touch only this process's newly created private snapshot. They
exercise exception paths, not a same-user OS adversary guarantee.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "P02-format"))

from review_support import (  # noqa: E402
    REVISIONS,
    SOURCE_HASHES,
    assert_cpu,
    cpu_only,
    read_json,
    sha,
    source_check,
    value_sha,
    write_json,
)
from review_tokenizers import loaded_state  # noqa: E402

COMMON = ("post_cleanup", "different_size_update", "config_update", "all_extra_files")
REFERENCE_ONLY = ("write_error", "load_error", "template_error")


def exercise(adapter, root):
    from toolalign.model_io import prompt_messages
    from toolalign.tools._json import parse_action

    sys.path.insert(0, str(root / "tests/model_io"))
    from model_io_cases import cases

    records = []
    for name, example in cases():
        model_input = {k: example[k] for k in ("messages", "tools")}
        prompt = adapter.render(
            prompt_messages(model_input), tools=None,
            enable_thinking=False, add_generation_prompt=True,
        )
        sequence = adapter.training_sequence(example)
        assert sequence.prompt_text == prompt
        completion_ids = sequence.sequence_ids[len(sequence.prompt_ids):-1]
        assert adapter.decode(completion_ids, skip_special_tokens=False) == sequence.completion_text
        assert adapter.encode(prompt + sequence.completion_text, add_special_tokens=False) == list(sequence.sequence_ids[:-1])
        assert parse_action(sequence.completion_text) == example["expected_action"]
        records.append({"name": name, "sequence": value_sha(sequence.record())})
    return {"state": loaded_state(adapter), "records": records}


def child(args):
    from toolalign.model_io import ModelIOError
    from toolalign.model_io.offline import OfflineQwenTokenizer

    target = args.out / "owned-source"
    target.mkdir(parents=True)
    for name in SOURCE_HASHES:
        shutil.copyfile(args.source / name, target / name)
    assert source_check(target) == SOURCE_HASHES
    original = {name: (target / name).read_bytes() for name in SOURCE_HASHES}
    repo, revision = next(iter(REVISIONS.items()))

    def construct():
        return OfflineQwenTokenizer(target, repo_id=repo, revision=revision, engine=args.engine)

    baseline = construct()
    baseline_result = exercise(baseline, args.root)
    if args.scenario == "all_extra_files":
        extras = {
            "added_tokens.json": '{"ForeignSnapshotToken":151669}',
            "special_tokens_map.json": '{"eos_token":"ForeignSnapshotToken"}',
            "vocab.json": '{"ForeignSnapshotToken":0}',
            "merges.txt": "#version: 0.2\n",
            "chat_template.jinja": "ForeignSnapshotTemplate",
            "additional_chat_templates/foreign.jinja": "ForeignSnapshotNamedTemplate",
            "config.json": '{"model_type":"bert","tokenizer_class":"BertTokenizer"}',
        }
        for name, text in extras.items():
            path = target / name
            path.parent.mkdir(exist_ok=True)
            path.write_text(text)

    snapshots, snapshot_reads, events, source_extra_opens = [], [], [], []
    flags = {"active": True, "inside": False, "fault": False, "operations": False}
    source_operation_opens = []

    def audit(event, values):
        if not flags["active"] or flags["inside"]:
            return
        flags["inside"] = True
        try:
            if event == "tempfile.mkdtemp":
                path = Path(os.fsdecode(values[0])).resolve()
                if path.name.startswith("toolalign-qwen-tokenizer-"):
                    snapshots.append(path)
                    events.append("fresh_snapshot_created")
                return
            if event != "open" or not isinstance(values[0], (str, bytes, os.PathLike)):
                return
            path = Path(os.fsdecode(values[0])).resolve()
            reading = isinstance(values[1], str) and "r" in values[1]
            if path.is_relative_to(target) and reading:
                if flags["operations"]:
                    source_operation_opens.append(str(path.relative_to(target)))
                if str(path.relative_to(target)) not in SOURCE_HASHES:
                    source_extra_opens.append(str(path.relative_to(target)))
            if path == target / "LICENSE" and reading and not flags["fault"]:
                if args.scenario == "different_size_update":
                    (target / "tokenizer.json").write_bytes(original["tokenizer.json"] + b"\n")
                    flags["fault"] = True
                    events.append("source_size_changed_after_verified_json")
                elif args.scenario == "config_update":
                    config = json.loads(original["tokenizer_config.json"])
                    config["chat_template"] = "unverified updated source template"
                    (target / "tokenizer_config.json").write_text(json.dumps(config))
                    flags["fault"] = True
                    events.append("source_config_changed_after_verified_config")
            if path.parent not in snapshots or path.name != "tokenizer_config.json":
                return
            if not reading and args.scenario == "write_error" and not flags["fault"]:
                path.mkdir()
                flags["fault"] = True
                events.append("exclusive_config_write_failed_on_directory")
                return
            if not reading:
                return
            names = sorted(p.name for p in path.parent.iterdir())
            digests = {name: sha((path.parent / name).read_bytes()) for name in SOURCE_HASHES}
            snapshot_reads.append({
                "names": names, "hashes": digests,
                "directory_mode": path.parent.stat().st_mode & 0o777,
                "file_modes": {name: (path.parent / name).stat().st_mode & 0o777 for name in SOURCE_HASHES},
            })
            if not flags["fault"] and args.scenario in {"load_error", "template_error"}:
                path.chmod(0o600)
                if args.scenario == "load_error":
                    path.write_bytes(b"{")
                    events.append("actual_hf_config_json_read_error")
                else:
                    config = read_json(path)
                    config["chat_template"] = "valid JSON, mismatching loaded template"
                    path.write_text(json.dumps(config))
                    events.append("actual_hf_loaded_template_rejection")
                path.chmod(0o400)
                flags["fault"] = True
        finally:
            flags["inside"] = False

    sys.addaudithook(audit)
    adapter, error = None, None
    try:
        try:
            adapter = construct()
        except ModelIOError as exc:
            error = str(exc)
        assert all(not path.exists() for path in snapshots), "snapshot_leaked"
        if args.engine == "transformers":
            assert len(snapshots) == 1
            if args.scenario != "write_error":
                assert snapshot_reads
                assert snapshot_reads[0] == {
                    "names": sorted(SOURCE_HASHES), "hashes": SOURCE_HASHES,
                    "directory_mode": 0o500,
                    "file_modes": {name: 0o400 for name in SOURCE_HASHES},
                }
        else:
            assert not snapshots
        assert not source_extra_opens
        if args.scenario in REFERENCE_ONLY:
            assert flags["fault"] and adapter is None
            expected_error = (
                "loaded_tokenizer_source_mismatch" if args.scenario == "template_error"
                else "tokenizer_reference_snapshot_load_failed"
            )
            assert error == expected_error
            actual = None
        else:
            assert error is None and adapter is not None
            if args.scenario in {"different_size_update", "config_update"}:
                assert flags["fault"]
            assert adapter.identity == baseline.identity
            # Delete only the new source copy. All public adapter operations now
            # run after both the source copy and HF snapshot have disappeared.
            shutil.rmtree(target)
            flags["operations"] = True
            actual = exercise(adapter, args.root)
            assert actual == baseline_result
            assert exercise(adapter, args.root) == actual
            assert not source_operation_opens
    finally:
        flags["active"] = False
    assert_cpu()
    modules = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            path = Path(module.__file__).resolve()
            base = args.target.resolve() if args.target else args.root.resolve() / "src"
            assert path.is_relative_to(base), name
            modules[name] = str(path.relative_to(base))
    result = {
        "status": "PASS", "scenario": args.scenario, "engine": args.engine,
        "loader_methods_return_values_identity_or_hashes_patched": False,
        "fault_scope": "owned files only; cleanup fault injection is not an OS isolation claim",
        "source_extra_file_opens": source_extra_opens,
        "post_cleanup_source_opens": source_operation_opens,
        "source_and_snapshot_absent_during_successful_operations": actual is not None,
        "actual_state_and_12_fixtures_equal": actual == baseline_result if actual else None,
        "baseline_actual_state": baseline_result["state"], "error": error,
        "events": events, "snapshot_count": len(snapshots), "snapshots_removed": True,
        "verified_snapshot_first_read": snapshot_reads[:1], "toolalign_modules": modules,
        "toolalign_origin": "installed_target" if args.target else "candidate_src",
        "model_modules_loaded": [],
    }
    write_json(args.out / "result.json", result)
    print(json.dumps({k: result[k] for k in (
        "status", "engine", "scenario", "error", "snapshot_count", "snapshots_removed",
        "actual_state_and_12_fixtures_equal", "source_extra_file_opens",
    )}))


def main(args):
    cpu_only()
    args.root, args.source, args.out = args.root.resolve(), args.source.resolve(), args.out.resolve()
    if args.target:
        assert sys.flags.isolated
        args.target = args.target.resolve()
        sys.path.insert(0, str(args.target))
    if args.scenario:
        child(args)
        return
    args.out.mkdir(exist_ok=False, parents=True)
    results = []
    scenarios = COMMON + (REFERENCE_ONLY if args.engine == "transformers" else ())
    for scenario in scenarios:
        cmd = [sys.executable, "-B", str(Path(__file__).resolve()), "--root", str(args.root),
               "--source", str(args.source), "--out", str(args.out / scenario),
               "--engine", args.engine, "--scenario", scenario]
        done = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
        (args.out / (scenario + ".stdout")).write_bytes(done.stdout)
        (args.out / (scenario + ".stderr")).write_bytes(done.stderr)
        command = {"argv": cmd, "exit_code": done.returncode,
                   "stdout_sha256": sha(done.stdout), "stderr_sha256": sha(done.stderr)}
        write_json(args.out / (scenario + ".command.json"), command)
        assert done.returncode == 0, (scenario, done.stdout.decode(), done.stderr.decode())
        results.append(read_json(args.out / scenario / "result.json"))
    write_json(args.out / "result.json", {"status": "PASS", "engine": args.engine, "scenarios": results})
    print(json.dumps({"status": "PASS", "engine": args.engine, "scenario_executions": len(results)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("root", "source", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--engine", choices=("tokenizers", "transformers"), required=True)
    parser.add_argument("--scenario", choices=COMMON + REFERENCE_ONLY)
    parser.add_argument("--target", type=Path)
    main(parser.parse_args())
