# ADR-005: Low-Cost Production Deployment Architecture — Hetzner VPS + Caddy Reverse Proxy

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Senior Full-Stack Engineer, Product Lead

---

## Context & Problem Statement
BloodGrid is an early-stage commercial product targeted at Indian blood donation NGOs, hospital networks, and health-tech developers. The deployment architecture must:
1. Deliver sub-20ms TTFB across Indian metropolitan regions (Mumbai, Delhi, Bengaluru, Ahmedabad).
2. Automate HTTPS/TLS certificate management without manual renew crons.
3. Keep operational expenditures under $6/month to ensure unit economics break even with just 2 Pro subscribers (₹499/mo).

Options evaluated:
- **AWS ECS + ALB + RDS**: High operational reliability, but baseline cost > $65/month.
- **Fly.io / Railway**: Excellent developer experience; pricing starts at ~$10-15/month for persistent volume + database.
- **Hetzner Cloud CX22 / Small VPS + Caddy**: €3.79 (~$4.15/month) + Cloudflare DNS ($0) + Cloudflare R2 ($0).

---

## Decision
We selected **Hetzner Cloud VPS (CX22: 2 vCPU, 4GB RAM, 40GB NVMe) with Caddy v2**:
- **Caddy Web Server**: Reverse proxies traffic to Uvicorn on port 8000, handles automatic Let's Encrypt / ZeroSSL TLS certificates, enforces HTTP/3 (QUIC), and compresses static assets with zstd/gzip.
- **Docker Compose**: Orchestrates `bloodgrid-api` and optional stateful Postgres on a private Docker bridge network.
- **Cloudflare R2**: Stores immutable Parquet snapshots and daily database backups with zero egress fees.

---

## Consequences
- **Positive**:
  - Total monthly operating expenditure: **$5.30 / month** (₹440 / month).
  - Break-even point reached with **1 Developer subscription** or **2 Pro subscriptions**.
  - High performance: NVMe storage gives DuckDB queries < 2ms latency on local disk.
- **Negative**:
  - Requires standard Linux server administration (UFW firewall rules, SSH keys, unattended security upgrades).
