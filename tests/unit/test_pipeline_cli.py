"""
Unit Tests: Typer Pipeline CLI
==============================
Tests pipeline command-line interface commands:
- bloodgrid --help
- bloodgrid status
- bloodgrid test (anomaly gate)
- bloodgrid publish (atomic database swap)
"""

from unittest.mock import MagicMock, patch
import duckdb
from typer.testing import CliRunner

from bloodgrid.pipeline.run import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "BloodGrid: National Real-time Blood Inventory Orchestrator" in result.output
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
    with patch("bloodgrid.pipeline.run.get_warehouse_connection", return_value=mem_con):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "BloodGrid Pipeline Execution History" in result.output


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
    mem_con.execute("INSERT INTO main_gold.dim_blood_banks (hospital_code, hospital_name) VALUES (1, 'H1');")
    with patch("bloodgrid.pipeline.run.get_warehouse_connection", return_value=mem_con):
        result = runner.invoke(app, ["test"])
        assert result.exit_code == 0
        assert "STEP 4: Quality & Anomaly Gate Validation" in result.output


def test_cli_publish_command(tmp_path, monkeypatch):
    # Setup dummy warehouse and serving paths
    dummy_wh = tmp_path / "blood_warehouse.duckdb"
    dummy_wh.write_text("DUMMY_WAREHOUSE")
    monkeypatch.setattr("bloodgrid.config.settings.warehouse_path", dummy_wh)
    monkeypatch.setattr("bloodgrid.config.settings.serving_path", tmp_path / "serving.duckdb")
    monkeypatch.setattr(
        "bloodgrid.config.settings.serving_staging_path", tmp_path / "serving.duckdb.tmp"
    )

    result = runner.invoke(app, ["publish"])
    assert result.exit_code == 0
    assert "STEP 5: Atomic Database Publish" in result.output
    assert "Published Serving Database" in result.output


def test_cli_scrape_command_mocked(tmp_path):
    mem_con = duckdb.connect(":memory:")
    with (
        patch("bloodgrid.pipeline.run.get_warehouse_connection", return_value=mem_con),
        patch("bloodgrid.pipeline.run.scrape_nationwide") as mock_scrape,
        patch("bloodgrid.pipeline.run.write_raw_landing") as mock_write,
        patch("bloodgrid.pipeline.run.check_run_interval_guard"),
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
        patch("bloodgrid.pipeline.run.get_warehouse_connection", return_value=mem_con),
        patch("bloodgrid.pipeline.run.ingest_landing_to_bronze", return_value=100),
        patch("bloodgrid.pipeline.run.init_warehouse_metadata_tables"),
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
        return [{"hospital_name": "Test Bank"}], {"run_id": "test_1", "scraped_at": "2026-10-14T12:00:00"}

    with (
        patch("bloodgrid.pipeline.run.get_warehouse_connection", return_value=conn_wrapper),
        patch("bloodgrid.pipeline.run.check_run_interval_guard"),
        patch("bloodgrid.pipeline.run.scrape_nationwide", side_effect=fake_scrape),
        patch("bloodgrid.pipeline.run.write_raw_landing", return_value=(tmp_path / "test.parquet", "sha123", 1)),
        patch("bloodgrid.pipeline.run.ingest_landing_to_bronze"),
        patch("bloodgrid.pipeline.run.transform"),
        patch("bloodgrid.pipeline.run.test"),
        patch("bloodgrid.pipeline.run.publish"),
        patch("bloodgrid.pipeline.run.record_pipeline_run_start"),
        patch("bloodgrid.pipeline.run.record_pipeline_run_finish"),
    ):
        result = runner.invoke(app, ["all", "--force"])
        assert result.exit_code == 0
        assert "BLOODGRID END-TO-END PIPELINE" in result.output

