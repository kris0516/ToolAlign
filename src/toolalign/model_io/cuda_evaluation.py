"""G5 M0/base and M1/selected-SFT inference in an owned CUDA child."""

from __future__ import annotations

import os
import time

from toolalign.contracts import ContractError
from toolalign.model_io.cuda_generation import (
    ADAPTER_SHA256,
    CHECKPOINT_SHA256,
    CUDAGenerationBackend,
    decode_once,
    read_selected_adapter,
    restore_adapter,
    selected_model_identity,
)
from toolalign.model_io.prefix_cache import PrefixCache
from toolalign.runtime.gpu_lock import GPULease
from toolalign.tools._json import parse_action
from toolalign.training.cuda_sft.engine import load_model
from toolalign.training.cuda_sft.protocol import load_protocol, require


def evaluation_model_identity(repository, model):
    require(model in ("M0", "M1"), "evaluation_model_required")
    identity = selected_model_identity(repository)
    if model == "M0":
        identity["adapter_hash"] = None
    return identity


class CUDAEvaluationBackend(CUDAGenerationBackend):
    backend_label = "cuda-evaluation.v1"
    lease_task_id = "P06-G5-EVALUATION"
    lease_job = "evaluation"

    def __init__(self, *, model, cache_enabled=False, tenant_id="evaluation", **kwargs):
        super().__init__(**kwargs)
        require(model in ("M0", "M1") and type(cache_enabled) is bool,
                "evaluation_model_and_cache")
        require(type(tenant_id) is str and bool(tenant_id), "evaluation_tenant_required")
        self.condition_model = model
        self.identity = evaluation_model_identity(self.repository, model)
        self.cache_enabled = cache_enabled
        self.tenant_id = tenant_id
        self._prefix_cache = None

    def _load(self):
        config = load_protocol(self.repository)
        self._lease = GPULease(task_id=self.lease_task_id, worker_alias="S1",
                               run_id=self.run_id, expected_job=self.lease_job,
                               memory_strategy="BF16_base_optional_FP32_QV_LoRA_no_grad_KV_cache",
                               repository=self.repository, timeout_seconds=0)
        self._lease.__enter__()
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = config["numerics"]["cublas_workspace_config"]
        import torch

        require(torch.cuda.is_available(), "CUDA_unavailable_no_fallback")
        require(torch.cuda.is_bf16_supported(), "CUDA_BF16_unavailable")
        torch.use_deterministic_algorithms(True, warn_only=False)
        self._report("model_loading", backend=self.backend_label, model=self.condition_model)
        adapter = read_selected_adapter(self.checkpoint_dir) if self.condition_model == "M1" else None
        torch.cuda.reset_peak_memory_stats(0)
        self._model = load_model({"repository": self.repository, "model_root": self.model_root,
                                  "profile": "formal"}, config, self._lease,
                                 verified_files=self._verified_files,
                                 with_adapter=self.condition_model == "M1")
        if adapter is not None:
            restore_adapter(self._model, adapter, expected_hash=ADAPTER_SHA256)
        self._model.gradient_checkpointing_disable()
        self._model.config.use_cache = True
        self._model.eval()
        torch.cuda.synchronize(0)
        self._report("ready", cold_load_seconds=time.monotonic()
                     - self._metrics["cold_load_started_monotonic"],
                     device=torch.cuda.get_device_name(0),
                     actual_model_identity=self.identity,
                     checkpoint_sha256=CHECKPOINT_SHA256 if adapter is not None else None,
                     adapter_sha256=ADAPTER_SHA256 if adapter is not None else None)

    def _decode(self, ids, config):
        if self.cache_enabled and self._prefix_cache is None:
            self._prefix_cache = PrefixCache()
        metric = {}
        key = {"model_identity": self.identity, "tenant_id": self.tenant_id}
        output = decode_once(self._model, self._tokenizer, ids, config, device="cuda:0",
                             identity=self.identity, prefix_cache=self._prefix_cache,
                             cache_key=key, metrics=metric)
        try:
            parse_action(output.raw_text)
        except ContractError:
            if self._prefix_cache is not None:
                self._prefix_cache.clear()
        self._metrics.setdefault("decisions", []).append(metric)
        return output

    def generate(self, request, generation_config):
        try:
            output = super().generate(request, generation_config)
            if output.finish_reason != "stop" and self._prefix_cache is not None:
                self._prefix_cache.clear()
            return output
        except BaseException:
            if self._prefix_cache is not None:
                self._prefix_cache.clear()
            raise
