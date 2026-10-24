# =============================================================================
# Phase 9: Production Dockerfile — Enterprise Pharma Data Platform
# =============================================================================
# Multi-purpose, production-grade container image supporting:
#   - Pipeline Orchestrator (batch runner)
#   - FastAPI Clinical Data Serving Layer (REST service)
#   - Streamlit Clinical Intelligence Dashboard (Web UI)
# =============================================================================

FROM python:3.11-slim-bullseye AS base

# Environment variables to optimize Python runtime in container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENV=production \
    POSTGRES_HOST=postgres \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=pharma_clinical_db \
    POSTGRES_USER=pharma_admin \
    POSTGRES_PASSWORD=pharma_pass

# Install system dependencies needed for compiling psycopg2 and pyarrow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python packages
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application source code, configuration, tests, and SQL modules
COPY config/ ./config/
COPY src/ ./src/
COPY sql/ ./sql/
COPY tests/ ./tests/
COPY pytest.ini .
COPY README.md .

# Create directory structure for runtime data and logs
RUN mkdir -p data/raw data/silver data/gold logs

# Default entrypoint runs the full orchestrated pipeline
CMD ["python", "src/orchestrator.py"]
