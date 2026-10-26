"""Real HTTP suggestions cannot bypass the local registry or trajectory budget."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from toolalign.client.http import write_record
from toolalign.client.remote import RemoteClient
from toolalign.client.scripted import FixtureHandler, ScriptedHTTPFixture
from toolalign.client.trajectory import run_trajectory
from toolalign.tools import LocalToolRegistry

ROOT = Path(__file__).resolve().parents[2]
NORMAL = json.loads((ROOT / "examples/service/normal-input.json").read_text())
CONVERT = {"call_id": "one", "name": "convert_numeric_units", "arguments": {"value": 1536, "from_unit": "KiB", "to_unit": "MiB"}}


def action(*calls):
    return json.dumps({"kind": "tool_calls", "content": "", "tool_calls": list(calls)})


def private_root(tmp_path, name):
    root = (tmp_path / ".toolalign-local" / name).resolve()
    root.mkdir(mode=0o700, parents=True)
    return root


def test_user_cli_five_original_examples_preserve_success_and_expected_failure_separately(tmp_path):
    root = tmp_path / ".toolalign-local" / "five-examples"
    argv = [sys.executable, "-m", "toolalign.client", "demo", "--cases", str(ROOT / "examples/service/scripted.json"), "--output", str(root)]
    process = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert process.returncode == 0, process.stderr
    summary = json.loads(process.stdout)
    assert summary["real_model_examples"] == "NOT_RUN" and summary["synthetic_token_counts"]
    assert summary["planned_cases"] == 5 and not summary["not_started"]
    assert all(case["expected_behavior_passed"] for case in summary["cases"])
    assert [case["semantic_outcome"] for case in summary["cases"]] == ["success", "success", "failure", "success", "failure"]
    assert [case["model_decisions"] for case in summary["cases"]] == [2, 1, 1, 3, 3]
    assert [case["tool_rounds"] for case in summary["cases"]] == [1, 0, 0, 2, 2]
    local_records, remote_records = [], []
    for case in summary["cases"]:
        case_root = root / case["id"]
        trajectory = json.loads((case_root / "trajectory.json").read_text())
        http = json.loads((case_root / "http-fixture.json").read_text())
        local_records.extend(trajectory["process_records"])
        remote_records.extend(http["process_records"])
        token = (case_root / "token.txt").read_text().strip()
        for path in case_root.rglob("*.json"):
            assert token not in path.read_text(), path.name
        assert token not in process.stdout + process.stderr
        if case["id"] == "invalid-arguments":
            receipt = json.loads((case_root / "decision-00.json").read_text())
            assert receipt["state"]["status"] == "completed"
            assert trajectory["status"] == "rejected" and not trajectory["process_records"]
        if case["id"] == "recovery":
            assert [step["result"]["status"] for step in trajectory["tool_steps"]] == ["error", "completed"]
            second = json.loads((case_root / "decision-01.json").read_text())
            observation = json.loads(second["request_body"]["model_input"]["messages"][-1]["content"])
            assert observation["error_code"] == "injected_transient" and observation["retryable"]
            assert second["request_body"]["model_input"]["tools"] == LocalToolRegistry(["query_build_report"]).tools
    assert len(local_records) == 5 and len(remote_records) == 10
    assert all(row["reaped"] and row["directory_cleaned"] for row in local_records + remote_records)
    write_record(root / "cli-evidence.json", {"argv": argv, "returncode": process.returncode,
                                               "stdout": process.stdout, "stderr": process.stderr})


def test_real_run_cli_keeps_schemas_history_and_tool_results_without_exposing_token(tmp_path):
    root = private_root(tmp_path, "cli-run")
    final = json.dumps({"kind": "final", "content": "1.5", "tool_calls": []})
    with ScriptedHTTPFixture(root, [action(CONVERT), final]) as fixture:
        fixture.config()
        argv = [sys.executable, "-m", "toolalign.client", "run", "--config", str(root / "client-config.json"),
                "--input", str(ROOT / "examples/service/normal-input.json"), "--output", str(root / "output")]
        process = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=10)
        assert process.returncode == 0, process.stderr
        summary = json.loads(process.stdout)
        assert summary["status"] == "finalized" and summary["semantic_outcome"] == "not_scored"
        posts = [r["body"] for r in fixture.requests if r["method"] == "POST" and r["path"] == "/v1/tool-decisions"]
        assert len(posts) == 2 and posts[0]["model_input"] == NORMAL
        assert posts[1]["model_input"]["tools"] == NORMAL["tools"]
        history = posts[1]["model_input"]["messages"]
        assert history[:1] == NORMAL["messages"] and history[-2]["tool_calls"] == [CONVERT]
        assert json.loads(history[-1]["content"])["output"]["converted_value"] == 1.5
        assert posts[1]["timeout_ms"] < posts[0]["timeout_ms"]
        assert fixture.token not in process.stdout + process.stderr
    write_record(root / "fixture.json", fixture.evidence())


@pytest.mark.parametrize("calls,reason", [
    ([{"call_id": "other", "name": "query_build_report", "arguments": {"report_id": "atlas-100"}}], "unadvertised_tool"),
    ([CONVERT | {"arguments": CONVERT["arguments"] | {"path": "/tmp/never-executed"}}], "invalid_arguments"),
    ([CONVERT, {"call_id": "other", "name": "query_build_report", "arguments": {"report_id": "atlas-100"}}], "unadvertised_tool"),
])
def test_all_advertised_names_and_arguments_are_checked_before_any_local_execution(tmp_path, calls, reason):
    root = private_root(tmp_path, "untrusted-action")
    with ScriptedHTTPFixture(root, [action(*calls)]) as fixture:
        result = run_trajectory(RemoteClient(fixture.config()), NORMAL, root)
        assert result["status"] == "rejected" and result["reason"] == reason
        assert not result["tool_steps"] and not result["process_records"]
        received = json.loads((root / "decision-00.json").read_text())
        assert received["state"]["status"] == "completed" and received["state"]["result"]["raw_action_valid"]


def test_call_id_may_not_be_reused_after_an_observation(tmp_path):
    root = private_root(tmp_path, "duplicate-id")
    with ScriptedHTTPFixture(root, [action(CONVERT), action(CONVERT)]) as fixture:
        result = run_trajectory(RemoteClient(fixture.config()), NORMAL, root)
        assert result["status"] == "rejected" and result["reason"] == "duplicate_call_id"
        assert len(result["process_records"]) == 1 and result["process_records"][0]["reaped"]
        assert result["budget"]["tool_rounds"] == 1


def test_modified_advertised_schema_rejects_before_network_or_child(tmp_path):
    root = private_root(tmp_path, "schema")
    with ScriptedHTTPFixture(root, [action(CONVERT)]) as fixture:
        modified = copy.deepcopy(NORMAL)
        modified["tools"][0]["description"] += " changed"
        with pytest.raises(ValueError, match="unbound_tool_schema"):
            run_trajectory(RemoteClient(fixture.config()), modified, root)
        assert not fixture.requests and not fixture.jobs


@pytest.mark.parametrize("mutation,reason", [
    ("raw", "raw_action_mismatch"), ("identity", "model_identity_mismatch"),
    ("payload", "request_payload_mismatch"), ("cleanup", "unconfirmed_terminal_cleanup"),
])
def test_inconsistent_server_claims_cannot_execute_and_original_response_is_retained(tmp_path, mutation, reason):
    class ChangedResponse(FixtureHandler):
        def _send(self, status, value):
            if self.command == "GET" and value.get("status") == "completed":
                value = copy.deepcopy(value)
                if mutation == "raw":
                    value["result"]["raw_action"]["tool_calls"][0]["arguments"]["value"] = 3000
                elif mutation == "identity":
                    value["result"]["model_identity"]["adapter_hash"] = "a" * 64
                elif mutation == "payload":
                    value["payload_hash"] = "b" * 64
                else:
                    value.update(status="cancelled", worker_cleanup="live", reason="cancel_requested")
            super()._send(status, value)

    root = private_root(tmp_path, "inconsistent")
    with ScriptedHTTPFixture(root, [action(CONVERT)]) as fixture:
        fixture.server.RequestHandlerClass = ChangedResponse
        result = run_trajectory(RemoteClient(fixture.config(), cleanup_ms=100), NORMAL, root)
        assert result["status"] == "rejected" and result["reason"] == reason
        assert not result["process_records"]
        receipt = json.loads((root / "decision-00.json").read_text())
        assert receipt["rejected_response"]["result"]["raw_text"] == action(CONVERT)
        assert receipt["cleanup"]["resolution"] == "unknown"


def test_service_raw_parse_failure_is_preserved_without_repair(tmp_path):
    root = private_root(tmp_path, "raw-failure")
    raw = "```json\n" + action(CONVERT) + "\n```"
    with ScriptedHTTPFixture(root, [raw]) as fixture:
        result = run_trajectory(RemoteClient(fixture.config()), NORMAL, root)
        assert result["status"] == "parse_failure" and not result["process_records"]
        receipt = json.loads((root / "decision-00.json").read_text())
        assert receipt["state"]["result"]["raw_text"] == raw
        assert receipt["local_action"] is None and result["repairs"] == "DISABLED"
