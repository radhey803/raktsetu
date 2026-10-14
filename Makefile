.PHONY: help setup install lint format test run-pipeline run-api dbt-build clean docker-build

SHELL := /bin/bash

help:
	@echo "BloodGrid Developer Automation Makefile"
	@echo "-----------------------------------------"
	@echo "make setup        - Install all dependencies with uv"
	@echo "make lint         - Check code formatting and static typing"
	@echo "make format       - Automatically format code with ruff"
	@echo "make test         - Run full test suite with coverage report"
	@echo "make run-pipeline - Execute full scrape -> transform -> test -> publish pipeline"
	@echo "make run-api      - Run FastAPI server locally with auto-reload"
	@echo "make dbt-build    - Run dbt build and data validation tests"
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
	uv run pytest tests/ -v --cov=src/bloodgrid --cov-report=term-missing

run-pipeline:
	uv run python -m bloodgrid.pipeline.run all

run-api:
	uv run uvicorn bloodgrid.api.main:app --host 0.0.0.0 --port 8000 --reload

dbt-build:
	uv run dbt build --project-dir dbt --profiles-dir dbt

docker-build:
	docker build -t bloodgrid:latest .

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov __pycache__ dbt/target dbt/logs logs/
	find . -type d -name "__pycache__" -exec rm -rf {} +
