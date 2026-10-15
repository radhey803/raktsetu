"""
Integration Tests: API Against Isolated Synthetic Fixture DuckDB
================================================================
Proves that backend queries execute deterministically against an isolated synthetic
test database fixture (tests/fixtures/fixture_lakehouse.duckdb).
"""

from pathlib import Path
import duckdb
import pytest
from fastapi.testclient import TestClient

from bloodlake.api.main import app
from bloodlake.db import get_db_session
from tests.fixtures.generate_fixture_db import FIXTURE_DB_PATH, create_synthetic_fixture_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_synthetic_db():
    create_synthetic_fixture_db()
    assert FIXTURE_DB_PATH.exists()


@pytest.fixture
def fixture_db_con():
    con = duckdb.connect(str(FIXTURE_DB_PATH), read_only=True)
    con.execute(f"ATTACH '{FIXTURE_DB_PATH}' AS blood_warehouse (READ_ONLY);")
    try:
        yield con
    finally:
        con.close()


def test_fixture_meta_endpoint(fixture_db_con):
    app.dependency_overrides[get_db_session] = lambda: fixture_db_con
    try:
        resp = client.get("/api/v1/meta")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_facilities"] == 2
        assert "CHARUSAT" in data["institution"]
    finally:
        app.dependency_overrides.clear()


def test_fixture_summary_endpoint(fixture_db_con):
    app.dependency_overrides[get_db_session] = lambda: fixture_db_con
    try:
        resp = client.get("/api/v1/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_banks"] == 2
        assert data["fresh_banks_24h"] == 2
        assert data["stale_banks_30d"] == 0
        assert len(data["top_states"]) == 1
        assert data["top_states"][0]["state"] == "Gujarat"
    finally:
        app.dependency_overrides.clear()


def test_fixture_availability_pure_sql(fixture_db_con):
    app.dependency_overrides[get_db_session] = lambda: fixture_db_con
    try:
        resp = client.get(
            "/api/v1/availability?state=Gujarat&district=Anand&blood_group=O-&component=Packed+Red+Blood+Cells"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        items = data["items"]
        assert any(i["hospital_code"] == 9901 and i["units"] == 15 for i in items)
        assert any(i["hospital_code"] == 9902 and i["units"] == 2 for i in items)
    finally:
        app.dependency_overrides.clear()


def test_fixture_history_multi_snapshot(fixture_db_con):
    app.dependency_overrides[get_db_session] = lambda: fixture_db_con
    try:
        resp = client.get(
            "/api/v1/history?hospital_code=9901&component=Packed+Red+Blood+Cells&blood_group=O-"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_sufficient_history"] is True
        assert len(data["points"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_fixture_district_shortages(fixture_db_con):
    app.dependency_overrides[get_db_session] = lambda: fixture_db_con
    try:
        resp = client.get("/api/v1/shortages?state=Gujarat&blood_group=O-")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        kheda = next(d for d in data if d["district_name"] == "Kheda")
        assert kheda["total_units"] == 0
        assert kheda["shortage_status"] == "HIGH_SHORTAGE"
    finally:
        app.dependency_overrides.clear()


def test_fixture_rare_blood_inventory(fixture_db_con):
    app.dependency_overrides[get_db_session] = lambda: fixture_db_con
    try:
        resp = client.get("/api/v1/rare")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["blood_group"] == "Bombay (Oh+)"
        assert data[0]["units"] == 3
        assert data[0]["hospital_code"] == 9901
    finally:
        app.dependency_overrides.clear()
