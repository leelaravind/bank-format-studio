"""Socket-blocking harness (SEC-01/SEC-02): every test in this package runs with
socket creation forbidden — any network attempt fails the test loudly."""

import socket

import pytest


class _NetworkForbidden(Exception):
    pass


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def _blocked(*args, **kwargs):
        raise _NetworkForbidden("network access attempted during conversion (SEC-02 violation)")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield
