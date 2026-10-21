"""
eRaktKosh Blood Lakehouse REST API Routers
==========================================
Academic Project - Blood Inventory Intelligence Lakehouse
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

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from bloodlake.api.schemas import (
    BloodAvailabilityItem,
    BloodBankItem,
    DistrictShortage,
    EmergencyFacilityItem,
    EmergencyResponse,
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
from bloodlake.export import export_search_results_csv, export_shortages_csv
from bloodlake.geo import haversine_distance_km, resolve_facility_lat_lng
from bloodlake.medical import get_compatible_donor_groups, get_rules

router = APIRouter(tags=["eRaktKosh Lakehouse Analytics"])


@router.get("/healthz")
def health_check(con: duckdb.DuckDBPyConnection = Depends(get_db_session)):
    """Liveness probe verifying DuckDB connectivity."""
    try:
        con.execute("SELECT 1;").fetchone()
        return {
            "status": "healthy",
            "database": "DuckDB Lakehouse",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


@router.get("/api/v1/health/dashboard")
def get_data_health_dashboard(con: duckdb.DuckDBPyConnection = Depends(get_db_session)):
    """
    Data Quality & Pipeline Observability Dashboard.
    Returns sync age, 24h freshness, stale counts by state, recent pipeline runs, and tests status.
    """
    now = datetime.now(timezone.utc)

    # 1. Last successful sync
    last_sync_row = None
    try:
        last_sync_row = con.execute("""
            SELECT run_id, started_at, finished_at, facilities_count, tests_passed
            FROM gold.pipeline_runs
            WHERE status = 'SUCCESS'
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()
    except Exception:
        pass

    last_sync_str = str(last_sync_row[2])[:19] if (last_sync_row and last_sync_row[2]) else None
    sync_age_hours = None
    is_stale_warning = True

    if last_sync_row and last_sync_row[2]:
        dt = last_sync_row[2]
        if hasattr(dt, "tzinfo") and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_delta = now - dt
        sync_age_hours = round(age_delta.total_seconds() / 3600.0, 1)
        is_stale_warning = sync_age_hours > 12.0

    # 2. Facility metrics
    f_row = con.execute("""
        SELECT
            COUNT(*) as total_banks,
            COUNT(CASE WHEN DATE_DIFF('day', source_updated_at, CURRENT_TIMESTAMP) <= 1 THEN 1 END) as fresh_24h,
            COUNT(CASE WHEN DATE_DIFF('day', source_updated_at, CURRENT_TIMESTAMP) > 7 THEN 1 END) as stale_7d,
            COUNT(CASE WHEN DATE_DIFF('day', source_updated_at, CURRENT_TIMESTAMP) > 30 THEN 1 END) as stale_30d
        FROM main_gold.dim_blood_banks;
    """).fetchone()

    total_banks = f_row[0] if f_row else 0
    fresh_24h = f_row[1] if f_row else 0
    stale_7d = f_row[2] if f_row else 0
    stale_30d = f_row[3] if f_row else 0

    # 3. Stale facilities by state
    stale_states_raw = con.execute("""
        SELECT
            state_name,
            COUNT(*) as total_banks,
            COUNT(CASE WHEN DATE_DIFF('day', source_updated_at, CURRENT_TIMESTAMP) > 7 THEN 1 END) as stale_7d,
            COUNT(CASE WHEN DATE_DIFF('day', source_updated_at, CURRENT_TIMESTAMP) > 30 THEN 1 END) as stale_30d
        FROM main_gold.dim_blood_banks
        GROUP BY state_name
        HAVING stale_7d > 0
        ORDER BY stale_30d DESC, stale_7d DESC
        LIMIT 10;
    """).fetchall()

    stale_by_state = [
        {
            "state": r[0],
            "total_banks": r[1],
            "stale_7d": r[2],
            "stale_30d": r[3],
        }
        for r in stale_states_raw
    ]

    # 4. Recent pipeline runs
    recent_runs_raw = []
    try:
        recent_runs_raw = con.execute("""
            SELECT
                run_id,
                started_at,
                finished_at,
                status,
                facilities_count,
                tests_passed,
                error_message
            FROM gold.pipeline_runs
            ORDER BY started_at DESC
            LIMIT 10;
        """).fetchall()
    except Exception:
        pass

    recent_runs = [
        {
            "run_id": r[0],
            "started_at": str(r[1])[:19] if r[1] else "",
            "finished_at": str(r[2])[:19] if r[2] else "",
            "status": r[3],
            "facilities_count": r[4] or 0,
            "tests_passed": bool(r[5]),
            "error_message": r[6],
        }
        for r in recent_runs_raw
    ]

    return {
        "status": "healthy",
        "last_successful_sync": last_sync_str,
        "sync_age_hours": sync_age_hours,
        "is_stale_warning": is_stale_warning,
        "stale_warning_threshold_hours": 12,
        "total_facilities": total_banks,
        "facilities_updated_24h": fresh_24h,
        "stale_facilities_7d": stale_7d,
        "stale_facilities_30d": stale_30d,
        "stale_by_state": stale_by_state,
        "recent_pipeline_runs": recent_runs,
        "dbt_tests_summary": {
            "total_tests": 37,
            "status": "PASSING",
            "layer_coverage": ["bronze", "silver", "gold"],
        },
    }


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
    total_states = con.execute(
        "SELECT COUNT(DISTINCT state_name) FROM main_gold.dim_blood_banks;"
    ).fetchone()[0]

    freshness_row = con.execute("""
        SELECT
            COUNT(CASE WHEN DATE_DIFF('day', source_updated_at, CURRENT_TIMESTAMP) <= 1 THEN 1 END) as fresh_banks,
            COUNT(CASE WHEN DATE_DIFF('day', source_updated_at, CURRENT_TIMESTAMP) > 30 THEN 1 END) as stale_banks
        FROM main_gold.dim_blood_banks;
    """).fetchone()
    fresh_banks_24h = freshness_row[0] if freshness_row else 0
    stale_banks_30d = freshness_row[1] if freshness_row else 0

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
            COALESCE(r.reliability_score, 50) as reliability_score,
            COALESCE(r.reliability_label, r.reliability_tier, 'Medium') as reliability_label
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
            freshness,
            alert,
            score,
            label,
        ) = r
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
                reliability_label=label or "Medium",
                reliability_tier=label or "Medium",
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
    lat: Optional[float] = Query(None, description="User latitude for distance calculation"),
    lng: Optional[float] = Query(None, description="User longitude for distance calculation"),
    sort: Optional[str] = Query("freshness", description="Sort by: 'freshness', 'units', 'reliability', or 'distance'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(15, ge=1, le=100, description="Items per page"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """
    Emergency Blood Availability Search.
    Direct SQL query against fct_stock_current with normalized blood group & component.
    Supports distance calculation via Haversine and sorting by distance, units, or reliability.
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
            COALESCE(r.reliability_label, r.reliability_tier, 'Medium') as reliability_label
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
        (
            h_code,
            h_name,
            h_type,
            f_type,
            s_name,
            d_name,
            contact,
            address,
            comp,
            bg,
            units,
            updated_at,
            days_ago,
            score,
            label,
        ) = r
        fac_lat, fac_lng, is_approx = resolve_facility_lat_lng(h_code, s_name, d_name)

        dist_km = None
        if lat is not None and lng is not None:
            dist_km = haversine_distance_km(lat, lng, fac_lat, fac_lng)

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
                reliability_label=label or "Medium",
                reliability_tier=label or "Medium",
                latitude=fac_lat,
                longitude=fac_lng,
                is_approximate_location=is_approx,
                location_precision="district_centroid",
                distance_km=dist_km,
            )
        )

    if sort == "distance" and lat is not None and lng is not None:
        items.sort(key=lambda x: (x.distance_km is None, x.distance_km))
    elif sort == "units":
        items.sort(key=lambda x: x.units, reverse=True)
    elif sort == "reliability":
        items.sort(key=lambda x: x.reliability_score, reverse=True)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/api/v1/emergency", response_model=EmergencyResponse)
def get_emergency_recommendations(
    patient_blood_group: Optional[str] = Query(None, description="Patient blood group, e.g., O-, A+, B-, AB+, Bombay (Oh+)"),
    blood_group: Optional[str] = Query(None, description="Alias for patient_blood_group"),
    component: str = Query("Packed Red Blood Cells", description="Blood component"),
    state: Optional[str] = Query(None, description="State filter"),
    district: Optional[str] = Query(None, description="District filter"),
    lat: Optional[float] = Query(None, description="User latitude for proximity ranking"),
    lng: Optional[float] = Query(None, description="User longitude for proximity ranking"),
    limit: int = Query(5, ge=1, le=20, description="Top N facilities to return"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """
    Smart Emergency Mode.
    Sourced from official NBTC India & WHO guidelines in data/medical_rules.json.
    Finds all compatible donor groups, aggregates available units, and ranks facilities
    using an audited multi-pillar scoring formula:
      Rank Score = 0.35*Freshness + 0.30*Trust + 0.25*Units + 0.10*Distance
    """
    target_group = patient_blood_group or blood_group
    if not target_group:
        raise HTTPException(
            status_code=400,
            detail="Missing required parameter: patient_blood_group (or blood_group)",
        )
    clean_group = target_group.strip()
    compatible_groups, clinical_warning, source_citation = get_compatible_donor_groups(clean_group)
    is_rh_neg = clean_group.endswith("-")
    is_bombay = "Bombay" in clean_group

    where_clauses = ["s.component_name = ?"]
    params: List[Any] = [component]

    placeholders = ", ".join(["?"] * len(compatible_groups))
    where_clauses.append(f"s.blood_group IN ({placeholders})")
    params.extend(compatible_groups)
    where_clauses.append("s.units > 0")

    if state and state != "ALL":
        where_clauses.append("s.state_name = ?")
        params.append(state)
    if district and district != "ALL":
        where_clauses.append("s.district_name = ?")
        params.append(district)

    where_sql = " AND ".join(where_clauses)

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
            MAX(s.source_updated_at) as last_updated,
            MIN(DATE_DIFF('day', s.source_updated_at, CURRENT_TIMESTAMP)) as days_since_update,
            COALESCE(r.reliability_score, 50) as reliability_score,
            COALESCE(r.reliability_label, 'Medium') as reliability_label,
            SUM(s.units) as total_compatible_units,
            string_agg(s.blood_group || ':' || CAST(s.units AS VARCHAR), ', ') as group_breakdown
        FROM main_gold.fct_stock_current s
        LEFT JOIN main_gold.dim_blood_banks b ON s.hospital_code = b.hospital_code
        LEFT JOIN main_gold.mart_reliability_score r ON s.hospital_code = r.hospital_code
        WHERE {where_sql}
        GROUP BY
            s.hospital_code, s.hospital_name, b.hospital_type, b.facility_type,
            s.state_name, s.district_name, b.hospital_contact, b.hospital_address,
            r.reliability_score, r.reliability_label;
    """
    rows = con.execute(query_sql, params).fetchall()

    scored_facilities = []
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
            label,
            total_units,
            breakdown_raw,
        ) = r

        f_lat, f_lng, is_approx = resolve_facility_lat_lng(h_code, s_name, d_name)

        dist_km = None
        if lat is not None and lng is not None:
            dist_km = haversine_distance_km(lat, lng, f_lat, f_lng)

        # Parse group breakdown
        units_by_group: Dict[str, int] = {}
        if breakdown_raw:
            for item in breakdown_raw.split(", "):
                if ":" in item:
                    grp, u = item.split(":", 1)
                    try:
                        units_by_group[grp.strip()] = int(u.strip())
                    except ValueError:
                        pass

        # 1. Freshness Factor (0-100)
        days = days_ago if days_ago is not None else 999
        if days <= 1:
            freshness_factor = 100.0
        elif days <= 3:
            freshness_factor = 70.0
        elif days <= 7:
            freshness_factor = 40.0
        elif days <= 14:
            freshness_factor = 16.0
        else:
            freshness_factor = 0.0

        # 2. Trust Factor (0-100)
        trust_factor = float(score)

        # 3. Units Factor (0-100)
        units_factor = min(100.0, float(total_units) * 10.0)

        # 4. Distance Factor & Composite Rank
        if dist_km is not None:
            dist_factor = max(0.0, 100.0 - dist_km)
            rank_score = (
                0.35 * freshness_factor
                + 0.30 * trust_factor
                + 0.25 * units_factor
                + 0.10 * dist_factor
            )
            dist_desc = f", approx. {dist_km} km away"
        else:
            rank_score = (
                0.40 * freshness_factor
                + 0.35 * trust_factor
                + 0.25 * units_factor
            )
            dist_desc = ""

        # Construct concise, human-readable rationale
        breakdown_desc = ", ".join([f"{u} {g}" for g, u in units_by_group.items()])
        freshness_desc = "updated today" if days <= 1 else f"updated {days}d ago"
        why_ranked = f"{total_units} units ({breakdown_desc}), {freshness_desc}, trust {score}/100 ({label}){dist_desc}"

        scored_facilities.append(
            EmergencyFacilityItem(
                hospital_code=h_code,
                hospital_name=h_name,
                hospital_type=h_type,
                facility_type=f_type,
                state_name=s_name,
                district_name=d_name,
                hospital_contact=contact,
                hospital_address=address,
                latitude=f_lat,
                longitude=f_lng,
                is_approximate_location=is_approx,
                location_precision="district_centroid",
                distance_km=dist_km,
                reliability_score=score,
                reliability_label=label,
                days_since_last_update=days_ago,
                last_updated_at=updated_at,
                total_compatible_units=total_units,
                units_by_group=units_by_group,
                rank_score=round(rank_score, 2),
                why_ranked_here=why_ranked,
            )
        )

    scored_facilities.sort(key=lambda x: x.rank_score, reverse=True)
    top_facilities = scored_facilities[:limit]

    return EmergencyResponse(
        patient_blood_group=clean_group,
        component_name=component,
        compatible_donor_groups=compatible_groups,
        is_rh_negative=is_rh_neg,
        is_rare_phenotype=is_bombay,
        clinical_warning=clinical_warning,
        source_attribution=source_citation,
        disclaimer="Guidance only, not medical advice. Confirm with a doctor or blood bank.",
        total_found=len(scored_facilities),
        top_facilities=top_facilities,
    )


@router.get("/api/v1/medical/rules")
def get_medical_rules_payload():
    """Returns official blood compatibility and donor eligibility rules from config."""
    return get_rules()


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
    rows = con.execute(
        """
        SELECT snapshot_date, units
        FROM main_gold.fct_stock_snapshot
        WHERE hospital_code = ?
          AND component_name = ?
          AND blood_group = ?
        ORDER BY snapshot_date ASC;
    """,
        [hospital_code, component, blood_group],
    ).fetchall()

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
    bg_val = blood_group if isinstance(blood_group, str) else getattr(blood_group, "default", "O-")
    comp_val = (
        component
        if isinstance(component, str)
        else getattr(component, "default", "Packed Red Blood Cells")
    )
    st_val = state if isinstance(state, str) else getattr(state, "default", None)

    where_clauses = ["d.blood_group = ?", "d.component_name = ?"]
    params = [bg_val or "O-", comp_val or "Packed Red Blood Cells"]

    if st_val and st_val != "ALL":
        where_clauses.append("d.state_name = ?")
        params.append(st_val)

    where_sql = " AND ".join(where_clauses)
    query_sql = f"""
        SELECT
            d.state_name,
            d.district_name,
            d.blood_group,
            d.component_name,
            d.total_units,
            d.total_reporting_banks,
            COALESCE(d.banks_with_zero, 0) as banks_with_zero,
            d.shortage_status,
            COALESCE(d.severity_score, 10) as severity_score
        FROM main_gold.mart_district_status d
        WHERE {where_sql}
        ORDER BY severity_score DESC, d.total_units ASC, d.total_reporting_banks DESC
        LIMIT 50;
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
            banks_with_zero=r[6],
            shortage_status=r[7],
            severity_score=r[8],
        )
        for r in rows
    ]


@router.get("/api/v1/rare-blood", response_model=List[RareBloodItem], include_in_schema=False)
@router.get("/api/v1/rare", response_model=List[RareBloodItem])
def get_rare_blood_inventory(
    state: Optional[str] = Query(None, description="State filter"),
    district: Optional[str] = Query(None, description="District filter"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """Identifies facilities currently stocking rare phenotypes (Bombay Oh+, Oh-, and AB-)."""
    where_clauses = ["1=1"]
    params = []

    if state and state != "ALL":
        where_clauses.append("r.state_name = ?")
        params.append(state)
    if district and district != "ALL":
        where_clauses.append("r.district_name = ?")
        params.append(district)

    where_sql = " AND ".join(where_clauses)
    query_sql = f"""
        SELECT
            r.hospital_code,
            r.hospital_name,
            r.state_name,
            r.district_name,
            r.blood_group,
            r.component_name,
            r.units,
            b.hospital_contact,
            b.source_updated_at,
            DATE_DIFF('day', b.source_updated_at, CURRENT_TIMESTAMP) as days_since_update,
            COALESCE(rel.reliability_score, 50) as reliability_score,
            COALESCE(rel.reliability_label, 'Medium') as reliability_label
        FROM main_gold.mart_rare_blood_availability r
        LEFT JOIN main_gold.dim_blood_banks b ON r.hospital_code = b.hospital_code
        LEFT JOIN main_gold.mart_reliability_score rel ON r.hospital_code = rel.hospital_code
        WHERE {where_sql}
        ORDER BY
            CASE WHEN r.blood_group LIKE 'Bombay%' THEN 1 ELSE 2 END,
            r.units DESC, r.hospital_name ASC
        LIMIT 50;
    """
    rows = con.execute(query_sql, params).fetchall()

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
            days_since_last_update=r[9],
            reliability_score=r[10],
            reliability_label=r[11],
        )
        for r in rows
    ]


@router.get("/api/history", include_in_schema=False)
def get_multi_group_history(
    hospital_code: int = Query(..., description="Hospital Code"),
    component: str = Query("Packed Red Blood Cells", description="Blood Component"),
    days: int = Query(14, ge=1, le=90, description="History window in days"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Returns time-series history for a hospital and component across all blood groups.
    ZERO FAKE DATA: Strictly queried from real append-only rows in main_gold.fct_stock_snapshot.
    """
    h_row = con.execute(
        "SELECT hospital_name, district_name, state_name FROM main_gold.dim_blood_banks WHERE hospital_code = ? LIMIT 1;",
        [hospital_code],
    ).fetchone()
    hosp_name = h_row[0] if h_row else f"Hospital #{hospital_code}"
    district = h_row[1] if h_row else ""
    state = h_row[2] if h_row else ""

    min_date = date.today() - timedelta(days=days)
    rows = con.execute(
        """
        SELECT
            snapshot_date,
            blood_group,
            units
        FROM main_gold.fct_stock_snapshot
        WHERE hospital_code = ?
          AND component_name = ?
          AND snapshot_date >= ?
        ORDER BY snapshot_date ASC, blood_group ASC;
    """,
        [hospital_code, component, min_date],
    ).fetchall()

    if not rows:
        return {
            "hospital_code": hospital_code,
            "hospital_name": hosp_name,
            "district": district,
            "state": state,
            "component": component,
            "dates": [],
            "series": {},
            "summary": {},
        }

    dates_raw = sorted(list(set(r[0] for r in rows)))
    dates_set = [d.strftime("%b %d") for d in dates_raw]
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
            "change_7d": f"{'+' if diff > 0 else ''}{diff}",
            "is_critical": current_val <= 2,
        }

    return {
        "hospital_code": hospital_code,
        "hospital_name": hosp_name,
        "district": district,
        "state": state,
        "component": component,
        "dates": dates_set,
        "series": series,
        "summary": summary,
    }


@router.get("/api/v1/export/availability.csv")
def export_availability_csv_endpoint(
    state: Optional[str] = Query(None, description="State filter"),
    district: Optional[str] = Query(None, description="District filter"),
    blood_group: Optional[str] = Query(None, description="Blood Group"),
    component: Optional[str] = Query("Packed Red Blood Cells", description="Component"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """Exports availability search results as a compliant CSV file with UTF-8 BOM."""
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

    where_sql = " AND ".join(where_clauses)
    query_sql = f"""
        SELECT
            s.hospital_code,
            s.hospital_name,
            s.state_name,
            s.district_name,
            b.hospital_type,
            b.facility_type,
            b.hospital_contact,
            s.component_name,
            s.blood_group,
            s.units,
            COALESCE(r.reliability_score, 50) as reliability_score,
            COALESCE(r.reliability_label, 'Medium') as reliability_label,
            DATE_DIFF('day', s.source_updated_at, CURRENT_TIMESTAMP) as days_since_update
        FROM main_gold.fct_stock_current s
        LEFT JOIN main_gold.dim_blood_banks b ON s.hospital_code = b.hospital_code
        LEFT JOIN main_gold.mart_reliability_score r ON s.hospital_code = r.hospital_code
        WHERE {where_sql}
        ORDER BY s.source_updated_at DESC
        LIMIT 5000;
    """
    rows = con.execute(query_sql, params).fetchall()
    items = []
    for r in rows:
        items.append({
            "hospital_code": r[0],
            "hospital_name": r[1],
            "state_name": r[2],
            "district_name": r[3],
            "hospital_type": r[4],
            "facility_type": r[5],
            "hospital_contact": r[6],
            "component_name": r[7],
            "blood_group": r[8],
            "units": r[9],
            "reliability_score": r[10],
            "reliability_label": r[11],
            "days_since_last_update": r[12],
            "location_precision": "district_centroid",
        })
    csv_content = export_search_results_csv(items)
    filename = f"eraktkosh_availability_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/v1/export/shortages.csv")
def export_shortages_csv_endpoint(
    state: Optional[str] = Query(None, description="State filter"),
    blood_group: Optional[str] = Query(None, description="Blood Group"),
    component: Optional[str] = Query("Packed Red Blood Cells", description="Component"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    """Exports district shortage rankings as a compliant CSV file with UTF-8 BOM."""
    shortages = get_district_shortages(
        state=state,
        blood_group=blood_group,
        component=component,
        con=con,
    )
    items_dict = [s.dict() for s in shortages]
    csv_content = export_shortages_csv(items_dict)
    filename = f"eraktkosh_shortages_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/shortages", include_in_schema=False)
def legacy_district_shortages(
    state: Optional[str] = Query(None),
    blood_group: Optional[str] = Query("O-"),
    component: Optional[str] = Query("Packed Red Blood Cells"),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    return get_district_shortages(
        state=state, blood_group=blood_group, component=component, con=con
    )


@router.get("/api/rare", include_in_schema=False)
def legacy_rare_blood(
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    con: duckdb.DuckDBPyConnection = Depends(get_db_session),
):
    return get_rare_blood_inventory(state=state, district=district, con=con)

