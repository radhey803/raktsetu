# ADR-002: dbt Incremental Mart Design & Elimination of Synthetic Snapshot Manager

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Principal Data Engineer, Senior Full-Stack Engineer

---

## Context & Problem Statement
Prior versions of the repository used an ad-hoc Python script (`snapshot_manager.py`) to build daily stock history. However:
1. It generated synthetic/seeded historical records to mock an 8-day history, violating integrity rules.
2. The logic bypassed the dbt transformation graph and data testing framework.
3. Column parsing errors occurred during CSV serialization and deserialization.

---

## Decision
1. **Retire `snapshot_manager.py`**: All custom Python snapshot logic was decommissioned.
2. **Implement dbt Gold Mart `fct_stock_snapshot`**:
   - Built directly on top of `silver.stg_inventory_components`.
   - Granularity: `(hospital_code, component_name, blood_group, snapshot_at)`.
   - Incremental strategy: Append-only partition filtering on `scraped_at > (select max(snapshot_at) from {{ this }})`.
3. **Data Quality Gate**: dbt tests enforce unique composite keys, non-null guarantees, positive integer units, and source freshness prior to publishing.

---

## Consequences
- **Positive**:
  - Zero synthetic data: Real history begins strictly from real scrapes.
  - Snapshot logic is version-controlled and documented within dbt DAG.
  - Downstream models (`mart_stock_change`, `mart_district_status`) consume validated warehouse models.
- **Negative**:
  - Full refresh builds require reloading landing Parquet into Bronze to replay history.
