"""
BloodGrid Warehouse Connection & Lifecycle Manager
==================================================
Manages DuckDB warehouse connections, metadata tables (pipeline_runs, geocode_cache),
and zero-downtime atomic blue/green serving database swaps.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import duckdb

from bloodgrid.config import settings

logger = logging.getLogger("bloodgrid.warehouse")


def get_warehouse_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Returns a connection to the primary analytical warehouse (blood_warehouse.duckdb)."""
    return duckdb.connect(str(settings.warehouse_path), read_only=read_only)


def get_serving_connection() -> duckdb.DuckDBPyConnection:
    """Returns a connection to the atomic serving database (serving.duckdb) in read-only mode."""
    target_path = (
        settings.serving_path if settings.serving_path.exists() else settings.warehouse_path
    )
    if not target_path.exists():
        raise FileNotFoundError(
            f"Serving database file not found at {target_path}. Run pipeline first."
        )
    return duckdb.connect(str(target_path), read_only=True)


def init_warehouse_metadata_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Creates pipeline_runs, geocode_cache, and base schema tables if they do not exist."""
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    con.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")

    # Pipeline run execution metadata
    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.pipeline_runs (
            run_id VARCHAR PRIMARY KEY,
            started_at TIMESTAMP NOT NULL,
            finished_at TIMESTAMP,
            status VARCHAR NOT NULL,
            facilities_count INTEGER,
            tests_passed BOOLEAN,
            error_message VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Geocoding cache to prevent redundant Nominatim lookups
    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.geocode_cache (
            facility_key VARCHAR PRIMARY KEY,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            address VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            precision VARCHAR,
            geocoded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


def record_pipeline_run_start(con: duckdb.DuckDBPyConnection, run_id: str) -> None:
    """Records the beginning of a pipeline run."""
    init_warehouse_metadata_tables(con)
    con.execute(
        """
        INSERT INTO gold.pipeline_runs (run_id, started_at, status)
        VALUES (?, CURRENT_TIMESTAMP, 'RUNNING');
    """,
        [run_id],
    )


def record_pipeline_run_finish(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
    status: str,
    facilities_count: int,
    tests_passed: bool,
    error_message: Optional[str] = None,
) -> None:
    """Records completion status of a pipeline run."""
    con.execute(
        """
        UPDATE gold.pipeline_runs
        SET finished_at = CURRENT_TIMESTAMP,
            status = ?,
            facilities_count = ?,
            tests_passed = ?,
            error_message = ?
        WHERE run_id = ?;
    """,
        [status, facilities_count, tests_passed, error_message, run_id],
    )


def get_last_successful_run(con: duckdb.DuckDBPyConnection) -> Optional[Dict[str, Any]]:
    """Retrieves metadata of the most recent successful pipeline execution."""
    try:
        row = con.execute("""
            SELECT run_id, started_at, finished_at, facilities_count, tests_passed
            FROM gold.pipeline_runs
            WHERE status = 'SUCCESS' AND tests_passed = TRUE
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()

        if not row:
            return None

        return {
            "run_id": row[0],
            "started_at": row[1],
            "finished_at": row[2],
            "facilities_count": row[3],
            "tests_passed": row[4],
        }
    except Exception:
        return None


def atomic_swap_serving_database(staging_path: Path, target_path: Path) -> None:
    """
    Atomically swaps the staging database into serving position.
    Ensures readers never read a partially built or locked database.
    """
    if not staging_path.exists():
        raise FileNotFoundError(f"Staging file {staging_path} does not exist for atomic swap.")

    # In Linux, os.replace is atomic on the same filesystem
    backup_path = target_path.with_suffix(".duckdb.bak")
    if target_path.exists():
        try:
            shutil.copyfile(target_path, backup_path)
        except Exception as e:
            logger.warning("Could not create pre-swap backup: %s", e)

    os.replace(staging_path, target_path)
    logger.info("Atomic swap complete: %s -> %s", staging_path.name, target_path.name)
