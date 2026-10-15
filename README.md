<div align="center">

# eRaktKosh Blood Lakehouse

**National Blood Inventory Intelligence & Emergency Triage Platform**  
*Academic Mini Project (800 Marks) • Master of Computer Applications (MCA)*  
**Charotar University of Science and Technology (CHARUSAT)**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1+-FFF000.svg?logo=duckdb&logoColor=black)](https://duckdb.org)
[![dbt-duckdb](https://img.shields.io/badge/dbt-DuckDB-FF694B.svg?logo=dbt&logoColor=white)](dbt/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](api.py)
[![Pytest](https://img.shields.io/badge/Pytest-45%20Passed-brightgreen.svg)](tests/)
[![dbt Tests](https://img.shields.io/badge/dbt%20Tests-35%20Passed-brightgreen.svg)](dbt/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*Transforming fragmented public healthcare records into an auditable, high-performance in-process lakehouse for emergency blood availability discovery.*

</div>

---

> [!IMPORTANT]
> **Source Attribution & Non-Affiliation Disclaimer**:  
> Data is politely ingested from the public [eRaktKosh Portal](https://eraktkosh.mohfw.gov.in/) operated by the **Ministry of Health and Family Welfare (MoHFW), Government of India**. This project is an independent academic research initiative submitted for the MCA degree at **Charotar University of Science and Technology (CHARUSAT)** and is **not an official government service**. In clinical emergencies, always contact the blood bank directly to confirm bed-side availability before travelling.

---

## 📌 Problem Statement

Every day across India, emergency surgeries, trauma cases, thalassaemia transfusions, and postpartum hemorrhages depend on immediate blood availability. While India's Ministry of Health operates the central eRaktKosh database, accessing critical blood units during emergencies remains fraught with friction:

1. **Slow, Fragmented Discovery**: Users must manually cycle through single-district dropdowns across 781 districts without national aggregation, cross-district radius matching, or reliability indicators.
2. **Fragile Matching & Regex Traps**: Naive search scripts confuse `B+` inside `AB+` or misinterpret life-critical `Bombay (Oh+)` as regular `O+`.
3. **Information Asymmetry & Stale Data**: Many listings on public portals have not been updated for months. Anxious relatives waste the "golden hour" travelling to facilities with abandoned stock listings.
4. **No Zero-Overhead Analytical Lakehouse**: Traditional data warehouses (Snowflake, BigQuery) are cost-prohibitive for non-profit and academic healthcare deployments, while traditional relational databases (MySQL/PostgreSQL) lack fast columnar aggregations across nationwide snapshots.

---

## ⚡ The Solution: Modern Lakehouse Architecture

The **eRaktKosh Blood Lakehouse** pairs an asynchronous crawler with an in-process columnar lakehouse built on **DuckDB**, **dbt Core**, and **FastAPI**:

```mermaid
flowchart TD
    subgraph Ingestion ["1. Asynchronous Ingestion Layer"]
        EK[eRaktKosh Public Portal\n781 Administrative Districts] -->|Polite Async Crawl\nSemaphore: 10, Backoff| SCRAPER[src/bloodlake/ingestion/scraper.py]
        SCRAPER -->|Immutable Parquet\n+ SHA-256 Checksum| LANDING[data/landing/*.parquet]
    end

    subgraph Lakehouse ["2. Storage & Transformation Layer (DuckDB + dbt)"]
        LANDING -->|Direct Ingestion| BRONZE[(bronze.raw_inventory\nAppend-Only Raw Rows)]
        BRONZE -->|dbt Staging Views| SILVER[(silver.stg_blood_banks\nsilver.stg_inventory_components)]
        SILVER -->|dbt Build & Contracts| GOLD[(gold.dim_blood_banks\ngold.fct_stock_current\ngold.fct_stock_snapshot\ngold.mart_reliability_score\ngold.mart_district_status\ngold.mart_rare_blood_availability)]
    end

    subgraph QualityGate ["3. Data Quality & Anomaly Gate"]
        GOLD --> DBT_TEST[35 dbt Contract Tests\nUnique, Non-null, Accepted Values]
        DBT_TEST --> ANOMALY_TEST[Anomaly Gate:\nFacility Count >= 80% Prior Run]
        ANOMALY_TEST -->|Passed| ATOMIC_SWAP[Atomic Copy & Swap:\nblood_warehouse.duckdb -> serving.duckdb]
    end

    subgraph Serving ["4. Application & Analytical Serving"]
        ATOMIC_SWAP --> API[FastAPI REST API\nRead-Only Connection]
        API --> ENDPOINTS[/api/v1/availability\n/api/v1/banks\n/api/v1/history\n/api/v1/shortages\n/api/v1/rare]
        API --> UI[Clinical Vanilla Web App\nCarto Positron Map & Chart.js]
    end
```

---

## 🚀 Core Features & Innovations

- **Sub-15ms Emergency Search**: Exact SQL lookups on `fct_stock_current` with strict blood group normalization (`O+`, `O-`, `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `Bombay Oh+/Oh-`) executed without fragile application-side regex parsing.
- **Data Reliability Score (0–100)**: Proprietary 3-pillar algorithm penalizing stale reporting (>24h), invalid phone contacts, or incomplete stock distributions, categorizing facilities into `HIGH`, `MODERATE`, and `LOW` credibility tiers.
- **Zero Fake Data Contract**: Real history accumulates strictly from real scrapes. If fewer than 2 snapshots exist, the system displays an honest educational banner: *"Trend builds up with each data refresh"*. No artificial or simulated points are ever generated.
- **Geographic Honesty**: Because public portals report administrative district names rather than GPS coordinates, all map pins and facility cards explicitly declare: *"approximate location, district level"*.
- **Interactive Blood Map**: Zero-cost interactive mapping using Leaflet.js and Carto Positron tiles, avoiding costly commercial map API keys.
- **One-Click WhatsApp SOS Sharing**: Generates pre-formatted emergency dispatch messages containing verified facility contacts, address, component, and blood group for instant family coordination.
- **Rare Blood Phenotype Radar**: Rapid triage finder for Bombay Blood Group (`Oh+`, `Oh-`) and Rh-negative units across the country.
- **District Deficit Radar**: Aggregates inventory at the administrative district grain, highlighting areas experiencing complete stockouts (`SHORTAGE: 0 units`).
- **Multilingual Support**: Instant client-side switching between English, Hindi (हिन्दी), and Gujarati (ગુજરાતી).

---

## 📂 Project Directory Structure

```
eraktkosh-blood-lakehouse/
├── Makefile                      # Automated developer targets (run, test, lint, demo)
├── pyproject.toml                # Project metadata, dependencies, and tool configs
├── api.py                        # FastAPI application entry point
├── run_pipeline.py               # Pipeline runner wrapper
├── blood_warehouse.duckdb        # Local DuckDB warehouse (build target)
├── serving.duckdb                # Verified read-only database served to users
├── eraktkosh_all_metadata.json   # Master district metadata (36 states, 781 districts)
├── .github/workflows/            # GitHub Actions CI/CD workflows
│   └── pipeline.yml              # Automated test and scheduled ingestion pipeline
├── dbt/                          # dbt Core Project
│   ├── dbt_project.yml           # dbt project configuration
│   ├── profiles.yml              # DuckDB adapter connection profiles
│   ├── macros/                   # Jinja SQL macros
│   │   └── normalize_blood_group.sql # Prioritized blood group normalizer
│   └── models/                   # Medallion layers
│       ├── bronze/               # bronze.raw_inventory
│       ├── silver/               # silver.stg_blood_banks, stg_inventory_components
│       ├── gold/                 # dim_blood_banks, fct_stock_current, marts
│       └── schema.yml            # 35 relational schema and contract tests
├── src/bloodlake/                # Core Python Source Package
│   ├── api/                      # FastAPI routers, schemas, and endpoints
│   ├── crawler/                  # aiohttp async crawler with Semaphore(10)
│   ├── ingestion/                # Parquet landing and bronze loader
│   ├── warehouse/                # Anomaly gate, snapshots, and atomic swap
│   ├── config.py                 # Pydantic environment configuration
│   ├── db.py                     # DuckDB session manager & catalog resolver
│   ├── geo.py                    # District centroid gazetteer
│   └── pipeline.py               # Typer CLI application (`bloodlake`)
├── web/                          # Clinical Red-and-White Web Application
│   ├── index.html                # Semantic HTML5 dashboard
│   ├── css/style.css             # Vanilla CSS design system (zero frameworks)
│   └── js/                       # Vanilla JavaScript modules
│       ├── app.js                # Core UI controller and search logic
│       ├── map.js                # Leaflet & Carto Positron map module
│       └── translations.js       # Multilingual dictionary (EN, HI, GU)
├── tests/                        # Automated Pytest Suite
│   ├── unit/                     # Scraper, normalizer, and scoring unit tests
│   ├── integration/              # FastAPI endpoint tests against isolated fixture
│   └── fixtures/                 # Synthetic test lakehouse generator
└── docs/                         # Comprehensive Academic Documentation
    ├── REPORT.md                 # Complete Academic Project Report (800 Marks)
    ├── ARCHITECTURE.md           # Architecture Decision Records (ADRs) & C4 diagrams
    ├── DATA_DICTIONARY.md        # Full catalog of Bronze, Silver, and Gold schemas
    ├── API.md                    # REST API Reference with curl examples
    ├── USER_MANUAL.md            # Evaluator & user operational guide
    ├── VIVA_QA.md                # 60 Viva Voce questions and model answers
    ├── PRESENTATION_OUTLINE.md   # 15-slide presentation outline & 7-min demo script
    └── TESTING.md                # 40-case testing execution matrix
```

---

## 🛠️ Quickstart (Fresh Setup)

### 1. Prerequisites
- Linux / macOS / Windows WSL2
- Python 3.11 or 3.12
- [`uv`](https://docs.astral.sh/uv/) package manager (recommended) or standard `pip`

### 2. Clone & Install Dependencies
```bash
# Clone the project repository
git clone https://github.com/radhey803/eraktkosh-blood-lakehouse.git
cd eraktkosh-blood-lakehouse

# Install all dependencies into virtual environment using uv
uv sync
```

### 3. Start the Web Application
```bash
# Start the server using the Makefile
make run

# Or directly via uv:
uv run uvicorn api:app --reload --port 8000
```
Open your browser and navigate to: **[http://localhost:8000](http://localhost:8000)**.  
Interactive OpenAPI/Swagger documentation is available at: **[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

## 🧪 Automated Testing & Verification

The project enforces continuous quality control via automated unit, integration, and dbt relational contract tests:

```bash
# Run all 45 Python unit and integration tests (executes in <2s)
make test
# Or: uv run pytest

# Run all 35 dbt relational schema and contract tests (executes in ~3s)
uv run dbt test --project-dir dbt --profiles-dir dbt

# Run pre-commit code formatting and linting via Ruff
make lint
# Or: uv run ruff check . && uv run ruff format .
```

### Test Results Summary:
- **Pytest**: `45 passed, 0 failures` (Unit tests + API integration tests).
- **dbt Core**: `PASS=35 WARN=0 ERROR=0 TOTAL=35` (Unique keys, foreign keys, accepted values, non-negative assertions).
- **Ruff**: `All checks passed!` (100% PEP 8 compliant, zero unused imports).

---

## ⚙️ Lakehouse CLI Management (`bloodlake`)

The data pipeline can be executed modularly or end-to-end using the Typer CLI:

```bash
# View CLI documentation
uv run bloodlake --help

# Step 1: Scrape all 781 districts (~26s)
uv run bloodlake scrape

# Step 2: Ingest Parquet landing files into Bronze layer
uv run bloodlake ingest

# Step 3: Run dbt transformation models (Silver views & Gold marts)
uv run bloodlake transform

# Step 4: Record daily inventory snapshot in fct_stock_snapshot
uv run bloodlake snapshot

# Step 5: Execute the full pipeline end-to-end with anomaly gate validation
uv run bloodlake all
```

---

## 📚 Complete Academic Documentation

For academic evaluators, university examiners, and project guides:

| Document | Description |
| :--- | :--- |
| **[Project Report](docs/REPORT.md)** | Formal 800-mark MCA Academic Project Report covering introduction, literature review, requirements, system design, implementation, and ethics. |
| **[System Architecture](docs/ARCHITECTURE.md)** | Architectural principles, Medallion flow diagrams, and 6 Architecture Decision Records (ADRs). |
| **[Data Dictionary](docs/DATA_DICTIONARY.md)** | Comprehensive catalog of all Bronze, Silver, and Gold tables, columns, data types, constraints, and grains. |
| **[REST API Reference](docs/API.md)** | Full endpoint specification with curl examples, query parameters, schemas, and HTTP status codes. |
| **[User & Evaluator Manual](docs/USER_MANUAL.md)** | Step-by-step user guide for emergency search, map navigation, reliability interpretation, and WhatsApp SOS. |
| **[Viva Voce Examination Q&A](docs/VIVA_QA.md)** | 60 high-probability viva voce questions and comprehensive model answers covering data engineering, scraping, and architecture. |
| **[Presentation Outline & Demo Script](docs/PRESENTATION_OUTLINE.md)** | 15-slide presentation outline with speaker notes and a timed 7-minute live demonstration script. |
| **[Testing & Quality Assurance Matrix](docs/TESTING.md)** | 40-case testing execution matrix detailing unit, integration, and dbt contract test verification. |

---

## 🏛️ Academic Attribution & Team

- **Academic Institution**: Charotar University of Science and Technology (CHARUSAT)
- **Faculty / Institute**: Faculty of Computer Science and Applications (FCA)
- **Degree Program**: Master of Computer Applications (MCA)
- **Project Type**: Academic Mini Project (800 Marks)
- **Data Source**: eRaktKosh Portal, Ministry of Health and Family Welfare (MoHFW), Government of India
- **License**: MIT License (Open-Source Academic Research)
