# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Table of Contents

<!-- TOC for AI agents: Navigate to any section by searching for its ## heading -->

1. [Project Overview](#project-overview) - Mission, differentiators, core philosophy, competitive positioning
2. [Technology Stack](#technology-stack) - Full stack details with rationale and decision references
3. [Production Architecture Overview](#production-architecture-overview) - Infrastructure topology, data flows, deployment model
4. [AI Agent Architecture](#ai-agent-architecture) - Centralized conversational agent, skills, subagents, provider routing
5. [Design Decisions Summary](#design-decisions-summary) - 88 architectural decisions (DD-001 to DD-088)
6. [Development Commands](#development-commands) - Backend, frontend, Docker setup
7. [Project Structure](#project-structure) - Directory layout for backend and frontend
8. [Quality Gates](#quality-gates) - Non-negotiable standards for all code
9. [Architecture Patterns](#architecture-patterns) - Backend, AI, frontend patterns with business rationale
10. [Key Entities](#key-entities) - Domain model overview with relationships
11. [Current Implementation Status](#current-implementation-status) - Backend/frontend completion by module (75-80% done)
12. [Implementation Roadmap](#implementation-roadmap) - 6-phase plan, 173 tasks, 4-6 weeks to MVP
13. [Documentation Entry Points](#documentation-entry-points) - Where to find what
14. [Dev-Pattern Quick Reference](#dev-pattern-quick-reference) - Pattern loading order
15. [AI Agent Instructions](#ai-agent-instructions) - Per-section guidance for AI agents

---

## Project Overview

### Mission

**Pilot Space** is an AI-augmented SDLC platform built on a "Note-First" paradigm. It enables software development teams to ship quality software faster through intelligent AI assistance that augments human expertise in architecture design, documentation, code review, and project management -- while maintaining full human oversight and control.

### Business Context

**Problem**: Traditional issue trackers (Jira, Linear, GitHub Projects) force users into form-filling before thinking is complete. This creates friction: teams brainstorm in Slack/Notion, then manually transcribe into tickets, losing context and nuance. AI features in existing tools are bolt-on autocomplete, not embedded intelligence.

**Solution**: Pilot Space inverts the workflow. Users start with a collaborative note canvas where they write freely. AI acts as an embedded co-writing partner -- suggesting inline completions (ghost text), asking clarifying questions in the margin (annotations), and detecting actionable items. Issues emerge naturally from refined thinking, pre-filled with context from the source note. Notes remain bidirectionally linked to issues as living documentation.

**Value Proposition**: "Think first, structure later" -- issues emerge from refined thinking rather than form-filling.

| Traditional PM (Ticket-First) | Pilot Space (Thought-First) |
|-------------------------------|------------------------------|
| Start with forms, fill fields | Start with notes, write thoughts, AI extracts |
| Structure imposed upfront | Structure emerges from thinking |
| AI bolt-on (autocomplete) | AI embedded (co-writing partner) |
| Dashboard as home | **Note Canvas as home** |

### Competitive Positioning

| Tool | Strengths | Pilot Space Advantage |
|------|-----------|----------------------|
| **Jira** | Enterprise adoption, workflows | Simpler UX, AI-native, open source, no per-seat lock-in |
| **Linear** | Fast developer UX | Open source, deeper AI (ghost text, margin annotations, AI context) |
| **Plane** | Open source, modern UI | AI-first architecture, Note-First workflow, Claude Agent SDK |
| **GitHub Projects** | VCS integration | Full PM + multi-VCS + AI PR review + AI context generation |
| **Notion** | Flexible docs + databases | SDLC-specific AI (code review, task decomposition, architecture analysis) |

### Target Personas

- **Sarah (Architect)**: Needs automated architecture compliance, pattern suggestions. Pilot Space provides AI-powered code review + architecture analysis in PR reviews.
- **Marcus (Tech Lead)**: Needs AI-assisted code reviews, sprint analytics. Pilot Space provides unified PR review + task decomposition + velocity tracking.
- **Elena (PM)**: Needs intelligent planning, requirement clarity. Pilot Space provides AI issue enhancement + Note-First workflow for natural requirement capture.
- **Dev (Junior)**: Needs contextual guidance, code discovery. Pilot Space provides AI Context per issue with ready-to-use Claude Code prompts.

### Scale & Monetization

- **Target Scale**: 5-100 team members per workspace, 50,000+ issues
- **Pricing Model**: All features free (open source, self-hosted). Paid tiers ($10-$18/seat/mo) provide support SLAs only. Users bring their own LLM API keys (BYOK) -- no AI cost pass-through.

---

## Technology Stack

### Backend

| Component | Technology | Version | Rationale | Decision |
|-----------|-----------|---------|-----------|----------|
| **Framework** | FastAPI | 0.110+ | Modern async-first, automatic OpenAPI docs, Pydantic v2 integration | DD-001 |
| **ORM** | SQLAlchemy 2.0 (async) | 2.0+ | Native async with asyncpg driver, excellent FastAPI fit, mature migration tool (Alembic) | DD-001 |
| **Validation** | Pydantic v2 | 2.6+ | Request/response validation, strict type safety, fast serialization | DD-001 |
| **DI** | dependency-injector | 4+ | Constructor injection, testable services, Singleton + Factory providers | DD-064 |
| **Runtime** | Python | 3.12+ | Latest typing features, performance improvements | -- |

### Frontend

| Component | Technology | Version | Rationale | Decision |
|-----------|-----------|---------|-----------|----------|
| **Framework** | Next.js (App Router) | 14+ | Server Components, file-based routing, SSR/SSG, Vercel-optimized | -- |
| **UI Library** | React | 18+ | Proven ecosystem, concurrent features, Server Components | -- |
| **UI State** | MobX | 6+ | Complex observable state (selection, filters, modals, drag) -- NOT for server data | DD-065 |
| **Server State** | TanStack Query | 5+ | API caching, automatic deduplication, optimistic updates, pagination | DD-065 |
| **Styling** | TailwindCSS + shadcn/ui | 3.4+ | Utility-first CSS, pre-built accessible components, warm design system | -- |
| **Rich Text** | TipTap/ProseMirror | 2+ | Extensible editor framework, custom extensions (ghost text, annotations, slash commands) | -- |
| **Language** | TypeScript | 5.3+ | Strict mode, discriminated unions, exhaustive switches | -- |

### AI & Orchestration

| Component | Technology | Purpose | Decision |
|-----------|-----------|---------|----------|
| **Orchestration** | Claude Agent SDK | Centralized conversational agent with skills + subagents | DD-002, DD-086 |
| **Primary LLM** | Anthropic Claude (BYOK) | Code review, task planning, PR review, conversation | DD-002 |
| **Latency LLM** | Google Gemini Flash (BYOK) | Ghost text, margin annotations (<2s response) | DD-011 |
| **Embeddings** | OpenAI text-embedding-3-large (BYOK) | 3072-dim vectors for semantic search, RAG, duplicate detection | DD-011, DD-070 |
| **Streaming** | SSE via FastAPI StreamingResponse | One-way AI-to-UI streaming, simpler than WebSocket for unidirectional responses | DD-066 |

### Infrastructure & Platform

| Component | Technology | Purpose | Decision |
|-----------|-----------|---------|----------|
| **Database** | PostgreSQL 16+ with pgvector | Primary store + vector embeddings (HNSW index), soft deletion, UUID PKs, JSONB | DD-060 |
| **Auth** | Supabase Auth (GoTrue) | Email/password, OAuth, SAML 2.0 SSO, JWT tokens, RLS enforcement | DD-061 |
| **Cache** | Redis 7 | Sessions (30-min TTL), AI response cache (7-day TTL), rate limiting | -- |
| **Search** | Meilisearch 1.6 | Typo-tolerant full-text search for notes and issues | -- |
| **Queues** | Supabase Queues (pgmq + pg_cron) | Async AI jobs, GitHub webhook processing, dead-letter queue | DD-069 |
| **Storage** | Supabase Storage (S3-compatible) | File uploads, CDN delivery, image transforms | DD-060 |
| **Realtime** | Supabase Realtime (Phoenix WebSocket) | Per-workspace state change notifications | DD-060 |
| **Secrets** | Supabase Vault | AES-256-GCM encryption for BYOK API keys | DD-060 |

---

## Production Architecture Overview

### Infrastructure Topology

The system follows a three-tier architecture deployed as containerized services. Dependencies flow inward from presentation to infrastructure.

**Frontend Tier** (Next.js 14, App Router): Serves the React application with server-side rendering. Communicates with the backend via REST API (CRUD operations) and SSE (AI streaming). Authenticates via Supabase Auth (JWT in cookies for SSE compatibility, Bearer token for REST).

**Backend Tier** (FastAPI on port 8000): The API gateway and business logic layer. Follows Clean Architecture with 5 layers: Presentation (routers, schemas, middleware) → Application (CQRS-lite service classes) → Domain (entities, value objects, events) → Infrastructure (repositories, cache, queue, auth) → AI (agents, tools, providers, sessions). The PilotSpaceAgent orchestrator runs within this tier, making outbound calls to LLM providers.

**Data Tier**: PostgreSQL 16+ (via Supabase) serves as the primary data store with Row-Level Security for multi-tenant isolation. pgvector provides HNSW-indexed 3072-dimension embeddings for semantic search. Redis provides session caching and AI response caching. Meilisearch provides typo-tolerant full-text search. Supabase Queues (pgmq) handle async job processing.

**External Services**: Anthropic Claude API (primary LLM, BYOK), OpenAI API (embeddings, BYOK), Google Gemini API (latency-sensitive tasks, BYOK), GitHub API (PR linking, commit tracking, webhook receiver), Slack API (notifications, slash commands).

### Request Flows

**Standard CRUD** (e.g., create issue): Frontend → REST POST `/api/v1/issues` → Middleware (auth, rate limit, correlation ID) → Router (validate request, create Payload) → Service (orchestrate domain logic, begin transaction) → Domain Entity (execute business rules, emit events) → Repository (persist via async SQLAlchemy) → Commit + Publish Events → Response Schema → HTTP Response.

**AI Conversation** (e.g., "extract issues from this note"): Frontend → SSE POST `/api/v1/ai/pilot-space/chat` → PilotSpaceAgent syncs note to workspace markdown → Claude Agent SDK processes with MCP tools enabled → SDK calls `extract_issues` tool → Tool handler creates operation payload → Backend transforms SDK message → SSE events emitted (message_start, text_delta, tool_use, tool_result, message_stop) → Frontend PilotSpaceStore updates messages/tasks/approvals reactively.

**Ghost Text** (fast path, <2s): Editor typing pause (500ms) → SSE GET `/api/v1/notes/{id}/ghost-text` → GhostTextAgent (Gemini Flash) → Streaming tokens → Frontend TipTap GhostTextExtension renders at 40% opacity → Tab to accept, Escape to dismiss.

**AI PR Review** (async, <5min): GitHub webhook POST → Queue (pgmq) → ConversationWorker dequeues → PRReviewAgent (Claude Opus) analyzes diff → Comments posted to GitHub PR with severity tags (critical/warning/suggestion) → SSE notification to frontend.

### Note-First Data Flow

This is the core differentiating workflow:

1. **Capture**: User opens app → Note Canvas is home (not dashboard). User writes freely in block-based TipTap editor.
2. **AI Assists**: After 500ms typing pause, GhostTextAgent suggests inline completions. MarginAnnotationAgent detects ambiguity and posts clarifying questions in the right margin. Threaded AI discussions open per-block for deeper exploration.
3. **Extract**: User or AI identifies actionable items. `extract_issues` skill categorizes items as Explicit (literal problems), Implicit (inferred from context), or Related (consequential). Rainbow-bordered boxes wrap source text in the note.
4. **Approve**: Human-in-the-loop approval (DD-003). User previews extracted issues, edits fields (title, priority, labels), then approves creation. Destructive actions always require approval.
5. **Track**: Created issues link back to source note via `NoteIssueLink` (type: EXTRACTED). Inline `[PS-42]` badges appear in the note at the source block. Notes remain living documentation -- updates propagate bidirectionally.

### Multi-Tenant Isolation

**Database-Level Security (RLS)**: Every user-data table has Row-Level Security policies enforced by PostgreSQL. Policies use `auth.uid()` (from JWT claims) and `auth.user_workspace_ids()` to scope all queries to the user's workspaces. Four roles: owner (full access), admin (manage members, all CRUD), member (create/edit own, view all), guest (read-only assigned items). Default-deny: if no policy matches, access is rejected.

**Agent Sandboxing**: Each user gets an isolated workspace directory at `/sandbox/{user_id}/{workspace_id}/` with its own `.claude/` directory (skills, rules, templates) and `notes/` directory (markdown files synced from DB for SDK access). API keys are encrypted per-workspace in Supabase Vault (AES-256-GCM).

**Session Security**: Cryptographic session IDs (256-bit), IP binding, 24-hour TTL, stored in Redis with 30-min sliding expiration. Sessions persist to PostgreSQL (ai_session table) for multi-turn conversation resumption.

---

## AI Agent Architecture

### Design Philosophy (DD-086)

Pilot Space migrated from 13 siloed agents to a **centralized conversational agent** architecture. A single `PilotSpaceAgent` orchestrator handles all AI interactions through two mechanisms:

- **Skills**: Single-turn, stateless operations loaded from filesystem (`.claude/skills/`). Used for focused tasks like issue extraction, text enhancement, duplicate detection. Invoked via slash commands (e.g., `/extract-issues`) or natural language intent detection.
- **Subagents**: Multi-turn, stateful operations spawned by the orchestrator. Used for complex tasks requiring tool access and iterative reasoning (PR review, AI context generation, documentation). Communicate results back through the orchestrator's SSE stream.

This centralized design eliminates duplicated context management, provides a single conversation history, and enables cross-skill coordination (e.g., extract issues → then enhance each one → then find duplicates).

### Agent Roster

| Agent | Type | Model | Latency Target | Business Purpose |
|-------|------|-------|----------------|------------------|
| **GhostTextAgent** | Independent | Gemini Flash | <2s | Inline text completion as users write in notes. Triggers on 500ms typing pause. Max 50 tokens. Code-aware (respects language syntax). Reduces friction in note-taking. |
| **PilotSpaceAgent** | Orchestrator | Claude Sonnet | <10s | Central conversation agent. Routes user requests to skills or subagents. Manages session context, note sync, tool authorization. Single unified chat endpoint. |
| **PRReviewAgent** | Subagent | Claude Opus | <5min | Unified code review covering architecture compliance, security vulnerabilities, code quality, and documentation gaps. Posts inline comments on GitHub PRs with severity tags. |
| **AIContextAgent** | Subagent | Claude Opus | <30s | Aggregates all context for an issue: related issues, linked notes, code files (AST-aware), Git references. Generates implementation tasks with dependency graphs and Claude Code prompts. |
| **DocGeneratorAgent** | Subagent | Claude Sonnet | <60s | Generates documentation from code, issues, and notes. Supports ADR, API docs, and technical specification formats. |

### Skill System (DD-087)

Skills are filesystem-based (`.claude/skills/`) with YAML frontmatter defining metadata. The Claude Agent SDK auto-discovers and loads them. Each skill is a focused prompt template with structured output.

| Skill | Business Purpose | Input | Output |
|-------|-----------------|-------|--------|
| `extract-issues` | Detect actionable items from notes, categorize as Explicit/Implicit/Related | Note blocks, selected text | Issue candidates with title, description, priority, type |
| `enhance-issue` | Improve issue quality at creation time | Raw title/description | Enhanced title, expanded description with acceptance criteria, suggested labels/priority |
| `improve-writing` | Enhance text clarity and professionalism without changing meaning | Selected text block | Improved text preserving user voice |
| `summarize` | Multi-format content summarization | Note content, format preference | Bullet summary, executive summary, or detailed breakdown |
| `find-duplicates` | Prevent duplicate issues via semantic similarity | Issue title/description | Ranked list of similar issues with similarity scores (threshold: 70%) |
| `recommend-assignee` | Suggest team members based on expertise matching | Issue context, team roster | Ranked assignees with expertise percentage (e.g., "Alice: 85% -- owns auth-service") |
| `decompose-tasks` | Break features into implementation subtasks | Feature description, codebase context | Subtask list with Fibonacci story points (1-13), dependency graph |
| `generate-diagram` | Create visual architecture diagrams | Description, diagram type | Mermaid or PlantUML code for rendering |

### Human-in-the-Loop Approval (DD-003)

This is a core trust mechanism. Users control what AI can do autonomously vs. what requires explicit approval.

| Action Category | Behavior | Examples | UX |
|-----------------|----------|---------|-----|
| **Non-destructive** | Auto-execute, notify user | Suggest labels, ghost text, margin annotations, auto-transition on PR merge | Toast notification |
| **Content creation** | Require approval by default (configurable per-project) | Create issues from notes, post PR comments, generate documentation | ApprovalOverlay dialog |
| **Destructive** | **Always require approval**, no override | Delete issues, merge PRs, archive workspaces, bulk modifications | ApprovalOverlay with consequences description |

Implementation: SDK `canUseTool` callback classifies each tool invocation. Backend `PermissionHandler` checks action type against workspace autonomy level. Frontend `ApprovalStore` manages pending requests with 24-hour auto-expiry.

### MCP Note Tools (6 tools)

These are the custom Model Context Protocol tools registered via `create_note_tools_server()`. They enable the Claude Agent SDK to manipulate notes and issues while maintaining block ID integrity, TipTap↔Markdown conversion, and SSE event propagation.

| Tool | Operation | Business Use Case |
|------|-----------|-------------------|
| `update_note_block` | Replace or append content to a specific block | User asks "change the second paragraph to say X" -- AI modifies precisely |
| `enhance_text` | Improve clarity without changing meaning | User asks "make this more professional" -- AI polishes prose |
| `summarize_note` | Read full note content with metadata | Agent needs context before making modifications |
| `extract_issues` | Create multiple linked issues from identified blocks | User asks "create issues from the action items" -- bulk extraction |
| `create_issue_from_note` | Create single issue linked to a specific block | User selects text, says "turn this into a bug report" |
| `link_existing_issues` | Search workspace issues and link to current note | User asks "are there existing issues about API performance?" |

All tools return operation payloads (`status: pending_apply`), not direct DB mutations. The backend `transform_sdk_message()` function converts markdown payloads to TipTap JSON and applies updates through `NoteAIUpdateService`, emitting SSE `content_update` events.

### Provider Routing (DD-011)

Task-specific provider selection optimizes for cost, latency, and capability.

| Task Type | Provider | Model | Rationale |
|-----------|----------|-------|-----------|
| Agentic tasks (PR review, AI context, task decomp) | Anthropic | Claude Opus/Sonnet | Best code understanding, tool use, multi-turn reasoning |
| One-shot tasks (issue enhance, summarize, extract) | Anthropic | Claude Sonnet via `query()` | Fast single-turn, no session overhead |
| Latency-critical (ghost text, annotations) | Google | Gemini 2.0 Flash | Lowest latency for real-time suggestions |
| Embeddings (search, RAG, duplicates) | OpenAI | text-embedding-3-large | Superior 3072-dim embeddings, industry standard |

Fallback chain: If primary provider fails (circuit breaker open after 5 failures / 60s recovery), routes to secondary. Prompt caching (`cache_control: ephemeral`) reduces cost by 63% on repeated system prompts. Context window managed at 50k token prune threshold, preserving most recent 10 messages.

### Error Handling & Resilience

- **Retry**: `ResilientExecutor` with exponential backoff (1s base, 60s cap, 30% jitter) via 3 attempts. Retries on timeout and rate limit errors. Non-retryable: auth failures, validation errors.
- **Circuit Breaker**: Per-provider isolation. States: CLOSED (healthy) → OPEN (after 5 failures) → HALF_OPEN (after 60s, allows 1 probe). Prevents cascade failures across providers.
- **SSE Abort**: Backend `AbortController` for stream termination. Frontend max 3 reconnection attempts with exponential backoff.
- **Offline Queue**: Messages queued in pgmq when API unavailable, retry on reconnection.
- **Cost Tracking**: Per-request token logging (prompt, completion, cached tokens). Per-provider pricing registry. Budget alerts at 90% threshold.

---

## Design Decisions Summary

88 architectural decisions documented in `docs/DESIGN_DECISIONS.md`. Organized by category:

### Foundational (DD-001 to DD-012)

| ID | Decision | Alternatives Considered | Rationale |
|----|----------|------------------------|-----------|
| DD-001 | FastAPI replaces Django | Django (full-featured but sync-first), Flask (minimal but no async) | Async-first, automatic OpenAPI, Pydantic v2 native, lighter weight |
| DD-002 | BYOK + Claude Agent SDK | Hosted AI (pass-through billing), LangChain (framework lock-in) | Users control costs directly, no vendor lock-in on pricing, Claude best for code |
| DD-003 | Critical-only AI approval | Full approval (too slow), No approval (too risky) | Balance speed with safety; auto-execute non-destructive, approve destructive |
| DD-004 | MVP: GitHub + Slack only | GitLab, Jira, Discord, Bitbucket | Focus scope; GitHub has largest developer market share, Slack dominant for teams |
| DD-005 | No real-time collaboration in MVP | Y.js/HocusPocus (complex, Phase 2) | Last-write-wins simplicity; Supabase Realtime prepared for Phase 2 |
| DD-006 | Unified AI PR Review | Separate agents per aspect (architecture, security, quality) | Single review pass cheaper, contextual cross-references between aspects |
| DD-011 | Provider routing (Claude→code, Gemini→latency, OpenAI→embeddings) | Single provider for all | Optimize cost/latency per task type |
| DD-013 | Note-First, not Ticket-First workflow | Dashboard-first (conventional), Inbox-first | Core differentiator; reduces context-switching, preserves thinking |

### Infrastructure (DD-059 to DD-070)

| ID | Decision | Impact |
|----|----------|--------|
| DD-060 | Supabase platform (Auth, Storage, Queues, Realtime, Vault) | Consolidates 10+ services → 1 platform. 60-90% infrastructure cost savings |
| DD-061 | Supabase Auth + RLS (not custom JWT) | Database-level authorization, defense-in-depth, no application-level auth bugs |
| DD-064 | CQRS-lite with Service Classes + Payloads | Clean separation of commands and queries without Event Sourcing complexity |
| DD-065 | MobX (UI state) + TanStack Query (server state) | MobX for complex observable state; TanStack for caching, deduplication, optimistic updates |
| DD-066 | SSE for AI streaming (not WebSocket) | Simpler infrastructure, works with HTTP/2, cookie auth for EventSource, 30s heartbeat |
| DD-067 | Ghost text: 500ms trigger, 50 tokens max, code-aware | Balances responsiveness with API cost; word boundary handling prevents mid-word suggestions |
| DD-069 | Supabase Queues (pgmq) for background jobs | Native PostgreSQL, exactly-once within visibility window, 3 priority levels, 5min AI timeout |
| DD-070 | OpenAI embeddings (3072-dim, HNSW m=16, ef_construction=64) | Best embedding quality for RAG; HNSW provides sub-linear search on 100K+ vectors |

### Agent Architecture (DD-086 to DD-088)

| ID | Decision | Impact |
|----|----------|--------|
| DD-086 | Centralized conversational agent (1 orchestrator + 3 subagents + 8 skills) | Eliminates 13 siloed agents, unified context, single SSE stream, 8K token budget per turn |
| DD-087 | Filesystem-based skill system (`.claude/skills/` with YAML frontmatter) | Auto-discovery by Claude Agent SDK, easy to add/modify, version-controlled |
| DD-088 | MCP tool registry for domain operations | Custom tools registered via `create_sdk_mcp_server()`, RLS-enforced, decorator-based |

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
├── api/v1/routers/       # FastAPI routers (20 routers: issues, notes, ai_chat, ai_sessions, ai_approvals, etc.)
├── api/v1/schemas/       # Pydantic v2 request/response DTOs (not domain entities)
├── api/middleware/        # Auth, CORS, rate limiting, error handling (RFC 7807)
├── domain/
│   ├── models/           # Domain entities (Issue, Note, Cycle -- rich models with behavior + validation)
│   └── services/         # Domain services (pure business logic, no I/O)
├── application/
│   └── services/         # CQRS-lite: CreateIssueService.execute(payload), GetNoteService.execute(payload)
│       ├── note/         # Create, Update, Get, ContentConverter (TipTap↔Markdown), AIUpdateService
│       ├── issue/        # CRUD, state machine, activity tracking, Meilisearch indexing
│       ├── cycle/        # Sprint CRUD, velocity calculation, rollover
│       ├── ai_context/   # Context generation, refinement, export
│       ├── annotation/   # Margin annotation creation
│       ├── discussion/   # Threaded discussions per note block
│       └── integration/  # GitHub sync, webhook processing, auto-transition
├── ai/                   # AI layer
│   ├── agents/           # PilotSpaceAgent (orchestrator) + subagents + _archive/ (13 legacy agents)
│   ├── sdk/              # Claude Agent SDK: config, session_handler, permission_handler, hooks
│   ├── tools/            # MCP tools: note_tools (6), database_tools, search_tools, github_tools
│   ├── mcp/              # MCP server registry: create_note_tools_server()
│   ├── providers/        # Provider selector, mock generators, LLM client factory
│   ├── prompts/          # Prompt templates per agent/skill (issue extraction, ghost text, PR review, etc.)
│   ├── session/          # Conversation session management (Redis hot cache + PostgreSQL persistence)
│   ├── infrastructure/   # Cost tracker, key storage (Vault), rate limiter, resilience (circuit breaker)
│   └── workers/          # ConversationWorker (background queue consumer for async chat)
├── infrastructure/
│   ├── database/         # 22 SQLAlchemy models, 15 repositories, 21 Alembic migrations, RLS helpers
│   ├── cache/            # Redis client (sessions) + AICache (response caching)
│   ├── queue/            # Supabase Queues client (pgmq): enqueue, dequeue, ack, dead-letter
│   ├── auth/             # Supabase JWT validation, user lookup
│   └── search/           # Meilisearch client (notes, issues indexes)
├── spaces/               # Agent workspace sync: SpaceManager, LocalFileSystemSpace, ProjectBootstrapper
├── integrations/         # GitHub (OAuth, API client, webhooks, sync) + Slack (placeholder)
├── config.py             # Pydantic Settings (database, Redis, AI, queues, CORS, security, spaces)
├── container.py          # dependency-injector DeclarativeContainer (Singleton + Factory providers)
├── dependencies.py       # FastAPI Depends: CurrentUserId, DbSession, PilotSpaceAgentDep
└── main.py               # FastAPI app: lifespan (startup/shutdown), router registration, middleware

frontend/src/
├── app/                  # Next.js App Router: (auth)/, (workspace)/[workspaceSlug]/, (public)/
├── features/             # Feature-based modules
│   ├── notes/            # NoteCanvas, editor hooks, 13 TipTap extensions, ghost text service
│   ├── issues/           # IssueDetail, AIContextPanel, ConversationPanel, DuplicateWarning
│   ├── ai/               # ChatView component tree (25 components): ChatInput, MessageList, TaskPanel, ApprovalOverlay
│   ├── approvals/        # ApprovalQueue, ApprovalCard, ApprovalDetailModal
│   ├── cycles/           # CycleBoard, BurndownChart, VelocityChart, CycleRolloverModal
│   ├── github/           # PRReviewPanel, PRReviewStreaming, ReviewAspectCard
│   ├── costs/            # CostDashboard, CostByAgentChart, CostTrendsChart
│   └── settings/         # AISettingsPage, APIKeyForm, ProviderStatusCard
├── components/
│   ├── ui/               # shadcn/ui primitives (~25 components) + ConfidenceTagBadge, FAB
│   ├── editor/           # NoteCanvas, SelectionToolbar, MarginAnnotations, AutoTOC, VersionHistory
│   └── layout/           # AppShell, Sidebar, Header, OutlineTree
├── stores/               # MobX stores
│   ├── RootStore.ts      # Singleton containing all domain stores
│   ├── AuthStore.ts      # Supabase session, auth state changes
│   ├── UIStore.ts        # Sidebar, theme, modals, toasts (persisted to localStorage)
│   ├── WorkspaceStore.ts # Current workspace, members, roles
│   └── ai/               # 11 AI stores: PilotSpaceStore, GhostTextStore, ApprovalStore, ConversationStore, etc.
├── services/api/         # Typed API clients: client.ts (RFC 7807), notes, issues, ai, cycles, approvals
├── hooks/                # useMediaQuery, useApprovalFlow, usePinnedNotes, useTogglePin
├── lib/                  # supabase.ts, sse-client.ts (fetch ReadableStream), queryClient.ts, debounce.ts
└── types/                # Issue, Note, NoteAnnotation, Cycle, PendingApproval, AIContext, ChatMessage
```

---

## Quality Gates

All code must pass before merge. These are enforced by pre-commit hooks and CI.

**Backend**: `uv run pyright && uv run ruff check && uv run pytest --cov=.`

**Frontend**: `pnpm lint && pnpm type-check && pnpm test`

### Non-Negotiable Standards

| Standard | Rationale | Enforcement |
|----------|-----------|-------------|
| Type checking strict mode (pyright / TypeScript strict) | Catch type errors at build time, not runtime | Pre-commit hook, CI |
| Test coverage > 80% | Prevent regressions, document behavior | pytest-cov, vitest coverage |
| No N+1 queries | Database performance at scale (50K+ issues) | Code review, SQLAlchemy eager loading |
| No blocking I/O in async functions | FastAPI event loop must never block | pyright async analysis, code review |
| File size limit: 700 lines max | Maintainability, single responsibility | Pre-commit hook |
| No TODOs, mocks, or placeholder code | Production-readiness | Pre-commit hook |
| AI features respect DD-003 (human-in-the-loop) | User trust, safety for destructive actions | PermissionHandler, code review |
| RLS policies verified for multi-tenant data | Data isolation between workspaces | Database-level enforcement, integration tests |
| Conventional commits | Clear changelog, automated versioning | `feat\|fix\|refactor\|docs\|test\|chore(scope): description` |

---

## Architecture Patterns

**Load `docs/dev-pattern/45-pilot-space-patterns.md` first** for project-specific patterns.

### Backend Patterns

| Pattern | Implementation | Business Rationale |
|---------|----------------|-------------------|
| **CQRS-lite** (DD-064) | `CreateIssueService.execute(CreateIssuePayload) → CreateIssueResult` | Separate read/write models for scalability; no Event Sourcing complexity in MVP |
| **Repository** | `BaseRepository[T]` + specialized repos (15 total) with async SQLAlchemy 2.0 | Abstract persistence, enable testing with in-memory repos, enforce RLS |
| **Unit of Work** | `SQLAlchemyUnitOfWork` manages transaction boundaries | Atomic operations, consistent commit + event publishing |
| **Domain Events** | `IssueCreated`, `IssueStateChanged` published after commit | Decouple side effects (activity logging, notifications, search indexing) |
| **DI** (DD-064) | `dependency-injector`: Singleton for config/engine, Factory for repos/sessions | Testable services, explicit dependencies, no global state |
| **Errors** | RFC 7807 Problem Details (`DomainError` → `application/problem+json`) | Standard error format, rich details, machine-readable |
| **Validation** | Pydantic v2 schemas at API boundary, domain invariants in entities | Fail fast at boundary, rich domain behavior inside |
| **Auth** (DD-061) | Supabase Auth + RLS: JWT validation → workspace_id extraction → RLS enforcement | Defense-in-depth; even if application code has a bug, database prevents data leaks |

### AI Agent Patterns

| Pattern | Implementation | Business Rationale |
|---------|----------------|-------------------|
| **Centralized agent** (DD-086) | PilotSpaceAgent as single orchestrator with skills + subagents | Unified context, single conversation history, eliminates 13 siloed agents |
| **SDK integration** (DD-002) | `query()` for one-shot, `ClaudeSDKClient` for multi-turn | Fast one-shot for simple tasks, stateful sessions for complex workflows |
| **Skill system** (DD-087) | Filesystem `.claude/skills/` with YAML frontmatter | Easy to add/modify skills, version-controlled, auto-discovered by SDK |
| **MCP tools** (DD-088) | `create_sdk_mcp_server()` for note/database/search/GitHub operations | Structured tool access with RLS enforcement, operation payloads not direct mutations |
| **Provider routing** (DD-011) | Task-specific selection: Claude→code, Gemini→latency, OpenAI→embeddings | Optimize cost/latency per task; fallback chain for resilience |
| **Approval** (DD-003) | SDK `canUseTool` callback → PermissionHandler → ApprovalStore | Human oversight for critical actions; configurable per-workspace autonomy level |
| **Streaming** (DD-066) | SSE via FastAPI StreamingResponse, 8 event types | Real-time AI output; simpler than WebSocket for unidirectional streams |
| **Resilience** | `ResilientExecutor` (retry + backoff) + `CircuitBreaker` (per-provider) | Prevent cascade failures; graceful degradation when providers are unavailable |
| **Session persistence** | Redis (30-min hot cache) + PostgreSQL (ai_session, ai_message tables) | Fast resumption for active conversations; durable storage for history |

### Frontend Patterns

| Pattern | Implementation | Business Rationale |
|---------|----------------|-------------------|
| **State split** (DD-065) | MobX for UI state (selection, filters, modals, drag), TanStack Query for server state (API data) | Clear ownership; MobX reactive for complex UI, TanStack for caching/sync |
| **Anti-pattern** | Never store server data in MobX stores | TanStack Query is source of truth for API data; MobX only for ephemeral UI state |
| **Feature folders** | `features/{domain}/` (notes, issues, ai, cycles, approvals, costs) | Colocation of components, hooks, stores per business domain |
| **Editor extensions** | 13 TipTap extensions (ghost text, annotations, slash commands, block IDs, etc.) | Modular editor features; each extension is independently testable |
| **Optimistic updates** | TanStack Query `onMutate` with snapshot + rollback on error | Instant UI feedback; MobX `PendingOperations` map tracks in-flight mutations |
| **SSE handling** | Custom `sse-client.ts` (fetch ReadableStream for POST) + `use-sse-stream` hook | EventSource only supports GET; custom client enables POST with auth headers |
| **Auto-save** | MobX reaction watches `currentNote.content`, debounces 2s, calls `saveNote()` | No explicit save button; dirty state tracked, save indicator shown |
| **Accessibility** | WCAG 2.2 AA: keyboard nav, ARIA labels, focus management, `prefers-reduced-motion` | Inclusive by default; all interactive elements reachable via keyboard |

---

## Key Entities

### Domain Model

| Entity | Business Purpose | Key Relationships | Key Fields |
|--------|-----------------|-------------------|-----------|
| **Note** | Primary brainstorming document. Block-based TipTap JSON content. Home view default. | Has many NoteAnnotations, NoteIssueLinks, ThreadedDiscussions | content (JSONB), word_count, reading_time_mins, is_pinned, sync_state |
| **NoteAnnotation** | AI margin suggestion linked to specific block. Shows clarifying questions, issue detection, improvement suggestions. | Belongs to Note, references block_id | type (suggestion/question/issue_detected), confidence (0-1), status (pending/accepted/rejected) |
| **NoteIssueLink** | Bidirectional connection between notes and issues. Enables living documentation. | Joins Note ↔ Issue, references block_id | link_type (CREATED/EXTRACTED/REFERENCED), sync_direction |
| **Issue** | Work item with state machine. AI-enhanced at creation (title, labels, priority). | Belongs to Project, has State, Cycle, Module, Labels, Assignee | sequence_id, title, description, priority (urgent/high/medium/low), ai_metadata |
| **AIContext** | Aggregated context for an issue: related docs, code files, implementation tasks, Claude Code prompts. | Belongs to Issue | related_issues, documents, codebase_files (AST-aware), tasks (with dependency graph) |
| **Cycle** | Sprint container with time boundaries and velocity metrics. | Contains Issues, belongs to Project | start_date, end_date, status (upcoming/current/completed), velocity metrics |
| **Module** | Epic grouping for large features. Progress tracking by story points or issue count. | Contains Issues, belongs to Project, optional parent_id for hierarchy | target_date, lead_id, progress percentage |
| **ChatSession** | Multi-turn AI conversation. SDK session ID for resumption. | Has many ChatMessages, belongs to User + Workspace | sdk_session_id, context (JSONB), 24h TTL |
| **ChatMessage** | Individual message in conversation. Stores role, content, tool invocations. | Belongs to ChatSession | role (user/assistant/system), content, tool_calls (JSONB), token_usage |
| **TokenUsage** | Per-request cost tracking for BYOK transparency. | Belongs to ChatMessage | prompt_tokens, completion_tokens, cached_tokens, cost_usd, provider, model |

### State Machine (Issues)

Backlog → Todo → In Progress → In Review → Done (forward transitions). Any state → Cancelled (terminal). Reopen: Done → Todo (reverse). Invalid: Backlog → Done (no skipping).

---

## Current Implementation Status

**Overall MVP Completion**: 75-80% | **Remaining**: ~43 tasks across 4-6 weeks

### Backend (69,435 lines Python)

| Layer | Status | Completion |
|-------|--------|------------|
| API (20 routers) | Production-ready | 95% |
| Application Services (8 domains) | Production-ready | 90% |
| Domain (entities, value objects) | Complete | 95% |
| Infrastructure (22 models, 15 repos, 21 migrations) | Complete | 95% |
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
| Note Editor (TipTap, 13 extensions) | Scaffold + partial | 65% |
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

The implementation follows a 6-phase remediation plan migrating from siloed agents to the centralized conversational architecture. See `docs/architect/pilotspace-implementation-plan.md` for the full plan with 173 tasks, acceptance criteria, and definitions of done.

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
| **Data model (21 entities)** | `specs/001-pilot-space-mvp/data-model.md` |
| **UI/UX specification (v3.3.0)** | `specs/001-pilot-space-mvp/ui-design-spec.md` |
| **Technical research** | `specs/001-pilot-space-mvp/research.md` |

### Architecture (docs/architect/)

| Topic | Document |
|-------|----------|
| **Architecture overview & AI QA Index** | `docs/architect/README.md` |
| **Agent architecture (centralized)** | `docs/architect/pilotspace-agent-architecture.md` |
| **Agent remediation plan** | `docs/architect/agent-architecture-remediation-plan.md` |
| **Implementation plan (detailed)** | `docs/architect/pilotspace-implementation-plan.md` |
| **Claude SDK integration** | `docs/architect/claude-agent-sdk-architecture.md` |
| **AI layer (16 agents)** | `docs/architect/ai-layer.md` |
| **Feature-to-component mapping** | `docs/architect/feature-story-mapping.md` |
| **Backend architecture** | `docs/architect/backend-architecture.md` |
| **Frontend architecture** | `docs/architect/frontend-architecture.md` |
| **Infrastructure (Supabase)** | `docs/architect/infrastructure.md` |
| **Supabase integration** | `docs/architect/supabase-integration.md` |
| **RLS security patterns** | `docs/architect/rls-patterns.md` |
| **Features checklist** | `docs/architect/FEATURES_CHECKLIST.md` |

### Standards & Patterns

| Topic | Document |
|-------|----------|
| **Project constitution** | `.specify/memory/constitution.md` |
| **Architecture decisions (88)** | `docs/DESIGN_DECISIONS.md` |
| **Project vision & personas** | `docs/PROJECT_VISION.md` |
| **Feature specifications (17 features)** | `docs/PILOT_SPACE_FEATURES.md` |
| **Dev patterns (start here)** | `docs/dev-pattern/README.md` |
| **Pilot Space patterns (overrides)** | `docs/dev-pattern/45-pilot-space-patterns.md` |
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

| Standard Pattern | Override | Rationale |
|------------------|----------|-----------|
| 21a: Zustand | MobX | Complex observable state (selection, drag, modal trees), reactions for auto-save |
| 17: Custom JWT | Supabase Auth + RLS | Database-level authorization, defense-in-depth |
| 10: Kafka | Supabase Queues (pgmq) | Native PostgreSQL, no separate broker, exactly-once semantics |

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

- Use **CQRS-lite pattern**: Service Classes with Payloads, not direct DB manipulation. Each service has `execute(payload) → result`.
- Use **dependency-injector** for DI, not manual wiring. Singleton for config/engine, Factory for repos/sessions.
- Use **RFC 7807** Problem Details for all error responses (`application/problem+json`).
- All async functions must use **async SQLAlchemy** (`AsyncSession`). No blocking I/O.
- Check **RLS policies** when adding/modifying queries for multi-tenant data. All tables scoped by `workspace_id`.
- AI features must respect **DD-003** (human-in-the-loop approval via `PermissionHandler`).
- New AI agents go through **PilotSpaceAgent** as skills or subagents, not standalone.

### For Frontend Agents

- Use **MobX** for client state (`makeAutoObservable`, `observer()` pattern). Never store API data in MobX.
- Use **TanStack Query** for server state (API data fetching/caching). Use `useQuery` for reads, `useMutation` for writes with optimistic updates.
- Use **shadcn/ui** components as base, extend with feature-specific variants.
- All components must be **WCAG 2.2 AA** compliant (keyboard nav, ARIA labels, focus management).
- AI interactions go through **PilotSpaceStore** (unified store), not siloed stores.
- SSE events map to specific store updates -- see the event mapping in `pilotspace-agent-architecture.md` section 8.

### For AI/Agent Layer Agents

- **PilotSpaceAgent** is the single orchestrator -- do not create new independent agents.
- Simple operations → **skills** (filesystem `.claude/skills/`). Complex operations → **subagents**.
- All tools return **operation payloads** (`status: pending_apply`), not direct DB mutations.
- Note tools use **ContentConverter** for TipTap ↔ Markdown conversion with block ID preservation.
- SSE transform pipeline: SDK message → `transform_sdk_message()` → Frontend SSE event.
- **Prompt caching** must be enabled for system prompts (`cache_control: ephemeral`).
- **Error handling**: Use `ResilientExecutor` for retries, `CircuitBreaker` for provider failures.

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
- CLAUDE.md: Comprehensive enhancement with business context, technical details, design decisions, and use cases per section
