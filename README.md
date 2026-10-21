<div align="center">

# eRaktKosh Blood Lakehouse

**National Blood Inventory Intelligence & Emergency Triage Decision Tool**  
*Academic Mini Project (800 Marks) • Academic Project*  
**Academic Research Project**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1+-FFF000.svg?logo=duckdb&logoColor=black)](https://duckdb.org)
[![dbt-duckdb](https://img.shields.io/badge/dbt-DuckDB-FF694B.svg?logo=dbt&logoColor=white)](dbt/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](src/bloodlake/api/main.py)
[![Pytest](https://img.shields.io/badge/Pytest-98%20Passed-brightgreen.svg)](tests/)
[![dbt Tests](https://img.shields.io/badge/dbt%20Tests-37%20Passed-brightgreen.svg)](dbt/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> *"eRaktKosh shows blood stock like a phone book. My system turns it into a decision tool: where to go, how much to trust the listing, what is running low, and how it changed over time."*

</div>

---

> [!IMPORTANT]
> **Source Attribution & Medical Disclaimer**:  
> Data sourced from eRaktKosh (Ministry of Health and Family Welfare, Govt. of India). Academic project for Academic Project at Academic Research Project; not an official government service.  
> **Medical Guidance**: Sourced from official NBTC India & WHO standards. Guidance only, not medical advice. Always call the blood bank to confirm bed-side availability before travelling.

---

## 📌 Problem Statement & Core Philosophy

Across India, finding blood in emergencies is hindered by information asymmetry:
1. **Passive Listing vs. Active Decision Support**: Existing portals list numbers without telling users if a facility updated recently, whether they have a working phone, or which compatible alternative donor groups could save the patient.
2. **False Confidence from Stale Data**: Relatives waste critical "golden hour" time travelling to facilities with records un-updated for 30+ days.
3. **Regex Collisions & Phenotype Traps**: Naive search scripts confuse `B+` inside `AB+` or misclassify life-critical `Bombay (Oh+)` as regular `O+`.
4. **Zero Fake Data Contract**: We strictly reject synthetic numbers or fabricated history. If a trend requires real historical snapshots that do not exist yet, we show an honest notice instead of generating fictional numbers.

---

## ⚡ The Modern Lakehouse Architecture

The **eRaktKosh Blood Lakehouse** integrates an asynchronous crawler with an in-process columnar lakehouse built on **DuckDB**, **dbt Core**, and **FastAPI**:

```mermaid
flowchart TD
    subgraph Ingestion ["1. Asynchronous Ingestion Layer"]
        EK[eRaktKosh Public Portal\n781 Administrative Districts] -->|Polite Async Scraper\nSemaphore: 10, Backoff| SCRAPER[src/bloodlake/scraper.py]
        SCRAPER -->|Immutable Parquet\n+ SHA-256 Checksum| LANDING[data/landing/*.parquet]
    end

    subgraph Lakehouse ["2. Storage & Transformation (DuckDB + dbt)"]
        LANDING -->|Raw Parquet Ingestion| BRONZE[(bronze.raw_blood_inventory\nAppend-Only)]
        BRONZE -->|dbt Staging Views| SILVER[(silver.stg_blood_banks\nsilver.stg_inventory_components)]
        SILVER -->|dbt Gold Dimensional Marts| GOLD[(gold.dim_blood_banks\ngold.fct_stock_current\ngold.fct_stock_snapshot\ngold.mart_reliability_score\ngold.mart_district_status\ngold.mart_rare_blood_availability\ngold.mart_stock_change)]
    end

    subgraph QualityGate ["3. Dual-Database Publish Gate"]
        GOLD --> DBT_TEST[37 dbt Data Tests\nUnique, Non-null, Accepted Values]
        DBT_TEST --> ANOMALY_TEST[Publish Gate:\nFacility Count >= 80% Baseline & Zero Failures]
        ANOMALY_TEST -->|Passed| ATOMIC_SWAP[Atomic Copy & Swap:\nblood_warehouse.duckdb -> serving.duckdb]
        ANOMALY_TEST -->|Failed| ABORT[Abort Publish & Log Alert\nKeep Last Good Serving DB]
    end

    subgraph Serving ["4. Analytical Serving & Interface"]
        ATOMIC_SWAP --> API[FastAPI High-Concurrency Backend]
        API --> ENDPOINTS[/api/v1/availability\n/api/v1/emergency\n/api/v1/shortages\n/api/v1/rare\n/api/v1/health/dashboard\n/api/v1/export/*]
        API --> UI[Clinical Vanilla Web App\nCarto Positron Tiles / Inline SVG Sprite / PWA]
    end
```

---

## 🚀 Key Real-Use-Case Decision Features

1. **Blood Bank Trust Score (0–100)**:  
   Proprietary 3-pillar formula: Freshness ($50\text{ pts}$), Valid Contact Phone ($25\text{ pts}$), and Component Completeness ($25\text{ pts}$). Categorized into `High` ($\ge 75$), `Medium` ($40-74$), and `Low` ($<40$). Low-trust facilities display an explicit warning callout: *"Low reliability, call to confirm before travelling."*
2. **Smart Emergency Mode & Compatibility Matrix**:  
   Input patient blood group and component. Resolves all WHO/NBTC compatible donor red cells, queries active stock, and ranks the top 5 facilities using an audited formula ($0.35F + 0.30T + 0.25U + 0.10D$) with plain-language explanations. Automatically issues clinical warnings for Rh-negative and Bombay ($Oh$) phenotypes.
3. **Nearest Bank by Distance & Geocoding**:  
   User-initiated HTML5 browser geolocation calculates Haversine great-circle distance in SQL. Fallback to 781 district centroids with deterministic non-overlapping offsets. Integrates with Nominatim geocoding under strict 1 req/sec rate limits and permanent DuckDB caching (`geocode_cache`).
4. **District Shortage Ranking & Rare Blood Radar**:  
   dbt model `mart_district_status` highlights districts facing severe component deficits, distinguishing between physical stockouts and non-reporting facilities. Rare Blood Radar triages nationwide Bombay phenotype and Rh-negative units with trust and freshness badges.
5. **Stock History, Trend & Rule-Based Risk Flags**:  
   Append-only snapshot tracking with a strict zero-fake-data policy. Evaluates consecutive falling demand (decreased across 3 snapshot intervals) and sudden drop-to-zero anomalies.
6. **Client-Side Donor Help & Gap Calculator**:  
   100% private, client-side questionnaire (age, weight, donation interval). Calculates next donation date (90 days male, 120 days female per NBTC 2020) and suggests local blood banks with shortages. Zero personal data transmitted or stored.
7. **Sharing & Excel-Compatible CSV Export**:  
   Search state synchronized directly in URL query parameters. One-click WhatsApp emergency dispatch card. CSV exports for availability and shortages formatted with UTF-8 BOM (`\ufeff`) for seamless opening in Microsoft Excel with MoHFW attribution headers.
8. **Data Health & Pipeline Dashboard**:  
   Site-wide stale data banner if the last sync is $>12$ hours old. Observability page showing sync freshness, facility count retention, stale states breakdown, and recent pipeline executions.
9. **Inclusive Accessibility & Offline PWA**:  
   Full WCAG AA contrast, 44px touch targets, screen-reader `aria-live` regions, and an installable PWA Service Worker (`web/sw.js`) with cached offline search replay.
10. **Clinical Aesthetic & Design System**:  
    Warm off-white canvas `#FBF8F6`, deep ink `#1A1214`, primary clinical red `#D21F3C`, refined serif headings, tabular numbers for all stock counts, Carto Positron map tiles, and zero emojis (100% inline SVG sprite with icon + text status indicators).

---

## 📂 Project Structure

```
.
├── src/bloodlake/              Python package (all backend code)
│   ├── config.py               Settings and paths (overridable via .env)
│   ├── db.py                   DuckDB connections (read-only serving / read-write warehouse)
│   ├── scraper.py              Async eRaktKosh crawler → Parquet landing files
│   ├── pipeline.py             `bloodlake` CLI: scrape → load → transform → test → publish
│   ├── medical.py              Blood compatibility rules (reads data/medical_rules.json)
│   ├── scoring.py              Trust score formula (mirrors the dbt reliability mart)
│   ├── geo.py                  District/state centroids, Haversine distance, geocode cache
│   ├── export.py               Excel-friendly CSV export
│   └── api/
│       ├── main.py             FastAPI app: mounts routes + serves web/
│       ├── routes.py           All HTTP endpoints (/api/v1/*)
│       └── schemas.py          Pydantic response models
├── dbt/                        SQL transformations (dbt + DuckDB)
│   ├── macros/                 normalize_blood_group()
│   └── models/
│       ├── silver/             Cleaned views over bronze.raw_inventory
│       └── gold/               Facts, dimensions and marts the API reads
├── web/                        Frontend (plain HTML/CSS/JS, no build step)
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js
│   ├── sw.js, manifest.json    Offline / installable PWA
│   └── assets/                 Icons
├── tests/
│   ├── unit/                   Pure-function and module tests
│   ├── integration/            API tests against a generated fixture DB
│   └── fixtures/               generate_fixture_db.py (builds the fixture DB)
├── data/
│   ├── medical_rules.json      Compatibility & donor rules (NBTC / WHO sourced)
│   ├── eraktkosh_all_metadata.json   State → district catalogue the scraper crawls
│   └── landing/                Scraped Parquet files (git-ignored, generated)
├── demo/                       Offline demo database + presenter notes
├── docs/
│   ├── README.md               Index of all documentation — start here
│   ├── ARCHITECTURE.md, API.md, DATA_DICTIONARY.md, FEATURES.md, TESTING.md, USER_MANUAL.md
│   ├── adr/                    Architecture Decision Records
│   ├── diagrams/               UML / architecture PNGs (generated)
│   ├── screenshots/            UI screenshots used in the report
│   ├── academic/               Report, viva Q&A, presentation, submission checklists
│   └── learning/               DuckDB / dbt study notes
├── reports/                    Final submitted report (.docx / .pdf)
├── scripts/report/             Generators for diagrams and the .docx report
├── .github/workflows/          CI, scheduled pipeline, Docker build
├── Dockerfile, docker-compose.yml
├── Makefile                    Run `make help` for every command
└── pyproject.toml, uv.lock     Dependencies (managed with uv)
```

Generated at runtime and not committed: `blood_warehouse.duckdb` (pipeline build DB),
`serving.duckdb` (what the API reads), `data/landing/`, `dbt/target/`.

### Where to start reading

| If you want to… | Read |
|---|---|
| Understand the data flow | `src/bloodlake/pipeline.py` → `dbt/models/silver/` → `dbt/models/gold/` |
| Add or change an API endpoint | `src/bloodlake/api/routes.py` + `schemas.py` |
| Change the UI | `web/index.html`, `web/js/app.js`, `web/css/style.css` |
| Change medical rules | `data/medical_rules.json` (loaded by `medical.py`) |
| See every table and column | `docs/DATA_DICTIONARY.md` |

---

## 🛠️ Quickstart

### 1. Prerequisites
- Linux / macOS / Windows WSL2
- Python 3.12
- [`uv`](https://docs.astral.sh/uv/) package manager

### 2. Install & Run
```bash
git clone https://github.com/radhey803/eraktkosh-blood-lakehouse.git
cd eraktkosh-blood-lakehouse

make install          # uv sync
make demo-offline     # no scrape needed: uses demo/fallback_lakehouse.duckdb
# or, with an existing serving.duckdb:
make run
```
Visit: **[http://localhost:8000](http://localhost:8000)**  
API Documentation (Swagger UI): **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🧪 Automated Testing

```bash
make test        # pytest unit + integration tests with coverage
make dbt-test    # dbt data tests
make lint        # ruff lint + format check
```

---

## ⚙️ Lakehouse CLI (`bloodlake`)

```bash
uv run bloodlake --help        # View all subcommands
uv run bloodlake scrape        # Crawl all districts into data/landing/
uv run bloodlake load          # Load newest landing Parquet into bronze
uv run bloodlake transform     # dbt build: silver + gold (incl. incremental snapshots)
uv run bloodlake test          # Anomaly gate: facility count >= 80% of last run
uv run bloodlake publish       # Atomic copy warehouse -> serving.duckdb
uv run bloodlake all --force   # Everything above, end to end
uv run bloodlake status        # Recent pipeline runs
```

---

## 🏛️ Academic Attribution

- **Context**: Academic Research Project
- **Program**: Academic Project
- **Evaluation**: Mini Project (800 Marks)
- **Data Source**: eRaktKosh Portal, MoHFW, Government of India
- **License**: MIT License
