"""CPU plan/validation and separately authorized CUDA evaluation."""

import argparse
import json
import signal
from pathlib import Path

from toolalign.tools import CancellationToken
from toolalign.training.cuda_sft.protocol import document

from .protocol import MODES, evaluation_plan, read_inputs, validate_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--input", required=True, type=Path)
    plan.add_argument("--input-sha256", required=True)
    plan.add_argument("--mode", required=True, choices=MODES)
    for command in ("validate", "evaluate"):
        sub = commands.add_parser(command)
        sub.add_argument("--run-config", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "plan":
        inputs, _ = read_inputs(args.input, args.input_sha256, args.mode)
        print(json.dumps(evaluation_plan(inputs, args.mode), indent=2))
        return 0
    request = document(args.run_config)
    if args.command == "validate":
        inputs, _ = read_inputs(request["input_path"], request["input_sha256"], request["mode"])
        validate_run(request, inputs)
        print(json.dumps({"status": "CPU_VALIDATED", "real_evaluation": "NOT_RUN"}))
        return 0
    from .runner import execute

    cancellation = CancellationToken()
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        for sig in previous:
            signal.signal(sig, lambda *_: cancellation.cancel())
        summary = execute(request, cancellation=cancellation)
        print(json.dumps(summary, sort_keys=True))
        return 0 if summary["status"] == "prefix_complete" else 124
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())
