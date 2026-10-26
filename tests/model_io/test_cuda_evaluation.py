"""Original random Qwen CPU evidence; no pretrained files or GPU operations."""

import copy
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from toolalign.contracts.interfaces import GenerationConfig
from toolalign.model_io.cuda_evaluation import CUDAEvaluationBackend, evaluation_model_identity
from toolalign.model_io.cuda_generation import decode_once
from toolalign.model_io.prefix_cache import PrefixCache
from toolalign.tools.scripted import SCRIPTED_IDENTITY

ROOT = Path(__file__).resolve().parents[2]
# Prespecified before running the original random fixture. No fitted tolerance.
ATOL, RTOL = 2e-6, 2e-5


class Tokenizer:
    eos_token_id = 9

    def decode(self, ids, *, skip_special_tokens):
        assert not skip_special_tokens
        return json.dumps(ids)


@pytest.fixture
def original_qwen():
    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    torch.set_num_threads(1)
    torch.manual_seed(1234)
    config = transformers.Qwen3Config(vocab_size=16, hidden_size=8, intermediate_size=16,
        num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1, head_dim=4,
        max_position_embeddings=2048, attention_dropout=0.0, eos_token_id=9, pad_token_id=0)
    config._attn_implementation = "sdpa"
    model = transformers.Qwen3ForCausalLM(config).eval()
    assert sum(p.numel() for p in model.parameters()) < 4096
    return torch, model


def generation():
    return GenerationConfig(42, 0.7, 0.9, 256,
                            (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat())


def run_decode(model, cache=None, key=None, ids=None, metrics=True):
    metric = {} if metrics else None
    steps = []
    target = model.get_base_model() if hasattr(model, "get_base_model") else model
    hook = target.register_forward_hook(lambda module, args, output: steps.append(output.logits[:, -1].detach().clone()))
    try:
        output = decode_once(model, Tokenizer(), ids or [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4], generation(),
            device="cpu", identity=SCRIPTED_IDENTITY, prefix_cache=cache, cache_key=key, metrics=metric)
    finally:
        hook.remove()
    return output, metric, steps


@pytest.mark.parametrize("adapter", [False, True])
def test_real_dynamic_cache_reduces_prefill_and_preserves_seeded_tokens_and_step_logits(original_qwen, adapter):
    torch, model = original_qwen
    if adapter:
        peft = pytest.importorskip("peft")
        model = peft.get_peft_model(model, peft.LoraConfig(task_type="CAUSAL_LM", r=8, lora_alpha=16,
            target_modules=["q_proj", "v_proj"], lora_dropout=0, bias="none"))
        with torch.no_grad():
            for p in model.parameters():
                if p.requires_grad:
                    p.fill_(0.025)
    key = {"model_identity": SCRIPTED_IDENTITY, "tenant_id": "original-cpu"}
    cache = PrefixCache()
    plain, _, baseline = run_decode(model, metrics=False)
    off, off_metric, off_logits = run_decode(model)
    cold, cold_metric, cold_logits = run_decode(model, cache, key)
    hot, hot_metric, hot_logits = run_decode(model, cache, key)
    assert plain == off == cold == hot
    assert hot.finish_reason == "stop" and hot.output_tokens > 1
    assert [m["cache_hit_tokens"] for m in (off_metric, cold_metric, hot_metric)] == [0, 0, 11]
    assert [m["prefill_tokens"] for m in (off_metric, cold_metric, hot_metric)] == [12, 12, 1]
    assert cache._entry[2].get_seq_length() == 11
    for actual in (off_logits, cold_logits, hot_logits):
        assert len(actual) == len(baseline)
        for expected, result in zip(baseline, actual):
            torch.testing.assert_close(result, expected, atol=ATOL, rtol=RTOL)
    for metric in (off_metric, cold_metric, hot_metric):
        assert metric["prefill_seconds"] > 0
        assert 0 < metric["ttft_seconds"] < metric["generation_seconds"]
        assert metric["decode_seconds"] >= 0


@pytest.mark.parametrize("field", ["model_hash", "adapter_hash", "tokenizer_hash", "template_hash", "tenant_id"])
def test_real_cached_prefix_cannot_cross_bound_identity(original_qwen, field):
    _, model = original_qwen
    cache = PrefixCache()
    key = {"model_identity": SCRIPTED_IDENTITY, "tenant_id": "original-cpu"}
    run_decode(model, cache, key)
    changed = copy.deepcopy(key)
    if field == "tenant_id":
        changed[field] = "different-tenant"
    else:
        changed["model_identity"][field] = "different-identity"
    _, metric, _ = run_decode(model, cache, changed)
    assert metric["cache_hit_tokens"] == 0 and metric["prefill_tokens"] == 12


def test_nonmatching_tokens_failure_deadline_and_process_lifetime_clear_real_cache(original_qwen, monkeypatch):
    _, model = original_qwen
    cache, key = PrefixCache(), {"tenant": "original"}
    run_decode(model, cache, key)
    _, metric, _ = run_decode(model, cache, key, ids=[2, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4])
    assert metric["cache_hit_tokens"] == 0
    cache._pid = -1
    _, metric, _ = run_decode(model, cache, key)
    assert metric["cache_hit_tokens"] == 0 and cache._entry is None
    cache = PrefixCache()
    run_decode(model, cache, key)
    expired = GenerationConfig(42, 0.7, 0.9, 256,
        (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
    output = decode_once(model, Tokenizer(), [1, 2, 3], expired, device="cpu", identity=SCRIPTED_IDENTITY,
                         prefix_cache=cache, cache_key=key, metrics={})
    assert output.finish_reason == "timed_out" and cache._entry is None
    run_decode(model, cache, key)
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise RuntimeError("original injected forward failure")
        patch.setattr(model, "forward", fail)
        with pytest.raises(RuntimeError, match="original injected"):
            run_decode(model, cache, key)
    assert cache._entry is None


def test_m0_and_m1_identities_are_distinct_and_constructor_imports_no_framework():
    m0, m1 = [evaluation_model_identity(ROOT, model) for model in ("M0", "M1")]
    assert m0["adapter_hash"] is None and m1["adapter_hash"] is not None
    assert m0 | {"adapter_hash": m1["adapter_hash"]} == m1
    code = """
import sys,json
from toolalign.model_io.cuda_evaluation import CUDAEvaluationBackend
from toolalign.evaluation.cuda_eval.runner import execute
for model in ('M0','M1'):
    CUDAEvaluationBackend(model=model, repository=sys.argv[1], model_root='/not-loaded',
                          checkpoint_dir='/not-loaded', run_id='original-cpu')
print(json.dumps(sorted({'torch','transformers','peft','mlx'} & set(sys.modules))))
"""
    process = subprocess.run([sys.executable, "-c", code, str(ROOT)], capture_output=True, text=True, check=True)
    assert json.loads(process.stdout) == []


@pytest.mark.parametrize("condition", ["M0", "M1"])
def test_cuda_dispatch_m0_never_reads_or_restores_adapter(condition, monkeypatch):
    """MOCK_ONLY CUDA boundary; real tiny tensor loader behavior is checked separately."""
    torch = pytest.importorskip("torch")
    from toolalign.model_io import cuda_evaluation as module

    calls = []
    class Lease:
        def __init__(self, **kwargs):
            calls.append(("lease", kwargs["expected_job"]))
        def __enter__(self):
            return self

    class Model:
        class Config:
            use_cache = False
        config = Config()
        def gradient_checkpointing_disable(self):
            pass
        def eval(self):
            pass

    monkeypatch.setattr(module, "GPULease", Lease)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "is_bf16_supported", lambda: True)
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", lambda *_: None)
    monkeypatch.setattr(torch.cuda, "synchronize", lambda *_: None)
    monkeypatch.setattr(torch.cuda, "get_device_name", lambda *_: "MOCK_ONLY")
    monkeypatch.setattr(module, "load_model", lambda *a, **k: calls.append(("load", k["with_adapter"])) or Model())
    monkeypatch.setattr(module, "read_selected_adapter", lambda *_: calls.append(("read", True)) or {"saved": 1})
    monkeypatch.setattr(module, "restore_adapter", lambda *a, **k: calls.append(("restore", True)))
    instance = CUDAEvaluationBackend(model=condition, repository=ROOT, model_root="/not-loaded",
                                      checkpoint_dir="/not-loaded", run_id="cpu-fixture")
    instance._metrics = {"cold_load_started_monotonic": 0}
    monkeypatch.setattr(instance, "_report", lambda *a, **k: None)
    instance._load()
    assert calls == ([("lease", "evaluation"), ("load", False)] if condition == "M0" else
                     [("lease", "evaluation"), ("read", True), ("load", True), ("restore", True)])


def test_m0_shared_loader_freezes_real_base_tensors_without_attaching_adapter(monkeypatch):
    """Real original CPU tensors; file/lease/HF loading and CUDA transfer are MOCK_ONLY."""
    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    from types import SimpleNamespace

    from toolalign.model_io import qwen_model
    from toolalign.training.cuda_sft import engine

    base = torch.nn.Linear(2, 2, bias=False).to(dtype=torch.bfloat16)
    calls = []
    monkeypatch.setattr(qwen_model, "require_current_lease", lambda *_: None)
    monkeypatch.setattr(qwen_model, "recheck_model_files", lambda *a, **k:
                         calls.append("file_stat") or SimpleNamespace(root=Path("/original-fixture"), expected_base_parameter_count=4))
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "is_bf16_supported", lambda: True)
    monkeypatch.setattr(transformers.AutoModelForCausalLM, "from_pretrained", lambda *a, **k: base)
    def no_adapter(*args):
        raise AssertionError("M0 attempted to attach PEFT")
    monkeypatch.setattr(engine, "attach_adapter", no_adapter)
    monkeypatch.setattr(base, "to", lambda *, device: calls.append(device) or base)
    result = engine.load_model({"repository": str(ROOT), "model_root": "/original-fixture", "profile": "formal"},
                               {"profiles": {"formal": {"model_id": "original", "model_revision": "v1"}}},
                               object(), verified_files=object(), with_adapter=False)
    assert result is base and not any(p.requires_grad for p in result.parameters())
    assert all(p.dtype == torch.bfloat16 for p in result.parameters())
    assert calls == ["file_stat", "cuda:0", "file_stat"]
