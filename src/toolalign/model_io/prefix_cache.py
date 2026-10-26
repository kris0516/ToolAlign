"""One consumed-on-read DynamicCache, confined to one process lifetime."""

from __future__ import annotations

import os
import time

from toolalign.contracts import canonical_hash


class PrefixCache:
    def __init__(self):
        self._pid = os.getpid()
        self.clear()

    def clear(self):
        self._entry = None

    def take(self, ids, key):
        entry, self._entry = self._entry, None
        if self._pid != os.getpid() or entry is None:
            return None, 0
        digest, prefix, cache = entry
        if digest != canonical_hash(key) or tuple(ids[:len(prefix)]) != prefix:
            return None, 0
        # At least one prompt token must remain to produce the next-token logits.
        if len(ids) <= len(prefix) or cache.get_seq_length() != len(prefix):
            return None, 0
        return cache, len(prefix)

    def publish(self, ids, key, cache):
        from transformers.cache_utils import DynamicCache

        self.clear()
        if self._pid != os.getpid() or not 1 < len(ids) <= 2048:
            return
        if not isinstance(cache, DynamicCache):
            raise ValueError("dynamic_cache_required")
        prefix = tuple(ids[:-1])
        if cache.get_seq_length() < len(prefix):
            raise ValueError("incomplete_prefix_cache")
        cache.crop(len(prefix))
        self._entry = (canonical_hash(key), prefix, cache)


def measured_generate(model, kwargs, *, prefix_cache, key, metrics):
    """Identical synchronization/hooks with cache on or off; no output-score buffers.

    TTFT starts before cache lookup and ends when the first generated token reaches
    the streamer. Prefill measures the first forward, including a hot-cache suffix.
    Decode is the remainder after first token. Cold model load is measured outside.
    """
    import torch

    inputs = kwargs["input_ids"]
    ids = inputs[0].tolist()

    def sync():
        if inputs.device.type == "cuda":
            torch.cuda.synchronize(inputs.device)

    sync()
    started = time.monotonic()
    cache, hit = (None, 0) if prefix_cache is None else prefix_cache.take(ids, key)
    first_token = None
    forward_start = None
    forwards = []

    class Streamer:
        prompt = True

        def put(self, value):
            nonlocal first_token
            if self.prompt:
                self.prompt = False
            elif first_token is None:
                sync()
                first_token = time.monotonic()

        def end(self):
            pass

    def before(module, args, inputs):
        nonlocal forward_start
        sync()
        forward_start = time.monotonic()
        tokens = inputs.get("input_ids")
        forwards.append({"tokens": int(tokens.shape[-1]), "seconds": None})

    def after(module, args, output):
        sync()
        forwards[-1]["seconds"] = time.monotonic() - forward_start

    # PEFT.generate forwards directly through the wrapped causal LM.
    target = model.get_base_model() if hasattr(model, "get_base_model") else model
    handles = [target.register_forward_pre_hook(before, with_kwargs=True),
               target.register_forward_hook(after)]
    try:
        output = model.generate(**kwargs, past_key_values=cache,
                                return_dict_in_generate=True, streamer=Streamer())
        sync()
        finished = time.monotonic()
        if prefix_cache is not None:
            prefix_cache.publish(ids, key, output.past_key_values)
        metrics.update(cache_enabled=prefix_cache is not None, cache_hit_tokens=hit,
                       prompt_tokens=len(ids), prefill_tokens=forwards[0]["tokens"] if forwards else 0,
                       prefill_seconds=forwards[0]["seconds"] if forwards else None,
                       ttft_seconds=first_token - started if first_token is not None else None,
                       decode_seconds=finished - first_token if first_token is not None else None,
                       forward_calls=len(forwards), generation_seconds=time.monotonic() - started,
                       timing_scope="generation_includes_cache_lookup_and_publish_excludes_model_load")
        return output.sequences
    except BaseException:
        if prefix_cache is not None:
            prefix_cache.clear()
        raise
    finally:
        for handle in handles:
            handle.remove()
