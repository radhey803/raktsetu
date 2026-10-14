# BloodGrid Lakehouse Data Dictionary

This document details the schema definitions, grains, and business metrics materialized within `blood_warehouse.duckdb` and served via `serving.duckdb`.

---

## 1. Bronze Layer (Landing & Raw Ingestion)

### Table: `bronze.raw_inventory`
- **Description**: Append-only ingestion table loaded directly from immutable Parquet files. Preserves raw payload without CSV serialization loss.
- **Grain**: One row per reporting blood facility per pipeline execution.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `run_id` | `VARCHAR` | NOT NULL | Unique execution run identifier (e.g. `run_20261014_180000_a1b2c3`) |
| `scraped_at` | `TIMESTAMP` | NOT NULL | Timestamp when the scraper executed |
| `hospital_code` | `BIGINT` | NOT NULL | Unique national facility code assigned by eRaktKosh |
| `hospital_name` | `VARCHAR` | NOT NULL | Registered commercial/hospital name |
| `state_name` | `VARCHAR` | NOT NULL | Indian State / UT |
| `district_name` | `VARCHAR` | NOT NULL | Indian Administrative District |
| `hospital_type` | `VARCHAR` | NULLABLE | Facility ownership: `Government`, `Private`, `Red Cross`, `Charitable` |
| `facility_type` | `VARCHAR` | NULLABLE | Classification: `Blood Bank`, `Blood Storage Unit (BSU)` |
| `hospital_contact` | `VARCHAR` | NULLABLE | Phone/landline contact string |
| `hospital_address` | `VARCHAR` | NULLABLE | Physical address text |
| `entry_date_raw` | `VARCHAR` | NULLABLE | Portal string date (e.g. `14-Oct-2026 18:30`) |
| `components_raw` | `VARCHAR` | NULLABLE | Raw JSON string of available blood components and units |
| `raw_payload` | `VARCHAR` | NULLABLE | Complete untouched raw JSON facility object |

---

## 2. Silver Layer (Cleaned & Unnested Views)

### View: `silver.stg_blood_banks`
- **Description**: Cleaned facility dimension staging view with normalized names, contact sanitization, and geocoded coordinates.
- **Grain**: One row per distinct blood bank facility.

### View: `silver.stg_inventory_components`
- **Description**: Unnested component inventory staging model. Transforms nested JSON component blobs into granular stock records.
- **Grain**: `(hospital_code, component_name, blood_group, scraped_at)`

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `hospital_code` | `BIGINT` | NOT NULL | Reference to `dim_blood_banks.hospital_code` |
| `component_name` | `VARCHAR` | NOT NULL | Standardized component (PRBC, Whole Blood, Platelet Concentrate, Fresh Frozen Plasma, Cryoprecipitate, Single Donor Platelet) |
| `blood_group` | `VARCHAR` | NOT NULL | Strictly normalized group: `O+`, `O-`, `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `Bombay (Oh+)`, `Bombay (Oh-)` |
| `units` | `INTEGER` | NOT NULL, >= 0 | Numeric available stock units |
| `source_updated_at`| `TIMESTAMP` | NULLABLE | Timestamp reported by the facility |
| `scraped_at` | `TIMESTAMP` | NOT NULL | Pipeline crawl timestamp |

---

## 3. Gold Layer (Business Marts & Dimensions)

### Dimension: `gold.dim_blood_banks`
- **Description**: SCD Type 2 facility dimension maintaining historical tracking of address and phone number updates.
- **Grain**: One row per facility state version.

### Mart: `gold.fct_stock_current`
- **Description**: Latest stock level per facility, component, and blood group. Powering the emergency search API.
- **Grain**: `(hospital_code, component_name, blood_group)`

### Mart: `gold.fct_stock_snapshot`
- **Description**: Append-only incremental daily snapshot mart. Contains zero synthetic rows. Real history accumulates daily.
- **Grain**: `(hospital_code, component_name, blood_group, snapshot_at)`

### Mart: `gold.mart_reliability_score`
- **Description**: 0-100 facility data reliability rating calculated on three deterministic pillars:
  - **Freshness (50 pts)**: Updated < 24h = 50 pts; 24-48h = 35 pts; 48-168h = 15 pts; > 7 days = 0 pts.
  - **Valid Contact (25 pts)**: Valid phone string with >= 8 digits = 25 pts.
  - **Completeness (25 pts)**: Reports >= 4 blood groups with positive stock = 25 pts; 1-3 groups = 15 pts; 0 = 0 pts.
  - **Tiers**: `HIGH` (>= 75), `MEDIUM` (45-74), `LOW` (< 45).

### Mart: `gold.mart_district_status`
- **Description**: Aggregate district-level supply metrics, total reporting banks, total stock units by component, and shortage alert status (`SHORTAGE`, `LOW_STOCK`, `ADEQUATE`).

### Mart: `gold.mart_stock_change`
- **Description**: Rolling 7-day inventory consumption rate and estimated days-of-cover. Only computed when $\ge 7$ real daily snapshots exist.

### Mart: `gold.mart_rare_blood_availability`
- **Description**: Rapid filter for Bombay Blood Group (`Oh+`, `Oh-`) and rare negative groups (`O-`, `AB-`, `A-`, `B-`).
