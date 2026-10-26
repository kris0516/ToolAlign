"""Original CPU fixture, including a whole-process signal test entry point.

No fixed model files, tensor framework, real model predictions or CUDA calls.
"""

import json
import os
import sys
import time
from dataclasses import replace
from functools import partial
from pathlib import Path

from toolalign.contracts.interfaces import ModelOutput
from toolalign.inference.cuda import CUDAServiceBackend
from toolalign.runtime.gpu_lock import GPULease
from toolalign.service.http import serve, termination_signals
from toolalign.service.runtime import Service
from toolalign.tools import CancellationToken
from toolalign.tools.scripted import SCRIPTED_IDENTITY

ROOT = Path(__file__).resolve().parents[2]
IDENTITY = {"execution_kind": "ORIGINAL_CPU_FIXTURE", "model_identity": SCRIPTED_IDENTITY}


class OriginalBackend(CUDAServiceBackend):
    def __init__(self, repository, events, *, prepare_seconds=0):
        super().__init__(repository=ROOT, model_root="/not-loaded", checkpoint_dir="/not-loaded",
                         run_id="original-cpu-service", cache_enabled=True)
        self.identity = dict(SCRIPTED_IDENTITY)
        self.lock_repository, self.events = repository, events
        self.prepare_seconds = prepare_seconds

    def record(self, **event):
        with Path(self.events).open("a") as stream:
            stream.write(json.dumps({"pid": os.getpid(), **event}) + "\n")

    def _ensure_tokenizer(self):
        self._tokenizer = "ORIGINAL_CPU_NO_TOKENIZER"

    def _load(self):
        self._lease = GPULease(task_id="ORIGINAL_CPU_SERVICE", worker_alias="CPU",
            run_id="original", expected_job="serving", memory_strategy="no_model",
            repository=self.lock_repository)
        self._lease.__enter__()
        self.record(event="prepare", creator_pid=self._creator_pid)
        time.sleep(self.prepare_seconds)
        self._model = "ORIGINAL_CPU_NO_MODEL"

    def generate(self, request, generation_config):
        self._require_owned_child()
        seed = generation_config.seed
        self.record(event="generate", principal=self.tenant_id, seed=seed)
        time.sleep(20 if seed == 1 else 0.1)
        raw = json.dumps({"kind": "final", "content": self.tenant_id, "tool_calls": []})
        output = ModelOutput(raw, None, None, self.identity, 10, 3, "stop")
        if seed == 3:
            output = replace(output, raw_text="not JSON",
                parsed_action={"kind": "final", "content": "repaired", "tool_calls": []})
        elif seed == 4:
            output = replace(output, finish_reason="length")
        elif seed == 5:
            output = replace(output, input_tokens=None)
        elif seed == 6:
            output = replace(output, model_identity=self.identity | {"model_hash": "different"})
        elif seed == 7:
            output = replace(output, raw_text="x" * 150_000)
        elif seed == 8:
            output = replace(output, raw_text="", finish_reason="error", parse_failure="context_overflow")
        elif seed == 9:
            raise RuntimeError("original backend failure")
        elif seed == 10:
            output = replace(output, parsed_action={"oversized_backend_view": "x" * 150_000})
        return output


def build(request, *, prepare_seconds=0, started_monotonic=None):
    return Service(request, identity=IDENTITY, cancellation=CancellationToken(),
        started_monotonic=started_monotonic,
        backend_factory=partial(OriginalBackend, request["repository"],
                                str(Path(request["output_dir"]).parent / "events.jsonl"),
                                prepare_seconds=prepare_seconds))


if __name__ == "__main__":
    service = build(json.loads(Path(sys.argv[1]).read_text()))
    with termination_signals(service.cancellation):
        summary = serve(service)
    print(json.dumps(summary))
    raise SystemExit(0 if summary["cleanup_confirmed"] else 1)
