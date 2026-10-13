# 📘 Module 5: Pro-Level Macros, Incremental Models, and Deployment

> **Masterclass Series**: dbt — From Absolute Beginner to Senior Data Engineer  
> **Module**: 5 of 5  
> **Difficulty**: 🔴 Advanced → ⚫ Pro  
> **Estimated Time**: 5–6 hours  
> **Theme**: India Blood Bank Inventory System (eRaktKosh)  
> **Prerequisites**: Modules 1–4 completed. Full staging and marts layers built.

---

## 📑 Table of Contents

1. [Jinja Templating — The Language Inside SQL](#1-jinja-templating--the-language-inside-sql)
2. [Writing Custom Macros (DRY Principle)](#2-writing-custom-macros-dry-principle)
3. [Advanced Macro Patterns](#3-advanced-macro-patterns)
4. [Incremental Models — Handling Massive Datasets](#4-incremental-models--handling-massive-datasets)
5. [Incremental Strategies Deep Dive](#5-incremental-strategies-deep-dive)
6. [dbt Packages — Reusing Community Code](#6-dbt-packages--reusing-community-code)
7. [Data Lineage with dbt docs](#7-data-lineage-with-dbt-docs)
8. [Hooks: Pre and Post SQL Execution](#8-hooks-pre-and-post-sql-execution)
9. [Environment Management (Dev, Staging, Prod)](#9-environment-management-dev-staging-prod)
10. [CI/CD Pipeline with GitHub Actions](#10-cicd-pipeline-with-github-actions)
11. [Orchestration with Apache Airflow](#11-orchestration-with-apache-airflow)
12. [Production Best Practices Checklist](#12-production-best-practices-checklist)
13. [Practice Exercises](#13-practice-exercises)
14. [Senior Engineer Mindset](#14-senior-engineer-mindset)
15. [Key Takeaways — Full Course Summary](#15-key-takeaways--full-course-summary)

---

## 1. Jinja Templating — The Language Inside SQL

Jinja is the **templating language** that makes dbt models dynamic. It's embedded inside your SQL files using special delimiters:

### Jinja Syntax Reference

| Syntax | Purpose | Example |
|--------|---------|---------|
| `{{ ... }}` | **Expressions** — output a value | `{{ ref('model') }}`, `{{ var('threshold') }}` |
| `{% ... %}` | **Statements** — control flow (if, for, set) | `{% if target.name == 'prod' %}` |
| `{# ... #}` | **Comments** — ignored in output | `{# This is a Jinja comment #}` |

### Variables

```sql
-- Set a variable
{% set blood_groups = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'] %}

-- Use a variable
SELECT * FROM {{ ref('dim_hospitals') }}
WHERE days_since_update > {{ var('stale_data_threshold_days', 7) }}
```

### Conditionals (if/elif/else)

```sql
-- models/marts/analytics/fct_blood_availability.sql

SELECT
    hospital_id,
    hospital_name,
    
    {% if target.name == 'prod' %}
        -- In production: include all history
        *
    {% elif target.name == 'dev' %}
        -- In development: limit to recent data for speed
        *
    {% endif %}
    
FROM {{ ref('stg_blood_bank__hospitals') }}

{% if target.name == 'dev' %}
    WHERE last_inventory_update_at >= CURRENT_DATE - INTERVAL '30 days'
{% endif %}
```

### Loops (for)

```sql
-- Generate columns dynamically for each blood group

{% set blood_groups = ['A_POS', 'A_NEG', 'B_POS', 'B_NEG', 'O_POS', 'O_NEG', 'AB_POS', 'AB_NEG'] %}

SELECT
    state_name,
    {% for bg in blood_groups %}
        SUM(CASE WHEN blood_group = '{{ bg }}' THEN available_units ELSE 0 END) 
            AS {{ bg | lower }}_total_units
        {% if not loop.last %},{% endif %}
    {% endfor %}
FROM {{ ref('fct_blood_detail') }}
GROUP BY state_name
```

**Compiles to:**

```sql
SELECT
    state_name,
    SUM(CASE WHEN blood_group = 'A_POS' THEN available_units ELSE 0 END) AS a_pos_total_units,
    SUM(CASE WHEN blood_group = 'A_NEG' THEN available_units ELSE 0 END) AS a_neg_total_units,
    SUM(CASE WHEN blood_group = 'B_POS' THEN available_units ELSE 0 END) AS b_pos_total_units,
    SUM(CASE WHEN blood_group = 'B_NEG' THEN available_units ELSE 0 END) AS b_neg_total_units,
    SUM(CASE WHEN blood_group = 'O_POS' THEN available_units ELSE 0 END) AS o_pos_total_units,
    SUM(CASE WHEN blood_group = 'O_NEG' THEN available_units ELSE 0 END) AS o_neg_total_units,
    SUM(CASE WHEN blood_group = 'AB_POS' THEN available_units ELSE 0 END) AS ab_pos_total_units,
    SUM(CASE WHEN blood_group = 'AB_NEG' THEN available_units ELSE 0 END) AS ab_neg_total_units
FROM "blood_bank_db"."staging"."fct_blood_detail"
GROUP BY state_name
```

**8 columns generated from 3 lines of Jinja.** This is the power of DRY code.

### Jinja Filters

```sql
-- String filters
{{ 'hello world' | upper }}          -- HELLO WORLD
{{ 'HELLO WORLD' | lower }}          -- hello world
{{ 'hello' | capitalize }}           -- Hello
{{ '  spaces  ' | trim }}            -- spaces
{{ 'hello_world' | replace('_', ' ') }}  -- hello world

-- List filters
{% set items = ['a', 'b', 'c'] %}
{{ items | join(', ') }}             -- a, b, c
{{ items | length }}                 -- 3
{{ items | first }}                  -- a
{{ items | last }}                   -- c
```

---

## 2. Writing Custom Macros (DRY Principle)

### What Is a Macro?

A **macro** is a reusable Jinja function. Instead of copy-pasting the same SQL pattern everywhere, you define it once and call it from any model.

### Macro 1: `clean_text()` — Standardize Text Columns

```sql
-- macros/clean_text.sql

{% macro clean_text(column_name) %}
    TRIM(LOWER({{ column_name }}))
{% endmacro %}
```

**Usage:**

```sql
-- Before (repetitive)
SELECT
    TRIM(LOWER(hospitalname)) AS hospital_name,
    TRIM(LOWER(State)) AS state_name,
    TRIM(LOWER(District)) AS district_name

-- After (DRY with macro)
SELECT
    {{ clean_text('hospitalname') }} AS hospital_name,
    {{ clean_text('State') }} AS state_name,
    {{ clean_text('District') }} AS district_name
```

### Macro 2: `generate_surrogate_key()` — Create Deterministic Keys

```sql
-- macros/generate_surrogate_key.sql

{% macro generate_surrogate_key(columns) %}
    {#
        Generates a deterministic MD5 hash key from one or more columns.
        Handles NULLs by replacing them with the string 'NULL'.
        
        Usage: {{ generate_surrogate_key(['state_name', 'district_name']) }}
        Output: MD5('maharashtra||mumbai')
    #}
    MD5(
        {% for column in columns %}
            COALESCE(CAST({{ column }} AS TEXT), 'NULL')
            {% if not loop.last %} || '||' || {% endif %}
        {% endfor %}
    )
{% endmacro %}
```

**Usage:**

```sql
SELECT
    {{ generate_surrogate_key(['state_name', 'district_name']) }} AS district_id,
    state_name,
    district_name
FROM {{ ref('stg_blood_bank__hospitals') }}
```

**Compiles to:**

```sql
SELECT
    MD5(
        COALESCE(CAST(state_name AS TEXT), 'NULL') || '||' || 
        COALESCE(CAST(district_name AS TEXT), 'NULL')
    ) AS district_id,
    state_name,
    district_name
FROM "blood_bank_db"."staging"."stg_blood_bank__hospitals"
```

### Macro 3: `classify_stock_level()` — Reusable Business Logic

```sql
-- macros/classify_stock_level.sql

{% macro classify_stock_level(units_column) %}
    {#
        Classifies blood stock levels based on available units.
        
        Usage: {{ classify_stock_level('available_units') }} AS stock_status
    #}
    CASE
        WHEN {{ units_column }} IS NULL THEN 'UNKNOWN'
        WHEN {{ units_column }} = 0 THEN 'OUT_OF_STOCK'
        WHEN {{ units_column }} BETWEEN 1 AND {{ var('critical_stock_threshold', 5) }} THEN 'CRITICAL'
        WHEN {{ units_column }} BETWEEN 6 AND 20 THEN 'LOW'
        WHEN {{ units_column }} BETWEEN 21 AND 50 THEN 'MODERATE'
        ELSE 'ADEQUATE'
    END
{% endmacro %}
```

**Usage in multiple models:**

```sql
-- In fct_blood_detail.sql
SELECT
    available_units,
    {{ classify_stock_level('available_units') }} AS stock_status

-- In rpt_state_dashboard.sql
SELECT
    total_units,
    {{ classify_stock_level('total_units') }} AS state_stock_status
```

### Macro 4: `parse_contact_field()` — Extract Phone/Email from Raw String

```sql
-- macros/parse_contact_field.sql

{% macro parse_contact_field(contact_column, field_type) %}
    {#
        Extracts phone, fax, or email from a raw contact string.
        
        Raw format: "Phone: 9679535438 ,Fax: 0, Email: xxx@xxx.com"
        
        Usage: 
            {{ parse_contact_field('hospitalcontact', 'phone') }} AS phone_number
            {{ parse_contact_field('hospitalcontact', 'email') }} AS email_address
    #}
    
    {% if field_type == 'phone' %}
        CASE
            WHEN {{ contact_column }} LIKE '%Phone:%' THEN
                NULLIF(TRIM(SPLIT_PART(SPLIT_PART({{ contact_column }}, 'Phone:', 2), ',', 1)), '')
            ELSE NULL
        END
    {% elif field_type == 'fax' %}
        CASE
            WHEN {{ contact_column }} LIKE '%Fax:%' THEN
                NULLIF(
                    TRIM(SPLIT_PART(SPLIT_PART({{ contact_column }}, 'Fax:', 2), ',', 1)),
                    '0'
                )
            ELSE NULL
        END
    {% elif field_type == 'email' %}
        CASE
            WHEN {{ contact_column }} LIKE '%Email:%' THEN
                NULLIF(TRIM(LOWER(SPLIT_PART({{ contact_column }}, 'Email:', 2))), '')
            ELSE NULL
        END
    {% else %}
        NULL  -- Unknown field_type
    {% endif %}
    
{% endmacro %}
```

**Usage:**

```sql
-- models/staging/blood_bank/stg_blood_bank__contacts.sql

SELECT
    CAST(hospitalCode AS INTEGER) AS hospital_id,
    {{ parse_contact_field('hospitalcontact', 'phone') }} AS phone_number,
    {{ parse_contact_field('hospitalcontact', 'fax') }} AS fax_number,
    {{ parse_contact_field('hospitalcontact', 'email') }} AS email_address
FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
```

### Macro 5: `log_model_start()` — Audit Trail

```sql
-- macros/log_model_start.sql

{% macro log_model_start() %}
    {#
        Logs the model name and execution time.
        Call at the top of any model for debugging.
    #}
    {{ log("🔄 Running model: " ~ this.name ~ " at " ~ run_started_at, info=true) }}
{% endmacro %}
```

**Usage:**

```sql
-- At the top of any model:
{{ log_model_start() }}

SELECT ...
```

---

## 3. Advanced Macro Patterns

### Pattern 1: Dynamic Column Generation

```sql
-- macros/pivot_blood_groups.sql

{% macro pivot_blood_groups(source_column, agg_function='SUM') %}
    {#
        Generates pivot columns for all blood groups.
        
        Usage: {{ pivot_blood_groups('available_units', 'SUM') }}
        
        Generates:
            SUM(CASE WHEN blood_group = 'A+' THEN available_units END) AS a_pos_units,
            SUM(CASE WHEN blood_group = 'A-' THEN available_units END) AS a_neg_units,
            ...
    #}
    
    {% set blood_groups = {
        'A+': 'a_pos',
        'A-': 'a_neg',
        'B+': 'b_pos',
        'B-': 'b_neg',
        'O+': 'o_pos',
        'O-': 'o_neg',
        'AB+': 'ab_pos',
        'AB-': 'ab_neg',
        'Oh+': 'oh_pos',
        'Oh-': 'oh_neg'
    } %}
    
    {% for code, alias in blood_groups.items() %}
        {{ agg_function }}(
            CASE WHEN blood_group = '{{ code }}' THEN {{ source_column }} END
        ) AS {{ alias }}_units
        {% if not loop.last %},{% endif %}
    {% endfor %}
    
{% endmacro %}
```

**Usage:**

```sql
SELECT
    state_name,
    {{ pivot_blood_groups('available_units', 'SUM') }}
FROM {{ ref('fct_blood_detail') }}
GROUP BY state_name
```

### Pattern 2: Dynamic Schema Selection

```sql
-- macros/get_schema.sql

{% macro generate_schema_name(custom_schema_name, node) -%}
    {#
        In dbt, the default schema name is: <target_schema>_<custom_schema>
        Example: dev_staging, dev_marts
        
        This macro overrides that to use JUST the custom schema name:
        staging, marts (without the dev_ prefix)
        
        This is the standard behavior for production deployments.
    #}
    
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
    
{%- endmacro %}
```

**Effect:**

| Target | Custom Schema | Result |
|--------|--------------|--------|
| `dev` | `staging` | `dev_staging.stg_blood_bank__hospitals` |
| `dev` | `marts` | `dev_marts.fct_blood_availability` |
| `prod` | `staging` | `staging.stg_blood_bank__hospitals` |
| `prod` | `marts` | `marts.fct_blood_availability` |

### Pattern 3: Union All Sources Macro

```sql
-- macros/union_sources.sql

{% macro union_sources(source_name, table_names) %}
    {#
        Unions multiple source tables with a _source_table column.
        Useful when data arrives in separate tables by date/region.
        
        Usage: {{ union_sources('raw_blood_bank', ['inventory_jan', 'inventory_feb']) }}
    #}
    
    {% for table in table_names %}
        SELECT
            *,
            '{{ table }}' AS _source_table
        FROM {{ source(source_name, table) }}
        {% if not loop.last %}UNION ALL{% endif %}
    {% endfor %}
    
{% endmacro %}
```

---

## 4. Incremental Models — Handling Massive Datasets

### The Problem

Your `fct_daily_blood_inventory` table has **50 million rows** (3,000 hospitals × 10 components × 365 days × ~5 years). Every day, ~30,000 new rows are added.

**Without incremental:**

```bash
dbt run --select fct_daily_blood_inventory
# Drops the 50M row table
# Re-creates it from scratch (scans ALL 50M rows)
# Takes 45 minutes ⏱️
```

**With incremental:**

```bash
dbt run --select fct_daily_blood_inventory
# Only processes the ~30,000 new rows from today
# Inserts them into the existing table
# Takes 15 seconds ⏱️
```

### How Incremental Models Work

```
┌─────────────────────────────────────────────────────┐
│                INCREMENTAL MODEL                     │
│                                                      │
│  FIRST RUN:                                          │
│  ┌──────────┐     ┌──────────────────────────┐      │
│  │  Source   │ ──► │  CREATE TABLE AS SELECT  │      │
│  │  (all     │     │  (process ALL rows)      │      │
│  │   data)   │     └──────────────────────────┘      │
│  └──────────┘                                        │
│                                                      │
│  SUBSEQUENT RUNS:                                    │
│  ┌──────────┐     ┌──────────────────────────┐      │
│  │  Source   │ ──► │  INSERT INTO ... SELECT  │      │
│  │  (only    │     │  (process ONLY new rows) │      │
│  │   NEW     │     └──────────────────────────┘      │
│  │   data)   │                                       │
│  └──────────┘                                        │
│                                                      │
│  FULL REFRESH (manual):                              │
│  dbt run --full-refresh --select model_name          │
│  ──► Drops and rebuilds the entire table             │
└─────────────────────────────────────────────────────┘
```

### Building an Incremental Model

```sql
-- models/marts/analytics/fct_daily_blood_inventory.sql

-- ============================================================
-- INCREMENTAL FACT TABLE: Daily Blood Inventory Snapshots
-- Grain: One row per hospital per day
-- Strategy: Append new days only
--
-- This model runs FAST because it only processes rows
-- added since the last run.
-- ============================================================

{{
    config(
        materialized='incremental',
        unique_key=['hospital_id', 'snapshot_date'],
        incremental_strategy='delete+insert',
        on_schema_change='append_new_columns'
    )
}}

WITH hospitals AS (

    SELECT * FROM {{ ref('stg_blood_bank__hospitals') }}

),

components AS (

    SELECT * FROM {{ ref('stg_blood_bank__components') }}

),

daily_snapshot AS (

    SELECT
        h.hospital_id,
        h.hospital_name,
        h.state_name,
        h.district_name,
        h.hospital_type,
        COALESCE(c.has_available_stock, FALSE) AS has_available_stock,
        c.available_qty_raw,
        h.last_inventory_update_at,
        CURRENT_DATE AS snapshot_date,

        -- Business classifications
        {{ classify_stock_level('0') }} AS overall_stock_status,  -- Placeholder

        -- Metadata
        CURRENT_TIMESTAMP AS _inserted_at

    FROM hospitals h
    LEFT JOIN components c
        ON h.hospital_id = c.hospital_id

)

SELECT * FROM daily_snapshot

{# ========================================
   INCREMENTAL FILTER
   This is the KEY section that makes it incremental.
   On subsequent runs, only process rows NEWER than
   what's already in the table.
   ======================================== #}

{% if is_incremental() %}
    -- On incremental runs, only insert today's snapshot
    -- if it doesn't already exist
    WHERE snapshot_date > (SELECT MAX(snapshot_date) FROM {{ this }})
{% endif %}
```

### Understanding the Key Components

#### `is_incremental()` — The Magic Function

```sql
{% if is_incremental() %}
    WHERE snapshot_date > (SELECT MAX(snapshot_date) FROM {{ this }})
{% endif %}
```

| Run Type | `is_incremental()` | Behavior |
|----------|-------------------|----------|
| **First run** | `FALSE` | No WHERE clause → processes ALL rows → `CREATE TABLE AS` |
| **Subsequent runs** | `TRUE` | WHERE clause applied → processes only NEW rows → `INSERT INTO` |
| **`--full-refresh`** | `FALSE` | Drops table → processes ALL rows → `CREATE TABLE AS` |

#### `{{ this }}` — Self-Reference

```sql
WHERE snapshot_date > (SELECT MAX(snapshot_date) FROM {{ this }})
```

`{{ this }}` refers to the **current model's table**. It resolves to `marts.fct_daily_blood_inventory`.

#### `unique_key` — Deduplication Key

```yaml
config(
    unique_key=['hospital_id', 'snapshot_date']
)
```

The `unique_key` tells dbt: "If a row with this combination already exists, update it instead of inserting a duplicate."

#### `on_schema_change` — Handle Schema Evolution

```yaml
config(
    on_schema_change='append_new_columns'
)
```

| Option | Behavior |
|--------|----------|
| `'ignore'` | If you add a new column, it's silently dropped. Existing schema preserved. |
| `'fail'` | If schema changes, the model fails. You must `--full-refresh`. |
| `'append_new_columns'` | New columns are added to the table. Old columns remain. |
| `'sync_all_columns'` | Table schema is fully synced. Old columns removed, new ones added. |

---

## 5. Incremental Strategies Deep Dive

### Strategy 1: `append` (Default)

Simply inserts new rows. No deduplication.

```yaml
config(
    materialized='incremental',
    incremental_strategy='append'
)
```

**SQL generated:**

```sql
INSERT INTO marts.fct_daily_blood_inventory
SELECT * FROM (
    -- your model's SELECT
) WHERE snapshot_date > (SELECT MAX(snapshot_date) FROM marts.fct_daily_blood_inventory)
```

**Best for:** Event logs, audit trails, time-series data where duplicates are impossible.

### Strategy 2: `delete+insert` (Recommended for PostgreSQL)

Deletes existing rows with matching unique_key, then inserts new ones.

```yaml
config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key=['hospital_id', 'snapshot_date']
)
```

**SQL generated:**

```sql
-- Step 1: Delete existing rows
DELETE FROM marts.fct_daily_blood_inventory
WHERE (hospital_id, snapshot_date) IN (
    SELECT hospital_id, snapshot_date FROM __dbt_tmp_table
);

-- Step 2: Insert new rows
INSERT INTO marts.fct_daily_blood_inventory
SELECT * FROM __dbt_tmp_table;
```

**Best for:** Late-arriving data that needs to update existing records. Most common strategy.

### Strategy 3: `merge` (For databases that support MERGE)

Uses SQL `MERGE` (or `UPSERT`) — updates if exists, inserts if not.

```yaml
config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='hospital_id'
)
```

**Best for:** Slowly changing dimensions, BigQuery, Snowflake, Databricks.  
**Not available on:** PostgreSQL (use `delete+insert` instead).

### When to Use Incremental Models

| Scenario | Use Incremental? | Why |
|----------|------------------|-----|
| Staging models (Silver) | ❌ No | Small enough to rebuild. Views are always fresh. |
| Dimension tables (Gold) | ❌ Usually no | Dimensions are small. Full refresh is fast. |
| Fact tables < 1M rows | ❌ Probably not | Full refresh takes seconds. Complexity isn't worth it. |
| Fact tables > 10M rows | ✅ Yes | Full refresh takes minutes/hours. Incremental takes seconds. |
| Daily snapshots / time-series | ✅ Yes | Natural incremental pattern (only process today's data). |
| Event logs / audit trails | ✅ Yes | Append-only data, never needs to update. |

> **⚠️ Warning**: Incremental models add complexity. Don't use them unless you have a **performance problem** to solve. Start with `table` materialization and switch to `incremental` when the table gets too large.

---

## 6. dbt Packages — Reusing Community Code

### What Are Packages?

dbt packages are **pre-built macros, tests, and models** from the community that you can install into your project.

### Installing Packages

Create `packages.yml` in your project root:

```yaml
# packages.yml

packages:
  - package: dbt-labs/dbt_utils
    version: 1.3.0

  - package: dbt-labs/codegen
    version: 0.12.0

  - package: calogica/dbt_expectations
    version: 0.10.0
```

```bash
# Install packages
dbt deps

# This downloads packages to the dbt_packages/ directory
```

### dbt_utils — The Essential Package

`dbt_utils` provides 50+ utility macros. Here are the most useful:

#### `generate_surrogate_key()`

```sql
-- Instead of our custom macro, use dbt_utils:
SELECT
    {{ dbt_utils.generate_surrogate_key(['state_name', 'district_name']) }} AS district_id,
    state_name,
    district_name
FROM {{ ref('stg_blood_bank__hospitals') }}
```

#### `star()` — Select All Columns Except Specified

```sql
SELECT
    {{ dbt_utils.star(
        from=ref('stg_blood_bank__hospitals'),
        except=['_loaded_at', '_source_file', '_transformed_at']
    ) }}
FROM {{ ref('stg_blood_bank__hospitals') }}
```

#### `pivot()` — Dynamic Pivoting

```sql
SELECT
    state_name,
    {{ dbt_utils.pivot(
        column='hospital_type',
        values=['government', 'private', 'charitable'],
        agg='COUNT',
        then_value='hospital_id',
        else_value='NULL'
    ) }}
FROM {{ ref('stg_blood_bank__hospitals') }}
GROUP BY state_name
```

#### `date_spine()` — Generate Date Ranges

```sql
-- Generate all dates between two dates (useful for filling gaps in time-series)
{{ dbt_utils.date_spine(
    datepart="day",
    start_date="CAST('2024-01-01' AS DATE)",
    end_date="CURRENT_DATE"
) }}
```

#### `union_relations()` — Union Multiple Tables

```sql
-- Union multiple staging tables
{{ dbt_utils.union_relations(
    relations=[
        ref('stg_blood_bank__hospitals_2023'),
        ref('stg_blood_bank__hospitals_2024'),
        ref('stg_blood_bank__hospitals_2025')
    ]
) }}
```

### dbt_expectations — Data Quality Powerhouse

```yaml
# In your models YAML:

columns:
  - name: pct_hospitals_with_stock
    tests:
      - dbt_expectations.expect_column_values_to_be_between:
          min_value: 0
          max_value: 100

  - name: email_address
    tests:
      - dbt_expectations.expect_column_values_to_match_regex:
          regex: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

  - name: phone_number
    tests:
      - dbt_expectations.expect_column_value_lengths_to_be_between:
          min_value: 10
          max_value: 13
```

### codegen — Auto-Generate Code

```bash
# Generate a staging model from a source table
dbt run-operation generate_model_yaml --args '{"model_names": ["stg_blood_bank__hospitals"]}'

# Generate source YAML from existing database tables
dbt run-operation generate_source --args '{"schema_name": "raw_blood_bank", "database_name": "blood_bank_db"}'
```

---

## 7. Data Lineage with dbt docs

### Generating Documentation

```bash
# Step 1: Generate the docs
dbt docs generate

# Step 2: Serve them locally
dbt docs serve
# Opens http://localhost:8080 with an interactive documentation site
```

### What dbt docs Generates

```
┌─────────────────────────────────────────────────────────┐
│                dbt Documentation Site                    │
│                                                          │
│  📊 DAG Viewer                                           │
│  └── Interactive lineage graph                           │
│  └── Click any node to see its dependencies              │
│  └── Filter by tag, package, or model type               │
│                                                          │
│  📋 Model Catalog                                        │
│  └── Every model with its description                    │
│  └── Column names, types, and descriptions               │
│  └── SQL source code                                     │
│  └── Test results                                        │
│                                                          │
│  🔗 Source Catalog                                        │
│  └── All source tables with descriptions                 │
│  └── Freshness status                                    │
│  └── Column documentation                                │
└─────────────────────────────────────────────────────────┘
```

### Writing Better Documentation

#### In YAML files:

```yaml
models:
  - name: fct_blood_availability
    description: >
      **Core Fact Table**: Blood availability per hospital.
      
      ### Business Context
      This table powers the main blood bank availability dashboard.
      Each row represents one hospital's current blood availability status.
      
      ### Grain
      One row per `hospital_id`.
      
      ### Key Business Rules
      - `availability_status`: Classified based on stock AND data freshness
      - `urgency_level`: HIGH = blood bank with no stock, MEDIUM = BSU with no stock
      - `is_data_stale`: TRUE if data > 7 days old (configurable via var)
      
      ### Data Quality
      - `hospital_id` is unique and not null (tested)
      - `availability_status` is one of: AVAILABLE, POSSIBLY_AVAILABLE, OUT_OF_STOCK, UNKNOWN
      
      ### Usage
      ```sql
      -- Find all hospitals with critical stock in Maharashtra
      SELECT * FROM marts.fct_blood_availability
      WHERE state_name = 'Maharashtra'
        AND availability_status = 'OUT_OF_STOCK'
        AND urgency_level = 'HIGH'
      ```
```

#### In SQL files (using doc blocks):

```sql
-- models/marts/core/dim_hospitals.sql

{% docs hospital_data_freshness %}

### Data Freshness Status

Classifies how recent the hospital's inventory data is:

| Status | Criteria | Action |
|--------|----------|--------|
| FRESH | Updated within 1 day | ✅ Trust the data |
| RECENT | Updated within 3 days | ✅ Generally reliable |
| AGING | Updated within 7 days | ⚠️ Use with caution |
| STALE | Updated more than 7 days ago | ❌ Do not rely on this data |
| UNKNOWN | No update timestamp | ❌ Investigate |

{% enddocs %}
```

**Reference in YAML:**

```yaml
columns:
  - name: data_freshness_status
    description: '{{ doc("hospital_data_freshness") }}'
```

### Hosting Documentation

```bash
# For production, generate static HTML files
dbt docs generate

# The output is in target/
# You can host it on:
# - GitHub Pages
# - S3 + CloudFront
# - Any static file server
# - dbt Cloud (built-in hosting)
```

---

## 8. Hooks: Pre and Post SQL Execution

Hooks are SQL statements that run **before or after** model execution.

### Model-Level Hooks

```sql
-- models/marts/analytics/fct_blood_availability.sql

{{
    config(
        materialized='table',
        
        -- Run BEFORE the model
        pre_hook=[
            "CREATE INDEX IF NOT EXISTS idx_fct_avail_state ON {{ this }} (state_name)",
            "{{ log('Starting fct_blood_availability build', info=true) }}"
        ],
        
        -- Run AFTER the model
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_fct_avail_hospital ON {{ this }} (hospital_id)",
            "ANALYZE {{ this }}",
            "{{ log('Finished fct_blood_availability build', info=true) }}"
        ]
    )
}}

SELECT ...
```

### Project-Level Hooks

```yaml
# dbt_project.yml

on-run-start:
  - "{{ log('🚀 dbt run started at ' ~ run_started_at, info=true) }}"
  - "CREATE SCHEMA IF NOT EXISTS staging"
  - "CREATE SCHEMA IF NOT EXISTS marts"

on-run-end:
  - "{{ log('✅ dbt run completed. Models: ' ~ results | length, info=true) }}"
```

---

## 9. Environment Management (Dev, Staging, Prod)

### profiles.yml with Multiple Environments

```yaml
# ~/.dbt/profiles.yml

blood_bank_dbt:
  target: dev                      # Default to dev

  outputs:
    # ========================================
    # DEVELOPMENT (your local machine)
    # ========================================
    dev:
      type: postgres
      host: localhost
      port: 5432
      user: dbt_dev
      password: "{{ env_var('DBT_DEV_PASSWORD') }}"
      dbname: blood_bank_db
      schema: dev_{{ env_var('USER', 'default') }}    # dev_radhey
      threads: 4

    # ========================================
    # CI/CD (GitHub Actions / Jenkins)
    # ========================================
    ci:
      type: postgres
      host: "{{ env_var('DBT_CI_HOST') }}"
      port: 5432
      user: "{{ env_var('DBT_CI_USER') }}"
      password: "{{ env_var('DBT_CI_PASSWORD') }}"
      dbname: blood_bank_ci
      schema: ci_pr_{{ env_var('GITHUB_PR_NUMBER', 'unknown') }}
      threads: 4

    # ========================================
    # PRODUCTION
    # ========================================
    prod:
      type: postgres
      host: "{{ env_var('DBT_PROD_HOST') }}"
      port: 5432
      user: "{{ env_var('DBT_PROD_USER') }}"
      password: "{{ env_var('DBT_PROD_PASSWORD') }}"
      dbname: blood_bank_prod
      schema: analytics             # Clean schema names in prod
      threads: 8
```

### Switching Environments

```bash
# Run in development (default)
dbt run

# Run in CI
dbt run --target ci

# Run in production
dbt run --target prod

# Check which target you're using
dbt debug --target prod
```

### Environment-Specific Model Logic

```sql
{% if target.name == 'dev' %}
    -- In dev: limit data for fast iteration
    WHERE last_inventory_update_at >= CURRENT_DATE - INTERVAL '30 days'
{% elif target.name == 'ci' %}
    -- In CI: use a sample for speed
    WHERE hospital_id % 10 = 0  -- 10% sample
{% endif %}
-- In prod: no filter → process everything
```

---

## 10. CI/CD Pipeline with GitHub Actions

### The CI/CD Workflow

```
Developer pushes code → GitHub Actions runs:
  1. dbt deps        (install packages)
  2. dbt compile     (check for Jinja errors)
  3. dbt run         (execute models in CI database)
  4. dbt test        (run all data quality tests)
  5. dbt docs generate (build documentation)

If ALL pass → PR can be merged
If ANY fail → PR is blocked
```

### GitHub Actions Configuration

```yaml
# .github/workflows/dbt_ci.yml

name: dbt CI Pipeline

on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'models/**'
      - 'macros/**'
      - 'tests/**'
      - 'seeds/**'
      - 'dbt_project.yml'
      - 'packages.yml'

env:
  DBT_CI_HOST: ${{ secrets.DBT_CI_HOST }}
  DBT_CI_USER: ${{ secrets.DBT_CI_USER }}
  DBT_CI_PASSWORD: ${{ secrets.DBT_CI_PASSWORD }}
  DBT_PROFILES_DIR: ${{ github.workspace }}

jobs:
  dbt-ci:
    name: dbt Build & Test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dbt
        run: |
          pip install dbt-core dbt-postgres

      - name: Install dbt packages
        run: dbt deps

      - name: Validate project
        run: dbt debug --target ci

      - name: Compile models
        run: dbt compile --target ci

      - name: Seed reference data
        run: dbt seed --target ci

      - name: Run models
        run: dbt run --target ci

      - name: Test data quality
        run: dbt test --target ci

      - name: Generate documentation
        run: dbt docs generate --target ci

      - name: Upload docs artifact
        uses: actions/upload-artifact@v4
        with:
          name: dbt-docs
          path: target/
```

### PR-Specific Schemas (Advanced)

```yaml
# In profiles.yml for CI:
ci:
  schema: ci_pr_{{ env_var('GITHUB_PR_NUMBER', 'unknown') }}
```

Each PR gets its own schema (`ci_pr_42`, `ci_pr_43`, etc.), so PRs don't interfere with each other.

### Post-Merge Production Deployment

```yaml
# .github/workflows/dbt_prod.yml

name: dbt Production Deployment

on:
  push:
    branches: [main]
    paths:
      - 'models/**'
      - 'macros/**'

jobs:
  dbt-prod:
    name: Deploy to Production
    runs-on: ubuntu-latest
    environment: production      # Requires manual approval

    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install dbt-core dbt-postgres
      - run: dbt deps
      - run: dbt seed --target prod
      - run: dbt run --target prod
      - run: dbt test --target prod
      - run: dbt docs generate --target prod
```

---

## 11. Orchestration with Apache Airflow

### Why Airflow?

dbt handles the **transformation** logic, but it doesn't:
- Schedule when to run
- Retry on failure
- Send alerts when something breaks
- Coordinate with upstream (data loading) and downstream (dashboard refresh)

**Apache Airflow** handles all of this.

### Architecture: Airflow + dbt

```
┌───────────────────────────────────────────────────────────────┐
│                    APACHE AIRFLOW                              │
│                                                                │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐ │
│  │ Task 1:  │ ──►│ Task 2:  │ ──►│ Task 3:  │ ──►│ Task 4: │ │
│  │ Run      │    │ dbt seed │    │ dbt run  │    │ dbt test│ │
│  │ scraper  │    │          │    │          │    │         │ │
│  └──────────┘    └──────────┘    └──────────┘    └────┬────┘ │
│                                                       │      │
│                                               ┌───────▼────┐ │
│                                               │ Task 5:    │ │
│                                               │ dbt docs   │ │
│                                               │ generate   │ │
│                                               └───────┬────┘ │
│                                                       │      │
│                                               ┌───────▼────┐ │
│                                               │ Task 6:    │ │
│                                               │ Notify     │ │
│                                               │ Slack      │ │
│                                               └────────────┘ │
│                                                               │
│  Schedule: Every day at 6:00 AM IST                          │
│  Retry: 3 attempts with 5-minute delay                       │
│  Alert: Email + Slack on failure                             │
└───────────────────────────────────────────────────────────────┘
```

### Airflow DAG for the Blood Bank Pipeline

```python
# dags/blood_bank_dbt_pipeline.py

"""
Blood Bank Data Pipeline
========================
Orchestrates the complete ELT pipeline:
1. Extract data from eRaktKosh API (Python scraper)
2. Load into PostgreSQL (Bronze layer)
3. Transform with dbt (Silver + Gold layers)
4. Test data quality
5. Generate documentation
6. Send notifications
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

# ============================================================
# DAG Configuration
# ============================================================

default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email': ['data-alerts@eraktkosh.gov.in'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

dag = DAG(
    dag_id='blood_bank_dbt_pipeline',
    default_args=default_args,
    description='Daily blood bank data pipeline: Scrape → Load → Transform → Test',
    schedule_interval='0 6 * * *',          # Every day at 6:00 AM IST
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['blood_bank', 'dbt', 'production'],
    max_active_runs=1,                       # Only one run at a time
)

# ============================================================
# Task Definitions
# ============================================================

# Where your dbt project lives
DBT_PROJECT_DIR = '/opt/airflow/dbt/blood_bank_dbt'

# Task 1: Run the eRaktKosh scraper
extract_and_load = BashOperator(
    task_id='extract_and_load_blood_data',
    bash_command=f"""
        cd {DBT_PROJECT_DIR}/.. &&
        python async_scraper.py &&
        python load_to_postgres.py
    """,
    dag=dag,
)

# Task 2: Check source freshness
check_freshness = BashOperator(
    task_id='check_source_freshness',
    bash_command=f"""
        cd {DBT_PROJECT_DIR} &&
        dbt source freshness --target prod
    """,
    dag=dag,
)

# Task 3: Load seed data
seed_reference_data = BashOperator(
    task_id='seed_reference_data',
    bash_command=f"""
        cd {DBT_PROJECT_DIR} &&
        dbt seed --target prod --full-refresh
    """,
    dag=dag,
)

# Task 4: Run staging models (Silver layer)
run_staging = BashOperator(
    task_id='run_staging_models',
    bash_command=f"""
        cd {DBT_PROJECT_DIR} &&
        dbt run --target prod --select staging.*
    """,
    dag=dag,
)

# Task 5: Test staging models
test_staging = BashOperator(
    task_id='test_staging_models',
    bash_command=f"""
        cd {DBT_PROJECT_DIR} &&
        dbt test --target prod --select staging.*
    """,
    dag=dag,
)

# Task 6: Run mart models (Gold layer)
run_marts = BashOperator(
    task_id='run_mart_models',
    bash_command=f"""
        cd {DBT_PROJECT_DIR} &&
        dbt run --target prod --select marts.*
    """,
    dag=dag,
)

# Task 7: Test mart models
test_marts = BashOperator(
    task_id='test_mart_models',
    bash_command=f"""
        cd {DBT_PROJECT_DIR} &&
        dbt test --target prod --select marts.*
    """,
    dag=dag,
)

# Task 8: Generate documentation
generate_docs = BashOperator(
    task_id='generate_dbt_docs',
    bash_command=f"""
        cd {DBT_PROJECT_DIR} &&
        dbt docs generate --target prod
    """,
    dag=dag,
)

# Task 9: Notify on success
notify_success = SlackWebhookOperator(
    task_id='notify_success',
    slack_webhook_conn_id='slack_data_team',
    message="""
    ✅ *Blood Bank Pipeline Succeeded*
    📅 Date: {{ ds }}
    ⏱️ Duration: {{ task_instance.duration }}s
    🔗 <https://dbt-docs.eraktkosh.gov.in|View Documentation>
    """,
    dag=dag,
)

# ============================================================
# Task Dependencies (The DAG)
# ============================================================

(
    extract_and_load
    >> check_freshness
    >> seed_reference_data
    >> run_staging
    >> test_staging
    >> run_marts
    >> test_marts
    >> generate_docs
    >> notify_success
)
```

### Alternative: Using `cosmos` (Airflow dbt Provider)

The `astronomer-cosmos` package provides native dbt integration:

```python
# Using cosmos — each dbt model becomes an Airflow task
from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig

dbt_tasks = DbtTaskGroup(
    project_config=ProjectConfig("/opt/airflow/dbt/blood_bank_dbt"),
    profile_config=ProfileConfig(
        profile_name="blood_bank_dbt",
        target_name="prod",
    ),
    dag=dag,
)
```

This automatically creates one Airflow task per dbt model, giving you **granular retry** and **parallel execution** at the model level.

### Alternative Orchestrators

| Tool | Best For | Complexity |
|------|----------|-----------|
| **cron** | Simple, single-machine setups | 🟢 Low |
| **Apache Airflow** | Production, complex pipelines | 🔴 High |
| **Dagster** | Modern alternative to Airflow | 🟡 Medium |
| **Prefect** | Python-native orchestration | 🟡 Medium |
| **dbt Cloud** | Managed scheduling (no self-hosting) | 🟢 Low |
| **GitHub Actions** | CI/CD-triggered runs | 🟡 Medium |

---

## 12. Production Best Practices Checklist

### ✅ Code Quality

- [ ] All models follow naming conventions (`stg_`, `int_`, `dim_`, `fct_`, `rpt_`)
- [ ] All staging models use `{{ source() }}` — no hardcoded table names
- [ ] All mart models use `{{ ref() }}` — no hardcoded table names
- [ ] Jinja macros used to eliminate duplicate code (DRY)
- [ ] SQL formatted consistently (CTEs, column naming, indentation)
- [ ] No `SELECT *` in production models (explicit column lists)

### ✅ Testing

- [ ] Every primary key has `unique` + `not_null` tests
- [ ] Every foreign key has a `relationships` test
- [ ] Every enum column has `accepted_values` test
- [ ] Singular tests for critical business rules
- [ ] `dbt build` used in CI/CD (runs + tests in dependency order)

### ✅ Documentation

- [ ] Every model has a description in YAML
- [ ] Every column has a description in YAML
- [ ] Sources have descriptions and freshness configs
- [ ] `dbt docs generate` runs in CI/CD
- [ ] Documentation is hosted and accessible to stakeholders

### ✅ Configuration

- [ ] `profiles.yml` uses `env_var()` for ALL credentials
- [ ] `profiles.yml` is NOT in the Git repository
- [ ] `.gitignore` includes: `target/`, `dbt_packages/`, `logs/`, `.env`
- [ ] Separate environments: dev, ci, prod
- [ ] `generate_schema_name` macro configured for clean prod schemas

### ✅ Performance

- [ ] Staging models materialized as `view`
- [ ] Mart models materialized as `table`
- [ ] Large fact tables (>10M rows) use `incremental` materialization
- [ ] Indexes created via `post_hook` for frequently queried columns
- [ ] `threads` configured based on database capacity

### ✅ Deployment

- [ ] CI/CD pipeline runs on every PR
- [ ] Production deployment requires PR approval
- [ ] Airflow/scheduler configured for regular execution
- [ ] Alerting configured for pipeline failures
- [ ] Source freshness checked before transformation

---

## 13. Practice Exercises

### 🏋️ Exercise 1: Write 3 Custom Macros

Create these macros from scratch (without looking at the examples):

**Macro 1**: `days_since(timestamp_column)` — Returns the number of days between a timestamp and today.

**Macro 2**: `safe_cast_integer(column_name)` — Casts a TEXT column to INTEGER, returning NULL if the value isn't numeric.

**Macro 3**: `standardize_state_name(column_name)` — Trims, title-cases, and handles common state name variations.

<details>
<summary>Click to reveal solutions</summary>

```sql
-- macros/days_since.sql
{% macro days_since(timestamp_column) %}
    CURRENT_DATE - ({{ timestamp_column }})::DATE
{% endmacro %}
```

```sql
-- macros/safe_cast_integer.sql
{% macro safe_cast_integer(column_name) %}
    CASE
        WHEN {{ column_name }} ~ '^[0-9]+$' THEN CAST({{ column_name }} AS INTEGER)
        ELSE NULL
    END
{% endmacro %}
```

```sql
-- macros/standardize_state_name.sql
{% macro standardize_state_name(column_name) %}
    CASE INITCAP(TRIM({{ column_name }}))
        WHEN 'Jammu And Kashmir' THEN 'Jammu & Kashmir'
        WHEN 'Andaman And Nicobar Islands' THEN 'Andaman & Nicobar Islands'
        WHEN 'Dadra And Nagar Haveli And Daman And Diu' THEN 'Dadra & Nagar Haveli and Daman & Diu'
        ELSE INITCAP(TRIM({{ column_name }}))
    END
{% endmacro %}
```

</details>

---

### 🏋️ Exercise 2: Build an Incremental Model

Create `fct_daily_hospital_snapshot.sql` that:

1. Takes a daily snapshot of every hospital's status
2. Uses `incremental` materialization
3. Uses `delete+insert` strategy with `unique_key = ['hospital_id', 'snapshot_date']`
4. Includes an `is_incremental()` filter
5. Adds a `snapshot_date` column

<details>
<summary>Click to reveal solution</summary>

```sql
-- models/marts/analytics/fct_daily_hospital_snapshot.sql

{{
    config(
        materialized='incremental',
        unique_key=['hospital_id', 'snapshot_date'],
        incremental_strategy='delete+insert'
    )
}}

WITH hospitals AS (
    SELECT * FROM {{ ref('dim_hospitals') }}
)

SELECT
    hospital_id,
    hospital_name,
    state_name,
    district_name,
    hospital_type,
    operational_status,
    data_freshness_status,
    has_available_stock,
    days_since_update,
    CURRENT_DATE AS snapshot_date,
    CURRENT_TIMESTAMP AS _inserted_at
FROM hospitals

{% if is_incremental() %}
    WHERE CURRENT_DATE > (SELECT MAX(snapshot_date) FROM {{ this }})
{% endif %}
```

**Test it:**

```bash
# First run (creates table with all data)
dbt run --select fct_daily_hospital_snapshot

# Second run (only inserts today's data, if not already present)
dbt run --select fct_daily_hospital_snapshot

# Force full rebuild
dbt run --select fct_daily_hospital_snapshot --full-refresh
```

</details>

---

### 🏋️ Exercise 3: Set Up dbt Packages

1. Create a `packages.yml` file
2. Add `dbt-labs/dbt_utils` version 1.3.0
3. Run `dbt deps`
4. Refactor `dim_districts.sql` to use `dbt_utils.generate_surrogate_key()` instead of your custom `MD5()` approach
5. Use `dbt_utils.star()` in one model to select all columns except metadata

<details>
<summary>Click to reveal solution</summary>

```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.3.0
```

```bash
dbt deps
```

```sql
-- models/marts/core/dim_districts.sql (refactored)

SELECT
    {{ dbt_utils.generate_surrogate_key(['state_name', 'district_name']) }} AS district_id,
    state_name,
    district_name,
    total_hospitals,
    ...
```

```sql
-- Using star() to exclude metadata columns
SELECT
    {{ dbt_utils.star(
        from=ref('stg_blood_bank__hospitals'),
        except=['_loaded_at', '_source_file', '_transformed_at']
    ) }}
FROM {{ ref('stg_blood_bank__hospitals') }}
```

</details>

---

### 🏋️ Exercise 4: Generate and Explore Documentation

1. Run `dbt docs generate`
2. Run `dbt docs serve`
3. In the DAG viewer, find:
   - Which models have the most dependencies?
   - Which source does every staging model depend on?
   - What's the longest path from source to final report?
4. Take a screenshot of your DAG and save it

<details>
<summary>Click to reveal expected findings</summary>

```bash
dbt docs generate
dbt docs serve
# Opens http://localhost:8080
```

**Expected findings:**

1. **Most dependencies**: `rpt_state_availability_dashboard` (depends on fact + dimension)
2. **Common source**: `raw_blood_bank.blood_inventory_raw` → all staging models
3. **Longest path**: 
   ```
   source → stg_hospitals → dim_hospitals → fct_blood_availability → rpt_state_dashboard
   ```
   (4 hops, 5 nodes)

</details>

---

### 🏋️ Exercise 5: Write a Complete CI/CD Pipeline

Create a GitHub Actions workflow that:

1. Triggers on PRs to `main`
2. Installs Python 3.11 and dbt
3. Runs `dbt deps`
4. Runs `dbt compile` (catch syntax errors)
5. Runs `dbt seed --target ci`
6. Runs `dbt run --target ci`
7. Runs `dbt test --target ci`
8. Uploads the `target/` directory as an artifact

<details>
<summary>Click to reveal solution</summary>

```yaml
# .github/workflows/dbt_ci.yml

name: dbt CI

on:
  pull_request:
    branches: [main]

jobs:
  dbt-ci:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: ci_user
          POSTGRES_PASSWORD: ci_password
          POSTGRES_DB: blood_bank_ci
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      DBT_CI_HOST: localhost
      DBT_CI_USER: ci_user
      DBT_CI_PASSWORD: ci_password

    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dbt
        run: pip install dbt-core dbt-postgres

      - name: Install packages
        run: dbt deps

      - name: Setup CI database schemas
        run: |
          PGPASSWORD=ci_password psql -h localhost -U ci_user -d blood_bank_ci -c "
            CREATE SCHEMA IF NOT EXISTS raw_blood_bank;
            CREATE SCHEMA IF NOT EXISTS staging;
            CREATE SCHEMA IF NOT EXISTS marts;
          "

      - name: Compile (syntax check)
        run: dbt compile --target ci

      - name: Seed reference data
        run: dbt seed --target ci

      - name: Run models
        run: dbt run --target ci

      - name: Test data quality
        run: dbt test --target ci

      - name: Generate docs
        run: dbt docs generate --target ci

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dbt-artifacts
          path: target/
```

</details>

---

### 🏋️ Exercise 6: Design a Full Production Pipeline

On paper or in a markdown file, design the complete data pipeline for the blood bank system:

1. **Schedule**: When should each step run?
2. **Dependencies**: What depends on what?
3. **Error handling**: What happens when each step fails?
4. **Monitoring**: How do you know if the pipeline is healthy?
5. **Alerting**: Who gets notified and how?

<details>
<summary>Click to reveal production design</summary>

```
BLOOD BANK PRODUCTION PIPELINE
================================

Schedule: Daily at 5:30 AM IST (before analysts start at 9 AM)

Step 1: Extract (5:30 AM)
├── Run async_scraper.py
├── Retry: 3 times, 5 min delay
├── On Failure: Alert #data-engineering Slack channel
└── Timeout: 30 minutes

Step 2: Load (6:00 AM)
├── Load CSV into raw_blood_bank.blood_inventory_raw
├── APPEND mode (don't overwrite history)
├── Add _loaded_at and _source_file metadata
├── On Failure: Alert + abort pipeline
└── Timeout: 15 minutes

Step 3: Source Freshness Check (6:15 AM)
├── dbt source freshness --target prod
├── If WARN: Log warning, continue pipeline
├── If ERROR: Alert + abort pipeline
└── Timeout: 5 minutes

Step 4: dbt Seed (6:20 AM)
├── dbt seed --target prod
├── Only runs if seeds/ files changed
└── Timeout: 5 minutes

Step 5: dbt Run - Staging (6:25 AM)
├── dbt run --target prod --select staging.*
├── On Failure: Alert + abort (don't run marts on bad staging)
└── Timeout: 15 minutes

Step 6: dbt Test - Staging (6:40 AM)
├── dbt test --target prod --select staging.*
├── If any ERROR tests fail: Abort pipeline
├── If WARN tests fail: Log warning, continue
└── Timeout: 10 minutes

Step 7: dbt Run - Marts (6:50 AM)
├── dbt run --target prod --select marts.*
├── On Failure: Alert + keep old tables (don't corrupt prod)
└── Timeout: 30 minutes

Step 8: dbt Test - Marts (7:20 AM)
├── dbt test --target prod --select marts.*
├── On Failure: Alert but don't rollback (data is already there)
└── Timeout: 15 minutes

Step 9: Documentation (7:35 AM)
├── dbt docs generate --target prod
├── Deploy to docs.eraktkosh.gov.in
└── Timeout: 5 minutes

Step 10: Notify (7:40 AM)
├── Send Slack summary: models run, tests passed, duration
├── Send email to stakeholders if any WARN tests
└── Update monitoring dashboard

MONITORING:
- Airflow UI: Task status, duration trends, failure rates
- DataDog/Grafana: Row counts, data freshness, query performance
- PagerDuty: On-call for critical failures (page if Step 1-6 fail)

ALERTING MATRIX:
| Failure     | Alert Channel           | Severity |
|-------------|------------------------|----------|
| Scraper     | Slack + PagerDuty      | P1       |
| Staging     | Slack + Email           | P1       |
| Marts       | Slack                   | P2       |
| Tests (ERR) | Slack + Email           | P1       |
| Tests (WARN)| Slack                   | P3       |
| Docs        | None (non-critical)     | P4       |
```

</details>

---

## 14. Senior Engineer Mindset

### What Separates Junior from Senior dbt Engineers

| Junior | Senior |
|--------|--------|
| Writes SQL that works | Writes SQL that's **testable, documented, and maintainable** |
| Builds models | Builds **data platforms** with testing, monitoring, and CI/CD |
| Copies SQL patterns | Creates **macros** that the team reuses |
| Runs `dbt run` manually | Orchestrates with **Airflow** and deploys via **CI/CD** |
| Thinks about today's query | Thinks about **schema evolution**, **incremental processing**, and **scale** |
| Asks "does it return the right data?" | Asks "how do we **know** it returns the right data?" |

### The 10 Principles of Senior dbt Engineering

1. **Test like your career depends on it** — because it does
2. **Document like you'll leave tomorrow** — because you might
3. **DRY your SQL with macros** — copy-paste is a bug factory
4. **Materialize intentionally** — views for staging, tables for marts, incremental for big facts
5. **Separate concerns** — staging cleans, marts apply business logic
6. **Version control everything** — SQL, YAML, configs. If it's not in Git, it doesn't exist
7. **Automate the boring stuff** — CI/CD for testing, Airflow for scheduling
8. **Monitor proactively** — source freshness, row counts, test coverage
9. **Think about the consumer** — your dashboard user doesn't care about your CTE names
10. **Build for change** — schemas evolve, business rules change. Design for it.

---

## 15. Key Takeaways — Full Course Summary

### Module 1: Core Concepts

| Concept | Summary |
|---------|---------|
| ELT > ETL | Load raw data first, transform inside the warehouse |
| Modern Data Stack | Airbyte (EL) + dbt (T) + Looker (Viz) |
| Medallion Architecture | Bronze → Silver → Gold |
| dbt = the "T" in ELT | SQL transformation, testing, documentation |

### Module 2: Installation & Setup

| Concept | Summary |
|---------|---------|
| `dbt-core` + adapter | `pip install dbt-core dbt-postgres` |
| `profiles.yml` | Database connections, lives in `~/.dbt/`, uses `env_var()` |
| `dbt_project.yml` | Project config, materializations, directory paths |
| `dbt debug` | Test your connection |

### Module 3: Sources & Staging

| Concept | Summary |
|---------|---------|
| `sources.yml` | Declare raw tables. Use `{{ source() }}` to reference them |
| Staging models | One per entity. Clean, cast, rename, deduplicate. No business logic |
| Source freshness | `dbt source freshness` checks data staleness |
| Naming | `stg_{source}__{entity}` |

### Module 4: Marts & Testing

| Concept | Summary |
|---------|---------|
| `{{ ref() }}` | Reference other models. Builds the DAG automatically |
| `dim_` tables | Entities (WHO, WHAT, WHERE). One row per entity |
| `fct_` tables | Measurements (WHAT happened). Can be large |
| Generic tests | `unique`, `not_null`, `accepted_values`, `relationships` |
| Singular tests | SQL files that return failing rows |

### Module 5: Pro-Level (This Module)

| Concept | Summary |
|---------|---------|
| Jinja macros | Reusable SQL functions. DRY principle |
| Incremental models | Only process new rows. Essential for large datasets |
| `dbt docs` | Auto-generated documentation with DAG visualization |
| CI/CD | GitHub Actions runs `dbt build` on every PR |
| Airflow | Production scheduling, retry, alerting |
| Environments | dev/ci/prod with separate schemas and credentials |

### The Complete Blood Bank Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  eRaktKosh API                                                        │
│       │                                                               │
│       ▼                                                               │
│  async_scraper.py  ──►  CSV  ──►  PostgreSQL (Bronze)                │
│                                       │                               │
│                                       ▼                               │
│  ┌─────────────────── dbt Pipeline ──────────────────────────────┐   │
│  │                                                                │   │
│  │  sources.yml ──► stg_hospitals ──► dim_hospitals               │   │
│  │                  stg_components    dim_districts               │   │
│  │                  stg_contacts      dim_blood_components        │   │
│  │                       │                                        │   │
│  │                       ▼                                        │   │
│  │                  fct_blood_availability                        │   │
│  │                  fct_daily_snapshot (incremental)              │   │
│  │                       │                                        │   │
│  │                       ▼                                        │   │
│  │                  rpt_state_dashboard                           │   │
│  │                                                                │   │
│  │  Tests: unique, not_null, accepted_values, relationships      │   │
│  │  Macros: clean_text, classify_stock, parse_contact             │   │
│  │  Docs: Auto-generated with DAG visualization                  │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                       │                               │
│                                       ▼                               │
│                              Dashboard (Metabase/Grafana)             │
│                                                                       │
│  Orchestrated by: Apache Airflow (daily at 5:30 AM IST)             │
│  CI/CD: GitHub Actions on every PR                                   │
│  Monitoring: Source freshness + data quality tests                   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🎓 Course Complete!

Congratulations! You've completed the entire dbt Masterclass. You now have the knowledge to:

1. ✅ Design a Medallion Architecture (Bronze → Silver → Gold)
2. ✅ Install and configure dbt with PostgreSQL
3. ✅ Write staging models that clean and standardize raw data
4. ✅ Build dimension and fact tables for analytics
5. ✅ Write comprehensive data quality tests
6. ✅ Create reusable Jinja macros
7. ✅ Build incremental models for massive datasets
8. ✅ Generate documentation with lineage graphs
9. ✅ Deploy dbt in CI/CD pipelines
10. ✅ Orchestrate with Apache Airflow

### What to Do Next

1. **Build it**: Implement the complete blood bank pipeline from scratch
2. **Break it**: Intentionally introduce bugs and practice debugging
3. **Share it**: Push to GitHub, write a README, show it in interviews
4. **Scale it**: Try with BigQuery or Snowflake (just change the adapter!)
5. **Teach it**: The best way to learn is to teach. Explain dbt to a colleague.

---

> **📝 Final Note**: The difference between knowing dbt and *mastering* dbt is the same as the difference between reading about swimming and actually swimming. Build the pipeline. Break it. Fix it. Repeat. That's how you become a senior data engineer.
>
> Good luck! 🚀
