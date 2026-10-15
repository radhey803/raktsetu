"""
Integration Tests: V1 REST API & Public Endpoints
==================================================
Tests detailed facility profile retrieval, stock availability filtering,
historical trend series, and district trend summaries.
"""

from starlette.testclient import TestClient

from bloodgrid.api.main import app

client = TestClient(app)


def test_v1_bank_profile_detail():
    # 1. Fetch listing to get a real hospital code
    list_resp = client.get("/v1/banks?limit=1")
    assert list_resp.status_code == 200
    banks = list_resp.json()["data"]
    assert len(banks) > 0
    hcode = banks[0]["hospital_code"]

    # 2. Query specific bank profile
    detail_resp = client.get(f"/v1/banks/{hcode}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert data["success"] is True
    facility = data["data"]
    assert facility["hospital_code"] == hcode
    assert "reliability" in facility
    assert "stock_matrix" in facility


def test_v1_bank_profile_not_found():
    resp = client.get("/v1/banks/99999999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_v1_availability_search():
    resp = client.get(
        "/v1/availability?state=Gujarat&district=Anand&component=Packed%20Red%20Blood%20Cells&limit=5"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data
    assert "pagination" in data
    assert "source_attribution" in data
    assert len(data["data"]) > 0


def test_api_history_endpoint():
    list_resp = client.get("/v1/banks?limit=1")
    hcode = list_resp.json()["data"][0]["hospital_code"]

    resp = client.get(
        f"/api/history?hospital_code={hcode}&component=Packed%20Red%20Blood%20Cells&days=7"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "series" in data
    assert "dates" in data
    assert "summary" in data


def test_api_district_trends():
    resp = client.get("/api/district-trends?state=Gujarat&district=Anand")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "Gujarat"
    assert data["district"] == "Anand"
    assert "dates" in data
    assert "total_units" in data
    assert "stocked_banks" in data
