"""python -m toolalign.training.cuda_sft prepare|encode|train."""

from __future__ import annotations

import argparse
import json

from .protocol import document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "encode"):
        commands.add_parser(name).add_argument("--request", required=True)
    commands.add_parser("train").add_argument("--run-config", required=True)
    args = parser.parse_args(argv)
    from .runtime import supervise

    request_path = args.run_config if args.command == "train" else args.request
    result = supervise(document(request_path, limit=1024 * 1024), command=args.command)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
