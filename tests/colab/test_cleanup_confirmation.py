"""Bounded confirmation of the observed signal-0 EPERM exit race."""

import errno
import signal
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import test_control
from test_control import read_json, remote, terminal_output

run = test_control.run


@pytest.fixture
def process_clock(monkeypatch):
    process = Mock(pid=12345)
    process.poll.return_value = None
    process.wait.return_value = -signal.SIGKILL
    clock = SimpleNamespace(now=0.0)

    def sleep(seconds):
        clock.now += seconds

    monkeypatch.setattr(remote, "time", SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep))
    return process, clock


def test_transient_query_eperm_still_requires_confirmed_group_exit(process_clock, monkeypatch):
    process, clock = process_clock
    signals, after_kill_queries = [], []

    def killpg(pgid, signum):
        assert pgid == process.pid
        if signum:
            signals.append(signum)
        elif signals[-1] == signal.SIGKILL:
            after_kill_queries.append(signum)
            if len(after_kill_queries) == 1:
                raise PermissionError(errno.EPERM, "transient query during group exit")
            raise ProcessLookupError(errno.ESRCH, "group has disappeared")

    monkeypatch.setattr(remote.os, "killpg", killpg)
    remote.terminate_owned_group(process)
    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert len(after_kill_queries) == 2  # EPERM alone must not complete cleanup.
    assert 10 < clock.now <= 20
    process.wait.assert_called_once()


def test_persistent_query_eperm_keeps_timeout_unconfirmed_and_blocks_export(
    run, process_clock, monkeypatch,
):
    repository, directory, payload = run
    process, clock = process_clock
    terminal_output(directory)
    process.wait.side_effect = subprocess.TimeoutExpired("fixture-worker", 1)
    monkeypatch.setattr(remote.subprocess, "Popen", lambda *args, **kwargs: process)
    signals = []

    def killpg(pgid, signum):
        assert pgid == process.pid
        if signum:
            signals.append(signum)
        else:
            raise PermissionError(errno.EPERM, "persistent query failure")

    monkeypatch.setattr(remote.os, "killpg", killpg)
    assert remote.worker(repository, payload) == 124
    ended = read_json(directory / "exit.json")
    assert ended["timed_out"] is True
    assert ended["timeout_cleanup_completed"] is False
    assert "bounded SIGKILL cleanup" in ended["error"]
    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert clock.now == pytest.approx(20)
    with pytest.raises(ValueError, match="cleanup is unconfirmed"):
        remote.export(repository, payload)


@pytest.mark.parametrize("denied_signal", [signal.SIGTERM, signal.SIGKILL])
def test_signal_delivery_eperm_is_not_suppressed(process_clock, monkeypatch, denied_signal):
    process, clock = process_clock
    signals = []

    def killpg(pgid, signum):
        assert pgid == process.pid
        if signum:
            signals.append(signum)
            if signum == denied_signal:
                raise PermissionError(errno.EPERM, "signal delivery denied")

    monkeypatch.setattr(remote.os, "killpg", killpg)
    with pytest.raises(PermissionError, match="signal delivery denied"):
        remote.terminate_owned_group(process)
    assert signals[-1] == denied_signal
    assert clock.now <= 10
    process.wait.assert_not_called()
