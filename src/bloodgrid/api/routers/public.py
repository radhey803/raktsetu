"""
BloodGrid Public API Router
===========================
Maintains 100% backward compatibility for existing frontend dashboard calls:
- GET /api/health
- GET /api/summary
- GET /api/locations
- GET /api/search
- GET /api/history
- GET /api/district-trends
Queries the verified serving database (serving.duckdb) with zero file locks.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import duckdb
from fastapi import APIRouter, Depends, Query

from bloodgrid.api.deps import get_db
from bloodgrid.api.services.search import execute_emergency_search
from bloodgrid.config import settings

router = APIRouter(prefix="/api", tags=["Public Dashboard Endpoints"])


@router.get("/health")
def health_check(con: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Health check validating read-only database connectivity."""
    facility_count = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
    return {
        "status": "healthy",
        "engine": "DuckDB Lakehouse + dbt Core",
        "version": "1.0.0",
        "facilities_active": facility_count,
    }


@router.get("/summary")
def get_national_summary(con: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Returns high-level KPI cards for the national dashboard header."""
    row_banks = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()
    total_banks = row_banks[0] if row_banks else 0

    row_states = con.execute(
        "SELECT COUNT(DISTINCT state_name) FROM main_gold.dim_blood_banks;"
    ).fetchone()
    total_states = row_states[0] if row_states else 0

    row_fresh = con.execute("""
        SELECT COUNT(*)
        FROM main_gold.dim_blood_banks
        WHERE source_updated_at >= (CURRENT_TIMESTAMP - INTERVAL 24 HOUR);
    """).fetchone()
    fresh_banks = row_fresh[0] if row_fresh else 0

    row_stale = con.execute("""
        SELECT COUNT(*)
        FROM main_gold.dim_blood_banks
        WHERE source_updated_at < (CURRENT_TIMESTAMP - INTERVAL 30 DAY)
           OR source_updated_at IS NULL;
    """).fetchone()
    stale_banks = row_stale[0] if row_stale else 0

    top_states = con.execute("""
        SELECT state_name, COUNT(*) as banks
        FROM main_gold.dim_blood_banks
        GROUP BY state_name
        ORDER BY banks DESC
        LIMIT 6;
    """).fetchall()

    return {
        "total_banks": total_banks,
        "total_states": total_states,
        "fresh_banks": fresh_banks,
        "stale_banks": stale_banks,
        "top_states": [{"state": s[0], "banks": s[1]} for s in top_states],
        "source_attribution": settings.source_attribution,
    }


@router.get("/locations")
def get_location_hierarchy(con: duckdb.DuckDBPyConnection = Depends(get_db)):
    """Returns distinct states and districts for dropdown selectors."""
    results = con.execute("""
        SELECT DISTINCT state_name, district_name
        FROM main_gold.dim_blood_banks
        WHERE state_name IS NOT NULL AND district_name IS NOT NULL
        ORDER BY state_name, district_name;
    """).fetchall()

    locations: Dict[str, List[str]] = {}
    for state, district in results:
        if state not in locations:
            locations[state] = []
        if district and district not in locations[state]:
            locations[state].append(district)

    return locations


@router.get("/search")
def search_hospitals(
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    component: Optional[str] = Query("Packed Red Blood Cells"),
    blood_group: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None),
    limit: int = Query(500, le=1000),
    offset: int = Query(0, ge=0),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """Emergency SOS Search checking live inventory by exact component and blood group."""
    hospitals, total = execute_emergency_search(
        con=con,
        component=component,
        blood_group=blood_group,
        state=state,
        district=district,
        search_query=search_query,
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(hospitals),
        "total": total,
        "hospitals": hospitals,
        "source_attribution": settings.source_attribution,
    }


@router.get("/history")
def get_hospital_history(
    hospital_code: int = Query(..., description="Hospital Code"),
    component: Optional[str] = Query("Packed Red Blood Cells"),
    days: int = Query(14, ge=1, le=90),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Returns time-series stock history for a specific hospital across all blood groups.
    Honest empty state returned if fewer than 2 distinct real snapshots exist.
    """
    distinct_dates_cnt = con.execute(
        "SELECT COUNT(DISTINCT snapshot_date) FROM main_gold.fct_stock_snapshot;"
    ).fetchone()[0]

    min_date = date.today() - timedelta(days=days)
    target_comp = component or "Packed Red Blood Cells"

    rows = con.execute(
        """
        SELECT
            snapshot_date,
            blood_group,
            units,
            hospital_name,
            district_name,
            state_name
        FROM main_gold.fct_stock_snapshot
        WHERE hospital_code = ?
          AND component_name = ?
          AND snapshot_date >= ?
        ORDER BY snapshot_date ASC, blood_group ASC;
    """,
        [hospital_code, target_comp, min_date],
    ).fetchall()

    if not rows:
        return {
            "hospital_code": hospital_code,
            "component": target_comp,
            "dates": [],
            "series": {},
            "summary": {},
            "distinct_days_available": distinct_dates_cnt,
            "honest_empty_state_note": "Trend data builds up daily. Real snapshots accumulate with each scheduled run.",
        }

    hosp_name = rows[0][3]
    district = rows[0][4]
    state = rows[0][5]

    dates_set = sorted(
        list(set(r[0].strftime("%b %d") for r in rows)), key=lambda x: datetime.strptime(x, "%b %d")
    )
    date_to_idx = {d: i for i, d in enumerate(dates_set)}

    series: Dict[str, List[int]] = {}
    for r in rows:
        sdate = r[0].strftime("%b %d")
        bg = r[1]
        units = r[2]
        if bg not in series:
            series[bg] = [0] * len(dates_set)
        idx = date_to_idx[sdate]
        series[bg][idx] = units

    summary = {}
    for bg, vals in series.items():
        current_val = vals[-1] if vals else 0
        initial_val = vals[0] if vals else 0
        diff = current_val - initial_val
        summary[bg] = {
            "current": current_val,
            "peak": max(vals) if vals else 0,
            "change": f"{'+' if diff > 0 else ''}{diff}",
            "is_critical": current_val <= 2,
        }

    return {
        "hospital_code": hospital_code,
        "hospital_name": hosp_name,
        "district": district,
        "state": state,
        "component": target_comp,
        "dates": dates_set,
        "series": series,
        "summary": summary,
        "distinct_days_available": distinct_dates_cnt,
        "honest_empty_state_note": (
            None
            if distinct_dates_cnt >= 2
            else "First snapshot recorded. Trend data builds up daily with each scheduled run."
        ),
    }


@router.get("/district-trends")
def get_district_trends(
    state: str = Query(...),
    district: str = Query(...),
    component: Optional[str] = Query("Packed Red Blood Cells"),
    blood_group: Optional[str] = Query("O-"),
    days: int = Query(14, ge=1, le=90),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """Aggregate district stock trend over time."""
    min_date = date.today() - timedelta(days=days)
    target_comp = component or "Packed Red Blood Cells"

    sql = """
        SELECT
            snapshot_date,
            SUM(units) as total_units,
            COUNT(DISTINCT hospital_code) as reporting_banks,
            COUNT(DISTINCT CASE WHEN units > 0 THEN hospital_code END) as stocked_banks
        FROM main_gold.fct_stock_snapshot
        WHERE LOWER(state_name) = LOWER(?)
          AND LOWER(district_name) = LOWER(?)
          AND component_name = ?
    """
    params = [state.strip(), district.strip(), target_comp]

    if blood_group and blood_group.upper() != "ALL":
        sql += " AND blood_group = ?"
        params.append(blood_group.strip())

    sql += " AND snapshot_date >= ? GROUP BY snapshot_date ORDER BY snapshot_date ASC;"
    params.append(min_date)

    rows = con.execute(sql, params).fetchall()
    dates = [r[0].strftime("%b %d") for r in rows]
    total_units = [r[1] for r in rows]
    stocked_banks = [r[3] for r in rows]

    return {
        "state": state,
        "district": district,
        "component": target_comp,
        "blood_group": blood_group,
        "dates": dates,
        "total_units": total_units,
        "stocked_banks": stocked_banks,
    }
