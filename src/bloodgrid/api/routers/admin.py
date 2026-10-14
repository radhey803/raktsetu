"""
BloodGrid Admin & Operational Observability Router
==================================================
Exposes pipeline run logs, data freshness health, and manual sync triggers.
"""

from typing import List, Optional
import duckdb
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from bloodgrid.api.deps import get_db, get_request_id, verify_api_key_or_jwt
from bloodgrid.config import settings

router = APIRouter(prefix="/v1/admin", tags=["Operational Admin & Health"])


@router.get("/pipeline-runs", summary="Audit Pipeline Execution Logs")
def get_pipeline_runs(
    request: Request,
    limit: int = 10,
    auth: dict = Depends(verify_api_key_or_jwt),
    con: duckdb.DuckDBPyConnection = Depends(get_db)
):
    req_id = get_request_id(request)
    runs = con.execute("""
        SELECT run_id, started_at, finished_at, status, facilities_count, tests_passed, error_message
        FROM gold.pipeline_runs
        ORDER BY started_at DESC
        LIMIT ?;
    """, [limit]).fetchall()

    data = [
        {
            "run_id": r[0],
            "started_at": r[1].isoformat() if r[1] else None,
            "finished_at": r[2].isoformat() if r[2] else None,
            "status": r[3],
            "facilities_count": r[4],
            "tests_passed": r[5],
            "error_message": r[6]
        }
        for r in runs
    ]

    return {
        "success": True,
        "request_id": req_id,
        "runs": data
    }
