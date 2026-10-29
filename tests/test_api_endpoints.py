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


def test_security_status_frontend_contract():
    """Pin the ``/security/status`` shape the dashboard reads.

    The frontend reads counters and trust from ``data['security']`` and detection
    metrics from ``data['security']['analytics']``. Guard against a backend
    refactor silently blanking the charts.
    """
    app = create_app()
    client = TestClient(app)

    demo = client.post(
        "/api/v1/security/demo/access-control",
        json={"legitimate_count": 10, "ghost_count": 3},
    )
    assert demo.status_code == 200
    assert demo.json()["status"] == "ok"

    data = client.get("/api/v1/security/status").json()["data"]
    assert "security" in data
    sec = data["security"]

    for key in (
        "processed_joins",
        "processed_packets",
        "legitimate_devices",
        "ghost_nodes",
    ):
        assert isinstance(sec[key], int), key

    trust = sec["trust"]
    for key in (
        "total_devices",
        "average_trust",
        "accepted_count",
        "monitored_count",
        "rejected_count",
        "blacklisted_count",
    ):
        assert key in trust, key

    analytics = sec["analytics"]
    assert "detection_accuracy" in analytics
    assert "confusion_matrix" in analytics
    assert analytics["detector"]["versions"] == ["ghost-detector/2.0"]


def test_entrypoint_parity_routes():
    """Both backend.main:app and backend.app.main:app expose equivalent apps."""
    # Check they are FastAPI instances
    from fastapi import FastAPI

    import backend.app.main
    import backend.main
    assert isinstance(backend.main.app, FastAPI)
    assert isinstance(backend.app.main.app, FastAPI)
    # Both created by create_app
    paths1 = set(r.path for r in backend.main.app.routes if hasattr(r, 'path'))
    paths2 = set(r.path for r in backend.app.main.app.routes if hasattr(r, 'path'))
    # Should be equivalent
    assert paths1 == paths2
    assert len(paths1) > 0
