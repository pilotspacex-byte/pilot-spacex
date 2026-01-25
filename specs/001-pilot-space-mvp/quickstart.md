# Quickstart Guide: Pilot Space MVP

**Branch**: `001-pilot-space-mvp` | **Date**: 2026-01-21
**Purpose**: Developer setup instructions for local development environment.

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.12+ | Backend runtime |
| **Node.js** | 20 LTS+ | Frontend runtime |
| **pnpm** | 9.0+ | Package manager |
| **Docker** | 24+ | Container runtime |
| **Docker Compose** | 2.20+ | Multi-container orchestration |
| **uv** | 0.4+ | Python package manager |

### Installation Commands

```bash
# macOS (Homebrew)
brew install python@3.12 node pnpm docker docker-compose

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installations
python3 --version  # 3.12+
node --version     # 20+
pnpm --version     # 9+
docker --version   # 24+
uv --version       # 0.4+
```

---

## Quick Start (Docker Compose)

The fastest way to run the complete stack locally:

```bash
# Clone repository
git clone https://github.com/pilot-space/pilot-space.git
cd pilot-space

# Copy environment template
cp .env.example .env

# Edit .env with your configuration (see Environment Variables section)

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Keycloak: http://localhost:8080
# RabbitMQ: http://localhost:15672
# Meilisearch: http://localhost:7700
```

### Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | Next.js application |
| `backend` | 8000 | FastAPI application |
| `worker` | - | Celery worker for async tasks |
| `postgres` | 5432 | PostgreSQL with pgvector |
| `redis` | 6379 | Cache and session store |
| `rabbitmq` | 5672, 15672 | Message queue |
| `meilisearch` | 7700 | Search engine |
| `keycloak` | 8080 | Identity provider |
| `minio` | 9000, 9001 | S3-compatible storage |

---

## Development Setup

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # Unix/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
uv sync

# Install pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env

# Edit .env (see Environment Variables section)
```

### Database Setup

```bash
# Start PostgreSQL with pgvector (Docker)
docker compose up -d postgres

# Or use local PostgreSQL (install pgvector extension)
# macOS: brew install postgresql pgvector
# Ubuntu: sudo apt install postgresql-15-pgvector

# Create database
createdb pilot_space

# Enable pgvector extension
psql pilot_space -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
alembic upgrade head

# Seed default data (optional)
python -m pilot_space.infrastructure.database.seed
```

### Running Backend

```bash
# Development server with auto-reload
uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000

# Or using the CLI
python -m pilot_space serve

# API documentation available at:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### Running Celery Worker

```bash
# Start RabbitMQ (Docker)
docker compose up -d rabbitmq

# Start Celery worker
celery -A pilot_space.infrastructure.queue.celery_config worker --loglevel=info

# Start Celery Beat (for scheduled tasks)
celery -A pilot_space.infrastructure.queue.celery_config beat --loglevel=info

# Start Flower (monitoring)
celery -A pilot_space.infrastructure.queue.celery_config flower --port=5555
```

### Backend Quality Gates

```bash
# Run all checks
uv run pyright && uv run ruff check && uv run pytest --cov=.

# Individual commands
uv run pyright                    # Type checking
uv run ruff check                 # Linting
uv run ruff format --check        # Format check
uv run pytest                     # Tests
uv run pytest --cov=. --cov-report=html  # Coverage report
```

---

### Frontend Setup

```bash
# Navigate to frontend directory (from repo root)
cd frontend

# Install dependencies
pnpm install

# Copy environment template
cp .env.example .env.local

# Edit .env.local (see Environment Variables section)
```

### Creating New Frontend Project (From Scratch)

If starting from scratch, use shadcn/ui with Next.js:

```bash
# Create new Next.js project with shadcn/ui
pnpm dlx shadcn@latest init

# Follow the prompts:
# - Would you like to use TypeScript? Yes
# - Which style would you like to use? Default
# - Which color would you like to use as base color? Slate
# - Where is your global CSS file? src/app/globals.css
# - Would you like to use CSS variables for colors? Yes
# - Are you using a custom tailwind prefix? No
# - Where is your tailwind.config.js located? tailwind.config.ts
# - Configure the import alias for components? @/components
# - Configure the import alias for utils? @/lib/utils
# - Are you using React Server Components? Yes

# Add commonly used components
pnpm dlx shadcn@latest add button input label card dialog dropdown-menu
pnpm dlx shadcn@latest add toast tooltip popover command
pnpm dlx shadcn@latest add tabs badge avatar separator

# Install additional dependencies
pnpm add @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder
pnpm add @tiptap/extension-link @tiptap/extension-image @tiptap/extension-code-block-lowlight
pnpm add mobx mobx-react-lite
pnpm add @tanstack/react-virtual
pnpm add date-fns zod @hookform/resolvers react-hook-form
pnpm add lucide-react
```

### Running Frontend

```bash
# Development server
pnpm dev

# Access at http://localhost:3000

# Build for production
pnpm build

# Start production server
pnpm start
```

### Frontend Quality Gates

```bash
# Run all checks
pnpm lint && pnpm type-check && pnpm test

# Individual commands
pnpm lint           # ESLint
pnpm type-check     # TypeScript
pnpm test           # Jest/Vitest tests
pnpm test:e2e       # Playwright E2E tests
```

---

## Environment Variables

### Backend (.env)

```bash
# Application
APP_ENV=development
APP_DEBUG=true
APP_SECRET_KEY=your-secret-key-min-32-chars

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pilot_space

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Meilisearch
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your-meilisearch-key

# Keycloak OIDC
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=pilot-space
KEYCLOAK_CLIENT_ID=pilot-space-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret

# MinIO/S3
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=pilot-space

# GitHub Integration (optional for local dev)
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# Slack Integration (optional for local dev)
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=

# AI Configuration (BYOK - at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
```

### Frontend (.env.local)

```bash
# API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Keycloak
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_REALM=pilot-space
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=pilot-space-frontend

# Feature Flags
NEXT_PUBLIC_ENABLE_AI_FEATURES=true
NEXT_PUBLIC_ENABLE_GITHUB_INTEGRATION=false
NEXT_PUBLIC_ENABLE_SLACK_INTEGRATION=false
```

---

## Keycloak Setup

### Initial Configuration

1. Access Keycloak admin console: http://localhost:8080
2. Login with `admin` / `admin`
3. Create realm "pilot-space"
4. Create clients:
   - `pilot-space-backend` (confidential, service account)
   - `pilot-space-frontend` (public, authorization code flow)

### Realm Import (Recommended)

```bash
# Import pre-configured realm
docker compose exec keycloak /opt/keycloak/bin/kc.sh import \
  --file /opt/keycloak/data/import/pilot-space-realm.json
```

Realm export file location: `infra/keycloak/pilot-space-realm.json`

---

## Sample Data

### Seed Development Data

```bash
# Seed sample workspace, project, issues
cd backend
python -m pilot_space.infrastructure.database.seed --sample-data

# This creates:
# - Workspace: "Pilot Space Dev"
# - Project: "Core Platform" (identifier: PS)
# - 10 sample issues
# - 5 sample notes
# - Default templates
```

### Create Test User

```bash
# Via Keycloak Admin API
curl -X POST "http://localhost:8080/admin/realms/pilot-space/users" \
  -H "Authorization: Bearer $(get_admin_token)" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "enabled": true,
    "credentials": [{
      "type": "password",
      "value": "testpassword",
      "temporary": false
    }]
  }'
```

---

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=pilot_space --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_issue_service.py

# Run with verbose output
uv run pytest -v

# Run only fast tests (skip integration)
uv run pytest -m "not integration"

# Run integration tests (requires Docker services)
uv run pytest -m integration
```

### Frontend Tests

```bash
cd frontend

# Unit tests
pnpm test

# Watch mode
pnpm test:watch

# E2E tests (Playwright)
pnpm test:e2e

# E2E with UI
pnpm test:e2e:ui
```

---

## Common Development Tasks

### Adding a New API Endpoint

1. Create/update router in `backend/src/pilot_space/api/v1/routers/`
2. Add Pydantic schemas in `backend/src/pilot_space/api/v1/schemas/`
3. Create service method in `backend/src/pilot_space/domain/services/`
4. Add tests in `backend/tests/`
5. Update OpenAPI spec in `specs/001-pilot-space-mvp/contracts/openapi.yaml`

### Adding a New TipTap Extension

1. Create extension in `frontend/src/components/editor/extensions/`
2. Register in `frontend/src/components/editor/NoteCanvas.tsx`
3. Add CSS styles in `frontend/src/styles/editor.css`
4. Add tests in `frontend/tests/`

### Adding a New AI Agent

1. Create agent in `backend/src/pilot_space/ai/agents/`
2. Add prompts in `backend/src/pilot_space/ai/prompts/`
3. Register in orchestrator `backend/src/pilot_space/ai/orchestrator.py`
4. Add Celery task if async
5. Add API endpoint
6. Add tests

### Running Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "Add new_table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

---

## Troubleshooting

### Common Issues

**Port already in use**
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

**Docker containers not starting**
```bash
# Reset all containers
docker compose down -v
docker compose up -d
```

**Database connection refused**
```bash
# Check PostgreSQL is running
docker compose ps postgres
docker compose logs postgres
```

**pgvector extension not found**
```bash
# Install pgvector in container
docker compose exec postgres psql -U postgres -d pilot_space \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Keycloak login issues**
```bash
# Check Keycloak logs
docker compose logs keycloak

# Reset Keycloak
docker compose down keycloak
docker volume rm pilot-space_keycloak_data
docker compose up -d keycloak
```

**AI features not working**
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## IDE Setup

### VS Code Extensions

Recommended extensions (`.vscode/extensions.json`):

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "prisma.prisma",
    "mtxr.sqltools",
    "ms-azuretools.vscode-docker"
  ]
}
```

### VS Code Settings

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.analysis.typeCheckingMode": "strict",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

---

## Next Steps

After completing setup:

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Create a workspace**: Use the API or frontend
3. **Try the Note Canvas**: Create notes and see ghost text suggestions
4. **Configure AI**: Add your LLM API keys in workspace settings
5. **Connect integrations**: Set up GitHub/Slack (optional)

For implementation details, see:
- `specs/001-pilot-space-mvp/plan.md` - Implementation plan
- `specs/001-pilot-space-mvp/data-model.md` - Data model
- `specs/001-pilot-space-mvp/contracts/openapi.yaml` - API specification
- `docs/AI_CAPABILITIES.md` - AI agent documentation

---

*Quickstart Version: 1.0*
*Generated: 2026-01-21*
