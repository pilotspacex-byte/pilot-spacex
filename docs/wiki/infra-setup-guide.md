# Pilot Space Infrastructure Setup Guide

> **Audience**: Developers setting up the Pilot Space local development environment from scratch.
> **Prerequisites**: Docker Desktop, Node.js 20+, Python 3.12+, `pnpm`, `uv`, Git.

---

## Architecture Overview

```
Browser (:3000)
    │
    ├── Next.js App Router (frontend)
    │       │
    │       └── /api/v1/* proxy ──► FastAPI backend (:8000)
    │                                   │
    │                                   ├── PostgreSQL (:15433 direct / :15432 pooled)
    │                                   ├── Redis (:6379)
    │                                   └── Supabase Auth via Kong (:18000)
    │
    └── Supabase JS client ──► Kong Gateway (:18000)
                                    │
                                    ├── /auth/v1/*   → GoTrue (auth)
                                    ├── /rest/v1/*   → PostgREST
                                    ├── /realtime/*  → Realtime WebSocket
                                    ├── /storage/v1/* → Storage API
                                    └── /functions/* → Edge Runtime
```

### Port Reference

| Port  | Service             | Protocol | Notes                          |
|-------|---------------------|----------|--------------------------------|
| 3000  | Frontend (Next.js)  | HTTP     | Dev server with API proxy      |
| 8000  | Backend (FastAPI)   | HTTP     | API + SSE streaming + Swagger  |
| 18000 | Kong Gateway        | HTTP     | Supabase API gateway           |
| 8443  | Kong Gateway        | HTTPS    | TLS termination (optional)     |
| 15432 | Supavisor (pooler)  | TCP      | Pooled PostgreSQL connections   |
| 15433 | PostgreSQL (direct) | TCP      | Direct DB access for migrations|
| 6543  | Supavisor (txn)     | TCP      | Transaction-mode pooling       |
| 6379  | Redis               | TCP      | Cache, sessions, rate limiting |

---

## Step 1: Start Supabase Stack

### 1.1 Configure Environment

```bash
cd infra/supabase
```

The `.env` file contains all Supabase configuration. Key variables grouped by function:

#### Core Database

| Variable           | Example                  | Description                          |
|--------------------|--------------------------|--------------------------------------|
| `POSTGRES_HOST`    | `db`                     | Docker service name (always `db`)    |
| `POSTGRES_PORT`    | `15432`                  | Internal PostgreSQL port             |
| `POSTGRES_DB`      | `postgres`               | Database name                        |
| `POSTGRES_PASSWORD`| `(generated)`            | Database superuser password           |

#### JWT & Auth Keys

| Variable           | Description                                              |
|--------------------|----------------------------------------------------------|
| `JWT_SECRET`       | Shared JWT signing secret (min 32 chars). Must match `SUPABASE_JWT_SECRET` in backend. |
| `ANON_KEY`         | Public JWT for anonymous/unauthenticated access. Used by frontend. |
| `SERVICE_ROLE_KEY` | Privileged JWT that bypasses RLS. Used by backend for admin operations. |
| `JWT_EXPIRY`       | Token TTL in seconds (default: `3600`).                  |

> Generate keys at https://supabase.com/docs/guides/self-hosting#api-keys or use `infra/supabase/utils/generate-keys.sh`.

#### API Gateway (Kong)

| Variable           | Example                  | Description                          |
|--------------------|--------------------------|--------------------------------------|
| `KONG_HTTP_PORT`   | `18000`                  | External HTTP port for all Supabase APIs |
| `KONG_HTTPS_PORT`  | `8443`                   | External HTTPS port (optional)       |
| `API_EXTERNAL_URL` | `http://localhost:8000`  | GoTrue uses this for OAuth callbacks |
| `SUPABASE_PUBLIC_URL`| `http://localhost:18000`| Studio and Functions public URL      |

#### Authentication (GoTrue)

| Variable                   | Default | Description                            |
|----------------------------|---------|----------------------------------------|
| `ENABLE_EMAIL_SIGNUP`      | `true`  | Allow email/password registration      |
| `ENABLE_EMAIL_AUTOCONFIRM` | `true`  | Skip email verification (dev only)     |
| `ENABLE_ANONYMOUS_USERS`   | `false` | Allow anonymous sessions               |
| `ENABLE_PHONE_SIGNUP`      | `false` | Phone-based auth                       |
| `DISABLE_SIGNUP`           | `false` | Invite-only mode                       |
| `SITE_URL`                 | `http://localhost:3000` | Frontend URL for auth redirects |

#### SMTP (Email)

For development, set `ENABLE_EMAIL_AUTOCONFIRM=true` to skip email verification entirely. For testing email flows:

```
SMTP_HOST=supabase-mail
SMTP_PORT=2500
SMTP_USER=fake_mail_user
SMTP_PASS=fake_mail_password
```

#### Connection Pooler (Supavisor)

| Variable                       | Default | Description                     |
|--------------------------------|---------|---------------------------------|
| `POOLER_TENANT_ID`            | `pilot-space-dev` | Tenant identifier for pooler auth |
| `POOLER_DEFAULT_POOL_SIZE`    | `20`    | PostgreSQL connections per pool  |
| `POOLER_MAX_CLIENT_CONN`      | `100`   | Max client connections accepted  |
| `POOLER_PROXY_PORT_TRANSACTION`| `6543` | Transaction-mode pooling port    |
| `POOLER_DB_POOL_SIZE`         | `5`     | Internal metadata pool size      |
| `SECRET_KEY_BASE`             | `(generated)` | Erlang crypto key (base64 48 chars) |

#### Analytics & Logging

| Variable                        | Description                      |
|---------------------------------|----------------------------------|
| `LOGFLARE_PUBLIC_ACCESS_TOKEN`  | Vector → Logflare ingestion token|
| `LOGFLARE_PRIVATE_ACCESS_TOKEN` | Logflare management token        |
| `DOCKER_SOCKET_LOCATION`       | `/var/run/docker.sock` for log collection |

#### Storage & Other

| Variable                    | Default | Description                          |
|-----------------------------|---------|--------------------------------------|
| `GLOBAL_S3_BUCKET`         | `stub`  | S3 bucket or local directory name    |
| `REGION`                   | `local` | Storage region                       |
| `STORAGE_TENANT_ID`        | `stub`  | Storage tenant ID                    |
| `S3_PROTOCOL_ACCESS_KEY_ID`| `(generated)` | S3 protocol endpoint credentials |
| `PG_META_CRYPTO_KEY`       | `(generated)` | Postgres-meta encryption key     |
| `DASHBOARD_USERNAME`       | `supabase` | Studio login username             |
| `DASHBOARD_PASSWORD`       | `(generated)` | Studio login password            |
| `IMGPROXY_ENABLE_WEBP_DETECTION`| `true` | WebP auto-detection              |
| `FUNCTIONS_VERIFY_JWT`     | `true`  | JWT verification for edge functions  |

### 1.2 Volume Mounts

Docker Compose mounts these config files from `infra/supabase/volumes/`:

```
volumes/
├── api/
│   └── kong.yml              # Kong declarative config (route definitions)
├── db/
│   ├── config/
│   │   └── postgresql.conf   # PostgreSQL tuning (max_connections=200, shared_buffers=256MB)
│   ├── init/
│   │   ├── 01-extensions.sql # pgvector, pgmq, pg_cron, pg_net, pg_trgm, pgsodium
│   │   └── 02-schemas.sql   # util schema, RLS context helpers
│   ├── _supabase.sql         # Internal Supabase schemas
│   ├── jwt.sql               # JWT configuration
│   ├── logs.sql              # Logging setup
│   ├── pooler.sql            # Pooler roles
│   ├── realtime.sql          # Realtime extension
│   ├── roles.sql             # Database roles
│   └── webhooks.sql          # Webhook triggers
├── functions/                 # Edge function source files
├── logs/
│   └── vector.yml            # Vector log pipeline config (MUST be a file, not directory)
├── pooler/
│   └── pooler.exs            # Supavisor tenant configuration
├── snippets/                  # Studio SQL snippets
└── storage/                   # Local file storage
```

> **Common issue**: If `volumes/logs/vector.yml` is a directory instead of a file (created by Docker on first mount), the `supabase-vector` container will fail with `Configuration error. error=Is a directory`. Delete the directory and create the file manually.

### 1.3 Direct DB Access (Override)

Supavisor (port 15432) requires `user.tenant_id` username format for pooled connections. For Alembic migrations and direct DB access, expose PostgreSQL on a separate port via `docker-compose.override.yml`:

```yaml
# infra/supabase/docker-compose.override.yml
services:
  db:
    ports:
      - "15433:15432"
```

This maps host port 15433 directly to the PostgreSQL container, bypassing the pooler.

### 1.4 Start Services

```bash
cd infra/supabase

# Pull images (first time or after version updates)
docker compose pull

# Start all services
docker compose up -d

# Verify health
docker compose ps
```

Expected: all containers `Up` and `healthy` within 30-60 seconds. The dependency chain is:

```
vector → db → analytics → { auth, rest, kong, meta, realtime, functions, pooler } → storage
```

### 1.5 Verify Supabase

```bash
# Auth health check
ANON_KEY=$(grep '^ANON_KEY=' .env | cut -d= -f2-)
curl -s "http://localhost:18000/auth/v1/health" -H "apikey: $ANON_KEY"
# Expected: {"version":"v2.186.0","name":"GoTrue",...}
```

---

## Step 2: Start Redis

Redis is used for session management, AI response caching, and rate limiting. Run it as a standalone container:

```bash
docker run -d --name pilot-redis -p 6379:6379 redis:7-alpine
```

Or use Docker Compose from `infra/docker/docker-compose.yml` if available.

---

## Step 3: Configure Backend

### 3.1 Environment File

```bash
cd backend
cp .env.example .env
```

Key variables to configure:

| Variable              | Value                            | Notes                              |
|-----------------------|----------------------------------|------------------------------------|
| `DATABASE_URL`        | `postgresql+asyncpg://supabase_admin:<password>@localhost:15433/postgres` | Use port 15433 (direct DB) |
| `REDIS_URL`           | `redis://localhost:6379/0`       | Local Redis                        |
| `SUPABASE_URL`        | `http://localhost:18000`         | Kong gateway URL                   |
| `SUPABASE_ANON_KEY`   | `(from infra/supabase/.env ANON_KEY)` | Must match Supabase               |
| `SUPABASE_JWT_SECRET` | `(from infra/supabase/.env JWT_SECRET)` | Must match exactly              |
| `ENCRYPTION_KEY`      | `(32-byte base64 Fernet key)`    | For workspace API key encryption   |
| `AUTH_PROVIDER`       | `authcore`                       | JWT provider (authcore or supabase)|
| `APP_ENV`             | `development`                    | Enables debug features             |

#### AI Provider Keys (optional, BYOK)

```
ANTHROPIC_API_KEY=sk-ant-...    # App-level fallback only
GOOGLE_API_KEY=...               # For embeddings
```

In production, workspace-level API keys (stored encrypted in `workspace_api_keys` table) take precedence over app-level keys.

### 3.2 Install Dependencies

```bash
cd backend
uv sync
```

### 3.3 Run Migrations

Alembic uses synchronous `psycopg2` (auto-converted from `asyncpg` URL). The `alembic_version` table uses `varchar(128)` for descriptive revision IDs.

```bash
cd backend

# Verify migration chain
uv run alembic heads     # Should show single head

# Apply all migrations
uv run alembic upgrade head

# Verify models match DB
uv run alembic check
```

> **Note**: If you get `StringDataRightTruncation: value too long for type character varying(32)`, the `alembic_version` table was created with the default column width. Fix with:
> ```sql
> ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(128);
> ```
> Then re-run `alembic upgrade head`.

### 3.4 Seed Demo Data (Optional)

The seed script creates a complete demo environment with realistic data. It requires:
- Supabase stack running (Step 1)
- Database migrations applied (Step 3.3)
- `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` set in `backend/.env`

```bash
cd backend
uv run python scripts/seed_demo.py
```

The script performs two steps:
1. **Supabase Auth user** — Creates (or reuses) a demo user via the GoTrue Admin API
2. **Database seeding** — Populates the database with:

| Entity           | Count | Details                                    |
|------------------|-------|--------------------------------------------|
| User             | 1     | `test@pilot.space` / `DemoPassword123!`    |
| Workspace        | 1     | `pilot-space-demo`                         |
| Projects         | 3     | AUTH, API, FE                              |
| Workflow states  | 18    | 6 per project (Backlog → Cancelled)        |
| Labels           | 14    | Type + domain labels per project           |
| Notes            | 7     | 2 pinned, 5 recent (TipTap JSON content)   |
| Issues           | 51    | Distributed across all workflow states      |
| Skill templates  | N     | Seeded from `role_templates` table         |

The script is **idempotent** — re-running it clears existing demo data and reseeds.

After seeding, log in at `http://localhost:3000/login` with:
- **Email**: `test@pilot.space`
- **Password**: `DemoPassword123!`

### 3.5 Start Backend

```bash
cd backend
uv run uvicorn pilot_space.main:app --reload --port 8000
```

Verify: `http://localhost:8000/health` should return `200` with all checks passing.

---

## Step 4: Configure Frontend

### 4.1 Environment File

```bash
cd frontend
cp .env.example .env.local
```

Key variables:

| Variable                       | Value                     |
|--------------------------------|---------------------------|
| `NEXT_PUBLIC_API_URL`          | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_SUPABASE_URL`     | `http://localhost:18000`  |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`| `(ANON_KEY from Supabase .env)` |
| `NEXT_PUBLIC_ENABLE_AI_FEATURES`| `true`                   |

### 4.2 Install & Run

```bash
cd frontend
pnpm install
pnpm dev
```

Frontend runs on `http://localhost:3000`. API calls are proxied to the backend via Next.js rewrites.

---

## Step 5: Verify End-to-End

### Create Test User

```bash
ANON_KEY="(your anon key)"

# Sign up (auto-confirmed in dev)
curl -s "http://localhost:18000/auth/v1/signup" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@pilot.space","password":"DemoPassword123!"}'
```

### Test Backend API

```bash
# Get JWT token
TOKEN=$(curl -s "http://localhost:18000/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@pilot.space","password":"DemoPassword123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# List workspaces
curl -s "http://localhost:8000/api/v1/workspaces" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

### Open Frontend

Navigate to `http://localhost:3000/login` and sign in with the test credentials.

---

## Quality Gates

Run before every commit:

```bash
# Backend
make quality-gates-backend     # pyright + ruff check + pytest --cov

# Frontend
make quality-gates-frontend    # eslint + tsc --noEmit + vitest

# Or individually:
cd backend && uv run ruff check && uv run pyright && uv run pytest
cd frontend && pnpm lint && pnpm type-check && pnpm test
```

---

## Troubleshooting

### Supavisor "Tenant or user not found"

The pooler (port 15432) requires connections in `user.tenant_id` format. If your backend connects to port 15432 with a plain username, it fails. **Fix**: use port 15433 (direct DB) in `DATABASE_URL`, or format the username as `supabase_admin.pilot-space-dev`.

### Vector Container Unhealthy

```
Configuration error. error=Is a directory
```

The `volumes/logs/vector.yml` mount is a directory instead of a file. Docker creates directories for missing bind mount targets.

```bash
rm -rf infra/supabase/volumes/logs/vector.yml
# Recreate as a file with proper Vector config
```

### Port Conflicts

```bash
# Find what's using a port
lsof -i :15432
lsof -i :6543
lsof -i :6379

# Kill stale containers from old compose projects
docker ps -a --format '{{.Names}}' | grep pilot-space | xargs docker rm -f
```

### Database Connection Refused

1. Check `docker compose ps` — is `supabase-db` healthy?
2. Verify `POSTGRES_PASSWORD` matches between `infra/supabase/.env` and `backend/.env`.
3. For direct access, ensure `docker-compose.override.yml` exposes port 15433.

### Redis Connection Refused

Backend logs `redis_connect_failed — running in degraded mode`. This is non-fatal but disables session management and caching.

```bash
docker run -d --name pilot-redis -p 6379:6379 redis:7-alpine
```

---

## Service Dependency Graph

```
                         ┌─────────────┐
                         │   vector    │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                    ┌────│     db      │────┐
                    │    └──────┬──────┘    │
                    │           │           │
             ┌──────▼──────┐   │   ┌───────▼──────┐
             │  analytics  │◄──┘   │   imgproxy   │
             └──────┬──────┘       └───────┬──────┘
                    │                      │
     ┌──────────────┼──────────────┐       │
     │       │      │      │       │       │
  ┌──▼──┐ ┌──▼──┐ ┌▼───┐ ┌▼────┐ ┌▼────┐  │
  │auth │ │rest │ │kong│ │meta │ │func │  │
  └──┬──┘ └──┬──┘ └─┬──┘ └─────┘ └─────┘  │
     │       │      │                      │
     │    ┌──▼──────▼──────────────────────▼──┐
     │    │              storage               │
     │    └────────────────────────────────────┘
     │
  ┌──▼────────┐
  │ supavisor │
  └───────────┘

  External (not in Supabase compose):
  ┌───────┐  ┌──────────┐  ┌──────────┐
  │ redis │  │ backend  │  │ frontend │
  └───────┘  └──────────┘  └──────────┘
```
