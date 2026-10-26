"""One original integration case against E1's real heldout catalog candidate."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from test_cuda_eval import INPUT, request_for, run

from toolalign.contracts import canonical_hash
from toolalign.contracts.interfaces import OracleTask
from toolalign.evaluation.cuda_eval.protocol import read_inputs
from toolalign.evaluation.oracles.semantic import ORACLE_VERSION
from toolalign.tools import LocalToolRegistry
from toolalign.tools.scripted import ScriptedCPUModelBackend
from toolalign.training.cuda_sft.protocol import encoded, sha


def test_real_heldout_reader_to_model_child_to_bound_tool_child_and_recovery_off(tmp_path):
    full = LocalToolRegistry(catalog_id="heldout-devops.v1")
    names = ["read_release_manifest", "read_deployment_snapshot"]
    subset = LocalToolRegistry(names, catalog_id=full.catalog_id)
    arguments = {"application": "comet-gateway", "release": "4.3.0"}
    def call(ident):
        return {"kind": "tool_calls", "content": "", "tool_calls": [
            {"call_id": ident, "name": "read_release_manifest", "arguments": arguments}]}
    # Independent expected values from the published original catalog resources.
    output = {**arguments, "deployment_id": "comet-green", "artifact_label": "comet-430",
              "desired_replicas": 6, "channel": "canary"}
    failed = {"name": "read_release_manifest", "arguments": arguments, "status": "error",
              "output": None, "error_code": "injected_transient", "retryable": True}
    succeeded = failed | {"status": "completed", "output": output, "error_code": None, "retryable": False}
    example = {"schema_version": "toolalign.example.v1", "example_id": "original-heldout-integration",
        "source": "original-cpu-component-test", "source_revision": "v1", "license_id": "MIT",
        "source_record_hash": canonical_hash({"original": "heldout-integration"}), "group_id": "cpu-only",
        "split": "test", "category": "recovery", "messages": [{**INPUT["messages"][0],
            "content": "Read the intended replica count for comet-gateway release 4.3.0. Return its JSON number. Retry once if the read has a transient failure."}],
        "tools": subset.tools, "expected_action": call("first")}
    task = OracleTask(example["example_id"], "cpu-only", "test", call("first"),
        {"version": ORACLE_VERSION, "answers": [{"kind": "final", "value": 6}], "strategies": [[failed, succeeded]]})
    entry = {"task_id": task.task_id, "family_id": "original-component-test", "group_id": task.group_id,
             "category": "recovery", "example": example, "oracle_task": asdict(task), "faults": {
                 "read_release_manifest": ["transient", None]}, "tool_names": names}
    value = {"schema_version": "toolalign.evaluation-tasks.v1", "purpose": "heldout-model-evaluation",
             "catalog": "heldout-devops.v1", "registry_hash": full.registry_hash, "tasks": [entry],
             "recovery_task_ids": [task.task_id]}
    request = request_for(tmp_path, value, "l1")
    inputs, registries = read_inputs(request["input_path"], request["input_sha256"], "l1")
    assert registries[task.task_id].catalog_id == "heldout-devops.v1"
    responses = [json.dumps(call("first")), json.dumps(call("retry")),
                 json.dumps({"kind": "final", "content": "6", "tool_calls": []})]
    summary, rows = run(request, inputs, lambda _: ScriptedCPUModelBackend(responses), registries)
    assert summary["planned_trajectories"] == 3
    assert summary["terminal_counts"] == {"success": 2, "failure": 1}
    assert rows[2]["reason"] == "recovery_disabled:injected_transient"
    assert len(summary["tool_execution_seconds"]) == 5
    for row in rows:
        result = row["result"]
        assert all(p["reaped"] for p in result["process_records"])
        assert all(item["implementation"].startswith("toolalign.tools.heldout_catalog:")
                   for item in result["registry_manifest"]["tools"])
        assert result["decision_inputs"][0] == {"messages": example["messages"], "tools": subset.tools}
    for row in rows[:2]:
        observations = [event["tool_result"] for event in row["result"]["trace"] if event["event"] == "observing"]
        assert [item["error_code"] for item in observations] == ["injected_transient", None]
        assert observations[1]["output"] == output
    entry["example"]["tools"][0]["description"] += " tampered"
    Path(request["input_path"]).write_bytes(encoded(value))
    with pytest.raises(ValueError, match="tool_schema"):
        read_inputs(request["input_path"], sha(encoded(value)), "l1")
