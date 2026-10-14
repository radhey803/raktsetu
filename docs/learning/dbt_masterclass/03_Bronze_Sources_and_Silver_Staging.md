# 📘 Module 3: Bronze Sources and Silver Staging

> **Masterclass Series**: dbt — From Absolute Beginner to Senior Data Engineer  
> **Module**: 3 of 5  
> **Difficulty**: 🟡 Intermediate  
> **Estimated Time**: 3–4 hours  
> **Theme**: India Blood Bank Inventory System (eRaktKosh)  
> **Prerequisites**: Modules 1 & 2 completed, PostgreSQL running, dbt project initialized

---

## 📑 Table of Contents

1. [The Source → Staging Pipeline](#1-the-source--staging-pipeline)
2. [Defining Sources in YAML (Bronze Layer)](#2-defining-sources-in-yaml-bronze-layer)
3. [Deep Dive: The source() Function](#3-deep-dive-the-source-function)
4. [Source Freshness — Is Our Data Stale?](#4-source-freshness--is-our-data-stale)
5. [Staging Model Design Principles](#5-staging-model-design-principles)
6. [Building the Blood Bank Staging Models](#6-building-the-blood-bank-staging-models)
7. [Schema YAML Files — Documentation & Configuration](#7-schema-yaml-files--documentation--configuration)
8. [Running and Verifying Your Staging Layer](#8-running-and-verifying-your-staging-layer)
9. [Practice Exercises](#10-practice-exercises)
10. [Common Anti-Patterns to Avoid](#10-common-anti-patterns-to-avoid)
11. [Key Takeaways](#11-key-takeaways)

---

## 1. The Source → Staging Pipeline

In Module 1, we learned about the Medallion Architecture. Now we're going to build the first two layers:

```
┌──────────────────────┐          ┌──────────────────────┐
│       BRONZE         │          │       SILVER          │
│   (Sources/Raw)      │  ──dbt──►│   (Staging/Cleaned)   │
│                      │          │                       │
│  raw_blood_bank.     │          │  staging.              │
│  blood_inventory_raw │          │  stg_blood_bank__     │
│                      │          │  hospitals             │
│  • All TEXT columns  │          │  • Proper data types  │
│  • Messy names       │          │  • snake_case names   │
│  • Duplicates        │          │  • Deduplicated       │
│  • No validation     │          │  • Filtered junk      │
└──────────────────────┘          └──────────────────────┘
```

**The workflow in this module:**

1. **Define sources** → Tell dbt about your raw tables using `sources.yml`
2. **Write staging models** → Clean, cast, rename, and filter the raw data
3. **Document everything** → Describe tables and columns in YAML
4. **Test data quality** → (Covered in detail in Module 4)

---

## 2. Defining Sources in YAML (Bronze Layer)

### What Are Sources?

**Sources** are dbt's way of formally declaring the raw tables that already exist in your warehouse. They tell dbt:

- **Where** the raw data lives (schema + table name)
- **What** the data represents (descriptions)
- **How fresh** the data should be (freshness thresholds)
- **What tests** to run on the raw data (optional)

### Why Not Just Reference Raw Tables Directly?

You *could* write:

```sql
-- ❌ BAD: Hardcoding the table name
SELECT * FROM raw_blood_bank.blood_inventory_raw
```

But this creates problems:

| Problem | Impact |
|---------|--------|
| **No lineage tracking** | dbt's DAG doesn't know about this table |
| **No freshness monitoring** | You can't check if the data is stale |
| **No documentation** | No descriptions for columns or tables |
| **Hardcoded references** | If the table moves or is renamed, you must find-and-replace everywhere |
| **No compile-time validation** | dbt can't warn you if the source doesn't exist |

Instead, you should use the **source() function**:

```sql
-- ✅ GOOD: Using the source() function
SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
```

### Creating Your First sources.yml

Create the following file:

```
models/
└── staging/
    └── blood_bank/
        ├── _blood_bank__sources.yml    ← This file!
        ├── stg_blood_bank__hospitals.sql
        └── stg_blood_bank__components.sql
```

> **📌 Naming Convention**: Source YAML files are prefixed with `_` (underscore) to sort them to the top of the directory. The format is `_{source_name}__sources.yml`.

```yaml
# models/staging/blood_bank/_blood_bank__sources.yml

version: 2

sources:
  - name: raw_blood_bank                        # Source name (used in source() function)
    description: >
      Raw blood bank inventory data scraped from India's eRaktKosh portal.
      This data is loaded by the async_scraper.py Python script and represents
      the Bronze/landing layer of our data pipeline.
      Data includes 3,000+ blood banks across all Indian states and UTs.
    database: blood_bank_db                      # Database name
    schema: raw_blood_bank                       # Schema where raw tables live

    # Source freshness configuration
    loaded_at_field: _loaded_at                  # Column that tracks when data was loaded
    freshness:
      warn_after:
        count: 24
        period: hour                             # Warn if data > 24 hours old
      error_after:
        count: 72
        period: hour                             # Error if data > 72 hours old

    # Quoting (set to true if your identifiers have special characters)
    quoting:
      database: false
      schema: false
      identifier: false

    tables:
      - name: blood_inventory_raw                # Table name in the database
        description: >
          Raw blood bank inventory data with one row per hospital/blood storage unit.
          Contains hospital details, blood component availability, and contact information.
          Data is loaded as-is from the eRaktKosh API — all columns are TEXT type.
          Approximately 14,000+ rows covering all states and union territories of India.
        
        # Column-level documentation
        columns:
          - name: hospitalCode
            description: >
              Unique identifier for each hospital/blood bank. 
              May contain '-' for some BSU entries (these should be filtered in staging).
              Cast to INTEGER in the staging layer.
            tests:
              - not_null:
                  config:
                    where: "hospitalCode != '-'"

          - name: hospitalname
            description: >
              Full name of the hospital or blood bank.
              May contain leading/trailing whitespace — clean with TRIM() in staging.

          - name: hospitaladd
            description: >
              Full address of the hospital as a single text string.
              Contains city, district, state, and pincode in various formats.

          - name: hospitalcontact
            description: >
              Contact details including phone, fax, and email.
              Format varies: "Phone: XXXXXXXXXX ,Fax: XXXXXXXXXX, Email: xxx@xxx.com"

          - name: hospitalType
            description: >
              Type of hospital ownership.
              Expected values: "Govt.", "Private", "Charitable/Vol"

          - name: entrydate
            description: >
              Timestamp of when the hospital last updated its inventory.
              Format: "YYYY-MM-DD HH:MI:SS" (stored as TEXT in Bronze).
              Cast to TIMESTAMP in the staging layer.

          - name: offline
            description: >
              Whether the hospital data was submitted offline.
              Values: "0" (online) or "1" (offline). Cast to BOOLEAN in staging.

          - name: type
            description: >
              Type of facility. Values: "Blood Bank" or "BSU" (Blood Storage Unit).

          - name: State
            description: >
              Indian state or union territory name.
              E.g., "Maharashtra", "Andaman and Nicobar Islands"

          - name: District
            description: >
              District within the state.
              E.g., "South Andaman", "Alluri Sitharama Raju"

          - name: available_WithQty
            description: >
              Available blood components with quantities.
              Complex string format: "O+Ve : 16, A+Ve : 13, B+Ve : 17"

          - name: not_available_WithQty
            description: >
              Unavailable blood components (quantity = 0).
              Complex string format: "B+Ve : 0, Oh+VE : 0, AB+Ve : 0"

          - name: components
            description: >
              Complete component breakdown as a Python dictionary string.
              Contains all blood components and their availability status.
              This is the most complex column — requires parsing in staging.

          - name: moderateStock
            description: >
              Flag indicating moderate stock levels. Values: "0" or "1".

          - name: _loaded_at
            description: >
              Metadata column: Timestamp when this row was loaded into the warehouse.
              Added by the loading script, not from the source API.

          - name: _source_file
            description: >
              Metadata column: Name of the CSV file this data was loaded from.
              Added by the loading script for data lineage tracking.
```

### sources.yml Deep Dive: Every Field Explained

| Field | Level | Purpose | Required? |
|-------|-------|---------|-----------|
| `version: 2` | Top | YAML schema version (always 2) | ✅ Yes |
| `sources` | Top | List of source definitions | ✅ Yes |
| `name` | Source | Source name — used in `{{ source('name', 'table') }}` | ✅ Yes |
| `description` | Source/Table/Column | Human-readable description | ❌ No (but DO it!) |
| `database` | Source | Database name | ❌ No (uses default from profiles.yml) |
| `schema` | Source | Schema where raw tables live | ✅ Yes |
| `loaded_at_field` | Source | Column name for freshness checks | ❌ No (needed for freshness) |
| `freshness` | Source | Freshness thresholds | ❌ No |
| `tables` | Source | List of tables in this source | ✅ Yes |
| `columns` | Table | List of column definitions | ❌ No (but DO it!) |
| `tests` | Column | Data quality tests on the source | ❌ No |

---

## 3. Deep Dive: The source() Function

### Syntax

```sql
{{ source('source_name', 'table_name') }}
```

### What It Compiles To

```sql
-- Jinja (what you write)
SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

-- Compiled SQL (what dbt runs)
SELECT * FROM "blood_bank_db"."raw_blood_bank"."blood_inventory_raw"
```

### How dbt Resolves the source() Function

```
{{ source('raw_blood_bank', 'blood_inventory_raw') }}
           │                    │
           │                    └── Matches: tables: - name: blood_inventory_raw
           └── Matches: sources: - name: raw_blood_bank
                                      schema: raw_blood_bank
                                      database: blood_bank_db

Result: "blood_bank_db"."raw_blood_bank"."blood_inventory_raw"
```

### Why source() is Better Than Hardcoding

```sql
-- ❌ Hardcoded: If you rename the schema, you must update EVERY model
SELECT * FROM raw_blood_bank.blood_inventory_raw

-- ✅ source(): If you rename the schema, update ONE place (sources.yml)
SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
```

| Benefit | Explanation |
|---------|-------------|
| **Single source of truth** | Table references defined in ONE file, not scattered across models |
| **DAG visibility** | dbt's lineage graph shows which models depend on which sources |
| **Freshness monitoring** | `dbt source freshness` checks if data is stale |
| **Documentation** | Source descriptions appear in `dbt docs` |
| **Refactoring safety** | Rename a table in sources.yml → all models update automatically |

---

## 4. Source Freshness — Is Our Data Stale?

### The Problem

Your blood bank dashboard shows "O+ available: 50 units" but the data is **3 days old**. A patient relies on this and drives to the hospital — the blood is gone. **Stale data kills.**

### The Solution: dbt Source Freshness

```yaml
# In your sources.yml (already configured above)

loaded_at_field: _loaded_at
freshness:
  warn_after:
    count: 24
    period: hour    # ⚠️ Warning after 24 hours
  error_after:
    count: 72
    period: hour    # ❌ Error after 72 hours
```

### Running Freshness Checks

```bash
# Check freshness of all sources
dbt source freshness

# Expected output:
# 01:50:00  Running with dbt=1.9.0
# 01:50:01  Found 1 source, 1 table
# 01:50:01
# 01:50:01  1 of 1 WARN freshness of raw_blood_bank.blood_inventory_raw ... [WARN in 0.12s]
# 01:50:01
# 01:50:01  Done. PASS=0 WARN=1 ERROR=0 SKIP=0 TOTAL=1
```

### Interpreting Freshness Results

| Status | Meaning | Action |
|--------|---------|--------|
| **PASS** ✅ | Data loaded within the `warn_after` threshold | All good |
| **WARN** ⚠️ | Data loaded between `warn_after` and `error_after` | Investigate — is the scraper running? |
| **ERROR** ❌ | Data loaded beyond `error_after` | Alert! Stop pipeline. Fix the data source. |

### Best Practice: Freshness Check Before Transformation

```bash
# In your CI/CD pipeline or Airflow DAG:
# Step 1: Check freshness
dbt source freshness

# Step 2: Only run models if freshness passed
dbt run
```

---

## 5. Staging Model Design Principles

### The 5 Rules of Staging Models

Staging models are the **foundation** of your data warehouse. Get them right, and everything downstream is easy. Get them wrong, and you'll fight bugs for months.

### Rule 1: One Staging Model Per Source Table

```
✅ CORRECT:
raw_blood_bank.blood_inventory_raw  →  stg_blood_bank__hospitals.sql
                                    →  stg_blood_bank__components.sql
                                    →  stg_blood_bank__contacts.sql

❌ WRONG:
raw_blood_bank.blood_inventory_raw  →  stg_all_data.sql  (one giant model)
```

> **💡 Why?** Each staging model should represent a **single entity** (hospitals, components, contacts). This makes the models focused, testable, and reusable.

### Rule 2: Only SELECT from source()

```sql
-- ✅ CORRECT: Staging reads from source()
SELECT ... FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

-- ❌ WRONG: Staging reads from another staging model
SELECT ... FROM {{ ref('stg_blood_bank__hospitals') }}  -- This belongs in marts!

-- ❌ WRONG: Staging reads from a hardcoded table
SELECT ... FROM raw_blood_bank.blood_inventory_raw      -- Use source()!
```

### Rule 3: Only Cleaning Operations (No Business Logic!)

**What staging SHOULD do:**

| Operation | Example |
|-----------|---------|
| **Rename columns** | `hospitalCode` → `hospital_id` |
| **Cast data types** | `TEXT` → `INTEGER`, `TIMESTAMP`, `BOOLEAN` |
| **Clean whitespace** | `TRIM(hospitalname)` |
| **Standardize values** | `LOWER(TRIM(State))` → `'maharashtra'` |
| **Filter junk rows** | `WHERE hospitalCode IS NOT NULL AND hospitalCode != '-'` |
| **Deduplicate** | `ROW_NUMBER() OVER (PARTITION BY hospital_id ORDER BY entrydate DESC)` |
| **Add metadata** | `CURRENT_TIMESTAMP AS _transformed_at` |

**What staging should NOT do:**

| Operation | Where It Belongs |
|-----------|-----------------|
| **Joins across sources** | Intermediate or Marts layer |
| **Aggregations** (SUM, COUNT, AVG) | Marts layer |
| **Business classifications** (stock_status) | Marts layer |
| **Complex calculations** | Marts layer |
| **KPIs and metrics** | Marts layer |

### Rule 4: Naming Convention `stg_{source}__{entity}`

```
stg_blood_bank__hospitals          ✅
stg_blood_bank__components         ✅
stg_blood_bank__contacts           ✅
stg_eraktkosh__hospitals           ✅ (if you had a different source)

staging_hospitals                  ❌ (no source prefix)
stg_hospitals                      ❌ (missing source name)
clean_hospitals                    ❌ (wrong prefix)
stg_blood_bank_hospitals           ❌ (single underscore)
```

### Rule 5: Materialize as Views

```yaml
# dbt_project.yml
models:
  blood_bank_dbt:
    staging:
      +materialized: view     # Views are always up-to-date, no storage cost
```

**Why views for staging?**
- Views don't store data — they just run the SELECT on-demand
- They always reflect the latest data in Bronze
- They use zero extra storage
- For small to medium datasets (< 10M rows), views are fast enough

---

## 6. Building the Blood Bank Staging Models

Now let's build the complete staging layer for our blood bank project.

### Directory Structure

```
models/
└── staging/
    └── blood_bank/
        ├── _blood_bank__sources.yml        # Source definitions (already created)
        ├── _blood_bank__models.yml         # Model documentation & tests
        ├── stg_blood_bank__hospitals.sql   # Hospital entity
        ├── stg_blood_bank__components.sql  # Blood component availability
        └── stg_blood_bank__contacts.sql    # Hospital contact details
```

### Model 1: `stg_blood_bank__hospitals.sql`

This model extracts the **hospital entity** from the raw data.

```sql
-- models/staging/blood_bank/stg_blood_bank__hospitals.sql

-- ============================================================
-- STAGING MODEL: Blood Bank Hospitals
-- Source: raw_blood_bank.blood_inventory_raw
-- Grain: One row per unique hospital
-- 
-- This model:
--   1. Extracts hospital attributes from the raw inventory table
--   2. Casts all columns to proper data types
--   3. Renames columns to snake_case convention
--   4. Deduplicates hospitals (keeps the most recent entry)
--   5. Filters out invalid records (null/invalid hospital codes)
-- ============================================================

WITH source_data AS (

    SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

),

-- Step 1: Clean and cast all columns
cleaned AS (

    SELECT
        -- Primary key
        CAST(hospitalCode AS INTEGER)                           AS hospital_id,

        -- Hospital attributes
        TRIM(hospitalname)                                      AS hospital_name,
        TRIM(hospitaladd)                                       AS hospital_address,

        -- Hospital classification
        CASE TRIM(hospitalType)
            WHEN 'Govt.'          THEN 'government'
            WHEN 'Private'        THEN 'private'
            WHEN 'Charitable/Vol' THEN 'charitable'
            ELSE 'unknown'
        END                                                     AS hospital_type,

        -- Facility type
        CASE TRIM(type)
            WHEN 'Blood Bank' THEN 'blood_bank'
            WHEN 'BSU'        THEN 'blood_storage_unit'
            ELSE 'unknown'
        END                                                     AS facility_type,

        -- Geographic attributes
        TRIM(State)                                             AS state_name,
        TRIM(District)                                          AS district_name,

        -- Operational status
        CASE TRIM(offline)
            WHEN '1' THEN TRUE
            WHEN '0' THEN FALSE
            ELSE NULL
        END                                                     AS is_offline,

        CAST(moderateStock AS INTEGER)                          AS moderate_stock_flag,

        -- Temporal attributes
        CAST(entrydate AS TIMESTAMP)                            AS last_inventory_update_at,

        -- Metadata
        _loaded_at                                              AS _loaded_at,
        _source_file                                            AS _source_file,
        CURRENT_TIMESTAMP                                       AS _transformed_at,

        -- Deduplication: Keep the most recent entry per hospital
        ROW_NUMBER() OVER (
            PARTITION BY CAST(hospitalCode AS INTEGER)
            ORDER BY CAST(entrydate AS TIMESTAMP) DESC NULLS LAST
        )                                                       AS _row_number

    FROM source_data
    WHERE 
        -- Filter out invalid hospital codes
        hospitalCode IS NOT NULL
        AND TRIM(hospitalCode) != '-'
        AND TRIM(hospitalCode) != ''
        -- Ensure hospital code is numeric
        AND hospitalCode ~ '^[0-9]+$'
        -- Filter out null states
        AND State IS NOT NULL
        AND TRIM(State) != ''

)

-- Step 2: Keep only the most recent record per hospital
SELECT
    hospital_id,
    hospital_name,
    hospital_address,
    hospital_type,
    facility_type,
    state_name,
    district_name,
    is_offline,
    moderate_stock_flag,
    last_inventory_update_at,
    _loaded_at,
    _source_file,
    _transformed_at
FROM cleaned
WHERE _row_number = 1
```

### Understanding the Model: Line by Line

Let's break down the key techniques used:

#### Technique 1: CTE Pattern (WITH ... AS)

```sql
WITH source_data AS (
    SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
),

cleaned AS (
    SELECT ... FROM source_data
)

SELECT ... FROM cleaned
```

**Why CTEs?**
- Each CTE has a clear purpose (source_data → cleaned → final select)
- Easy to debug (you can comment out the final SELECT and test each CTE)
- Readable — anyone can follow the transformation pipeline

#### Technique 2: Type Casting

```sql
-- TEXT → INTEGER
CAST(hospitalCode AS INTEGER) AS hospital_id

-- TEXT → TIMESTAMP
CAST(entrydate AS TIMESTAMP) AS last_inventory_update_at

-- TEXT → BOOLEAN (using CASE because the values are "0"/"1")
CASE TRIM(offline)
    WHEN '1' THEN TRUE
    WHEN '0' THEN FALSE
    ELSE NULL
END AS is_offline
```

> **💡 Pro Tip**: PostgreSQL's `CAST(x AS BOOLEAN)` only works for `'true'`/`'false'` strings, NOT `'1'`/`'0'`. Use a `CASE` statement for `'1'`/`'0'` conversion.

#### Technique 3: Value Standardization

```sql
CASE TRIM(hospitalType)
    WHEN 'Govt.'          THEN 'government'
    WHEN 'Private'        THEN 'private'
    WHEN 'Charitable/Vol' THEN 'charitable'
    ELSE 'unknown'
END AS hospital_type
```

**Why standardize?**
- Raw data might have `'Govt.'`, `'govt.'`, `'GOVT.'`, or `'Government'`
- Downstream models and dashboards need consistent values
- The `ELSE 'unknown'` catches any unexpected values

#### Technique 4: Deduplication with ROW_NUMBER()

```sql
ROW_NUMBER() OVER (
    PARTITION BY CAST(hospitalCode AS INTEGER)    -- Group by hospital
    ORDER BY CAST(entrydate AS TIMESTAMP) DESC    -- Most recent first
    NULLS LAST                                    -- Push nulls to the bottom
) AS _row_number

-- Then in the final SELECT:
WHERE _row_number = 1  -- Keep only the most recent record
```

This is the **industry-standard deduplication pattern**. It:
1. Groups rows by the entity key (`hospital_id`)
2. Orders by the "freshness" column (`entrydate`) descending
3. Keeps only the first row (most recent) for each group

#### Technique 5: Input Validation

```sql
WHERE 
    hospitalCode IS NOT NULL
    AND TRIM(hospitalCode) != '-'
    AND TRIM(hospitalCode) != ''
    AND hospitalCode ~ '^[0-9]+$'    -- Regex: only numeric codes
    AND State IS NOT NULL
```

**Why validate inputs?**
- Raw data is messy. Some hospitals have `-` as their code.
- Some have empty strings or non-numeric codes.
- Filtering in staging prevents type casting errors (`CAST('-' AS INTEGER)` would fail!)

---

### Model 2: `stg_blood_bank__components.sql`

This model extracts **blood component availability** per hospital.

```sql
-- models/staging/blood_bank/stg_blood_bank__components.sql

-- ============================================================
-- STAGING MODEL: Blood Bank Component Availability
-- Source: raw_blood_bank.blood_inventory_raw
-- Grain: One row per hospital per component type
-- 
-- This model:
--   1. Extracts component names and availability strings
--   2. Parses the available_WithQty string to extract blood groups
--   3. Creates a row per hospital-component combination
--   4. Casts quantities to INTEGER
-- ============================================================

WITH source_data AS (

    SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

),

-- Step 1: Extract available components with their quantities
-- The raw data has 'available_WithQty' as a string like: "O+Ve : 16, A+Ve : 13, B+Ve : 17"
-- We need to parse this into individual rows

hospital_components AS (

    SELECT
        CAST(hospitalCode AS INTEGER)       AS hospital_id,
        TRIM(hospitalname)                  AS hospital_name,
        TRIM(State)                         AS state_name,
        TRIM(District)                      AS district_name,
        TRIM(type)                          AS facility_type,
        CAST(entrydate AS TIMESTAMP)        AS last_inventory_update_at,

        -- Extract the available_WithQty string
        COALESCE(TRIM(available_WithQty), '') AS available_qty_raw,

        -- Extract the not_available_WithQty string
        COALESCE(TRIM(not_available_WithQty), '') AS not_available_qty_raw,

        -- Metadata
        CURRENT_TIMESTAMP                   AS _transformed_at

    FROM source_data
    WHERE 
        hospitalCode IS NOT NULL
        AND TRIM(hospitalCode) != '-'
        AND TRIM(hospitalCode) != ''
        AND hospitalCode ~ '^[0-9]+$'

),

-- Step 2: Determine overall availability status per hospital
availability_summary AS (

    SELECT
        hospital_id,
        hospital_name,
        state_name,
        district_name,
        facility_type,
        last_inventory_update_at,

        -- Has any available blood?
        CASE
            WHEN available_qty_raw != '' THEN TRUE
            ELSE FALSE
        END AS has_available_stock,

        -- Raw strings for downstream parsing
        available_qty_raw,
        not_available_qty_raw,

        _transformed_at

    FROM hospital_components

),

-- Step 3: Deduplicate
deduplicated AS (

    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY hospital_id
            ORDER BY last_inventory_update_at DESC NULLS LAST
        ) AS _row_number
    FROM availability_summary

)

SELECT
    hospital_id,
    hospital_name,
    state_name,
    district_name,
    facility_type,
    has_available_stock,
    available_qty_raw,
    not_available_qty_raw,
    last_inventory_update_at,
    _transformed_at
FROM deduplicated
WHERE _row_number = 1
```

---

### Model 3: `stg_blood_bank__contacts.sql`

This model extracts **contact information** for each hospital.

```sql
-- models/staging/blood_bank/stg_blood_bank__contacts.sql

-- ============================================================
-- STAGING MODEL: Blood Bank Contact Information
-- Source: raw_blood_bank.blood_inventory_raw
-- Grain: One row per unique hospital
-- 
-- This model:
--   1. Parses the hospitalcontact string into phone, fax, email
--   2. Extracts city/pincode from the address where possible
--   3. Cleans and standardizes contact fields
-- ============================================================

WITH source_data AS (

    SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

),

-- Step 1: Extract and parse contact information
parsed_contacts AS (

    SELECT
        CAST(hospitalCode AS INTEGER)           AS hospital_id,
        TRIM(hospitalname)                      AS hospital_name,

        -- Parse phone number from "Phone: 9679535438 ,Fax: 0, Email: xxx@xxx.com"
        CASE 
            WHEN hospitalcontact LIKE '%Phone:%' THEN
                TRIM(
                    SPLIT_PART(
                        SPLIT_PART(hospitalcontact, 'Phone:', 2),
                        ',', 1
                    )
                )
            ELSE NULL
        END                                     AS phone_number,

        -- Parse fax number
        CASE 
            WHEN hospitalcontact LIKE '%Fax:%' THEN
                TRIM(
                    SPLIT_PART(
                        SPLIT_PART(hospitalcontact, 'Fax:', 2),
                        ',', 1
                    )
                )
            ELSE NULL
        END                                     AS fax_number,

        -- Parse email
        CASE 
            WHEN hospitalcontact LIKE '%Email:%' THEN
                TRIM(LOWER(
                    SPLIT_PART(hospitalcontact, 'Email:', 2)
                ))
            ELSE NULL
        END                                     AS email_address,

        -- Full address (cleaned)
        TRIM(hospitaladd)                       AS full_address,

        -- State and District for joining
        TRIM(State)                             AS state_name,
        TRIM(District)                          AS district_name,

        -- Metadata
        CURRENT_TIMESTAMP                       AS _transformed_at,

        -- Deduplication
        ROW_NUMBER() OVER (
            PARTITION BY CAST(hospitalCode AS INTEGER)
            ORDER BY CAST(entrydate AS TIMESTAMP) DESC NULLS LAST
        )                                       AS _row_number

    FROM source_data
    WHERE 
        hospitalCode IS NOT NULL
        AND TRIM(hospitalCode) != '-'
        AND TRIM(hospitalCode) != ''
        AND hospitalCode ~ '^[0-9]+$'

)

SELECT
    hospital_id,
    hospital_name,
    phone_number,
    -- Clean up fax (ignore "0" or "1234567890" placeholders)
    CASE 
        WHEN fax_number IN ('0', '1234567890', '') THEN NULL
        ELSE fax_number
    END AS fax_number,
    email_address,
    full_address,
    state_name,
    district_name,
    _transformed_at
FROM parsed_contacts
WHERE _row_number = 1
```

### Understanding Contact Parsing

The raw `hospitalcontact` column looks like:

```
"Phone: 9679535438 ,Fax: 0, Email: pillar.portblair@gmail.com"
```

We use `SPLIT_PART()` to parse it:

```sql
-- How SPLIT_PART works:
SPLIT_PART('Phone: 9679535438 ,Fax: 0, Email: xxx', 'Phone:', 2)
-- Returns: ' 9679535438 ,Fax: 0, Email: xxx'

SPLIT_PART(' 9679535438 ,Fax: 0, Email: xxx', ',', 1)
-- Returns: ' 9679535438 '

TRIM(' 9679535438 ')
-- Returns: '9679535438'
```

> **💡 Pro Tip**: In a production environment, you might use a **regex** or a **custom macro** for this parsing. We'll build a macro for this in Module 5.

---

## 7. Schema YAML Files — Documentation & Configuration

### Creating the Models YAML

```yaml
# models/staging/blood_bank/_blood_bank__models.yml

version: 2

models:
  # ============================
  # Model 1: Hospitals
  # ============================
  - name: stg_blood_bank__hospitals
    description: >
      Cleaned and deduplicated hospital/blood bank entities from the eRaktKosh 
      raw data. One row per unique hospital. All columns are properly typed,
      renamed to snake_case, and validated.
    
    config:
      materialized: view
      tags: ['staging', 'blood_bank', 'hospitals']
    
    columns:
      - name: hospital_id
        description: "Unique integer identifier for each hospital (cast from hospitalCode)"
        tests:
          - unique
          - not_null
      
      - name: hospital_name
        description: "Full name of the hospital or blood bank (trimmed)"
        tests:
          - not_null

      - name: hospital_type
        description: "Standardized hospital ownership type"
        tests:
          - not_null
          - accepted_values:
              values: ['government', 'private', 'charitable', 'unknown']

      - name: facility_type
        description: "Type of blood facility"
        tests:
          - not_null
          - accepted_values:
              values: ['blood_bank', 'blood_storage_unit', 'unknown']

      - name: state_name
        description: "Indian state or union territory name"
        tests:
          - not_null

      - name: district_name
        description: "District within the state"

      - name: last_inventory_update_at
        description: "Timestamp when the hospital last updated its blood inventory"
        tests:
          - not_null

  # ============================
  # Model 2: Components
  # ============================
  - name: stg_blood_bank__components
    description: >
      Blood component availability per hospital. Contains parsed availability 
      strings and an overall stock indicator. One row per unique hospital.
    
    config:
      materialized: view
      tags: ['staging', 'blood_bank', 'components']
    
    columns:
      - name: hospital_id
        description: "Foreign key to stg_blood_bank__hospitals"
        tests:
          - unique
          - not_null

      - name: has_available_stock
        description: "TRUE if the hospital has any blood components in stock"
        tests:
          - not_null

      - name: available_qty_raw
        description: >
          Raw string of available blood groups and quantities.
          Format: "O+Ve : 16, A+Ve : 13". Empty string if nothing available.

  # ============================
  # Model 3: Contacts
  # ============================
  - name: stg_blood_bank__contacts
    description: >
      Parsed contact information for each hospital. Phone, fax, and email 
      extracted from the raw contact string. One row per unique hospital.
    
    config:
      materialized: view
      tags: ['staging', 'blood_bank', 'contacts']
    
    columns:
      - name: hospital_id
        description: "Foreign key to stg_blood_bank__hospitals"
        tests:
          - unique
          - not_null

      - name: phone_number
        description: "Primary phone number (extracted from contact string)"

      - name: email_address
        description: "Email address (extracted and lowercased)"
```

### Why YAML Documentation Matters

1. **`dbt docs generate`** reads these YAML files and creates a **searchable documentation website**
2. **Tests** defined here run automatically with `dbt test`
3. **Descriptions** help onboard new team members — they don't need to read SQL to understand each column
4. **Column-level lineage** is tracked through these definitions

---

## 8. Running and Verifying Your Staging Layer

### Run All Staging Models

```bash
# Run only staging models
dbt run --select staging.*

# Expected output:
# 02:00:00  Running with dbt=1.9.0
# 02:00:00  Found 3 models, 1 source, 8 tests, 0 seeds
# 02:00:00
# 02:00:00  Concurrency: 4 threads (target='dev')
# 02:00:00
# 02:00:01  1 of 3 START sql view model staging.stg_blood_bank__hospitals ... [RUN]
# 02:00:01  2 of 3 START sql view model staging.stg_blood_bank__components ... [RUN]
# 02:00:01  3 of 3 START sql view model staging.stg_blood_bank__contacts ... [RUN]
# 02:00:01  1 of 3 OK created sql view model staging.stg_blood_bank__hospitals [CREATE VIEW in 0.08s]
# 02:00:01  2 of 3 OK created sql view model staging.stg_blood_bank__components [CREATE VIEW in 0.09s]
# 02:00:01  3 of 3 OK created sql view model staging.stg_blood_bank__contacts [CREATE VIEW in 0.10s]
# 02:00:01
# 02:00:01  Finished running 3 view models in 0.35s.
# 02:00:01
# 02:00:01  Completed successfully
```

### Run Tests

```bash
# Run all tests
dbt test

# Run tests for a specific model
dbt test --select stg_blood_bank__hospitals
```

### Verify in PostgreSQL

```bash
psql -U dbt_user -d blood_bank_db -h localhost
```

```sql
-- Check hospitals
SELECT COUNT(*) FROM staging.stg_blood_bank__hospitals;
-- Expected: ~3,000+ unique hospitals

-- Verify data types
SELECT 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_schema = 'staging' 
  AND table_name = 'stg_blood_bank__hospitals'
ORDER BY ordinal_position;

-- Preview hospital data
SELECT 
    hospital_id,
    hospital_name,
    hospital_type,
    state_name,
    last_inventory_update_at
FROM staging.stg_blood_bank__hospitals
LIMIT 10;

-- Check state distribution
SELECT 
    state_name,
    hospital_type,
    COUNT(*) AS count
FROM staging.stg_blood_bank__hospitals
GROUP BY state_name, hospital_type
ORDER BY count DESC
LIMIT 15;

-- Check contacts parsing
SELECT 
    hospital_name,
    phone_number,
    email_address
FROM staging.stg_blood_bank__contacts
WHERE email_address IS NOT NULL
LIMIT 10;
```

### Check the Compiled SQL

```bash
# See the compiled SQL that dbt generated
cat target/compiled/blood_bank_dbt/models/staging/blood_bank/stg_blood_bank__hospitals.sql
```

This shows you the SQL **after all Jinja was resolved** — useful for debugging.

---

## 9. Practice Exercises

### 🏋️ Exercise 1: Add a New Staging Model

Create a new staging model: `stg_blood_bank__state_districts.sql`

**Requirements:**
- Extract distinct state + district combinations from the raw data
- Create a surrogate key by concatenating state and district
- Count the number of hospitals in each district
- Include columns: `state_name`, `district_name`, `hospital_count`

<details>
<summary>Click to reveal solution</summary>

```sql
-- models/staging/blood_bank/stg_blood_bank__state_districts.sql

WITH source_data AS (

    SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

),

districts AS (

    SELECT
        TRIM(State) AS state_name,
        TRIM(District) AS district_name,
        COUNT(DISTINCT hospitalCode) FILTER (
            WHERE hospitalCode IS NOT NULL 
            AND hospitalCode != '-' 
            AND hospitalCode ~ '^[0-9]+$'
        ) AS hospital_count
    FROM source_data
    WHERE State IS NOT NULL 
      AND TRIM(State) != ''
      AND District IS NOT NULL 
      AND TRIM(District) != ''
    GROUP BY TRIM(State), TRIM(District)

)

SELECT
    -- Create a surrogate key
    MD5(state_name || '||' || district_name) AS district_id,
    state_name,
    district_name,
    hospital_count,
    CURRENT_TIMESTAMP AS _transformed_at
FROM districts
ORDER BY state_name, district_name
```

</details>

---

### 🏋️ Exercise 2: Write a sources.yml From Scratch

Imagine you have a second source: a CSV of Indian state population data loaded into `raw_census.state_population`.

| Column | Type | Description |
|--------|------|-------------|
| state_code | TEXT | 2-letter state code |
| state_name | TEXT | Full state name |
| population_2021 | TEXT | Population count (as text) |
| area_sq_km | TEXT | Geographic area |
| literacy_rate | TEXT | Literacy percentage |
| _loaded_at | TEXT | Load timestamp |

Write the complete `_census__sources.yml` file with:
- Source description
- All column descriptions
- Freshness configuration (warn: 30 days, error: 90 days)

<details>
<summary>Click to reveal solution</summary>

```yaml
# models/staging/census/_census__sources.yml

version: 2

sources:
  - name: raw_census
    description: >
      Indian census and demographic data. Loaded annually from government sources.
      Used to enrich blood bank data with population context (per-capita availability).
    database: blood_bank_db
    schema: raw_census

    loaded_at_field: _loaded_at
    freshness:
      warn_after:
        count: 30
        period: day
      error_after:
        count: 90
        period: day

    tables:
      - name: state_population
        description: >
          State-level population data from Census 2021. One row per state/UT.
          Used to calculate per-capita blood availability metrics.
        columns:
          - name: state_code
            description: "2-letter ISO state code (e.g., 'MH' for Maharashtra)"
            tests:
              - unique
              - not_null

          - name: state_name
            description: "Full state or union territory name"
            tests:
              - unique
              - not_null

          - name: population_2021
            description: "Total population from Census 2021 (stored as TEXT, cast in staging)"

          - name: area_sq_km
            description: "Geographic area in square kilometers (stored as TEXT)"

          - name: literacy_rate
            description: "Literacy rate as a percentage (stored as TEXT, e.g., '83.5')"

          - name: _loaded_at
            description: "Metadata: Timestamp when this data was loaded into the warehouse"
```

</details>

---

### 🏋️ Exercise 3: Debug This Staging Model

The following staging model has **5 bugs**. Find and fix them all:

```sql
-- models/staging/blood_bank/stg_blood_bank__hospitals_buggy.sql

WITH source_data AS (

    SELECT * FROM raw_blood_bank.blood_inventory_raw   -- Bug 1

),

cleaned AS (

    SELECT
        hospitalCode AS hospital_id,                    -- Bug 2
        TRIM(hospitalname) AS hospital_name,
        TRIM(hospitalType) as hospital_type,            -- Bug 3
        CAST(entrydate AS TIMESTAMP) AS last_updated_at,
        offline AS is_offline                           -- Bug 4
    FROM source_data

)

SELECT * FROM cleaned                                   -- Bug 5
```

<details>
<summary>Click to reveal all 5 bugs and fixes</summary>

| Bug # | Problem | Fix |
|-------|---------|-----|
| 1 | **Hardcoded table reference** instead of `source()` | Use `{{ source('raw_blood_bank', 'blood_inventory_raw') }}` |
| 2 | **No type casting** on hospitalCode | Use `CAST(hospitalCode AS INTEGER) AS hospital_id` |
| 3 | **No value standardization** on hospital_type | Use a `CASE` statement to standardize 'Govt.', 'Private', etc. |
| 4 | **No type casting on boolean** — offline is TEXT '0'/'1' | Use `CASE WHEN offline = '1' THEN TRUE ELSE FALSE END AS is_offline` |
| 5 | **No filtering** of invalid records | Add `WHERE hospitalCode IS NOT NULL AND hospitalCode != '-'` |

**Fixed version:**

```sql
WITH source_data AS (
    SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
),

cleaned AS (
    SELECT
        CAST(hospitalCode AS INTEGER) AS hospital_id,
        TRIM(hospitalname) AS hospital_name,
        CASE TRIM(hospitalType)
            WHEN 'Govt.' THEN 'government'
            WHEN 'Private' THEN 'private'
            WHEN 'Charitable/Vol' THEN 'charitable'
            ELSE 'unknown'
        END AS hospital_type,
        CAST(entrydate AS TIMESTAMP) AS last_updated_at,
        CASE WHEN offline = '1' THEN TRUE ELSE FALSE END AS is_offline
    FROM source_data
    WHERE hospitalCode IS NOT NULL
      AND TRIM(hospitalCode) != '-'
      AND hospitalCode ~ '^[0-9]+$'
)

SELECT * FROM cleaned
```

</details>

---

### 🏋️ Exercise 4: Tracing the DAG

Given the following models, draw the dependency graph:

```sql
-- Model A
SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

-- Model B
SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

-- Model C
SELECT * FROM {{ ref('stg_blood_bank__hospitals') }}  -- Model A

-- Model D
SELECT 
    a.*, b.*
FROM {{ ref('stg_blood_bank__hospitals') }} a         -- Model A
JOIN {{ ref('stg_blood_bank__components') }} b        -- Model B
    ON a.hospital_id = b.hospital_id
```

<details>
<summary>Click to reveal DAG</summary>

```
                raw_blood_bank.blood_inventory_raw
                (SOURCE)
                     │
          ┌──────────┼──────────┐
          ▼                     ▼
    Model A:                Model B:
    stg_hospitals           stg_components
          │                     │
          ├─────────┐           │
          ▼         │           │
    Model C:        └─────┬─────┘
    (some model               │
     using only A)            ▼
                        Model D:
                        fct_blood_availability
                        (joins A + B)
```

**Execution order:**
1. `raw_blood_bank.blood_inventory_raw` (already exists — source)
2. `stg_blood_bank__hospitals` (Model A) — depends on source
3. `stg_blood_bank__components` (Model B) — depends on source
4. Model C — depends on Model A
5. Model D — depends on Models A AND B (runs after both are done)

Models A and B can run **in parallel** (they have no dependency on each other).

</details>

---

### 🏋️ Exercise 5: Build a Complete Staging Pipeline

Starting from scratch, build the following:

1. Create `_blood_bank__sources.yml` with one source and one table
2. Create `stg_blood_bank__hospitals.sql` with at least 6 columns
3. Create `_blood_bank__models.yml` with descriptions and tests
4. Run `dbt run --select staging.*`
5. Run `dbt test --select staging.*`
6. Run `dbt source freshness`
7. Verify the output in PostgreSQL

**Verification checklist:**

| Step | Command | Expected Result |
|------|---------|----------------|
| 1 | `dbt compile` | No errors |
| 2 | `dbt run --select staging.*` | All models created successfully |
| 3 | `dbt test --select staging.*` | All tests passed |
| 4 | `dbt source freshness` | PASS or WARN (not ERROR) |
| 5 | `psql -c "SELECT COUNT(*) FROM staging.stg_blood_bank__hospitals"` | > 0 rows |

---

## 10. Common Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Doing Too Much in Staging

```sql
-- ❌ BAD: Business logic in staging
SELECT
    hospital_id,
    CASE 
        WHEN available_units = 0 THEN 'OUT_OF_STOCK'   -- Business logic!
        WHEN available_units < 5 THEN 'CRITICAL'        -- Belongs in marts!
    END AS stock_status
FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
```

```sql
-- ✅ GOOD: Just clean the data, let marts handle business logic
SELECT
    CAST(hospitalCode AS INTEGER) AS hospital_id,
    CAST(count AS INTEGER) AS available_units      -- Just cast, no classification
FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
```

### ❌ Anti-Pattern 2: Joining in Staging

```sql
-- ❌ BAD: Joining multiple sources in staging
SELECT *
FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }} a
JOIN {{ source('raw_census', 'state_population') }} b           -- Wrong layer!
    ON a.State = b.state_name
```

### ❌ Anti-Pattern 3: Hardcoding Source References

```sql
-- ❌ BAD
SELECT * FROM raw_blood_bank.blood_inventory_raw

-- ✅ GOOD
SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}
```

### ❌ Anti-Pattern 4: No Deduplication

```sql
-- ❌ BAD: Raw data may have duplicates
SELECT * FROM {{ source('raw_blood_bank', 'blood_inventory_raw') }}

-- ✅ GOOD: Deduplicate with ROW_NUMBER()
-- (see the hospital model above for the full pattern)
```

### ❌ Anti-Pattern 5: No Column Documentation

```yaml
# ❌ BAD: No descriptions
models:
  - name: stg_blood_bank__hospitals
    columns:
      - name: hospital_id
      - name: hospital_name

# ✅ GOOD: Descriptive documentation
models:
  - name: stg_blood_bank__hospitals
    description: "Cleaned hospital entities. One row per unique hospital."
    columns:
      - name: hospital_id
        description: "Unique integer ID (cast from hospitalCode). Primary key."
        tests:
          - unique
          - not_null
```

---

## 11. Key Takeaways

| Concept | One-Line Summary |
|---------|-----------------|
| **Sources** | YAML declarations of your raw/Bronze tables. Use `{{ source() }}` to reference them. |
| **source() function** | `{{ source('source_name', 'table_name') }}` — resolves to the full table path. |
| **Source Freshness** | `dbt source freshness` checks if your raw data is stale using `loaded_at_field`. |
| **Staging Models** | Clean, cast, rename, deduplicate. One model per entity. No business logic. |
| **Naming Convention** | `stg_{source}__{entity}` with double underscore. |
| **CTE Pattern** | `WITH source_data AS (...), cleaned AS (...) SELECT ... FROM cleaned` |
| **Deduplication** | `ROW_NUMBER() OVER (PARTITION BY key ORDER BY ts DESC) = 1` |
| **Schema YAML** | `_models.yml` files document columns and define tests. |
| **Materialization** | Staging models should be **views** (always fresh, zero storage). |
| **Anti-Patterns** | No business logic, no joins, no hardcoded refs, always deduplicate. |

---

## 🔜 Next Module

**[Module 4: Gold Marts and Data Testing →](./04_Gold_Marts_and_Data_Testing.md)**

In the next module, you'll:
- Build fact tables (`fct_`) and dimension tables (`dim_`)
- Use the `{{ ref() }}` function to link models together
- Master the DAG (Directed Acyclic Graph)
- Write comprehensive data quality tests
- Build the complete Gold layer for the blood bank project

---

> **📝 Author's Note**: If you can look at any raw table and immediately sketch out the staging model in your head — column renames, type casts, deduplication, and filters — you've internalized this module. Practice with your own datasets. The pattern is always the same.
