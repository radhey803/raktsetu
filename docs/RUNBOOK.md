# BloodGrid Operational Runbook

This runbook guides engineers through monitoring, triage, failure response, and recovery procedures for the BloodGrid data pipeline and API service.

---

## 1. System Health & Probes

| Endpoint | Method | Expected Output | Purpose |
| :--- | :--- | :--- | :--- |
| `/healthz` | `GET` | `{"status":"ok","service":"bloodgrid-api"}` | Liveness probe (HTTP server alive) |
| `/readyz` | `GET` | `{"status":"ready","database":"serving.duckdb"}` | Readiness probe (database mount check) |
| `/v1/meta` | `GET` | `{"total_facilities": 4681, ...}` | System metadata & facility count |
| `/v1/admin/pipeline-runs` | `GET` | Execution history & status | Pipeline run audit log |

---

## 2. Common Alerts & Triage Steps

### Alert 1: Pipeline Anomaly Gate Tripped (`FACILITY_COUNT_DROP`)
- **Trigger**: Pipeline returns $< 80\%$ of previous run's facility count.
- **Root Cause**: eRaktKosh portal may be undergoing maintenance, returning empty HTML, or blocking IPs.
- **Action**:
  1. The pipeline automatically **aborts publication**; `serving.duckdb` remains untouched and continues serving the last verified snapshot.
  2. Inspect the latest log in GitHub Actions: `gh run view --log`.
  3. Test manual district fetch from CLI:
     ```bash
     uv run python -c "from bloodgrid.ingestion.scraper import *; import asyncio; print(asyncio.run(fetch_district_data(...)))"
     ```
  4. If eRaktKosh is down, wait for the next scheduled 4-hour cycle. The frontend will show a subtle *"Data updated > 12h ago"* warning after 12 hours.

### Alert 2: Circuit Breaker Error (>20% Failure Rate)
- **Trigger**: More than 156 of 781 districts failed to return valid JSON.
- **Action**:
  1. Check if the portal changed query parameters or headers.
  2. Verify network connectivity from the server: `curl -I https://eraktkosh.mohfw.gov.in`.
  3. Review `failed_samples` in `pipeline_runs` table:
     ```bash
     uv run python -c "import duckdb; con = duckdb.connect('blood_warehouse.duckdb', read_only=True); print(con.execute('SELECT * FROM gold.pipeline_runs ORDER BY started_at DESC LIMIT 1;').fetchall())"
     ```

### Alert 3: Database Lock or Serving File Corrupt
- **Trigger**: `/readyz` returns HTTP 503.
- **Action**:
  1. Check if `serving.duckdb.tmp` was left hanging during a crash:
     ```bash
     ls -lh data/serving*
     ```
  2. Restore the latest verified snapshot from backup or previous run:
     ```bash
     cp data/warehouse/blood_warehouse.duckdb data/serving/serving.duckdb
     ```
  3. Trigger the signed cache refresh webhook:
     ```bash
     curl -X POST http://localhost:8000/v1/meta/refresh -H "Authorization: Bearer $API_KEY_SECRET"
     ```

---

## 3. Manual Pipeline Execution

To trigger a full, out-of-schedule nationwide crawl and atomic database swap:
```bash
# Execute end-to-end pipeline with source guard override
uv run bloodgrid all --force
```

To run individual stages:
```bash
# 1. Scrape only
uv run bloodgrid scrape --force --concurrency 10

# 2. Ingest landing Parquet into Bronze
uv run bloodgrid load

# 3. Transform via dbt
uv run bloodgrid transform

# 4. Run data quality tests & anomaly gate
uv run bloodgrid test

# 5. Atomically publish to serving.duckdb
uv run bloodgrid publish
```

---

## 4. Backups and Disaster Recovery

### Parquet Landing & Database Backup to S3 / Cloudflare R2
```bash
# Sync immutable landing zone
aws s3 sync data/landing/ s3://bloodgrid-lakehouse-backups/landing/ --endpoint-url $R2_ENDPOINT_URL

# Copy serving database
aws s3 cp data/serving/serving.duckdb s3://bloodgrid-lakehouse-backups/snapshots/serving_$(date +%Y%m%d).duckdb --endpoint-url $R2_ENDPOINT_URL
```

### Complete Disaster Recovery from Scratch
If all local databases are deleted:
1. Re-run `uv run bloodgrid all --force` (takes ~2 minutes from empty state).
2. The pipeline will:
   - Scrape all 781 districts.
   - Write immutable landing Parquet with SHA-256 metadata.
   - Ingest into fresh Bronze DuckDB table.
   - Run dbt build (materializing all 47 views, models, and tests).
   - Atomically publish `serving.duckdb`.
   - Restore `/readyz` to HTTP 200.
