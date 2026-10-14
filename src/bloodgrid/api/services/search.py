"""
BloodGrid Emergency Search Service
==================================
Executes high-performance SQL searches against fct_stock_current, dim_blood_banks,
and mart_reliability_score with exact normalized blood group matching.
Eliminates all raw regex string searches.
"""

from typing import Any, Dict, List, Optional, Tuple
import duckdb

from bloodgrid.geo.geocode import resolve_facility_lat_lng


def execute_emergency_search(
    con: duckdb.DuckDBPyConnection,
    component: Optional[str] = "Packed Red Blood Cells",
    blood_group: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    min_units: int = 0,
    search_query: Optional[str] = None,
    sort: str = "freshness",
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Structured analytical query matching exact blood group and component quantities.
    Returns (results_list, total_matching_facilities).
    """
    # 1. Base query joining dim_blood_banks with mart_reliability_score
    params: List[Any] = []
    where_clauses: List[str] = ["1=1"]

    if state and state.upper() != "ALL":
        where_clauses.append("LOWER(b.state_name) = LOWER(?)")
        params.append(state.strip())

    if district and district.upper() != "ALL":
        where_clauses.append("LOWER(b.district_name) = LOWER(?)")
        params.append(district.strip())

    if search_query and search_query.strip():
        q = f"%{search_query.strip().lower()}%"
        where_clauses.append("(LOWER(b.hospital_name) LIKE ? OR LOWER(b.hospital_address) LIKE ?)")
        params.extend([q, q])

    # 2. Filtering by component and blood group if specified
    stock_filter_sql = ""
    if component and component.upper() != "ALL":
        stock_filter_sql += " AND s.component_name = ?"
        params.append(component)
    if blood_group and blood_group.upper() != "ALL":
        stock_filter_sql += " AND s.blood_group = ?"
        params.append(blood_group)
    if min_units > 0:
        stock_filter_sql += " AND s.units >= ?"
        params.append(min_units)

    # Count total matching facilities
    count_sql = f"""
        SELECT COUNT(DISTINCT b.hospital_code)
        FROM main_gold.dim_blood_banks b
        LEFT JOIN main_gold.fct_stock_current s ON b.hospital_code = s.hospital_code {stock_filter_sql}
        WHERE {" AND ".join(where_clauses)}
    """
    if blood_group and blood_group.upper() != "ALL":
        count_sql += " AND s.units > 0"

    total_count = con.execute(count_sql, params).fetchone()[0]

    # Ordering
    order_clause = "r.days_since_update ASC NULLS LAST, r.reliability_score DESC"
    if sort == "units":
        order_clause = "stock_units DESC NULLS LAST, r.days_since_update ASC"
    elif sort == "reliability":
        order_clause = "r.reliability_score DESC, r.days_since_update ASC"

    # Data fetch query
    fetch_sql = f"""
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
            r.days_since_update,
            COALESCE(r.reliability_score, 0) AS reliability_score,
            COALESCE(r.reliability_tier, 'UNKNOWN') AS reliability_tier,
            COALESCE(SUM(s.units), 0) AS stock_units
        FROM main_gold.dim_blood_banks b
        LEFT JOIN main_gold.mart_reliability_score r ON b.hospital_code = r.hospital_code
        LEFT JOIN main_gold.fct_stock_current s ON b.hospital_code = s.hospital_code {stock_filter_sql}
        WHERE {" AND ".join(where_clauses)}
    """
    if blood_group and blood_group.upper() != "ALL":
        fetch_sql += " AND s.units > 0"

    fetch_sql += f"""
        GROUP BY 
            b.hospital_code, b.hospital_name, b.hospital_type, b.facility_type,
            b.state_name, b.district_name, b.hospital_contact, b.hospital_address,
            b.source_updated_at, r.days_since_update, r.reliability_score, r.reliability_tier
        ORDER BY {order_clause}
        LIMIT ? OFFSET ?;
    """
    params.extend([limit, offset])

    rows = con.execute(fetch_sql, params).fetchall()

    facility_codes = [r[0] for r in rows]

    # Fetch 4x2 matrix stock breakdown for returned facilities
    all_stock_map: Dict[int, Dict[str, Dict[str, int]]] = {}
    if facility_codes:
        stock_rows = con.execute(f"""
            SELECT hospital_code, component_name, blood_group, units
            FROM main_gold.fct_stock_current
            WHERE hospital_code IN ({','.join(['?'] * len(facility_codes))})
            ORDER BY hospital_code, component_name, blood_group;
        """, facility_codes).fetchall()

        for hcode, comp, bg, u in stock_rows:
            if hcode not in all_stock_map:
                all_stock_map[hcode] = {}
            if comp not in all_stock_map[hcode]:
                all_stock_map[hcode][comp] = {}
            all_stock_map[hcode][comp][bg] = u

    results = []
    for r in rows:
        hcode = r[0]
        hname = r[1]
        state_n = r[4] or ""
        dist_n = r[5] or ""
        addr = r[7] or ""

        lat, lng, prec = resolve_facility_lat_lng(
            hospital_code=hcode,
            hospital_name=hname,
            hospital_address=addr,
            state=state_n,
            district=dist_n,
            con=con,
            allow_network_lookup=False
        )

        h_stocks = all_stock_map.get(hcode, {})
        # Format stock summary string for the requested component
        target_comp = component or "Packed Red Blood Cells"
        comp_stock = h_stocks.get(target_comp, {})
        stock_summary_parts = [f"{bg} : {u}" for bg, u in comp_stock.items() if u > 0]
        stock_str = ", ".join(stock_summary_parts)

        results.append({
            "code": hcode,
            "name": hname,
            "type": r[2] or "Govt.",
            "facility": r[3] or "Blood Centre",
            "state": state_n,
            "district": dist_n,
            "contact": r[6] or "",
            "address": addr,
            "last_updated": str(r[8]) if r[8] else "Unknown",
            "days_stale": r[9],
            "reliability_score": r[10],
            "reliability_tier": r[11],
            "matched_units": r[12],
            "stock": stock_str,
            "component": target_comp,
            "all_stock": h_stocks,
            "lat": lat,
            "lng": lng,
            "precision": prec
        })

    return results, total_count
