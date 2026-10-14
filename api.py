"""
BloodGrid API Forwarder
=======================
Exposes the modular FastAPI application for backwards-compatible runner invocations.
Canonical application defined in bloodgrid.api.main:app.
"""

from bloodgrid.api.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bloodgrid.api.main:app", host="0.0.0.0", port=8000, reload=True)
