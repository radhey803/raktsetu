"""
Integration Tests: BloodGrid API
================================
Validates all public, v1, and authentication endpoints against the serving DuckDB database.
"""

import pytest
from starlette.testclient import TestClient

from bloodgrid.api.main import app

client = TestClient(app)


def test_healthz_and_readyz():
    resp_health = client.get("/healthz")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "ok"

    resp_ready = client.get("/readyz")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["status"] == "ready"


def test_api_summary():
    resp = client.get("/api/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_banks" in data
    assert data["total_banks"] > 0
    assert "top_states" in data
    assert len(data["top_states"]) > 0
    assert "source_attribution" in data


def test_api_locations():
    resp = client.get("/api/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert len(data) > 0
    # Check Gujarat is present
    assert any("gujarat" in k.lower() for k in data.keys())


def test_api_search_emergency():
    resp = client.get("/api/search?state=Gujarat&district=Anand&component=Packed+Red+Blood+Cells")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "hospitals" in data
    if data["count"] > 0:
        first = data["hospitals"][0]
        assert "name" in first
        assert "reliability_score" in first
        assert "precision" in first


def test_v1_meta():
    resp = client.get("/v1/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "total_reporting_facilities" in data["data"]
    assert data["data"]["total_reporting_facilities"] > 0
    assert "source_attribution" in data["data"]


def test_v1_banks_listing():
    resp = client.get("/v1/banks?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]) <= 5
    assert "pagination" in data


def test_v1_rare_blood_radar():
    resp = client.get("/v1/rare?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data
    assert len(data["data"]) > 0
    # Every returned row must be Bombay or Rh-negative
    for r in data["data"]:
        assert r["blood_group"] in ("Bombay (Oh+)", "Bombay (Oh-)", "O-", "A-", "B-", "AB-")


def test_v1_shortages_feed():
    resp = client.get("/v1/shortages?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data


def test_user_registration_and_login():
    email = "doctor_test@example.com"
    pwd = "StrongPassword123!"

    # 1. Register
    reg_resp = client.post("/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "full_name": "Dr. Ramesh Patel",
        "organization_name": "Apollo Clinic"
    })
    assert reg_resp.status_code in (200, 409)  # 200 or 409 if already registered

    # 2. Login
    login_resp = client.post("/v1/auth/login", json={
        "email": email,
        "password": pwd
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["success"] is True
    assert "tokens" in login_data
    assert "access_token" in login_data["tokens"]
