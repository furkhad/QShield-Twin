"""Tests for API/WebSocket authentication, rate limiting and body-size limits.

These verify that when a token is configured the sensitive endpoints are
protected, and that local development (no token) keeps working.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.app import create_app
from backend.settings import Settings

_PROTECTED = "/api/v1/simulation/status"


def _settings(**overrides) -> Settings:
    base = dict(environment="test", debug=False)
    base.update(overrides)
    return Settings(**base)


def test_sensitive_endpoint_requires_token_when_configured():
    app = create_app(_settings(api_token="s3cret-token"))
    client = TestClient(app)

    assert client.get(_PROTECTED).status_code == 401
    assert client.get(_PROTECTED, headers={"X-API-Token": "wrong"}).status_code == 401
    # A non-ASCII token must be rejected (401), not crash the constant-time check.
    assert (
        client.get(
            _PROTECTED, headers={"X-API-Token": "tökén-ünicode".encode("latin-1")}
        ).status_code
        == 401
    )


def test_sensitive_endpoint_accepts_valid_token_forms():
    app = create_app(_settings(api_token="s3cret-token"))
    client = TestClient(app)

    via_header = client.get(_PROTECTED, headers={"X-API-Token": "s3cret-token"})
    via_bearer = client.get(
        _PROTECTED, headers={"Authorization": "Bearer s3cret-token"}
    )
    assert via_header.status_code == 200
    assert via_bearer.status_code == 200
    assert via_header.json()["status"] == "ok"


def test_health_remains_open_with_token_configured():
    app = create_app(_settings(api_token="s3cret-token"))
    client = TestClient(app)
    assert client.get("/api/v1/health").status_code == 200


def test_local_development_without_token_is_open():
    app = create_app(_settings())
    client = TestClient(app)
    assert client.get(_PROTECTED).status_code == 200


def test_rate_limit_returns_429_and_exempts_health():
    app = create_app(
        _settings(rate_limit_enabled=True, rate_limit_requests=3, rate_limit_window_seconds=60)
    )
    client = TestClient(app)

    for _ in range(3):
        assert client.get("/api/v1/version").status_code == 200
    limited = client.get("/api/v1/version")
    assert limited.status_code == 429
    assert limited.json()["status"] == "error"
    # Health checks are exempt so orchestration probes keep working.
    assert client.get("/api/v1/health").status_code == 200


def test_max_body_size_is_enforced():
    app = create_app(_settings(max_request_bytes=1024))
    client = TestClient(app)

    big = "x" * 5000
    r = client.post(
        "/api/v1/devices/bulk",
        content=big,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 413
    assert r.json()["status"] == "error"


def test_websocket_requires_token_when_configured():
    app = create_app(_settings(api_token="s3cret-token"))
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/api/v1/ws/stream"):
                pass
        # A valid token in the query string is accepted.
        with client.websocket_connect("/api/v1/ws/stream?token=s3cret-token") as ws:
            ws.send_text("ping")
            assert ws.receive_text() == "ack:ping"


def test_websocket_connection_limit_enforced():
    app = create_app(
        _settings(api_token="s3cret-token", max_ws_connections=1)
    )
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/stream?token=s3cret-token") as ws:
            ws.send_text("ping")
            assert ws.receive_text() == "ack:ping"
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect(
                    "/api/v1/ws/stream?token=s3cret-token"
                ):
                    pass


def test_websocket_open_when_no_token_configured():
    app = create_app(_settings())
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/stream") as ws:
            ws.send_text("hi")
            assert ws.receive_text() == "ack:hi"
