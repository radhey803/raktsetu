# 📘 Module 1: dbt Core Concepts and Architecture

> **Masterclass Series**: dbt — From Absolute Beginner to Senior Data Engineer  
> **Module**: 1 of 5  
> **Difficulty**: 🟢 Beginner  
> **Estimated Time**: 2–3 hours  
> **Theme**: India Blood Bank Inventory System (eRaktKosh)

---

## 📑 Table of Contents

1. [What Problem Are We Solving?](#1-what-problem-are-we-solving)
2. [The Old Way: ETL (Extract, Transform, Load)](#2-the-old-way-etl-extract-transform-load)
3. [The New Way: ELT (Extract, Load, Transform)](#3-the-new-way-elt-extract-load-transform)
4. [The Modern Data Stack (MDS)](#4-the-modern-data-stack-mds)
5. [Deep Dive: Medallion Architecture (Bronze → Silver → Gold)](#5-deep-dive-medallion-architecture-bronze--silver--gold)
6. [Where dbt Fits — The "T" in ELT](#6-where-dbt-fits--the-t-in-elt)
7. [Why dbt Replaced Stored Procedures](#7-why-dbt-replaced-stored-procedures)
8. [dbt Core vs. dbt Cloud](#8-dbt-core-vs-dbt-cloud)
9. [Mental Model: How dbt Thinks](#9-mental-model-how-dbt-thinks)
10. [Practice Exercises](#10-practice-exercises)
11. [Key Takeaways](#11-key-takeaways)

---

## 1. What Problem Are We Solving?

Imagine you work at **eRaktKosh** — India's centralized blood bank management system. Every day, **3,000+ blood banks** across India send you raw inventory data:

```
hospitalname, State, District, componentName, blood_group, quantity, entrydate, hospitalType ...
```

Your job is to answer questions like:

- 🩸 *Which states have critically low O+ Packed Red Blood Cells right now?*
- 🏥 *Which government hospitals haven't updated their inventory in 7 days?*
- 📊 *What's the national trend of blood availability over the last 90 days?*
- ⚠️ *Which districts have ZERO units of any rare blood group (e.g., Oh-VE)?*

**The raw CSV data cannot answer any of these questions directly.** It needs to be:

1. **Extracted** from the source (scraped from eRaktKosh API)
2. **Loaded** into a data warehouse (PostgreSQL, BigQuery, Snowflake)
3. **Transformed** into clean, analytics-ready tables

This is where the **Modern Data Stack** comes in, and dbt is the **industry-standard tool** for step 3.

---

## 2. The Old Way: ETL (Extract, Transform, Load)

### How ETL Works

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  SOURCE  │ ──► │  TRANSFORM   │ ──► │  DATA        │
│  SYSTEM  │     │  (middleware) │     │  WAREHOUSE   │
└──────────┘     └──────────────┘     └──────────────┘
     E                  T                    L
```

In the **ETL** paradigm:

1. **Extract**: Pull raw data from sources (APIs, databases, files)
2. **Transform**: Clean, join, and reshape data **BEFORE** loading it into the warehouse — often using expensive middleware tools like **Informatica**, **SSIS**, or **Talend**
3. **Load**: Push the cleaned data into the warehouse

### Why ETL Was the Standard (2000s–2015)

| Factor | Reality |
|--------|---------|
| **Storage was expensive** | Disk space on data warehouses cost $$$. You only wanted clean data in there. |
| **Compute was limited** | Warehouses couldn't handle heavy transformations. |
| **Tools were monolithic** | One tool (Informatica) did everything — extraction, transformation, loading. |

### The Problems with ETL

| Problem | Impact |
|---------|--------|
| **Slow feedback loops** | A single pipeline change required redeploying the entire ETL job. |
| **Vendor lock-in** | Informatica licenses cost **$100K–$500K/year**. |
| **No version control** | Transformations lived inside proprietary GUIs, not in Git. |
| **Fragile pipelines** | One schema change upstream could break everything downstream with no warning. |
| **Data loss risk** | If the transform step failed, you lost the raw data — it was never loaded. |

### Blood Bank ETL Example (The Old Way)

```
eRaktKosh API → [Informatica Server: Clean nulls, cast types, join tables] → PostgreSQL
```

If the API adds a new column `vaccine_status`, the entire Informatica job breaks. You can't debug it because the logic is buried in a drag-and-drop GUI.

---

## 3. The New Way: ELT (Extract, Load, Transform)

### How ELT Works

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  SOURCE  │ ──► │  DATA        │ ──► │  TRANSFORM   │
│  SYSTEM  │     │  WAREHOUSE   │     │  (in-warehouse)│
└──────────┘     └──────────────┘     └──────────────┘
     E                  L                    T
```

The **key insight**: Modern cloud data warehouses (BigQuery, Snowflake, Redshift, even PostgreSQL) are **so powerful and cheap** that you should:

1. **Extract**: Pull raw data from sources
2. **Load**: Dump the raw data **as-is** into the warehouse (no transformation!)
3. **Transform**: Use SQL **inside the warehouse** to clean and model the data

### Why ELT Won

| Factor | Why It's Better |
|--------|----------------|
| **Storage is cheap** | Cloud storage costs ~$0.02/GB/month. Load everything! |
| **Compute is elastic** | Warehouses can auto-scale to handle any transformation. |
| **Raw data is preserved** | You always have the original data. You can re-transform it any time. |
| **SQL is the universal language** | Every data professional knows SQL. No proprietary tools needed. |
| **Version control** | Transformations are SQL files that live in Git. |

### Blood Bank ELT Example (The New Way)

```
eRaktKosh API → [Airbyte/Fivetran: Just load it] → PostgreSQL (raw data)
                                                          ↓
                                                    [dbt: Transform with SQL]
                                                          ↓
                                                    PostgreSQL (clean analytics tables)
```

If the API adds a new column `vaccine_status`, **nothing breaks**. The raw data just gets a new column. You update your dbt models when you're ready.

---

## 4. The Modern Data Stack (MDS)

The **Modern Data Stack** is the industry-standard architecture for analytics engineering. It's a collection of best-in-class tools, each doing one thing exceptionally well:

```
┌─────────────────────────────────────────────────────────────────┐
│                    THE MODERN DATA STACK                        │
│                                                                 │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌──────────┐ │
│  │  EXTRACT  │   │   LOAD    │   │ TRANSFORM │   │ VISUALIZE│ │
│  │  & LOAD   │──►│   (Data   │──►│   (dbt)   │──►│(BI Tool) │ │
│  │(Ingestion)│   │ Warehouse)│   │           │   │          │ │
│  └───────────┘   └───────────┘   └───────────┘   └──────────┘ │
│                                                                 │
│  Fivetran        BigQuery         dbt Core /      Metabase     │
│  Airbyte         Snowflake        dbt Cloud       Looker       │
│  Custom Python   Redshift                         Superset     │
│  (your scraper!) PostgreSQL                       Grafana      │
│                  Databricks                       Power BI     │
└─────────────────────────────────────────────────────────────────┘
```

### How This Maps to Our Blood Bank Project

| Layer | Tool | What It Does |
|-------|------|-------------|
| **Extract & Load** | Your `async_scraper.py` | Scrapes eRaktKosh API and dumps raw CSV data |
| **Data Warehouse** | PostgreSQL | Stores the raw and transformed data |
| **Transform** | **dbt** | Cleans, models, and tests the data using SQL |
| **Visualize** | Metabase / Grafana / Custom Dashboard | Renders charts and dashboards |

> **💡 Key Insight**: dbt does NOT extract or load data. It **only transforms** data that is already inside your warehouse. This is the "T" in ELT.

### The MDS Philosophy: Best-in-Class, Not All-in-One

Unlike the old days where one tool (Informatica) did everything poorly, the MDS uses **specialized tools** that excel at one job:

| Old World (Monolith) | New World (MDS) |
|----------------------|-----------------|
| Informatica does E, T, and L | Airbyte does E+L, dbt does T, Looker does visualization |
| One vendor, one license, one headache | Best tool for each job, swappable |
| GUI-based, no version control | Code-based, Git-native, CI/CD ready |

---

## 5. Deep Dive: Medallion Architecture (Bronze → Silver → Gold)

The **Medallion Architecture** (popularized by Databricks, now industry standard) organizes your data warehouse into **three layers of increasing quality**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDALLION ARCHITECTURE                        │
│                                                                 │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐             │
│  │  BRONZE  │ ───► │  SILVER  │ ───► │   GOLD   │             │
│  │  (Raw)   │      │ (Cleaned)│      │(Business)│             │
│  └──────────┘      └──────────┘      └──────────┘             │
│                                                                 │
│  "Land it"         "Clean it"        "Serve it"                │
│                                                                 │
│  Raw CSVs          Type-casted       Aggregated                │
│  API dumps         Renamed cols      Joined tables             │
│  Duplicates OK     Deduplicated      Business KPIs             │
│  No schema         Consistent schema Dashboard-ready           │
└─────────────────────────────────────────────────────────────────┘
```

### 🥉 Bronze Layer (Raw / Landing Zone)

**Purpose**: Store raw data exactly as it arrived from the source. No transformations. No cleaning. Just dump it.

**Blood Bank Example**:

```sql
-- This is your raw table in PostgreSQL
-- It mirrors your INDIA_blood_inventory_async.csv exactly

CREATE TABLE raw_blood_bank.blood_inventory_raw (
    bldgrpcode1         TEXT,       -- Might be null, might be messy
    compId              TEXT,       -- No type casting
    componentName       TEXT,
    count               TEXT,       -- It's TEXT, not INTEGER! (raw data)
    hospitalname        TEXT,
    hospitaladd         TEXT,       -- Full address as one messy string
    hospitalcontact     TEXT,       -- Phone, fax, email all mashed together
    hospitalCode        TEXT,
    moderateStock       TEXT,
    hospitalType        TEXT,       -- "Govt.", "Charitable/Vol", "Private"
    entrydate           TEXT,       -- "2026-10-08 23:41:54" as TEXT
    offline             TEXT,       -- "1" or "0" as TEXT
    type                TEXT,       -- "Blood Bank" or "BSU"
    available_WithQty   TEXT,       -- Empty or complex string
    components          TEXT,       -- Giant JSON-like string
    not_available_WithQty TEXT,
    State               TEXT,
    District            TEXT
);
```

**Rules for Bronze**:
- ✅ Store data as-is (TEXT types are fine)
- ✅ Include metadata columns: `_loaded_at`, `_source_file`
- ✅ Keep duplicates (you'll deduplicate in Silver)
- ❌ Never transform Bronze data directly for analytics
- ❌ Never delete records from Bronze (it's your source of truth)

### 🥈 Silver Layer (Cleaned / Staging)

**Purpose**: Clean, type-cast, rename, and deduplicate the Bronze data. This is where the data becomes **trustworthy**.

**Blood Bank Example**:

```sql
-- Silver layer: stg_blood_bank__hospitals
-- Notice the naming convention: stg_{source}__{entity}

SELECT
    CAST(hospitalCode AS INTEGER)           AS hospital_id,
    TRIM(hospitalname)                      AS hospital_name,
    TRIM(hospitaladd)                       AS hospital_address,
    TRIM(hospitalType)                      AS hospital_type,
    TRIM(State)                             AS state_name,
    TRIM(District)                          AS district_name,
    CASE 
        WHEN TRIM(type) = 'Blood Bank' THEN 'blood_bank'
        WHEN TRIM(type) = 'BSU' THEN 'blood_storage_unit'
        ELSE 'unknown'
    END                                     AS facility_type,
    CAST(offline AS BOOLEAN)                AS is_offline,
    CAST(entrydate AS TIMESTAMP)            AS last_updated_at,
    CURRENT_TIMESTAMP                       AS _transformed_at
FROM raw_blood_bank.blood_inventory_raw
WHERE hospitalCode IS NOT NULL
  AND hospitalCode != '-'
```

**Rules for Silver**:
- ✅ Cast all columns to proper data types (`TEXT` → `INTEGER`, `TIMESTAMP`, `BOOLEAN`)
- ✅ Rename columns to `snake_case` (no more `hospitalname` → `hospital_name`)
- ✅ Apply basic filters (remove obvious junk rows)
- ✅ Deduplicate records
- ✅ Use `stg_` prefix in table names
- ❌ No business logic yet (no aggregations, no joins across sources)

### 🥇 Gold Layer (Business / Marts)

**Purpose**: Build business-ready tables that directly answer stakeholder questions. This layer contains **aggregations, joins, and KPIs**.

**Blood Bank Example**:

```sql
-- Gold layer: fct_blood_availability
-- Fact table with one row per hospital-component-blood_group combination

SELECT
    h.hospital_id,
    h.hospital_name,
    h.state_name,
    h.district_name,
    c.component_name,
    c.blood_group,
    c.available_units,
    CASE 
        WHEN c.available_units = 0 THEN 'OUT_OF_STOCK'
        WHEN c.available_units BETWEEN 1 AND 5 THEN 'CRITICAL'
        WHEN c.available_units BETWEEN 6 AND 20 THEN 'LOW'
        ELSE 'ADEQUATE'
    END AS stock_status,
    h.last_updated_at,
    CURRENT_DATE - h.last_updated_at::date AS days_since_update
FROM stg_blood_bank__hospitals h
JOIN stg_blood_bank__components c
    ON h.hospital_id = c.hospital_id
```

```sql
-- Gold layer: dim_hospitals (Dimension table)
-- One row per hospital with enriched attributes

SELECT
    hospital_id,
    hospital_name,
    hospital_address,
    state_name,
    district_name,
    hospital_type,
    facility_type,
    is_offline,
    last_updated_at,
    CASE 
        WHEN CURRENT_DATE - last_updated_at::date > 7 THEN 'STALE'
        WHEN CURRENT_DATE - last_updated_at::date > 3 THEN 'WARNING'
        ELSE 'FRESH'
    END AS data_freshness_status
FROM stg_blood_bank__hospitals
```

**Rules for Gold**:
- ✅ Use `fct_` prefix for **fact tables** (events, transactions, measurements)
- ✅ Use `dim_` prefix for **dimension tables** (entities, lookups, attributes)
- ✅ Apply business logic (KPIs, status classifications, aggregations)
- ✅ Join data from multiple Silver tables
- ✅ These tables directly power dashboards and reports
- ❌ Never reference Bronze tables directly — always go through Silver

### The Complete Flow

```
eRaktKosh API
     │
     ▼
┌──────────┐    Your async_scraper.py loads CSV into PostgreSQL
│  BRONZE  │    raw_blood_bank.blood_inventory_raw
│  (Raw)   │    → All TEXT columns, duplicates, messy data
└────┬─────┘
     │
     ▼         dbt transforms (SQL models)
┌──────────┐
│  SILVER  │    staging.stg_blood_bank__hospitals
│ (Cleaned)│    staging.stg_blood_bank__components
└────┬─────┘    → Proper types, snake_case, deduplicated
     │
     ▼         dbt transforms (SQL models)
┌──────────┐
│   GOLD   │    marts.fct_blood_availability
│(Business)│    marts.dim_hospitals
└──────────┘    marts.dim_blood_components
                → Business logic, KPIs, dashboard-ready
```

---

## 6. Where dbt Fits — The "T" in ELT

Let's be crystal clear about what dbt does and does NOT do:

### ✅ What dbt DOES

| Capability | How |
|-----------|-----|
| **Transform data** | Runs SELECT statements that create tables/views in your warehouse |
| **Test data quality** | Asserts that columns are unique, not null, within expected values |
| **Document data** | Generates a website with table descriptions, column docs, and lineage graphs |
| **Build dependency graphs (DAG)** | Automatically determines the correct order to run models |
| **Version control** | All logic is SQL files in Git — PRs, code review, blame, history |
| **DRY code with Jinja** | Macros and Jinja templating eliminate copy-paste SQL |

### ❌ What dbt does NOT do

| Not dbt's job | Use this instead |
|--------------|-----------------|
| Extract data from APIs | Airbyte, Fivetran, custom Python scripts |
| Load data into the warehouse | Airbyte, Fivetran, `COPY` commands, your `async_scraper.py` |
| Orchestrate/schedule pipelines | Apache Airflow, Dagster, Prefect, cron |
| Visualize data | Metabase, Grafana, Looker, Superset |
| Real-time streaming | Apache Kafka, Flink, Spark Streaming |

### The dbt Mental Model

```
┌──────────────────────────────────────────────┐
│               YOUR DATA WAREHOUSE            │
│                                              │
│  ┌────────────────┐                          │
│  │  raw_blood_bank│  ← Data already here     │
│  │  (Bronze)      │     (loaded by scraper)  │
│  └───────┬────────┘                          │
│          │                                   │
│          │  dbt reads from here              │
│          ▼                                   │
│  ┌────────────────┐                          │
│  │    staging     │  ← dbt CREATES this      │
│  │    (Silver)    │     using SELECT queries  │
│  └───────┬────────┘                          │
│          │                                   │
│          │  dbt reads from here              │
│          ▼                                   │
│  ┌────────────────┐                          │
│  │     marts      │  ← dbt CREATES this      │
│  │     (Gold)     │     using SELECT queries  │
│  └────────────────┘                          │
│                                              │
│  dbt ONLY runs SQL inside the warehouse.     │
│  It doesn't move data in or out.             │
└──────────────────────────────────────────────┘
```

> **💡 The most important thing to understand**: A dbt model is just a `SELECT` statement saved as a `.sql` file. dbt wraps it in a `CREATE TABLE AS` or `CREATE VIEW AS` statement and runs it in your warehouse. That's it. That's the magic.

---

## 7. Why dbt Replaced Stored Procedures

Before dbt, the "T" in ELT was done using **stored procedures** — SQL code stored directly inside the database. Here's why the industry moved away from them:

### Stored Procedures: The Old Way

```sql
-- A stored procedure in PostgreSQL
CREATE OR REPLACE PROCEDURE transform_blood_inventory()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Step 1: Clean hospitals
    DROP TABLE IF EXISTS staging.hospitals;
    CREATE TABLE staging.hospitals AS
    SELECT ...
    FROM raw_blood_bank.blood_inventory_raw;

    -- Step 2: Create availability fact table
    DROP TABLE IF EXISTS marts.blood_availability;
    CREATE TABLE marts.blood_availability AS
    SELECT ...
    FROM staging.hospitals;

    -- Step 3: Hope nothing broke 🤞
    COMMIT;
END;
$$;
```

### The Problems with Stored Procedures

| Problem | dbt's Solution |
|---------|---------------|
| **No version control** — procedures live in the database, not in Git | dbt models are `.sql` files in a Git repo. Full history, PRs, blame. |
| **No dependency management** — you manually order procedures | dbt auto-builds a DAG using `{{ ref() }}`. It knows the correct order. |
| **No testing** — you hope the data is correct | dbt has built-in tests: `unique`, `not_null`, `accepted_values`, custom SQL tests. |
| **No documentation** — tribal knowledge only | `dbt docs generate` creates a website with lineage graphs and column descriptions. |
| **No DRY code** — copy-paste SQL everywhere | Jinja macros let you write reusable SQL functions. |
| **Database-specific** — PL/pgSQL ≠ T-SQL ≠ PL/SQL | dbt abstracts SQL dialects. Same project works on Postgres, BigQuery, Snowflake. |
| **No environments** — dev = prod (😱) | dbt supports dev/staging/prod environments with different schemas. |
| **Monolithic** — one giant procedure with 500 lines | dbt encourages modular, single-purpose models. |

### A dbt Model: The New Way

```sql
-- models/staging/stg_blood_bank__hospitals.sql
-- This is the ENTIRE file. Just a SELECT statement.

SELECT
    CAST(hospitalCode AS INTEGER) AS hospital_id,
    TRIM(hospitalname) AS hospital_name,
    TRIM(State) AS state_name,
    CAST(entrydate AS TIMESTAMP) AS last_updated_at
FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
WHERE hospitalCode IS NOT NULL
  AND hospitalCode != '-'
```

dbt takes this `SELECT` and automatically wraps it in:

```sql
CREATE TABLE staging.stg_blood_bank__hospitals AS (
    SELECT
        CAST(hospitalCode AS INTEGER) AS hospital_id,
        TRIM(hospitalname) AS hospital_name,
        ...
);
```

**You write the SELECT. dbt handles everything else.**

---

## 8. dbt Core vs. dbt Cloud

| Feature | dbt Core (Open Source) | dbt Cloud (SaaS) |
|---------|----------------------|-------------------|
| **Price** | Free forever | Free tier + paid plans |
| **Where it runs** | Your machine / CI server | dbt Labs' servers |
| **CLI** | ✅ Full `dbt run`, `dbt test`, etc. | ✅ Same CLI + Web IDE |
| **Scheduling** | You manage (Airflow, cron) | Built-in scheduler |
| **Git integration** | You manage | Built-in |
| **Documentation hosting** | You host | Hosted for you |
| **Best for** | Learning, full control, production with Airflow | Teams wanting managed service |

> **📌 For this masterclass**: We will use **dbt Core** (open source) with **PostgreSQL**. This gives you maximum learning and is the setup used in most production environments with Airflow.

---

## 9. Mental Model: How dbt Thinks

### The DAG (Directed Acyclic Graph)

dbt's superpower is the **DAG** — a dependency graph that determines the order in which models run:

```
                    ┌─────────────────────────┐
                    │    sources.yml          │
                    │    (Bronze: raw tables)  │
                    └──────────┬──────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │stg_blood_bank│  │stg_blood_bank│  │stg_blood_bank│
    │__hospitals   │  │__components  │  │__contacts    │
    │  (Silver)    │  │  (Silver)    │  │  (Silver)    │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           └────────┬────────┘                 │
                    ▼                          │
          ┌──────────────────┐                 │
          │fct_blood_        │                 │
          │availability      │                 │
          │  (Gold)          │                 │
          └────────┬─────────┘                 │
                   │                           │
                   └─────────┬─────────────────┘
                             ▼
                   ┌──────────────────┐
                   │dim_hospitals     │
                   │  (Gold)          │
                   └──────────────────┘
```

When you run `dbt run`, dbt:

1. Parses all `.sql` files
2. Finds `{{ source() }}` and `{{ ref() }}` calls
3. Builds the DAG (dependency tree)
4. Executes models in the correct order (sources first, then staging, then marts)
5. Reports success/failure for each model

### Key dbt Commands (Preview)

| Command | What It Does |
|---------|-------------|
| `dbt run` | Executes all models (creates/refreshes tables and views) |
| `dbt test` | Runs all data quality tests |
| `dbt build` | Runs models AND tests in dependency order |
| `dbt docs generate` | Creates documentation website |
| `dbt docs serve` | Opens documentation in browser |
| `dbt compile` | Compiles Jinja → raw SQL (for debugging) |
| `dbt seed` | Loads CSV files into the warehouse as tables |
| `dbt source freshness` | Checks if source data is stale |

---

## 10. Practice Exercises

### 🏋️ Exercise 1: Draw the Architecture (Paper/Whiteboard)

On a piece of paper, draw the complete data flow for the blood bank project:

1. **Source**: eRaktKosh API
2. **Extract & Load**: Your Python scraper → CSV → PostgreSQL
3. **Transform**: dbt (Bronze → Silver → Gold)
4. **Visualize**: Dashboard

Label each component with:
- The tool used
- The Medallion layer (Bronze/Silver/Gold)
- One example table name

**Expected output:**

```
eRaktKosh API
     │
     ▼ (async_scraper.py)
┌─────────────────────────────────┐
│ PostgreSQL                      │
│                                 │
│  BRONZE: raw.blood_inventory    │
│     │                           │
│     ▼ (dbt)                     │
│  SILVER: staging.stg_hospitals  │
│     │                           │
│     ▼ (dbt)                     │
│  GOLD: marts.fct_availability   │
└─────────────────────────────────┘
     │
     ▼
  Dashboard (Metabase/Grafana)
```

---

### 🏋️ Exercise 2: ETL vs. ELT Classification

For each scenario below, determine if it's ETL or ELT:

| # | Scenario | ETL or ELT? |
|---|----------|-------------|
| 1 | Data is cleaned in Informatica before loading into Oracle | ? |
| 2 | Raw JSON is dumped into BigQuery, then transformed with dbt | ? |
| 3 | A Python script cleans CSVs, then loads them into PostgreSQL | ? |
| 4 | Fivetran loads raw API data into Snowflake, dbt transforms it | ? |
| 5 | An SSIS package transforms data in-memory before writing to SQL Server | ? |

<details>
<summary>Click to reveal answers</summary>

| # | Answer | Explanation |
|---|--------|-------------|
| 1 | **ETL** | Transformation happens BEFORE loading (in Informatica middleware) |
| 2 | **ELT** | Raw data loaded first, then transformed in-warehouse with dbt |
| 3 | **ETL** | Python cleans data BEFORE loading into Postgres |
| 4 | **ELT** | Fivetran loads raw data, dbt transforms inside Snowflake |
| 5 | **ETL** | SSIS transforms in-memory (middleware) before loading |

</details>

---

### 🏋️ Exercise 3: Classify These Tables by Medallion Layer

Given these table names, classify them as Bronze, Silver, or Gold:

| Table Name | Layer |
|-----------|-------|
| `raw_blood_bank.blood_inventory_dump` | ? |
| `staging.stg_blood_bank__hospitals` | ? |
| `marts.fct_daily_blood_availability` | ? |
| `raw_blood_bank.api_response_log` | ? |
| `staging.stg_blood_bank__blood_components` | ? |
| `marts.dim_districts` | ? |
| `marts.rpt_state_wise_availability_summary` | ? |

<details>
<summary>Click to reveal answers</summary>

| Table Name | Layer | Why |
|-----------|-------|-----|
| `raw_blood_bank.blood_inventory_dump` | **🥉 Bronze** | `raw_` schema, dump in name, unprocessed |
| `staging.stg_blood_bank__hospitals` | **🥈 Silver** | `stg_` prefix, staging schema, cleaned entity |
| `marts.fct_daily_blood_availability` | **🥇 Gold** | `fct_` prefix, marts schema, business metric |
| `raw_blood_bank.api_response_log` | **🥉 Bronze** | Raw API logs, unprocessed |
| `staging.stg_blood_bank__blood_components` | **🥈 Silver** | `stg_` prefix, cleaned entity |
| `marts.dim_districts` | **🥇 Gold** | `dim_` prefix, dimension table |
| `marts.rpt_state_wise_availability_summary` | **🥇 Gold** | `rpt_` report table, aggregated business data |

</details>

---

### 🏋️ Exercise 4: Spot the Anti-Patterns

Review this data architecture and identify **at least 3 problems**:

```
eRaktKosh API
     │
     ▼
PostgreSQL (raw.blood_data)
     │
     ▼
marts.blood_summary  ← (dbt model that reads directly from raw table)
     │
     ▼
Dashboard
```

<details>
<summary>Click to reveal answers</summary>

**Anti-patterns identified:**

1. **❌ No Silver/Staging layer**: The Gold mart reads directly from Bronze. There's no data cleaning step. If the raw data has nulls, wrong types, or duplicates, they'll propagate directly to the dashboard.

2. **❌ No data testing**: There are no tests between layers. How do you know `hospital_id` is unique? How do you know `state_name` isn't null? Without tests, you're flying blind.

3. **❌ Single model does everything**: One model (`blood_summary`) is trying to clean AND aggregate AND apply business logic. This violates the Single Responsibility Principle and makes debugging impossible.

4. **❌ No intermediate models**: If the mart fails, you have to re-process everything from raw. With a Silver layer, you'd only need to re-run the Gold layer.

**Correct architecture:**
```
raw.blood_data → stg_blood_bank__hospitals → fct_blood_availability → Dashboard
                 stg_blood_bank__components → dim_hospitals
```

</details>

---

### 🏋️ Exercise 5: Write a Pseudo-Silver Model

Without looking at the examples above, write a pseudo-SQL `SELECT` statement that would transform this raw blood bank row into a clean Silver row:

**Raw data:**

| hospitalname | hospitalCode | State | District | hospitalType | entrydate | offline |
|-------------|-------------|-------|----------|-------------|-----------|---------|
| `  G.B.Pant Hospital  ` | `280695` | `Andaman and Nicobar Islands` | `South Andaman` | `Govt.` | `2026-09-11 10:15:31` | `1` |

**Requirements:**
- Remove leading/trailing whitespace from text fields
- Cast `hospitalCode` to INTEGER
- Cast `entrydate` to TIMESTAMP
- Cast `offline` to BOOLEAN
- Rename columns to snake_case

<details>
<summary>Click to reveal solution</summary>

```sql
SELECT
    CAST(hospitalCode AS INTEGER)       AS hospital_id,
    TRIM(hospitalname)                  AS hospital_name,
    TRIM(State)                         AS state_name,
    TRIM(District)                      AS district_name,
    TRIM(hospitalType)                  AS hospital_type,
    CAST(entrydate AS TIMESTAMP)        AS last_updated_at,
    CASE 
        WHEN offline = '1' THEN TRUE 
        ELSE FALSE 
    END                                 AS is_offline
FROM raw_blood_bank.blood_inventory_raw
```

</details>

---

## 11. Key Takeaways

| Concept | One-Line Summary |
|---------|-----------------|
| **ETL** | Transform BEFORE loading. Old, expensive, fragile. |
| **ELT** | Load first, transform inside the warehouse. Modern, cheap, flexible. |
| **Modern Data Stack** | Best-in-class tools: Airbyte (EL) + dbt (T) + Looker (Viz) |
| **Medallion Architecture** | Bronze (raw) → Silver (clean) → Gold (business-ready) |
| **dbt** | The "T" in ELT. SQL-based transformation tool. Open-source. Industry standard. |
| **Stored Procedures** | The old way. No Git, no tests, no docs, no portability. |
| **DAG** | dbt automatically figures out the correct order to run your models. |

---

## 🔜 Next Module

**[Module 2: dbt Installation and PostgreSQL Setup →](./02_dbt_Installation_and_Postgres_Setup.md)**

In the next module, you'll:
- Install dbt-core and the PostgreSQL adapter
- Set up your `profiles.yml` securely
- Run `dbt init` and explore the generated project structure
- Load your blood bank CSV into PostgreSQL as the Bronze layer

---

> **📝 Author's Note**: If you can explain the Medallion Architecture and the difference between ETL and ELT to someone in under 2 minutes, you've mastered this module. Go explain it to a friend or a rubber duck. Teaching is the fastest way to learn.
