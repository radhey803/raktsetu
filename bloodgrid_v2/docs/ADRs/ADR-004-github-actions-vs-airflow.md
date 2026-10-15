# ADR-004: GitHub Actions Cron Orchestration vs Heavyweight Orchestrators (Airflow/Dagster)

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Principal Data Engineer, Senior Full-Stack Engineer

---

## Context & Problem Statement
The nationwide crawl and lakehouse transformation runs every 4 hours (00/04/08/12/16/20 IST). The pipeline consists of 5 sequential stages:
`scrape -> load -> transform -> test -> publish`.

Options considered for scheduling:
1. **Apache Airflow**: Industry standard, extensive UI, DAG scheduling. Requires webserver, scheduler, metadata Postgres, and worker daemon (minimum 4GB RAM).
2. **Dagster / Prefect**: Modern orchestrators, assets and code-as-configuration.
3. **GitHub Actions Scheduled Workflow**: Runs on GitHub-hosted Ubuntu runners (2 vCPU, 7GB RAM) at zero server infrastructure cost.

---

## Decision
We selected **GitHub Actions Scheduled Workflows** (`.github/workflows/pipeline.yml`):
- Executes `bloodgrid all` inside the containerized repository environment.
- Uploads validated `serving.duckdb` and Parquet landing files directly to Cloudflare R2 / S3 object storage.
- Dispatches signed refresh webhook to the serving API upon successful publication.
- Sends Telegram / Email notifications upon double retry failure.

Airflow or Dagster remain documented as architectural alternatives in the repository documentation if sub-hour pipelines or complex dynamic branching are required in the future.

---

## Consequences
- **Positive**:
  - $0/month orchestration cost (included in free GitHub Actions minutes for public/standard repositories).
  - Zero server maintenance, zero daemon crashes, zero orchestrator database migrations.
  - Transparent execution logs visible directly in the repository pull request & action tab.
- **Negative**:
  - Cron triggers on GitHub Actions can experience variable queue delays (up to 5-15 minutes during peak GitHub load).
  - Max job timeout of 6 hours (irrelevant since our entire crawl and build runs in under 4 minutes).
