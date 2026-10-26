"""Original tiny CPU DynamicCache evidence, separate from CUDA service claims."""

import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from toolalign.contracts.interfaces import GenerationConfig
from toolalign.inference.cuda import CUDAServiceBackend
from toolalign.inference.worker import service_child
from toolalign.tools import CancellationToken
from toolalign.tools.isolation import OwnedProcess, write_packet
from toolalign.tools.scripted import SCRIPTED_IDENTITY

ROOT = Path(__file__).resolve().parents[2]


class OriginalTokenizer:
    eos_token_id = 9

    def decode(self, ids, *, skip_special_tokens):
        assert not skip_special_tokens
        return json.dumps({"kind": "final", "content": json.dumps(ids), "tool_calls": []})


class OriginalTinyBackend(CUDAServiceBackend):
    def __init__(self):
        super().__init__(repository=ROOT, model_root="/not-loaded", checkpoint_dir="/not-loaded",
                         run_id="original-tiny-cpu", cache_enabled=True)
        self.identity = dict(SCRIPTED_IDENTITY)

    def _ensure_tokenizer(self):
        self._tokenizer = OriginalTokenizer()

    def _load(self):
        import torch
        from transformers import Qwen3Config, Qwen3ForCausalLM

        from toolalign.model_io import cuda_evaluation
        from toolalign.model_io.cuda_generation import decode_once

        torch.set_num_threads(1)
        torch.manual_seed(1234)
        config = Qwen3Config(vocab_size=16, hidden_size=8, intermediate_size=16,
            num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1, head_dim=4,
            max_position_embeddings=2048, attention_dropout=0.0, eos_token_id=9, pad_token_id=0)
        config._attn_implementation = "sdpa"
        self._model = Qwen3ForCausalLM(config).eval()
        assert sum(p.numel() for p in self._model.parameters()) < 4096

        # Only the device is redirected for this original fixture. The actual
        # service/evaluation _decode constructs the identity+principal cache key.
        def cpu_decode(*args, **kwargs):
            return decode_once(*args, **(kwargs | {"device": "cpu"}))
        cuda_evaluation.decode_once = cpu_decode

    def generate(self, request, generation_config):
        self._require_owned_child()
        output = self._decode([1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4], generation_config)
        self._service_metrics = self._metrics["decisions"][-1]
        return output


def test_prepare_and_binding_reject_parent_without_importing_framework():
    code = """
import sys,json
from toolalign.inference.cuda import CUDAServiceBackend
from toolalign.service.runner import execute
backend = CUDAServiceBackend(repository=sys.argv[1], model_root='/not-loaded',
    checkpoint_dir='/not-loaded', run_id='original-cpu', cache_enabled=True)
for operation in (backend.prepare, lambda: backend.bind_principal('alice')):
    try:
        operation()
    except ValueError as error:
        assert str(error) == 'owned_model_child_required'
    else:
        raise AssertionError('parent guard missing')
print(json.dumps(sorted({'torch','transformers','peft','mlx'} & set(sys.modules))))
"""
    result = subprocess.run([sys.executable, "-c", code, str(ROOT)], check=True, text=True, capture_output=True)
    assert json.loads(result.stdout) == []


def test_service_child_real_prefix_cache_uses_authenticated_principal_and_one_entry(tmp_path):
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    import time

    backend = OriginalTinyBackend()
    worker = OwnedProcess(tmp_path.resolve(), service_child, (backend, 1, 5), "model")
    cancellation = CancellationToken()
    packets = []
    try:
        status, ready = worker.wait("ready.json", time.monotonic() + 30, cancellation)
        assert status == "completed" and ready["error"] is None
        assert ready["ready"]["model_identity"] == SCRIPTED_IDENTITY
        assert not (worker.directory / "generating-0.json").exists()
        for i, principal in enumerate(("alice", "alice", "bob", "bob", "alice")):
            config = GenerationConfig(42, 0.7, 0.9, 256,
                (datetime.now(timezone.utc) + timedelta(seconds=15)).isoformat())
            write_packet(worker.directory / f"request-{i}.json", {"input": {}, "config": asdict(config),
                                                                  "principal": principal})
            status, packet = worker.wait(f"result-{i}.json", time.monotonic() + 15, cancellation)
            assert status == "completed" and packet["error"] is None
            packets.append(packet)
            write_packet(worker.directory / f"ack-{i}.json", {})
        assert [p["metrics"]["cache_hit_tokens"] for p in packets] == [0, 11, 0, 11, 0]
        assert [p["metrics"]["prefill_tokens"] for p in packets] == [12, 1, 12, 1, 12]
        assert all(p["output"] == packets[0]["output"] for p in packets)
        assert packets[0]["output"]["finish_reason"] == "stop"
        (tmp_path / "cpu-cache-results.json").write_text(json.dumps(packets, indent=2))
    finally:
        write_packet(worker.directory / "stop.json", {})
        worker.close()
        (tmp_path / "cpu-cache-process.json").write_text(json.dumps(worker.record, indent=2))
    assert worker.record["reaped"] and worker.record["directory_cleaned"]
