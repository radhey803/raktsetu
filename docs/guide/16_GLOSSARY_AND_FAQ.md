# 16 · Glossary & FAQ

**What you will learn**
- What every term used in these guides means (A–Z)
- Short answers to common questions, including likely viva questions

---

## Glossary (A–Z)

| Term | Meaning |
|------|---------|
| **ABO / Rh** | The two main blood group systems. ABO gives A, B, AB or O; Rh gives + or −. |
| **ADR** | Architecture Decision Record: a short note explaining why a design choice was made (`docs/adr/`). |
| **Anomaly gate** | A check that stops publishing if the bank count drops below 80 % of the last run. |
| **API** | A set of URLs a program can call to get data (`/api/...`). |
| **async / await** | Python syntax for running tasks that wait on I/O at the same time. |
| **Atomic publish** | Swapping in the new database in one step (`os.replace`), so nobody sees half an update. |
| **Backoff (exponential)** | Waiting longer after each failure (2 s, 4 s, 8 s) before retrying. |
| **Bombay (Oh)** | A very rare blood group with no H antigen; these patients can only receive Bombay blood. |
| **BOM** | Byte Order Mark: 3 bytes at the start of a file that tell Excel it is UTF-8. |
| **Bronze / Silver / Gold** | Raw / cleaned / ready-to-use data layers (the Medallion architecture). |
| **CDN** | Content Delivery Network: servers that host libraries such as Chart.js close to users. |
| **Circuit breaker** | Stops the scraper when more than 20 % of requests fail. |
| **Component** | A product made from blood: PRBC, platelets, plasma, cryo, whole blood… |
| **CORS** | Browser rules about which websites may call an API. |
| **CTE** | `WITH name AS (...)`: a named sub-query in SQL. |
| **Cron** | A time-based schedule (`0 */6 * * *` = every 6 hours). |
| **dbt** | A tool that builds tables from SQL `SELECT` files, in order, with tests. |
| **DFD** | Data Flow Diagram (in the report). |
| **Dimension / Fact table** | Dimension = describes things (banks). Fact = measurements (units). |
| **DuckDB** | A file-based analytics SQL database. |
| **E2E test** | End-to-end test: a robot browser uses the real site. |
| **ELT** | Extract, Load, then Transform inside the database. |
| **Endpoint** | One API URL + method, e.g. `GET /api/v1/rare`. |
| **Fixture** | Fixed test data (`tests/fixtures/`). |
| **FFP** | Fresh Frozen Plasma. |
| **Geocoding** | Turning a place name into latitude/longitude. |
| **Grain** | What one row of a table represents. |
| **Haversine** | A formula for the distance between two GPS points. |
| **Idempotent** | Running it twice gives the same result as running it once. |
| **Immutable** | Never changed after it is written (the landing files). |
| **Incremental model** | A dbt table that only adds new rows on each run. |
| **Jitter** | A small random delay added to the backoff. |
| **KPI** | Key Performance Indicator: the headline numbers. |
| **Lakehouse** | Raw files (lake) + clean SQL tables (warehouse) together. |
| **Landing zone** | `data/landing/`, where raw Parquet files first arrive. |
| **Lineage** | Which table is built from which. |
| **Macro (dbt)** | A reusable SQL snippet (`normalize_blood_group`). |
| **Manifest** | The JSON file next to each Parquet file, with its row count and SHA-256. |
| **Mart** | A gold table made for one feature (`mart_district_status`). |
| **Medallion** | The bronze → silver → gold layering. |
| **Naive timestamp** | A time with no timezone attached. |
| **NBTC** | National Blood Transfusion Council (India). |
| **Network-first** | Try the internet first; use the cache if that fails. |
| **OLAP / OLTP** | Analytics databases / transaction databases. |
| **Parameterised query** | SQL with `?` placeholders. Values are sent separately, which prevents SQL injection. |
| **Parquet** | A compressed, columnar file format. |
| **Partition** | Splitting files into folders by a key (`dt=2026-10-22/hh=06`). |
| **PRBC** | Packed Red Blood Cells. |
| **PWA** | Progressive Web App: an installable website that works offline. |
| **Pydantic** | A Python library for data validation. |
| **Race condition** | When results arrive in an unexpected order. Fixed here with `searchSeq`. |
| **Reliability / trust score** | 0–100: freshness 50 + phone 25 + components 25. |
| **REST** | A style of API built around resource URLs and HTTP methods. |
| **Rh-negative** | Blood without the D antigen. These patients need Rh-negative red cells. |
| **Secure context** | HTTPS or localhost. Required for geolocation. |
| **Semaphore** | A limit on how many tasks run at the same time. |
| **Service worker** | A browser script that sits between the page and the network, for caching and offline use. |
| **SHA-256** | A fingerprint of a file's content; it changes if even 1 byte changes. |
| **Snapshot** | The stock at one point in time. |
| **Stale** | Old data: not updated for more than 30 days (KPI), or more than 12 h since the last sync (banner). |
| **TestClient** | FastAPI's tool for calling the API in tests, without starting a server. |
| **UTC / IST** | World time / India time (UTC + 5:30). |
| **Uvicorn** | The server that runs the FastAPI app. |
| **View vs table** | A view is saved SQL that runs on every read; a table stores the result. |
| **XSS** | Cross-site scripting: injecting a script through data. Prevented with `escapeHTML`. |

---

## FAQ

### About the project
**1. What problem does Raktsetu solve?**
In an emergency, families phone blood bank after blood bank. eRaktKosh has the data but is hard to
search. Raktsetu collects it for all of India every few hours and gives a fast, mobile-friendly search.
It shows compatible groups, freshness and a trust score, and has a call button.

**2. Who are the end users?**
Patient families, doctors and hospital staff, health officials, blood donors, and the operator who runs
the pipeline.

**3. Is this real data?**
Yes. It comes from eRaktKosh (MoHFW). There is no fake data. When there is not enough history, the app
says "insufficient history" instead of inventing a trend.

**4. How fresh is the data?**
The pipeline runs every 6 hours. Each card also shows when **the bank itself** last updated
eRaktKosh, which can be older.

**5. How many blood banks does it cover?**
About 4,700 banks in 35 states/UTs and 700+ districts (check the live numbers at `/api/v1/meta`).

### Architecture
**6. Why DuckDB and not MySQL?**
The workload is analytics: big GROUP BYs over about 66k stock rows, with almost no writes. DuckDB is
built for this, needs no server, and reads Parquet directly. See ADR-001.

**7. Why keep raw Parquet files?**
So we can rebuild every table if a cleaning rule was wrong, and prove exactly what the source said
(the SHA-256 in the manifest).

**8. What is the Medallion architecture?**
Bronze (raw) → silver (cleaned) → gold (business tables). Each layer has one job, so bugs are easy to
find.

**9. Why two database files?**
DuckDB allows only one writer. The pipeline writes to the warehouse and then atomically copies it to
`serving.duckdb`, which the API only reads. Users never see half-updated data or lock errors.

**10. What happens if eRaktKosh goes down during a scrape?**
The circuit breaker stops the run. The anomaly gate also blocks a big drop in banks. Either way, the
site keeps the last good data, and the failure is recorded in `pipeline_runs`.

**11. How do you avoid overloading eRaktKosh?**
At most 10 requests at once, a User-Agent with contact details, exponential backoff on 429/5xx, the
circuit breaker, and a minimum of 6 hours between runs.

**12. Why dbt?**
Transformations are plain SQL files, run in dependency order, with built-in tests (37) and generated
docs.

### Logic
**13. How is the trust score calculated?**
Freshness (up to 50) + a valid phone (25) + reporting 3 or more components (25). High ≥ 75, Medium 40–74, Low < 40.

**14. How does Emergency Mode rank banks?**
0.35·freshness + 0.30·trust + 0.25·units + 0.10·distance (without a location: 0.40/0.35/0.25).
Each card shows a "why ranked here" explanation.

**15. Where do the compatibility rules come from?**
NBTC India and WHO guidelines. They are stored with their source URLs in `data/medical_rules.json`.

**16. Why is plasma compatibility different?**
Plasma carries antibodies instead of antigens, so the rule is reversed: AB is the universal plasma
donor, and Rh does not matter.

**17. How accurate is the map location?**
It is at district level: the district's OpenStreetMap centre plus a small fixed offset, and it is marked
as approximate. eRaktKosh addresses are not clean enough to geocode each hospital reliably.

**18. How is distance calculated?**
With the Haversine (straight-line) formula, using an Earth radius of 6371 km.

**19. If a group disappears from a bank's listing, what do you show?**
0 units. eRaktKosh only lists available groups, so "missing in the latest scrape" means it ran out
(`fct_stock_current`).

### Quality and security
**20. How is the project tested?**
98 pytest unit and integration tests, 37 dbt data tests, a 146-check Playwright browser test at desktop
and mobile sizes, ruff linting, and CI on every push.

**21. How do you prevent SQL injection?**
Every user value is passed as a `?` parameter; it is never pasted into the SQL string.

**22. How do you prevent XSS?**
All API text goes through `escapeHTML()` before it is put into the page.

**23. Is the CSV export safe?**
Yes. Cells starting with `= + - @` get a `'` prefix, which blocks formula injection. The file is UTF-8
with a BOM, so it opens correctly in Excel.

**24. Does it work offline?**
Yes. The service worker caches the app shell and recent API answers (network-first) and shows an
offline banner.

**25. Does it collect personal data?**
No. There are no accounts. Location is used only in the browser for the distance query and is never
stored. The donor checker runs entirely in the browser.

### Limitations and future scope
**26. What are the limitations?**
- Accuracy depends on how often banks update eRaktKosh.
- Locations are district-level.
- There is no live reservation of units.
- There are no forecasts yet.

**27. Why no machine-learning forecasting?**
There isn't enough clean history yet, and a wrong forecast in a medical setting is risky (ADR-003).
It is planned once there are months of snapshots.

**28. What could be added next?**
- SMS/WhatsApp alerts when a rare group becomes available;
- donor registration and blood-drive matching;
- hospital login for direct updates;
- demand forecasting;
- Indian-language versions;
- exact hospital geocoding.

---

← Back to [00 · Start here](00_START_HERE.md)
