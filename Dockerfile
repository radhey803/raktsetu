# ==============================================================================
# Multi-stage production Dockerfile for BloodGrid
# ==============================================================================

# Stage 1: Build & dependency resolution
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for rapid deterministic dependency installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Minimal runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH"

# Install curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user for secure execution
RUN groupadd -r bloodgrid && useradd -r -g bloodgrid -s /bin/false -d /app bloodgrid

# Copy installed venv from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source, dbt models, and frontend
COPY src/ /app/src/
COPY dbt/ /app/dbt/
COPY web/ /app/web/
COPY data/eraktkosh_all_metadata.json data/medical_rules.json /app/data/
COPY pyproject.toml README.md /app/

# Create runtime directories with appropriate permissions
RUN mkdir -p /app/data/landing /app/logs \
    && chown -R bloodgrid:bloodgrid /app

USER bloodgrid

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "bloodlake.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
