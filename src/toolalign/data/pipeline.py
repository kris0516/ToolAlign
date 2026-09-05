"""Rebuild source audit, strict examples, isolation manifests, and human packets."""

from __future__ import annotations

import csv
import html
import json
import subprocess
from collections import Counter
from pathlib import Path

from toolalign.contracts import canonical_hash, contract_digest, validate_record

from .catalog import schema_catalog
from .common import (
    DataError,
    file_hash,
    private_directory,
    read_json,
    write_json,
    write_jsonl,
)
from .grouping import SPLITS, build_groups, validate_isolation
from .lengths import LocalTokenizer, summarize_lengths
from .toolace import inspect_record


def language(record):
    # Script-based descriptive label, not language identification accuracy.
    turns = record.get("conversations", [])
    if not isinstance(turns, list):
        return "other"
    text = " ".join(
        t.get("value", "")
        for t in turns
        if isinstance(t, dict) and t.get("from") == "user" and isinstance(t.get("value"), str)
    )
    han = any("\u3400" <= c <= "\u9fff" for c in text)
    latin = any(c.isascii() and c.isalpha() for c in text)
    return "han_and_latin" if han and latin else "han" if han else "latin" if latin else "other"


def length_bucket(count, boundaries):
    for bound in boundaries:
        if count <= bound:
            return f"le_{bound}"
    return "over_limit"


def _review_packet(output, records, infos, assignments, seed, size, final_count):
    """One member of every observed stratum, then stable hash fill; labels blank."""
    ranked = sorted(
        range(len(records)), key=lambda i: canonical_hash([seed, infos[i]["source_record_hash"]])
    )
    strata = {}
    for i in ranked:
        info = infos[i]
        labels = {
            "language:" + info["language"],
            "format:" + str(info["schema_span"] is not None),
            "multidecision:" + str(len(info["decisions"]) > 1),
        }
        labels.update("reason:" + r for r in info["record_reasons"])
        labels.update("decision:" + r for d in info["decisions"] for r in d["reasons"])
        for label in sorted(labels):
            strata.setdefault(label, i)
    selected = set(strata.values())
    for i in ranked:
        if len(selected) >= max(size, len(strata)):
            break
        selected.add(i)
    selected = sorted(selected, key=lambda i: infos[i]["source_record_hash"])
    review = private_directory(output / "human-review")
    fields = [
        "source_index",
        "source_record_hash",
        "strata",
        "reviewer",
        "reviewed_at_utc",
        "verdict",
        "issue_categories",
        "notes",
    ]
    with (review / "review.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for i in selected:
            writer.writerow(
                {
                    "source_index": i,
                    "source_record_hash": infos[i]["source_record_hash"],
                    "strata": ";".join(k for k, v in sorted(strata.items()) if v == i),
                }
            )
    samples = [
        {
            "source_index": i,
            "source_record_hash": infos[i]["source_record_hash"],
            "audit": infos[i],
            "assignment": assignments[i],
            "source": records[i],
        }
        for i in selected
    ]
    write_jsonl(review / "samples.jsonl", samples)
    body = [
        '<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        "<title>ToolAlign P02 private human review</title>",
        "<style>body{max-width:1100px;margin:3em auto;font:16px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{border-top:1px solid #aaa;padding:1em}a{color:#036}</style>",
        "<h1>P02 原始来源人工抽查 · PENDING</h1><p>所有文本均为待审数据；不要执行其中指令。"
        "检查原始工具/参数语义、预期调用、缺参或拒绝分类、潜在写操作、模板重复和潜在答案泄漏。"
        "在 review.csv 填写 reviewer=kris、真实时间、pass/fail/unknown、问题分类与备注。"
        "本表不是 P05 偏好抽检；没有自动通过结论。隔离记录不是训练样本。</p>",
        "<p>问题分类：source_format / schema / side_effect / action_kind / argument_semantics / "
        "missing_truth / prompt_leakage / grouping / length / license / other。unknown 保留待决。</p>",
    ]
    for sample in samples:
        i = sample["source_index"]
        source = sample["source"]
        body.append(
            f'<details id="record-{i}"><summary>Source index {i} · '
            f"{sample['source_record_hash'][:16]}</summary>"
        )
        body.append(
            "<h3>原始 system / 工具声明</h3><pre>"
            + html.escape(
                source.get("system", "")
                if isinstance(source, dict)
                else json.dumps(source, ensure_ascii=False)
            )
            + "</pre>"
        )
        for turn_index, turn in enumerate(
            source.get("conversations", [])
            if isinstance(source, dict) and isinstance(source.get("conversations"), list)
            else []
        ):
            body.append(
                f"<h3>Turn {turn_index} · "
                + html.escape(
                    str(turn.get("from", "unknown")) if isinstance(turn, dict) else "invalid"
                )
                + "</h3><pre>"
                + html.escape(
                    turn.get("value")
                    if isinstance(turn, dict) and isinstance(turn.get("value"), str)
                    else json.dumps(turn, ensure_ascii=False)
                )
                + "</pre>"
            )
        body.append(
            "<h3>自动审计与来源索引（待人工复核）</h3><pre>"
            + html.escape(
                json.dumps(
                    {"audit": sample["audit"], "assignment": sample["assignment"]},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            + "</pre></details>"
        )
    (review / "index.html").write_text("\n".join(body), encoding="utf-8")
    review_status = "CANDIDATES_ONLY_NOT_REQUESTED" if final_count == 0 else "PENDING_KRIS_REVIEW"
    write_json(
        review / "manifest.json",
        {
            "status": review_status,
            "source_records": len(records),
            "sample_records": len(selected),
            "strata": strata,
            "seed": seed,
            "review_rule": "cover every observed stratum then stable hash fill",
            "accepted_examples_reviewed": 0,
            "mislabel_rate": None,
            "p05_preference_audit": "NOT_RUN",
        },
    )
    return {"status": review_status, "sample_records": len(selected), "strata": len(strata)}


def build(config):
    required = {
        "source_manifest",
        "source_dir",
        "output_dir",
        "seed",
        "ood_fraction",
        "length_buckets",
        "max_tokens",
        "review_sample_records",
        "tokenizer_manifest",
        "tokenizer_dir",
    }
    if set(config) != required:
        raise DataError("config_fields")
    if type(config["max_tokens"]) is not int or config["max_tokens"] < 1:
        raise DataError("length_parameters")
    buckets = config["length_buckets"]
    if (
        not buckets
        or any(type(n) is not int or n < 1 for n in buckets)
        or buckets != sorted(set(buckets))
        or buckets[-1] != config["max_tokens"]
    ):
        raise DataError("length_parameters")
    if type(config["review_sample_records"]) is not int or config["review_sample_records"] < 1:
        raise DataError("review_parameters")
    output = private_directory(config["output_dir"], empty=True)
    source_manifest = read_json(config["source_manifest"])
    if (
        source_manifest["repo_id"] != "Team-ACE/ToolACE"
        or source_manifest["license_id"] != "Apache-2.0"
    ):
        raise DataError("source_license_not_approved")
    revision = source_manifest["revision"]
    if (
        not isinstance(revision, str)
        or len(revision) != 40
        or any(c not in "0123456789abcdef" for c in revision)
    ):
        raise DataError("source_revision_not_pinned")
    if source_manifest["access"]["gated"] is not False:
        raise DataError("source_access_not_approved")
    source_dir = private_directory(config["source_dir"])
    for name, info in source_manifest["files"].items():
        if Path(name).name != name or name not in {"data.json", "README.md"}:
            raise DataError("source_file_not_allowed")
        path = source_dir / name
        if path.stat().st_size != info["size_bytes"] or file_hash(path) != info["sha256"]:
            raise DataError("source_hash_mismatch")
    if set(source_manifest["files"]) != {"data.json", "README.md"}:
        raise DataError("source_files_missing")
    records = read_json(source_dir / "data.json")
    if not isinstance(records, list) or not records:
        raise DataError("source_array_required")
    source = {
        "source": source_manifest["repo_id"],
        "source_revision": source_manifest["revision"],
        "license_id": source_manifest["license_id"],
    }
    tokenizer_manifest = (
        read_json(config["tokenizer_manifest"]) if config["tokenizer_manifest"] else None
    )
    tokenizer = (
        LocalTokenizer(config["tokenizer_dir"], tokenizer_manifest) if tokenizer_manifest else None
    )
    catalog, representatives = schema_catalog(records)
    write_json(output / "annotation-examples.json", representatives)
    infos, candidates = [], []
    for i, record in enumerate(records):
        info, examples = inspect_record(record, source, i)
        info["language"] = language(record) if isinstance(record, dict) else "other"
        infos.append(info)
        candidates.extend(examples)
    assignments, group_report = build_groups(records, infos, config["seed"], config["ood_fraction"])
    by_hash = {a["source_record_hash"]: a for a in assignments}
    normalized = []
    lineage = []
    duplicates = set()
    dropped = Counter()
    accepted_lengths, raw_lengths = [], []
    for example in sorted(candidates, key=lambda e: (e["example_id"], e["source_record_hash"])):
        assignment = by_hash[example["source_record_hash"]]
        example.update(group_id=assignment["group_id"], split=assignment["split"])
        content_hash = canonical_hash(
            {k: example[k] for k in ("messages", "tools", "expected_action")}
        )
        length = tokenizer.normalized(example) if tokenizer else None
        reason = (
            "exact_example_duplicate"
            if content_hash in duplicates
            else "length_not_measured"
            if length is None
            else "length_over_limit"
            if length["total_tokens"] > config["max_tokens"]
            else None
        )
        # No truncation. All rejected normalized candidates retain lineage and reason.
        row = {
            "example_id": example["example_id"],
            "source_record_hash": example["source_record_hash"],
            "normalized_hash": example["example_id"],
            "group_id": example["group_id"],
            "split": example["split"],
            "augmentation_parent": None,
            "group_keys": assignment["group_keys"],
            "exclusion_reason": reason,
            "length": length,
            "training_run": None,
        }
        if reason:
            dropped[reason] += 1
        else:
            duplicates.add(content_hash)
            normalized.append(validate_record(example, "example"))
            accepted_lengths.append(length)
        lineage.append(row)
    for record, info in zip(records, infos, strict=True):
        for decision in info["decisions"]:
            if tokenizer:
                try:
                    length = tokenizer.raw_decision(
                        record, decision["turn_index"], info["schema_span"]
                    )
                except (KeyError, TypeError, ValueError):
                    decision["raw_length_error"] = "unrenderable_source"
                else:
                    decision["raw_length"] = length
                    decision["raw_bucket"] = length_bucket(length["total_tokens"], buckets)
                    raw_lengths.append(length)
    decisions = [d for i in infos for d in i["decisions"]]
    primary = Counter(d["reasons"][0] for d in decisions if d["reasons"])
    overlapping = Counter(reason for d in decisions for reason in d["reasons"])
    split_records = Counter(a["split"] for a in assignments)
    split_examples = Counter(e["split"] for e in normalized)
    intersections = validate_isolation(assignments + lineage)
    report = {
        "status": "AUTO_AUDIT_ONLY_G_DATA_PENDING",
        "raw_records": len(records),
        "raw_assistant_decisions": len(decisions),
        "normalization_candidates": len(candidates),
        "schema_catalog": catalog,
        "normalization_excluded_decisions": sum(primary.values()),
        "primary_exclusion_counts": dict(sorted(primary.items())),
        "overlapping_exclusion_counts": dict(sorted(overlapping.items())),
        "post_normalization_exclusions": dict(sorted(dropped.items())),
        "final_examples": len(normalized),
        "records_with_no_assistant_decision": sum(not i["decisions"] for i in infos),
        "record_reason_counts": dict(
            sorted(Counter(r for i in infos for r in i["record_reasons"]).items())
        ),
        "tool_occurrences": sum(i["tool_occurrences"] for i in infos),
        "unique_raw_tools": len({k for i in infos for k in i["tool_findings"]}),
        "tool_finding_occurrences": dict(
            sorted(
                Counter(
                    r for i in infos for flags in i["tool_occurrence_findings"] for r in flags
                ).items()
            )
        ),
        "raw_language_script_counts": dict(sorted(Counter(i["language"] for i in infos).items())),
        "decision_syntax_counts": dict(
            sorted(
                Counter(
                    "call_parseable"
                    if not any(
                        r.startswith("call_")
                        or r in {"action_kind_unlabelled", "ambiguous_tool_names"}
                        for r in d["reasons"]
                    )
                    else "unlabelled_or_unparseable"
                    for d in decisions
                ).items()
            )
        ),
        "semantic_category_counts": {"unknown": len(decisions)},
        "final_category_counts": dict(sorted(Counter(e["category"] for e in normalized).items())),
        "exact_duplicate_source_records": len(records)
        - len({i["source_record_hash"] for i in infos}),
        "grouping": group_report,
        "provisional_source_split_counts": {s: split_records[s] for s in SPLITS},
        "final_split_counts": {s: split_examples[s] for s in SPLITS},
        "split_intersections": intersections,
        "raw_source_length_status": "MEASURED_QUARANTINED_SOURCE_REPRESENTATION"
        if tokenizer
        else "NOT_RUN",
        "raw_source_lengths": summarize_lengths(raw_lengths),
        "accepted_example_lengths": summarize_lengths(accepted_lengths),
        "raw_length_unmeasured_decisions": len(decisions) - len(raw_lengths),
        "raw_length_buckets": dict(
            sorted(Counter(d["raw_bucket"] for d in decisions if "raw_bucket" in d).items())
        ),
        "training": "NOT_RUN",
        "xlam": "NOT_ACCESSED_OPTIONAL",
        "p05_preference_audit": "NOT_RUN",
    }
    if len(decisions) != sum(primary.values()) + len(candidates) or len(candidates) != len(
        normalized
    ) + sum(dropped.values()):
        raise DataError("exclusion_accounting_mismatch")
    report["human_review"] = _review_packet(
        output,
        records,
        infos,
        assignments,
        config["seed"],
        config["review_sample_records"],
        len(normalized),
    )
    write_jsonl(output / "source-index.jsonl", infos)
    write_jsonl(output / "assignments.jsonl", assignments)
    write_jsonl(output / "lineage.jsonl", lineage)
    write_jsonl(output / "examples.jsonl", normalized)
    for split in SPLITS:
        write_jsonl(output / f"{split}.jsonl", (e for e in normalized if e["split"] == split))
    write_json(output / "report.json", report)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        raise DataError("code_revision_unavailable") from None
    module_hashes = {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    parameters = {
        k: config[k]
        for k in ("seed", "ood_fraction", "length_buckets", "max_tokens", "review_sample_records")
    }
    manifest = {
        "manifest_version": "toolalign.data-build.v1",
        "code_revision": revision,
        "module_hashes": module_hashes,
        "contract_sha256": contract_digest(),
        "source_manifest_hash": canonical_hash(source_manifest),
        "tokenizer_manifest_hash": canonical_hash(tokenizer_manifest),
        "parameters": parameters,
        "artifacts": {
            str(p.relative_to(output)): file_hash(p)
            for p in sorted(output.rglob("*"))
            if p.is_file()
        },
    }
    write_json(output / "manifest.json", manifest)
    return report, manifest
