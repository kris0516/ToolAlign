"""Picklable synthetic workers for the parent's real process-boundary checks."""

import time
from pathlib import Path


def large_receipt(request, sender):
    sender.send({"status": "PASS", "synthetic": True, "receipt": "original-fixture" * 20000})
    sender.close()


def waiting(request, sender):
    time.sleep(30)


def oversized_output(request, sender):
    (Path(request["output_dir"]) / "synthetic-partial.txt").write_bytes(b"x" * 32768)
    time.sleep(30)


def failed(request, sender):
    sender.send({"status": "FAIL", "error": "original synthetic worker failure"})
    sender.close()


def _near_full_output(request, sender, metadata):
    # R1's output-budget counterexample: the files fit but the terminal receipt does not.
    (Path(request["output_dir"]) / "synthetic-output.bin").write_bytes(b"x" * 60000)
    sender.send({"status": "PASS", "synthetic": True,
                 "identity": {"diagnostic_fixture_metadata": metadata}})
    sender.close()


def terminal_receipt(request, sender):
    _near_full_output(request, sender, "s" * 8192)


def unicode_terminal_receipt(request, sender):
    _near_full_output(request, sender, "界" * 2048)


def fills_receipt_reserve(request, sender):
    (Path(request["output_dir"]) / "synthetic-output.bin").write_bytes(b"x" * 62400)
    time.sleep(30)
