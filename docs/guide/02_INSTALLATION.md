# 02 · Installation

**What you will learn**
- What to install before you start
- How to set up the project on Linux, macOS or Windows
- How to get data (live scrape, or the offline demo)
- How to check that everything works
- How to fix common install errors

---

## 1. Prerequisites

| Tool | Version | Why | Check with |
|------|---------|-----|-----------|
| **Git** | any | Download the code | `git --version` |
| **Python** | 3.12 (see `.python-version`) | Runs everything | `python3 --version` |
| **uv** | latest | Installs Python packages very fast and creates `.venv` | `uv --version` |
| **make** | any | Short commands (`make run`) | `make --version` |
| Docker *(optional)* | 24+ | Run as a container | `docker --version` |
| Graphviz + LibreOffice *(optional)* | any | Only to rebuild the report/diagrams | `dot -V`, `soffice --version` |

> You do **not** need to install DuckDB or a database server. DuckDB comes as a Python package, and the
> database is just a file.

### Install uv
```bash
# Linux / macOS / WSL
curl -LsSf https://astral.sh/uv/install.sh | sh
# then restart the terminal
```
uv can also install Python 3.12 for you: `uv python install 3.12`.

### Windows
Use **WSL 2** (Windows Subsystem for Linux):
1. Open PowerShell as admin and run `wsl --install`. Restart, then open "Ubuntu".
2. Inside Ubuntu, run `sudo apt update && sudo apt install -y git make curl`.
3. Install uv (command above) and follow the Linux steps below.

### macOS
`xcode-select --install` gives you git and make. Then install uv.

---

## 2. Get the code and install

```bash
git clone <your-repo-url> raktsetu
cd raktsetu
make install            # runs: uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, creates a `.venv/` folder, and installs the exact versions
of FastAPI, DuckDB, dbt-duckdb, aiohttp, pytest, ruff and the rest.

To run anything inside that environment, put `uv run` in front of it, for example
`uv run python`, `uv run pytest`, or `uv run bloodlake status`.
The Makefile does this for you.

For browser tests and screenshots, also install Chromium once:
```bash
uv run playwright install chromium
```

---

## 3. Get some data

The website needs `serving.duckdb`. There are three ways to get it.

### Option A: Offline demo (fastest, no internet needed)
```bash
make demo-offline
```
This copies `demo/fallback_lakehouse.duckdb` to `serving.duckdb` and starts the server.

### Option B: Full live pipeline (needs internet; takes about 5–15 minutes)
```bash
make pipeline           # = uv run bloodlake all --force
```
You will see:
```
🩸 BLOODLAKE END-TO-END PIPELINE: pipeline_20261022_...
🌐 ... scrape ...
⚙️ STEP 3: dbt Build Transformations
🔍 STEP 4: Quality & Anomaly Gate Validation
📊 Current Reporting Facilities: 4,716
✅ Anomaly gate passed!
🚀 STEP 5: Atomic Database Publish
🎉 PIPELINE COMPLETED IN ...s! Facilities: 4,716
```

### Option C: Run step by step (for learning or debugging)
```bash
make scrape      # 1. eRaktKosh → data/landing/dt=.../hh=.../inventory_*.parquet
make load        # 2. newest Parquet → bronze.raw_inventory
make transform   # 3. dbt build (silver + gold + tests)
make gate        # 4. anomaly gate
make publish     # 5. blood_warehouse.duckdb → serving.duckdb
make status      # see the run history
```
> `make scrape` refuses to run if the last successful run was less than 6 hours ago. To override it, use
> `uv run bloodlake scrape --force`.

---

## 4. Settings (`.env`)

```bash
cp .env.example .env
```

**Important (read this):** the settings class in [`config.py`](../../src/bloodlake/config.py) reads
environment variables **by field name with no prefix**. For example, it reads `SCRAPER_CONCURRENCY`,
**not** `BLOODGRID_SCRAPER_CONCURRENCY`. Most `BLOODGRID_*` lines in `.env.example` are placeholders for
future features (JWT, Razorpay, S3, Telegram) and the current code **does not read them**.

The settings that actually work:

| Variable in `.env` | Default (config.py) | What it controls |
|---|---|---|
| `SCRAPER_CONCURRENCY` | 10 | How many districts are fetched at the same time |
| `SCRAPER_TIMEOUT_SECONDS` | 30 | Seconds before one request gives up |
| `SCRAPER_MAX_RETRIES` | 3 | Retries per district |
| `MIN_RUN_INTERVAL_HOURS` | 6.0 | The run-interval guard |
| `MIN_FACILITY_THRESHOLD_RATIO` | 0.80 | The anomaly gate (0.80 = block if fewer than 80 % of the previous run) |
| `USER_AGENT` | `BloodLake/1.0 (...)` | How the scraper identifies itself |
| `CORS_ORIGINS` | `["*"]` | Which websites may call the API |
| `WAREHOUSE_PATH`, `SERVING_PATH` | project root | Where the DuckDB files live |

dbt reads `BLOODGRID_WAREHOUSE_PATH` from your **shell** (not from `.env`), through `dbt/profiles.yml`.
If it is not set, it uses `blood_warehouse.duckdb`.

> **Never commit `.env`.** It is already in `.gitignore`.

---

## 5. Start the website

```bash
make run        # uvicorn with auto-reload on http://localhost:8000
```

| Open | You should see |
|------|---------------|
| http://localhost:8000 | The Raktsetu website with numbers on the KPI cards |
| http://localhost:8000/docs | Swagger UI listing every API endpoint |
| http://localhost:8000/healthz | `{"status":"healthy",...}` |
| http://localhost:8000/api/v1/meta | Total banks, states and districts |

On your phone (on the same Wi-Fi), open `http://<your-computer-IP>:8000`. "Near me" will **not** work
there, because it is not HTTPS. See [13](13_TROUBLESHOOTING.md#near-me-does-nothing).

---

## 6. Check that everything works

```bash
make test       # pytest: should end with "98 passed"
make lint       # ruff: "All checks passed!"
make dbt-test   # dbt: PASS=… ERROR=0
```

---

## 7. Docker (optional)

```bash
docker compose up --build
```
The container runs only the API and website. It mounts your `serving.duckdb` read-only, so run the
pipeline on the host first. More in [12](12_DEPLOYMENT_AND_OPERATIONS.md).

---

## 8. Common install errors

| Error | Cause | Fix |
|-------|-------|-----|
| `uv: command not found` | uv is not on your PATH | Restart the terminal, or run `source ~/.bashrc` / `~/.zshrc` |
| `requires-python >=3.12` | Your Python is too old | `uv python install 3.12` |
| `make: command not found` | make is not installed | `sudo apt install make` (Linux/WSL), `xcode-select --install` (macOS) |
| `DuckDB database file not found` (HTTP 500) | There is no `serving.duckdb` | `make demo-offline` or `make pipeline` |
| `Metadata catalog missing` | `data/eraktkosh_all_metadata.json` was deleted | `git checkout data/eraktkosh_all_metadata.json` |
| `Minimum run interval guard` | Last scrape was less than 6 h ago | Add `--force` |
| `Address already in use` (port 8000) | Another server is still running | `lsof -i :8000` then `kill <PID>` |
| `IO Error: Could not set lock on file` | Another process has the warehouse open for writing | Close DBeaver / the DuckDB CLI / a second pipeline |
| `Executable doesn't exist ... chromium` | Playwright browser not installed | `uv run playwright install chromium` |
| `dbt: Runtime Error ... profiles.yml` | dbt was run from the wrong folder | Always add `--project-dir dbt --profiles-dir dbt`, or use `make` |

---

Next: [03 · User guide →](03_USER_GUIDE.md)
