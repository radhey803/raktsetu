"""
Unit Tests: Warehouse Loader & Pipeline Tracking
================================================
Tests bronze parquet ingestion and pipeline run tracking.
"""

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from bloodlake.pipeline import (
    get_last_successful_run,
    init_metadata_tables,
    ingest_landing_to_bronze,
    record_run_finish,
    record_run_start,
)


def test_warehouse_pipeline_run_tracking():
    con = duckdb.connect(":memory:")
    init_metadata_tables(con)

    run_id = "run_test_track_001"
    record_run_start(con, run_id)

    status = con.execute(
        "SELECT status FROM gold.pipeline_runs WHERE run_id = ?;", [run_id]
    ).fetchone()[0]
    assert status == "RUNNING"

    record_run_finish(
        con, run_id=run_id, status="SUCCESS", facilities_count=4681, tests_passed=True
    )

    last_run = get_last_successful_run(con)
    assert last_run is not None
    assert last_run["run_id"] == run_id
    assert last_run["facilities_count"] == 4681
    assert last_run["tests_passed"] is True


def test_ingest_landing_to_bronze(tmp_path):
    parquet_path = tmp_path / "test_inventory.parquet"

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
            "raw_payload_json",
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
