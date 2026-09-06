"""Read-only byte/epoch audit of the precise native-toy candidate and original receipts."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

CANDIDATE = "f7326d1823c4cf132ae44525f4755c96c88ec159"
BASE = "50867c0be43d110df6c3620c94022fcfdaf779b5"
NUMERIC = "534445bb8eecd600b65e90e541cd30601b4fd07c"
DELIVERY = "e3145eafd84eef3a8f316f8fb8a4f4a124b4a6662ca12796987fc0365bc9203b"
FINAL = "5a266eac20dd5e44db90b23711ca580b624d7cf071462c6da0e6fac6056eb1e0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode())


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, old = Path.cwd(), args.t1.resolve()
    t1_repo = old.parents[1]

    def git(*argv):
        return subprocess.check_output(["git", *argv], cwd=root)

    def source(commit):
        return {name: sha(git("show", commit + ":" + name)) for name in
                git("ls-tree", "-r", "--name-only", commit).decode().splitlines()}

    def read(name):
        return json.loads((old / name).read_text())

    def check_files(base, entries):
        for name, expected in entries.items():
            path = base / name
            assert not path.is_symlink() and path.is_file(), name
            assert {"sha256": sha(path.read_bytes()), "size_bytes": path.stat().st_size} == expected, name
        return len(entries)

    assert sha((old / "delivery.json").read_bytes()) == DELIVERY
    assert sha((old / "FINAL_FILES.json").read_bytes()) == FINAL
    delivery, final, measurement = read("delivery.json"), read("FINAL_FILES.json"), read("MEASUREMENT_FILES.json")
    assert delivery["candidate"] == final["candidate"] == CANDIDATE
    candidate, base = source(CANDIDATE), source(BASE)
    assert len(candidate) == 408 and len(base) == 401
    changed = {name: digest for name, digest in candidate.items() if base.get(name) != digest}
    assert len(changed) == 9 and not set(base) - set(candidate)
    assert changed == delivery["changed_files"]
    assert all(sha((root / name).read_bytes()) == digest for name, digest in candidate.items())
    assert len([name for name in base if candidate[name] == base[name]]) == 399
    assert git("show", "-s", "--format=%T %P", CANDIDATE).decode().strip() == (
        "247eba004d714def81f0bef65375ddbf0fee95cf c06782a61857259097932078c661189b4fda781d")
    counts = {"final_files": check_files(old, final["files"]),
              "measurement_files": check_files(old, measurement["files"]),
              "preserved_t1_files": check_files(t1_repo, read("preservation-before.json")["files"])}
    assert counts == {"final_files": 3038, "measurement_files": 3016, "preserved_t1_files": 1559}
    for name, expected in final["links"].items():
        path = old / name
        assert path.is_symlink() and os.readlink(path) == expected["target"], name
        assert sha(os.readlink(path).encode()) == expected["target_bytes_sha256"], name
    counts["symlinks_no_target_following"] = len(final["links"])
    assert counts["symlinks_no_target_following"] == 197
    for ref, commit in read("preservation-before.json")["refs"].items():
        assert git("rev-parse", ref).decode().strip() == commit
    assert sha((old / "MEASUREMENT_FILES.json").read_bytes()) == delivery["measurement_manifest_sha256"]
    assert sha((root / "reports/experiments/P04_SFT_NATIVE_TOY_VALIDATION.json").read_bytes()) == delivery["public_validation_sha256"]
    public = json.loads((root / "reports/experiments/P04_SFT_NATIVE_TOY_VALIDATION.json").read_text())
    index = read("source-snapshots/index.json")
    assert index["commands"] == public["command_receipts_at_measurement_seal"]
    snapshots = {}
    blobs = old / "source-snapshots/blobs"
    for path in blobs.iterdir():
        assert path.is_file() and sha(path.read_bytes()) == path.name
    assert len(list(blobs.iterdir())) == 409
    for path in (old / "source-snapshots").glob("*.json"):
        if path.name == "index.json":
            continue
        data = json.loads(path.read_text())
        assert canonical(data) == path.stem
        assert all(sha((blobs / digest).read_bytes()) == digest for digest in data.values())
        snapshots[path.stem] = data
    assert len(snapshots) == 7
    commands, committed = [], {}
    snapshot_commands = {item["label"]: item for item in index["commands"]}
    for item in delivery["original_command_receipts"]:
        label = item["label"]
        receipt_path = old / label / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        assert sha(receipt_path.read_bytes()) == item["sha256"], label
        assert receipt["exit_code"] == item["exit_code"], label
        assert receipt["source_files_before"] == receipt["source_files_after"], label
        assert receipt["source_unchanged_during_command"] is True
        assert receipt["error"] is None
        assert receipt["cwd"] == str(t1_repo)
        assert datetime.fromisoformat(receipt["ended_at_utc"]) >= datetime.fromisoformat(receipt["started_at_utc"])
        assert receipt["wall_seconds"] >= 0
        started = json.loads((old / label / "started.json").read_text())
        assert all(receipt[key] == value for key, value in started.items()), label
        for stream in ("stdout", "stderr"):
            assert sha((old / label / (stream + ".log")).read_bytes()) == receipt[stream + "_sha256"], label
        head = receipt["source_head"]
        assert git("rev-parse", head + "^{tree}").decode().strip() == receipt["source_tree"]
        if head not in committed:
            committed[head] = source(head)
        mismatch = sorted(name for name in set(committed[head]) | set(receipt["source_files_before"])
                          if committed[head].get(name) != receipt["source_files_before"].get(name))
        if label in snapshot_commands:
            item2 = snapshot_commands[label]
            assert snapshots[item2["source_snapshot_sha256"]] == receipt["source_files_before"]
            for field in ("source_head", "source_tree", "started_at_utc", "ended_at_utc", "exit_code",
                          "wall_seconds", "stdout_sha256", "stderr_sha256"):
                assert item2[field] == receipt[field], (label, field)
            assert item2["original_receipt_sha256"] == item["sha256"]
            assert item2["original_argv_sha256"] == canonical(receipt["argv"])
            assert item2["original_environment_sha256"] == canonical(receipt["environment"])
            assert item2["snapshot_files"] == len(receipt["source_files_before"])
            assert item2["recorded_head_mismatch_paths"] == mismatch
            matching = item2["matching_committed_tree"]
            if matching is not None:
                if matching not in committed:
                    committed[matching] = source(matching)
                assert committed[matching] == receipt["source_files_before"]
        else:
            assert label in {"diff-final", "public-final", "staged-diff-final", "push-new-branch"}
            assert receipt["source_files_before"] == candidate
            assert head == (CANDIDATE if label == "push-new-branch" else delivery["parents"][0])
        commands.append({"label": label, "exit_code": receipt["exit_code"], "receipt_sha256": item["sha256"],
                         "source_head": head, "source_tree": receipt["source_tree"],
                         "source_snapshot_sha256": canonical(receipt["source_files_before"]),
                         "recorded_head_mismatch_paths": mismatch})
    assert len(commands) == 31 and len(snapshot_commands) == 27
    assert {c["label"] for c in commands if c["exit_code"] != 0} == {
        "final-cpu-combined", "package-final-command", "source-segmented-command-r1"}
    reconstructed = index["guard_r3_reconstructed_blob_sha256"]
    assert sha((blobs / reconstructed).read_bytes()) == reconstructed
    guard = json.loads((old / "guard-tests-r3/receipt.json").read_text())
    assert reconstructed == guard["source_files_before"]["src/toolalign/training/sft/native_toy.py"]
    functions = ("_numeric_body", "_numerics", "_case_bounds", "_versions", "load_inputs", "require_current_lease")
    name = "src/toolalign/training/sft/native_toy.py"
    def nodes(commit):
        return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(git("show", commit + ":" + name)).body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    original_nodes, final_nodes = nodes(NUMERIC), nodes(CANDIDATE)
    assert all(original_nodes[name] == final_nodes[name] for name in functions)
    for name in ("mlx_adapter.py", "validation.py"):
        path = "src/toolalign/training/sft/" + name
        assert git("show", NUMERIC + ":" + path) == git("show", CANDIDATE + ":" + path)
    launches = [json.loads(p.read_text()) for p in sorted((old / "framework-launches").glob("launch-*.json"))]
    assert len(launches) == 3 and [v["launch_number"] for v in launches] == [1, 2, 3]
    run_checks = []
    for entry in launches:
        run = Path(entry["output"])
        assert run.parent == old
        data = json.loads((run / "preregistration.json").read_text())
        assert data == entry
        result = json.loads((run / "result.json").read_text())
        if data["source_head"] not in committed:
            committed[data["source_head"]] = source(data["source_head"])
        for group in (data["parent_origins"], result["origins"]):
            for module_name, origin in group.items():
                module_path = "src/" + module_name.replace(".", "/")
                if module_path + "/__init__.py" in committed[data["source_head"]]:
                    module_path += "/__init__.py"
                else:
                    module_path += ".py"
                assert committed[data["source_head"]][module_path] == origin["sha256"], module_name
                if data["mode"] == "installed_segmented":
                    assert "/installed-wheel/toolalign/" in origin["path"]
                    assert sha(Path(origin["path"]).read_bytes()) == origin["sha256"]
        supervision = json.loads((run / "supervision.json").read_text())
        lease = json.loads((run / "lease-acquired.json").read_text())
        terminal = json.loads((run / "child-terminal.json").read_text())
        owner = lease["actual_lock"]["owner"]
        assert lease["numerical_modules_before_import"] == [] and lease["actual_lock"]["held"] is True
        assert owner["pid"] == lease["pid"] == supervision["pid"]
        assert owner["worker_alias"] == "T1" and owner["task_id"] == "P04-SFT-NATIVE-TOY"
        assert owner["process_started_at"] and terminal["lease_held_until_process_exit"] is True
        assert supervision["actual_child_exit"] == supervision["exit_code"] == terminal["exit_code"] == 0
        assert supervision["own_process_reaped"] is True and supervision["own_pid_exists"] is False
        assert supervision["lock_after"]["held"] is False and supervision["consumer_unchanged"] is True
        assert supervision["wall_seconds"] <= 300 and 0 < supervision["peak_rss_bytes"] <= 4 * 1024**3
        assert result["consumer_identity"] == data["consumer_identity"]
        assert canonical(result["consumer_identity"]) == data["consumer_sha256"]
        assert result["environment"] == data["environment"]
        assert result["device"]["mlx_default"] == result["device"]["mlx_execution_stream"] == "Device(gpu, 0)"
        assert result["device"]["torch"] == "cpu"
        assert result["device"]["torch_intra_threads"] == result["device"]["torch_inter_threads"] == 2
        assert max(row["mlx_peak_bytes"] for row in result["memory"]) <= 1024**3
        assert result["training_authorized"] is False
        for stream in ("stdout", "stderr"):
            assert sha((run / (stream + ".log")).read_bytes()) == supervision[stream + "_sha256"]
        wired = json.loads((run / "wired-limit-and-compile.json").read_text())
        assert wired["setter_restored"] is True and wired["compile_preserved"] is True
        run_checks.append({"mode": data["mode"], "source_head": data["source_head"], "status": result["status"],
                           "launch_number": data["launch_number"], "pid": supervision["pid"],
                           "wall_seconds": supervision["wall_seconds"], "peak_rss_bytes": supervision["peak_rss_bytes"],
                           "stderr_sha256": supervision["stderr_sha256"], "supervision_sha256": sha((run / "supervision.json").read_bytes())})
    output = {"status": "PASS", "candidate": CANDIDATE, "candidate_files": 408, "base_unchanged": 399,
              "changed": changed, "counts": counts, "commands": commands, "original_runs": run_checks,
              "source_snapshots": 7, "source_blobs": 409, "original_numeric_functions_unchanged": list(functions),
              "reconstructed_guard_blob_sha256": reconstructed, "new_framework_launches": 0,
              "reviewer_script_sha256": sha(Path(__file__).read_bytes())}
    save(args.output, output)
    print(json.dumps({key: output[key] for key in ("status", "candidate", "counts", "source_snapshots", "source_blobs")}))


if __name__ == "__main__":
    main()
