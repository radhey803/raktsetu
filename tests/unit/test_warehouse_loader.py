"""
Unit Tests: Warehouse Loader & Connection Utilities
===================================================
Tests bronze parquet ingestion, clean JSON serialization,
pipeline run tracking, and zero-downtime atomic swap.
"""

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from bloodgrid.warehouse.connection import (
    atomic_swap_serving_database,
    get_last_successful_run,
    init_warehouse_metadata_tables,
    record_pipeline_run_finish,
    record_pipeline_run_start,
)
from bloodgrid.warehouse.loader import clean_to_json_str, ingest_landing_to_bronze


def test_clean_to_json_str():
    assert clean_to_json_str(None) == "{}"
    assert clean_to_json_str("") == "{}"
    assert clean_to_json_str({"A+": 10}) == '{"A+": 10}'
    assert clean_to_json_str('{"B+": 5}') == '{"B+": 5}'
    # Single-quoted string dict
    assert clean_to_json_str("{'O-': 2}") == '{"O-": 2}'


def test_warehouse_pipeline_run_tracking():
    con = duckdb.connect(":memory:")
    init_warehouse_metadata_tables(con)

    run_id = "run_test_track_001"
    record_pipeline_run_start(con, run_id)

    # Check status is running
    status = con.execute(
        "SELECT status FROM gold.pipeline_runs WHERE run_id = ?;", [run_id]
    ).fetchone()[0]
    assert status == "RUNNING"

    # Finish run
    record_pipeline_run_finish(
        con, run_id=run_id, status="SUCCESS", facilities_count=4681, tests_passed=True
    )

    last_run = get_last_successful_run(con)
    assert last_run is not None
    assert last_run["run_id"] == run_id
    assert last_run["facilities_count"] == 4681
    assert last_run["tests_passed"] is True


def test_ingest_landing_to_bronze(tmp_path):
    parquet_path = tmp_path / "test_inventory.parquet"

    # Create dummy parquet
    tbl = pa.Table.from_arrays(
        [
            pa.array(["run_001"]),
            pa.array([None], type=pa.timestamp("us")),
            pa.array([9001], type=pa.int64()),
            pa.array(["Hospital XYZ"]),
            pa.array(["Gujarat"]),
            pa.array(["Anand"]),
            pa.array(["Government"]),
            pa.array(["Blood Bank"]),
            pa.array(["02692-111111"]),
            pa.array(["Address 123"]),
            pa.array(["14-Oct-2026"]),
            pa.array(['{"PRBC": 10}']),
            pa.array(['{"raw": true}']),
        ],
        names=[
            "run_id",
            "scraped_at",
            "hospital_code",
            "hospital_name",
            "state_name",
            "district_name",
            "hospital_type",
            "facility_type",
            "hospital_contact",
            "hospital_address",
            "entry_date_raw",
            "components_raw",
            "raw_payload",
        ],
    )
    pq.write_table(tbl, parquet_path)

    con = duckdb.connect(":memory:")
    count = ingest_landing_to_bronze(con, parquet_path=parquet_path)
    assert count == 1

    bronze_rows = con.execute(
        "SELECT hospital_name, district_name FROM bronze.raw_inventory;"
    ).fetchall()
    assert len(bronze_rows) == 1
    assert bronze_rows[0][0] == "Hospital XYZ"
    assert bronze_rows[0][1] == "Anand"


def test_atomic_swap_serving_database(tmp_path):
    staging_file = tmp_path / "serving.duckdb.tmp"
    staging_file.write_text("STAGING_DATABASE_CONTENT")

    target_file = tmp_path / "serving.duckdb"
    target_file.write_text("OLD_SERVING_CONTENT")

    atomic_swap_serving_database(staging_file, target_file)

    assert not staging_file.exists()
    assert target_file.exists()
    assert target_file.read_text() == "STAGING_DATABASE_CONTENT"

    # Backup file created
    backup_file = target_file.with_suffix(".duckdb.bak")
    assert backup_file.exists()
    assert backup_file.read_text() == "OLD_SERVING_CONTENT"
