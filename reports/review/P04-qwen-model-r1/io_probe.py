"""R1 original CPU-only file replacement probe; never loads tensor values."""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from toolalign.model_io import qwen_model as q


def main():
    root, operation, replacement = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    root.mkdir()
    path = root / "original.safetensors"
    header = json.dumps({"original": {"dtype": "BF16", "shape": [2],
                                      "data_offsets": [0, 4]}}).encode()
    header += b" " * (-len(header) % 8)
    original = len(header).to_bytes(8, "little") + header + b"\x00\x00\x00\x80"
    path.write_bytes(original)
    outside = root.parent / "outside"
    outside.mkdir()
    (outside / path.name).write_bytes(b"outside sentinel must not be read")
    identity = q._hash_file(path)
    directory_token = q._token(root.stat())
    real_open = os.open
    events = []

    def switch_before_open(name, flags, *args, **kwargs):
        if name == path.name and not events:
            events.append({"flags": flags, "has_dir_fd": kwargs.get("dir_fd") is not None})
            if replacement == "parent":
                root.rename(root.with_name(root.name + "-retained"))
                root.symlink_to(outside, target_is_directory=True)
            else:
                path.rename(root / "retained-original")
                if replacement == "fifo":
                    os.mkfifo(path)
                else:
                    path.symlink_to(outside / path.name)
        return real_open(name, flags, *args, **kwargs)

    os.open = switch_before_open
    started = time.monotonic()
    code = None
    try:
        if operation == "hash":
            result = q._hash_file(path).sha256
        elif operation == "bytes":
            result = hashlib.sha256(q._read_bytes(path, identity)).hexdigest()
        else:
            result = q._header(path, identity)[1]["tensor_count"]
    except q.QwenModelError as exc:
        code = str(exc)
    finally:
        os.open = real_open
    elapsed = time.monotonic() - started
    assert len(events) == 1 and events[0]["has_dir_fd"]
    assert events[0]["flags"] & os.O_NONBLOCK
    assert events[0]["flags"] & os.O_NOFOLLOW
    if replacement == "parent":
        assert code is None and result == hashlib.sha256(original).hexdigest()
        try:
            q._unchanged(root, {path.name: identity}, directory_token)
        except q.QwenModelError as exc:
            code = str(exc)
        else:
            raise AssertionError("The changed root must be rejected")
    expected = ("regular_local_file_or_directory_required" if replacement == "fifo"
                else "unsafe_or_missing_local_path")
    assert code == expected and elapsed < 1.0
    assert not any(n.split(".")[0] in {"mlx", "mlx_lm", "numpy", "torch", "tokenizers",
                                       "safetensors", "transformers"} for n in sys.modules)
    print(json.dumps({"operation": operation, "replacement": replacement, "error": code,
                      "elapsed_seconds": elapsed, "same_directory_descriptor": True,
                      "framework_imports": 0, "real_model_files": 0, "status": "PASS"}))


if __name__ == "__main__":
    main()
