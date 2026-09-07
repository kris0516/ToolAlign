"""Original R1 probes. Array stand-ins below are explicit CPU simulations."""

import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolalign.model_io import qwen_model as q


@pytest.mark.parametrize("operation", ["hash", "bytes", "header"])
@pytest.mark.parametrize("replacement", ["fifo", "symlink"])
def test_bounded_replacement_before_actual_open(tmp_path, operation, replacement):
    result = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).with_name("io_probe.py")),
         str(tmp_path / "fixture"), operation, replacement],
        capture_output=True, text=True, timeout=4, check=True,
    )
    assert not result.stderr and json.loads(result.stdout)["status"] == "PASS"
    print(result.stdout.strip())


def test_parent_replaced_after_directory_fd_is_open(tmp_path):
    result = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).with_name("io_probe.py")),
         str(tmp_path / "fixture"), "hash", "parent"],
        capture_output=True, text=True, timeout=4, check=True,
    )
    assert not result.stderr and json.loads(result.stdout)["status"] == "PASS"
    print(result.stdout.strip())


@pytest.mark.parametrize("model_id", ["Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B"])
def test_complete_mapping_from_pinned_qwen_and_lora_dimensions(model_id):
    root = Path(__file__).resolve().parents[3]
    raw = (root / "configs/qwen-models.v1.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == q.CONFIG_SHA256
    config = json.loads(raw)
    assert config["is_run_authorization"] is False
    spec = config["models"][model_id]
    c = spec["model_config"]
    d, h, qdim, kvdim = (c["hidden_size"], c["intermediate_size"],
                         c["head_dim"] * c["num_attention_heads"],
                         c["head_dim"] * c["num_key_value_heads"])
    # These names/shapes follow the pinned Qwen3 constructors, independently
    # of the candidate's declared mapping and count fields.
    expected = {"model.embed_tokens.weight": [c["vocab_size"], d], "model.norm.weight": [d]}
    adapters = {}
    for i in range(c["num_hidden_layers"]):
        prefix = f"model.layers.{i}."
        layer = {"input_layernorm.weight": [d], "post_attention_layernorm.weight": [d],
                 "self_attn.q_proj.weight": [qdim, d], "self_attn.k_proj.weight": [kvdim, d],
                 "self_attn.v_proj.weight": [kvdim, d], "self_attn.o_proj.weight": [d, qdim],
                 "self_attn.q_norm.weight": [c["head_dim"]],
                 "self_attn.k_norm.weight": [c["head_dim"]],
                 "mlp.gate_proj.weight": [h, d], "mlp.up_proj.weight": [h, d],
                 "mlp.down_proj.weight": [d, h]}
        expected.update({prefix + k: v for k, v in layer.items()})
        for name, output in (("q_proj", qdim), ("v_proj", kvdim)):
            adapters[prefix + "self_attn." + name + ".lora_a"] = [d, 8]
            adapters[prefix + "self_attn." + name + ".lora_b"] = [8, output]
    serialized = spec["serialized_tensors"]
    assert set(serialized) == set(expected) | {"lm_head.weight"}
    assert all(serialized[n]["shape"] == shape and serialized[n]["dtype"] == "BF16"
               for n, shape in expected.items())
    assert c["tie_word_embeddings"] is True
    assert spec["expected_loader_sanitize_drop"] == ["lm_head.weight"]
    for field in ("shape", "dtype", "raw_tensor_sha256"):
        assert serialized["lm_head.weight"][field] == serialized["model.embed_tokens.weight"][field]
    mapping = {n: n.removesuffix(".weight") + ".linear.weight"
               if n.endswith(("self_attn.q_proj.weight", "self_attn.v_proj.weight")) else n
               for n in expected}
    assert mapping == spec["expected_raw_to_lora_frozen_key_mapping"]
    assert {n: v["shape"] for n, v in spec["expected_lora"]["tensors"].items()} == adapters
    assert len(set(mapping.values())) == 310 and len(adapters) == 112
    assert all(v["dtype"] == "float32" and v["parameters"] == math.prod(adapters[n])
               for n, v in spec["expected_lora"]["tensors"].items())
    assert spec["expected_frozen_parameter_count"] == sum(math.prod(s) for s in expected.values())
    assert spec["expected_lora"]["parameter_count"] == sum(math.prod(s) for s in adapters.values())
    frozen = q._frozen_spec(spec, lora=True)
    assert {n: v["shape"] for n, v in frozen.items()} == {mapping[n]: s for n, s in expected.items()}
    assert {n: v["shape"] for n, v in q._adapter_spec(spec).items()} == adapters
    print(json.dumps({"model_id": model_id, "complete_base_names": len(expected),
                      "complete_frozen_mapping": len(mapping), "complete_adapter_names": len(adapters),
                      "runtime": "NOT_RUN; source-derived mapping and intake-bound header shapes"}))


class ByteArray:
    """An original byte container, not an MLX or NumPy array."""

    def __init__(self, raw, dtype, shape=None):
        self.raw, self.dtype = raw, dtype
        self.width = {"BF16": 2, "F32": 4, "U8": 1}[dtype]
        self.size = len(raw) // self.width
        self.shape = (self.size,) if shape is None else shape

    def reshape(self, dimension):
        assert dimension == -1
        return ByteArray(self.raw, self.dtype)

    def __getitem__(self, part):
        assert part.step is None
        return ByteArray(self.raw[part.start * self.width:part.stop * self.width], self.dtype)


def byte_runtime():
    copies = []

    class Host:
        dtype = "uint8"
        flags = SimpleNamespace(c_contiguous=True)

        def __init__(self, raw):
            self.raw = raw

        def tobytes(self, *, order):
            assert order == "C"
            copies.append(len(self.raw))
            return self.raw

    def view(a, dtype):
        assert dtype == "U8"
        return ByteArray(a.raw, "U8")

    def asarray(a, *, order):
        assert a.dtype == "U8" and order == "C"
        return Host(a.raw)

    mx = SimpleNamespace(array=ByteArray, bfloat16="BF16", float32="F32", uint8="U8",
                         contiguous=lambda x: x, view=view, eval=lambda x: None)
    numpy = SimpleNamespace(asarray=asarray, dtype=lambda x: x)
    return mx, numpy, copies


def test_simulated_original_bf16_payload_preserves_signed_zero_and_nan_bits():
    mx, numpy, copies = byte_runtime()
    raw = struct.pack("<4H", 0x0000, 0x8000, 0x7FC1, 0x7FC2)
    value = q._leaf(ByteArray(raw, "BF16"), {"shape": [4], "dtype": "BF16"}, mx, numpy)
    assert value["bytes"] == 8 and value["raw_tensor_sha256"] == hashlib.sha256(raw).hexdigest()
    converted = struct.pack("<4I", 0x00000000, 0x80000000, 0x7FC10000, 0x7FC20000)
    assert value["raw_tensor_sha256"] != hashlib.sha256(converted).hexdigest()
    assert copies == [8]


def test_simulated_host_copy_limit_includes_final_partial_chunk():
    mx, numpy, copies = byte_runtime()
    raw = b"\x81\x3f" * (q._CHUNK_BYTES // 2 + 3)
    value = q._leaf(ByteArray(raw, "BF16"), {"shape": [len(raw) // 2], "dtype": "BF16"}, mx, numpy)
    assert value["raw_tensor_sha256"] == hashlib.sha256(raw).hexdigest()
    assert copies == [1024 * 1024, 6]


@pytest.mark.parametrize("bits", [0x7F800000, 0x7FC00001])
def test_simulated_nonfinite_adapter_bytes_are_rejected(bits):
    mx, numpy, _ = byte_runtime()
    with pytest.raises(q.QwenModelError, match="^nonfinite_adapter_parameter$"):
        q._leaf(ByteArray(struct.pack("<I", bits), "F32"), {"shape": [1], "dtype": "F32"}, mx, numpy)


def test_simulated_adapter_shape_and_raw_content_are_both_bound():
    mx, numpy, _ = byte_runtime()
    raw = struct.pack("<6f", 0.0, -0.0, 1.0, 2.0, 3.0, 4.0)
    expected = {"shape": [2, 3], "dtype": "F32", "raw_tensor_sha256": hashlib.sha256(raw).hexdigest()}
    q._leaf(ByteArray(raw, "F32", (2, 3)), expected, mx, numpy)
    with pytest.raises(q.QwenModelError, match="^runtime_tensor_shape$"):
        q._leaf(ByteArray(raw, "F32", (3, 2)), expected, mx, numpy)
    changed = struct.pack("<6f", 0.0, 0.0, 1.0, 2.0, 3.0, 4.0)
    with pytest.raises(q.QwenModelError, match="^runtime_parameter_content_mismatch$"):
        q._leaf(ByteArray(changed, "F32", (2, 3)), expected, mx, numpy)
