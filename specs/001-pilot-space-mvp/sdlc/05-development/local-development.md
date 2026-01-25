# Local Development Guide

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

This guide covers setting up a local development environment for Pilot Space.

---

## Prerequisites

### Required Software

| Software | Version | Installation |
|----------|---------|--------------|
| Python | 3.12+ | `brew install python@3.12` or [python.org](https://python.org) |
| Node.js | 20+ | `brew install node@20` or [nodejs.org](https://nodejs.org) |
| pnpm | 9+ | `npm install -g pnpm` |
| Docker | 24+ | [Docker Desktop](https://docker.com/products/docker-desktop) |
| Supabase CLI | Latest | `brew install supabase/tap/supabase` |
| uv | Latest | `pip install uv` |

### Verify Installation

```bash
python3 --version   # Should be 3.12+
node --version      # Should be 20+
pnpm --version      # Should be 9+
docker --version    # Should be 24+
supabase --version  # Latest
uv --version        # Latest
```

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/pilot-space.git
cd pilot-space
```

### 2. Start Infrastructure

```bash
# Start Supabase locally (database, auth, storage)
supabase start

# This starts:
# - PostgreSQL on port 54322
# - Supabase Studio on port 54323
# - Auth on port 54321
# - Storage on port 54321/storage

# Start Redis (for caching)
docker compose up redis -d

# Start Meilisearch (for search)
docker compose up meilisearch -d
```

### 3. Setup Backend

```bash
cd backend

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Install pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env.local

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Setup Frontend

```bash
cd frontend

# Install dependencies
pnpm install

# Copy environment file
cp .env.example .env.local

# Start development server
pnpm dev
```

### 5. Access Applications

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Supabase Studio | http://localhost:54323 |

---

## Environment Configuration

### Backend (.env.local)

```env
# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=debug

# Supabase (local)
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Database (local Supabase)
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres

# Redis (local)
REDIS_URL=redis://localhost:6379

# Meilisearch (local)
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_KEY=masterKey

# AI Providers (optional for development)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# GitHub App (optional)
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# Slack App (optional)
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_SIGNING_SECRET=
```

### Frontend (.env.local)

```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase (local)
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Feature flags
NEXT_PUBLIC_ENABLE_AI=true
NEXT_PUBLIC_ENABLE_GITHUB=false
NEXT_PUBLIC_ENABLE_SLACK=false
```

---

## Docker Compose (Full Stack)

For running everything with Docker:

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - SUPABASE_URL=http://supabase:54321
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres
      - REDIS_URL=redis://redis:6379
      - MEILISEARCH_URL=http://meilisearch:7700
    depends_on:
      - redis
      - meilisearch
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
    depends_on:
      - backend
    volumes:
      - ./frontend:/app

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  meilisearch:
    image: getmeili/meilisearch:v1.6
    ports:
      - "7700:7700"
    environment:
      - MEILI_MASTER_KEY=masterKey
    volumes:
      - meilisearch_data:/meili_data

volumes:
  redis_data:
  meilisearch_data:
```

Run with:
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f backend

# Stop all services
docker compose down
```

---

## Database Management

### Supabase CLI Commands

```bash
# Start local Supabase
supabase start

# Stop local Supabase
supabase stop

# Reset database (drops all data)
supabase db reset

# View migration status
supabase migration list

# Create new migration
supabase migration new add_new_table

# Apply migrations
supabase db push
```

### Alembic Migrations (Backend)

```bash
cd backend

# Generate migration from models
alembic revision --autogenerate -m "Add users table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Seed Data

```bash
# Seed development data
cd backend
python -m pilot_space.scripts.seed_data

# Or via Supabase
supabase db seed
```

---

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=pilot_space --cov-report=html

# Run specific test file
pytest tests/unit/test_issue_service.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_create"
```

### Frontend Tests

```bash
cd frontend

# Run all tests
pnpm test

# Run with coverage
pnpm test --coverage

# Run in watch mode
pnpm test --watch

# Run E2E tests
pnpm test:e2e
```

### Quality Gates

```bash
# Backend quality check
cd backend
uv run pyright && uv run ruff check && uv run pytest --cov=.

# Frontend quality check
cd frontend
pnpm lint && pnpm type-check && pnpm test
```

---

## Common Tasks

### Create Test User

```bash
# Via Supabase Studio: http://localhost:54323
# Authentication > Users > Add User

# Or via API
curl -X POST 'http://localhost:54321/auth/v1/admin/users' \
  -H "apikey: your-service-key" \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@example.com", "password": "testpass123"}'
```

### Test AI Features

To test AI features locally, you need real API keys:

```bash
# Add to .env.local
ANTHROPIC_API_KEY=sk-ant-...  # For PR review, task decomposition
OPENAI_API_KEY=sk-...          # For embeddings
GOOGLE_API_KEY=AIza...         # For ghost text (optional)
```

Without keys, AI features will gracefully degrade.

### Debug Backend

```bash
# Run with debugger
python -m debugpy --listen 5678 -m uvicorn pilot_space.main:app --reload

# VS Code launch.json
{
  "name": "Python: FastAPI",
  "type": "python",
  "request": "attach",
  "connect": { "host": "localhost", "port": 5678 }
}
```

### Debug Frontend

```bash
# Run with Node inspector
NODE_OPTIONS='--inspect' pnpm dev

# Or use React DevTools browser extension
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn pilot_space.main:app --port 8001
```

### Supabase Won't Start

```bash
# Check Docker is running
docker ps

# Reset Supabase
supabase stop --no-backup
supabase start
```

### Database Connection Failed

```bash
# Verify Supabase is running
supabase status

# Check connection string
psql "postgresql://postgres:postgres@localhost:54322/postgres"
```

### pnpm Install Fails

```bash
# Clear cache
pnpm store prune

# Remove node_modules and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Python Dependencies Issues

```bash
# Recreate virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv sync
```

---

## IDE Setup

### VS Code Extensions

Recommended extensions (in `.vscode/extensions.json`):

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "prisma.prisma",
    "GitHub.copilot"
  ]
}
```

### VS Code Settings

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.analysis.typeCheckingMode": "strict",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "editor.formatOnSave": true
}
```

---

## References

- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [testing-strategy.md](./testing-strategy.md) - Testing details
- [Supabase CLI Reference](https://supabase.com/docs/reference/cli)
