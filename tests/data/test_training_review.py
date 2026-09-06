"""Original HTML/shift review cases; these character tokens are not Qwen IDs."""

import copy
import json
from dataclasses import replace
from html.parser import HTMLParser

import pytest
from training_binding_cases import config, example, row

from toolalign.data.common import DataError
from toolalign.data.training_review import choose_review_cases, render_page, sequence_record
from toolalign.data.training_selection import select_examples
from toolalign.model_io import TEMPLATE_SHA256, training_sequence


def protocol_examples():
    return [example("protocol-" + k, kind=k, content="原创协议检查：" + k) for k in ("final", "clarify", "refuse")]


def plan():
    values = [example("selected-" + str(i), content="原创回答" if i == 5 else "Original answer.") for i in range(12)]
    measured = [row(e, p=100 + i * 10) for i, e in enumerate(values)]
    return select_examples({"train": values, "validation": []}, measured, config())


def test_exactly_ten_distinct_actual_selected_and_three_protocol_cases():
    source = plan()
    before = copy.deepcopy(source)
    cases, coverage = choose_review_cases(source, protocol_examples())
    assert len(cases) == len({c["example"]["example_id"] for c in cases}) == 13
    assert {c["example"]["example_id"] for c in cases[:10]} <= {
        e["example_id"] for e in source["formal"]["train"]["examples"]}
    assert cases[0]["example"]["example_id"] == "selected-0"
    assert cases[1]["example"]["example_id"] == "selected-11"
    assert coverage["actual_materials"]["non_ascii"] >= 1
    assert coverage["available_in_selected_train"]["observation_history"] == 0
    assert {c["example"]["expected_action"]["kind"] for c in cases[10:]} == {"final", "clarify", "refuse"}
    assert all(not c["profiles"] and c["audit"] is None for c in cases[10:])
    assert source == before
    for profile in source.values():
        profile["train"]["examples"].reverse()
        profile["train"]["sidecars"].reverse()
    assert choose_review_cases(source, list(reversed(protocol_examples()))) == (cases, coverage)


@pytest.mark.parametrize("failure", ["wrong_sidecar", "too_few", "protocol_overlap", "duplicate_protocol"])
def test_review_case_binding_failures(failure):
    source, protocols = plan(), protocol_examples()
    if failure == "wrong_sidecar":
        source["smoke"]["train"]["sidecars"][0]["audit"]["example_sha256"] = "f" * 64
    elif failure == "too_few":
        for profile in source.values():
            for key in ("examples", "sidecars"):
                profile["train"][key] = profile["train"][key][:2]
    elif failure == "protocol_overlap":
        protocols[0]["example_id"] = source["formal"]["train"]["examples"][0]["example_id"]
    else:
        protocols[1]["example_id"] = protocols[0]["example_id"]
    with pytest.raises(DataError):
        choose_review_cases(source, protocols)


def original_sequence():
    value = example("html-case", content='保留 </pre><script>alert(42)</script> & "文本"')
    value["messages"][0]["content"] = '</pre><img src="https://invalid.invalid/a" onerror="alert(42)">'
    ptext = "PROMPT"
    sequence = training_sequence(value, renderer=lambda *a, **k: ptext,
        encoder=lambda text, **kw: [151645] if text == "<|im_end|>" else [ord(c) for c in text],
        decoder=lambda ids, **kw: "".join(chr(i) for i in ids),
        eos_token_id=151645, template_sha256=TEMPLATE_SHA256)
    case = {"case_id": "protocol-final", "category": "original_protocol_only", "example": value,
            "audit": None, "profiles": {}, "primary_profile": "smoke", "selection_reasons": []}
    return case, sequence


def test_full_padding_and_next_token_positions_keep_eos_and_supervision_denominator():
    case, sequence = original_sequence()
    result = sequence_record(case, sequence)
    pad = result["padding"]
    p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
    assert pad["causal_target_ids"][p - 1] == ord("{")
    assert pad["causal_target_ids"][n - 2] == 151645
    assert pad["causal_target_ids"][n - 1] == 151643
    assert pad["causal_loss_mask"][p - 2:p] == [0, 1]
    assert pad["causal_loss_mask"][n - 2:n] == [1, 0]
    assert sum(pad["causal_loss_mask"]) == len(sequence.completion_text) + 1
    assert len(pad["sequence_ids"]) == len(pad["attention_mask"]) == len(pad["loss_mask"]) == 1024
    assert len(pad["causal_input_ids"]) == len(pad["causal_target_ids"]) == len(pad["causal_loss_mask"]) == 1023


@pytest.mark.parametrize("failure", ["eos", "mask", "prefix", "history_hash"])
def test_sequence_eos_mask_and_historical_identity_fail_closed(failure):
    case, sequence = original_sequence()
    if failure == "eos":
        sequence = replace(sequence, sequence_ids=sequence.sequence_ids[:-1] + (151643,))
    elif failure == "mask":
        sequence = replace(sequence, loss_mask=(1,) * len(sequence.sequence_ids))
    elif failure == "prefix":
        sequence = replace(sequence, prompt_ids=(99,) + sequence.prompt_ids[1:])
    else:
        case["audit"] = sequence.metadata() | {"prompt_sha256": "0" * 64}
    with pytest.raises(DataError):
        sequence_record(case, sequence)


def test_html_injection_becomes_text_and_every_token_is_present():
    case, sequence = original_sequence()
    record = sequence_record(case, sequence)
    rendered = render_page(record, ['</td><script>alert("x")</script>'] * record["padding"]["bucket"])

    class Tags(HTMLParser):
        def __init__(self):
            super().__init__()
            self.names, self.row_count, self.data = [], 0, []

        def handle_starttag(self, tag, attrs):
            self.names.append(tag)
            self.row_count += tag == "tr"
            assert not any(k.startswith("on") for k, _ in attrs)

        def handle_data(self, data):
            self.data.append(data)

    tags = Tags()
    tags.feed(rendered)
    assert not {"script", "img", "iframe", "a", "form", "object"} & set(tags.names)
    assert tags.row_count == record["padding"]["bucket"] + 1
    visible = "".join(tags.data)
    assert json.dumps(case["example"]["expected_action"]["content"], ensure_ascii=False)[1:-1] in visible
    assert json.dumps(case["example"]["messages"][0]["content"], ensure_ascii=False)[1:-1] in visible
    assert "default-src 'none'" in rendered
    assert "全部 token" in visible
