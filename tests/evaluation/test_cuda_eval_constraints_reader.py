"""Original reader fixture; no formal heldout task or model execution."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import OracleTask
from toolalign.evaluation.cuda_eval.protocol import read_inputs
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.tools import LocalToolRegistry
from toolalign.tools.constraints_catalog import DEPENDENCY_GRAPHS, DOMAIN_TOOLS, VERSION
from toolalign.training.cuda_sft.protocol import encoded, sha


@pytest.fixture
def constraints_input():
    full = LocalToolRegistry(catalog_id=VERSION)
    names = list(DOMAIN_TOOLS["packages"])
    subset = LocalToolRegistry(names, catalog_id=VERSION)
    action = {"kind": "tool_calls", "content": "", "tool_calls": [{
        "call_id": "read-graph", "name": "read_dependency_graph", "arguments": {"bundle": "delivery-cli"},
    }]}
    example = {
        "schema_version": "toolalign.example.v1", "example_id": "original-constraints-reader",
        "source": "original-cpu-component-test", "source_revision": "v1", "license_id": "MIT",
        "source_record_hash": canonical_hash({"original": "constraints-reader"}),
        "group_id": "original-reader-component", "split": "test", "category": "single-tool",
        "messages": [{"role": "user", "content": "Read delivery-cli's dependency graph. Return the JSON array of required nodes for target parser, sorted alphabetically, including transitive prerequisites.",
                      "tool_calls": [], "tool_call_id": None}],
        "tools": subset.tools, "expected_action": action,
    }
    oracle = OracleTask(example["example_id"], example["group_id"], "test", action, {
        "version": ORACLE_VERSION, "answers": [{"kind": "final", "value": ["kernel", "parser"]}],
        "strategies": [[{
            "name": "read_dependency_graph", "arguments": {"bundle": "delivery-cli"},
            "status": "completed", "output": deepcopy(DEPENDENCY_GRAPHS["delivery-cli"]),
            "error_code": None, "retryable": False,
        }]],
    })
    entry = {"task_id": oracle.task_id, "group_id": oracle.group_id, "family_id": "original-reader",
             "category": "single-tool", "example": example, "oracle_task": asdict(oracle),
             "faults": {}, "tool_names": names}
    return {"schema_version": "toolalign.evaluation-tasks.v1", "purpose": "heldout-model-evaluation",
            "catalog": VERSION, "registry_hash": full.registry_hash, "tasks": [entry], "recovery_task_ids": []}


def read_fixture(tmp_path, value):
    path = tmp_path / "original-reader.json"
    path.write_bytes(encoded(value))
    return read_inputs(path, sha(path.read_bytes()), "l1")


def test_reader_selects_new_full_catalog_and_task_subset(tmp_path, constraints_input):
    value, registries = read_fixture(tmp_path, constraints_input)
    assert value == constraints_input
    task = value["tasks"][0]
    registry = registries[task["task_id"]]
    assert registry.catalog_id == VERSION
    assert registry.tools == task["example"]["tools"]
    assert registry.manifest == LocalToolRegistry(DOMAIN_TOOLS["packages"], catalog_id=VERSION).manifest
    assert registry.registry_hash != value["registry_hash"]


@pytest.mark.parametrize("catalog", ["local-devops.v1", "toolalign.tools.constraints_catalog", None])
def test_reader_allows_only_explicit_heldout_catalogs(tmp_path, constraints_input, catalog):
    constraints_input["catalog"] = catalog
    with pytest.raises(ValueError, match="evaluation_task_schema"):
        read_fixture(tmp_path, constraints_input)


def test_reader_rejects_other_catalog_identity_and_changed_tool_schema(tmp_path, constraints_input):
    constraints_input["registry_hash"] = LocalToolRegistry(catalog_id="heldout-devops.v1").registry_hash
    with pytest.raises(ValueError, match="evaluation_registry_identity"):
        read_fixture(tmp_path, constraints_input)
    constraints_input["registry_hash"] = LocalToolRegistry(catalog_id=VERSION).registry_hash
    constraints_input["tasks"][0]["example"]["tools"][0]["description"] += " altered"
    with pytest.raises(ValueError, match="evaluation_task_tool_schema"):
        read_fixture(tmp_path, constraints_input)
