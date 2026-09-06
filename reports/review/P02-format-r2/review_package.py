"""Fresh r2 archive/install verification, derived from the preserved R1 helper.

Only this new attachment targets the fixed candidate; the original is unchanged.
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

CANDIDATE = "8c439f683b9d6b04919ff1f7184d8924ccf82f9f"
BLOCKED = {"tokenizers", "transformers", "torch", "mlx", "mlx_lm", "tensorflow", "flax", "jax"}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def dump(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def check_installed(args):
    assert sys.flags.isolated and sys.flags.no_site
    target = args.target.resolve()
    sys.path.insert(0, str(target))
    expected = json.loads(args.expected.read_text())
    for name, digest in expected["package"].items():
        assert sha((target / name).read_bytes()) == digest
    assert all(importlib.util.find_spec(name) is None for name in BLOCKED)
    from importlib.resources import files

    from toolalign.contracts import canonical_hash, contract_digest
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

    descriptor = format_descriptor()
    assert sha(files("toolalign.model_io").joinpath("descriptor.v1.json").read_bytes()) == expected["descriptor"]
    assert format_identity()["descriptor_sha256"] == expected["descriptor"]
    assert contract_digest() == expected["contract"]

    def wire(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e")

    def render(messages, **flags):
        assert flags == {"tools": None, "enable_thinking": False, "add_generation_prompt": True}
        assert all(set(item) == {"role", "content"} for item in messages)
        return "PACKAGE_REVIEW_PREFIX\n"

    def encode(text, *, add_special_tokens):
        assert add_special_tokens is False
        return [2] if text == "<|im_end|>" else [ord(c) + 10 for c in text]

    def decode(ids, *, skip_special_tokens):
        assert skip_special_tokens is False
        return "".join(chr(i - 10) for i in ids)

    checked = []
    for case in expected["fixtures"]:
        example = case["example"]
        original = canonical_hash(example)
        model_input = {k: example[k] for k in ("messages", "tools")}
        copied = validate_model_input(model_input)
        assert copied == model_input and copied is not model_input
        projected = prompt_messages(model_input)
        assert projected[0] == {"role": "system", "content": descriptor["instruction"] + "\n" + wire({"format_version": descriptor["format_id"], "tools": model_input["tools"]})}
        for i, message in enumerate(model_input["messages"]):
            assert projected[i + 1] == {"role": message["role"], "content": wire({"message": message, "message_index": i})}
        raw = encode_action(example["expected_action"])
        assert raw == wire(example["expected_action"]) == case["qwen_verified_completion"]
        assert parse_action(raw) == example["expected_action"]
        sequence = training_sequence(example, renderer=render, encoder=encode, decoder=decode,
                                     eos_token_id=2, template_sha256=expected["template"])
        p, n = len(sequence.prompt_ids), len(sequence.sequence_ids)
        joined = encode(sequence.prompt_text + raw, add_special_tokens=False)
        assert list(sequence.sequence_ids) == joined + [2]
        assert list(sequence.loss_mask) == [0] * p + [1] * (n - p)
        assert sequence.causal_target_ids[p - 1] == ord("{") + 10 and sequence.causal_target_ids[-1] == 2
        assert sequence.causal_loss_mask == sequence.loss_mask[1:]
        pad = pad_sequence(sequence, length=n + 4, pad_token_id=2)
        assert pad.loss_mask == sequence.loss_mask + (0,) * 4
        assert pad.attention_mask == (1,) * n + (0,) * 4
        assert canonical_hash(example) == original
        checked.append(case["name"])
    imported = {}
    for name, module in tuple(sys.modules.items()):
        if name == "toolalign" or name.startswith("toolalign."):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(target)
            imported[name] = str(path.relative_to(target))
    assert not BLOCKED & {name.split(".")[0] for name in sys.modules}
    packages = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions(path=[str(target)])}
    assert set(n.lower().replace("_", "-") for n in packages) == {"toolalign", "jsonschema", "attrs", "jsonschema-specifications", "referencing", "rpds-py"}
    result = {"status": "PASS", "isolated_no_site": True, "packages": packages,
              "source_files": len(expected["package"]), "fixture_names": checked,
              "imported_package_paths": imported, "source_tree_imports": 0,
              "optional_or_model_imports": [], "sequence_callback_kind": "character_interface_double_not_Qwen"}
    dump(args.out, result)
    print(json.dumps(result))


def verify(args):
    root, out, archives = args.root.resolve(), args.out.resolve(), args.archives.resolve()
    out.mkdir(exist_ok=False)
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == CANDIDATE
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", CANDIDATE], cwd=root, text=True).splitlines()
    payload = {name: subprocess.check_output(["git", "show", CANDIDATE + ":" + name], cwd=root) for name in names}
    config = tomllib.loads(payload["pyproject.toml"].decode())
    include = config["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    sdist_names = {name for name in names if any(name == entry or name.startswith(entry + "/") for entry in include)} | {".gitignore"}
    package = {name.removeprefix("src/"): data for name, data in payload.items() if name.startswith("src/toolalign/")}
    metadata = {"toolalign-0.0.1.dist-info/" + n for n in ("METADATA", "WHEEL", "entry_points.txt", "licenses/LICENSE", "RECORD")}
    results = {}
    for label, archive in (("sdist", archives / "default/toolalign-0.0.1.tar.gz"),
                           ("default_wheel", archives / "default/toolalign-0.0.1-py3-none-any.whl"),
                           ("rebuilt_wheel", archives / "rebuilt/toolalign-0.0.1-py3-none-any.whl")):
        contents = {}
        if label == "sdist":
            with tarfile.open(archive) as tf:
                for member in tf.getmembers():
                    name = PurePosixPath(member.name)
                    assert member.isfile() and not name.is_absolute() and ".." not in name.parts
                    assert name.parts[0] == "toolalign-0.0.1"
                    short = str(PurePosixPath(*name.parts[1:]))
                    assert short not in contents
                    contents[short] = tf.extractfile(member).read()
            assert set(contents) == sdist_names | {"PKG-INFO"}
            for name in sdist_names:
                assert contents[name] == payload[name], name
        else:
            with zipfile.ZipFile(archive) as zf:
                for item in zf.infolist():
                    name = PurePosixPath(item.filename)
                    assert not item.is_dir() and not name.is_absolute() and ".." not in name.parts
                    assert (item.external_attr >> 16) & 0o170000 != 0o120000
                    assert item.filename not in contents
                    contents[item.filename] = zf.read(item.filename)
            assert set(contents) == set(package) | metadata
            assert all(contents[name] == data for name, data in package.items())
        results[label] = {"sha256": sha(archive.read_bytes()), "size_bytes": archive.stat().st_size,
                          "member_count": len(contents), "members": {k: sha(v) for k, v in contents.items()}}
    assert results["default_wheel"]["sha256"] == results["rebuilt_wheel"]["sha256"]
    dump(out / "archives.json", results)
    sys.path.insert(0, str(root / "tests/model_io"))
    from model_io_cases import cases

    real = json.loads(args.fixtures.read_text())["models"]["Qwen/Qwen3-0.6B"]["rows"]
    real = {row["name"]: row["actual"]["completion_text"] for row in real}
    descriptor = json.loads(payload["configs/model_io.action-json.v1.json"])
    expected = {"package": {k: sha(v) for k, v in package.items()},
                "descriptor": sha(payload["configs/model_io.action-json.v1.json"]),
                "contract": descriptor["contract_schema_sha256"], "template": descriptor["template"]["utf8_sha256"],
                "fixtures": [{"name": name, "example": example, "qwen_verified_completion": real[name]} for name, example in cases()]}
    expected_file = out / "expected.json"
    dump(expected_file, expected)
    commands = []
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}

    def run(name, command, cwd=root):
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=60)
        (out / (name + ".stdout")).write_bytes(result.stdout)
        (out / (name + ".stderr")).write_bytes(result.stderr)
        record = {"name": name, "command": list(map(str, command)), "exit_code": result.returncode,
                  "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr)}
        commands.append(record)
        dump(out / (name + ".command.json"), record)
        assert result.returncode == 0, (name, result.stdout.decode(errors="replace"), result.stderr.decode(errors="replace"))
        return result.stdout.decode()

    runtime = out / "runtime.txt"
    target = out / "site-packages"
    run("export", ["uv", "export", "--offline", "--locked", "--no-dev", "--no-emit-project", "--output-file", str(runtime)])
    run("dependencies", ["uv", "pip", "install", "--offline", "--python", sys.executable, "--target", str(target), "--require-hashes", "-r", str(runtime)])
    run("default-wheel-install", ["uv", "pip", "install", "--offline", "--python", sys.executable, "--target", str(target), "--no-deps", str(archives / "default/toolalign-0.0.1-py3-none-any.whl")])
    with tempfile.TemporaryDirectory(prefix="toolalign-r1-format-installed-") as temp:
        probe = Path(temp) / "probe.py"
        shutil.copyfile(__file__, probe)
        run("installed-api", [sys.executable, "-I", "-S", str(probe), "--installed", "--target", str(target), "--expected", str(expected_file), "--out", str(out / "installed-api.json")], temp)
        bootstrap = "import sys; sys.path.insert(0,sys.argv.pop(1)); from toolalign.cli import main; main()"
        cmd = [sys.executable, "-I", "-S", "-c", bootstrap, str(target)]
        assert run("digest", cmd + ["contract-digest"], temp).strip() == expected["contract"]
        for kind in ("example", "tool", "preference", "run", "trace"):
            text = run("validate-" + kind, cmd + ["validate", str(root / "tests/fixtures/contracts" / (kind + ".json"))], temp)
            assert "VALID: 1 record(s)" in text
    result = {"status": "PASS", "candidate": CANDIDATE, "commands": commands,
              "archives": {k: {field: value for field, value in v.items() if field != "members"} for k, v in results.items()},
              "archive_manifest_sha256": sha((out / "archives.json").read_bytes()),
              "default_wheel_origin": "uv default build from same sdist", "installed_wheel": "default",
              "direct_source_wheel": "NOT_RUN", "installed": json.loads((out / "installed-api.json").read_text())}
    dump(out / "result.json", result)
    print(json.dumps({"status": "PASS", "commands": len(commands), "archives": result["archives"], "installed_source_files": len(package)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed", action="store_true")
    for name in ("root", "archives", "fixtures", "target", "expected", "out"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.installed:
        check_installed(args)
    else:
        verify(args)
