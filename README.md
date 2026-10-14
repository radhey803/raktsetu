<div align="center">

# 🩸 BloodGrid

**Real-Time National Blood Banking Intelligence Platform & Emergency Shortage Radar**

[![CI Pipeline](https://github.com/radhey803/eraktkosh-blood-lakehouse/actions/workflows/ci.yml/badge.svg)](https://github.com/radhey803/eraktkosh-blood-lakehouse/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1+-FFF000.svg?logo=duckdb&logoColor=black)](https://duckdb.org)
[![dbt](https://img.shields.io/badge/dbt-DuckDB-FF694B.svg?logo=dbt&logoColor=white)](https://getdbt.com)
[![Coverage: 85%](https://img.shields.io/badge/Coverage-85%25-brightgreen.svg)](tests/)

*Transforming fragmented national blood metrics into emergency life-saving intelligence, automated shortage alerts, and commercial-grade developer APIs.*

</div>

---

> [!IMPORTANT]
> **Source Attribution & Non-Affiliation**:  
> Data is politely sourced from the public eRaktKosh portal (Ministry of Health & Family Welfare, Government of India). BloodGrid is an independent open-access analytics platform and is **not an official government service**. In clinical emergencies, always contact the blood bank directly to confirm bed-side availability before travelling.

---

## 📌 Problem Statement

Every day across India, emergency surgeries, trauma cases, and postpartum hemorrhages depend on immediate blood availability. While India's Ministry of Health operates the central eRaktKosh database, accessing critical blood units remains fraught with friction:

1. **Slow, Fragmented Discovery**: Users must manually cycle through single-district dropdowns across 781 districts without cross-district radius matching or reliability ratings.
2. **Fragile Matching & Misleading Stocks**: Naive keyword search matches `B+` inside `AB+` or confuses rare `Bombay (Oh+)` with regular `O+`.
3. **No Proactive Shortage Intelligence**: Blood donation NGOs and foundations lack automated alerts when regional stocks of rare negative or platelet units are exhausted.
4. **No Low-Latency Developer API**: Health-tech startups, hospital information systems (HIS), and ambulance dispatchers lack an SLA-backed REST API for real-time inventory checks.

---

## ⚡ The Solution: BloodGrid Architecture

BloodGrid solves this with a **modern data lakehouse** built on DuckDB, dbt Core, and FastAPI:

```mermaid
flowchart TD
    subgraph Ingestion ["1. Ingestion Layer"]
        EK[eRaktKosh Portal\n781 Districts] -->|Polite Async Crawl\nSemaphore: 10| SCRAPER[src/bloodgrid/ingestion/scraper.py]
        SCRAPER -->|Zstandard Parquet\n+ SHA-256 Manifest| LANDING[data/landing/dt=YYYY-MM-DD/hh=HH/]
    end

    subgraph Lakehouse ["2. Storage & Transformation Layer"]
        LANDING -->|Direct Ingestion| BRONZE[(bronze.raw_inventory\nDuckDB)]
        BRONZE -->|dbt Staging Views| SILVER[(silver.stg_blood_banks\nsilver.stg_inventory_components)]
        SILVER -->|dbt Build & Contracts| GOLD[(gold.dim_blood_banks\ngold.fct_stock_current\ngold.fct_stock_snapshot\ngold.mart_reliability_score\ngold.mart_district_status)]
    end

    subgraph QualityGate ["3. Quality & Anomaly Gate"]
        GOLD --> DBT_TEST[47 dbt Tests\nUnique, Non-null, Normalizer]
        DBT_TEST --> ANOMALY_TEST[Anomaly Gate:\nFacility Count >= 80% Prior Run]
        ANOMALY_TEST -->|Passed| ATOMIC_SWAP[Atomic Rename:\nserving.duckdb.tmp -> serving.duckdb]
    end

    subgraph Serving ["4. Application & API Serving"]
        ATOMIC_SWAP --> API[FastAPI REST Engine\nRead-Only Connection]
        API --> V1[/v1/availability\n/v1/banks\n/v1/shortages\n/v1/rare]
        API --> ALERTS[Alert Engine\nEmail + Telegram Dispatcher]
        API --> UI[SPA Frontend\nCarto Positron Map & Skeletons]
    end
```

---

## 🚀 Key Features

- **Sub-5ms Emergency Search**: Exact SQL lookups on `fct_stock_current` with strict blood group normalization (`O+`, `O-`, `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `Bombay Oh+/Oh-`).
- **Reliability Scoring Engine (0-100)**: Proprietary 3-pillar algorithm penalizing stale reporting (>24h), invalid phone contacts, or missing component splits.
- **Automated Shortage Alerts**: Multi-channel notifications via Telegram and Email with quiet-hour suppression and daily deduplication caps.
- **NGO Donation Camp Suggester**: Mathematically identifies districts suffering chronic deficits across consecutive snapshots.
- **Programmatic SEO**: Pre-rendered routes (`/blood-banks/{state}/{district}`) with Schema.org JSON-LD structured metadata and dynamic `sitemap.xml`.
- **Zero Fake Data Policy**: Real history accumulates strictly from real scrapes; honest empty states until real snapshots exist.

---

## 🛠️ Quickstart (Fresh Clone)

### 1. Prerequisites
- Linux / macOS / WSL
- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) package manager

```bash
# Clone the repository
git clone https://github.com/radhey803/eraktkosh-blood-lakehouse.git bloodgrid
cd bloodgrid

# Install dependencies and setup virtual environment
uv sync --all-extras --dev
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your specific secrets (default dev values work out of the box)
```

### 3. Run Pipeline to Produce Initial Dataset
Because lakehouse and database files are git-ignored, produce your fresh dataset with one command:
```bash
# Execute end-to-end ingestion, dbt build, anomaly testing, and publishing:
uv run bloodgrid all --force
```

### 4. Start the Application & API
```bash
uv run uvicorn bloodgrid.api.main:app --reload --port 8000
```
- **Web App**: Visit `http://localhost:8000`
- **Developer Console**: Visit `http://localhost:8000/dashboard`
- **Interactive OpenAPI Docs**: Visit `http://localhost:8000/docs`

---

## 📊 Testing & Quality Verification

Run the comprehensive unit, integration, and coverage test suite:
```bash
# Run pytest with 80% coverage enforcement
uv run pytest tests/ -v --cov=src/bloodgrid --cov-report=term-missing --cov-fail-under=80

# Linting & Formatting validation
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Security audit
uv run pip-audit
```

---

## 📡 REST API Quickstart

### Search Live Component Availability
```bash
curl "http://localhost:8000/v1/availability?state=Gujarat&district=Anand&blood_group=O-&component=Packed%20Red%20Blood%20Cells"
```

### Rare Blood Radar (Bombay & Negatives)
```bash
curl "http://localhost:8000/v1/rare?state=Gujarat&group=Bombay%20(Oh%2B)"
```

### System Metadata & Last Sync Status
```bash
curl "http://localhost:8000/v1/meta"
```

---

## 💳 Commercial Plans & Pricing (INR)

| Plan | Price | Intended Audience | Features |
| :--- | :--- | :--- | :--- |
| **Community** | Free | Public & Emergency Donors | Web search, CARTO map, shareable SOS card, public district trends |
| **Pro** | ₹499 / mo | Critical Patients & Thalassemia Families | 10 custom district alerts, Telegram/Email shortage dispatches |
| **Developer** | ₹2,499 / mo | Health-tech Startups & HIS Software | Programmatic REST API, 500 req/min, 99.9% uptime SLA, webhooks |
| **Organization** | ₹7,999 / mo | Blood Donation NGOs & Hospital Chains | Multi-seat console, monthly shortage CSV export, blood camp suggester |

---

## ⚠️ Known Limitations & Honesty Statement

1. **Source Refresh Cadence**: BloodGrid is only as fresh as the last crawl (scheduled every 4 hours).
2. **Voluntary Hospital Updates**: Hospital stock levels are updated manually by blood bank personnel on eRaktKosh; emergency cases should always telephone the facility before travelling.
3. **Map Geocoding Precision**: Facilities without exact OpenStreetMap street addresses fallback to deterministic district centroids tagged visually with an *"approximate location"* badge.
4. **Machine Learning Forecasting**: Stock level forecasting is deliberately disabled until $\ge 60$ days of real historical snapshots have accumulated to prevent spurious medical projections.

---

## 📄 License & Legal

- Code is licensed under the [MIT License](LICENSE).
- For data licensing, NIC/NHM attribution, DPDP Act 2023 compliance, and draft policies, review [`docs/LEGAL.md`](docs/LEGAL.md).
