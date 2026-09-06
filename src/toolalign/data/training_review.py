"""Readable private token/mask evidence, with no model imports or human verdicts.

The trusted caller supplies already verified selection and a CPU tokenizer adapter.
Original protocol fixtures remain distinct from selected training records.
"""

from __future__ import annotations

import copy
import csv
import html
import json
from collections import Counter
from datetime import datetime, timezone

from toolalign.contracts import canonical_hash, validate_record
from toolalign.model_io.sequence import pad_sequence

from .common import encoded, file_hash
from .training_selection import _require, consumer_identity, new_private_directory, rank_key


def _features(example):
    return {
        "multiple_tools": len(example["tools"]) > 1,
        "multiple_target_calls": len(example["expected_action"]["tool_calls"]) > 1,
        "observation_history": any(m["role"] == "tool" for m in example["messages"]),
        "multiple_messages": len(example["messages"]) > 1,
        "non_ascii": any(ord(c) > 127 for c in encoded(example).decode()),
    }


def choose_review_cases(plan, protocol_examples):
    """Extrema, available features, then fixed ranking; exactly 10 distinct originals."""
    union = {}
    for profile in ("smoke", "formal"):
        selected = plan[profile]["train"]
        _require(len(selected["examples"]) == len(selected["sidecars"]), "review_sidecar_count")
        for example, sidecar in zip(selected["examples"], selected["sidecars"], strict=True):
            ident = example["example_id"]
            _require(sidecar["audit"]["example_sha256"] == canonical_hash(example), "review_example_binding")
            if ident not in union:
                union[ident] = {"example": copy.deepcopy(example), "audit": copy.deepcopy(sidecar["audit"]),
                                "profiles": {}, "features": _features(example)}
            _require(union[ident]["example"] == example and union[ident]["audit"] == sidecar["audit"],
                     "review_profile_identity_mismatch")
            union[ident]["profiles"][profile] = {"padding_bucket": sidecar["padding_bucket"],
                                                "selection_rank": sidecar["selection_rank"]}
    ordered = sorted(union, key=rank_key)
    _require(len(ordered) >= 10, "insufficient_distinct_review_examples")
    chosen, reasons = [], {}

    def add(ident, reason):
        if ident not in chosen:
            chosen.append(ident)
        reasons.setdefault(ident, []).append(reason)

    add(min(ordered, key=lambda i: (union[i]["audit"]["total_tokens"], rank_key(i))), "shortest_selected")
    add(min(ordered, key=lambda i: (-union[i]["audit"]["total_tokens"], rank_key(i))), "longest_selected")
    smoke = [i for i in ordered if "smoke" in union[i]["profiles"]]
    if smoke:
        add(min(smoke, key=lambda i: (-union[i]["audit"]["total_tokens"], rank_key(i))), "longest_smoke")
    for feature in ("multiple_tools", "multiple_target_calls", "observation_history", "multiple_messages", "non_ascii"):
        available = [i for i in ordered if union[i]["features"][feature]]
        if available:
            add(available[0], feature)
    for ident in ordered:
        if len(chosen) == 10:
            break
        if ident not in chosen:
            add(ident, "ranking_fill")
    _require(len(chosen) == 10, "review_selection_count")
    cases = [{"case_id": f"actual-{i:02d}", "category": "actual_selected_train", **union[ident],
              "selection_reasons": reasons[ident],
              "primary_profile": "smoke" if "smoke" in union[ident]["profiles"] else "formal"}
             for i, ident in enumerate(chosen, 1)]
    originals = list(protocol_examples)
    _require(len(originals) == 3 and {e["expected_action"]["kind"] for e in originals}
             == {"final", "clarify", "refuse"}, "protocol_fixture_kinds")
    protocol_ids = set()
    for example in sorted(originals, key=lambda e: e["expected_action"]["kind"]):
        validate_record(example, "example")
        ident = example["example_id"]
        _require(ident not in union and ident not in protocol_ids, "protocol_fixture_identity_overlap")
        protocol_ids.add(ident)
        cases.append({"case_id": "protocol-" + example["expected_action"]["kind"],
                      "category": "original_protocol_only", "example": copy.deepcopy(example),
                      "audit": None, "profiles": {}, "features": _features(example),
                      "selection_reasons": ["supplemental_action_kind"], "primary_profile": "smoke"})
    coverage = {"available_in_selected_train": {k: sum(v["features"][k] for v in union.values())
                                               for k in _features(cases[0]["example"])},
                "actual_materials": {k: sum(union[i]["features"][k] for i in chosen)
                                     for k in _features(cases[0]["example"])},
                "available_action_kinds": dict(Counter(v["example"]["expected_action"]["kind"] for v in union.values())),
                "actual_count": 10, "protocol_only_count": 3, "distinct_count": 13,
                "selected_union_count": len(union), "human_review": "PENDING",
                "protocol_examples_enter_training": False}
    return cases, coverage


def sequence_record(case, sequence, *, pad_token_id=151643):
    """Materialize complete arrays and independently assert shift/mask boundaries."""
    record = sequence.record()
    p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
    _require(p > 0 and n > p + 1, "review_empty_sequence")
    _require(sequence.sequence_ids[:p] == sequence.prompt_ids, "review_prefix_mismatch")
    _require(sequence.sequence_ids[:-1] == sequence.concatenated_ids, "review_eos_append_mismatch")
    _require(sequence.eos_token_id == 151645 and sequence.sequence_ids[-1] == 151645
             and sequence.sequence_ids[p:].count(151645) == 1, "review_eos_mismatch")
    _require(sequence.loss_mask == (0,) * p + (1,) * (n - p), "review_mask_mismatch")
    _require(sequence.causal_input_ids == sequence.sequence_ids[:-1]
             and sequence.causal_target_ids == sequence.sequence_ids[1:]
             and sequence.causal_loss_mask == sequence.loss_mask[1:], "review_shift_mismatch")
    record.update(causal_input_ids=list(sequence.causal_input_ids), causal_target_ids=list(sequence.causal_target_ids))
    record["causal_input_ids_sha256"] = canonical_hash(record["causal_input_ids"])
    record["causal_target_ids_sha256"] = canonical_hash(record["causal_target_ids"])
    if case["audit"] is not None:
        measured = sequence.metadata() | {k: record[k] for k in ("causal_input_ids_sha256", "causal_target_ids_sha256")}
        _require(all(case["audit"].get(k) == v for k, v in measured.items()), "historical_representation_difference")
        bucket = case["profiles"][case["primary_profile"]]["padding_bucket"]
    else:
        bucket = next((b for b in (1024, 1536) if b >= n), None)
        _require(bucket is not None, "protocol_fixture_over_budget")
    padded = pad_sequence(sequence, length=bucket, pad_token_id=pad_token_id)
    _require(padded.sequence_ids == sequence.sequence_ids + (pad_token_id,) * (bucket - n)
             and padded.attention_mask == (1,) * n + (0,) * (bucket - n)
             and padded.loss_mask == sequence.loss_mask + (0,) * (bucket - n), "review_padding_mismatch")
    _require(sum(padded.causal_loss_mask) == n - p
             and padded.causal_loss_mask[p - 1] == 1
             and padded.causal_loss_mask[n - 2] == 1
             and not any(padded.causal_loss_mask[n - 1:]), "review_supervision_mismatch")
    return {"case": case, "sequence": record, "padding": {
        "bucket": bucket, "pad_token_id": pad_token_id, "unpadded_length": n,
        "sequence_ids": list(padded.sequence_ids), "attention_mask": list(padded.attention_mask),
        "loss_mask": list(padded.loss_mask), "causal_input_ids": list(padded.causal_input_ids),
        "causal_target_ids": list(padded.causal_target_ids), "causal_loss_mask": list(padded.causal_loss_mask),
        "effective_supervised_targets": n - p,
        "first_supervised_causal_position": p - 1, "last_supervised_causal_position": n - 2}}


def render_page(record, token_texts):
    """Only fixed markup is executable HTML; all source values become escaped text."""
    case, sequence, padded = record["case"], record["sequence"], record["padding"]
    _require(len(token_texts) == padded["bucket"], "token_display_count")
    def esc(value):
        return html.escape(str(value), quote=True)

    def block(title, value, *, json_value=True):
        text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) if json_value else value
        return f"<h2>{esc(title)}</h2><pre>{esc(text)}</pre>"

    p, n = sequence["prompt_tokens"], sequence["total_tokens"]
    page = ['<!doctype html><html lang="zh"><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>ToolAlign token / mask review</title><style>body{font:15px system-ui;margin:32px;max-width:1300px;background:#fbfcfe;color:#15202b}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf1f7;padding:16px}table{border-collapse:collapse;width:100%;font:13px monospace}td,th{padding:6px;border:1px solid #ccd5df;text-align:left;white-space:pre-wrap;overflow-wrap:anywhere}th{position:sticky;top:0;background:#dae5f2}.scroll{max-height:650px;overflow:auto}details{margin:24px 0}summary{font-size:20px;font-weight:600}.eos{background:#d0f0df}.completion{background:#fff2c5}.padding{background:#e7e7e7}</style>',
        f'<h1>{esc(case["case_id"])} · token / mask 人工检查</h1>',
        '<p>待人工审阅；本页没有人工 PASS。索引从 0 开始。黄色是目标 Action，绿色是唯一追加 EOS，灰色是右 padding。</p>',
        '<p>检查原始语义、P/C 边界、JSON 完整性；核对第 P−1 个 next-token 位置开始监督，第 N−2 个位置预测 EOS；padding 和 prompt 不计 loss。单 token 解码仅供辅助阅读，精确文字和完整 IDs 如下。</p>',
        block("身份与用途", {k: v for k, v in case.items() if k not in ("example", "audit")}),
        block("ModelInput（完整）", {k: case["example"][k] for k in ("messages", "tools")}),
        block("Action（完整原值）", case["example"]["expected_action"]),
        block("P：精确渲染 prompt", sequence["prompt_text"], json_value=False),
        block("C：精确 completion；EOS 单独追加", sequence["completion_text"], json_value=False),
        block("边界与监督分母", {"P": p, "C_without_eos": n - p - 1, "N_including_eos": n,
            **{k: padded[k] for k in ("bucket", "pad_token_id", "effective_supervised_targets",
                "first_supervised_causal_position", "last_supervised_causal_position")}}),
        '<details><summary>全部 token 与 next-token 表（无截断）</summary><div class="scroll"><table><thead><tr><th>position</th><th>segment</th><th>input ID</th><th>单 token 文字</th><th>attention</th><th>token loss</th><th>next target ID</th><th>shifted loss</th></tr></thead><tbody>']
    for i, token in enumerate(padded["sequence_ids"]):
        segment = "prompt" if i < p else "completion" if i < n - 1 else "eos" if i == n - 1 else "padding"
        target = padded["causal_target_ids"][i] if i < padded["bucket"] - 1 else "—"
        loss = padded["causal_loss_mask"][i] if i < padded["bucket"] - 1 else "—"
        cells = (i, segment, token, token_texts[i], padded["attention_mask"][i], padded["loss_mask"][i], target, loss)
        page.append(f'<tr class="{segment}">' + "".join(f"<td>{esc(v)}</td>" for v in cells) + "</tr>")
    page.append('</tbody></table></div></details><details><summary>全部未 padding 数组、hash 与精确文字</summary>')
    page.append(block("Sequence", sequence))
    page.append('</details><details><summary>全部右 padding / shift / attention / loss 数组</summary>')
    page.append(block("Padded sequence", padded))
    page.append('</details></html>')
    return "\n".join(page)


def write_measurement(cases, coverage, *, tokenizers_by_profile, output):
    """Perform exactly one full encoding per case with the supplied CPU adapters."""
    _require(len(cases) == 13 and len({c["example"]["example_id"] for c in cases}) == 13
             and Counter(c["category"] for c in cases) == {
                 "actual_selected_train": 10, "original_protocol_only": 3}, "review_unique_denominator")
    out = new_private_directory(output)
    identities = {k: v.identity for k, v in tokenizers_by_profile.items()}
    _require(set(identities) == {"smoke", "formal"}, "review_tokenizer_profiles")
    for profile, repo_id, revision in (
        ("smoke", "Qwen/Qwen3-0.6B", "c1899de289a04d12100db370d81485cdf75e47ca"),
        ("formal", "Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"),
    ):
        _require(identities[profile]["repo_id"] == repo_id and identities[profile]["revision"] == revision,
                 "review_tokenizer_model_mismatch")
    records, artifacts = [], {}
    for case in cases:
        tokenizer = tokenizers_by_profile[case["primary_profile"]]
        sequence = tokenizer.training_sequence(case["example"])
        record = sequence_record(case, sequence)
        record["token_texts"] = [tokenizer.decode([i], skip_special_tokens=False) for i in record["padding"]["sequence_ids"]]
        name = case["case_id"]
        _require(name in {f"actual-{i:02d}" for i in range(1, 11)} | {"protocol-final", "protocol-clarify", "protocol-refuse"},
                 "review_case_name")
        for suffix, data in ((".json", encoded(record) + b"\n"),
                             (".html", render_page(record, record["token_texts"]).encode())):
            with (out / (name + suffix)).open("xb") as stream:
                stream.write(data)
            (out / (name + suffix)).chmod(0o600)
            artifacts[name + suffix] = {"sha256": file_hash(out / (name + suffix)), "size_bytes": len(data)}
        records.append(record)
    with (out / "review.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("case_id", "category", "reviewer", "verdict", "reviewed_at_utc", "notes"))
        for record in records:
            writer.writerow((record["case"]["case_id"], record["case"]["category"], "", "", "", ""))
    artifacts["review.csv"] = {"sha256": file_hash(out / "review.csv"), "size_bytes": (out / "review.csv").stat().st_size}
    manifest = {"manifest_version": "toolalign.training-token-review.v1", "coverage": coverage,
        "tokenizers": identities, "consumer": consumer_identity(), "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "records_sha256": canonical_hash(records), "artifacts": artifacts,
        "unique_examples": len(records), "model_loading": "NOT_RUN", "trainer_collator": "NOT_RUN",
        "human_review": "PENDING", "training_authorized": False}
    with (out / "manifest.json").open("xb") as stream:
        stream.write(encoded(manifest) + b"\n")
    return manifest
