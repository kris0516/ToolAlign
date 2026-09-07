"""Use the sealed R1 original/changed pages and small in-memory array mutations.

This reads existing records and pages only. It does not tokenize, render new
material, execute HTML, or change the supplied fixtures. Source data stays local.
"""

import argparse
import copy
import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[3] / "reports/data/quality-audit-r1"
    sys.path.insert(0, str(source))
    checker = importlib.import_module("check_materials")
    assert Path(checker.__file__).resolve() == source / "check_materials.py"
    inputs = {name: (args.fixture / name).read_bytes()
              for name in ("record.json", "original.html", "modified.html")}
    descriptor_bytes = args.descriptor.read_bytes()
    record = json.loads(inputs["record.json"])
    descriptor = json.loads(descriptor_bytes)
    page = inputs["original.html"].decode()
    assert checker.inspect_record(record, page, descriptor)["static_html_content_exact"] is True
    results = {"original_page": "PASS"}

    def reject(name, candidate, html):
        try:
            checker.inspect_record(candidate, html, descriptor)
        except AssertionError:
            results[name] = "REJECTED"
        else:
            raise AssertionError("Type-changed fixture was accepted: " + name)

    reject("r1_displayed_false_to_zero", record, inputs["modified.html"].decode())
    for name in ("loss_mask", "causal_loss_mask"):
        candidate = copy.deepcopy(record)
        values = candidate["sequence"][name]
        index = next(i for i, value in enumerate(values) if value == 0)
        values[index] = False
        # A refreshed array hash must not bypass the independent type check.
        candidate["sequence"][name + "_sha256"] = checker.canonical(values)
        reject("sequence_" + name + "_false", candidate, page)
    for name in ("attention_mask", "loss_mask"):
        candidate = copy.deepcopy(record)
        values = candidate["padding"][name]
        index = next(i for i, value in enumerate(values) if value == 1)
        values[index] = True
        reject("padding_" + name + "_true", candidate, page)
    candidate = copy.deepcopy(record)
    candidate["sequence"]["sequence_ids"][0] = float(candidate["sequence"]["sequence_ids"][0])
    candidate["sequence"]["sequence_sha256"] = checker.canonical(candidate["sequence"]["sequence_ids"])
    reject("token_id_float", candidate, page)
    candidate = copy.deepcopy(record)
    candidate["sequence"]["append_eos_count"] = True
    reject("eos_count_bool", candidate, page)
    candidate = copy.deepcopy(record)
    contexts = candidate["budget_observations"]["context_including_eos"]
    key = next(iter(contexts))
    contexts[key] = int(contexts[key])
    reject("budget_boolean_to_integer", candidate, page)
    for name, payload in inputs.items():
        assert (args.fixture / name).read_bytes() == payload
    assert args.descriptor.read_bytes() == descriptor_bytes
    result = {"status": "PASS", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "checks": results, "input_sha256": {k: hashlib.sha256(v).hexdigest() for k, v in inputs.items()},
              "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
              "source_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                                for name in ("check_materials.py", "json_values.py")},
              "new_tokenizer_or_model_runs": 0, "original_materials_modified": False}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "checks": results}, sort_keys=True))


if __name__ == "__main__":
    main()
