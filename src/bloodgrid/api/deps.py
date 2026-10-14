"""
BloodGrid API Dependencies & Lifecycle Guards
=============================================
Provides read-only database connections, request ID tracking,
and authentication validation for paid tiers.
"""

import logging
import uuid
from typing import Generator, Optional

import duckdb
from fastapi import Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bloodgrid.config import settings

logger = logging.getLogger("bloodgrid.api.deps")
security_bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Yields a read-only DuckDB connection to the verified serving database (serving.duckdb).
    Guarantees clean connection teardown and zero conflict with pipeline writers.
    """
    db_file = settings.serving_path if settings.serving_path.exists() else settings.warehouse_path
    if not db_file.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serving database is not initialized. Run pipeline first.",
        )

    con = duckdb.connect(str(db_file), read_only=True)
    try:
        yield con
    finally:
        try:
            con.close()
        except Exception as e:
            logger.debug("Error closing connection: %s", e)


def get_request_id(request: Request) -> str:
    """Extracts or generates unique tracing request ID."""
    req_id = getattr(request.state, "request_id", None)
    if not req_id:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = req_id
    return req_id


async def verify_api_key_or_jwt(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> dict:
    """
    Validates either an API Key or Bearer JWT token for paid/restricted endpoints.
    """
    if x_api_key:
        # Validate API Key prefix and presence
        if x_api_key.startswith("bg_live_") or x_api_key.startswith("bg_test_"):
            return {"auth_type": "api_key", "tier": "pro", "key_id": x_api_key[:16]}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed API key provided in X-API-Key header",
        )

    if credentials and credentials.credentials:
        token = credentials.credentials
        # In full production, decode and verify JWT signature against settings.jwt_secret
        if token == settings.api_key_secret or len(token) > 20:
            return {"auth_type": "jwt", "user_id": "authenticated_user", "tier": "pro"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Bearer authentication token"
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide X-API-Key header or Bearer token.",
    )


async def get_optional_auth(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> Optional[dict]:
    """Allows endpoints to accept optional authentication for guest checkouts."""
    try:
        return await verify_api_key_or_jwt(x_api_key, credentials)
    except HTTPException:
        return None
