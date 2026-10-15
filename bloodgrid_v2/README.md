# BloodGrid V2 (Enterprise & Sellable Edition)

This directory stores the complete, audited, and production-tested version of **BloodGrid**:
- **Backend**: Modular FastAPI architecture with versioned `/v1` REST endpoints, structured SQL emergency search, Argon2id auth, hashed API keys, Razorpay subscriptions, and alert dispatcher.
- **Frontend**: Accessible, premium red-and-white theme with Carto Positron map, developer dashboard, legal policies, SOS card, and 0 emojis.
- **Lakehouse & Data Engineering**: Parquet landing zone, dbt models, Gold analytical marts, and atomic database swapping.

---

## Folder Structure

```
bloodgrid_v2/
├── backend/          # Modular FastAPI application (routers, schemas, services, pipeline)
├── frontend/         # Web application (index.html, dashboard, terms, privacy, etc.)
├── dbt/              # dbt lakehouse transformation models, macros, and schema contracts
├── docs/             # Architecture, ADRs, data dictionary, legal docs, runbook, pitch
├── tests/            # Pytest unit and integration test suite (>85% coverage)
└── run_server.py     # Standalone runner for this edition
```

---

## How to Run BloodGrid V2

From the project root:

```bash
# Run on port 8001
uv run python bloodgrid_v2/run_server.py

# Or directly via uvicorn
uv run uvicorn bloodgrid.api.main:app --reload --port 8001
```

Access in your browser:
- Main Finder: [http://localhost:8001](http://localhost:8001)
- Developer Console: [http://localhost:8001/dashboard](http://localhost:8001/dashboard)
- Interactive API Docs: [http://localhost:8001/docs](http://localhost:8001/docs)
