# 14 · Build It Yourself (no AI needed)

**What you will learn**
- How to build a **mini Raktsetu** from an empty folder, in 9 milestones
- What to check after each milestone, and the mistakes people usually make
- How to use the same pattern for a completely different dataset

The mini version has the same architecture as the real one
(scrape → Parquet → DuckDB bronze → dbt gold → FastAPI → HTML), but it is about 150 lines in total.
**All the code below has been tested and works.** Type it yourself instead of copy-pasting; you will
learn much more.

---

## Milestone 0: Set up the project

```bash
mkdir mini-blood && cd mini-blood
uv init --python 3.12
uv add aiohttp pyarrow duckdb dbt-duckdb fastapi uvicorn pytest httpx
mkdir -p mini dbt/models && touch mini/__init__.py
```
✅ **Check:** `uv run python -c "import duckdb, fastapi, aiohttp; print('ok')"` prints `ok`.

---

## Milestone 1: Scrape one district

`mini/scrape.py`:
```python
import asyncio, json, sys
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
import pyarrow as pa
import pyarrow.parquet as pq

URL = "https://eraktkosh.mohfw.gov.in/eraktkoshPortal/eraktkosh/blood-availability"
HEADERS = {"User-Agent": "MiniBlood/0.1 (student project; you@example.com)"}


async def fetch(session, sem, state_code, district_id):
    async with sem:                                   # limits how many requests run at once
        params = {"stateCode": state_code, "districtId": district_id}
        async with session.get(URL, params=params, headers=HEADERS, timeout=30) as r:
            r.raise_for_status()
            text = await r.text()
            return json.loads(text) if text.strip() else []


async def scrape(districts):
    sem = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as s:
        results = await asyncio.gather(*(fetch(s, sem, sc, d) for sc, d in districts),
                                       return_exceptions=True)
    rows = []
    for res in results:
        if isinstance(res, Exception):               # one failed district must not kill the run
            print("failed:", res)
            continue
        rows.extend(res)
    return rows
```
(The `__main__` part is in Milestone 2.)

**What to understand:**
- `async`/`await` and `gather` run the requests at the same time.
- The `Semaphore` makes it polite: at most 5 requests at once.
- `return_exceptions=True` keeps the other results when one district fails.

**Common mistakes:**
- calling `fetch()` without `await`;
- forgetting the `User-Agent`;
- making 700 requests with no limit (you will get blocked).

---

## Milestone 2: Save the raw data as Parquet

Add this to `mini/scrape.py`:
```python
def save_parquet(rows):
    now = datetime.now(timezone.utc)
    out = Path("landing") / f"dt={now:%Y-%m-%d}" / f"run_{now:%H%M%S}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({
        "scraped_at": [now] * len(rows),
        "hospital_code": [int(r.get("hospitalCode") or 0) for r in rows],
        "hospital_name": [str(r.get("hospitalname", "")) for r in rows],
        "entry_date": [str(r.get("entrydate", "")) for r in rows],
        "components": [json.dumps(r.get("components", {})) for r in rows],
    })
    pq.write_table(table, out)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1:                      # offline: uv run python -m mini.scrape sample.json
        rows = json.loads(Path(sys.argv[1]).read_text())
    else:
        rows = asyncio.run(scrape([("24", "482")]))   # Gujarat, Anand (codes from the metadata JSON)
    print("saved", save_parquet(rows), len(rows), "rows")
```

To work **without internet**, create `sample.json`:
```json
[{"hospitalCode": 1, "hospitalname": "City Blood Bank", "entrydate": "2026-10-20 10:00:00",
  "components": {"Packed Red Blood Cells": {"available_WithQty": "O+Ve : 4, A-Ve : 1"},
                 "Plasma": {"available_WithQty": "AB+Ve : 2"}}},
 {"hospitalCode": 2, "hospitalname": "Civil Hospital", "entrydate": "2026-10-21 09:00:00",
  "components": {"Packed Red Blood Cells": {"available_WithQty": "O+Ve : 7"}}}]
```

✅ **Check:**
- `uv run python -m mini.scrape` prints `saved landing/dt=.../run_....parquet 7 rows`;
- or, offline, `uv run python -m mini.scrape sample.json`.

**Why save the raw data first?** If your cleaning code has a bug, you can fix it and rebuild. You
never need to download the data again.

---

## Milestone 3: Load into DuckDB (bronze)

`mini/load.py`:
```python
from pathlib import Path

import duckdb

con = duckdb.connect("mini.duckdb")
con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
con.execute("""CREATE TABLE IF NOT EXISTS bronze.raw (
    scraped_at TIMESTAMPTZ, hospital_code BIGINT, hospital_name VARCHAR,
    entry_date VARCHAR, components VARCHAR, source_file VARCHAR)""")
for f in sorted(Path("landing").glob("dt=*/*.parquet")):
    if con.execute("SELECT COUNT(*) FROM bronze.raw WHERE source_file = ?", [str(f)]).fetchone()[0]:
        continue                                  # idempotent: skip files already loaded
    con.execute(
        "INSERT INTO bronze.raw SELECT scraped_at, hospital_code, hospital_name, entry_date, "
        "components, ? FROM read_parquet(?)",
        [str(f), str(f)],
    )
    print("loaded", f)
print(con.sql("SELECT COUNT(*) AS rows FROM bronze.raw"))
```
✅ **Check:** run it **twice**. The second time, the row count must **not** go up (idempotency).

**Common mistake:** `SELECT *` from a `dt=...` folder. DuckDB adds an extra `dt` column (hive
partitioning), and you get "6 columns but 7 values". Always list the columns by name.

---

## Milestone 4: One dbt model (gold)

`dbt/dbt_project.yml`
```yaml
name: mini
version: "1.0"
profile: mini
models:
  mini:
    +materialized: table
    +schema: gold
```
`dbt/profiles.yml`
```yaml
mini:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: ../mini.duckdb
```
`dbt/models/sources.yml`
```yaml
version: 2
sources:
  - name: bronze
    schema: bronze
    tables:
      - name: raw
```
`dbt/models/stock_current.sql`
```sql
-- one row per bank x component x blood group, from the newest scrape only
WITH latest AS (
    SELECT * FROM {{ source('bronze', 'raw') }}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY hospital_code ORDER BY scraped_at DESC) = 1
),
comp AS (
    SELECT hospital_code, hospital_name, CAST(components AS JSON) AS j,
           UNNEST(json_keys(CAST(components AS JSON))) AS component_name
    FROM latest
),
pairs AS (
    SELECT hospital_code, hospital_name, component_name,
           UNNEST(string_split((j -> component_name) ->> 'available_WithQty', ',')) AS pair
    FROM comp
)
SELECT hospital_code, hospital_name, component_name,
       REPLACE(UPPER(TRIM(string_split(pair, ':')[1])), 'VE', '') AS blood_group,
       TRY_CAST(TRIM(string_split(pair, ':')[2]) AS INTEGER) AS units
FROM pairs
WHERE pair LIKE '%:%'
```
`dbt/models/schema.yml`
```yaml
version: 2
models:
  - name: stock_current
    columns:
      - name: hospital_code
        tests: [not_null]
      - name: blood_group
        tests:
          - accepted_values:
              values: ['A+','A-','B+','B-','AB+','AB-','O+','O-','OH+','OH-']
```
✅ **Check:**
- `cd dbt && uv run dbt build --profiles-dir . && cd ..` ends with `PASS=3 ... ERROR=0`;
- `uv run python -c "import duckdb;print(duckdb.connect('mini.duckdb').sql('select * from main_gold.stock_current'))"`.

**What to understand:** `QUALIFY` filters on a window function. `json_keys` + `UNNEST` turns JSON keys
into rows. `string_split(...)[1]` takes the part before the `:` (lists in DuckDB start at 1).

**Common mistakes:**
- the table is called `gold.stock_current` (it is really `main_gold.…`);
- running dbt from the wrong folder;
- leaving the DB open in another program (lock error).

---

## Milestone 5: One API endpoint

`mini/api.py`:
```python
import duckdb
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse

app = FastAPI(title="Mini Blood Finder")


@app.get("/api/stock")
def stock(blood_group: str = Query("O+", max_length=12)):
    con = duckdb.connect("mini.duckdb", read_only=True)
    try:
        rows = con.execute(
            "SELECT hospital_name, component_name, units FROM main_gold.stock_current "
            "WHERE blood_group = ? AND units > 0 ORDER BY units DESC LIMIT 50",
            [blood_group],                    # ← a parameter, never an f-string
        ).fetchall()
    finally:
        con.close()
    return [{"hospital": r[0], "component": r[1], "units": r[2]} for r in rows]


@app.get("/")
def index():
    return FileResponse("index.html")
```
✅ **Check:**
- `uv run uvicorn mini.api:app --reload`, then open http://localhost:8000/docs and try `/api/stock`;
- `curl "localhost:8000/api/stock?blood_group=O%2B"` (`+` must be written as `%2B` in a URL).

---

## Milestone 6: One HTML page

`index.html`:
```html
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mini Blood Finder</title>
<style>body{font-family:sans-serif;max-width:600px;margin:auto;padding:16px}li{padding:4px 0}</style></head>
<body>
<h1>Mini Blood Finder</h1>
<select id="g"><option>O+</option><option>O-</option><option>A+</option><option>A-</option>
<option>B+</option><option>B-</option><option>AB+</option><option>AB-</option></select>
<button id="go">Search</button>
<ul id="out"></ul>
<script>
const esc = s => String(s).replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`);
document.getElementById('go').onclick = async () => {
  const g = document.getElementById('g').value;
  const res = await fetch('/api/stock?blood_group=' + encodeURIComponent(g));
  const rows = await res.json();
  document.getElementById('out').innerHTML = rows.length
    ? rows.map(r => `<li>${esc(r.hospital)} - ${esc(r.component)}: <b>${r.units}</b></li>`).join('')
    : '<li>No stock found</li>';
};
</script>
</body>
</html>
```
✅ **Check:** open http://localhost:8000, choose O+ and press Search. The banks appear.

**Common mistakes:**
- forgetting `encodeURIComponent` (`O+` becomes `O ` with a space);
- putting data into `innerHTML` without escaping it (XSS).

---

## Milestone 7: Run it on a schedule

`run.sh`:
```bash
#!/usr/bin/env bash
set -e                                     # stop at the first error
cd "$(dirname "$0")"
uv run python -m mini.scrape
uv run python mini/load.py
(cd dbt && uv run dbt build --profiles-dir .)
```
Make it executable with `chmod +x run.sh`, then add it to `crontab -e`:
`0 */6 * * * /path/to/mini-blood/run.sh >> run.log 2>&1`

**Next steps to add** (all of them are in the real project):
- a quality gate (stop if the row count drops a lot);
- a separate serving copy of the DB (atomic publish);
- a run log table.

---

## Milestone 8: Tests

`mini/test_mini.py`:
```python
from fastapi.testclient import TestClient

from mini.api import app


def test_o_positive_found():
    r = TestClient(app).get("/api/stock", params={"blood_group": "O+"})
    assert r.status_code == 200
    assert r.json()[0]["units"] == 7
```
✅ **Check:** after loading `sample.json`, `uv run pytest -q` gives `1 passed`.

---

## Milestone 9: Deploy

1. Rent a small VPS and install `uv` and `caddy`.
2. `git clone`, then `uv sync`, then `./run.sh`.
3. Run the server as a service:
   `uv run uvicorn mini.api:app --host 127.0.0.1 --port 8000` (use systemd or `tmux`).
4. Caddyfile: `yourdomain.in { reverse_proxy localhost:8000 }`. HTTPS is set up automatically.

The full version is in [12](12_DEPLOYMENT_AND_OPERATIONS.md).

---

## From mini to full Raktsetu: what to add next

| Add | Learn from |
|-----|-----------|
| All districts from the metadata JSON + retry/backoff + circuit breaker | `src/bloodlake/scraper.py` |
| Manifest + SHA-256 + immutability | `write_landing_parquet()` |
| Proper blood group normalisation | `dbt/macros/normalize_blood_group.sql` |
| History (incremental) + "missing = 0" | `fct_stock_snapshot.sql`, `fct_stock_current.sql` |
| Trust score, shortages, rare blood | `mart_*.sql` |
| Compatibility rules | `medical.py` + `data/medical_rules.json` |
| Location + distance | `geo.py` |
| Gate + atomic publish + run log | `pipeline.py` |
| Map, charts, PWA | `web/` |

---

## Using the pattern for another dataset

This pattern works for any **public data that changes over time**. Some examples:
- hospital bed availability;
- mandi (crop market) prices from data.gov.in / Agmarknet;
- air quality (CPCB);
- fuel prices;
- bus or train delays;
- vaccine stock.

**Checklist:**
1. ☐ **Source:** is it public? Read the terms and `robots.txt`. Is there an official API? Prefer that.
2. ☐ **Unit of fetching:** what does one request return (per district, per station, per day)? List all the keys you will need.
3. ☐ **Politeness:** a concurrency limit, a User-Agent with your contact, backoff, and a minimum interval.
4. ☐ **Raw storage:** Parquet partitioned by date, never overwritten, keeping the full raw JSON.
5. ☐ **Grain:** write it down in one sentence, e.g. "one row per station × pollutant × hour".
6. ☐ **Silver:** clean the types, trim, de-duplicate (`ROW_NUMBER`), and normalise the categories (a macro).
7. ☐ **Gold:** the "current" table, the history (incremental) table, and 1–3 tables for user questions.
8. ☐ **Tests:** not_null/unique on keys, accepted_values on categories, and a count-drop gate.
9. ☐ **API:** one endpoint per screen; parameters validated; SQL always parameterised.
10. ☐ **UI:** mobile first; show **how fresh** each number is; let users export.
11. ☐ **Trust:** show the source, the last update time and a disclaimer.
12. ☐ **Ops:** a schedule, a run log, a health endpoint and backups of the raw files.

---

Next: [15 · Tech stack reference →](15_TECH_STACK_REFERENCE.md)
