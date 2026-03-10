# Technology Stack

**Analysis Date:** 2026-03-07

## Languages

**Primary:**
- Python 3.12 - Backend (FastAPI application, AI layer, CLI)
- TypeScript 5.x - Frontend (Next.js application)

**Secondary:**
- SQL - Alembic migrations, RLS policies, pgmq RPC calls

## Runtime

**Environment:**
- Python >=3.12 (strict, also supports 3.13)
- Node.js 20.x (confirmed v20.19.5)

**Package Manager:**
- Backend: `uv` — lockfile at `backend/uv.lock`
- Frontend: `pnpm` — lockfile at `frontend/pnpm-lock.yaml`, workspace config at `frontend/pnpm-workspace.yaml`

## Frameworks

**Core (Backend):**
- FastAPI >=0.115.0 — HTTP API, SSE streaming, OpenAPI auto-docs
- Uvicorn >=0.32.0 (with `[standard]` extras) — ASGI server, reload in dev
- SQLAlchemy >=2.0.36 (asyncio mode) — ORM, async session management, 35 models
- Alembic >=1.14.0 — schema migrations (36+ migrations in `backend/alembic/versions/`)
- Pydantic >=2.10.0 + pydantic-settings >=2.6.0 — validation, settings, RFC 7807 error responses
- dependency-injector >=4.43.0 — DI container wiring (`backend/src/pilot_space/container/container.py`)

**Core (Frontend):**
- Next.js 16.1.4 — App Router, standalone Docker output, rewrite proxy to backend
- React 19.2.3 — UI, strict mode enabled
- MobX 6.15.0 + mobx-react-lite 4.1.1 — observable UI state, auto-save reactions
- TanStack Query 5.x — server state, caching, request deduplication

**Rich Text:**
- TipTap 3.x (core, react, starter-kit, + 12 extensions) — note editor
- ProseMirror (via `@tiptap/pm`) — editor state
- Yjs 13.x + y-prosemirror + y-indexeddb — CRDT collaborative editing (local persistence via IndexedDB)
- tiptap-markdown — markdown serialization

**UI Components:**
- Radix UI (15 primitives: dialog, dropdown, popover, select, tabs, etc.)
- shadcn/ui component system (`frontend/components.json`)
- Tailwind CSS 4.x — utility-first styling
- Lucide React — icons
- dnd-kit (core, sortable, utilities) — drag-and-drop
- cmdk 1.x — command palette
- Recharts 3.x — charts
- React Flow (`@xyflow/react`) — knowledge graph visualization
- Motion 12.x (Framer Motion) — animations
- Sonner — toast notifications

**Testing (Backend):**
- pytest >=8.3.0 (asyncio_mode=auto)
- pytest-asyncio >=0.24.0
- pytest-cov >=6.0.0 (branch coverage, fail_under=80)
- pytest-xdist >=3.5.0 — parallel test execution
- respx >=0.21.0 — HTTP mocking
- factory-boy >=3.3.0 + faker — test data
- aiosqlite >=0.22.1 — in-memory SQLite for unit tests

**Testing (Frontend):**
- Vitest 3.x — test runner (jsdom environment, coverage via v8, fail_under=80)
- @testing-library/react 16.x + @testing-library/user-event
- Playwright 1.52.x — E2E tests (`frontend/e2e/`)
- msw 2.x — API mocking

**Build/Dev:**
- Ruff >=0.8.0 — Python linting + formatting (line-length=100, target=py312)
- Pyright >=1.1.390 — strict type checking (`typeCheckingMode: strict`)
- ESLint 9.x (eslint-config-next 16.1.4) — frontend linting
- Prettier 3.x — frontend formatting
- prek — pre-commit hook runner (NOT standard pre-commit; `prek install` to set up)

## Key Dependencies

**Critical (Backend):**
- `asyncpg >=0.30.0` — async PostgreSQL driver
- `pgvector >=0.3.6` — vector similarity search (semantic search, embeddings)
- `redis >=5.2.0` — session cache (30-min TTL), AI cache (7-day TTL), rate limiting
- `meilisearch >=0.31.0` — typo-tolerant full-text search
- `supabase >=2.10.0` + `gotrue >=2.10.0` + `postgrest >=0.17.0` + `storage3 >=0.8.0` — Supabase client suite
- `anthropic >=0.40.0` — Claude AI provider
- `openai >=1.55.0` — OpenAI embeddings (text-embedding-3-large)
- `google-generativeai >=0.8.0` — Gemini Flash (ghost text, latency-sensitive tasks)
- `claude-agent-sdk >=0.1.0,<1.0` — Claude Agent SDK (in-process MCP tool execution)
- `structlog >=24.4.0` — structured logging
- `cryptography >=43.0.0` — Fernet encryption for BYOK API key storage
- `markdown-it-py >=3.0.0` — heading-based markdown chunking for KG population
- `orjson >=3.10.0` — fast JSON serialization

**Critical (Frontend):**
- `@supabase/supabase-js ^2.49.0` — auth (JWT), realtime subscriptions
- `axios ^1.7.0` — HTTP client for backend API
- `ai ^6.0.50` — Vercel AI SDK (streaming, SSE consumption)
- `zod ^3.24.0` — runtime schema validation
- `date-fns ^4.1.0` — date utilities
- `dompurify ^3.3.1` — HTML sanitization
- `mermaid ^11.12.2` — diagram rendering

## Configuration

**Environment (Backend):**
- Loaded from `backend/.env` via `pydantic-settings` BaseSettings
- `get_settings()` uses `@lru_cache` — call `get_settings.cache_clear()` in tests after env changes
- Template: `backend/.env.example`

**Key backend env vars:**
- `DATABASE_URL` — PostgreSQL+asyncpg connection string
- `REDIS_URL` — Redis connection URL
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
- `MEILISEARCH_URL`, `MEILISEARCH_API_KEY`
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` — optional BYOK fallback defaults
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_WEBHOOK_SECRET`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — Google Drive OAuth
- `ENCRYPTION_KEY` — Fernet key for API key storage (32-byte base64)
- `AUTH_PROVIDER` — `supabase` (default) or `authcore`
- `APP_ENV` — `development`, `staging`, `production`
- `AI_FAKE_MODE` — skip external AI calls in dev

**Environment (Frontend):**
- Loaded from `frontend/.env.local`
- Template: `frontend/.env.example`
- Key vars: Supabase anon key, `BACKEND_URL` (proxied via Next.js rewrite)

**Build:**
- Backend: `pyproject.toml` with `hatchling` build backend (`packages = ["src/pilot_space"]`)
- Frontend: `next.config.ts` — standalone output, API rewrite `/api/v1/*` → backend, image domains for Supabase storage

## Platform Requirements

**Development:**
- Docker + Docker Compose (Supabase stack: `infra/supabase/docker-compose.yml`, Redis+Meilisearch: `docker-compose.yml`)
- Supabase local on port 18000 (Kong gateway), Studio on port 54323
- Redis on port 6379, Meilisearch on port 7700
- Backend on port 8000, Frontend on port 3000

**Production:**
- Frontend: Docker standalone Next.js image (configured via `output: 'standalone'` in `next.config.ts`)
- Backend: Uvicorn with Docker (`backend/Dockerfile`)
- Database: Self-hosted Supabase stack (PostgreSQL 16 + Kong + GoTrue + PostgREST + Realtime + Storage)
- Connection pooler: Supavisor

---

*Stack analysis: 2026-03-07*
