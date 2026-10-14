"""
BloodGrid Main Application Entrypoint
=====================================
Production-ready FastAPI application with modular routers, lifespan management,
security headers, CORS policies, rate limiting, and static SPA serving.
"""

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from bloodgrid.api.routers import admin, auth, billing, public, reports, seo, v1
from bloodgrid.config import settings
from bloodgrid.warehouse.connection import get_serving_connection

logger = logging.getLogger("bloodgrid.api")

# Rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_public])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager validating read-only database readiness on startup."""
    logger.info("Initializing BloodGrid API service (%s mode)...", settings.env)
    try:
        con = get_serving_connection()
        count = con.execute("SELECT COUNT(*) FROM main_gold.dim_blood_banks;").fetchone()[0]
        con.close()
        logger.info("Serving database mounted successfully. Active facilities: %d", count)
    except Exception as e:
        logger.warning("Serving database check at startup: %s. Run pipeline if not generated yet.", e)

    yield

    logger.info("Shutting down BloodGrid API service.")


app = FastAPI(
    title="BloodGrid API",
    description="Real-time National Blood Banking Intelligence Platform & Shortage Radar API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. Gzip compression for payloads > 1000 bytes
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS middleware locked to allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)


# 3. Security headers & Request-ID middleware
@app.middleware("http")
async def security_and_tracing_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id

    start_time = time.time()
    response: Response = await call_next(request)
    duration = time.time() - start_time

    # Set tracing and performance headers
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"

    # Set OWASP security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    return response


# Include modular routers
app.include_router(public.router)
app.include_router(v1.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(reports.router)
app.include_router(billing.router)
app.include_router(seo.router)

# Serve web static frontend assets
web_dir = settings.web_dir if settings.web_dir.exists() else settings.base_dir / "static"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.get("/", tags=["Frontend"])
def serve_index():
    """Serves the main application dashboard."""
    index_file = web_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "BloodGrid API online. Frontend build directory available at /static."}


@app.get("/healthz", tags=["Observability"])
def liveness_probe():
    """Kubernetes / Docker liveness probe."""
    return {"status": "ok", "service": "bloodgrid-api"}


@app.get("/readyz", tags=["Observability"])
def readiness_probe():
    """Kubernetes / Docker readiness probe checking database availability."""
    try:
        con = get_serving_connection()
        con.execute("SELECT 1;").fetchone()
        con.close()
        return {"status": "ready", "database": "serving.duckdb"}
    except Exception as e:
        return Response(content=f'{{"status":"not ready","error":"{e}"}}', status_code=503, media_type="application/json")
