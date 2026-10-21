"""
Synthetic Test Fixture Generator
================================
Creates an isolated, purely synthetic test fixture DuckDB database in tests/fixtures/
for deterministic API and pipeline integration tests.
NEVER shipped to production or serving warehouse.
"""

from pathlib import Path

import duckdb

FIXTURE_DB_PATH = Path(__file__).parent / "fixture_lakehouse.duckdb"


def create_synthetic_fixture_db(db_path: Path = FIXTURE_DB_PATH) -> Path:
    """Builds a minimal synthetic DuckDB database for integration test fixtures."""
    if db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))

    # Create schemas
    con.execute("CREATE SCHEMA IF NOT EXISTS main_gold;")

    # 1. dim_blood_banks
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

    # 2. fct_stock_current
    con.execute("""
        CREATE TABLE main_gold.fct_stock_current (
            hospital_code BIGINT,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            component_name VARCHAR,
            blood_group VARCHAR,
            units INTEGER,
            source_updated_at TIMESTAMP
        );
    """)

    # 3. fct_stock_snapshot
    con.execute("""
        CREATE TABLE main_gold.fct_stock_snapshot (
            snapshot_date DATE,
            snapshot_time TIMESTAMP,
            hospital_code BIGINT,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            component_name VARCHAR,
            blood_group VARCHAR,
            units INTEGER,
            source_updated_at TIMESTAMP
        );
    """)

    # 4. fct_state_blood_summary
    con.execute("""
        CREATE TABLE main_gold.fct_state_blood_summary (
            state_name VARCHAR PRIMARY KEY,
            active_blood_banks BIGINT,
            fresh_reporting_banks BIGINT,
            stale_reporting_banks BIGINT,
            total_units_stocked BIGINT,
            last_aggregated_at TIMESTAMP
        );
    """)

    # 5. mart_district_status
    con.execute("""
        CREATE TABLE main_gold.mart_district_status (
            state_name VARCHAR,
            district_name VARCHAR,
            component_name VARCHAR,
            blood_group VARCHAR,
            total_reporting_banks BIGINT,
            stocked_banks BIGINT,
            banks_with_zero BIGINT,
            total_units BIGINT,
            min_facility_units BIGINT,
            max_facility_units BIGINT,
            shortage_flag BOOLEAN,
            severity_score INTEGER,
            shortage_status VARCHAR
        );
    """)

    # 6. mart_reliability_score
    con.execute("""
        CREATE TABLE main_gold.mart_reliability_score (
            hospital_code BIGINT PRIMARY KEY,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            freshness_pts INTEGER,
            contact_pts INTEGER,
            completeness_pts INTEGER,
            reliability_score INTEGER,
            reliability_label VARCHAR,
            reliability_tier VARCHAR
        );
    """)

    # 7. mart_rare_blood_availability
    con.execute("""
        CREATE TABLE main_gold.mart_rare_blood_availability (
            hospital_code BIGINT,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            blood_group VARCHAR,
            component_name VARCHAR,
            units INTEGER
        );
    """)

    # 8. pipeline_runs
    con.execute("""
        CREATE TABLE IF NOT EXISTS main_gold.pipeline_runs (
            run_id VARCHAR PRIMARY KEY,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            status VARCHAR,
            facilities_scraped INTEGER,
            tests_passed INTEGER,
            notes VARCHAR
        );
    """)

    # Populate Synthetic Deterministic Rows
    con.execute("""
        INSERT INTO main_gold.dim_blood_banks VALUES
        (9901, 'Synthetic Civil Hospital', 'Govt', 'Blood Bank', 'Gujarat', 'Anand', 'Phone: 9825000001', 'Medical Campus, Anand', CURRENT_TIMESTAMP),
        (9902, 'Synthetic Red Cross Centre', 'Charitable/Vol', 'Blood Bank', 'Gujarat', 'Anand', 'Phone: 9825000002', 'Station Road, Anand', CURRENT_TIMESTAMP);

        INSERT INTO main_gold.fct_stock_current VALUES
        (9901, 'Synthetic Civil Hospital', 'Gujarat', 'Anand', 'Packed Red Blood Cells', 'O-', 15, CURRENT_TIMESTAMP),
        (9901, 'Synthetic Civil Hospital', 'Gujarat', 'Anand', 'Packed Red Blood Cells', 'O+', 45, CURRENT_TIMESTAMP),
        (9901, 'Synthetic Civil Hospital', 'Gujarat', 'Anand', 'Packed Red Blood Cells', 'B+', 30, CURRENT_TIMESTAMP),
        (9901, 'Synthetic Civil Hospital', 'Gujarat', 'Anand', 'Packed Red Blood Cells', 'Bombay (Oh+)', 3, CURRENT_TIMESTAMP),
        (9902, 'Synthetic Red Cross Centre', 'Gujarat', 'Anand', 'Packed Red Blood Cells', 'O-', 2, CURRENT_TIMESTAMP);

        INSERT INTO main_gold.fct_stock_snapshot VALUES
        (CURRENT_DATE - INTERVAL 1 DAY, CURRENT_TIMESTAMP - INTERVAL 1 DAY, 9901, 'Synthetic Civil Hospital', 'Gujarat', 'Anand', 'Packed Red Blood Cells', 'O-', 18, CURRENT_TIMESTAMP - INTERVAL 1 DAY),
        (CURRENT_DATE, CURRENT_TIMESTAMP, 9901, 'Synthetic Civil Hospital', 'Gujarat', 'Anand', 'Packed Red Blood Cells', 'O-', 15, CURRENT_TIMESTAMP);

        INSERT INTO main_gold.fct_state_blood_summary VALUES
        ('Gujarat', 2, 2, 0, 95, CURRENT_TIMESTAMP);

        INSERT INTO main_gold.mart_district_status VALUES
        ('Gujarat', 'Anand', 'Packed Red Blood Cells', 'O-', 2, 2, 0, 17, 2, 15, false, 10, 'NORMAL'),
        ('Gujarat', 'Kheda', 'Packed Red Blood Cells', 'O-', 1, 0, 1, 0, 0, 0, true, 100, 'HIGH_SHORTAGE');

        INSERT INTO main_gold.mart_reliability_score VALUES
        (9901, 'Synthetic Civil Hospital', 'Gujarat', 'Anand', 50, 25, 25, 100, 'High', 'High'),
        (9902, 'Synthetic Red Cross Centre', 'Gujarat', 'Anand', 50, 25, 15, 90, 'High', 'High');

        INSERT INTO main_gold.mart_rare_blood_availability VALUES
        (9901, 'Synthetic Civil Hospital', 'Gujarat', 'Anand', 'Bombay (Oh+)', 'Packed Red Blood Cells', 3);

        INSERT INTO main_gold.pipeline_runs VALUES
        ('run_syn_001', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'SUCCESS', 2, 35, 'Synthetic Fixture Run');
    """)

    con.close()
    return db_path


if __name__ == "__main__":
    p = create_synthetic_fixture_db()
    print(f"✅ Generated synthetic fixture DB: {p}")
