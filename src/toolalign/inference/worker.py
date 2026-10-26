"""Bounded persistent owned child; no HTTP, tool execution or oracle."""

from __future__ import annotations

import time
from pathlib import Path

from toolalign.contracts.interfaces import GenerationConfig, ModelOutput
from toolalign.evaluation.harness import _output_packet
from toolalign.tools._json import INPUT_BYTES
from toolalign.tools.isolation import enter_child, read_packet, write_packet


def service_child(directory, backend, epoch, max_generations):
    enter_child(directory)
    root = Path(directory)
    try:
        ready = backend.prepare()
        write_packet(root / "ready.json", {"epoch": epoch, "ready": ready, "error": None})
    except Exception as error:
        write_packet(root / "ready.json", {"epoch": epoch, "ready": None,
                                          "error": type(error).__name__})
        return
    for index in range(max_generations):
        path = root / f"request-{index}.json"
        while not path.exists():
            if (root / "stop.json").exists():
                return
            time.sleep(0.01)
        started = time.monotonic()
        try:
            packet = read_packet(path, INPUT_BYTES + 4096)
            backend.bind_principal(packet["principal"])
            write_packet(root / f"generating-{index}.json", {"started": True})
            output = backend.generate(packet["input"], GenerationConfig(**packet["config"]))
            if type(output) is not ModelOutput:
                raise ValueError("Backend must return ModelOutput")
            result = _output_packet(output)
            result["metrics"] = backend.generation_metrics()
        except Exception as error:
            result = {"output": None, "error": type(error).__name__,
                      "usage": None, "diagnostic": None, "metrics": {}}
        result["child_generation_seconds"] = time.monotonic() - started
        write_packet(root / f"result-{index}.json", result)
        # Only the active IPC exchange is retained; the parent journals the input
        # and raw result before acknowledging. Bound a warm worker's disk usage.
        acknowledgement = root / f"ack-{index}.json"
        while not acknowledgement.exists():
            if (root / "stop.json").exists():
                return
            time.sleep(0.01)
        for name in (f"request-{index}.json", f"result-{index}.json",
                     f"generating-{index}.json", f"ack-{index}.json"):
            (root / name).unlink()
    # Exhaustion is not a new worker authorization. Retain the loaded lifecycle
    # for read-only status/cleanup until its owner explicitly stops it.
    while not (root / "stop.json").exists():
        time.sleep(0.01)
