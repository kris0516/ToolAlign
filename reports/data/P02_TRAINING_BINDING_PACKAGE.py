"""Inspect real archives and exercise this wheel with existing pure CPU dependencies.

The existing dependency target is read only. -B -I -S suppresses bytecode writes,
site loading and source-cwd imports; only the newly installed wheel is selected.
"""

from __future__ import annotations

import argparse
import base64
import csv
import email.parser
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def installed(args):
    target, runtime = Path(args.target).resolve(), Path(args.runtime).resolve()
    sys.path[:0] = [str(target), str(runtime)]
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    from toolalign.data.common import DataError
    from toolalign.data.training_review import render_page, sequence_record
    from toolalign.data.training_selection import load_config, select_examples
    from toolalign.model_io import TEMPLATE_SHA256, training_sequence

    expected = json.loads(Path(args.expected).read_text())
    for name, digest in expected["package_files"].items():
        assert sha((target / name).read_bytes()) == digest
    config = load_config(expected["config_path"])
    examples, rows = expected["examples"], expected["audit_rows"]
    plan = select_examples({"train": examples, "validation": []}, rows, config)
    assert plan["smoke"]["train"]["summary"]["selected_count"] == 1
    assert plan["formal"]["train"]["summary"]["selected_count"] == 2
    assert plan == select_examples({"train": list(reversed(examples)), "validation": []}, list(reversed(rows)), config)
    rows[0]["source_record_hash"] = "f" * 64
    try:
        select_examples({"train": examples, "validation": []}, rows, config)
    except DataError:
        pass
    else:
        raise AssertionError("installed_selection_accepted_bad_identity")
    example = examples[0]
    sequence = training_sequence(example, renderer=lambda *a, **kw: "ORIGINAL_PROMPT",
        encoder=lambda text, **kw: [151645] if text == "<|im_end|>" else [ord(c) for c in text],
        decoder=lambda ids, **kw: "".join(chr(i) for i in ids),
        eos_token_id=151645, template_sha256=TEMPLATE_SHA256)
    case = {"case_id": "protocol-final", "category": "original_protocol_only", "example": example,
            "audit": None, "profiles": {}, "primary_profile": "smoke"}
    record = sequence_record(case, sequence)
    page = render_page(record, ["original"] * record["padding"]["bucket"])
    assert "<script>" not in page and record["padding"]["effective_supervised_targets"] == len(sequence.completion_text) + 1
    blocked = {"tokenizers", "transformers", "torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax"}
    assert all(importlib.util.find_spec(name) is None for name in blocked)
    assert not blocked & {name.split(".", 1)[0] for name in sys.modules}
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            assert Path(module.__file__).is_relative_to(target)
            origins[name] = sha(Path(module.__file__).read_bytes())
    result = {"status": "PASS", "original_small_examples": 3, "actual_Qwen_encoding": "NOT_RUN",
        "installed_source_files": len(expected["package_files"]), "module_origins": origins,
        "package_version": importlib.metadata.version("toolalign"), "optional_imports": [],
        "isolated": True, "no_site": True, "no_bytecode": True, "source_cwd_imports": 0}
    save(args.output, result)
    print(json.dumps(result))


def archives_and_install(args):
    root, archives, out = (Path(v).resolve() for v in (args.root, args.archives, args.output))
    assert out.is_relative_to(root / ".toolalign-local")
    out.mkdir(exist_ok=False)
    tracked = set(subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=root, text=True).splitlines())
    project = tomllib.loads((root / "pyproject.toml").read_text())
    includes = project["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    source_names = {p for p in tracked if any(p == i or p.startswith(i + "/") for i in includes)} | {".gitignore"}
    package_names = {p[4:] for p in tracked if p.startswith("src/toolalign/")}
    result = {"status": "PASS", "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(), "archives": {}}
    for name in source_names:
        assert (root / name).read_bytes() == subprocess.check_output(["git", "show", "HEAD:" + name], cwd=root)
    sdist = archives / "default/toolalign-0.0.1.tar.gz"
    with tarfile.open(sdist) as archive:
        members = archive.getmembers()
        assert len(members) == len({m.name for m in members})
        contents = {}
        for member in members:
            path = PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and ".." not in path.parts
            assert path.parts[0] == "toolalign-0.0.1"
            name = str(PurePosixPath(*path.parts[1:]))
            data = archive.extractfile(member).read()
            if name != "PKG-INFO":
                assert name in source_names and data == (root / name).read_bytes()
            contents[name] = data
        assert set(contents) == source_names | {"PKG-INFO"}
        pkg_info = email.parser.BytesParser().parsebytes(contents["PKG-INFO"])
        result["archives"]["sdist"] = {"sha256": sha(sdist.read_bytes()), "size_bytes": sdist.stat().st_size,
            "members": {n: sha(d) for n, d in contents.items()}}
    meta_prefix = "toolalign-0.0.1.dist-info/"
    expected_meta = {meta_prefix + n for n in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")}
    for label in ("default", "rebuilt"):
        wheel = archives / label / "toolalign-0.0.1-py3-none-any.whl"
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) and set(names) == package_names | expected_meta
            for info in archive.infolist():
                path = PurePosixPath(info.filename)
                assert not info.is_dir() and not path.is_absolute() and ".." not in path.parts
                assert (info.external_attr >> 16) & 0o170000 != 0o120000
                if info.filename in package_names:
                    assert archive.read(info.filename) == (root / "src" / info.filename).read_bytes()
            metadata = email.parser.BytesParser().parsebytes(archive.read(meta_prefix + "METADATA"))
            for key in ("Name", "Version", "Requires-Python", "Requires-Dist", "Provides-Extra", "License-Expression"):
                assert metadata.get_all(key) == pkg_info.get_all(key)
            assert metadata["Name"] == project["project"]["name"] and metadata["Version"] == project["project"]["version"]
            assert [v for v in metadata.get_all("Requires-Dist") if "extra ==" not in v] == ["jsonschema==4.26.0"]
            wheel_meta = archive.read(meta_prefix + "WHEEL").decode()
            assert "Root-Is-Purelib: true" in wheel_meta and "Tag: py3-none-any" in wheel_meta
            assert archive.read(meta_prefix + "licenses/LICENSE") == (root / "LICENSE").read_bytes()
            assert "toolalign = toolalign.cli:main" in archive.read(meta_prefix + "entry_points.txt").decode()
            records = list(csv.reader(io.StringIO(archive.read(meta_prefix + "RECORD").decode())))
            assert len(records) == len(names) and {r[0] for r in records} == set(names)
            for name, digest, size in records:
                if name == meta_prefix + "RECORD":
                    assert digest == size == ""
                else:
                    data = archive.read(name)
                    expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
                    assert digest == expected and size == str(len(data))
            result["archives"][label + "_wheel"] = {"sha256": sha(wheel.read_bytes()), "size_bytes": wheel.stat().st_size,
                "members": {n: sha(archive.read(n)) for n in names}, "record_verified": True, "metadata_verified": True}
    assert result["archives"]["default_wheel"]["sha256"] == result["archives"]["rebuilt_wheel"]["sha256"]
    result.update(default_wheel_origin="uv_default_build_from_same_sdist", direct_source_wheel="NOT_RUN")
    save(out / "archives.json", result)
    sys.path.insert(0, str(root / "tests/data"))
    from training_binding_cases import example, row
    original = [example("installed-a"), example("installed-b"), example("installed-c")]
    expected = {"package_files": {n: sha((root / "src" / n).read_bytes()) for n in package_names},
        "config_path": str(root / "configs/training-data.v1.json"), "examples": original,
        "audit_rows": [row(original[0], p=1280, c=255), row(original[1], p=1792, c=255), row(original[2], p=100, c=256)]}
    save(out / "expected.json", expected)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    commands = []

    def run(label, command):
        started = datetime.now(timezone.utc).isoformat()
        done = subprocess.run(command, cwd=out, env=environment, capture_output=True, timeout=60)
        for suffix, data in (("stdout", done.stdout), ("stderr", done.stderr)):
            with (out / (label + "." + suffix)).open("xb") as stream:
                stream.write(data)
        record = {"label": label, "argv": command, "started_at_utc": started,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(), "exit_code": done.returncode,
            "stdout_sha256": sha(done.stdout), "stderr_sha256": sha(done.stderr)}
        save(out / (label + ".command.json"), record)
        commands.append(record)
        assert done.returncode == 0, label

    target, runtime = out / "installed-wheel", Path(args.runtime).resolve()
    assert runtime.is_dir() and runtime != target
    run("install-default-wheel", ["uv", "pip", "install", "--offline", "--python", sys.executable,
        "--target", str(target), "--no-deps", str(archives / "default/toolalign-0.0.1-py3-none-any.whl")])
    run("installed-small-api", [sys.executable, "-B", "-I", "-S", str(Path(__file__).resolve()), "installed",
        "--target", str(target), "--runtime", str(runtime), "--expected", str(out / "expected.json"),
        "--output", str(out / "installed-api.json")])
    bootstrap = "import sys; sys.path[:0]=[sys.argv.pop(1),sys.argv.pop(1)]; from toolalign.data.training_selection import main; raise SystemExit(main())"
    base = [sys.executable, "-B", "-I", "-S", "-c", bootstrap, str(target), str(runtime)]
    run("installed-help", base + ["--help"])
    inputs = json.loads(Path(args.inputs).read_text())
    flags = [v for k, value in inputs.items() for v in ("--" + k.replace("_", "-"), value)]
    run("installed-verify-original-selection", base + ["verify", *flags, "--output", str(Path(args.selection).resolve())])
    summary = {"status": "PASS", "archives_sha256": sha((out / "archives.json").read_bytes()),
        "installed_api_sha256": sha((out / "installed-api.json").read_bytes()), "commands": commands,
        "new_environments": 0, "new_dependencies": 0, "existing_runtime_target": str(runtime),
        "default_wheel_installed": True, "source_cwd_imports": 0}
    save(out / "summary.json", summary)
    print(json.dumps({"status": "PASS", "summary_sha256": sha((out / "summary.json").read_bytes()),
        "commands": len(commands), "sdist_members": len(result["archives"]["sdist"]["members"]),
        "wheel_members": len(result["archives"]["default_wheel"]["members"])}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("verify")
    for key in ("root", "archives", "output", "runtime", "inputs", "selection"):
        command.add_argument("--" + key, required=True)
    command = sub.add_parser("installed")
    for key in ("target", "runtime", "expected", "output"):
        command.add_argument("--" + key, required=True)
    args = parser.parse_args()
    {"verify": archives_and_install, "installed": installed}[args.command](args)


if __name__ == "__main__":
    main()
