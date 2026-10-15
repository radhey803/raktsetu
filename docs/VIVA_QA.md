# eRaktKosh Blood Lakehouse: Comprehensive Viva Voce Examination Guide

**Institution**: Charotar University of Science and Technology (CHARUSAT)  
**Department**: Department of Computer Applications (MCA Program)  
**Project**: eRaktKosh Blood Lakehouse (Academic Mini Project — 800 Marks)  
**Topics Covered**: Modern Data Engineering, Lakehouse Architecture, In-Process OLAP, dbt Transformations, Asynchronous Ingestion, Data Quality Contracts, and Full-Stack System Design.

---

## Table of Contents
1. [Part I: Modern Data Engineering & Lakehouse Architecture (Q1 – Q15)](#part-i-modern-data-engineering--lakehouse-architecture)
2. [Part II: Ingestion, Scraping, Network Engineering & Ethics (Q16 – Q28)](#part-ii-ingestion-scraping-network-engineering--ethics)
3. [Part III: Data Quality, Normalization & Analytics Engineering (Q29 – Q42)](#part-iii-data-quality-normalization--analytics-engineering)
4. [Part IV: Backend Architecture, REST API & Frontend Design (Q43 – Q52)](#part-iv-backend-architecture-rest-api--frontend-design)
5. [Part V: Testing, Reliability, Scalability & Viva Defense (Q53 – Q60)](#part-v-testing-reliability-scalability--viva-defense)

---

## Part I: Modern Data Engineering & Lakehouse Architecture

### Q1: What is a Data Lakehouse, and how does it differ from a traditional Data Warehouse or Data Lake?
**Answer**:  
A **Data Lake** stores vast volumes of raw, unstructured or semi-structured data (like raw JSON or Parquet) affordably, but lacks ACID transaction guarantees, schema enforcement, and fast indexing. A **Data Warehouse** (like Snowflake or traditional OLTP databases) provides strong schema enforcement and fast SQL queries, but is expensive, rigid, and tightly coupled to proprietary storage.  
A **Data Lakehouse** merges both: it keeps raw data in open, immutable file formats (like Parquet in our `data/landing/` directory) while providing an ACID-compliant, high-performance SQL query engine (DuckDB) on top with schema enforcement and versioned transformations via dbt.

### Q2: Why did you choose an ELT approach instead of traditional ETL?
**Answer**:  
In traditional **ETL (Extract-Transform-Load)**, data is transformed in-flight before loading into the database. If business requirements change or an error occurs during parsing, the raw data is lost and must be re-fetched.  
In our **ELT (Extract-Load-Transform)** pattern:
1. **Extract & Load**: We extract raw JSON from 781 districts and load it verbatim into immutable Parquet files and the Bronze layer (`bronze.raw_inventory`).
2. **Transform**: All normalization, JSON unnesting, and aggregation are executed declaratively in SQL using dbt inside DuckDB. If our normalization rules change (e.g., adding a new component or group), we simply re-run dbt models without re-scraping the upstream portal.

### Q3: Explain the Medallion Architecture implemented in your project.
**Answer**:  
We follow the industry-standard three-tier Medallion pattern:
- **Bronze (`bronze.raw_inventory`)**: Append-only ingestion table that stores raw portal responses, ingestion run IDs, and original JSON strings without altering data types or structures.
- **Silver (`silver.stg_blood_banks`, `silver.stg_inventory_components`)**: Cleans, deduplicates, and unnests the data. It explodes nested JSON component arrays into atomic rows, sanitizes phone numbers, normalizes blood group names, and joins district centroid coordinates.
- **Gold (`gold.dim_blood_banks`, `gold.fct_stock_current`, `gold.fct_stock_snapshot`, `gold.mart_reliability_score`, etc.)**: Star-schema dimensional models and business marts optimized for sub-millisecond API queries and dashboard analytics.

### Q4: Why did you choose DuckDB over traditional databases like PostgreSQL, MySQL, or SQLite?
**Answer**:  
1. **OLAP Columnar Vectorization**: DuckDB uses vectorized columnar execution. When filtering `fct_stock_current` across 40,000+ stock rows for `blood_group = 'O-'` and computing sums, it scans only the required column chunks in CPU L1/L2 caches, executing queries in $<5$ ms. Traditional row-oriented databases (PostgreSQL/MySQL) load entire rows from disk into memory.
2. **Embedded Zero-Latency Serverless Deployment**: DuckDB runs in-process inside the Python runtime—there is no network hop, socket overhead, or separate database daemon to manage.
3. **Direct Parquet Reading**: DuckDB can query and ingest Parquet files directly using vectorized SIMD instructions without intermediate CSV conversions.
4. **Superior to SQLite for Analytics**: SQLite is row-oriented and lacks modern analytical window functions, parallel query execution, and rich native JSON unnesting functions.

### Q5: What is dbt (data build tool), and why is it used in this project?
**Answer**:  
dbt Core is an open-source analytics engineering framework that allows software engineering best practices to be applied to data transformations:
- **SQL Modularity**: Models are written as declarative `SELECT` queries with Jinja templating.
- **DAG Lineage**: dbt automatically builds a Directed Acyclic Graph (DAG) determining execution dependencies (`bronze` $\rightarrow$ `silver` $\rightarrow$ `gold`).
- **Data Testing**: Enforces constraints (`unique`, `not_null`, `accepted_values`, foreign keys) directly in SQL.
- **Documentation**: Automatically compiles lineage graphs and documentation (`dbt docs`).

### Q6: What is idempotency, and how does your data pipeline guarantee it?
**Answer**:  
An operation is **idempotent** if running it multiple times produces the exact same end state without side effects or duplicates.  
In our pipeline:
1. Each ingestion assigns an immutable `run_id`.
2. The atomic swap pattern builds the warehouse in a staging database (`blood_warehouse.duckdb`) and performs an atomic copy to `serving.duckdb`.
3. In `fct_stock_snapshot`, an incremental merge key `[hospital_code, component_name, blood_group, snapshot_date]` prevents duplicate records if the pipeline is triggered multiple times on the same calendar day.

### Q7: Explain the difference between Table, View, and Incremental materializations in dbt.
**Answer**:  
- **View (`materialized='view'`)**: A saved SQL query. No data is stored physically; the query executes every time the view is referenced. We use this for Silver staging models (`stg_inventory_components`) to avoid data duplication.
- **Table (`materialized='table'`)**: Physical storage on disk created via `CREATE TABLE AS SELECT ...`. Provides maximum query performance for frequently queried marts like `dim_blood_banks` and `fct_stock_current`.
- **Incremental (`materialized='incremental'`)**: Only processes new or modified records since the last run. We use this for `fct_stock_snapshot` to append daily snapshots efficiently without re-computing historical snapshots.

### Q8: How does DuckDB handle concurrent reads and writes?
**Answer**:  
DuckDB enforces a single-writer, multi-reader concurrency model. If a process opens a DuckDB database in read-write mode, it holds an exclusive file lock.  
To prevent API readers from being blocked while a pipeline run writes new data:
1. The batch pipeline writes exclusively to `blood_warehouse.duckdb`.
2. Upon passing the validation gate, the pipeline atomically replaces `serving.duckdb`.
3. FastAPI opens `serving.duckdb` in **Read-Only** mode (`read_only=True`), allowing virtually unlimited concurrent reader threads without locking contention.

### Q9: Why did you encounter a `BinderError` during cross-catalog view resolution, and how did you resolve it?
**Answer**:  
When dbt compiles views inside `blood_warehouse.duckdb`, the SQL queries reference `blood_warehouse.bronze.raw_inventory`. When the database was copied to `serving.duckdb`, DuckDB looked for a catalog named `blood_warehouse`, which didn't exist in the new context, causing a `BinderError`.  
We resolved this in `src/bloodlake/db.py` by attaching the serving database alias:
```sql
ATTACH 'serving.duckdb' AS blood_warehouse (READ_ONLY);
```
This cleanly maps catalog references without needing to rewrite compiled dbt views.

### Q10: What is the benefit of Parquet over CSV for the landing zone?
**Answer**:  
1. **Schema Preservation**: Parquet stores typed columns (integers, timestamps, strings) natively in metadata; CSV stores everything as untyped text prone to parsing errors.
2. **Columnar Compression**: Parquet uses Snappy/zstd compression and dictionary encoding, achieving 70–85% file size reductions compared to CSV.
3. **Chunk Splitting & Pushdown**: DuckDB reads Parquet file metadata footers to skip entire row groups based on min/max statistics without reading the whole file.

### Q11: What is a Star Schema, and where is it visible in your Gold layer?
**Answer**:  
A Star Schema organizes data into central **Fact tables** containing numerical metrics and foreign keys surrounded by **Dimension tables** containing descriptive context:
- **Central Facts**: `fct_stock_current` (units, last updated) and `fct_stock_snapshot` (historical quantities).
- **Dimension**: `dim_blood_banks` (facility name, contact, address, coordinates, type).
- **Marts**: `mart_reliability_score` (dimension metrics) and `mart_district_status` (aggregated fact).

### Q12: What is SCD Type 2, and why is it important in healthcare data pipelines?
**Answer**:  
**Slowly Changing Dimension (SCD) Type 2** tracks historical changes in dimension attributes by creating a new record with valid date ranges (`valid_from`, `valid_to`) rather than overwriting existing records. If a blood bank changes its contact phone number or moves to a new address, SCD Type 2 preserves the historical record so past emergency dispatches can be audited against the accurate address at that point in time.

### Q13: What is the grain of `fct_stock_current` versus `fct_stock_snapshot`?
**Answer**:  
- **`fct_stock_current`**: Grain is `(hospital_code, component_name, blood_group)`. It represents only the latest known inventory state for each active facility.
- **`fct_stock_snapshot`**: Grain is `(hospital_code, component_name, blood_group, snapshot_date)`. It represents the daily snapshot accumulation over time.

### Q14: How does dbt DAG compilation ensure execution order?
**Answer**:  
dbt parses Jinja `{{ ref('model_name') }}` and `{{ source('...') }}` expressions within SQL files. It constructs a directed acyclic graph where child models depend on parent models. When `dbt run` executes, it uses topological sort to ensure `bronze` finishes before `silver` models run, and all `silver` dependencies finish before `gold` models are materialized.

### Q15: What is the "Zero Fake Data Contract" in your project?
**Answer**:  
Many student dashboards generate random mock time-series data using scripts (e.g. `random.randint()`) to simulate 30-day graphs. In a life-critical application, fake data is dangerous and unscientific.  
Our project strictly prohibits synthetic data generation:
- If only one pipeline run has occurred, the time-series API explicitly returns `has_sufficient_history: false` and a transparent message stating that historical delta builds with subsequent scrapes.
- Evaluators can verify that every single row in `fct_stock_snapshot` traces back to a genuine `run_id` and raw Parquet landing hash.

---

## Part II: Ingestion, Scraping, Network Engineering & Ethics

### Q16: How does the asynchronous crawler achieve scraping 781 districts in ~26 seconds?
**Answer**:  
In synchronous scraping (e.g., Python `requests`), each HTTP call blocks the thread waiting for network I/O, taking $781 \times 0.5\text{ s} \approx 390\text{ seconds}$ (~6.5 minutes).  
Our crawler uses `aiohttp` and Python's `asyncio` event loop:
- It launches coroutines concurrently for all districts.
- While coroutine A waits for packet round-trips from the server, the single-threaded event loop processes responses for coroutine B and C.
- By utilizing non-blocking sockets, all 781 requests complete in ~26 seconds.

### Q17: What is `asyncio.Semaphore(10)`, and why did you limit concurrency?
**Answer**:  
A **Semaphore** is a synchronization primitive that limits the number of simultaneous active operations.  
If we fired all 781 requests simultaneously without limits:
1. It could trigger Denial of Service (DoS) protections on the government server.
2. It could exhaust local OS file descriptors / socket buffers.
3. It would be unethical and impolite network behavior.  
`Semaphore(10)` guarantees that no more than 10 requests are concurrently active in flight at any millisecond.

### Q18: What is exponential backoff with jitter?
**Answer**:  
When a network request fails (e.g., HTTP 429 Too Many Requests or 503 Server Busy), immediately retrying can overwhelm the recovering server ("thundering herd" problem).  
- **Exponential Backoff**: Doubles the delay on each consecutive retry: $1\text{ s}, 2\text{ s}, 4\text{ s}, 8\text{ s}$.
- **Jitter**: Adds a random float to the delay (e.g., $2\text{ s} \pm 0.3\text{ s}$) so multiple retrying workers do not synchronize their retry attempts.

### Q19: Why direct HTTP calls via `aiohttp` instead of Selenium or Playwright?
**Answer**:  
Headless browsers (Selenium/Playwright) launch full Chromium instances to render HTML and execute JavaScript. This consumes 300–500 MB of RAM per process, renders CPU-heavy DOM trees, and takes 10–15 minutes to crawl 781 districts.  
By reverse-engineering the underlying REST endpoint used by the portal (`/eraktkoshPortal/eraktkosh/blood-availability`), we fetch raw JSON payloads directly over lightweight HTTP, reducing CPU and memory overhead by 95% and running in 26 seconds.

### Q20: What is the ethical policy for scraping a public health portal?
**Answer**:  
1. **Academic Attribution**: Data is explicitly attributed to the Ministry of Health and Family Welfare (MoHFW), Govt. of India.
2. **Politeness**: Requests are throttled (`Semaphore(10)`), timeouts are strict (15 seconds), and user agents identify the academic research project.
3. **No Commercial Exploitation**: The project contains zero paywalls, advertisements, or monetization.
4. **Safety Disclaimers**: The UI prominently advises users to call the blood bank directly before travelling.

### Q21: What is the Anomaly Detection Gate, and what threshold does it use?
**Answer**:  
Public web scrapers can fail if an upstream portal encounters database outages or changes its response format, returning an empty list or error page.  
If our pipeline blindly accepted an empty crawl, it would overwrite the Gold mart and erase all nationwide inventory data.  
To prevent this, our pipeline implements an **Anomaly Gate**:
- It counts the number of reporting facilities scraped.
- If the facility count drops by more than **20%** compared to the previous baseline (threshold $<80\%$), the pipeline aborts immediately, logs a critical alert, and refuses to overwrite `serving.duckdb`. The existing verified database remains untouched.

### Q22: Why do you calculate SHA-256 checksums on Parquet landing files?
**Answer**:  
Data integrity and non-repudiation. Computing a SHA-256 cryptographic hash of every generated Parquet file guarantees that the landing file has not been tampered with or corrupted by disk write errors. The hash is logged in the pipeline execution metadata.

### Q23: How do you handle schema drift if eRaktKosh adds or renames keys in their API response?
**Answer**:  
In the Bronze layer, we store the verbatim JSON response in a `raw_payload` string column. If eRaktKosh adds new fields (e.g., "rare_phenotype_flag"), the raw data is safely preserved. In dbt, we use DuckDB's flexible JSON extractors (`json_extract_path`) in Silver views, allowing new columns to be extracted without rebuilding historical Bronze tables.

### Q24: What is the role of `eraktkosh_all_metadata.json`?
**Answer**:  
It serves as the master geographic seed dictionary containing all 36 Indian States/UT codes and their corresponding 781 district identifiers recognized by the eRaktKosh portal. The async scraper iterates through this master list to query district-level availability.

### Q25: How does the GitHub Actions workflow automate the pipeline?
**Answer**:  
In `.github/workflows/pipeline.yml`, a scheduled cron trigger runs every 6 hours:
1. Checks out the repository.
2. Sets up Python 3.12 with `uv`.
3. Executes `bloodlake all` (scrape, ingest, transform, snapshot).
4. Runs `pytest` and `dbt test` to validate the resulting database.
5. Uploads the verified database artifact.

### Q26: Explain the difference between connection timeouts and read timeouts.
**Answer**:  
- **Connection Timeout**: The maximum time permitted to establish the initial TCP handshake with the server (set to 5 seconds). If the server is offline or unreachable, the connection aborts quickly.
- **Read Timeout**: The maximum time permitted for the server to transmit the data packets once the connection is established (set to 15 seconds). This prevents coroutines from hanging indefinitely on stalled responses.

### Q27: How does the Typer CLI framework structure commands?
**Answer**:  
Typer uses Python 3.10+ type hints to automatically generate command-line interfaces with subcommands (`scrape`, `ingest`, `transform`, `snapshot`, `all`), flags, help text (`--help`), and exit status codes, ensuring professional developer usability.

### Q28: What is a Circuit Breaker pattern in web crawling?
**Answer**:  
If the upstream government portal experiences an extended outage, repeatedly firing 781 requests is wasteful. A **Circuit Breaker** tracks the consecutive failure rate. If 15 consecutive requests fail, the circuit trips ("OPEN"), immediately halting the crawl and alerting the operator instead of hammering a failing server.

---

## Part III: Data Quality, Normalization & Analytics Engineering

### Q29: What is the "Blood Group Normalization Problem," and why are regexes dangerous?
**Answer**:  
In raw portal data, blood groups often contain trailing whitespace, inconsistent casing, or non-standard symbols (e.g. `B +ve`, `B POS`, `AB+`, `Oh+`).  
Simple regex replacement like replacing `B+` can inadvertently corrupt `AB+` into `AAB+`. Similarly, replacing `O+` can corrupt Bombay blood group `Oh+` into `O+`.  
We solve this using our dbt Jinja macro `normalize_blood_group.sql`:
- It matches longer, specific tokens first (like `Bombay (Oh+)`, `AB+`, `AB-`) before evaluating single-letter groups (`B+`, `O+`).
- It maps variations into 10 canonical dbt `accepted_values`.

### Q30: Walk through the 0–100 Data Reliability Score algorithm.
**Answer**:  
The score is calculated deterministically in SQL in `gold.mart_reliability_score` across three objective pillars:
1. **Freshness (50 Points)**:
   - Updated $\le 24$ hours: **50 pts**
   - Updated $> 24$ and $\le 48$ hours: **35 pts**
   - Updated $> 48$ and $\le 168$ hours (7 days): **15 pts**
   - Updated $> 7$ days or null: **0 pts**
2. **Valid Contact Information (25 Points)**:
   - Facility provides a phone number with $\ge 8$ digits: **25 pts**
   - Missing or short number: **0 pts**
3. **Stock Completeness (25 Points)**:
   - Reports positive stock across $\ge 4$ distinct blood groups: **25 pts**
   - Reports 1–3 groups: **15 pts**
   - Reports 0 units: **0 pts**
- **Tiers**: `HIGH` ($\ge 75$), `MODERATE` ($45-74$), `LOW` ($< 45$).

### Q31: Why is the Reliability Score calculated inside SQL instead of Python?
**Answer**:  
1. **Performance**: Executing the score calculation vectorized in DuckDB across 4,600+ facilities takes $<2$ milliseconds. In Python, looping through dictionaries and applying conditional logic takes 50–100x longer.
2. **Single Source of Truth**: The metric is defined once in the database schema. Any consumer (FastAPI, CLI, Jupyter, BI tools) reads the exact same reliability score without reimplementing the calculation.

### Q32: What automated dbt tests are executed, and what happens if a test fails?
**Answer**:  
We run 35 automated dbt tests:
- **`unique`**: Verifies `hospital_code` uniqueness in `dim_blood_banks`.
- **`not_null`**: Ensures no nulls in mandatory fields (hospital name, state, district, component, units).
- **`accepted_values`**: Strictly validates that `blood_group` only contains the 10 allowed categories and `reliability_tier` only contains `HIGH`, `MODERATE`, `LOW`.
- **`relationships`**: Validates foreign key referential integrity between fact rows and dimension facilities.  
If any test fails, dbt exits with code 1, the pipeline halts, and the atomic swap to `serving.duckdb` is aborted.

### Q33: How does the pipeline handle blood banks that have stopped updating their data?
**Answer**:  
The facility record remains in `dim_blood_banks`, but its `freshness_score` drops to 0, which reduces its `reliability_score` below 45 (`LOW` tier). On the frontend, the facility is flagged with a grey/red badge and pushed to the bottom of sorted search results so users do not prioritize stale facilities.

### Q34: What is the District Deficit Status, and how is it classified?
**Answer**:  
In `mart_district_status`, stock is aggregated by district, component, and blood group:
- **`SHORTAGE`**: Total available units = 0 across all reporting facilities in the district.
- **`LOW_STOCK`**: Total available units between 1 and 5.
- **`ADEQUATE`**: Total available units $> 5$.

### Q35: What is the Rare Blood Phenotype Radar?
**Answer**:  
The Rare Blood Radar indexes facilities with non-zero stock of critical rare groups:
- **Bombay Blood Group (`Oh+`, `Oh-`)**: Individuals lacking the H antigen cannot receive O, A, B, or AB blood—they can only receive Bombay blood.
- **Rh-Negative Groups (`AB-`, `O-`, `A-`, `B-`)**: Low prevalence in the Indian population (~2-5%).  
The mart enables rapid cross-district searching during rare phenotype emergencies.

### Q36: How does dbt handle incremental models (`is_incremental()`) in DuckDB?
**Answer**:  
In `fct_stock_snapshot.sql`, we use Jinja:
```sql
{{ config(materialized='incremental', unique_key=['hospital_code', 'component_name', 'blood_group', 'snapshot_date']) }}
SELECT ... FROM ...
{% if is_incremental() %}
WHERE snapshot_date >= (SELECT MAX(snapshot_date) FROM {{ this }})
{% endif %}
```
On initial run, it builds the entire table. On subsequent runs, it only evaluates new snapshot dates and executes an `INSERT OR REPLACE` (merge) on the unique key.

### Q37: What is the difference between data accuracy and data freshness?
**Answer**:  
- **Accuracy**: Whether the reported data matches reality (e.g., if the facility actually has 14 units of O-).
- **Freshness**: The age of the reported record (e.g., whether the portal was updated 1 hour ago or 3 weeks ago).  
A facility can report 100% accurate data on Monday, but by Friday the data is stale and potentially inaccurate because units were transfused. This is why our reliability algorithm weights Freshness at 50%.

### Q38: How do you prevent negative inventory units in the Silver and Gold layers?
**Answer**:  
1. In `stg_inventory_components.sql`, we apply `GREATEST(CAST(units AS INTEGER), 0)`.
2. In `schema.yml`, we define a custom SQL dbt assertion test verifying `units >= 0`.

### Q39: What is a surrogate key, and did you use one in this project?
**Answer**:  
A surrogate key is an artificial, system-generated primary key (such as an MD5/SHA-256 hash or auto-incrementing integer) used to uniquely identify a record regardless of upstream business keys. In `fct_stock_snapshot`, the surrogate key is derived from:
`MD5(hospital_code || '-' || component_name || '-' || blood_group || '-' || snapshot_date)`.

### Q40: What is data grain, and why is defining it critical?
**Answer**:  
The **grain** is the exact level of detail represented by a single row in a table. Defining the grain prevents accidental duplicate aggregations or Cartesian join explosions. For example:
- Grain of `dim_blood_banks`: One row per facility (`hospital_code`).
- Grain of `fct_stock_current`: One row per facility, component, and blood group (`hospital_code`, `component_name`, `blood_group`).

### Q41: How do you sanitize messy hospital contact strings?
**Answer**:  
Raw strings often contain multiple numbers, landlines with STD codes, slashes, and spaces (e.g., `02692-223344 / 98250 12345`).  
In `stg_blood_banks.sql`, we strip whitespace, isolate the primary phone token before any delimiter (`/`, `,`), remove non-numeric characters, and check that the remaining digits $\ge 8$.

### Q42: What is the difference between a dimensional mart and an aggregate fact?
**Answer**:  
- A **Dimensional Mart** is focused on a specific business entity and its attributes (e.g. `dim_blood_banks` with address and contact info).
- An **Aggregate Fact** pre-computes group-level summary metrics (e.g. `mart_district_status`, which groups by state and district to compute `SUM(units)` and `COUNT(banks)`).

---

## Part IV: Backend Architecture, REST API & Frontend Design

### Q43: Why FastAPI instead of Flask or Django?
**Answer**:  
1. **Asynchronous Throughput**: FastAPI is built on ASGI (Starlette + Uvicorn) and supports asynchronous I/O natively.
2. **Pydantic Validation**: Automatic schema enforcement and type validation on query parameters and response payloads.
3. **Automatic OpenAPI/Swagger Docs**: Generates interactive documentation at `/docs` without external plugins.
4. **Lightweight**: Unlike Django, it does not bring an unneeded heavy ORM, admin panel, or session middleware.

### Q44: How are your SQL queries protected against SQL Injection?
**Answer**:  
We **never** concatenate user-supplied input strings into raw SQL queries.  
Every dynamic filter in `bloodlake/api/routes.py` uses parameterized queries with `?` placeholders:
```python
where_clauses.append("s.state_name = ?")
params.append(state)
con.execute(query_sql, params)
```
The DuckDB query compiler treats inputs strictly as parameter constants, rendering SQL injection impossible.

### Q45: How did you replace application-side regex parsing with pure SQL aggregation?
**Answer**:  
Earlier versions of the application extracted full-facility stock matrices by loading raw JSON or comma-separated strings into Python and parsing them with regular expressions.  
We replaced this entirely with pure SQL in DuckDB:
```sql
SELECT 
    hospital_code,
    string_agg(blood_group || ': ' || CAST(units AS VARCHAR), ', ') as stock_matrix
FROM main_gold.fct_stock_current
GROUP BY hospital_code;
```
This offloads text processing to DuckDB's C++ execution engine and executes in $<3$ ms.

### Q46: Why Vanilla HTML, CSS, and JavaScript instead of React, Next.js, or Vue?
**Answer**:  
1. **Zero Build Step & Zero Overhead**: No Webpack, Vite, or npm compilation; the frontend opens immediately in any browser.
2. **Fast Page Loads & Minimal Footprint**: The entire frontend is $<150$ KB (HTML, CSS, JS), loading in $<50$ ms on 3G connections.
3. **Longevity & Transparency**: Vanilla web standards do not suffer from breaking framework dependency updates or Node.js version conflicts, making it ideal for academic evaluation and long-term reproducibility.

### Q47: Describe your Red-and-White design system.
**Answer**:  
To break away from stereotypical "AI-generated dashboards" (which rely on dark mode glassmorphism, heavy neon gradients, and emoji icons), our design follows a clinical health-tech aesthetic:
- **Canvas**: Clean warm off-white (`#FBF8F6`) with crisp white card containers (`#FFFFFF`).
- **Typography**: Inter / System UI with clear hierarchical font weights (`400`, `500`, `600`, `700`).
- **Primary Color**: Subdued clinical blood red (`#D21F3C`) used with discipline on primary action buttons and urgent shortages.
- **Icons**: 100% inline SVG Lucide-style icons (stroke 1.5px, 18px size) with zero emojis.

### Q48: How does the interactive map render without costly Google Maps API keys?
**Answer**:  
We use **Leaflet.js** (open-source mapping library) paired with **Carto Positron** tiles. Carto Positron provides clean, high-contrast, distraction-free map rendering that highlights blood bank markers clearly without commercial billing dependencies or API key limits.

### Q49: Why do all map markers state "approximate location, district level"?
**Answer**:  
The eRaktKosh portal reports district names and postal addresses but does not publish verified GPS latitude and longitude coordinates. Instead of attempting automated geocoding that could place a marker on an incorrect building, we map facilities to verified **district centroids** and explicitly declare the precision tier to the user.

### Q50: How does the WhatsApp SOS sharing feature work without third-party APIs?
**Answer**:  
Instead of paying for a WhatsApp Business / Twilio API integration, we use the standard WhatsApp universal URL scheme (`https://wa.me/?text=...`):
- The frontend formats an emergency message string containing the blood bank name, address, contact, blood group, units, and verification date.
- The string is URL-encoded and opened in a new tab, allowing users on mobile or desktop to send the emergency alert directly to family or group chats.

### Q51: How does the 7-day trend modal render, and what library does it use?
**Answer**:  
It uses **Chart.js** via a clean canvas element inside an accessible modal dialog:
- Fetches verified time-series data from `/api/history?hospital_code=...`.
- Plots multi-series lines for each blood group over real snapshot dates.
- Destroys previous canvas instances before re-rendering to prevent memory leaks.

### Q52: What is the purpose of the multilingual translation dictionary?
**Answer**:  
In emergency healthcare, accessibility across diverse linguistic populations is vital. `web/js/translations.js` provides instant client-side switching between **English**, **Hindi (हिन्दी)**, and **Gujarati (ગુજરાતી)** without requiring server-side reloads.

---

## Part V: Testing, Reliability, Scalability & Viva Defense

### Q53: Describe your automated testing strategy.
**Answer**:  
We implement a three-tiered testing pyramid:
1. **Unit Tests (pytest)**: Tests individual Python functions in isolation (blood group normalizer, reliability scoring logic, geocoding centroid resolver, scraper circuit breaker).
2. **Integration Tests (FastAPI TestClient)**: Validates all API endpoints (`/healthz`, `/api/v1/meta`, `/summary`, `/locations`, `/banks`, `/availability`, `/history`, `/shortages`, `/rare`) against an isolated synthetic test database (`tests/fixtures/fixture_lakehouse.duckdb`).
3. **Data Quality Tests (dbt test)**: 35 relational schema and contract tests validating uniqueness, foreign keys, accepted values, and non-negative constraints.

### Q54: Why did you create an isolated synthetic fixture database for integration tests?
**Answer**:  
Running integration tests against the live `serving.duckdb` file can cause lock contention if the pipeline or local dev server is running. Furthermore, test environments must be deterministic. By generating `tests/fixtures/fixture_lakehouse.duckdb` with controlled mock rows, tests pass in $<2$ seconds in CI/CD without depending on live network data.

### Q55: What is the pre-commit workflow with Ruff?
**Answer**:  
Ruff is an extremely fast Python linter and formatter written in Rust. Our `.pre-commit-config.yaml` runs `ruff check --fix` and `ruff format` before every git commit, ensuring zero unused imports, consistent code formatting, and PEP 8 compliance across all repository files.

### Q56: What are the primary technical limitations of the current architecture?
**Answer**:  
1. **Upstream Portal Latency**: Inventory data is only as fresh as the updates entered by hospital staff on the eRaktKosh portal.
2. **District Centroid Resolution**: Facilities are plotted at district centroids rather than precise building-level coordinates.
3. **Single In-Process Storage**: While DuckDB easily handles millions of rows locally, if the platform scaled to thousands of writes per second, a distributed lakehouse (e.g. Apache Iceberg on AWS S3 + ClickHouse/Trino) would be necessary.

### Q57: If this project were deployed to serve 100,000 requests per second, what changes would you make?
**Answer**:  
1. **Edge Caching & CDN**: Place Cloudflare or AWS CloudFront in front of read-only endpoints (`/api/v1/summary`, `/api/v1/locations`, `/api/v1/availability`) with 60-second TTL cache headers.
2. **Serving Engine**: Migrate the read-only serving layer from local DuckDB files to **ClickHouse** or **DuckDB on AWS Lambda/S3** read replicas behind an Application Load Balancer.
3. **Data Lake Storage**: Store historical Parquet landing files on Amazon S3 / Google Cloud Storage managed via Apache Iceberg catalogs.

### Q58: How could machine learning / predictive modeling be integrated into this lakehouse?
**Answer**:  
With historical daily snapshots accumulating in `fct_stock_snapshot`, we can train time-series forecasting models (such as ARIMA, Prophet, or LSTM) to predict district-level blood shortages 7 to 14 days in advance, alerting blood bank administrators to schedule voluntary blood donation camps before stock hits zero.

### Q59: If an examiner asks: "What will you do if the eRaktKosh portal is down during the viva?", how do you respond?
**Answer**:  
"Our Lakehouse architecture is decoupled by design. The serving layer (`serving.duckdb`) is completely independent of the scraping layer. Even if the eRaktKosh portal is completely offline or college Wi-Fi is disconnected, our local lakehouse contains a fully verified, real snapshot of 4,692 facilities across 35 states and 59,259 stock records. All search queries, interactive map navigation, and analytical marts run 100% offline at local speeds."

### Q60: How does this project satisfy the 800-mark MCA Mini Project curriculum requirements at CHARUSAT?
**Answer**:  
1. **Data Engineering Rigor**: Implements modern lakehouse design (ELT, Medallion Architecture, Parquet landing, DuckDB, dbt Core transformations).
2. **Full-Stack Competence**: Production-grade asynchronous FastAPI backend, RESTful API design, and a responsive vanilla frontend with Leaflet mapping and Chart.js analytics.
3. **Software Engineering Best Practices**: Clean repository structure, Typer CLI, 45 pytest tests, 35 dbt tests, pre-commit Ruff linting, and automated GitHub Actions CI/CD.
4. **Social & Ethical Impact**: Solves an authentic public health crisis in India by surfacing real, life-saving blood availability without commercial distractions or fabricated data.
