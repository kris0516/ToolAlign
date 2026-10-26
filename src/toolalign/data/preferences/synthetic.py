"""CPU authoring checks only. Explicit scripts never count as learned candidates."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from toolalign.contracts.interfaces import OracleTask, SandboxContext
from toolalign.data.common import read_json, write_json
from toolalign.evaluation.harness import LocalHarness
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend

from .extract import PARAMETERS, freeze_plan


class RecordingScriptedBackend(ScriptedCPUModelBackend):
    def __init__(self, responses, directory):
        super().__init__(responses)
        self.directory = str(directory)

    def generate(self, request, generation_config):
        write_json(Path(self.directory) / f"request-{self.index}.json",
                   {"input": request, "config": asdict(generation_config)})
        return super().generate(request, generation_config)


def run_script(task, responses, root, candidate_id):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    registry = LocalToolRegistry()
    context = SandboxContext(root, candidate_id,
                             (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
                             CancellationToken())
    result = LocalHarness(registry, LocalToolExecutor(registry, faults=task["faults"])).run(
        task["example"], OracleTask(**task["oracle_task"]), RecordingScriptedBackend(responses, root),
        context, model_identity=SCRIPTED_IDENTITY)
    requests = [read_json(path) for path in sorted(root.glob("request-*.json"))]
    row = {"task_id": task["task_id"], "candidate_id": candidate_id,
           "generation_parameters": {k: result.provenance["generation_config"][k] for k in PARAMETERS},
           "model_identity": SCRIPTED_IDENTITY, "harness_result": asdict(result),
           "decision_inputs": [value["input"] for value in requests],
           "status": result.trace[-1]["event"], "synthetic": True}
    write_json(root / "candidate.json", row)
    return row


def authoring_validation(bundle, authoring, root):
    """Validate every authored positive alternative and one counterexample per task."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    planned = {task["task_id"]: [
        {"candidate_id": name, "generation_parameters": {
            "seed": 0, "temperature": 0.0, "top_p": 1.0, "max_new_tokens": 256}}
        for name in ("synthetic-0-positive", "synthetic-1-negative")]
        for task in bundle["tasks"]}
    plan = freeze_plan(bundle, SCRIPTED_IDENTITY, planned, synthetic=True)
    write_json(root / "plan.json", plan)
    candidates, checks = [], []
    for task in bundle["tasks"]:
        case = authoring[task["task_id"]]
        scripts = [("positive", i, values) for i, values in enumerate(case["positive_scripts"])]
        scripts.append(("negative", 0, case["negative_script"]))
        for kind, index, values in scripts:
            identity = f"synthetic-{int(kind == 'negative')}-{kind}"
            row = run_script(task, values, root / task["task_id"] / f"{kind}-{index}", identity)
            expected = "success" if kind == "positive" else "failure"
            checks.append({"task_id": task["task_id"], "kind": kind, "alternative": index,
                           "expected": expected, "actual": row["harness_result"]["score"]["outcome"],
                           "pass": row["harness_result"]["score"]["outcome"] == expected,
                           "processes_reaped": all(p["reaped"] for p in row["harness_result"]["process_records"])})
            if index == 0:
                candidates.append(row)
    summary = {"synthetic": True, "real_model_candidates": 0, "checks": checks,
               "pass": all(c["pass"] and c["processes_reaped"] for c in checks)}
    write_json(root / "summary.json", summary)
    return plan, candidates, summary
