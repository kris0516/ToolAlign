"""Small CPU fixtures; no pretrained model, tokenizer file or CUDA access."""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from toolalign.contracts.interfaces import GenerationConfig, SandboxContext
from toolalign.evaluation.harness import LocalHarness
from toolalign.model_io.cuda_generation import (
    CUDAGenerationBackend,
    decode_once,
    prompt_ids,
    restore_adapter,
    selected_model_identity,
)
from toolalign.model_io.format import prompt_messages
from toolalign.tools import CancellationToken, LocalToolExecutor, LocalToolRegistry
from toolalign.tools.__main__ import development_case
from toolalign.tools.scripted import SCRIPTED_IDENTITY

ROOT = Path(__file__).resolve().parents[2]
CASE = {"id": "cpu-generation-original", "group": "cpu-generation-test", "category": "no_tool",
        "prompt": "Return the number 17 without calling a tool.",
        "scripted_responses": [json.dumps({"kind": "final", "content": "17", "tool_calls": []})],
        "answers": [{"kind": "final", "value": 17}], "strategies": [[]]}


def backend(cls=CUDAGenerationBackend):
    return cls(repository=str(ROOT), model_root="/not-loaded-model",
               checkpoint_dir="/not-loaded-checkpoint", run_id="cpu-fixture")


class OverflowBackend(CUDAGenerationBackend):
    def _tokenize(self, request):
        return [1] * 1793

    def _load(self):
        raise AssertionError("overflow must reject before model loading")


class SlowLoadBackend(CUDAGenerationBackend):
    def _tokenize(self, request):
        self._metrics = {"cold_load_started_monotonic": time.monotonic(), "cold_load_seconds": None}
        self._report("model_loading")
        return [1, 2]

    def _load(self):
        time.sleep(60)


def owned_run(tmp_path, instance, seconds=5):
    registry = LocalToolRegistry()
    example, task = development_case(CASE, registry)
    context = SandboxContext(tmp_path.resolve(), "cpu-generation-fixture",
        (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(), CancellationToken())
    return LocalHarness(registry, LocalToolExecutor(registry)).run(
        example, task, instance, context, model_identity=instance.identity)


def test_cuda_backend_requires_the_harness_child_before_loading():
    instance = backend()
    config = GenerationConfig(42, 0.7, 0.9, 256,
        (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat())
    with pytest.raises(ValueError, match="owned_model_child_required"):
        instance.generate({}, config)
    assert instance.identity == selected_model_identity(ROOT)


def test_overflow_counts_complete_input_without_loading_or_truncating(tmp_path):
    result = owned_run(tmp_path, backend(OverflowBackend))
    assert result.score.outcome == "failure"
    decision = result.decisions[0]
    assert decision["backend_parse_failure"] == "context_overflow"
    assert decision["input_tokens"] == 1793 and decision["output_tokens"] == 0
    assert decision["raw_text"] == "" and decision["finish_reason"] == "error"
    assert result.process_records[0]["reaped"]
    assert len(result.decision_inputs) == 1


def test_cold_load_deadline_reaps_child_and_preserves_incomplete_cost(tmp_path):
    result = owned_run(tmp_path, backend(SlowLoadBackend), seconds=0.8)
    assert result.trace[-1]["event"] == "timed_out"
    assert result.process_records[0]["stopped"] and result.process_records[0]["reaped"]
    metric = result.provenance["backend_metrics"]
    assert metric["cold_load_seconds"] is None
    assert metric["incomplete_cold_load_seconds"] > 0
    assert result.trace[-1]["latency_ms"] < 3000
    assert not list(tmp_path.iterdir())


class ToyTokenizer:
    eos_token_id = 9

    def decode(self, ids, *, skip_special_tokens):
        assert skip_special_tokens is False
        self.decoded = ids
        return '  {"not_repaired":true}\n'

    def render(self, messages, **options):
        self.messages, self.options = messages, options
        return json.dumps(messages)

    def encode(self, text, *, add_special_tokens):
        assert add_special_tokens is False
        return [1, 2]


def test_prompt_uses_complete_fixed_projection():
    registry = LocalToolRegistry()
    example, _ = development_case(CASE, registry)
    request = {key: example[key] for key in ("messages", "tools")}
    tokenizer = ToyTokenizer()
    assert prompt_ids(tokenizer, request) == [1, 2]
    assert tokenizer.messages == prompt_messages(request)
    assert tokenizer.options == {"tools": None, "add_generation_prompt": True, "enable_thinking": False}


@pytest.mark.parametrize("mode", ["sample", "greedy", "length", "deadline"])
def test_decode_preserves_raw_counts_and_explicit_hf_parameters(mode):
    torch = pytest.importorskip("torch")
    pytest.importorskip("transformers")
    tokenizer = ToyTokenizer()
    tokens = [3] * 256 if mode == "length" else [3, 4, 9]

    class Model:
        def eval(self):
            self.evaluating = True

        def generate(self, **kwargs):
            assert self.evaluating and not torch.is_grad_enabled()
            self.options = kwargs["generation_config"]
            assert kwargs["stopping_criteria"][0](None, None) == (mode == "deadline")
            return torch.tensor([[1, 2] + tokens])

    model = Model()
    config = GenerationConfig(43, 0.0 if mode == "greedy" else 0.7, 0.9, 256,
        (datetime.now(timezone.utc) + timedelta(seconds=-1 if mode == "deadline" else 10)).isoformat())
    output = decode_once(model, tokenizer, [1, 2], config, device="cpu", identity=SCRIPTED_IDENTITY)
    assert output.raw_text == '  {"not_repaired":true}\n'
    assert output.parsed_action is None and output.parse_failure is None
    assert output.input_tokens == 2 and output.output_tokens == len(tokens)
    assert tokenizer.decoded == (tokens if mode == "length" else tokens[:-1])
    assert output.finish_reason == {"length": "length", "deadline": "timed_out"}.get(mode, "stop")
    assert model.options.do_sample == (mode != "greedy")
    assert model.options.top_k == 0 and model.options.repetition_penalty == 1.0
    assert model.options.max_new_tokens == 256 and model.options.num_beams == 1
    assert model.options.top_p == (1.0 if mode == "greedy" else 0.9)


def test_selected_adapter_copy_checks_keys_values_hash_and_scaling():
    torch = pytest.importorskip("torch")
    peft = pytest.importorskip("peft")
    from toolalign.training.cuda_sft.checkpoint import parameter_hash

    # An original 2x2 projection, with the production rank/alpha convention.
    model = peft.get_peft_model(torch.nn.Sequential(torch.nn.Linear(2, 2, bias=False)),
        peft.LoraConfig(r=8, lora_alpha=16, target_modules=["0"], lora_dropout=0.0, bias="none"))
    with torch.no_grad():
        for p in model.parameters():
            if p.requires_grad:
                p.fill_(0.25)
    stored = {n: p.detach().clone() for n, p in model.named_parameters() if p.requires_grad}
    expected = parameter_hash(model)
    with torch.no_grad():
        for p in model.parameters():
            if p.requires_grad:
                p.zero_()
    restore_adapter(model, stored, expected_hash=expected)
    assert parameter_hash(model) == expected
    with pytest.raises(ValueError, match="adapter_keys"):
        restore_adapter(model, {}, expected_hash=expected)
    with pytest.raises(ValueError, match="adapter_hash"):
        restore_adapter(model, stored, expected_hash="0" * 64)
    wrong = {n: value.to(torch.bfloat16) for n, value in stored.items()}
    with pytest.raises(ValueError, match="shape_dtype"):
        restore_adapter(model, wrong, expected_hash=expected)
    layer = next(m for m in model.modules() if hasattr(m, "lora_A"))
    layer.scaling["default"] = 4.0
    with pytest.raises(ValueError, match="adapter_scaling"):
        restore_adapter(model, stored, expected_hash=expected)
