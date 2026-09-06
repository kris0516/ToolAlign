"""Read the exact S0 CPU-only configuration; there are no executable options."""

from __future__ import annotations

import hashlib
from importlib.resources import files

from toolalign.data.common import DataError, file_hash, read_json

CONFIG_SHA256 = "5aad6ff6db68ee4fe9bac0aa6104eaeff17bf948b509bfce3d14e3eac9d9aa29"


def require(condition, code):
    if not condition:
        raise DataError(code)


def load_config(path):
    require(file_hash(path) == CONFIG_SHA256, "sft_config_file_hash_mismatch")
    return read_json(path)


def consumer_identity():
    names = ("__init__.py", "__main__.py", "config.py", "data.py", "collator.py",
             "plan.py", "validation.py", "mlx_adapter.py")
    return {name: hashlib.sha256(files("toolalign.training.sft").joinpath(name).read_bytes()).hexdigest()
            for name in names}
