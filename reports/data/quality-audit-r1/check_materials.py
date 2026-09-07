"""Inspect sealed token records and static HTML without running a tokenizer.

This checks every array position, inverse message binding and displayed table
cell. It never computes a semantic verdict or certifies browser rendering.
"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from json_values import json_equal, json_key


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return sha(encoded(value).encode())


def wire_json(value):
    return encoded(value).replace("<", "\\u003c").replace(">", "\\u003e")


def expected_prompt(example, descriptor):
    """Independent text construction for the pinned role-preserving protocol."""
    catalog = {"format_version": descriptor["format_id"], "tools": example["tools"]}
    result = "<|im_start|>system\n" + descriptor["instruction"] + "\n" + wire_json(catalog) + "<|im_end|>\n"
    messages = example["messages"]
    for index, message in enumerate(messages):
        value = wire_json({"message_index": index, "message": message})
        role = message["role"]
        if role == "tool":
            if index == 0 or messages[index - 1]["role"] != "tool":
                result += "<|im_start|>user"
            result += "\n<tool_response>\n" + value + "\n</tool_response>"
            if index == len(messages) - 1 or messages[index + 1]["role"] != "tool":
                result += "<|im_end|>\n"
        else:
            result += "<|im_start|>" + role + "\n" + value + "<|im_end|>\n"
    return result + "<|im_start|>assistant\n<think>\n\n</think>\n\n"


class StaticPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pre = []
        self.rows = []
        self.cell = None
        self.row = None
        self.block = None
        self.active_tags = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "iframe", "object", "embed"}:
            self.active_tags.append(tag)
        if tag == "pre":
            assert self.block is None
            self.block = []
        elif tag == "tr":
            self.row = []
        elif tag == "td":
            assert self.cell is None
            self.cell = []

    def handle_endtag(self, tag):
        if tag == "pre":
            self.pre.append("".join(self.block))
            self.block = None
        elif tag == "td":
            self.row.append("".join(self.cell))
            self.cell = None
        elif tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.block is not None:
            self.block.append(data)
        if self.cell is not None:
            self.cell.append(data)


def inspect_record(record, page, descriptor):
    case = record["case"]
    example = case["example"]
    sequence = record["sequence"]
    padding = record["padding"]
    binding = record["source_binding"]
    assert json_equal(binding["example_id"], example["example_id"])
    assert binding["example_sha256"] == canonical(example)
    assert binding["action_sha256"] == canonical(example["expected_action"])
    assert binding["model_input_sha256"] == canonical({k: example[k] for k in ("messages", "tools")})
    for key in ("source", "source_revision", "source_record_hash", "group_id", "split"):
        assert json_equal(binding[key], example[key])
    if case["category"] != "original_protocol_only":
        assert example["example_id"] == canonical({k: v for k, v in example.items() if k not in {"example_id", "group_id", "split"}})
        assert example["split"] == "train"
    if case["category"] != "effective_selected_train":
        assert case["enters_effective_training"] is False
    if "annotation" in case:
        annotation = case["annotation"]
        assert json_equal(annotation["example_id"], example["example_id"])
        assert annotation["example_sha256"] == binding["example_sha256"]
        assert annotation["candidate_model_input_sha256"] == binding["model_input_sha256"]
        assert annotation["candidate_action_sha256"] == binding["action_sha256"]
        assert annotation["enters_effective_training"] is False
        assert annotation["external_execution"] == "NOT_RUN"
        assert annotation["downstream_condition_verified"] is False

    prompt = expected_prompt(example, descriptor)
    completion = wire_json(example["expected_action"])
    assert sequence["prompt_text"] == prompt
    assert sequence["completion_text"] == completion
    assert json_equal(json.loads(completion), example["expected_action"])
    assert sequence["prompt_sha256"] == sha(prompt.encode())
    assert sequence["completion_sha256"] == sha(completion.encode())
    assert json_equal(sequence["completion_utf8_bytes"], len(completion.encode()))
    assert sequence["instruction_sha256"] == sha(descriptor["instruction"].encode())
    assert sequence["format_id"] == descriptor["format_id"]
    assert sequence["prefix_stable"] is True
    ids, prompt_ids = sequence["sequence_ids"], sequence["prompt_ids"]
    for values in (ids, prompt_ids):
        assert type(values) is list and all(type(v) is int and v >= 0 for v in values)
    p, n = len(prompt_ids), len(ids)
    c = n - p - 1
    assert p > 0 and c > 0
    assert json_equal(sequence["prompt_tokens"], p)
    assert json_equal(sequence["total_tokens"], n)
    assert json_equal(sequence["completion_tokens"], c)
    assert json_equal(sequence["completion_tokens_including_eos"], c + 1)
    assert json_equal(ids[:p], prompt_ids)
    assert json_equal(sequence["concatenated_ids"], ids[:-1])
    assert json_equal(ids[-1], 151645) and json_equal(sequence["eos_token_id"], 151645)
    assert ids[p:].count(151645) == 1 and json_equal(sequence["append_eos_count"], 1)
    mask = [int(i >= p) for i in range(n)]
    assert json_equal(sequence["loss_mask"], mask)
    assert json_equal(sequence["causal_input_ids"], ids[:-1])
    assert json_equal(sequence["causal_target_ids"], ids[1:])
    assert json_equal(sequence["causal_loss_mask"], mask[1:])
    assert json_equal(sequence["first_supervised_causal_position"], p - 1)
    assert json_equal(sequence["last_supervised_causal_position"], n - 2)
    hash_fields = {"sequence_ids": "sequence_sha256"}
    for name in ("prompt_ids", "concatenated_ids", "loss_mask", "causal_loss_mask", "causal_input_ids", "causal_target_ids"):
        hash_fields[name] = name + "_sha256"
    for name, field in hash_fields.items():
        assert sequence[field] == canonical(sequence[name])

    bucket = padding["bucket"]
    assert type(bucket) is int and bucket >= n
    assert json_equal(padding["unpadded_length"], n)
    assert json_equal(padding["pad_token_id"], 151643)
    padded = ids + [151643] * (bucket - n)
    attention = [int(i < n) for i in range(bucket)]
    loss = [int(p <= i < n) for i in range(bucket)]
    assert json_equal(padding["sequence_ids"], padded)
    assert json_equal(padding["attention_mask"], attention)
    assert json_equal(padding["loss_mask"], loss)
    assert json_equal(padding["causal_input_ids"], padded[:-1])
    assert json_equal(padding["causal_target_ids"], padded[1:])
    assert json_equal(padding["causal_loss_mask"], loss[1:])
    assert json_equal(padding["effective_supervised_targets"], c + 1)
    assert sum(loss) == sum(loss[1:]) == c + 1
    assert json_equal(padding["first_supervised_causal_position"], p - 1)
    assert json_equal(padding["last_supervised_causal_position"], n - 2)
    texts = record["token_texts"]
    assert type(texts) is list and all(type(t) is str for t in texts)
    assert len(texts) == bucket
    assert texts[n - 1] == "<|im_end|>"
    assert all(t == "<|endoftext|>" for t in texts[n:])
    budget = record["budget_observations"]
    assert budget["used_to_promote_staged_annotation"] is False
    assert json_equal(budget["response_256_including_eos"], c + 1 <= 256)
    assert json_equal(budget["context_including_eos"], {str(size): n <= size for size in (1024, 1536, 2048)})

    parsed = StaticPage()
    parsed.feed(page)
    parsed.close()
    assert not parsed.active_tags
    assert prompt in parsed.pre and completion in parsed.pre
    json_blocks = set()
    for block in parsed.pre:
        try:
            json_blocks.add(json_key(json.loads(block)))
        except json.JSONDecodeError:
            pass
    # The revised material page shows the complete Example (including its full
    # ModelInput), rather than the older page's standalone ModelInput block.
    for expected in (example, example["expected_action"], sequence, padding):
        assert json_key(expected) in json_blocks
    assert len(parsed.rows) == bucket
    for i, row in enumerate(parsed.rows):
        segment = "prompt" if i < p else "completion" if i < n - 1 else "eos" if i == n - 1 else "padding"
        target = padded[i + 1] if i < bucket - 1 else "—"
        shifted = loss[i + 1] if i < bucket - 1 else "—"
        expected = (i, segment, padded[i], texts[i], attention[i], loss[i], target, shifted)
        assert row == [str(v) for v in expected], (case["case_id"], i)

    boundaries = []
    for i in sorted({0, p - 2, p - 1, p, p + 1, n - 2, n - 1, n, bucket - 1}):
        if 0 <= i < bucket:
            boundaries.append(parsed.rows[i])
    return {"case_id": case["case_id"], "category": case["category"], "example_id": example["example_id"],
            "prompt_tokens": p, "completion_without_eos": c, "completion_with_eos": c + 1,
            "total_tokens": n, "padding_bucket": bucket, "padding_tokens": bucket - n,
            "first_supervised_causal_position": p - 1, "last_supervised_causal_position": n - 2,
            "all_array_positions_checked": True, "all_html_token_rows_checked": bucket,
            "prompt_inverse_exact": True, "completion_action_exact": True,
            "static_html_content_exact": True, "boundary_rows": boundaries,
            "budget_observations": budget, "semantic_verdict": "NOT_COMPUTED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    descriptor_bytes = args.descriptor.read_bytes()
    descriptor = json.loads(descriptor_bytes)
    assert sha(descriptor_bytes) == "e985dd734a6e3478eb14f80d702e1c79817e955d488e6a37ceeab857b4a79207"
    manifests = {name: json.loads((args.inputs / name / "manifest.json").read_text()) for name in ("review-reference", "review-native")}
    assert json_equal(manifests["review-reference"]["case_order"], manifests["review-native"]["case_order"])
    results, records, vocabulary = [], [], {}
    for name in manifests["review-reference"]["case_order"]:
        pair = []
        for engine, manifest in manifests.items():
            payload = (args.inputs / engine / (name + ".json")).read_bytes()
            assert sha(payload) == manifest["artifacts"][name + ".json"]["sha256"]
            pair.append(json.loads(payload))
        assert json_equal(pair[0], pair[1])
        record = pair[0]
        page = (args.inputs / "review-reference" / (name + ".html")).read_bytes()
        assert sha(page) == manifests["review-reference"]["artifacts"][name + ".html"]["sha256"]
        assert page == (args.inputs / "review-native" / (name + ".html")).read_bytes()
        results.append(inspect_record(record, page.decode(), descriptor))
        for token, text in zip(record["padding"]["sequence_ids"], record["token_texts"], strict=True):
            if token in vocabulary:
                assert vocabulary[token] == text
            else:
                vocabulary[token] = text
        records.append(record)
    assert canonical(records) == manifests["review-reference"]["records_sha256"]
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "cases": results,
              "case_categories": dict(Counter(r["category"] for r in results)),
              "records_canonical_sha256": canonical(records), "unique_cases": len(results),
              "existing_engine_record_count": 2 * len(results), "token_text_id_consistent": True,
              "unique_observed_token_ids": len(vocabulary), "new_tokenizer_runs": 0,
              "new_model_or_framework_runs": 0, "browser_actual_observation": "NOT_RUN",
              "semantic_verdict": "NOT_COMPUTED", "training_authorized": False}
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"output_sha256": sha(args.output.read_bytes()), "unique_cases": len(results),
                      "html_token_rows": sum(r["all_html_token_rows_checked"] for r in results),
                      "unique_observed_token_ids": len(vocabulary)}, sort_keys=True))


if __name__ == "__main__":
    main()
