# Prompt: Write the Complete Beginner-Friendly Documentation for Raktsetu

> Copy everything below the line into an AI assistant that has access to this repository
> (Claude Code, Cursor, etc.). Run it from the project root.

---

## Role

You are a senior software engineer and technical writer. Your job is to write a **complete set of Markdown
documentation** for the project in this repository, called **Raktsetu** (Python package `bloodlake`).

The documentation has three readers:

1. **A beginner IT student** who knows basic Python, HTML and SQL, but has never used DuckDB, dbt, FastAPI,
   Parquet, asyncio or service workers.
2. **The project owners** (Radhey Gajera and Shruti Gajipara), who must be able to fix any issue later
   **without AI help**.
3. **Someone who wants to build a similar project from scratch** (a different data source, the same pattern).

After reading the docs, each reader must understand **what** every part does, **why** it was built that way,
and **how** to change it or build it again.

## Ground rules

- **Read the code first, then write.** Every claim must match the real code. Quote real file paths,
  function names, table names, column names, API routes, Make targets and environment variables.
  Never invent a feature. If something is unclear, write `> TODO: verify` instead of guessing.
- **Use simple English.** Short sentences. Explain every technical term the first time it appears,
  and also add it to the glossary.
- **Teach, don't just describe.** For each concept, give:
  1. what it is, in one line;
  2. why this project uses it;
  3. where it is in the code (`file:function`);
  4. a small real snippet from the repo (5–20 lines), with an explanation line by line where it helps;
  5. how to change it safely.
- **Show the flows with Mermaid diagrams** (`flowchart`, `sequenceDiagram`, `erDiagram`) so they render on GitHub.
- **Every command must be copy-pasteable** and must be one that actually works in this repo
  (check the `Makefile`, `pyproject.toml`, `docker-compose.yml` and `.env.example`).
- Each file starts with a short "What you will learn" list and ends with "Next: <link>".
- Link files to each other with relative links.
- Don't repeat the same explanation in two files; link to it instead.

## The project, in brief (verify each point against the code)

- **Problem:** in India, finding blood stock means calling many blood banks. The government portal
  **eRaktKosh** has the data, but it is slow and hard to search.
- **Solution:** a data pipeline collects stock from eRaktKosh on a schedule, cleans it, checks its quality,
  and serves it through a fast API to a mobile-friendly web app (PWA).
- **Architecture (Medallion lakehouse):**
  1. async `aiohttp` scraper (`src/bloodlake/scraper.py`)
  2. Parquet landing files that are never changed after writing (`data/landing/...`)
  3. DuckDB **bronze** tables
  4. dbt **silver** models (`dbt/models/silver`) and **gold** models (`dbt/models/gold`)
  5. anomaly/quality gate
  6. atomic publish to `serving.duckdb`
  7. FastAPI (`src/bloodlake/api/main.py`, `routes.py`, `schemas.py`)
  8. vanilla JavaScript PWA (`web/index.html`, `web/js/app.js`, `web/css/style.css`, `web/sw.js`,
     `web/manifest.json`)
- **Orchestration:** `src/bloodlake/pipeline.py` (CLI) and the Make targets `scrape`, `load`, `transform`,
  `gate`, `publish` and `pipeline`. GitHub Actions workflows are in `.github/workflows/`
  (`ci.yml`, `pipeline.yml`, `deploy.yml`).
- **Domain logic:**
  - `medical.py`: blood group compatibility (red cells and plasma), rare groups, Bombay group
  - `scoring.py`: trust/reliability score
  - `geo.py`: district coordinates from `data/district_coords.json`, distance / "near me"
  - `export.py`: CSV export with a BOM, header first, CRLF line endings and a formula-injection guard
- **Website features:**
  - KPIs and a state chart (Chart.js)
  - blood finder (state → district → group → component, sorting, pagination, URL sync)
  - map view (Leaflet + CARTO tiles)
  - emergency mode (compatible groups, radius search 50 → 150 → 400 km)
  - trend modal and trust score modal
  - rare blood radar and district shortages
  - CSV export, donor eligibility checker and data health panel
  - offline support, mobile hamburger nav
- **Timezone:** DuckDB runs in `Asia/Kolkata`. Explain how timestamps are stored and shown, and why that matters.
- **Tests:**
  - `tests/unit`, `tests/integration`, `tests/fixtures/generate_fixture_db.py`
  - dbt tests (`schema.yml`, `dbt/tests`)
  - ruff lint, pre-commit
- **Report tooling:** `scripts/report/` (diagram generation and the DOCX/PDF builder).
- **Existing docs to merge, update or replace:** `README.md`, `docs/*.md`, `docs/adr/*`, `docs/academic/*`,
  `docs/learning/*`. Keep the ADRs and link to them.

## Files to produce

Write these into `docs/guide/`, and update the root `README.md` so it links to them.

| # | File | Contents |
|---|------|----------|
| 00 | `00_START_HERE.md` | What Raktsetu is, who uses it, a 2-minute tour, a reading order for each type of reader, and a map of the repo (tree with one line per folder/file). |
| 01 | `01_CONCEPTS_FOR_BEGINNERS.md` | Plain explanations of: client/server, HTTP and REST, JSON, API, async vs sync, web scraping and its ethics (rate limits, robots, politeness), CSV vs Parquet (row vs columnar), OLTP vs OLAP, data warehouse vs data lake vs lakehouse, Medallion (bronze/silver/gold), ETL vs ELT, idempotency, atomic publish, data quality, PWA, service worker and caching, geolocation, the Haversine formula, and timezones. Each one with a real-life analogy and the place where it appears in Raktsetu. |
| 02 | `02_INSTALLATION.md` | Step-by-step setup on Linux, macOS and Windows (WSL): prerequisites with versions (Python from `.python-version`, `uv`, git, Docker optional), clone, `make install`, `.env` from `.env.example` (explain every variable), running the first pipeline, `make run`, `make demo` / `demo-offline`, Docker Compose, and checking that it works (URLs to open, expected output). Finish with a "Common install errors" table: error → cause → fix. |
| 03 | `03_USER_GUIDE.md` | How to use every feature of the website, with screenshots from `docs/screenshots/`. Cover desktop and mobile, what each number and badge means, and how to read the trust score and shortage severity. |
| 04 | `04_ARCHITECTURE.md` | The big picture: a Mermaid flowchart of the full data flow, why each layer exists, the folder ↔ layer mapping, and the design decisions (link the ADRs). Include the trade-offs and the alternatives that were considered. |
| 05 | `05_DATA_PIPELINE.md` | Walk through each stage **with code**: scraper (concurrency with a semaphore, retries, sleep, headers, the endpoints it calls, the shape of the raw response), landing (file naming, partitioning, immutability), bronze load (idempotent load, parameterised `read_parquet`), the anomaly gate (which rules, their thresholds, what happens when one fails), publish (atomic swap, run records, `SUCCESS_NO_SCRAPE`). Include a sequence diagram of one full run and how to re-run or back-fill. |
| 06 | `06_DBT_MODELS.md` | What dbt is and how `dbt-duckdb` works here. For **every** model in silver and gold: its purpose, inputs, output grain, key columns, the core SQL explained, and its tests. Include a lineage diagram, macros, seeds and snapshots, how to add a new model, and how to run one model or test. |
| 07 | `07_DATABASE.md` | The DuckDB files (warehouse vs `serving.duckdb`), an ER diagram, the data dictionary (tables in serving: columns, types, meaning, example values; generate these from `DESCRIBE`), useful SQL queries for debugging, and how to open the database in the DuckDB CLI. |
| 08 | `08_BACKEND_API.md` | FastAPI basics, app startup, the DB connection (`db.py`), config (`config.py`), CORS, and static file serving. For **every endpoint**: method, path, query parameters with their limits, a response example (real JSON), the error codes, the function that handles it, and the SQL it runs. Cover the Pydantic schemas, the emergency logic step by step, the search/sort/distance logic, CSV export, and the `/docs` Swagger UI. |
| 09 | `09_DOMAIN_LOGIC.md` | The medical rules (compatibility tables for red cells, plasma and platelets, why O- is the universal red cell donor and AB+ the universal plasma donor, rare groups, Bombay), with a disclaimer that this is not medical advice; the trust score formula with a worked example; the shortage severity score; donor eligibility rules; the distance calculation; geocoding (`scripts/data/geocode_districts.py`, Nominatim, the cache). |
| 10 | `10_FRONTEND.md` | How `index.html` is laid out (sections and ids), how `app.js` is organised (state, fetch helpers, render functions, event wiring), the request race guard (`searchSeq`), URL state restore, the map (Leaflet, CARTO key, markers, user location), charts, modals and keyboard handling, responsive CSS (breakpoints 1200/640/480/360, touch targets), PWA (`manifest.json`, `sw.js` cache strategy and versioning, the offline banner), and how to add a new section end-to-end. |
| 11 | `11_TESTING.md` | Test types and why each exists, how to run each one (`make test`, `make lint`, `make dbt-test`, and the Playwright e2e/responsive checks), what the fixture database is, how to write a new test (with an example), and how CI runs them. |
| 12 | `12_DEPLOYMENT_AND_OPERATIONS.md` | Docker, Docker Compose, the VPS + Caddy deployment (see ADR-005), GitHub Actions schedules and secrets, monitoring (the data health panel, run records, `make status`), backups, and updating the service-worker cache version on release. |
| 13 | `13_TROUBLESHOOTING.md` | A **runbook**: symptom → how to check (exact command or SQL) → cause → fix. Cover at least: the scraper being blocked or getting a timeout or empty data; the gate failing; dbt test failures; a stale data banner; wrong times (timezone); an empty district list; "Near me" not working (HTTPS / secure context, permission denied); map tiles showing "API KEY REQUIRED"; CSV opening wrongly in Excel; the service worker serving old files; a port already in use; a DuckDB lock error; uvicorn reload not picking up changes; CORS errors; and mobile layout overflow. Include a general debugging method (logs, browser DevTools Network/Console, `curl` the API, query DuckDB). |
| 14 | `14_BUILD_IT_YOURSELF.md` | A from-zero tutorial to rebuild a **smaller version** of this project without AI: milestones (1 scrape one endpoint → 2 save Parquet → 3 load DuckDB → 4 one dbt model → 5 one API route → 6 one HTML page that calls it → 7 schedule it → 8 tests → 9 deploy). For each milestone: the goal, the minimal code, how to verify it, and common mistakes. Then explain how to adapt the pattern to another public dataset (for example hospital beds, mandi prices, air quality), as a checklist. |
| 15 | `15_TECH_STACK_REFERENCE.md` | One section per technology (Python, uv, asyncio/aiohttp, Parquet/PyArrow, DuckDB, dbt, FastAPI/Uvicorn, Pydantic, Leaflet, CARTO, Chart.js, service workers, pytest, Playwright, ruff, pre-commit, Docker, GitHub Actions, Caddy, LibreOffice/python-docx/Graphviz/matplotlib for the report): what it is, why it was chosen, alternatives, the 5 commands or APIs you'll use most, and official doc links. |
| 16 | `16_GLOSSARY_AND_FAQ.md` | An A–Z glossary of every term used in the docs, plus 25+ FAQs (including likely viva questions, with short answers). |

## Quality checklist (check every item before finishing)

- [ ] Every file path, function, route, table and command you mention exists. Grep to confirm.
- [ ] Every Mermaid diagram is valid.
- [ ] A beginner can follow `02_INSTALLATION.md` on a fresh machine with no outside help.
- [ ] Every endpoint in `routes.py` and `main.py` is documented.
- [ ] Every dbt model is documented.
- [ ] `13_TROUBLESHOOTING.md` has at least 15 entries, each with a concrete command.
- [ ] `14_BUILD_IT_YOURSELF.md` code runs on its own.
- [ ] No secrets are copied into the docs. Show only the variable names from `.env.example`.
- [ ] Old docs that are now duplicated are either deleted or replaced by a one-line link to the new guide.
  List which ones you changed.

When done, print a short summary: the files created, the files changed, and the `TODO: verify` items left.
