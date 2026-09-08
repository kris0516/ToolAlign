"""Original FIFO input probe; no corpus, tokenizer, framework, or data API.

The parent owns and reaps the only child. An empty FIFO writer releases the
blocked read-only open after observation; no payload bytes are supplied.
"""

from __future__ import annotations

import argparse
import faulthandler
import hashlib
import json
import os
import select
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def child(fifo):
    from toolalign.data.common import DataError
    from toolalign.training.sft.data_v3 import _read

    faulthandler.register(signal.SIGUSR1, all_threads=True)
    print("READ_ATTEMPT", flush=True)
    try:
        _read(fifo, digest="0" * 64, size=0)
    except DataError as error:
        print("REJECTED:" + str(error), flush=True)
        return
    raise AssertionError("nonregular input accepted")


def probe(output):
    output.mkdir(mode=0o700)
    fifo = output / "original-empty-input.fifo"
    os.mkfifo(fifo, 0o600)
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", str(fifo)]
    started = datetime.now(timezone.utc).isoformat()
    with (output / "child-stderr.log").open("xb") as errors:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=errors, text=True)
        observed, first, rest, released = False, "", "", False
        try:
            ready, _, _ = select.select([process.stdout], [], [], 15)
            assert ready, "child import did not finish within its independent startup allowance"
            first = process.stdout.readline()
            assert first == "READ_ATTEMPT\n"
            before = time.monotonic()
            try:
                process.wait(timeout=1)
                observed = True
            except subprocess.TimeoutExpired:
                process.send_signal(signal.SIGUSR1)
                time.sleep(0.1)
                writer = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
                os.close(writer)
                released = True
            rest, _ = process.communicate(timeout=10)
            elapsed = time.monotonic() - before
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            process.stdout.close()
    stdout = first + rest
    (output / "child-stdout.log").write_text(stdout)
    result = {
        "candidate_expectation": "nonregular input rejected without a FIFO writer",
        "rejected_before_writer": observed,
        "empty_writer_needed_to_release_open": released,
        "after_release_rejection": "REJECTED:v3_regular_file_budget" in stdout,
        "child_argv": argv,
        "child_pid": process.pid,
        "child_exit_code": process.returncode,
        "child_reaped": process.poll() is not None,
        "observed_seconds_after_ready": elapsed,
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256((output / "child-stderr.log").read_bytes()).hexdigest(),
        "real_corpus_or_encoding_framework_model_calls": 0,
        "status": "PASS" if observed else "FAIL_NONREGULAR_OPEN_BLOCKS_BEFORE_TYPE_CHECK",
    }
    (output / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    assert observed, "FIFO input blocks before the regular-file validation"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.child is not None:
        child(args.child)
    else:
        assert args.output is not None
        probe(args.output)
