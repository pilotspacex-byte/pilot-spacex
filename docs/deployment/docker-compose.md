# Docker Compose Deployment

This guide walks through deploying Pilot Space from scratch using Docker Compose. After following these steps, you will have the full application stack running with a single command.

## Prerequisites

- **Docker 24+** with Docker Compose v2 — ships with Docker Desktop 4.x+. Verify:
  ```bash
  docker --version        # Docker version 24.x or higher
  docker compose version  # Docker Compose version v2.x or higher
  ```
- **8 GB RAM minimum** (16 GB recommended — Postgres + Meilisearch + backend are memory-intensive)
- **20 GB disk space** (Docker images + database volumes)
- **Linux or macOS** (Windows: use WSL2 with Docker Desktop)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-org/pilot-space.git
cd pilot-space
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in the **required** values (marked `CHANGE_ME`):

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | Strong password for PostgreSQL |
| `JWT_SECRET` | 32+ character secret (`openssl rand -hex 32`) |
| `SUPABASE_ANON_KEY` | Supabase anon JWT (see note below) |
| `SUPABASE_SERVICE_KEY` | Supabase service role JWT (keep secret) |
| `MEILI_MASTER_KEY` | Meilisearch master key (`openssl rand -hex 16`) |

> **Supabase JWT keys**: The anon and service role keys are JWTs signed with your `JWT_SECRET`. For local development, you can use the [Supabase self-hosting key generator](https://supabase.com/docs/guides/self-hosting#api-keys) or generate them with the `supabase` CLI.

### 3. Start all services

```bash
docker compose up -d
```

Docker pulls images and starts services in dependency order. Initial startup takes 2-3 minutes on first run (image downloads). Check progress:

```bash
docker compose ps
```

All services should show `healthy` status before proceeding.

### 4. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

---

## Service Map

| Service | Host Port | Purpose |
|---|---|---|
| `postgres` | 5432 | Primary database (PostgreSQL 16, pgvector enabled) |
| `redis` | 6379 | Cache + session storage + rate limiting |
| `meilisearch` | 7700 | Full-text and typo-tolerant search |
| `supabase-auth` | 9999 | Auth service (GoTrue — handles JWTs, OAuth, MFA) |
| `supabase-kong` | 18000 | Supabase API gateway (routes /auth/v1/*) |
| `backend` | 8000 | FastAPI application (Python) |
| `frontend` | 3000 | Next.js application (React) |

### Optional services (profiles)

| Service | Profile | Host Port | Purpose |
|---|---|---|---|
| `supabase-studio` | `dev` | 54323 | Supabase admin dashboard |
| `nginx` | `production` | 80, 443 | Reverse proxy + TLS termination |

Start with optional services:

```bash
# Development tools (adds Supabase Studio)
docker compose --profile dev up -d

# Production (adds nginx TLS proxy)
docker compose --profile production up -d
```

---

## First-Run Initialization

After `docker compose up -d`, run these once:

```bash
# Apply all Alembic database migrations
docker compose exec backend alembic upgrade head

# Verify migrations are current
docker compose exec backend alembic check
```

---

## Health Verification

Check that all services are running correctly:

```bash
# Backend liveness
curl -f http://localhost:8000/health
# Expected: {"status": "ok"} or similar

# Backend readiness (includes DB and Redis checks)
curl -f http://localhost:8000/health/ready

# Meilisearch
curl -f http://localhost:7700/health
# Expected: {"status": "available"}

# Supabase Kong gateway
curl -f http://localhost:18000/auth/v1/health
# Expected: {"code": 200, "description": "Auth service is running"}
```

Access the application:

- **Frontend**: http://localhost:3000
- **Backend API docs**: http://localhost:8000/docs
- **Supabase Studio** (if `--profile dev`): http://localhost:54323

---

## Production Deployment

### 1. Prepare TLS certificates

Place your certificates in `infra/nginx/certs/`:

```
infra/nginx/certs/
  server.crt    # Full certificate chain (PEM)
  server.key    # Private key (PEM, no passphrase)
```

For a quick self-signed certificate (development or staging only):

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout infra/nginx/certs/server.key \
  -out infra/nginx/certs/server.crt \
  -subj "/CN=your-domain.com"
```

### 2. Update environment for production

In your `.env` file:

```bash
APP_ENV=production
DEBUG=false
GOTRUE_DISABLE_SIGNUP=true          # Invite-only
GOTRUE_MAILER_AUTOCONFIRM=false     # Require email verification

# Update to your actual domain
SUPABASE_URL=https://your-domain.com
NEXT_PUBLIC_SUPABASE_URL=https://your-domain.com
GOTRUE_SITE_URL=https://your-domain.com
NEXT_PUBLIC_API_URL=https://your-domain.com/api/v1
CORS_ORIGINS=https://your-domain.com

BACKEND_WORKERS=8
```

### 3. Start with production profile

```bash
docker compose --profile production up -d
```

Nginx handles TLS termination and proxies:
- `/` → frontend (Next.js)
- `/api/*`, `/health` → backend (FastAPI)
- `/auth/*` → supabase-kong → supabase-auth (GoTrue)

---

## Environment Variables Reference

See `.env.example` for the full list with descriptions. Key variables:

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `JWT_SECRET` | Yes | Supabase JWT signing secret (32+ chars) |
| `SUPABASE_ANON_KEY` | Yes | Supabase anonymous key (JWT) |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key (JWT) |
| `MEILI_MASTER_KEY` | Yes | Meilisearch authentication key |
| `ANTHROPIC_API_KEY` | No | Platform fallback AI key (BYOK per workspace) |
| `BACKEND_IMAGE` | No | CI override: pre-built backend image tag |
| `FRONTEND_IMAGE` | No | CI override: pre-built frontend image tag |

---

## Upgrading

When upgrading to a new version:

```bash
# Pull new images
docker compose pull

# Apply migrations before restarting application services
docker compose up -d postgres redis meilisearch supabase-auth supabase-kong
docker compose exec backend alembic upgrade head

# Restart all services with new images
docker compose up -d

# Verify health
docker compose ps
curl -f http://localhost:8000/health/ready
```

For detailed upgrade instructions: `docs/operations/upgrade-guide.md`

---

## Troubleshooting

### Port already in use

```bash
# Find what is using a port (e.g., 5432)
lsof -i :5432

# Change the port in .env
POSTGRES_PORT=5433
docker compose up -d
```

### Database not ready / backend failing to start

```bash
# Check postgres health
docker compose ps postgres

# View postgres logs
docker compose logs postgres --tail=50

# If postgres is unhealthy, check for volume permission issues
docker compose down -v  # WARNING: destroys data
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Auth not working / GoTrue errors

```bash
# Check supabase-auth logs
docker compose logs supabase-auth --tail=50

# Common cause: JWT_SECRET mismatch between postgres, supabase-auth, backend
# All three services must use the exact same JWT_SECRET value.
grep JWT_SECRET .env

# Restart auth services after fixing
docker compose restart supabase-auth supabase-kong
```

### Meilisearch returning 401

```bash
# Your MEILI_MASTER_KEY in .env must match what backend uses
# backend uses MEILI_MASTER_KEY as MEILISEARCH_API_KEY
grep MEILI_MASTER_KEY .env
docker compose restart meilisearch backend
```

### Frontend cannot reach backend

```bash
# Check backend is healthy
docker compose ps backend
curl -f http://localhost:8000/health

# Check CORS_ORIGINS in .env includes your frontend URL
grep CORS_ORIGINS .env

# Restart frontend to pick up env changes
docker compose restart frontend
```

### View logs for all services

```bash
docker compose logs -f
docker compose logs backend -f --tail=100
docker compose logs frontend -f --tail=100
```
