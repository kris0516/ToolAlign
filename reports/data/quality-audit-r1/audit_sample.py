"""Fixed offline source sampling for P02-QUALITY-AUDIT; no semantic verdicts.

Only train/validation Examples enter the pool. Held-out assignments and previous
review identities may be read as metadata; their source content is never exported.
All outputs, including sample identities and source packets, stay in this
worktree's ignored private directory. Dataset strings are never executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash, validate_record

CONFIG_SHA256 = "922b7807eef4aed3140b3679b702decbc93c319afcbd4e83e9ea1b7ea8745bb3"
ALLOWED_SPLITS = {"train", "validation"}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path):
    if sha256(path) != CONFIG_SHA256:
        raise ValueError("Configuration is not the S0-authorized audit policy")
    return json.loads(Path(path).read_text())


def jsonl(path, expected_sha256):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"Input hash mismatch: {Path(path).name}")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path, values):
    with Path(path).open("w") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def rank(source_hash, config):
    sampling = config["sampling"]
    return canonical_hash([sampling["rank_domain"], sampling["seed"], source_hash])


def patterns_for(examples, config):
    """Invoked parameters belong to valid decisions' expected tool calls.

    User text includes every user message in their complete prefixes. No keyword
    or structural trigger is a semantic finding or an automatic training rule.
    """
    user_text = "\n".join(
        msg["content"] for example in examples for msg in example["messages"]
        if msg["role"] == "user"
    )
    invoked = []
    for example in examples:
        tools = {tool["name"]: tool for tool in example["tools"]}
        for call in example["expected_action"]["tool_calls"]:
            schema = tools[call["name"]]["parameters_json_schema"]
            invoked.append((call["arguments"], schema))
    hits = []
    for pattern in config["patterns"]:
        name = pattern["name"]
        if name == "conditional_history":
            hit = bool(re.search(pattern["user_text_regex"], user_text, re.IGNORECASE)) or (
                len(examples) > pattern["or_valid_decision_count_greater_than"]
            )
        elif name == "identifier_scope":
            hit = any(
                re.search(
                    pattern["invoked_parameter_name_suffix_regex"],
                    re.sub("[^A-Za-z0-9]", "", key), re.IGNORECASE,
                )
                for arguments, _ in invoked for key in arguments
            )
        elif name == "unit_or_encoding":
            hit = any(
                re.search(
                    pattern["invoked_parameter_name_or_description_regex"],
                    key + " " + schema["properties"][key].get("description", ""),
                    re.IGNORECASE,
                )
                for arguments, schema in invoked for key in arguments
            )
        elif name == "relative_time":
            hit = bool(re.search(pattern["user_text_regex"], user_text, re.IGNORECASE))
        elif name == "parallel_object":
            hit = max(len(e["expected_action"]["tool_calls"]) for e in examples) >= (
                pattern["maximum_expected_tool_calls_at_least"]
            )
        elif name == "optional_arguments":
            hit = any(
                set(schema["properties"]) - set(schema.get("required", [])) - set(arguments)
                for arguments, schema in invoked
            )
        else:
            raise ValueError("Unknown configured diagnostic pattern")
        if hit:
            hits.append(name)
    return hits


def index_sources(examples_by_split, assignments, excluded_hashes, config):
    by_hash = defaultdict(list)
    for assignment in assignments:
        by_hash[assignment["source_record_hash"]].append(assignment)
    valid = defaultdict(list)
    invalid = []
    seen_ids = set()
    for split, examples in examples_by_split.items():
        if split not in ALLOWED_SPLITS:
            raise ValueError("Held-out Example input is forbidden")
        for line_number, example in enumerate(examples, 1):
            if example["split"] != split:
                raise ValueError("Example is in the wrong split file")
            source_hash = example["source_record_hash"]
            source_assignments = by_hash[source_hash]
            if not source_assignments or any(
                (a["split"], a["group_id"]) != (split, example["group_id"])
                for a in source_assignments
            ):
                raise ValueError("Example source/group/split disagrees with assignments")
            if example["example_id"] in seen_ids:
                raise ValueError("Duplicate Example identity")
            seen_ids.add(example["example_id"])
            try:
                validate_record(example, "example")
            except ContractError as exc:
                invalid.append({"split": split, "line": line_number,
                                "example_id": example["example_id"], "error": str(exc)})
                continue
            valid[source_hash].append(example)
    descriptors = {}
    for source_hash, examples in valid.items():
        indices = sorted({a["source_index"] for a in by_hash[source_hash]})
        descriptors[source_hash] = {
            "source_record_hash": source_hash,
            "source_index": indices[0],
            "source_indices": indices,
            "split": examples[0]["split"],
            "group_id": examples[0]["group_id"],
            "example_ids": sorted(e["example_id"] for e in examples),
            "valid_decision_count": len(examples),
            "categories": sorted({e["category"] for e in examples}),
            "pattern_hits": patterns_for(examples, config),
            "rank_sha256": rank(source_hash, config),
        }
    pool = {key: value for key, value in descriptors.items() if key not in excluded_hashes}
    return pool, descriptors, valid, invalid


def select_sources(pool, config):
    selected = []
    chosen = set()
    phases = []

    def take(label, candidates, requested):
        candidates = sorted(candidates, key=lambda row: (
            rank(row["source_record_hash"], config), row["source_record_hash"]
        ))
        available = [row for row in candidates if row["source_record_hash"] not in chosen]
        picked = available[:requested]
        phases.append({"phase": label, "candidate_pool": len(candidates),
                       "available_before_phase": len(available), "requested": requested,
                       "selected": len(picked), "shortfall": requested - len(picked)})
        for row in picked:
            chosen.add(row["source_record_hash"])
            selected.append({**row, "selection_phase": label})

    for split in ("train", "validation"):
        take("random/" + split, [row for row in pool.values() if row["split"] == split],
             config["sampling"]["random_by_split"][split])
    for pattern in config["patterns"]:
        name = pattern["name"]
        take("diagnostic/" + name,
             [row for row in pool.values() if name in row["pattern_hits"]],
             config["sampling"]["targeted_max_per_pattern"])
    if len(selected) > config["sampling"]["new_source_limit"]:
        raise ValueError("Selected sources exceed the fixed audit limit")
    if any(row["split"] not in ALLOWED_SPLITS for row in selected):
        raise ValueError("Held-out selection is forbidden")
    return selected, phases


def freeze(args):
    repository = Path(__file__).resolve().parents[3]
    output = args.output_root.resolve()
    if not output.is_relative_to(repository / ".toolalign-local"):
        raise ValueError("Audit outputs must remain in this worktree's private directory")
    config = load_config(args.config)
    bindings = config["input_bindings"]
    policy = args.policy_root
    delegated = args.delegated_root
    assignments = jsonl(policy / "assignments.jsonl", bindings["assignments_sha256"])
    examples = {split: jsonl(policy / (split + ".jsonl"), bindings[split + "_sha256"])
                for split in ("train", "validation")}
    samples = jsonl(policy / "human-review/samples.jsonl", bindings["old_semantic_samples_sha256"])
    if sha256(delegated / "token-original-sources.json") != (
        bindings["old_token_original_sources_sha256"]
    ):
        raise ValueError("Previous actual-token source identity mismatch")
    token_sources = json.loads((delegated / "token-original-sources.json").read_text())
    excluded = {row["source_record_hash"] for row in samples + token_sources}
    semantic_old = {row["source_record_hash"] for row in samples}
    token_old = {row["source_record_hash"] for row in token_sources}
    if sha256(delegated / "remediation_proposal.json") != bindings["remediation_proposal_sha256"]:
        raise ValueError("Prior issue proposal identity mismatch")
    proposal = json.loads((delegated / "remediation_proposal.json").read_text())
    prior_ids = sorted({row["source_record_hash"] for row in proposal["issues"]})
    if len(prior_ids) != config["prior_issue_review"]["source_count"] or not set(prior_ids) <= excluded:
        raise ValueError("Prior issue source population mismatch")
    # Discard prior prose and all unselected/held-out sample bodies before indexing.
    del proposal, samples, token_sources
    pool, descriptors, valid, invalid = index_sources(examples, assignments, excluded, config)
    selected, phases = select_sources(pool, config)
    prior = [descriptors[key] for key in prior_ids]
    if any(row["split"] != "train" for row in prior):
        raise ValueError("Prior issue source is not an effective train source")
    if set(prior_ids) & {row["source_record_hash"] for row in selected}:
        raise ValueError("Prior/new denominator overlap")
    output.mkdir(parents=True, exist_ok=False)
    ordered_pool = sorted(pool.values(), key=lambda row: row["source_record_hash"])
    write_jsonl(output / "pool-index.jsonl", ordered_pool)
    write_json(output / "invalid-examples.json", invalid)
    summary = {
        "valid_examples_by_split": dict(Counter(e["split"] for rows in valid.values() for e in rows)),
        "valid_sources_before_exclusions": dict(Counter(row["split"] for row in descriptors.values())),
        "eligible_sources_by_split": dict(Counter(row["split"] for row in pool.values())),
        "old_semantic_source_count": len(semantic_old), "old_token_source_count": len(token_old),
        "old_review_overlap": len(semantic_old & token_old), "excluded_union": len(excluded),
        "excluded_with_valid_allowed_examples": len(set(descriptors) & excluded),
        "invalid_example_count": len(invalid),
        "eligible_pattern_hits": {p["name"]: sum(p["name"] in row["pattern_hits"] for row in pool.values())
                                  for p in config["patterns"]},
        "category_source_denominators": dict(Counter(c for row in pool.values() for c in row["categories"])),
        "valid_decision_count_strata": dict(Counter(str(row["valid_decision_count"]) for row in pool.values())),
        "selection_phases": phases,
        "new_sources": len(selected), "prior_sources_separate": len(prior),
        "new_valid_decisions": sum(row["valid_decision_count"] for row in selected),
        "prior_valid_decisions": sum(row["valid_decision_count"] for row in prior),
        "heldout_selected": 0,
    }
    write_json(output / "pool-summary.json", summary)
    manifest = {
        "task": "P02-QUALITY-AUDIT", "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": sha256(args.config), "input_bindings": bindings,
        "sampler_sha256": sha256(__file__),
        "sampler_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "parameter_scope": "expected_action calls of all valid Examples",
        "user_text_scope": "all user messages in complete valid Example prefixes",
        "prior_sources": prior, "new_sources": selected, "phases": phases,
        "verdicts_started": False,
    }
    write_json(output / "sample-manifest.json", manifest)
    seal = {name: {"sha256": sha256(output / name), "bytes": (output / name).stat().st_size}
            for name in ("pool-index.jsonl", "pool-summary.json", "invalid-examples.json", "sample-manifest.json")}
    write_json(output / "sample-seal.json", {"sealed_at_utc": datetime.now(timezone.utc).isoformat(),
                                            "artifacts": seal})
    # Only after sealing identities, locate and export allowed raw source packets.
    if sha256(args.raw_source) != bindings["raw_source_sha256"]:
        raise ValueError("Raw source identity mismatch")
    raw_records = json.loads(args.raw_source.read_text())
    lineage = jsonl(policy / "lineage.jsonl", bindings["lineage_sha256"])
    selected_ids = {eid for row in prior + selected for eid in row["example_ids"]}
    selected_lineage = [row for row in lineage if row["example_id"] in selected_ids
                        and row["exclusion_reason"] is None]
    lineage_by_id = {row["example_id"]: row for row in selected_lineage}
    if set(lineage_by_id) != selected_ids or len(selected_lineage) != len(selected_ids):
        raise ValueError("Selected decisions lack unique effective lineage")
    packet_manifest = []
    (output / "packets").mkdir()
    for cohort, rows in (("prior", prior), ("new", selected)):
        for number, row in enumerate(rows, 1):
            source_hash = row["source_record_hash"]
            raw = raw_records[row["source_index"]]
            if canonical_hash(raw) != source_hash:
                raise ValueError("Raw source index/hash mismatch")
            decisions = sorted(valid[source_hash], key=lambda e: (
                lineage_by_id[e["example_id"]]["source_turn_index"], e["example_id"]
            ))
            for example in decisions:
                evidence = lineage_by_id[example["example_id"]]
                turn_index = evidence["source_turn_index"]
                original = raw["conversations"][turn_index]
                if (
                    evidence["source_record_hash"] != source_hash
                    or evidence["split"] != row["split"]
                    or evidence["group_id"] != row["group_id"]
                    or evidence["prefix_turn_end_exclusive"] != turn_index
                    or original["from"] != "assistant"
                    or hashlib.sha256(original["value"].encode()).hexdigest() != (
                        evidence["source_action_sha256"]
                    )
                ):
                    raise ValueError("Selected target/prefix lineage does not match original source")
                payload = {k: v for k, v in example.items()
                           if k not in {"example_id", "group_id", "split"}}
                if canonical_hash(payload) != example["example_id"]:
                    raise ValueError("Selected Example identity does not match normalized payload")
            packet = {"cohort": cohort, "identity": row, "source": raw,
                      "valid_decisions": [{"example": e, "lineage": lineage_by_id[e["example_id"]]}
                                          for e in decisions]}
            name = f"{cohort}-{number:03d}.json"
            write_json(output / "packets" / name, packet)
            packet_manifest.append({"packet": name, "sha256": sha256(output / "packets" / name),
                                    "source_record_hash": source_hash,
                                    "example_ids": row["example_ids"]})
    write_json(output / "packet-manifest.json", packet_manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("config", "policy-root", "delegated-root", "raw-source", "output-root"):
        parser.add_argument("--" + option, type=Path, required=True)
    freeze(parser.parse_args())
