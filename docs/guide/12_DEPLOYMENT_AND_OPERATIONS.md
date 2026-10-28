# 12 · Deployment & Operations

**What you will learn**
- How to run the app in Docker
- How to put it online with HTTPS (VPS + Caddy)
- How the scheduled pipeline works
- Day-to-day monitoring, backups and releases

---

## 1. Docker

### The Dockerfile (2 stages)
1. **builder:** `python:3.12-slim` + build tools + uv. It runs `uv sync --frozen --no-dev` into `.venv`.
2. **runner:** a clean `python:3.12-slim`. It copies `.venv`, `src/`, `dbt/`, `web/` and the two data JSON
   files, then:
   - runs as a **non-root** user (`bloodgrid`);
   - has a `HEALTHCHECK` that runs `curl -f http://localhost:8000/healthz` every 30 s;
   - starts with `uvicorn bloodlake.api.main:app --host 0.0.0.0 --port 8000`.

Two stages keep the final image small: the compilers stay behind in the builder.

### docker-compose.yml
```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
      - ./blood_warehouse.duckdb:/app/blood_warehouse.duckdb:ro
      - ./serving.duckdb:/app/serving.duckdb:ro
    restart: unless-stopped
```
The databases are mounted **read-only** (`:ro`). The container only *serves* data. The pipeline runs on
the host (or in CI), and the container sees the new `serving.duckdb` straight away.

```bash
docker compose up -d --build     # start in the background
docker compose logs -f api       # follow the logs
docker compose ps                # health status
docker compose down              # stop
```

> If the file is missing on the host, Docker creates an empty **folder** with that name. Run the
> pipeline (or `make demo-offline`) **before** the first `docker compose up`.

---

## 2. Going live: VPS + Caddy ([ADR-005](../adr/ADR-005-low-cost-vps-caddy-deployment.md))

**Why:** a small VPS (about $4/month) is enough. **Caddy** is a web server that gets and renews HTTPS
certificates by itself. HTTPS is also **required** for "Near me" and for installing the PWA.

Steps on a fresh Ubuntu VPS:
```bash
# 1. basics
sudo apt update && sudo apt install -y git make curl docker.io docker-compose-plugin caddy
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. code + data
git clone <repo> /opt/raktsetu && cd /opt/raktsetu
uv sync && make pipeline

# 3. app
docker compose up -d --build

# 4. HTTPS: point your domain's DNS A-record to the VPS IP, then:
echo 'raktsetu.example.in {
    reverse_proxy localhost:8000
}' | sudo tee /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Open `https://raktsetu.example.in`. Caddy has fetched the certificate automatically.

### Scheduling the pipeline on the VPS
```bash
crontab -e
# every 6 hours, at minute 10
10 */6 * * * cd /opt/raktsetu && /root/.local/bin/uv run bloodlake all >> logs/pipeline.log 2>&1
```
(Without `--force`, the 6 h guard protects eRaktKosh if cron runs twice by mistake.)

---

## 3. GitHub Actions

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `ci.yml` | push / PR to `main` | lint, tests, dbt build, pip-audit ([11 §8](11_TESTING.md#8-ci-github-actions)) |
| `pipeline.yml` | cron `0 0,6,12,18 * * *` (UTC) + manual | `uv run bloodlake all --force` |
| `deploy.yml` | push to `main` that changes `src/`, `web/`, `Dockerfile` | builds the Docker image (a check that the build works) |

> **Note:** `pipeline.yml` runs on a temporary GitHub machine. Its database disappears when the job
> ends, unless you add a step that saves it, for example
> `actions/upload-artifact`, an `scp` to the VPS, or S3/R2. For production, the **VPS cron** above is simpler.

Manual run: GitHub → Actions → *Scheduled Ingestion* → **Run workflow**.

---

## 4. Daily operations checklist

| Check | How | Healthy |
|-------|-----|---------|
| Is the site up? | `curl -s https://<domain>/healthz` | `"status":"healthy"` |
| Is the data fresh? | Data Health panel, or `/api/v1/health/dashboard` | `sync_age_hours` < 12 |
| Did the last runs work? | `make status` | Recent `SUCCESS` |
| Bank count stable? | `make status` → Facilities | About 4,700 (± a few %) |
| dbt tests | Data Health → dbt tests | `PASSING` |
| Disk | `du -sh data/landing *.duckdb` | Landing grows about 1–2 MB per run |

---

## 5. Backups and clean-up

- **The most important thing to back up is `data/landing/`.** Everything else can be rebuilt from it
  (see [05 §9](05_DATA_PIPELINE.md#9-re-running-and-back-filling)).
  ```bash
  tar czf backup_landing_$(date +%F).tgz data/landing
  ```
- Keep a known-good offline copy: `cp serving.duckdb demo/fallback_lakehouse.duckdb`.
- Old landing partitions can be archived, for example everything older than 90 days:
  `find data/landing -maxdepth 1 -name 'dt=*' -mtime +90`.

---

## 6. Releasing a change

1. Create a branch, make the change, and run `make lint test` (plus the e2e check for UI changes).
2. If you changed the **service worker logic** (`sw.js`), raise `CACHE_NAME`/`DATA_CACHE_NAME` (`v4` → `v5`).
3. If you changed dbt models, run `make transform publish`.
4. Open a PR and merge it once CI is green.
5. On the VPS: `git pull && docker compose up -d --build`.
6. Check `/healthz` and open the site on a phone.

**Rollback:** `git checkout <previous-tag> && docker compose up -d --build`. For data, run
`cp demo/fallback_lakehouse.duckdb serving.duckdb`.

---

Next: [13 · Troubleshooting →](13_TROUBLESHOOTING.md)
