"""Optional offline CPU tokenizer adapter; importing this module imports no engine.

The model-independent callbacks in sequence.py remain usable by other trusted
application adapters. This adapter supports only the CPU environments audited here.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import os
import sys
import tempfile
from pathlib import Path

from .format import TEMPLATE_SHA256, ModelIOError, format_identity
from .sequence import build_sequence, training_sequence

_REVISIONS = {
    "Qwen/Qwen3-0.6B": "c1899de289a04d12100db370d81485cdf75e47ca",
    "Qwen/Qwen3-1.7B": "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e",
}
_FILES = {
    "tokenizer.json": {
        "sha256": "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
        "size_bytes": 11422654,
    },
    "tokenizer_config.json": {
        "sha256": "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101",
        "size_bytes": 9732,
    },
    "LICENSE": {
        "sha256": "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
        "size_bytes": 11343,
    },
}
_MODEL_ROOTS = {"torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax"}


def model_modules_loaded() -> list[str]:
    return sorted({name.split(".", 1)[0] for name in sys.modules} & _MODEL_ROOTS)


def _source_bytes(root: Path) -> dict[str, bytes]:
    result = {}
    for name, expected in _FILES.items():
        try:
            if (root / name).stat().st_size != expected["size_bytes"]:
                raise ModelIOError("tokenizer_source_size_mismatch")
            data = (root / name).read_bytes()
        except OSError as exc:
            raise ModelIOError("tokenizer_source_unavailable") from exc
        if hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ModelIOError("tokenizer_source_hash_mismatch")
        result[name] = data
    return result


def _reference_from_snapshot(data: dict[str, bytes], template: str):
    """Load real HF from a private snapshot of the verified buffers, eagerly.

    The caller's directory can be updated while HF opens its inputs. Never give
    that mutable directory to HF, or copy its unverified overrides/extra files.
    Only these three verified buffers enter a fresh directory; it is read-only
    during loading and removed on success or exception. This binds ordinary
    source-directory updates, not arbitrary same-user OS tampering.
    """
    from transformers import AutoTokenizer

    try:
        with tempfile.TemporaryDirectory(prefix="toolalign-qwen-tokenizer-") as temporary:
            snapshot = Path(temporary)
            for name in _FILES:
                with (snapshot / name).open("xb") as stream:
                    stream.write(data[name])
                (snapshot / name).chmod(0o400)
            snapshot.chmod(0o500)
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    str(snapshot), local_files_only=True, trust_remote_code=False
                )
                if tokenizer.chat_template != template:
                    raise ModelIOError("loaded_tokenizer_source_mismatch")
            finally:
                # Restore directory write permission only for our own cleanup.
                snapshot.chmod(0o700)
        return tokenizer
    except ModelIOError:
        raise
    except (OSError, ValueError) as exc:
        raise ModelIOError("tokenizer_reference_snapshot_load_failed") from exc


class OfflineQwenTokenizer:
    """Fixed local tokenizer bytes with either native tokenizers or HF rendering.

    HF use requires USE_TORCH/USE_TF/USE_FLAX=0 and offline environment variables
    to be set by the CPU process before construction. No model class is loaded.
    """

    def __init__(self, root, *, repo_id: str, revision: str, engine: str = "tokenizers"):
        format_identity()
        if type(repo_id) is not str or type(revision) is not str or _REVISIONS.get(repo_id) != revision:
            raise ModelIOError("tokenizer_model_revision_mismatch")
        if type(engine) is not str or engine not in ("tokenizers", "transformers"):
            raise ModelIOError("unsupported_tokenizer_engine")
        if model_modules_loaded():
            raise ModelIOError("tokenizer_only_process_required")
        root = Path(root)
        data = _source_bytes(root)
        config = json.loads(data["tokenizer_config.json"])
        template = config["chat_template"]
        if hashlib.sha256(template.encode()).hexdigest() != TEMPLATE_SHA256:
            raise ModelIOError("template_identity_mismatch")
        packages = {p: importlib.metadata.version(p) for p in ("tokenizers", "Jinja2")}
        if packages["Jinja2"] != "3.1.6" or packages["tokenizers"] not in ("0.22.2", "0.23.2"):
            raise ModelIOError("unsupported_tokenizer_package_identity")
        self._engine = engine
        self._template_text = template
        self._eos_token = config["eos_token"]
        if engine == "tokenizers":
            from jinja2.sandbox import ImmutableSandboxedEnvironment
            from tokenizers import Tokenizer

            environment = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
            environment.filters["tojson"] = lambda value: json.dumps(value, ensure_ascii=False)
            self._template = environment.from_string(template)
            # Construct from the bytes just verified, not a second unbound path read.
            self._tokenizer = Tokenizer.from_str(data["tokenizer.json"].decode())
            self._eos_token_id = self._tokenizer.token_to_id(self.eos_token)
        else:
            if any(os.environ.get(name) != "0" for name in ("USE_TORCH", "USE_TF", "USE_FLAX")):
                raise ModelIOError("tokenizer_only_environment_required")
            if any(os.environ.get(name) != "1" for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")):
                raise ModelIOError("offline_environment_required")
            packages["transformers"] = importlib.metadata.version("transformers")
            if packages["transformers"] != "5.16.1" or packages["tokenizers"] != "0.23.2":
                raise ModelIOError("unsupported_reference_package_identity")
            self._tokenizer = _reference_from_snapshot(data, template)
            self._eos_token_id = self._tokenizer.eos_token_id
        if model_modules_loaded():
            raise ModelIOError("model_dependency_imported")
        if (
            self.eos_token != "<|im_end|>" or self.eos_token_id != 151645
            or self.encode(self.eos_token, add_special_tokens=False) != [self.eos_token_id]
        ):
            raise ModelIOError("tokenizer_eos_identity_mismatch")
        self._identity = {
            "repo_id": repo_id, "revision": revision, "engine": engine,
            "files": copy.deepcopy(_FILES), "template_sha256": TEMPLATE_SHA256,
            "eos_token": self.eos_token, "eos_token_id": self.eos_token_id,
            "packages": packages,
            "render_parameters": {
                "tools": None, "add_generation_prompt": True, "enable_thinking": False,
            },
            "encoding_parameters": {"add_special_tokens": False},
            "decoding_parameters": {
                "skip_special_tokens": False,
                "clean_up_tokenization_spaces": False if engine == "transformers" else None,
            },
        }

    @property
    def identity(self) -> dict:
        return copy.deepcopy(self._identity)

    @property
    def eos_token(self) -> str:
        return self._eos_token

    @property
    def eos_token_id(self) -> int:
        return self._eos_token_id

    def render(self, messages, *, tools, add_generation_prompt, enable_thinking) -> str:
        if tools is not None or add_generation_prompt is not True or enable_thinking is not False:
            raise ModelIOError("renderer_parameters_mismatch")
        if type(messages) is not list or any(
            type(m) is not dict or set(m) != {"role", "content"}
            or m["role"] not in ("system", "user", "assistant", "tool")
            or type(m["content"]) is not str for m in messages
        ):
            raise ModelIOError("invalid_template_messages")
        if self._engine == "transformers":
            return self._tokenizer.apply_chat_template(
                messages, tools=None, tokenize=False, add_generation_prompt=True,
                enable_thinking=False,
            )
        return self._template.render(
            messages=messages, tools=None, add_generation_prompt=True, enable_thinking=False
        )

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        if type(text) is not str or add_special_tokens is not False:
            raise ModelIOError("encoder_parameters_mismatch")
        encoded = self._tokenizer.encode(text, add_special_tokens=False)
        return list(encoded.ids) if self._engine == "tokenizers" else list(encoded)

    def decode(self, ids, *, skip_special_tokens: bool) -> str:
        if skip_special_tokens is not False:
            raise ModelIOError("decoder_parameters_mismatch")
        if self._engine == "transformers":
            return self._tokenizer.decode(
                list(ids), skip_special_tokens=False, clean_up_tokenization_spaces=False
            )
        return self._tokenizer.decode(list(ids), skip_special_tokens=False)

    def callbacks(self) -> dict:
        return {
            "renderer": self.render, "encoder": self.encode, "decoder": self.decode,
            "eos_token_id": self.eos_token_id, "eos_token": self.eos_token,
            "template_sha256": self._identity["template_sha256"],
        }

    def sequence(self, model_input: dict, action: dict):
        return build_sequence(model_input, action, **self.callbacks())

    def training_sequence(self, example: dict):
        return training_sequence(example, **self.callbacks())
