# BloodGrid REST API Reference (`/v1`)

Welcome to the BloodGrid REST API. All endpoints return predictable JSON with standard error formats, request tracing IDs (`X-Request-ID`), and data source attributions.

**Base URL**: `https://api.bloodgrid.in` (Production) / `http://localhost:8000` (Local Dev)  
**OpenAPI Specification**: Interactive Swagger docs available at `/docs` or ReDoc at `/redoc`.

---

## 1. Authentication

Public search endpoints do not require authentication. Commercial and programmatic endpoints require an API Key passed in the `X-API-Key` header:

```bash
curl -H "X-API-Key: bg_live_your_api_key_secret" \
  https://api.bloodgrid.in/v1/availability
```

API Key prefixes:
- `bg_live_...`: Production key
- `bg_test_...`: Sandbox test key

---

## 2. Endpoints

### 2.1 Emergency Component Availability Search
`GET /v1/availability`

Search live component inventory with exact normalized blood groups and reliability ratings.

**Parameters**:
- `state` *(string, optional)*: State name (e.g. `Gujarat`)
- `district` *(string, optional)*: District name (e.g. `Anand`)
- `component` *(string, optional, default: "Packed Red Blood Cells")*: Component name
- `blood_group` *(string, optional)*: Normalized group (`O+`, `O-`, `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `Bombay (Oh+)`, `Bombay (Oh-)`)
- `min_units` *(integer, default: 0)*: Filter minimum units
- `sort` *(string, default: "freshness")*: `freshness`, `units`, or `reliability`
- `limit` *(integer, default: 50, max: 200)*: Result limit
- `offset` *(integer, default: 0)*: Result offset for pagination

**Curl Example**:
```bash
curl "https://api.bloodgrid.in/v1/availability?state=Gujarat&district=Anand&blood_group=O-&component=Packed%20Red%20Blood%20Cells"
```

**Response**:
```json
{
  "success": true,
  "request_id": "9d48b783-ff02-4809-a1b4-5698bcf33a1e",
  "pagination": {
    "total": 4,
    "limit": 50,
    "offset": 0,
    "has_more": false
  },
  "data": [
    {
      "hospital_code": 24125,
      "hospital_name": "Indian Red Cross Society Anand",
      "hospital_type": "Red Cross",
      "facility_type": "Blood Bank",
      "state_name": "Gujarat",
      "district_name": "Anand",
      "hospital_contact": "02692-223344",
      "hospital_address": "Station Road, Anand",
      "source_updated_at": "2026-10-14T18:00:00",
      "matched_component": "Packed Red Blood Cells",
      "matched_group": "O-",
      "matched_units": 6,
      "reliability_score": 92,
      "reliability_tier": "HIGH",
      "latitude": 22.5645,
      "longitude": 72.9289,
      "precision": "exact",
      "all_components_stock": {
        "Packed Red Blood Cells": {"O+": 18, "O-": 6, "A+": 12, "B+": 24}
      }
    }
  ],
  "source_attribution": "Data sourced from eRaktKosh (Ministry of Health & Family Welfare, Govt. of India). Not an official service. Always call the blood bank to confirm before travelling."
}
```

---

### 2.2 Facility Profile & Full Stock Matrix
`GET /v1/banks/{hospital_code}`

Fetches full facility details, reliability score breakdown, and complete multi-component stock matrix.

**Curl Example**:
```bash
curl "https://api.bloodgrid.in/v1/banks/24125"
```

---

### 2.3 Rare Blood Radar
`GET /v1/rare`

Rapid emergency radar for rare Bombay Blood Group (`Oh+`, `Oh-`) and negative blood groups (`O-`, `AB-`, `A-`, `B-`).

**Curl Example**:
```bash
curl "https://api.bloodgrid.in/v1/rare?state=Gujarat&group=Bombay%20(Oh%2B)"
```

---

### 2.4 District Shortage & Supply Status
`GET /v1/shortages`

Identifies districts with critical deficit states where reporting banks indicate 0 available units for a given group.

**Curl Example**:
```bash
curl "https://api.bloodgrid.in/v1/shortages?state=Gujarat"
```

---

### 2.5 System Metadata & Attribution
`GET /v1/meta`

System execution stats, total reporting facilities, and last successful crawl timestamp.

**Curl Example**:
```bash
curl "https://api.bloodgrid.in/v1/meta"
```

---

## 3. Error Handling

Standard HTTP status codes are returned with a structured error payload:

```json
{
  "success": false,
  "request_id": "c76e5d22-19e3-4f33-8a9d-5a67123bcdef",
  "detail": "Facility code 9999999 not found",
  "code": "FACILITY_NOT_FOUND"
}
```

Common status codes:
- `400 Bad Request`: Invalid parameter format or validation error.
- `401 Unauthorized`: Missing or invalid API key.
- `404 Not Found`: Resource does not exist.
- `429 Too Many Requests`: Rate limit exceeded for tier.
- `503 Service Unavailable`: Serving database is mounting or refreshing.
