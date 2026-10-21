.PHONY: help install run demo demo-offline test lint format \
        scrape load transform gate publish pipeline status \
        dbt-test docs serve-docs diagrams report clean

SHELL := /bin/bash
APP   := bloodlake.api.main:app

help:
	@echo "Raktsetu / eRaktKosh Blood Lakehouse"
	@echo ""
	@echo "Setup & app"
	@echo "  make install       Install dependencies (uv sync)"
	@echo "  make run           Run the API + web UI with hot-reload on http://localhost:8000"
	@echo "  make demo          Run the test suite, then start the server"
	@echo "  make demo-offline  Restore serving.duckdb from demo/ and start the server"
	@echo ""
	@echo "Quality"
	@echo "  make test          Run pytest with coverage"
	@echo "  make lint          Ruff lint + format check"
	@echo "  make format        Ruff auto-format and fix"
	@echo "  make dbt-test      Run dbt data tests"
	@echo ""
	@echo "Data pipeline (each step = one 'bloodlake' CLI command)"
	@echo "  make scrape        Crawl eRaktKosh into data/landing/ (Parquet)"
	@echo "  make load          Load the newest landing file into bronze"
	@echo "  make transform     dbt build (silver + gold, incl. snapshots)"
	@echo "  make gate          Facility-count anomaly gate"
	@echo "  make publish       Copy warehouse -> serving.duckdb atomically"
	@echo "  make pipeline      All of the above, end to end"
	@echo "  make status        Show recent pipeline runs"
	@echo ""
	@echo "Docs & report"
	@echo "  make docs          Generate dbt docs (served at /dbt-docs/)"
	@echo "  make serve-docs    Serve dbt docs on http://localhost:8080"
	@echo "  make diagrams      Regenerate UML diagrams into docs/diagrams/"
	@echo "  make report        Rebuild reports/Raktsetu_Project_Report.docx"
	@echo "  make clean         Remove caches and build artifacts"

install:
	uv sync

run:
	uv run uvicorn $(APP) --host 0.0.0.0 --port 8000 --reload

demo:
	uv run pytest tests/ -q
	uv run uvicorn $(APP) --host 0.0.0.0 --port 8000

demo-offline:
	@if [ ! -f demo/fallback_lakehouse.duckdb ]; then \
		echo "Creating demo/fallback_lakehouse.duckdb from serving.duckdb..."; \
		cp serving.duckdb demo/fallback_lakehouse.duckdb; \
	fi
	@cp demo/fallback_lakehouse.duckdb serving.duckdb
	uv run uvicorn $(APP) --host 0.0.0.0 --port 8000

test:
	uv run pytest tests/ -v --cov=src/bloodlake --cov-report=term-missing

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

dbt-test:
	uv run dbt test --project-dir dbt --profiles-dir dbt

scrape:
	uv run bloodlake scrape

load:
	uv run bloodlake load

transform:
	uv run bloodlake transform

gate:
	uv run bloodlake test

publish:
	uv run bloodlake publish

pipeline:
	uv run bloodlake all --force

status:
	uv run bloodlake status

docs:
	uv run dbt docs generate --project-dir dbt --profiles-dir dbt

serve-docs:
	uv run dbt docs serve --project-dir dbt --profiles-dir dbt --port 8080

diagrams:
	uv run python scripts/report/generate_diagrams.py

report: diagrams
	uv run python scripts/report/build_raktsetu_docx.py

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dbt/target dbt/logs logs/
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
