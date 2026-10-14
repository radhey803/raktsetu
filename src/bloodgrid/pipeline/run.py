"""
BloodGrid Pipeline Orchestrator CLI
===================================
Unified command-line interface powered by Typer for end-to-end data lifecycle:
1. scrape:    Polite asynchronous crawl of eRaktKosh with source protection
2. load:      Direct ingestion of immutable Parquet landing data into Bronze
3. transform: dbt transformation into Silver and Gold analytical marts
4. test:      Data contract validation and row-count anomaly detection
5. publish:   Zero-downtime atomic swap to serving.duckdb
6. all:       Complete end-to-end pipeline run with audit tracking
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import duckdb
import typer
from rich.console import Console
from rich.table import Table

from bloodgrid.config import settings
from bloodgrid.ingestion.landing import write_raw_landing
from bloodgrid.ingestion.scraper import scrape_nationwide, CircuitBreakerError
from bloodgrid.warehouse.connection import (
    get_warehouse_connection,
    init_warehouse_metadata_tables,
    record_pipeline_run_start,
    record_pipeline_run_finish,
    get_last_successful_run,
    atomic_swap_serving_database,
)
from bloodgrid.warehouse.loader import ingest_landing_to_bronze

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bloodgrid.pipeline")
console = Console()
app = typer.Typer(help="BloodGrid: National Real-time Blood Inventory Orchestrator")


def check_run_interval_guard(con: duckdb.DuckDBPyConnection, min_hours: float, force: bool) -> None:
    """Ensures a polite interval between full national crawls."""
    if force:
        logger.info("Run interval guard bypassed with --force flag.")
        return

    last_run = get_last_successful_run(con)
    if last_run and last_run.get("finished_at"):
        finished_at = last_run["finished_at"]
        if isinstance(finished_at, str):
            finished_at = datetime.fromisoformat(finished_at)
        elapsed = datetime.utcnow() - finished_at
        if elapsed < timedelta(hours=min_hours):
            remaining = (timedelta(hours=min_hours) - elapsed).total_seconds() / 60
            err_msg = (
                f"Source Protection Guard: Last run was {elapsed.total_seconds() / 3600:.2f} hours ago. "
                f"Minimum allowed interval is {min_hours} hours. Retry in {remaining:.1f} minutes, "
                f"or pass --force to override."
            )
            console.print(f"[bold yellow]⚠️  {err_msg}[/bold yellow]")
            raise typer.Exit(code=1)


@app.command()
def scrape(
    concurrency: int = typer.Option(settings.scraper_concurrency, "--concurrency", "-c", help="Max concurrent HTTP requests"),
    timeout: int = typer.Option(settings.scraper_timeout_sec, "--timeout", "-t", help="HTTP request timeout in seconds"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass the 3-hour minimum interval guard")
):
    """Scrapes all 781 districts from eRaktKosh and writes immutable landing Parquet."""
    console.print("\n[bold red]🩸 STEP 1: Polite Nationwide Ingestion[/bold red]")
    con = get_warehouse_connection(read_only=False)
    check_run_interval_guard(con, settings.min_run_interval_hours, force)
    con.close()

    try:
        records, summary = asyncio.run(scrape_nationwide(concurrency=concurrency, timeout_sec=timeout))
        if not records:
            console.print("[bold red]❌ No records returned by scraper. Aborting.[/bold red]")
            raise typer.Exit(code=1)

        run_id = summary["run_id"]
        scraped_at = datetime.fromisoformat(summary["scraped_at"])
        parquet_path, sha256, count = write_raw_landing(records, run_id, scraped_at)

        console.print(f"[bold green]✅ Ingestion Complete:[/bold green] {count:,} facilities saved to [cyan]{parquet_path}[/cyan] (SHA: {sha256[:10]})")
        return parquet_path
    except CircuitBreakerError as cbe:
        console.print(f"[bold red]💥 Circuit Breaker Triggered:[/bold red] {cbe}")
        raise typer.Exit(code=2)


@app.command()
def load(
    parquet_file: Optional[Path] = typer.Option(None, "--file", "-f", help="Specific landing Parquet file to load")
):
    """Loads landing Parquet into DuckDB bronze.raw_inventory table."""
    console.print("\n[bold red]📥 STEP 2: Ingest Landing Parquet into Bronze[/bold red]")
    con = get_warehouse_connection(read_only=False)
    init_warehouse_metadata_tables(con)
    try:
        count = ingest_landing_to_bronze(con, parquet_file)
        console.print(f"[bold green]✅ Bronze Ingested:[/bold green] {count:,} records loaded into bronze.raw_inventory.")
    finally:
        con.close()


@app.command()
def transform():
    """Runs dbt build to compile and materialize Silver and Gold analytical marts."""
    console.print("\n[bold red]⚙️ STEP 3: dbt Build Transformations[/bold red]")
    cmd = [
        "uv", "run", "dbt", "build",
        "--project-dir", str(settings.dbt_project_dir),
        "--profiles-dir", str(settings.dbt_project_dir)
    ]
    result = subprocess.run(cmd, cwd=settings.base_dir, capture_output=False)
    if result.returncode != 0:
        console.print("[bold red]❌ dbt build failed! Review test failures above.[/bold red]")
        raise typer.Exit(code=result.returncode)
    console.print("[bold green]✅ All 47 dbt models & tests transformed successfully![/bold green]")


@app.command()
def test():
    """Runs data contract validation and facility row-count anomaly detection."""
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
        if ratio < settings.anomaly_min_facility_ratio:
            err_msg = (
                f"ANOMALY GATE FAILED: Facility count dropped to {ratio:.1%} of previous run "
                f"({current_count} vs {prev_count}). Minimum required threshold is {settings.anomaly_min_facility_ratio:.0%}."
            )
            console.print(f"[bold red]❌ {err_msg}[/bold red]")
            raise typer.Exit(code=3)

    console.print("[bold green]✅ Anomaly gate passed! No critical data volume regressions detected.[/bold green]")


@app.command()
def publish():
    """Atomically swaps validated warehouse to serving.duckdb for zero-downtime serving."""
    console.print("\n[bold red]🚀 STEP 5: Atomic Database Publish[/bold red]")
    staging_file = settings.serving_staging_path
    serving_file = settings.serving_path

    # Build clean copy for serving
    shutil.copyfile(settings.warehouse_path, staging_file)
    atomic_swap_serving_database(staging_file, serving_file)
    console.print(f"[bold green]✅ Published Serving Database:[/bold green] [cyan]{serving_file}[/cyan]")


@app.command()
def all(
    concurrency: int = typer.Option(settings.scraper_concurrency, "--concurrency", "-c"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass minimum run interval guard"),
    skip_scrape: bool = typer.Option(False, "--skip-scrape", help="Skip network scrape and build from existing bronze")
):
    """Executes the complete production pipeline from end to end."""
    run_id = f"pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.utcnow()
    start_time = time.time()

    console.print(f"[bold magenta]🩸 BLOODGRID END-TO-END PIPELINE: {run_id}[/bold magenta]")
    con = get_warehouse_connection(read_only=False)
    record_pipeline_run_start(con, run_id)
    con.close()

    try:
        # Step 1: Scrape (or skip if requested)
        if not skip_scrape:
            con = get_warehouse_connection(read_only=False)
            check_run_interval_guard(con, settings.min_run_interval_hours, force)
            con.close()

            records, summary = asyncio.run(scrape_nationwide(concurrency=concurrency))
            if not records:
                raise RuntimeError("Scraper returned 0 facilities.")
            parquet_path, _, _ = write_raw_landing(records, run_id, datetime.utcnow())

            # Step 2: Load
            con = get_warehouse_connection(read_only=False)
            ingest_landing_to_bronze(con, parquet_path)
            con.close()
        else:
            console.print("[yellow]⏩ Skipping network scrape (--skip-scrape flag).[/yellow]")

        # Step 3: dbt Build (Transform)
        transform()

        # Step 4: Quality & Anomaly Gate
        test()

        # Step 5: Atomic Publish
        publish()

        elapsed = time.time() - start_time
        con = get_warehouse_connection(read_only=False)
        facility_count = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
        record_pipeline_run_finish(con, run_id, "SUCCESS", facility_count, tests_passed=True)
        con.close()

        console.print(f"\n[bold green]🎉 PIPELINE COMPLETED IN {elapsed:.2f}s! Facilities: {facility_count:,}[/bold green]\n")

    except Exception as exc:
        con = get_warehouse_connection(read_only=False)
        record_pipeline_run_finish(con, run_id, "FAILED", 0, tests_passed=False, error_message=str(exc))
        con.close()
        console.print(f"[bold red]❌ Pipeline failed: {exc}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def status():
    """Displays last successful run metadata and warehouse health status."""
    con = get_warehouse_connection(read_only=True)
    try:
        last_run = get_last_successful_run(con)
        recent_runs = con.execute("""
            SELECT run_id, started_at, finished_at, status, facilities_count, tests_passed
            FROM gold.pipeline_runs
            ORDER BY started_at DESC
            LIMIT 5;
        """).fetchall()
    finally:
        con.close()

    table = Table(title="BloodGrid Pipeline Execution History")
    table.add_column("Run ID", style="cyan")
    table.add_column("Started", style="white")
    table.add_column("Status", style="green")
    table.add_column("Facilities", style="magenta")
    table.add_column("Tests Passed", style="yellow")

    for r in recent_runs:
        status_style = "bold green" if r[3] == "SUCCESS" else "bold red"
        table.add_row(r[0], str(r[1])[:19], f"[{status_style}]{r[3]}[/{status_style}]", str(r[4] or 0), str(r[5]))

    console.print(table)


if __name__ == "__main__":
    app()
