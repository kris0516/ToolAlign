"""Complete adapter/optimizer/RNG state, atomic publication and three retained states."""

from __future__ import annotations

import hashlib
import io
import os
import random
import shutil
import tempfile
from pathlib import Path

from .protocol import (
    MAX_BUNDLE_BYTES,
    document,
    encoded,
    finite_score,
    read_bytes,
    require,
    sha,
    write_bytes,
)


def _cpu(value):
    import torch

    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: _cpu(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(_cpu(v) for v in value)
    return value


def rng_state(*, device):
    import numpy as np
    import torch

    state = np.random.get_state()
    return {"python_rng": random.getstate(),
            "numpy_rng": (state[0], state[1].tolist(), state[2], state[3], state[4]),
            "torch_cpu_rng": torch.get_rng_state(),
            "torch_cuda_rng": [torch.cuda.get_rng_state(0)] if str(device).startswith("cuda") else []}


def restore_rng(state, *, device):
    import numpy as np
    import torch

    require(bool(state["torch_cuda_rng"]) == str(device).startswith("cuda"), "resume_rng_device")
    random.setstate(state["python_rng"])
    value = state["numpy_rng"]
    np.random.set_state((value[0], np.asarray(value[1], dtype=np.uint32), *value[2:]))
    torch.set_rng_state(state["torch_cpu_rng"])
    if state["torch_cuda_rng"]:
        require(len(state["torch_cuda_rng"]) == 1, "resume_cuda_device_count")
        torch.cuda.set_rng_state(state["torch_cuda_rng"][0], device=0)


def capture(model, optimizer, *, step, cursor, identity, device):
    return {"schema": "toolalign.cuda-sft-state.v1", "identity": identity,
            "adapter": {n: _cpu(p) for n, p in model.named_parameters() if p.requires_grad},
            "optimizer": _cpu(optimizer.state_dict()), "constant_lr": 0.0001,
            "optimizer_step": step, "data_cursor": cursor, "validation_ce": None,
            "historical_best": None, **rng_state(device=device)}


def serialize(state):
    import torch

    buffer = io.BytesIO()
    torch.save(state, buffer)
    return buffer.getvalue()


def deserialize(raw, *, identity, train_count, manifest=None, device="cpu"):
    import numpy as np
    import torch

    state = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
    required = {"schema", "identity", "adapter", "optimizer", "constant_lr", "optimizer_step",
                "data_cursor", "python_rng", "numpy_rng", "torch_cpu_rng", "torch_cuda_rng",
                "validation_ce", "historical_best"}
    require(type(state) is dict and set(state) == required
            and state["schema"] == "toolalign.cuda-sft-state.v1", "incomplete_checkpoint_state")
    require(state["identity"] == identity, "checkpoint_identity_mismatch")
    if state["validation_ce"] is not None:
        finite_score(state["validation_ce"], state["optimizer_step"], sha(raw))
    if manifest is not None:
        require(all(state[k] == manifest[k] for k in ("optimizer_step", "data_cursor", "validation_ce")),
                "checkpoint_manifest_state_mismatch")
        historical = state["historical_best"]
        if historical is not None:
            require(manifest["best"] == historical | {"file": "best.pt"}, "checkpoint_selection_mismatch")
        elif state["validation_ce"] is not None:
            expected = {k: state[k] for k in ("optimizer_step", "data_cursor", "validation_ce")}
            require(manifest["best"] == expected | {"file": "state.pt", "checkpoint_sha256": sha(raw)},
                    "checkpoint_selection_mismatch")
        else:
            require(manifest["best"] is None, "checkpoint_selection_mismatch")
    step, cursor = state["optimizer_step"], state["data_cursor"]
    require(type(step) is int and 0 < step <= (train_count + 7) // 8
            and type(cursor) is int and cursor == min(step * 8, train_count), "checkpoint_cursor")
    require(state["constant_lr"] == 0.0001 and state["adapter"], "checkpoint_optimizer_contract")
    require(len(state["optimizer"]["param_groups"]) == 1, "checkpoint_optimizer_groups")
    group = state["optimizer"]["param_groups"][0]
    require(group["lr"] == 0.0001 and tuple(group["betas"]) == (0.9, 0.999)
            and group["eps"] == 1e-8 and group["weight_decay"] == 0
            and all(group[k] is False for k in ("foreach", "fused", "amsgrad", "maximize", "capturable", "differentiable")),
            "checkpoint_optimizer_contract")
    identifiers, moments = group["params"], state["optimizer"]["state"]
    require(len(identifiers) == len(state["adapter"]) == len(moments)
            and set(identifiers) == set(moments), "incomplete_optimizer_state")
    for ident, adapter in zip(identifiers, state["adapter"].values(), strict=True):
        moment = moments[ident]
        require(set(moment) == {"step", "exp_avg", "exp_avg_sq"}, "incomplete_optimizer_state")
        require(isinstance(adapter, torch.Tensor) and adapter.dtype == torch.float32
                and bool(torch.isfinite(adapter).all()), "invalid_adapter_state")
        require(isinstance(moment["step"], torch.Tensor) and moment["step"].numel() == 1
                and float(moment["step"]) == step, "optimizer_step_mismatch")
        require(all(isinstance(moment[k], torch.Tensor) and moment[k].shape == adapter.shape
                    and moment[k].dtype == adapter.dtype and bool(torch.isfinite(moment[k]).all())
                    for k in ("exp_avg", "exp_avg_sq")), "invalid_optimizer_moments")
    # Validate saved RNGs on private generators, without perturbing the process.
    try:
        random.Random(0).setstate(state["python_rng"])
        numpy_state = state["numpy_rng"]
        np.random.RandomState(0).set_state((numpy_state[0], np.asarray(numpy_state[1], dtype=np.uint32), *numpy_state[2:]))
        torch.Generator(device="cpu").set_state(state["torch_cpu_rng"])
        cuda_states = state["torch_cuda_rng"]
        require(type(cuda_states) is list and len(cuda_states) == (1 if str(device).startswith("cuda") else 0),
                "invalid_rng_state")
        if cuda_states:
            require(isinstance(cuda_states[0], torch.Tensor) and cuda_states[0].dtype == torch.uint8
                    and cuda_states[0].shape == torch.cuda.get_rng_state(0).shape, "invalid_rng_state")
    except (TypeError, ValueError, RuntimeError, IndexError, OverflowError) as exc:
        raise ValueError("invalid_rng_state") from exc
    return state


def restore(state, model, optimizer, *, device):
    import torch

    parameters = {n: p for n, p in model.named_parameters() if p.requires_grad}
    require(set(parameters) == set(state["adapter"]), "resume_adapter_keys")
    with torch.no_grad():
        for name, parameter in parameters.items():
            stored = state["adapter"][name]
            require(stored.dtype == parameter.dtype and stored.shape == parameter.shape,
                    "resume_adapter_shape_or_dtype")
            parameter.copy_(stored.to(device=parameter.device))
    optimizer.load_state_dict(state["optimizer"])
    restore_rng(state, device=device)
    return state["optimizer_step"], state["data_cursor"]


def inspect_checkpoint(root, *, identity, expected_sha=None):
    """Verify complete bytes and identity before loading a model or unpickling state."""
    root = Path(root)
    manifest = document(root / "manifest.json", limit=4 * 1024**2)
    require(manifest.get("schema") == "toolalign.cuda-sft-checkpoint.v1"
            and manifest.get("complete") is True, "incomplete_checkpoint")
    require(manifest["identity"] == identity, "checkpoint_identity_mismatch")
    require(expected_sha is None or manifest["checkpoint_sha256"] == expected_sha,
            "resume_checkpoint_hash")
    expected_names = {"state.pt"} | ({"best.pt"} if manifest["best"] is not None
                                    and manifest["best"]["file"] == "best.pt" else set())
    require(set(manifest["files"]) == expected_names, "checkpoint_files")
    contents = {}
    for name, spec in manifest["files"].items():
        raw = read_bytes(root / name)
        require(len(raw) == spec["bytes"] and sha(raw) == spec["sha256"], "checkpoint_file_identity")
        contents[name] = raw
    require(sha(contents["state.pt"]) == manifest["checkpoint_sha256"], "checkpoint_hash")
    if manifest["best"] is not None:
        best = manifest["best"]
        require(best["file"] in contents and sha(contents[best["file"]]) == best["checkpoint_sha256"],
                "checkpoint_best_identity")
        finite_score(best["validation_ce"], best["optimizer_step"], best["checkpoint_sha256"])
    return manifest, contents


def _publish(root, name, manifest, contents):
    """Rename a complete private directory on each filesystem; manifest is last."""
    root = Path(root)
    temporary = Path(tempfile.mkdtemp(prefix=".pending-", dir=root))
    try:
        for filename, raw in contents.items():
            write_bytes(temporary / filename, raw)
        write_bytes(temporary / "manifest.json", encoded(manifest) + b"\n")
        inspect_checkpoint(temporary, identity=manifest["identity"], expected_sha=manifest["checkpoint_sha256"])
        require(not (root / name).exists(), "checkpoint_already_exists")
        os.rename(temporary, root / name)
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _record(manifest):
    return {k: manifest[k] for k in ("optimizer_step", "data_cursor", "validation_ce", "checkpoint_sha256")}


def _name(record):
    return f"step-{record['optimizer_step']:06d}-{record['checkpoint_sha256'][:12]}"


class CheckpointStore:
    def __init__(self, *, local, persistent, identity, max_bytes):
        self.local, self.persistent = Path(local), Path(persistent)
        require(self.local.resolve() != self.persistent.resolve(), "distinct_persistent_storage_required")
        self.identity, self.max_bytes = identity, max_bytes
        self.records, self.best, self.best_bytes = [], None, None
        self.local.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.persistent.mkdir(mode=0o700, parents=False, exist_ok=False)

    def _budget(self, contents, manifest):
        existing = sum(p.stat().st_size for root in (self.local, self.persistent)
                       for p in root.rglob("*") if p.is_file())
        incoming = 2 * (sum(len(v) for v in contents.values()) + len(encoded(manifest)) + 1)
        require(existing + incoming + 1024**2 <= min(self.max_bytes, MAX_BUNDLE_BYTES), "checkpoint_byte_budget")

    def _write(self, manifest, contents):
        self._budget(contents, manifest)
        name = _name(manifest)
        _publish(self.local, name, manifest, contents)
        _publish(self.persistent, name, manifest, contents)
        # This proves a second verified copy, not persistence across a Colab reset.
        # E1 must retrieve and read back the full directory outside the instance.
        inspect_checkpoint(self.persistent / name, identity=self.identity,
                           expected_sha=manifest["checkpoint_sha256"])
        self.records.append(_record(manifest))
        self._retain()
        return self.local / name

    def save(self, state, *, validation_ce=None):
        require(state["identity"] == self.identity, "checkpoint_identity_mismatch")
        require(not self.records or state["optimizer_step"] > max(r["optimizer_step"] for r in self.records),
                "checkpoint_step_must_advance")
        if validation_ce is not None:
            finite_score(validation_ce, state["optimizer_step"], "")
        # Bind score/selection metadata into the pinned state.pt itself. The
        # manifest cannot substitute a different score or historical best.
        new_best = validation_ce is not None and (self.best is None or
            finite_score(validation_ce, state["optimizer_step"], "")[:2] <
            finite_score(self.best["validation_ce"], self.best["optimizer_step"], "")[:2])
        state = state | {"validation_ce": validation_ce,
                         "historical_best": None if new_best else self.best}
        raw = serialize(state)
        record = {"optimizer_step": state["optimizer_step"], "data_cursor": state["data_cursor"],
                  "validation_ce": validation_ce, "checkpoint_sha256": sha(raw)}
        if new_best:
            self.best, self.best_bytes = record, raw
        contents = {"state.pt": raw}
        best = None
        if self.best is not None:
            filename = "state.pt" if self.best["checkpoint_sha256"] == sha(raw) else "best.pt"
            best = {**self.best, "file": filename}
            contents[filename] = self.best_bytes
        manifest = {"schema": "toolalign.cuda-sft-checkpoint.v1", "complete": True,
            "identity": self.identity, **record, "best": best,
            "files": {n: {"sha256": sha(b), "bytes": len(b)} for n, b in contents.items()}}
        return self._write(manifest, contents)

    def seed(self, manifest, contents):
        """Carry the historical best across a new output directory or rollback.

        Each complete checkpoint includes its best core state without recursively
        embedding older checkpoints, so retention cannot erase that selection.
        """
        require(manifest["identity"] == self.identity and not self.records, "resume_store_identity")
        best = manifest["best"]
        if best is not None:
            self.best = {k: v for k, v in best.items() if k != "file"}
            self.best_bytes = contents[best["file"]]
            if best["checkpoint_sha256"] != manifest["checkpoint_sha256"]:
                best_manifest = {**manifest, **self.best, "best": {**self.best, "file": "state.pt"},
                    "files": {"state.pt": {"sha256": best["checkpoint_sha256"], "bytes": len(self.best_bytes)}}}
                self._write(best_manifest, {"state.pt": self.best_bytes})
        self._write(manifest, contents)

    def _retain(self):
        last = max(self.records, key=lambda r: r["optimizer_step"])
        keep = {last["checkpoint_sha256"]}
        if self.best is not None:
            keep.add(self.best["checkpoint_sha256"])
        rollback = [r for r in self.records if r["validation_ce"] is not None and r["checkpoint_sha256"] not in keep]
        if rollback:
            keep.add(max(rollback, key=lambda r: r["optimizer_step"])["checkpoint_sha256"])
        retained = [r for r in self.records if r["checkpoint_sha256"] in keep]
        index = {"schema": "toolalign.cuda-sft-checkpoints.v1", "identity": self.identity,
                 "best": self.best, "last": last, "retained": retained}
        for root in (self.local, self.persistent):
            temporary = root / ".index-new.json"
            write_bytes(temporary, encoded(index) + b"\n")
            os.replace(temporary, root / "index.json")
            for record in self.records:
                if record["checkpoint_sha256"] not in keep:
                    shutil.rmtree(root / _name(record))
        self.records = retained


def parameter_hash(model, *, trainable=True):
    import torch

    hasher = hashlib.sha256()
    for name, parameter in model.named_parameters():
        if parameter.requires_grad == trainable:
            value = parameter.detach().cpu().contiguous()
            hasher.update(encoded([name, str(value.dtype), list(value.shape)]))
            hasher.update(value.view(torch.uint8).numpy().tobytes())
    return hasher.hexdigest()
