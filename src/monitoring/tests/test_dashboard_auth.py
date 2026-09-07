"""WebSocket authorization tests for the sensor dashboard.

Covers the two protections on ``/ws``:

* the ``Origin`` check that blocks cross-site WebSocket hijacking, and
* the ``SENSOR_DASHBOARD_TOKEN`` requirement on ``start_recording`` /
  ``stop_recording``.

Run with::

    pip install fastapi httpx pytest python-multipart opencv-python numpy pyyaml
    pytest src/monitoring/tests/test_dashboard_auth.py

The dashboard module is imported directly by path; ``uvicorn.run`` and the
browser launch live in its ``__main__`` block, and the TCP listener / zeroconf
browser start from the FastAPI lifespan, so importing it and driving ``app``
without entering ``TestClient``'s context manager has no side effects.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard"))

import launch_sensor_dashboard as dash  # noqa: E402

TOKEN = "s3cret-token"
# TestClient reports the client host as "testclient", i.e. deliberately not a
# loopback address — the same position a remote browser is in.
LOCAL_ORIGIN = "http://localhost:8000"


@pytest.fixture
def client():
    return TestClient(dash.app, base_url="http://localhost:8000")


def _ws_headers(origin=LOCAL_ORIGIN):
    """Headers for a websocket handshake.

    ``TestClient.websocket_connect`` hardcodes ``host: testserver`` in the ASGI
    scope regardless of ``base_url``, which TrustedHostMiddleware then rejects
    with HTTP 400, so Host has to be set explicitly here.
    """
    headers = {"host": "localhost:8000"}
    if origin is not None:
        headers["origin"] = origin
    return headers


@pytest.fixture
def stub_recorder(monkeypatch):
    """Replace the CSV/thread machinery with a flag so no files are written."""
    calls = []

    def fake_begin():
        calls.append("begin")
        dash.recording_state["is_recording"] = True
        dash.recording_state["session_timestamp"] = "20260908_000000"

    def fake_finalize():
        calls.append("finalize")
        return "/dev/null/fake.csv"

    monkeypatch.setattr(dash, "begin_recording_session", fake_begin)
    monkeypatch.setattr(dash, "finalize_recording_session", fake_finalize)
    monkeypatch.setitem(dash.recording_state, "is_recording", False)
    yield calls
    dash.recording_state["is_recording"] = False


def _drain_greeting(ws):
    """The server pushes config/discovery/status frames right after accept."""
    for _ in range(3):
        ws.receive_json()


def test_ws_rejects_foreign_origin(client):
    """A page on another site must not be able to open the control WebSocket."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws", headers=_ws_headers("http://evil.example")) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_ws_rejects_missing_origin_from_non_local_client(client):
    """No Origin means a non-browser client, which is only trusted on loopback."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws", headers=_ws_headers(origin=None)) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_ws_accepts_allowed_origin(client):
    with client.websocket_connect("/ws", headers=_ws_headers()) as ws:
        assert ws.receive_json()["type"] == "config_update"


def test_start_recording_without_token_is_refused(client, stub_recorder, monkeypatch):
    monkeypatch.setattr(dash, "AUTH_TOKEN", TOKEN)
    with client.websocket_connect("/ws", headers=_ws_headers()) as ws:
        _drain_greeting(ws)
        ws.send_json({"action": "start_recording"})
        msg = ws.receive_json()
    assert msg["type"] == "error"
    assert msg["action"] == "start_recording"
    assert "token" in msg["detail"]
    assert stub_recorder == []
    assert dash.recording_state["is_recording"] is False


def test_start_recording_with_wrong_token_is_refused(client, stub_recorder, monkeypatch):
    monkeypatch.setattr(dash, "AUTH_TOKEN", TOKEN)
    with client.websocket_connect("/ws", headers=_ws_headers()) as ws:
        _drain_greeting(ws)
        ws.send_json({"action": "start_recording", "token": "wrong"})
        msg = ws.receive_json()
    assert msg["type"] == "error"
    assert stub_recorder == []


def test_start_recording_with_token_in_message(client, stub_recorder, monkeypatch):
    monkeypatch.setattr(dash, "AUTH_TOKEN", TOKEN)
    with client.websocket_connect("/ws", headers=_ws_headers()) as ws:
        _drain_greeting(ws)
        ws.send_json({"action": "start_recording", "token": TOKEN})
        msg = ws.receive_json()
    assert msg["type"] == "recording_status"
    assert msg["is_recording"] is True
    assert stub_recorder == ["begin"]


def test_start_recording_with_token_in_query_string(client, stub_recorder, monkeypatch):
    monkeypatch.setattr(dash, "AUTH_TOKEN", TOKEN)
    with client.websocket_connect(f"/ws?token={TOKEN}", headers=_ws_headers()) as ws:
        _drain_greeting(ws)
        ws.send_json({"action": "start_recording"})
        msg = ws.receive_json()
    assert msg["type"] == "recording_status"
    assert msg["is_recording"] is True
    assert stub_recorder == ["begin"]


def test_recording_is_local_only_when_no_token_configured(client, stub_recorder, monkeypatch):
    """With no token set, a non-loopback client still cannot start a recording."""
    monkeypatch.setattr(dash, "AUTH_TOKEN", None)
    with client.websocket_connect("/ws", headers=_ws_headers()) as ws:
        _drain_greeting(ws)
        ws.send_json({"action": "start_recording"})
        msg = ws.receive_json()
    assert msg["type"] == "error"
    assert stub_recorder == []


def test_update_config_stays_local_only_even_with_token(client, monkeypatch):
    """The privileged actions are not unlocked by knowing the token."""
    monkeypatch.setattr(dash, "AUTH_TOKEN", TOKEN)
    before = dash.recording_state["save_dir"]
    with client.websocket_connect("/ws", headers=_ws_headers()) as ws:
        _drain_greeting(ws)
        ws.send_json({"action": "update_config", "save_dir": "/tmp/attacker", "token": TOKEN})
        msg = ws.receive_json()
    assert msg["type"] == "error"
    assert dash.recording_state["save_dir"] == before


@pytest.mark.parametrize(
    "origin,client_host,expected",
    [
        ("http://localhost:8000", "testclient", True),
        ("http://127.0.0.1:8000", "testclient", True),
        ("http://evil.example", "127.0.0.1", False),
        ("https://localhost", "testclient", True),
        ("file://", "testclient", False),
        (None, "127.0.0.1", True),
        (None, "192.0.2.5", False),
    ],
)
def test_origin_allowed(origin, client_host, expected):
    assert dash._origin_allowed(origin, client_host) is expected
