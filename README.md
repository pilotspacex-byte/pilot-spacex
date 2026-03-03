# Pilot Space

> AI-Augmented SDLC Platform · Note-First Workflow · BYOK

Pilot Space embeds an AI agent directly into your software development lifecycle. Write freely in a block-based note canvas — AI provides inline completions, extracts issues from prose, annotates ambiguous requirements, and reviews PRs. Human-in-the-loop on all consequential actions. No AI cost pass-through: bring your own API keys.

**Status**: `v0.1.0-alpha.1` · MIT License

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [1. Supabase (Auth + Database)](#1-supabase-auth--database)
  - [2. Configure Environment](#2-configure-environment)
  - [3. Start All Services](#3-start-all-services)
  - [4. Rebuild After Code Changes](#4-rebuild-after-code-changes)
- [Development Commands](#development-commands)
- [Project Structure](#project-structure)
- [AI Agent System](#ai-agent-system)
- [Quality Gates](#quality-gates)
- [Documentation](#documentation)
- [License](#license)

---

## Overview

Pilot Space is built on the **Note-First paradigm** — users think and write in a free-form canvas first; AI helps structure that content into actionable issues, tasks, and documentation later. The workflow is:

1. **Capture** — Write freely in the block-based Note Canvas
2. **AI Assists** — Ghost text completions appear after a 500ms pause; margin annotations flag ambiguity after 2s
3. **Extract** — `\extract-issues` categorizes text into Explicit/Implicit/Related issues with confidence scores
4. **Approve** — Human-in-the-loop gates all consequential AI actions (create, update, delete)
5. **Track** — Issues link back to source text via `[PS-42]` inline badges and rainbow-border highlights

Scale: 5–100 members per workspace. BYOK model: Anthropic Claude, Google Gemini, OpenAI — workspace-level keys, AES-256-GCM encrypted at rest.

---

## Features

### Note Canvas
- Block-based rich text editor (TipTap/ProseMirror) with 13+ extensions
- **Ghost text** — inline AI completions at 40% opacity (Tab to accept, Right Arrow for word-by-word, Escape to dismiss)
- **Margin annotations** — AI detects ambiguous text and surfaces clarifying questions in the margin
- **Slash commands** (`\`) — 13 AI commands: extract-issues, improve-writing, summarize, generate-diagram, and more
- **Issue extraction** — streams candidates with confidence scores; rainbow-border highlights link source text to created issues
- **Realtime collaboration** — Yjs CRDT with Supabase Realtime; ghost text is local-only

### Issue Tracking
- Full state machine: Backlog → Todo → In Progress → In Review → Done
- PropertyBlock editor — structured properties (state, priority, labels, assignees, cycle) inside TipTap
- Bidirectional links to notes via `NoteIssueLink` (EXTRACTED / CREATED / REFERENCED)
- AI commands from issue detail: Generate description, Decompose tasks, Find duplicates, Recommend assignee

### AI Chat (ChatView)
- Real-time SSE conversation with `PilotSpaceAgent` orchestrator
- 24 slash-command skills: `\extract-issues`, `\enhance-issue`, `\generate-docs`, `\review-code`, `\daily-standup`, and more
- Agent mentions: `@pr-review`, `@doc-generator`, `@ai-context`
- Task decomposition panel — live step-by-step progress for multi-turn tasks
- Extended thinking blocks, tool call timelines, structured result cards
- Session history with resume (`\resume`) and fork

### Chat Context Attachments (Feature 020)
- Attach local files (PDF, DOCX, images, code, plain text) to any conversation turn — injected as Claude content blocks
- Google Drive integration: OAuth PKCE flow per workspace, Drive file browser with folder navigation and search, import Docs/Sheets/Slides (auto-exported to PDF/CSV) or raw files up to per-type size limits
- Silent token refresh: access tokens refreshed proactively 5 min before expiry, with single mid-request retry on 401
- Attachment lifecycle: 24-hour TTL, retry on upload failure, two-phase ownership/expiry error distinction (403 vs 400)
- Guest restriction: attachment upload and Drive OAuth blocked for guest-role members

### GitHub Integration
- Webhook-triggered PR review: 5-dimension analysis (Architecture, Code Quality, Security, Performance, Docs)
- Severity-based comment filtering: only `critical` and `major` are posted as blocking
- OAuth per workspace (BYOK scoping)

### Human-in-the-Loop (DD-003)
| Tier | Examples | UI |
|------|---------|-----|
| AUTO | `list_*`, `get_*`, `search_*` | No prompt |
| DEFAULT | `create_issue`, `update_note`, `post_comment` | Inline approval card (24h) |
| CRITICAL | `delete_issue`, `archive_workspace`, `merge_pr` | Blocking modal (5-min auto-reject) |

### Multi-Tenant Security
- PostgreSQL Row-Level Security on every table — database-level isolation, not just application-layer
- Four roles: owner, admin, member, guest
- Agent filesystem sandboxed per `user_id` + `workspace_id`
- BYOK keys: PBKDF2-HMAC-SHA256 (600K iterations) + Fernet AES-128-CBC

---

## Architecture

```
Frontend (Next.js 16, port 3000)
  └── App Router · React 19 · MobX + TanStack Query
  └── Note Canvas (TipTap + 13 extensions + Yjs)
  └── ChatView (SSE · 14 event types · approval overlay)
         │
         │ REST + SSE
         ▼
Backend (FastAPI, port 8000)
  └── 5-layer Clean Architecture:
      Presentation → Application (CQRS-lite) → Domain → Infrastructure → AI
  └── PilotSpaceAgent orchestrator (Claude Agent SDK)
  └── 8 in-process MCP servers · 33 tools
  └── GhostTextService (independent path, <2.5s SLA)
         │
         ├── PostgreSQL 16 (Supabase, port 54322)  pgvector · RLS · pgmq
         ├── Redis 7          (port 6379)           session cache · rate limit
         ├── Meilisearch 1.6  (port 7700)           full-text search
         └── Supabase Auth    (GoTrue · JWT · RLS)
```

**Request flows:**
- **Standard CRUD**: REST → Router → Service → Domain Entity → Repository → Commit
- **AI Conversation**: POST `/api/v1/ai/chat` → PilotSpaceAgent → Claude Agent SDK → MCP tools → SSE events
- **Ghost Text**: GET `/api/v1/ai/ghost-text` → GhostTextService (bypasses orchestrator) → Haiku/Flash → JSON
- **PR Review**: GitHub webhook → pgmq → PRReviewSubagent → 5-dimension analysis → GitHub comments

---

## Tech Stack

### Backend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI + uvicorn | 0.115+ |
| ORM | SQLAlchemy 2.0 async | 2.0+ |
| Validation | Pydantic v2 | 2.10+ |
| DI | dependency-injector | 4.43+ |
| Migrations | Alembic | 1.14+ |
| Runtime | Python | 3.12+ |
| AI SDK | Claude Agent SDK | 0.1+ |
| AI Providers | Anthropic, Google Generative AI, OpenAI | latest |

### Frontend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Next.js (App Router) | 16.x |
| Runtime | React | 19.x |
| UI State | MobX | 6+ |
| Server State | TanStack Query | 5+ |
| Editor | TipTap / ProseMirror | 3.16+ |
| Collab | Yjs + y-prosemirror | 13+ |
| Styling | TailwindCSS v4 + shadcn/ui | 4.x |
| Components | Radix UI | latest |
| Language | TypeScript | 5.3+ |

### Infrastructure
| Component | Technology |
|-----------|------------|
| Database | PostgreSQL 16+ with pgvector (via Supabase) |
| Auth | Supabase Auth (GoTrue) + RLS |
| Cache | Redis 7 |
| Search | Meilisearch 1.6 |
| Queues | Supabase Queues (pgmq + pg_cron) |
| Realtime | Supabase Realtime (Phoenix WebSocket) |

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker | 24+ | All services run in containers |
| Docker Compose | 2.x+ | Bundled with Docker Desktop |

That's it. Everything else (PostgreSQL, Redis, Meilisearch, backend, frontend) runs inside Docker.

---

## Setup

All services start from `infra/docker/`. The full stack is:

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js application |
| Backend | 8000 | FastAPI application |
| PostgreSQL | 5432 | Database (pgvector) |
| Redis | 6379 | Session cache |
| Meilisearch | 7700 | Full-text search |

### 1. Supabase (Auth + Database)

Pilot Space uses Supabase for authentication, Row-Level Security, Realtime, and Storage. Choose one option:

**Option A — Supabase Cloud (recommended for quick start)**

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Project Settings → API** and copy:
   - Project URL
   - `anon` public key
   - `service_role` secret key
   - JWT secret

**Option B — Self-hosted Supabase via Docker**

Follow the official self-hosting guide: https://supabase.com/docs/guides/self-hosting/docker

```bash
# Clone the Supabase repo and start the stack
git clone --depth 1 https://github.com/supabase/supabase
cd supabase/docker
cp .env.example .env   # Edit credentials as needed
docker compose up -d
```

Self-hosted services will be available at:
- API: `http://localhost:54321`
- Studio: `http://localhost:54323`
- Database: `postgresql://postgres:postgres@localhost:54322/postgres`

Get your keys from `supabase status` (CLI) or the Studio → Settings → API page.

### 2. Configure Environment

```bash
cd infra/docker
cp .env.example .env
```

Edit `.env` with your values. Required fields:

```env
# Supabase — paste from Step 1
SUPABASE_URL=https://<project-ref>.supabase.co    # or http://localhost:54321 for self-hosted
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_KEY=<service_role key>
SUPABASE_JWT_SECRET=<jwt secret>

# AI Providers (BYOK — bring your own keys)
ANTHROPIC_API_KEY=sk-ant-...       # Required for AI features
GOOGLE_API_KEY=AIza...             # Required for ghost text (Gemini Flash) + embeddings
OPENAI_API_KEY=sk-...              # Required for semantic search embeddings

# Security
ENCRYPTION_KEY=<32-byte base64 Fernet key>
```

Generate an encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Development shortcut**: Set `AI_FAKE_MODE=true` in `.env` to use fake AI responses without API keys.

### 3. Start All Services

```bash
cd infra/docker
docker compose up -d
```

This starts PostgreSQL, Redis, Meilisearch, runs Alembic migrations, then starts the backend and frontend.

Check status:
```bash
docker compose ps
docker compose logs -f backend    # tail backend logs
docker compose logs -f frontend   # tail frontend logs
```

Once all containers are healthy:
- App: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Meilisearch: `http://localhost:7700`

### 4. Rebuild After Code Changes

```bash
# Rebuild a single service
docker compose build backend
docker compose up -d backend

# Rebuild everything
docker compose build && docker compose up -d
```

---

## Development Commands

### Backend

```bash
# Quality gates (run before every commit)
uv run pyright && uv run ruff check && uv run pytest --cov=.

# Individual gates
uv run pyright              # Type checking
uv run ruff check           # Linting
uv run ruff check --fix     # Auto-fix linting
uv run pytest               # Tests
uv run pytest --cov=. -v    # Tests with coverage

# Database
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic heads               # Verify single head

# Dev server with auto-reload
uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
# Quality gates
pnpm lint && pnpm type-check && pnpm test

# Individual gates
pnpm lint                   # ESLint
pnpm lint:fix               # Auto-fix
pnpm type-check             # TypeScript (tsc --noEmit)
pnpm test                   # Vitest (unit)
pnpm test:coverage          # With coverage report
pnpm test:e2e               # Playwright E2E
pnpm test:e2e:ui            # Playwright with UI

# Dev server
pnpm dev
pnpm build && pnpm start    # Production build
```

---

## Project Structure

```
pilot-space/
├── backend/
│   ├── src/pilot_space/
│   │   ├── api/v1/              # FastAPI routers + Pydantic schemas
│   │   ├── domain/              # Rich domain entities + domain services
│   │   ├── application/services/ # CQRS-lite service modules
│   │   ├── infrastructure/      # SQLAlchemy models, repositories, Redis, migrations
│   │   └── ai/                  # PilotSpaceAgent + subagents + MCP tools + SDK
│   │       ├── agents/          # Orchestrator + subagents (PR review, doc gen, AI context)
│   │       ├── mcp/             # 6 MCP servers · 33 tools
│   │       ├── sdk/             # Claude Agent SDK integration (hooks, permissions, sessions)
│   │       ├── skills/          # Skill discovery + executor (24 skills)
│   │       ├── providers/       # Model routing (DD-011) + BYOK validation
│   │       └── infrastructure/  # Cost tracker, key storage, circuit breaker, rate limiter
│   ├── alembic/versions/        # Database migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/                 # Next.js App Router (auth, workspace/[slug], public)
│       ├── features/
│       │   ├── notes/           # Note Canvas + TipTap extensions + ghost text
│       │   ├── issues/          # Issue tracking + PropertyBlock editor
│       │   ├── ai/              # ChatView + approval overlay + session management
│       │   ├── cycles/          # Sprint management
│       │   └── github/          # GitHub integration UI
│       ├── stores/              # MobX: RootStore, PilotSpaceStore, GhostTextStore, …
│       ├── components/          # Shared UI (shadcn/ui primitives + editor components)
│       └── services/api/        # Typed API clients
├── infra/docker/
│   ├── docker-compose.yml       # Full stack: postgres, redis, meilisearch, backend, frontend
│   ├── .env.example             # Environment template — copy to .env and fill in values
│   ├── Dockerfile.backend       # FastAPI image
│   ├── Dockerfile.frontend      # Next.js image
│   ├── Dockerfile.migration     # Alembic one-shot migration runner
│   └── init-scripts/            # PostgreSQL init SQL (extensions, etc.)
├── docs/
│   ├── wiki/                    # 19 feature wiki docs
│   ├── architect/               # Architecture decision records
│   └── dev-pattern/             # 45 dev patterns
├── specs/                       # Product specs (MVP, data model, UI/UX)
└── CLAUDE.md                    # AI agent and developer conventions
```

---

## AI Agent System

The AI layer is built on the **centralized orchestrator pattern** (DD-086): one `PilotSpaceAgent` handles all user-facing AI interactions.

```
PilotSpaceAgent (orchestrator)
  │
  ├── IntentClassifier (~1ms, regex-based, no LLM call)
  │     └── skill_invocation | agent_mention | free_conversation
  │
  ├── PromptAssembler (6-layer system prompt)
  │     base → workspace → role → document → history → message
  │
  ├── Claude Agent SDK execution loop
  │     ├── PreToolHook → PermissionHandler (AUTO / DEFAULT / CRITICAL)
  │     ├── 8 in-process MCP servers (33 tools, note/issue/project/comment/…)
  │     ├── PostToolHook → cost tracking + audit
  │     └── SSEDeltaBuffer (50ms batching) → 14 SSE event types
  │
  ├── Skills (24, YAML-defined, single-turn stateless)
  │     extract-issues · enhance-issue · improve-writing · summarize
  │     generate-docs · review-code · daily-standup · generate-diagram · …
  │
  ├── Subagents (multi-turn, stateful)
  │     @pr-review       → 5-dimension GitHub PR review
  │     @doc-generator   → multi-type documentation generation
  │     @ai-context      → iterative context aggregation
  │     \plan            → task decomposition with DAG validation
  │
  └── GhostTextService (independent path, bypasses orchestrator)
        500ms debounce → Haiku/Flash → <2.5s total latency
```

**Provider routing** (DD-011):
| Task | Model |
|------|-------|
| PR Review, AI Context | Claude Opus 4.5 |
| Issue ops, Doc gen, Conversation | Claude Sonnet |
| Ghost Text, Assignee scoring | Claude Haiku / Gemini Flash |
| Semantic search embeddings | OpenAI text-embedding-3-large |

**Resilience**: Circuit breaker (3 failures → OPEN → 30s → probe) + exponential backoff (1–60s, ±30% jitter, 3 retries) + graceful degradation (AI features fail-open, CRUD unaffected).

For full AI architecture documentation: `backend/src/pilot_space/ai/README.md` and `docs/wiki/agent-index.md`.

---

## Quality Gates

| Gate | Command | Threshold |
|------|---------|-----------|
| Backend type check | `uv run pyright` | Zero errors |
| Backend lint | `uv run ruff check` | Zero violations |
| Backend tests | `uv run pytest --cov=.` | >80% coverage |
| Frontend lint | `pnpm lint` | Zero errors |
| Frontend type check | `pnpm type-check` | Zero errors |
| Frontend tests | `pnpm test` | >80% coverage |

**Hard constraints enforced by pre-commit hooks:**
- File size limit: 700 lines (Python, TS, JS)
- No TODOs, mocks, or placeholder functions
- Conventional commit format required

---

## Documentation

| Topic | Location |
|-------|----------|
| Feature wiki (19 docs) | `docs/wiki/` |
| Architecture overview | `docs/architect/README.md` |
| AI agent architecture | `docs/wiki/agent-index.md` |
| Dev patterns (45) | `docs/dev-pattern/README.md` |
| Design decisions (88) | `docs/DESIGN_DECISIONS.md` |
| Data model (21 entities) | `specs/001-pilot-space-mvp/data-model.md` |
| UI/UX spec | `specs/001-pilot-space-mvp/ui-design-spec.md` |
| Backend guide | `backend/README.md` |
| Frontend guide | `frontend/README.md` |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
