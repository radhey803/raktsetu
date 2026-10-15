"""
BloodGrid Bronze Warehouse Loader
=================================
Loads immutable landing Parquet partitions directly into bronze.raw_inventory
without CSV round-trip formatting loss. Standardizes JSON payloads for downstream
dbt silver unnesting.
"""

import ast
import json
import logging
from pathlib import Path
from typing import Optional

import duckdb

from bloodgrid.config import settings

logger = logging.getLogger("bloodgrid.loader")


def clean_to_json_str(val: any) -> str:
    """Safely converts dict, list, or python-stringified dict into standard JSON."""
    if not val:
        return "{}"
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    if isinstance(val, str):
        val_str = val.strip()
        if val_str.startswith("{") and val_str.endswith("}"):
            try:
                # Try standard json first
                parsed = json.loads(val_str)
                return json.dumps(parsed)
            except Exception:
                try:
                    # Fallback to python literal evaluation for single-quoted dict strings
                    parsed = ast.literal_eval(val_str)
                    if isinstance(parsed, (dict, list)):
                        return json.dumps(parsed)
                except Exception:
                    pass
    return "{}"


def ingest_landing_to_bronze(
    con: duckdb.DuckDBPyConnection, parquet_path: Optional[Path] = None
) -> int:
    """
    Ingests raw Parquet file into bronze.raw_inventory.
    If parquet_path is not specified, loads the most recent Parquet file from data/landing/.
    """
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")

    target_file = parquet_path
    if not target_file:
        landing_files = sorted(settings.landing_dir.glob("dt=*/**/*.parquet"), reverse=True)
        if not landing_files:
            raise FileNotFoundError(f"No landing Parquet files found in {settings.landing_dir}")
        target_file = landing_files[0]

    logger.info("Ingesting landing file into bronze.raw_inventory: %s", target_file)

    # Create bronze.raw_inventory if it doesn't exist
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze.raw_inventory (
            run_id VARCHAR,
            scraped_at TIMESTAMP,
            hospital_code BIGINT,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            hospital_type VARCHAR,
            facility_type VARCHAR,
            hospital_contact VARCHAR,
            hospital_address VARCHAR,
            entry_date_raw VARCHAR,
            components_raw VARCHAR,
            raw_payload VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Fast insertion from Parquet
    con.execute(f"""
        INSERT INTO bronze.raw_inventory (
            run_id, scraped_at, hospital_code, hospital_name, state_name,
            district_name, hospital_type, facility_type, hospital_contact,
            hospital_address, entry_date_raw, components_raw, raw_payload
        )
        SELECT
            run_id,
            scraped_at,
            hospital_code,
            hospital_name,
            state_name,
            district_name,
            hospital_type,
            facility_type,
            hospital_contact,
            hospital_address,
            entry_date_raw,
            components_raw,
            raw_payload
        FROM read_parquet('{target_file}');
    """)

    # Count loaded records
    row_count = con.execute("SELECT COUNT(*) FROM read_parquet(?);", [str(target_file)]).fetchone()[
        0
    ]
    total_bronze = con.execute("SELECT COUNT(*) FROM bronze.raw_inventory;").fetchone()[0]

    logger.info(
        "Bronze ingestion complete: %d records added. Total bronze rows: %d",
        row_count,
        total_bronze,
    )
    return row_count
