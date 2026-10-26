"""Pinned official AST scoring with a separate execution/strict-Action gate."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash
from toolalign.tools._json import parse_action

from . import COMMIT, PACKAGE, PROFILE
from .adapter import StrictActionDecoder
from .source import source_identity


class OfficialScorer:
    """Imports official code lazily; never constructs a model/provider handler."""

    def __init__(self, source_root):
        self.identity = source_identity(source_root)
        package = (Path(source_root) / PACKAGE).resolve()
        sys.path.insert(0, str(package))
        from bfcl_eval.constants.enums import Language, ReturnFormat
        from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING
        from bfcl_eval.eval_checker import eval_runner

        if Path(eval_runner.__file__).resolve() != package / "bfcl_eval/eval_checker/eval_runner.py":
            raise ValueError("official_scorer_import_path_mismatch")
        if MODEL_CONFIG_MAPPING[PROFILE].underscore_to_dot is not False:
            raise ValueError("official_profile_name_mapping_mismatch")
        self.ast = eval_runner._evaluate_single_ast_entry
        self.relevance = eval_runner._evaluate_single_relevance_entry
        self.language, self.return_format = Language.PYTHON, ReturnFormat.PYTHON

    def __call__(self, selected, raw_text, ground_truth):
        decoder = StrictActionDecoder(selected["name_map"])
        prompt = copy.deepcopy(selected["record"])
        common = (decoder, selected["task_id"], raw_text)
        if selected["category"] == "irrelevance":
            return self.relevance(*common, prompt, PROFILE, selected["category"])
        return self.ast(*common, copy.deepcopy(ground_truth), prompt, PROFILE,
                        selected["category"], self.language, self.return_format)


def score_action(row, selected, ground_truth, scorer):
    result = row.get("result") or {}
    raw = result.get("raw_text")
    try:
        action = parse_action(raw)
        valid, parse_reason = True, None
    except ContractError as exc:
        action, valid, parse_reason = None, False, str(exc)
    scored = {"plan": row["plan"], "batch_sha256": row["batch_sha256"],
              "task_id": selected["task_id"], "group_id": selected["group_id"],
              "category": selected["category"], "status": row["status"],
              "runtime_reason": row.get("reason"), "raw_text": raw,
              "raw_action_valid": valid, "raw_action_kind": action["kind"] if action else None,
              "raw_parse_reason": parse_reason, "official_status": "NOT_RUN",
              "official_raw_valid": None, "official_result": None, "strict_success": None,
              "gate_reasons": [], "official_commit": COMMIT, "official_profile": PROFILE}
    if scorer is None:
        scored["gate_reasons"] = ["official_scorer_not_run"]
        return scored
    try:
        official = scorer(selected, raw, ground_truth)
        if type(official.get("valid")) is not bool:
            raise ValueError("official_result_missing_boolean_valid")
        scored.update(official_status="RUN", official_result=official, official_raw_valid=official["valid"])
    except Exception as exc:
        # Scorer failures remain visible and unmeasured; never turn them into matches.
        scored.update(official_status="ERROR", official_result={"error": type(exc).__name__ + ": " + str(exc)})
    gates = scored["gate_reasons"]
    if row["status"] != "completed":
        gates.append("runtime:" + row["status"])
    if not valid:
        gates.append("invalid_raw_action")
    if scored["official_status"] != "RUN":
        gates.append("official_scorer_error")
    elif not scored["official_raw_valid"]:
        gates.append("official_mismatch")
    scored["strict_success"] = (not gates) if scored["official_status"] == "RUN" else None
    return scored


def score_batch(loaded, selection, selection_sha256, answers, scorer):
    """Every frozen ID × model is scored, including missing runtime results."""
    if (loaded["mode"] != "action-only" or selection["status"] != "FROZEN"
            or selection["official_commit"] != COMMIT
            or selection["inputs_sha256"] != loaded["input_sha256"]):
        raise ValueError("bfcl_selection_input_binding")
    chosen = {entry["task_id"]: entry for entry in selection["selected"]}
    inputs = loaded["inputs"]["inputs"]
    if len(chosen) != len(inputs) or set(chosen) != {item["task_id"] for item in inputs}:
        raise ValueError("bfcl_selection_ids")
    for item in inputs:
        selected = chosen[item["task_id"]]
        if (selected["model_input_hash"] != canonical_hash(item["model_input"])
                or any(selected[k] != item[k] for k in ("category", "group_id", "family_id"))):
            raise ValueError("bfcl_selection_task_binding")
    if answers is not None and (answers["selection_sha256"] != selection_sha256
                                or answers["official_commit"] != COMMIT):
        raise ValueError("bfcl_answer_selection_binding")
    rows = []
    for row in loaded["rows"]:
        selected = chosen[row["plan"]["task_id"]]
        ground_truth = None
        if selected["category"] != "irrelevance" and scorer is not None:
            answer = answers["answers"][selected["task_id"]]
            if answer["prompt_ordinal"] != selected["ordinal"]:
                raise ValueError("bfcl_answer_ordinal_binding")
            ground_truth = answer["ground_truth"]
        rows.append(score_action(row, selected, ground_truth, scorer))
    return {"schema_version": "toolalign.bfcl-scores.v1", "official_commit": COMMIT,
            "source_identity": scorer.identity if scorer is not None else None,
            "selection_sha256": selection_sha256, "input_sha256": loaded["input_sha256"],
            "batch_sha256": loaded["batch_sha256"], "rows": rows,
            "scope": "fixed_subset_AST_and_irrelevance;not_API_execution_or_official_overall"}
