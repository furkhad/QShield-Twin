from fastapi.testclient import TestClient

from backend.main import app


def test_health_check():
    client = TestClient(app)
    resp = client.get('/api/v1/health')
    assert resp.status_code == 200
    assert resp.json().get('status') == 'ok'
    assert resp.json().get('data', {}).get('status') == 'healthy'
