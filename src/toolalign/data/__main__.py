"""python -m toolalign.data: private download, audit/rebuild, and hash comparison."""

import argparse
import json
import sys

from .common import DataError, canonical_hash, read_json, verified_build_manifest
from .pipeline import build
from .sources import fetch_source


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser(
        "fetch", help="Verify/download pinned official source without authentication"
    )
    fetch.add_argument("--manifest", required=True)
    fetch.add_argument("--destination", required=True)
    fetch.add_argument("--ca-file")
    rebuild = sub.add_parser(
        "build", help="Rebuild strict examples and full audit into an empty private directory"
    )
    rebuild.add_argument("--config", required=True)
    compare = sub.add_parser("compare", help="Compare two independently produced build manifests")
    compare.add_argument("first")
    compare.add_argument("second")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            result = fetch_source(read_json(args.manifest), args.destination, args.ca_file)
        elif args.command == "build":
            report, manifest = build(read_json(args.config))
            result = {
                "raw_records": report["raw_records"],
                "raw_assistant_decisions": report["raw_assistant_decisions"],
                "final_examples": report["final_examples"],
                "groups": report["grouping"]["groups"],
                "manifest_hash": canonical_hash(manifest),
                "status": report["status"],
            }
        else:
            first, second = (
                verified_build_manifest(args.first),
                verified_build_manifest(args.second),
            )
            if first != second:
                raise DataError("rebuild_manifest_mismatch")
            result = {
                "match": True,
                "manifest_hash": canonical_hash(first),
                "compared_artifacts": len(first["artifacts"]),
            }
    except (DataError, OSError, ValueError, KeyError, ImportError) as exc:
        # Never print source contents, paths, authentication material or parser tracebacks.
        print(
            json.dumps({"error": str(exc) if isinstance(exc, DataError) else type(exc).__name__}),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
