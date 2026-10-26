"""Fixed M1 production entry; no backend selection or CPU fallback in the CLI."""

import time
from pathlib import Path

from toolalign.inference.cuda import CUDAServiceBackend
from toolalign.model_io.cuda_generation import (
    BATCH_FILE_VALIDATION,
    MODEL_ID,
    MODEL_REVISION,
    selected_model_identity,
)
from toolalign.model_io.qwen_model import validate_model_files
from toolalign.training.cuda_sft.protocol import dependency_identity, load_protocol, source_identity

from .http import serve
from .protocol import validate_run
from .runtime import Service


def execute(request, *, cancellation=None):
    started = time.monotonic()
    validate_run(request)
    load_protocol(request["repository"])
    source = source_identity(request["repository"], request["source_commit"])
    dependencies = dependency_identity(request["dependency_lock"], request["dependency_lock_sha256"])
    preflight = time.monotonic()
    verified = validate_model_files(request["model_root"], model_id=MODEL_ID, revision=MODEL_REVISION,
                                     config_path=Path(request["repository"]) / "configs/qwen-models.v1.json")
    identity = {"execution_kind": "REAL_CUDA_SERVICE", "source": source, "dependencies": dependencies,
                "model_identity": selected_model_identity(request["repository"]),
                "checkpoint_sha256": request["checkpoint_sha256"],
                "adapter_sha256": request["adapter_sha256"], "model_file_validation": BATCH_FILE_VALIDATION,
                "model_file_preflight_seconds": time.monotonic() - preflight}

    def backend():
        return CUDAServiceBackend(repository=request["repository"], model_root=request["model_root"],
            checkpoint_dir=request["checkpoint_dir"], run_id=request["run_id"],
            cache_enabled=request["cache_enabled"], verified_files=verified)

    return serve(Service(request, identity=identity, backend_factory=backend,
                         cancellation=cancellation, started_monotonic=started))
