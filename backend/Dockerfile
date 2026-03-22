# =============================================================================
# Pilot Space Backend - Production Dockerfile
# =============================================================================
# Multi-stage build for minimal, secure production image
# Base: python:3.12-slim-bookworm
# Package Manager: uv (astral.sh)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and create virtual environment
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # uv configuration
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv - fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock README.md ./

# Create virtual environment and install production dependencies only
# --frozen ensures uv.lock is used exactly as-is
# --no-dev excludes development dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code
COPY src/ ./src/

# Install the project itself
RUN uv sync --frozen --no-dev

# Strip unnecessary files from venv to reduce image size
RUN find .venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null; \
    find .venv -type d -name "test" -exec rm -rf {} + 2>/dev/null; \
    find .venv -name "*.pyi" -delete 2>/dev/null; \
    true

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Labels for container metadata
LABEL org.opencontainers.image.title="Pilot Space Backend" \
      org.opencontainers.image.description="AI-Augmented SDLC Platform API" \
      org.opencontainers.image.vendor="Pilot Space" \
      org.opencontainers.image.source="https://github.com/pilotspace/pilot-space"

# Security: Run as non-root user
# Create user and group before copying files
RUN groupadd --gid 1000 pilot \
    && useradd --uid 1000 --gid pilot --shell /bin/bash --create-home pilot

# Runtime environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Virtual environment path
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    # Application settings
    APP_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    # Uvicorn settings
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_WORKERS=1 \
    UVICORN_LOG_LEVEL=info

# Install runtime dependencies (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=pilot:pilot /app/.venv /app/.venv

# Copy application source code and alembic config
COPY --chown=pilot:pilot src/ ./src/
COPY --chown=pilot:pilot alembic.ini ./
COPY --chown=pilot:pilot alembic/ ./alembic/

# Switch to non-root user
USER pilot

# Expose the application port
EXPOSE 8000

# Health check configuration
# Checks the /health endpoint every 30 seconds
# Allows 5 seconds for startup, 10 second timeout, 3 retries before unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: Run uvicorn with production settings
# - host: Bind to all interfaces for container networking
# - port: Default 8000, configurable via environment
# - workers: Single worker by default, scale via orchestrator (K8s, ECS)
# - log-level: Info for production observability
# - proxy-headers: Trust X-Forwarded-* headers from reverse proxy
# - forwarded-allow-ips: Allow forwarded headers from any IP (handled by ingress)
CMD ["uvicorn", "pilot_space.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
