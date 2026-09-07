"""Read a sealed fixture and vary its inert JSON display blocks in memory only."""

import argparse
import copy
import hashlib
import html
import importlib
import json
import re
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
    inputs = {name: (args.fixture / name).read_bytes() for name in ("record.json", "original.html")}
    descriptor_bytes = args.descriptor.read_bytes()
    record = json.loads(inputs["record.json"])
    page = inputs["original.html"].decode()
    descriptor = json.loads(descriptor_bytes)
    assert checker.inspect_record(record, page, descriptor)["static_html_content_exact"] is True
    checks = {"original_page": "PASS"}

    def replace_block(base_page, expected, replacement):
        matches = []
        for match in re.finditer(r"(<pre\b[^>]*>)(.*?)(</pre>)", base_page, re.DOTALL):
            try:
                parsed = json.loads(html.unescape(match.group(2)))
            except json.JSONDecodeError:
                continue
            if checker.json_equal(parsed, expected):
                matches.append(match)
        assert len(matches) == 1
        match = matches[0]
        return base_page[:match.start(2)] + html.escape(replacement, quote=False) + base_page[match.end(2):]

    for area, field, mode in (
        ("sequence", "sequence_ids", "float"),
        ("sequence", "loss_mask", "bool"),
        ("padding", "attention_mask", "bool"),
        ("padding", "loss_mask", "float"),
    ):
        value = copy.deepcopy(record[area])
        old = value[field][0]
        value[field][0] = float(old) if mode == "float" else bool(old)
        altered = replace_block(page, record[area], json.dumps(value, ensure_ascii=False))
        try:
            checker.inspect_record(record, altered, descriptor)
        except AssertionError:
            checks[f"display_{area}_{field}_{mode}"] = "REJECTED"
        else:
            raise AssertionError("Changed display array was accepted")

    reordered = page
    for expected in (record["case"]["example"], record["sequence"], record["padding"]):
        value = dict(reversed(list(expected.items())))
        reordered = replace_block(reordered, expected, json.dumps(value, ensure_ascii=False, indent=3))
    assert checker.inspect_record(record, reordered, descriptor)["static_html_content_exact"] is True
    checks["display_key_order_and_whitespace"] = "PASS"
    for name, data in inputs.items():
        assert (args.fixture / name).read_bytes() == data
    assert args.descriptor.read_bytes() == descriptor_bytes
    result = {
        "status": "PASS", "checked_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
        "input_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()},
        "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
        "source_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                          for name in ("check_materials.py", "json_values.py")},
        "mutations_in_memory_only": True, "originals_unchanged": True,
        "new_tokenizer_model_framework_runs": 0,
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "checks": checks}, sort_keys=True))


if __name__ == "__main__":
    main()
