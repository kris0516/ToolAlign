"""CPU-only registry inspection and public scripted development demo."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from toolalign.contracts import ContractError, canonical_hash, validate_record
from toolalign.contracts.interfaces import OracleTask, SandboxContext
from toolalign.evaluation.harness import LocalHarness, summarize
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools._json import INPUT_BYTES, decode, parse_action
from toolalign.tools.scripted import SCRIPTED_IDENTITY, ScriptedCPUModelBackend


def development_case(case, registry):
    """Build a validation-only public demo; scripts and truth are distinct fields."""
    example = {
        "schema_version": "toolalign.example.v1",
        "example_id": case["id"],
        "source": "toolalign-original-development",
        "source_revision": "p03-dev.v1",
        "license_id": "MIT",
        "source_record_hash": canonical_hash(case),
        "group_id": case["group"],
        "split": "validation",
        "messages": [
            {"role": "user", "content": case["prompt"], "tool_calls": [], "tool_call_id": None}
        ],
        "tools": registry.tools,
        "expected_action": parse_action(case["scripted_responses"][0]),
        "category": case["category"],
    }
    example = validate_record(example, "example")
    task = OracleTask(
        case["id"],
        case["group"],
        "validation",
        example["expected_action"],
        {"version": ORACLE_VERSION, "answers": case["answers"], "strategies": case["strategies"]},
    )
    return example, task


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, prog="python -m toolalign.tools")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("registry", help="Print exact local implementation and schema identities")
    demo = commands.add_parser("demo", help="Run public scripted CPU development cases")
    demo.add_argument(
        "--cases", type=Path, required=True, help="Original development JSON manifest"
    )
    demo.add_argument("--output", type=Path, required=True, help="New private output directory")
    args = parser.parse_args(argv)
    try:
        registry = LocalToolRegistry()
        if args.command == "registry":
            print(
                json.dumps({"registry_hash": registry.registry_hash, **registry.manifest}, indent=2)
            )
            return 0
        with args.cases.open("rb") as stream:
            manifest = decode(stream.read(INPUT_BYTES + 1), INPUT_BYTES)
        if (
            manifest["purpose"] != "public-original-development"
            or not 1 <= len(manifest["cases"]) <= 32
        ):
            raise ValueError("Only bounded public development cases are supported")
        prepared = [(case, *development_case(case, registry)) for case in manifest["cases"]]
        args.output.mkdir(parents=True, exist_ok=False)
        root = args.output.resolve()
        results = []
        for index, (case, example, task) in enumerate(prepared):
            executor = LocalToolExecutor(registry, faults=case.get("faults"))
            harness = LocalHarness(registry, executor)
            context = SandboxContext(
                root,
                f"demo-{index}",
                (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
                CancellationToken(),
            )
            backend = ScriptedCPUModelBackend(case["scripted_responses"])
            result = harness.run(example, task, backend, context, model_identity=SCRIPTED_IDENTITY)
            results.append(result)
            (root / f"case-{index:02d}.json").write_text(
                json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n"
            )
        summary = {
            **summarize(results),
            "registry_hash": registry.registry_hash,
            "synthetic_tokens_only": True,
            "repairs": "DISABLED",
            "formal_hidden_test": "NOT_RUN",
            "categories": {
                case["id"]: {"category": case["category"], "outcome": result.score.outcome}
                for (case, _, _), result in zip(prepared, results)
            },
        }
        (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        return 0 if summary["success"] == summary["total"] else 1
    except (ContractError, OSError, ValueError, KeyError, TypeError):
        print("Unable to run bounded public development demo", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
