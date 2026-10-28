# 01 · Concepts for Beginners

**What you will learn**
- Every technical idea this project uses, in plain English
- A real-life comparison for each one
- Where each idea appears in Raktsetu

Read this once from top to bottom. Later, come back to it when a word confuses you.

---

## Part A: How the web works

### Client and server
- **What:** the *client* asks for something; the *server* answers.
- **Analogy:** you (client) order at a restaurant counter; the kitchen (server) prepares the food.
- **In Raktsetu:** your browser is the client. FastAPI (`src/bloodlake/api/`) is the server. The
  scraper is *also* a client: it asks the eRaktKosh server for data.

### HTTP, URL and status codes
- **HTTP** is the language clients and servers speak. A request has a **method** (`GET` = read,
  `POST` = send) and a **URL**.
- **Query parameters** are the part after `?`, for example `/api/v1/emergency?patient_blood_group=O-&limit=5`.
- **Status codes** say how it went:

| Code | Meaning | Where you see it here |
|------|---------|-----------------------|
| 200 | OK | Normal answers |
| 400 | Bad request (something missing) | Emergency search without a blood group |
| 422 | Input not valid | Unknown blood group, or `limit=0` |
| 429 | Too many requests | eRaktKosh asks the scraper to slow down |
| 500 | Server error | The database is missing |
| 503 | Service unavailable | The service worker answers this when you are offline |

### JSON
Text that stores data as `{"key": value}`. Both the API and eRaktKosh answer in JSON.

```json
{"hospital_name": "Civil Hospital Anand", "blood_group": "O-", "units": 4}
```

### API and REST
- **API** (Application Programming Interface): a fixed set of URLs a program can call to get data.
- **REST** is a common style for this: each URL is a "resource" (`/api/v1/shortages`) and you use
  GET to read it.
- **In Raktsetu:** every `/api/...` URL. There is a full list in [08_BACKEND_API.md](08_BACKEND_API.md).
  Open `http://localhost:8000/docs` to try them in your browser.

---

## Part B: Collecting data

### Web scraping, and doing it politely
- **What:** a program that calls a website the same way a browser does, and saves the answer.
- **Analogy:** instead of phoning 700 blood banks yourself, a helper phones them all and writes the answers down.
- **Polite scraping** means you don't overload the source:
  - **Limit how many calls run at once.** Here that limit is 10 (`asyncio.Semaphore`).
  - **Say who you are.** The `User-Agent` header carries a contact email.
  - **Back off when the server says "slow down"** (HTTP 429 or 5xx): wait 2, then 4, then 8 seconds.
  - **Stop completely if more than 20 % of calls fail.** This is the **circuit breaker**.
  - **Don't run again too soon.** The run-interval guard waits at least 6 hours unless you pass `--force`.
- **In Raktsetu:** [`scraper.py`](../../src/bloodlake/scraper.py). The details are in [05](05_DATA_PIPELINE.md).

### Sync vs async
- **Sync (synchronous):** do one call, wait, then do the next. 700 districts × 2 s = more than 20 minutes.
- **Async (asynchronous):** start a call, and *while waiting* start others. That is about 10 times faster.
- **Analogy:** a cook who starts the rice, and chops vegetables while it boils, instead of standing and watching it.
- **In Python:** `async def`, `await`, `asyncio.gather(...)`. The library `aiohttp` makes the async HTTP calls.

---

## Part C: Storing data

### CSV vs Parquet
| | CSV | Parquet |
|---|---|---|
| Format | Plain text, row by row | Binary, **column by column** |
| Size | Large | Small (compressed; here with zstd) |
| Data types | Everything is text | It knows int, string and timestamp |
| Best for | Opening in Excel | Analytics, and keeping raw data |

- **Analogy:** CSV is a notebook written line by line. Parquet is a filing cabinet with one drawer per
  column. If you only need the "units" column, you open one drawer.
- **In Raktsetu:** raw scrapes are saved as Parquet in `data/landing/`. Users download CSV from the website.

### Database, OLTP vs OLAP
- **OLTP** (for example PostgreSQL or MySQL): many small writes, such as bank transactions.
- **OLAP** (for example DuckDB): few writes, big read queries such as "sum all units by district".
- Raktsetu is read-heavy analytics, so it uses **DuckDB**: an OLAP database that is *just a file*, with no
  server to install. See [ADR-001](../adr/ADR-001-duckdb-for-analytics-postgres-for-app-state.md).

### Data warehouse, data lake, lakehouse
- **Data lake:** a folder of raw files (our Parquet files).
- **Data warehouse:** clean tables you can query with SQL (our DuckDB gold tables).
- **Lakehouse:** both at once. Raw files are kept forever *and* clean tables are built from them.
  If a cleaning rule was wrong, you fix it and rebuild from the raw files.

### Medallion architecture (bronze → silver → gold)
| Layer | Meaning | Raktsetu table |
|-------|---------|----------------|
| **Bronze** | Raw, exactly as received | `bronze.raw_inventory` |
| **Silver** | Cleaned: trimmed, typed, de-duplicated, one row per blood group | `main_silver.stg_blood_banks`, `stg_inventory_components` |
| **Gold** | Ready to use: business tables for the app | `main_gold.fct_stock_current`, `mart_reliability_score`, … |

**Analogy:** bronze is raw vegetables, silver is washed and chopped vegetables, gold is the cooked dish.

### ETL vs ELT
- **ETL:** Extract → Transform → Load. You clean the data *before* storing it.
- **ELT:** Extract → Load → Transform. You store the raw data first and clean it inside the database.
- Raktsetu uses **ELT**: raw data goes into bronze, and dbt transforms it there with SQL.

### dbt (data build tool)
You write each table as a `SELECT` statement in a `.sql` file. dbt:
- runs the files in the right order (`ref('...')` tells it what depends on what);
- creates each view or table;
- runs **tests** such as "this column is never null" or "this value is unique".

All the models are explained in [06](06_DBT_MODELS.md).

---

## Part D: Making data trustworthy

### Idempotency
- **What:** doing something twice gives the same result as doing it once.
- **In Raktsetu:** loading the same Parquet file twice does **not** create duplicate rows. The loader
  checks if the `run_id` is already in bronze (`ingest_landing_to_bronze` in `pipeline.py`).

### Atomic publish
- **What:** a change happens *completely or not at all*. Nobody ever sees it half-done.
- **How:** copy the warehouse to `serving.duckdb.tmp`, then **rename** it to `serving.duckdb`
  (`os.replace`). On one disk, a rename is instant and all-or-nothing.
- **Analogy:** you prepare a new menu board in the back room, then swap it with the old board in one move.

### Data quality gate
- **What:** an automatic check that blocks bad data from going live.
- **In Raktsetu:**
  1. the dbt tests (not null, unique, accepted values);
  2. the **anomaly gate**: if today's blood bank count is less than **80 %** of the last good run,
     something broke, so the pipeline does not publish.

### Timezones
- **UTC** is world time. **IST** (Asia/Kolkata) is UTC + 5:30.
- A timestamp with **no timezone attached** ("naive") is dangerous, because 10:00 could mean UTC or IST.
- **In Raktsetu:** DuckDB uses the machine's timezone (here `Asia/Kolkata`). Naive timestamps read
  from DuckDB are treated as being in that zone:

  ```python
  # src/bloodlake/scraper.py, check_run_interval_guard
  if last_run_time.tzinfo is None:
      last_run_time = last_run_time.replace(
          tzinfo=ZoneInfo(con.execute("SELECT current_setting('TimeZone')").fetchone()[0]))
  ```

  If you forget this, "last synced" can show **−5 hours** or 5 hours too old.

---

## Part E: The website

### Vanilla JavaScript
"Vanilla" means plain JavaScript with no React or Vue. One file, [`web/js/app.js`](../../web/js/app.js), does
everything: it calls the API with `fetch()`, builds HTML and adds click handlers.

### PWA (Progressive Web App)
A website that can be **installed** like an app and **works offline**. It needs:
- `manifest.json`: the app name, icons and colours;
- `sw.js`: a **service worker**.

### Service worker and caching
- **What:** a small script the browser runs *between* the page and the network. It can save responses
  (a **cache**) and return them when you are offline.
- **Strategy used here: network-first.** It tries the internet first. If that fails, it uses the saved copy.
  This way you get fresh data when you are online and old data when you are offline.
- **Analogy:** a secretary who phones for the latest news, and reads yesterday's notes if the phone line is dead.

### Responsive design
The same page adapts to phone, tablet and desktop using CSS **media queries**
(`@media (max-width: 640px) { ... }`). See [10](10_FRONTEND.md).

### Geolocation and secure context
- `navigator.geolocation` asks the browser for your GPS position. It works **only on HTTPS or localhost**
  (a "secure context"), and only after the user allows it.
- **In Raktsetu:** the "Near me" and "Use my location" buttons.

### Haversine formula
It calculates the distance between two latitude/longitude points on a sphere (the Earth, radius 6371 km).
It gives the straight "as the crow flies" distance, not the road distance.
The code is `haversine_distance_km` in [`geo.py`](../../src/bloodlake/geo.py).

### Geocoding
Turning a place name ("Anand, Gujarat") into coordinates (22.56, 72.93). Here it was done once with
OpenStreetMap's **Nominatim** service, and the result is saved in `data/district_coords.json`.

---

## Part F: Engineering habits

| Idea | Meaning | Here |
|------|---------|------|
| **Unit test** | Tests one function on its own | `tests/unit/` |
| **Integration test** | Tests parts working together (API + DB) | `tests/integration/` |
| **E2E test** | A robot browser clicks through the site | Playwright |
| **Linting** | Automatic code-style checks | `ruff` |
| **CI** | Tests run automatically on every push | `.github/workflows/ci.yml` |
| **Cron / schedule** | Runs a job at fixed times | `pipeline.yml`, every 6 h |
| **Container** | Packs the app and everything it needs into one image | `Dockerfile` |
| **ADR** | A short note on why a decision was made | `docs/adr/` |

---

Next: [02 · Installation →](02_INSTALLATION.md)
