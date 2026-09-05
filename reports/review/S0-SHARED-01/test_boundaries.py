"""CPU review probes for packaging and policy compatibility, not a D1 normalizer."""

import copy
import email
import hashlib
import json
import subprocess
import tomllib
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import pytest
from packaging.markers import Marker, default_environment
from packaging.requirements import Requirement

from toolalign.contracts import ContractError, schema_for, validate_record, validate_tool_arguments

ROOT = Path(__file__).resolve().parents[3]
BASE = "4cfbe1a5b8d93c20d7b11ec14b31757a574d0903"
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())
LOCK = tomllib.loads((ROOT / "uv.lock").read_text())
POLICY = json.loads((ROOT / "configs/source_toolace.v1.json").read_text())
PINS = {"mlx": "0.32.2", "mlx-lm": "0.31.3", "torch": "2.14.0", "psutil": "7.2.2"}


def enabled(marker, environment):
    return not marker or Marker(marker).evaluate(environment)


def lock_closure(environment, extra):
    pending = [{"name": "toolalign"}]
    selected = {}
    while pending:
        dependency = pending.pop()
        if not enabled(dependency.get("marker"), environment):
            continue
        if dependency["name"] in selected:
            continue
        candidates = [p for p in LOCK["package"] if p["name"] == dependency["name"]]
        if "version" in dependency:
            candidates = [p for p in candidates if p["version"] == dependency["version"]]
        candidates = [p for p in candidates if not p.get("resolution-markers") or any(
            enabled(marker, environment) for marker in p["resolution-markers"]
        )]
        assert len(candidates) == 1
        package = candidates[0]
        selected[package["name"]] = package["version"]
        pending.extend(package.get("dependencies", []))
        if package["name"] == "toolalign":
            pending.extend(package["dev-dependencies"]["dev"])
            if extra:
                pending.extend(package["optional-dependencies"][extra])
    return selected


@pytest.mark.parametrize("python", ["3.11", "3.12", "3.13", "3.14"])
@pytest.mark.parametrize("platform,machine", [
    ("darwin", "arm64"), ("darwin", "x86_64"), ("linux", "x86_64"),
    ("linux", "aarch64"), ("win32", "AMD64"),
])
@pytest.mark.parametrize("extra", ["", "compatibility"])
def test_markers_and_transitive_lock_respect_platform_and_opt_in(python, platform, machine, extra):
    env = {**default_environment(), "python_version": python, "python_full_version": python + ".0",
           "sys_platform": platform, "platform_machine": machine, "extra": extra,
           "platform_system": {"darwin": "Darwin", "linux": "Linux", "win32": "Windows"}[platform]}
    optional = [Requirement(r) for r in PROJECT["project"]["optional-dependencies"]["compatibility"]]
    direct = {r.name for r in optional if extra and (not r.marker or r.marker.evaluate(env))}
    expected = set() if not extra else (set(PINS) if (platform, machine) == ("darwin", "arm64") else {"psutil"})
    assert direct == expected
    closure = lock_closure(env, extra)
    assert set(closure) & set(PINS) == expected
    assert ("mlx-metal" in closure) == ("mlx" in expected)
    assert not any(name.startswith(("nvidia", "cuda", "mlx-cuda")) or name == "triton" for name in closure)
    if "mlx" in expected:
        assert closure["numpy"] == ("2.4.6" if python == "3.11" else "2.5.2")


def test_only_four_pins_and_existing_cpu_lock_unchanged():
    assert PROJECT["project"]["dependencies"] == ["jsonschema==4.26.0"]
    extras = PROJECT["project"]["optional-dependencies"]
    assert set(extras) == {"compatibility"}
    requirements = [Requirement(value) for value in extras["compatibility"]]
    assert len(requirements) == 4
    assert {r.name: str(r.specifier) for r in requirements} == {k: "==" + v for k, v in PINS.items()}
    old = tomllib.loads(subprocess.check_output(["git", "show", BASE + ":uv.lock"], cwd=ROOT).decode())
    current = {(p["name"], p["version"]): p for p in LOCK["package"]}
    for package in old["package"]:
        if package["name"] != "toolalign":
            assert current[(package["name"], package["version"])] == package
    assert "mlx-tune" not in {p["name"] for p in LOCK["package"]}


def test_all_registry_artifacts_have_official_source_and_hash():
    for package in LOCK["package"]:
        if package["name"] == "toolalign":
            assert package["source"] == {"editable": "."}
            continue
        assert package["source"] == {"registry": "https://pypi.org/simple"}
        for artifact in package.get("wheels", []) + ([package["sdist"]] if "sdist" in package else []):
            parsed = urlparse(artifact["url"])
            assert parsed.scheme == "https" and parsed.hostname == "files.pythonhosted.org"
            assert artifact["hash"].startswith("sha256:") and len(artifact["hash"]) == 71


def test_built_wheel_keeps_extras_optional_and_frozen_schema():
    (wheel,) = (ROOT / "dist").glob("toolalign-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        (name,) = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        metadata = email.message_from_bytes(archive.read(name))
        assert metadata.get_all("Provides-Extra") == ["compatibility"]
        requirements = [Requirement(value) for value in metadata.get_all("Requires-Dist")]
        assert len(requirements) == 5
        for requirement in requirements:
            if requirement.name == "jsonschema":
                assert requirement.marker is None
            else:
                assert requirement.name in PINS
                assert not requirement.marker.evaluate({**default_environment(), "extra": ""})
        assert hashlib.sha256(archive.read("toolalign/contracts/v1.json")).hexdigest() == (
            hashlib.sha256((ROOT / "src/toolalign/contracts/v1.json").read_bytes()).hexdigest()
        )


def tool_with(node, required=True):
    tool = json.loads((ROOT / "tests/fixtures/contracts/tool.json").read_text())
    tool.update(name="ta_synthetic_" + "a" * 12, side_effect_class=POLICY["wire_side_effect_class"],
                timeout_ms=POLICY["wire_timeout_ms"])
    tool["parameters_json_schema"] = {
        "type": "object", "properties": {"value": node},
        "required": ["value"] if required else [],
        "additionalProperties": POLICY["missing_object_additional_properties"],
    }
    return tool


def test_policy_envelope_fits_frozen_contract_without_execution_claim():
    assert POLICY["record_scope"] == "historical_supervision_only"
    assert POLICY["execution_binding"] == "none" and POLICY["original_side_effect_class"] == "unknown"
    assert POLICY["execution_registration_from_dataset"] == "forbidden"
    assert POLICY["wire_side_effect_class"] == "sandbox_only"
    max_name = "ta_" + "a" * POLICY["tool_name_slug_max_length"] + "_" + "a" * POLICY["tool_name_hash_length"]
    tool = tool_with({"type": "string", "maxLength": POLICY["missing_string_max_length"]})
    tool["name"] = max_name
    validate_record(tool)
    assert len(max_name) == 63
    assert schema_for("tool")["$defs"]["tool"]["additionalProperties"] is False


@pytest.mark.parametrize("keyword,value", [
    ("pattern", "^[a-z]+$"), ("format", "date-time"), ("examples", ["synthetic"]),
    ("$ref", "https://example.invalid/schema"), ("default", "synthetic"),
])
def test_original_keywords_cannot_enter_wire_unexamined(keyword, value):
    node = {"type": "string", "maxLength": 64, keyword: value}
    with pytest.raises(ContractError):
        validate_record(tool_with(node))


@pytest.mark.parametrize("kind,good,bad", [
    ("boolean", True, "true"), ("number", 0.25, "0.25"), ("integer", 2, "2"),
    ("integer", 2, True), ("boolean", False, 0),
])
def test_default_annotation_must_pass_type_without_coercion(kind, good, bad):
    tool = tool_with({"type": kind, "description": "Synthetic default annotation; never auto-fill"})
    validate_tool_arguments(tool, {"value": good})
    with pytest.raises(ContractError):
        validate_tool_arguments(tool, {"value": bad})
    with pytest.raises(ContractError):
        validate_tool_arguments(tool, {})
    tool["parameters_json_schema"]["required"] = []
    arguments = {}
    validate_tool_arguments(tool, arguments)
    assert arguments == {}


@pytest.mark.parametrize("node,good,bad", [
    ({"type": "string", "maxLength": 3}, "abc", "abcd"),
    ({"type": "array", "items": {"type": "integer"}, "maxItems": 2}, [1, 2], [1, 2, 3]),
    ({"type": "integer", "minimum": 2, "maximum": 4, "enum": [2, 4]}, 2, 3),
])
def test_narrowed_or_existing_bounds_reject_violating_calls(node, good, bad):
    tool = tool_with(copy.deepcopy(node))
    validate_tool_arguments(tool, {"value": good})
    with pytest.raises(ContractError):
        validate_tool_arguments(tool, {"value": bad})
    with pytest.raises(ContractError):
        validate_tool_arguments(tool, {"value": good, "undeclared": True})
