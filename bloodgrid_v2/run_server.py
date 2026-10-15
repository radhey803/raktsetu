"""
BloodGrid V2 Application Runner
================================
Runs the modular, production-grade BloodGrid API & Frontend.
Default port: 8001 (to allow older version on 8000 to run concurrently if desired).
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import uvicorn
from bloodgrid.api.main import app

if __name__ == "__main__":
    port = int(os.environ.get("BLOODGRID_PORT", 8001))
    print(f"Starting BloodGrid V2 on http://localhost:{port}")
    uvicorn.run("bloodgrid.api.main:app", host="0.0.0.0", port=port, reload=True)
