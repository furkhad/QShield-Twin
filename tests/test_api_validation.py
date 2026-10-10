"""Tests for request validation and bounded inputs on state-changing endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_bulk_device_count_is_bounded():
    client = _client()
    # Absurd counts must be rejected with 422 before any work happens.
    r = client.post("/api/v1/devices/bulk", json={"count": 10_000_000})
    assert r.status_code == 422
    assert r.json()["status"] == "error"

    ok = client.post("/api/v1/devices/bulk", json={"count": 3, "prefix": "t"})
    assert ok.status_code == 200
    assert ok.json()["data"]["count"] == 3


def test_negative_bulk_count_is_rejected():
    client = _client()
    r = client.post("/api/v1/devices/bulk", json={"count": -5})
    assert r.status_code == 422


def test_attack_count_is_bounded():
    client = _client()
    r = client.post("/api/v1/security/attack/start", json={"count": 999_999})
    assert r.status_code == 422

    ok = client.post(
        "/api/v1/security/attack/start",
        json={"attacker": "t", "count": 2, "intensity": 1.0, "duration": 0.1},
    )
    assert ok.status_code == 200


def test_trust_threshold_is_bounded():
    client = _client()
    r = client.get("/api/v1/security/trust/high-risk", params={"threshold": 5.0})
    assert r.status_code == 422


def test_devices_listing_is_bounded_and_reports_total():
    client = _client()
    r = client.get("/api/v1/devices", params={"limit": 1})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "total" in data and "count" in data
    assert data["count"] <= 1


def test_ledger_integrity_endpoint():
    client = _client()
    r = client.get("/api/v1/security/ledger/integrity")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["data"]["valid"] is True
