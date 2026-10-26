"""Authenticated loopback HTTP with one monotonic budget and no redirects/proxies."""

from __future__ import annotations

import http.client
import os
import re
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from toolalign.contracts import ContractError
from toolalign.tools._json import INPUT_BYTES, decode, encode, validate_part

from .protocol import SCHEMA, ClientError, fields, require, text


class TransportError(ClientError):
    pass


class APIError(ClientError):
    def __init__(self, status, value):
        fields(value, "schema error", "http_error_fields")
        require(value["schema"] == SCHEMA and text(value["error"]), "http_error_values")
        self.status = status
        self.remote_code = value["error"]
        super().__init__("http_rejected_" + str(status))


def read_json(path):
    with Path(path).open("rb") as stream:
        return decode(stream.read(INPUT_BYTES + 1), INPUT_BYTES)


def load_config(path):
    value = read_json(path)
    fields(value, "schema url service_run_id model_identity token_file", "client_config_fields")
    require(value["schema"] == "toolalign.mac-client.v1" and text(value["service_run_id"])
            and text(value["token_file"]), "client_config_values")
    validate_part(value["model_identity"], "model_identity")
    token_path = Path(value["token_file"])
    if not token_path.is_absolute():
        token_path = Path(path).resolve().parent / token_path
    return value | {"token_file": str(token_path.resolve())}


def private_output(path):
    path = Path(path).resolve()
    require(".toolalign-local" in path.parts, "output_must_be_private")
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    return path


def write_record(path, value):
    # A receipt can contain both a bounded HTTP body and response. It is not a
    # new wire packet; retain them together without truncating either history.
    import json

    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    staging = Path(path).with_suffix(".pending")
    descriptor = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
    staging.replace(path)


class LoopbackHTTP:
    def __init__(self, url, token_file):
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except (TypeError, ValueError) as exc:
            raise ClientError("loopback_url_required") from exc
        require(parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "::1")
                and parsed.username is None and parsed.password is None
                and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
                and type(port) is int and 1 <= port <= 65535, "loopback_url_required")
        self.host, self.port = parsed.hostname, port
        path = Path(token_file)
        require(path.is_file() and path.stat().st_mode & 0o077 == 0, "private_token_file_required")
        with path.open("rb") as stream:
            raw = stream.read(4097)
        require(len(raw) <= 4096, "token_file_limit")
        try:
            token = raw.decode("ascii").strip()
        except UnicodeError as exc:
            raise ClientError("invalid_bearer_token") from exc
        require(bool(token) and all(33 <= ord(char) <= 126 for char in token), "invalid_bearer_token")
        self._authorization = "Bearer " + token

    def request(self, method, path, *, expires, cancellation, key=None, body=None):
        remaining = expires - time.monotonic()
        if remaining <= 0 or cancellation.is_cancelled():
            raise TransportError("transport_deadline_or_cancelled")
        if key is not None:
            require(type(key) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", key), "invalid_idempotency_key")
        raw = None if body is None else encode(body, INPUT_BYTES)
        headers = {"Authorization": self._authorization, "Accept": "application/json"}
        if key is not None:
            headers["Idempotency-Key"] = key
        if raw is not None:
            headers["Content-Type"] = "application/json"
        # One short attempt permits by-key recovery after a lost POST response.
        # The watchdog also bounds trickling headers/body and signal cancellation.
        attempt_deadline = min(expires, time.monotonic() + 1.0)
        connection = http.client.HTTPConnection(self.host, self.port, timeout=max(0.001, attempt_deadline - time.monotonic()))
        finished = threading.Event()
        watcher = None
        try:
            connection.connect()
            connected_socket = connection.sock

            def stop_at_deadline():
                while not finished.is_set():
                    left = attempt_deadline - time.monotonic()
                    if left <= 0 or cancellation.is_cancelled():
                        try:
                            connected_socket.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                        return
                    finished.wait(min(left, 0.02))

            watcher = threading.Thread(target=stop_at_deadline, daemon=True)
            watcher.start()
            if time.monotonic() >= expires or cancellation.is_cancelled():
                raise TransportError("transport_deadline_or_cancelled")
            connection.request(method, path, body=raw, headers=headers)
            response = connection.getresponse()
            packet = response.read(INPUT_BYTES + 1)
            if time.monotonic() >= attempt_deadline or cancellation.is_cancelled():
                raise TransportError("transport_deadline_or_cancelled")
            try:
                value = decode(packet, INPUT_BYTES)
            except ContractError as exc:
                raise ClientError("invalid_http_json") from exc
            return response.status, value
        except (OSError, http.client.HTTPException) as exc:
            raise TransportError("network_error") from exc
        finally:
            finished.set()
            connection.close()
            if watcher is not None:
                watcher.join()
