"""Frozen, unfilled Q1 review materials and the original-denominator quality gate."""

from __future__ import annotations

import html
import math
from collections import defaultdict

from toolalign.contracts import canonical_hash, validate_record
from toolalign.data.common import DataError, encoded

from .extract import ERROR_CLASSES, validate_generation_model


def freeze_review(preferences, lineage, *, synthetic):
    by_id = {p["preference_id"]: validate_record(p, "preference") for p in preferences}
    for value in by_id.values():
        validate_generation_model(value["generation_model"], synthetic=synthetic)
    lines = {row["preference_id"]: row for row in lineage}
    if len(by_id) != len(preferences) or len(lines) != len(lineage) or set(by_id) != set(lines):
        raise DataError("review_pool_identity")
    strata = defaultdict(list)
    for identity, row in lines.items():
        if row["error_class"] not in ERROR_CLASSES or row["synthetic"] != synthetic:
            raise DataError("review_stratum_or_mode")
        strata[row["error_class"]].append(identity)
    total = len(by_id)
    size = min(total, max(100, math.ceil(total * 0.10)))
    quotas = {name: 1 for name in ERROR_CLASSES if strata[name]}
    remaining = size - len(quotas)
    population = sum(len(strata[name]) - 1 for name in quotas)
    if population:
        for name in quotas:
            quotas[name] += remaining * (len(strata[name]) - 1) // population
    # Proportional floors, then unassigned seats in the frozen class order.
    for name in quotas:
        if sum(quotas.values()) == size:
            break
        if quotas[name] < len(strata[name]):
            quotas[name] += 1
    sample = [identity for name, quota in quotas.items()
              for identity in sorted(strata[name], key=lambda ident: canonical_hash([42, ident]))[:quota]]
    return {"schema_version": "toolalign.preference-q1-sample.v1", "seed": 42,
            "synthetic": synthetic, "pool_size": total,
            "pool_hash": canonical_hash([by_id[key] for key in sorted(by_id)]),
            "lineage_hash": canonical_hash([lines[key] for key in sorted(lines)]),
            "class_order": list(ERROR_CLASSES), "quotas": quotas, "sample_ids": sample,
            "sample_size": size, "reviewer": None,
            "judgments": [{"preference_id": identity, "verdict": None, "reason": ""} for identity in sample]}


def review_html(packet, preferences, lineage):
    by_id = {p["preference_id"]: p for p in preferences}
    lines = {row["preference_id"]: row for row in lineage}
    sections = []
    for identity in packet["sample_ids"]:
        value = {"preference": by_id[identity], "lineage": lines[identity]}
        sections.append("<section><h2>" + html.escape(identity) + "</h2><p>Q1 verdict: PENDING</p><pre>"
                        + html.escape(encoded(value).decode()) + "</pre></section>")
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            "<title>G4 Q1 preference review</title><style>body{max-width:960px;margin:40px auto;"
            "font:16px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}section{border-top:1px solid #999}</style>"
            "<h1>G4 Q1 preference review</h1><p>Independent review required. Check full request, legal alternatives, "
            "first divergence and trace provenance. Automatic checks are not a Q1 verdict.</p>"
            "<p>Mode: " + ("SYNTHETIC CPU EXERCISE" if packet["synthetic"] else "formal pool, pending Q1")
            + "</p>" + "".join(sections) + "</html>")


def apply_review(packet, preferences, lineage, review):
    frozen = freeze_review(preferences, lineage, synthetic=packet["synthetic"])
    if canonical_hash(packet) != canonical_hash(frozen):
        raise DataError("review_sample_changed")
    if (review.get("sample_hash") != canonical_hash(packet)
            or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()):
        raise DataError("review_binding_or_identity")
    judgments = review["judgments"]
    by_id = {row["preference_id"]: row for row in judgments}
    pool = {p["preference_id"] for p in preferences}
    if (len(by_id) != len(judgments) or not set(by_id) <= pool
            or any(row["verdict"] not in ("pass", "fail", "unknown")
                   or not isinstance(row["reason"], str) or not row["reason"].strip()
                   for row in judgments)):
        raise DataError("invalid_review_judgment")
    missing = sorted(set(packet["sample_ids"]) - set(by_id))
    excluded = {identity for identity, row in by_id.items() if row["verdict"] in ("fail", "unknown")}
    errors = len(set(packet["sample_ids"]) & excluded)
    denominator = packet["sample_size"]
    blocked = bool(missing) or denominator == 0 or errors * 20 > denominator
    accepted = [p for p in preferences if p["preference_id"] not in excluded]
    return {"quality_pass": not blocked, "training_authorized": False,
            "dpo_quality_gate": "BLOCKED" if blocked or packet["synthetic"] else "PASS",
            "synthetic": packet["synthetic"], "reviewer": review["reviewer"],
            "review_hash": canonical_hash(review), "sample_hash": canonical_hash(packet),
            "original_review_denominator": denominator, "sample_errors_including_unknown": errors,
            "error_rate": errors / denominator if denominator else None, "missing_judgments": missing,
            "excluded_ids": sorted(excluded), "remaining_preferences": accepted,
            "training_preferences": [] if blocked or packet["synthetic"] else accepted,
            "replacement_sampling": False}
