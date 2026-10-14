# DuckDB & dbt-duckdb: The Complete Masterclass Guide

> **Target Audience:** Modern Data Engineers, Analytics Engineers, and Students  
> **Environment:** Arch Linux, Python (`uv`), Local & Cloud Modern Data Stack  

---

## Table of Contents
1. [What is DuckDB?](#1-what-is-duckdb)
   - [Why is it called the "SQLite for Analytics"?](#why-is-it-called-the-sqlite-for-analytics)
   - [Row-Oriented (Postgres/SQLite) vs. Column-Oriented (DuckDB)](#row-oriented-vs-column-oriented)
   - [Vectorized Execution Engine](#vectorized-execution-engine)
2. [Installation Guide](#2-installation-guide)
   - [Installing DuckDB CLI on Arch Linux](#installing-duckdb-cli-on-arch-linux)
   - [Installing DuckDB in Python using `uv`](#installing-duckdb-in-python-using-uv)
   - [GUI Tools & IDE Extensions](#gui-tools--ide-extensions)
3. [DuckDB CLI Masterclass & Dot Commands](#3-duckdb-cli-masterclass--dot-commands)
   - [Starting the CLI](#starting-the-cli)
   - [Essential Dot Commands Reference](#essential-dot-commands-reference)
4. [DuckDB SQL Superpowers & Advanced Syntax](#4-duckdb-sql-superpowers--advanced-syntax)
   - [Querying Files Directly (Zero Ingestion)](#querying-files-directly-zero-ingestion)
   - [Ingesting CSV into Persistent Tables](#ingesting-csv-into-persistent-tables)
   - [Exporting Data to Parquet & CSV](#exporting-data-to-parquet--csv)
   - [Friendly SQL: `SELECT * EXCLUDE / REPLACE`](#friendly-sql-select--exclude--replace)
   - [`QUALIFY` Clause (Deduplication without Subqueries)](#qualify-clause-deduplication-without-subqueries)
   - [`PIVOT` and `UNPIVOT`](#pivot-and-unpivot)
   - [Handling Nested JSON and Structs](#handling-nested-json-and-structs)
5. [DuckDB Python API Masterclass](#5-duckdb-python-api-masterclass)
   - [Basic Querying and In-Memory Execution](#basic-querying-and-in-memory-execution)
   - [Zero-Copy Integration with Pandas, Polars, and Arrow](#zero-copy-integration-with-pandas-polars-and-arrow)
   - [Persistent Database Storage](#persistent-database-storage)
6. [DuckDB Extensions System](#6-duckdb-extensions-system)
   - [`httpfs` (Query Remote S3 / HTTPS Files)](#httpfs-query-remote-s3--https-files)
   - [`postgres_scanner` & `sqlite_scanner`](#postgres_scanner--sqlite_scanner)
7. [What is `dbt-duckdb`?](#7-what-is-dbt-duckdb)
   - [Why does `dbt-duckdb` exist?](#why-does-dbt-duckdb-exist)
   - [How `dbt-duckdb` Transforms Local Data Engineering](#how-dbt-duckdb-transforms-local-data-engineering)
   - [Architecture: Local DuckDB vs. Cloud MotherDuck](#architecture-local-duckdb-vs-cloud-motherduck)
8. [Configuring `dbt-duckdb` Step-by-Step](#8-configuring-dbt-duckdb-step-by-step)
   - [Installation](#installation)
   - [Configuring `profiles.yml`](#configuring-profilesyml)
   - [Connecting to Raw CSVs or External Sources](#connecting-to-raw-csvs-or-external-sources)
   - [Writing Your First Model (Bronze $\rightarrow$ Silver $\rightarrow$ Gold)](#writing-your-first-model)
9. [Performance Tuning & Production Best Practices](#9-performance-tuning--production-best-practices)
10. [Quick Command Cheatsheet](#10-quick-command-cheatsheet)

---

## 1. What is DuckDB?

**DuckDB** is an open-source, embedded, columnar, analytical database (OLAP) engine. Think of it as **SQLite, but designed specifically for data analysis, aggregations, data warehousing, and fast reporting**.

### Why is it called the "SQLite for Analytics"?

| Feature | SQLite | PostgreSQL / MySQL | DuckDB |
| :--- | :--- | :--- | :--- |
| **Type** | In-process (Embedded) | Client-Server | **In-process (Embedded)** |
| **Storage Layout** | Row-oriented | Row-oriented | **Column-oriented** |
| **Best Used For** | Mobile apps, simple OLTP | Production transactional backends | **Analytics, BI, Data Pipelines, dbt** |
| **Installation** | Single binary or library | Background service / daemon | **Single binary or library (`uv add duckdb`)** |
| **Multi-Million Row Aggregation** | Slow (seconds to minutes) | Medium (seconds) | **Instant (milliseconds)** |

### Row-Oriented vs. Column-Oriented

- **Row-Oriented (Postgres, SQLite):** Stores data row by row:
  `[Row 1: ID, Name, BloodGroup, Units] -> [Row 2: ID, Name, BloodGroup, Units]`
  *Great for:* `INSERT INTO ...` or `SELECT * FROM users WHERE id = 10`.
- **Column-Oriented (DuckDB, Snowflake, BigQuery):** Stores data column by column:
  `[IDs: 1, 2, 3...] | [BloodGroups: A+, B+, O+...] | [Units: 10, 4, 18...]`
  *Great for analytics:* When you run `SELECT BloodGroup, SUM(Units) GROUP BY BloodGroup`, DuckDB **only reads the 2 needed columns from disk**, ignoring the other 50 columns entirely.

### Vectorized Execution Engine
DuckDB processes data in **vectors (batches of ~2048 values)** utilizing modern CPU SIMD (Single Instruction, Multiple Data) instructions and multi-core parallelism. It runs at the theoretical speed limit of modern hardware.

---

## 2. Installation Guide

### Installing DuckDB CLI on Arch Linux

On Arch Linux, you can install the official standalone DuckDB CLI using `pacman`:

```bash
sudo pacman -S duckdb
```

Verify the installation:
```bash
duckdb --version
```

### Installing DuckDB in Python using `uv`

Inside your project virtual environment:

```bash
# Install core DuckDB python library
uv add duckdb

# Install dbt with DuckDB adapter
uv add dbt-duckdb
```

### GUI Tools & IDE Extensions
If you prefer a visual interface for querying DuckDB files:
1. **Harlequin (Terminal GUI for DuckDB):**
   ```bash
   uv add harlequin
   uv run harlequin blood_warehouse.duckdb
   ```
2. **DBeaver / DataGrip:** Community drivers for DuckDB exist natively.
3. **VS Code / Antigravity IDE Extension:** Search for `DuckDB SQL Tools` in the Extensions marketplace.

---

## 3. DuckDB CLI Masterclass & Dot Commands

### Starting the CLI

```bash
# 1. In-memory temporary session (data disappears on exit)
duckdb

# 2. Open or create a persistent database file
duckdb blood_warehouse.duckdb

# 3. Open in Read-Only mode (safe for concurrently reading files)
duckdb -readonly blood_warehouse.duckdb
```

### Essential Dot Commands Reference

Inside the `duckdb` interactive shell, special meta-commands start with a dot (`.`):

| Command | Description | Example |
| :--- | :--- | :--- |
| `.help` | Show all available dot commands | `.help` |
| `.open <path>` | Open or switch to a database file | `.open warehouse.duckdb` |
| `.tables` | List all tables and views in current database | `.tables` |
| `.schema <table>` | Show the `CREATE TABLE` DDL of a table | `.schema raw_blood_inventory` |
| `.mode <format>` | Change output formatting (`box`, `csv`, `markdown`, `json`, `line`) | `.mode markdown` |
| `.timer on / off` | Display query execution time | `.timer on` |
| `.output <file>` | Redirect query output to an external file | `.output summary.csv` |
| `.output stdout` | Reset output back to screen | `.output stdout` |
| `.import <file> <table>` | Import CSV into a table | `.import data.csv my_table` |
| `.read <file.sql>` | Execute SQL commands from a `.sql` script file | `.read build_marts.sql` |
| `.exit` or `.quit` | Exit the CLI shell | `.exit` |

---

## 4. DuckDB SQL Superpowers & Advanced Syntax

### Querying Files Directly (Zero Ingestion)
You do **not** need to create a table before querying data. DuckDB can read directly from raw files:

```sql
-- Query CSV directly with automatic header and type detection
SELECT * 
FROM 'INDIA_blood_inventory_async.csv' 
LIMIT 5;

-- Filter directly from CSV
SELECT state_name, count(*) as count 
FROM 'INDIA_blood_inventory_async.csv'
GROUP BY state_name 
ORDER BY count DESC;

-- Query Parquet directly
SELECT * FROM 'data/*.parquet';

-- Query JSON directly
SELECT * FROM read_json_auto('eraktkosh_all_metadata.json');
```

### Ingesting CSV into Persistent Tables

```sql
-- 1. Create table by auto-detecting schema from CSV
CREATE TABLE bronze_blood_raw AS 
SELECT * FROM read_csv_auto('INDIA_blood_inventory_async.csv');

-- 2. Create table with custom CSV reading parameters
CREATE TABLE bronze_blood_raw AS 
SELECT * FROM read_csv('INDIA_blood_inventory_async.csv', 
    header=True, 
    delim=',', 
    dateformat='%Y-%m-%d',
    ignore_errors=True
);
```

### Exporting Data to Parquet & CSV

Parquet is 10x smaller and 50x faster than CSV:

```sql
-- Export query results directly to compressed Parquet
COPY (
    SELECT * FROM bronze_blood_raw WHERE state_name = 'Gujarat'
) TO 'gujarat_blood.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);

-- Export to CSV with headers
COPY bronze_blood_raw TO 'cleaned_blood.csv' (HEADER, DELIMITER ',');
```

### Friendly SQL: `SELECT * EXCLUDE / REPLACE`
DuckDB solves one of the oldest annoyances in standard SQL:

```sql
-- Select all 20 columns EXCEPT scraped_at
SELECT * EXCLUDE (scraped_at) 
FROM bronze_blood_raw;

-- Select all columns, but format state_name in UPPERCASE
SELECT * REPLACE (UPPER(state_name) AS state_name) 
FROM bronze_blood_raw;
```

### `QUALIFY` Clause (Deduplication without Subqueries)
In standard Postgres/MySQL, deduplication requires nested subqueries with `ROW_NUMBER()`. DuckDB allows `QUALIFY`:

```sql
-- Keep only the single most recent record per blood bank
SELECT * 
FROM bronze_blood_raw
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY blood_bank_name, blood_component, blood_group 
    ORDER BY scraped_at DESC
) = 1;
```

### `PIVOT` and `UNPIVOT`
Turn row data into summary matrix tables instantly:

```sql
-- Pivot blood groups into columns
PIVOT bronze_blood_raw
ON blood_group
USING SUM(units_available)
GROUP BY state_name;
```

---

## 5. DuckDB Python API Masterclass

DuckDB's Python library is fully integrated with Python data structures.

### Basic Querying and In-Memory Execution

```python
import duckdb

# Connect in-memory (no file created)
con = duckdb.connect()

# Run SQL and fetch results as python tuples
results = con.execute("SELECT 42 AS answer").fetchall()
print(results)  # [(42,)]
```

### Zero-Copy Integration with Pandas, Polars, and Arrow

DuckDB can directly query Python variables in memory without copying data:

```python
import pandas as pd
import duckdb

# A normal pandas dataframe
df = pd.read_csv("INDIA_blood_inventory_async.csv")

# DuckDB can query the variable 'df' directly in SQL!
query = """
    SELECT 
        state_name, 
        COUNT(DISTINCT blood_bank_name) AS total_banks,
        SUM(TRY_CAST(units_available AS INTEGER)) AS total_units
    FROM df
    GROUP BY state_name
    ORDER BY total_units DESC
"""

# Output directly back to pandas, polars, or arrow
result_df = duckdb.sql(query).df()
print(result_df.head())
```

### Persistent Database Storage

```python
import duckdb

# Open or create persistent database file
con = duckdb.connect("blood_warehouse.duckdb")

# Ingest CSV into a persistent table
con.execute("""
    CREATE OR REPLACE TABLE bronze_blood_inventory AS
    SELECT * FROM read_csv_auto('INDIA_blood_inventory_async.csv');
""")

print("Saved to blood_warehouse.duckdb successfully!")
con.close()
```

---

## 6. DuckDB Extensions System

DuckDB has a modular extension ecosystem that downloads and installs in 1 second.

### `httpfs` (Query Remote S3 / HTTPS Files)

```sql
-- Install and load httpfs
INSTALL httpfs;
LOAD httpfs;

-- Read Parquet directly from GitHub or an S3 URL without downloading it!
SELECT * 
FROM 'https://raw.githubusercontent.com/datasets/blood/main/data.parquet' 
LIMIT 10;
```

### `postgres_scanner` (Read/Write Directly to PostgreSQL)

```sql
INSTALL postgres;
LOAD postgres;

-- Attach a live PostgreSQL database into DuckDB!
ATTACH 'dbname=blood_db user=postgres host=localhost password=secret' AS pg_db (TYPE POSTGRES);

-- Copy data directly from DuckDB into PostgreSQL
CREATE TABLE pg_db.gold_inventory AS SELECT * FROM local_gold_inventory;
```

---

## 7. What is `dbt-duckdb`?

### Why does `dbt-duckdb` exist?

Normally, `dbt` (data build tool) is used against massive, expensive cloud data warehouses:
- `dbt-snowflake` $\rightarrow$ requires Snowflake ($$$)
- `dbt-bigquery` $\rightarrow$ requires Google Cloud
- `dbt-redshift` $\rightarrow$ requires AWS Redshift

**`dbt-duckdb`** is an adapter plugin that allows you to run **the full, production-grade dbt toolset entirely locally on your laptop against DuckDB**.

### How `dbt-duckdb` Transforms Local Data Engineering

1. **Zero Cloud Bills:** You write the exact same enterprise dbt models (Jinja templating, tests, docs, lineage DAGs, snapshots) without paying a single dollar.
2. **Instant Feedback:** `dbt run` against Snowflake or BigQuery takes 15–45 seconds per model over network APIs. `dbt run` on DuckDB executes in **0.1 to 0.5 seconds**.
3. **Data Lake Querying:** `dbt-duckdb` can read from CSV, Parquet, Iceberg, and Delta Lake files directly.
4. **Cloud Portability:** When your dbt project is finished and tested on DuckDB, porting it to BigQuery, Snowflake, or Databricks takes less than 15 minutes (just changing `profiles.yml` and dialect nuances).

---

## 8. Configuring `dbt-duckdb` Step-by-Step

### Installation

```bash
uv add dbt-duckdb
```

### Configuring `profiles.yml`

dbt looks for database credentials in `~/.dbt/profiles.yml`. For DuckDB, the configuration is minimal:

```yaml
# ~/.dbt/profiles.yml
blood_project:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: '/home/radhey/Documents/project_idea/blood_warehouse.duckdb'
      threads: 4
      extensions:
        - httpfs
        - parquet
```

### Connecting to Raw CSVs or External Sources

In dbt, define the source in `models/sources.yml`:

```yaml
version: 2

sources:
  - name: external_source
    meta:
      external_location: "/home/radhey/Documents/project_idea/INDIA_blood_inventory_async.csv"
    tables:
      - name: raw_blood_csv
```

### Writing Your First Model

#### Silver Staging Model: `models/silver/stg_blood_inventory.sql`

```sql
{{ config(materialized='view') }}

WITH source_data AS (
    SELECT * FROM read_csv_auto('/home/radhey/Documents/project_idea/INDIA_blood_inventory_async.csv')
),

cleaned AS (
    SELECT
        TRIM(state_name) AS state_name,
        TRIM(district_name) AS district_name,
        TRIM(blood_bank_name) AS blood_bank_name,
        UPPER(TRIM(blood_group)) AS blood_group,
        TRIM(blood_component) AS blood_component,
        COALESCE(TRY_CAST(units_available AS INTEGER), 0) AS units_available,
        TRY_CAST(last_updated AS TIMESTAMP) AS updated_at
    FROM source_data
    WHERE blood_bank_name IS NOT NULL
)

SELECT * FROM cleaned
```

#### Gold Mart Model: `models/gold/fct_state_blood_shortage.sql`

```sql
{{ config(materialized='table') }}

SELECT
    state_name,
    blood_group,
    SUM(units_available) AS total_units_in_stock,
    COUNT(DISTINCT blood_bank_name) AS active_blood_banks,
    CASE 
        WHEN SUM(units_available) = 0 THEN 'CRITICAL DEFICIT'
        WHEN SUM(units_available) < 10 THEN 'LOW STOCK'
        ELSE 'STABLE'
    END AS stock_status
FROM {{ ref('stg_blood_inventory') }}
GROUP BY state_name, blood_group
```

When you run:
```bash
dbt run
```
DuckDB executes the transformations and materializes `fct_state_blood_shortage` into your `blood_warehouse.duckdb` file in **0.2 seconds**!

---

## 9. Performance Tuning & Production Best Practices

1. **Always Use `read_csv_auto` with `sample_size`:**  
   If your CSV has millions of rows, DuckDB analyzes the first 20,480 rows by default. Set `sample_size=-1` if types are inconsistent.
2. **Convert Raw CSV to Parquet Early:**  
   Parquet reads are 10x–50x faster than CSV:
   ```sql
   COPY (SELECT * FROM read_csv_auto('input.csv')) TO 'bronze.parquet' (FORMAT PARQUET);
   ```
3. **Set Memory Limits on Low-RAM Laptops:**  
   Prevent Out-Of-Memory (OOM) errors:
   ```sql
   SET max_memory = '8GB';
   SET threads = 4;
   ```
4. **Out-of-Core Processing:**  
   DuckDB automatically spills to temporary disk files if your dataset exceeds physical RAM.

---

## 10. Quick Command Cheatsheet

```bash
# --- CLI USAGE ---
duckdb                                       # Start in-memory session
duckdb db.duckdb                             # Open persistent DB
duckdb -c "SELECT * FROM 'data.csv' LIMIT 5" # Run one-shot query from terminal

# --- PYTHON USAGE ---
uv add duckdb dbt-duckdb                     # Install in venv
python -c "import duckdb; print(duckdb.sql('SELECT 1').fetchall())"

# --- SQL RAPID RECIPES ---
SELECT * FROM 'file.csv';                    # Read CSV
SELECT * FROM 'file.parquet';                # Read Parquet
SELECT * FROM read_json_auto('file.json');   # Read JSON
COPY my_table TO 'out.parquet' (FORMAT PARQUET); # Save to Parquet
DESCRIBE SELECT * FROM 'file.csv';           # Inspect auto-detected schema
```
