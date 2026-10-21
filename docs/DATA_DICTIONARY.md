# eRaktKosh Blood Lakehouse: Data Dictionary

**Context**: Academic Research Project  
**Department**: Academic Research Team  
**Project**: eRaktKosh Blood Lakehouse (Academic Mini Project — 800 Marks)  
**Storage Engine**: DuckDB (Columnar In-Process OLAP)  
**Transformation Framework**: dbt Core (`dbt-duckdb`)  

---

## 1. Architectural Overview & Medallion Layers

The **eRaktKosh Blood Lakehouse** utilizes a three-tier **Medallion Architecture** to guarantee data lineage, auditability, schema enforcement, and zero data fabrication:

```
[ eRaktKosh Public API ]
         │ (aiohttp crawler)
         ▼
[ Immutable Parquet Landing: data/landing/*.parquet ]
         │ (SHA-256 Checksum Verified)
         ▼
┌────────────────────────────────────────────────────────┐
│ DuckDB Storage: blood_warehouse.duckdb                 │
│                                                        │
│   [ Bronze Layer: Append-Only Raw Ingestion ]          │
│   └── bronze.raw_inventory                             │
│         │                                              │
│   [ Silver Layer: Cleaned, Unnested & Normalized ]     │
│   ├── silver.stg_blood_banks                           │
│   └── silver.stg_inventory_components                 │
│         │                                              │
│   [ Gold Layer: Dimensional Marts & Analytics ]        │
│   ├── gold.dim_blood_banks                             │
│   ├── gold.fct_stock_current                           │
│   ├── gold.fct_stock_snapshot                          │
│   ├── gold.mart_reliability_score                     │
│   ├── gold.mart_district_status                        │
│   ├── gold.mart_stock_change                           │
│   └── gold.mart_rare_blood_availability                │
└────────────────────────────────────────────────────────┘
         │ (Atomic Verification & Copy)
         ▼
[ Serving Database: serving.duckdb (Read-Only to FastAPI) ]
```

---

## 2. Bronze Layer (Raw Ingestion)

### Table: `bronze.raw_inventory`
* **Purpose**: Raw, append-only landing table directly ingested from timestamped Parquet batches. Preserves the full upstream API response without loss of structural or string precision.
* **Materialization**: `table` (Append-Only)
* **Storage Location**: `blood_warehouse.duckdb` -> schema `bronze`
* **Grain**: One record per reporting facility per ingestion run (`run_id`, `hospital_code`).

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description | Sample Value |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `run_id` | `VARCHAR` | No | Format: `run_YYYYMMDD_HHMMSS_hash` | Unique execution run identifier | `run_20261014_180000_a1b2c3` |
| `scraped_at` | `TIMESTAMP` | No | ISO 8601 UTC timestamp | Time the async crawler fetched the record | `2026-10-14 18:00:00` |
| `hospital_code` | `BIGINT` | No | Primary Identifier in eRaktKosh | Official facility ID assigned by MoHFW | `24125` |
| `hospital_name` | `VARCHAR` | No | Length > 0 | Registered name of the blood facility | `Indian Red Cross Society Blood Bank` |
| `state_name` | `VARCHAR` | No | Valid Indian State/UT | Name of the state or union territory | `Gujarat` |
| `district_name` | `VARCHAR` | No | Valid District | Administrative district name | `Anand` |
| `hospital_type` | `VARCHAR` | Yes | Category | Ownership type (`Govt`, `Private`, `Red Cross`, etc.) | `Charitable` |
| `facility_type` | `VARCHAR` | Yes | Classification | Level of service (`Blood Bank`, `Blood Storage Unit`) | `Blood Bank` |
| `hospital_contact`| `VARCHAR`| Yes | Raw Phone/Mobile string | Telephone string as provided by source | `02692-223344 / 9825012345` |
| `hospital_address`| `VARCHAR`| Yes | Text address | Physical address string | `Station Road, Near Anand Railway Station` |
| `entry_date_raw` | `VARCHAR` | Yes | Unparsed date string | Raw portal update timestamp string | `14-Oct-2026 17:45` |
| `components_raw` | `VARCHAR` | Yes | JSON String | Raw nested JSON array of blood components & units | `[{"component":"PRBC","group":"O+","units":12}]` |
| `raw_payload` | `VARCHAR` | Yes | JSON String | Complete verbatim JSON response object | `{"id":24125,"name":"..."}` |

---

## 3. Silver Layer (Cleaned, Unnested & Normalized)

### View: `silver.stg_blood_banks`
* **Purpose**: Cleaned facility dimension staging model. Sanitizes phone strings, trims whitespace, standardizes state/district naming, and resolves geospatial coordinates from the district centroid gazetteer.
* **Materialization**: `view`
* **Grain**: One record per distinct blood facility (`hospital_code`).

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description | Sample Value |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `hospital_code` | `BIGINT` | No | `unique`, `not_null` | Unique blood bank facility identifier | `24125` |
| `hospital_name` | `VARCHAR` | No | `not_null` | Cleaned and trimmed hospital/bank name | `Indian Red Cross Society Anand` |
| `state_name` | `VARCHAR` | No | `not_null` | Standardized Indian State name | `Gujarat` |
| `district_name` | `VARCHAR` | No | `not_null` | Standardized Indian District name | `Anand` |
| `hospital_type` | `VARCHAR` | Yes | Defaults to `'Government'` if null | Facility ownership category | `Red Cross` |
| `facility_type` | `VARCHAR` | Yes | Defaults to `'Blood Bank'` | Facility operational classification | `Blood Bank` |
| `hospital_contact`| `VARCHAR`| Yes | Cleaned contact string | Phone number with clean formatting | `02692-223344` |
| `hospital_address`| `VARCHAR`| Yes | Cleaned address | Full address string without irregular control chars | `Station Road, Anand 388001` |
| `latitude` | `DOUBLE` | No | Indian Bounding Box `[6.0, 38.0]` | Approximate latitude (district centroid) | `22.5645` |
| `longitude` | `DOUBLE` | No | Indian Bounding Box `[68.0, 98.0]` | Approximate longitude (district centroid) | `72.9289` |
| `precision` | `VARCHAR` | No | `IN ('district', 'exact')` | Geographic precision disclaimer | `district` |
| `source_updated_at`| `TIMESTAMP`| Yes | Converted to UTC Timestamp | Parsed portal timestamp from `entry_date_raw` | `2026-10-14 17:45:00` |

---

### View: `silver.stg_inventory_components`
* **Purpose**: Atomic component inventory staging view. Explodes the nested JSON array from `components_raw` into individual rows and normalizes blood group and component names via the strict `normalize_blood_group` macro.
* **Materialization**: `view`
* **Grain**: One row per facility, blood group, component, and scrape timestamp (`hospital_code`, `component_name`, `blood_group`, `scraped_at`).

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description | Sample Value |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `hospital_code` | `BIGINT` | No | `not_null`, References `stg_blood_banks` | Facility identifier | `24125` |
| `component_name` | `VARCHAR` | No | `not_null`, Canonical Component | Standardized component (PRBC, Whole Blood, FFP, etc.) | `Packed Red Blood Cells` |
| `blood_group` | `VARCHAR` | No | `not_null`, `accepted_values` | Strictly normalized blood group | `O-` |
| `units` | `INTEGER` | No | `not_null`, `units >= 0` | Available verified units in stock | `8` |
| `source_updated_at`| `TIMESTAMP`| Yes | UTC Timestamp | Source portal last-modified date | `2026-10-14 17:45:00` |
| `scraped_at` | `TIMESTAMP` | No | `not_null` | Pipeline crawl timestamp | `2026-10-14 18:00:00` |

#### Canonical Blood Group Accepted Values
The dbt contract enforces the following ten valid blood group categories:
`'O+'`, `'O-'`, `'A+'`, `'A-'`, `'B+'`, `'B-'`, `'AB+'`, `'AB-'`, `'Bombay (Oh+)'`, `'Bombay (Oh-)'`.

---

## 4. Gold Layer (Dimensional Marts & Analytics)

### Dimension: `gold.dim_blood_banks`
* **Purpose**: Facility dimension table serving as the central entity for geospatial lookups, ownership filtering, and facility metadata.
* **Materialization**: `table`
* **Grain**: One record per distinct blood bank (`hospital_code`).

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description |
| :--- | :--- | :---: | :--- | :--- |
| `hospital_code` | `BIGINT` | No | `unique`, `not_null`, Primary Key | Unique facility code |
| `hospital_name` | `VARCHAR` | No | `not_null` | Cleaned facility name |
| `state_name` | `VARCHAR` | No | `not_null` | State name |
| `district_name` | `VARCHAR` | No | `not_null` | District name |
| `hospital_type` | `VARCHAR` | No | `not_null` | Ownership category |
| `facility_type` | `VARCHAR` | No | `not_null` | Service level |
| `hospital_contact`| `VARCHAR`| Yes | Telephone/Mobile | Primary contact number |
| `hospital_address`| `VARCHAR`| Yes | Address text | Full physical address |
| `latitude` | `DOUBLE` | No | `not_null` | Latitude (district centroid) |
| `longitude` | `DOUBLE` | No | `not_null` | Longitude (district centroid) |
| `precision` | `VARCHAR` | No | `not_null` | Geocoding precision label (`district`) |
| `source_updated_at`| `TIMESTAMP`| Yes | Source portal time | Most recent stock timestamp reported |

---

### Fact: `gold.fct_stock_current`
* **Purpose**: The core operational search mart. Contains the most recent stock level for every facility, component, and blood group. Powers the emergency inventory search API with sub-millisecond execution.
* **Materialization**: `table`
* **Grain**: `(hospital_code, component_name, blood_group)`.

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description | Sample Value |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `hospital_code` | `BIGINT` | No | `not_null` | Blood bank facility code | `24125` |
| `component_name` | `VARCHAR` | No | `not_null` | Component name | `Packed Red Blood Cells` |
| `blood_group` | `VARCHAR` | No | `not_null` | Normalized blood group | `O-` |
| `units` | `INTEGER` | No | `not_null`, `>= 0` | Available verified units | `14` |
| `source_updated_at`| `TIMESTAMP`| Yes | Source update date | Facility portal update timestamp | `2026-10-14 17:45:00` |
| `scraped_at` | `TIMESTAMP` | No | `not_null` | Pipeline crawl timestamp | `2026-10-14 18:00:00` |

---

### Fact: `gold.fct_stock_snapshot`
* **Purpose**: Append-only historical fact table storing daily inventory snapshots. Adheres strictly to the **Zero Fake Data Contract**: contains no synthetic or backfilled records. History accumulates organically with each scheduled execution.
* **Materialization**: `incremental` (Unique Key: `[hospital_code, component_name, blood_group, snapshot_date]`)
* **Grain**: One record per facility, component, blood group, and calendar date.

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description |
| :--- | :--- | :---: | :--- | :--- |
| `hospital_code` | `BIGINT` | No | `not_null` | Facility code |
| `component_name` | `VARCHAR` | No | `not_null` | Blood component name |
| `blood_group` | `VARCHAR` | No | `not_null` | Normalized blood group |
| `units` | `INTEGER` | No | `not_null`, `>= 0` | Quantity recorded on date |
| `snapshot_date` | `DATE` | No | `not_null` | Calendar date of snapshot |
| `scraped_at` | `TIMESTAMP` | No | `not_null` | Precise ingestion timestamp |

---

### Mart: `gold.mart_reliability_score`
* **Purpose**: Deterministic 0-100 facility credibility scoring model designed to prevent users from travelling to facilities with abandoned or outdated records. Evaluated purely inside SQL across three transparent pillars:
  1. **Freshness (50 Points)**:
     - Updated $\le 24$ hours: **50 pts**
     - Updated $> 24$ and $\le 48$ hours: **35 pts**
     - Updated $> 48$ and $\le 168$ hours (7 days): **15 pts**
     - Updated $> 7$ days or null: **0 pts**
  2. **Valid Contact Information (25 Points)**:
     - Facility provides non-null phone with $\ge 8$ numeric digits: **25 pts**
     - No valid contact phone: **0 pts**
  3. **Stock Completeness (25 Points)**:
     - Reports $\ge 4$ distinct blood groups with non-zero stock: **25 pts**
     - Reports 1 to 3 distinct groups with positive stock: **15 pts**
     - Reports 0 units across all groups: **0 pts**
* **Materialization**: `table`
* **Grain**: One record per facility (`hospital_code`).

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description |
| :--- | :--- | :---: | :--- | :--- |
| `hospital_code` | `BIGINT` | No | `unique`, `not_null` | Blood bank identifier |
| `freshness_score`| `INTEGER` | No | `BETWEEN 0 AND 50` | Score based on hours since last update |
| `contact_score` | `INTEGER` | No | `IN (0, 25)` | Score based on phone validity |
| `completeness_score`| `INTEGER`| No | `IN (0, 15, 25)` | Score based on reported stock breadth |
| `reliability_score`| `INTEGER`| No | `BETWEEN 0 AND 100` | Aggregate reliability score |
| `reliability_tier` | `VARCHAR`| No | `accepted_values: HIGH, MODERATE, LOW` | Tier label: `HIGH` ($\ge 75$), `MODERATE` ($45-74$), `LOW` ($< 45$) |

---

### Mart: `gold.mart_district_status`
* **Purpose**: Aggregates component-level inventory at the administrative district grain. Classifies supply health into actionable emergency triage categories.
* **Materialization**: `table`
* **Grain**: `(state_name, district_name, component_name, blood_group)`.

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description |
| :--- | :--- | :---: | :--- | :--- |
| `state_name` | `VARCHAR` | No | `not_null` | State name |
| `district_name` | `VARCHAR` | No | `not_null` | District name |
| `component_name` | `VARCHAR` | No | `not_null` | Blood component |
| `blood_group` | `VARCHAR` | No | `not_null` | Blood group |
| `total_units` | `BIGINT` | No | `not_null`, `>= 0` | Total available units across all facilities in district |
| `reporting_banks`| `BIGINT` | No | `not_null`, `>= 0` | Number of facilities reporting inventory |
| `status` | `VARCHAR` | No | `accepted_values: SHORTAGE, LOW_STOCK, ADEQUATE` | Triage label: `SHORTAGE` (0 units), `LOW_STOCK` ($1-5$ units), `ADEQUATE` ($> 5$ units) |

---

### Mart: `gold.mart_rare_blood_availability`
* **Purpose**: Filtered mart specifically indexing life-critical rare blood phenotypes, including Bombay Blood Group (`Bombay (Oh+)`, `Bombay (Oh-)`) and Rh-negative blood groups (`O-`, `A-`, `B-`, `AB-`).
* **Materialization**: `view`
* **Grain**: One record per rare stock entry per facility.

| Column Name | DuckDB Type | Nullable | Constraints / Checks | Description |
| :--- | :--- | :---: | :--- | :--- |
| `hospital_code` | `BIGINT` | No | `not_null` | Facility code |
| `hospital_name` | `VARCHAR` | No | `not_null` | Blood bank name |
| `state_name` | `VARCHAR` | No | `not_null` | State name |
| `district_name` | `VARCHAR` | No | `not_null` | District name |
| `hospital_contact`| `VARCHAR`| Yes | Telephone/Mobile | Contact number |
| `component_name` | `VARCHAR` | No | `not_null` | Component name |
| `blood_group` | `VARCHAR` | No | `not_null` | Rare blood group category |
| `units` | `INTEGER` | No | `not_null`, `units > 0` | Units currently available |
| `reliability_score`| `INTEGER`| Yes | `0-100` | Facility reliability rating |
| `source_updated_at`| `TIMESTAMP`| Yes | UTC Timestamp | Last update timestamp |

---

## 5. dbt Quality Contracts & Assertions

All models within `blood_warehouse.duckdb` are enforced via automated dbt schema tests defined in `dbt/models/schema.yml`.

### Summary of Data Quality Rules:
1. **Primary Key Uniqueness**: `unique` tests on `dim_blood_banks.hospital_code`, `stg_blood_banks.hospital_code`, and `mart_reliability_score.hospital_code`.
2. **Mandatory Fields**: `not_null` tests on geographic attributes (`state_name`, `district_name`), facility names, components, and blood groups.
3. **Domain Value Integrity**: `accepted_values` tests on `stg_inventory_components.blood_group` (10 groups) and `mart_reliability_score.reliability_tier` (`HIGH`, `MODERATE`, `LOW`).
4. **Relational Referential Integrity**: Foreign key checks ensuring all inventory rows link to a valid facility in `dim_blood_banks`.
5. **Non-Negative Value Assertions**: Custom SQL tests ensuring inventory unit counts never drop below zero.

*All 35 automated schema and contract tests are executed before any database release.*
