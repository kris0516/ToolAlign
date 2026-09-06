"""Original exact-cap/failure cases for the candidate's published statistics helper."""

import importlib.util
from pathlib import Path

import pytest


def helper():
    root = Path(__file__).resolve().parents[3]
    path = root / "reports/data/P02_FORMAT_V1_CHECKS.py"
    spec = importlib.util.spec_from_file_location("r1_format_candidate_checks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("cap", [1024, 1536, 2048])
def test_inclusive_caps_missing_rows_and_parser_failures_remain_separate(cap):
    module = helper()
    rows = [
        {"prompt_tokens": cap - 256, "total_tokens": cap, "completion_tokens_including_eos": 256,
         "sequence_error": None, "parser_accepted_exact": True},
        {"prompt_tokens": cap - 256, "total_tokens": cap + 1, "completion_tokens_including_eos": 257,
         "sequence_error": None, "parser_accepted_exact": True},
        {"prompt_tokens": 3, "total_tokens": 9, "completion_tokens_including_eos": 6,
         "sequence_error": None, "parser_error": "Invalid JSON"},
        {"sequence_error": "completion_decode_mismatch"},
    ]
    for row in rows:
        row["budgets"] = module.budget_metrics(row)
    result = module.summarize(rows)
    expected = {"denominator": 4, "pass": 2, "over": 1, "unmeasured": 1}
    assert result["denominator"] == 4
    assert result["budgets"][f"context_{cap}_total_including_eos_pass"] == expected
    assert result["budgets"][f"context_{cap}_context_and_response_pass"] == expected
    assert result["budgets"]["response_including_eos"] == expected
    assert result["budgets"]["response_excluding_eos"] == {"denominator": 4, "pass": 3, "over": 0, "unmeasured": 1}
    assert result["budgets"][f"context_{cap}_prompt_plus_reserved_response_pass"] == {"denominator": 4, "pass": 3, "over": 0, "unmeasured": 1}
    assert result["sequence_errors"] == {"completion_decode_mismatch": 1}
    assert result["parser_errors"] == {"Invalid JSON": 1}
    assert result["parser_accepted_exact"] == 2
    assert result["lengths"]["total_tokens"]["missing_reasons"] == {"completion_decode_mismatch": 1}


def test_quantiles_use_nearest_rank_without_interpolation():
    module = helper()
    rows = [{"prompt_tokens": value, "sequence_error": None} for value in range(1, 11)]
    for row in rows:
        row["budgets"] = module.budget_metrics(row)
    metric = module.summarize(rows)["lengths"]["prompt_tokens"]
    assert metric == {"denominator": 10, "measured": 10, "missing": 0, "missing_reasons": {},
                      "max": 10, "p50": 5, "p90": 9, "p95": 10, "p99": 10}
