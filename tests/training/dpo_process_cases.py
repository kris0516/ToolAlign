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
