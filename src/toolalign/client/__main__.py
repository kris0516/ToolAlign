"""Mac loopback client and original CPU examples; never starts a Colab instance."""

from __future__ import annotations

import argparse
import json
import re
import signal
import sys
from pathlib import Path

from toolalign.contracts import ContractError
from toolalign.data.common import loads

from . import protocol as p
from .examples import run_examples
from .http import load_config, private_output, read_json, write_record
from .remote import RemoteClient
from .trajectory import ClientCancellation, run_trajectory


def restore_request(path, config):
    with path.open("rb") as stream:
        raw = stream.read(4 * p.INPUT_BYTES + 1)
    p.require(len(raw) <= 4 * p.INPUT_BYTES, "receipt_limit")
    saved = loads(raw.decode("utf-8"))
    p.require(saved["schema"] == "toolalign.client-decision.v1"
              and type(saved["idempotency_key"]) is str
              and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", saved["idempotency_key"]), "request_receipt")
    body = saved["request_body"]
    p.fields(body, "schema service_run_id model_input seed timeout_ms", "request_body_fields")
    p.require(body["schema"] == p.SCHEMA and body["service_run_id"] == config["service_run_id"]
              and p.integer(body["seed"], 0, 2**63 - 1) and p.integer(body["timeout_ms"], 1, 30000), "request_body_values")
    p.bound_input(body["model_input"])
    p.require(saved["request_id"] is None or p.text(saved["request_id"]), "request_receipt_id")
    return {"request_body": body, "idempotency_key": saved["idempotency_key"],
            "request_id": saved["request_id"], "state": None, "http_events": []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, prog="python -m toolalign.client")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Run at most 3 pinned remote decisions and 2 local tool rounds")
    run.add_argument("--config", type=Path, required=True, help="Private URL/run/ModelIdentity/token-file configuration")
    run.add_argument("--input", type=Path, required=True, help="Complete ModelInput JSON; exact local catalog subset")
    run.add_argument("--output", type=Path, required=True, help="New directory under .toolalign-local")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--timeout-ms", type=int, default=30000, help="Whole trajectory decision budget, 1..30000")
    run.add_argument("--cleanup-ms", type=int, default=5000, help="Separate remote cleanup budget, 1..30000")
    cancel = commands.add_parser("cancel", help="Read back the original key and cancel; never creates a decision")
    cancel.add_argument("--config", type=Path, required=True)
    cancel.add_argument("--request", type=Path, required=True, help="Saved decision-NN.json receipt")
    cancel.add_argument("--output", type=Path, required=True, help="New private cleanup directory")
    cancel.add_argument("--cleanup-ms", type=int, default=5000)
    demo = commands.add_parser("demo", help="Original scripted CPU examples over real loopback; no learned model")
    demo.add_argument("--cases", type=Path, required=True)
    demo.add_argument("--case", help="One case ID; omitted runs all declared examples")
    demo.add_argument("--output", type=Path, required=True, help="New directory under .toolalign-local")
    args = parser.parse_args(argv)
    token = ClientCancellation()
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    for sig in previous:
        signal.signal(sig, lambda *_: token.cancel())
    try:
        if args.command == "demo":
            result = run_examples(args.cases, private_output(args.output), selected=args.case, cancellation=token)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 130 if token.is_cancelled() else 0 if result["passed"] else 1
        config = load_config(args.config)
        client = RemoteClient(config, cleanup_ms=args.cleanup_ms)
        if args.command == "cancel":
            receipt = restore_request(args.request, config)
            root = private_output(args.output)
            result = client.cleanup(receipt)
            write_record(root / "cleanup.json", {"request": receipt, "cleanup": result})
            state = result["state"]
            print(json.dumps({"resolution": result["resolution"],
                              "remote_status": None if state is None else state["status"],
                              "worker_cleanup": None if state is None else state["worker_cleanup"]}))
            return 0 if result["resolution"] == "terminal_observed" else 1
        model_input, _ = p.bound_input(read_json(args.input))
        p.require(p.integer(args.seed, 0, 2**63 - 1) and p.integer(args.timeout_ms, 1, 30000), "client_run_budget")
        root = private_output(args.output)
        result = run_trajectory(client, model_input, root, seed=args.seed,
                                timeout_ms=args.timeout_ms, cancellation=token)
        print(json.dumps({key: result[key] for key in ("execution_kind", "status", "reason", "semantic_outcome",
                                                       "budget", "local_children_reaped", "decision_seconds",
                                                       "cleanup_seconds", "complete_wall_seconds")}, indent=2))
        return 130 if result["status"] == "cancelled" else 0 if result["status"] == "finalized" else 1
    except (p.ClientError, ContractError, OSError, ValueError, KeyError, TypeError):
        print("Client rejected invalid input, identity, contract or local I/O; no credential details logged.", file=sys.stderr)
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == "__main__":
    sys.exit(main())
