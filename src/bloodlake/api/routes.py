"""
eRaktKosh Blood Lakehouse REST API Routers
==========================================
Academic Mini Project - MCA, CHARUSAT
Provides analytical query endpoints powered directly by DuckDB Gold marts:
- Meta & Attribution (/api/v1/meta)
- National Summary KPIs (/api/v1/summary)
- Location Hierarchy (/api/v1/locations)
- Blood Bank Directory (/api/v1/banks)
- Real-time Inventory Query (/api/v1/availability) - Pure SQL on fct_stock_current
- Time-series Historical Trends (/api/v1/history) - From fct_stock_snapshot
- District Shortage Radar (/api/v1/shortages) - From mart_district_status
- Rare Blood Phenotype Finder (/api/v1/rare) - Bombay Oh+, Oh-, AB-
- System Health (/healthz)
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from bloodlake.api.schemas import (
    BloodAvailabilityItem,
    BloodBankItem,
    DistrictShortage,
    MetaResponse,
    NationalSummary,
    PaginatedResponse,
    RareBloodItem,
    StateSummaryItem,
    TrendPoint,
    TrendResponse,
)
from bloodlake.config import settings
from bloodlake.db import get_db_session
from bloodlake.geo import resolve_facility_lat_lng

router = APIRouter(tags=["eRaktKosh Lakehouse Analytics"])


@router.get("/healthz")
def health_check(con: duckdb.DuckDBPyConnection = Depends(get_db_session)):
    """Liveness probe verifying DuckDB connectivity."""
    try:
        row = con.execute("SELECT 1;").fetchone()
        return {
            "status": "healthy",
            "database": "DuckDB Lakehouse",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


@router.get("/api/v1/meta", response_model=MetaResponse)
def get_metadata(con: duckdb.DuckDBPyConnection = Depends(get_db_session)):
    """Returns project details, academic attribution, and last sync timestamp."""
    last_synced = None
    try:
        row = con.execute("""
            SELECT finished_at
            FROM gold.pipeline_runs
            WHERE status = 'SUCCESS'
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()
        if row and row[0]:
            last_synced = str(row[0])[:19]
    except Exception:
        pass

    try:
        total_banks = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
    except Exception:
        total_banks = 0

    return MetaResponse(
        project_name=settings.project_name,
        project_subtitle=settings.project_subtitle,
        version=settings.version,
        institution=settings.institution,
        department=settings.department,
        academic_guide=settings.academic_guide,
        author=settings.author_name,
        last_synced_at=last_synced,
        total_facilities=total_banks,
        data_source="eRaktKosh (MoHFW, Govt. of India)",
        attribution="Data sourced from eRaktKosh (MoHFW, Govt. of India). Academic project, not an official service.",
        disclaimer="Data reflects periodic snapshots from eRaktKosh portal. Always contact the blood bank directly to confirm live unit availability.",
    )


@router.get("/api/v1/summary", response_model=NationalSummary)
def get_national_summary(
    response: Response,
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """Returns high-level KPI cards and top state distributions for dashboard."""
    response.headers["Cache-Control"] = "public, max-age=60"

    total_banks = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
    total_states = con.execute("SELECT COUNT(DISTINCT state_name) FROM main_gold.dim_blood_banks;").fetchone()[0]

    fresh_row = con.execute("""
        SELECT COUNT(*)
        FROM main_gold.fct_blood_shortage_alerts
        WHERE days_since_last_update <= 1;
    """).fetchone()
    fresh_banks_24h = fresh_row[0] if fresh_row else 0

    stale_row = con.execute("""
        SELECT COUNT(*)
        FROM main_gold.fct_blood_shortage_alerts
        WHERE days_since_last_update > 30;
    """).fetchone()
    stale_banks_30d = stale_row[0] if stale_row else 0

    top_states_raw = con.execute("""
        SELECT state_name, COUNT(*) as count
        FROM main_gold.dim_blood_banks
        GROUP BY state_name
        ORDER BY count DESC
        LIMIT 8;
    """).fetchall()

    top_states = [StateSummaryItem(state=r[0], banks=r[1]) for r in top_states_raw]

    return NationalSummary(
        total_banks=total_banks,
        total_states=total_states,
        fresh_banks_24h=fresh_banks_24h,
        stale_banks_30d=stale_banks_30d,
        top_states=top_states,
    )


@router.get("/api/v1/locations")
def get_locations(con: duckdb.DuckDBPyConnection = Depends(get_db_session)) -> Dict[str, List[str]]:
    """Returns distinct states and districts for dropdown navigation."""
    rows = con.execute("""
        SELECT DISTINCT state_name, district_name
        FROM main_gold.dim_blood_banks
        WHERE state_name IS NOT NULL AND district_name IS NOT NULL
        ORDER BY state_name, district_name;
    """).fetchall()

    locs: Dict[str, List[str]] = {}
    for st, dist in rows:
        if st not in locs:
            locs[st] = []
        if dist and dist not in locs[st]:
            locs[st].append(dist)
    return locs


@router.get("/api/v1/banks", response_model=PaginatedResponse)
def list_blood_banks(
    state: Optional[str] = Query(None, description="Filter by state name"),
    district: Optional[str] = Query(None, description="Filter by district name"),
    search: Optional[str] = Query(None, description="Search by hospital name or address"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(15, ge=1, le=100, description="Items per page"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """Paginated directory of blood banks with freshness and reliability score."""
    where_clauses = ["1=1"]
    params = []

    if state and state != "ALL":
        where_clauses.append("b.state_name = ?")
        params.append(state)
    if district and district != "ALL":
        where_clauses.append("b.district_name = ?")
        params.append(district)
    if search and search.strip():
        where_clauses.append("(LOWER(b.hospital_name) LIKE ? OR LOWER(b.hospital_address) LIKE ?)")
        q = f"%{search.strip().lower()}%"
        params.extend([q, q])

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(*)
        FROM main_gold.dim_blood_banks b
        WHERE {where_sql}
    """
    total = con.execute(count_sql, params).fetchone()[0]

    offset = (page - 1) * page_size
    query_sql = f"""
        SELECT
            b.hospital_code,
            b.hospital_name,
            b.hospital_type,
            b.facility_type,
            b.state_name,
            b.district_name,
            b.hospital_contact,
            b.hospital_address,
            b.source_updated_at,
            a.days_since_last_update,
            a.data_freshness_status,
            a.stock_alert_level,
            r.reliability_score,
            r.reliability_tier
        FROM main_gold.dim_blood_banks b
        LEFT JOIN (
            SELECT hospital_code, days_since_last_update, data_freshness_status, stock_alert_level
            FROM main_gold.fct_blood_shortage_alerts
            QUALIFY ROW_NUMBER() OVER (PARTITION BY hospital_code ORDER BY last_updated_at DESC NULLS LAST) = 1
        ) a ON b.hospital_code = a.hospital_code
        LEFT JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
        WHERE {where_sql}
        ORDER BY a.days_since_last_update ASC NULLS LAST, b.hospital_name ASC
        LIMIT ? OFFSET ?;
    """
    exec_params = list(params) + [page_size, offset]
    rows = con.execute(query_sql, exec_params).fetchall()

    items = []
    for r in rows:
        h_code, h_name, h_type, f_type, s_name, d_name, contact, address, updated_at, days_ago, freshness, alert, score, tier = r
        lat, lng, is_approx = resolve_facility_lat_lng(h_code, s_name, d_name)
        items.append(
            BloodBankItem(
                hospital_code=h_code,
                hospital_name=h_name,
                hospital_type=h_type,
                facility_type=f_type,
                state_name=s_name,
                district_name=d_name,
                hospital_contact=contact,
                hospital_address=address,
                last_updated_at=updated_at,
                days_since_last_update=days_ago,
                data_freshness_status=freshness or "UNKNOWN",
                stock_alert_level=alert or "NORMAL",
                reliability_score=score if score is not None else 50,
                reliability_tier=tier or "SILVER",
                latitude=lat,
                longitude=lng,
                is_approximate_location=is_approx,
            )
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/api/v1/availability", response_model=PaginatedResponse)
def get_blood_availability(
    state: Optional[str] = Query(None, description="State Name"),
    district: Optional[str] = Query(None, description="District Name"),
    blood_group: Optional[str] = Query(None, description="Blood Group, e.g., O+, O-, AB-"),
    component: Optional[str] = Query("Packed Red Blood Cells", description="Component Name"),
    min_units: int = Query(0, ge=0, description="Minimum units available"),
    max_age_hours: Optional[int] = Query(None, ge=1, description="Max hours since update"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(15, ge=1, le=100, description="Items per page"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """
    Emergency Blood Availability Search.
    Direct SQL query against fct_stock_current with normalized blood group & component.
    Replaces fragile regex matching with index-accelerated relational filter.
    """
    where_clauses = ["1=1"]
    params = []

    if state and state != "ALL":
        where_clauses.append("s.state_name = ?")
        params.append(state)
    if district and district != "ALL":
        where_clauses.append("s.district_name = ?")
        params.append(district)
    if component and component != "ALL":
        where_clauses.append("s.component_name = ?")
        params.append(component)
    if blood_group and blood_group != "ALL":
        where_clauses.append("s.blood_group = ?")
        params.append(blood_group)
    if min_units > 0:
        where_clauses.append("s.units >= ?")
        params.append(min_units)

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(*)
        FROM main_gold.fct_stock_current s
        WHERE {where_sql}
    """
    total = con.execute(count_sql, params).fetchone()[0]

    offset = (page - 1) * page_size
    query_sql = f"""
        SELECT
            s.hospital_code,
            s.hospital_name,
            b.hospital_type,
            b.facility_type,
            s.state_name,
            s.district_name,
            b.hospital_contact,
            b.hospital_address,
            s.component_name,
            s.blood_group,
            s.units,
            s.source_updated_at,
            DATE_DIFF('day', s.source_updated_at, CURRENT_TIMESTAMP) as days_since_update,
            COALESCE(r.reliability_score, 50) as reliability_score,
            COALESCE(r.reliability_tier, 'SILVER') as reliability_tier
        FROM main_gold.fct_stock_current s
        LEFT JOIN main_gold.dim_blood_banks b ON s.hospital_code = b.hospital_code
        LEFT JOIN main_gold.mart_reliability_score r ON s.hospital_code = r.hospital_code
        WHERE {where_sql}
        ORDER BY days_since_update ASC NULLS LAST, s.units DESC
        LIMIT ? OFFSET ?;
    """
    exec_params = list(params) + [page_size, offset]
    rows = con.execute(query_sql, exec_params).fetchall()

    items = []
    for r in rows:
        h_code, h_name, h_type, f_type, s_name, d_name, contact, address, comp, bg, units, updated_at, days_ago, score, tier = r
        lat, lng, is_approx = resolve_facility_lat_lng(h_code, s_name, d_name)
        items.append(
            BloodAvailabilityItem(
                hospital_code=h_code,
                hospital_name=h_name,
                hospital_type=h_type,
                facility_type=f_type,
                state_name=s_name,
                district_name=d_name,
                hospital_contact=contact,
                hospital_address=address,
                component_name=comp,
                blood_group=bg,
                units=units,
                last_updated_at=updated_at,
                days_since_last_update=days_ago,
                reliability_score=score,
                reliability_tier=tier,
                latitude=lat,
                longitude=lng,
                is_approximate_location=is_approx,
            )
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/api/v1/history", response_model=TrendResponse)
def get_facility_trend(
    hospital_code: int = Query(..., description="Hospital Code"),
    component: str = Query("Packed Red Blood Cells", description="Blood Component"),
    blood_group: str = Query("O-", description="Blood Group"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """
    Returns verified time-series history from real incremental snapshots in fct_stock_snapshot.
    ZERO FAKE DATA: If fewer than 2 distinct real snapshots exist, returns an honest
    academic message explaining that trend builds with subsequent pipeline runs.
    """
    h_row = con.execute(
        "SELECT hospital_name FROM main_gold.dim_blood_banks WHERE hospital_code = ? LIMIT 1;",
        [hospital_code],
    ).fetchone()
    hospital_name = h_row[0] if h_row else f"Hospital #{hospital_code}"

    # Query real snapshot points
    rows = con.execute("""
        SELECT snapshot_date, units
        FROM main_gold.fct_stock_snapshot
        WHERE hospital_code = ?
          AND component_name = ?
          AND blood_group = ?
        ORDER BY snapshot_date ASC;
    """, [hospital_code, component, blood_group]).fetchall()

    points = [TrendPoint(snapshot_date=str(r[0]), units=r[1]) for r in rows]
    has_sufficient = len(points) >= 2

    if not has_sufficient:
        message = (
            "Historical delta builds with each real scrape. Only 1 snapshot date currently exists. "
            "Execute 'bloodlake all' on subsequent days to visualize multi-day inventory depletion/replenishment trends."
        )
    else:
        message = f"Real historical trend across {len(points)} snapshot intervals."

    return TrendResponse(
        hospital_code=hospital_code,
        hospital_name=hospital_name,
        component_name=component,
        blood_group=blood_group,
        points=points,
        has_sufficient_history=has_sufficient,
        message=message,
    )


@router.get("/api/v1/shortages", response_model=List[DistrictShortage])
def get_district_shortages(
    state: Optional[str] = Query(None, description="State filter"),
    blood_group: Optional[str] = Query("O-", description="Blood group to inspect"),
    component: Optional[str] = Query("Packed Red Blood Cells", description="Component to inspect"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """District-level shortage radar highlighting critical deficit areas."""
    where_clauses = ["d.blood_group = ?", "d.component_name = ?"]
    params = [blood_group or "O-", component or "Packed Red Blood Cells"]

    if state and state != "ALL":
        where_clauses.append("d.state_name = ?")
        params.append(state)

    where_sql = " AND ".join(where_clauses)
    query_sql = f"""
        SELECT
            d.state_name,
            d.district_name,
            d.blood_group,
            d.component_name,
            d.total_units,
            d.total_reporting_banks,
            d.shortage_status
        FROM main_gold.mart_district_status d
        WHERE {where_sql}
        ORDER BY d.total_units ASC, d.total_reporting_banks DESC
        LIMIT 30;
    """
    rows = con.execute(query_sql, params).fetchall()

    return [
        DistrictShortage(
            state_name=r[0],
            district_name=r[1],
            blood_group=r[2],
            component_name=r[3],
            total_units=r[4],
            reporting_banks=r[5],
            shortage_status=r[6],
        )
        for r in rows
    ]


@router.get("/api/v1/rare", response_model=List[RareBloodItem])
def get_rare_blood_inventory(
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """Identifies facilities currently stocking rare phenotypes (Bombay Oh+, Oh-, and AB-)."""
    rows = con.execute("""
        SELECT
            r.hospital_code,
            r.hospital_name,
            r.state_name,
            r.district_name,
            r.blood_group,
            r.component_name,
            r.units,
            b.hospital_contact,
            b.source_updated_at
        FROM main_gold.mart_rare_blood_availability r
        LEFT JOIN main_gold.dim_blood_banks b ON r.hospital_code = b.hospital_code
        ORDER BY r.units DESC, r.hospital_name ASC
        LIMIT 50;
    """).fetchall()

    return [
        RareBloodItem(
            hospital_code=r[0],
            hospital_name=r[1],
            state_name=r[2],
            district_name=r[3],
            blood_group=r[4],
            component_name=r[5],
            units=r[6],
            hospital_contact=r[7],
            last_updated_at=r[8],
        )
        for r in rows
    ]
