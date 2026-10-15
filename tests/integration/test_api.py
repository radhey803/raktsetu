"""
Integration Tests: eRaktKosh Blood Lakehouse API
================================================
Tests end-to-end HTTP request handling against serving DuckDB database.
"""

from fastapi.testclient import TestClient

from bloodlake.api.main import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "DuckDB" in data["database"]


def test_meta_endpoint():
    resp = client.get("/api/v1/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert "eRaktKosh Blood Lakehouse" in data["project_name"]
    assert "CHARUSAT" in data["institution"]
    assert data["total_facilities"] > 0
    assert "eRaktKosh" in data["data_source"]


def test_summary_endpoint():
    resp = client.get("/api/v1/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_banks"] > 0
    assert data["total_states"] > 0
    assert "top_states" in data
    assert len(data["top_states"]) > 0


def test_locations_endpoint():
    resp = client.get("/api/v1/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert "Gujarat" in data
    assert "Anand" in data["Gujarat"]


def test_banks_directory():
    resp = client.get("/api/v1/banks?state=Gujarat&district=Anand&page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert len(data["items"]) > 0
    first = data["items"][0]
    assert first["state_name"] == "Gujarat"
    assert first["district_name"] == "Anand"
    assert first["is_approximate_location"] is True


def test_availability_sql_search():
    resp = client.get(
        "/api/v1/availability?state=Gujarat&district=Anand&component=Packed+Red+Blood+Cells&page=1&page_size=10"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_history_trend():
    resp = client.get(
        "/api/v1/history?hospital_code=1001&component=Packed+Red+Blood+Cells&blood_group=O-"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert "has_sufficient_history" in data
    assert "message" in data


def test_district_shortages():
    resp = client.get("/api/v1/shortages?state=Gujarat&blood_group=O-")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_rare_blood():
    resp = client.get("/api/v1/rare")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_html_index_route():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
