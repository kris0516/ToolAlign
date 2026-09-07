"""Validate and aggregate already authored private semantic judgments.

This program never assigns a semantic verdict. It checks identity and coverage,
then exports the recorded decisions, issue explanations and separate cohorts.
The output contains private source identifiers and must remain outside Git.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

VERDICTS = ("pass", "unknown", "fail")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def counts(values):
    result = Counter(values)
    return {verdict: result[verdict] for verdict in VERDICTS}


def summarize(rows):
    return {
        "sources": len(rows),
        "decisions": sum(len(row["decisions"]) for row in rows),
        "source_verdicts": counts(row["source_verdict"] for row in rows),
        "decision_verdicts": counts(
            decision["verdict"] for row in rows for decision in row["decisions"]
        ),
        "distinct_groups": len({row["group_id"] for row in rows}),
        "sources_by_split": dict(Counter(row["split"] for row in rows)),
        "decisions_by_split": dict(Counter(
            row["split"] for row in rows for _ in row["decisions"]
        )),
    }


def load_record(root, name, cohort, selection=None):
    judgment_path = root / "judgments" / (name + ".json")
    packet_path = root / "frozen" / "packets" / (name + ".json")
    row = read(judgment_path)
    packet = read(packet_path)
    identity = packet["identity"]
    assert row["packet"] == name
    assert row["packet_sha256"] == sha(packet_path)
    assert row["reviewer"] == "Codex-AI(E1)"
    assert datetime.fromisoformat(row["reviewed_at_utc"]).utcoffset().total_seconds() == 0
    assert row["complete_source_reviewed"] and row["all_valid_decisions_reviewed"]
    assert not row["old_verdict_consulted"]
    for key in ("source_index", "source_record_hash", "split", "group_id"):
        assert row[key] == identity[key]
    assert row["split"] in {"train", "validation"}
    view_path = root / "views" / row["view"]
    view_meta = read(view_path.with_suffix(".json"))
    assert sha(view_path) == view_meta["view_sha256"] == row["view_sha256"]
    coverage = [item for item in view_meta["coverage"] if item["packet"] == name]
    assert len(coverage) == 1
    assert coverage[0]["packet_sha256"] == row["packet_sha256"]
    assert coverage[0]["raw_turn_count"] == len(packet["source"]["conversations"])
    originals = {
        item["lineage"]["source_turn_index"]: item for item in packet["valid_decisions"]
    }
    assert len(originals) == len(row["decisions"]) == identity["valid_decision_count"]
    assert {decision["turn"] for decision in row["decisions"]} == set(originals)
    expected_ids = {item["example"]["example_id"] for item in originals.values()}
    assert set(coverage[0]["example_ids"]) == expected_ids
    if selection is not None:
        assert selection == identity
        assert set(selection["example_ids"]) == expected_ids
    for decision in row["decisions"]:
        original = originals[decision["turn"]]
        assert decision["example_id"] == original["example"]["example_id"]
        for key in ("source_action_sha256", "prefix_turn_end_exclusive"):
            assert decision[key] == original["lineage"][key]
        assert decision["full_prefix_reviewed"] and decision["basis"]
        assert decision["verdict"] in VERDICTS
        assert bool(decision.get("issues")) == (decision["verdict"] != "pass")
    expected_verdict = max(
        (decision["verdict"] for decision in row["decisions"]), key=VERDICTS.index
    )
    assert row["source_verdict"] == expected_verdict
    return {
        **row,
        "cohort": cohort,
        "selection_phase": identity.get("selection_phase", cohort),
        "pattern_hits": identity.get("pattern_hits", []),
        "rank_sha256": identity.get("rank_sha256"),
        "categories": identity.get("categories", []),
        "judgment_sha256": sha(judgment_path),
        "packet_path": str(packet_path),
        "judgment_path": str(judgment_path),
        "view_path": str(view_path),
    }


def write_csv(path, fields, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: encoded(value) if isinstance(value, (dict, list)) else value
                for key, value in row.items() if key in fields
            })


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.audit_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = read(root / "frozen" / "sample-manifest.json")
    rows = []
    for key, prefix, cohort, expected_count in (
        ("prior_sources", "prior", "prior_32", 32),
        ("new_sources", "new", "new_180", 180),
    ):
        assert len(manifest[key]) == expected_count
        rows.extend(
            load_record(root, f"{prefix}-{index:03d}", cohort, identity)
            for index, identity in enumerate(manifest[key], start=1)
        )
    assert {path.stem for path in (root / "judgments").glob("*.json")} == {
        row["packet"] for row in rows
    }
    material_root = root / "material-review"
    material_names = sorted(path.stem for path in (material_root / "judgments").glob("*.json"))
    assert len(material_names) == 10
    rows.extend(load_record(material_root, name, "additional_effective_10") for name in material_names)
    assert len({row["source_record_hash"] for row in rows}) == 222
    assert len({d["example_id"] for row in rows for d in row["decisions"]}) == 251
    addendum = read(root / "independent-review-addendum.json")
    overrides = {
        (item["packet"], item["source_turn_index"], item["issue_index"]): item
        for item in addendum["issue_verdict_overrides"]
    }
    used_overrides = set()
    decisions, issues, context_issues, proposals = [], [], [], []
    identity_fields = (
        "packet", "cohort", "source_index", "source_record_hash", "split", "group_id",
        "selection_phase", "pattern_hits", "source_verdict", "reviewer", "reviewed_at_utc",
        "judgment_sha256", "packet_sha256", "view_sha256",
    )
    for row in rows:
        identity = {key: row[key] for key in identity_fields}
        for decision in row["decisions"]:
            decisions.append({**identity, **decision})
            for index, issue in enumerate(decision.get("issues", [])):
                key = (row["packet"], decision["turn"], index)
                override = overrides.get(key)
                if override:
                    used_overrides.add(key)
                verdict = override["verdict"] if override else issue.get("verdict", decision["verdict"])
                assert verdict in {"fail", "unknown"}
                assert all(issue.get(k) for k in (
                    "category", "evidence", "reason", "recommendation", "downstream"
                ))
                issues.append({
                    **identity, **issue, "verdict": verdict,
                    "source_turn_index": decision["turn"], "example_id": decision["example_id"],
                    "issue_index": index, "source_action_sha256": decision["source_action_sha256"],
                    "override": override, "status": "PROPOSED_TO_S0", "implemented": False,
                })
        for finding in row.get("context_findings", []):
            context_issues.append({
                **identity, **finding,
                "affected_prefix_example_ids": [
                    d["example_id"] for d in row["decisions"]
                    if d["turn"] in finding["affected_prefix_target_turns"]
                ],
                "included_in_action_failure_counts": False,
                "status": "ADVISORY_TO_S0", "implemented": False,
            })
        if row["source_verdict"] != "pass":
            proposals.append({
                **identity, "status": "PROPOSED_TO_S0", "implemented": False,
                "handling": "propose_source_quarantine" if row["source_verdict"] == "fail"
                else "hold_for_missing_source_evidence",
                "all_valid_example_ids": [d["example_id"] for d in row["decisions"]],
                "affected_targets": [
                    {"turn": d["turn"], "example_id": d["example_id"], "verdict": d["verdict"],
                     "issues": [issue for issue in issues if issue["example_id"] == d["example_id"]]}
                    for d in row["decisions"] if d["verdict"] != "pass"
                ],
                "release_requires": "S0 freezes exact revision scope and independent review; changed historical observations and dependent prefixes require source-supported revalidation.",
            })
    assert used_overrides == set(overrides)
    write_csv(output / "review.csv", [
        *identity_fields, "rank_sha256", "categories", "decisions", "context_findings",
        "packet_path", "judgment_path", "view_path",
    ], rows)
    write_csv(output / "decision-review.csv", [
        *identity_fields, "turn", "example_id", "verdict", "basis", "issues",
        "source_action_sha256", "prefix_turn_end_exclusive", "full_prefix_reviewed",
    ], decisions)
    for filename, values in (("issues.jsonl", issues), ("context-issues.jsonl", context_issues)):
        with (output / filename).open("x", encoding="utf-8") as stream:
            for value in values:
                stream.write(encoded(value) + "\n")
    write_json(output / "proposals.json", {"status": "PROPOSED_TO_S0", "sources": proposals})
    write_json(output / "traceability.json", [{
        key: row[key] for key in (*identity_fields, "packet_path", "judgment_path", "view_path")
    } | {"all_example_ids": [d["example_id"] for d in row["decisions"]]} for row in rows])
    comparison = read(root / "prior-comparison.json")
    write_csv(output / "prior-recheck.csv", list(comparison["rows"][0]), comparison["rows"])
    prior = [row for row in rows if row["cohort"] == "prior_32"]
    new = [row for row in rows if row["cohort"] == "new_180"]
    material = [row for row in rows if row["cohort"] == "additional_effective_10"]
    modes = read(root / "frozen" / "pool-summary.json")["eligible_pattern_hits"]
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "Codex-AI(E1)", "aggregation_policy": addendum["aggregation_policy"],
        "cohorts": {
            "prior_32": summarize(prior), "new_180": summarize(new),
            "random_120": summarize([row for row in new if row["selection_phase"].startswith("random/")]),
            "targeted_60": summarize([row for row in new if row["selection_phase"].startswith("diagnostic/")]),
            "additional_effective_10": summarize(material),
        },
        "by_selection_phase": {
            phase: summarize([row for row in new if row["selection_phase"] == phase])
            for phase in sorted({row["selection_phase"] for row in new})
        },
        "by_split": {split: summarize([row for row in new if row["split"] == split]) for split in ("train", "validation")},
        "by_decision_count": {
            str(n): summarize([row for row in new if len(row["decisions"]) == n])
            for n in sorted({len(row["decisions"]) for row in new})
        },
        "pattern_hits_overlapping": {
            mode: {"eligible_pool_sources": pool, **summarize([row for row in new if mode in row["pattern_hits"]])}
            for mode, pool in modes.items()
        },
        "category_sources": dict(Counter(category for row in new for category in row["categories"])),
        "prior_comparison": dict(Counter(row["comparison"] for row in comparison["rows"])),
        "prior_grade_transitions": dict(Counter(row["old_verdict"] + "->" + row["new_verdict"] for row in comparison["rows"])),
        "issues": len(issues), "issue_verdicts": counts(issue["verdict"] for issue in issues),
        "issue_categories": dict(Counter(issue["category"] for issue in issues)),
        "context_advisories": len(context_issues), "proposed_sources": len(proposals),
        "coverage": {"sources": len(rows), "decisions": len(decisions), "heldout": 0},
        "excluded_from_source_denominator": "Three staged candidate Examples reuse two prior sources; three protocol fixtures are not training examples. The 16-case material table has its own separate denominator.",
        "population_error_rate_claimed": False, "semantic_verdicts_computed_by_script": False,
        "training_authorized": False,
    }
    write_json(output / "summary.json", summary)
    for path in output.iterdir():
        path.chmod(0o444)
    print(encoded({"coverage": summary["coverage"], "cohorts": summary["cohorts"],
                   "issues": len(issues), "context_advisories": len(context_issues)}))


if __name__ == "__main__":
    main()
