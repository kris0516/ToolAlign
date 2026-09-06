"""Ensure failures and response caps cannot disappear behind total lengths."""

import importlib.util
from pathlib import Path


def checks():
    path = Path(__file__).resolve().parents[2] / "reports/data/P02_FORMAT_V1_CHECKS.py"
    # Reports are intentionally absent from the production sdist. Keep ordinary
    # core package tests runnable there; this evidence test is source-only.
    if not path.exists():
        import pytest
        pytest.skip("source-only audit helper absent from sdist")
    spec = importlib.util.spec_from_file_location("format_audit_checks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_denominator_and_independent_response_budget():
    module = checks()
    rows = [
        {"prompt_tokens": 500, "completion_tokens": 276, "completion_tokens_including_eos": 277, "total_tokens": 777, "sequence_error": None, "parser_accepted_exact": True},
        {"prompt_tokens": 1800, "completion_tokens": 50, "completion_tokens_including_eos": 51, "total_tokens": 1851, "sequence_error": None, "parser_error": "parser_failed"},
        {"sequence_error": "boundary_failed"},
    ]
    for row in rows:
        row["budgets"] = module.budget_metrics(row)
    summary = module.summarize(rows)
    assert summary["denominator"] == 3
    assert summary["lengths"]["total_tokens"]["measured"] == 2
    assert summary["lengths"]["total_tokens"]["missing_reasons"] == {"boundary_failed": 1}
    assert summary["budgets"]["context_2048_total_including_eos_pass"] == {"denominator": 3, "pass": 2, "over": 0, "unmeasured": 1}
    assert summary["budgets"]["response_including_eos"] == {"denominator": 3, "pass": 1, "over": 1, "unmeasured": 1}
    assert summary["budgets"]["context_2048_context_and_response_pass"]["pass"] == 1
    assert summary["parser_errors"] == {"parser_failed": 1}


def test_parser_complexity_counts_values_with_root_depth_zero():
    assert checks().complexity({"not_a_node": [{"also_not_a_node": "value"}, True]}) == (5, 3)
