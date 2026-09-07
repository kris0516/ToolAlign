"""Private quality-review cases and complete CPU token/mask evidence.

Selected originals, protocol fixtures, direct drafts and dependent prefixes keep
separate identities and purposes. No semantic verdict is filled by this module.
"""

from __future__ import annotations

import argparse
import copy
import csv
import html
import io
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash, validate_record
from toolalign.model_io.format import ModelIOError, encode_action
from toolalign.model_io.sequence import pad_sequence

from . import quality_revision as q
from .common import DataError, encoded, loads
from .training_review import choose_review_cases


def choose_cases(inputs, artifacts, manifest):
    """Apply the original ten-case rules to the effective selection only."""
    plan = {p: {"train": {k: q.jsonl(artifacts[f"selection/{p}/train.{k}.jsonl"])[0]
                          for k in ("examples", "sidecars")}} for p in q.PROFILES}
    protocols = [r["case"]["example"] for r in inputs["old_token_cases"].values()
                 if r["case"]["category"] == "original_protocol_only"]
    cases, coverage = choose_review_cases(plan, protocols)
    old_cases = {r["case"]["example"]["example_id"]: r["case"]["case_id"]
                 for r in inputs["old_token_cases"].values()}
    revision = manifest["quality_revision_sha256"]
    for case in cases:
        ident = case["example"]["example_id"]
        case["quality_revision_sha256"] = revision
        case["previous_material_case_id"] = old_cases.get(ident)
        case["semantic_verdict"] = None
        if case["category"] == "actual_selected_train":
            q.require(case["example"]["source_record_hash"] not in inputs["issues"], "quarantined_review_example")
            case["category"] = "effective_selected_train"
            case["case_id"] = case["case_id"].replace("actual-", "effective-")
            case["original_jsonl_line_sha256"] = q.sha(inputs["original_bytes"][ident])
            case["original_lineage_sha256"] = canonical_hash(inputs["index"]["lineage"][ident])
            for p, info in case["profiles"].items():
                sidecar = next(r for r in plan[p]["train"]["sidecars"] if r["audit"]["example_id"] == ident)
                info["parent_selection_rank"] = sidecar["parent_selection_rank"]
        else:
            case["enters_effective_training"] = False
    staged = q.jsonl(artifacts["staging/examples.jsonl"])[0]
    sidecars = q.jsonl(artifacts["staging/sidecars.jsonl"])[0]
    q.require(len(staged) == len(sidecars), "staged_material_count")
    counts = Counter()
    for example, sidecar in zip(staged, sidecars, strict=True):
        q.require(sidecar["example_id"] == example["example_id"]
                  and sidecar["example_sha256"] == canonical_hash(example)
                  and sidecar["quality_revision_sha256"] == revision
                  and sidecar["enters_effective_training"] is False, "staged_material_identity")
        direct = sidecar["kind"] == "direct_action_revision"
        kind = "direct" if direct else "dependent"
        counts[kind] += 1
        cases.append({"case_id": f"staged-{kind}-{counts[kind]:02d}",
            "category": "staged_direct_annotation" if direct else "staged_dependent_prefix",
            "example": copy.deepcopy(example), "annotation": copy.deepcopy(sidecar), "audit": None,
            "profiles": {}, "primary_profile": "formal", "selection_reasons": [sidecar["kind"]],
            "quality_revision_sha256": revision, "enters_effective_training": False, "semantic_verdict": None})
    q.require(len(cases) == len({c["example"]["example_id"] for c in cases}) <= inputs["config"]["materials"]["new_case_limit_per_engine"],
              "review_unique_case_budget")
    q.require(counts["direct"] == manifest["annotations"]["direct_action_revisions"], "missing_direct_material")
    coverage.pop("human_review", None)
    coverage.update({"actual_count": 10, "staged_direct_count": counts["direct"],
        "staged_dependent_count": counts["dependent"], "distinct_count": len(cases),
        "quality_revision_sha256": revision, "semantic_review": "UNFILLED_FOR_DELEGATED_AI_REVIEW",
        "browser_actual_observation": "NOT_RUN", "new_annotations_enter_training": False,
        "old_quarantined_materials_used_as_effective": 0})
    return cases, coverage


def sequence_record(case, sequence):
    """Assert the full joined encoding, unique appended EOS and shifted padding."""
    validate_record(case["example"], "example")
    p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
    q.require(0 < p < n - 1 and n <= 32768, "material_sequence_budget")
    q.require(sequence.sequence_ids[:p] == sequence.prompt_ids
              and sequence.sequence_ids[:-1] == sequence.concatenated_ids, "material_joined_prefix")
    q.require(sequence.eos_token_id == 151645 and sequence.sequence_ids[-1] == 151645
              and sequence.sequence_ids[p:].count(151645) == 1, "material_eos")
    q.require(sequence.loss_mask == (0,) * p + (1,) * (n - p), "material_loss_mask")
    q.require(sequence.causal_input_ids == sequence.sequence_ids[:-1]
              and sequence.causal_target_ids == sequence.sequence_ids[1:]
              and sequence.causal_loss_mask == sequence.loss_mask[1:], "material_shift")
    q.require(sequence.completion_text == encode_action(case["example"]["expected_action"]), "material_action_binding")
    record = sequence.record()
    record.update(causal_input_ids=list(sequence.causal_input_ids), causal_target_ids=list(sequence.causal_target_ids))
    for key in ("causal_input_ids", "causal_target_ids"):
        record[key + "_sha256"] = canonical_hash(record[key])
    audit = case["audit"]
    if case["category"] == "effective_selected_train":
        q.require(audit is not None and audit["example_sha256"] == canonical_hash(case["example"]), "material_original_binding")
        measured = sequence.metadata() | {k: record[k] for k in ("causal_input_ids_sha256", "causal_target_ids_sha256")}
        q.require(all(audit.get(k) == v for k, v in measured.items()), "historical_representation_difference")
        bucket = case["profiles"][case["primary_profile"]]["padding_bucket"]
    else:
        q.require(audit is None and case["category"] in {"original_protocol_only", "staged_direct_annotation", "staged_dependent_prefix"},
                  "material_category")
        # This is a display bucket, never an expanded training or context limit.
        bucket = max(1024, ((n + 511) // 512) * 512)
    padded = pad_sequence(sequence, length=bucket, pad_token_id=151643)
    q.require(padded.sequence_ids == sequence.sequence_ids + (151643,) * (bucket - n)
              and padded.attention_mask == (1,) * n + (0,) * (bucket - n)
              and padded.loss_mask == sequence.loss_mask + (0,) * (bucket - n), "material_padding")
    q.require(sum(padded.causal_loss_mask) == n - p and padded.causal_loss_mask[p - 1] == 1
              and padded.causal_loss_mask[n - 2] == 1 and not any(padded.causal_loss_mask[n - 1:]), "material_supervised_targets")
    return {"case": copy.deepcopy(case), "sequence": record,
        "source_binding": {**{k: case["example"][k] for k in q.IDENTITY},
            "example_sha256": canonical_hash(case["example"]),
            "model_input_sha256": canonical_hash({k: case["example"][k] for k in ("messages", "tools")}),
            "action_sha256": canonical_hash(case["example"]["expected_action"])},
        "budget_observations": {"context_including_eos": {str(cap): n <= cap for cap in (1024, 1536, 2048)},
            "response_256_including_eos": n - p <= 256, "used_to_promote_staged_annotation": False},
        "padding": {"bucket": bucket, "pad_token_id": 151643, "unpadded_length": n,
            "sequence_ids": list(padded.sequence_ids), "attention_mask": list(padded.attention_mask),
            "loss_mask": list(padded.loss_mask), "causal_input_ids": list(padded.causal_input_ids),
            "causal_target_ids": list(padded.causal_target_ids), "causal_loss_mask": list(padded.causal_loss_mask),
            "effective_supervised_targets": n - p, "first_supervised_causal_position": p - 1,
            "last_supervised_causal_position": n - 2}}


def render_page(record):
    """Static local review text; source values cannot become executable markup."""
    case, seq, pad = record["case"], record["sequence"], record["padding"]
    texts = record["token_texts"]
    q.require(len(texts) == pad["bucket"], "material_token_text_count")

    def esc(value):
        return html.escape(str(value), quote=True)

    def block(label, value, literal=False):
        text = value if literal else json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        return f"<h2>{esc(label)}</h2><pre>{esc(text)}</pre>"

    page = ['<!doctype html><html lang="zh"><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>ToolAlign 质量修订复核</title><style>body{font:15px system-ui;margin:28px;max-width:1400px;color:#172536;background:#fafbfd}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf2f7;padding:16px}table{border-collapse:collapse;width:100%;font:13px monospace}td,th{border:1px solid #bdcbdc;padding:6px;white-space:pre-wrap;overflow-wrap:anywhere}th{position:sticky;top:0;background:#dee9f4}.scroll{max-height:650px;overflow:auto}.completion{background:#fff0cb}.eos{background:#cdf1dc}.padding{background:#e9e9e9}</style>',
        f'<h1>{esc(case["case_id"])} · {esc(case["category"])}</h1>',
        '<p>本页供委托 AI 或独立审阅者复核，语义结论尚未填写。协议例和 staging 候选均不进入有效训练集合。数组结构检查不构成语义通过。</p>',
        '<p>历史工具观察没有重新执行。UNVERIFIED_AFTER_ACTION_CHANGE 表示前序 Action 已变更，原观察及其后续条件仍未验证。</p>',
        '<p>位置从 0 开始；P−1 位置开始预测目标 Action，N−2 位置预测唯一追加 EOS。prompt 与右 padding 不计入 loss。单 token 文字仅辅助阅读。</p>',
        block("用途、选择规则与修订来源", {k: v for k, v in case.items() if k not in ("example", "audit")}),
        block("完整 Example 与来源身份", case["example"]),
        block("原序列依据（仅有效原例继承）", case["audit"]),
        block("新测序列的身份与预算观察", {"source_binding": record["source_binding"], "budget_observations": record["budget_observations"]}),
        block("P：精确 prompt", seq["prompt_text"], True),
        block("C：精确 Action；EOS 单独追加", seq["completion_text"], True),
        '<details><summary>全部 token、padding 与 next-token 表</summary><div class="scroll"><table><thead><tr><th>position</th><th>segment</th><th>input ID</th><th>单 token 文字</th><th>attention</th><th>token loss</th><th>next target ID</th><th>shifted loss</th></tr></thead><tbody>']
    p, n = seq["prompt_tokens"], seq["total_tokens"]
    for i, token in enumerate(pad["sequence_ids"]):
        segment = "prompt" if i < p else "completion" if i < n - 1 else "eos" if i == n - 1 else "padding"
        target = pad["causal_target_ids"][i] if i < pad["bucket"] - 1 else "—"
        mask = pad["causal_loss_mask"][i] if i < pad["bucket"] - 1 else "—"
        cells = (i, segment, token, texts[i], pad["attention_mask"][i], pad["loss_mask"][i], target, mask)
        page.append(f'<tr class="{segment}">' + "".join(f"<td>{esc(c)}</td>" for c in cells) + "</tr>")
    page.append('</tbody></table></div></details>')
    page.append(block("全部未 padding IDs / mask / shift / EOS / hash", seq))
    page.append(block("全部右 padding、attention 和 shifted loss", pad))
    page.append('</html>')
    return "\n".join(page)


def consumer_identity():
    result = q.consumer_identity()
    for name in ("data/quality_materials.py", "data/training_review.py", "model_io/sequence.py", "model_io/offline.py"):
        result["package_files"][name] = q.sha(files("toolalign").joinpath(name).read_bytes())
    return result


def case_names(counts):
    return {f"effective-{i:02d}" for i in range(1, 11)} | {"protocol-" + k for k in ("final", "clarify", "refuse")} | {
        f"staged-{kind}-{i:02d}" for kind in ("direct", "dependent") for i in range(1, counts[kind] + 1)}


def write_measurement(cases, coverage, *, tokenizers_by_profile, output, revision_manifest_sha256):
    q.require(not Path(output).exists() and not Path(output).is_symlink(), "output_already_exists")
    q.require(not q.MODEL_ROOTS & {n.split(".", 1)[0] for n in sys.modules}, "cpu_only_process_required")
    categories = Counter(c["category"] for c in cases)
    counts = {"direct": categories["staged_direct_annotation"], "dependent": categories["staged_dependent_prefix"]}
    names = case_names(counts)
    q.require(categories["effective_selected_train"] == 10 and categories["original_protocol_only"] == 3
              and categories["staged_direct_annotation"] >= 1
              and len(cases) == len(names) == len({c["case_id"] for c in cases})
              == len({c["example"]["example_id"] for c in cases}) <= 20
              and {c["case_id"] for c in cases} == names, "material_unique_denominator")
    q.require(set(tokenizers_by_profile) == set(q.PROFILES), "material_tokenizer_profiles")
    identities = {k: v.identity for k, v in tokenizers_by_profile.items()}
    for profile, repo, revision in (("smoke", "Qwen/Qwen3-0.6B", "c1899de289a04d12100db370d81485cdf75e47ca"),
                                   ("formal", "Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e")):
        q.require(identities[profile]["repo_id"] == repo and identities[profile]["revision"] == revision,
                  "material_tokenizer_model")
    artifacts, records = {}, []
    for case in cases:
        adapter = tokenizers_by_profile[case["primary_profile"]]
        record = sequence_record(case, adapter.training_sequence(case["example"]))
        record["token_texts"] = [adapter.decode([i], skip_special_tokens=False) for i in record["padding"]["sequence_ids"]]
        q.require(adapter.decode(record["sequence"]["concatenated_ids"][record["sequence"]["prompt_tokens"]:],
                                 skip_special_tokens=False) == record["sequence"]["completion_text"], "material_decoded_action")
        name = case["case_id"]
        artifacts[name + ".json"] = encoded(record) + b"\n"
        artifacts[name + ".html"] = render_page(record).encode("utf-8")
        records.append(record)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(("case_id", "category", "example_id", "example_sha256", "quality_revision_sha256",
                     "reviewer", "semantic_verdict", "token_mask_verdict", "reviewed_at_utc", "notes"))
    for record in records:
        case = record["case"]
        writer.writerow((case["case_id"], case["category"], case["example"]["example_id"], canonical_hash(case["example"]),
                         case["quality_revision_sha256"], "", "", "", "", ""))
    artifacts["review.csv"] = stream.getvalue().encode("utf-8")
    artifacts["index.html"] = ('<!doctype html><html lang="zh"><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; base-uri \'none\'; form-action \'none\'">'
        '<title>ToolAlign 质量修订材料</title><h1>质量修订复核</h1>'
        '<p>10 个有效 train 原例、3 个原创协议例，以及独立 staging 候选。语义和 token/mask 判定列均空；浏览器实显 NOT_RUN。</p><ul>'
        + "".join(f'<li><a href="{c["case_id"]}.html">{html.escape(c["case_id"])} · {html.escape(c["category"])}</a></li>' for c in cases)
        + '</ul></html>').encode("utf-8")
    q.require(not q.MODEL_ROOTS & {n.split(".", 1)[0] for n in sys.modules}, "model_dependency_imported")
    manifest = {"manifest_version": "toolalign.quality-token-review.v1", "coverage": coverage,
        "revision_manifest_sha256": revision_manifest_sha256, "quality_revision_sha256": coverage["quality_revision_sha256"],
        "tokenizers": identities, "consumer": consumer_identity(), "case_order": [c["case_id"] for c in cases],
        "categories": dict(categories), "unique_examples": len(cases), "records_sha256": canonical_hash(records),
        "artifacts": {k: {"sha256": q.sha(v), "size_bytes": len(v)} for k, v in artifacts.items()},
        "model_modules_loaded": [], "external_execution": "NOT_RUN", "browser_actual_observation": "NOT_RUN",
        "semantic_review": "UNFILLED_FOR_DELEGATED_AI_REVIEW", "trainer_collator": "NOT_RUN", "training_authorized": False}
    artifacts["manifest.json"] = encoded(manifest) + b"\n"
    run = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "consumer": consumer_identity(),
           "stable_manifest_sha256": q.sha(artifacts["manifest.json"]), "model_modules_loaded": [],
           "training_authorized": False, "output_path": str(Path(output).resolve())}
    q.publish(output, artifacts, run)
    return manifest


def checked_measurement(root, engine):
    root = Path(root).resolve()
    q.require(root.is_dir() and ".toolalign-local" in root.parts, "private_output_required")
    manifest_data = (root / "manifest.json").read_bytes()
    manifest = loads(manifest_data.decode())
    q.require(manifest["manifest_version"] == "toolalign.quality-token-review.v1"
              and manifest["training_authorized"] is False and manifest["model_modules_loaded"] == []
              and manifest["semantic_review"] == "UNFILLED_FOR_DELEGATED_AI_REVIEW"
              and manifest["browser_actual_observation"] == "NOT_RUN", "measurement_scope")
    q.require(all(t["engine"] == engine for t in manifest["tokenizers"].values()), "measurement_engine")
    order = manifest["case_order"]
    counts = {"direct": manifest["categories"].get("staged_direct_annotation", 0),
              "dependent": manifest["categories"].get("staged_dependent_prefix", 0)}
    q.require(set(order) == case_names(counts) and len(order) == len(set(order)) <= 20, "measurement_case_set")
    names = {n + ext for n in order for ext in (".json", ".html")} | {"index.html", "review.csv"}
    q.require(set(manifest["artifacts"]) == names, "measurement_artifact_set")
    q.require(not any(p.is_symlink() for p in root.rglob("*")), "output_symlink")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    q.require(actual == names | {"manifest.json", "run.json"}, "measurement_extra_or_missing_artifact")
    data = q.checked_bundle(root, manifest["artifacts"], names)
    records = [loads(data[n + ".json"].decode()) for n in order]
    q.require(canonical_hash(records) == manifest["records_sha256"]
              and len(records) == manifest["unique_examples"], "measurement_record_hash")
    for name, record in zip(order, records, strict=True):
        case = record["case"]
        q.require(case["case_id"] == name and case["quality_revision_sha256"] == manifest["quality_revision_sha256"]
                  and case["semantic_verdict"] is None, "measurement_case_identity")
        q.require(data[name + ".html"] == render_page(record).encode(), "measurement_static_html")
        q.require(record["source_binding"]["example_sha256"] == canonical_hash(case["example"]), "measurement_example_binding")
    rows = q.csv_rows(data["review.csv"])
    q.require(len(rows) == len(records), "measurement_csv_count")
    for row, record in zip(rows, records, strict=True):
        case = record["case"]
        q.require(row["case_id"] == case["case_id"] and row["category"] == case["category"]
                  and row["example_id"] == case["example"]["example_id"]
                  and row["example_sha256"] == canonical_hash(case["example"])
                  and row["quality_revision_sha256"] == manifest["quality_revision_sha256"], "measurement_csv_identity")
        q.require(all(row[k] == "" for k in ("reviewer", "semantic_verdict", "token_mask_verdict", "reviewed_at_utc", "notes")),
                  "measurement_verdict_prefilled")
    run = loads((root / "run.json").read_text(encoding="utf-8"))
    q.require(run["stable_manifest_sha256"] == q.sha(manifest_data)
              and run["consumer"] == manifest["consumer"] and run["model_modules_loaded"] == []
              and run["training_authorized"] is False, "measurement_run_binding")
    q.require(manifest["consumer"]["package_files"] == consumer_identity()["package_files"], "measurement_consumer_changed")
    return manifest, records


def measure(*, inputs_path, revision, tokenizer_root, engine, output):
    q.require(all(os.environ.get(n) == "0" for n in ("USE_TORCH", "USE_TF", "USE_FLAX"))
              and all(os.environ.get(n) == "1" for n in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")), "offline_cpu_environment_required")
    from toolalign.model_io.offline import OfflineQwenTokenizer, model_modules_loaded

    q.require(not model_modules_loaded(), "cpu_only_process_required")
    paths = loads(Path(inputs_path).read_text(encoding="utf-8"))
    inputs = q.bound_inputs(**paths)
    artifacts, manifest = q.stable_artifacts(inputs)
    q.verify_artifacts(revision, artifacts)
    cases, coverage = choose_cases(inputs, artifacts, manifest)
    adapters = {p: OfflineQwenTokenizer(tokenizer_root, engine=engine, repo_id=spec["model_id"], revision=spec["model_revision"])
                for p, spec in inputs["parent_config"]["profiles"].items()}
    return write_measurement(cases, coverage, tokenizers_by_profile=adapters, output=output,
                             revision_manifest_sha256=q.sha(artifacts["manifest.json"]))


def compare(*, reference, native):
    left, left_records = checked_measurement(reference, "transformers")
    right, right_records = checked_measurement(native, "tokenizers")
    q.require(left_records == right_records, "engine_records_differ")
    q.require(all(left[k] == right[k] for k in ("coverage", "categories", "revision_manifest_sha256", "quality_revision_sha256")),
              "engine_input_binding_differ")
    for profile in q.PROFILES:
        a, b = left["tokenizers"][profile], right["tokenizers"][profile]
        for key in ("repo_id", "revision", "files", "template_sha256", "eos_token", "eos_token_id", "render_parameters", "encoding_parameters"):
            q.require(a[key] == b[key], "engine_tokenizer_identity_differ")
    return {"status": "PASS_COMPLETE_RECORD_EQUALITY", "unique_examples": len(left_records),
        "engine_measurements": 2 * len(left_records), "categories": left["categories"],
        "quality_revision_sha256": left["quality_revision_sha256"], "records_sha256": left["records_sha256"],
        "reference_manifest_sha256": q.sha((Path(reference) / "manifest.json").read_bytes()),
        "native_manifest_sha256": q.sha((Path(native) / "manifest.json").read_bytes()),
        "static_html_exact": True, "browser_actual_observation": "NOT_RUN", "semantic_verdicts_filled": 0,
        "candidate_budget_observations": {r["case"]["case_id"]: r["budget_observations"] for r in left_records
                                          if r["case"]["category"].startswith("staged_")},
        "training_authorized": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("measure")
    for flag in ("inputs-path", "revision", "tokenizer-root", "output"):
        command.add_argument("--" + flag, required=True, type=Path)
    command.add_argument("--engine", required=True, choices=("transformers", "tokenizers"))
    command = sub.add_parser("compare")
    for flag in ("reference", "native"):
        command.add_argument("--" + flag, required=True, type=Path)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        result = {"measure": measure, "compare": compare}[command](**args)
    except (DataError, ContractError, ModelIOError, OSError, KeyError, TypeError, ValueError, IndexError) as exc:
        print(encoded({"status": "FAIL", "error_type": type(exc).__name__,
                       "error_code": str(exc) if type(exc) in (DataError, ModelIOError) else "invalid_input_or_io"}).decode())
        return 1
    if command == "measure":
        result = {"status": "PASS_CPU_MATERIAL_MEASUREMENT", "categories": result["categories"],
                  "unique_examples": result["unique_examples"], "quality_revision_sha256": result["quality_revision_sha256"],
                  "records_sha256": result["records_sha256"], "model_modules_loaded": result["model_modules_loaded"],
                  "training_authorized": False, "semantic_review": result["semantic_review"]}
    print(encoded(result).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
