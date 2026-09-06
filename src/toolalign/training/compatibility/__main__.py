"""Explicit P01 entry points. Optional libraries are loaded only when needed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="P01 hardware, mathematical and bounded model probes"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser(
        "audit", help="Read sanitized hardware/dependency metadata (no model import)"
    )
    audit.add_argument("--output", type=Path)
    for name in ("math", "smoke", "calibrate", "_worker"):
        p = sub.add_parser(name, help="Private config required; models are always leased")
        p.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    from .execution import dependency_versions, hardware_audit, launch, worker

    if args.command == "audit":
        result = {"hardware": hardware_audit(), "dependencies": dependency_versions()}
        if args.output:
            from .core import write_json

            write_json(args.output, result)
        print(json.dumps(result, indent=2))
        return 0
    config = json.loads(args.config.read_text())
    if args.command == "_worker":
        return worker(config, Path(config["output_dir"]))
    if args.command != config["mode"]:
        parser.error("Subcommand must match declared config mode")
    return launch(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
