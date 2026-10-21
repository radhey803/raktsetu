# eRaktKosh Blood Lakehouse: Evaluator Live Demo & Offline Contingency

**Context**: Academic Research Project  
**Department**: Academic Research Team  
**Project**: eRaktKosh Blood Lakehouse (Academic Mini Project — 800 Marks)  
**Purpose**: Offline presentation survival kit, viva cheat sheet, and database contingency.

---

## 1. The Offline Contingency Plan

During viva voce examinations, internet connections may be unstable, slow, or blocked by institutional firewall proxies. Additionally, the public eRaktKosh portal may occasionally undergo maintenance.

### The Decoupled Lakehouse Advantage:
Our Lakehouse architecture completely decouples the **Ingestion Layer** from the **Analytical Serving Layer**:
1. All client interactions (search, maps, metrics, charts, modals) query the local **`serving.duckdb`** database.
2. The `demo/fallback_lakehouse.duckdb` file is an authentic, verified snapshot containing:
   - **4,692 Licensed Facilities** across 35 Indian States and Union Territories.
   - **59,259 Verified Historical Snapshot Rows**.
   - **0 Synthetic or Fabricated Rows**.
3. **The live demonstration can run 100% offline at local speeds (<15ms per query).**

---

## 2. One-Command Demo Execution

### Standard Live Demo:
```bash
make demo
```
*This command executes automated test assertions and launches the web application at `http://localhost:8000`.*

### Offline Fallback Demo (No Internet / Disconnected Wi-Fi):
```bash
make demo-offline
```
*This command ensures `serving.duckdb` is restored from `demo/fallback_lakehouse.duckdb` and launches the application without touching the network.*

---

## 3. Evaluator Viva Voce Cheat Sheet

Keep these metrics and SQL queries handy during the examination:

### Quick Verification Queries (DuckDB):
```bash
# Verify total facilities and distinct states
uv run duckdb -readonly serving.duckdb "SELECT COUNT(*) as banks, COUNT(DISTINCT state_name) as states FROM main_gold.dim_blood_banks;"

# Verify total verified stock snapshots
uv run duckdb -readonly serving.duckdb "SELECT COUNT(*) as snapshots FROM main_gold.fct_stock_snapshot;"

# Show top 5 highest-reliability facilities in Gujarat
uv run duckdb -readonly serving.duckdb "
    SELECT b.hospital_name, b.district_name, r.reliability_score, r.reliability_tier
    FROM main_gold.dim_blood_banks b
    JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
    WHERE b.state_name = 'Gujarat'
    ORDER BY r.reliability_score DESC
    LIMIT 5;
"

# Demonstrate Rare Blood Phenotypes (Bombay Blood Group Oh+)
uv run duckdb -readonly serving.duckdb "
    SELECT hospital_name, state_name, district_name, blood_group, units
    FROM main_gold.mart_rare_blood_availability
    WHERE blood_group LIKE 'Bombay%'
    LIMIT 5;
"
```

---

## 4. 7-Minute Timed Demonstration Sequence

1. **Step 1 (0:00 - 1:00)**: Open `http://localhost:8000` and demonstrate the **Status: Live** badge, **Academic Attribution**, and national KPI cards (4,692 facilities, 35 states).
2. **Step 2 (1:00 - 2:30)**: Search for **Packed Red Blood Cells**, blood group **O-** in **Gujarat -> Anand**.
   - Point out **Indian Red Cross Society Anand Blood Bank** with **Score 90/100 (HIGH)**.
   - Point out the geographic disclaimer: *"approximate location, district level"*.
3. **Step 3 (2:30 - 3:30)**: Toggle **Map View**.
   - Show Carto Positron tiles rendering without paid API keys.
   - Click the Anand marker popup showing real component counts.
4. **Step 4 (3:30 - 4:30)**: Click **7-Day History** modal on the card.
   - Show Chart.js multi-group time series.
   - Highlight the **Zero Fake Data Contract**: honest message stating history accumulates across daily scrapes.
5. **Step 5 (4:30 - 5:15)**: Click **WhatsApp SOS**.
   - Demonstrate the pre-formatted emergency dispatch message.
6. **Step 6 (5:15 - 6:00)**: Scroll down to **Rare Blood Radar** (Bombay `Oh+`) and **District Deficit Radar** (Shortage areas with 0 units).
7. **Step 7 (6:00 - 7:00)**: In terminal, run `uv run pytest` (45 passed in <2s) and `uv run dbt test --project-dir dbt --profiles-dir dbt` (35 passed in ~3s).
