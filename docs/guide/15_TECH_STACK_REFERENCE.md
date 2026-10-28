# 15 · Tech Stack Reference

**What you will learn**
- For each technology: what it is, why it was chosen, the alternatives, the commands or APIs you will use most, and where to learn more

---

## Data and backend

### Python 3.12
- **What:** the main programming language.
- **Why:** it has the best libraries for data work, and it is easy to read.
- **Use most:** f-strings, `pathlib.Path`, `datetime` with `timezone.utc`, type hints, `async def`.
- **Docs:** https://docs.python.org/3.12/

### uv
- **What:** a very fast package and environment manager (it replaces pip + venv + pip-tools).
- **Why:** installs about 10–100 times faster, and `uv.lock` gives exact, repeatable versions.
- **Alternatives:** pip + venv, Poetry, conda.
- **Top commands:** `uv sync` · `uv add <pkg>` · `uv add --dev <pkg>` · `uv run <cmd>` · `uv python install 3.12`
- **Docs:** https://docs.astral.sh/uv/

### asyncio + aiohttp
- **What:** asyncio is Python's built-in way to run many tasks that wait on I/O at the same time;
  aiohttp is an async HTTP client.
- **Why:** it fetches about 780 districts in minutes instead of more than 20 minutes.
- **Alternatives:** `requests` + threads, `httpx` (async too).
- **Use most:** `asyncio.run()`, `asyncio.gather()`, `asyncio.Semaphore(n)`, `aiohttp.ClientSession()`,
  `session.get(url, timeout=...)`, `await resp.text()`.
- **Docs:** https://docs.aiohttp.org/

### Apache Parquet + PyArrow
- **What:** a compressed, columnar file format; PyArrow writes it from Python.
- **Why:** small files that keep the data types, and DuckDB reads them directly.
- **Use most:** `pa.table({...})`, `pa.Table.from_arrays(...)`, `pq.write_table(t, path, compression="zstd")`, `pq.read_table(path)`.
- **Docs:** https://arrow.apache.org/docs/python/parquet.html

### DuckDB
- **What:** an in-process analytics (OLAP) SQL database. The whole database is one file.
- **Why:** no server, very fast aggregations, reads Parquet and JSON, and is free ([ADR-001](../adr/ADR-001-duckdb-for-analytics-postgres-for-app-state.md)).
- **Alternatives:** PostgreSQL, SQLite, ClickHouse, BigQuery.
- **Use most:**
  - `duckdb.connect(path, read_only=True)`
  - `con.execute(sql, [params]).fetchall()`
  - `read_parquet('glob')`
  - `QUALIFY`, `UNNEST`, `json_keys`, `->>`, `string_split`, `DATE_DIFF`
- **Gotcha:** only one writer at a time. Naive timestamps use the session timezone.
- **Docs:** https://duckdb.org/docs/
- **Learning notes in this repo:** [`docs/learning/`](../learning/)

### dbt (dbt-core + dbt-duckdb)
- **What:** SQL-based transformation tool with dependencies, tests and docs.
- **Why:** clear layers, tests built in, and lineage docs ([ADR-002](../adr/ADR-002-dbt-incremental-mart-design.md)).
- **Alternatives:** plain SQL scripts, pandas, SQLMesh.
- **Top commands:** `dbt build` · `dbt run --select model+` · `dbt test` · `dbt run --full-refresh` · `dbt docs generate`
  (always add `--project-dir dbt --profiles-dir dbt` here)
- **Docs:** https://docs.getdbt.com/ · https://github.com/duckdb/dbt-duckdb

### FastAPI + Uvicorn
- **What:** FastAPI is a modern Python web framework; Uvicorn is the server that runs it.
- **Why:** automatic `/docs`, validation through type hints, and fast.
- **Alternatives:** Flask, Django REST Framework.
- **Use most:**
  - `@router.get(path)`
  - `Query(default, ge=, le=)`
  - `Depends(...)`
  - `HTTPException(status_code, detail)`
  - `response_model=`
  - `StaticFiles`
  - `TestClient`
- **Docs:** https://fastapi.tiangolo.com/

### Pydantic + pydantic-settings
- **What:** data validation with Python classes; `BaseSettings` reads settings from the environment or `.env`.
- **Why:** API responses always have the right shape, and settings are typed.
- **Use most:** `class X(BaseModel)`, `Optional[...]`, `.model_dump()`, `SettingsConfigDict(env_file=".env")`.
- **Docs:** https://docs.pydantic.dev/

### Typer + Rich
- **What:** Typer builds command-line tools from functions; Rich prints coloured tables.
- **Use most:** `app = typer.Typer()`, `@app.command()`, `typer.Option(...)`, `raise typer.Exit(code=n)`.
- **Docs:** https://typer.tiangolo.com/

---

## Frontend

### HTML / CSS / vanilla JavaScript
- **Why no framework:** no build step, a small download, and it works on cheap phones.
- **Use most:**
  - `fetch()` + `async/await`
  - `document.getElementById`, `addEventListener`
  - template literals
  - `URLSearchParams`, `history.replaceState`
  - CSS Grid, `@media`, CSS variables
- **Docs:** https://developer.mozilla.org/

### Leaflet + CARTO tiles
- **What:** Leaflet is a map library; CARTO provides the background map images (tiles).
- **Why:** light (about 40 KB) and free. Tiles need a CARTO key.
- **Alternatives:** Google Maps (paid), MapLibre, OpenStreetMap tiles.
- **Use most:** `L.map(id, {center, zoom})`, `L.tileLayer(url).addTo(map)`, `L.marker([lat,lng]).bindPopup(html)`, `map.fitBounds()`, `map.invalidateSize()`.
- **Docs:** https://leafletjs.com/reference.html

### Chart.js 4
- **What:** a canvas chart library.
- **Use most:** `new Chart(ctx, {type:'bar'|'line', data:{labels, datasets}, options})`, `chart.destroy()`.
  Always destroy the old chart before drawing a new one on the same canvas.
- **Docs:** https://www.chartjs.org/docs/latest/

### Service Worker + Web App Manifest (PWA)
- **Use most:** `navigator.serviceWorker.register('/sw.js')`, the `install`/`activate`/`fetch` events, `caches.open/put/match`.
- **Docs:** https://web.dev/learn/pwa/

### Geolocation API
- **Use most:** `navigator.geolocation.getCurrentPosition(ok, err, {timeout})`, `window.isSecureContext`.

---

## Quality and tooling

| Tool | What | Top commands | Docs |
|------|------|--------------|------|
| **pytest** | Test runner | `pytest -q`, `-k name`, `-x`, `--cov` | https://docs.pytest.org/ |
| **Playwright** | Browser automation | `playwright install chromium`, `page.goto/click/fill/locator` | https://playwright.dev/python/ |
| **ruff** | Linter + formatter | `ruff check .`, `ruff check --fix`, `ruff format .` | https://docs.astral.sh/ruff/ |
| **pre-commit** | Runs checks before each commit | `pre-commit install`, `pre-commit run -a` | https://pre-commit.com/ |
| **pip-audit** | Checks dependencies for known security problems | `uv run pip-audit` | https://pypi.org/project/pip-audit/ |
| **Make** | Short names for commands | `make help` | — |

---

## Deployment

| Tool | What | Top commands | Docs |
|------|------|--------------|------|
| **Docker** | Container images | `docker build -t x .`, `docker run -p 8000:8000 x` | https://docs.docker.com/ |
| **Docker Compose** | Runs containers from YAML | `up -d --build`, `logs -f`, `down` | https://docs.docker.com/compose/ |
| **GitHub Actions** | CI and schedules | the `.github/workflows/*.yml` files; `on: schedule: cron` | https://docs.github.com/actions |
| **Caddy** | Web server with automatic HTTPS | `reverse_proxy localhost:8000`, `systemctl reload caddy` | https://caddyserver.com/docs/ |

---

## Report tooling (`scripts/report/`)

| Tool | Used for |
|------|----------|
| **python-docx** | Builds `reports/Raktsetu_Project_Report.docx` (`build_raktsetu_docx.py`) |
| **LibreOffice** (`soffice --headless --convert-to pdf`) | DOCX → PDF |
| **Graphviz** (`dot`) | Architecture, class, DFD, ER and activity diagrams |
| **matplotlib** | Use case, sequence and Gantt diagrams |
| **Playwright** | Screenshots (`capture_screenshots.py`) |

Rebuild the report with `make report`.

---

## External data sources

| Source | Used for | Notes |
|--------|----------|-------|
| **eRaktKosh** (MoHFW) | All the blood stock data | Public; be polite (guide 05) |
| **NBTC India / WHO** | Compatibility and donor rules | Cited in `medical_rules.json` |
| **OpenStreetMap Nominatim** | District coordinates (run once) | At most 1 request/s; credit OSM |
| **CARTO** | Map tiles | Needs a key |

---

Next: [16 · Glossary & FAQ →](16_GLOSSARY_AND_FAQ.md)
