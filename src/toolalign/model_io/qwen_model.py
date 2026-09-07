"""Fixed local Qwen files and leased runtime parameter identity.

``validate_model_files`` uses only file bytes and JSON headers. It neither
imports a model framework nor constructs a tokenizer. The separate runtime
entry requires an already held, current-process gpu0 lease. A metadata file is
not execution authorization; the caller needs a separately authorized S0 run.

Runtime methods never acquire/release the caller's lease, run a forward pass,
write checkpoints, or choose an adapter. Keep the original lease until *all*
references to the returned model have been discarded, including on failure.
"""

from __future__ import annotations

import fcntl
import hashlib
import importlib
import importlib.machinery
import io
import json
import math
import os
import re
import socket
import stat
import struct
import subprocess
import sys
import sysconfig
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from email.parser import BytesParser
from pathlib import Path

from toolalign.runtime.gpu_lock import GPULease, inspect_gpu_lock, lock_path

CONFIG_SHA256 = "b8a5e48bc2b93064c511ba796dabf55024f65df97fe0db39c43366b7bc877145"
CONFIG_BYTES = 372437
_HEADER_LIMIT = 1024 * 1024
_CHUNK_BYTES = 1024 * 1024
_DTYPE_BYTES = {"BF16": 2, "F32": 4}
_CREATE = object()


class QwenModelError(ValueError):
    """A fixed-input, physical-lease, import-origin or parameter check failed."""


def _require(condition, code):
    if not condition:
        raise QwenModelError(code)


def _same(left, right):
    """JSON equality that preserves bool/int/float distinctions at every depth."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if type(left) in (list, tuple):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def floating(value):
        result = float(value)
        _require(math.isfinite(result), "nonfinite_json_number")
        return result

    def constant(_):
        raise QwenModelError("nonfinite_json_number")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_float=floating,
                          parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise QwenModelError("invalid_json") from exc


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _absolute(path):
    _require(isinstance(path, (str, Path)), "explicit_local_path_required")
    path = Path(path)
    _require(path.is_absolute() and ".." not in path.parts and "://" not in str(path),
             "explicit_local_path_required")
    return path


@contextmanager
def _open(path, *, directory=False):
    """Walk every component with O_NOFOLLOW, including the parent directories."""
    path = _absolute(path)
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, component in enumerate(path.parts[1:]):
            is_directory = directory or index < len(path.parts) - 2
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if is_directory:
                flags |= os.O_DIRECTORY
            new_descriptor = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = new_descriptor
        info = os.fstat(descriptor)
        _require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
                 "regular_local_file_or_directory_required")
        yield descriptor
    except OSError as exc:
        raise QwenModelError("unsafe_or_missing_local_path") from exc
    finally:
        os.close(descriptor)


def _token(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@dataclass(frozen=True)
class FileIdentity:
    name: str
    bytes: int
    sha256: str
    stat_token: tuple[int, ...]


def _hash_file(path, *, expected=None, limit=None):
    with _open(path) as descriptor:
        before = os.fstat(descriptor)
        if expected is not None:
            _require(before.st_size == expected["bytes"], "file_size_mismatch")
        if limit is not None:
            _require(before.st_size <= limit, "file_size_limit")
        hasher, total = hashlib.sha256(), 0
        while chunk := os.read(descriptor, _CHUNK_BYTES):
            total += len(chunk)
            _require(total <= before.st_size, "file_changed_during_read")
            hasher.update(chunk)
        _require(total == before.st_size and _token(before) == _token(os.fstat(descriptor)),
                 "file_changed_during_read")
    digest = hasher.hexdigest()
    if expected is not None:
        _require(digest == expected["sha256"], "file_sha256_mismatch")
    return FileIdentity(Path(path).name, before.st_size, digest, _token(before))


def _read_bytes(path, identity):
    with _open(path) as descriptor:
        _require(_token(os.fstat(descriptor)) == identity.stat_token, "file_changed")
        with io.FileIO(descriptor, "rb", closefd=False) as stream:
            raw = stream.read()
        _require(_token(os.fstat(descriptor)) == identity.stat_token, "file_changed")
    _require(len(raw) == identity.bytes and hashlib.sha256(raw).hexdigest() == identity.sha256,
             "file_changed")
    return raw


def _config(config_path):
    expected = {"bytes": CONFIG_BYTES, "sha256": CONFIG_SHA256}
    identity = _hash_file(config_path, expected=expected)
    return _json(_read_bytes(config_path, identity))


def _model_spec(config, model_id, revision):
    _require(type(model_id) is str and model_id in config["models"], "unsupported_model")
    spec = config["models"][model_id]
    _require(type(revision) is str and revision == spec["revision"], "model_revision_mismatch")
    return spec


@dataclass(frozen=True)
class _Tensor:
    dtype: str
    shape: tuple[int, ...]
    offsets: tuple[int, int]

    @property
    def elements(self):
        return math.prod(self.shape)

    @property
    def bytes(self):
        return self.offsets[1] - self.offsets[0]


def _header(path, identity):
    with _open(path) as descriptor:
        _require(_token(os.fstat(descriptor)) == identity.stat_token, "file_changed")
        prefix = os.read(descriptor, 8)
        _require(len(prefix) == 8, "truncated_safetensors_prefix")
        length = int.from_bytes(prefix, "little")
        _require(2 <= length <= min(_HEADER_LIMIT, identity.bytes - 8) and length % 8 == 0,
                 "safetensors_header_size")
        with io.FileIO(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(length)
        _require(len(raw) == length, "truncated_safetensors_header")
        _require(_token(os.fstat(descriptor)) == identity.stat_token, "file_changed")
    value = _json(raw)
    _require(type(value) is dict, "safetensors_header_object")
    metadata = value.pop("__metadata__", {})
    _require(type(metadata) is dict and all(type(k) is str and type(v) is str
                                           for k, v in metadata.items()), "safetensors_metadata")
    tensors = {}
    for name, item in value.items():
        _require(name and type(item) is dict and set(item) == {"dtype", "shape", "data_offsets"},
                 "safetensors_tensor_fields")
        dtype, shape, offsets = item["dtype"], item["shape"], item["data_offsets"]
        _require(type(dtype) is str and dtype in _DTYPE_BYTES, "safetensors_dtype")
        _require(type(shape) is list and len(shape) <= 8
                 and all(type(n) is int and n > 0 for n in shape), "safetensors_shape")
        _require(type(offsets) is list and len(offsets) == 2
                 and all(type(n) is int and n >= 0 for n in offsets), "safetensors_offsets")
        tensor = _Tensor(dtype, tuple(shape), tuple(offsets))
        _require(tensor.bytes == tensor.elements * _DTYPE_BYTES[dtype], "safetensors_tensor_size")
        tensors[name] = tensor
    end = 0
    for tensor in sorted(tensors.values(), key=lambda t: t.offsets):
        _require(tensor.offsets[0] == end, "safetensors_gap_or_overlap")
        end = tensor.offsets[1]
    _require(end == identity.bytes - 8 - length, "safetensors_payload_size")
    return tensors, {"header_bytes": length, "header_sha256": hashlib.sha256(raw).hexdigest(),
                     "metadata": metadata, "tensor_count": len(tensors),
                     "tensor_payload_bytes": end}


def _check_index(index, tensors):
    _require(type(index) is dict and set(index) == {"metadata", "weight_map"}, "shard_index_fields")
    _require(type(index["metadata"]) is dict and set(index["metadata"]) == {"total_size"},
             "shard_index_metadata")
    size = index["metadata"]["total_size"]
    _require(type(size) is int and size == sum(t.bytes for _, t in tensors.values()),
             "shard_index_size")
    expected = {name: filename for name, (filename, _) in tensors.items()}
    _require(_same(index["weight_map"], expected), "shard_index_mapping")


def _directory_files(root, spec):
    with _open(root, directory=True) as descriptor:
        directory_token = _token(os.fstat(descriptor))
        names = set(os.listdir(descriptor))
    expected_weights = {name for name in spec["files"] if name.endswith(".safetensors")}
    actual_weights = {name for name in names if name.startswith("model")
                      and name.endswith(".safetensors")}
    _require(actual_weights == expected_weights, "model_weight_file_set")
    _require({n for n in names if n.startswith("model") and n.endswith(".index.json")}
             == {n for n in spec["files"] if n.endswith(".index.json")}, "model_index_file_set")
    files = {name: _hash_file(root / name, expected=item) for name, item in spec["files"].items()}
    # All declared hashes precede JSON interpretation, including tokenizer metadata.
    objects = {name: _json(_read_bytes(root / name, identity))
               for name, identity in files.items() if name.endswith(".json")}
    _require(_same(objects["config.json"], spec["model_config"]), "model_config_mismatch")
    _require(_same(objects["generation_config.json"], spec["generation_config_original"]),
             "generation_config_mismatch")
    tensors = {}
    for name in sorted(expected_weights):
        members, header = _header(root / name, files[name])
        _require(_same(header, spec["headers"][name]), "model_header_mismatch")
        for key, tensor in members.items():
            _require(key not in tensors, "duplicate_shard_tensor")
            tensors[key] = (name, tensor)
    _require(set(tensors) == set(spec["serialized_tensors"]), "serialized_tensor_keys")
    for key, (name, tensor) in tensors.items():
        expected = spec["serialized_tensors"][key]
        _require(name == expected["file"] and tensor.dtype == expected["dtype"]
                 and tensor.shape == tuple(expected["shape"])
                 and tensor.offsets == tuple(expected["data_offsets"])
                 and tensor.bytes == expected["bytes"], "serialized_tensor_identity")
    _require(len(tensors) == spec["serialized_tensor_count"]
             and sum(t.elements for _, t in tensors.values()) == spec["serialized_parameter_count"],
             "serialized_tensor_count")
    if "model.safetensors.index.json" in objects:
        _check_index(objects["model.safetensors.index.json"], tensors)
    _unchanged(root, files, directory_token)
    return files, directory_token


def _unchanged(root, files, directory_token):
    with _open(root, directory=True) as descriptor:
        _require(_token(os.fstat(descriptor)) == directory_token, "model_directory_changed")
    for name, identity in files.items():
        with _open(root / name) as descriptor:
            _require(_token(os.fstat(descriptor)) == identity.stat_token, "file_changed")


@dataclass(frozen=True)
class ModelFiles:
    """Static file evidence. Expected runtime counts are explicitly *not* measurements."""

    model_id: str
    revision: str
    root: Path
    files: tuple[FileIdentity, ...]
    serialized_tensor_count: int
    serialized_parameter_count: int
    expected_base_leaf_count: int
    expected_base_parameter_count: int
    generation_eos_ids: tuple[int, ...]
    training_eos_id: int
    padding_id: int
    generation_config_json: bytes
    metadata_sha256: str = CONFIG_SHA256
    runtime_status: str = "NOT_RUN"


def _files_result(root, spec, files):
    return ModelFiles(spec["model_id"], spec["revision"], root, tuple(files.values()),
                      spec["serialized_tensor_count"], spec["serialized_parameter_count"],
                      spec["expected_frozen_leaf_tensors"], spec["expected_frozen_parameter_count"],
                      tuple(spec["generation_eos_ids"]), spec["training_eos_id"], spec["padding_id"],
                      _canonical(spec["generation_config_original"]))


def validate_model_files(model_root, *, model_id, revision, config_path):
    """Verify fixed metadata, all local files and headers, with zero tensor decoding."""
    config = _config(config_path)
    spec = _model_spec(config, model_id, revision)
    root = _absolute(model_root)
    files, _ = _directory_files(root, spec)
    return _files_result(root, spec, files)


def require_current_lease(lease, repository):
    """Check the caller's existing descriptor against the common-dir physical flock.

    ``repository`` is the trusted caller's ToolAlign checkout, not the model root
    or an independently created lock directory. Never release this lease here.
    """
    _require(type(lease) is GPULease and lease._handle is not None
             and not lease._handle.closed, "active_current_gpu0_lease_required")
    path = lock_path(_absolute(repository))
    _require(lock_path(lease.repository) == path, "lease_repository_mismatch")
    with _open(path) as descriptor:
        actual, expected = os.fstat(lease._handle.fileno()), os.fstat(descriptor)
        _require((actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino),
                 "lease_descriptor_mismatch")
    observation = inspect_gpu_lock(repository)
    owner = observation.get("owner")
    _require(observation.get("held") is True and type(owner) is dict,
             "active_current_gpu0_lease_required")
    _require(type(owner.get("pid")) is int and owner["pid"] == os.getpid(), "lease_pid_mismatch")
    started = subprocess.check_output(["ps", "-p", str(os.getpid()), "-o", "lstart="],
                                      text=True).strip()
    _require(owner.get("process_started_at") == started
             and owner.get("host_fingerprint") == hashlib.sha256(socket.gethostname().encode()).hexdigest(),
             "lease_process_or_host_mismatch")
    fields = {"task_id", "worker_alias", "run_id", "expected_job", "memory_strategy"}
    _require(type(lease.metadata) is dict and set(lease.metadata) == fields
             and all(type(v) is str and v for v in lease.metadata.values())
             and all(_same(owner.get(k), v) for k, v in lease.metadata.items()), "lease_owner_mismatch")
    try:
        acquired = datetime.fromisoformat(owner["acquired_at"])
        _require(acquired.tzinfo is not None, "lease_acquisition_time")
        # A busy probe alone could observe some *other* descriptor's lease.
        # Reaffirming this descriptor must also succeed; this never unlocks it.
        fcntl.flock(lease._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise QwenModelError("lease_descriptor_not_owner") from exc
    return dict(owner)


_PACKAGES = ("mlx", "mlx_lm", "numpy", "psutil", "safetensors", "tokenizers",
             "transformers", "jinja2")
_RUNTIME_MODULES = ("mlx.core", "mlx.nn", "mlx.nn.layers.base", "mlx.nn.layers.linear",
                    "mlx.utils", "mlx_lm.utils", "mlx_lm.models.qwen3",
                    "mlx_lm.tuner.lora", "mlx_lm.tuner.utils", "numpy")


def _import_hooks():
    standard = (importlib.machinery.BuiltinImporter, importlib.machinery.FrozenImporter,
                importlib.machinery.PathFinder)
    for finder in sys.meta_path:
        # The normal setuptools shim handles distutils, not any model package.
        distutils = (type(finder).__module__, type(finder).__name__) == (
            "_distutils_hack", "DistutilsMetaFinder")
        _require(any(finder is expected for expected in standard) or distutils,
                 "unsupported_import_hook")


def _module_spec(name, site):
    """PathFinder's explicit paths avoid importing parent packages during preflight."""
    search = sys.path
    spec = None
    parts = name.split(".")
    for index in range(len(parts)):
        fullname = ".".join(parts[:index + 1])
        spec = importlib.machinery.PathFinder.find_spec(fullname, search)
        _require(spec is not None, "missing_runtime_module")
        if fullname == "mlx.core":
            _require(type(spec.loader) is importlib.machinery.ExtensionFileLoader,
                     "mlx_core_extension_required")
        expected = site.joinpath(*parts[:index + 1])
        if spec.origin is None:
            _require(spec.loader is None
                     and list(spec.submodule_search_locations or []) == [str(expected)],
                     "shadow_runtime_namespace")
            with _open(expected, directory=True):
                pass
        else:
            _require(type(spec.loader) in (importlib.machinery.SourceFileLoader,
                                          importlib.machinery.ExtensionFileLoader),
                     "unsupported_runtime_loader")
            valid = {expected.with_suffix(".py"), expected / "__init__.py"}
            valid.update(Path(str(expected) + suffix)
                         for suffix in importlib.machinery.EXTENSION_SUFFIXES)
            _require(Path(spec.origin) in valid, "shadow_runtime_origin")
            with _open(spec.origin):
                pass
        if spec.submodule_search_locations is not None:
            _require(list(spec.submodule_search_locations) == [str(expected)],
                     "shadow_runtime_package_path")
        search = spec.submodule_search_locations
        _require(search is not None or index == len(parts) - 1, "runtime_parent_not_package")
    return spec


def _loaded_origins(site, specs):
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] not in _PACKAGES:
            continue
        _require(module is not None, "invalid_loaded_runtime_module")
        origin = getattr(module, "__file__", None)
        if origin is not None:
            path = _absolute(origin)
            _require(path.is_relative_to(site / name.split(".")[0]), "shadow_loaded_module")
            with _open(path):
                pass
        elif name != "mlx" and not name.startswith("mlx.core."):
            _require(name in specs and specs[name].origin is None, "unbound_loaded_module")
    for name, spec in specs.items():
        if name not in sys.modules:
            continue
        module = sys.modules[name]
        actual = getattr(module, "__spec__", None)
        _require(actual is not None and actual.origin == spec.origin
                 and getattr(module, "__file__", None) == spec.origin, "loaded_module_origin_mismatch")
        if spec.submodule_search_locations is not None:
            _require(list(getattr(module, "__path__", [])) == list(spec.submodule_search_locations),
                     "loaded_package_path_mismatch")


def _environment(config):
    _import_hooks()
    site = _absolute(sysconfig.get_path("purelib"))
    with _open(site, directory=True):
        pass
    identities = {}
    for name, expected in config["existing_environment_metadata"].items():
        distribution = name.replace("-", "_")
        paths = list(site.glob(f"{distribution}-*.dist-info"))
        directory = site / f"{distribution}-{expected['version']}.dist-info"
        _require(paths == [directory], "runtime_distribution_version_or_duplicates")
        path = directory / "METADATA"
        identity = _hash_file(path, limit=1024 * 1024)
        _require(identity.sha256 == expected["metadata_sha256"], "runtime_metadata_sha256")
        metadata = BytesParser().parsebytes(_read_bytes(path, identity))
        _require(metadata.get_all("Version") == [expected["version"]]
                 and [v.lower().replace("_", "-") for v in metadata.get_all("Name", [])]
                 == [name], "runtime_metadata_name_or_version")
        identities[str(path)] = identity
    for name, expected in config["source_files"].items():
        path = site / name
        identities[str(path)] = _hash_file(path, expected=expected)
    names = set(_RUNTIME_MODULES) | set(_PACKAGES)
    specs = {name: _module_spec(name, site) for name in sorted(names)}
    _loaded_origins(site, specs)
    return site, identities, specs


def _check_runtime_environment(environment, modules):
    site, identities, specs = environment
    _import_hooks()
    for path, identity in identities.items():
        with _open(path) as descriptor:
            _require(_token(os.fstat(descriptor)) == identity.stat_token, "runtime_source_changed")
    _loaded_origins(site, specs)
    _require(all(sys.modules.get(name) is module for name, module in modules.items()),
             "runtime_module_replaced")


def _function_origin(function, module_name, environment):
    origin = environment[2][module_name].origin
    _require(getattr(function, "__module__", None) == module_name
             and getattr(getattr(function, "__code__", None), "co_filename", None) == origin,
             "runtime_function_origin")


def _flatten(tree, utility):
    pairs = utility.tree_flatten(tree)
    result = {}
    for name, array in pairs:
        _require(type(name) is str and name not in result, "runtime_parameter_duplicate")
        result[name] = array
    return result


def _raw_chunks(array, dtype, mx, numpy):
    """C-order little-endian original bits; each host copy is at most 1 MiB.

    MLX ``view(uint8)`` preserves the binary representation. No BF16->FP32
    conversion occurs. A reshape may materialize one device leaf; host arrays
    and their byte copies are discarded at each chunk, not collected per model.
    """
    _require(sys.byteorder == "little", "little_endian_runtime_required")
    expected_dtype = mx.bfloat16 if dtype == "BF16" else mx.float32
    _require(type(array) is mx.array and array.dtype == expected_dtype, "runtime_tensor_dtype")
    flat = array.reshape(-1)
    step = _CHUNK_BYTES // _DTYPE_BYTES[dtype]
    for begin in range(0, array.size, step):
        block = mx.contiguous(flat[begin:begin + step])
        raw = mx.view(block, mx.uint8)
        mx.eval(raw)
        host = numpy.asarray(raw, order="C")
        _require(host.dtype == numpy.dtype("uint8") and host.flags.c_contiguous,
                 "runtime_raw_byte_view")
        chunk = host.tobytes(order="C")
        _require(len(chunk) == min(step, array.size - begin) * _DTYPE_BYTES[dtype]
                 and len(chunk) <= _CHUNK_BYTES, "runtime_raw_byte_size")
        yield chunk
        del host, chunk, raw, block


def _leaf(array, expected, mx, numpy, *, zero=False):
    shape = tuple(expected["shape"])
    _require(type(array) is mx.array and tuple(array.shape) == shape
             and all(type(n) is int for n in array.shape)
             and type(array.size) is int and array.size == math.prod(shape), "runtime_tensor_shape")
    dtype = expected["dtype"]
    digest, length = hashlib.sha256(), 0
    for chunk in _raw_chunks(array, dtype, mx, numpy):
        if dtype == "F32":
            _require(all(math.isfinite(value) for (value,) in struct.iter_unpack("<f", chunk)),
                     "nonfinite_adapter_parameter")
        if zero:
            _require(not any(chunk), "initial_lora_b_not_zero")
        digest.update(chunk)
        length += len(chunk)
    _require(length == math.prod(shape) * _DTYPE_BYTES[dtype], "runtime_tensor_byte_count")
    result = {"shape": list(shape), "dtype": dtype, "bytes": length,
              "raw_tensor_sha256": digest.hexdigest()}
    if "raw_tensor_sha256" in expected:
        _require(result["raw_tensor_sha256"] == expected["raw_tensor_sha256"],
                 "runtime_parameter_content_mismatch")
    return result


def _frozen_spec(spec, *, lora):
    _require(spec["expected_loader_sanitize_drop"] == ["lm_head.weight"], "fixed_sanitize")
    serialized = spec["serialized_tensors"]
    head, embedding = serialized["lm_head.weight"], serialized["model.embed_tokens.weight"]
    _require(all(_same(head[k], embedding[k]) for k in ("shape", "dtype", "raw_tensor_sha256")),
             "tied_embedding_identity")
    mapping = spec["expected_raw_to_lora_frozen_key_mapping"]
    result = {}
    for name, item in serialized.items():
        if name == "lm_head.weight":
            continue
        key = mapping[name] if lora else name
        _require(key not in result and item["dtype"] == "BF16", "frozen_parameter_mapping")
        result[key] = {"shape": item["shape"], "dtype": "BF16",
                       "raw_tensor_sha256": item["raw_tensor_sha256"]}
    _require(len(result) == spec["expected_frozen_leaf_tensors"]
             and sum(math.prod(v["shape"]) for v in result.values())
             == spec["expected_frozen_parameter_count"], "frozen_parameter_count")
    return result


def _adapter_spec(spec):
    return {name: {"shape": value["shape"], "dtype": "F32"}
            for name, value in spec["expected_lora"]["tensors"].items()}


def _dropout_state(module):
    # Compare with a fresh exact-class zero-dropout object. This binds all
    # scalar state without assuming an undocumented dropout field's name.
    attributes = {k: v for k, v in vars(module).items() if k not in ("_training", "_no_grad")}
    _require(not dict(module) and getattr(module, "_no_grad", None) == set(), "dropout_extra_state")
    return attributes


def _lora_structure(model, spec, modules):
    nn, lora_module = modules["mlx.nn"], modules["mlx_lm.tuner.lora"]
    targets = {name.rsplit(".", 1)[0] for name in spec["expected_lora"]["tensors"]}
    named = model.named_modules()
    _require(len({name for name, _ in named}) == len(named), "runtime_module_duplicate")
    actual = {name: layer for name, layer in named if isinstance(layer, lora_module.LoRALinear)}
    _require(set(actual) == targets and len(actual) == spec["expected_lora"]["module_count"],
             "lora_module_set")
    dropout = _dropout_state(nn.Dropout(p=0.0))
    for layer in actual.values():
        _require(type(layer) is lora_module.LoRALinear and type(layer.linear) is nn.Linear
                 and type(layer.scale) is float and layer.scale == 2.0
                 and type(layer.dropout) is nn.Dropout
                 and _same(_dropout_state(layer.dropout), dropout), "lora_fixed_structure")
    return actual


def _parameters(model, spec, modules, *, lora, initial=False):
    mx, numpy, utility = modules["mlx.core"], modules["numpy"], modules["mlx.utils"]
    lora_modules = _lora_structure(model, spec, modules) if lora else {}
    arrays = _flatten(model.parameters(), utility)
    trainable = _flatten(model.trainable_parameters(), utility)
    frozen = _frozen_spec(spec, lora=lora)
    adapters = _adapter_spec(spec) if lora else {}
    _require(set(arrays) == set(frozen) | set(adapters), "runtime_parameter_keys")
    for name, layer in lora_modules.items():
        _require(layer.lora_a is arrays[name + ".lora_a"]
                 and layer.lora_b is arrays[name + ".lora_b"]
                 and layer.linear.weight is arrays[name + ".linear.weight"], "lora_parameter_objects")
    _require(set(trainable) == set(adapters)
             and all(trainable[name] is arrays[name] for name in trainable), "trainable_parameter_keys")
    _require(len({id(a) for a in arrays.values()}) == len(arrays), "aliased_parameter_objects")
    leaves = {}
    for name in sorted(arrays):
        expected = frozen[name] if name in frozen else adapters[name]
        leaves[name] = _leaf(arrays[name], expected, mx, numpy,
                             zero=initial and name.endswith(".lora_b"))
        leaves[name]["trainable"] = name in adapters
    actual_base_count = sum(math.prod(leaves[n]["shape"]) for n in frozen)
    actual_adapter_count = sum(math.prod(leaves[n]["shape"]) for n in adapters)
    if lora:
        _require(len(adapters) == spec["expected_lora"]["tensor_count"]
                 and actual_adapter_count == spec["expected_lora"]["parameter_count"]
                 and len(leaves) == spec["expected_model_leaf_tensors_with_lora"],
                 "runtime_lora_parameter_count")
    value = {"schema": "toolalign.qwen-parameter-content.v1", "model_id": spec["model_id"],
             "revision": spec["revision"], "metadata_sha256": CONFIG_SHA256,
             "encoding": "C-order little-endian original BF16/F32 bits; SHA256 per leaf; sorted UTF-8 JSON",
             "lora": {"rank": 8, "scale": 2.0, "dropout": 0.0,
                      "keys": ["self_attn.q_proj", "self_attn.v_proj"], "layers": 28} if lora else None,
             "actual_base_leaf_count": len(frozen), "actual_base_parameter_count": actual_base_count,
             "actual_adapter_leaf_count": len(adapters), "actual_adapter_parameter_count": actual_adapter_count,
             "actual_total_leaf_count": len(leaves), "leaves": leaves}
    return {**value, "content_sha256": hashlib.sha256(_canonical(value)).hexdigest()}


def _adapter_file(path, expected_sha256, spec):
    _require(type(expected_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_sha256),
             "adapter_sha256_required")
    path = _absolute(path)
    _require(path.suffix == ".safetensors", "adapter_safetensors_required")
    identity = _hash_file(path, limit=spec["expected_lora"]["parameter_count"] * 4 + _HEADER_LIMIT + 8)
    _require(identity.sha256 == expected_sha256, "adapter_file_sha256")
    tensors, header = _header(path, identity)
    expected = _adapter_spec(spec)
    _require(set(tensors) == set(expected), "adapter_tensor_keys")
    for name, tensor in tensors.items():
        _require(tensor.dtype == "F32" and tensor.shape == tuple(expected[name]["shape"]),
                 "adapter_tensor_identity")
    # Read original payload bytes only, after binding the complete file hash.
    with _open(path) as descriptor:
        _require(_token(os.fstat(descriptor)) == identity.stat_token, "adapter_file_changed")
        for name, tensor in tensors.items():
            os.lseek(descriptor, 8 + header["header_bytes"] + tensor.offsets[0], os.SEEK_SET)
            remaining, hasher = tensor.bytes, hashlib.sha256()
            while remaining:
                chunk = os.read(descriptor, min(_CHUNK_BYTES, remaining))
                _require(bool(chunk), "truncated_adapter_payload")
                hasher.update(chunk)
                remaining -= len(chunk)
            expected[name]["raw_tensor_sha256"] = hasher.hexdigest()
        _require(_token(os.fstat(descriptor)) == identity.stat_token, "adapter_file_changed")
    return identity, expected


class QwenModel:
    """A caller-owned resident model; any failed operation is terminal for this wrapper.

    ``model`` exposes the actual model for a future authorized caller. Call
    ``parameter_identity`` after updates to verify unchanged BF16 base content,
    the exact trainable set, and the current finite FP32 adapter contents.
    """

    def __init__(self, marker, *, model, spec, files, directory_token, lease, repository,
                 environment, modules):
        _require(marker is _CREATE, "use_load_qwen_model")
        self._model, self._spec, self._files = model, spec, files
        self._directory_token = directory_token
        self._lease, self._repository = lease, repository
        self._environment, self._modules = environment, modules
        self._state, self._failure = "BASE_READY", None

    @property
    def files(self):
        return self._files

    @property
    def state(self):
        return self._state

    @property
    def failure(self):
        return self._failure

    def _live(self):
        _require(self._state in ("BASE_READY", "LORA_READY"), "runtime_failed_state")
        owner = require_current_lease(self._lease, self._repository)
        _check_runtime_environment(self._environment, self._modules)
        _unchanged(self.files.root, {item.name: item for item in self.files.files}, self._directory_token)
        architecture = self._modules["mlx_lm.models.qwen3"]
        _require(type(self._model) is architecture.Model
                 and type(self._model.args) is architecture.ModelArgs
                 and type(self._model.training) is bool
                 and self._model.model_type == self._spec["model_config"]["model_type"],
                 "runtime_model_architecture")
        _require(all(_same(getattr(self._model.args, name), self._spec["model_config"][name])
                     for name in architecture.ModelArgs.__dataclass_fields__), "runtime_model_args")
        return owner

    @contextmanager
    def _operation(self):
        try:
            owner = self._live()
            yield owner
            self._live()
        except BaseException as exc:
            if self._failure is None:
                self._failure = {"type": type(exc).__name__, "message": str(exc)}
            self._state = "FAILED"
            raise

    @property
    def model(self):
        with self._operation():
            return self._model

    def parameter_identity(self):
        with self._operation() as owner:
            value = _parameters(self._model, self._spec, self._modules,
                                lora=self._state == "LORA_READY")
            return self._identity_result(value, owner)

    def _identity_result(self, value, owner):
        return {**value, "state": self._state, "model_training": self._model.training,
                "lease_owner_sha256": hashlib.sha256(_canonical(owner)).hexdigest(),
                "module_origins": {name: module.__spec__.origin
                                   for name, module in self._modules.items()},
                "model_file_sha256": {item.name: item.sha256 for item in self.files.files}}

    def attach_lora(self):
        """Freeze first; install only rank8/scale2/zero-dropout q/v in all 28 layers."""
        with self._operation() as owner:
            _require(self._state == "BASE_READY", "lora_already_attached")
            _parameters(self._model, self._spec, self._modules, lora=False)
            mode = self._model.training
            _require(type(mode) is bool, "model_training_mode")
            self._model.freeze()
            loader = self._modules["mlx_lm.tuner.utils"].linear_to_lora_layers
            _function_origin(loader, "mlx_lm.tuner.utils", self._environment)
            loader(self._model, 28, {"rank": 8, "scale": 2.0, "dropout": 0.0,
                                    "keys": ["self_attn.q_proj", "self_attn.v_proj"]}, use_dora=False)
            self._model.train(mode)
            value = _parameters(self._model, self._spec, self._modules, lora=True, initial=True)
            self._state = "LORA_READY"
            return self._identity_result(value, owner)

    def reload_adapter(self, path, *, expected_sha256):
        """Load only an explicitly selected exact adapter file into existing fixed LoRA."""
        with self._operation() as owner:
            _require(self._state == "LORA_READY", "existing_lora_required")
            before = _parameters(self._model, self._spec, self._modules, lora=True)
            identity, expected = _adapter_file(path, expected_sha256, self._spec)
            loaded = self._modules["mlx.core"].load(str(_absolute(path)))
            _require(type(loaded) is dict and set(loaded) == set(expected), "loaded_adapter_keys")
            for name, array in loaded.items():
                _leaf(array, expected[name], self._modules["mlx.core"], self._modules["numpy"])
            with _open(path) as descriptor:
                _require(_token(os.fstat(descriptor)) == identity.stat_token, "adapter_file_changed")
            self._live()
            utility = self._modules["mlx.utils"]
            self._model.update(utility.tree_unflatten(sorted(loaded.items())), strict=True)
            after = _parameters(self._model, self._spec, self._modules, lora=True)
            for name, leaf in after["leaves"].items():
                if name in expected:
                    _require(leaf["raw_tensor_sha256"] == expected[name]["raw_tensor_sha256"],
                             "reloaded_adapter_content")
                else:
                    _require(_same(leaf, before["leaves"][name]), "reloaded_base_changed")
            return self._identity_result({**after, "adapter_file_sha256": identity.sha256}, owner)


def load_qwen_model(model_root, *, model_id, revision, config_path, lease, repository):
    """Future authorized runtime: fixed local eager BF16 loader under the caller's lease.

    No config/architecture overrides, Hub fallback, tokenizer construction, or
    bypass flags. CPU/mock validation of this code is not a real model run.
    """
    require_current_lease(lease, repository)
    config = _config(config_path)
    spec = _model_spec(config, model_id, revision)
    root = _absolute(model_root)
    files, directory_token = _directory_files(root, spec)
    environment = _environment(config)
    require_current_lease(lease, repository)
    _unchanged(root, files, directory_token)
    modules = {name: importlib.import_module(name) for name in _RUNTIME_MODULES}
    _check_runtime_environment(environment, modules)
    require_current_lease(lease, repository)
    _unchanged(root, files, directory_token)
    mx, loader = modules["mlx.core"], modules["mlx_lm.utils"].load_model
    _require(mx.default_device() == mx.gpu, "gpu_default_device_required")
    _function_origin(loader, "mlx_lm.utils", environment)
    model, loaded_config = loader(root, lazy=False, strict=True)
    expected_config = {**spec["model_config"], "eos_token_id": spec["generation_eos_ids"]}
    _require(_same(loaded_config, expected_config), "loaded_model_config_mismatch")
    _require(type(model) is modules["mlx_lm.models.qwen3"].Model, "loaded_model_class")
    model.freeze()
    resident = QwenModel(_CREATE, model=model, spec=spec, files=_files_result(root, spec, files),
                         directory_token=directory_token, lease=lease, repository=repository,
                         environment=environment, modules=modules)
    resident.parameter_identity()
    return resident
