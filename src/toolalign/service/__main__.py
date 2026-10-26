"""CPU configuration validation and separately authorized restricted CUDA service."""

import argparse
import json
from pathlib import Path

from toolalign.tools import CancellationToken
from toolalign.training.cuda_sft.protocol import document

from .http import termination_signals
from .protocol import TokenAuth, validate_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "serve"):
        commands.add_parser(command).add_argument("--run-config", required=True, type=Path)
    args = parser.parse_args()
    request = validate_run(document(args.run_config))
    TokenAuth(request["auth_file"])
    if args.command == "validate":
        print(json.dumps({"status": "CPU_VALIDATED", "cuda_service": "NOT_RUN"}))
        return 0
    from .runner import execute

    cancellation = CancellationToken()
    with termination_signals(cancellation):
        summary = execute(request, cancellation=cancellation)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["cleanup_confirmed"] and summary["status"] in (
        "signal", "requested", "service_budget_exhausted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
