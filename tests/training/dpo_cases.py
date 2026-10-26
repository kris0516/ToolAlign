"""Original random-initialized CPU fixtures; no pretrained files or training data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
from tokenizers import Tokenizer, decoders, models, pre_tokenizers
from transformers import PreTrainedTokenizerFast, Qwen3Config, Qwen3ForCausalLM, TrainerCallback

from toolalign.training.cuda_dpo.checkpoint import inspect, validate_native_state
from toolalign.training.cuda_dpo.models import restore_pair
from toolalign.training.cuda_dpo.trainer import create_trainer
from toolalign.training.cuda_sft.checkpoint import parameter_hash
from toolalign.training.cuda_sft.engine import attach_adapter

ROOT = Path(__file__).resolve().parents[2]
ATOL, RTOL = 2e-6, 2e-5


def tokenizer():
    vocab = {"<pad>": 0, "<eos>": 1, "<unk>": 2}
    vocab.update({char: index + 3 for index, char in enumerate(sorted(pre_tokenizers.ByteLevel.alphabet()))})
    backend = Tokenizer(models.BPE(vocab=vocab, merges=[], unk_token="<unk>"))
    backend.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    backend.decoder = decoders.ByteLevel()
    return PreTrainedTokenizerFast(tokenizer_object=backend, pad_token="<pad>",
                                   eos_token="<eos>", unk_token="<unk>")


def base():
    torch.manual_seed(314159)
    config = Qwen3Config(vocab_size=259, hidden_size=8, intermediate_size=16,
                        num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1,
                        head_dim=4, max_position_embeddings=256, tie_word_embeddings=True,
                        attention_dropout=0, pad_token_id=0, eos_token_id=1, use_cache=False)
    config._attn_implementation = "sdpa"
    model = Qwen3ForCausalLM(config)
    model = attach_adapter(model, {"model": {"rank": 8, "lora_alpha": 16,
        "targets": ["q_proj", "v_proj"], "layers": 1, "lora_dropout": 0.0,
        "use_rslora": False, "gradient_checkpointing_use_reentrant": False}})
    assert sum(p.numel() for p in model.parameters()) < 4096
    return model


def pair():
    original = base()
    # Nonzero synthetic "SFT" adapter, generated directly, not obtained by training.
    with torch.no_grad():
        for name, value in original.named_parameters():
            if ".lora_B." in name:
                value.normal_(mean=0.0, std=0.03)
    adapter = {name: value.detach().clone() for name, value in original.named_parameters()
               if value.requires_grad}
    expected = parameter_hash(original)
    policy, reference = restore_pair(base(), base(), adapter, expected_hash=expected)
    return policy, reference, original


def rows(count=10):
    return [{"preference_id": f"synthetic-{index:02d}",
             "prompt": f"Synthetic task {index}." + "\n" * (1 + index % 3),
             "chosen": '{"answer":"' + "yes" * (1 + index % 2) + '"}',
             "rejected": ' { "answer": "' + "wrong" * (1 + index % 3) + '" } '}
            for index in range(count)]


def expected_tokens(values, processor):
    result = []
    for row in values:
        entry = {"preference_id": row["preference_id"],
                 "prompt_input_ids": processor.encode(row["prompt"], add_special_tokens=False)}
        for side in ("chosen", "rejected"):
            completion = processor.encode(row[side], add_special_tokens=False)
            assert processor.encode(row["prompt"] + row[side], add_special_tokens=False) == (
                entry["prompt_input_ids"] + completion)
            entry[side + "_input_ids"] = completion + [processor.eos_token_id]
        result.append(entry)
    return result


def config():
    return json.loads((ROOT / "configs/dpo-cuda.v1.json").read_text())


def trainer_at(output, *, count=10, stop=2, identities=None):
    policy, reference, original = pair()
    processor, values = tokenizer(), rows(count)
    expected = expected_tokens(values, processor)
    trainer, boundary = create_trainer(
        policy=policy, reference=reference, tokenizer=processor, rows=values, expected=expected,
        config=config(), output=output, identity=identities or {"synthetic": True, "fixture": "v1"},
        stop_step=stop, use_cpu=True,
    )
    return trainer, boundary, expected, original


def manual_logps(model, prompt, completion):
    """Independent unpadded forward, one scalar logsumexp per completion target."""
    ids = prompt + completion
    logits = model(torch.tensor([ids]), attention_mask=torch.ones(1, len(ids), dtype=torch.long),
                   use_cache=False).logits[0]
    terms = [logits[position - 1, token].double()
             - torch.logsumexp(logits[position - 1].double(), dim=0)
             for position, token in enumerate(ids) if position >= len(prompt)]
    return torch.stack(terms).sum(), torch.stack(terms)


def manual_loss(policy, reference, expected):
    losses, all_terms = [], []
    for row in expected:
        p_c, tc = manual_logps(policy, row["prompt_input_ids"], row["chosen_input_ids"])
        p_r, tr = manual_logps(policy, row["prompt_input_ids"], row["rejected_input_ids"])
        with torch.no_grad():
            r_c, _ = manual_logps(reference, row["prompt_input_ids"], row["chosen_input_ids"])
            r_r, _ = manual_logps(reference, row["prompt_input_ids"], row["rejected_input_ids"])
        score = 0.1 * ((p_c - p_r) - (r_c - r_r))
        losses.append(torch.logaddexp(torch.zeros_like(score), -score))
        all_terms.append((tc, tr))
    return torch.stack(losses).mean(), all_terms


class GradientAudit(TrainerCallback):
    def __init__(self):
        self.values = []

    def on_pre_optimizer_step(self, args, state, control, model=None, **kwargs):
        self.values.append({name: value.grad.detach().clone()
                            for name, value in model.named_parameters() if value.requires_grad})


def run(output, stop, resume=None):
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    trainer, boundary, expected, _ = trainer_at(output, stop=stop)
    audit = GradientAudit()
    trainer.add_callback(audit)
    if resume is not None:
        from toolalign.training.cuda_sft.protocol import document

        previous = document(Path(resume) / "dpo-manifest.json")
        manifest = inspect(resume, identity=boundary.identity,
                           expected_sha=previous["checkpoint_sha256"], pair_count=10, max_bytes=1024**3)
        validate_native_state(resume, trainer.model, manifest)
    before = {"policy_base": parameter_hash(trainer.model, trainable=False),
              "policy_adapter": parameter_hash(trainer.model),
              "reference_all": parameter_hash(trainer.ref_model, trainable=False)}
    trainer.train(resume_from_checkpoint=resume)
    after = {"policy_base": parameter_hash(trainer.model, trainable=False),
             "policy_adapter": parameter_hash(trainer.model),
             "reference_all": parameter_hash(trainer.ref_model, trainable=False)}
    torch.save({"gradients": audit.values}, Path(output) / "gradient-audit.pt")
    result = {"synthetic": True, "real_model_loaded": False, "before": before, "after": after,
              "consumed": trainer.consumed, "events": boundary.events,
              "precision": boundary.precision, "step": trainer.state.global_step,
              "epoch": trainer.state.epoch, "total_steps": trainer.state.max_steps}
    (Path(output) / "fixture-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    run(Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
