"""Build an original scripted T1 CPU run for the public score/analyze CLIs."""

import argparse
from pathlib import Path

from bfcl_original_cases import action, original_record, selected
from test_cuda_eval import request_for, run

from toolalign.contracts import canonical_hash
from toolalign.data.common import file_hash, write_json
from toolalign.evaluation.bfcl import COMMIT
from toolalign.evaluation.bfcl.source import source_identity
from toolalign.tools.scripted import ScriptedCPUModelBackend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    chosen = [selected(original_record("original-simple")),
              selected(original_record("original-multiple", names=("lab.pick_version", "lab.archive_version")), "multiple"),
              selected(original_record("original-irrelevant", prompt="Return an answer without calling a function."), "irrelevance")]
    inputs = []
    for i, item in enumerate(chosen):
        item.update(ordinal=i, family_id="original-fixture", model_input_hash=canonical_hash(item["model_input"]))
        inputs.append({key: item[key] for key in ("task_id", "family_id", "group_id", "category", "model_input")})
    value = {"schema_version": "toolalign.evaluation-inputs.v1", "purpose": "action-only-model-evaluation", "inputs": inputs}
    request = request_for(root, value, "action-only")
    request["stop_after_unit"] = 5  # Keep a genuine unstarted planned unit.
    selection = {"official_commit": COMMIT, "status": "FROZEN", "selected": chosen,
                 "inputs_sha256": request["input_sha256"], "evidence_kind": "ORIGINAL_CPU_FIXTURE"}
    write_json(root / "selection.json", selection)
    write_json(root / "source.json", source_identity(args.source_root))
    write_json(root / "answers.json", {"official_commit": COMMIT,
        "selection_sha256": file_hash(root / "selection.json"), "sources": "ORIGINAL_CPU_FIXTURE",
        "answers": {item["task_id"]: {"prompt_ordinal": item["ordinal"], "ground_truth": [{"lab.pick_version": {"revision": [17]}}]}
                    for item in chosen if item["category"] != "irrelevance"}})
    by_id = {item["task_id"]: item for item in chosen}

    def backend(unit):
        item = by_id[unit["task_id"]]
        raw = "" if item["category"] == "irrelevance" else action(item["name_map"]["lab.pick_version"],
            17 if (item["category"] == "simple_python") == (unit["model"] == "M1") else 18)
        return ScriptedCPUModelBackend([raw])

    summary, rows = run(request, value, backend)
    assert summary["planned_units"] == 6 and summary["not_started_units"] == 1
    processes = [p for row in rows for p in (row.get("result") or {}).get("process_records", [])]
    assert len(processes) == 5 and all(p["reaped"] for p in processes)
    write_json(root / "fixture-receipt.json", {"status": "PASS", "evidence_kind": "ORIGINAL_SCRIPTED_CPU_FIXTURE",
        "planned_units": 6, "reaped_children": len(processes), "selection_sha256": file_hash(root / "selection.json")})
    print((root / "fixture-receipt.json").read_text())


if __name__ == "__main__":
    main()
