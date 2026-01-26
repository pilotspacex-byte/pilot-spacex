# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Pilot Space** is an AI-augmented SDLC platform with a "Note-First" workflow where users brainstorm with AI in collaborative documents, and issues emerge naturally from refined thinking. The platform provides comprehensive project management (issues, cycles, modules, pages) enhanced with AI capabilities using a Claude Agent SDK.

**Core Differentiator**: Note canvas as the default home view, not a dashboard. AI acts as an embedded co-writing partner, not a bolt-on feature.

## Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| **Backend** | FastAPI + SQLAlchemy 2.0 (async) + Alembic | Pydantic v2 for validation |
| **Frontend** | React 18 + TypeScript + MobX + TailwindCSS | TipTap/ProseMirror for rich text |
| **Database** | PostgreSQL 16+ with pgvector | Soft deletion, UUID PKs, RLS |
| **AI** | Claude Agent SDK | No local LLM support |
| **Platform** | Supabase (Auth, Storage, Queues, DB) | Unified platform |
| **Cache** | Redis | Sessions, AI response cache |
| **Search** | Meilisearch | Typo-tolerant search |

## Development Commands

### Backend (Python 3.12+)

```bash
# Setup
cd backend
uv venv && source .venv/bin/activate
uv sync
pre-commit install

# Run development server
uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000

# Quality gates (must pass before merge)
uv run pyright && uv run ruff check && uv run pytest --cov=.

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Frontend (Node 20+, pnpm 9+)

```bash
# Setup
cd frontend
pnpm install

# Run development server
pnpm dev

# Quality gates (must pass before merge)
pnpm lint && pnpm type-check && pnpm test

# E2E tests
pnpm test:e2e
```

### Docker Compose (Full Stack)

```bash
docker compose up -d
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Supabase Studio: http://localhost:54323
```

## Project Structure

```
backend/src/pilot_space/
├── api/v1/routers/       # FastAPI routers (issues, notes, pages, ai, etc.)
├── api/v1/schemas/       # Pydantic request/response models
├── domain/
│   ├── models/           # Domain entities (Issue, Note, Page, Cycle, etc.)
│   └── services/         # Domain services (pure business logic)
├── application/
│   └── services/         # CQRS-lite service classes (command/query handlers)
├── ai/                   # AI layer
│   ├── orchestrator.py   # Task router + context manager
│   ├── providers/        # LLM provider adapters (OpenAI, Anthropic, etc.)
│   ├── agents/           # AI agents using Claude Agent SDK
│   └── rag/              # RAG pipeline (embeddings, retriever)
├── infrastructure/
│   ├── database/         # SQLAlchemy models, repositories, migrations
│   ├── cache/            # Redis
│   ├── queue/            # Supabase Queues (pgmq)
│   └── auth/             # Supabase Auth
└── integrations/         # GitHub, Slack

frontend/src/
├── app/                  # Next.js app router
├── features/             # Feature-based modules
│   ├── notes/            # Note canvas, ghost text, annotations
│   ├── issues/           # Issue views, AI context
│   └── workspace/        # Workspace settings
├── components/
│   ├── ui/               # Base shadcn/ui components
│   └── editor/           # TipTap extensions
├── stores/               # MobX stores
└── services/             # API clients
```

## Key Design Decisions

| Decision | Reference |
|----------|-----------|
| FastAPI replaces Django entirely | DD-001 |
| Claude Agent SDK orchestration (Anthropic required, OpenAI for embeddings, Gemini optional) | DD-002 |
| Critical-only approval model for AI actions (auto-execute non-destructive, approve destructive) | DD-003 |
| MVP integrations: GitHub + Slack only | DD-004 |
| No real-time collaboration in MVP (last-write-wins) | DD-005 |
| Unified AI PR Review (architecture + code + security + performance + docs) | DD-006 |
| Provider routing: Claude→code, Gemini→latency, OpenAI→embeddings | DD-011 |
| Note-First, not Ticket-First workflow | DD-013 |
| AI confidence tags: Recommended/Default/Current/Alternative | DD-048 |
| Supabase platform (Auth, Storage, Queues) | Session 2026-01-22 |
| CQRS-lite with Service Classes + Payloads | Session 2026-01-22 |
| MobX for frontend state (not Zustand) | Session 2026-01-22 |
| SSE for AI streaming (not WebSocket) | research.md |

## Quality Gates

All code must pass before merge:

**Non-negotiables**:
- Type checking in strict mode (pyright/TypeScript)
- Test coverage > 80%
- No N+1 queries, no blocking I/O in async functions
- File size limit: 700 lines maximum
- No TODOs, mocks, or placeholder code in production paths
- AI features respect human-in-the-loop principle
- RLS policies verified for multi-tenant data

## Architecture Patterns

**Load `docs/dev-pattern/45-pilot-space-patterns.md` first** for project-specific patterns.

### Backend Patterns
- **CQRS-lite**: Service Classes with Payloads (`CreateIssueService.execute(payload)`)
- **Repository**: Generic + Specific (`BaseRepository[T]`)
- **DI**: `dependency-injector` library
- **Errors**: RFC 7807 Problem Details

### AI Agent Patterns
- **SDK**: Claude Agent SDK for orchestration (`query()` for one-shot, `ClaudeSDKClient` for multi-turn)
- **Routing**: Task-specific provider selection per DD-011 (Claude→code, Gemini→latency, OpenAI→embeddings)
- **BYOK**: Users provide API keys (Anthropic required, OpenAI required for search, Gemini optional)
- **Approval**: Human-in-the-loop per DD-003 (auto-execute non-destructive, approve critical actions)
- **Streaming**: SSE via FastAPI StreamingResponse

### Frontend Patterns
- **State**: MobX for client state, TanStack Query for server state
- **Structure**: Feature folders (`features/{domain}/`)
- **Editor**: TipTap Extension per feature
- **Realtime**: Supabase Realtime per-workspace subscription

## Key Entities

| Entity | Purpose |
|--------|---------|
| **Note** | Block-based document with AI annotations, primary entry for Note-First workflow |
| **NoteAnnotation** | AI suggestions in right margin, linked to specific blocks |
| **Issue** | Work item with state machine, AI metadata, integration links |
| **AIContext** | Aggregated context for issue (related docs, code, tasks with Claude Code prompts) |
| **Cycle** | Sprint container with velocity/burndown metrics |
| **Module** | Epic grouping for issues |

## Documentation Entry Points

### Specifications
| Topic | Document |
|-------|----------|
| **MVP specification (P0+P1)** | `specs/001-pilot-space-mvp/spec.md` |
| **MVP implementation plan** | `specs/001-pilot-space-mvp/plan.md` |
| **Phase 2 specification (P2)** | `specs/002-pilot-space-phase2/spec.md` |
| **Phase 3 specification (P3)** | `specs/003-pilot-space-phase3/spec.md` |
| **Data model** | `specs/001-pilot-space-mvp/data-model.md` |
| **UI/UX specification** | `specs/001-pilot-space-mvp/ui-design-spec.md` |
| **Technical research** | `specs/001-pilot-space-mvp/research.md` |

### Architecture (docs/architect/)
| Topic | Document |
|-------|----------|
| **🔍 AI QA Retrieval Index** | `docs/architect/README.md#ai-qa-retrieval-index` - **START HERE to find any architecture info** |
| **Architecture overview** | `docs/architect/README.md` |
| **Feature-to-component mapping** | `docs/architect/feature-story-mapping.md` |
| **Backend architecture** | `docs/architect/backend-architecture.md` |
| **Frontend architecture** | `docs/architect/frontend-architecture.md` |
| **AI layer (16 agents)** | `docs/architect/ai-layer.md` |
| **Infrastructure (Supabase)** | `docs/architect/infrastructure.md` |
| **Supabase integration** | `docs/architect/supabase-integration.md` |
| **RLS security patterns** | `docs/architect/rls-patterns.md` |
| **Design patterns** | `docs/architect/design-patterns.md` |
| **Features checklist** | `docs/architect/FEATURES_CHECKLIST.md` |

### Deployment
| Topic | Document |
|-------|----------|
| **Self-hosted Supabase** | `infra/supabase/README.md` |
| **Docker Compose (dev)** | `infra/docker/docker-compose.yml` |
| **Kubernetes** | `infra/k8s/` |
| **Terraform modules** | `infra/terraform/modules/` |

### Standards & Patterns
| Topic | Document |
|-------|----------|
| **Project constitution** | `.specify/memory/constitution.md` |
| **Architecture decisions** | `docs/DESIGN_DECISIONS.md` |
| **AI capabilities** | `docs/AI_CAPABILITIES.md` |
| **Dev patterns (start here)** | `docs/dev-pattern/README.md` |
| **Pilot Space patterns** | `docs/dev-pattern/45-pilot-space-patterns.md` |
| **MobX patterns** | `docs/dev-pattern/21c-frontend-mobx-state.md` |

## Dev-Pattern Quick Reference

For any new feature, load patterns in this order:

```text
1. feature-story-mapping.md   → Find US-XX and its components
2. 45-pilot-space-patterns.md → Project-specific overrides
3. Domain-specific pattern    → (e.g., 07-repository, 20-component)
4. Cross-cutting patterns     → (e.g., 26-di, 06-validation)
```

**User Story to Architecture**: See `docs/architect/feature-story-mapping.md` for:
- 18 user stories mapped to architecture components (MVP: 6, Phase 2: 9, Phase 3: 3)
- Data entities per feature
- AI agents per user story
- Implementation phases

**Pilot Space Overrides** (from 45):
| Standard Pattern | Override |
|------------------|----------|
| 21a: Zustand | MobX |
| 17: Custom JWT | Supabase Auth + RLS |
| 10: Kafka | Supabase Queues |

## Active Technologies
- Python 3.12+ (Backend), TypeScript 5.x (Frontend) (001-pilot-space-mvp)
- Python 3.12+ (Backend) + FastAPI, SQLAlchemy 2.0 (async), claude-agent-sdk>=1.0,<2.0, anthropic, openai, google-generativeai (004-mvp-agents-build)
- PostgreSQL 16+ with pgvector, Redis (sessions), Supabase Vault (key encryption) (004-mvp-agents-build)

## Recent Changes
- 001-pilot-space-mvp: Supabase platform, Claude Agent SDK, MobX, CQRS-lite
- docs/architect/: Updated to align with constitution v1.1.0, added feature-story-mapping.md, rls-patterns.md
