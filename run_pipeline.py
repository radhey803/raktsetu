"""
eRaktKosh End-to-End Data Pipeline Entrypoint
============================================
Delegates to bloodlake.pipeline Typer CLI for nationwide async ingestion,
Parquet landing, DuckDB Bronze loading, dbt transformations, and anomaly validation.
"""

import sys
from bloodlake.pipeline import app

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Default to running the full pipeline with interval bypass for convenience
        sys.argv.extend(["all", "--force"])
    app()
