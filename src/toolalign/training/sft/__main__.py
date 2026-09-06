"""Installable default-CPU preparation CLI; no training command is exposed."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolalign.contracts import ContractError
from toolalign.data.common import DataError, encoded
from toolalign.data.training_selection import new_private_directory

from .data import prepare


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sft-config-path", "public-selection-manifest-path", "selection-path",
                 "config-path", "data-manifest-path", "representation-path", "audit-path", "protocol-path",
                 "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = vars(parser.parse_args(argv))
    output = args.pop("output")
    try:
        out = new_private_directory(output)
    except (OSError, DataError) as exc:
        print(encoded({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}).decode())
        return 1
    try:
        _, report = prepare(**args)
        code = 0
    except (OSError, ContractError, KeyError, TypeError, ValueError) as exc:
        report = {"status": "FAIL", "scope": "CPU_PREPARATION_ONLY", "training_authorized": False,
                  "error_type": type(exc).__name__,
                  "error": str(exc) if isinstance(exc, DataError) else "invalid_input_or_io"}
        code = 1
    with (out / "preparation.json").open("xb") as stream:
        stream.write(encoded(report) + b"\n")
    print(encoded(report).decode())
    return code


if __name__ == "__main__":
    sys.exit(main())
