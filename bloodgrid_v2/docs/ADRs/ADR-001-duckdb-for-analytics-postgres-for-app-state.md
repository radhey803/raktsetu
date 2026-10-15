# ADR-001: Hybrid Storage Architecture — DuckDB for Analytics and PostgreSQL for Application State

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Principal Data Engineer, Senior Full-Stack Engineer, Product Lead

---

## Context & Problem Statement
BloodGrid requires two distinct data access patterns:
1. **High-throughput OLAP Analytics**: Querying ~4,680+ facilities, 59,000+ unnested component records, aggregations across 781 districts, and historical daily stock snapshots with sub-10ms response times.
2. **Transactional OLTP Application State**: User authentication (passwords, JWTs), developer API keys with prefix hashes, alert rule triggers, event logs, billing subscription states, and Razorpay webhook receipts requiring ACID guarantees and row-level locks.

Initial implementations either attempted to store application users inside DuckDB (risking file lock contention during pipeline writes) or planned a heavy Postgres deployment for everything (costly for analytical window queries on snapshots).

---

## Decision Drivers
- **Zero-Downtime Serving**: The backend API must continue serving search requests while scheduled pipeline crawls build fresh datasets.
- **Cost Minimization**: Infrastructure operating costs must remain below $10/month to allow profitable operation at low subscription volumes.
- **Concurrency Safety**: DuckDB supports multiple concurrent readers, but only a single writer. API workers must never lock the analytical store.
- **Portability**: The analytical store must be publishable as an immutable artifact to S3/Cloudflare R2.

---

## Decision
We adopted a **Hybrid Storage Architecture**:
1. **DuckDB (`serving.duckdb`) for Analytical Serving**:
   - Stores Bronze landing tables, Silver cleaned views, and Gold business marts (`dim_blood_banks`, `fct_stock_current`, `fct_stock_snapshot`, `mart_district_status`, `mart_reliability_score`, `mart_stock_change`, `mart_rare_blood_availability`).
   - The scheduled pipeline builds into `blood_warehouse.duckdb` and atomically swaps a verified snapshot to `serving.duckdb`.
   - The FastAPI backend opens `serving.duckdb` strictly with `read_only=True`.
2. **PostgreSQL (or managed relational store) for Application State**:
   - Stores users, sessions, hashed API keys, subscription records, and alert subscriptions.
   - Handled via standard SQL migrations and relational foreign-key constraints.

---

## Consequences
- **Positive**:
  - Analytical searches return in < 5ms without complex indexing or indexing overhead.
  - Zero locking conflicts between pipeline ingestion and API query traffic.
  - Serving database can be archived to R2/S3 as a single compressed file and downloaded by edge workers.
- **Negative**:
  - Two database engines in production; requires separate backup procedures (duckdb atomic copy vs. `pg_dump`).
  - No direct SQL joins between app users and warehouse inventory; crossed at the API service layer.
