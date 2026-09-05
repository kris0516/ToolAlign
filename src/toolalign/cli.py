"""Small CPU-only verification CLI; never executes model or dataset code."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from toolalign.contracts import ContractError, contract_digest, schema_for, validate_record
from toolalign.contracts.validation import KINDS
from toolalign.runtime import inspect_gpu_lock


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("Duplicate JSON key")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="toolalign")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a JSON record or JSONL file")
    validate.add_argument("path", type=Path)
    validate.add_argument("--kind", choices=KINDS)
    validate.add_argument("--jsonl", action="store_true")
    schema = commands.add_parser("schema", help="Print a self-contained Draft 2020-12 schema")
    schema.add_argument("kind", choices=KINDS)
    commands.add_parser("contract-digest", help="SHA-256 of the frozen schema bundle")
    lock = commands.add_parser("lock-status", help="Inspect local private GPU lease metadata")
    lock.add_argument("--repository", default=".")
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            print(json.dumps(schema_for(args.kind), indent=2))
        elif args.command == "contract-digest":
            print(contract_digest())
        elif args.command == "lock-status":
            print(json.dumps(inspect_gpu_lock(args.repository), indent=2))
        else:
            count = 0
            with args.path.open(encoding="utf-8") as stream:
                records = stream if args.jsonl else [stream.read()]
                for record in records:
                    if not record.strip():
                        raise ContractError("Empty JSON record")
                    validate_record(json.loads(record, object_pairs_hook=_object), args.kind)
                    count += 1
            if count == 0:
                raise ContractError("Empty input")
            print(f"VALID: {count} record(s)")
        return 0
    except (ContractError, OSError, ValueError) as exc:
        message = str(exc) if isinstance(exc, ContractError) else "Unable to read valid JSON input"
        print(f"INVALID: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
