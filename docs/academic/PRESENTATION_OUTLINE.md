# eRaktKosh Blood Lakehouse: Viva Presentation & Live Demo Script

**Context**: Academic Research Project  
**Department**: Academic Research Team  
**Course Code / Project**: Academic Project (800 Marks)  
**Title**: eRaktKosh Blood Lakehouse: Modern Lakehouse Architecture for National Blood Inventory Intelligence & Emergency Triage  
**Time Limit**: 15 Minutes (8 Minutes Slides + 7 Minutes Live System Demo)  

---

## 1. 15-Slide Presentation Outline & Speaker Notes

### Slide 1: Title & Academic Credentials
- **Header**: eRaktKosh Blood Lakehouse
- **Sub-header**: National Blood Inventory Analytics & Emergency Finder via In-Process OLAP Lakehouse Architecture
- **Credentials**:
  - Student Name: MCA Final Year Student Team
  - Institution: Academic Research Project
  - Department: Department of Computer Applications
  - Academic Guide: MCA Faculty Mentor
  - Evaluation: Academic Mini Project (800 Marks)
- **Speaker Notes**:
  > "Respected evaluators and faculty members, good morning. Today, I am proud to present the 'eRaktKosh Blood Lakehouse'—a modern data engineering and analytics solution designed to address India's critical blood shortage and data fragmentation challenges. Over the next 15 minutes, I will walk you through the real-world healthcare problem, our architectural design using DuckDB and dbt Core, and conduct a live demonstration of the operational platform."

---

### Slide 2: The Healthcare Problem: Blood Fragmentation & Information Asymmetry
- **Key Challenges in India**:
  - Over 4,600 licensed blood facilities across 781 districts operate in silos.
  - During medical emergencies (trauma, thalassaemia, obstetric hemorrhage), families waste critical "golden hour" minutes making desperate phone calls or visiting blood banks with zero stock.
  - Public portals contain data, but lack fast analytical filtering, reliability indicators, or mobile-friendly emergency workflows.
- **Visual**: Flow diagram illustrating frantic manual calling vs. immediate single-query emergency lookup.
- **Speaker Notes**:
  > "In an emergency, every minute counts. India requires over 14 million units of blood annually, yet thousands of lives are lost because available units cannot be discovered in time. While the Ministry of Health operates the eRaktKosh portal, the data is fragmented across 781 district pages. Patients' families have no objective way of knowing if a reported stock number was updated today or is a three-month-old stale record. Our project bridges this vital information gap."

---

### Slide 3: Project Vision & Core Academic Principles
- **Four Core Pillars**:
  1. **In-Process Lakehouse Architecture**: High-speed columnar analytics via DuckDB and dbt Core without heavy server infrastructure.
  2. **100% Zero Fake Data Guarantee**: No simulated or mock data. Every single metric originates from authentic eRaktKosh portal ingestions.
  3. **Data Reliability Scoring (0–100)**: Objective, automated evaluation of data freshness, contact availability, and stock completeness.
  4. **Public Health Ethics & Geographic Honesty**: Explicit disclaimers, district-level centroid accuracy labeling, and source attribution to MoHFW.
- **Speaker Notes**:
  > "From day one, our academic contract was strict: zero fake data. We do not generate synthetic numbers or artificial graphs. If only one scrape exists, the system honestly states that trend history builds with subsequent runs. We also introduced an objective 0 to 100 Data Reliability Score that warns users when a facility has abandoned its inventory records."

---

### Slide 4: High-Level System Architecture
- **Architecture Flow**:
  - **Source Layer**: MoHFW eRaktKosh Public API (781 Districts).
  - **Ingestion**: Asynchronous Python Crawler (`aiohttp` + `asyncio.Semaphore(10)`).
  - **Landing Zone**: Immutable Parquet storage (`data/landing/*.parquet`) with SHA-256 verification.
  - **Transformation**: Medallion Architecture in DuckDB (`blood_warehouse.duckdb`) orchestrated via dbt Core.
  - **Serving Layer**: Atomic swap to read-only `serving.duckdb`.
  - **Application Layer**: Asynchronous FastAPI REST API (`/api/v1`) & Vanilla HTML5/CSS/JavaScript frontend with Leaflet mapping and Chart.js analytics.
- **Visual**: Comprehensive Medallion flow diagram (Bronze $\rightarrow$ Silver $\rightarrow$ Gold).
- **Speaker Notes**:
  > "Here is our complete lakehouse architecture. We follow the modern ELT paradigm. Raw data is extracted in parallel across 781 districts in just 26 seconds and stored in immutable Parquet files. DuckDB then loads the data into Bronze, Silver, and Gold medallion layers with dbt Core. Finally, FastAPI queries the serving database in read-only mode with sub-millisecond response times."

---

### Slide 5: The Ingestion Engine: Asynchronous Crawling & Network Politeness
- **Technical Specifications**:
  - Asynchronous event-loop execution using `aiohttp` and Python `asyncio`.
  - **Politeness Controls**: Concurrency capped at `Semaphore(10)` to respect government infrastructure.
  - **Resilience**: Exponential backoff with random jitter, connection timeout (5s), and read timeout (15s).
  - **Performance**: 781 districts (~4,690 facilities) scraped in **26.4 seconds** compared to ~6.5 minutes synchronously.
  - **Circuit Breaker**: Halts crawl after 15 consecutive failures to prevent hammering offline servers.
- **Speaker Notes**:
  > "To ingest data efficiently without overloading government servers, we built an asynchronous crawler. Using a semaphore of 10, we ensure that no more than 10 requests are ever active concurrently. By querying the underlying JSON endpoint directly instead of loading heavy browser DOMs, the entire nationwide dataset is fetched in just 26 seconds with complete network politeness."

---

### Slide 6: The Storage Engine: Why In-Process Columnar DuckDB?
- **DuckDB vs. Traditional RDBMS (PostgreSQL/MySQL)**:
  - **Columnar Vectorized Execution**: Scans only the needed columns for aggregations (SIMD instruction sets).
  - **In-Process Embedding**: Zero network latency or socket overhead; runs inside Python memory.
  - **Zero Server Overhead**: No database daemon to configure or maintain.
  - **Superior to SQLite**: Built specifically for OLAP aggregations, window functions, and direct Parquet I/O.
- **Visual**: Row-oriented vs. Columnar storage memory layout comparison.
- **Speaker Notes**:
  > "Why DuckDB? Traditional relational databases like MySQL or PostgreSQL are row-oriented (OLTP). When querying nationwide blood metrics across tens of thousands of stock rows, they waste CPU cycles loading unneeded row attributes. DuckDB is a columnar vectorized OLAP engine. It performs aggregations in CPU L1/L2 caches, running complex queries in under 5 milliseconds right inside the application process."

---

### Slide 7: Medallion Architecture: Bronze, Silver & Gold
- **Bronze Layer (`bronze.raw_inventory`)**:
  - Verbatim raw payload ingestion with `run_id`, `scraped_at`, and raw JSON strings.
- **Silver Layer (`silver.stg_blood_banks`, `silver.stg_inventory_components`)**:
  - JSON unnesting into atomic rows: `(hospital_code, component_name, blood_group)`.
  - Contact sanitization and district centroid geocoding.
  - Blood group normalization via dbt Jinja macro.
- **Gold Layer (Dimensional Marts)**:
  - `dim_blood_banks`: Master facility dimension.
  - `fct_stock_current`: Active stock levels for sub-second emergency queries.
  - `fct_stock_snapshot`: Append-only daily historical accumulation.
  - `mart_reliability_score`: 0–100 credibility rating.
  - `mart_district_status`: District supply health triage (`SHORTAGE`, `LOW_STOCK`, `ADEQUATE`).
  - `mart_rare_blood_availability`: Rapid index for Bombay and Rh-negative phenotypes.
- **Speaker Notes**:
  > "Our data flows through three Medallion layers. Bronze preserves the exact source payload for full auditability. Silver unnests component JSON blobs into atomic records and normalizes blood groups. Gold materializes the Star Schema: dimension tables and analytical marts that power our emergency API."

---

### Slide 8: Data Quality Engineering: The Normalization Challenge
- **The Problem**: Raw portal inputs contain arbitrary strings (`B POS`, `B +ve`, `AB+`, `Bombay Oh+`).
- **The Trap**: Naive regex replacement of `B+` inadvertently corrupts `AB+` into `AAB+`. Replacing `O+` corrupts Bombay `Oh+`.
- **Our Solution**:
  - Custom Jinja dbt macro `normalize_blood_group.sql`.
  - Prioritized token evaluation: Multi-character tokens evaluated first (`Bombay (Oh+)`, `AB+`, `AB-`) before single-letter groups (`B+`, `O+`).
  - Enforced by dbt `accepted_values` test on all 10 canonical groups.
- **Speaker Notes**:
  > "Data normalization is a critical engineering hurdle. If a patient with B+ blood is shown AB+ units due to poor regex replacement, the result could be fatal. We designed a prioritized Jinja macro in dbt that isolates compound groups like Bombay Oh+ and AB+ before matching single characters, backed by 35 automated dbt schema tests."

---

### Slide 9: The 0–100 Data Reliability Scoring Algorithm
- **Three Deterministic Pillars (Calculated in Pure SQL)**:
  1. **Freshness (50 Points)**:
     - $\le 24$ hours: 50 pts | $24-48$ hours: 35 pts | $48-168$ hours: 15 pts | $> 7$ days: 0 pts.
  2. **Contact Validity (25 Points)**:
     - Non-null telephone string with $\ge 8$ valid numeric digits: 25 pts | Invalid: 0 pts.
  3. **Stock Completeness (25 Points)**:
     - Reports $\ge 4$ distinct blood groups: 25 pts | $1-3$ groups: 15 pts | 0 units: 0 pts.
- **Tiers**:
  - `HIGH` ($\ge 75$): Verified active facility.
  - `MODERATE` ($45-74$): Call in advance.
  - `LOW` ($< 45$): Stale or incomplete records.
- **Speaker Notes**:
  > "How do we prevent users from travelling to facilities with outdated records? We created an objective 0 to 100 Data Reliability Score computed directly in SQL. Freshness carries 50 points, valid contact carries 25 points, and inventory completeness carries 25 points. This immediately highlights active, trustworthy blood banks."

---

### Slide 10: Production Safeguards: Anomaly Gate & Concurrency Control
- **Statistical Anomaly Gate**:
  - Evaluates scraped facility count against the historical baseline.
  - If facility count drops by $>20\%$ (threshold $<80\%$), the pipeline aborts immediately and refuses to swap databases.
- **Atomic Blue-Green Database Swap**:
  - Batch writes occur in `blood_warehouse.duckdb`.
  - Once tests pass, it is atomically copied to `serving.duckdb`.
  - FastAPI readers open `serving.duckdb` in `READ_ONLY` mode, preventing locking bottlenecks.
- **Cross-Catalog View Resolution**:
  - Uses `ATTACH 'serving.duckdb' AS blood_warehouse (READ_ONLY)` to resolve compiled dbt view references.
- **Speaker Notes**:
  > "To ensure enterprise reliability, our pipeline includes an Anomaly Gate. If eRaktKosh experiences server issues and returns an empty list, our gate detects the drop and protects the warehouse from being wiped. Furthermore, our atomic swap ensures that read-only API requests from users are never blocked by background writes."

---

### Slide 11: Backend Engineering: Asynchronous FastAPI & Security
- **Backend Features**:
  - FastAPI on Python 3.12 with Uvicorn ASGI server.
  - Automatic OpenAPI / Swagger UI interactive documentation at `/docs`.
  - Pydantic models for request validation and response serialisation.
  - **SQL Injection Prevention**: 100% parameterized queries using `?` placeholders.
  - **Pure SQL Stock Aggregation**: Uses DuckDB `string_agg()` for instant multi-component summaries without Python string parsing.
- **Speaker Notes**:
  > "Our REST API is built on FastAPI. It provides sub-millisecond query execution, automatic schema validation with Pydantic, and comprehensive Swagger documentation. Every query is strictly parameterized to completely eliminate SQL injection vulnerabilities."

---

### Slide 12: Frontend Design System: Clinical Red-and-White Health-Tech
- **Design Philosophy**:
  - Rejects dark-mode neon glassmorphism and generic emojis.
  - Clinical, trustworthy health-tech aesthetic:
    - Canvas: Warm off-white (`#FBF8F6`)
    - Cards: Crisp white (`#FFFFFF`)
    - Primary Accent: Subdued clinical red (`#D21F3C`)
    - Icons: 100% inline SVG Lucide-style icons (stroke 1.5px, 18px size)
  - Vanilla HTML5, CSS3, and JavaScript: Zero npm build step, $<150$ KB total payload, loads in $<50$ ms.
- **Speaker Notes**:
  > "The frontend was crafted to inspire trust. Rather than looking like a generic AI dashboard with dark glassmorphism and emojis, it uses a disciplined red-and-white clinical theme. Built with vanilla web standards, it has zero dependencies and loads in 50 milliseconds."

---

### Slide 13: Emergency Action Workflows
- **Core User Features**:
  1. **Instant Availability Search**: Filter by state, district, component, and blood group.
  2. **Interactive Blood Map**: District centroid clustering using Leaflet.js and Carto Positron tiles.
  3. **7-Day History Modal**: Multi-group time-series line chart via Chart.js with honest zero-fake-data messaging.
  4. **Emergency WhatsApp SOS**: One-click generation of formatted emergency dispatch messages for instant group sharing.
  5. **Rare Blood Phenotype Radar**: Dedicated tracking for Bombay Blood Group and Rh-negative units.
  6. **District Deficit Radar**: Identifies administrative districts facing critical blood shortages.
- **Speaker Notes**:
  > "We built features that matter in real emergencies: instant inventory search, an interactive district map, historical stock trends, a dedicated radar for rare Bombay blood, a district deficit radar, and one-click WhatsApp SOS sharing that generates pre-formatted emergency dispatches without paid APIs."

---

### Slide 14: Automated Testing & Verification
- **Test Matrix Summary**:
  - **45 Pytest Unit & Integration Tests**: Passed in 1.99s.
  - **35 dbt Relational & Contract Tests**: Passed in 3.22s.
  - **Pre-commit Ruff Linter & Formatter**: 100% clean PEP 8 compliance.
  - **Isolated Synthetic Fixture**: `tests/fixtures/fixture_lakehouse.duckdb` guarantees fast, deterministic CI execution without network dependencies.
- **Visual**: Terminal screenshot showing `45 passed` and `PASS=35 WARN=0 ERROR=0 TOTAL=35`.
- **Speaker Notes**:
  > "Quality is enforced through rigorous testing. We maintain 45 pytest unit and integration tests and 35 dbt data tests, all passing with zero warnings or errors. Our code is formatted and linted with Ruff via pre-commit hooks."

---

### Slide 15: Conclusion, Social Impact & Viva Defense Summary
- **Academic Highlights**:
  - Modern ELT Lakehouse with DuckDB & dbt Core.
  - Real-world social impact: Solves emergency blood discovery in India.
  - 100% Authentic Portal Data: Zero fake numbers, verified audit lineage.
  - Production-ready full-stack architecture with automated CI/CD.
- **Closing Statement**:
  - Ready for Viva Examination and Live Demonstration.
- **Speaker Notes**:
  > "In conclusion, the eRaktKosh Blood Lakehouse demonstrates how modern data engineering can deliver tangible social impact. By transforming fragmented public data into actionable, trustworthy intelligence, we offer a system that is robust, ethical, and fast. Thank you, and I am now excited to demonstrate the live application."

---

## 2. Timed 7-Minute Live Demonstration Script

| Time | Phase | Target Screen / Tool | Action & Speaker Script |
| :---: | :--- | :--- | :--- |
| **0:00 - 1:00** | **System Startup & Health Verification** | Terminal / Browser | 1. Show the terminal running `make run`.<br>2. Open browser at `http://localhost:8000`.<br>3. Point to the **Status: Live** badge and the **Academic Attribution** in the header.<br>*"As you can see, our system is running locally at localhost:8000. The header displays our project attribution to Academic Project and MoHFW."* |
| **1:00 - 2:30** | **Emergency Availability Search** | Dashboard Hero & Filter Bar | 1. Select State: **Gujarat**, District: **Anand**.<br>2. Select Component: **Packed Red Blood Cells**, Blood Group: **O-**.<br>3. Click **Search Inventory**.<br>4. Inspect the returned facility card: point to **Reliability Score: 90/100 (HIGH)**, the **Freshness status**, and the **approximate location disclaimer**.<br>*"In under 15 milliseconds, the DuckDB query returns verified facilities in Anand. Notice the 90/100 Reliability Score badge, confirming this facility regularly reports complete, fresh data."* |
| **2:30 - 3:30** | **Interactive Map & Geographic Honesty** | Results Grid -> Map Toggle | 1. Click **Map View** toggle.<br>2. Show the Leaflet map rendered with Carto Positron tiles.<br>3. Click a pin marker: show popup displaying available blood groups, phone number, and 'call to confirm' notice.<br>*"Our map runs without paid Google Maps APIs using Carto Positron. In accordance with our honesty contract, pins explicitly indicate district-level centroid precision."* |
| **3:30 - 4:30** | **Historical Trend Modal & Zero-Fake-Data Proof** | Facility Card -> 7-Day History Modal | 1. Click **7-Day History** on a card.<br>2. Modal opens with Chart.js line charts.<br>3. Point out the honest informational message when fewer than 2 scrape dates exist: *"Trend builds up with each data refresh."*<br>*"This modal proves our Zero Fake Data commitment. Rather than faking 30 days of data, our system honestly informs the evaluator that history builds with subsequent scrapes."* |
| **4:30 - 5:15** | **Emergency WhatsApp SOS Dispatch** | Facility Card -> WhatsApp SOS Button | 1. Click **WhatsApp SOS**.<br>2. Demonstrate the pre-formatted WhatsApp message containing patient blood details, facility address, phone, and verification date.<br>*"With a single click, an attendant can dispatch this pre-formatted emergency alert to family members over WhatsApp."* |
| **5:15 - 6:00** | **Rare Blood Radar & District Shortage Radar** | Lower Dashboard Sections | 1. Scroll to **Rare Blood Phenotype Radar** and show facilities holding rare Bombay Blood Group (`Oh+`).<br>2. Scroll to **District Shortage Radar** showing districts with 0 units.<br>*"Here is our Rare Blood Radar indexing rare Bombay Oh+ units, and our District Shortage Radar highlighting critical supply deficits."* |
| **6:00 - 7:00** | **CLI Pipeline Execution & Test Evidence** | Terminal | 1. In terminal, run: `uv run bloodlake --help`.<br>2. Run test suite: `uv run pytest`.<br>3. Run dbt tests: `uv run dbt test --project-dir dbt --profiles-dir dbt`.<br>4. Point to `45 passed` and `PASS=35`.<br>*"Finally, our entire data pipeline is managed via the 'bloodlake' CLI. All 45 pytest tests and 35 dbt data tests pass cleanly. This concludes our live demonstration."* |

---

## 3. Contingency Procedures During Demo

- **What if the internet is disconnected?**  
  The demo requires **zero internet access**. DuckDB, FastAPI, and the frontend assets are stored locally. Leaflet tiles are cached. All searches and modal trends execute locally.
- **What if an examiner asks to see the database schema?**  
  Open terminal and run:
  ```bash
  uv run duckdb serving.duckdb "DESCRIBE main_gold.fct_stock_current;"
  ```
- **What if an examiner asks to see dbt lineage?**  
  Run:
  ```bash
  uv run dbt docs generate --project-dir dbt --profiles-dir dbt
  uv run dbt docs serve --project-dir dbt --profiles-dir dbt --port 8081
  ```
  Open `http://localhost:8081` to display the interactive DAG.
