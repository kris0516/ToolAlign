"""Rebuild the fixed 43 views once in a fresh directory and map original bytes.

Only the sealed packet order is used. No sampling, judgments, tokenizer, model
or external tools run. Original views, metadata and judgments stay read-only.
"""

import argparse
import difflib
import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")


def sections(text):
    result = {}
    name = None
    for line in text.splitlines():
        if line.startswith("PACKET "):
            name = line.split(" ", 2)[1]
            result[name] = []
        if name is not None:
            result[name].append(line)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[3] / "reports/data/quality-audit-r1"
    sys.path.insert(0, str(source))
    renderer = importlib.import_module("semantic_view")
    verifier = importlib.import_module("verify_semantic_views")
    values = importlib.import_module("json_values")
    source_hashes = {name: sha((source / name).read_bytes()) for name in
                     ("semantic_view.py", "verify_semantic_views.py", "json_values.py")}
    roots = (args.audit_root, args.audit_root / "material-review")
    view_count = sum(len(list((root / "views").glob("*.txt"))) for root in roots)
    assert view_count == 43
    args.output.mkdir(parents=True, exist_ok=False)
    # This exclusive start marker makes interrupted work visible; the directory
    # must not be deleted or reused to disguise a second reconstruction.
    save(args.output / "started.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(),
                                       "source_sha256": source_hashes, "planned_views": view_count})
    totals = {"views": 0, "sources": 0, "decisions": 0, "raw_turns": 0, "prefix_messages": 0}
    original_files, view_map, affected, old_rejections = {}, [], [], []

    def read(path):
        data = path.read_bytes()
        original_files[str(path.resolve())] = {"sha256": sha(data), "bytes": len(data)}
        return data

    for root in roots:
        output_root = args.output / root.relative_to(args.audit_root)
        seen = set()
        for old_view in sorted((root / "views").glob("*.txt")):
            old_bytes = read(old_view)
            old_meta = json.loads(read(old_view.with_suffix(".json")))
            assert sha(old_bytes) == old_meta["view_sha256"]
            paths, packets = [], []
            for item in old_meta["coverage"]:
                name = item["packet"]
                assert name not in seen and Path(name).name == name
                seen.add(name)
                path = root / "frozen/packets" / (name + ".json")
                data = read(path)
                assert sha(data) == item["packet_sha256"]
                packet = json.loads(data)
                assert packet["identity"]["split"] in {"train", "validation"}
                judgment = json.loads(read(root / "judgments" / (name + ".json")))
                assert judgment["view"] == old_view.name
                assert judgment["view_sha256"] == sha(old_bytes)
                assert judgment["packet_sha256"] == sha(data)
                new_packet = output_root / "frozen/packets" / path.name
                new_packet.parent.mkdir(parents=True, exist_ok=True)
                with new_packet.open("xb") as stream:
                    stream.write(data)
                paths.append(path)
                packets.append(packet)
            text, coverage = renderer.render(paths)
            new_view = output_root / "views" / old_view.name
            new_view.parent.mkdir(parents=True, exist_ok=True)
            with new_view.open("xb") as stream:
                stream.write(text.encode())
            metadata = {"rendered_at_utc": datetime.now(timezone.utc).isoformat(),
                        "renderer_sha256": source_hashes["semantic_view.py"],
                        "json_values_sha256": source_hashes["json_values.py"],
                        "view_sha256": sha(text.encode()), "view_bytes": len(text.encode()),
                        "coverage": coverage, "semantic_review_completed": False}
            save(new_view.with_suffix(".json"), metadata)
            checked = verifier.verify(new_view, output_root / "frozen/packets")
            totals["views"] += 1
            for key, count in checked.items():
                totals[key] += count
            try:
                verifier.verify(old_view, root / "frozen/packets")
            except AssertionError as error:
                old_rejections.append({"view": str(old_view.relative_to(args.audit_root)),
                                       "error_type": type(error).__name__})
            changed = old_bytes != text.encode()
            old_parts, new_parts = sections(old_bytes.decode()), sections(text)
            for item, packet in zip(coverage, packets, strict=True):
                name = item["packet"]
                if old_parts[name] != new_parts[name]:
                    affected.append({"view": str(old_view.relative_to(args.audit_root)),
                                     "packet": name, "packet_sha256": item["packet_sha256"],
                                     "source_record_hash": item["source_record_hash"],
                                     "all_packet_decisions_pending_S0_Q1_scope": [
                                         {"example_id": d["example"]["example_id"],
                                          "source_turn_index": d["lineage"]["source_turn_index"]}
                                         for d in packet["valid_decisions"]]})
            if changed:
                diff = "".join(difflib.unified_diff(old_bytes.decode().splitlines(True),
                               text.splitlines(True), fromfile="original", tofile="reconstructed"))
                with new_view.with_suffix(".diff").open("x", encoding="utf-8") as stream:
                    stream.write(diff)
            view_map.append({"view": str(old_view.relative_to(args.audit_root)),
                             "original_view_sha256": sha(old_bytes), "new_view_sha256": sha(text.encode()),
                             "original_metadata_sha256": sha(old_view.with_suffix(".json").read_bytes()),
                             "new_metadata_sha256": sha(new_view.with_suffix(".json").read_bytes()),
                             "original_renderer_sha256": old_meta["renderer_sha256"],
                             "new_renderer_sha256": source_hashes["semantic_view.py"],
                             "content_changed": changed,
                             "coverage_changed": not values.json_equal(old_meta["coverage"], coverage),
                             "checked": checked})
    assert totals["views"] == 43 and totals["sources"] == 222 and totals["decisions"] == 251
    for name, expected in original_files.items():
        data = Path(name).read_bytes()
        assert sha(data) == expected["sha256"] and len(data) == expected["bytes"]
    result = {"status": "CHECKED", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
              "coverage": totals, "source_sha256": source_hashes, "view_map": view_map,
              "affected_packets": affected, "old_views_rejected_by_new_verifier": old_rejections,
              "content_changed_views": sum(item["content_changed"] for item in view_map),
              "coverage_changed_views": sum(item["coverage_changed"] for item in view_map),
              "original_files": original_files, "originals_unchanged": True,
              "original_judgments_rewritten": False, "semantic_verdicts_computed": False,
              "retroactive_review_rebinding": False, "reconstruction_runs": 1}
    save(args.output / "impact.json", result)
    print(json.dumps({key: result[key] for key in ("status", "coverage", "content_changed_views",
                     "coverage_changed_views", "originals_unchanged", "reconstruction_runs")}, sort_keys=True))


if __name__ == "__main__":
    main()
