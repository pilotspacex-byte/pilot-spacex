# Pilot Space - AI-Augmented SDLC Platform

**Built on "Note-First" paradigm** - Think first, structure later.

---

## Quick Reference

### Role-Based Navigation

**Backend developers** → See `backend/README.md` for:
- Backend architecture & patterns
- CQRS-lite service design
- RLS security requirements
- Quality gates & testing

**Frontend developers** → See `frontend/README.md` for:
- Frontend architecture & patterns
- MobX + TanStack Query state management
- TipTap editor extensions
- Accessibility requirements

**All developers** → Continue reading this file for:
- Project overview & business context
- Technology stack & infrastructure
- AI agent architecture
- Documentation entry points

### Critical Constants

| Constraint | Value | Enforcement | Configuration |
|------------|-------|-------------|----------------|
| Code file size limit | 700 lines (Python, TS, JS) | Pre-commit hook | Hard-coded; excludes *.md docs |
| Test coverage | >80% (strictly greater) | pytest-cov / vitest | pytest.ini / vitest.config.ts |
| Token budget/session | 8K tokens | AI session manager | Per-user session (env var) |
| Auto-save debounce | 2s (fixed) | Frontend | Frontend constant (not configurable) |
| Ghost text trigger | 500ms pause | GhostTextAgent | Frontend constant (not configurable) |

### Quality Gates

**Backend**: `uv run pyright && uv run ruff check && uv run pytest --cov=.`
**Frontend**: `pnpm lint && pnpm type-check && pnpm test`

**These gates protect production stability and prevent technical debt accumulation.** Bypassing checks has historically led to 3-5 hour debugging sessions. Consistent enforcement correlates with 85% reduction in post-deployment hotfixes.

---

## Project Overview

AI-augmented SDLC on a "Note-First" paradigm — users write in a note canvas, AI provides ghost text completions, extracts issues from text, and reviews PRs. Human-in-the-loop on all destructive actions (DD-003). BYOK — no AI cost pass-through. Scale: 5-100 members/workspace. Details: `docs/BUSINESS_CONTEXT.md`

---

## Technology Stack

### Backend

| Component | Technology | Version | Decision |
|-----------|------------|---------|----------|
| Framework | FastAPI | 0.110+ | DD-001 (async-first stack) |
| ORM | SQLAlchemy 2.0 (async) | 2.0+ | DD-001 |
| Validation | Pydantic v2 | 2.6+ | DD-001 |
| DI | dependency-injector | 4+ | DD-064 |
| Runtime | Python | 3.12+ | — |

### Frontend

| Component | Technology | Version | Decision |
|-----------|------------|---------|----------|
| Framework | Next.js (App Router) | 16.x | — |
| Runtime | React | 19.x | — |
| UI State | MobX | 6+ | DD-065 |
| Server State | TanStack Query | 5+ | DD-065 |
| Styling | TailwindCSS + shadcn/ui | 3.4+ | — |
| Rich Text | TipTap/ProseMirror | 3.16+ | — |
| Language | TypeScript | 5.3+ | — |

### AI & Orchestration

| Component | Technology | Decision |
|-----------|------------|----------|
| Orchestration | Claude Agent SDK | DD-002, DD-086 |
| Primary LLM | Anthropic Claude (BYOK) | DD-002 |
| Latency LLM | Google Gemini Flash (BYOK) | DD-011 |
| Embeddings | Google Gemini gemini-embedding-001 (BYOK) | DD-011, DD-070 |
| Streaming | SSE via FastAPI StreamingResponse | DD-066 |

### Infrastructure & Platform

| Component | Technology | Decision |
|-----------|------------|----------|
| Database | PostgreSQL 16+ with pgvector | DD-060 |
| Auth | Supabase Auth (GoTrue) + RLS | DD-061 |
| Cache | Redis 7 (30-min session TTL; 7-day AI TTL) | — |
| Search | Meilisearch 1.6 (typo-tolerant) | — |
| Queues | Supabase Queues (pgmq + pg_cron) | DD-069 |
| Storage | Supabase Storage (S3-compatible) | DD-060 |
| Realtime | Supabase Realtime (Phoenix WebSocket) | DD-060 |
| Secrets | Supabase Vault (AES-256-GCM) | DD-060 |

---

## Production Architecture Overview

### Infrastructure Topology

Three-tier containerized architecture: Frontend (Next.js 16 App Router) → Backend (FastAPI on port 8000) → Data (PostgreSQL 16+ with RLS, Redis, Meilisearch).

**Frontend Tier**: SSR, REST API for CRUD, SSE for AI streaming. Auth via Supabase JWT (cookies for SSE, Bearer for REST).

**Backend Tier**: Clean Architecture with 5 layers: Presentation → Application (CQRS-lite) → Domain → Infrastructure → AI. PilotSpaceAgent orchestrator runs within this tier.

**Data Tier**: PostgreSQL 16+ with RLS for multi-tenant isolation. pgvector for 768-dim HNSW-indexed embeddings. Redis for session/AI caching. Meilisearch for full-text search. Supabase Queues (pgmq) for async jobs.

**External Services**: Anthropic Claude API, Google Gemini API, GitHub API, Slack API (all BYOK where applicable).

### Request Flows

**Standard CRUD**: Frontend → REST → Middleware → Router → Service → Domain Entity → Repository → Commit + Events → Response.

**AI Conversation**: Frontend → SSE POST `/api/v1/ai/pilot-space/chat` → PilotSpaceAgent syncs note → SDK processes with MCP tools → Tool handler creates operation payload → Backend transforms → SSE events → Frontend store updates.

**SSE Events**: message_start, text_delta, tool_use, tool_result, task_progress, approval_request, content_update, message_stop, error.

**Ghost Text** (<2.5s total): 500ms typing pause triggers → SSE GET → GhostTextAgent (Gemini Flash) responds within 1.5s → Streaming tokens → TipTap renders at 40% opacity → Tab accept, Escape dismiss.

**AI PR Review** (<5min): GitHub webhook → Queue (pgmq) → PRReviewAgent (Claude Opus) → Comments posted to GitHub PR with severity tags → SSE notification.

### Note-First Data Flow

1. **Capture**: User opens app → Note Canvas is home. User writes freely in block-based editor.
2. **AI Assists**: 500ms pause triggers ghost text. Margin annotations detect ambiguity. Threaded AI discussions per block.
3. **Extract**: `extract_issues` categorizes items as Explicit/Implicit/Related. Rainbow-bordered boxes wrap source text.
4. **Approve**: Human-in-the-loop (DD-003). User previews, edits, approves. Destructive actions always require approval.
5. **Track**: Issues link back via `NoteIssueLink` (EXTRACTED). Inline `[PS-42]` badges. Bidirectional updates.

### Multi-Tenant Isolation

**RLS**: Every table has Row-Level Security. Policies use `auth.uid()` + `auth.user_workspace_ids()`. Four roles: owner, admin, member, guest. Default-deny.

**RLS violations expose sensitive data across workspaces—this is our core security boundary.** Database-level enforcement prevents application-layer bypass.

**Agent Sandboxing**: Isolated workspace at `/sandbox/{user_id}/{workspace_id}/` with `.claude/` and `notes/` directories. API keys encrypted via Supabase Vault (AES-256-GCM).

**Session Security**: 256-bit session IDs, IP binding. **User Sessions**: Redis hot cache (30-min sliding expiration) + PostgreSQL durable storage (24h TTL for resumption). **Chat Sessions**: PostgreSQL storage (24h TTL), optional Redis cache.

---

## AI Agent Architecture

**Complete AI layer architecture, agents, skills, MCP tools, and provider routing**: See `backend/src/pilot_space/ai/README.md`

**Design Philosophy (DD-086)**: Centralized conversational agent. Single `PilotSpaceAgent` orchestrator routes to skills (single-turn, stateless) and subagents (multi-turn, stateful).

**Agent Roster**: 1 orchestrator (PilotSpaceAgent) + 3 subagents (PR Review, AI Context, Doc Generator) + 1 independent (GhostText for <2s latency)

**Skills (8)**: extract-issues, enhance-issue, improve-writing, summarize, find-duplicates, recommend-assignee, decompose-tasks, generate-diagram

**MCP Tools**: 8 servers (note, note_content, issue, issue_relation, project, comment, interaction, ownership) with operation payloads pattern

**Provider Routing (DD-011)**: Task-based selection (PR review→Opus, AI context→Opus, code gen→Sonnet, ghost→Flash) + per-task fallback chains

**Approval Workflow (DD-003)**: Non-destructive→auto, content creation→configurable, destructive→always require

**Resilience**: Exponential backoff (1-60s, 3 retries) + circuit breaker (3 failures→OPEN, 30s recovery) + cost tracking with 90% alerts

---

## Design Decisions

Key DDs are referenced inline above (DD-001, DD-003, DD-011, DD-060–DD-070, DD-086–DD-088). **Full list (88 decisions)**: `docs/DESIGN_DECISIONS.md`

---

## Development Commands

### Backend (Python 3.12+)

**Setup**: `cd backend && uv venv && source .venv/bin/activate && uv sync && pre-commit install`
**Dev server**: `uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000`
**Quality gates**: `uv run pyright && uv run ruff check && uv run pytest --cov=.`
**Migrations**: `cd backend && alembic revision --autogenerate -m "Description"` then `alembic upgrade head`

### Frontend (Node 20+, pnpm 9+, TypeScript 5.3+, Next.js 16+)

**Setup**: `cd frontend && pnpm install`
**Dev server**: `pnpm dev`
**Quality gates**: `pnpm lint && pnpm type-check && pnpm test`
**E2E**: `pnpm test:e2e`

### Docker Compose

`docker compose up -d` → Frontend :3000, Backend API :8000/docs, Supabase Studio :54323

---

## Project Structure

Full structure: `docs/architect/project-structure.md`

### Backend (`backend/src/pilot_space/`)

5-layer Clean Architecture:

- **api/v1/** — FastAPI routers + Pydantic v2 schemas + middleware (auth, CORS, rate limiting, RFC 7807 errors)
- **domain/** — Rich domain entities (Issue, Note, Cycle) with behavior + validation, domain services (pure logic, no I/O)
- **application/services/** — Domain service modules: note, issue, cycle, ai_context, annotation, discussion, integration, task, role_skill, memory, onboarding, and more
- **ai/** — PilotSpaceAgent orchestrator + subagents, Claude Agent SDK integration, MCP tools, providers, session management, cost tracking
- **infrastructure/** — SQLAlchemy models, repositories, Alembic migrations (`backend/alembic/versions/`), RLS helpers, Redis cache, pgmq queue, Supabase JWT auth

*Full structure with current counts: see `backend/README.md`*

### Frontend (`frontend/src/`)

Feature-based architecture:

- **app/** — Next.js App Router: auth, workspace/[slug], public routes
- **features/** — Domain modules: notes (canvas + TipTap extensions + ghost text), issues, ai (ChatView), approvals, cycles, github, costs, settings, homepage, onboarding, spaces, integrations, projects
- **components/** — Shared UI (shadcn/ui primitives), editor (canvas + toolbar + annotations + TOC), layout (shell + sidebar + header)
- **stores/** — MobX: RootStore, AuthStore, UIStore, WorkspaceStore + AI stores: PilotSpaceStore (unified orchestrator), GhostTextStore, PRReviewStore, AIContextStore, ApprovalStore, CostStore, SessionListStore, MarginAnnotationStore, and more
- **services/api/** — Typed API clients with RFC 7807 error handling

*Full structure: see `frontend/README.md`*

---

## Quality Standards

### Non-Negotiable Standards

Write tests for all new features and bug fixes. **80% coverage catches 85% of regressions before deployment.** This metric directly correlates with production stability.

| Standard | Enforcement |
|----------|-------------|
| Strict type checking (pyright / TypeScript strict) | Pre-commit; CI |
| Test coverage > 80% | pytest-cov; vitest |
| No N+1 queries | SQLAlchemy eager loading; review |
| No blocking I/O in async functions | pyright analysis; review |
| File size: 700 lines max for code file | Pre-commit |
| No TODOs; mocks; placeholder code | Pre-commit |
| AI features respect DD-003 (human-in-the-loop) | PermissionHandler; review |
| RLS verified for multi-tenant data | DB enforcement; integration tests |
| Conventional commits | feat\|fix\|refactor\|docs\|test\|chore(scope): description |

**Blocking calls in async context cause thread starvation under load.** Can degrade API latency by 10-50x.

---

## Architecture Patterns

**Complete patterns with code examples**: See `docs/dev-pattern/45-pilot-space-patterns.md` (project-specific patterns)

### Backend Patterns

**See `backend/README.md` for complete backend patterns**

**Quick Summary**: CQRS-lite (Service.execute), Repository (RLS-enforced), Unit of Work, Domain Events, DI (dependency-injector), RFC 7807 Errors, Pydantic v2 Validation, Supabase Auth+RLS

### AI Agent Patterns

**See `backend/src/pilot_space/ai/README.md` for complete AI patterns**

**Quick Summary**: Centralized agent (PilotSpaceAgent), SDK integration (query/multi-turn), Skill system (YAML), MCP tools (operation payloads), Provider routing (DD-011), Approval (DD-003), SSE streaming, Resilience (retry+circuit breaker), Session management (Redis+PostgreSQL)

### Frontend Patterns

**See `frontend/README.md` for complete frontend patterns**

**Quick Summary**: State split (MobX UI/TanStack server), Feature folders, 13 TipTap extensions, Optimistic updates, SSE handling (custom client), Auto-save (2s debounce), WCAG 2.2 AA Accessibility

---

## UI/UX Design System

Warm, Capable, Collaborative. Primary: `#29A386` (teal-green), AI accent: `#6B8FAD` (dusty blue), background: `#FDFCFA`. Geist font, 4px grid, squircle corners. Full spec: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0 / `frontend/README.md`

---

## Key Entities

**Full data model (21 entities)**: `specs/001-pilot-space-mvp/data-model.md`

**Core Entities**: Note (block-based TipTap), Issue (state machine), Cycle (sprint container), Project, Module (epic grouping)

**AI Entities**: AIContext, ChatSession, ChatMessage, TokenUsage, NoteAnnotation

**Relations**: NoteIssueLink (bidirectional CREATED/EXTRACTED/REFERENCED), IssueLabel, IssueAssignee, IssueWatcher

**Issue State Machine**: Backlog → Todo → In Progress → In Review → Done (any → Cancelled, Done → Todo reopen)

**State-Cycle Constraints**:
- Backlog: No cycle assignment
- Todo: Cycle optional
- In Progress/In Review: Cycle required (active cycle)
- Done: Leaves cycle, archived with metrics
- Cancelled: Leaves cycle immediately, excluded from metrics

---

## Documentation Entry Points

### Specifications

| Topic | Document |
|-------|----------|
| MVP specification | `specs/001-pilot-space-mvp/spec.md` |
| MVP implementation plan | `specs/001-pilot-space-mvp/plan.md` |
| Phase 2/3 specs | `specs/002-*/spec.md`; `specs/003-*/spec.md` |
| Data model (21 entities) | `specs/001-pilot-space-mvp/data-model.md` |
| UI/UX spec (v4.0) | `specs/001-pilot-space-mvp/ui-design-spec.md` |
| Business design (v2.0) | `specs/001-pilot-space-mvp/business-design.md` |

### Architecture

| Topic | Document |
|-------|----------|
| Architecture overview | `docs/architect/README.md` |
| Agent architecture | `docs/architect/pilotspace-agent-architecture.md` |
| Claude SDK integration | `docs/architect/claude-agent-sdk-architecture.md` |
| Feature-to-component mapping | `docs/architect/feature-story-mapping.md` |
| Backend architecture | `docs/architect/backend-architecture.md` |
| Frontend architecture | `docs/architect/frontend-architecture.md` |
| RLS security patterns | `docs/architect/rls-patterns.md` |

### Standards & Patterns

| Topic | Document |
|-------|----------|
| Architecture decisions (88) | `docs/DESIGN_DECISIONS.md` |
| Dev patterns (start here) | `docs/dev-pattern/README.md` |
| Pilot Space patterns | `docs/dev-pattern/45-pilot-space-patterns.md` |
| MobX patterns | `docs/dev-pattern/21c-frontend-mobx-state.md` |
| Feature specs (17 features) | `docs/PILOT_SPACE_FEATURES.md` |

---

## How to Explore This Codebase

- **Find a feature** → `docs/architect/feature-story-mapping.md` (US-XX → files)
- **Find a file/symbol** → use `mcp__serena` tools (`find_symbol`, `search_for_pattern`)
- **Understand a module** → read its `README.md` (backend, frontend, ai/ each have one)
- **Find patterns/gotchas** → `docs/dev-pattern/45-pilot-space-patterns.md`
- **Full file tree** → `docs/architect/project-structure.md`

---

## Dev-Pattern Quick Reference

Load order for new features:

1. `feature-story-mapping.md` → Find US-XX and components
2. `45-pilot-space-patterns.md` → Project-specific overrides
3. Domain-specific pattern → (e.g., 07-repository, 20-component)
4. Cross-cutting patterns → (e.g., 26-di, 06-validation)

**Pilot Space Overrides** (from pattern 45):
- Zustand → MobX (complex observable state, auto-save reactions)
- Custom JWT → Supabase Auth+RLS (database-level auth)
- Kafka → Supabase Queues/pgmq (native PostgreSQL, exactly-once)

---

## Core Principles

**Keep solutions simple and focused.** Only make changes directly requested or clearly necessary. Don't add features, refactor code, or make "improvements" beyond what was asked.

**Prefer editing existing files to creating new ones.** Only create new files when adding distinct functionality (new entity, new router, new feature module).

**Read and understand relevant files before proposing changes.** Don't speculate about code you haven't inspected. Review existing style, conventions, and abstractions before implementing.

**Write tests for all new features and bug fixes.** 80% coverage catches 85% of regressions before deployment.

**Follow the patterns.** Load `docs/dev-pattern/45-pilot-space-patterns.md` first for project-specific patterns, then domain-specific patterns as needed.

---

## Terminology & Definitions

**Critical terms used throughout this document**:

### Agent Types

- **PilotSpaceAgent (Orchestrator)**: Centralized conversational agent handling all user-facing AI interactions. Routes to skills/subagents, manages sessions, handles approvals.
- **Subagent**: Multi-turn, stateful agent spawned by orchestrator for complex tasks (PR review, AI context). Results flow through orchestrator's SSE stream.
- **Skill**: Single-turn, stateless operation defined in `.claude/skills/` YAML file. Invoked via slash commands or intent detection.
- **Independent Agent**: Fast-path agent (GhostTextAgent) bypassing orchestrator for latency-critical operations. Exception to centralized model.

### Architecture Patterns

- **CQRS-lite**: Command/Query separation without Event Sourcing. Pattern: `Service.execute(Payload) → Result`. Commands mutate state, queries read state.
- **Payload**: Pydantic v2 schema containing validated user input for a command/query. Created at API boundary, passed to service layer.
- **Entity**: Rich domain object with behavior and validation (e.g., `Issue`, `Note`, `Cycle`). Lives in domain layer.
- **DTO (Data Transfer Object)**: Pydantic schema for API responses. Created from entities at presentation layer.
- **Repository**: Data access abstraction. Pattern: `BaseRepository[T]`. Handles RLS enforcement, async SQLAlchemy queries.

### Session Types

- **User Session**: Authentication session. Redis hot cache (30-min sliding expiration) + PostgreSQL durable storage (24h TTL). Used for workspace access control.
- **Chat Session**: Conversational AI session. PostgreSQL storage (24h TTL), optional Redis cache. Contains message history for multi-turn conversations.

## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:

1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes

### Claude Agent SDK Documentation

Read index at `docs/claude-sdk.txt` for full documentation.
