"""Actual loopback and spawn-process checks; all model work is original CPU code."""

import copy
import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from cpu_service import ROOT, build

from toolalign.contracts import canonical_hash
from toolalign.model_io.cuda_generation import ADAPTER_SHA256, CHECKPOINT_SHA256
from toolalign.runtime.gpu_lock import GPULease, inspect_gpu_lock
from toolalign.service.http import serve
from toolalign.service.protocol import HTTP_SCHEMA, RUN_SCHEMA, TokenAuth, validate_run
from toolalign.service.runtime import REQUEST_RESERVE, metadata_reserve
from toolalign.tools import LocalToolRegistry
from toolalign.tools.isolation import OwnedProcess
from toolalign.training.cuda_sft.protocol import CONFIG_SHA256

TOKENS = {"alice": "original_cpu_alice_" + "a" * 32, "bob": "original_cpu_bob_" + "b" * 32}
INPUT = {"messages": [{"role": "user", "content": "Return your original CPU principal.",
                       "tool_calls": [], "tool_call_id": None}], "tools": []}


def eventually(predicate, seconds=6):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError("original CPU condition did not become true")


@pytest.fixture
def config(tmp_path):
    repository = tmp_path / "repository"
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({"schema": "toolalign.service-auth.v1", "tokens": TOKENS}))
    auth.chmod(0o600)
    return {"schema": RUN_SCHEMA, "authorized_by": "S1", "run_kind": "serving", "run_id": "original-service",
        "source_commit": "a" * 40, "config_sha256": CONFIG_SHA256, "model_root": "/not-loaded",
        "checkpoint_dir": "/not-loaded", "checkpoint_sha256": CHECKPOINT_SHA256, "adapter_sha256": ADAPTER_SHA256,
        "dependency_lock": "/not-loaded", "dependency_lock_sha256": "b" * 64,
        "repository": str(repository), "lock_root": str(repository), "output_dir": str(tmp_path / "output"),
        "auth_file": str(auth), "listen_host": "127.0.0.1", "listen_port": 0, "cache_enabled": True,
        "max_generations": 12, "max_wall_seconds": 60, "max_output_bytes": 256 * 1024**2}


class Client:
    def __init__(self, port, config):
        self.port, self.config = port, config

    def request(self, method, path, payload=None, *, principal="alice", key=None, raw=None, headers=None):
        fields = {} if principal is None else {"Authorization": "Bearer " + TOKENS.get(principal, principal)}
        if key is not None:
            fields["Idempotency-Key"] = key
        fields.update(headers or {})
        data = raw if raw is not None else None if payload is None else json.dumps(payload).encode()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=4)
        try:
            connection.request(method, path, body=data, headers=fields)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def submit(self, key, *, seed=42, timeout=30000, principal="alice", model_input=None):
        body = {"schema": HTTP_SCHEMA, "service_run_id": self.config["run_id"],
                "model_input": copy.deepcopy(INPUT) if model_input is None else model_input,
                "seed": seed, "timeout_ms": timeout}
        return self.request("POST", "/v1/tool-decisions", body, key=key, principal=principal)

    def state(self, ident, *, principal="alice"):
        return self.request("GET", "/v1/runs/" + ident, principal=principal)

    def terminal(self, ident, *, principal="alice"):
        return eventually(lambda: (state if (state := self.state(ident, principal=principal)[1])["status"] not in
                                   ("queued", "running", "stopping") else None))

    def ready(self):
        return self.request("GET", "/readyz")


@pytest.fixture
def launch():
    active = []

    def start(config, *, prepare_seconds=0, wait_ready=True, started_monotonic=None):
        service = build(config, prepare_seconds=prepare_seconds, started_monotonic=started_monotonic)
        errors = []
        def run():
            try:
                serve(service)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=run)
        active.append((service, thread, errors))
        thread.start()
        listening = Path(config["output_dir"]) / "listening.json"
        eventually(listening.exists)
        client = Client(json.loads(listening.read_text())["port"], config)
        if wait_ready:
            eventually(lambda: client.ready()[0] == 200)
        return client, service

    yield start
    for service, thread, errors in active:
        service.cancellation.cancel()
        thread.join(8)
        assert not thread.is_alive() and not errors
        assert service.summary["cleanup_confirmed"]
        assert all(w["process"]["reaped"] and w["process"]["directory_cleaned"] for w in service.workers)
        assert not inspect_gpu_lock(service.request["repository"])["held"]
        assert sum(p.stat().st_size for p in service.store.root.rglob("*") if p.is_file()) <= service.store.max_bytes


def events(config):
    path = Path(config["output_dir"]).parent / "events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_prepare_readiness_identity_and_private_auth(config, launch):
    client, service = launch(config, prepare_seconds=0.4, wait_ready=False)
    assert client.request("GET", "/healthz", principal=None) == (200, {"schema": HTTP_SCHEMA, "status": "alive"})
    assert client.ready()[0] == 503
    assert client.submit("early")[1]["error"] == "not_ready"
    assert all(e["event"] != "generate" for e in events(config))
    for endpoint in ("/readyz", "/v1/model-info", "/v1/tool-decisions", "/v1/runs/unknown"):
        assert client.request("GET", endpoint, principal=None)[0] == 401
        assert client.request("GET", endpoint, principal="invalid")[0] == 401
    eventually(lambda: client.ready()[0] == 200)
    prepared = events(config)[0]
    assert prepared["creator_pid"] == os.getpid() and prepared["pid"] != os.getpid()
    owner = inspect_gpu_lock(config["repository"])
    assert owner["held"] and owner["owner"]["pid"] == prepared["pid"]
    info = client.request("GET", "/v1/model-info")[1]
    assert info == service.info and info["limits"]["max_records"] == 64
    assert info["model_identity"] == service.model_identity
    assert info["sampling"]["max_new_tokens"] == 256 and info["cache"]["scope"] == "principal"
    assert client.request("GET", "/v1/tool-decisions", key="never")[0] == 404
    assert client.request("GET", "/v1/tool-decisions")[0] == 400
    assert events(config) == [prepared]


def test_idempotency_principal_isolation_and_terminal_cancel(config, launch):
    client, service = launch(config)
    status, receipt = client.submit("same")
    assert status == 202 and not receipt["replayed"]
    ident = receipt["request_id"]
    state = client.terminal(ident)
    assert state["status"] == "completed" and state["worker_cleanup"] == "live"
    assert state["result"]["raw_action"]["content"] == "alice"
    assert state["result"]["raw_text"] == json.dumps({"kind": "final", "content": "alice", "tool_calls": []})
    assert state["timing"]["ttft_seconds"] is None
    assert client.submit("same")[0] == 200
    assert client.request("GET", "/v1/tool-decisions", key="same")[1] == state
    assert client.submit("same", seed=2)[0] == 409
    assert client.state(ident, principal="bob")[0] == 404
    assert client.request("POST", f"/v1/runs/{ident}/cancel", {}, principal="bob")[0] == 404
    assert client.request("GET", "/v1/tool-decisions", key="same", principal="bob")[0] == 404
    _, second = client.submit("same", principal="bob")
    second_state = client.terminal(second["request_id"], principal="bob")
    assert second_state["result"]["raw_action"]["content"] == "bob"
    assert second_state["worker_epoch"] == state["worker_epoch"]
    _, running = client.submit("active", seed=1)
    eventually(lambda: client.state(running["request_id"])[1]["status"] == "running")
    assert client.request("POST", f"/v1/runs/{ident}/cancel", {}) == (200, state)
    assert client.state(running["request_id"])[1]["status"] == "running"
    assert len(service.workers) == 1
    assert [e["principal"] for e in events(config) if e["event"] == "generate"][:2] == ["alice", "bob"]


def test_queue_expiry_cancel_and_full_do_not_kill_active(config, launch):
    client, service = launch(config)
    _, active = client.submit("active", seed=1)
    eventually(lambda: any(e.get("seed") == 1 for e in events(config)))
    _, expires = client.submit("expires", timeout=80)
    _, cancelled = client.submit("cancelled")
    assert client.submit("full")[1]["error"] == "queue_full"
    ready = client.ready()[1]
    assert ready["ready"] and not ready["accepting"]
    cancelled_id = cancelled["request_id"]
    assert client.request("POST", f"/v1/runs/{cancelled_id}/cancel", {})[1]["status"] == "cancelled"
    state = client.terminal(expires["request_id"])
    assert state["reason"] == "queue_deadline" and state["worker_cleanup"] == "not_started"
    assert state["started_at_utc"] is None and state["result"] is None
    assert client.state(active["request_id"])[1]["status"] == "running"
    assert len(service.workers) == 1
    assert [e["seed"] for e in events(config) if e["event"] == "generate"] == [1]


@pytest.mark.parametrize("cancel", [False, True])
def test_active_stop_reaps_lease_before_terminal_then_reloads(config, launch, cancel):
    client, service = launch(config, prepare_seconds=0.2)
    _, receipt = client.submit("active", seed=1, timeout=30000 if cancel else 250)
    ident = receipt["request_id"]
    eventually(lambda: any(e.get("seed") == 1 for e in events(config)))
    if cancel:
        status, stopping = client.request("POST", f"/v1/runs/{ident}/cancel", {})
        assert status == 202 and stopping["status"] == "stopping"
    state = client.terminal(ident)
    assert state["status"] == ("cancelled" if cancel else "timed_out")
    assert state["worker_cleanup"] == "reaped" and state["timing"]["cleanup_seconds"] >= 0
    worker = service.workers[0]
    assert worker["process"]["reaped"] and not worker["lease_held_by_worker_after_close"]
    with pytest.raises(ProcessLookupError):
        os.kill(worker["process"]["pid"], 0)
    eventually(lambda: client.ready()[1]["ready"])
    _, receipt2 = client.submit("after")
    state2 = client.terminal(receipt2["request_id"])
    assert state2["status"] == "completed" and state2["worker_epoch"] == 2
    assert state2["started_at_utc"] > worker["closed_at_utc"]


def test_queued_deadline_during_reload_is_not_refreshed(config, launch):
    client, service = launch(config, prepare_seconds=0.4)
    _, active = client.submit("active", seed=1)
    eventually(lambda: any(e.get("seed") == 1 for e in events(config)))
    _, queued = client.submit("queued", timeout=150)
    original = client.state(queued["request_id"])[1]
    assert client.request("POST", f"/v1/runs/{active['request_id']}/cancel", {})[0] == 202
    terminal = client.terminal(queued["request_id"])
    assert terminal["reason"] == "queue_deadline" and terminal["worker_epoch"] is None
    assert terminal["deadline_utc"] == original["deadline_utc"] and terminal["started_at_utc"] is None
    eventually(lambda: client.ready()[1]["ready"])
    assert service._epoch == 2
    assert [e["seed"] for e in events(config) if e["event"] == "generate"] == [1]


def test_initial_prepare_deadline_includes_parent_preflight(config, launch):
    config["max_wall_seconds"] = 900
    _, service = launch(config, prepare_seconds=2, wait_ready=False,
                        started_monotonic=time.monotonic() - 119.5)
    assert service.done.wait(2)
    assert service.summary["status"] == "worker_start_failed" and service.summary["accepted_requests"] == 0
    assert service.workers[0]["prepare_status"] == "timed_out"
    assert not any(e["event"] == "generate" for e in events(config))


def test_cleanup_unconfirmed_keeps_stopping_and_stops_accepting(config, monkeypatch):
    """MOCK_ONLY close acknowledgement fault, after a real child is actually reaped."""
    original = OwnedProcess.close

    def missing_acknowledgement(worker):
        original(worker)
        raise OSError("original injected post-reap acknowledgement failure")

    monkeypatch.setattr(OwnedProcess, "close", missing_acknowledgement)
    service = build(config)
    service.start()
    try:
        eventually(lambda: service.readiness()["ready"])
        payload = {"schema": HTTP_SCHEMA, "service_run_id": config["run_id"],
                   "model_input": INPUT, "seed": 1, "timeout_ms": 30000}
        _, receipt = service.submit("alice", "cancel", payload, json.dumps(payload).encode())
        eventually(lambda: any(e.get("seed") == 1 for e in events(config)))
        service.cancel("alice", receipt["request_id"])
        assert service.done.wait(4)
        state = service.lookup("alice", ident=receipt["request_id"])
        assert state["status"] == "stopping" and state["reason"] == "cleanup_unconfirmed"
        assert state["worker_cleanup"] == "unconfirmed" and state["finished_at_utc"] is None
        assert not service.readiness()["accepting"] and not service.summary["cleanup_confirmed"]
        assert service.workers[0]["process"]["reaped"]
        assert not (service.store.root / "requests" / receipt["request_id"] / "terminal.json").exists()
    finally:
        service.stop()
    assert not inspect_gpu_lock(config["repository"])["held"]


def test_retained_raw_action_is_parsed_even_when_backend_packet_is_oversized(config, launch):
    client, _ = launch(config)
    _, receipt = client.submit("oversized-view", seed=10)
    state = client.terminal(receipt["request_id"])
    assert state["status"] == "infrastructure_error" and state["worker_cleanup"] == "reaped"
    result = state["result"]
    assert result["diagnostic"]["raw_truncated"] is False and result["token_accounting_complete"]
    assert result["raw_action_valid"] is True and result["raw_parse_failure"] is None
    assert result["raw_action"] == json.loads(result["raw_text"])


@pytest.mark.parametrize(("seed", "status", "reason"), [
    (3, "parse_failure", "invalid_raw_action"), (4, "budget_exhausted", "response_token_limit"),
    (5, "infrastructure_error", "invalid_token_accounting"),
    (6, "infrastructure_error", "model_identity_mismatch"),
    (7, "infrastructure_error", "backend_error"), (8, "infrastructure_error", "context_overflow"),
    (9, "infrastructure_error", "backend_error"),
])
def test_raw_gate_failure_and_unknown_metrics_are_preserved(config, launch, seed, status, reason):
    client, _ = launch(config)
    _, receipt = client.submit("failure", seed=seed)
    state = client.terminal(receipt["request_id"])
    assert state["status"] == status and state["reason"] == reason and state["worker_cleanup"] == "reaped"
    result = state["result"]
    assert result["input_tokens"] is None if seed in (5, 9) else result["input_tokens"] == 10
    assert result["token_accounting_complete"] is (seed not in (5, 9))
    assert state["timing"]["cache_hit_tokens"] is None
    if seed == 3:
        assert result["raw_text"] == "not JSON" and result["raw_action"] is None
    if seed == 7:
        assert result["raw_text"] is None and result["diagnostic"]["raw_size_bytes"] == 150000
        assert result["diagnostic"]["raw_truncated"]


def test_input_contract_and_body_bounds_before_dispatch(config, launch):
    client, _ = launch(config)
    good = {"schema": HTTP_SCHEMA, "service_run_id": config["run_id"], "model_input": INPUT, "seed": 0, "timeout_ms": 1000}
    for patch in ({"seed": True}, {"seed": 2**63}, {"timeout_ms": 30001}, {"path": "/tmp"},
                  {"model_input": INPUT | {"private_oracle": {}}}, {"service_run_id": "other"}):
        assert client.request("POST", "/v1/tool-decisions", good | patch, key="bad")[0] in (400, 409)
    assert client.request("POST", "/v1/tool-decisions", good, key="bad.key")[0] == 400
    assert client.request("POST", "/v1/tool-decisions", raw=b'{"schema":0,"schema":1}', key="bad")[0] == 400
    assert client.request("POST", "/v1/tool-decisions", raw=b"{}", key="bad",
                          headers={"Content-Length": "524289"})[0] == 413
    tools = LocalToolRegistry(catalog_id="local-devops.v1").tools[:1]
    changed = copy.deepcopy(tools)
    changed[0]["description"] += "changed"
    assert client.submit("tool", model_input=INPUT | {"tools": changed})[1]["error"] == "unbound_tool_schema"
    _, receipt = client.submit("tool", model_input=INPUT | {"tools": tools})
    state = client.terminal(receipt["request_id"])
    assert state["status"] == "completed" and state["input_hash"] == canonical_hash(INPUT | {"tools": tools})
    assert len([e for e in events(config) if e["event"] == "generate"]) == 1


def test_record_limit_idempotency_and_generation_limit(config, launch):
    client, service = launch(config)
    _, active = client.submit("active", seed=1)
    eventually(lambda: client.state(active["request_id"])[1]["status"] == "running")
    for i in range(63):
        status, row = client.submit("queued-" + str(i))
        assert status == 202
        assert client.request("POST", f"/v1/runs/{row['request_id']}/cancel", {})[1]["status"] == "cancelled"
    assert client.submit("record-65")[1]["error"] == "record_limit"
    assert client.submit("queued-0")[0] == 200
    assert len(service._jobs) == 64 and service._generations == 1


def test_generation_and_output_budget_include_shutdown(config, launch):
    config["max_generations"] = 1
    config["max_output_bytes"] = metadata_reserve(1) + REQUEST_RESERVE
    client, service = launch(config)
    _, row = client.submit("one")
    assert client.terminal(row["request_id"])["status"] == "completed"
    assert client.submit("two")[1]["error"] == "service_budget_exhausted"
    assert client.submit("one")[0] == 200
    eventually(lambda: service.workers[0]["process"]["reaped"])
    assert len(service.workers) == 1


def test_output_reservation_rejects_before_any_generation(config, launch):
    config["max_output_bytes"] = metadata_reserve(12) + REQUEST_RESERVE - 1
    client, _ = launch(config)
    assert client.submit("rejected")[1]["error"] == "output_budget_exhausted"
    assert client.request("GET", "/v1/tool-decisions", key="rejected")[0] == 404
    assert not any(e["event"] == "generate" for e in events(config))


def test_gpu_lease_conflict_has_no_ready_or_generation(config, launch):
    with GPULease(task_id="ORIGINAL_TRAINING", worker_alias="CPU", run_id="held",
                  expected_job="training", memory_strategy="no_model", repository=config["repository"]):
        _, service = launch(config, wait_ready=False)
        assert service.done.wait(5)
        assert service.summary["status"] == "worker_start_failed"
        assert service.summary["accepted_requests"] == 0
        assert inspect_gpu_lock(config["repository"])["owner"]["pid"] == os.getpid()
        assert not events(config)


def test_wall_limit_and_slow_connection_leave_cleanup_time(config, launch):
    config["max_wall_seconds"] = 6
    client, service = launch(config)
    _, row = client.submit("active", seed=1)
    slow = socket.create_connection(("127.0.0.1", client.port))
    try:
        slow.sendall(b"GET /healthz HTTP/1.1\r\nX-Incomplete: ")
        assert service.done.wait(5)
        assert service.summary["wall_seconds"] < 6
        state = json.loads((service.store.root / "requests" / row["request_id"] / "terminal.json").read_text())
        assert state["status"] == "cancelled" and state["worker_cleanup"] == "reaped"
    finally:
        slow.close()


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT])
def test_whole_service_process_signal_reaps_real_child_and_lock(config, tmp_path, sig):
    path = tmp_path / "run.json"
    path.write_text(json.dumps(config))
    with (tmp_path / "process.stdout").open("w") as stdout, (tmp_path / "process.stderr").open("w") as stderr:
        process = subprocess.Popen([sys.executable, str(ROOT / "tests/service/cpu_service.py"), str(path)],
                                   stdout=stdout, stderr=stderr)
        try:
            listening = Path(config["output_dir"]) / "listening.json"
            eventually(listening.exists)
            client = Client(json.loads(listening.read_text())["port"], config)
            eventually(lambda: client.ready()[0] == 200)
            _, active = client.submit("active", seed=1)
            eventually(lambda: any(e.get("seed") == 1 for e in events(config)))
            _, queued = client.submit("queued")
            before = time.monotonic()
            process.send_signal(sig)
            assert process.wait(timeout=5) == 0 and time.monotonic() - before < 5
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    output = Path(config["output_dir"])
    summary = json.loads((output / "summary.json").read_text())
    assert summary["status"] == "signal" and summary["cleanup_confirmed"]
    assert summary["generation_attempts"] == 1 and summary["terminal_counts"] == {"cancelled": 2}
    assert not inspect_gpu_lock(config["repository"])["held"]
    for worker in summary["workers"]:
        assert worker["process"]["reaped"] and worker["process"]["directory_cleaned"]
        with pytest.raises(ProcessLookupError):
            os.kill(worker["process"]["pid"], 0)
    for receipt in (active, queued):
        state = json.loads((output / "requests" / receipt["request_id"] / "terminal.json").read_text())
        assert state["status"] == "cancelled"


def test_cpu_cli_validation_and_rejected_configuration(config, tmp_path):
    for patch in ({"listen_host": "0.0.0.0"}, {"listen_port": True}, {"max_generations": 13},
                  {"max_wall_seconds": 901}, {"max_output_bytes": 256 * 1024**2 + 1},
                  {"cache_enabled": 1}, {"run_kind": "training"}, {"backend": "arbitrary"}):
        with pytest.raises(ValueError):
            validate_run(config | patch)
    auth = Path(config["auth_file"])
    auth.chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        TokenAuth(auth)
    auth.chmod(0o600)
    path = tmp_path / "run.json"
    path.write_text(json.dumps(config))
    result = subprocess.run([sys.executable, "-m", "toolalign.service", "validate", "--run-config", str(path)],
                            capture_output=True, text=True, check=True, timeout=10)
    assert json.loads(result.stdout) == {"status": "CPU_VALIDATED", "cuda_service": "NOT_RUN"}
    assert not Path(config["output_dir"]).exists()
