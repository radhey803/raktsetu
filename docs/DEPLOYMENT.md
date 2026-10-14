# BloodGrid: Production Deployment Guide & Infrastructure Architecture

**Author**: Senior Full-Stack & Infrastructure Architect  
**Target Environment**: Linux VPS (Ubuntu 22.04 / 24.04 LTS), Docker, Caddy v2, Cloudflare R2 / S3.

---

## 1. Hosting Architecture Overview

BloodGrid employs a decoupled **Analytical Engine + Application State** pattern:
- **Serving Analytical Warehouse**: DuckDB (`serving.duckdb`) mounted in read-only mode, serving sub-millisecond aggregate queries with zero database connection overhead.
- **Application State Database**: PostgreSQL (Users, API Keys, Alert Rules, Subscriptions, Audit Logs).
- **Static Assets & SPA**: Served directly via FastAPI / Caddy with Gzip and HTTP/2 compression.
- **Edge Reverse Proxy**: Caddy server providing automatic Let's Encrypt TLS/SSL certificates, security headers, and reverse proxying to `localhost:8000`.

```
 Internet (HTTPS 443)
       │
       ▼
 ┌───────────────┐
 │ Caddy Proxy   │ ── TLS Termination & HTTP/2
 └───────┬───────┘
         │ Reverse Proxy (127.0.0.1:8000)
         ▼
 ┌────────────────────────────────────────────────────────┐
 │ FastAPI Container (BloodGrid)                         │
 │  ├── /v1/ (Public API, Emergency Search, SEO Pages)   │
 │  ├── /web (Clean Health-Tech Static SPA)              │
 │  │                                                     │
 │  ├── Read-Only Analytics ──► serving.duckdb (local)    │
 │  └── App State / Auth    ──► PostgreSQL (port 5432)   │
 └────────────────────────────────────────────────────────┘
```

---

## 2. Recommended Low-Cost Hosting Option: Hetzner / DigitalOcean VPS + Caddy

### Why a Small VPS ($4 - $6 / month)?
- **Predictable Cost**: $4.50/mo on Hetzner Cloud (CPX11: 2 vCPU, 2 GB RAM, 40 GB NVMe) or $6/mo on DigitalOcean.
- **No Cold Starts**: Dedicated 24/7 uptime without container sleep delays.
- **Fast Local Disk I/O**: DuckDB analytical vectorization executes at NVMe disk bus speed (< 2ms query latency).

---

## 3. Step-by-Step Production Deployment

### Step 1: Server Provisioning & Initial Hardening
```bash
# Update and install Docker + Caddy
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl git ufw fail2ban ca-certificates

# Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy

# Firewall Configuration (SSH, HTTP, HTTPS only)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Step 2: Clone Codebase & Configure Environment
```bash
cd /opt
sudo git clone https://github.com/radhey803/eraktkosh-blood-lakehouse.git bloodgrid
cd bloodgrid
sudo chown -R $USER:$USER /opt/bloodgrid

# Configure Production Secrets
cp .env.example .env
nano .env
# Set BLOODGRID_ENV=production, strong JWT_SECRET, and CARTO_API_KEY
```

### Step 3: Run Initial Data Pipeline to Generate `serving.duckdb`
```bash
# Build and execute the full pipeline
make setup
uv run bloodgrid all --force
```

### Step 4: Start Production Services via Docker Compose
```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/api/health
```

### Step 5: Configure Caddy Reverse Proxy & Automatic SSL
Edit `/etc/caddy/Caddyfile`:
```caddy
bloodgrid.in, www.bloodgrid.in {
    encode gzip zstd

    # Security Headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(self), camera=(), microphone=()"
    }

    # Reverse proxy to FastAPI application
    reverse_proxy 127.0.0.1:8000
}
```
Reload Caddy:
```bash
sudo systemctl reload caddy
```

---

## 4. Domain & DNS Configuration

| Type | Name | Content / Target | TTL | Proxy Status |
|---|---|---|---|---|
| `A` | `@` | `YOUR_SERVER_IP` | Auto | DNS Only / Cloudflare Proxied |
| `CNAME` | `www` | `bloodgrid.in` | Auto | DNS Only / Cloudflare Proxied |
| `TXT` | `@` | `v=spf1 include:_spf.mx.cloudflare.net ~all` | Auto | DNS Only (for transactional alerts) |

---

## 5. Monthly Cost Breakdown & Break-Even Analysis

| Service | Provider | Specifications | Monthly Cost (USD) | Monthly Cost (INR) |
|---|---|---|---|---|
| **VPS Compute** | Hetzner Cloud (CPX11) | 2 vCPU, 2 GB RAM, 40 GB NVMe | $4.50 | ₹375 |
| **Domain Name** | Cloudflare Registrar | `.in` or `.org` domain | $0.80 | ₹65 |
| **Object Storage Backups** | Cloudflare R2 | 10 GB free tier | $0.00 | ₹0 |
| **SSL Certificates** | Let's Encrypt / Caddy | Automated Wildcard / SAN | $0.00 | ₹0 |
| **Scheduled Ingestion** | GitHub Actions | 2,000 free runner mins/mo | $0.00 | ₹0 |
| **Transactional Email** | SendGrid / Resend | 100 free emails/day | $0.00 | ₹0 |
| **Total Operating Cost** | | | **~$5.30 / mo** | **~₹440 / month** |

### Break-Even Threshold:
- At **₹299/mo** for Pro plan: **Only 2 paid subscribers** required to achieve 100% operational profitability.
- At **₹999/mo** for API Developer tier: **1 subscriber** yields immediate net positive margins.
