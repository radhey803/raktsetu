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


def test_robots_txt_and_sitemap_xml():
    # robots.txt
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap: https://bloodgrid.in/sitemap.xml" in robots.text

    # sitemap.xml
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "<urlset" in sitemap.text
    assert "https://bloodgrid.in/blood-banks/" in sitemap.text


def test_district_seo_landing_page():
    resp = client.get("/blood-banks/gujarat/anand")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Blood Banks in Anand, Gujarat" in resp.text
    assert "schema.org" in resp.text
    assert "MedicalOrganization" in resp.text
    # Attribution notice present
    assert "Data sourced from eRaktKosh" in resp.text


def test_reports_shortages_csv_export():
    resp = client.get("/v1/reports/district-shortages.csv?state=Gujarat")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment; filename=" in resp.headers["content-disposition"]
    content = resp.text
    assert "State,District,Component,Blood_Group" in content


def test_reports_donation_camp_suggester():
    resp = client.get("/v1/reports/donation-camp-suggester?state=Gujarat&blood_group=O-")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "suggested_locations" in data
    assert len(data["suggested_locations"]) > 0
    first = data["suggested_locations"][0]
    assert "camp_priority_score" in first
    assert "recommendation" in first


def test_forecasting_stub_honest_accumulation():
    resp = client.get("/v1/reports/forecasting-stub")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DATA_ACCUMULATION_PHASE"
    assert data["feature_flag"] == "ml_forecasting_disabled"
    assert data["required_real_snapshot_days"] == 60
    assert "Synthetic or random forecasting is strictly prohibited" in data["message"]


def test_pricing_endpoint():
    resp = client.get("/v1/reports/pricing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["currency"] == "INR"
    assert "free" in data["plans"]
    assert "pro" in data["plans"]
    assert "developer" in data["plans"]
    assert "organization" in data["plans"]

