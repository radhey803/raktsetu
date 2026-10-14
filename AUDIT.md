# BloodGrid: Technical & Architectural Audit Report (Phase 0)

**Date**: 2026-10-15  
**Auditor**: Principal Data Engineer & Senior Full-Stack Architect  
**Scope**: Repository structure, eRaktKosh ingestion pipeline, DuckDB warehouse, dbt transformations, FastAPI backend, Leaflet/Vanilla frontend, security, and deployment readiness.

---

## 1. Executive Summary

The project originated as an experimental "eRaktKosh Blood Lakehouse" built to demonstrate high-speed scraping and local DuckDB + dbt analytical modeling. While the core scraper is exceptionally fast (~26s for ~4,681 facilities across 781 districts) and the UI styling has been refined to a clean health-tech aesthetic, the system possesses critical architectural blockers and data integrity flaws that currently prevent it from being an enterprise-grade, deployable, and sellable product.

The primary blockers include **413,098 synthetic/seeded historical snapshot rows** masquerading as genuine hospital inventory history, **fragile regex-based string extraction** of blood availability, **DuckDB concurrency file locks**, and **approximate district centroids** presented on the interactive map without precision indicators.

This audit maps every finding categorized by severity and defines the remediation executed in Phase 0 and subsequent phases.

---

## 2. Findings Catalog

### 🚨 Blocker Findings

| ID | Component | Finding | Impact | Remediation Plan |
|---|---|---|---|---|
| **BLK-01** | `snapshot_manager.py` / `blood_warehouse.duckdb` | **413,098 Synthetic / Fake Snapshot Records**: `seed_historical_backfill_if_empty()` used `random.seed(42)` and `random.choice([-2, -1, 0, 1, 2])` to generate 7 fake days of historical data for demonstration. | Falsifies medical data and destroys trust. 7 out of 8 snapshot dates in DuckDB are fabricated. | **Purge all synthetic rows immediately.** Delete synthetic backfill code. Enforce strict rule: history begins with real scrapes only. UI displays transparent empty state until $\ge 2$ real snapshots exist. |
| **BLK-02** | `api.py` / `silver.stg_blood_inventory` | **Fragile Regex Stock Matching**: Component quantities and blood groups are matched via raw text regular expressions (`available_stock`, `components_raw`) rather than unnested structured columns. | False positives and negatives (e.g. Bombay group `Oh+` falsely matching `O+`, or `B+` matching `AB+`). | Implement `stg_inventory_components` in dbt Silver layer to unnest into `(hospital_code, component_name, blood_group, units, source_updated_at)` with a strict normalizer macro and unit tests. |
| **BLK-03** | `api.py` / DuckDB Storage | **DuckDB File Lock Concurrency Crash**: Simultaneous pipeline writes and API read queries resulted in `duckdb.IOException: Could not set lock on file`. A shadow database copy (`.blood_warehouse_shadow.duckdb`) was used as an ad-hoc band-aid. | Process deadlocks, corrupted file reads, or outdated cached shadows during pipeline runs. | Implement **atomic blue/green database swapping**: write pipeline builds to an isolated staging DuckDB (`serving_staging.duckdb`), validate quality gates, then atomically rename to `serving.duckdb`. API mounts `serving.duckdb` exclusively in `read_only=True` mode. |
| **BLK-04** | Pipeline / Orchestration | **Lack of Automated Scheduling & Staleness Protection**: Scraper and pipeline runs were manually triggered. When scraping paused, data silently aged without warning users. | Life-critical blood searchers could travel based on days-old or weeks-old stock data. | Create automated GitHub Actions cron running every 4 hours. Add a global UI stale-data warning banner if last successful sync exceeds 12 hours. Record metadata in `pipeline_runs` table. |

---

### ⚠️ Major Findings

| ID | Component | Finding | Impact | Remediation Plan |
|---|---|---|---|---|
| **MAJ-01** | `geo_coords.py` / Map | **Approximate Centroid Pins Presented as Facilities**: Blood bank pins use district-level centroid coordinates rather than real facility addresses. | Misleading navigation distances; users may believe a blood bank is located at a district center point. | Implement Nominatim geocoding with permanent caching (`geocode_cache`), 1 req/sec rate limit, precision tagging (`exact`, `street`, `district_centroid`), and visual legend indicators. |
| **MAJ-02** | `api.py` & `static/app.js` | **Hardcoded Credentials & Missing Config Management**: CARTO API key was hardcoded in client scripts; database paths were hardcoded in Python modules. No `.env.example` or unified settings. | Secret leakage risk, inability to configure environments across dev/staging/prod. | Introduce `bloodgrid.config.Settings` backed by `pydantic-settings`. Commit `.env.example` and add `.env` to `.gitignore`. Expose map tile configuration securely via API metadata endpoint. |
| **MAJ-03** | Repository Layout | **Code Duplication & Script Sprawl**: Multiple scrapers (`fast_scraper.py`, `scraper.py`, `async_scraper.py`, `scrape_targeted_anand.py`), ad-hoc test scripts (`test_anand_scrape.py`, `find_api.py`), and unused Node artifacts (`bundle.js`, `node_modules`). | High maintenance overhead, confusion over canonical entry points, bloated repository size. | Consolidate single canonical scraper in `src/bloodgrid/ingestion/scraper.py`. Remove all obsolete scripts and artifacts. Reorganize into structured Python package. |
| **MAJ-04** | Backend Architecture | **Monolithic API without Versioning or DI**: `api.py` combined routing, direct database execution, regex parsing, and static file serving in a single 316-line file with no OpenAPI schemas. | Cannot support tiered API monetization, rate limiting, or independent testing. | Refactor into modular routers (`/v1/banks`, `/v1/availability`, `/v1/history`, `/v1/shortages`, `/v1/rare`, `/v1/meta`), Pydantic v2 schemas, and dependency-injected database connections. |
| **MAJ-05** | Testing & Quality Assurance | **Zero Automated Test Coverage**: Only 7 default dbt not-null/unique tests existed. No pytest unit tests, integration tests, or API smoke tests. | Regressions in blood group normalization or scraper response handling go undetected. | Implement pytest suite with $\ge 80\%$ target coverage across normalizers, alert rules, and API endpoints, plus Playwright e2e verification. |

---

### ℹ️ Minor Findings

| ID | Component | Finding | Impact | Remediation Plan |
|---|---|---|---|---|
| **MIN-01** | Frontend Copy | **Inflated KPI Metrics**: Footer copy claimed "14,000+ records", whereas the real nationwide facility count is ~4,681. | Damaged credibility with healthcare professionals and enterprise partners. | Replace vanity numbers with truthful metrics: actual reporting blood centres (~4,681) and "Facilities updated in the last 24 hours". |
| **MIN-02** | Documentation | **Masterclass Course Notes Cluttering Source Tree**: Large dbt training documents (`DuckDB_and_dbt_duckdb_Masterclass.md`, `dbt_masterclass/`) lived in the root project tree. | Distracted from production documentation. | Moved into dedicated `docs/learning/` hierarchy; reserve root `docs/` for architecture, runbooks, and API specs. |
| **MIN-03** | Legal & Compliance | **Missing Disclaimers & DPDP Compliance**: No published Terms of Service, Privacy Policy (DPDP Act 2023 aligned), or clear medical disclaimer. | Legal exposure when launching commercially or collecting alert subscriptions. | Draft legally sound, DPDP-aligned privacy policy, disclaimers, and clear eRaktKosh MoHFW attribution across all pages. |

---

## 3. Phase 0 Cleanup Actions Completed

1. **Obsolete & Duplicate File Purge**:
   - Removed `fast_scraper.py`, `scrape_targeted_anand.py`, `test_anand_scrape.py`, `find_api.py`, `scraper.py`.
   - Removed `ahmedabad_blood_inventory.csv`, `test_api.json`, `paths.txt`, `de`, `demo.sql`.
   - Removed `bundle.js`, `analyze.js`, `package.json`, `package-lock.json`, `node_modules/`.
   - Removed duplicate database shadow files (`.blood_warehouse_shadow.duckdb`, `blood_project/dev.duckdb`).
   - Removed redundant stylesheet `static/styles.css` (identical to `static/style.css`).
2. **Documentation Relocation**:
   - Moved `dbt_masterclass/` and `DuckDB_and_dbt_duckdb_Masterclass.md` to `docs/learning/`.
   - Moved `project_features_and_architecture.md` to `docs/`.
3. **Directory Restructuring**:
   - Renamed `blood_project/` to `dbt/`.
   - Created `src/bloodgrid/` modules (`config`, `ingestion`, `warehouse`, `pipeline`, `api`, `alerts`, `geo`).
   - Created `web/` frontend source directory.
   - Initialized `tests/` (`unit`, `integration`, `e2e`, `fixtures`).
   - Initialized `.github/workflows/` (`ci.yml`, `pipeline.yml`, `deploy.yml`).
