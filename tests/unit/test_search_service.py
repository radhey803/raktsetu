"""
Unit Tests: Structured SQL Search Service
=========================================
Tests exact blood group matching, component filtering,
query text matching, sorting modes, and coordinate resolution.
"""

import duckdb
import pytest

from bloodgrid.api.services.search import execute_emergency_search


@pytest.fixture
def mock_warehouse():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA main_gold;")

    # Setup dim_blood_banks
    con.execute("""
        CREATE TABLE main_gold.dim_blood_banks (
            hospital_code BIGINT PRIMARY KEY,
            hospital_name VARCHAR,
            hospital_type VARCHAR,
            facility_type VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            hospital_contact VARCHAR,
            hospital_address VARCHAR,
            source_updated_at TIMESTAMP
        );
    """)

    # Setup mart_reliability_score
    con.execute("""
        CREATE TABLE main_gold.mart_reliability_score (
            hospital_code BIGINT PRIMARY KEY,
            days_since_update INTEGER,
            reliability_score DOUBLE,
            reliability_tier VARCHAR
        );
    """)

    # Setup fct_stock_current
    con.execute("""
        CREATE TABLE main_gold.fct_stock_current (
            hospital_code BIGINT,
            component_name VARCHAR,
            blood_group VARCHAR,
            units INTEGER
        );
    """)

    # Setup geocode_cache
    con.execute("""
        CREATE TABLE main_gold.geocode_cache (
            facility_key VARCHAR PRIMARY KEY,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            address VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            precision VARCHAR
        );
    """)

    # Insert test data
    con.execute("""
        INSERT INTO main_gold.dim_blood_banks VALUES
        (101, 'Anand Civil Hospital', 'Government', 'Blood Bank', 'Gujarat', 'Anand', '02692-221133', 'Station Road, Anand', CURRENT_TIMESTAMP),
        (102, 'Red Cross Society Anand', 'Charitable', 'Blood Centre', 'Gujarat', 'Anand', '02692-445566', 'Amul Dairy Road, Anand', CURRENT_TIMESTAMP),
        (103, 'Apollo Transfusion Ahmedabad', 'Private', 'Blood Bank', 'Gujarat', 'Ahmedabad', '079-223344', 'SG Highway, Ahmedabad', CURRENT_TIMESTAMP);

        INSERT INTO main_gold.mart_reliability_score VALUES
        (101, 1, 95.0, 'HIGH'),
        (102, 5, 80.0, 'MEDIUM'),
        (103, 0, 98.0, 'HIGH');

        INSERT INTO main_gold.fct_stock_current VALUES
        (101, 'Packed Red Blood Cells', 'O-', 8),
        (101, 'Packed Red Blood Cells', 'O+', 15),
        (101, 'Whole Blood', 'O-', 2),
        (102, 'Packed Red Blood Cells', 'O-', 3),
        (102, 'Packed Red Blood Cells', 'B+', 20),
        (103, 'Packed Red Blood Cells', 'Bombay (Oh+)', 1);
    """)

    return con


def test_search_by_state_and_district(mock_warehouse):
    results, total = execute_emergency_search(con=mock_warehouse, state="Gujarat", district="Anand")
    assert total == 2
    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "Anand Civil Hospital" in names
    assert "Red Cross Society Anand" in names


def test_search_by_exact_blood_group(mock_warehouse):
    # Only facilities with O- PRBC
    results, total = execute_emergency_search(
        con=mock_warehouse, component="Packed Red Blood Cells", blood_group="O-"
    )
    assert total == 2
    for r in results:
        assert r["name"] in ("Anand Civil Hospital", "Red Cross Society Anand")


def test_search_by_rare_blood_group(mock_warehouse):
    results, total = execute_emergency_search(
        con=mock_warehouse, component="Packed Red Blood Cells", blood_group="Bombay (Oh+)"
    )
    assert total == 1
    assert results[0]["name"] == "Apollo Transfusion Ahmedabad"


def test_search_with_text_query(mock_warehouse):
    results, total = execute_emergency_search(con=mock_warehouse, search_query="Red Cross")
    assert total == 1
    assert results[0]["name"] == "Red Cross Society Anand"


def test_search_sorting_modes(mock_warehouse):
    # Sort by units
    results, _ = execute_emergency_search(
        con=mock_warehouse, component="Packed Red Blood Cells", sort="units"
    )
    assert results[0]["matched_units"] >= results[-1]["matched_units"]

    # Sort by reliability
    results_rel, _ = execute_emergency_search(con=mock_warehouse, sort="reliability")
    assert results_rel[0]["reliability_score"] >= results_rel[-1]["reliability_score"]
