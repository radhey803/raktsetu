# 08 · Backend API

**What you will learn**
- How FastAPI starts and serves both the API and the website
- Every endpoint: its parameters, an example answer and how it works
- How validation (Pydantic), the DB connection and CORS work
- How to add a new endpoint

Files:
- [`api/main.py`](../../src/bloodlake/api/main.py): the app, static files, legacy `/api/*` routes;
- [`api/routes.py`](../../src/bloodlake/api/routes.py): all `/api/v1/*` routes;
- [`api/schemas.py`](../../src/bloodlake/api/schemas.py): the response shapes;
- [`db.py`](../../src/bloodlake/db.py): DB connections;
- [`config.py`](../../src/bloodlake/config.py): settings.

---

## 1. How the server starts

```bash
uv run uvicorn bloodlake.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Uvicorn** is the web server. It runs the `app` object found in `bloodlake/api/main.py`.
- `--reload` restarts it whenever you save a `.py` file. Use this only during development.

What `main.py` does, from top to bottom:
1. `app = FastAPI(title=..., docs_url="/docs", redoc_url="/redoc")` creates the app.
2. `CORSMiddleware` lets other websites call the API. It uses `allow_origins=settings.cors_origins`
   (default `*`) and `allow_credentials=False`, because browsers reject credentials with `*`.
3. `app.include_router(router)` adds every route from `routes.py`.
4. Static files: `/css`, `/js`, `/assets` are served from `web/`, and `/dbt-docs` from `dbt/target`
   if those docs have been generated.
5. Page routes: `/` and `/dashboard` return `web/index.html`; `/manifest.json`; `/sw.js` (with the
   header `Service-Worker-Allowed: /`).

### The DB connection for each request
```python
def get_db_session():
    con = get_serving_connection(read_only=True)
    try:
        yield con          # FastAPI gives this to the endpoint
    finally:
        con.close()        # always closed, even after an error
```
An endpoint asks for it with `con: duckdb.DuckDBPyConnection = Depends(get_db_session)`.
This is called **dependency injection**: FastAPI creates the connection for each request and cleans it up afterwards.

### Validation
`Query(15, ge=1, le=100)` means: the default is 15, and the value must be at least 1 and at most 100.
If it is not, FastAPI answers **422** automatically, with a clear message.
`response_model=EmergencyResponse` makes the output follow the schema exactly.

---

## 2. Endpoint list

Try them all at **http://localhost:8000/docs**.

| Method + path | Used by | Purpose |
|---|---|---|
| `GET /healthz` | Docker healthcheck | Is the API up? |
| `GET /api/v1/meta` | — | Project info, last sync, total facilities |
| `GET /api/v1/summary` (also `/api/summary`) | KPI cards, state chart | National totals |
| `GET /api/v1/locations` (also `/api/locations`) | State and district dropdowns | `{state: [districts]}` |
| `GET /api/search` | **Blood finder, map** | Search with sorting and distance (in `main.py`) |
| `GET /api/v1/banks` | — | Paginated list of banks |
| `GET /api/v1/availability` | — | Paginated stock rows |
| `GET /api/v1/emergency` | **Emergency Mode** | Compatible groups + ranked banks |
| `GET /api/v1/medical/rules` | — | Contents of `medical_rules.json` |
| `GET /api/v1/history` | — | Trend for one group |
| `GET /api/history` | **Trend modal** | Trend for all groups, last N days |
| `GET /api/v1/shortages` (also `/api/shortages`) | **Shortages table** | District shortage radar |
| `GET /api/v1/rare` (also `/api/rare`, `/api/v1/rare-blood`) | **Rare Blood Radar** | Rh-negative and Bombay stock |
| `GET /api/v1/health/dashboard` | **Data Health panel** | Sync age, stale states, runs, dbt tests |
| `GET /api/v1/export/availability.csv` | Export button | CSV download |
| `GET /api/v1/export/shortages.csv` | Export button | CSV download |

The "legacy" paths (`/api/search`, `/api/summary`, …) are older short URLs that the frontend still uses.
They are hidden from `/docs` (`include_in_schema=False`) but they work.

---

## 3. Endpoints in detail

### `GET /healthz`
```json
{"status":"healthy","database":"DuckDB Lakehouse","timestamp":"2026-10-21T19:23:26+00:00"}
```

### `GET /api/v1/summary`
```json
{"total_banks":4716,"total_states":35,"fresh_banks_24h":3272,"stale_banks_30d":292,
 "top_states":[{"state":"Uttar Pradesh","banks":677}, ...]}
```
- **Fresh** = `source_updated_at` in the last 24 h.
- **Stale** = not updated for more than 30 days.

### `GET /api/search`: the main finder
| Param | Default | Notes |
|-------|---------|-------|
| `state`, `district` | — | `ALL` or empty = no filter |
| `component` | `Packed Red Blood Cells` | `ALL` = sum of every component |
| `blood_group` | — | e.g. `O-` |
| `search_query` | — | Text inside the name or address (uses `contains(LOWER(...))`) |
| `sort` | `freshness` | `freshness` / `units` / `reliability` / `distance` |
| `lat`, `lng` | — | Needed for distance |
| `limit` | 300 | 1–10000 (the frontend asks for 10000 and pages through them itself) |

**How it works:**
1. It builds a `WHERE` list with `?` placeholders. User text is **never** pasted into the SQL.
2. A sub-query sums the units for each bank and group:
   ```sql
   SELECT hospital_code, blood_group, SUM(units) AS units, MAX(source_updated_at) ...
   FROM main_gold.fct_stock_current {comp_clause} GROUP BY hospital_code, blood_group
   ```
3. It joins `dim_blood_banks` (details) and `mart_reliability_score` (trust).
4. `string_agg(blood_group || ': ' || units)` gives a `stock` string such as `"A+: 3, O-: 1"`.
5. `COUNT(*) OVER ()` gives the total number of matches before the `LIMIT`.
6. In Python, it adds coordinates from `resolve_facility_lat_lng` and the distance from `haversine_distance_km`.
7. With `sort=distance`, it fetches **all** matches, sorts them by distance in Python, then cuts to `limit`.

### `GET /api/v1/emergency`: Emergency Mode
| Param | Default | Notes |
|-------|---------|-------|
| `patient_blood_group` (or `blood_group`) | **required** | Missing → **400**. Unknown group → **422** |
| `component` | `Packed Red Blood Cells` | Plasma uses different rules |
| `state`, `district` | — | Filters |
| `lat`, `lng` | — | Turn on distance ranking |
| `radius_km` | — | 0 < r ≤ 3000; only banks within the radius |
| `limit` | 5 | 1–20 |

**Algorithm:**
1. `get_compatible_donor_groups(group, component)` returns the allowed donor groups, a warning and the
   source ([09](09_DOMAIN_LOGIC.md)).
2. SQL: the component matches, the group is in the allowed list, and `units > 0`. The result is grouped
   per bank: total units + a breakdown per group.
3. For each bank, it calculates four factors from 0 to 100:

| Factor | Formula |
|--------|---------|
| Freshness | ≤1 day: 100, ≤3: 70, ≤7: 40, ≤14: 16, else 0 |
| Trust | `reliability_score` |
| Units | `min(100, units × 10)`, so 10 or more units = 100 |
| Distance | `max(0, 100 − km)` |

4. **Rank score:**
   - with a location: `0.35·fresh + 0.30·trust + 0.25·units + 0.10·distance`
   - without a location: `0.40·fresh + 0.35·trust + 0.25·units`
5. It writes `why_ranked_here`, for example
   `"12 units (8 O-, 4 O+), updated today, trust 100/100 (High), approx. 3.4 km away"`.
6. It sorts by score and returns the top `limit`.

**Response (shortened):**
```json
{
  "patient_blood_group": "O-",
  "compatible_donor_groups": ["O-"],
  "is_rh_negative": true,
  "clinical_warning": "Rh-Negative Protocol: ...",
  "source_attribution": "NBTC India Blood Transfusion Guidelines & WHO BTS (...)",
  "disclaimer": "Guidance only, not medical advice. ...",
  "total_found": 2370,
  "top_facilities": [{"hospital_code": 283595, "total_compatible_units": 12,
                      "units_by_group": {"O-": 12}, "rank_score": 91.5, "why_ranked_here": "..."}]
}
```
The frontend widens the radius by itself: it calls with `radius_km=50`, and if nothing comes back, `150`, then `400`.

### `GET /api/history`: trend modal
Params: `hospital_code` (required), `component`, and `days` (14, range 1–90).
It reads `fct_stock_snapshot` and returns one series per blood group. Days with no snapshot are
returned as `null`, so the chart shows a **gap** instead of a false zero.

`/api/v1/history` does the same for **one** group:
```json
{"hospital_code":323,"blood_group":"B+","points":[{"snapshot_date":"2026-10-14","units":2}, ...],
 "has_sufficient_history":true}
```

### `GET /api/v1/shortages`
Params: `state`, `blood_group` (`O-`), `component`, `limit` (50).
It reads `mart_district_status` and sorts by severity.
```json
[{"state_name":"Andhra Pradesh","district_name":"Anakapalli","blood_group":"O-","total_units":0,
  "reporting_banks":2,"banks_with_zero":2,"shortage_status":"CRITICAL_DEPLETION","severity_score":100}]
```

### `GET /api/v1/rare`
Params: `state`, `district`. It returns rows from `mart_rare_blood_availability`, with Bombay first.

### `GET /api/v1/health/dashboard`
```json
{"status":"healthy","last_successful_sync":"...","sync_age_hours":3.2,"is_stale_warning":false,
 "stale_warning_threshold_hours":12,"total_facilities":4716,"stale_by_state":[...],
 "recent_pipeline_runs":[...],"dbt_tests_summary":{"total_tests":37,"passed":37,"status":"PASSING"}}
```
- `dbt_tests_summary` is read from `dbt/target/run_results.json` (`_dbt_tests_summary()`).
- `sync_age_hours` uses the timezone fix from [01](01_CONCEPTS_FOR_BEGINNERS.md#timezones).

### CSV exports
- `/api/v1/export/availability.csv?state=&district=&blood_group=&component=&search=` returns all
  matching rows, with **no limit**.
- `/api/v1/export/shortages.csv?state=&blood_group=&component=`

Both use [`export.py`](../../src/bloodlake/export.py):

| Rule | Why |
|------|-----|
| UTF-8 **BOM** at the start | Excel then reads Indian-language names correctly |
| Header in the first row, no comment lines | pandas and Sheets read it straight away |
| CRLF (`\r\n`) line endings | The RFC 4180 CSV standard |
| `split_contact()` gives separate Phone and Email columns | Easy to filter and dial |
| `_clean()` adds `'` before `= + - @` | Stops **CSV formula injection** (a cell like `=HYPERLINK(...)` running in Excel) |
| A `Source` column | Credits eRaktKosh |

---

## 4. Error responses

| Code | When | Body |
|------|------|------|
| 400 | Emergency search without a group | `{"detail":"Missing required parameter: patient_blood_group ..."}` |
| 422 | Invalid parameter (e.g. `limit=0`) or unknown group | `{"detail": [...]}` or `"Unknown blood group: X"` |
| 500 | No database file | `"DuckDB database file not found or inaccessible. Please run pipeline first."` |

---

## 5. Testing an endpoint by hand

```bash
curl -s "http://localhost:8000/api/v1/emergency?patient_blood_group=AB-&limit=2" | python3 -m json.tool
curl -s "http://localhost:8000/api/search?state=Gujarat&district=Anand&limit=3" | python3 -m json.tool
curl -sOJ "http://localhost:8000/api/v1/export/shortages.csv?blood_group=O-"   # saves the file
```

---

## 6. How to add a new endpoint

Example: total units per state (using the model from [06 §6](06_DBT_MODELS.md#6-how-to-add-a-new-model-example)).

```python
# src/bloodlake/api/routes.py
@router.get("/api/v1/state-units")
def get_state_units(
    blood_group: str = Query("O-", description="Blood group"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    rows = con.execute(
        "SELECT state_name, total_units FROM main_gold.mart_state_units "
        "WHERE blood_group = ? ORDER BY total_units DESC",
        [blood_group],                    # ← always pass values as parameters
    ).fetchall()
    return [{"state": r[0], "units": r[1]} for r in rows]
```
Then:
1. Open `/docs` and try it.
2. Add a test in `tests/integration/test_api.py` ([11](11_TESTING.md)).
3. Call it from `app.js` with `fetch('/api/v1/state-units?blood_group=O-')`.

---

Next: [09 · Domain logic →](09_DOMAIN_LOGIC.md)
