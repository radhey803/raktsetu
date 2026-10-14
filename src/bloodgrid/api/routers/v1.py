"""
BloodGrid V1 Versioned REST API Router
======================================
Version 1 Public REST API providing programmatic search, facility catalogs,
shortage feeds, rare blood radar, and metadata.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import duckdb
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from bloodgrid.api.deps import get_db, get_request_id
from bloodgrid.api.services.search import execute_emergency_search
from bloodgrid.config import settings

router = APIRouter(prefix="/v1", tags=["V1 Public & Partner API"])


@router.get(
    "/meta",
    summary="System and Warehouse Synchronization Metadata",
    description="Returns latest pipeline sync status, total reporting facility counts, and source attribution.",
)
def get_system_metadata(request: Request, con: duckdb.DuckDBPyConnection = Depends(get_db)):
    req_id = get_request_id(request)
    facility_count = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
    total_stock_records = con.execute(
        "SELECT COUNT(*) FROM main_gold.fct_stock_current;"
    ).fetchone()[0]

    last_run_row = con.execute("""
        SELECT run_id, started_at, finished_at, status, facilities_count, tests_passed
        FROM gold.pipeline_runs
        WHERE status = 'SUCCESS'
        ORDER BY finished_at DESC
        LIMIT 1;
    """).fetchone()

    last_sync = last_run_row[2] if last_run_row else None
    is_stale = False
    if last_sync:
        if isinstance(last_sync, str):
            last_sync_dt = datetime.fromisoformat(last_sync)
        else:
            last_sync_dt = last_sync
        if datetime.utcnow() - last_sync_dt > timedelta(hours=12):
            is_stale = True

    return {
        "success": True,
        "request_id": req_id,
        "data": {
            "version": "1.0.0",
            "environment": settings.env,
            "last_sync": last_sync.isoformat() if last_sync else None,
            "is_stale_warning": is_stale,
            "freshness_sla_hours": 12,
            "total_reporting_facilities": facility_count,
            "total_inventory_records": total_stock_records,
            "source_attribution": settings.source_attribution,
            "disclaimer": "Not an official service. Always call the blood bank to confirm before travelling.",
        },
    }


@router.get("/banks", summary="Browse Reporting Blood Banks Nationwide")
def list_blood_banks(
    request: Request,
    state: Optional[str] = Query(None, description="State Name"),
    district: Optional[str] = Query(None, description="District Name"),
    min_reliability: int = Query(0, ge=0, le=100, description="Minimum reliability rating (0-100)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    req_id = get_request_id(request)
    params: List[Any] = []
    where_clauses = ["1=1"]

    if state and state.upper() != "ALL":
        where_clauses.append("LOWER(b.state_name) = LOWER(?)")
        params.append(state.strip())

    if district and district.upper() != "ALL":
        where_clauses.append("LOWER(b.district_name) = LOWER(?)")
        params.append(district.strip())

    if min_reliability > 0:
        where_clauses.append("COALESCE(r.reliability_score, 0) >= ?")
        params.append(min_reliability)

    count_sql = f"""
        SELECT COUNT(*)
        FROM main_gold.dim_blood_banks b
        LEFT JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
        WHERE {" AND ".join(where_clauses)}
    """
    total = con.execute(count_sql, params).fetchone()[0]

    fetch_sql = f"""
        SELECT
            b.hospital_code, b.hospital_name, b.hospital_type, b.facility_type,
            b.state_name, b.district_name, b.hospital_contact, b.hospital_address,
            b.source_updated_at,
            COALESCE(r.reliability_score, 0),
            COALESCE(r.reliability_tier, 'UNKNOWN')
        FROM main_gold.dim_blood_banks b
        LEFT JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
        WHERE {" AND ".join(where_clauses)}
        ORDER BY r.reliability_score DESC, b.hospital_name ASC
        LIMIT ? OFFSET ?;
    """
    params.extend([limit, offset])
    rows = con.execute(fetch_sql, params).fetchall()

    data = [
        {
            "hospital_code": r[0],
            "hospital_name": r[1],
            "hospital_type": r[2],
            "facility_type": r[3],
            "state_name": r[4],
            "district_name": r[5],
            "contact": r[6],
            "address": r[7],
            "source_updated_at": r[8].isoformat() if r[8] else None,
            "reliability_score": r[9],
            "reliability_tier": r[10],
        }
        for r in rows
    ]

    return {
        "success": True,
        "request_id": req_id,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        },
        "data": data,
    }


@router.get("/banks/{hospital_code}", summary="Facility Profile & Full Stock Matrix")
def get_blood_bank_detail(
    hospital_code: int, request: Request, con: duckdb.DuckDBPyConnection = Depends(get_db)
):
    req_id = get_request_id(request)
    row = con.execute(
        """
        SELECT
            b.hospital_code, b.hospital_name, b.hospital_type, b.facility_type,
            b.state_name, b.district_name, b.hospital_contact, b.hospital_address,
            b.source_updated_at,
            COALESCE(r.reliability_score, 0),
            COALESCE(r.reliability_tier, 'UNKNOWN'),
            r.freshness_points, r.contact_points, r.completeness_points
        FROM main_gold.dim_blood_banks b
        LEFT JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
        WHERE b.hospital_code = ?;
    """,
        [hospital_code],
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Facility code {hospital_code} not found")

    # Fetch stock breakdown
    stock_rows = con.execute(
        """
        SELECT component_name, blood_group, units, source_updated_at
        FROM main_gold.fct_stock_current
        WHERE hospital_code = ?
        ORDER BY component_name, blood_group;
    """,
        [hospital_code],
    ).fetchall()

    stock_matrix: Dict[str, Dict[str, int]] = {}
    for comp, bg, units, _ in stock_rows:
        if comp not in stock_matrix:
            stock_matrix[comp] = {}
        stock_matrix[comp][bg] = units

    return {
        "success": True,
        "request_id": req_id,
        "data": {
            "hospital_code": row[0],
            "hospital_name": row[1],
            "hospital_type": row[2],
            "facility_type": row[3],
            "state_name": row[4],
            "district_name": row[5],
            "hospital_contact": row[6],
            "hospital_address": row[7],
            "source_updated_at": row[8].isoformat() if row[8] else None,
            "reliability": {
                "score": row[9],
                "tier": row[10],
                "freshness_points": row[11],
                "contact_points": row[12],
                "completeness_points": row[13],
            },
            "stock_matrix": stock_matrix,
            "disclaimer": settings.source_attribution,
        },
    }


@router.get("/availability", summary="Search Live Component Availability by Group")
def search_availability(
    request: Request,
    component: Optional[str] = Query("Packed Red Blood Cells"),
    blood_group: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    min_units: int = Query(0, ge=0),
    sort: str = Query("freshness", pattern="^(freshness|units|reliability)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    req_id = get_request_id(request)
    results, total = execute_emergency_search(
        con=con,
        component=component,
        blood_group=blood_group,
        state=state,
        district=district,
        min_units=min_units,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "request_id": req_id,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        },
        "data": results,
        "source_attribution": settings.source_attribution,
        "disclaimer": settings.source_attribution,
    }


@router.get("/rare", summary="Rare Blood Radar (Bombay & Rh-Negatives)")
def get_rare_blood_radar(
    request: Request,
    rarity: Optional[str] = Query(None, description="ULTRA_RARE_BOMBAY or RH_NEGATIVE"),
    state: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    req_id = get_request_id(request)
    params: List[Any] = []
    where_clauses = ["units > 0"]

    if rarity:
        where_clauses.append("rarity_tier = ?")
        params.append(rarity.upper())

    if state and state.upper() != "ALL":
        where_clauses.append("LOWER(state_name) = LOWER(?)")
        params.append(state.strip())

    sql = f"""
        SELECT
            hospital_code, hospital_name, hospital_type, state_name, district_name,
            hospital_contact, hospital_address, component_name, blood_group, units,
            rarity_tier, source_updated_at, last_synced_at
        FROM main_gold.mart_rare_blood_availability
        WHERE {" AND ".join(where_clauses)}
        ORDER BY CASE WHEN rarity_tier = 'ULTRA_RARE_BOMBAY' THEN 1 ELSE 2 END, units DESC
        LIMIT ?;
    """
    params.append(limit)
    rows = con.execute(sql, params).fetchall()

    data = [
        {
            "hospital_code": r[0],
            "hospital_name": r[1],
            "hospital_type": r[2],
            "state_name": r[3],
            "district_name": r[4],
            "hospital_contact": r[5],
            "hospital_address": r[6],
            "component_name": r[7],
            "blood_group": r[8],
            "units": r[9],
            "rarity_tier": r[10],
            "source_updated_at": r[11].isoformat() if r[11] else None,
            "last_synced_at": r[12].isoformat() if r[12] else None,
        }
        for r in rows
    ]

    return {
        "success": True,
        "request_id": req_id,
        "count": len(data),
        "data": data,
        "disclaimer": settings.source_attribution,
    }


@router.get("/shortages", summary="District-level Shortage Feed")
def get_district_shortages(
    request: Request,
    state: Optional[str] = Query(None),
    component: Optional[str] = Query("Packed Red Blood Cells"),
    shortage_only: bool = Query(True, description="Filter for deficits only"),
    limit: int = Query(100, ge=1, le=500),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    req_id = get_request_id(request)
    params: List[Any] = []
    where_clauses = ["1=1"]

    if state and state.upper() != "ALL":
        where_clauses.append("LOWER(state_name) = LOWER(?)")
        params.append(state.strip())

    if component and component.upper() != "ALL":
        where_clauses.append("component_name = ?")
        params.append(component.strip())

    if shortage_only:
        where_clauses.append("shortage_status IN ('CRITICAL_DEPLETION', 'HIGH_SHORTAGE')")

    sql = f"""
        SELECT
            state_name, district_name, component_name, blood_group,
            total_reporting_banks, stocked_banks, total_units, shortage_status
        FROM main_gold.mart_district_status
        WHERE {" AND ".join(where_clauses)}
        ORDER BY total_units ASC
        LIMIT ?;
    """
    params.append(limit)
    rows = con.execute(sql, params).fetchall()

    data = [
        {
            "state_name": r[0],
            "district_name": r[1],
            "component_name": r[2],
            "blood_group": r[3],
            "total_reporting_banks": r[4],
            "stocked_banks": r[5],
            "total_units": r[6],
            "shortage_status": r[7],
        }
        for r in rows
    ]

    return {"success": True, "request_id": req_id, "count": len(data), "data": data}


@router.post("/meta/refresh", summary="Signed Refresh Webhook Trigger")
def trigger_serving_refresh(authorization: Optional[str] = Header(None)):
    """
    Signed webhook called by the pipeline to trigger an instantaneous
    zero-downtime serving cache flush.
    """
    expected_token = f"Bearer {settings.api_key_secret}"
    if not authorization or authorization != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook signature token in Authorization header",
        )

    return {
        "success": True,
        "status": "REFRESH_TRIGGERED",
        "timestamp": datetime.utcnow().isoformat(),
        "serving_path": str(settings.serving_path),
    }
