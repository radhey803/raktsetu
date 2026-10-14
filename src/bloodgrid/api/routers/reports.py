"""
BloodGrid NGO & CSR Analytics Router
====================================
Provides analytical exports for blood donor organizations, CSR foundations,
and transfusion coordinators:
- CSV Shortage Exports
- Donation Camp Location Suggester
- Honest ML Demand Forecasting Stub
"""

import io
from datetime import datetime, timezone
from typing import Optional

import duckdb
from fastapi import APIRouter, Depends, Query, Response

from bloodgrid.api.deps import get_db
from bloodgrid.config import settings

router = APIRouter(prefix="/v1/reports", tags=["NGO, CSR & Analytical Reports"])


@router.get("/district-shortages.csv", summary="Export District Deficit Report as CSV")
def export_shortage_report_csv(
    state: Optional[str] = Query(None),
    component: Optional[str] = Query("Packed Red Blood Cells"),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """Generates downlodable CSV report of district blood deficits for planning donation drives."""
    params = []
    where_clauses = ["1=1"]

    if state and state.upper() != "ALL":
        where_clauses.append("LOWER(state_name) = LOWER(?)")
        params.append(state.strip())

    if component and component.upper() != "ALL":
        where_clauses.append("component_name = ?")
        params.append(component.strip())

    sql = f"""
        SELECT
            state_name AS State,
            district_name AS District,
            component_name AS Component,
            blood_group AS Blood_Group,
            total_reporting_banks AS Reporting_Facilities,
            stocked_banks AS Stocked_Facilities,
            total_units AS Total_Units,
            shortage_status AS Shortage_Status
        FROM main_gold.mart_district_status
        WHERE {" AND ".join(where_clauses)}
        ORDER BY state_name, district_name, total_units ASC;
    """.strip()
    df = con.execute(sql, params).df()

    output = io.StringIO()
    df.to_csv(output, index=False)
    csv_bytes = output.getvalue().encode("utf-8")

    filename = f"bloodgrid_shortage_report_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/donation-camp-suggester", summary="Smart Donation Camp Location Suggester")
def suggest_donation_camp_locations(
    state: Optional[str] = Query(None),
    blood_group: Optional[str] = Query("O-"),
    limit: int = Query(10, ge=1, le=50),
    con: duckdb.DuckDBPyConnection = Depends(get_db),
):
    """
    Identifies districts with critical blood deficits where donation drives
    will deliver the highest life-saving community impact.
    """
    params = []
    where_clauses = ["1=1"]

    if state and state.upper() != "ALL":
        where_clauses.append("LOWER(state_name) = LOWER(?)")
        params.append(state.strip())

    if blood_group and blood_group.upper() != "ALL":
        where_clauses.append("blood_group = ?")
        params.append(blood_group.strip())

    sql = f"""
        SELECT
            state_name,
            district_name,
            component_name,
            blood_group,
            total_reporting_banks,
            stocked_banks,
            total_units,
            shortage_status,
            CASE
                WHEN total_units = 0 THEN 100
                WHEN total_units <= 5 THEN 80
                WHEN total_units <= 15 THEN 50
                ELSE 10
            END AS camp_priority_score
        FROM main_gold.mart_district_status
        WHERE {" AND ".join(where_clauses)}
        ORDER BY camp_priority_score DESC, total_units ASC
        LIMIT ?;
    """
    params.append(limit)
    rows = con.execute(sql, params).fetchall()

    suggestions = [
        {
            "rank": idx + 1,
            "state": r[0],
            "district": r[1],
            "component": r[2],
            "blood_group": r[3],
            "reporting_banks": r[4],
            "stocked_banks": r[5],
            "current_units": r[6],
            "status": r[7],
            "camp_priority_score": r[8],
            "recommendation": f"Schedule immediate mobile donation camp targeting {r[3]} donors in {r[1]}.",
        }
        for idx, r in enumerate(rows)
    ]

    return {
        "success": True,
        "criteria": {"state": state or "Nationwide", "blood_group": blood_group or "All"},
        "suggested_locations": suggestions,
    }


@router.get("/forecasting-stub", summary="Predictive Demand Forecasting Status")
def get_forecasting_status(con: duckdb.DuckDBPyConnection = Depends(get_db)):
    """
    Honest ML Forecasting Stub.
    Adheres strictly to Rule 1: ZERO fake data or fabricated forecasts.
    ML demand forecasting requires >= 60 days of genuine real lakehouse snapshots.
    """
    dates_cnt = con.execute(
        "SELECT COUNT(DISTINCT snapshot_date) FROM main_gold.fct_stock_snapshot;"
    ).fetchone()[0]

    return {
        "status": "DATA_ACCUMULATION_PHASE",
        "feature_flag": "ml_forecasting_disabled",
        "current_real_snapshot_days": dates_cnt,
        "required_real_snapshot_days": 60,
        "remaining_days_needed": max(0, 60 - dates_cnt),
        "message": (
            f"Machine learning demand forecasting is disabled until at least 60 days of real, continuous "
            f"lakehouse snapshots are recorded. Current real history: {dates_cnt} day(s). "
            f"Synthetic or random forecasting is strictly prohibited by BloodGrid core principles."
        ),
    }


@router.get("/pricing", summary="Available Pricing Tiers (INR)")
def get_pricing_tiers():
    """Returns official commercial tier entitlements and prices in INR."""
    return {
        "currency": "INR",
        "plans": settings.pricing_plans,
        "note": "Prices are configurable via application configuration.",
    }
