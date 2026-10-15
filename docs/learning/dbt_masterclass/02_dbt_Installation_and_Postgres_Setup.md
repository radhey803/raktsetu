# 📘 Module 2: dbt Installation and PostgreSQL Setup

> **Masterclass Series**: dbt — From Absolute Beginner to Senior Data Engineer  
> **Module**: 2 of 5  
> **Difficulty**: 🟢 Beginner → 🟡 Intermediate  
> **Estimated Time**: 2–3 hours  
> **Theme**: India Blood Bank Inventory System (eRaktKosh)  
> **Prerequisites**: Module 1 completed, PostgreSQL installed, Python 3.9+

---

## 📑 Table of Contents

1. [Prerequisites Check](#1-prerequisites-check)
2. [Installing dbt-core and PostgreSQL Adapter](#2-installing-dbt-core-and-postgresql-adapter)
3. [Setting Up PostgreSQL for dbt](#3-setting-up-postgresql-for-dbt)
4. [Loading Your Bronze Data into PostgreSQL](#4-loading-your-bronze-data-into-postgresql)
5. [Configuring profiles.yml (Securely)](#5-configuring-profilesyml-securely)
6. [Running dbt init — Your First Project](#6-running-dbt-init--your-first-project)
7. [Deep Dive: Every File and Folder Explained](#7-deep-dive-every-file-and-folder-explained)
8. [Configuring dbt_project.yml](#8-configuring-dbt_projectyml)
9. [Your First dbt run — Hello World](#9-your-first-dbt-run--hello-world)
10. [Practice Exercises](#10-practice-exercises)
11. [Troubleshooting Common Issues](#11-troubleshooting-common-issues)
12. [Key Takeaways](#12-key-takeaways)

---

## 1. Prerequisites Check

Before we begin, make sure you have these installed:

```bash
# Check Python version (need 3.9+)
python3 --version
# Expected: Python 3.10.x or higher

# Check pip version
pip --version
# or
pip3 --version

# Check if uv is installed (recommended, faster than pip)
uv --version
# If not installed: curl -LsSf https://astral.sh/uv/install.sh | sh

# Check PostgreSQL
psql --version
# Expected: psql (PostgreSQL) 14.x or higher

# Check if PostgreSQL is running
sudo systemctl status postgresql
# or on macOS:
brew services list | grep postgresql
```

> **💡 Why PostgreSQL?** While dbt works with BigQuery, Snowflake, Redshift, Databricks, and more — PostgreSQL is **free**, runs locally, and is perfect for learning. Everything you learn here transfers directly to cloud warehouses.

---

## 2. Installing dbt-core and PostgreSQL Adapter

### Option A: Using `uv` (⚡ Recommended — 10x faster than pip)

`uv` is a blazing-fast Python package manager written in Rust. If you're serious about Python development, use `uv`.

```bash
# Create a new virtual environment for your dbt project
mkdir -p ~/blood_bank_dbt && cd ~/blood_bank_dbt

# Initialize with uv
uv init

# Add dbt-core and the PostgreSQL adapter
uv add dbt-core dbt-postgres

# Verify installation
uv run dbt --version
```

**Expected output:**

```
Core:
  - installed: 1.9.x
  - latest:    1.9.x - Up to date!

Plugins:
  - postgres: 1.9.x - Up to date!
```

### Option B: Using `pip` with Virtual Environment

```bash
# Create project directory
mkdir -p ~/blood_bank_dbt && cd ~/blood_bank_dbt

# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dbt-core and PostgreSQL adapter
pip install dbt-core dbt-postgres

# Verify installation
dbt --version
```

### Option C: Using `pipx` (Isolated Global Install)

```bash
# Install pipx if you don't have it
pip install pipx

# Install dbt globally in an isolated environment
pipx install dbt-core
pipx inject dbt-core dbt-postgres

# Verify
dbt --version
```

### Understanding What You Just Installed

| Package | What It Does |
|---------|-------------|
| `dbt-core` | The core dbt engine — parses models, builds DAGs, runs commands |
| `dbt-postgres` | The **adapter** that lets dbt talk to PostgreSQL. Each database needs its own adapter. |

> **🔑 Key Concept: Adapters**: dbt doesn't know how to talk to databases directly. It uses **adapters** — plugins that translate dbt commands into database-specific SQL. There are adapters for:
> - `dbt-postgres` (PostgreSQL)
> - `dbt-bigquery` (Google BigQuery)
> - `dbt-snowflake` (Snowflake)
> - `dbt-redshift` (AWS Redshift)
> - `dbt-databricks` (Databricks)
> - `dbt-duckdb` (DuckDB — great for local analytics!)

---

## 3. Setting Up PostgreSQL for dbt

### Step 1: Create a Dedicated Database User for dbt

**Never use the default `postgres` superuser for dbt.** Create a dedicated user with limited permissions:

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql
```

```sql
-- Inside psql:

-- Create a dedicated dbt user
CREATE USER dbt_user WITH PASSWORD 'your_secure_password_here';

-- Create the blood bank database
CREATE DATABASE blood_bank_db OWNER dbt_user;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE blood_bank_db TO dbt_user;

-- Exit psql
\q
```

### Step 2: Create Schemas for the Medallion Architecture

```bash
# Connect as the dbt user
psql -U dbt_user -d blood_bank_db -h localhost
```

```sql
-- Create schemas matching our Medallion Architecture
CREATE SCHEMA IF NOT EXISTS raw_blood_bank;    -- Bronze layer (raw data)
CREATE SCHEMA IF NOT EXISTS staging;            -- Silver layer (cleaned data)
CREATE SCHEMA IF NOT EXISTS marts;              -- Gold layer (business data)

-- Verify schemas were created
\dn

-- Expected output:
--       List of schemas
--       Name       |  Owner
-- -----------------+----------
--  marts           | dbt_user
--  public          | postgres
--  raw_blood_bank  | dbt_user
--  staging         | dbt_user

\q
```

### Step 3: Verify Connection

```bash
# Test the connection (you should be prompted for password)
psql -U dbt_user -d blood_bank_db -h localhost -c "SELECT current_database(), current_user, version();"
```

**Expected output:**

```
 current_database | current_user |          version
------------------+--------------+---------------------------
 blood_bank_db    | dbt_user     | PostgreSQL 16.x on ...
```

---

## 4. Loading Your Bronze Data into PostgreSQL

Before dbt can transform data, the raw data must be **already loaded** into the warehouse. Remember: dbt is the "T" in ELT — it doesn't extract or load.

### Method 1: Using COPY Command (Recommended for Large CSVs)

```bash
# First, create the raw table to match your CSV structure
psql -U dbt_user -d blood_bank_db -h localhost
```

```sql
-- Create the Bronze table (all TEXT columns — it's raw data!)
CREATE TABLE raw_blood_bank.blood_inventory_raw (
    bldgrpcode1         TEXT,
    compId              TEXT,
    componentName       TEXT,
    count               TEXT,
    hospitalname        TEXT,
    hospitaladd         TEXT,
    hospitalcontact     TEXT,
    hospitalCode        TEXT,
    moderateStock       TEXT,
    hospitalType        TEXT,
    entrydate           TEXT,
    offline             TEXT,
    type                TEXT,
    available_WithQty   TEXT,
    components          TEXT,
    not_available_WithQty TEXT,
    State               TEXT,
    District            TEXT,

    -- Metadata columns (best practice!)
    _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    _source_file TEXT DEFAULT 'INDIA_blood_inventory_async.csv'
);

-- Load the CSV (update the path to your actual file)
\COPY raw_blood_bank.blood_inventory_raw (
    bldgrpcode1, compId, componentName, count,
    hospitalname, hospitaladd, hospitalcontact, hospitalCode,
    moderateStock, hospitalType, entrydate, offline,
    type, available_WithQty, components, not_available_WithQty,
    State, District
) FROM '/home/radhey/Documents/project_idea/INDIA_blood_inventory_async.csv'
WITH (FORMAT CSV, HEADER TRUE, QUOTE '"', ESCAPE '"');

-- Verify the load
SELECT COUNT(*) AS total_rows FROM raw_blood_bank.blood_inventory_raw;
-- Expected: ~14,000+ rows

-- Preview the data
SELECT hospitalname, State, District, hospitalType, entrydate
FROM raw_blood_bank.blood_inventory_raw
LIMIT 5;
```

### Method 2: Using Python Script (Programmatic)

```python
#!/usr/bin/env python3
"""
Bronze Layer Loader: Load raw blood bank CSV into PostgreSQL.
This script handles the E+L (Extract & Load) part of ELT.
dbt will handle the T (Transform).
"""

import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# Database connection
DB_URL = "postgresql://dbt_user:your_password@localhost:5432/blood_bank_db"
engine = create_engine(DB_URL)

# Load CSV
print("📂 Loading CSV...")
df = pd.read_csv(
    "/home/radhey/Documents/project_idea/INDIA_blood_inventory_async.csv",
    dtype=str,  # Load everything as STRING (Bronze layer = raw!)
)

# Add metadata columns
df["_loaded_at"] = datetime.now().isoformat()
df["_source_file"] = "INDIA_blood_inventory_async.csv"

# Load into PostgreSQL (Bronze layer)
print(f"📤 Loading {len(df)} rows into raw_blood_bank.blood_inventory_raw...")
df.to_sql(
    name="blood_inventory_raw",
    schema="raw_blood_bank",
    con=engine,
    if_exists="replace",  # Use 'append' for incremental loads
    index=False,
)

print(f"✅ Successfully loaded {len(df)} rows into Bronze layer!")
```

### Method 3: Using dbt Seeds (For Small Reference Tables Only)

dbt can load CSV files directly using `dbt seed`. This is great for **small reference tables** (< 10K rows), but **NOT for your main data**:

```bash
# Place small CSVs in the seeds/ directory
# Example: seeds/ref_blood_groups.csv

# Then run:
dbt seed
```

We'll create seed files later. For now, use Method 1 or 2 for the main dataset.

---

## 5. Configuring profiles.yml (Securely)

The `profiles.yml` file tells dbt **how to connect to your database**. It lives in `~/.dbt/profiles.yml` (your home directory, NOT in the project).

### Step 1: Create the profiles.yml file

```bash
# Create the .dbt directory
mkdir -p ~/.dbt

# Create the profiles.yml file
nano ~/.dbt/profiles.yml
```

### Step 2: Write the Configuration

```yaml
# ~/.dbt/profiles.yml
# This file tells dbt how to connect to your database(s).
# IMPORTANT: This file should NEVER be committed to Git!

blood_bank_dbt:                    # Profile name (must match dbt_project.yml)
  target: dev                       # Default target environment
  outputs:

    # Development environment (your local machine)
    dev:
      type: postgres                # Database type
      host: localhost               # Database host
      port: 5432                    # PostgreSQL default port
      user: dbt_user                # The user we created earlier
      password: "{{ env_var('DBT_POSTGRES_PASSWORD') }}"  # 🔐 Use env var!
      dbname: blood_bank_db         # Database name
      schema: staging               # Default schema for dbt models
      threads: 4                    # Number of parallel threads (match your CPU cores)
      keepalives_idle: 0            # Prevent connection timeouts
      connect_timeout: 10           # Connection timeout in seconds

    # Production environment (example)
    prod:
      type: postgres
      host: "{{ env_var('DBT_PROD_HOST') }}"
      port: 5432
      user: "{{ env_var('DBT_PROD_USER') }}"
      password: "{{ env_var('DBT_PROD_PASSWORD') }}"
      dbname: blood_bank_db
      schema: marts                 # Production writes to marts schema
      threads: 8
      keepalives_idle: 0
      connect_timeout: 10
```

### Step 3: Set the Environment Variable (Securely)

**NEVER hardcode passwords in profiles.yml!** Use environment variables:

```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, or ~/.profile)
echo 'export DBT_POSTGRES_PASSWORD="your_secure_password_here"' >> ~/.bashrc

# Reload the shell
source ~/.bashrc

# Verify the variable is set
echo $DBT_POSTGRES_PASSWORD
```

### Alternative: Using a .env File

```bash
# Create .env in your project root (add to .gitignore!)
echo 'DBT_POSTGRES_PASSWORD=your_secure_password_here' > ~/blood_bank_dbt/.env

# Add to .gitignore
echo '.env' >> ~/blood_bank_dbt/.gitignore
```

Then load it before running dbt:

```bash
# Load env vars before dbt commands
set -a && source .env && set +a && dbt run
```

### profiles.yml Deep Dive: Every Field Explained

| Field | Purpose | Example |
|-------|---------|---------|
| `blood_bank_dbt` | **Profile name**. Must match the `profile` field in `dbt_project.yml` | — |
| `target` | **Default environment**. Which output to use when you run `dbt run` | `dev` |
| `outputs` | **Environment definitions**. You can have dev, staging, prod, etc. | — |
| `type` | **Adapter type**. Must match the adapter you installed | `postgres` |
| `host` | **Database hostname** | `localhost` or `db.example.com` |
| `port` | **Database port** | `5432` (PostgreSQL default) |
| `user` | **Database username** | `dbt_user` |
| `password` | **Database password**. Use `{{ env_var('...') }}` for security | — |
| `dbname` | **Database name** | `blood_bank_db` |
| `schema` | **Default schema**. dbt will create models here unless overridden | `staging` |
| `threads` | **Parallelism**. Number of models dbt runs simultaneously | `4` |
| `keepalives_idle` | **TCP keepalive**. Set to 0 to prevent idle disconnections | `0` |
| `connect_timeout` | **Connection timeout** in seconds | `10` |

### Step 4: Test the Connection

```bash
cd ~/blood_bank_dbt

# Test if dbt can connect to your database
dbt debug
```

**Expected output:**

```
  Connection:
  - host: localhost
  - port: 5432
  - user: dbt_user
  - database: blood_bank_db
  - schema: staging
  - Connection test: [OK connection ok]

  All checks passed!
```

### 🔐 Security Best Practices for profiles.yml

| Practice | Why |
|----------|-----|
| **Never commit `profiles.yml` to Git** | It's in `~/.dbt/`, outside your project. If you ever copy it into your project, add it to `.gitignore` |
| **Use `env_var()` for passwords** | Jinja function `{{ env_var('VAR_NAME') }}` reads from environment variables |
| **Use different credentials per environment** | Dev, staging, and prod should have separate database users |
| **Restrict permissions** | The dbt user should only have the permissions it needs (no SUPERUSER) |
| **Use `connect_timeout`** | Prevents dbt from hanging if the database is down |

---

## 6. Running dbt init — Your First Project

### Initialize the Project

```bash
# Navigate to your project directory
cd ~/blood_bank_dbt

# Initialize a new dbt project
dbt init blood_bank_dbt
```

dbt will ask you a few questions:

```
Which database would you like to use?
[1] postgres

Enter a number: 1

Your new dbt project "blood_bank_dbt" was created!
```

### What dbt init Creates

```
blood_bank_dbt/
├── README.md                    # Project documentation
├── dbt_project.yml              # 🔑 Main project configuration
├── analyses/                    # Ad-hoc analytical queries
│   └── .gitkeep
├── macros/                      # Reusable Jinja SQL functions
│   └── .gitkeep
├── models/                      # 🔑 Your SQL transformation models
│   └── example/
│       ├── my_first_dbt_model.sql
│       ├── my_second_dbt_model.sql
│       └── schema.yml
├── seeds/                       # CSV files to load as tables
│   └── .gitkeep
├── snapshots/                   # Slowly Changing Dimension (SCD) logic
│   └── .gitkeep
└── tests/                       # Custom data quality tests
    └── .gitkeep
```

---

## 7. Deep Dive: Every File and Folder Explained

### `dbt_project.yml` — The Brain of Your Project

This is the **most important configuration file**. It tells dbt how your project is structured and how to materialize your models.

```yaml
# dbt_project.yml

name: 'blood_bank_dbt'           # Project name (no spaces, no hyphens)
version: '1.0.0'                  # Semantic version
config-version: 2                 # dbt config version (always 2)
profile: 'blood_bank_dbt'        # Must match profile name in profiles.yml

# Directories (usually keep defaults)
model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]
asset-paths: ["assets"]

# Output directories (generated files, add to .gitignore)
clean-targets:
  - "target"                     # Compiled SQL output
  - "dbt_packages"               # Installed packages
  - "logs"                       # Log files
```

### `models/` — Where the Magic Happens

This is where **all your SQL transformations** live. Each `.sql` file is a **model** that dbt will execute.

**Best practice directory structure:**

```
models/
├── staging/                     # 🥈 Silver layer
│   ├── blood_bank/              # Grouped by source
│   │   ├── _blood_bank__models.yml    # Model documentation
│   │   ├── _blood_bank__sources.yml   # Source definitions
│   │   ├── stg_blood_bank__hospitals.sql
│   │   ├── stg_blood_bank__components.sql
│   │   └── stg_blood_bank__contacts.sql
│   └── README.md
│
├── intermediate/                # Optional: complex transformations
│   └── int_blood_bank__pivoted_components.sql
│
└── marts/                       # 🥇 Gold layer
    ├── core/                    # Core business tables
    │   ├── _core__models.yml
    │   ├── dim_hospitals.sql
    │   ├── dim_blood_components.sql
    │   └── dim_districts.sql
    │
    └── analytics/               # Analytics-specific tables
        ├── _analytics__models.yml
        ├── fct_blood_availability.sql
        ├── fct_daily_stock_summary.sql
        └── rpt_state_availability_dashboard.sql
```

**Naming conventions (industry standard):**

| Prefix | Layer | Purpose | Example |
|--------|-------|---------|---------|
| `stg_` | Silver/Staging | Clean a single source table | `stg_blood_bank__hospitals` |
| `int_` | Intermediate | Complex transformations between staging and marts | `int_blood_bank__pivoted_components` |
| `dim_` | Gold/Marts | Dimension tables (entities, lookups) | `dim_hospitals`, `dim_districts` |
| `fct_` | Gold/Marts | Fact tables (events, measurements) | `fct_blood_availability` |
| `rpt_` | Gold/Marts | Report tables (pre-aggregated for dashboards) | `rpt_state_availability_dashboard` |

> **📌 The double underscore `__` convention**: `stg_{source_name}__{entity_name}`. This tells you WHERE the data comes from and WHAT entity it represents.

### `seeds/` — CSV Files as Tables

Seeds are **small CSV files** that dbt can load directly into your warehouse. Great for:

- Reference data (blood group codes, state codes)
- Lookup tables
- Test data

```csv
# seeds/ref_blood_groups.csv

blood_group_code,blood_group_name,rh_factor,is_rare
A_POS,A+,positive,false
A_NEG,A-,negative,false
B_POS,B+,positive,false
B_NEG,B-,negative,false
O_POS,O+,positive,false
O_NEG,O-,negative,false
AB_POS,AB+,positive,false
AB_NEG,AB-,negative,false
OH_POS,Oh+,positive,true
OH_NEG,Oh-,negative,true
```

```bash
# Load seeds into the warehouse
dbt seed

# This creates a table: staging.ref_blood_groups (or whatever your default schema is)
```

### `macros/` — Reusable Jinja Functions

Macros are **reusable SQL snippets** written in Jinja. Think of them as **SQL functions**:

```sql
-- macros/clean_text.sql

{% macro clean_text(column_name) %}
    TRIM(LOWER({{ column_name }}))
{% endmacro %}
```

Usage in a model:

```sql
-- models/staging/stg_blood_bank__hospitals.sql

SELECT
    {{ clean_text('hospitalname') }} AS hospital_name,
    {{ clean_text('State') }} AS state_name
FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
```

We'll deep-dive into macros in Module 5.

### `tests/` — Custom Data Quality Tests

Custom SQL tests that assert business rules:

```sql
-- tests/assert_no_negative_blood_units.sql
-- This test FAILS if it returns any rows

SELECT
    hospital_id,
    component_name,
    available_units
FROM {{ ref('fct_blood_availability') }}
WHERE available_units < 0
```

We'll deep-dive into testing in Module 4.

### `snapshots/` — Slowly Changing Dimensions (SCD)

Snapshots track **how data changes over time**. For our blood bank:

```sql
-- snapshots/snp_blood_inventory.sql
-- Track how blood inventory changes daily

{% snapshot snp_blood_inventory %}

{{
    config(
      target_schema='snapshots',
      unique_key='hospital_id || component_name || blood_group',
      strategy='timestamp',
      updated_at='last_updated_at',
    )
}}

SELECT * FROM {{ ref('stg_blood_bank__components') }}

{% endsnapshot %}
```

This creates a historical record so you can query: *"What was the O+ inventory in Maharashtra on October 1st?"*

### `analyses/` — Ad-Hoc Queries

One-off analytical queries that you want to version control but don't want to create as tables:

```sql
-- analyses/monthly_blood_shortage_report.sql
-- This gets compiled but NOT materialized as a table

SELECT
    state_name,
    blood_group,
    SUM(CASE WHEN stock_status = 'OUT_OF_STOCK' THEN 1 ELSE 0 END) AS stockout_count,
    COUNT(*) AS total_hospitals,
    ROUND(
        SUM(CASE WHEN stock_status = 'OUT_OF_STOCK' THEN 1 ELSE 0 END)::NUMERIC
        / COUNT(*)::NUMERIC * 100, 2
    ) AS stockout_percentage
FROM {{ ref('fct_blood_availability') }}
GROUP BY state_name, blood_group
ORDER BY stockout_percentage DESC
```

### `target/` — Compiled Output (Auto-Generated)

dbt compiles your Jinja-templated SQL into plain SQL and stores it here. **Add this to `.gitignore`:**

```
target/
dbt_packages/
logs/
.env
```

---

## 8. Configuring dbt_project.yml

Now let's configure the project file properly for our blood bank project:

```yaml
# dbt_project.yml

name: 'blood_bank_dbt'
version: '1.0.0'
config-version: 2
profile: 'blood_bank_dbt'

# Directory paths
model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

# Output directories
clean-targets:
  - "target"
  - "dbt_packages"
  - "logs"

# ============================================================
# MODEL CONFIGURATION
# This is where you define HOW each model should be materialized
# ============================================================

models:
  blood_bank_dbt:                # Must match the 'name' field above

    # Silver/Staging layer
    staging:
      +materialized: view        # Staging models are VIEWS (lightweight, always fresh)
      +schema: staging           # Write to the 'staging' schema
      +tags: ['staging', 'silver']

    # Intermediate layer
    intermediate:
      +materialized: ephemeral   # Intermediate models are CTEs (not stored in DB)
      +tags: ['intermediate']

    # Gold/Marts layer
    marts:
      +materialized: table       # Mart models are TABLES (pre-computed, fast queries)
      +schema: marts             # Write to the 'marts' schema
      +tags: ['marts', 'gold']

# ============================================================
# SEED CONFIGURATION
# ============================================================

seeds:
  blood_bank_dbt:
    +schema: staging             # Seeds go to the staging schema
    ref_blood_groups:
      +column_types:
        blood_group_code: varchar(10)
        blood_group_name: varchar(10)
        is_rare: boolean

# ============================================================
# SNAPSHOT CONFIGURATION
# ============================================================

snapshots:
  blood_bank_dbt:
    +target_schema: snapshots

# ============================================================
# VARIABLES (accessible via var() in models)
# ============================================================

vars:
  stale_data_threshold_days: 7   # Flag hospitals not updated in 7 days
  critical_stock_threshold: 5    # Flag components with < 5 units
```

### Materialization Types Explained

| Materialization | SQL Equivalent | When to Use | Pros | Cons |
|----------------|---------------|-------------|------|------|
| **`view`** | `CREATE VIEW AS` | Staging models (Silver) | Always fresh data, no storage cost | Slower queries (re-computed on read) |
| **`table`** | `CREATE TABLE AS` | Mart models (Gold) | Fast queries (pre-computed) | Takes storage, can become stale |
| **`incremental`** | `INSERT INTO ... WHERE` | Large fact tables (100M+ rows) | Only processes new rows | Complex to configure correctly |
| **`ephemeral`** | CTE (Common Table Expression) | Intermediate helper models | No table/view created, zero storage | Can't be queried directly, harder to debug |

**Blood bank analogy:**

| Model | Materialization | Why |
|-------|----------------|-----|
| `stg_blood_bank__hospitals` | **view** | Always shows the latest data from Bronze |
| `stg_blood_bank__components` | **view** | Same — lightweight, always fresh |
| `int_blood_bank__pivoted_components` | **ephemeral** | Helper model, not needed in DB |
| `fct_blood_availability` | **table** | Dashboard queries need fast performance |
| `dim_hospitals` | **table** | Dimension tables are queried frequently |
| `fct_daily_stock_changes` | **incremental** | Millions of daily rows — only insert new ones |

---

## 9. Your First dbt run — Hello World

### Step 1: Create a Simple Model

```bash
# Remove the example models
rm -rf models/example/
```

Create your first real model:

```bash
mkdir -p models/staging/blood_bank
```

```sql
-- models/staging/blood_bank/stg_blood_bank__hospital_count.sql
-- Your first dbt model! 🎉

-- This model counts the number of unique hospitals per state

SELECT
    TRIM(State) AS state_name,
    COUNT(DISTINCT hospitalCode) AS hospital_count
FROM raw_blood_bank.blood_inventory_raw
WHERE State IS NOT NULL
  AND hospitalCode IS NOT NULL
  AND hospitalCode != '-'
GROUP BY TRIM(State)
ORDER BY hospital_count DESC
```

### Step 2: Run dbt

```bash
# Run all models
dbt run

# Expected output:
# 01:45:23  Running with dbt=1.9.0
# 01:45:23  Found 1 model, 0 sources, 0 tests, 0 seeds, ...
# 01:45:23  
# 01:45:23  Concurrency: 4 threads (target='dev')
# 01:45:23  
# 01:45:23  1 of 1 START sql view model staging.stg_blood_bank__hospital_count ... [RUN]
# 01:45:24  1 of 1 OK created sql view model staging.stg_blood_bank__hospital_count ... [CREATE VIEW in 0.15s]
# 01:45:24  
# 01:45:24  Finished running 1 view model in 0.42s.
# 01:45:24  
# 01:45:24  Completed successfully
```

### Step 3: Verify in PostgreSQL

```bash
psql -U dbt_user -d blood_bank_db -h localhost
```

```sql
-- Check if the view was created
SELECT * FROM staging.stg_blood_bank__hospital_count LIMIT 10;

-- Expected output:
--          state_name          | hospital_count
-- ----------------------------+----------------
--  Uttar Pradesh              |            312
--  Maharashtra                |            287
--  Tamil Nadu                 |            245
--  Karnataka                  |            198
--  ...
```

### Step 4: Run dbt with Verbosity

```bash
# Run with debug output to see the exact SQL being executed
dbt run --debug

# Run a specific model
dbt run --select stg_blood_bank__hospital_count

# Run with full refresh (drops and recreates tables)
dbt run --full-refresh
```

---

## 10. Practice Exercises

### 🏋️ Exercise 1: Complete Setup from Scratch

Follow these steps to set up dbt from zero:

1. Create a new PostgreSQL database called `practice_db`
2. Create a user called `practice_user`
3. Create the three Medallion schemas (`raw`, `staging`, `marts`)
4. Install `dbt-core` and `dbt-postgres` in a virtual environment
5. Run `dbt init practice_project`
6. Configure `profiles.yml` with environment variables
7. Run `dbt debug` and verify all checks pass

**Verification checklist:**

```bash
# All should pass ✅
dbt debug
# Connection test: [OK connection ok]
# All checks passed!
```

---

### 🏋️ Exercise 2: Create Reference Seed Data

Create a CSV file for blood component types:

```csv
# seeds/ref_blood_components.csv

component_code,component_name,shelf_life_days,storage_temp_celsius,is_critical
WB,Whole Blood,35,-6,true
PRBC,Packed Red Blood Cells,42,-6,true
FFP,Fresh Frozen Plasma,365,-30,true
PLT,Platelet Concentrate,5,22,true
RDP,Random Donor Platelets,5,22,false
SDP,Single Donor Platelet,5,22,false
CRYO,Cryoprecipitate,365,-30,false
CPP,Cryo Poor Plasma,365,-30,false
PLS,Plasma,365,-30,false
```

**Tasks:**
1. Save this file in `seeds/ref_blood_components.csv`
2. Run `dbt seed`
3. Verify the table was created in PostgreSQL
4. Query the table to find all components with a shelf life < 7 days

<details>
<summary>Click to reveal solution</summary>

```bash
# Run the seed
dbt seed

# Verify in PostgreSQL
psql -U dbt_user -d blood_bank_db -h localhost -c "
SELECT component_name, shelf_life_days 
FROM staging.ref_blood_components 
WHERE shelf_life_days < 7 
ORDER BY shelf_life_days;
"

# Expected:
#     component_name       | shelf_life_days
# -------------------------+-----------------
#  Platelet Concentrate    |               5
#  Random Donor Platelets  |               5
#  Single Donor Platelet   |               5
```

</details>

---

### 🏋️ Exercise 3: Write Your First 3 Models

Create these three models from scratch:

**Model 1**: `stg_blood_bank__state_summary.sql`
- Count hospitals per state
- Count hospitals by type (Govt., Private, Charitable/Vol) per state
- Sort by total hospital count descending

**Model 2**: `stg_blood_bank__stale_hospitals.sql`
- Find all hospitals where `entrydate` is more than 7 days old
- Include: hospital_name, state, district, days_since_update

**Model 3**: `stg_blood_bank__facility_types.sql`
- List all distinct facility types (`type` column)
- Count how many hospitals belong to each type

<details>
<summary>Click to reveal Model 1 solution</summary>

```sql
-- models/staging/blood_bank/stg_blood_bank__state_summary.sql

SELECT
    TRIM(State) AS state_name,
    COUNT(DISTINCT hospitalCode) FILTER (WHERE hospitalCode != '-') AS total_hospitals,
    COUNT(DISTINCT hospitalCode) FILTER (
        WHERE TRIM(hospitalType) = 'Govt.' AND hospitalCode != '-'
    ) AS govt_hospitals,
    COUNT(DISTINCT hospitalCode) FILTER (
        WHERE TRIM(hospitalType) = 'Private' AND hospitalCode != '-'
    ) AS private_hospitals,
    COUNT(DISTINCT hospitalCode) FILTER (
        WHERE TRIM(hospitalType) = 'Charitable/Vol' AND hospitalCode != '-'
    ) AS charitable_hospitals
FROM raw_blood_bank.blood_inventory_raw
WHERE State IS NOT NULL
GROUP BY TRIM(State)
ORDER BY total_hospitals DESC
```

</details>

<details>
<summary>Click to reveal Model 2 solution</summary>

```sql
-- models/staging/blood_bank/stg_blood_bank__stale_hospitals.sql

SELECT
    TRIM(hospitalname) AS hospital_name,
    TRIM(State) AS state_name,
    TRIM(District) AS district_name,
    CAST(entrydate AS TIMESTAMP) AS last_updated_at,
    CURRENT_DATE - CAST(entrydate AS TIMESTAMP)::DATE AS days_since_update
FROM raw_blood_bank.blood_inventory_raw
WHERE hospitalCode IS NOT NULL
  AND hospitalCode != '-'
  AND entrydate IS NOT NULL
  AND (CURRENT_DATE - CAST(entrydate AS TIMESTAMP)::DATE) > 7
ORDER BY days_since_update DESC
```

</details>

<details>
<summary>Click to reveal Model 3 solution</summary>

```sql
-- models/staging/blood_bank/stg_blood_bank__facility_types.sql

SELECT
    TRIM(type) AS facility_type,
    COUNT(DISTINCT hospitalCode) FILTER (WHERE hospitalCode != '-') AS hospital_count,
    ROUND(
        COUNT(DISTINCT hospitalCode) FILTER (WHERE hospitalCode != '-')::NUMERIC /
        NULLIF(
            (SELECT COUNT(DISTINCT hospitalCode) 
             FROM raw_blood_bank.blood_inventory_raw 
             WHERE hospitalCode != '-'), 0
        )::NUMERIC * 100, 2
    ) AS percentage_of_total
FROM raw_blood_bank.blood_inventory_raw
WHERE type IS NOT NULL
GROUP BY TRIM(type)
ORDER BY hospital_count DESC
```

</details>

---

### 🏋️ Exercise 4: Explore dbt Commands

Run each command and understand what it does:

```bash
# 1. Run all models
dbt run

# 2. Run only staging models
dbt run --select staging.*

# 3. Run a specific model
dbt run --select stg_blood_bank__hospital_count

# 4. Compile models (see the raw SQL without running it)
dbt compile

# 5. Check the compiled SQL
cat target/compiled/blood_bank_dbt/models/staging/blood_bank/stg_blood_bank__hospital_count.sql

# 6. Check the run SQL (the actual CREATE VIEW/TABLE statement)
cat target/run/blood_bank_dbt/models/staging/blood_bank/stg_blood_bank__hospital_count.sql

# 7. See what would run without actually running it
dbt ls --select staging.*
```

**Question**: What's the difference between the compiled SQL and the run SQL?

<details>
<summary>Click to reveal answer</summary>

- **Compiled SQL** (`target/compiled/`): The pure `SELECT` statement after all Jinja has been resolved. No `CREATE VIEW` or `CREATE TABLE` wrapper.

- **Run SQL** (`target/run/`): The actual SQL that was executed against the database, including the `CREATE VIEW AS` or `CREATE TABLE AS` wrapper.

Example:

Compiled:
```sql
SELECT TRIM(State) AS state_name, COUNT(*) AS hospital_count
FROM raw_blood_bank.blood_inventory_raw
GROUP BY TRIM(State)
```

Run:
```sql
CREATE VIEW staging.stg_blood_bank__hospital_count AS (
    SELECT TRIM(State) AS state_name, COUNT(*) AS hospital_count
    FROM raw_blood_bank.blood_inventory_raw
    GROUP BY TRIM(State)
);
```

</details>

---

### 🏋️ Exercise 5: Break Things (Intentionally!)

The best way to learn is to understand error messages. Try each of these and observe the errors:

**Break 1**: Misspell the profile name in `dbt_project.yml`

```yaml
profile: 'wrong_profile_name'
```

Then run `dbt debug`. What error do you get?

**Break 2**: Write invalid SQL in a model

```sql
-- models/staging/blood_bank/broken_model.sql
SELECT * FORM raw_blood_bank.blood_inventory_raw  -- "FORM" instead of "FROM"
```

Then run `dbt run`. What error do you get?

**Break 3**: Reference a non-existent table

```sql
SELECT * FROM raw_blood_bank.table_that_does_not_exist
```

Then run `dbt run`. What error do you get?

**Break 4**: Use the wrong database password in `profiles.yml`

Then run `dbt debug`. What error do you get?

> **💡 Pro Tip**: Understanding error messages is 50% of being a good engineer. Don't just read the error — understand WHY it happened and memorize the pattern.

---

## 11. Troubleshooting Common Issues

### Issue 1: `dbt debug` fails with "Could not find profile"

```
Runtime Error: Could not find profile named 'blood_bank_dbt'
```

**Fix**: Ensure the profile name in `dbt_project.yml` exactly matches the top-level key in `~/.dbt/profiles.yml`.

```yaml
# dbt_project.yml
profile: 'blood_bank_dbt'   # ← Must match

# ~/.dbt/profiles.yml
blood_bank_dbt:              # ← This key
  target: dev
```

### Issue 2: PostgreSQL connection refused

```
Connection refused: Is the server running on host "localhost" and accepting TCP/IP connections on port 5432?
```

**Fix**:

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Check if it's listening on port 5432
sudo netstat -tlnp | grep 5432

# Check pg_hba.conf for local authentication
sudo cat /etc/postgresql/*/main/pg_hba.conf | grep -v '^#'
```

### Issue 3: Password authentication failed

```
FATAL: password authentication failed for user "dbt_user"
```

**Fix**:

```bash
# Reset the password
sudo -u postgres psql -c "ALTER USER dbt_user WITH PASSWORD 'new_password';"

# Update the environment variable
export DBT_POSTGRES_PASSWORD='new_password'
```

### Issue 4: Schema does not exist

```
ERROR: schema "staging" does not exist
```

**Fix**: Create the schema:

```sql
CREATE SCHEMA IF NOT EXISTS staging;
GRANT ALL ON SCHEMA staging TO dbt_user;
```

### Issue 5: Permission denied for schema

```
ERROR: permission denied for schema raw_blood_bank
```

**Fix**:

```sql
-- Run as postgres superuser
GRANT USAGE ON SCHEMA raw_blood_bank TO dbt_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw_blood_bank TO dbt_user;
GRANT CREATE ON SCHEMA staging TO dbt_user;
GRANT CREATE ON SCHEMA marts TO dbt_user;
```

### Issue 6: `env_var` not found

```
Runtime Error: Env var required but not provided: 'DBT_POSTGRES_PASSWORD'
```

**Fix**:

```bash
# Set the environment variable
export DBT_POSTGRES_PASSWORD='your_password'

# Or temporarily for one command
DBT_POSTGRES_PASSWORD='your_password' dbt debug
```

---

## 12. Key Takeaways

| Concept | One-Line Summary |
|---------|-----------------|
| **dbt-core** | Open-source CLI tool. Install with `pip install dbt-core dbt-postgres` |
| **Adapters** | Plugins that let dbt talk to specific databases (`dbt-postgres`, `dbt-bigquery`) |
| **profiles.yml** | Lives in `~/.dbt/`. Stores database connection info. Never commit to Git! |
| **dbt_project.yml** | Lives in your project root. Configures project structure and materializations |
| **dbt init** | Scaffolds a new dbt project with standard directory structure |
| **dbt debug** | Tests your connection to the database |
| **dbt run** | Executes all your SQL models in dependency order |
| **Materializations** | `view` (staging), `table` (marts), `incremental` (large facts), `ephemeral` (CTEs) |
| **Seeds** | Small CSV files loaded with `dbt seed` — for reference data only |
| **env_var()** | Jinja function to read environment variables — use for passwords |

---

## 🔜 Next Module

**[Module 3: Bronze Sources and Silver Staging →](./03_Bronze_Sources_and_Silver_Staging.md)**

In the next module, you'll:
- Define `sources.yml` to formally reference your Bronze tables
- Write proper staging models with `{{ source() }}` function
- Master naming conventions and data type casting
- Build the complete Silver layer for the blood bank project

---

> **📝 Author's Note**: If `dbt debug` shows "All checks passed!" — congratulations, you've completed the hardest part. Setup is always harder than the actual coding. From here, it's pure SQL and Jinja. The fun begins in Module 3.
