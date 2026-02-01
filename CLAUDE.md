# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Table of Contents

<!-- TOC for AI agents: Navigate to any section by searching for its ## heading -->

1. [Project Overview](#project-overview) - Mission, differentiators, core philosophy
2. [Technology Stack](#technology-stack) - Full stack details with rationale
3. [Production Architecture Overview](#production-architecture-overview) - System topology, data flow, deployment
4. [AI Agent Architecture](#ai-agent-architecture) - Centralized conversational agent, skills, subagents
5. [Design Decisions Summary](#design-decisions-summary) - 88 architectural decisions (DD-001 to DD-088)
6. [Development Commands](#development-commands) - Backend, frontend, Docker setup
7. [Project Structure](#project-structure) - Directory layout for backend and frontend
8. [Quality Gates](#quality-gates) - Non-negotiable standards for all code
9. [Architecture Patterns](#architecture-patterns) - Backend, AI, frontend patterns
10. [Key Entities](#key-entities) - Domain model overview
11. [Current Implementation Status](#current-implementation-status) - Backend/frontend completion by module (75-80% done)
12. [Implementation Roadmap](#implementation-roadmap) - 6-phase plan, 173 tasks, 4-6 weeks to MVP
13. [Documentation Entry Points](#documentation-entry-points) - Where to find what
14. [Dev-Pattern Quick Reference](#dev-pattern-quick-reference) - Pattern loading order
15. [AI Agent Instructions](#ai-agent-instructions) - Per-section guidance for AI agents

---

## Project Overview

**Pilot Space** is an AI-augmented SDLC platform with a "Note-First" workflow where users brainstorm with AI in collaborative documents, and issues emerge naturally from refined thinking. The platform provides comprehensive project management (issues, cycles, modules, pages) enhanced with AI capabilities using a Claude Agent SDK.

**Mission**: Enable software development teams to ship quality software faster through intelligent AI assistance that augments human expertise in architecture design, documentation, code review, and project management -- while maintaining full human oversight and control.

**Core Differentiator**: Note canvas as the default home view, not a dashboard. AI acts as an embedded co-writing partner, not a bolt-on feature.

**Philosophy**: "Think first, structure later" -- users write thoughts in a living document, AI assists inline, and structured issues emerge from refined thinking rather than form-filling.

| Traditional PM (Ticket-First) | Pilot Space (Thought-First) |
|-------------------------------|------------------------------|
| Start with forms, fill fields | Start with notes, write thoughts, AI extracts |
| Structure imposed upfront | Structure emerges from thinking |
| AI bolt-on (autocomplete) | AI embedded (co-writing partner) |
| Dashboard as home | **Note Canvas as home** |

**Target Scale**: 5-100 team members per workspace, 50,000+ issues.

---

## Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| **Backend** | FastAPI + SQLAlchemy 2.0 (async) + Alembic | Pydantic v2 for validation, Python 3.12+ |
| **Frontend** | React 18 + TypeScript 5.x + MobX + TailwindCSS | TipTap/ProseMirror for rich text, shadcn/ui components |
| **Database** | PostgreSQL 16+ with pgvector | Soft deletion, UUID PKs, RLS, JSONB |
| **AI Orchestration** | Claude Agent SDK (centralized conversational agent) | Skills + subagents architecture |
| **AI Providers** | BYOK: Anthropic (required), OpenAI (embeddings), Gemini (optional) | DD-002 |
| **Platform** | Supabase (Auth, Storage, Queues, Realtime, Vault) | Unified platform, DD-060 |
| **Cache** | Redis | Sessions, AI response cache, rate limiting |
| **Search** | Meilisearch | Typo-tolerant full-text search |
| **Streaming** | SSE via FastAPI StreamingResponse | One-way AI to UI, DD-066 |

---

## Production Architecture Overview

### System Topology

```
                          ┌──────────────────────────────────┐
                          │       FRONTEND (React 18)         │
                          │  NoteCanvas  ChatView  Approvals  │
                          │       PilotSpaceStore (MobX)      │
                          └──────────┬───────────┬────────────┘
                                     │ SSE       │ REST
                          ┌──────────▼───────────▼────────────┐
                          │      BACKEND (FastAPI)             │
                          │  /api/v1/ai/chat (unified)         │
                          │  /api/v1/notes, issues, cycles...  │
                          │  PilotSpaceAgent (orchestrator)    │
                          └──┬────┬────┬────┬────┬────────────┘
                             │    │    │    │    │
              ┌──────────────┘    │    │    │    └──────────────┐
              ▼                   ▼    ▼    ▼                   ▼
        ┌──────────┐     ┌──────┐ ┌──────┐ ┌──────┐     ┌──────────┐
        │PostgreSQL│     │Redis │ │Supa- │ │Meili-│     │Claude API│
        │+pgvector │     │      │ │base  │ │search│     │OpenAI API│
        └──────────┘     └──────┘ └──────┘ └──────┘     └──────────┘
```

### Request Flow

1. **GhostText (fast path)**: Editor typing -> GhostTextAgent (Haiku) -> SSE (<2s)
2. **Skill invocation**: `\skill-name` -> PilotSpaceAgent -> Skill Executor -> SSE
3. **Subagent invocation**: `@agent-name` -> PilotSpaceAgent -> Subagent Spawner -> SSE
4. **Natural language**: Free text -> PilotSpaceAgent -> Intent parsing -> Plan -> Execute

### Data Flow (Note-First Workflow)

```
User writes in Note -> AI suggests (margin annotations)
   -> User refines with AI (ghost text, enhance)
   -> AI identifies actionable items (extract-issues skill)
   -> User approves issue creation (human-in-the-loop)
   -> Issues link back to source note (bidirectional sync)
   -> Note continues as living documentation
```

### Multi-Tenant Isolation

- **Supabase RLS**: Row-level security on all tables (workspace_id, user_id)
- **Sandbox per user**: `/sandbox/{user_id}/{workspace_id}/` with isolated `.claude/` directory
- **API key encryption**: Supabase Vault (AES-256-GCM), per-workspace BYOK keys
- **Session security**: Cryptographic session IDs (256-bit), IP binding, 24h TTL

---

## AI Agent Architecture

### Centralized Conversational Agent (DD-086)

PilotSpace uses a **centralized conversational agent** architecture where a single `PilotSpaceAgent` orchestrates all AI interactions through skills and subagents.

```
┌─────────────────────────────────────────────────────────────┐
│                    PilotSpaceAgent (Sonnet)                   │
│                    Main Orchestrator                          │
│                                                               │
│  ┌─────────────────────┐    ┌─────────────────────────────┐  │
│  │   Skill Executor    │    │    Subagent Spawner         │  │
│  │                     │    │                             │  │
│  │ extract-issues      │    │ PRReviewAgent (Opus)        │  │
│  │ enhance-issue       │    │ AIContextAgent (Opus)       │  │
│  │ improve-writing     │    │ DocGeneratorAgent (Sonnet)  │  │
│  │ summarize           │    │                             │  │
│  │ find-duplicates     │    │ (Multi-turn, tool access,   │  │
│  │ recommend-assignee  │    │  streaming output)          │  │
│  │ decompose-tasks     │    │                             │  │
│  │ generate-diagram    │    │                             │  │
│  └─────────────────────┘    └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ▲                              ▲
         │ (single prompt)              │ (multi-turn, tools)
         │                              │
    GhostTextAgent                  POST /api/v1/ai/chat
    (Independent, Haiku, <2s)       (Unified endpoint, SSE)
```

### Agent Classification

| Agent | Type | Model | Latency | Purpose |
|-------|------|-------|---------|---------|
| **GhostTextAgent** | Independent | Haiku | <2s | Inline text completion |
| **PilotSpaceAgent** | Orchestrator | Sonnet | <10s | Conversation, planning, coordination |
| **PRReviewAgent** | Subagent | Opus | <5min | Deep code analysis |
| **AIContextAgent** | Subagent | Opus | <30s | Issue context aggregation |
| **DocGeneratorAgent** | Subagent | Sonnet | <60s | Documentation generation |

### Skill System (DD-087)

Skills are filesystem-based (`/.claude/skills/`) and loaded by Claude Agent SDK:

| Skill | Purpose | Migrated From |
|-------|---------|---------------|
| `extract-issues` | Identify actionable items from notes | IssueExtractorAgent |
| `enhance-issue` | Improve issue title/description/labels | IssueEnhancerAgent |
| `improve-writing` | Enhance text clarity and style | New |
| `summarize` | Multi-format content summarization | New |
| `find-duplicates` | Vector search for similar issues | DuplicateDetectorAgent |
| `recommend-assignee` | Expertise-based assignment | AssigneeRecommenderAgent |
| `decompose-tasks` | Break features into subtasks | TaskDecomposerAgent |
| `generate-diagram` | Mermaid/C4 diagram generation | DiagramGeneratorAgent |

### Human-in-the-Loop Approval (DD-003)

| Action Category | Behavior | Override |
|-----------------|----------|----------|
| Non-destructive (suggest labels, ghost text) | Auto-execute | Per-project |
| Content creation (create issues, extract) | Require approval | Per-project |
| Destructive (delete, merge PR, archive) | **Always require approval** | No |

### MCP Note Tools (6 tools)

| Tool | Operation | Category |
|------|-----------|----------|
| `update_note_block` | Replace/append block content | Write |
| `enhance_text` | Improve clarity without changing meaning | Write |
| `summarize_note` | Read full note content | Read |
| `extract_issues` | Create linked issues from blocks | Write |
| `create_issue_from_note` | Create single linked issue | Write |
| `link_existing_issues` | Search and link existing issues | Write |

### Provider Routing (DD-011)

| Task Type | Provider | Model |
|-----------|----------|-------|
| Agentic tasks (PR review, task decomp, AI context) | Claude SDK (full) | Opus/Sonnet |
| One-shot tasks (doc gen, issue enhance) | Claude SDK `query()` | Sonnet |
| Latency-critical (ghost text, annotations) | Google Gemini Flash | 2.0-flash |
| Embeddings (semantic search, RAG, duplicates) | OpenAI | text-embedding-3-large |

### Cost Optimization

- **Prompt caching**: `cache_control: ephemeral` for system prompts (63% cost reduction)
- **Context window management**: Prune at 50k tokens, preserve recent 10 messages
- **Token usage tracking**: Per-request logging, budget alerts at 90%
- **Model routing**: Haiku for fast tasks, Sonnet for orchestration, Opus for deep analysis

### Error Handling & Resilience

- **Retry**: Exponential backoff (3 retries, 1-10s wait) via `tenacity`
- **Circuit breaker**: 5 failure threshold, 60s recovery timeout
- **SSE abort**: Backend AbortController for stream termination
- **Offline queue**: Messages queued when API unavailable, retry on reconnection
- **Frontend optimistic updates**: PendingOperations map with rollback on error

---

## Design Decisions Summary

88 architectural decisions documented in `docs/DESIGN_DECISIONS.md`. Key decisions:

| ID | Decision | Impact |
|----|----------|--------|
| DD-001 | FastAPI replaces Django entirely | Stack |
| DD-002 | BYOK + Claude Agent SDK orchestration (Anthropic required, OpenAI for embeddings, Gemini optional) | AI |
| DD-003 | Critical-only AI approval model (auto-execute non-destructive, approve destructive) | AI |
| DD-004 | MVP integrations: GitHub + Slack only | Scope |
| DD-005 | No real-time collaboration in MVP (last-write-wins) | Scope |
| DD-006 | Unified AI PR Review (architecture + code + security + performance + docs) | AI |
| DD-011 | Provider routing: Claude->code, Gemini->latency, OpenAI->embeddings | AI |
| DD-013 | Note-First, not Ticket-First workflow | Core UX |
| DD-048 | AI confidence tags: Recommended/Default/Current/Alternative | AI |
| DD-060 | Supabase platform (Auth, Storage, Queues, Realtime, Vault) | Infra |
| DD-064 | CQRS-lite with Service Classes + Payloads | Arch |
| DD-065 | MobX for frontend state (not Zustand) | Arch |
| DD-066 | SSE for AI streaming (not WebSocket) | AI |
| DD-086 | Centralized conversational agent architecture | AI |
| DD-087 | Filesystem-based skill system | AI |
| DD-088 | MCP tool registry for domain operations | AI |

---

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

---

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
│   ├── sdk/              # Claude Agent SDK integration (config, sessions, permissions, hooks, resilience)
│   ├── providers/        # LLM provider adapters (Claude, OpenAI, Gemini, Azure)
│   ├── agents/           # PilotSpaceAgent + subagents (pr-review, ai-context, doc-generator)
│   ├── tools/            # Custom MCP tools (database, github, search, note tools)
│   ├── prompts/          # Prompt templates per agent/skill
│   ├── rag/              # RAG pipeline (embedder, chunker, retriever, indexer)
│   ├── session/          # Conversation session management
│   └── infrastructure/   # Cost tracker, rate limiter, cache, resilience
├── infrastructure/
│   ├── database/         # SQLAlchemy models, repositories, migrations (chat_session, chat_message, token_usage)
│   ├── cache/            # Redis
│   ├── queue/            # Supabase Queues (pgmq)
│   └── auth/             # Supabase Auth
└── integrations/         # GitHub, Slack

frontend/src/
├── app/                  # Next.js app router
├── features/             # Feature-based modules
│   ├── notes/            # Note canvas, ghost text, annotations
│   ├── issues/           # Issue views, AI context
│   ├── ai/               # ChatView component tree (25 components)
│   │   └── ChatView/     # ChatView, MessageList, TaskPanel, ApprovalOverlay, ChatInput
│   └── workspace/        # Workspace settings
├── components/
│   ├── ui/               # Base shadcn/ui components
│   └── editor/           # TipTap extensions
├── stores/               # MobX stores
│   └── ai/               # PilotSpaceStore (unified), GhostTextStore (independent)
└── services/             # API clients, SSE client
```

---

## Quality Gates

All code must pass before merge:

**Non-negotiables**:
- Type checking in strict mode (pyright for Python, TypeScript strict)
- Test coverage > 80%
- No N+1 queries, no blocking I/O in async functions
- File size limit: 700 lines maximum
- No TODOs, mocks, or placeholder code in production paths
- AI features respect human-in-the-loop principle (DD-003)
- RLS policies verified for multi-tenant data
- Conventional commits: `feat|fix|refactor|docs|test|chore(scope): description`

**Backend quality command**: `uv run pyright && uv run ruff check && uv run pytest --cov=.`

**Frontend quality command**: `pnpm lint && pnpm type-check && pnpm test`

---

## Architecture Patterns

**Load `docs/dev-pattern/45-pilot-space-patterns.md` first** for project-specific patterns.

### Backend Patterns
- **CQRS-lite**: Service Classes with Payloads (`CreateIssueService.execute(payload)`) - DD-064
- **Repository**: Generic + Specific (`BaseRepository[T]`) with async SQLAlchemy 2.0
- **DI**: `dependency-injector` library for constructor injection
- **Errors**: RFC 7807 Problem Details format
- **Validation**: Pydantic v2 models for all request/response schemas
- **Auth**: Supabase Auth + RLS for multi-tenant isolation - DD-061

### AI Agent Patterns
- **Centralized agent**: PilotSpaceAgent as single orchestrator with skills + subagents - DD-086
- **SDK integration**: `query()` for one-shot, `ClaudeSDKClient` for multi-turn - DD-058
- **Skill system**: Filesystem-based `.claude/skills/` with YAML frontmatter - DD-087
- **MCP tools**: Custom tools via `create_sdk_mcp_server()` for domain operations - DD-088
- **Provider routing**: Task-specific selection per DD-011
- **BYOK**: Anthropic required, OpenAI required for search, Gemini optional - DD-002
- **Approval**: Human-in-the-loop per DD-003 via SDK `canUseTool` callback
- **Streaming**: SSE via FastAPI StreamingResponse - DD-066
- **Resilience**: Retry, circuit breaker, offline queue, prompt caching
- **Session persistence**: ChatSession/ChatMessage in PostgreSQL with SDK session resumption

### Frontend Patterns
- **State**: MobX for client state (`PilotSpaceStore`), TanStack Query for server state - DD-065
- **Structure**: Feature folders (`features/{domain}/`)
- **Editor**: TipTap Extension per feature (ghost text, annotations, issue extraction)
- **Realtime**: Supabase Realtime per-workspace subscription
- **SSE handling**: Event-driven store updates (8 event types mapped to UI components)
- **Optimistic updates**: PendingOperations map with rollback on error
- **Accessibility**: WCAG 2.2 AA (keyboard nav, ARIA, screen readers, touch targets)

---

## Key Entities

| Entity | Purpose |
|--------|---------|
| **Note** | Block-based document with AI annotations, primary entry for Note-First workflow |
| **NoteAnnotation** | AI suggestions in right margin, linked to specific blocks |
| **Issue** | Work item with state machine, AI metadata, integration links |
| **AIContext** | Aggregated context for issue (related docs, code, tasks with Claude Code prompts) |
| **Cycle** | Sprint container with velocity/burndown metrics |
| **Module** | Epic grouping for issues |
| **ChatSession** | AI conversation session with SDK session ID, context JSONB, 24h TTL |
| **ChatMessage** | Individual messages in a session (role, content, tool_calls JSONB) |
| **TokenUsage** | Per-request token tracking (prompt, completion, cached, cost) |

---

## Current Implementation Status

**Overall MVP Completion**: 75-80% | **Remaining**: ~43 tasks across 4-6 weeks

### Backend (69,435 lines Python)

| Layer | Status | Completion |
|-------|--------|------------|
| API (20 routers) | Production-ready | 95% |
| Application Services (8 domains) | Production-ready | 90% |
| Domain (entities, value objects) | Complete | 95% |
| Infrastructure (26 models, 17 repos, 19 migrations) | Complete | 95% |
| AI Agent (PilotSpaceAgent, SDK, sessions) | Functional | 85% |
| AI Tools (6 note tools, search, DB, GitHub) | Partial | 70% |
| AI Infrastructure (cost, keys, rate limit, resilience) | Complete | 90% |

### Frontend (60,010 lines TypeScript)

| Feature | Status | Completion |
|---------|--------|------------|
| ChatView (25 components) | Production-ready | 95% |
| MobX Stores (12 stores) | Functional | 80% |
| UI Components (25 shadcn/ui) | Complete | 95% |
| API Services (9 clients) | Complete | 90% |
| Note Editor (TipTap, 8 extensions) | Scaffold + partial | 65% |
| Ghost Text | Skeleton | 30% |
| Margin Annotations | Skeleton | 25% |
| Issue Extraction UI | Skeleton | 30% |
| Cycle/Sprint Charts | Scaffold | 60% |

### Critical Remaining Work

1. **Ghost Text Extension** - Complete TipTap extension + SSE streaming (P4-005:009)
2. **Margin Annotations UI** - Card component + positioning + real-time sync (P4-010:013)
3. **Issue Extraction Approval** - Preview modal + diff + bulk ops (P4-014:017)
4. **Note MCP Tools E2E** - All 6 tools tested end-to-end (P3-005:010)
5. **PilotSpaceStore Wiring** - MobX → API → SSE event mapping (P4-001:002)
6. **SSE Transform Pipeline** - SDK message → Frontend SSE event (P3-014:015)
7. **E2E Tests** - 6 critical paths + performance + security (P5-001:024)

---

## Implementation Roadmap

The implementation follows a 6-phase remediation plan migrating from siloed agents to the centralized conversational architecture. See `docs/architect/pilotspace-implementation-plan.md` for the full plan.

| Phase | Name | Tasks | Status | Critical Path |
|-------|------|-------|--------|---------------|
| **1** | Foundation & SDK Integration | 25 | **85% Done** | SSE abort, prompt caching, token budget, session security |
| **2** | Skill Migration | 11 | **70% Done** | find-duplicates, recommend-assignee, skill validation, output schemas |
| **3** | Backend Consolidation | 15 | **80% Done** | Note MCP tools E2E (6 tools), SSE transform pipeline |
| **4** | Frontend Architecture | 34 | **60% Done** (ChatView + stores) | Ghost Text, Margin Annotations, Issue Extraction UI, Note Canvas |
| **5** | Integration & Testing | 26 | **15% Started** | E2E tests, performance, security audit |
| **6** | Polish & Refinement | 41 | Not Started | Animations, accessibility, theming, performance (post-MVP) |

**Total**: 173 tasks | **Remaining**: ~43 tasks | **Timeline**: 4-6 weeks to MVP | **Architecture Grade**: B+ (83/100)

**Critical Path**: P3 Note MCP Tools E2E → P4 PilotSpaceStore Wiring → P4 Ghost Text → P4 Annotations → P4 Issue Extraction → P5 E2E Tests → MVP Release

---

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
| **Architecture overview & AI QA Index** | `docs/architect/README.md` |
| **Agent architecture (centralized)** | `docs/architect/pilotspace-agent-architecture.md` |
| **Agent remediation plan** | `docs/architect/agent-architecture-remediation-plan.md` |
| **Implementation plan (detailed)** | `docs/architect/pilotspace-implementation-plan.md` |
| **Claude SDK integration** | `docs/architect/claude-agent-sdk-architecture.md` |
| **AI layer** | `docs/architect/ai-layer.md` |
| **Feature-to-component mapping** | `docs/architect/feature-story-mapping.md` |
| **Backend architecture** | `docs/architect/backend-architecture.md` |
| **Frontend architecture** | `docs/architect/frontend-architecture.md` |
| **Infrastructure (Supabase)** | `docs/architect/infrastructure.md` |
| **Supabase integration** | `docs/architect/supabase-integration.md` |
| **RLS security patterns** | `docs/architect/rls-patterns.md` |
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
| **Architecture decisions (88)** | `docs/DESIGN_DECISIONS.md` |
| **AI capabilities** | `docs/AI_CAPABILITIES.md` |
| **Project vision** | `docs/PROJECT_VISION.md` |
| **Feature specifications** | `docs/PILOT_SPACE_FEATURES.md` |
| **Dev patterns (start here)** | `docs/dev-pattern/README.md` |
| **Pilot Space patterns** | `docs/dev-pattern/45-pilot-space-patterns.md` |
| **MobX patterns** | `docs/dev-pattern/21c-frontend-mobx-state.md` |

---

## Dev-Pattern Quick Reference

For any new feature, load patterns in this order:

```text
1. feature-story-mapping.md   -> Find US-XX and its components
2. 45-pilot-space-patterns.md -> Project-specific overrides
3. Domain-specific pattern    -> (e.g., 07-repository, 20-component)
4. Cross-cutting patterns     -> (e.g., 26-di, 06-validation)
```

**User Story to Architecture**: See `docs/architect/feature-story-mapping.md` for:
- 18 user stories mapped to architecture components (MVP: 6, Phase 2: 9, Phase 3: 3)
- Data entities per feature
- AI agents per user story
- Implementation phases

**Pilot Space Overrides** (from pattern 45):
| Standard Pattern | Override |
|------------------|----------|
| 21a: Zustand | MobX |
| 17: Custom JWT | Supabase Auth + RLS |
| 10: Kafka | Supabase Queues |

---

## AI Agent Instructions

<!-- Instructions for AI agents working on this codebase -->

### For All Agents

- **Read this file first** before any implementation work.
- **Load dev patterns** in the order specified in Dev-Pattern Quick Reference.
- **Check feature-story-mapping.md** to understand which components are affected.
- **Follow quality gates** -- all code must pass `uv run pyright && uv run ruff check && uv run pytest --cov=.` (backend) and `pnpm lint && pnpm type-check && pnpm test` (frontend).
- **File limit**: 700 lines max. Split files proactively.
- **Conventional commits**: `feat|fix|refactor|docs|test|chore(scope): description`

### For Backend Agents

- Use **CQRS-lite pattern**: Service Classes with Payloads, not direct DB manipulation.
- Use **dependency-injector** for DI, not manual wiring.
- Use **RFC 7807** Problem Details for all error responses.
- All async functions must use **async SQLAlchemy** (`AsyncSession`).
- Check **RLS policies** when adding/modifying queries for multi-tenant data.
- AI features must respect **DD-003** (human-in-the-loop approval).
- New AI agents go through **PilotSpaceAgent** as skills or subagents, not standalone.

### For Frontend Agents

- Use **MobX** for client state (`makeAutoObservable`, `observer()` pattern).
- Use **TanStack Query** for server state (API data fetching/caching).
- Use **shadcn/ui** components as base, extend with feature-specific variants.
- All components must be **WCAG 2.2 AA** compliant (keyboard nav, ARIA labels, focus management).
- AI interactions go through **PilotSpaceStore** (unified store), not siloed stores.
- SSE events map to specific store updates -- see the event mapping in `pilotspace-agent-architecture.md` section 8.

### For AI/Agent Layer Agents

- **PilotSpaceAgent** is the single orchestrator -- do not create new independent agents.
- Simple operations -> **skills** (filesystem `.claude/skills/`). Complex operations -> **subagents**.
- All tools return **operation payloads** (`status: pending_apply`), not direct DB mutations.
- Note tools use **ContentConverter** for TipTap <-> Markdown conversion with block ID preservation.
- SSE transform pipeline: SDK message -> `transform_sdk_message()` -> Frontend SSE event.
- **Prompt caching** must be enabled for system prompts (`cache_control: ephemeral`).
- **Error handling**: Use tenacity for retries, circuitbreaker for API failures.

### For Testing Agents

- **Backend**: pytest with `--cov=.`, async tests with `pytest-asyncio`, fixture-based DB sessions.
- **Frontend**: Vitest for unit tests, Playwright for E2E tests.
- **Coverage target**: >80% for all modules.
- **E2E critical paths**: Skill invocation, subagent invocation, approval flow, session resumption, error recovery.

---

## Active Technologies
- Python 3.12+ (Backend), TypeScript 5.x (Frontend) (001-pilot-space-mvp)
- Python 3.12+ (Backend) + FastAPI, SQLAlchemy 2.0 (async), claude-agent-sdk>=1.0,<2.0, anthropic, openai, google-generativeai (004-mvp-agents-build)
- PostgreSQL 16+ with pgvector, Redis (sessions), Supabase Vault (key encryption) (004-mvp-agents-build)

## Recent Changes
- 001-pilot-space-mvp: Supabase platform, Claude Agent SDK, MobX, CQRS-lite
- 004-mvp-agents-build: AI agents, MCP tools, note tools pipeline, multi-turn sessions
- 005-conversational-agent-arch: Centralized PilotSpaceAgent, skill system, ChatView (25 components), 12 MobX stores
- docs/architect/: pilotspace-agent-architecture.md, agent-architecture-remediation-plan.md, pilotspace-implementation-plan.md
- CLAUDE.md: Added implementation status tracking (75-80% MVP complete), updated roadmap with actual progress
