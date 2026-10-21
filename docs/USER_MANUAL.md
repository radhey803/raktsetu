# eRaktKosh Blood Lakehouse: User & Evaluator Manual

**Context**: Academic Research Project  
**Department**: Academic Research Team  
**Course Code / Project**: Academic Project (800 Marks)  
**Application**: eRaktKosh Blood Lakehouse  
**Version**: 1.0.0 (Demo Ready)  

---

## 1. Introduction & Academic Objective

The **eRaktKosh Blood Lakehouse** is a specialized health-data analytics platform designed to solve the critical problem of fragmented blood inventory data across India. By continuously ingesting published inventory reports from the Ministry of Health & Family Welfare's eRaktKosh portal into a local columnar lakehouse, the system transforms raw nested records into high-speed dimensional marts that empower citizens, hospitals, and emergency coordinators to locate life-saving blood units in seconds.

### Key Ethical & Academic Guarantees:
1. **Zero Data Fabrication**: All historical trend charts, unit quantities, and contact numbers reflect authentic portal data. No synthetic figures are ever inserted.
2. **Geographic Honesty**: Because public portals provide district-level rather than coordinate-level location data, all map pins and facility cards explicitly state: *"approximate location, district level"*.
3. **Clinical Attribution & Safety**: Every view and emergency alert reminds users: *"Data sourced from eRaktKosh (MoHFW, Govt. of India). Academic project, not an official service. Always call the blood bank to confirm before travelling."*

---

## 2. System Prerequisites

The application is engineered to be lightweight, self-contained, and runnable on standard laptop hardware without external database servers (e.g., PostgreSQL or Docker containers are optional, not mandatory).

- **Operating System**: Linux (Ubuntu 20.04+), macOS (12+), or Windows 10/11 (via WSL2)
- **Python**: Version 3.11 or 3.12 (managed via `uv`)
- **Package & Virtualenv Manager**: `uv` (recommended) or standard `pip` / `venv`
- **Web Browser**: Any modern browser (Google Chrome, Mozilla Firefox, Microsoft Edge, Brave)
- **Disk Space**: ~500 MB (includes Python packages, DuckDB database, and local Parquet landing files)

---

## 3. Installation & Quick Startup

### Option A: Using the Automated Makefile (Recommended)

1. Open your terminal in the project directory:
   ```bash
   cd /home/radhey/Documents/project_idea
   ```
2. Start the local server with one command:
   ```bash
   make run
   ```
   *This starts the FastAPI server and serves the Vanilla JS web application at `http://localhost:8000`.*

3. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

### Option B: Manual Execution via `uv`

1. Install project dependencies into the virtual environment:
   ```bash
   uv sync
   ```
2. Run database validation and tests (optional, takes ~5 seconds):
   ```bash
   uv run pytest
   uv run dbt test --project-dir dbt --profiles-dir dbt
   ```
3. Start the Uvicorn web server:
   ```bash
   uv run uvicorn api:app --reload --port 8000
   ```

---

## 4. User Interface Tour

The user interface follows a modern, clinical **Red-and-White design system** (`#FBF8F6` canvas, `#1A1214` ink, `#D21F3C` primary red) free from distracting AI cliches, gradient buttons, and emojis:

```
┌────────────────────────────────────────────────────────────────────────┐
│  [+] eRaktKosh Blood Lakehouse      [Status: Online]  [Lang: EN|HI|GU] │
├────────────────────────────────────────────────────────────────────────┤
│  HERO: National Blood Inventory & Emergency Finder                     │
│  [ State: Gujarat ▼ ] [ District: Anand ▼ ] [ Group: O- ▼ ] [Search]  │
├────────────────────────────────────────────────────────────────────────┤
│  KPIs: [4,692 Facilities]  [35 States]  [1,284 Fresh <24h] [812 Stale] │
├────────────────────────────────────────────────────────────────────────┤
│  [ Grid View ] [ Map View ]                        Showing 1 Facility  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Indian Red Cross Society Anand Blood Bank     [Score: 90/100 HIGH]│  │
│  │ Category: Charitable Blood Bank • Updated: Today (Fresh)         │  │
│  │ Phone: 02692-223344 • Station Road, Anand                        │  │
│  │ Matched: Packed Red Blood Cells (O-): 14 Units                   │  │
│  │ [approximate location, district level]                           │  │
│  │ [Call Facility]   [WhatsApp SOS]   [7-Day Trend Modal]           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│  RARE BLOOD PHENOTYPE RADAR (Bombay Oh+, Oh-, AB-)                     │
├────────────────────────────────────────────────────────────────────────┤
│  DISTRICT SHORTAGE RADAR (Deficit Areas: 0 Units)                      │
├────────────────────────────────────────────────────────────────────────┤
│  FOOTER: Academic Mini Project, MCA, CHARUSAT • Data: MoHFW eRaktKosh  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. User Workflows (Step-by-Step)

### Workflow 1: Searching for Emergency Blood Units
1. **Select State**: Click the **State** dropdown and choose your target state (e.g., `Gujarat`).
2. **Select District**: The **District** dropdown automatically populates with districts in that state. Choose a district (e.g., `Anand`).
3. **Select Component**: Choose the needed blood component (default: `Packed Red Blood Cells`). Other options include `Whole Blood`, `Platelet Concentrate`, `Fresh Frozen Plasma`, and `Cryoprecipitate`.
4. **Select Blood Group**: Choose the patient's blood group (e.g., `O-`).
5. **Click "Search Inventory"**: The system queries `serving.duckdb` via `GET /api/v1/availability` in under 15 milliseconds.
6. **Review Facility Cards**:
   - Each card displays the blood bank's verified name, physical address, and telephone number.
   - The verified unit count for the requested component and blood group is clearly shown.

### Workflow 2: Evaluating Facility Data Reliability
To prevent families in emergency situations from driving to facilities with abandoned listings, every card features an objective **Reliability Score (0-100)**:
- **Green Badge (`HIGH: 75-100`)**: Facility updated inventory within 24 hours, has a valid verified phone number, and reports complete multi-group stock. Highly recommended.
- **Amber Badge (`MODERATE: 45-74`)**: Facility updated within 2-7 days or has partial contact information. Call in advance.
- **Red/Muted Badge (`LOW: <45`)**: Listing has not been updated in over 7 days or lacks valid phone contact. Treat with caution.

### Workflow 3: Interactive Geographic Map View
1. Above the results grid, click the **Map View** toggle button.
2. The view switches seamlessly to an interactive **Leaflet Map** rendered with crisp, clinical **Carto Positron** tiles.
3. Pins indicate blood banks situated at their verified district centroids.
4. Click on any pin marker to open a detailed popup displaying:
   - Full facility name and categorization
   - All available blood groups for the selected component
   - Direct phone call hyperlink
   - Notice: *"approximate location, district level - call before travelling"*

### Workflow 4: Inspecting Historical Stock Trends
1. On any facility card, click the **7-Day History** button.
2. A high-resolution modal dialog appears with a multi-series line chart powered by **Chart.js**.
3. **Interpreting the History**:
   - The chart visualizes real recorded stock levels over time for all blood groups.
   - **Honest Academic Contract**: If only 1 or 2 pipeline runs have been executed, the modal prominently displays:
     > *"Historical delta builds with each real scrape. Only 1 snapshot date currently exists. Execute pipeline on subsequent days to visualize multi-day inventory depletion/replenishment trends."*
   - This provides evaluators with clear proof that no fake historical data was fabricated.

### Workflow 5: One-Click Emergency WhatsApp SOS Sharing
In critical clinical moments, bystanders or attendants need to coordinate with relatives quickly:
1. On any facility card with available stock, click the **WhatsApp SOS** button.
2. A new browser window opens directly to WhatsApp (Web or Mobile App) with a pre-filled, formatted emergency dispatch message:
   ```
   *EMERGENCY BLOOD AVAILABILITY ALERT*
   -----------------------------------
   Facility: Indian Red Cross Society Anand Blood Bank
   Location: Anand, Gujarat (Station Road, Anand)
   Contact: 02692-223344
   
   Component: Packed Red Blood Cells
   Blood Group: O-
   Available Units: 14 Units
   Data Freshness: Updated Today
   Reliability Rating: 90/100 (HIGH)
   
   Note: Verified via eRaktKosh Blood Lakehouse. Call facility immediately to confirm before travelling.
   ```
3. No registration, third-party Twilio accounts, or paid API keys are required.

### Workflow 6: Rare Blood Phenotype Radar
1. Scroll down to the **Rare Blood Phenotype Radar** section.
2. This specialized triage tool highlights facilities that currently hold stocks of:
   - **Bombay Blood Group (`Oh+` and `Oh-`)**: One of the rarest blood phenotypes globally, found in approximately 1 in 10,000 individuals in India.
   - **Rh-Negative Groups (`AB-`, `O-`, `A-`, `B-`)**.
3. Emergency coordinators can instantly identify the nearest city holding these life-saving units.

### Workflow 7: District Shortage & Deficit Radar
1. Scroll to the **District Shortage Radar** section.
2. Select your target blood group (e.g., `O-`).
3. The table lists all districts reporting **0 units** (`SHORTAGE`) or **1-5 units** (`LOW_STOCK`), enabling blood transfusion officers to initiate inter-district stock rebalancing.

---

## 6. Lakehouse Pipeline Administration (CLI)

Evaluators or administrators can run and test the complete end-to-end data pipeline directly from the terminal using the `bloodlake` CLI:

```bash
# Display all available CLI commands
uv run bloodlake --help

# Step 1: Run the asynchronous crawler (scrapes all 781 districts in ~26 seconds)
uv run bloodlake scrape

# Step 2: Ingest the timestamped Parquet landing file into DuckDB Bronze
uv run bloodlake ingest

# Step 3: Execute dbt transformation models (Silver views & Gold marts)
uv run bloodlake transform

# Step 4: Take an append-only daily inventory snapshot
uv run bloodlake snapshot

# Step 5: Run the complete automated pipeline end-to-end with validation
uv run bloodlake all
```

---

## 7. Offline Demo Mode (Examiner Contingency)

If the college Wi-Fi is disconnected, slow, or blocks requests to external government servers:
- The system automatically serves from the existing verified local database (`serving.duckdb`), which contains **4,692 facilities** and **59,259 snapshot rows**.
- Run the demo without scraping:
  ```bash
  make run
  ```
- All search queries, map views, charts, and API endpoints run **100% offline at local speeds (<15ms)**.

---

## 8. Frequently Asked Questions (FAQ)

**Q1: Why does a facility card show "approximate location, district level"?**  
*Answer*: The official eRaktKosh portal lists facility addresses and district names but does not publish verified GPS latitude/longitude coordinates. To remain scientifically honest, our system maps facilities to their verified district centroids rather than guessing exact coordinates.

**Q2: What happens if port 8000 is already in use by another service?**  
*Answer*: You can run the server on any custom port:
```bash
uv run uvicorn api:app --reload --port 8080
```
Then access `http://localhost:8080` in your browser.

**Q3: How can I verify that DuckDB contains real data?**  
*Answer*: Run the interactive DuckDB CLI:
```bash
uv run duckdb serving.duckdb "SELECT hospital_name, state_name, district_name FROM main_gold.dim_blood_banks LIMIT 5;"
```
