"""Original CPU fixtures and MOCK_ONLY runtime objects; no real model/framework run.

Miniature specifications exercise private validators, never the public pinned
configuration gate. Public loader orchestration tests explicitly mock file,
environment and model operations. Production constants are never relaxed.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.machinery
import json
import os
import struct
import subprocess
import sys
import types
from dataclasses import make_dataclass
from pathlib import Path

import pytest

from toolalign.model_io import qwen_model as qm
from toolalign.runtime.gpu_lock import GPULease, LockBusy, inspect_gpu_lock, lock_path

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "configs/qwen-models.v1.json"


def info(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def original_safetensors(path, members, *, header_bytes=None, extra_payload=b""):
    """Write small original bit patterns using the documented 8-byte JSON header framing."""
    header, raw, expected = {"__metadata__": {"fixture": "MOCK_ONLY"}}, b"", {}
    for name, (dtype, shape, data) in members.items():
        start = len(raw)
        raw += data
        header[name] = {"dtype": dtype, "shape": shape, "data_offsets": [start, len(raw)]}
        expected[name] = {**header[name], "bytes": len(data), "file": path.name,
                          "raw_tensor_sha256": hashlib.sha256(data).hexdigest()}
    if header_bytes is None:
        header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode()
    header_bytes += b" " * (-len(header_bytes) % 8)
    path.write_bytes(struct.pack("<Q", len(header_bytes)) + header_bytes + raw + extra_payload)
    summary = {"header_bytes": len(header_bytes), "header_sha256": hashlib.sha256(header_bytes).hexdigest(),
               "metadata": header["__metadata__"], "tensor_count": len(members),
               "tensor_payload_bytes": len(raw)}
    return expected, summary


@pytest.fixture
def miniature(tmp_path):
    """Private validator input: three 2x2 BF16 leaves, not an accepted Qwen model."""
    root = tmp_path.resolve() / "MOCK_ONLY"
    root.mkdir()
    embedding = bytes.fromhex("0000803f00400040")
    projection = bytes.fromhex("803e803f003f00bf")
    members = {"lm_head.weight": ("BF16", [2, 2], embedding),
               "model.embed_tokens.weight": ("BF16", [2, 2], embedding),
               "model.layers.0.self_attn.q_proj.weight": ("BF16", [2, 2], projection)}
    tensors, header = original_safetensors(root / "model.safetensors", members)
    model_config = {"model_type": "MOCK_ONLY", "tie_word_embeddings": True, "layers": 1}
    generation = {"eos_token_id": [4, 3], "pad_token_id": 3, "do_sample": True}
    for name, value in {"config.json": model_config, "generation_config.json": generation,
                        "tokenizer.json": {"MOCK_ONLY": True}}.items():
        (root / name).write_text(json.dumps(value))
    target = "model.layers.0.self_attn.q_proj"
    lora = {target + ".lora_a": {"shape": [2, 8], "dtype": "float32", "parameters": 16},
            target + ".lora_b": {"shape": [8, 2], "dtype": "float32", "parameters": 16}}
    spec = {"model_id": "MOCK_ONLY", "revision": "MOCK_ONLY", "model_config": model_config,
            "generation_config_original": generation, "files": {p.name: info(p.read_bytes()) for p in root.iterdir()},
            "serialized_tensors": tensors, "serialized_tensor_count": 3, "serialized_parameter_count": 12,
            "headers": {"model.safetensors": header}, "expected_loader_sanitize_drop": ["lm_head.weight"],
            "expected_frozen_leaf_tensors": 2, "expected_frozen_parameter_count": 8,
            "expected_raw_to_lora_frozen_key_mapping": {"model.embed_tokens.weight": "model.embed_tokens.weight",
                                                       target + ".weight": target + ".linear.weight"},
            "expected_lora": {"tensors": lora, "parameter_count": 32, "tensor_count": 2, "module_count": 1},
            "expected_model_leaf_tensors_with_lora": 4}
    return root, spec, members


@pytest.mark.parametrize("raw", [b'{"x":0,"x":1}', b'{"a":{"x":0,"x":1}}', b'{"x":NaN}',
                                 b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}', b'\xff', b'[]x',
                                 '{"x":1}'.encode("utf-16"), b'\xef\xbb\xbf{}'])
def test_strict_json_rejects_duplicate_nonfinite_or_malformed(raw):
    with pytest.raises(qm.QwenModelError):
        qm._json(raw)


@pytest.mark.parametrize("left,right", [(False, 0), (True, 1), (0, 0.0), ([1], [True]),
                                        ({"a": [2]}, {"a": [2.0]})])
def test_json_semantics_preserve_types(left, right):
    assert not qm._same(left, right)
    assert qm._same(qm._json(b'{"a":1,"b":false}'), qm._json(b'{"b":false, "a":1}'))


def test_fixed_public_metadata_cannot_be_replaced_by_fixture(miniature):
    root, _, _ = miniature
    with pytest.raises(qm.QwenModelError, match="file_size_mismatch"):
        qm.validate_model_files(root, model_id="MOCK_ONLY", revision="MOCK_ONLY",
                                config_path=root / "config.json")
    original = CONFIG.read_bytes()
    changed = original.replace(b'"is_run_authorization": false', b'"is_run_authorization":  true')
    assert len(changed) == len(original) and changed != original
    (root / "changed.json").write_bytes(changed)
    with pytest.raises(qm.QwenModelError, match="file_sha256_mismatch"):
        qm._config(root / "changed.json")
    assert qm.CONFIG_SHA256 == "b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145"


@pytest.mark.parametrize("model_id,revision", [("unbound", "x"), ("Qwen/Qwen3-0.6B", "main"),
                                              (False, "x"), ("Qwen/Qwen3-1.7B", True)])
def test_public_model_and_revision_are_fixed_before_directory_access(model_id, revision):
    with pytest.raises(qm.QwenModelError):
        qm.validate_model_files(Path("/MISSING_MOCK_ONLY"), model_id=model_id, revision=revision,
                                config_path=CONFIG)


def test_static_serialized_and_sanitized_counts_are_distinct():
    config = qm._config(CONFIG)
    for name, base_count, lora_count in [("Qwen/Qwen3-0.6B", 596049920, 1146880),
                                        ("Qwen/Qwen3-1.7B", 1720574976, 1605632)]:
        spec = config["models"][name]
        base, adapted = qm._frozen_spec(spec, lora=False), qm._frozen_spec(spec, lora=True)
        assert spec["serialized_tensor_count"] == 311 and len(base) == len(adapted) == 310
        assert "lm_head.weight" not in base and sum(qm.math.prod(v["shape"]) for v in base.values()) == base_count
        assert len(set(adapted) - set(base)) == 56
        adapters = qm._adapter_spec(spec)
        assert len(adapters) == 112 and sum(qm.math.prod(v["shape"]) for v in adapters.values()) == lora_count
        assert spec["generation_eos_ids"] == [151645, 151643]
        assert spec["training_eos_id"] == 151645 and spec["padding_id"] == 151643
        assert spec["generation_config_original"]["do_sample"] is True


def test_private_original_directory_is_structurally_valid(miniature):
    root, spec, _ = miniature
    files, token = qm._directory_files(root, spec)
    assert len(files) == 4 and files["model.safetensors"].sha256 == spec["files"]["model.safetensors"]["sha256"]
    qm._unchanged(root, files, token)


@pytest.mark.parametrize("change", ["missing", "extra", "payload", "size", "directory", "symlink", "parent_link", "index"])
def test_directory_file_boundaries(miniature, change):
    root, spec, _ = miniature
    path = root / "model.safetensors"
    if change == "missing":
        path.unlink()
    elif change == "extra":
        (root / "model-extra.safetensors").write_bytes(b"MOCK_ONLY")
    elif change == "payload":
        data = path.read_bytes()
        path.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
    elif change == "size":
        path.write_bytes(path.read_bytes() + b"x")
    elif change == "directory":
        path.unlink()
        path.mkdir()
    elif change == "symlink":
        target = root / "original.mock"
        path.rename(target)
        path.symlink_to(target)
    elif change == "parent_link":
        link = root.parent / "symlink"
        link.symlink_to(root, target_is_directory=True)
        root = link
    else:
        (root / "model.safetensors.index.json").write_text("{}")
    with pytest.raises(qm.QwenModelError):
        qm._directory_files(root, spec)


@pytest.mark.parametrize("value", ["relative", "../escape", "https://example.invalid/model"])
def test_explicit_local_paths_only(value):
    with pytest.raises(qm.QwenModelError):
        with qm._open(value):
            pytest.fail("unsafe path accepted")


@pytest.mark.parametrize("key,value", [("tie_word_embeddings", 1), ("layers", True), ("layers", 1.0),
                                       ("auto_map", {}), ("model_file", "custom.py"),
                                       ("quantization", {}), ("quantization_config", {}),
                                       ("architectures", ["OtherModel"]), ("model_type", "other")])
def test_private_model_config_comparison_rejects_types_and_overrides(miniature, key, value):
    root, spec, _ = miniature
    mutated = {**spec["model_config"], key: value}
    path = root / "config.json"
    path.write_text(json.dumps(mutated))
    # Rebind only this *private original fixture's* file digest, leaving the
    # expected semantic value unchanged. The public CONFIG_SHA256 is untouched.
    spec["files"][path.name] = info(path.read_bytes())
    with pytest.raises(qm.QwenModelError, match="model_config_mismatch"):
        qm._directory_files(root, spec)


@pytest.mark.parametrize("field,value", [("shape", [True]), ("shape", [2.0]), ("shape", [0]),
                                         ("shape", [-1]), ("data_offsets", [False, 4]),
                                         ("data_offsets", [0.0, 4]), ("data_offsets", [2, 6]),
                                         ("data_offsets", [0, 2]), ("dtype", "F16"), ("dtype", False)])
def test_original_safetensors_reject_bad_types_shapes_offsets_and_dtypes(tmp_path, field, value):
    path = tmp_path.resolve() / "original.safetensors"
    item = {"dtype": "BF16", "shape": [2], "data_offsets": [0, 4], field: value}
    original_safetensors(path, {"a": ("BF16", [2], b"\x00" * 4)},
                         header_bytes=json.dumps({"a": item}).encode())
    with pytest.raises(qm.QwenModelError):
        qm._header(path, qm._hash_file(path))


@pytest.mark.parametrize("header,tail", [(b'{"a":{"dtype":"BF16","shape":[1],"data_offsets":[0,2]},"a":{}}', b""),
                                        (b'{"__metadata__":{"number":0}}', b""),
                                        (b'{"a":{"dtype":"BF16","shape":[1],"data_offsets":[0,2],"extra":0}}', b""),
                                        (b'[]', b""), (b'{}', b"extra")])
def test_original_safetensors_reject_duplicates_fields_and_trailing_payload(tmp_path, header, tail):
    path = tmp_path.resolve() / "original.safetensors"
    original_safetensors(path, {}, header_bytes=header, extra_payload=tail)
    with pytest.raises(qm.QwenModelError):
        qm._header(path, qm._hash_file(path))


@pytest.mark.parametrize("prefix", [b"x", struct.pack("<Q", 2**63), struct.pack("<Q", 9) + b" " * 9])
def test_header_length_bounds_before_allocation(tmp_path, prefix):
    path = tmp_path.resolve() / "original.safetensors"
    path.write_bytes(prefix)
    with pytest.raises(qm.QwenModelError):
        qm._header(path, qm._hash_file(path))


def test_shards_mapping_and_no_duplicate_keys(miniature):
    root, spec, members = miniature
    (root / "model.safetensors").unlink()
    spec["files"].pop("model.safetensors")
    spec["headers"], spec["serialized_tensors"] = {}, {}
    mapping = {}
    for i, names in enumerate([["lm_head.weight"], list(members)[1:]], 1):
        path = root / f"model-{i:05}-of-00002.safetensors"
        tensors, header = original_safetensors(path, {n: members[n] for n in names})
        spec["files"][path.name] = info(path.read_bytes())
        spec["headers"][path.name] = header
        spec["serialized_tensors"].update(tensors)
        mapping.update({n: path.name for n in names})
    index = root / "model.safetensors.index.json"
    index.write_text(json.dumps({"metadata": {"total_size": 24}, "weight_map": mapping}))
    spec["files"][index.name] = info(index.read_bytes())
    qm._directory_files(root, spec)
    index.write_text(index.read_text().replace("00001", "00009"))
    spec["files"][index.name] = info(index.read_bytes())
    with pytest.raises(qm.QwenModelError, match="shard_index_mapping"):
        qm._directory_files(root, spec)
    # A second shard using the same name must fail before the index can hide it.
    path = root / "model-00002-of-00002.safetensors"
    _, header = original_safetensors(path, {"lm_head.weight": members["lm_head.weight"]})
    spec["files"][path.name], spec["headers"][path.name] = info(path.read_bytes()), header
    with pytest.raises(qm.QwenModelError, match="duplicate_shard_tensor"):
        qm._directory_files(root, spec)


@pytest.mark.parametrize("size,mapping", [(True, {"a": "one"}), (2.0, {"a": "one"}),
                                         (2, {"a": "../one"}), (2, {"b": "one"}),
                                         (2, {"a": "one", "b": "one"})])
def test_shard_index_is_typed_and_exact(size, mapping):
    with pytest.raises(qm.QwenModelError):
        qm._check_index({"metadata": {"total_size": size}, "weight_map": mapping},
                         {"a": ("one", qm._Tensor("BF16", (1,), (0, 2)))})


@pytest.fixture
def cpu_repository(tmp_path):
    """A small temporary Git repository; only the existing P00 lease implementation."""
    root = tmp_path.resolve() / "MOCK_ONLY_git"
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    return root


def cpu_lease(root):
    return GPULease(task_id="MOCK_ONLY_CPU_LEASE", worker_alias="E1", run_id="fixture",
                    expected_job="CPU OS-lock boundary", memory_strategy="no model", repository=root)


def test_real_cpu_flock_current_origin_competition_and_release(cpu_repository):
    lease = cpu_lease(cpu_repository)
    with pytest.raises(qm.QwenModelError):
        qm.require_current_lease(lease, cpu_repository)
    with lease:
        owner = qm.require_current_lease(lease, cpu_repository)
        assert owner["pid"] == os.getpid()
        nested = cpu_repository / "subdirectory"
        nested.mkdir()
        assert qm.require_current_lease(lease, nested) == owner
        with pytest.raises(LockBusy):
            with cpu_lease(cpu_repository):
                pytest.fail("second descriptor acquired same physical lock")
        code = """import sys
from toolalign.runtime.gpu_lock import inspect_gpu_lock
assert inspect_gpu_lock(sys.argv[1])['held'] is True
"""
        result = subprocess.run([sys.executable, "-B", "-c", code, str(cpu_repository)],
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
        assert not lease._handle.closed and inspect_gpu_lock(cpu_repository)["held"] is True
    with pytest.raises(qm.QwenModelError):
        qm.require_current_lease(lease, cpu_repository)
    assert inspect_gpu_lock(cpu_repository)["held"] is False


def test_other_descriptor_cannot_borrow_current_pid_metadata(cpu_repository):
    with cpu_lease(cpu_repository) as owner:
        impostor = cpu_lease(cpu_repository)
        with lock_path(cpu_repository).open("r+") as unrelated:
            impostor._handle = unrelated
            with pytest.raises(qm.QwenModelError, match="lease_descriptor_not_owner"):
                qm.require_current_lease(impostor, cpu_repository)
        assert qm.require_current_lease(owner, cpu_repository)["pid"] == os.getpid()


@pytest.mark.parametrize("field,value", [("pid", True), ("pid", 1.0), ("pid", -123),
                                         ("host_fingerprint", "other-host"),
                                         ("process_started_at", "reused-pid"), ("run_id", "other-run")])
def test_physical_lease_metadata_identity_is_not_just_a_nonempty_handle(cpu_repository, field, value):
    with cpu_lease(cpu_repository) as lease:
        handle = lease._handle
        handle.seek(0)
        owner = json.load(handle)
        owner[field] = value
        handle.seek(0)
        handle.truncate()
        json.dump(owner, handle)
        handle.flush()
        with pytest.raises(qm.QwenModelError):
            qm.require_current_lease(lease, cpu_repository)
        assert not handle.closed


def test_different_git_common_directory_lease_is_rejected(cpu_repository, tmp_path):
    other = tmp_path.resolve() / "other"
    subprocess.run(["git", "init", "-q", str(other)], check=True, capture_output=True)
    with cpu_lease(cpu_repository) as lease, pytest.raises(qm.QwenModelError, match="repository_mismatch"):
        qm.require_current_lease(lease, other)


def test_no_framework_import_precedes_lease_failure(monkeypatch):
    imported = []
    monkeypatch.setattr(qm.importlib, "import_module", lambda name: imported.append(name))
    with pytest.raises(qm.QwenModelError, match="lease_required"):
        qm.load_qwen_model("/MOCK_ONLY", model_id="Qwen/Qwen3-0.6B", revision="main",
                           config_path=CONFIG, lease=object(), repository=REPO)
    assert imported == []


def test_valid_cpu_lease_bad_metadata_still_imports_no_framework(cpu_repository, miniature, monkeypatch):
    imported = []
    monkeypatch.setattr(qm.importlib, "import_module", lambda name: imported.append(name))
    with cpu_lease(cpu_repository) as lease:
        with pytest.raises(qm.QwenModelError, match="file_size_mismatch"):
            qm.load_qwen_model(miniature[0], model_id="Qwen/Qwen3-0.6B", revision="main",
                               config_path=miniature[0] / "config.json", lease=lease, repository=cpu_repository)
        assert qm.require_current_lease(lease, cpu_repository)
    assert imported == []


def test_pathfinder_detects_shadow_without_importing_python(tmp_path, monkeypatch):
    site, shadow = tmp_path.resolve() / "site", tmp_path.resolve() / "shadow"
    for folder in (site, shadow):
        (folder / "mlx_lm").mkdir(parents=True)
        (folder / "mlx_lm/__init__.py").write_text("raise RuntimeError('MUST_NOT_IMPORT')\n")
        (folder / "mlx_lm/utils.py").write_text("raise RuntimeError('MUST_NOT_IMPORT')\n")
    monkeypatch.setattr(sys, "path", [str(site)])
    spec = qm._module_spec("mlx_lm.utils", site)
    assert spec.origin == str(site / "mlx_lm/utils.py")
    monkeypatch.setattr(sys, "path", [str(shadow), str(site)])
    with pytest.raises(qm.QwenModelError, match="shadow_runtime_origin"):
        qm._module_spec("mlx_lm.utils", site)


def test_preloaded_shadow_and_custom_import_hook_are_rejected(tmp_path, monkeypatch):
    site = tmp_path.resolve() / "site"
    site.mkdir()
    module = types.ModuleType("mlx_lm.MOCK_ONLY")
    module.__file__ = str(tmp_path / "shadow.py")
    monkeypatch.setitem(sys.modules, module.__name__, module)
    with pytest.raises(qm.QwenModelError, match="shadow_loaded_module"):
        qm._loaded_origins(site, {})
    monkeypatch.setattr(sys, "meta_path", [object()])
    with pytest.raises(qm.QwenModelError, match="unsupported_import_hook"):
        qm._import_hooks()


def standard_importers(monkeypatch):
    monkeypatch.setattr(sys, "meta_path", [importlib.machinery.BuiltinImporter,
                                         importlib.machinery.FrozenImporter, importlib.machinery.PathFinder])


@pytest.mark.parametrize("change", ["version", "hash", "name", "duplicate_version", "source"])
def test_original_runtime_metadata_rejects_mismatches_before_any_import(tmp_path, monkeypatch, change):
    site = tmp_path.resolve() / "site"
    directory = site / "mock_only-1.dist-info"
    directory.mkdir(parents=True)
    data = b"Name: mock-only\nVersion: 1\n\nMOCK_ONLY metadata\n"
    (directory / "METADATA").write_bytes(data)
    source = site / "original.py"
    source.write_text("# MOCK_ONLY source; never imported\n")
    config = {"existing_environment_metadata": {"mock-only": {"version": "1", "metadata_sha256": info(data)["sha256"]}},
              "source_files": {"original.py": info(source.read_bytes())}}
    if change == "version":
        directory.rename(site / "mock_only-2.dist-info")
    elif change == "duplicate_version":
        (site / "mock_only-2.dist-info").mkdir()
    elif change == "hash":
        (directory / "METADATA").write_bytes(data + b"changed")
    elif change == "name":
        data = data.replace(b"mock-only", b"different")
        (directory / "METADATA").write_bytes(data)
        config["existing_environment_metadata"]["mock-only"]["metadata_sha256"] = info(data)["sha256"]
    else:
        source.write_text("# changed MOCK_ONLY source\n")
    standard_importers(monkeypatch)
    monkeypatch.setattr(qm.sysconfig, "get_path", lambda _: str(site))
    expected_error = "file_size_mismatch" if change == "source" else "runtime_"
    with pytest.raises(qm.QwenModelError, match=expected_error):
        qm._environment(config)


def test_original_runtime_sources_detect_change_after_preflight(tmp_path, monkeypatch):
    site = tmp_path.resolve()
    path = site / "source.py"
    path.write_bytes(b"# MOCK_ONLY source\n")
    identities = {str(path): qm._hash_file(path)}
    standard_importers(monkeypatch)
    qm._check_runtime_environment((site, identities, {}), {})
    path.write_bytes(b"# MUTATED ORIGINAL\n")
    with pytest.raises(qm.QwenModelError, match="runtime_source_changed"):
        qm._check_runtime_environment((site, identities, {}), {})


def test_import_namespace_resolution_is_local_and_does_not_run_code(tmp_path, monkeypatch):
    site = tmp_path.resolve()
    (site / "mlx").mkdir()
    monkeypatch.setattr(sys, "path", [str(site)])
    spec = qm._module_spec("mlx", site)
    assert spec.origin is None and list(spec.submodule_search_locations) == [str(site / "mlx")]


def test_python_source_cannot_impersonate_mlx_core_extension(tmp_path, monkeypatch):
    site = tmp_path.resolve()
    (site / "mlx").mkdir()
    (site / "mlx/core.py").write_text("raise RuntimeError('MUST_NOT_IMPORT')\n")
    monkeypatch.setattr(sys, "path", [str(site)])
    with pytest.raises(qm.QwenModelError, match="mlx_core_extension_required"):
        qm._module_spec("mlx.core", site)


def test_file_replacement_is_rejected_between_hash_and_header(miniature):
    root, _, _ = miniature
    path = root / "model.safetensors"
    identity = qm._hash_file(path)
    data = path.read_bytes()
    path.unlink()
    path.write_bytes(data)
    with pytest.raises(qm.QwenModelError, match="file_changed"):
        qm._header(path, identity)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="fork is an additional POSIX descriptor-origin check")
def test_inherited_fork_descriptor_does_not_authorize_child(cpu_repository):
    with cpu_lease(cpu_repository) as lease:
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            try:
                qm.require_current_lease(lease, cpu_repository)
                message = b"INVALID_PASS"
            except qm.QwenModelError as error:
                message = str(error).encode()
            os.write(write_fd, message)
            os.close(write_fd)
            os._exit(0)
        os.close(write_fd)
        try:
            message = os.read(read_fd, 256)
        finally:
            os.close(read_fd)
            completed, status = os.waitpid(pid, 0)
        assert completed == pid and status == 0 and message == b"lease_pid_mismatch"
        assert qm.require_current_lease(lease, cpu_repository)["pid"] == os.getpid()


class MockArray:
    """MOCK_ONLY original bytes; intentionally has no numeric conversion method."""

    def __init__(self, data, dtype, shape):
        self.data, self.dtype, self.shape = data, dtype, tuple(shape)
        self.size = qm.math.prod(self.shape)

    def reshape(self, size):
        assert size == -1
        return MockArray(self.data, self.dtype, (self.size,))

    def __getitem__(self, selection):
        start, stop, step = selection.indices(self.size)
        assert step == 1
        width = {"bfloat16": 2, "float32": 4, "uint8": 1}[self.dtype]
        return MockArray(self.data[start * width:stop * width], self.dtype, (stop - start,))


class MockHost:
    dtype = "uint8"
    flags = types.SimpleNamespace(c_contiguous=True)

    def __init__(self, data):
        self.data = data

    def tobytes(self, *, order):
        assert order == "C"
        return self.data


class MockDropout(dict):
    def __init__(self, p):
        self.probability = p
        self._training, self._no_grad = True, set()


class MockLinear:
    def __init__(self, weight):
        self.weight = weight


class MockLoRA:
    def __init__(self, weight, a, b):
        self.linear, self.lora_a, self.lora_b = MockLinear(weight), a, b
        self.scale, self.dropout = 2.0, MockDropout(0.0)


class MockModel:
    def __init__(self, spec, members):
        self.spec = spec
        self.arrays = {name: MockArray(data, "bfloat16", shape)
                       for name, (_, shape, data) in members.items() if name != "lm_head.weight"}
        self.trainable = set(self.arrays)
        self.training, self.layers, self.events = False, {}, []
        self.Args = make_dataclass("MOCK_ONLY_Args", list(spec["model_config"]))
        self.args = self.Args(**spec["model_config"])
        self.model_type = spec["model_config"]["model_type"]
        self.corrupt_after_update = False

    def parameters(self):
        return dict(self.arrays)

    def trainable_parameters(self):
        return {name: self.arrays[name] for name in self.trainable}

    def named_modules(self):
        return list(self.layers.items())

    def freeze(self):
        self.events.append("freeze")
        self.trainable = set()

    def train(self, mode):
        self.training = mode
        for layer in self.layers.values():
            layer.dropout._training = mode

    def install(self):
        assert not self.trainable, "base must be frozen before MOCK_ONLY conversion"
        for name, shape in qm._adapter_spec(self.spec).items():
            value = 0.0 if name.endswith(".lora_b") else 0.25
            data = struct.pack("<f", value) * qm.math.prod(shape["shape"])
            self.arrays[name] = MockArray(data, "float32", shape["shape"])
        for raw, mapped in self.spec["expected_raw_to_lora_frozen_key_mapping"].items():
            if raw == mapped:
                continue
            array = self.arrays.pop(raw)
            self.arrays[mapped] = array
            name = raw.removesuffix(".weight")
            self.layers[name] = MockLoRA(array, self.arrays[name + ".lora_a"], self.arrays[name + ".lora_b"])
        self.trainable = set(qm._adapter_spec(self.spec))
        self.events.append("install")

    def update(self, values, *, strict):
        assert strict is True and set(values) <= set(self.arrays)
        self.events.append("update")
        self.arrays.update(values)
        for name, layer in self.layers.items():
            layer.lora_a, layer.lora_b = self.arrays[name + ".lora_a"], self.arrays[name + ".lora_b"]
        if self.corrupt_after_update:
            self.arrays["model.embed_tokens.weight"].data = b"\x01" * 8


def mock_modules(model):
    mx = types.SimpleNamespace(array=MockArray, bfloat16="bfloat16", float32="float32", uint8="uint8",
                               contiguous=lambda x: x, view=lambda x, _: MockArray(x.data, "uint8", (len(x.data),)),
                               eval=lambda _: None, gpu="MOCK_ONLY_GPU", default_device=lambda: "MOCK_ONLY_GPU")
    numpy = types.SimpleNamespace(asarray=lambda x, **_: MockHost(x.data), dtype=lambda x: x)
    utility = types.SimpleNamespace(tree_flatten=lambda x: list(x.items()), tree_unflatten=lambda x: dict(x))

    def convert(actual, layers, config, *, use_dora):
        assert actual is model and layers == 28 and use_dora is False
        assert qm._same(config, {"rank": 8, "scale": 2.0, "dropout": 0.0,
                                 "keys": ["self_attn.q_proj", "self_attn.v_proj"]})
        model.install()

    modules = {name: types.SimpleNamespace() for name in qm._RUNTIME_MODULES}
    modules.update({"mlx.core": mx, "numpy": numpy, "mlx.utils": utility,
                    "mlx.nn": types.SimpleNamespace(Dropout=MockDropout, Linear=MockLinear),
                    "mlx_lm.tuner.lora": types.SimpleNamespace(LoRALinear=MockLoRA),
                    "mlx_lm.tuner.utils": types.SimpleNamespace(linear_to_lora_layers=convert),
                    "mlx_lm.models.qwen3": types.SimpleNamespace(Model=MockModel, ModelArgs=model.Args)})
    for name, module in modules.items():
        module.__spec__ = types.SimpleNamespace(origin="/MOCK_ONLY_NOT_IMPORTED/" + name)
    return modules


def mock_resident(monkeypatch, miniature):
    """MOCK_ONLY runtime body tests; lease and origins have separate real CPU boundary tests."""
    root, spec, members = miniature
    model = MockModel(spec, members)
    model.freeze()
    modules = mock_modules(model)
    monkeypatch.setattr(qm, "require_current_lease", lambda *_: {"status": "MOCK_ONLY"})
    monkeypatch.setattr(qm, "_check_runtime_environment", lambda *_: None)
    monkeypatch.setattr(qm, "_unchanged", lambda *_: None)
    monkeypatch.setattr(qm, "_function_origin", lambda *_: None)
    files = qm.ModelFiles("MOCK_ONLY", "MOCK_ONLY", root, (), 3, 12, 2, 8, (4, 3), 4, 3, b"{}")
    lease = types.SimpleNamespace(_handle="MOCK_ONLY_CALLER_OWNED")
    resident = qm.QwenModel(qm._CREATE, model=model, spec=spec, files=files, directory_token=(),
                            lease=lease, repository=root, environment=(root, {}, {}), modules=modules)
    return resident, model, modules, lease


def test_mock_only_bf16_hash_reads_original_bits_and_bounds_host_copies():
    model = types.SimpleNamespace(Args=object)
    modules = mock_modules(model)
    bits = bytes.fromhex("00008080013f807f817f00ff") * 100000
    array = MockArray(bits, "bfloat16", (len(bits) // 2,))
    chunks = list(qm._raw_chunks(array, "BF16", modules["mlx.core"], modules["numpy"]))
    assert b"".join(chunks) == bits and len(chunks) == 2 and max(map(len, chunks)) <= 1024 * 1024
    expected = {"dtype": "BF16", "shape": [len(bits) // 2], "raw_tensor_sha256": hashlib.sha256(bits).hexdigest()}
    assert qm._leaf(array, expected, modules["mlx.core"], modules["numpy"])["bytes"] == len(bits)


def test_mock_only_sanitize_freeze_lora_identity_and_current_content(miniature, monkeypatch):
    resident, model, _, lease = mock_resident(monkeypatch, miniature)
    initial = resident.parameter_identity()
    assert initial["actual_base_leaf_count"] == 2 and initial["actual_adapter_leaf_count"] == 0
    assert initial["state"] == "BASE_READY" and model.training is False
    attached = resident.attach_lora()
    assert resident.state == "LORA_READY" and attached["actual_adapter_leaf_count"] == 2
    assert attached["actual_total_leaf_count"] == 4 and attached["actual_adapter_parameter_count"] == 32
    assert model.events[:3] == ["freeze", "freeze", "install"] and model.training is False
    baseline = resident.parameter_identity()
    name = next(n for n in model.trainable if n.endswith(".lora_a"))
    model.arrays[name].data = struct.pack("<f", 0.5) * 16
    updated = resident.parameter_identity()
    assert updated["content_sha256"] != baseline["content_sha256"]
    assert updated["leaves"]["model.embed_tokens.weight"] == baseline["leaves"]["model.embed_tokens.weight"]
    assert resident.model is model and lease._handle == "MOCK_ONLY_CALLER_OWNED"
    with pytest.raises(AttributeError):
        resident.files = None


@pytest.mark.parametrize("change", ["missing", "extra", "shape", "dtype", "base_changed", "base_trainable",
                                     "not_trainable", "nonfinite", "scale", "dropout", "alias", "module_extra",
                                     "module_mismatch", "args_type", "args_value", "training_type"])
def test_mock_only_runtime_parameter_and_structure_rejections(miniature, monkeypatch, change):
    resident, model, _, lease = mock_resident(monkeypatch, miniature)
    resident.attach_lora()
    a = next(n for n in model.trainable if n.endswith(".lora_a"))
    b = a.replace(".lora_a", ".lora_b")
    layer = next(iter(model.layers.values()))
    if change == "missing":
        model.trainable.remove(a)
        model.arrays.pop(a)
    elif change == "extra":
        model.arrays["unexpected"] = MockArray(b"\x00" * 2, "bfloat16", [1])
    elif change == "shape":
        model.arrays[a].shape = (1, 16)
    elif change == "dtype":
        model.arrays[a].dtype = "bfloat16"
    elif change == "base_changed":
        model.arrays["model.embed_tokens.weight"].data = b"\x00" * 8
    elif change == "base_trainable":
        model.trainable.add("model.embed_tokens.weight")
    elif change == "not_trainable":
        model.trainable.remove(b)
    elif change == "nonfinite":
        model.arrays[a].data = struct.pack("<f", float("nan")) * 16
    elif change == "scale":
        layer.scale = 0.25
    elif change == "dropout":
        layer.dropout.probability = 0.1
    elif change == "alias":
        model.arrays[b] = model.arrays[a]
        layer.lora_b = model.arrays[a]
    elif change == "module_extra":
        model.layers["extra"] = layer
    elif change == "module_mismatch":
        layer.lora_b = copy.copy(layer.lora_b)
    elif change == "args_type":
        model.args.layers = True
    elif change == "args_value":
        model.args.model_type = "other"
    elif change == "training_type":
        model.training = 1
    with pytest.raises(qm.QwenModelError):
        resident.parameter_identity()
    assert resident.state == "FAILED" and resident.failure
    first = resident.failure
    with pytest.raises(qm.QwenModelError, match="runtime_failed_state"):
        resident.attach_lora()
    assert resident.failure == first and lease._handle == "MOCK_ONLY_CALLER_OWNED"


def test_mock_only_nonzero_initial_b_and_wrong_base_precision(miniature):
    _, spec, members = miniature
    model = MockModel(spec, members)
    model.freeze()
    modules = mock_modules(model)
    model.arrays["model.embed_tokens.weight"].dtype = "float32"
    with pytest.raises(qm.QwenModelError, match="runtime_tensor_dtype"):
        qm._parameters(model, spec, modules, lora=False)
    model.arrays["model.embed_tokens.weight"].dtype = "bfloat16"
    model.install()
    b = next(n for n in model.trainable if n.endswith(".lora_b"))
    model.arrays[b].data = struct.pack("<f", 1.0) * 16
    with pytest.raises(qm.QwenModelError, match="initial_lora_b_not_zero"):
        qm._parameters(model, spec, modules, lora=True, initial=True)


def adapter_original(root, spec, *, change=None):
    path = root / "MOCK_ONLY_adapter.safetensors"
    members = {name: ("F32", value["shape"], struct.pack("<f", 0.5) * qm.math.prod(value["shape"]))
               for name, value in qm._adapter_spec(spec).items()}
    name = next(iter(members))
    if change == "missing":
        members.pop(name)
    elif change == "extra":
        members["model.embed_tokens.weight"] = ("F32", [1], b"\x00" * 4)
    elif change == "dtype":
        members[name] = ("BF16", [2, 8], b"\x00" * 32)
    elif change == "shape":
        members[name] = ("F32", [4, 4], b"\x00" * 64)
    original_safetensors(path, members)
    return path, members


@pytest.mark.parametrize("change", ["missing", "extra", "dtype", "shape", "wrong_hash"])
def test_original_adapter_file_rejections_precede_tensor_loading(miniature, change):
    root, spec, _ = miniature
    path, _ = adapter_original(root, spec, change=change)
    digest = info(path.read_bytes())["sha256"] if change != "wrong_hash" else "0" * 64
    with pytest.raises(qm.QwenModelError):
        qm._adapter_file(path, digest, spec)


def test_mock_only_adapter_reload_checks_contents_then_only_updates_ab(miniature, monkeypatch):
    resident, model, modules, lease = mock_resident(monkeypatch, miniature)
    resident.attach_lora()
    root, spec, _ = miniature
    path, members = adapter_original(root, spec)
    loaded = {name: MockArray(data, "float32", shape) for name, (_, shape, data) in members.items()}
    calls = []

    def load(filename):
        calls.append(filename)
        return loaded

    modules["mlx.core"].load = load
    before = resident.parameter_identity()
    after = resident.reload_adapter(path, expected_sha256=info(path.read_bytes())["sha256"])
    assert calls == [str(path)] and model.events.count("update") == 1
    assert after["leaves"]["model.embed_tokens.weight"] == before["leaves"]["model.embed_tokens.weight"]
    assert resident.state == "LORA_READY" and lease._handle == "MOCK_ONLY_CALLER_OWNED"
    for name, array in loaded.items():
        assert model.arrays[name] is array and after["leaves"][name]["raw_tensor_sha256"] == info(array.data)["sha256"]


@pytest.mark.parametrize("change", ["loaded_content", "loaded_missing", "loaded_dtype", "updated_base"])
def test_mock_only_reload_rejects_wrong_loads_and_post_update_corruption(miniature, monkeypatch, change):
    resident, model, modules, lease = mock_resident(monkeypatch, miniature)
    resident.attach_lora()
    path, members = adapter_original(miniature[0], miniature[1])
    loaded = {name: MockArray(data, "float32", shape) for name, (_, shape, data) in members.items()}
    name = next(iter(loaded))
    if change == "loaded_content":
        loaded[name].data = b"\x00" * 64
    elif change == "loaded_missing":
        loaded.pop(name)
    elif change == "loaded_dtype":
        loaded[name].dtype = "bfloat16"
    else:
        model.corrupt_after_update = True
    modules["mlx.core"].load = lambda _: loaded
    with pytest.raises(qm.QwenModelError):
        resident.reload_adapter(path, expected_sha256=info(path.read_bytes())["sha256"])
    assert model.events.count("update") == (1 if change == "updated_base" else 0)
    assert resident.state == "FAILED" and lease._handle == "MOCK_ONLY_CALLER_OWNED"


def test_mock_only_conversion_exception_is_terminal_and_does_not_release_caller_lease(miniature, monkeypatch):
    resident, _, modules, lease = mock_resident(monkeypatch, miniature)

    def fail(*_, **__):
        raise RuntimeError("MOCK_ONLY conversion failure")

    modules["mlx_lm.tuner.utils"].linear_to_lora_layers = fail
    with pytest.raises(RuntimeError, match="MOCK_ONLY conversion failure"):
        resident.attach_lora()
    assert resident.state == "FAILED" and lease._handle == "MOCK_ONLY_CALLER_OWNED"


def test_mock_only_loader_orchestration_uses_fixed_arguments_and_real_metadata(monkeypatch, tmp_path):
    """File/lease/environment/parameter work is mocked; this is NOT a model validation."""
    spec = qm._config(CONFIG)["models"]["Qwen/Qwen3-0.6B"]
    model = MockModel(spec, {})
    modules = mock_modules(model)
    events = []
    root = tmp_path.resolve()
    monkeypatch.setattr(qm, "require_current_lease", lambda *_: events.append("lease") or {"MOCK_ONLY": True})
    monkeypatch.setattr(qm, "_directory_files", lambda *_: events.append("files") or ({}, ()))
    monkeypatch.setattr(qm, "_environment", lambda *_: events.append("environment") or (root, {}, {}))
    monkeypatch.setattr(qm, "_check_runtime_environment", lambda *_: events.append("origins"))
    monkeypatch.setattr(qm, "_unchanged", lambda *_: events.append("unchanged"))
    monkeypatch.setattr(qm, "_function_origin", lambda *_: events.append("function_origin"))
    monkeypatch.setattr(qm, "_parameters", lambda *_, **__: events.append("parameters") or {"MOCK_ONLY": True})

    def import_module(name):
        events.append("mock_import:" + name)
        return modules[name]

    monkeypatch.setattr(qm.importlib, "import_module", import_module)

    def load(path, *, lazy, strict):
        assert path == root and lazy is False and strict is True
        events.append("mock_load")
        return model, {**spec["model_config"], "eos_token_id": [151645, 151643]}

    modules["mlx_lm.utils"].load_model = load
    result = qm.load_qwen_model(root, model_id=spec["model_id"], revision=spec["revision"],
                                config_path=CONFIG, lease=object(), repository=root)
    assert result.state == "BASE_READY" and model.events == ["freeze"]
    first_import = next(i for i, event in enumerate(events) if event.startswith("mock_import:"))
    assert events.index("lease") < events.index("files") < events.index("environment") < first_import
    assert events.index("mock_load") > first_import and events[-1] == "unchanged"
    assert not any(name == "mlx" or name.startswith("mlx.") for name in sys.modules)
