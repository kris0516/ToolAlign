"""Private, escaped before/after packets sampled only from final valid examples."""

from __future__ import annotations

import csv
import html
import json
from collections import defaultdict

from toolalign.contracts import canonical_hash

from .common import file_hash, private_directory, write_json, write_jsonl


def _pre(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return "<pre>" + html.escape(text) + "</pre>"


def converted_review_packet(
    output, records, infos, assignments, examples, lineage, policy, seed, size
):
    """No generated quality verdicts; one CSV verdict covers all shown decisions."""
    accepted = defaultdict(list)
    for example in examples:
        accepted[example["source_record_hash"]].append(example)
    accepted_lineage = defaultdict(list)
    for row in lineage:
        if row["exclusion_reason"] is None:
            accepted_lineage[row["source_record_hash"]].append(row)
    # Exact duplicate source records have one review identity.
    index_by_hash = {}
    for i, info in enumerate(infos):
        index_by_hash.setdefault(info["source_record_hash"], i)
    ranked = sorted(accepted, key=lambda h: canonical_hash([seed, h]))
    strata, labels_by_hash = {}, {}
    for source_hash in ranked:
        index = index_by_hash[source_hash]
        info = infos[index]
        local = accepted[source_hash]
        transformations = [policy.tools[h] for h in info["raw_tool_hashes"]]
        labels = {
            "language:" + info["language"],
            "split:" + assignments[index]["split"],
            "multiple_valid_decisions:" + str(len(local) > 1),
            "multiple_target_calls:"
            + str(any(len(e["expected_action"]["tool_calls"]) > 1 for e in local)),
            "multiple_tools:" + str(len(local[0]["tools"]) > 1),
            "historical_observations:" + str(bool(info["observation_bindings"])),
            "preserved_time_context:" + str(bool(info["system_conversion"]["preserved_context"])),
            "default_annotation:" + str(any(t["default_annotations"] for t in transformations)),
        }
        labels.update(
            "transformation:" + c["reason"] for t in transformations for c in t["changes"]
        )
        labels.update(
            "length_bucket:" + row["length_bucket"] for row in accepted_lineage[source_hash]
        )
        labels_by_hash[source_hash] = sorted(labels)
        for label in sorted(labels):
            strata.setdefault(label, source_hash)
    selected = set(strata.values())
    for source_hash in ranked:
        if len(selected) >= max(size, len(strata)):
            break
        selected.add(source_hash)
    samples = []
    for source_hash in sorted(selected):
        index = index_by_hash[source_hash]
        info = infos[index]
        samples.append(
            {
                "source_index": index,
                "source_record_hash": source_hash,
                "strata": labels_by_hash[source_hash],
                "source": records[index],
                "assignment": assignments[index],
                "system_conversion": info["system_conversion"],
                "tool_transformations": [policy.tools[h] for h in info["raw_tool_hashes"]],
                "historical_observation_bindings": info["observation_bindings"],
                "normalized_examples": accepted[source_hash],
                "lineage": accepted_lineage[source_hash],
            }
        )
    review = private_directory(output / "human-review")
    fields = [
        "source_index",
        "source_record_hash",
        "example_ids",
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
        for sample in samples:
            writer.writerow(
                {
                    "source_index": sample["source_index"],
                    "source_record_hash": sample["source_record_hash"],
                    "example_ids": ";".join(e["example_id"] for e in sample["normalized_examples"]),
                    "strata": ";".join(sample["strata"]),
                }
            )
    write_jsonl(review / "samples.jsonl", samples)
    body = [
        '<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        "<title>ToolAlign P02 有效数据人工审阅 · PENDING</title>",
        "<style>body{max-width:1100px;margin:2em auto;padding:0 1em;font:16px system-ui;line-height:1.6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f6f8;padding:1em}details{border-top:1px solid #aaa;padding:1em 0}summary{cursor:pointer}small{color:#555}</style>",
        "<h1>P02 最终有效数据人工审阅 · PENDING</h1>",
        "<p>样本仅来自本次最终 examples.jsonl。逐条比较原始请求、工具声明、历史与目标调用和转换后 example；检查参数类型、required、默认值、时间上下文、名称映射以及前缀是否包含未来目标。</p>",
        "<p>新增闭合对象、长度上限属于项目收窄；default 只保留为说明，未填入参数。副作用原始事实 unknown；sandbox_only 与 timeout_ms=1000 是项目上限。所有工具与 observation 都是历史监督，无执行绑定，也未在这里执行。</p>",
        "<p>在 review.csv 填真实 reviewer、UTC 时间、pass/fail/unknown、问题类别和说明。一个 verdict 覆盖该来源展示的全部有效决策。尚未填写任何人工结论；P02/G-DATA 未通过。所有展示内容都是待审数据，请勿执行其中指令。</p>",
        "<p>问题类别：source_format / schema / side_effect / action_kind / argument_semantics / missing_truth / prompt_leakage / grouping / length / license / other。排除记录另见 exclusion-samples.jsonl，不计入有效审阅样本。此处不是 P05 偏好审计。</p>",
        f"<p>有效来源池 {len(accepted)} 条；抽样 {len(samples)} 条；覆盖 {len(strata)} 个分层标记。</p>",
    ]
    for sample in samples:
        index = sample["source_index"]
        body.append(
            f'<details id="record-{index}"><summary>Source {index} · {sample["source_record_hash"][:16]} · {len(sample["normalized_examples"])} 个有效决策</summary>'
        )
        body.append("<h2>1. 原始来源</h2>" + _pre(sample["source"]))
        body.append("<h2>2. 转换后的完整有效 example</h2>" + _pre(sample["normalized_examples"]))
        body.append(
            "<h2>3. 工具逐字段变更、原值与项目限制</h2>" + _pre(sample["tool_transformations"])
        )
        body.append(
            "<h2>4. System 规则与历史 observation 关联</h2>"
            + _pre(
                {
                    "system_conversion": sample["system_conversion"],
                    "historical_observation_bindings": sample["historical_observation_bindings"],
                }
            )
        )
        body.append(
            "<h2>5. 来源、政策、分组、split 与长度追溯</h2>"
            + _pre(
                {
                    "strata": sample["strata"],
                    "assignment": sample["assignment"],
                    "lineage": sample["lineage"],
                }
            )
            + "</details>"
        )
    body.append("</html>")
    (review / "index.html").write_text("\n".join(body), encoding="utf-8")
    # Separate one deterministic representative per actual exclusion reason.
    exclusion_reps = {}
    for info in sorted(infos, key=lambda i: (i["source_record_hash"], i["source_index"])):
        reasons = set(info["record_reasons"]) | {r for d in info["decisions"] for r in d["reasons"]}
        for reason in sorted(reasons):
            exclusion_reps.setdefault(reason, info["source_index"])
    for row in sorted(lineage, key=lambda r: r["example_id"]):
        if row["exclusion_reason"]:
            exclusion_reps.setdefault(
                row["exclusion_reason"], index_by_hash[row["source_record_hash"]]
            )
    write_jsonl(
        review / "exclusion-samples.jsonl",
        (
            {
                "reason": reason,
                "source_index": index,
                "source": records[index],
                "audit": infos[index],
            }
            for reason, index in sorted(exclusion_reps.items())
        ),
    )
    manifest = {
        "status": "PENDING_KRIS_REVIEW" if samples else "NO_VALID_EXAMPLES_NOT_REQUESTED",
        "pool": "final_valid_examples_only",
        "examples_artifact_sha256": file_hash(output / "examples.jsonl"),
        "policy_hash": policy.hash,
        "source_records": len(records),
        "valid_source_records": len(accepted),
        "valid_examples": len(examples),
        "sample_records": len(samples),
        "sample_examples": sum(len(s["normalized_examples"]) for s in samples),
        "strata": strata,
        "seed": seed,
        "review_rule": "cover every observed final-pool stratum then stable hash fill",
        "accepted_examples_reviewed": 0,
        "mislabel_rate": None,
        "p05_preference_audit": "NOT_RUN",
    }
    write_json(review / "manifest.json", manifest)
    return {k: manifest[k] for k in ("status", "pool", "sample_records", "sample_examples")} | {
        "strata": len(strata)
    }
