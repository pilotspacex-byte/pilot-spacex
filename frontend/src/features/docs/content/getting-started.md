# Developer Setup

Get PilotSpace running locally in under 5 minutes.

## Prerequisites

- **Node.js** 20+ with `pnpm` (frontend)
- **Python** 3.12+ with `uv` (backend)
- **Docker** + Docker Compose (Supabase stack)

## 1. Start Infrastructure

```bash
# Start Supabase local stack (PostgreSQL, Auth, Realtime, Storage)
cd infra/supabase && docker compose up -d
```

This starts 14 containers including PostgreSQL 16 (port 5432), Kong API Gateway (port 18000), and GoTrue Auth.

## 2. Install Dependencies

```bash
cd backend && uv sync          # Backend Python deps
cd frontend && pnpm install    # Frontend Node deps
```

## 3. Configure Environment

```bash
# Backend
cp backend/.env.example backend/.env
# Set: DATABASE_URL, SUPABASE_URL, SUPABASE_JWT_SECRET, AI provider keys

# Frontend
cp frontend/.env.example frontend/.env.local
# Set: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
```

## 4. Run Migrations

```bash
cd backend && alembic upgrade head
```

## 5. Start Dev Servers

```bash
# Terminal 1: Backend (port 8000)
cd backend && uv run uvicorn pilot_space.main:app --reload --port 8000

# Terminal 2: Frontend (port 3000)
cd frontend && pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

## Quality Gates

Run before every commit:

```bash
# Backend
make quality-gates-backend     # pyright + ruff check + pytest --cov

# Frontend
make quality-gates-frontend    # eslint + tsc --noEmit + vitest
```

## Pre-Commit Hooks

This project uses **prek** (not standard pre-commit):

```bash
prek install    # NOT pre-commit install
```

Hooks run: eslint, tsc, prettier, ruff, pyright, file size check (700-line limit).

## Test Database

Default test DB is SQLite in-memory (`backend/tests/conftest.py`). For integration tests with RLS/pgvector:

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/pilot_space_test
```

## Ports Reference

| Service               | Port                         |
| --------------------- | ---------------------------- |
| Frontend (Next.js)    | 3000                         |
| Backend (FastAPI)     | 8000                         |
| Supabase Kong Gateway | 18000                        |
| PostgreSQL            | 5432 (host) / 15432 (Docker) |
| Redis                 | 6379                         |
| Meilisearch           | 7700                         |
