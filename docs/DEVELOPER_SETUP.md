# Developer Setup Guide

This guide provides step-by-step instructions for setting up the Pilot Space development environment.

## Prerequisites

Before starting, ensure you have the following installed:

| Tool | Minimum Version | Check Command |
|------|-----------------|---------------|
| **Node.js** | 20.x | `node --version` |
| **pnpm** | 9.x | `pnpm --version` |
| **Python** | 3.12+ | `python3 --version` |
| **uv** | latest | `uv --version` |
| **Docker** | 24+ | `docker --version` |
| **Docker Compose** | 2.x | `docker compose version` |
| **Git** | 2.x | `git --version` |

### Installing Prerequisites

#### macOS

```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Node.js (includes npm)
brew install node@20

# Install pnpm
npm install -g pnpm@9

# Install Python 3.12
brew install python@3.12

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Docker Desktop
brew install --cask docker
```

#### Linux (Ubuntu/Debian)

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install pnpm
npm install -g pnpm@9

# Install Python 3.12
sudo apt-get install python3.12 python3.12-venv

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

---

## Step-by-Step Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/pilot-space.git
cd pilot-space
```

### 2. Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, Meilisearch, and Supabase
docker compose up -d

# Verify services are running
docker compose ps

# Expected output:
# pilot-space-db        running   5432/tcp
# pilot-space-redis     running   6379/tcp
# pilot-space-search    running   7700/tcp
# supabase-studio       running   54323/tcp
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync

# Copy environment file
cp .env.example .env

# Edit .env with your local settings
# See "Environment Variables" section below

# Run database migrations
uv run alembic upgrade head

# Install pre-commit hooks
pre-commit install

# Verify setup
uv run pytest --co  # Should list available tests
uv run pyright      # Should pass type checking
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Copy environment file
cp .env.example .env.local

# Edit .env.local with your settings
# See "Environment Variables" section below

# Verify setup
pnpm lint        # Should pass linting
pnpm type-check  # Should pass type checking
```

### 5. Start Development Servers

In separate terminal windows:

```bash
# Terminal 1: Backend
cd backend
uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
pnpm dev
```

Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- Supabase Studio: http://localhost:54323

---

## Environment Variables

### Backend (`backend/.env`)

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pilot_space
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # From Supabase Studio

# Redis
REDIS_URL=redis://localhost:6379

# Search
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=masterKey

# AI Providers (BYOK - Bring Your Own Key)
ANTHROPIC_API_KEY=sk-ant-...        # Required for Claude
OPENAI_API_KEY=sk-...               # Required for embeddings
GOOGLE_AI_API_KEY=...               # Optional for Gemini

# GitHub Integration
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# Security
SECRET_KEY=your-secret-key-min-32-chars
CORS_ORIGINS=http://localhost:3000
```

### Frontend (`frontend/.env.local`)

```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key  # From Supabase Studio

# Features
NEXT_PUBLIC_ENABLE_AI_FEATURES=true
```

---

## Database Setup and Seeding

### Initial Migration

```bash
cd backend

# Run all migrations
uv run alembic upgrade head

# Check current migration
uv run alembic current
```

### Seed Sample Data

```bash
cd backend

# Run seed script
uv run python -m pilot_space.scripts.seed_data

# This creates:
# - Sample workspace
# - Sample project
# - Sample issues, notes, cycles
# - Sample user (test@example.com / testpassword123)
```

### Reset Database

```bash
cd backend

# Downgrade all migrations
uv run alembic downgrade base

# Re-run migrations
uv run alembic upgrade head

# Re-seed data
uv run python -m pilot_space.scripts.seed_data
```

---

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run specific test file
uv run pytest tests/integration/test_issues.py

# Run with verbose output
uv run pytest -v

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run with coverage
pnpm test:coverage

# Run E2E tests (requires running app)
pnpm test:e2e

# Run E2E tests with UI
pnpm test:e2e --ui
```

### Quality Gates

```bash
# Backend quality gate (must pass before commit)
cd backend && uv run ruff check && uv run pyright && uv run pytest --cov=. --cov-fail-under=80

# Frontend quality gate
cd frontend && pnpm lint && pnpm type-check && pnpm test
```

---

## Troubleshooting

### Common Issues

#### Docker Services Not Starting

```bash
# Check Docker is running
docker info

# Check port conflicts
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :7700  # Meilisearch

# View container logs
docker compose logs db
docker compose logs redis
```

#### Database Connection Errors

```bash
# Verify PostgreSQL is running
docker compose ps db

# Test connection
psql -h localhost -U postgres -d pilot_space

# Check migrations
cd backend && uv run alembic current
```

#### Python Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv sync
```

#### Node Modules Issues

```bash
# Clear and reinstall
rm -rf node_modules
rm pnpm-lock.yaml
pnpm install
```

#### Redis Connection Errors

```bash
# Test Redis connection
docker compose exec redis redis-cli ping
# Should return: PONG
```

#### Supabase Auth Issues

```bash
# Check Supabase is running
docker compose ps supabase-studio

# Verify API keys in Supabase Studio
# http://localhost:54323/project/default/settings/api
```

### Getting Help

- Check existing issues: https://github.com/your-org/pilot-space/issues
- Create new issue with detailed logs
- Join team Slack channel: #pilot-space-dev

---

## IDE Setup

### VS Code (Recommended)

Install recommended extensions:

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "prisma.prisma"
  ]
}
```

### PyCharm

1. Open `backend/` as project root
2. Configure Python interpreter: `.venv/bin/python`
3. Enable Ruff plugin
4. Set pyright as type checker

---

## Next Steps

After completing setup:

1. Review [Architecture Documentation](./architect/README.md)
2. Read [Contributing Guide](./getting-started/CONTRIBUTING.md)
3. Check [Design Decisions](./DESIGN_DECISIONS.md)
4. Explore [API Documentation](http://localhost:8000/docs)
