# 📘 Module 4: Gold Marts and Data Testing

> **Masterclass Series**: dbt — From Absolute Beginner to Senior Data Engineer  
> **Module**: 4 of 5  
> **Difficulty**: 🟡 Intermediate → 🔴 Advanced  
> **Estimated Time**: 4–5 hours  
> **Theme**: India Blood Bank Inventory System (eRaktKosh)  
> **Prerequisites**: Modules 1, 2, & 3 completed. Staging models built and running.

---

## 📑 Table of Contents

1. [From Silver to Gold: The Final Transformation](#1-from-silver-to-gold-the-final-transformation)
2. [Dimensional Modeling: Facts vs. Dimensions](#2-dimensional-modeling-facts-vs-dimensions)
3. [The ref() Function and the DAG](#3-the-ref-function-and-the-dag)
4. [Building Dimension Tables (dim_)](#4-building-dimension-tables-dim_)
5. [Building Fact Tables (fct_)](#5-building-fact-tables-fct_)
6. [Building Report Tables (rpt_)](#6-building-report-tables-rpt_)
7. [Intermediate Models (int_)](#7-intermediate-models-int_)
8. [Deep Dive: dbt Testing](#8-deep-dive-dbt-testing)
9. [Generic Tests (Built-in)](#9-generic-tests-built-in)
10. [Custom Singular Tests](#10-custom-singular-tests)
11. [Custom Generic Tests (Macros)](#11-custom-generic-tests-macros)
12. [Running Tests and Interpreting Results](#12-running-tests-and-interpreting-results)
13. [Practice Exercises](#13-practice-exercises)
14. [Key Takeaways](#14-key-takeaways)

---

## 1. From Silver to Gold: The Final Transformation

The Gold layer is where data becomes **business-valuable**. This is what stakeholders actually use:

```
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│     BRONZE        │     │     SILVER         │     │      GOLD         │
│  (Raw Sources)    │ ──► │  (Staging Models)  │ ──► │  (Mart Models)    │
│                   │     │                    │     │                   │
│  raw_blood_bank.  │     │  stg_blood_bank__  │     │  dim_hospitals    │
│  blood_inventory  │     │  hospitals         │     │  dim_districts    │
│                   │     │  stg_blood_bank__  │     │  fct_blood_avail  │
│                   │     │  components        │     │  rpt_state_dash   │
│                   │     │  stg_blood_bank__  │     │                   │
│                   │     │  contacts          │     │                   │
└───────────────────┘     └───────────────────┘     └───────────────────┘

   source() reads            ref() reads              Dashboard reads
   from here                 from here                from here
```

### What Changes in the Gold Layer?

| Silver (Staging) | Gold (Marts) |
|-----------------|-------------|
| One model per source table | Models can join MULTIPLE staging models |
| No business logic | Full business logic (KPIs, classifications, aggregations) |
| `{{ source() }}` references | `{{ ref() }}` references |
| Materialized as **views** | Materialized as **tables** (performance!) |
| No aggregations | SUM, COUNT, AVG, window functions |
| Technical column names | Business-friendly column names |

---

## 2. Dimensional Modeling: Facts vs. Dimensions

### The Star Schema

The Gold layer follows the **Star Schema** pattern — the most widely used pattern in analytics engineering:

```
                 ┌──────────────┐
                 │ dim_hospitals │ ← WHO
                 └──────┬───────┘
                        │
    ┌──────────────┐    │    ┌───────────────────┐
    │dim_blood_    │    │    │ dim_districts      │ ← WHERE
    │components    │────┼────│                    │
    └──────────────┘    │    └───────────────────┘
         ↑ WHAT         │
                        │
                 ┌──────┴───────┐
                 │    fct_blood │ ← MEASUREMENTS
                 │  availability│
                 └──────────────┘
                        │
                 ┌──────┴───────┐
                 │  dim_dates   │ ← WHEN
                 └──────────────┘
```

### Dimension Tables (`dim_`)

**Dimensions describe entities** — the WHO, WHAT, WHERE, WHEN of your data.

| Dimension | Describes | Example Columns |
|-----------|----------|----------------|
| `dim_hospitals` | WHO provides blood | hospital_id, name, type, is_offline |
| `dim_districts` | WHERE blood is available | district_id, district_name, state_name |
| `dim_blood_components` | WHAT blood products exist | component_id, component_name, shelf_life |
| `dim_dates` | WHEN data was collected | date_key, day_of_week, is_weekend |

**Characteristics of dimension tables:**
- ✅ One row per entity (hospital, district, blood group)
- ✅ Contain descriptive attributes (names, types, statuses)
- ✅ Change slowly (a hospital's name rarely changes)
- ✅ Relatively small (thousands, not millions of rows)
- ✅ Wide tables (many columns)

### Fact Tables (`fct_`)

**Facts record measurements and events** — the actual business data.

| Fact | Measures | Grain |
|------|----------|-------|
| `fct_blood_availability` | Units available per hospital-component | One row per hospital × component |
| `fct_daily_stock_summary` | Daily aggregated stock levels | One row per state × day |
| `fct_inventory_changes` | Stock level changes over time | One row per change event |

**Characteristics of fact tables:**
- ✅ Contain numeric measurements (quantities, counts, amounts)
- ✅ Reference dimension tables via foreign keys
- ✅ Append-only (new records are added, old ones aren't changed)
- ✅ Can be very large (millions/billions of rows)
- ✅ Narrow tables (mostly keys + measures)

---

## 3. The ref() Function and the DAG

### What is ref()?

The `ref()` function is how Gold models reference Silver models:

```sql
-- In a mart model:
SELECT * FROM {{ ref('stg_blood_bank__hospitals') }}

-- Compiles to:
SELECT * FROM "blood_bank_db"."staging"."stg_blood_bank__hospitals"
```

### Why ref() Instead of Hardcoding?

```sql
-- ❌ Hardcoded (BAD)
SELECT * FROM staging.stg_blood_bank__hospitals

-- ✅ ref() (GOOD)
SELECT * FROM {{ ref('stg_blood_bank__hospitals') }}
```

| Benefit | Explanation |
|---------|-------------|
| **Automatic DAG building** | dbt sees the `ref()` and knows model B depends on model A |
| **Environment awareness** | In dev, it resolves to `dev_staging.stg_...`. In prod, to `staging.stg_...` |
| **Refactoring safety** | Rename a model once, all `ref()` calls update automatically |
| **Dependency ordering** | dbt runs models in the correct order based on `ref()` chains |
| **Cross-project refs** | Can reference models from other dbt projects |

### How dbt Builds the DAG

When you run `dbt run`, dbt:

1. **Parses** all `.sql` files looking for `{{ source() }}` and `{{ ref() }}` calls
2. **Builds a graph** (DAG) of all dependencies
3. **Topologically sorts** the graph to determine execution order
4. **Executes** models in order, respecting parallelism (`threads`)

```
Parsing: stg_blood_bank__hospitals.sql
  → Found: source('raw_blood_bank', 'blood_inventory_raw')
  → Dependency: raw_blood_bank.blood_inventory_raw → stg_blood_bank__hospitals

Parsing: dim_hospitals.sql
  → Found: ref('stg_blood_bank__hospitals')
  → Dependency: stg_blood_bank__hospitals → dim_hospitals

Parsing: fct_blood_availability.sql
  → Found: ref('stg_blood_bank__hospitals')
  → Found: ref('stg_blood_bank__components')
  → Dependencies: stg_blood_bank__hospitals → fct_blood_availability
                   stg_blood_bank__components → fct_blood_availability

Execution Order:
  1. stg_blood_bank__hospitals (no dependencies except source)
  2. stg_blood_bank__components (no dependencies except source)
  3. stg_blood_bank__contacts (no dependencies except source)
  4. dim_hospitals (depends on #1)           ← Can run in parallel with #5
  5. fct_blood_availability (depends on #1 + #2)
  6. rpt_state_availability (depends on #4 + #5)
```

### Visualizing the DAG

```bash
# Generate the documentation (including DAG visualization)
dbt docs generate
dbt docs serve
# Opens a browser with an interactive DAG viewer
```

---

## 4. Building Dimension Tables (dim_)

### Directory Structure

```
models/
└── marts/
    ├── core/
    │   ├── _core__models.yml
    │   ├── dim_hospitals.sql
    │   ├── dim_districts.sql
    │   └── dim_blood_components.sql
    │
    └── analytics/
        ├── _analytics__models.yml
        ├── fct_blood_availability.sql
        ├── fct_daily_stock_summary.sql
        └── rpt_state_availability_dashboard.sql
```

### dim_hospitals.sql — The Hospital Dimension

```sql
-- models/marts/core/dim_hospitals.sql

-- ============================================================
-- DIMENSION: Hospitals
-- Grain: One row per unique hospital
-- Source: Silver staging models
--
-- This dimension enriches the staging hospital data with:
--   - Contact information (from stg_contacts)
--   - Data freshness classification
--   - Operational status flags
-- ============================================================

WITH hospitals AS (

    SELECT * FROM {{ ref('stg_blood_bank__hospitals') }}

),

contacts AS (

    SELECT * FROM {{ ref('stg_blood_bank__contacts') }}

),

components AS (

    SELECT * FROM {{ ref('stg_blood_bank__components') }}

),

-- Join hospitals with contacts and component status
enriched AS (

    SELECT
        -- ========================================
        -- Primary Key
        -- ========================================
        h.hospital_id,

        -- ========================================
        -- Hospital Attributes
        -- ========================================
        h.hospital_name,
        h.hospital_type,
        h.facility_type,
        h.hospital_address,
        h.is_offline,

        -- ========================================
        -- Geographic Attributes
        -- ========================================
        h.state_name,
        h.district_name,

        -- ========================================
        -- Contact Information (from stg_contacts)
        -- ========================================
        c.phone_number,
        c.fax_number,
        c.email_address,

        -- ========================================
        -- Availability Status (from stg_components)
        -- ========================================
        COALESCE(comp.has_available_stock, FALSE) AS has_available_stock,

        -- ========================================
        -- Data Freshness (Business Logic!)
        -- ========================================
        h.last_inventory_update_at,
        
        CURRENT_DATE - h.last_inventory_update_at::DATE AS days_since_update,
        
        CASE
            WHEN h.last_inventory_update_at IS NULL THEN 'UNKNOWN'
            WHEN CURRENT_DATE - h.last_inventory_update_at::DATE <= 1 THEN 'FRESH'
            WHEN CURRENT_DATE - h.last_inventory_update_at::DATE <= 3 THEN 'RECENT'
            WHEN CURRENT_DATE - h.last_inventory_update_at::DATE <= {{ var('stale_data_threshold_days', 7) }} THEN 'AGING'
            ELSE 'STALE'
        END AS data_freshness_status,

        -- ========================================
        -- Operational Classification
        -- ========================================
        CASE
            WHEN h.is_offline = TRUE THEN 'OFFLINE'
            WHEN h.last_inventory_update_at IS NULL THEN 'INACTIVE'
            WHEN CURRENT_DATE - h.last_inventory_update_at::DATE > 30 THEN 'DORMANT'
            ELSE 'ACTIVE'
        END AS operational_status,

        -- ========================================
        -- Metadata
        -- ========================================
        h._loaded_at,
        CURRENT_TIMESTAMP AS _transformed_at

    FROM hospitals h
    LEFT JOIN contacts c
        ON h.hospital_id = c.hospital_id
    LEFT JOIN components comp
        ON h.hospital_id = comp.hospital_id

)

SELECT * FROM enriched
```

### Key Techniques Used

#### Using `{{ var() }}` for Configurable Thresholds

```sql
-- This reads from dbt_project.yml:
-- vars:
--   stale_data_threshold_days: 7

WHEN CURRENT_DATE - h.last_inventory_update_at::DATE <= {{ var('stale_data_threshold_days', 7) }} THEN 'AGING'

-- The 7 is a default value if the variable isn't set
```

#### LEFT JOIN (Not INNER JOIN)

```sql
FROM hospitals h
LEFT JOIN contacts c ON h.hospital_id = c.hospital_id
```

**Why LEFT JOIN?** We want ALL hospitals in the dimension, even if they don't have contact information. An INNER JOIN would silently drop hospitals without contacts.

> **🔑 Rule of Thumb**: In dimension tables, always use **LEFT JOIN** unless you have a very good reason to exclude records.

---

### dim_districts.sql — The Geography Dimension

```sql
-- models/marts/core/dim_districts.sql

-- ============================================================
-- DIMENSION: Districts (Geography)
-- Grain: One row per unique state-district combination
-- Source: stg_blood_bank__hospitals
--
-- This dimension provides geographic context for analysis:
--   - State and district names
--   - Hospital counts per district
--   - Hospital type distribution
-- ============================================================

WITH hospitals AS (

    SELECT * FROM {{ ref('stg_blood_bank__hospitals') }}

),

district_summary AS (

    SELECT
        state_name,
        district_name,
        
        -- Hospital counts
        COUNT(DISTINCT hospital_id) AS total_hospitals,
        COUNT(DISTINCT hospital_id) FILTER (
            WHERE hospital_type = 'government'
        ) AS government_hospital_count,
        COUNT(DISTINCT hospital_id) FILTER (
            WHERE hospital_type = 'private'
        ) AS private_hospital_count,
        COUNT(DISTINCT hospital_id) FILTER (
            WHERE hospital_type = 'charitable'
        ) AS charitable_hospital_count,

        -- Facility type counts
        COUNT(DISTINCT hospital_id) FILTER (
            WHERE facility_type = 'blood_bank'
        ) AS blood_bank_count,
        COUNT(DISTINCT hospital_id) FILTER (
            WHERE facility_type = 'blood_storage_unit'
        ) AS blood_storage_unit_count,

        -- Data quality metrics
        COUNT(DISTINCT hospital_id) FILTER (
            WHERE is_offline = TRUE
        ) AS offline_hospital_count,

        MIN(last_inventory_update_at) AS oldest_update,
        MAX(last_inventory_update_at) AS newest_update

    FROM hospitals
    GROUP BY state_name, district_name

)

SELECT
    -- Surrogate key (deterministic hash)
    MD5(state_name || '||' || district_name) AS district_id,
    
    state_name,
    district_name,
    
    total_hospitals,
    government_hospital_count,
    private_hospital_count,
    charitable_hospital_count,
    blood_bank_count,
    blood_storage_unit_count,
    offline_hospital_count,
    
    -- Calculated metrics
    ROUND(
        government_hospital_count::NUMERIC / NULLIF(total_hospitals, 0) * 100, 1
    ) AS pct_government,
    
    oldest_update,
    newest_update,
    
    -- Coverage classification
    CASE
        WHEN total_hospitals >= 10 THEN 'HIGH_COVERAGE'
        WHEN total_hospitals >= 5  THEN 'MEDIUM_COVERAGE'
        WHEN total_hospitals >= 1  THEN 'LOW_COVERAGE'
        ELSE 'NO_COVERAGE'
    END AS coverage_level,
    
    CURRENT_TIMESTAMP AS _transformed_at

FROM district_summary
```

### dim_blood_components.sql — Using Seeds

```sql
-- models/marts/core/dim_blood_components.sql

-- ============================================================
-- DIMENSION: Blood Components
-- Grain: One row per unique blood component type
-- Source: ref_blood_components seed + manual enrichment
-- ============================================================

WITH seed_data AS (

    SELECT * FROM {{ ref('ref_blood_components') }}  -- This is a SEED (CSV file)

)

SELECT
    component_code AS component_id,
    component_name,
    shelf_life_days,
    storage_temp_celsius,
    is_critical,
    
    -- Derived attributes
    CASE
        WHEN shelf_life_days <= 5  THEN 'VERY_SHORT'
        WHEN shelf_life_days <= 42 THEN 'SHORT'
        ELSE 'LONG'
    END AS shelf_life_category,
    
    CASE
        WHEN storage_temp_celsius < 0  THEN 'FROZEN'
        WHEN storage_temp_celsius < 10 THEN 'REFRIGERATED'
        ELSE 'ROOM_TEMPERATURE'
    END AS storage_category,
    
    CURRENT_TIMESTAMP AS _transformed_at

FROM seed_data
```

> **💡 Note**: `{{ ref('ref_blood_components') }}` references a **seed** table (from the CSV in `seeds/ref_blood_components.csv`). The `ref()` function works for both models AND seeds!

---

## 5. Building Fact Tables (fct_)

### fct_blood_availability.sql — The Core Fact

```sql
-- models/marts/analytics/fct_blood_availability.sql

-- ============================================================
-- FACT TABLE: Blood Availability
-- Grain: One row per hospital
-- Source: Multiple staging models
--
-- This is the primary fact table that powers the blood bank
-- dashboard. It combines hospital info with availability data
-- and applies business classifications.
-- ============================================================

{{
    config(
        materialized='table',
        tags=['analytics', 'gold', 'critical'],
        description='Core fact table tracking blood availability per hospital'
    )
}}

WITH hospitals AS (

    SELECT * FROM {{ ref('stg_blood_bank__hospitals') }}

),

components AS (

    SELECT * FROM {{ ref('stg_blood_bank__components') }}

),

contacts AS (

    SELECT * FROM {{ ref('stg_blood_bank__contacts') }}

),

-- Join all staging models
combined AS (

    SELECT
        -- ========================================
        -- Keys
        -- ========================================
        h.hospital_id,
        
        -- ========================================
        -- Hospital Context (denormalized for query performance)
        -- ========================================
        h.hospital_name,
        h.state_name,
        h.district_name,
        h.hospital_type,
        h.facility_type,
        
        -- ========================================
        -- Availability Measures
        -- ========================================
        COALESCE(c.has_available_stock, FALSE) AS has_available_stock,
        c.available_qty_raw,
        c.not_available_qty_raw,

        -- ========================================
        -- Contact for Emergency Outreach
        -- ========================================
        ct.phone_number,
        ct.email_address,

        -- ========================================
        -- Temporal Context
        -- ========================================
        h.last_inventory_update_at,
        CURRENT_DATE - h.last_inventory_update_at::DATE AS days_since_update,

        -- ========================================
        -- Business Classifications
        -- ========================================
        
        -- Data freshness flag
        CASE
            WHEN CURRENT_DATE - h.last_inventory_update_at::DATE > {{ var('stale_data_threshold_days', 7) }}
            THEN TRUE
            ELSE FALSE
        END AS is_data_stale,

        -- Availability status
        CASE
            WHEN c.has_available_stock = TRUE
                AND CURRENT_DATE - h.last_inventory_update_at::DATE <= {{ var('stale_data_threshold_days', 7) }}
            THEN 'AVAILABLE'
            
            WHEN c.has_available_stock = TRUE
                AND CURRENT_DATE - h.last_inventory_update_at::DATE > {{ var('stale_data_threshold_days', 7) }}
            THEN 'POSSIBLY_AVAILABLE'    -- Has stock but data is old
            
            WHEN c.has_available_stock = FALSE
                AND CURRENT_DATE - h.last_inventory_update_at::DATE <= {{ var('stale_data_threshold_days', 7) }}
            THEN 'OUT_OF_STOCK'          -- Confirmed no stock (recent data)
            
            ELSE 'UNKNOWN'               -- No stock AND stale data
        END AS availability_status,

        -- Urgency level
        CASE
            WHEN c.has_available_stock = FALSE 
                AND h.facility_type = 'blood_bank'
            THEN 'HIGH'                   -- Blood bank with no stock = urgent
            
            WHEN c.has_available_stock = FALSE 
                AND h.facility_type = 'blood_storage_unit'
            THEN 'MEDIUM'                 -- BSU with no stock = concerning
            
            WHEN CURRENT_DATE - h.last_inventory_update_at::DATE > 14
            THEN 'MEDIUM'                 -- Very stale data = concerning
            
            ELSE 'LOW'
        END AS urgency_level,

        -- ========================================
        -- Metadata
        -- ========================================
        CURRENT_TIMESTAMP AS _transformed_at

    FROM hospitals h
    LEFT JOIN components c
        ON h.hospital_id = c.hospital_id
    LEFT JOIN contacts ct
        ON h.hospital_id = ct.hospital_id

)

SELECT * FROM combined
```

### Understanding the config() Block

```sql
{{
    config(
        materialized='table',           -- Create a physical table (not a view)
        tags=['analytics', 'gold'],     -- Tags for selective execution
        description='Core fact table'   -- Model description
    )
}}
```

You can override `dbt_project.yml` settings at the model level using `config()`. This is useful when one model needs different settings than the rest of its folder.

| Config Option | Purpose |
|--------------|---------|
| `materialized` | Override the default materialization |
| `tags` | Labels for selective execution (`dbt run --select tag:critical`) |
| `schema` | Override the target schema |
| `alias` | Override the table name |
| `enabled` | Set to `false` to disable a model |
| `pre_hook` / `post_hook` | SQL to run before/after the model |

---

## 6. Building Report Tables (rpt_)

Report tables are **pre-aggregated** for dashboard performance:

```sql
-- models/marts/analytics/rpt_state_availability_dashboard.sql

-- ============================================================
-- REPORT TABLE: State-Level Availability Dashboard
-- Grain: One row per state
-- Purpose: Powers the main dashboard state-level overview
-- ============================================================

{{
    config(
        materialized='table',
        tags=['dashboard', 'report']
    )
}}

WITH availability AS (

    SELECT * FROM {{ ref('fct_blood_availability') }}

),

districts AS (

    SELECT * FROM {{ ref('dim_districts') }}

)

SELECT
    a.state_name,

    -- ========================================
    -- Hospital Counts
    -- ========================================
    COUNT(DISTINCT a.hospital_id) AS total_hospitals,
    
    COUNT(DISTINCT a.hospital_id) FILTER (
        WHERE a.has_available_stock = TRUE
    ) AS hospitals_with_stock,
    
    COUNT(DISTINCT a.hospital_id) FILTER (
        WHERE a.has_available_stock = FALSE
    ) AS hospitals_without_stock,

    -- ========================================
    -- Availability Percentages
    -- ========================================
    ROUND(
        COUNT(DISTINCT a.hospital_id) FILTER (WHERE a.has_available_stock = TRUE)::NUMERIC
        / NULLIF(COUNT(DISTINCT a.hospital_id), 0)::NUMERIC * 100,
        1
    ) AS pct_hospitals_with_stock,

    -- ========================================
    -- Data Quality Metrics
    -- ========================================
    COUNT(DISTINCT a.hospital_id) FILTER (
        WHERE a.is_data_stale = TRUE
    ) AS stale_data_hospitals,

    ROUND(
        COUNT(DISTINCT a.hospital_id) FILTER (WHERE a.is_data_stale = TRUE)::NUMERIC
        / NULLIF(COUNT(DISTINCT a.hospital_id), 0)::NUMERIC * 100,
        1
    ) AS pct_stale_data,

    -- ========================================
    -- Urgency Distribution
    -- ========================================
    COUNT(DISTINCT a.hospital_id) FILTER (
        WHERE a.urgency_level = 'HIGH'
    ) AS high_urgency_count,

    COUNT(DISTINCT a.hospital_id) FILTER (
        WHERE a.urgency_level = 'MEDIUM'
    ) AS medium_urgency_count,

    -- ========================================
    -- Geographic Coverage
    -- ========================================
    COUNT(DISTINCT a.district_name) AS districts_covered,

    -- ========================================
    -- Temporal Metrics
    -- ========================================
    MIN(a.last_inventory_update_at) AS oldest_data_point,
    MAX(a.last_inventory_update_at) AS newest_data_point,
    ROUND(AVG(a.days_since_update), 1) AS avg_days_since_update,

    -- ========================================
    -- Metadata
    -- ========================================
    CURRENT_TIMESTAMP AS _report_generated_at

FROM availability a
GROUP BY a.state_name
ORDER BY total_hospitals DESC
```

---

## 7. Intermediate Models (int_)

Sometimes the jump from Silver to Gold requires complex transformations. **Intermediate models** bridge this gap:

```sql
-- models/intermediate/int_blood_bank__parsed_availability.sql

-- ============================================================
-- INTERMEDIATE: Parse available_WithQty into structured rows
-- 
-- This model transforms:
--   "O+Ve : 16, A+Ve : 13, B+Ve : 17"
-- Into separate rows:
--   hospital_id | blood_group | available_units
--   123         | O+          | 16
--   123         | A+          | 13
--   123         | B+          | 17
-- ============================================================

{{
    config(
        materialized='ephemeral'  -- Won't create a table, just a CTE
    )
}}

WITH components AS (

    SELECT * FROM {{ ref('stg_blood_bank__components') }}

),

-- Split the available_qty_raw string into individual entries
-- using regexp_split_to_table

split_available AS (

    SELECT
        hospital_id,
        hospital_name,
        state_name,
        district_name,
        TRIM(unnest(string_to_array(available_qty_raw, ','))) AS blood_group_entry
    FROM components
    WHERE available_qty_raw != ''
      AND available_qty_raw IS NOT NULL

),

-- Parse each entry into blood_group and quantity
parsed AS (

    SELECT
        hospital_id,
        hospital_name,
        state_name,
        district_name,
        -- Extract blood group: "O+Ve : 16" → "O+Ve"
        TRIM(SPLIT_PART(blood_group_entry, ':', 1)) AS blood_group_raw,
        -- Extract quantity: "O+Ve : 16" → 16
        TRIM(SPLIT_PART(blood_group_entry, ':', 2))::INTEGER AS available_units
    FROM split_available
    WHERE blood_group_entry LIKE '%:%'
      AND TRIM(SPLIT_PART(blood_group_entry, ':', 2)) ~ '^[0-9]+$'

),

-- Standardize blood group names
standardized AS (

    SELECT
        hospital_id,
        hospital_name,
        state_name,
        district_name,
        -- Standardize: "O+Ve" → "O+", "O -ve" → "O-"
        CASE
            WHEN blood_group_raw ILIKE '%Oh+%'  THEN 'Oh+'
            WHEN blood_group_raw ILIKE '%Oh-%'  THEN 'Oh-'
            WHEN blood_group_raw ILIKE '%AB+%'  THEN 'AB+'
            WHEN blood_group_raw ILIKE '%AB-%'  THEN 'AB-'
            WHEN blood_group_raw ILIKE '%A+%'   THEN 'A+'
            WHEN blood_group_raw ILIKE '%A-%'   THEN 'A-'
            WHEN blood_group_raw ILIKE '%B+%'   THEN 'B+'
            WHEN blood_group_raw ILIKE '%B-%'   THEN 'B-'
            WHEN blood_group_raw ILIKE '%O+%'   THEN 'O+'
            WHEN blood_group_raw ILIKE '%O-%'   THEN 'O-'
            ELSE blood_group_raw
        END AS blood_group,
        available_units
    FROM parsed
    WHERE available_units > 0  -- Only rows with actual stock

)

SELECT * FROM standardized
```

### Why Ephemeral?

```yaml
config(materialized='ephemeral')
```

Ephemeral models are **not** created as tables or views. Instead, dbt inlines them as CTEs in the downstream model that references them. This is ideal for intermediate transformations that:

- Don't need to be queried directly
- Are only used by one or two downstream models
- Add complexity that should be encapsulated

```sql
-- When fct_blood_detail.sql does:
SELECT * FROM {{ ref('int_blood_bank__parsed_availability') }}

-- dbt compiles it as:
WITH int_blood_bank__parsed_availability AS (
    -- The entire SELECT from the intermediate model is inlined here
    SELECT ...
)
SELECT * FROM int_blood_bank__parsed_availability
```

---

## 8. Deep Dive: dbt Testing

### Why Testing is Non-Negotiable

Without tests, you're **guessing** that your data is correct. In a blood bank system:

| Failure | Impact |
|---------|--------|
| Duplicate hospital_ids | Dashboard double-counts stock → patient thinks blood is available when it's not |
| NULL blood quantities | SUM ignores NULLs → understated stock levels |
| Negative quantities | Impossible values → data corruption from upstream |
| Unexpected hospital_types | Dashboard filters break → entire states disappear |
| Stale data not flagged | Patients rely on week-old inventory data |

> **🔑 The Testing Pyramid**: Test at every layer. Sources → Staging → Marts.

### Types of dbt Tests

```
┌─────────────────────────────────────────────┐
│              dbt Testing Types              │
│                                             │
│  1. GENERIC TESTS (Built-in)               │
│     - unique                                │
│     - not_null                              │
│     - accepted_values                       │
│     - relationships                         │
│                                             │
│  2. CUSTOM SINGULAR TESTS                   │
│     - SQL files in tests/ directory         │
│     - Return rows that FAIL the test        │
│                                             │
│  3. CUSTOM GENERIC TESTS (Macros)           │
│     - Reusable test templates               │
│     - Parameterized with Jinja              │
│                                             │
│  4. PACKAGE TESTS (dbt-utils, etc.)         │
│     - Community-maintained test libraries   │
└─────────────────────────────────────────────┘
```

---

## 9. Generic Tests (Built-in)

Generic tests are defined in your YAML files. They're the **first line of defense**.

### Test 1: `unique`

Asserts that a column has no duplicate values.

```yaml
columns:
  - name: hospital_id
    tests:
      - unique
```

**What dbt runs:**

```sql
SELECT hospital_id
FROM staging.stg_blood_bank__hospitals
GROUP BY hospital_id
HAVING COUNT(*) > 1
-- If any rows return, the test FAILS
```

### Test 2: `not_null`

Asserts that a column has no NULL values.

```yaml
columns:
  - name: hospital_name
    tests:
      - not_null
```

**What dbt runs:**

```sql
SELECT hospital_name
FROM staging.stg_blood_bank__hospitals
WHERE hospital_name IS NULL
-- If any rows return, the test FAILS
```

### Test 3: `accepted_values`

Asserts that a column only contains expected values.

```yaml
columns:
  - name: hospital_type
    tests:
      - accepted_values:
          values: ['government', 'private', 'charitable', 'unknown']
```

**What dbt runs:**

```sql
SELECT hospital_type
FROM staging.stg_blood_bank__hospitals
WHERE hospital_type NOT IN ('government', 'private', 'charitable', 'unknown')
-- If any rows return, the test FAILS
```

### Test 4: `relationships`

Asserts that every value in a column exists in another model's column (referential integrity).

```yaml
# In fct_blood_availability's YAML:
columns:
  - name: hospital_id
    tests:
      - relationships:
          to: ref('dim_hospitals')
          field: hospital_id
```

**What dbt runs:**

```sql
SELECT fct.hospital_id
FROM marts.fct_blood_availability fct
LEFT JOIN marts.dim_hospitals dim
    ON fct.hospital_id = dim.hospital_id
WHERE dim.hospital_id IS NULL
-- If any rows return, the test FAILS (orphaned foreign keys!)
```

### Complete Test Configuration Example

```yaml
# models/marts/analytics/_analytics__models.yml

version: 2

models:
  - name: fct_blood_availability
    description: "Core fact table: blood availability per hospital"
    
    columns:
      - name: hospital_id
        description: "FK to dim_hospitals"
        tests:
          - unique
          - not_null
          - relationships:
              to: ref('dim_hospitals')
              field: hospital_id

      - name: availability_status
        description: "Business classification of availability"
        tests:
          - not_null
          - accepted_values:
              values: ['AVAILABLE', 'POSSIBLY_AVAILABLE', 'OUT_OF_STOCK', 'UNKNOWN']

      - name: urgency_level
        description: "Urgency classification for alerting"
        tests:
          - not_null
          - accepted_values:
              values: ['HIGH', 'MEDIUM', 'LOW']

      - name: days_since_update
        description: "Days since the hospital last updated inventory"
        tests:
          - not_null

  - name: rpt_state_availability_dashboard
    description: "Pre-aggregated state-level availability report"
    
    columns:
      - name: state_name
        tests:
          - unique
          - not_null

      - name: total_hospitals
        tests:
          - not_null

      - name: pct_hospitals_with_stock
        description: "Percentage should be between 0 and 100"
        tests:
          - not_null
```

### Test Severity Levels

```yaml
columns:
  - name: hospital_id
    tests:
      - unique:
          config:
            severity: error      # FAIL the entire pipeline (default)
      - not_null:
          config:
            severity: warn       # Log a warning but don't fail
```

| Severity | Behavior |
|----------|----------|
| `error` (default) | Test failure = pipeline stops. Use for critical data quality issues. |
| `warn` | Test failure = warning logged. Pipeline continues. Use for non-critical issues. |

### Conditional Tests with `where`

```yaml
columns:
  - name: phone_number
    tests:
      - not_null:
          config:
            where: "hospital_type = 'government'"  # Only test govt hospitals
```

---

## 10. Custom Singular Tests

Singular tests are **SQL files** in the `tests/` directory. They assert complex business rules that can't be expressed with generic tests.

**The rule**: A singular test **FAILS if it returns any rows**. Write a query that returns the "bad" data.

### Test: No Negative Blood Units

```sql
-- tests/assert_no_negative_available_units.sql

-- This test ensures no hospital has negative blood units.
-- If any rows return, the test FAILS.

SELECT
    hospital_id,
    hospital_name,
    state_name,
    available_qty_raw
FROM {{ ref('stg_blood_bank__components') }}
WHERE available_qty_raw LIKE '%-%'  -- Contains negative numbers
  AND available_qty_raw NOT LIKE '%Ve%'  -- Not a blood group name
```

### Test: No Orphaned Hospital IDs in Facts

```sql
-- tests/assert_fact_hospital_ids_exist_in_dim.sql

-- Every hospital_id in the fact table must exist in dim_hospitals.
-- Orphaned IDs indicate a join error or data loss.

SELECT
    f.hospital_id,
    f.hospital_name,
    f.state_name
FROM {{ ref('fct_blood_availability') }} f
LEFT JOIN {{ ref('dim_hospitals') }} d
    ON f.hospital_id = d.hospital_id
WHERE d.hospital_id IS NULL
```

### Test: All States Should Have At Least One Hospital

```sql
-- tests/assert_all_states_have_hospitals.sql

-- We expect at least 28 states + 8 UTs = 36 state/UT entries.
-- If a state has zero hospitals, something is wrong with the data load.

WITH state_counts AS (
    SELECT
        state_name,
        COUNT(DISTINCT hospital_id) AS hospital_count
    FROM {{ ref('dim_hospitals') }}
    GROUP BY state_name
)

SELECT *
FROM state_counts
WHERE hospital_count = 0
```

### Test: Dashboard Report Should Have Recent Data

```sql
-- tests/assert_dashboard_data_is_recent.sql

-- The dashboard report should have been generated recently.
-- If the newest data point is more than 48 hours old, something is wrong.

SELECT
    state_name,
    newest_data_point,
    CURRENT_TIMESTAMP - newest_data_point AS data_age
FROM {{ ref('rpt_state_availability_dashboard') }}
WHERE newest_data_point < CURRENT_TIMESTAMP - INTERVAL '48 hours'
```

### Test: Stale Data Percentage Should Not Exceed 50%

```sql
-- tests/assert_stale_data_under_threshold.sql

-- If more than 50% of hospitals in any state have stale data,
-- it indicates a systematic data collection problem.

SELECT
    state_name,
    pct_stale_data,
    total_hospitals
FROM {{ ref('rpt_state_availability_dashboard') }}
WHERE pct_stale_data > 50
  AND total_hospitals >= 10  -- Only flag states with meaningful sample size
```

---

## 11. Custom Generic Tests (Macros)

Custom generic tests are **reusable test templates** written as macros. They can be applied to any model/column via YAML.

### Example: `test_is_positive`

```sql
-- macros/tests/test_is_positive.sql

{% test is_positive(model, column_name) %}

SELECT
    {{ column_name }}
FROM {{ model }}
WHERE {{ column_name }} < 0

{% endtest %}
```

**Usage in YAML:**

```yaml
columns:
  - name: total_hospitals
    tests:
      - is_positive  # Uses our custom generic test!
```

### Example: `test_is_in_range`

```sql
-- macros/tests/test_is_in_range.sql

{% test is_in_range(model, column_name, min_val, max_val) %}

SELECT
    {{ column_name }}
FROM {{ model }}
WHERE {{ column_name }} < {{ min_val }}
   OR {{ column_name }} > {{ max_val }}

{% endtest %}
```

**Usage:**

```yaml
columns:
  - name: pct_hospitals_with_stock
    tests:
      - is_in_range:
          min_val: 0
          max_val: 100
```

### Example: `test_row_count_above`

```sql
-- macros/tests/test_row_count_above.sql

{% test row_count_above(model, min_count) %}

-- Ensures a model has at least min_count rows

WITH row_count AS (
    SELECT COUNT(*) AS cnt
    FROM {{ model }}
)

SELECT cnt
FROM row_count
WHERE cnt < {{ min_count }}

{% endtest %}
```

**Usage:**

```yaml
models:
  - name: dim_hospitals
    tests:
      - row_count_above:
          min_count: 1000  # We expect at least 1000 hospitals
```

---

## 12. Running Tests and Interpreting Results

### Running All Tests

```bash
# Run all tests
dbt test

# Expected output:
# 02:30:00  Running with dbt=1.9.0
# 02:30:00  Found 5 models, 1 source, 15 tests
# 02:30:00
# 02:30:00  Concurrency: 4 threads (target='dev')
# 02:30:00
# 02:30:00  1 of 15 PASS unique_stg_blood_bank__hospitals_hospital_id ............... [PASS in 0.08s]
# 02:30:00  2 of 15 PASS not_null_stg_blood_bank__hospitals_hospital_id ............. [PASS in 0.06s]
# 02:30:00  3 of 15 PASS not_null_stg_blood_bank__hospitals_hospital_name ........... [PASS in 0.05s]
# 02:30:00  4 of 15 PASS accepted_values_stg_blood_bank__hospitals_hospital_type .... [PASS in 0.07s]
# 02:30:01  5 of 15 PASS relationships_fct_blood_availability_hospital_id ........... [PASS in 0.12s]
# 02:30:01  ...
# 02:30:01  15 of 15 PASS assert_no_negative_available_units ....................... [PASS in 0.09s]
# 02:30:01
# 02:30:01  Finished running 15 tests in 1.23s.
# 02:30:01
# 02:30:01  Completed successfully
# 02:30:01
# 02:30:01  Done. PASS=15 WARN=0 ERROR=0 SKIP=0 TOTAL=15
```

### Selective Test Execution

```bash
# Test a specific model
dbt test --select stg_blood_bank__hospitals

# Test all models with a specific tag
dbt test --select tag:critical

# Test all mart models
dbt test --select marts.*

# Test a specific test by name
dbt test --select assert_no_negative_available_units

# Test only generic tests (not singular)
dbt test --select test_type:generic

# Test only singular tests
dbt test --select test_type:singular
```

### Using `dbt build` (Run + Test Together)

```bash
# dbt build runs EACH model and then its tests, in dependency order
dbt build

# This is equivalent to:
# 1. dbt run --select stg_blood_bank__hospitals
# 2. dbt test --select stg_blood_bank__hospitals
# 3. dbt run --select stg_blood_bank__components
# 4. dbt test --select stg_blood_bank__components
# 5. ... and so on
```

> **💡 Best Practice**: Use `dbt build` in production. It ensures that if a staging model's tests fail, the downstream mart models **won't execute**, preventing bad data from reaching dashboards.

### Investigating Test Failures

When a test fails:

```bash
# 1. See the compiled test SQL
cat target/compiled/blood_bank_dbt/tests/assert_no_negative_available_units.sql

# 2. Run the SQL directly in PostgreSQL to see the failing rows
psql -U dbt_user -d blood_bank_db -h localhost -c "
$(cat target/compiled/blood_bank_dbt/tests/assert_no_negative_available_units.sql)
"

# 3. Check the dbt logs
cat logs/dbt.log | tail -50
```

---

## 13. Practice Exercises

### 🏋️ Exercise 1: Build a Complete Gold Layer

Build these 3 models from scratch:

1. `dim_hospitals.sql` — Join hospitals + contacts. Add data_freshness_status.
2. `fct_blood_availability.sql` — Join hospitals + components. Add business classifications.
3. `rpt_state_availability_dashboard.sql` — Aggregate fact table by state.

**Verification:**

```bash
dbt run --select marts.*
dbt test --select marts.*
```

---

### 🏋️ Exercise 2: Write 5 Generic Tests

Add these tests to your `_analytics__models.yml`:

1. `hospital_id` in `fct_blood_availability` should be `unique` and `not_null`
2. `availability_status` should only contain `['AVAILABLE', 'POSSIBLY_AVAILABLE', 'OUT_OF_STOCK', 'UNKNOWN']`
3. `hospital_id` in `fct_blood_availability` should exist in `dim_hospitals` (relationship test)
4. `state_name` in `rpt_state_availability_dashboard` should be `unique` and `not_null`
5. `urgency_level` should only contain `['HIGH', 'MEDIUM', 'LOW']`

<details>
<summary>Click to reveal solution</summary>

```yaml
# models/marts/analytics/_analytics__models.yml

version: 2

models:
  - name: fct_blood_availability
    columns:
      - name: hospital_id
        tests:
          - unique                         # Test 1a
          - not_null                       # Test 1b
          - relationships:                 # Test 3
              to: ref('dim_hospitals')
              field: hospital_id
      - name: availability_status
        tests:
          - accepted_values:               # Test 2
              values: ['AVAILABLE', 'POSSIBLY_AVAILABLE', 'OUT_OF_STOCK', 'UNKNOWN']
      - name: urgency_level
        tests:
          - accepted_values:               # Test 5
              values: ['HIGH', 'MEDIUM', 'LOW']

  - name: rpt_state_availability_dashboard
    columns:
      - name: state_name
        tests:
          - unique                         # Test 4a
          - not_null                       # Test 4b
```

</details>

---

### 🏋️ Exercise 3: Write 3 Singular Tests

Create these tests in the `tests/` directory:

1. `assert_total_hospitals_reasonable.sql` — The total count of hospitals should be between 1,000 and 10,000
2. `assert_no_future_dates.sql` — No hospital's `last_inventory_update_at` should be in the future
3. `assert_all_hospital_types_represented.sql` — All 3 hospital types (government, private, charitable) should exist

<details>
<summary>Click to reveal solutions</summary>

```sql
-- tests/assert_total_hospitals_reasonable.sql
WITH total AS (
    SELECT COUNT(*) AS cnt
    FROM {{ ref('dim_hospitals') }}
)
SELECT cnt
FROM total
WHERE cnt < 1000 OR cnt > 10000
```

```sql
-- tests/assert_no_future_dates.sql
SELECT
    hospital_id,
    hospital_name,
    last_inventory_update_at
FROM {{ ref('dim_hospitals') }}
WHERE last_inventory_update_at > CURRENT_TIMESTAMP
```

```sql
-- tests/assert_all_hospital_types_represented.sql
WITH expected_types AS (
    SELECT unnest(ARRAY['government', 'private', 'charitable']) AS expected_type
),
actual_types AS (
    SELECT DISTINCT hospital_type AS actual_type
    FROM {{ ref('dim_hospitals') }}
)
SELECT e.expected_type
FROM expected_types e
LEFT JOIN actual_types a
    ON e.expected_type = a.actual_type
WHERE a.actual_type IS NULL
```

</details>

---

### 🏋️ Exercise 4: Trace the DAG

Given this set of models, draw the complete DAG and determine the execution order:

```
sources.yml → raw_blood_bank.blood_inventory_raw

stg_blood_bank__hospitals.sql     → source('raw_blood_bank', 'blood_inventory_raw')
stg_blood_bank__components.sql    → source('raw_blood_bank', 'blood_inventory_raw')
stg_blood_bank__contacts.sql      → source('raw_blood_bank', 'blood_inventory_raw')

int_blood_bank__parsed_availability.sql → ref('stg_blood_bank__components')

dim_hospitals.sql                 → ref('stg_blood_bank__hospitals')
                                  → ref('stg_blood_bank__contacts')
                                  → ref('stg_blood_bank__components')

dim_districts.sql                 → ref('stg_blood_bank__hospitals')

fct_blood_availability.sql        → ref('stg_blood_bank__hospitals')
                                  → ref('stg_blood_bank__components')
                                  → ref('stg_blood_bank__contacts')

rpt_state_availability_dashboard.sql → ref('fct_blood_availability')
                                     → ref('dim_districts')
```

<details>
<summary>Click to reveal DAG and execution order</summary>

```
                  raw_blood_bank.blood_inventory_raw
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                  ▼
     stg_hospitals        stg_components      stg_contacts
         │ │ │                │ │                  │ │
         │ │ │                │ │                  │ │
         │ │ └──────┐         │ └────────┐        │ │
         │ │        │         │          │        │ │
         │ │    dim_districts  │   int_parsed    │ │
         │ │                  │   availability   │ │
         │ │                  │                  │ │
         │ └──────────────────┼──────────────────┘ │
         │                    │                    │
         └──────────┬─────────┘                    │
                    ▼                              │
           dim_hospitals                           │
                    │                              │
         ┌──────────┼──────────────────────────────┘
         │          │
         │     fct_blood_availability
         │          │
         │          ▼
         └──►rpt_state_availability_dashboard
```

**Execution order** (with 4 threads):

| Step | Models (can run in parallel) |
|------|------------------------------|
| 1 | `stg_hospitals`, `stg_components`, `stg_contacts` (all 3 in parallel) |
| 2 | `dim_districts`, `int_parsed_availability` (parallel, both depend on step 1) |
| 3 | `dim_hospitals`, `fct_blood_availability` (parallel, both depend on step 1) |
| 4 | `rpt_state_availability_dashboard` (depends on step 3) |

</details>

---

### 🏋️ Exercise 5: Fix These Test Failures

You run `dbt test` and get these failures. For each, explain the root cause and how to fix it:

**Failure 1:**
```
FAIL 3 accepted_values_fct_blood_availability_availability_status
  Got unexpected value: 'AVAILABLE_STALE'
```

**Failure 2:**
```
FAIL 147 unique_stg_blood_bank__hospitals_hospital_id
  147 duplicate hospital_ids found
```

**Failure 3:**
```
FAIL 12 relationships_fct_blood_availability_hospital_id__hospital_id__ref_dim_hospitals_
  12 orphaned hospital_ids found in fact table
```

<details>
<summary>Click to reveal diagnoses and fixes</summary>

**Failure 1**: Your CASE statement in `fct_blood_availability.sql` produces a value `'AVAILABLE_STALE'` that isn't in the accepted_values list.

**Fix options:**
- Add `'AVAILABLE_STALE'` to the accepted_values list in YAML
- Fix the CASE statement to use `'POSSIBLY_AVAILABLE'` instead of `'AVAILABLE_STALE'`

**Failure 2**: Your deduplication in `stg_blood_bank__hospitals.sql` isn't working correctly. 147 hospitals have duplicate entries.

**Fix**: Check the ROW_NUMBER() window function:
- Is the `PARTITION BY` using the correct column? (`hospital_id`)
- Is the `WHERE _row_number = 1` filter present in the final SELECT?
- Is `hospitalCode` being cast to INTEGER before deduplication? (String `'01'` ≠ `'1'`)

**Failure 3**: 12 `hospital_id` values exist in the fact table but NOT in the dimension table. This means the dimension is filtering out hospitals that the fact table includes.

**Fix**: 
- Check if `dim_hospitals` has stricter WHERE filters than `fct_blood_availability`
- Use LEFT JOIN in the fact table (already done) — the issue is likely in the dimension
- Ensure both models use the same deduplication logic

</details>

---

## 14. Key Takeaways

| Concept | One-Line Summary |
|---------|-----------------|
| **ref() function** | `{{ ref('model_name') }}` — references other models and auto-builds the DAG |
| **Dimension tables** | `dim_` prefix. Describe entities (WHO, WHAT, WHERE). One row per entity. |
| **Fact tables** | `fct_` prefix. Contain measurements/events. Can join multiple dimensions. |
| **Report tables** | `rpt_` prefix. Pre-aggregated for dashboard performance. |
| **Intermediate models** | `int_` prefix. Bridge Silver→Gold. Often materialized as `ephemeral`. |
| **config() block** | Override project-level settings at the model level |
| **Generic tests** | `unique`, `not_null`, `accepted_values`, `relationships` — defined in YAML |
| **Singular tests** | SQL files in `tests/`. Return failing rows. Any rows returned = FAIL. |
| **Custom generic tests** | Reusable test macros. Applied via YAML like built-in tests. |
| **dbt build** | Runs models AND tests in dependency order. Best for production. |
| **Test severity** | `error` (stops pipeline) vs `warn` (logs warning, continues) |
| **LEFT JOIN in dims** | Always LEFT JOIN in dimensions to avoid silently dropping records |

---

## 🔜 Next Module

**[Module 5: Pro-Level Macros and Deployment →](./05_Pro_Level_Macros_and_Deployment.md)**

In the next module, you'll:
- Write advanced Jinja macros to eliminate duplicate SQL
- Build incremental models for massive datasets
- Generate data lineage documentation
- Deploy dbt in CI/CD pipelines and Apache Airflow
- Master the techniques that separate junior from senior data engineers

---

> **📝 Author's Note**: Testing is the **most underrated** skill in data engineering. Anyone can write a `SELECT` statement. A senior engineer writes tests that catch problems before they reach the dashboard. If you skip this module, go back and re-read the testing section. It will save your career.
