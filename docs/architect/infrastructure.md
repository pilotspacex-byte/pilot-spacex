# Infrastructure Architecture

**Status**: Adopted (Session 2026-01-22)
**Platform**: Supabase Unified Platform
**Containerization**: Docker + Docker Compose

---

## Service Architecture

Pilot Space uses **Supabase** as the unified backend platform, reducing infrastructure from 10+ services to 3 core services.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PILOT SPACE INFRASTRUCTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                          FRONTEND (Next.js 14)                       │    │
│  │    ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │    │
│  │    │Note Canvas │  │Issue Board │  │  AI Panel  │  │  Settings  │   │    │
│  │    │(TipTap +   │  │(Kanban +   │  │(SSE Stream)│  │   (BYOK)   │   │    │
│  │    │ Realtime)  │  │ Realtime)  │  │            │  │            │   │    │
│  │    └────────────┘  └────────────┘  └────────────┘  └────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      FASTAPI BACKEND (:8000)                         │    │
│  │    ┌────────────────────────────────────────────────────────────┐   │    │
│  │    │ Application Layer (Use Cases, Domain Services, CQRS-lite) │   │    │
│  │    │ AI Layer (Claude Agent SDK, Providers, Agents)            │   │    │
│  │    └────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      SUPABASE PLATFORM                               │    │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │    │
│  │   │PostgreSQL 16 │  │ Auth (GoTrue)│  │   Storage (S3-compat)    │  │    │
│  │   │  + pgvector  │  │  + JWT + MFA │  │   + CDN + Transforms     │  │    │
│  │   │  + RLS       │  │  + SAML SSO  │  │                          │  │    │
│  │   └──────────────┘  └──────────────┘  └──────────────────────────┘  │    │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │    │
│  │   │   Realtime   │  │Queues (pgmq) │  │   pgBouncer (Pooling)    │  │    │
│  │   │  (Phoenix)   │  │ + pg_cron    │  │                          │  │    │
│  │   └──────────────┘  └──────────────┘  └──────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    EXTERNAL SERVICES                                  │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │   │   Redis    │  │Meilisearch │  │   GitHub   │  │   Slack    │    │   │
│  │   │  (Cache)   │  │  (Search)  │  │    App     │  │    Bot     │    │   │
│  │   │   :6379    │  │   :7700    │  │            │  │            │    │   │
│  │   └────────────┘  └────────────┘  └────────────┘  └────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Docker Compose Configuration

### Development Environment

```yaml
# infra/docker/docker-compose.yml
version: '3.9'

services:
  # ============================================
  # SUPABASE LOCAL DEVELOPMENT
  # ============================================
  # Note: Use `supabase start` for local development
  # This compose file is for custom deployments

  # ============================================
  # APPLICATION SERVICES
  # ============================================

  backend:
    build:
      context: ../../backend
      dockerfile: ../infra/docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      # Supabase Connection
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - SUPABASE_DB_URL=${SUPABASE_DB_URL}
      # Redis (kept for caching)
      - REDIS_URL=redis://redis:6379/0
      # Meilisearch
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_API_KEY=${MEILISEARCH_API_KEY}
      # AI Providers (BYOK)
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      # Debug
      - DEBUG=true
    volumes:
      - ../../backend/src:/app/src:ro
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ../../frontend
      dockerfile: ../infra/docker/Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
      - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
    volumes:
      - ../../frontend/src:/app/src:ro
    depends_on:
      - backend

  # ============================================
  # EXTERNAL SERVICES (Still Required)
  # ============================================

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  meilisearch:
    image: getmeili/meilisearch:v1.6
    ports:
      - "7700:7700"
    environment:
      - MEILI_MASTER_KEY=${MEILISEARCH_API_KEY}
      - MEILI_ENV=development
    volumes:
      - meilisearch_data:/meili_data

volumes:
  redis_data:
  meilisearch_data:

networks:
  default:
    name: pilot-space-network
```

### Supabase Local Development

For local development, use the Supabase CLI instead of Docker Compose for database services:

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Start local Supabase (PostgreSQL, Auth, Storage, Realtime, Queues)
cd infra/supabase
supabase start

# Output shows all local URLs:
# - API URL: http://localhost:54321
# - GraphQL URL: http://localhost:54321/graphql/v1
# - Database URL: postgresql://postgres:postgres@localhost:54322/postgres
# - Studio URL: http://localhost:54323
# - Inbucket URL: http://localhost:54324 (email testing)
# - JWT secret: super-secret-jwt-token-with-at-least-32-characters-long
# - anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# - service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Dockerfiles

### Backend Dockerfile

```dockerfile
# infra/docker/Dockerfile.backend
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/
COPY alembic.ini ./

# Set Python path
ENV PYTHONPATH=/app/src

# Development stage
FROM base AS development
RUN uv sync --frozen
CMD ["uv", "run", "uvicorn", "pilot_space.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production
CMD ["uv", "run", "uvicorn", "pilot_space.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile

```dockerfile
# infra/docker/Dockerfile.frontend
FROM node:20-alpine AS base

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9 --activate

# Copy dependency files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Development stage
FROM base AS development
CMD ["pnpm", "dev"]

# Build stage
FROM base AS builder
RUN pnpm build

# Production stage
FROM node:20-alpine AS production
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9 --activate

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

ENV NODE_ENV=production
ENV PORT=3000

CMD ["node", "server.js"]
```

---

## Environment Configuration

### Development Environment

```bash
# .env.example

# ============================================
# SUPABASE (Primary Platform)
# ============================================
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_DB_URL=postgresql+asyncpg://postgres:postgres@localhost:54322/postgres

# ============================================
# REDIS (Session + AI Cache)
# ============================================
REDIS_URL=redis://localhost:6379/0

# ============================================
# MEILISEARCH (Typo-Tolerant Search)
# ============================================
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your-master-key

# ============================================
# AI PROVIDERS (BYOK - User Provides Keys)
# ============================================
# These are for development/testing only
# In production, users configure their own keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# ============================================
# FRONTEND
# ============================================
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ============================================
# DEBUG
# ============================================
DEBUG=true
```

---

## Supabase Background Jobs

Pilot Space uses **Supabase Queues (pgmq)** and **pg_cron** for background tasks, replacing Celery + RabbitMQ.

### Queue Configuration

```sql
-- Create queue table for AI tasks
CREATE TABLE ai_task_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_type text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  priority integer DEFAULT 0,
  retry_count integer DEFAULT 0,
  max_retries integer DEFAULT 3,
  created_at timestamptz DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz,
  error text,
  result jsonb
);

-- Efficient dequeue index
CREATE INDEX idx_ai_task_queue_status
  ON ai_task_queue(status, priority DESC, created_at);

-- Enable RLS (service role only)
ALTER TABLE ai_task_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access"
  ON ai_task_queue
  USING (auth.role() = 'service_role');
```

### Scheduled Tasks with pg_cron

```sql
-- Schedule embedding indexing daily at 2 AM
SELECT cron.schedule(
  'index-embeddings-daily',
  '0 2 * * *',
  $$
    SELECT net.http_post(
      url := 'https://your-project.supabase.co/functions/v1/index-embeddings',
      headers := jsonb_build_object(
        'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key')
      )
    );
  $$
);

-- Process AI queue every minute
SELECT cron.schedule(
  'process-ai-queue',
  '* * * * *',
  $$
    SELECT net.http_post(
      url := 'https://your-project.supabase.co/functions/v1/process-ai-tasks',
      headers := jsonb_build_object(
        'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key')
      )
    );
  $$
);

-- Cleanup old completed jobs weekly
SELECT cron.schedule(
  'cleanup-old-jobs',
  '0 3 * * 0',
  $$
    DELETE FROM ai_task_queue
    WHERE status = 'completed'
    AND completed_at < now() - interval '7 days';
  $$
);
```

### Task Types

| Task | Queue Priority | Timeout | Use Case |
|------|---------------|---------|----------|
| `ghost_text` | 10 (high) | 5s | Real-time text suggestions |
| `pr_review` | 5 (medium) | 10m | GitHub PR analysis |
| `ai_context` | 5 (medium) | 5m | Issue context aggregation |
| `embeddings` | 1 (low) | 30m | Batch vector indexing |

---

## Authentication Flow

Pilot Space uses **Supabase Auth (GoTrue)** with Row-Level Security.

```
USER              FRONTEND                 BACKEND              SUPABASE
  │                  │                        │                    │
  ├─ login ─────────>│                        │                    │
  │                  ├─ supabase.auth.signIn ─────────────────────>│
  │                  │<─ JWT + Refresh Token ──────────────────────┤
  │<─ session ───────┤                        │                    │
  │                  │                        │                    │
  │ API call         │                        │                    │
  ├─────────────────>│ (with JWT in header)   │                    │
  │                  ├─ GET /api/v1/issues ──>│                    │
  │                  │                        ├─ Validate JWT ────>│
  │                  │                        │<─ user context ────┤
  │                  │                        ├─ Query with RLS ──>│
  │                  │                        │   (auto-filtered)  │
  │                  │                        │<─ rows ────────────┤
  │<─ results ───────┤<─ JSON response ───────┤                    │
```

### Backend JWT Validation

```python
# api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from supabase import Client

security = HTTPBearer()

async def get_current_user(
    credentials = Depends(security),
    supabase: Client = Depends(get_supabase_client),
):
    """Validate Supabase JWT and return user."""
    try:
        user = supabase.auth.get_user(credentials.credentials)
        return user.user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
```

---

## Health Checks

### Backend Health Endpoint

```python
# backend/src/pilot_space/api/v1/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
):
    """Health check for container orchestration."""
    checks = {}

    # Supabase Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    # Redis check
    try:
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"

    all_healthy = all(v == "healthy" for v in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
    }

@router.get("/ready")
async def readiness_check():
    """Readiness check for load balancer."""
    return {"status": "ready"}
```

---

## Production Deployment

### Supabase Managed (Recommended)

```bash
# Create production project at supabase.com
# Configure environment variables in hosting platform (Vercel, Railway, etc.)

# Backend deployment
docker build -t pilot-space-backend:latest --target production .
docker push your-registry/pilot-space-backend:latest

# Frontend deployment (Vercel recommended)
vercel deploy --prod
```

### Self-Hosted Supabase

```bash
# Clone Supabase self-hosted setup
git clone https://github.com/supabase/supabase.git
cd supabase/docker

# Configure environment
cp .env.example .env
# Edit .env with production values

# Start all services
docker compose up -d
```

### Scaling Guidelines

| Service | Scaling Strategy | Trigger |
|---------|-----------------|---------|
| FastAPI Backend | Horizontal (pods) | CPU > 70%, p95 latency > 400ms |
| Next.js Frontend | Horizontal (pods) | CPU > 70% |
| Supabase | Upgrade tier / Add replicas | Connections > 80% |
| Redis | Cluster mode | Memory > 80% |

---

## Security Checklist

- [ ] Enable TLS for all services
- [ ] Use Supabase Vault for secrets
- [ ] Configure RLS policies for all tables
- [ ] Enable audit logging
- [ ] Set up WAF rules (if using CDN)
- [ ] Configure rate limiting (1000 req/min standard, 100 req/min AI)
- [ ] Enable database encryption at rest
- [ ] Rotate API keys regularly

---

## Related Documents

- [Supabase Integration Details](./supabase-integration.md) - Comprehensive Supabase patterns
- [Backend Architecture](./backend-architecture.md) - Service architecture details
- [RLS Patterns](./rls-patterns.md) - Row-Level Security policies (TODO)
- [Project Structure](./project-structure.md) - Directory layout
- [Quickstart](../../specs/001-pilot-space-mvp/quickstart.md) - Development setup
