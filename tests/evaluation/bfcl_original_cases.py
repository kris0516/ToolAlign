"""Original scorer cases, never copied from benchmark prompts or answers.

Run this file explicitly in the separate BFCL CPU environment. It is not a CI
test that silently skips when official dependencies/source are unavailable.
"""

import argparse
import copy
import json
import sys

from toolalign.evaluation.bfcl.adapter import adapt_prompt
from toolalign.evaluation.bfcl.scoring import OfficialScorer, score_action


def original_record(identifier="original-0", *, names=("lab.pick_version",), prompt="Read revision 17."):
    return {"id": identifier, "question": [[{"role": "user", "content": prompt}]], "function": [
        {"name": name, "description": "Read one revision from the original CPU fixture.",
         "parameters": {"type": "dict", "properties": {"revision": {"type": "integer"}},
                        "required": ["revision"], "additionalProperties": False}} for name in names]}


def action(name=None, revision=17, *, kind="final"):
    return json.dumps({"kind": "tool_calls" if name else kind, "content": "" if name else "No tool is needed.",
                       "tool_calls": [{"call_id": "original-call", "name": name,
                                       "arguments": {"revision": revision}}] if name else []})


def selected(record, category="simple_python"):
    return {"task_id": record["id"], "group_id": "original-group", "category": category,
            "record": record, **adapt_prompt(record)}


def original_cases():
    simple = selected(original_record())
    alias = simple["name_map"]["lab.pick_version"]
    multiple = selected(original_record("original-multiple", names=("lab.pick_version", "lab.archive_version")), "multiple")
    irrelevant = {**simple, "category": "irrelevance"}
    answer = [{"lab.pick_version": {"revision": [17]}}]
    cases = [
        ("correct_arguments", simple, action(alias), "completed", answer, True, True),
        ("wrong_arguments", simple, action(alias, 18), "completed", answer, False, False),
        ("wrong_function", simple, action("different_tool"), "completed", answer, False, False),
        ("multiple_selection", multiple, action(multiple["name_map"]["lab.pick_version"]), "completed", answer, True, True),
        ("multiple_wrong_selection", multiple, action(multiple["name_map"]["lab.archive_version"]), "completed", answer, False, False),
        ("multiple_calls_not_one_selection", multiple, json.dumps({"kind": "tool_calls", "content": "", "tool_calls": [
            {"call_id": str(i), "name": name, "arguments": {"revision": 17}}
            for i, name in enumerate(multiple["name_map"].values())]}), "completed", answer, False, False),
        ("final_when_tool_needed", simple, action(), "completed", answer, False, False),
        ("bad_action_irrelevance", irrelevant, '{"kind":"final"}', "parse_failure", None, True, False),
        ("bad_action_reported_completed", irrelevant, '{"kind":"final"}', "completed", None, True, False),
        ("empty_irrelevance", irrelevant, "", "parse_failure", None, True, False),
        ("not_started_irrelevance", irrelevant, None, "not_started", None, True, False),
        ("unknown_tool_irrelevance", irrelevant, action("different_tool"), "completed", None, False, False),
    ]
    for kind in ("final", "clarify", "refuse"):
        cases.append(("legal_no_tool_" + kind, irrelevant, action(kind=kind), "completed", None, True, True))
    for status in ("timed_out", "cancelled", "infrastructure_error", "interrupted"):
        cases.append((status + "_with_legal_final", irrelevant, action(), status, None, True, False))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    network = []

    def audit(event, args):
        if event == "socket.connect":
            network.append(event)
            raise RuntimeError("CPU official scoring must not use network")

    sys.addaudithook(audit)
    scorer = OfficialScorer(args.source_root)
    results = []
    for index, (name, item, raw, status, answer, expected_raw, expected_strict) in enumerate(original_cases()):
        before = copy.deepcopy(item)
        row = {"plan": {"unit_id": index, "task_id": item["task_id"], "condition": "M0"},
               "batch_sha256": "original-fixture", "status": status,
               "reason": name, "result": {"raw_text": raw, "raw_action_valid": True}}
        result = score_action(row, item, answer, scorer)
        results.append({"case": name, "expected_raw": expected_raw, "expected_strict": expected_strict, **result})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
        assert result["official_status"] == "RUN", (name, result)
        assert result["official_raw_valid"] is expected_raw and result["strict_success"] is expected_strict, name
        assert item == before, "official scorer mutated retained source"
    print(json.dumps({"status": "PASS", "cases": len(results), "network_attempts": network,
                      "model_framework_modules": sorted(set(sys.modules) & {"torch", "transformers", "tensorflow", "mlx", "jax", "flax"}),
                      "source": scorer.identity, "evidence_kind": "ORIGINAL_CPU_SCORER_CASES"}, indent=2))


if __name__ == "__main__":
    main()
