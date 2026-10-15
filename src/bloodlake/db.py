"""
DuckDB Database Connection & Session Management
===============================================
Provides isolated read-only query connections for the API layer and read-write
connections for the Lakehouse ELT pipeline. Implements zero-lock replica fallback
and automatic catalog alias attachment for dbt-compiled views.
"""

import os
import duckdb
from typing import Generator
from fastapi import HTTPException
from bloodlake.config import settings


def get_serving_connection(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """
    Connects to the published serving database in read-only mode for zero-lock concurrency.
    Falls back gracefully to the warehouse database if serving.duckdb does not yet exist.
    Attaches catalog alias 'blood_warehouse' so dbt-generated views resolve without BinderError.
    """
    candidate_paths = [settings.serving_path, settings.warehouse_path]

    for path in candidate_paths:
        if path.exists():
            try:
                con = duckdb.connect(str(path), read_only=read_only)
                # Attach catalog alias so any cross-catalog dbt view references resolve
                try:
                    con.execute(f"ATTACH '{path}' AS blood_warehouse (READ_ONLY);")
                except Exception:
                    pass
                return con
            except duckdb.IOException:
                # If path has a write lock, try next candidate
                continue
            except Exception:
                continue

    raise HTTPException(
        status_code=500,
        detail="DuckDB database file not found or inaccessible. Please run pipeline first."
    )


def get_warehouse_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """
    Connects to the primary DuckDB warehouse for ETL operations (Bronze loading,
    dbt transformations, snapshot updates).
    """
    return duckdb.connect(str(settings.warehouse_path), read_only=read_only)


def get_db_session() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """FastAPI dependency yielding an isolated, auto-closing read-only DuckDB connection."""
    con = get_serving_connection(read_only=True)
    try:
        yield con
    finally:
        try:
            con.close()
        except Exception:
            pass
