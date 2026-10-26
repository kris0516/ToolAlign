"""Loopback HTTP control plane; model waits belong to the service scheduler."""

from __future__ import annotations

import signal
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

from toolalign.contracts import ContractError
from toolalign.tools._json import INPUT_BYTES, decode, encode

from .protocol import HTTP_SCHEMA, APIError


@contextmanager
def termination_signals(cancellation):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        for sig in previous:
            signal.signal(sig, lambda *_: cancellation.cancel())
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


class Handler(BaseHTTPRequestHandler):
    def handle(self):
        # An absolute connection deadline also bounds slowly trickled headers.
        # Only one HTTP handler is active; a timer never owns a model process.
        def expire():
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        timer = threading.Timer(2, expire)
        timer.start()
        try:
            super().handle()
        finally:
            timer.cancel()
            timer.join()

    def log_message(self, *_):
        # Request headers, raw prompts and authorization never enter access logs.
        pass

    def _header(self, name):
        values = self.headers.get_all(name, [])
        return values[0] if len(values) == 1 else None

    def _body(self):
        size = self._header("Content-Length")
        if self.headers.get_all("Transfer-Encoding") or size is None or not size.isascii() or not size.isdecimal():
            raise APIError(400, "invalid_request")
        if len(size) > 6:
            raise APIError(413, "request_too_large")
        size = int(size)
        if size > INPUT_BYTES:
            raise APIError(413, "request_too_large")
        raw = self.rfile.read(size)
        if len(raw) != size:
            raise APIError(400, "invalid_json")
        try:
            return decode(raw, INPUT_BYTES), raw
        except ContractError:
            raise APIError(400, "invalid_json") from None

    def _route(self):
        service = self.server.service
        if self.command == "GET" and self.path == "/healthz":
            return 200, {"schema": HTTP_SCHEMA, "status": "alive"}
        principal = service.auth.principal(self._header("Authorization"))
        if self.command == "GET":
            if self.path == "/readyz":
                state = service.readiness()
                return (200 if state["ready"] else 503), state
            if self.path == "/v1/model-info":
                return 200, service.info
            if self.path == "/v1/tool-decisions":
                key = self._header("Idempotency-Key")
                # Validate even when the header is missing: lookup(None) is an ID lookup.
                from .protocol import idempotency_key

                return 200, service.lookup(principal, key=idempotency_key(key))
            parts = self.path.split("/")
            if len(parts) == 4 and parts[1:3] == ["v1", "runs"] and parts[3]:
                return 200, service.lookup(principal, ident=parts[3])
        if self.command == "POST":
            if self.path == "/v1/tool-decisions":
                payload, raw = self._body()
                return service.submit(principal, self._header("Idempotency-Key"), payload, raw)
            parts = self.path.split("/")
            if len(parts) == 5 and parts[1:3] == ["v1", "runs"] and parts[3] and parts[4] == "cancel":
                payload, _ = self._body()
                if type(payload) is not dict or payload:
                    raise APIError(400, "invalid_request")
                return service.cancel(principal, parts[3])
        raise APIError(404, "endpoint_not_found")

    def _dispatch(self):
        try:
            status, value = self._route()
        except APIError as error:
            status, value = error.status, {"schema": HTTP_SCHEMA, "error": error.code}
        raw = encode(value, INPUT_BYTES)
        self.close_connection = True
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    do_GET = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_DELETE = _dispatch
    do_PATCH = _dispatch


def serve(service):
    """Return only after the scheduler has reaped its child and written summary."""
    request = service.request
    with HTTPServer((request["listen_host"], request["listen_port"]), Handler) as server:
        server.timeout = 0.1
        server.service = service
        service._write("listening.json", {"host": server.server_address[0],
                                          "port": server.server_address[1]})
        service.start()
        try:
            while service.thread.is_alive() and not service.done.is_set() and not service.cancellation.is_cancelled():
                server.handle_request()
        finally:
            summary = service.stop("signal" if service.cancellation.is_cancelled() else "http_stopped")
    return summary
