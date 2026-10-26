"""CPU plan/validation and the separately authorized CUDA generation command."""

from __future__ import annotations

import argparse
import json
import signal
from pathlib import Path

from toolalign.tools import CancellationToken
from toolalign.training.cuda_sft.protocol import document

from .protocol import candidate_plan, read_tasks, validate_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--tasks", required=True, type=Path)
    plan.add_argument("--tasks-sha256", required=True)
    for command in ("validate", "generate"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--run-config", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "plan":
        tasks, _ = read_tasks(args.tasks, args.tasks_sha256)
        print(json.dumps(candidate_plan(tasks["tasks"]), indent=2))
        return 0
    request = document(args.run_config)
    if args.command == "validate":
        tasks, _ = read_tasks(request["tasks_path"], request["tasks_sha256"])
        validate_run(request, tasks)
        print(json.dumps({"status": "CPU_VALIDATED", "real_generation": "NOT_RUN"}))
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
