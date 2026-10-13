"""
eRaktKosh Analytics & Emergency Finder API
==========================================
FastAPI backend querying DuckDB Gold layer in read-only mode (<2ms latency).
"""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import duckdb

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(WORKSPACE_DIR, "blood_warehouse.duckdb")

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
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="DuckDB warehouse file not found. Run pipeline first.")
    # Always open in read_only mode to prevent locks and enable instant concurrent queries
    return duckdb.connect(DB_PATH, read_only=True)

# ----------------- API ENDPOINTS -----------------

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "engine": "DuckDB + dbt Core", "version": "1.0.0"}

@app.get("/api/summary")
def get_national_summary():
    """Returns high-level KPI cards for the dashboard header."""
    con = get_db()
    
    total_banks = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
    total_states = con.execute("SELECT COUNT(DISTINCT state_name) FROM main_gold.fct_state_blood_summary;").fetchone()[0]
    stale_banks = con.execute("SELECT COUNT(*) FROM main_gold.fct_blood_shortage_alerts WHERE days_since_last_update > 30;").fetchone()[0]
    fresh_banks = con.execute("SELECT COUNT(*) FROM main_gold.fct_blood_shortage_alerts WHERE days_since_last_update <= 1;").fetchone()[0]

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

@app.get("/api/search")
def search_hospitals(
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None),
    limit: int = 50
):
    """Emergency SOS Search with hospital contacts and staleness ratings."""
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
            b.last_updated_at,
            a.days_since_last_update,
            a.data_freshness_status,
            a.stock_alert_level
        FROM main_gold.dim_blood_banks b
        LEFT JOIN main_gold.fct_blood_shortage_alerts a 
               ON b.hospital_code = a.hospital_code
        WHERE 1=1
    """
    params = []
    
    if state and state != "ALL":
        sql += " AND b.state_name = ?"
        params.append(state)
        
    if district and district != "ALL":
        sql += " AND b.district_name = ?"
        params.append(district)
        
    if search_query:
        sql += " AND (LOWER(b.hospital_name) LIKE ? OR LOWER(b.hospital_address) LIKE ?)"
        q = f"%{search_query.lower()}%"
        params.extend([q, q])

    sql += " ORDER BY a.days_since_last_update ASC NULLS LAST LIMIT ?"
    params.append(limit)

    rows = con.execute(sql, params).fetchall()
    con.close()

    results = []
    for r in rows:
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
            "alert": r[11] or "NORMAL"
        })

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
