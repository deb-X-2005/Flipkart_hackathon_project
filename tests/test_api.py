import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


DEMO_PASSWORDS = {"viewer": "viewer123", "operator": "operator123", "admin": "admin123"}


def _token(role: str = "operator") -> str:
    r = client.post("/auth/login", json={"username": role, "password": DEMO_PASSWORDS[role]})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(role: str = "operator") -> dict:
    return {"Authorization": f"Bearer {_token(role)}"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_login_issues_jwt():
    r = client.post("/auth/login", json={"username": "operator", "password": "operator123"})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body and body["expires_in"] > 0


def test_login_rejects_bad_password():
    r = client.post("/auth/login", json={"username": "operator", "password": "wrong"})
    assert r.status_code == 401


def test_login_requires_password():
    r = client.post("/auth/login", json={"username": "x"})
    assert r.status_code == 400


def test_metrics_requires_auth():
    assert client.get("/metrics").status_code == 401


def test_metrics_with_token():
    r = client.get("/metrics", headers=_hdr())
    assert r.status_code == 200
    assert r.json()["total_events"] > 0


def test_forecast_viewer_forbidden():
    r = client.post("/forecast", headers=_hdr("viewer"),
                    json={"event_cause": "construction"})
    assert r.status_code == 403


def test_forecast_operator_ok():
    r = client.post("/forecast", headers=_hdr("operator"),
                    json={"event_cause": "vip_movement", "corridor": "Mysore Road", "hour": 18})
    assert r.status_code == 200
    p = r.json()["closure_prob"]
    assert 0.0 <= p <= 1.0


def test_erasure_operator_forbidden():
    r = client.delete("/events/does-not-exist", headers=_hdr("operator"))
    assert r.status_code == 403


def test_events_pagination_and_role_classification():
    r_viewer = client.get("/events?limit=1", headers=_hdr("viewer"))
    r_op     = client.get("/events?limit=1", headers=_hdr("operator"))
    assert r_viewer.status_code == 200 and r_op.status_code == 200
    v_keys = set(r_viewer.json()["items"][0].keys())
    o_keys = set(r_op.json()["items"][0].keys())
    assert "address" not in v_keys
    # operator should see at least the public viewer fields, possibly more
    assert v_keys.issubset(o_keys) or len(o_keys) > len(v_keys)
