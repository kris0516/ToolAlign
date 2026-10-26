"""Bind/prepare reviewed input, validate a request, or run bounded native CUDA DPO."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from toolalign.model_io.cuda_generation import MODEL_ID, MODEL_REVISION
from toolalign.model_io.offline import OfflineQwenTokenizer
from toolalign.training.cuda_sft.protocol import document, encoded, write_bytes

from .data import bind_input, prepare_input, read_input
from .protocol import CONFIG_SHA256, load_protocol, validate_run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    bind = commands.add_parser("bind-input")
    for name in ("extraction", "reviewed", "review", "output"):
        bind.add_argument("--" + name, required=True, type=Path)
    prepare = commands.add_parser("prepare")
    for name in ("repository", "input-root", "model-root", "output"):
        prepare.add_argument("--" + name, required=True, type=Path)
    prepare.add_argument("--input-manifest-sha256", required=True)
    for command in ("validate", "train"):
        entry = commands.add_parser(command)
        entry.add_argument("--run-config", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "bind-input":
        result = bind_input(extraction=args.extraction, reviewed=args.reviewed,
                            review=args.review, output=args.output)
    elif args.command == "prepare":
        load_protocol(args.repository)
        tokenizer = OfflineQwenTokenizer(args.model_root, repo_id=MODEL_ID, revision=MODEL_REVISION)
        _, result = prepare_input(args.input_root, args.input_manifest_sha256, tokenizer,
                                  config_sha=CONFIG_SHA256)
        write_bytes(args.output, encoded(result) + b"\n")
    else:
        request = document(args.run_config)
        validate_run(request)
        load_protocol(request["repository"])
        if args.command == "validate":
            training, _ = read_input(request["input_root"], request["input_manifest_sha256"])
            result = {"status": "CPU_VALIDATED", "q1_accepted_pairs": len(training),
                      "encoding_plan": "RECHECKED_AT_EXECUTION", "formal_DPO": "NOT_RUN"}
        else:
            from .runtime import supervise

            result = supervise(request)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
