"""
eRaktKosh End-to-End Data Pipeline Orchestrator
==============================================
1. Scrapes latest blood inventory from eRaktKosh API asynchronously
2. Ingests raw data into DuckDB Bronze Layer
3. Executes dbt build (Silver & Gold models + Data Tests)
"""

import sys
import asyncio
import os
import subprocess
import time
import duckdb
from async_scraper import scrape_entire_country_async
from snapshot_manager import record_live_snapshot, seed_historical_backfill_if_empty

# Paths
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
DBT_DIR = os.path.join(WORKSPACE_DIR, "blood_project")
DB_PATH = os.path.join(WORKSPACE_DIR, "blood_warehouse.duckdb")
CSV_PATH = os.path.join(WORKSPACE_DIR, "INDIA_blood_inventory_async.csv")

def step_banner(step_num: int, title: str):
    print("\n" + "=" * 60)
    print(f"🚀 STEP {step_num}: {title}")
    print("=" * 60)

def scrape_live_data():
    step_banner(1, "Scraping Live Nationwide Blood Inventory (eRaktKosh API)")
    asyncio.run(scrape_entire_country_async())

def ingest_to_bronze():
    step_banner(2, "Ingesting Fresh Data into DuckDB Bronze Layer & Snapshot Lakehouse")
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Missing {CSV_PATH}. Scraping failed.")

    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    
    print("📥 Loading fresh CSV into bronze.raw_blood_inventory...")
    con.execute(f"""
        CREATE OR REPLACE TABLE bronze.raw_blood_inventory AS
        SELECT *, CURRENT_TIMESTAMP AS ingested_at
        FROM read_csv(
            '{CSV_PATH}',
            header = True,
            delim = ',',
            quote = '"',
            escape = '"',
            auto_detect = True,
            ignore_errors = True,
            null_padding = True
        );
    """)

    total_rows = con.execute("SELECT COUNT(*) FROM bronze.raw_blood_inventory;").fetchone()[0]
    print(f"✅ Bronze table refreshed! Total records loaded: {total_rows:,}")
    
    # BloodGrid Core Feature: Append-only Stock Snapshots & History
    print("📸 Ingesting append-only stock snapshot for time-series intelligence...")
    record_live_snapshot(con)
    seed_historical_backfill_if_empty(con, days_back=7)

    con.close()

def run_dbt_transformations():
    step_banner(3, "Running dbt Build (Transformations & Data Tests)")
    cmd = ["uv", "run", "dbt", "build"]
    
    result = subprocess.run(cmd, cwd=DBT_DIR, capture_output=False)
    if result.returncode != 0:
        raise RuntimeError("❌ dbt build failed! Check test logs above.")
    print("✅ All dbt models transformed and tests passed!")

def main():
    total_start = time.time()
    print("🩸 STARTING END-TO-END BLOOD INVENTORY PIPELINE 🩸")

    # Step 1: Live Scraping (can be skipped with --skip-scrape if offline)
    if "--skip-scrape" in sys.argv:
        print("⏩ Skipping live scraping (--skip-scrape flag passed). Using existing CSV.")
    else:
        scrape_live_data()

    # Step 2: Ingest fresh CSV to DuckDB Bronze
    ingest_to_bronze()

    # Step 3: dbt Build (Silver, Gold, Tests)
    run_dbt_transformations()

    elapsed = time.time() - total_start
    print("\n" + "🎉" * 25)
    print(f"🏆 PIPELINE EXECUTION COMPLETED IN {elapsed:.2f}s!")
    print("🎉" * 25 + "\n")

if __name__ == "__main__":
    main()
