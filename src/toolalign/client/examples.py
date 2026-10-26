"""Run declared original scripts through real loopback HTTP and local tools."""

from __future__ import annotations

import re
from pathlib import Path

from toolalign.contracts import ContractError
from toolalign.evaluation.oracles.semantic import equivalent
from toolalign.tools._json import decode

from . import protocol as p
from .http import read_json, write_record
from .remote import RemoteClient
from .scripted import ScriptedHTTPFixture
from .trajectory import run_trajectory


def run_examples(manifest_path, root, *, selected=None, cancellation):
    manifest_path = Path(manifest_path).resolve()
    manifest = read_json(manifest_path)
    p.fields(manifest, "schema purpose cases", "example_manifest_fields")
    p.require(manifest["schema"] == "toolalign.service-examples.v1"
              and manifest["purpose"] == "public-original-scripted-development"
              and type(manifest["cases"]) is list and 1 <= len(manifest["cases"]) <= 5, "example_manifest")
    cases = manifest["cases"]
    for case in cases:
        p.fields(case, "id input_file scripted_responses faults expected_status expected_reason expected_final", "example_fields")
        p.require(type(case["id"]) is str and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", case["id"])
                  and type(case["scripted_responses"]) is list and 1 <= len(case["scripted_responses"]) <= 3
                  and all(type(raw) is str for raw in case["scripted_responses"]), "example_values")
    p.require(len({case["id"] for case in cases}) == len(cases), "duplicate_example_id")
    if selected is not None:
        p.require(selected in {case["id"] for case in cases}, "unknown_example")
        cases = [case for case in cases if case["id"] == selected]
    summary = {"schema": "toolalign.service-examples-result.v1", "execution_kind": "ORIGINAL_SCRIPTED_CPU",
               "real_model_examples": "NOT_RUN", "synthetic_token_counts": True,
               "planned_cases": len(cases), "cases": [], "not_started": []}
    for case in cases:
        if cancellation.is_cancelled():
            summary["not_started"].append(case["id"])
            continue
        input_path = (manifest_path.parent / case["input_file"]).resolve()
        p.require(input_path.is_relative_to(manifest_path.parent), "example_input_path")
        model_input = read_json(input_path)
        case_root = root / case["id"]
        case_root.mkdir(mode=0o700)
        with ScriptedHTTPFixture(case_root, case["scripted_responses"]) as fixture:
            client = RemoteClient(fixture.config())
            result = run_trajectory(client, model_input, case_root, faults=case["faults"], cancellation=cancellation)
        write_record(case_root / "http-fixture.json", fixture.evidence())
        answer = result["final_action"]
        matches = False
        if answer is not None and answer["kind"] == "final":
            try:
                matches = equivalent(decode(answer["content"]), case["expected_final"])
            except ContractError:
                pass
        passed = (result["status"] == case["expected_status"] and result["reason"] == case["expected_reason"]
                  and (case["expected_status"] != "finalized" or matches))
        summary["cases"].append({"id": case["id"], "status": result["status"], "reason": result["reason"],
                                  "expected_behavior_passed": passed, "semantic_outcome": "success" if matches else "failure",
                                  "model_decisions": result["budget"]["model_decisions"],
                                  "tool_rounds": result["budget"]["tool_rounds"],
                                  "local_children": len(result["process_records"]),
                                  "local_children_reaped": result["local_children_reaped"]})
        write_record(root / "summary.json", summary)
    summary["passed"] = not summary["not_started"] and all(case["expected_behavior_passed"] for case in summary["cases"])
    write_record(root / "summary.json", summary)
    return summary
