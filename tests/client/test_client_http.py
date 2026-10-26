"""Real loopback/CLI evidence of recovery, cancellation and identity boundaries."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from toolalign.client.http import LoopbackHTTP, private_output, write_record
from toolalign.client.protocol import ClientError
from toolalign.client.remote import RemoteClient
from toolalign.client.scripted import FixtureHandler, ScriptedHTTPFixture
from toolalign.client.trajectory import ClientCancellation
from toolalign.contracts import canonical_hash

ROOT = Path(__file__).resolve().parents[2]
NO_TOOL = json.loads((ROOT / "examples/service/no-tool-input.json").read_text())
FINAL = json.dumps({"kind": "final", "content": "5", "tool_calls": []})


def private_root(tmp_path, name):
    return private_output(tmp_path / ".toolalign-local" / name)


def wait_until(predicate, seconds=5):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Expected observable event did not occur")


def decide(client, root, *, seconds=3):
    return client.decision(NO_TOOL, seed=42, expires=time.monotonic() + seconds,
                           cancellation=ClientCancellation(), receipt_path=root / "decision.json")


def drop_connection(handler):
    try:
        handler.connection.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    handler.connection.close()


class DropAcceptedPost(FixtureHandler):
    def _send(self, status, value):
        if self.command == "POST" and self.path == "/v1/tool-decisions" and not getattr(self.server, "dropped", False):
            self.server.dropped = True
            drop_connection(self)
            return
        super()._send(status, value)


class DropBeforeAcceptance(FixtureHandler):
    def do_POST(self):
        if self.path == "/v1/tool-decisions" and not getattr(self.server, "dropped", False):
            self.server.dropped = True
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            self.server.lost_post = {"key": self.headers["Idempotency-Key"], "body": json.loads(raw)}
            drop_connection(self)
            return
        super().do_POST()


def test_lost_post_response_is_recovered_by_original_key_without_regeneration(tmp_path):
    root = private_root(tmp_path, "lost-accepted")
    with ScriptedHTTPFixture(root, [FINAL]) as fixture:
        fixture.server.RequestHandlerClass = DropAcceptedPost
        receipt = decide(RemoteClient(fixture.config()), root)
        assert receipt["status"] == "completed" and receipt["local_action"]["kind"] == "final"
        assert receipt["post_attempts"] == len(fixture.jobs) == 1
        lookups = [r for r in fixture.requests if r["method"] == "GET" and r["path"] == "/v1/tool-decisions"]
        assert lookups and all(r["key"] == receipt["idempotency_key"] for r in lookups)
        assert receipt["request_id"] == fixture.keys[receipt["idempotency_key"]]
    write_record(root / "fixture.json", fixture.evidence())
    assert all(p["reaped"] and p["directory_cleaned"] for p in fixture.evidence()["process_records"])


def test_post_not_received_retries_identical_key_and_payload_within_original_budget(tmp_path):
    root = private_root(tmp_path, "lost-before-acceptance")
    with ScriptedHTTPFixture(root, [FINAL]) as fixture:
        fixture.server.RequestHandlerClass = DropBeforeAcceptance
        receipt = decide(RemoteClient(fixture.config()), root)
        assert receipt["status"] == "completed" and receipt["post_attempts"] == 2
        assert len(fixture.jobs) == 1
        posted = [r for r in fixture.requests if r["method"] == "POST"]
        assert len(posted) == 1
        assert posted[0]["key"] == fixture.server.lost_post["key"] == receipt["idempotency_key"]
        assert canonical_hash(posted[0]["body"]) == canonical_hash(fixture.server.lost_post["body"]) == canonical_hash(receipt["request_body"])
    write_record(root / "fixture.json", fixture.evidence())


@pytest.mark.parametrize("accept_late", [False, True])
def test_after_deadline_only_lookup_and_cancel_even_without_request_id(tmp_path, accept_late):
    class DelayedPost(FixtureHandler):
        def do_POST(self):
            if self.path == "/v1/tool-decisions":
                self.server.post_times.append(time.monotonic())
                time.sleep(0.18)
                if not accept_late:
                    drop_connection(self)
                    return
            super().do_POST()

    root = private_root(tmp_path, "late-original")
    with ScriptedHTTPFixture(root, [FINAL], delay_seconds=10) as fixture:
        fixture.server.post_times = []
        fixture.server.RequestHandlerClass = DelayedPost
        began = time.monotonic()
        receipt = decide(RemoteClient(fixture.config(), cleanup_ms=600), root, seconds=0.12)
        assert receipt["status"] == "timed_out"
        assert len(fixture.server.post_times) == receipt["post_attempts"] == 1
        assert fixture.server.post_times[0] < began + 0.12
        assert any(r["method"] == "GET" and r["path"] == "/v1/tool-decisions" for r in fixture.requests)
        assert all(r["method"] == "GET" or r["path"].endswith("/cancel") or
                   (accept_late and r["body"] == receipt["request_body"])
                   for r in fixture.requests if r["at_monotonic"] > began + 0.12)
        if accept_late:
            assert len(fixture.jobs) == 1
            assert receipt["cleanup"]["resolution"] == "terminal_observed"
            assert receipt["cleanup"]["state"]["worker_cleanup"] in ("reaped", "not_started")
            assert any(r["path"].endswith("/cancel") for r in fixture.requests)
        else:
            assert not fixture.jobs
            assert receipt["request_id"] is None and receipt["cleanup"]["resolution"] == "unknown"
    write_record(root / "fixture.json", fixture.evidence())


def test_network_loss_keeps_remote_cleanup_unknown(tmp_path):
    class DisconnectedControl(FixtureHandler):
        def _send(self, status, value):
            if self.path.startswith("/v1/runs/") or (self.path == "/v1/tool-decisions" and self.command == "GET"):
                drop_connection(self)
                return
            super()._send(status, value)

    root = private_root(tmp_path, "unreachable")
    with ScriptedHTTPFixture(root, [FINAL], delay_seconds=10) as fixture:
        fixture.server.RequestHandlerClass = DisconnectedControl
        receipt = decide(RemoteClient(fixture.config(), cleanup_ms=150), root, seconds=0.15)
        assert receipt["status"] == "timed_out" and receipt["request_id"] is not None
        assert receipt["cleanup"]["resolution"] == "unknown"
        assert receipt["cleanup"]["state"] is None
        assert receipt["cleanup_seconds"] > 0 and receipt["complete_wall_seconds"] > receipt["decision_seconds"]
    write_record(root / "fixture.json", fixture.evidence())


def test_cli_interrupt_cancels_actual_remote_child_and_saved_receipt_supports_readonly_cancel(tmp_path):
    root = private_root(tmp_path, "interrupt")
    output = root / "client-output"
    with ScriptedHTTPFixture(root, [FINAL], delay_seconds=10) as fixture:
        fixture.config()
        argv = [sys.executable, "-m", "toolalign.client", "run", "--config", str(root / "client-config.json"),
                "--input", str(ROOT / "examples/service/no-tool-input.json"), "--output", str(output), "--cleanup-ms", "2000"]
        process = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            wait_until(lambda: any(j["state"]["status"] == "running" for j in fixture.jobs.values()))
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)
        assert process.returncode == 130, (stdout, stderr)
        trajectory = json.loads((output / "trajectory.json").read_text())
        receipt = json.loads((output / "decision-00.json").read_text())
        assert trajectory["status"] == "cancelled"
        assert receipt["cleanup"]["resolution"] == "terminal_observed"
        assert receipt["cleanup"]["state"]["status"] == "cancelled"
        assert receipt["cleanup"]["state"]["worker_cleanup"] == "reaped"
        assert fixture.jobs[receipt["request_id"]]["process"]["reaped"]
        assert any(r["path"].endswith("/cancel") for r in fixture.requests)
        creates = sum(r["method"] == "POST" and r["path"] == "/v1/tool-decisions" for r in fixture.requests)
        cleanup = subprocess.run([sys.executable, "-m", "toolalign.client", "cancel", "--config", str(root / "client-config.json"),
                                  "--request", str(output / "decision-00.json"), "--output", str(root / "manual-cleanup")],
                                 cwd=ROOT, capture_output=True, text=True, timeout=5)
        assert cleanup.returncode == 0, cleanup.stderr
        assert json.loads(cleanup.stdout)["worker_cleanup"] == "reaped"
        assert sum(r["method"] == "POST" and r["path"] == "/v1/tool-decisions" for r in fixture.requests) == creates
        assert fixture.token not in stdout + stderr + cleanup.stdout + cleanup.stderr
    write_record(root / "cli-evidence.json", {"argv": argv, "returncode": process.returncode,
                                               "stdout": stdout, "stderr": stderr})
    write_record(root / "fixture.json", fixture.evidence())


@pytest.mark.parametrize("pin", ["run", "model"])
def test_pinned_identity_mismatch_rejects_before_post(tmp_path, pin):
    root = private_root(tmp_path, "pin")
    with ScriptedHTTPFixture(root, [FINAL]) as fixture:
        config = fixture.config()
        if pin == "run":
            config["service_run_id"] += "-different"
        else:
            config["model_identity"]["adapter_hash"] = "a" * 64
        receipt = decide(RemoteClient(config), root)
        assert receipt["status"] == "rejected"
        assert receipt["reason"] == ("service_run_mismatch" if pin == "run" else "model_identity_mismatch")
        assert receipt["post_attempts"] == 0 and not fixture.jobs


def test_invalid_bearer_token_is_rejected_before_any_decision(tmp_path):
    root = private_root(tmp_path, "authentication")
    with ScriptedHTTPFixture(root, [FINAL]) as fixture:
        config = fixture.config()
        wrong_token = root / "wrong-token.txt"
        wrong_token.write_text("original-invalid-test-token")
        wrong_token.chmod(0o600)
        receipt = decide(RemoteClient(config | {"token_file": str(wrong_token)}), root)
        assert receipt["status"] == "rejected" and receipt["reason"] == "http_rejected_401"
        assert receipt["post_attempts"] == 0 and not fixture.jobs


def test_shortest_cli_budget_is_a_timeout_without_tool_execution(tmp_path):
    root = private_root(tmp_path, "short-budget")
    with ScriptedHTTPFixture(root, [FINAL]) as fixture:
        fixture.config()
        result = subprocess.run([sys.executable, "-m", "toolalign.client", "run", "--config", str(root / "client-config.json"),
                                 "--input", str(ROOT / "examples/service/no-tool-input.json"), "--output", str(root / "output"),
                                 "--timeout-ms", "1", "--cleanup-ms", "100"],
                                cwd=ROOT, capture_output=True, text=True, timeout=5)
        assert result.returncode == 1
        summary = json.loads(result.stdout)
        assert summary["status"] == "timed_out"
        trajectory = json.loads((root / "output/trajectory.json").read_text())
        assert not trajectory["process_records"]
    write_record(root / "cli-evidence.json", {"returncode": result.returncode,
                                               "stdout": result.stdout, "stderr": result.stderr})


@pytest.mark.parametrize("url", ["http://example.com:80", "http://localhost:80", "https://127.0.0.1:80",
    "http://user:password@127.0.0.1:80", "http://127.0.0.1:80/other", "http://127.0.0.1:80/?token=value"])
def test_only_literal_loopback_url_without_embedded_credentials_or_paths(tmp_path, url):
    with pytest.raises(ClientError, match="loopback_url_required"):
        LoopbackHTTP(url, tmp_path / "unread-token-file")


def test_no_proxy_or_redirect_can_forward_bearer_token(tmp_path):
    root = private_root(tmp_path, "redirect")
    target_root = private_root(tmp_path, "redirect-target")
    with ScriptedHTTPFixture(target_root, [FINAL]) as target, ScriptedHTTPFixture(root, [FINAL]) as fixture:
        class RedirectInfo(FixtureHandler):
            def _send(self, status, value):
                packet = json.dumps({"schema": "toolalign.service-http.v1", "error": "redirect"}).encode()
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{target.server.server_port}/v1/model-info")
                self.send_header("Content-Length", str(len(packet)))
                self.end_headers()
                self.wfile.write(packet)

        fixture.server.RequestHandlerClass = RedirectInfo
        fixture.config()
        result = subprocess.run([sys.executable, "-m", "toolalign.client", "run", "--config", str(root / "client-config.json"),
                                 "--input", str(ROOT / "examples/service/no-tool-input.json"), "--output", str(root / "output")],
                                cwd=ROOT, env=os.environ | {"HTTP_PROXY": f"http://127.0.0.1:{target.server.server_port}", "NO_PROXY": ""},
                                capture_output=True, text=True, timeout=5)
        assert result.returncode == 1
        assert json.loads(result.stdout)["reason"] == "http_rejected_302"
        assert not target.requests and not fixture.jobs
        assert fixture.token not in result.stdout + result.stderr


def test_trickling_http_headers_cannot_extend_monotonic_deadline(tmp_path):
    class SlowHeaders(FixtureHandler):
        def _send(self, status, value):
            for part in (b"HTTP/1.0 200 OK\r\n", b"X-Slow: a", b"b", b"c", b"d\r\n\r\n"):
                try:
                    self.wfile.write(part)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
                time.sleep(0.06)

    root = private_root(tmp_path, "trickle")
    with ScriptedHTTPFixture(root, [FINAL]) as fixture:
        fixture.server.RequestHandlerClass = SlowHeaders
        started = time.monotonic()
        receipt = decide(RemoteClient(fixture.config()), root, seconds=0.10)
        assert time.monotonic() - started < 0.35
        assert receipt["status"] == "timed_out" and receipt["post_attempts"] == 0
        assert not fixture.jobs
