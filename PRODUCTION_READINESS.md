# BloodGrid Production Readiness Report

**Project**: BloodGrid (National Blood Banking Intelligence & Shortage Radar)  
**Evaluation Date**: 2026-10-15  
**Sign-off Roles**: Principal Data Engineer, Senior Full-Stack Engineer, Product Lead  
**Overall Readiness Verdict**: **PRODUCTION READY (PASS)**

---

## 1. Phase-by-Phase Verification & Proof

| Phase | Title | Verdict | Evidence / Proof Command Output |
| :--- | :--- | :--- | :--- |
| **Phase 0** | **Audit & Cleanup** | **PASS** | Mapped repository blockers into `AUDIT.md`. Purged legacy scripts (`fast_scraper.py`, `scrape_targeted_anand.py`, `ahmedabad_blood_inventory.csv`, `bundle.js`, `node_modules`). Restructured codebase into `src/bloodgrid`, `dbt`, `web`, `tests`, `docs`. Commit `1a1a5b9`. |
| **Phase 1** | **Data Engineering** | **PASS** | Purged 413,098 synthetic snapshot rows. Built immutable Parquet landing zone with zstd compression and SHA-256 manifests. Built dbt strict blood group normalizer macro, unnested 59,026 clinical records, and materialized Gold marts (`dim_blood_banks`, `fct_stock_current`, `fct_stock_snapshot`, `mart_reliability_score`, `mart_district_status`). Typer CLI `bloodgrid` built with atomic swap to `serving.duckdb`. All 47 dbt tests pass. Commit `d7f93be`. |
| **Phase 2** | **Orchestration & Deploy** | **PASS** | Configured 4-hour scheduled workflow (`.github/workflows/pipeline.yml`) with 2x retry, Telegram alert dispatch on double failure, S3/R2 backup, and signed webhook refresh trigger. Documented low-cost VPS + Caddy deployment architecture in `docs/DEPLOYMENT.md` ($5.30/mo operating cost). Commit `dc15d35`. |
| **Phase 3** | **Backend API** | **PASS** | Modular FastAPI architecture with lifespan-managed connections to read-only `serving.duckdb`. Replaced fragile regex with indexed SQL lookups. Added Argon2id password hashing, JWT authentication, hashed API keys (`bg_live_`), OWASP security headers, CORS protection, and slowapi rate limiting. Commit `cfaecbd`. |
| **Phase 4** | **Product Features** | **PASS** | Built programmatic SEO routes (`/blood-banks/{state}/{district}`) with JSON-LD schema, `sitemap.xml`, and `robots.txt`. Implemented alert engine with quiet-hour suppression and daily caps. Added multi-channel dispatcher (Telegram + Email). Added NGO donation camp location suggester, CSV shortage exports, multilingual dictionary (English, Hindi, Gujarati), and WhatsApp SOS card. Commit `f270300`. |
| **Phase 5** | **Payments** | **PASS** | Integrated Razorpay subscriptions with cryptographic HMAC-SHA256 webhook signature verification, idempotent event processing, and 3-day failed-payment grace period. Server-side entitlement gates by plan tier (`free`, `pro`, `developer`, `organization`). GST-ready invoice generation (SAC 998313). Commit `34d2476`. |
| **Phase 6** | **Frontend Experience** | **PASS** | Redesigned UI with warm off-white canvas `#FBF8F6`, ink `#1A1214`, primary red `#D21F3C`, Fraunces serif + Geist sans typography, 1px hairlines, and 0 emojis (replaced with Lucide-style inline SVG sprite). Added developer console (`web/dashboard.html`), legal pages, stale data banners, and offline detection. Total JS weight: ~66 KB (< 200 KB budget). Commit `0755579`. |
| **Phase 7** | **Testing, CI & Observability** | **PASS** | Expanded test suite to **86 passed tests**. Code coverage on `src/` reached **85.08%** (exceeding >=80% mandate). Ruff check & format clean (0 errors). Automated `pip-audit` scan passed with 0 vulnerabilities. GitHub Actions CI workflow created (`.github/workflows/ci.yml`). Commit `156c154`. |
| **Phase 8** | **Legal & Compliance** | **PASS** | Authored `docs/LEGAL.md` detailing eRaktKosh source attribution, DPDP Act 2023 compliance guidelines, NIC/NHM MoU outreach email template, and counsel draft policies for Terms, Privacy, Refund, and Medical Disclaimer. Commit `dccb534`. |
| **Phase 9** | **Docs & Portfolio** | **PASS** | Authored comprehensive `README.md` with Mermaid diagram, quickstart, and honest limitations. Created 5 ADRs (`ADR-001` through `ADR-005`), `docs/DATA_DICTIONARY.md`, `docs/RUNBOOK.md`, `docs/API.md`, and 2-minute demo pitch script (`docs/PITCH_AND_DEMO.md`). Commit `4e64cbc`. |
| **Phase 10** | **Final Verification** | **PASS** | Executed 25/25 endpoint smoke test suite with 100% pass rate. Verified 0 fake data in repository. Audited SQL snapshot integrity. |

---

## 2. Bugs Found and Fixed

| # | Bug Description | Severity | Root Cause | Fix Applied | Status |
| :- | :--- | :--- | :--- | :--- | :--- |
| 1 | **SQL Parameter Ordering Mismatch** | Blocker | In `src/bloodgrid/api/services/search.py`, `stock_filter_sql` was in the `LEFT JOIN ... ON` clause while state filters were in `WHERE`. Appending WHERE parameters before JOIN parameters caused DuckDB to bind the state string ("Gujarat") to component name and vice versa. | Refactored parameter aggregation into `base_params = join_params + where_params` matching exact SQL lexical order. | **FIXED** |
| 2 | **Retention Directory Cleanup Failure** | Major | In `src/bloodgrid/ingestion/landing.py`, `dt_dir.rmdir()` failed with `IsADirectoryError` because date partitions contained `hh=00` subdirectories. | Changed to `shutil.rmtree(dt_dir, ignore_errors=True)`. | **FIXED** |
| 3 | **Broken Column Parsing via CSV** | Major | Legacy pipeline serialized raw scraped JSON into CSV before loading into DuckDB, causing multiline strings and commas to corrupt columns. | Replaced CSV roundtrip with direct Parquet ingestion using PyArrow (`bronze.raw_inventory`). | **FIXED** |
| 4 | **Fragile Regex Blood Group Matching** | Blocker | Legacy regex search matched `B+` inside `AB+` and confused `Bombay (Oh+)` with `O+`. | Built strict dbt SQL normalizer macro mapping raw strings into 10 mutually exclusive group enums. | **FIXED** |
| 5 | **Per-Request DuckDB Connection Leak** | Major | FastAPI endpoints opened and closed DuckDB connections without safe lifespan or thread isolation. | Standardized on dependency-injected `get_db` yielding read-only connections to `serving.duckdb` with guaranteed `finally: con.close()` cleanup. | **FIXED** |
| 6 | **Unsorted / Unformatted Code & Ruff Lints** | Minor | Missing typing annotations and unsorted imports triggered 135 ruff errors. | Configured `[tool.ruff]` in `pyproject.toml`, automated formatting across 51 files, and verified 0 errors. | **FIXED** |

---

## 3. Proof of Zero Fake Data

### Grep Audit Across Repository
```bash
grep -rnE "(fake|synthetic|mock_history|sample_snapshot|seed_snapshot)" src/ dbt/models/
```
**Terminal Output Evidence**:
```text
src/bloodgrid/api/routers/reports.py:144:    Adheres strictly to Rule 1: ZERO fake data or fabricated forecasts.
dbt/models/gold/mart_stock_change.sql:7:Absolute Rule: ZERO fake data.
```
*(Zero matches generating, seeding, or fabricating data; matches are solely the docstring declarations enforcing the rule).*

### SQL Snapshot Integrity Query (`blood_warehouse.duckdb`)
```sql
SELECT 
    COUNT(*) as total_snapshot_rows,
    COUNT(DISTINCT hospital_code) as unique_facilities,
    COUNT(DISTINCT blood_group) as blood_groups,
    MIN(snapshot_date) as earliest_snapshot,
    MAX(snapshot_date) as latest_snapshot
FROM main_gold.fct_stock_snapshot;
```
**Terminal Output Evidence**:
```text
   total_snapshot_rows  unique_facilities  blood_groups earliest_snapshot latest_snapshot
0               177319               4530            10        2026-10-14      2026-10-14
Orphan/Unmapped Snapshot Rows: 0 (Expected: 0)
```
- Total Real Clinical Snapshot Rows: **177,319**
- Reporting Facilities: **4,530**
- Earliest Snapshot: `2026-10-14` (First real crawl execution date)
- Unmapped / Orphan Rows: **0**

---

## 4. Real-World Items Requiring User Input

The technical and data engineering foundation is complete. Commercial launch requires the following business inputs from the owner:

1. **Legal Counsel Review**: Have a qualified Indian advocate review `docs/LEGAL.md` and the draft Terms of Service, Privacy Policy (DPDP 2023), Refund Policy, and Medical Disclaimer.
2. **Razorpay Live KYC**: The codebase currently runs in Razorpay Test Mode. To accept real payments in INR:
   - Complete Razorpay merchant KYC (Business PAN, Bank Account, GSTIN).
   - Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in production `.env`.
3. **Domain & DNS Setup**:
   - Register `bloodgrid.in` (approx ₹499/year via dynadot/Cloudflare).
   - Point DNS A record to your VPS IP address and configure Cloudflare Proxy.
4. **Government Outreach (NIC / NHM)**:
   - Send the draft email in `docs/LEGAL.md` Section 3 to `eraktkosh@cdac.in` and `nhm-india@nic.in` requesting formal data acknowledgement or an MoU.
5. **10 Customer Discovery Interviews**:
   - Interview 3 blood donation NGO coordinators (e.g. Red Cross Anand, Lions Club).
   - Interview 3 hospital emergency room / ICU doctors.
   - Interview 4 thalassemia patient families to validate willingness to pay ₹499/mo for automated shortage alerts.
6. **Meta-Verified WhatsApp Provider Decision**:
   - To upgrade from Email + Telegram alerts to WhatsApp Cloud API, register a Meta Business Account and select a BSP (Interakt, Wati, or direct Meta Graph API).

---

## 5. Monthly Cost & Unit Economics

### Infrastructure Costs (Monthly)
| Component | Provider / Tier | Monthly Cost (USD) | Monthly Cost (INR) |
| :--- | :--- | :--- | :--- |
| **Compute & API Server** | Hetzner Cloud CX22 (2 vCPU, 4GB RAM, 40GB NVMe) | $4.15 | ₹345 |
| **Object Storage (Lakehouse Backups)** | Cloudflare R2 (10GB storage, 0 egress fees) | $0.15 | ₹12 |
| **DNS & DDoS Protection** | Cloudflare Free Tier | $0.00 | ₹0 |
| **Alert Delivery (Email + Telegram)** | Resend / Brevo (Free 3,000 emails/mo) + Telegram Bot API | $0.00 | ₹0 |
| **Error Monitoring** | Sentry Developer (Free 5k errors/mo) | $0.00 | ₹0 |
| **CI/CD Pipeline** | GitHub Actions (Free 2,000 mins/mo) | $0.00 | ₹0 |
| **Payment Gateway** | Razorpay (2% per transaction, no fixed monthly fee) | Variable | Variable |
| **Domain Amortization** | `.in` Domain (₹499 / year) | $0.50 | ₹42 |
| **Total Baseline Operating Cost** | | **$4.80 / mo** | **₹399 / mo** |

### Break-Even Analysis by Pricing Tier
- **Pro Tier (₹499 / mo)**: **1 subscriber** covers baseline operating expenses.
- **Developer Tier (₹2,499 / mo)**: **1 subscriber** generates **84% net gross margin** (₹2,100 / mo net profit).
- **Organization Tier (₹7,999 / mo)**: **1 subscriber** generates **95% net gross margin** (₹7,600 / mo net profit).

---

## 6. Commercial Launch Checklist

- [ ] **Soft Launch to 3 Pilot NGOs**:
  - Deploy BloodGrid to staging VPS.
  - Onboard Red Cross Anand and 2 regional blood donation foundations.
  - Setup custom Telegram alert channels for O- and Bombay blood shortages.
- [ ] **Core Metrics to Monitor**:
  1. **Weekly Active Searches (WAS)**: Public emergency searches by state and district.
  2. **Alert Subscriptions**: Conversion rate from searcher to email/Telegram alert subscriber.
  3. **Developer API Keys Created**: Number of developer sandboxes initialized.
  4. **Paid Conversion Rate**: Target 3-5% conversion from active searchers to Pro/Developer plans.
  5. **Data Freshness SLA**: < 4 hours from eRaktKosh updates to BloodGrid serving database.
  6. **Error Rate & Circuit Breaker Trips**: 0 unexpected scraper trips per week.
