# 13 · Troubleshooting Runbook

**What you will learn**
- A general way to debug any problem
- 20 common problems, each with: **symptom → how to check → cause → fix**

---

## 0. A general debugging method

When something is wrong, find **which layer** is broken. Work from the user towards the data:

```text
Browser UI → app.js → network → FastAPI → serving.duckdb → gold → silver → bronze → landing → eRaktKosh
```

1. **Browser:** press F12.
   - **Console** tab: red errors are JavaScript problems.
   - **Network** tab: click the failing `/api/...` request and look at its status code and response.
2. **API:** call it directly and see if the data is right without the UI:
   ```bash
   curl -s "http://localhost:8000/api/search?state=Gujarat&limit=2" | python3 -m json.tool
   ```
3. **Server log:** the terminal running `make run` prints every request and the full Python traceback.
4. **Database:** query the table the endpoint reads (see [07 §5](07_DATABASE.md#5-useful-debugging-queries)).
5. **Pipeline:** `make status` and the `error_message` column.
6. **Raw data:** open the newest Parquet file:
   ```bash
   uv run python -c "import duckdb;print(duckdb.sql(\"select hospital_name, components_raw from 'data/landing/dt=*/hh=*/*.parquet' limit 3\"))"
   ```

If the API answer is right but the screen is wrong, the bug is in `app.js` or the CSS. If the API answer
is wrong, the bug is in `routes.py` or the database.

---

## 1. Pipeline and data

### Scraper: "Circuit Breaker Triggered" or many timeouts
- **Check:** the log shows `HTTP 429` / `5xx` / `TimeoutError`. Also open the eRaktKosh site in a browser.
- **Cause:** eRaktKosh is slow or down, or it is limiting our requests.
- **Fix:**
  - Wait and try again later.
  - Lower the concurrency: `uv run bloodlake scrape -c 4`.
  - Raise the timeout: set `SCRAPER_TIMEOUT_SECONDS=60` in `.env`.
  - The live site keeps serving the old data meanwhile, so there is no emergency.

### Scraper returns 0 records
- **Check:**
  ```bash
  curl -s -A "test" "https://eraktkosh.mohfw.gov.in/eraktkoshPortal/eraktkosh/blood-availability?stateCode=24&districtId=<id>" | head -c 300
  ```
  (take a real id from `data/eraktkosh_all_metadata.json`).
- **Cause:** eRaktKosh changed its URL or response format, or district codes changed.
- **Fix:**
  - Update `eraktkosh_base_url` in `config.py`, or the field names in `write_landing_parquet()`
    (`hospitalCode`, `hospitalname`, `components`, …).
  - Refresh the metadata JSON if the codes changed.

### "Minimum run interval guard"
- **Cause:** a successful run happened less than 6 h ago.
- **Fix:** add `--force`, or change `MIN_RUN_INTERVAL_HOURS`.

### "ANOMALY GATE FAILED" (exit code 3)
- **Check:** `make status` and compare the Facilities counts. Look for missing states:
  ```sql
  SELECT state_name, COUNT(*) FROM bronze.raw_inventory WHERE run_id = '<new run>' GROUP BY 1 ORDER BY 2;
  ```
- **Cause:** the new scrape found far fewer banks, usually because of a partial outage.
- **Fix:**
  - Usually just wait for the next run.
  - If the drop is real (eRaktKosh removed banks), lower `MIN_FACILITY_THRESHOLD_RATIO` for one run,
    then set it back.

### dbt build/test fails
- **Check:** the dbt output names the model or test. Look at the compiled SQL in `dbt/target/compiled/...`
  and run it yourself in DuckDB.
- **Common causes:**
  - **`accepted_values` on blood_group** fails because of a new spelling such as `"A1+VE"`.
    Find it with `SELECT DISTINCT blood_group FROM main_silver.stg_inventory_components`, then add it
    to `dbt/macros/normalize_blood_group.sql`.
  - **`unique` on hospital_code** fails because of duplicates. Check the `ROW_NUMBER` logic in `stg_blood_banks`.
  - A **SQL syntax error** after editing a model.
- **Fix:** fix the model, then `uv run dbt build --project-dir dbt --profiles-dir dbt --select <model>+`.

### The trend chart shows nothing, or "insufficient history"
- **Cause:** only one snapshot exists for that bank and component, or `fct_stock_snapshot` was built
  before the older files were loaded.
- **Fix:** back-fill the landing files ([05 §9](05_DATA_PIPELINE.md#9-re-running-and-back-filling)), then
  `uv run dbt run --project-dir dbt --profiles-dir dbt --select fct_stock_snapshot+ --full-refresh` and
  `make publish`.

### Units look wrong: stock shown that the bank no longer has
- **Check:**
  ```sql
  SELECT * FROM main_gold.fct_stock_snapshot WHERE hospital_code=<id> ORDER BY snapshot_at DESC LIMIT 20;
  ```
- **Cause:** the rule "missing from the latest scrape = 0" lives in `fct_stock_current.sql`. If someone
  removed it, old numbers stay.
- **Fix:** keep `CASE WHEN r.snapshot_at >= l.latest_at THEN r.units ELSE 0 END`.

---

## 2. Database and server

### `IO Error: Could not set lock on file "blood_warehouse.duckdb"`
- **Cause:** another process has the file open for writing: a second pipeline, a DuckDB CLI, DBeaver or a notebook.
- **Check:** `lsof blood_warehouse.duckdb`
- **Fix:** close that program, or open it with `read_only=True` / `duckdb -readonly`.

### API returns 500 "DuckDB database file not found"
- **Cause:** neither `serving.duckdb` nor `blood_warehouse.duckdb` exists.
- **Fix:** `make demo-offline` or `make pipeline`.

### API returns 500 with `Catalog Error: Table ... does not exist`
- **Cause:** the code expects a model that is not in `serving.duckdb` yet. You added a model but did not publish.
- **Fix:** `make transform publish`.

### `Address already in use` (port 8000)
- **Check:** `lsof -i :8000`
- **Fix:** `kill <PID>`, or run on another port:
  `uv run uvicorn bloodlake.api.main:app --port 8001 --reload`.

### Code changes are not picked up
- **Cause:**
  - the server was started without `--reload` (for example by `make demo-offline`);
  - you changed `.env` or `data/district_coords.json`, which are only read once at start-up (`lru_cache`);
  - the old process is still alive.
- **Fix:** stop it with Ctrl+C, check that it is gone (`lsof -i :8000`), and run `make run` again.

### CORS error in the browser console ("blocked by CORS policy")
- **Cause:** the page is served from a different origin than the API (for example a separate frontend
  on port 5500), and that origin is not allowed.
- **Fix:** set `CORS_ORIGINS=["http://localhost:5500"]` in `.env` and restart. Better still, open the site
  through FastAPI on port 8000, which is the same origin.

---

## 3. Website

### Wrong times ("synced −5 h ago", or 5.5 h off)
- **Cause:** a naive timestamp was treated as UTC. DuckDB saves naive times in its session timezone
  (`Asia/Kolkata` here).
- **Check:** `SELECT current_setting('TimeZone');` and compare with what the API returns.
- **Fix:** whenever Python reads a naive time from DuckDB, attach that timezone (the pattern is in
  [01](01_CONCEPTS_FOR_BEGINNERS.md#timezones)). Never use `datetime.now()` without `timezone.utc`.

### "Data may be outdated" banner (stale sync)
- **Check:** `curl -s localhost:8000/api/v1/health/dashboard | python3 -m json.tool | head` and look at `sync_age_hours`. Also run `make status`.
- **Cause:** no successful pipeline run in the last 12 h (the scheduler stopped, or the runs are failing).
- **Fix:** read the `error_message` in `make status`, fix that problem, then `make pipeline`.

### The district dropdown is empty or disabled
- **Check:** Network tab → `/api/locations`. Does it return `{state: [districts]}`?
- **Cause:** the API failed, or the state name in the dropdown does not match the data (spelling or spaces).
- **Fix:** if the API is fine, check `loadLocations()` in `app.js`. If not, see the 500 errors above.

### "Near me" does nothing
- **Check:** the browser shows an alert, or the Console shows a geolocation error.
- **Causes and fixes:**
  - **Not a secure page:** you opened `http://192.168.x.x:8000` on a phone. Use HTTPS (Caddy), or test on
    `localhost`. With Chrome on a computer, you can forward the phone's port 8000 through `chrome://inspect`
    and open `localhost:8000` on the phone.
  - **Permission denied:** click the lock icon in the address bar → Location → Allow.
  - **GPS timeout indoors:** try again. Wi-Fi location is usually enough.

### Map tiles show "API KEY REQUIRED"
- **Cause:** the CARTO key is missing or wrong in `app.js` (`cartoApiKey`).
- **Fix:** put the key back into the tile URL `...light_all/{z}/{x}/{y}{r}.png?key=<key>`.
  If you don't have a key, use OpenStreetMap tiles instead:
  `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` (and credit OSM).

### The map is grey or only half drawn
- **Cause:** Leaflet was set up while its container was hidden.
- **Fix:** call `leafletMap.invalidateSize()` after showing the map view. `initOrUpdateLeafletMap` already does this.

### The CSV looks broken in Excel (garbled Hindi text, everything in one column)
- **Check:** `head -c 3 file.csv | xxd`. It should start with `efbbbf` (the BOM).
- **Cause:**
  - The BOM was removed, so Excel guessed the encoding wrongly.
  - Excel is set to a locale that uses `;` as the separator.
- **Fix:**
  - Keep `export_to_csv_with_bom()`.
  - In Excel, use Data → From Text/CSV → Delimiter: Comma.

### Old JS or CSS keeps loading after a change (service worker)
- **Check:** DevTools → Application → Service Workers. Which version is active?
- **Fix:**
  - **You:** in DevTools, tick "Update on reload", or click **Unregister** and do a hard refresh (Ctrl+Shift+R).
  - **All users:** raise `CACHE_NAME` in `sw.js` (`v5` → `v6`).

### The page scrolls sideways on mobile
- **Check:** in the Console, run
  ```js
  [...document.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > innerWidth)
  ```
  This lists the elements that are too wide.
- **Cause:** a fixed `width`, a long unbroken string (an email address), or a table.
- **Fix:**
  - Use `max-width: 100%`, `minmax(min(Xpx,100%),1fr)` or `overflow-wrap: anywhere`.
  - Wrap tables in a container with `overflow-x: auto`.

### Buttons do nothing, or the page stops halfway
- **Check:** the Console. One JS error stops everything after it in that function.
- **Common cause:** an element `id` was renamed in `index.html` but not in `app.js`, so you get
  `Cannot read properties of null`.
- **Fix:** keep the ids the same in both files. Optional chaining (`?.`) also avoids the crash.

---

## 4. Install and tools

| Symptom | Fix |
|---------|-----|
| `uv: command not found` | Reopen the terminal, or `source ~/.zshrc` |
| `ModuleNotFoundError: bloodlake` | Run through `uv run …` (not bare `python`); run `uv sync` |
| Playwright: `Executable doesn't exist` | `uv run playwright install chromium` |
| `ruff format --check` fails | `make format` |
| Report build: `soffice` / `dot` not found | `sudo apt install libreoffice graphviz` |

---

Next: [14 · Build it yourself →](14_BUILD_IT_YOURSELF.md)
