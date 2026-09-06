"""Read-only verification of R1's actual two processes, origins and named semaphores."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib.metadata
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from toolalign.runtime.gpu_lock import inspect_gpu_lock, lock_path


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("private", "t1", "header", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    private = args.private.resolve()
    inputs = json.loads((private / "inputs.json").read_text())
    repository = Path(inputs["repository"])
    target = private / "installed-wheel"
    runtime = Path(inputs["replay_python"]).parents[1] / "lib/python3.14/site-packages"
    expected_versions = {"mlx": "0.32.2", "mlx-lm": "0.31.3", "numpy": "2.5.2", "psutil": "7.2.2", "torch": "2.14.0"}
    versions = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions(path=[str(runtime)])
                if d.metadata["Name"] in expected_versions}
    assert versions == expected_versions
    hashed = {}

    def sha(path):
        path = Path(path)
        if str(path) not in hashed:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            hashed[str(path)] = digest.hexdigest()
        return hashed[str(path)]

    records = []
    launches = sorted((private / "r1-framework-launches").glob("launch-*.json"))
    assert len(launches) == 2
    for index, file in enumerate(launches, 1):
        registration = json.loads(file.read_text())
        run = Path(registration["output"])

        def read(name):
            return json.loads((run / name).read_text())

        assert run.parent == private and read("preregistration.json") == registration
        result, supervision, lease = read("result.json"), read("supervision.json"), read("lease-acquired.json")
        terminal, origins, wrapper = read("child-terminal.json"), read("all-module-origins.json"), read("wrapper-terminal.json")
        assert registration["launch_number"] == index and registration["launch_limit"] == 2
        assert registration["limits"]["review_framework_launches_max"] == 2
        assert registration["candidate"] == "f7326d1823c4cf132ae44525f4755c96c88ec159"
        assert registration["review_authorization"] == inputs["review_authorization"]
        assert registration["review_task"] == lease["review_task"] == "P04-SFT-NATIVE-TOY-R1"
        assert sha(inputs["config"]) == result["config_sha256"] == registration["config_sha256"]
        assert sha(inputs["cases"]) == result["original_cases_sha256"] == registration["cases_sha256"]
        assert result["consumer_identity"] == registration["consumer_identity"]
        assert canonical(result["consumer_identity"]) == registration["consumer_sha256"]
        for name, digest in result["consumer_identity"]["sft"].items():
            assert sha(target / "toolalign/training/sft" / name) == digest
        for name, digest in result["consumer_identity"]["support"].items():
            assert sha(target / "toolalign" / name) == digest
        assert result["environment"] == registration["environment"] == read("environment-before-import.json")
        assert result["environment"]["versions"] == versions
        for name, digest in result["environment"]["upstream_sources"].items():
            assert sha(runtime / "mlx_lm/tuner" / (name + ".py")) == digest
        assert lease["numerical_modules_before_import"] == registration["parent_numerical_modules"] == []
        owner = lease["actual_lock"]["owner"]
        assert lease["actual_lock"]["held"] is True and owner["pid"] == supervision["pid"] == terminal["pid"]
        assert owner["worker_alias"] == "R1" and owner["task_id"] == "P04-SFT-NATIVE-TOY"
        assert owner["process_started_at"] == lease["process_started_at"]
        assert lease["lock_path"] == str(lock_path(repository))
        current = lock_path(repository).stat()
        assert (lease["fd_device"], lease["fd_inode"]) == (current.st_dev, current.st_ino)
        assert origins["lease_after_numerics"]["held"] is True and origins["lease_after_numerics"]["owner"] == owner
        assert terminal["lease_held_until_process_exit"] is True and origins["framework_loaded_under_lease"] is True
        assert supervision["actual_child_exit"] == supervision["exit_code"] == terminal["exit_code"] == wrapper["exit_code"] == 0
        assert supervision["diagnostic_errors"] == [] and supervision["error"] is None
        assert supervision["own_process_reaped"] is True and supervision["own_pid_exists"] is False
        assert not supervision["lock_after"]["held"] and not wrapper["lock_after"]["held"]
        try:
            os.kill(supervision["pid"], 0)
        except ProcessLookupError:
            absent = True
        else:
            raise AssertionError("recorded framework child PID is still present")
        assert supervision["consumer_unchanged"] is True and wrapper["wrapper_unchanged"] is True
        assert 0 < supervision["wall_seconds"] <= 300 and 0 < supervision["peak_rss_bytes"] <= 4 * 1024**3
        assert supervision["peak_rss_bytes"] == max(row["rss_bytes"] for row in supervision["samples"])
        assert 0 < supervision["private_disk_bytes"] < 2 * 1024**3
        for stream in ("stdout", "stderr"):
            assert sha(run / (stream + ".log")) == supervision[stream + "_sha256"]
        assert result["device"]["mlx_default"] == result["device"]["mlx_execution_stream"] == "Device(gpu, 0)"
        assert result["device"]["torch"] == "cpu"
        assert result["device"]["torch_intra_threads"] == result["device"]["torch_inter_threads"] == 2
        peak = max(item["mlx_peak_bytes"] for item in result["memory"])
        assert peak <= 1024**3
        wired = read("wired-limit-and-compile.json")
        assert wired["setter_restored"] is True and wired["compile_preserved"] is True
        assert wired["events"]
        for group in (registration["parent_origins"], result["origins"]):
            assert all(Path(value["path"]).is_relative_to(target) for value in group.values())
            assert all(sha(value["path"]) == value["sha256"] for value in group.values())
        for name, value in origins["modules"].items():
            assert sha(value["path"]) == value["sha256"], name
            if name == "toolalign" or name.startswith("toolalign."):
                assert Path(value["path"]).is_relative_to(target)
        assert registration["wrapper_sha256"] == terminal["wrapper_sha256"] == wrapper["wrapper_sha256"] == origins["wrapper_sha256"]
        assert sha(origins["modules"]["__main__"]["path"]) == registration["wrapper_sha256"]
        assert result["actual_model_parameters"] == 64 and result["unique_original_examples"] == 13
        assert result["actual_vocabulary"] == 8 and result["actual_largest_sequence"] == 16
        assert result["independent_reference_optimizer_updates"] == 2 and result["training_authorized"] is False
        assert result["status"] == ("PASS" if index == 1 else "EXPECTED_NEGATIVE")
        assert result["actual_optimizer_updates"] == (2 if index == 1 else 1)
        records.append({"mode": registration["mode"], "status": result["status"], "pid": supervision["pid"],
            "current_pid_absent": absent, "wall_seconds": supervision["wall_seconds"], "peak_rss_bytes": supervision["peak_rss_bytes"],
            "mlx_peak_bytes": peak, "all_module_origins": len(origins["modules"]),
            "toolalign_origins": len(result["origins"]), "supervision_sha256": sha(run / "supervision.json"),
            "registration_sha256": sha(file), "result_sha256": sha(run / "result.json"),
            "all_origins_sha256": sha(run / "all-module-origins.json")})
    # Only the exact historical/own names in retained stderr. No creation,
    # unlink, enumeration of unrelated semaphores, or global leak claim.
    header = args.header.read_text()
    assert "#define SEM_FAILED ((sem_t *)-1)" in header
    library = ctypes.CDLL(None, use_errno=True)
    library.sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int]
    library.sem_open.restype = ctypes.c_void_p
    library.sem_close.argtypes = [ctypes.c_void_p]
    library.sem_close.restype = ctypes.c_int
    sentinel = ctypes.c_void_p(-1).value
    semaphores = []
    warning_runs = [args.t1 / "source-segmented-r2", args.t1 / "installed-segmented-r1",
                    private / "framework-installed-segmented-r1", private / "framework-tail-negative-r1"]
    for run in warning_runs:
        for name in sorted(set(re.findall(r"/mp-[A-Za-z0-9_-]+", (run / "stderr.log").read_text()))):
            ctypes.set_errno(0)
            handle = library.sem_open(name.encode(), 0)
            number = ctypes.get_errno()
            close = None if handle == sentinel else library.sem_close(handle)
            absent = handle == sentinel and number == errno.ENOENT
            semaphores.append({"run": str(run), "exact_name": name, "raw_return": handle, "errno": number,
                "flags": 0, "sem_close_return": close, "absent": absent, "created": False, "unlinked": False,
                "checked_at": datetime.now(timezone.utc).isoformat()})
    assert len(semaphores) == 3 and all(row["absent"] for row in semaphores)
    assert not inspect_gpu_lock(repository)["held"]
    result = {"status": "PASS", "framework_launches": 2, "framework_launch_limit": 2, "runs": records,
              "versions": versions, "files_hash_verified": hashed, "named_semaphores": semaphores,
              "semaphore_scope": "exact two historical and one own warning names only; not a global leak audit",
              "defining_sdk_header_sha256": sha(args.header), "current_lock": inspect_gpu_lock(repository),
              "audit_script_sha256": sha(__file__), "new_framework_launches_in_this_audit": 0}
    with args.output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "runs": records, "exact_absent_semaphores": len(semaphores),
                      "files_hash_verified": len(hashed), "new_framework_launches": 0}))


if __name__ == "__main__":
    main()
