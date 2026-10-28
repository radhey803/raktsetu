# 11 · Testing

**What you will learn**
- The kinds of tests in this project, and why each one exists
- How to run each kind
- What the fixture database is
- How to write a new test
- How CI runs the tests

---

## 1. The testing pyramid

```text
            ▲  few, slow, realistic
           ╱ ╲     E2E (Playwright): a robot clicks through the real site
          ╱───╲    Data tests (dbt): rules on real tables
         ╱─────╲   Integration (pytest + TestClient): API + database
        ╱───────╲  Unit (pytest): one function, no network or DB
            ▼  many, fast
```

| Kind | Where | Count | Command | Needs |
|------|-------|-------|---------|-------|
| Unit + integration | `tests/unit`, `tests/integration` | 98 | `make test` | nothing (uses a fixture DB) |
| Lint / format | whole repo | — | `make lint` | — |
| dbt data tests | `dbt/models/*/schema.yml` | 37 | `make dbt-test` | `blood_warehouse.duckdb` |
| Browser E2E | `tests/e2e/e2e_check.py` | 146 checks | `uv run python tests/e2e/e2e_check.py` | `make run` in another terminal + Chromium |

---

## 2. What each test file covers

| File | Tests |
|------|-------|
| `test_reliability_score.py` | Score boundaries (day 1 → 50, day 2 → 35, …), labels, phone check |
| `test_emergency_mode.py` | Compatibility (O- only gets O-, AB+ gets all), Bombay, plasma rules |
| `test_normalizer.py` | Blood group spelling normalisation |
| `test_scraper.py` | Retry/backoff, 429 handling, circuit breaker (fake HTTP) |
| `test_landing_pipeline.py` | Parquet landing: immutability, manifest, SHA-256 |
| `test_warehouse_loader.py` | Bronze load + **idempotency** |
| `test_pipeline_cli.py` | CLI commands, the interval guard, the anomaly gate |
| `test_stock_change_risk.py` | `Falling` / `Depleted` / `SUDDEN_DROP_TO_ZERO` |
| `test_geocoding_service.py` | Haversine, district lookup, offsets |
| `test_csv_export.py` | BOM, header first, phone/email split, formula guard |
| `test_schemas.py` | Pydantic models |
| `integration/test_api.py` | Endpoints against the real `serving.duckdb` |
| `integration/test_fixture_api.py` | Endpoints against the **synthetic** fixture DB |

---

## 3. Running the tests

```bash
make test                                   # everything, with coverage
uv run pytest tests/unit -q                 # unit tests only, short output
uv run pytest tests/unit/test_csv_export.py # one file
uv run pytest -k emergency                  # tests whose name contains "emergency"
uv run pytest -x --pdb                      # stop at the first failure and open the debugger
```
Reading the output:
- `.` = passed
- `F` = failed (the assert and the values are shown)
- `E` = an error while setting up the test

The coverage report lists the lines that no test runs (`Missing`).

---

## 4. The fixture database

`tests/fixtures/generate_fixture_db.py` builds a **tiny fake** DuckDB
(`tests/fixtures/fixture_lakehouse.duckdb`) with a few banks and known numbers. The integration tests
swap the real database for it:

```python
app.dependency_overrides[get_db_session] = lambda: fixture_db_con
response = client.get("/api/v1/meta")
```
**Why:** the tests then give the same result on every machine and in CI, without internet access and
without real data.

---

## 5. Writing a new test

**Unit test example:** add this to `tests/unit/test_reliability_score.py`.
```python
def test_old_bank_with_phone_is_low():
    score, label = calculate_reliability_score(
        days_since_update=20, phone="9876543210", distinct_components_count=1)
    assert score == 0 + 25 + 15
    assert label == "Medium"      # 40 is the lowest Medium score
```

**API test example:**
```python
from fastapi.testclient import TestClient
from bloodlake.api.main import app
client = TestClient(app)

def test_emergency_unknown_group_is_422():
    r = client.get("/api/v1/emergency", params={"patient_blood_group": "XYZ"})
    assert r.status_code == 422
```

Rules of thumb:
- One behaviour per test.
- Name the test after what it proves.
- Test the edges: 0, 1, the exact boundary value, None, and negative numbers.

---

## 6. dbt tests

They are declared in `schema.yml`:
```yaml
- name: hospital_code
  tests: [not_null, unique]
- name: blood_group
  tests:
    - accepted_values:
        values: ['A+','A-','B+','B-','AB+','AB-','O+','O-','Bombay (Oh+)','Bombay (Oh-)']
```
If a test fails, dbt prints which one. To see the bad rows:
```bash
uv run dbt test --project-dir dbt --profiles-dir dbt --store-failures
# then query the dbt_test__audit tables in blood_warehouse.duckdb
```

---

## 7. The E2E browser check

`tests/e2e/e2e_check.py` uses Playwright to open the site in Chromium at **desktop (1366 px)** and
**mobile (390 px)** sizes, then:
- checks the KPIs, every nav link and the disclaimer;
- runs state → district → search, the blood group filter, an empty search and reset;
- checks sorting, pagination, `tel:` links, the trend modal and the trust modal;
- checks the map markers and popups;
- runs Emergency Mode for every group (and checks the Rh-negative and Bombay alerts);
- checks the rare blood and shortage filters, and both CSV downloads;
- runs 5 donor eligibility cases (including a future date);
- checks the Data Health panel;
- fails on **any console error, failed request or unexpected alert**;
- goes **offline** and checks that the app shell still loads.

```bash
make run                                   # terminal 1
uv run python tests/e2e/e2e_check.py       # terminal 2 → "PASS 146  FAIL 0"
```

---

## 8. CI (GitHub Actions)

`.github/workflows/ci.yml` runs on every push and pull request to `main`:
1. `uv sync --dev`
2. `ruff check` + `ruff format --check`
3. `pytest` with coverage
4. `dbt build` (models + tests)
5. `pip-audit` (checks dependencies for known security problems)

A red ❌ on GitHub means one of these failed. Click the job to read the log, run the same command on
your computer, fix the problem, and push again.

---

Next: [12 · Deployment & operations →](12_DEPLOYMENT_AND_OPERATIONS.md)
