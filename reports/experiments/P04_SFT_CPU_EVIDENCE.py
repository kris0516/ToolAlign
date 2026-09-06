"""Verify original receipts and produce a public index containing no private paths."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from P04_SFT_CPU_COMMAND import save, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, private = Path.cwd(), args.private.resolve()
    assert ".toolalign-local" in private.parts

    def read(relative):
        return json.loads((private / relative).read_text())

    def digest(relative):
        return sha((private / relative).read_bytes())

    def redact(value):
        if value.startswith("PYTHONPATH=") and "/" in value and value != "PYTHONPATH=src":
            return "PYTHONPATH=<READ_ONLY_BUILD_CACHE_PATHS>"
        if value.startswith("--basetemp="):
            return "--basetemp=<NEW_SYSTEM_TEMP>"
        if value.endswith("/bin/python"):
            if "venv-replay" in value:
                return "<EXISTING_REPLAY_PYTHON>"
            if "integration-cpu" in value:
                return "<EXISTING_TOKENIZER_CPU_PYTHON>"
            return "<EXISTING_DEFAULT_PYTHON>"
        value = value.replace(str(private), "<NEW_PRIVATE_ROOT>")
        value = value.replace(str(private.relative_to(root)), "<NEW_PRIVATE_ROOT>")
        value = value.replace(str(root), "<WORKTREE>")
        if value.startswith("/"):
            return "<EXPLICIT_EXISTING_LOCAL_PATH>"
        return value

    commands = []
    for path in sorted((private / "commands").glob("*/receipt.json")):
        record = json.loads(path.read_text())
        assert record["source_unchanged_during_command"]
        assert record["source_files_before"] == record["source_files_after"]
        assert sha((path.parent / "stdout.log").read_bytes()) == record["stdout_sha256"]
        assert sha((path.parent / "stderr.log").read_bytes()) == record["stderr_sha256"]
        # Bind each original measurement to its real Git epoch, not this later index.
        for name, expected in record["source_files_before"].items():
            data = subprocess.check_output(["git", "show", record["source_head"] + ":" + name])
            assert sha(data) == expected, (path.parent.name, name)
        commands.append({"label": path.parent.name, "argv": [redact(v) for v in record["argv"]],
            **{k: record[k] for k in ("source_head", "source_tree", "started_at_utc", "ended_at_utc",
                                       "exit_code", "wall_seconds", "stdout_sha256", "stderr_sha256")},
            "environment": {k: redact(v) for k, v in record["environment"].items()},
            "source_file_count": len(record["source_files_before"]), "source_unchanged": True,
            "original_receipt_sha256": sha(path.read_bytes())})
    expected_failures = {"toy-segmented", "toy-segmented-r2"}
    assert {r["label"] for r in commands if r["exit_code"]} == expected_failures
    for label, text in {"cpu-combined": "895 passed, 2 skipped", "original-format-review": "60 passed",
                        "independent-deadline-review": "2 passed", "independent-training-binding-review": "13 passed",
                        "new-cpu": "51 passed"}.items():
        assert text in (private / "commands" / label / "stdout.log").read_text()
    collator = read("collator/summary.json")
    assert collator["status"] == "PASS" and collator["new_native_encodings"] == 13
    assert all(c["all_arrays_equal"] for c in collator["cases"])
    numerical = read("toy-segmented-r2/TOY_CPU-numerics.json")
    assert len(numerical["cases"]) == 13
    errors = {name: max(row[name] for row in numerical["cases"]) for name in (
        "loss_error", "gradient_error", "right_padding_loss_error", "right_padding_gradient_error")}
    assert all(value <= 2e-6 for value in errors.values())
    trials = []
    for label in ("toy-segmented", "toy-segmented-r2"):
        supervision = read(label + "/supervision.json")
        terminal = read(label + "/child-terminal.json")
        acquired = read(label + "/lease-acquired.json")
        assert acquired["frameworks_loaded_before_lease"] == []
        assert acquired["actual_lock"]["held"] and acquired["actual_lock"]["owner"]["pid"] == acquired["pid"]
        assert terminal["lease_held_until_process_exit"] and terminal["exit_code"] == 1
        assert supervision["own_process_reaped"] and not supervision["own_pid_exists"]
        assert not supervision["lock_after"]["held"]
        assert supervision["wall_seconds"] <= 300 and supervision["peak_rss_bytes"] <= 4 * 1024**3
        for stream in ("stdout", "stderr"):
            assert digest(label + "/" + stream + ".log") == supervision[stream + "_sha256"]
        trials.append({"label": label, "actual_child_exit": supervision["actual_child_exit"],
            "wall_seconds": supervision["wall_seconds"], "peak_rss_bytes": supervision["peak_rss_bytes"],
            "lease_before_frameworks": True, "lease_retained_until_exit": True, "reaped": True,
            "own_pid_exists": False, "shared_lock_held_after": False,
            "supervision_sha256": digest(label + "/supervision.json"),
            "failure_sha256": digest(label + "/failure.json"),
            "stderr_sha256": digest(label + "/stderr.log"), "mlx_optimizer_updates": 0})
    archive = read("package-check/accepted-archive-checks/archives.json")
    package = read("package-check/summary.json")
    assert package["status"] == "PASS" and package["new_modules"] == 8
    archives = {name: {k: v for k, v in record.items() if k != "members"}
                | {"member_count": len(record["members"])} for name, record in archive["archives"].items()}
    preserve = read("preservation-after.json")
    assert preserve["base_files_unchanged"] == 364 and preserve["old_private_files_preserved"] == 1310
    assert preserve["private_bytes"] < 2 * 1024**3
    config = private / "authorization/coordination/tasks/P04_SFT_CPU_CONFIG.v1.json"
    assert config.read_bytes() == (root / "configs/sft-cpu.v1.json").read_bytes()
    proof = {"status": "CPU_PARTIAL_UPSTREAM_BLOCKED", "task": "P04-SFT-CPU", "worker": "T1",
        "model": "gpt-6-astra", "thinking": "max",
        "code_base": "42eaa50a9519efe96d60b49f07cfbd106b36778c",
        "authorization_commit": "e42536dd7c77d90ed33ab5354f288ab0f1c3d6c6",
        "branch": "work/p04-sft-cpu", "sft_config_sha256": sha(config.read_bytes()),
        "source_measurement_epochs": sorted({r["source_head"] for r in commands}),
        "final_documentation_commit": "supplied in native handoff; no fabricated rerun",
        "commands": commands,
        "cpu_tests": {"combined_including_new": 895, "combined_skipped": 2,
            "format_review": 60, "deadline_review": 2, "training_binding_review": 13,
            "distinct_total": 970, "original_baseline": 919, "new_sft": 51,
            "new_sft_repeat_added": False, "binding_110_subtests_added": False,
            "skips": "2 native-engine HF-only snapshot-cleanup tests"},
        "collator": {k: v for k, v in collator.items() if k != "tokenizers"},
        "collator_summary_sha256": digest("collator/summary.json"),
        "numerics": {"scope": "TOY_CPU", "completed_original_cases": 13, "atol": 2e-6,
            "max_errors": errors, "ignored_prediction_logits_error": numerical["ignored_prediction_logits_error"],
            "default_padding_negative": numerical["upstream_default_padding_negative"],
            "numerics_file_sha256": digest("toy-segmented-r2/TOY_CPU-numerics.json"),
            "device": read("toy-segmented-r2/device-before-numerics.json"), "trials": trials,
            "actual_mlx_train_loop": "NOT_RUN_ENTRY_KEYERROR", "actual_mlx_optimizer_updates": 0,
            "torch_reference_updates_reached_before_entry_failure": 2,
            "torch_final_parameter_files": "NOT_SAVED_BEFORE_ENTRY_FAILURE",
            "native_evaluate": "NOT_RUN", "native_tail_replay": "NOT_RUN",
            "actual_save_reload_post_tail": "NOT_RUN", "native_pre_post_score_binding": "NOT_RUN"},
        "archives": archives, "package_summary_sha256": digest("package-check/summary.json"),
        "archive_proof_sha256": digest("package-check/accepted-archive-checks/archives.json"),
        "installed_modules": 8, "installed_commands_total": 10,
        "installed_expected_rejections": 3, "installed_tests_added_to_distinct_count": False,
        "optional_installed_toy_replay": "NOT_RUN", "direct_source_normal_wheel": "NOT_RUN",
        "new_environments": 0, "new_dependencies": 0,
        "preservation": {k: v for k, v in preserve.items() if k != "human"},
        "human_review": list(preserve["human"].values()),
        "preservation_sha256": digest("preservation-after.json"),
        "formal_training_authorized": False, "formal_training_baselines_sft_checkpoint": "NOT_RUN",
        "new_pretrained_model_loads": 0, "new_gpu_execution": 0,
        "actual_browser_pages": 0, "human_gate_closure": False}
    save(args.output, proof)
    print(json.dumps({"status": proof["status"], "commands": len(commands), "distinct_tests": 970,
                      "output_sha256": sha(Path(args.output).read_bytes())}))


if __name__ == "__main__":
    main()
