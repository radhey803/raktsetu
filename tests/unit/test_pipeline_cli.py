"""
Unit Tests: Typer Pipeline CLI
==============================
Tests pipeline command-line interface commands:
- bloodlake --help
- bloodlake status
- bloodlake test (anomaly gate)
- bloodlake publish (atomic database swap)
- bloodlake scrape (polite nationwide crawler)
- bloodlake load (bronze ingestion)
- bloodlake transform (dbt build)
- bloodlake all (end-to-end orchestration)
"""

from unittest.mock import MagicMock, patch

import duckdb
from typer.testing import CliRunner

from bloodlake.pipeline import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "eRaktKosh Blood Lakehouse" in result.output
    assert "scrape" in result.output
    assert "load" in result.output
    assert "transform" in result.output
    assert "test" in result.output
    assert "publish" in result.output
    assert "status" in result.output


def test_cli_status():
    mem_con = duckdb.connect(":memory:")
    mem_con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    mem_con.execute("""
        CREATE TABLE gold.pipeline_runs (
            run_id VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP,
            status VARCHAR, facilities_count INTEGER, tests_passed BOOLEAN, error_message VARCHAR
        );
    """)
    mem_con.execute("""
        INSERT INTO gold.pipeline_runs VALUES ('run_001', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'SUCCESS', 4692, TRUE, NULL);
    """)
    with patch("bloodlake.pipeline.get_warehouse_connection", return_value=mem_con):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "BloodLake Pipeline Execution History" in result.output


def test_cli_test_anomaly_gate():
    mem_con = duckdb.connect(":memory:")
    mem_con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    mem_con.execute("""
        CREATE TABLE gold.pipeline_runs (
            run_id VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP,
            status VARCHAR, facilities_count INTEGER, tests_passed BOOLEAN, error_message VARCHAR
        );
    """)
    mem_con.execute("CREATE SCHEMA IF NOT EXISTS main_gold;")
    mem_con.execute("""
        CREATE TABLE main_gold.dim_blood_banks (
            hospital_code BIGINT, hospital_name VARCHAR, hospital_type VARCHAR,
            facility_type VARCHAR, state_name VARCHAR, district_name VARCHAR,
            hospital_contact VARCHAR, hospital_address VARCHAR, source_updated_at TIMESTAMP
        );
    """)
    mem_con.execute(
        "INSERT INTO main_gold.dim_blood_banks (hospital_code, hospital_name) VALUES (1, 'H1');"
    )
    with patch("bloodlake.pipeline.get_warehouse_connection", return_value=mem_con):
        result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        assert "STEP 4: Quality & Anomaly Gate Validation" in result.output


def test_cli_publish_command(tmp_path, monkeypatch):
    dummy_wh = tmp_path / "blood_warehouse.duckdb"
    dummy_wh.write_text("DUMMY_WAREHOUSE")
    monkeypatch.setattr("bloodlake.config.settings.warehouse_path", dummy_wh)
    monkeypatch.setattr("bloodlake.config.settings.serving_path", tmp_path / "serving.duckdb")
    monkeypatch.setattr(
        "bloodlake.config.settings.serving_staging_path", tmp_path / "serving.duckdb.tmp"
    )

    result = runner.invoke(app, ["publish"])
    assert result.exit_code == 0
    assert "STEP 5: Atomic Database Publish" in result.output
    assert "Published Serving Database" in result.output


def test_cli_scrape_command_mocked(tmp_path):
    mem_con = duckdb.connect(":memory:")
    with (
        patch("bloodlake.pipeline.get_warehouse_connection", return_value=mem_con),
        patch("bloodlake.pipeline.scrape_nationwide") as mock_scrape,
        patch("bloodlake.pipeline.write_landing_parquet") as mock_write,
        patch("bloodlake.pipeline.check_run_interval_guard"),
    ):

        async def fake_scrape(*args, **kwargs):
            return [{"hospital_name": "Test Bank"}], {
                "run_id": "test_1",
                "scraped_at": "2026-10-14T12:00:00",
            }

        mock_scrape.side_effect = fake_scrape
        mock_write.return_value = (tmp_path / "test.parquet", "sha123", 1)

        result = runner.invoke(app, ["scrape", "--force"])
        assert result.exit_code == 0
        assert "STEP 1: Polite Nationwide Ingestion" in result.output


def test_cli_load_command_mocked(tmp_path):
    mem_con = duckdb.connect(":memory:")
    with (
        patch("bloodlake.pipeline.get_warehouse_connection", return_value=mem_con),
        patch("bloodlake.pipeline.ingest_landing_to_bronze", return_value=100),
        patch("bloodlake.pipeline.init_metadata_tables"),
    ):
        result = runner.invoke(app, ["load"])
        assert result.exit_code == 0
        assert "STEP 2: Ingest Landing Parquet into Bronze" in result.output


def test_cli_transform_command_mocked():
    with patch("subprocess.run") as mock_sub:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_sub.return_value = mock_res

        result = runner.invoke(app, ["transform"])
        assert result.exit_code == 0
        assert "STEP 3: dbt Build Transformations" in result.output


def test_cli_all_command_mocked(tmp_path):
    real_mem_con = duckdb.connect(":memory:")
    real_mem_con.execute("CREATE SCHEMA IF NOT EXISTS main_gold;")
    real_mem_con.execute("CREATE TABLE main_gold.dim_blood_banks (id INT);")
    real_mem_con.execute("INSERT INTO main_gold.dim_blood_banks VALUES (1);")

    class ResilientConn:
        def __init__(self, con):
            self._con = con

        def close(self):
            pass

        def __getattr__(self, item):
            return getattr(self._con, item)

    conn_wrapper = ResilientConn(real_mem_con)

    async def fake_scrape(*args, **kwargs):
        return [{"hospital_name": "Test Bank"}], {
            "run_id": "test_1",
            "scraped_at": "2026-10-14T12:00:00",
        }

    with (
        patch("bloodlake.pipeline.get_warehouse_connection", return_value=conn_wrapper),
        patch("bloodlake.pipeline.check_run_interval_guard"),
        patch("bloodlake.pipeline.scrape_nationwide", side_effect=fake_scrape),
        patch(
            "bloodlake.pipeline.write_landing_parquet",
            return_value=(tmp_path / "test.parquet", "sha123", 1),
        ),
        patch("bloodlake.pipeline.ingest_landing_to_bronze"),
        patch("bloodlake.pipeline.transform"),
        patch("bloodlake.pipeline.test"),
        patch("bloodlake.pipeline.publish"),
        patch("bloodlake.pipeline.record_run_start"),
        patch("bloodlake.pipeline.record_run_finish"),
    ):
        result = runner.invoke(app, ["all", "--force"])
        assert result.exit_code == 0
        assert "BLOODLAKE END-TO-END PIPELINE" in result.output
