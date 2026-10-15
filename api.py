"""
eRaktKosh Analytics & Emergency Finder API
==========================================
FastAPI backend querying DuckDB Gold layer in read-only mode (<2ms latency).
"""

import os
import re
import sys
from typing import Optional

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import duckdb
from snapshot_manager import query_hospital_trend, query_district_trend
from geo_coords import resolve_facility_lat_lng

SERVING_DB_PATH = os.path.join(WORKSPACE_DIR, "serving.duckdb")
WAREHOUSE_DB_PATH = os.path.join(WORKSPACE_DIR, "blood_warehouse.duckdb")

app = FastAPI(title="eRaktKosh Blood Lakehouse API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    """
    Connects to the database in read_only mode.
    Prefers serving.duckdb for zero-lock concurrency, falling back to blood_warehouse.duckdb.
    Attaches catalog alias so compiled dbt views resolve without BinderError.
    """
    for path in [SERVING_DB_PATH, WAREHOUSE_DB_PATH]:
        if os.path.exists(path):
            try:
                con = duckdb.connect(path, read_only=True)
                # Ensure cross-database dbt catalog references resolve
                try:
                    con.execute(f"ATTACH '{path}' AS blood_warehouse (READ_ONLY);")
                except Exception:
                    pass
                return con
            except Exception:
                continue
    raise HTTPException(status_code=500, detail="DuckDB database file not found or accessible. Run pipeline first.")



# ----------------- API ENDPOINTS -----------------

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "engine": "DuckDB + dbt Core", "version": "1.0.0"}

@app.get("/api/summary")
def get_national_summary():
    """Returns high-level KPI cards for the dashboard header."""
    con = get_db()
    
    row_banks = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()
    total_banks = row_banks[0] if row_banks else 0

    row_states = con.execute("SELECT COUNT(DISTINCT state_name) FROM main_gold.fct_state_blood_summary;").fetchone()
    total_states = row_states[0] if row_states else 0

    row_stale = con.execute("SELECT COUNT(*) FROM main_gold.fct_blood_shortage_alerts WHERE days_since_last_update > 30;").fetchone()
    stale_banks = row_stale[0] if row_stale else 0

    row_fresh = con.execute("SELECT COUNT(*) FROM main_gold.fct_blood_shortage_alerts WHERE days_since_last_update <= 1;").fetchone()
    fresh_banks = row_fresh[0] if row_fresh else 0

    top_states = con.execute("""
        SELECT state_name, SUM(total_blood_banks) as banks
        FROM main_gold.fct_state_blood_summary
        GROUP BY state_name
        ORDER BY banks DESC
        LIMIT 6;
    """).fetchall()

    con.close()
    return {
        "total_banks": total_banks,
        "total_states": total_states,
        "fresh_banks": fresh_banks,
        "stale_banks": stale_banks,
        "top_states": [{"state": s[0], "banks": s[1]} for s in top_states]
    }

@app.get("/api/locations")
def get_location_hierarchy():
    """Returns distinct states and districts for dropdown filters."""
    con = get_db()
    results = con.execute("""
        SELECT DISTINCT state_name, district_name 
        FROM main_gold.dim_blood_banks 
        WHERE state_name IS NOT NULL AND district_name IS NOT NULL
        ORDER BY state_name, district_name;
    """).fetchall()
    con.close()

    locations = {}
    for state, district in results:
        if state not in locations:
            locations[state] = []
        if district and district not in locations[state]:
            locations[state].append(district)

    return locations

@app.get("/api/history")
def get_hospital_history(
    hospital_code: int = Query(..., description="Hospital Code"),
    component: Optional[str] = Query("Packed Red Blood Cells", description="Blood Component"),
    days: int = Query(14, ge=1, le=90, description="Number of days of history")
):
    """
    Returns time-series stock history and 7-day trend metrics for a specific hospital
    across all blood groups.
    """
    con = get_db()
    data = query_hospital_trend(con, hospital_code, component_name=component or "Packed Red Blood Cells", days=days)
    con.close()
    return data

@app.get("/api/district-trends")
def get_district_trends(
    state: str = Query(..., description="State Name"),
    district: str = Query(..., description="District Name"),
    component: Optional[str] = Query("Packed Red Blood Cells", description="Blood Component"),
    blood_group: Optional[str] = Query("O-", description="Target Blood Group"),
    days: int = Query(14, ge=1, le=90, description="Number of days")
):
    """
    Returns aggregate time-series stock trends for an entire district to track
    evolving shortages and well-stocked periods.
    """
    con = get_db()
    data = query_district_trend(
        con,
        state=state,
        district=district,
        component_name=component or "Packed Red Blood Cells",
        blood_group=blood_group or "O-",
        days=days
    )
    con.close()
    return data

def extract_component_stock(comp_raw: str, target_component: Optional[str] = None) -> str:
    """
    Extracts available_WithQty for a target component,
    or combines all available_WithQty if target_component is 'ALL' or None.
    """
    if not comp_raw:
        return ""
    
    if target_component and target_component != "ALL":
        pattern = rf"'{re.escape(target_component)}':\s*\{{[^}}]*'available_WithQty':\s*'([^']*)'"
        match = re.search(pattern, comp_raw, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
    else:
        avail_matches = re.findall(r"'available_WithQty':\s*'([^']+)'", comp_raw)
        return ', '.join([m.strip() for m in avail_matches if m.strip()])

def check_blood_group_available(stock_str: str, bg: str) -> bool:
    if not stock_str:
        return False
    bg = bg.strip().lower()
    
    # Check specific group patterns in in-stock string (using negative lookbehind to prevent B+ matching AB+)
    patterns = {
        "o-": r'(?<![a-zA-Z])O\s*-\s*[Vv]e\s*:\s*([1-9]\d*)',
        "o+": r'(?<![a-zA-Z])O\s*\+\s*[Vv]e\s*:\s*([1-9]\d*)',
        "a+": r'(?<![a-zA-Z])A\s*\+\s*[Vv]e\s*:\s*([1-9]\d*)',
        "a-": r'(?<![a-zA-Z])A\s*-\s*[Vv]e\s*:\s*([1-9]\d*)',
        "b+": r'(?<![a-zA-Z])B\s*\+\s*[Vv]e\s*:\s*([1-9]\d*)',
        "b-": r'(?<![a-zA-Z])B\s*-\s*[Vv]e\s*:\s*([1-9]\d*)',
        "ab+": r'(?<![a-zA-Z])AB\s*\+\s*[Vv]e\s*:\s*([1-9]\d*)',
        "ab-": r'(?<![a-zA-Z])AB\s*-\s*[Vv]e\s*:\s*([1-9]\d*)',
        "bombay": r'Oh\s*[\+\-]\s*[Vv][Ee]\s*:\s*([1-9]\d*)'
    }
    
    if bg in patterns:
        return bool(re.search(patterns[bg], stock_str))
        
    return bg in stock_str.lower()

@app.get("/api/search")
def search_hospitals(
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    component: Optional[str] = Query("Packed Red Blood Cells"),
    blood_group: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None),
    limit: int = 60
):
    """Emergency SOS Search checking live inventory by component, blood group, and contact."""
    con = get_db()
    
    sql = """
        SELECT 
            b.hospital_code,
            b.hospital_name,
            b.hospital_type,
            b.facility_type,
            b.state_name,
            b.district_name,
            b.hospital_contact,
            b.hospital_address,
            b.source_updated_at AS last_updated_at,
            a.days_since_last_update,
            a.data_freshness_status,
            a.stock_alert_level,
            s.components_raw
        FROM main_gold.dim_blood_banks b
        LEFT JOIN (
            SELECT 
                hospital_code,
                days_since_last_update,
                data_freshness_status,
                stock_alert_level
            FROM main_gold.fct_blood_shortage_alerts
            QUALIFY ROW_NUMBER() OVER (PARTITION BY hospital_code ORDER BY last_updated_at DESC NULLS LAST) = 1
        ) a ON b.hospital_code = a.hospital_code
        LEFT JOIN (
            SELECT hospital_code, components_raw
            FROM main_silver.stg_blood_inventory
            WHERE components_raw IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (PARTITION BY hospital_code ORDER BY last_updated_at DESC NULLS LAST) = 1
        ) s ON b.hospital_code = s.hospital_code
        WHERE 1=1
    """
    params = []
    
    if state and state != "ALL":
        sql += " AND b.state_name = ?"
        params.append(state)
        
    if district and district != "ALL":
        sql += " AND b.district_name = ?"
        params.append(district)
        
    if search_query and search_query.strip():
        sql += " AND (LOWER(b.hospital_name) LIKE ? OR LOWER(b.hospital_address) LIKE ?)"
        q = f"%{search_query.lower().strip()}%"
        params.extend([q, q])

    sql += " ORDER BY a.days_since_last_update ASC NULLS LAST"

    rows = con.execute(sql, params).fetchall()
    con.close()

    results = []
    for r in rows:
        comp_raw = r[12] or ""
        
        # Extract stock specifically for the chosen component (e.g. Packed Red Blood Cells)
        stock_str = extract_component_stock(comp_raw, component)
        
        # If user picked a component but this hospital has 0 stock of that component,
        # and they're filtering by blood group or searching by component:
        if component and component != "ALL" and blood_group:
            if not check_blood_group_available(stock_str, blood_group):
                continue
        elif blood_group and blood_group.strip():
            if not check_blood_group_available(stock_str, blood_group):
                continue

        lat, lng = resolve_facility_lat_lng(r[0], r[4] or "", r[5] or "")

        results.append({
            "code": r[0],
            "name": r[1],
            "type": r[2],
            "facility": r[3],
            "state": r[4],
            "district": r[5],
            "contact": r[6],
            "address": r[7],
            "last_updated": str(r[8]) if r[8] else "Unknown",
            "days_stale": r[9],
            "freshness": r[10] or "UNKNOWN",
            "alert": r[11] or "NORMAL",
            "stock": stock_str,
            "component": component or "All Components",
            "lat": lat,
            "lng": lng
        })
        
        if len(results) >= limit:
            break

    return {"count": len(results), "hospitals": results}


# Serve static web frontend
os.makedirs(os.path.join(WORKSPACE_DIR, "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(WORKSPACE_DIR, "static")), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(WORKSPACE_DIR, "static", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "eRaktKosh API running. Create static/index.html to view dashboard."}

@app.get("/dashboard")
def serve_dashboard():
    dash_file = os.path.join(WORKSPACE_DIR, "static", "dashboard.html")
    if os.path.exists(dash_file):
        return FileResponse(dash_file)
    return {"message": "Dashboard available at /static/dashboard.html"}

@app.get("/terms")
def serve_terms():
    terms_file = os.path.join(WORKSPACE_DIR, "static", "terms.html")
    if os.path.exists(terms_file):
        return FileResponse(terms_file)
    return {"message": "Terms available at /static/terms.html"}

@app.get("/privacy")
def serve_privacy():
    priv_file = os.path.join(WORKSPACE_DIR, "static", "privacy.html")
    if os.path.exists(priv_file):
        return FileResponse(priv_file)
    return {"message": "Privacy available at /static/privacy.html"}

@app.get("/disclaimer")
def serve_disclaimer():
    disc_file = os.path.join(WORKSPACE_DIR, "static", "disclaimer.html")
    if os.path.exists(disc_file):
        return FileResponse(disc_file)
    return {"message": "Disclaimer available at /static/disclaimer.html"}

