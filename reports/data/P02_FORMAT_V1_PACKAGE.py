"""Verify actual archives and an isolated default CPU target installation.

Use an existing Python and offline uv cache. The installation creates a new
private target directory, not a tokenizer environment; child checks use -I -S
and only that target plus the standard library. No model packages are installed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def check_installed(target, expected_file, output):
    target = Path(target).resolve()
    sys.path.insert(0, str(target))
    from importlib.resources import files

    import toolalign
    from toolalign.contracts import canonical_hash, contract_digest, validate_record
    from toolalign.model_io import (
        encode_action,
        format_descriptor,
        format_identity,
        pad_sequence,
        prompt_messages,
        training_sequence,
        validate_model_input,
    )
    from toolalign.tools._json import parse_action

    expected = json.loads(Path(expected_file).read_text())
    assert sys.flags.isolated and sys.flags.no_site
    assert Path(toolalign.__file__).is_relative_to(target)
    for relative, digest in expected["package_files"].items():
        assert sha((target / relative).read_bytes()) == digest
    descriptor_bytes = files("toolalign.model_io").joinpath("descriptor.v1.json").read_bytes()
    assert sha(descriptor_bytes) == expected["descriptor_sha256"]
    assert format_identity()["descriptor_sha256"] == expected["descriptor_sha256"]
    assert contract_digest() == expected["contract_sha256"]
    descriptor = format_descriptor()

    def encode(text, *, add_special_tokens):
        assert add_special_tokens is False
        return [1] if text == "<|im_end|>" else [ord(c) + 10 for c in text]

    def decode(ids, *, skip_special_tokens):
        assert skip_special_tokens is False
        return "".join(chr(i - 10) for i in ids)

    def render(messages, *, tools, add_generation_prompt, enable_thinking):
        assert tools is None and add_generation_prompt is True and enable_thinking is False
        assert set(messages[0]) == {"role", "content"}
        return "TEST_PROMPT"

    checks = []
    for fixture in expected["fixtures"]:
        example = fixture["example"]
        before = canonical_hash(example)
        assert validate_record(example) == example
        model_input = {"messages": example["messages"], "tools": example["tools"]}
        assert validate_model_input(model_input) == model_input
        messages = prompt_messages(model_input)
        catalog = json.loads(messages[0]["content"][len(descriptor["instruction"]) + 1:])
        original = [json.loads(item["content"])["message"] for item in messages[1:]]
        assert canonical_hash({"messages": original, "tools": catalog["tools"]}) == canonical_hash(model_input)
        raw = encode_action(example["expected_action"])
        assert canonical_hash(parse_action(raw)) == canonical_hash(example["expected_action"])
        assert raw == fixture["actual_tokenizer_completion"]
        sequence = training_sequence(example, renderer=render, encoder=encode, decoder=decode,
            eos_token_id=1, template_sha256=expected["template_sha256"])
        p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
        assert sequence.causal_target_ids[p - 1] == ord("{") + 10
        assert sequence.causal_target_ids[-1] == 1
        assert sequence.loss_mask == tuple([0] * p + [1] * (n - p))
        assert sum(sequence.causal_loss_mask) == n - p
        assert pad_sequence(sequence, length=n + 3, pad_token_id=1).loss_mask[-3:] == (0, 0, 0)
        assert canonical_hash(example) == before
        checks.append({"name": fixture["name"], "action_sha256": canonical_hash(example["expected_action"])})
    blocked = ("tokenizers", "transformers", "torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax")
    assert all(importlib.util.find_spec(name) is None for name in blocked)
    assert not set(blocked) & {name.split(".", 1)[0] for name in sys.modules}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            assert Path(module.__file__).is_relative_to(target)
    packages = {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions(path=[str(target)])}
    result = {
        "status": "PASS", "python_isolated": bool(sys.flags.isolated), "python_no_site": bool(sys.flags.no_site),
        "package_source_files_verified": len(expected["package_files"]),
        "fixture_checks": checks, "packages": packages,
        "sequence_callback_kind": "transparent_character_test_double_not_Qwen",
        "installed_raw_parser_roundtrips": len(checks), "source_imports": 0,
        "optional_and_model_packages_importable": [],
    }
    dump(output, result)
    print(json.dumps(result, ensure_ascii=False))


def verify(root, archive_root, out):
    root, archive_root, out = (Path(p).resolve() for p in (root, archive_root, out))
    assert out.is_relative_to(root / ".toolalign-local")
    out.mkdir(exist_ok=False)
    tracked = set(subprocess.check_output(["git", "ls-files", "-z"], cwd=root, text=True).split("\0")) - {""}
    config = tomllib.loads((root / "pyproject.toml").read_text())
    included = config["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    source_expected = {name for name in tracked if any(name == prefix or name.startswith(prefix + "/") for prefix in included)}
    # The actual Hatchling sdist also includes this tracked VCS file. Verify its
    # exact repository bytes; do not generalize this exception to other payloads.
    assert ".gitignore" in tracked
    source_expected.add(".gitignore")
    package_expected = {name[4:] for name in tracked if name.startswith("src/toolalign/")}
    sdist = archive_root / "default/toolalign-0.0.1.tar.gz"
    result = {"status": "PASS", "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(), "archives": {}}
    with tarfile.open(sdist) as archive:
        names = [m.name for m in archive.getmembers()]
        assert len(names) == len(set(names))
        payload = {}
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and ".." not in path.parts
            assert path.parts[0] == "toolalign-0.0.1"
            name = str(PurePosixPath(*path.parts[1:]))
            data = archive.extractfile(member).read()
            payload[name] = sha(data)
            if name != "PKG-INFO":
                assert name in source_expected and data == (root / name).read_bytes()
        assert set(payload) == source_expected | {"PKG-INFO"}
        result["archives"]["sdist"] = {"sha256": sha(sdist.read_bytes()), "bytes": sdist.stat().st_size, "members": payload}
    metadata = {"toolalign-0.0.1.dist-info/" + name for name in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")}
    for label in ("default", "rebuilt"):
        wheel = archive_root / label / "toolalign-0.0.1-py3-none-any.whl"
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) and set(names) == package_expected | metadata
            for info in archive.infolist():
                assert not info.is_dir() and (info.external_attr >> 16) & 0o170000 != 0o120000
                assert not PurePosixPath(info.filename).is_absolute() and ".." not in PurePosixPath(info.filename).parts
                if info.filename in package_expected:
                    assert archive.read(info.filename) == (root / "src" / info.filename).read_bytes()
            result["archives"][label + "_wheel"] = {"sha256": sha(wheel.read_bytes()), "bytes": wheel.stat().st_size,
                "members": {name: sha(archive.read(name)) for name in names}}
    assert result["archives"]["default_wheel"]["sha256"] == result["archives"]["rebuilt_wheel"]["sha256"]
    result["default_wheel_origin"] = "built_by_uv_from_same_sdist"
    result["direct_source_wheel"] = "NOT_RUN"
    result["new_package_files"] = sorted(name for name in package_expected if name.startswith("toolalign/model_io/"))
    result["untracked_missing_or_different_members"] = 0
    dump(out / "archives.json", result)

    sys.path.insert(0, str(root / "tests/model_io"))
    from model_io_cases import cases

    real = json.loads((root / ".toolalign-local/format-v1-r2/fixtures-native-r1/result.json").read_text())
    real_rows = {row["name"]: row for row in real["models"]["Qwen/Qwen3-0.6B"]["rows"]}
    descriptor = json.loads((root / "configs/model_io.action-json.v1.json").read_text())
    expected = {"package_files": {name: sha((root / "src" / name).read_bytes()) for name in package_expected},
        "descriptor_sha256": sha((root / "configs/model_io.action-json.v1.json").read_bytes()),
        "template_sha256": descriptor["template"]["utf8_sha256"], "contract_sha256": descriptor["contract_schema_sha256"],
        "fixtures": [{"name": name, "example": example, "actual_tokenizer_completion": real_rows[name]["completion_text"]} for name, example in cases()]}
    dump(out / "expected.json", expected)
    commands = []
    clean_env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME"):
        clean_env.pop(key, None)

    def run(label, args, cwd):
        done = subprocess.run(args, cwd=cwd, env=clean_env, capture_output=True, timeout=60)
        for kind, data in (("stdout", done.stdout), ("stderr", done.stderr)):
            (out / f"{label}.{kind}").write_bytes(data)
        commands.append({"label": label, "argv": args, "exit_code": done.returncode,
            "stdout_sha256": sha(done.stdout), "stderr_sha256": sha(done.stderr)})
        dump(out / f"{label}.command.json", commands[-1])
        if done.returncode:
            print(done.stdout.decode() + done.stderr.decode(), flush=True)
            raise RuntimeError(label + "_failed")
        return done.stdout.decode()

    target = out / "site-packages"
    run("export", ["uv", "export", "--offline", "--locked", "--no-dev", "--no-emit-project", "--output-file", str(out / "runtime.txt")], root)
    run("default-dependencies", ["uv", "pip", "install", "--offline", "--python", sys.executable, "--target", str(target), "--require-hashes", "-r", str(out / "runtime.txt")], root)
    wheel = archive_root / "rebuilt/toolalign-0.0.1-py3-none-any.whl"
    run("wheel-install", ["uv", "pip", "install", "--offline", "--python", sys.executable, "--target", str(target), "--no-deps", str(wheel)], root)
    with tempfile.TemporaryDirectory(prefix="toolalign-format-installed-") as temp:
        copied_probe = Path(temp) / "probe.py"
        shutil.copyfile(__file__, copied_probe)
        run("installed-api", [sys.executable, "-I", "-S", str(copied_probe), "--check-installed", str(target), "--expected", str(out / "expected.json"), "--out", str(out / "installed-api.json")], temp)
        bootstrap = "import sys; sys.path.insert(0, sys.argv.pop(1)); from toolalign.cli import main; main()"
        command = [sys.executable, "-I", "-S", "-c", bootstrap, str(target)]
        assert run("contract-digest", command + ["contract-digest"], temp).strip() == expected["contract_sha256"]
        for kind in ("example", "tool", "preference", "run", "trace"):
            text = run("validate-" + kind, command + ["validate", str(root / "tests/fixtures/contracts" / (kind + ".json"))], temp)
            assert "VALID: 1 record(s)" in text
    installed = json.loads((out / "installed-api.json").read_text())
    summary = {"status": "PASS", "commands": commands, "default_cpu_target_installation": True,
        "new_tokenizer_environments": 0, "isolated_default_interface": installed,
        "archives_sha256": sha((out / "archives.json").read_bytes()), "probe_sha256": sha(Path(__file__).read_bytes()),
        "lockfile_sha256": sha((root / "uv.lock").read_bytes()), "runtime_requirements_sha256": sha((out / "runtime.txt").read_bytes())}
    dump(out / "summary.json", summary)
    print(json.dumps({"status": "PASS", "commands_passed": len(commands), "sdist_members": len(result["archives"]["sdist"]["members"]),
        "wheel_members": len(result["archives"]["default_wheel"]["members"]), "installed_source_files": len(package_expected),
        "summary_sha256": sha((out / "summary.json").read_bytes())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    parser.add_argument("--archives")
    parser.add_argument("--out", required=True)
    parser.add_argument("--check-installed")
    parser.add_argument("--expected")
    arguments = parser.parse_args()
    if arguments.check_installed:
        check_installed(arguments.check_installed, arguments.expected, arguments.out)
    else:
        verify(arguments.root, arguments.archives, arguments.out)
