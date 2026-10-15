.PHONY: help setup install lint format test dbt-test run demo demo-offline scrape ingest transform snapshot pipeline docs clean

SHELL := /bin/bash

help:
	@echo "========================================================================"
	@echo "🩸 eRaktKosh Blood Lakehouse: Makefile (MCA Mini Project, CHARUSAT)"
	@echo "========================================================================"
	@echo "make run           - Run FastAPI server with hot-reload (http://localhost:8000)"
	@echo "make demo          - Run test assertions and launch live demo server"
	@echo "make demo-offline  - Restore serving database from demo fallback and launch"
	@echo "make test          - Run pytest test suite (45 unit & integration tests)"
	@echo "make dbt-test      - Run all 35 dbt relational schema and contract tests"
	@echo "make lint          - Check code quality with Ruff"
	@echo "make format        - Format code and fix linter issues with Ruff"
	@echo "make scrape        - Run asynchronous crawler across 781 districts (~26s)"
	@echo "make ingest        - Ingest Parquet landing files into Bronze layer"
	@echo "make transform     - Run dbt transformation models (Silver & Gold layers)"
	@echo "make snapshot      - Record daily inventory snapshot into fct_stock_snapshot"
	@echo "make pipeline      - Execute full pipeline end-to-end (bloodlake all)"
	@echo "make docs          - Generate dbt documentation and catalog"
	@echo "make clean         - Remove temporary cache files and test artifacts"
	@echo "========================================================================"

setup: install

install:
	uv sync

run:
	uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload

demo:
	@echo "========================================================================"
	@echo "🩸 eRaktKosh Blood Lakehouse: Initializing Evaluator Demo"
	@echo "========================================================================"
	uv run pytest tests/ -q
	uv run uvicorn api:app --host 0.0.0.0 --port 8000

demo-offline:
	@echo "========================================================================"
	@echo "🩸 eRaktKosh Blood Lakehouse: Offline Fallback Mode"
	@echo "========================================================================"
	@if [ ! -f demo/fallback_lakehouse.duckdb ]; then \
		echo "Creating demo/fallback_lakehouse.duckdb from serving.duckdb..."; \
		cp serving.duckdb demo/fallback_lakehouse.duckdb; \
	fi
	@cp demo/fallback_lakehouse.duckdb serving.duckdb
	@echo "Serving database verified. Launching offline server at http://localhost:8000..."
	uv run uvicorn api:app --host 0.0.0.0 --port 8000

test:
	uv run pytest tests/ -v --cov=src/bloodlake --cov-report=term-missing

dbt-test:
	uv run dbt test --project-dir dbt --profiles-dir dbt

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

scrape:
	uv run bloodlake scrape

ingest:
	uv run bloodlake ingest

transform:
	uv run bloodlake transform

snapshot:
	uv run bloodlake snapshot

pipeline:
	uv run bloodlake all --force

docs:
	uv run dbt docs generate --project-dir dbt --profiles-dir dbt

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov __pycache__ dbt/target dbt/logs logs/
	find . -type d -name "__pycache__" -exec rm -rf {} +
