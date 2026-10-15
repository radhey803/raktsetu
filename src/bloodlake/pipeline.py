"""
eRaktKosh Blood Lakehouse Orchestrator & CLI
============================================
Provides unified commands to execute, monitor, and validate the end-to-end
Medallion Lakehouse ELT pipeline:
- scrape: Polite nationwide crawl to immutable Parquet landing zone
- load: Direct Parquet ingestion into bronze.raw_inventory
- transform: Materialize silver and gold layers using dbt Core
- test: dbt contract tests and row-count anomaly gate (< 80% volume drop blocks publish)
- publish: Atomic swap into zero-lock serving.duckdb
- all: End-to-end automated pipeline
- status: Lakehouse sync history & health metadata
"""

import asyncio
import logging
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.table import Table

from bloodlake.config import settings
from bloodlake.db import get_warehouse_connection
from bloodlake.scraper import (
    CircuitBreakerError,
    RunIntervalGuardError,
    check_run_interval_guard,
    scrape_nationwide,
    write_landing_parquet,
)

logger = logging.getLogger("bloodlake.pipeline")
console = Console()
app = typer.Typer(
    name="bloodlake",
    help="eRaktKosh Blood Lakehouse: Nationwide ELT Pipeline & Quality Orchestrator (MCA CHARUSAT)",
    no_args_is_help=True,
)


def init_metadata_tables(con) -> None:
    """Ensures Lakehouse audit schemas and pipeline_runs tracking table exist."""
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    con.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    con.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    con.execute("""
        CREATE TABLE IF NOT EXISTS gold.pipeline_runs (
            run_id VARCHAR PRIMARY KEY,
            started_at TIMESTAMP NOT NULL,
            finished_at TIMESTAMP,
            status VARCHAR NOT NULL,
            facilities_count INTEGER DEFAULT 0,
            tests_passed BOOLEAN DEFAULT FALSE,
            error_message VARCHAR
        );
    """)


def record_run_start(con, run_id: str) -> None:
    init_metadata_tables(con)
    now = datetime.now(timezone.utc)
    con.execute("""
        INSERT INTO gold.pipeline_runs (run_id, started_at, status)
        VALUES (?, ?, 'RUNNING');
    """, [run_id, now])


def record_run_finish(
    con,
    run_id: str,
    status: str,
    facilities_count: int = 0,
    tests_passed: bool = False,
    error_message: Optional[str] = None,
) -> None:
    now = datetime.now(timezone.utc)
    con.execute("""
        UPDATE gold.pipeline_runs
        SET finished_at = ?,
            status = ?,
            facilities_count = ?,
            tests_passed = ?,
            error_message = ?
        WHERE run_id = ?;
    """, [now, status, facilities_count, tests_passed, error_message, run_id])


def get_last_successful_run(con) -> Optional[Dict[str, Any]]:
    try:
        row = con.execute("""
            SELECT run_id, started_at, finished_at, status, facilities_count, tests_passed
            FROM gold.pipeline_runs
            WHERE status = 'SUCCESS'
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()
        if row:
            return {
                "run_id": row[0],
                "started_at": row[1],
                "finished_at": row[2],
                "status": row[3],
                "facilities_count": row[4],
                "tests_passed": row[5],
            }
    except Exception:
        pass
    return None


def ingest_landing_to_bronze(con, parquet_path: Optional[Path] = None) -> int:
    """Loads immutable landing Parquet partitions directly into bronze.raw_inventory."""
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")

    target_file = parquet_path
    if not target_file:
        landing_files = sorted(settings.data_landing_dir.glob("dt=*/**/*.parquet"), reverse=True)
        if not landing_files:
            raise FileNotFoundError(f"No landing Parquet files found in {settings.data_landing_dir}")
        target_file = landing_files[0]

    logger.info("Ingesting landing file into bronze.raw_inventory: %s", target_file)

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
            raw_payload_json
        FROM read_parquet('{target_file}');
    """)

    row_count = con.execute("SELECT COUNT(*) FROM read_parquet(?);", [str(target_file)]).fetchone()[0]
    total_bronze = con.execute("SELECT COUNT(*) FROM bronze.raw_inventory;").fetchone()[0]
    logger.info("Bronze ingestion complete: %d records added. Total bronze rows: %d", row_count, total_bronze)
    return row_count


@app.command()
def scrape(
    concurrency: int = typer.Option(settings.scraper_concurrency, "--concurrency", "-c", help="Worker concurrency limit"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass minimum interval guard"),
):
    """Executes polite nationwide async crawl of eRaktKosh and writes immutable landing Parquet."""
    console.print("\n[bold red]🌐 STEP 1: Polite Nationwide Ingestion[/bold red]")
    con = get_warehouse_connection(read_only=False)
    init_metadata_tables(con)
    try:
        check_run_interval_guard(con, settings.min_run_interval_hours, force)
    finally:
        con.close()

    now = datetime.now(timezone.utc)
    run_id = f"scrape_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    try:
        records, summary = asyncio.run(scrape_nationwide(concurrency=concurrency))
        if not records:
            raise RuntimeError("Scraper returned 0 facility records.")

        parquet_path, sha256, count = write_landing_parquet(records, run_id, now)
        console.print(f"[bold green]✅ Ingestion Succeeded:[/bold green] {count:,} facilities collected.")
        console.print(f"📦 Landing File: [cyan]{parquet_path}[/cyan] (SHA-256: {sha256[:12]})")
    except CircuitBreakerError as cbe:
        console.print(f"[bold red]💥 Circuit Breaker Triggered:[/bold red] {cbe}")
        raise typer.Exit(code=2)


@app.command()
def load(
    parquet_file: Optional[Path] = typer.Option(None, "--file", "-f", help="Specific landing Parquet file to load"),
):
    """Loads landing Parquet into DuckDB bronze.raw_inventory table."""
    console.print("\n[bold red]📥 STEP 2: Ingest Landing Parquet into Bronze[/bold red]")
    con = get_warehouse_connection(read_only=False)
    init_metadata_tables(con)
    try:
        count = ingest_landing_to_bronze(con, parquet_file)
        console.print(f"[bold green]✅ Bronze Ingested:[/bold green] {count:,} records added to bronze.raw_inventory.")
    finally:
        con.close()


@app.command()
def transform():
    """Runs dbt build to compile and materialize Silver and Gold analytical marts."""
    console.print("\n[bold red]⚙️ STEP 3: dbt Build Transformations[/bold red]")
    cmd = [
        "uv",
        "run",
        "dbt",
        "build",
        "--project-dir",
        str(settings.dbt_project_dir),
        "--profiles-dir",
        str(settings.dbt_project_dir),
    ]
    result = subprocess.run(cmd, cwd=str(settings.base_dir), capture_output=False)
    if result.returncode != 0:
        console.print("[bold red]❌ dbt build failed! Review model compilation errors above.[/bold red]")
        raise typer.Exit(code=result.returncode)
    console.print("[bold green]✅ dbt models and schema tests compiled & executed successfully![/bold green]")


@app.command()
def test():
    """Validates Lakehouse data contracts and runs row-count anomaly detection."""
    console.print("\n[bold red]🔍 STEP 4: Quality & Anomaly Gate Validation[/bold red]")
    con = get_warehouse_connection(read_only=True)
    try:
        current_count = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
        prev_run = get_last_successful_run(con)
        prev_count = prev_run.get("facilities_count") if prev_run else None
    finally:
        con.close()

    console.print(f"📊 Current Reporting Facilities: [bold cyan]{current_count:,}[/bold cyan]")
    if prev_count and prev_count > 0:
        ratio = current_count / prev_count
        console.print(f"📊 Previous Run Facilities: {prev_count:,} (Ratio: {ratio:.1%})")
        if ratio < settings.min_facility_threshold_ratio:
            err_msg = (
                f"ANOMALY GATE FAILED: Facility count dropped to {ratio:.1%} of previous run "
                f"({current_count} vs {prev_count}). Threshold is {settings.min_facility_threshold_ratio:.0%}."
            )
            console.print(f"[bold red]❌ {err_msg}[/bold red]")
            raise typer.Exit(code=3)

    console.print("[bold green]✅ Anomaly gate passed! No data volume regressions detected.[/bold green]")


@app.command()
def publish():
    """Atomically publishes warehouse into zero-lock serving.duckdb database replica."""
    console.print("\n[bold red]🚀 STEP 5: Atomic Database Publish[/bold red]")
    if not settings.warehouse_path.exists():
        raise FileNotFoundError(f"Primary warehouse missing at {settings.warehouse_path}")

    shutil.copyfile(settings.warehouse_path, settings.serving_staging_path)
    os.replace(settings.serving_staging_path, settings.serving_path)
    console.print(f"[bold green]✅ Published Serving Database:[/bold green] [cyan]{settings.serving_path}[/cyan]")


@app.command()
def all(
    concurrency: int = typer.Option(settings.scraper_concurrency, "--concurrency", "-c"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass minimum interval guard"),
    skip_scrape: bool = typer.Option(False, "--skip-scrape", help="Skip scrape and transform existing bronze"),
):
    """Executes the complete production Lakehouse ELT pipeline end-to-end."""
    now = datetime.now(timezone.utc)
    run_id = f"pipeline_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    start_time = time.time()

    console.print(f"[bold magenta]🩸 BLOODLAKE END-TO-END PIPELINE: {run_id}[/bold magenta]")
    con = get_warehouse_connection(read_only=False)
    record_run_start(con, run_id)
    con.close()

    try:
        if not skip_scrape:
            con = get_warehouse_connection(read_only=False)
            check_run_interval_guard(con, settings.min_run_interval_hours, force)
            con.close()

            records, summary = asyncio.run(scrape_nationwide(concurrency=concurrency))
            if not records:
                raise RuntimeError("Scraper returned 0 facilities.")
            parquet_path, _, _ = write_landing_parquet(records, run_id, now)

            con = get_warehouse_connection(read_only=False)
            ingest_landing_to_bronze(con, parquet_path)
            con.close()
        else:
            console.print("[yellow]⏩ Skipping network scrape (--skip-scrape flag).[/yellow]")

        transform()
        test()
        publish()

        elapsed = time.time() - start_time
        con = get_warehouse_connection(read_only=False)
        facility_count = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
        record_run_finish(con, run_id, "SUCCESS", facility_count, tests_passed=True)
        con.close()

        console.print(
            f"\n[bold green]🎉 PIPELINE COMPLETED IN {elapsed:.2f}s! Facilities: {facility_count:,}[/bold green]\n"
        )
    except Exception as exc:
        con = get_warehouse_connection(read_only=False)
        record_run_finish(con, run_id, "FAILED", 0, tests_passed=False, error_message=str(exc))
        con.close()
        console.print(f"[bold red]❌ Pipeline failed: {exc}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def status():
    """Displays last successful run metadata and warehouse health status."""
    con = get_warehouse_connection(read_only=True)
    try:
        rows = con.execute("""
            SELECT run_id, started_at, finished_at, status, facilities_count, tests_passed, error_message
            FROM gold.pipeline_runs
            ORDER BY started_at DESC
            LIMIT 10;
        """).fetchall()
    except Exception:
        rows = []
    finally:
        con.close()

    if not rows:
        console.print("[yellow]No pipeline execution history found in gold.pipeline_runs.[/yellow]")
        return

    table = Table(title="BloodLake Pipeline Execution History (eRaktKosh Lakehouse)")
    table.add_column("Run ID", style="cyan")
    table.add_column("Started (UTC)", style="white")
    table.add_column("Finished (UTC)", style="white")
    table.add_column("Status", style="bold")
    table.add_column("Facilities", justify="right")
    table.add_column("Tests Passed", justify="center")

    for r in rows:
        status_style = "green" if r[3] == "SUCCESS" else "red"
        tests_str = "✅ Yes" if r[5] else "❌ No"
        table.add_row(
            r[0],
            str(r[1])[:19] if r[1] else "-",
            str(r[2])[:19] if r[2] else "-",
            f"[{status_style}]{r[3]}[/{status_style}]",
            f"{r[4]:,}" if r[4] else "0",
            tests_str,
        )

    console.print(table)


if __name__ == "__main__":
    app()
