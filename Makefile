.PHONY: help setup install lint format test run-pipeline run-api dbt-build clean demo

SHELL := /bin/bash

help:
	@echo "eRaktKosh Blood Lakehouse: Makefile (MCA Project, CHARUSAT)"
	@echo "------------------------------------------------------------"
	@echo "make setup        - Install dependencies with uv"
	@echo "make lint         - Check code formatting and static analysis"
	@echo "make format       - Automatically format code with ruff"
	@echo "make test         - Run pytest suite with coverage"
	@echo "make run-pipeline - Execute full scrape -> transform -> test -> publish pipeline"
	@echo "make run-api      - Run FastAPI server on port 8000 with auto-reload"
	@echo "make dbt-build    - Run dbt build and 35 schema validation tests"
	@echo "make demo         - Run pipeline verification and launch live web application"
	@echo "make clean        - Remove caches, temporary files, and test artifacts"

setup:
	uv sync

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

test:
	uv run pytest tests/ -v --cov=src/bloodlake --cov-report=term-missing

run-pipeline:
	uv run bloodlake all --force

run-api:
	uv run uvicorn bloodlake.api.main:app --host 0.0.0.0 --port 8000 --reload

dbt-build:
	uv run dbt build --project-dir dbt --profiles-dir dbt

demo:
	@echo "================================================================"
	@echo "🩸 eRaktKosh Blood Lakehouse: Demo Initializer (CHARUSAT MCA)"
	@echo "================================================================"
	uv run bloodlake status
	uv run pytest tests/ -q
	uv run uvicorn bloodlake.api.main:app --host 0.0.0.0 --port 8000

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov __pycache__ dbt/target dbt/logs logs/
	find . -type d -name "__pycache__" -exec rm -rf {} +
