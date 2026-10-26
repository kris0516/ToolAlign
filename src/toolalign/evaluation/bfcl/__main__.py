"""CPU-only BFCL source, selection and official scoring commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from toolalign.data.common import file_hash, private_directory, read_json, write_json
from toolalign.evaluation.analysis import load_batch

from .scoring import OfficialScorer, score_batch
from .source import fetch_source, selected_answers
from .subset import freeze_subset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch")
    fetch.add_argument("--output", required=True)
    select = commands.add_parser("select")
    for key in ("source-root", "p02-manifest", "p02-sha256", "g4-package", "development", "tokenizer-root", "output"):
        select.add_argument("--" + key, required=True)
    answers = commands.add_parser("answers")
    for key in ("source-root", "selection", "selection-sha256", "output"):
        answers.add_argument("--" + key, required=True)
    score = commands.add_parser("score")
    for key in ("source-root", "selection", "selection-sha256", "inputs", "run-root", "output"):
        score.add_argument("--" + key, required=True)
    score.add_argument("--answers", help="Frozen answer artifact, unnecessary for an irrelevance-only selection")
    args = parser.parse_args()
    if args.command == "fetch":
        result = fetch_source(args.output)
        result = {"commit": result["commit"], "files": len(result["files"])}
    elif args.command == "select":
        result = freeze_subset(args.source_root, args.p02_manifest, args.p02_sha256, args.g4_package,
                               args.development, args.tokenizer_root, args.output)
    elif args.command == "answers":
        result = selected_answers(args.source_root, args.selection, args.selection_sha256, args.output)
        result = {"status": "READ_AFTER_FREEZE", "answers": len(result["answers"])}
    else:
        if file_hash(args.selection) != args.selection_sha256:
            raise ValueError("selection_hash_mismatch")
        output = Path(args.output)
        if output.exists() or output.is_symlink():
            raise ValueError("score_output_already_exists")
        private_directory(output.parent)
        scorer = OfficialScorer(args.source_root)
        if scorer.identity != read_json(Path(args.selection).parent / "source.json"):
            raise ValueError("selection_scorer_source_binding")
        result = score_batch(load_batch(args.inputs, args.run_root), read_json(args.selection), args.selection_sha256,
                             read_json(args.answers) if args.answers else None, scorer)
        write_json(output, result)
        result = {"status": "SCORED", "rows": len(result["rows"]),
                  "official_statuses": sorted({row["official_status"] for row in result["rows"]})}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
