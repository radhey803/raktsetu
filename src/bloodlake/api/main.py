"""
eRaktKosh Blood Lakehouse FastAPI Application
=============================================
Academic Project - Blood Inventory Intelligence Lakehouse

Serves high-concurrency analytical queries from DuckDB and hosts the Vanilla JS/CSS
web interface from the web/ directory.
"""

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from bloodlake.api.routes import router
from bloodlake.config import settings

app = FastAPI(
    title=settings.project_name,
    description=(
        "Real-Time Medallion Blood Lakehouse & Emergency Finder across 781 districts in India. "
        "Academic Project for clinical decision support and public health informatics."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # browsers reject credentials with a wildcard origin
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

    # Mount dbt docs if generated in dbt/target
    dbt_target = settings.base_dir / "dbt" / "target"
    if dbt_target.exists() and (dbt_target / "index.html").exists():
        app.mount("/dbt-docs", StaticFiles(directory=str(dbt_target), html=True), name="dbt_docs")
    else:

        @app.get("/dbt-docs/", response_class=HTMLResponse)
        def dbt_docs_missing():
            return HTMLResponse("<p>dbt docs not generated yet. Run <code>make docs</code>.</p>")

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

    @app.get("/manifest.json")
    def serve_manifest():
        manifest_file = web_dir / "manifest.json"
        if manifest_file.exists():
            return FileResponse(str(manifest_file), media_type="application/manifest+json")
        return Response(status_code=404)

    @app.get("/sw.js")
    def serve_service_worker():
        sw_file = web_dir / "sw.js"
        if sw_file.exists():
            return FileResponse(
                str(sw_file),
                media_type="application/javascript",
                headers={"Service-Worker-Allowed": "/"},
            )
        return Response(status_code=404)


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
    sort: str = "freshness",
    lat: float = None,
    lng: float = None,
    limit: int = Query(300, ge=1, le=10000),
):
    from bloodlake.db import get_serving_connection
    from bloodlake.geo import haversine_distance_km, resolve_facility_lat_lng

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
        comp_clause = ""
        comp_params = []
        if component and component != "ALL":
            comp_clause = "WHERE component_name = ?"
            comp_params = [component]
        if blood_group and blood_group != "ALL":
            where_clauses.append("s.blood_group = ?")
            params.append(blood_group)
        if search_query and search_query.strip():
            where_clauses.append(
                "(contains(LOWER(b.hospital_name), ?) OR contains(LOWER(b.hospital_address), ?))"
            )
            q = search_query.strip().lower()
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
                COALESCE(r.reliability_label, r.reliability_tier, 'Medium') AS reliability_tier,
                string_agg(s.blood_group || ': ' || CAST(s.units AS VARCHAR), ', ') AS stock_summary,
                COUNT(*) OVER () AS total_matches
            FROM main_gold.dim_blood_banks b
            JOIN (
                -- one row per bank and group; "ALL" components are summed, not listed twice
                SELECT hospital_code, blood_group, SUM(units) AS units,
                       MAX(source_updated_at) AS source_updated_at
                FROM main_gold.fct_stock_current {comp_clause}
                GROUP BY hospital_code, blood_group
            ) s ON b.hospital_code = s.hospital_code
            LEFT JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
            WHERE {where_sql}
            GROUP BY
                b.hospital_code, b.hospital_name, b.hospital_type, b.facility_type,
                b.state_name, b.district_name, b.hospital_contact, b.hospital_address,
                r.reliability_score, r.reliability_label, r.reliability_tier
            ORDER BY days_since_update ASC NULLS LAST, reliability_score DESC
            LIMIT ?;
        """
        by_distance = sort == "distance" and lat is not None and lng is not None
        # distance is computed in Python, so fetch every match and cut after sorting
        rows = con.execute(sql, comp_params + params + [None if by_distance else limit]).fetchall()

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
                _total,
            ) = r
            f_lat, f_lng, is_approx = resolve_facility_lat_lng(h_code, s_name, d_name)
            dist_km = (
                haversine_distance_km(lat, lng, f_lat, f_lng)
                if lat is not None and lng is not None
                else None
            )
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
                    "days_stale": days_ago,
                    "reliability_score": score,
                    "reliability_tier": tier,
                    "lat": f_lat,
                    "lng": f_lng,
                    "is_approximate": is_approx,
                    "distance_km": dist_km,
                }
            )
        if by_distance:
            hospitals.sort(key=lambda h: h["distance_km"])
            hospitals = hospitals[:limit]
        elif sort == "reliability":
            hospitals.sort(key=lambda h: -h["reliability_score"])
        total = rows[0][-1] if rows else 0
        return {"hospitals": hospitals, "total": total}
    finally:
        con.close()
