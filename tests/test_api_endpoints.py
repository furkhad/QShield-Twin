"""API endpoint tests for core operational routes."""

from fastapi.testclient import TestClient

from backend.app import create_app


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_status_endpoint():
    app = create_app()
    client = TestClient(app)
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_version_endpoint():
    app = create_app()
    client = TestClient(app)
    r = client.get("/api/v1/version")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_system_and_research():
    app = create_app()
    client = TestClient(app)
    r1 = client.get("/api/v1/system/info")
    r2 = client.get("/api/v1/research/info")
    assert r1.status_code == 200
    assert r2.status_code == 200
