"""
eRaktKosh Blood Lakehouse FastAPI Application
=============================================
Academic Mini Project - Master of Computer Applications (MCA)
Charotar University of Science and Technology (CHARUSAT)

Serves high-concurrency analytical queries from DuckDB and hosts the Vanilla JS/CSS
web interface from the web/ directory.
"""

from pathlib import Path
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
    limit: int = 60,
):
    from bloodlake.api.routes import get_blood_availability
    from bloodlake.db import get_serving_connection
    con = get_serving_connection(read_only=True)
    try:
        res = get_blood_availability(
            state=state,
            district=district,
            blood_group=blood_group,
            component=component,
            min_units=0,
            page=1,
            page_size=limit,
            con=con,
        )
        return [
            {
                "code": item.hospital_code,
                "name": item.hospital_name,
                "type": item.hospital_type,
                "facility": item.facility_type,
                "state": item.state_name,
                "district": item.district_name,
                "contact": item.hospital_contact,
                "address": item.hospital_address,
                "component": item.component_name,
                "blood_group": item.blood_group,
                "units": item.units,
                "last_updated": str(item.last_updated_at)[:19] if item.last_updated_at else "",
                "days_since_update": item.days_since_last_update,
                "reliability_score": item.reliability_score,
                "reliability_tier": item.reliability_tier,
                "lat": item.latitude,
                "lng": item.longitude,
                "is_approximate": item.is_approximate_location,
            }
            for item in res.items
        ]
    finally:
        con.close()
