"""Real owned-process scripted checks and tokenizer-only input measurements."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from toolalign.contracts import canonical_hash, model_input_from_example
from toolalign.contracts.interfaces import OracleTask, SandboxContext
from toolalign.data.common import DataError, read_json, write_json
from toolalign.evaluation.harness import LocalHarness
from toolalign.model_io.cuda_generation import prompt_ids
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend

from .tasks import CATALOG


def run_script(task, responses, root, run_id):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    registry = LocalToolRegistry(task["tool_names"], catalog_id=CATALOG)
    executor = LocalToolExecutor(registry, faults=task["faults"])
    context = SandboxContext(root, run_id,
                             (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
                             CancellationToken())
    result = LocalHarness(registry, executor).run(
        task["example"], OracleTask(**task["oracle_task"]), ScriptedCPUModelBackend(responses),
        context, model_identity=SCRIPTED_IDENTITY)
    row = {"task_id": task["task_id"], "scripted_cpu_only": True,
           "responses": responses, "harness_result": asdict(result)}
    write_json(root / "result.json", row)
    return row


def check_scripts(bundle, authoring, root):
    root = Path(root)
    checks = []
    for task in bundle["tasks"]:
        case = authoring[task["task_id"]]
        scripts = [("positive", str(i), responses)
                   for i, responses in enumerate(case["positive_scripts"])]
        scripts.extend(("negative", label, responses)
                       for label, responses in case["negative_scripts"].items())
        for index, (kind, label, responses) in enumerate(scripts):
            relative = Path(task["task_id"]) / f"script-{index}" / "result.json"
            row = run_script(task, responses, root / relative.parent, f"cpu-{index}")
            result = row["harness_result"]
            expected = "success" if kind == "positive" else "failure"
            checks.append({"task_id": task["task_id"], "kind": kind, "label": label,
                           "path": relative.as_posix(), "expected": expected,
                           "actual": result["score"]["outcome"],
                           "pass": result["score"]["outcome"] == expected,
                           "processes_reaped": all(p["reaped"] for p in result["process_records"]),
                           "model_decisions": result["trace"][-1]["budget_consumed"]["model_decisions"],
                           "tool_rounds": result["trace"][-1]["budget_consumed"]["tool_rounds"]})
    summary = {"schema_version": "toolalign.evaluation-authoring-checks.v1",
               "task_list_hash": canonical_hash(bundle), "checks": checks,
               "scripted_cpu_only": True, "real_model_evaluation": "NOT_RUN",
               "pass": bool(checks) and all(c["pass"] and c["processes_reaped"] for c in checks)}
    write_json(root / "summary.json", summary)
    return summary


def measure_lengths(bundle, checks_root, tokenizer):
    root = Path(checks_root)
    summary = read_json(root / "summary.json")
    if not summary["pass"] or summary["task_list_hash"] != canonical_hash(bundle):
        raise DataError("lengths_require_matching_successful_cpu_checks")
    rows = []
    for task in bundle["tasks"]:
        rows.append({"task_id": task["task_id"], "stage": "initial", "script": None, "decision": 0,
                     "input_tokens": len(prompt_ids(tokenizer, model_input_from_example(task["example"]))),
                     "completion_tokens_with_eos": None})
    for check in summary["checks"]:
        if check["kind"] != "positive":
            continue
        result = read_json(root / check["path"])["harness_result"]
        for index, (request, decision) in enumerate(zip(
                result["decision_inputs"], result["decisions"], strict=True)):
            rows.append({"task_id": check["task_id"], "stage": "positive_history",
                         "script": check["label"], "decision": index,
                         "input_hash": canonical_hash(request),
                         "input_tokens": len(prompt_ids(tokenizer, request)),
                         "completion_tokens_with_eos": len(tokenizer.encode(
                             decision["raw_text"], add_special_tokens=False)) + 1})
    for row in rows:
        row["input_with_reserve"] = row["input_tokens"] + 256
        row["pass"] = (row["input_with_reserve"] <= 2048
                       and (row["completion_tokens_with_eos"] is None
                            or row["completion_tokens_with_eos"] <= 256))
    excluded = sorted({row["task_id"] for row in rows if not row["pass"]})
    return {"schema_version": "toolalign.evaluation-length-audit.v1",
            "task_list_hash": canonical_hash(bundle), "tokenizer": tokenizer.identity,
            "context_limit": 2048, "completion_reserve": 256, "rows": rows,
            "quarantined_task_ids": excluded,
            "maximum_input_tokens": max((r["input_tokens"] for r in rows), default=None),
            "maximum_completion_tokens_with_eos": max(
                (r["completion_tokens_with_eos"] for r in rows
                 if r["completion_tokens_with_eos"] is not None), default=None),
            "real_model_evaluation": "NOT_RUN"}
