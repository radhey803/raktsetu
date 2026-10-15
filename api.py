"""
eRaktKosh Blood Lakehouse API
=============================
Entrypoint for ASGI server (Uvicorn), delegating to the structured bloodlake package.
Maintains continuous uptime for: uv run uvicorn api:app --reload --port 8000
"""

from bloodlake.api.main import app

__all__ = ["app"]
