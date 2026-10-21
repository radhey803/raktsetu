# eRaktKosh Blood Lakehouse: REST API Reference (`/api/v1`)

**Context**: Academic Research Project  
**Department**: Academic Research Team  
**Project**: eRaktKosh Blood Lakehouse (Academic Mini Project — 800 Marks)  
**Framework**: FastAPI (Asynchronous Python 3.12)  
**Database**: DuckDB In-Process OLAP (`serving.duckdb`)  
**Base URL**: `http://localhost:8000`  
**Interactive Documentation**:  
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)  
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)  

---

## 1. Overview & Architecture

The **eRaktKosh Blood Lakehouse REST API** provides low-latency analytical query interfaces directly over DuckDB Gold dimensional marts. Queries are executed concurrently against `serving.duckdb` via read-only connections with parameterized inputs to completely eliminate SQL injection risks.

### Response Conventions
- All successful responses return HTTP status `200 OK`.
- Responses are formatted in JSON with ISO 8601 timestamps.
- Zero fake data policy: All returned figures originate from authentic eRaktKosh portal ingestions.
- Source Attribution: All public interfaces must cite MoHFW, Government of India.

---

## 2. API Endpoints

### 2.1 System Health Probe
`GET /healthz`

Liveness and readiness probe verifying DuckDB connectivity and serving database availability.

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/healthz"
```

#### Response (`200 OK`):
```json
{
  "status": "healthy",
  "database": "DuckDB Lakehouse",
  "timestamp": "2026-10-15T14:40:00.123456+00:00"
}
```

---

### 2.2 Academic Metadata & Sync Status
`GET /api/v1/meta`

Returns university project metadata, academic guide details, last successful pipeline synchronization timestamp, and legal/ethical attribution.

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/v1/meta"
```

#### Response (`200 OK`):
```json
{
  "project_name": "eRaktKosh Blood Lakehouse",
  "project_subtitle": "National Blood Inventory & Emergency Finder",
  "version": "1.0.0",
  "institution": "Academic Research Project",
  "department": "Department of Computer Applications (MCA)",
  "academic_guide": "MCA Faculty Guide",
  "author": "MCA Student Team",
  "last_synced_at": "2026-10-15 14:00:00",
  "total_facilities": 4692,
  "data_source": "eRaktKosh (MoHFW, Govt. of India)",
  "attribution": "Data sourced from eRaktKosh (MoHFW, Govt. of India). Academic project, not an official service.",
  "disclaimer": "Data reflects periodic snapshots from eRaktKosh portal. Always contact the blood bank directly to confirm live unit availability."
}
```

---

### 2.3 National Summary KPIs
`GET /api/v1/summary`

Returns national-level aggregate indicators for dashboard metric cards, including total facilities tracked, distinct states, facilities updated within 24 hours, stale facilities (>30 days), and top reporting states.

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/v1/summary"
```

#### Response (`200 OK`):
```json
{
  "total_banks": 4692,
  "total_states": 35,
  "fresh_banks_24h": 1284,
  "stale_banks_30d": 812,
  "top_states": [
    {"state": "Maharashtra", "banks": 384},
    {"state": "Uttar Pradesh", "banks": 362},
    {"state": "Tamil Nadu", "banks": 328},
    {"state": "Gujarat", "banks": 296},
    {"state": "Karnataka", "banks": 254},
    {"state": "West Bengal", "banks": 218},
    {"state": "Rajasthan", "banks": 198},
    {"state": "Kerala", "banks": 182}
  ]
}
```

---

### 2.4 Geographic Hierarchy (States & Districts)
`GET /api/v1/locations`

Returns the hierarchical mapping of Indian states to districts for populating cascading dropdown selectors on the user interface.

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/v1/locations"
```

#### Response (`200 OK`):
```json
{
  "Gujarat": [
    "Ahmedabad",
    "Amreli",
    "Anand",
    "Aravalli",
    "Banaskantha",
    "Bharuch",
    "Bhavnagar",
    "Botad",
    "Chhotaudepur",
    "Dahod",
    "Dang",
    "Devbhumi Dwarka",
    "Gandhinagar",
    "Gir Somnath",
    "Jamnagar",
    "Junagadh",
    "Kheda",
    "Kutch",
    "Mahisagar",
    "Mehsana",
    "Morbi",
    "Narmada",
    "Navsari",
    "Panchmahal",
    "Patan",
    "Porbandar",
    "Rajkot",
    "Sabarkantha",
    "Surat",
    "Surendranagar",
    "Tapi",
    "Vadodara",
    "Valsad"
  ],
  "Maharashtra": [
    "Ahmednagar",
    "Akola",
    "Amravati",
    "Aurangabad",
    "Mumbai City",
    "Pune"
  ]
}
```

---

### 2.5 Facility Directory
`GET /api/v1/banks`

Paginated listing of all licensed blood facilities with address details, contact numbers, freshness indicators, and 0-100 reliability ratings.

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `state` | `string` | No | `null` | Filter by state name (e.g. `Gujarat`) |
| `district` | `string` | No | `null` | Filter by district name (e.g. `Anand`) |
| `search` | `string` | No | `null` | Case-insensitive substring search in name/address |
| `page` | `integer`| No | `1` | Page number ($\ge 1$) |
| `page_size`| `integer`| No | `15` | Results per page ($1-100$) |

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/v1/banks?state=Gujarat&district=Anand&page=1&page_size=2"
```

#### Response (`200 OK`):
```json
{
  "items": [
    {
      "hospital_code": 24125,
      "hospital_name": "Indian Red Cross Society Anand Blood Bank",
      "hospital_type": "Charitable",
      "facility_type": "Blood Bank",
      "state_name": "Gujarat",
      "district_name": "Anand",
      "hospital_contact": "02692-223344",
      "hospital_address": "Station Road, Anand 388001",
      "last_updated_at": "2026-10-14T17:45:00",
      "days_since_last_update": 0,
      "data_freshness_status": "FRESH",
      "stock_alert_level": "ADEQUATE",
      "reliability_score": 90,
      "reliability_tier": "HIGH",
      "latitude": 22.5645,
      "longitude": 72.9289,
      "is_approximate_location": true
    }
  ],
  "total": 6,
  "page": 1,
  "page_size": 2,
  "total_pages": 3
}
```

---

### 2.6 Emergency Inventory Availability Search
`GET /api/v1/availability`

The core search endpoint for emergency blood availability. Queries `fct_stock_current` using pure SQL without brittle application-side regular expressions. Filters by state, district, blood component, normalized blood group, and minimum unit thresholds.

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `state` | `string` | No | `null` | State name |
| `district` | `string` | No | `null` | District name |
| `blood_group` | `string` | No | `null` | Normalized group (`O+`, `O-`, `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `Bombay (Oh+)`, `Bombay (Oh-)`) |
| `component` | `string` | No | `Packed Red Blood Cells` | Component name |
| `min_units` | `integer`| No | `0` | Minimum units threshold |
| `max_age_hours`| `integer`| No | `null` | Exclude records older than N hours |
| `page` | `integer`| No | `1` | Page number |
| `page_size` | `integer`| No | `15` | Items per page |

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/v1/availability?state=Gujarat&district=Anand&blood_group=O-&component=Packed%20Red%20Blood%20Cells"
```

#### Response (`200 OK`):
```json
{
  "items": [
    {
      "hospital_code": 24125,
      "hospital_name": "Indian Red Cross Society Anand Blood Bank",
      "hospital_type": "Charitable",
      "facility_type": "Blood Bank",
      "state_name": "Gujarat",
      "district_name": "Anand",
      "hospital_contact": "02692-223344",
      "hospital_address": "Station Road, Anand 388001",
      "component_name": "Packed Red Blood Cells",
      "blood_group": "O-",
      "units": 14,
      "last_updated_at": "2026-10-14T17:45:00",
      "days_since_last_update": 0,
      "reliability_score": 90,
      "reliability_tier": "HIGH",
      "latitude": 22.5645,
      "longitude": 72.9289,
      "is_approximate_location": true
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 15,
  "total_pages": 1
}
```

---

### 2.7 Historical Stock Trend (Time-Series)
`GET /api/v1/history`

Returns time-series history for a specified blood bank, component, and blood group queried strictly from `main_gold.fct_stock_snapshot`.

#### Zero Fake Data Contract:
If fewer than 2 distinct daily snapshots exist, `has_sufficient_history` returns `false` with an explanatory message: *"Historical delta builds with each real scrape. Only 1 snapshot date currently exists."* No simulated or extrapolated points are ever generated.

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `hospital_code` | `integer`| Yes | — | Facility ID code |
| `component` | `string` | No | `Packed Red Blood Cells` | Component name |
| `blood_group` | `string` | No | `O-` | Blood group |

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/v1/history?hospital_code=24125&blood_group=O-&component=Packed%20Red%20Blood%20Cells"
```

#### Response (`200 OK`):
```json
{
  "hospital_code": 24125,
  "hospital_name": "Indian Red Cross Society Anand Blood Bank",
  "component_name": "Packed Red Blood Cells",
  "blood_group": "O-",
  "points": [
    {
      "snapshot_date": "2026-10-14",
      "units": 14
    }
  ],
  "has_sufficient_history": false,
  "message": "Historical delta builds with each real scrape. Only 1 snapshot date currently exists. Execute 'bloodlake all' on subsequent days to visualize multi-day inventory depletion/replenishment trends."
}
```

---

### 2.8 Multi-Group Stock History (Modal Chart)
`GET /api/history`

Supplies multi-series historical data across all blood groups for a facility and component, formatting dates and critical stock flags for Chart.js visualization.

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `hospital_code` | `integer`| Yes | — | Facility ID code |
| `component` | `string` | No | `Packed Red Blood Cells` | Component name |
| `days` | `integer`| No | `14` | History window in days ($1-90$) |

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/history?hospital_code=24125&days=7"
```

#### Response (`200 OK`):
```json
{
  "hospital_code": 24125,
  "hospital_name": "Indian Red Cross Society Anand Blood Bank",
  "district": "Anand",
  "state": "Gujarat",
  "component": "Packed Red Blood Cells",
  "dates": ["Oct 14"],
  "series": {
    "A+": [18],
    "A-": [4],
    "B+": [22],
    "B-": [5],
    "O+": [30],
    "O-": [14],
    "AB+": [8],
    "AB-": [2]
  },
  "summary": {
    "O-": {
      "current": 14,
      "peak": 14,
      "change_7d": "0",
      "is_critical": false
    },
    "AB-": {
      "current": 2,
      "peak": 2,
      "change_7d": "0",
      "is_critical": true
    }
  }
}
```

---

### 2.9 District Deficit & Shortage Radar
`GET /api/v1/shortages`

Aggregates inventory at the district level from `mart_district_status` and flags administrative areas with critical stock deficits (`SHORTAGE` with 0 units, `LOW_STOCK` with 1-5 units, `ADEQUATE` with >5 units).

#### Query Parameters:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `state` | `string` | No | `null` | Filter by state |
| `blood_group` | `string` | No | `O-` | Blood group to inspect |
| `component` | `string` | No | `Packed Red Blood Cells` | Component to inspect |

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/v1/shortages?state=Gujarat&blood_group=O-"
```

#### Response (`200 OK`):
```json
[
  {
    "state_name": "Gujarat",
    "district_name": "Dang",
    "blood_group": "O-",
    "component_name": "Packed Red Blood Cells",
    "total_units": 0,
    "reporting_banks": 1,
    "shortage_status": "SHORTAGE"
  },
  {
    "state_name": "Gujarat",
    "district_name": "Aravalli",
    "blood_group": "O-",
    "component_name": "Packed Red Blood Cells",
    "total_units": 2,
    "reporting_banks": 2,
    "shortage_status": "LOW_STOCK"
  }
]
```

---

### 2.10 Rare Blood Phenotype Finder
`GET /api/v1/rare`

Rapid filter identifying facilities currently reporting verified availability of rare phenotypes: Bombay Blood Group (`Bombay (Oh+)`, `Bombay (Oh-)`) and Rh-negative blood groups (`AB-`, `O-`, `A-`, `B-`).

#### Curl Request:
```bash
curl -X GET "http://localhost:8000/api/v1/rare"
```

#### Response (`200 OK`):
```json
[
  {
    "hospital_code": 19283,
    "hospital_name": "KEM Hospital Blood Bank",
    "state_name": "Maharashtra",
    "district_name": "Mumbai City",
    "blood_group": "Bombay (Oh+)",
    "component_name": "Packed Red Blood Cells",
    "units": 2,
    "hospital_contact": "022-24107000",
    "last_updated_at": "2026-10-14T12:30:00"
  }
]
```

---

## 3. Error Handling & Status Codes

All API endpoints implement standard HTTP status codes:

| HTTP Status | Reason | Cause |
| :---: | :--- | :--- |
| `200 OK` | Success | Query executed successfully and returned data. |
| `400 Bad Request` | Client Error | Invalid parameter value or query format. |
| `404 Not Found` | Resource Not Found | Specified `hospital_code` does not exist. |
| `500 Internal Error`| Server Error | Unexpected DuckDB or server exception. |
| `503 Unavailable` | Database Error | DuckDB database file locked or connection failure. |

#### Error Format:
```json
{
  "detail": "Hospital code 999999 not found in database."
}
```
