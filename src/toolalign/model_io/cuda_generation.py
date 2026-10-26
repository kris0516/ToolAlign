"""Selected G3 SFT inference, lazily loaded in LocalHarness's owned child.

Importing or constructing this backend imports no model framework. The lease
stays open for the child's lifetime, including failures; process reaping frees
the CUDA context and the OS lock together.
"""

from __future__ import annotations

import io
import multiprocessing
import os
import time
from pathlib import Path

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import GenerationConfig, ModelOutput
from toolalign.evaluation.harness import MAX_NEW_TOKENS, SamplingParameters
from toolalign.model_io.format import TEMPLATE_SHA256, prompt_messages
from toolalign.model_io.offline import OfflineQwenTokenizer
from toolalign.model_io.qwen_model import CONFIG_SHA256 as MODEL_CONFIG_SHA256
from toolalign.runtime.gpu_lock import GPULease
from toolalign.tools.isolation import utc_remaining, write_packet
from toolalign.training.cuda_sft.checkpoint import parameter_hash
from toolalign.training.cuda_sft.engine import load_model
from toolalign.training.cuda_sft.protocol import (
    CONFIG_SHA256,
    document,
    load_protocol,
    read_bytes,
    require,
    sha,
)

MODEL_ID = "Qwen/Qwen3-1.7B"
MODEL_REVISION = "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
CHECKPOINT_SHA256 = "cfb02aec2279138c01f8b336abc08a588d0ab11efa8db68fd61ba0b6150b5d14"
ADAPTER_SHA256 = "973c440e29090892ad11d6d56b94bad4c98a5398c223e2b4302d7dba7c4640ed"
SFT_SOURCE_COMMIT = "2abbe7ac913661df1d5e430f285604b4ceb8ff4b"
CONTEXT_TOKENS = 2048
BATCH_FILE_VALIDATION = "batch_full_hash_child_stat.v1"


def selected_model_identity(repository):
    """File identity: model_hash binds the named original weight-file hashes."""
    metadata = document(Path(repository) / "configs/qwen-models.v1.json",
                        digest=MODEL_CONFIG_SHA256)
    spec = metadata["models"][MODEL_ID]
    require(spec["revision"] == MODEL_REVISION, "generation_model_revision")
    weights = {name: item["sha256"] for name, item in spec["files"].items()
               if name.endswith(".safetensors")}
    return {"model_id": MODEL_ID, "model_revision": MODEL_REVISION,
            "model_hash": canonical_hash(weights), "adapter_hash": ADAPTER_SHA256,
            "tokenizer_hash": spec["files"]["tokenizer.json"]["sha256"],
            "template_hash": TEMPLATE_SHA256, "quantization": "none"}


def restore_adapter(model, adapter, *, expected_hash):
    """Copy every saved adapter key, with no optimizer or training-state restore."""
    import torch

    parameters = {name: p for name, p in model.named_parameters() if p.requires_grad}
    require(type(adapter) is dict and set(adapter) == set(parameters), "generation_adapter_keys")
    for name, value in adapter.items():
        parameter = parameters[name]
        require(isinstance(value, torch.Tensor) and value.dtype == parameter.dtype == torch.float32
                and value.shape == parameter.shape and bool(torch.isfinite(value).all()),
                "generation_adapter_shape_dtype_or_value")
    with torch.no_grad():
        for name, parameter in parameters.items():
            parameter.copy_(adapter[name].to(device=parameter.device))
    require(parameter_hash(model) == expected_hash, "generation_adapter_hash")
    for _, module in model.named_modules():
        if hasattr(module, "lora_A"):
            require(set(module.scaling) == {"default"} and module.scaling["default"] == 2.0
                    and module.r["default"] == 8 and module.lora_alpha["default"] == 16,
                    "generation_adapter_scaling")


def read_selected_adapter(checkpoint_dir):
    """Verify the complete selected SFT checkpoint before exposing adapter tensors."""
    import torch

    root = Path(checkpoint_dir)
    raw = read_bytes(root / "state.pt")
    require(sha(raw) == CHECKPOINT_SHA256, "selected_checkpoint_hash")
    manifest = document(root / "manifest.json")
    require(manifest["schema"] == "toolalign.cuda-sft-checkpoint.v1"
            and manifest["complete"] is True
            and manifest["checkpoint_sha256"] == CHECKPOINT_SHA256
            and manifest["best"]["checkpoint_sha256"] == CHECKPOINT_SHA256,
            "selected_checkpoint_manifest")
    state = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
    identity = state["identity"]
    require(state["schema"] == "toolalign.cuda-sft-state.v1"
            and state["optimizer_step"] == 743 and state["data_cursor"] == 5938
            and identity == manifest["identity"]
            and identity["source"]["commit"] == SFT_SOURCE_COMMIT
            and identity["config_identity"] == CONFIG_SHA256
            and identity["run_kind"] == "sft" and identity["profile"] == "formal"
            and identity["model_identity"]["model_id"] == MODEL_ID
            and identity["model_identity"]["revision"] == MODEL_REVISION,
            "selected_checkpoint_identity")
    return state["adapter"]


def prompt_ids(tokenizer, request):
    rendered = tokenizer.render(prompt_messages(request), tools=None,
                                add_generation_prompt=True, enable_thinking=False)
    return tokenizer.encode(rendered, add_special_tokens=False)


def decode_once(model, tokenizer, ids, config, *, device, identity,
                prefix_cache=None, cache_key=None, metrics=None):
    """Shared generation kernel. Production calls it only after the CUDA gate."""
    import torch
    from transformers import GenerationConfig as HFGenerationConfig
    from transformers import StoppingCriteria, StoppingCriteriaList

    class Deadline(StoppingCriteria):
        def __call__(self, input_ids, scores, **kwargs):
            return utc_remaining(config.deadline_utc) <= 0

    # Construct a fresh configuration: Qwen's original top_k/repetition settings
    # must not silently augment the frozen sampling parameters.
    options = HFGenerationConfig(
        max_new_tokens=config.max_new_tokens, do_sample=config.temperature > 0,
        temperature=config.temperature if config.temperature > 0 else 1.0,
        top_p=config.top_p if config.temperature > 0 else 1.0, top_k=0,
        num_beams=1, num_return_sequences=1, repetition_penalty=1.0,
        bos_token_id=151643, pad_token_id=151643, eos_token_id=tokenizer.eos_token_id,
        use_cache=True,
    )
    inputs = torch.tensor([ids], dtype=torch.long, device=device)
    # Each actual decision resets to the candidate's recorded seed.
    torch.manual_seed(config.seed)
    model.eval()
    with torch.no_grad():
        kwargs = dict(input_ids=inputs, attention_mask=torch.ones_like(inputs),
                      generation_config=options,
                      stopping_criteria=StoppingCriteriaList([Deadline()]))
        if metrics is None:
            generated = model.generate(**kwargs)
        else:
            from toolalign.model_io.prefix_cache import measured_generate

            generated = measured_generate(model, kwargs, prefix_cache=prefix_cache,
                                          key=cache_key, metrics=metrics)
    tokens = generated[0, len(ids):].tolist()
    eos = bool(tokens) and tokens[-1] == tokenizer.eos_token_id
    # Exclude the structural terminal EOS from text, but count it in usage.
    # Every other generated byte, including whitespace/special tokens, is retained.
    try:
        raw = tokenizer.decode(tokens[:-1] if eos else tokens, skip_special_tokens=False)
    except BaseException:
        if prefix_cache is not None:
            prefix_cache.clear()
        raise
    reason = "timed_out" if utc_remaining(config.deadline_utc) <= 0 else (
        "stop" if eos else "length" if len(tokens) >= config.max_new_tokens else "error")
    if prefix_cache is not None and reason != "stop":
        prefix_cache.clear()
    return ModelOutput(raw, None, None, identity, len(ids), len(tokens), reason)


class CUDAGenerationBackend:
    backend_label = "cuda-selected-sft.v1"

    def __init__(self, *, repository, model_root, checkpoint_dir, run_id, verified_files=None):
        self.repository = str(repository)
        self.model_root = str(model_root)
        self.checkpoint_dir = str(checkpoint_dir)
        self.run_id = run_id
        self.identity = selected_model_identity(repository)
        self._creator_pid = os.getpid()
        self._verified_files = verified_files
        self._tokenizer = self._model = self._lease = None
        self._metrics = {}

    def _report(self, stage, **updates):
        self._metrics.update(stage=stage, **updates)
        write_packet(Path("backend-metrics.json"), self._metrics)

    def _ensure_tokenizer(self):
        if self._tokenizer is None:
            self._metrics = {"backend": self.backend_label, "cold_load_seconds": None,
                             "cold_load_started_monotonic": time.monotonic(),
                             "seed_policy": "reset_per_decision",
                             "model_file_validation": BATCH_FILE_VALIDATION
                             if self._verified_files is not None else "child_full_hash.v1",
                             "cold_load_scope": "tokenizer_through_cuda_ready_excludes_batch_file_preflight"
                             if self._verified_files is not None
                             else "tokenizer_through_cuda_ready_includes_full_file_validation"}
            self._report("tokenizer_loading")
            # This verified engine must be constructed before importing torch.
            self._tokenizer = OfflineQwenTokenizer(self.model_root, repo_id=MODEL_ID,
                                                   revision=MODEL_REVISION)

    def _tokenize(self, request):
        self._ensure_tokenizer()
        return prompt_ids(self._tokenizer, request)

    def _require_owned_child(self):
        require(os.getpid() != self._creator_pid
                and multiprocessing.current_process().name.startswith("toolalign-model-"),
                "owned_model_child_required")

    def prepare(self):
        """Load in the owned child without tokenizing a fake request or decoding."""
        self._require_owned_child()
        self._ensure_tokenizer()
        if self._model is None:
            self._load()
        return {"model_identity": dict(self.identity), "metrics": dict(self._metrics)}

    def _load(self):
        config = load_protocol(self.repository)
        self._lease = GPULease(task_id="P05-G4-GENERATION", worker_alias="S1",
                               run_id=self.run_id, expected_job="generation",
                               memory_strategy="BF16_base_FP32_QV_LoRA_no_grad_KV_cache",
                               repository=self.repository, timeout_seconds=0)
        self._lease.__enter__()
        self._report("checkpoint_loading")
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = config["numerics"]["cublas_workspace_config"]
        import torch

        require(torch.cuda.is_available(), "CUDA_unavailable_no_fallback")
        require(torch.cuda.is_bf16_supported(), "CUDA_BF16_unavailable")
        torch.use_deterministic_algorithms(True, warn_only=False)
        adapter = read_selected_adapter(self.checkpoint_dir)
        self._report("model_loading")
        torch.cuda.reset_peak_memory_stats(0)
        self._model = load_model({"repository": self.repository, "model_root": self.model_root,
                                  "profile": "formal"}, config, self._lease,
                                 verified_files=self._verified_files)
        restore_adapter(self._model, adapter, expected_hash=ADAPTER_SHA256)
        del adapter
        self._model.gradient_checkpointing_disable()
        self._model.config.use_cache = True
        self._model.eval()
        torch.cuda.synchronize(0)
        self._report("ready", cold_load_seconds=time.monotonic()
                     - self._metrics["cold_load_started_monotonic"],
                     device=torch.cuda.get_device_name(0),
                     peak_allocated_bytes=torch.cuda.max_memory_allocated(0),
                     peak_reserved_bytes=torch.cuda.max_memory_reserved(0),
                     checkpoint_sha256=CHECKPOINT_SHA256, adapter_sha256=ADAPTER_SHA256)

    def _decode(self, ids, config):
        return decode_once(self._model, self._tokenizer, ids, config, device="cuda:0",
                           identity=self.identity)

    def generate(self, request, generation_config):
        self._require_owned_child()
        require(type(generation_config) is GenerationConfig, "generation_config_required")
        config = generation_config
        SamplingParameters(config.seed, config.temperature, config.top_p)
        require(config.max_new_tokens == MAX_NEW_TOKENS and config.enable_thinking is False,
                "fixed_generation_budget_required")
        if utc_remaining(config.deadline_utc) <= 0:
            return ModelOutput("", None, "deadline_before_tokenization", self.identity, 0, 0,
                               "timed_out")
        try:
            ids = self._tokenize(request)
            if len(ids) + config.max_new_tokens > CONTEXT_TOKENS:
                self._report("context_overflow", input_tokens=len(ids))
                return ModelOutput("", None, "context_overflow", self.identity, len(ids), 0, "error")
            if utc_remaining(config.deadline_utc) <= 0:
                return ModelOutput("", None, "deadline_before_load", self.identity, len(ids), 0,
                                   "timed_out")
            if self._model is None:
                self._load()
            if utc_remaining(config.deadline_utc) <= 0:
                return ModelOutput("", None, "deadline_before_forward", self.identity, len(ids), 0,
                                   "timed_out")
            output = self._decode(ids, config)
            import torch

            self._report("decision_complete", peak_allocated_bytes=torch.cuda.max_memory_allocated(0),
                         peak_reserved_bytes=torch.cuda.max_memory_reserved(0))
            return output
        except Exception as error:
            self._report("error", error_type=type(error).__name__, error=str(error)[:1000])
            raise
