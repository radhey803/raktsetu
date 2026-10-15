"""
eRaktKosh Blood Lakehouse FastAPI Application
=============================================
Academic Mini Project - Master of Computer Applications (MCA)
Charotar University of Science and Technology (CHARUSAT)

Serves high-concurrency analytical queries from DuckDB and hosts the Vanilla JS/CSS
web interface from the web/ directory.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from bloodlake.api.routes import router
from bloodlake.config import settings

app = FastAPI(
    title=settings.project_name,
    description=(
        "Real-Time Medallion Blood Lakehouse & Emergency Finder across 781 districts in India. "
        "Academic Mini Project for Master of Computer Applications (MCA), CHARUSAT."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include v1 Analytics Router
app.include_router(router)

# Mount web assets if web directory exists
web_dir = settings.web_dir
if web_dir.exists():
    css_dir = web_dir / "css"
    js_dir = web_dir / "js"
    assets_dir = web_dir / "assets"

    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Also mount /static for backward compatibility
    static_dir = settings.base_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def serve_index():
        index_file = web_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return HTMLResponse("<h1>eRaktKosh Blood Lakehouse</h1><p>API Running. Visit /docs</p>")

    @app.get("/dashboard", response_class=HTMLResponse)
    def serve_dashboard():
        index_file = web_dir / "index.html"
        return FileResponse(str(index_file))


# Legacy Endpoint Shims for Full Backward Compatibility
@app.get("/api/summary", include_in_schema=False)
def legacy_summary(request: Request):
    from bloodlake.api.routes import get_national_summary
    from bloodlake.db import get_serving_connection

    con = get_serving_connection(read_only=True)
    try:
        from fastapi import Response

        res = Response()
        return get_national_summary(res, con)
    finally:
        con.close()


@app.get("/api/locations", include_in_schema=False)
def legacy_locations():
    from bloodlake.api.routes import get_locations
    from bloodlake.db import get_serving_connection

    con = get_serving_connection(read_only=True)
    try:
        return get_locations(con)
    finally:
        con.close()


@app.get("/api/search", include_in_schema=False)
def legacy_search(
    state: str = None,
    district: str = None,
    component: str = "Packed Red Blood Cells",
    blood_group: str = None,
    search_query: str = None,
    limit: int = 300,
):
    from bloodlake.db import get_serving_connection
    from bloodlake.geo import resolve_facility_lat_lng

    con = get_serving_connection(read_only=True)
    try:
        where_clauses = ["1=1"]
        params = []
        if state and state != "ALL":
            where_clauses.append("b.state_name = ?")
            params.append(state)
        if district and district != "ALL":
            where_clauses.append("b.district_name = ?")
            params.append(district)
        if component and component != "ALL":
            where_clauses.append("s.component_name = ?")
            params.append(component)
        if blood_group and blood_group != "ALL":
            where_clauses.append("s.blood_group = ?")
            params.append(blood_group)
        if search_query and search_query.strip():
            where_clauses.append(
                "(LOWER(b.hospital_name) LIKE ? OR LOWER(b.hospital_address) LIKE ?)"
            )
            q = f"%{search_query.strip().lower()}%"
            params.extend([q, q])

        where_sql = " AND ".join(where_clauses)
        sql = f"""
            SELECT
                b.hospital_code,
                b.hospital_name,
                b.hospital_type,
                b.facility_type,
                b.state_name,
                b.district_name,
                b.hospital_contact,
                b.hospital_address,
                MAX(s.source_updated_at) AS last_updated_at,
                DATE_DIFF('day', MAX(s.source_updated_at), CURRENT_TIMESTAMP) AS days_since_update,
                COALESCE(r.reliability_score, 50) AS reliability_score,
                COALESCE(r.reliability_tier, 'SILVER') AS reliability_tier,
                string_agg(s.blood_group || ': ' || CAST(s.units AS VARCHAR), ', ') AS stock_summary
            FROM main_gold.dim_blood_banks b
            JOIN main_gold.fct_stock_current s ON b.hospital_code = s.hospital_code
            LEFT JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
            WHERE {where_sql}
            GROUP BY
                b.hospital_code, b.hospital_name, b.hospital_type, b.facility_type,
                b.state_name, b.district_name, b.hospital_contact, b.hospital_address,
                r.reliability_score, r.reliability_tier
            ORDER BY days_since_update ASC NULLS LAST, reliability_score DESC
            LIMIT ?;
        """
        params.append(limit)
        rows = con.execute(sql, params).fetchall()

        hospitals = []
        for r in rows:
            (
                h_code,
                h_name,
                h_type,
                f_type,
                s_name,
                d_name,
                contact,
                address,
                updated_at,
                days_ago,
                score,
                tier,
                stock_str,
            ) = r
            lat, lng, is_approx = resolve_facility_lat_lng(h_code, s_name, d_name)
            hospitals.append(
                {
                    "code": h_code,
                    "name": h_name,
                    "type": h_type,
                    "facility": f_type,
                    "state": s_name,
                    "district": d_name,
                    "contact": contact or "",
                    "address": address or "",
                    "component": component
                    if component and component != "ALL"
                    else "Packed Red Blood Cells",
                    "stock": stock_str or "",
                    "last_updated": str(updated_at)[:19] if updated_at else "",
                    "days_stale": days_ago if days_ago is not None else 0,
                    "reliability_score": score,
                    "reliability_tier": tier,
                    "lat": lat,
                    "lng": lng,
                    "is_approximate": is_approx,
                }
            )
        return {"hospitals": hospitals, "total": len(hospitals)}
    finally:
        con.close()
