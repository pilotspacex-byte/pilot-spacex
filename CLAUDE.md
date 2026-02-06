# Pilot Space - AI-Augmented SDLC Platform

**Built on "Note-First" paradigm** - Think first, structure later.

---

## Quick Reference

### Role-Based Navigation

**Backend developers** → See `backend/CLAUDE.md` for:
- Backend architecture & patterns
- CQRS-lite service design
- RLS security requirements
- Quality gates & testing

**Frontend developers** → See `frontend/CLAUDE.md` for:
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

### Mission

**Pilot Space** is an AI-augmented SDLC platform built on a "Note-First" paradigm. It enables software development teams to ship quality software faster through intelligent AI assistance that augments human expertise in architecture design, documentation, code review, and project management -- while maintaining full human oversight and control.

### Business Context

**Problem**: Traditional issue trackers force form-filling before thinking is complete. Teams brainstorm in Slack/Notion, then manually transcribe into tickets, losing context. AI in existing tools is bolt-on autocomplete, not embedded intelligence.

**Solution**: Users start with a collaborative note canvas. AI acts as an embedded co-writing partner -- suggesting inline completions (ghost text), asking clarifying questions in the margin (annotations), and detecting actionable items. Issues emerge naturally from refined thinking, pre-filled with context.

**Value Proposition**: "Think first, structure later" -- issues emerge from refined thinking rather than form-filling.

Traditional PM: Start with forms → structure upfront → AI bolt-on → dashboard home.
Pilot Space: Start with notes → structure emerges → AI embedded → **Note Canvas home**.

### Target Personas

- **TinDang (Architect)**: AI-powered code review + architecture analysis in PR reviews
- **Tech Lead**: Unified PR review + task decomposition + velocity tracking
- **PM**: AI issue enhancement + Note-First workflow for natural requirement capture
- **Dev (Junior)**: AI Context per issue with ready-to-use Claude Code prompts

### Scale & Monetization

- **Target Scale**: 5-100 team members per workspace
- **Pricing Model**: All features free (open source, self-hosted). Paid tiers for support SLAs only. BYOK (Bring Your Own Key) -- no AI cost pass-through.

*Full business strategy, competitive moat, pricing, GTM phases: see `docs/BUSINESS_CONTEXT.md`*

---

## Technology Stack

### Backend

backend_tech[5]{component,technology,version,decision}
Framework,FastAPI,0.110+,DD-001 (async-first stack decision)
ORM,SQLAlchemy 2.0 (async),2.0+,DD-001 (async-first stack decision)
Validation,Pydantic v2,2.6+,DD-001 (async-first stack decision)
DI,dependency-injector,4+,DD-064
Runtime,Python,3.12+,--

**Note**: DD-001 encompasses the entire async-first backend stack philosophy (FastAPI + SQLAlchemy 2.0 async + Pydantic v2), replacing Django's synchronous architecture.

### Frontend

frontend_tech[6]{component,technology,version,decision}
Framework,Next.js (App Router),14+,--
UI State,MobX,6+,DD-065
Server State,TanStack Query,5+,DD-065
Styling,TailwindCSS + shadcn/ui,3.4+,--
Rich Text,TipTap/ProseMirror,2+,--
Language,TypeScript,5.3+,--

### AI & Orchestration

ai_tech[5]{component,technology,decision}
Orchestration,Claude Agent SDK,"DD-002, DD-086"
Primary LLM,Anthropic Claude (BYOK),DD-002
Latency LLM,Google Gemini Flash (BYOK),DD-011
Embeddings,Google Gemini gemini-embedding-001 (BYOK),"DD-011, DD-070"
Streaming,SSE via FastAPI StreamingResponse,DD-066

See [Provider Routing](#provider-routing-dd-011) for task-to-provider mapping and fallback chain.

### Infrastructure & Platform

infra_tech[8]{component,technology,decision}
Database,PostgreSQL 16+ with pgvector,DD-060
Auth,Supabase Auth (GoTrue) + RLS,DD-061
Cache,Redis 7 (sessions 30-min TTL; AI cache 7-day TTL),--
Search,Meilisearch 1.6 (typo-tolerant full-text),--
Queues,Supabase Queues (pgmq + pg_cron),DD-069
Storage,Supabase Storage (S3-compatible),DD-060
Realtime,Supabase Realtime (Phoenix WebSocket),DD-060
Secrets,Supabase Vault (AES-256-GCM),DD-060

---

## Production Architecture Overview

### Infrastructure Topology

Three-tier containerized architecture: Frontend (Next.js 14 App Router) → Backend (FastAPI on port 8000) → Data (PostgreSQL 16+ with RLS, Redis, Meilisearch).

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

### Design Philosophy (DD-086)

Migrated from 13 siloed agents to a **centralized conversational agent**. Single `PilotSpaceAgent` orchestrator handles all user-facing AI conversations through:

- **Skills**: Single-turn, stateless, filesystem-based (`.claude/skills/`). For focused tasks (extraction, enhancement, duplicates). Invoked via slash commands or intent detection.
- **Subagents**: Multi-turn, stateful, spawned by orchestrator. For complex tasks (PR review, AI context, docs). Results flow through orchestrator's SSE stream.

**Exception**: Fast-path independent agents (GhostTextAgent) bypass orchestrator for latency-critical operations (<2.5s SLA). These agents use direct provider calls without multi-turn context management.

### Agent Roster

agents[5]{agent,type,model,latency,purpose}
GhostTextAgent,Independent,Gemini Flash,<2s,Inline completions on 500ms typing pause; max 50 tokens; code-aware
PilotSpaceAgent,Orchestrator,Claude Sonnet,<10s,Routes requests to skills/subagents; manages sessions; note sync; tool auth
PRReviewAgent,Subagent,Claude Opus,<5min,Unified code review (architecture; security; quality; docs) with severity tags
AIContextAgent,Subagent,Claude Opus,<30s,Aggregates issue context: related issues; notes; code files; dependency graphs
DocGeneratorAgent,Subagent,Claude Sonnet,<60s,Generates ADR; API docs; technical specs from code/issues/notes

### Skill System (DD-087)

Filesystem-based `.claude/skills/` with YAML frontmatter, auto-discovered by SDK.

skills[8]{skill,purpose,output}
extract-issues,Detect actionable items; categorize Explicit/Implicit/Related,Issue candidates with title/description/priority/type
enhance-issue,Improve issue quality at creation,Enhanced title; acceptance criteria; suggested labels
improve-writing,Enhance text clarity preserving meaning,Improved text preserving user voice
summarize,Multi-format content summarization,Bullet; executive; or detailed breakdown
find-duplicates,Semantic similarity detection (threshold: 70%),Ranked similar issues with scores
recommend-assignee,Expertise matching for team members,Ranked assignees with expertise %
decompose-tasks,Break features into subtasks,Subtask list with Fibonacci points; dependency graph
generate-diagram,Create architecture diagrams,Mermaid or PlantUML output

### Human-in-the-Loop Approval (DD-003)

**Non-destructive** → Auto-execute, notify (labels, ghost text, annotations, auto-transition).
**Content creation** → Require approval, configurable (create issues, PR comments, docs).
**Destructive** → **Always require approval** (delete issues, merge PRs, archive workspaces).

Implementation: SDK `canUseTool` → `PermissionHandler` → `ApprovalStore` with 24h auto-expiry.

**Approval Classification Matrix**:

approval_matrix[12]{operation,category,approval_required,permission_handler}
enhance_text,Non-destructive,No (auto-execute),PermissionHandler.auto_approve()
improve_writing,Non-destructive,No (auto-execute),PermissionHandler.auto_approve()
summarize,Non-destructive,No (auto-execute),PermissionHandler.auto_approve()
extract_issues,Content creation,Yes (configurable),PermissionHandler.request_approval()
create_issue,Content creation,Yes (configurable),PermissionHandler.request_approval()
enhance_issue,Content creation,Yes (configurable),PermissionHandler.request_approval()
add_label,Non-destructive,No (auto-execute),PermissionHandler.auto_approve()
assign_issue,Non-destructive,No (auto-execute),PermissionHandler.auto_approve()
post_pr_comment,Content creation,Yes (configurable),PermissionHandler.request_approval()
delete_issue,Destructive,Yes (always),PermissionHandler.require_approval()
merge_pr,Destructive,Yes (always),PermissionHandler.require_approval()
archive_workspace,Destructive,Yes (always),PermissionHandler.require_approval()

### MCP Note Tools (6 tools)

Registered via `create_note_tools_server()`. All return operation payloads (`status: pending_apply`), not direct DB mutations. Backend `transform_sdk_message()` converts markdown to TipTap JSON and emits SSE `content_update` events.

mcp_tools[6]{tool,operation,use_case}
update_note_block,Replace or append block content,Precise text modification by block ID
enhance_text,Improve clarity without meaning change,Professional polish; expand abbreviations
summarize_note,Read full note with metadata,Context gathering before modifications
extract_issues,Create multiple linked issues from blocks,Bulk extraction from meeting notes
create_issue_from_note,Create single linked issue,Convert selection to bug/feature/task
link_existing_issues,Search and link workspace issues,Find related work; duplicate prevention

### Skills vs MCP Tools: Relationship

**Terminology Clarification**:

- **Skill** (DD-087): YAML file in `.claude/skills/` with frontmatter. Auto-discovered by SDK. Invoked via slash commands (`/extract-issues`) or intent detection. Defines behavior, prompt, and expected output format.

- **MCP Tool**: Python function registered via `create_note_tools_server()`. Exposed to Claude SDK as callable tools. Receives structured parameters, returns operation payloads. Backend applies transformations.

**Relationship Flow**:
```
User types "/extract-issues"
  → SDK detects skill intent
  → Skill executes (calls MCP Tool if needed)
  → MCP Tool: extract_issues() returns payload
  → Backend: transform_sdk_message() applies operations
  → SSE: content_update event to frontend
```

**Skills-to-Tools Mapping**:

skill_tool_mapping[8]{skill,mcp_tool,implementation}
extract-issues,extract_issues,Skill invokes MCP tool
enhance-issue,enhance_text (partial),Skill invokes MCP tool for text enhancement only
improve-writing,enhance_text,Skill invokes MCP tool
summarize,summarize_note,Skill invokes MCP tool
find-duplicates,--,Skill only (no direct tool; uses semantic search)
recommend-assignee,--,Skill only (no direct tool; uses workspace member data)
decompose-tasks,--,Skill only (no direct tool; uses issue analysis)
generate-diagram,--,Skill only (no direct tool; generates Mermaid/PlantUML text)

### Provider Routing (DD-011)

**Agentic Tasks** (complexity-based routing):
- **Complex analysis** (PR review, architecture analysis) → **Claude Opus** (preferred for deep reasoning)
- **Context aggregation** (AI context, simple routing) → **Claude Sonnet** (cost-optimized fallback)
- **Orchestration** (PilotSpaceAgent routing, chat management) → **Claude Sonnet**

**One-shot Tasks**:
- **Content enhancement** (enhance, summarize) → **Claude Sonnet** via `query()` (simple, stateless)

**Latency-Critical**:
- **Ghost text** (inline completions) → **Google Gemini 2.0 Flash** (<1.5s response time)

**Embeddings**:
- **Semantic search, RAG** → **Google Gemini gemini-embedding-001** (768-dim vectors)

**Fallback Chain** (on circuit breaker): Claude Opus → Claude Sonnet → Gemini Pro → Error + Queue. Circuit breaker: 5 failures trigger OPEN state, 60s recovery to HALF_OPEN, 1 probe request.

**Optimizations**: Prompt caching (`cache_control: ephemeral`) saves 63% tokens. Context window pruned at 50k tokens, preserving 10 most recent messages.

### Error Handling & Resilience

- **Retry**: `ResilientExecutor` exponential backoff (1s base, 60s cap, 30% jitter, 3 attempts). Retries on timeout/rate limit only.
- **Circuit Breaker**: Per-provider. CLOSED → OPEN (5 failures) → HALF_OPEN (60s, 1 probe).
- **SSE Abort**: Backend `AbortController`. Frontend max 3 reconnects with exponential backoff.
- **Offline Queue**: pgmq when API unavailable, retry on reconnection.
- **Cost Tracking**: Per-request token logging, per-provider pricing, budget alerts at 90%.

---

## Design Decisions Summary

88 total decisions documented in `docs/DESIGN_DECISIONS.md`. **Key decisions by category** (selected highlights below; full list in design decisions doc):

### Foundational (DD-001 to DD-013)

dd_foundational[8]{id,decision,rationale}
DD-001,FastAPI replaces Django,Async-first; OpenAPI; Pydantic v2 native
DD-002,BYOK + Claude Agent SDK,Users control costs; no vendor lock-in; Claude best for code
DD-003,Critical-only AI approval,Balance speed with safety
DD-004,MVP: GitHub + Slack only,Focus scope on largest market share
DD-005,No real-time collab in MVP,Last-write-wins; Supabase Realtime for Phase 2
DD-006,Unified AI PR Review,Single pass cheaper; cross-aspect references
DD-011,Provider routing per task,Optimize cost/latency per task type
DD-013,Note-First workflow,Core differentiator

### Infrastructure (DD-059 to DD-070)

dd_infra[8]{id,decision,impact}
DD-060,Supabase platform,Consolidates 10+ services; 60-90% cost savings
DD-061,Supabase Auth + RLS,Database-level authorization; defense-in-depth
DD-064,CQRS-lite + Service Classes,Clean command/query separation without Event Sourcing
DD-065,MobX (UI) + TanStack Query (server),MobX for observable state; TanStack for caching
DD-066,SSE for AI streaming,Simpler than WebSocket; HTTP/2 compatible; cookie auth
DD-067,Ghost text: 500ms/50 tokens/code-aware,Balance responsiveness with cost
DD-069,Supabase Queues (pgmq),Native PostgreSQL; exactly-once; 3 priority levels
DD-070,Gemini embeddings 768-dim HNSW,Best quality; sub-linear search on 100K+ vectors

### Agent Architecture (DD-086 to DD-088)

DD-086: Centralized agent (1+3+8) → unified context, single SSE stream, 8K token budget.
DD-087: Filesystem skill system → auto-discovery, version-controlled, easy to modify.
DD-088: MCP tool registry → RLS-enforced, operation payloads, decorator-based.

---

## Development Commands

### Backend (Python 3.12+)

**Setup**: `cd backend && uv venv && source .venv/bin/activate && uv sync && pre-commit install`
**Dev server**: `uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000`
**Quality gates**: `uv run pyright && uv run ruff check && uv run pytest --cov=.`
**Migrations**: `alembic revision --autogenerate -m "Description"` then `alembic upgrade head`

### Frontend (Node 20+, pnpm 9+, TypeScript 5.3+, Next.js 14+)

**Setup**: `cd frontend && pnpm install`
**Dev server**: `pnpm dev`
**Quality gates**: `pnpm lint && pnpm type-check && pnpm test`
**E2E**: `pnpm test:e2e`

### Docker Compose

`docker compose up -d` → Frontend :3000, Backend API :8000/docs, Supabase Studio :54323

---

## Project Structure

Read details at `project-structure.md` but concise summary below.

### Backend (`backend/src/pilot_space/`)

5-layer Clean Architecture:

- **api/v1/** — 20 FastAPI routers + Pydantic v2 schemas + middleware (auth, CORS, rate limiting, RFC 7807 errors)
- **domain/** — Rich domain entities (Issue, Note, Cycle) with behavior + validation, domain services (pure logic, no I/O)
- **application/services/** — 8 domain services: note, issue, cycle, ai_context, annotation, discussion, integration
- **ai/** — PilotSpaceAgent orchestrator + subagents, Claude Agent SDK integration, MCP tools, providers, session management, cost tracking
- **infrastructure/** — 22 SQLAlchemy models, ~15 repositories (some repos handle multiple models), 21 Alembic migrations, RLS helpers, Redis cache, pgmq queue, Supabase JWT auth

*Full structure with current counts: see `backend/CLAUDE.md`*

### Frontend (`frontend/src/`)

Feature-based architecture:

- **app/** — Next.js App Router: auth, workspace/[slug], public routes
- **features/** — Domain modules: notes (canvas + 13 TipTap extensions + ghost text), issues, ai (ChatView), approvals, cycles, github, costs, settings
- **components/** — Shared UI (25 shadcn/ui primitives), editor (canvas + toolbar + annotations + TOC), layout (shell + sidebar + header)
- **stores/** — MobX: RootStore, AuthStore, UIStore, WorkspaceStore, **11 AI stores**: PilotSpaceStore (unified orchestrator), GhostTextStore, PRReviewStore, AIContextStore, DocGeneratorStore, ApprovalStore, CostTrackingStore, SessionStore, ChatHistoryStore, AnnotationStore, ExtractionStore
- **services/api/** — 9 typed API clients with RFC 7807 error handling

*Full structure: see `frontend/CLAUDE.md`*

---

## Quality Standards

### Non-Negotiable Standards

Write tests for all new features and bug fixes. **80% coverage catches 85% of regressions before deployment.** This metric directly correlates with production stability.

quality_gates[9]{standard,enforcement}
Strict type checking (pyright / TypeScript strict),Pre-commit; CI
Test coverage > 80%,pytest-cov; vitest
No N+1 queries,SQLAlchemy eager loading; review
No blocking I/O in async functions,pyright analysis; review
File size: 700 lines max for code file,Pre-commit
No TODOs; mocks; placeholder code,Pre-commit
AI features respect DD-003 (human-in-the-loop),PermissionHandler; review
RLS verified for multi-tenant data,DB enforcement; integration tests
Conventional commits,feat|fix|refactor|docs|test|chore(scope): description

**Blocking calls in async context cause thread starvation under load.** Can degrade API latency by 10-50x.

---

## Architecture Patterns

**Load `docs/dev-pattern/45-pilot-space-patterns.md` first** for project-specific patterns.

### Backend Patterns

backend_patterns[8]{pattern,implementation,rationale}
CQRS-lite (DD-064),Service.execute(Payload) → Result,Separate read/write without Event Sourcing
Repository,BaseRepository[T] + 15 repos; async SQLAlchemy,Abstract persistence; testable; RLS-enforced
Unit of Work,SQLAlchemyUnitOfWork transaction boundaries,Atomic operations + event publishing
Domain Events,IssueCreated; IssueStateChanged after commit,Decouple side effects
DI (DD-064),dependency-injector: Singleton (config/engine); Factory (repos/sessions),Testable; explicit; no global state
Errors,RFC 7807 Problem Details,Standard machine-readable format
Validation,Pydantic v2 at boundary; domain invariants in entities,Fail fast at edge; rich behavior inside
Auth (DD-061),Supabase Auth + RLS: JWT → workspace_id → RLS enforcement,Defense-in-depth

*Summary above for quick reference; full patterns with code examples: see `backend/CLAUDE.md`*

### AI Agent Patterns

ai_patterns[9]{pattern,implementation,rationale}
Centralized agent (DD-086),PilotSpaceAgent orchestrator + skills + subagents,Unified context; eliminates 13 siloed agents
SDK integration (DD-002),query() one-shot; ClaudeSDKClient multi-turn,Fast for simple; stateful for complex
Skill system (DD-087),Filesystem .claude/skills/ YAML frontmatter,Auto-discovered; version-controlled
MCP tools (DD-088),create_sdk_mcp_server() for domain operations,RLS-enforced; operation payloads
Provider routing (DD-011),See Provider Routing section,Optimize cost/latency + fallback chain
Approval (DD-003),canUseTool → PermissionHandler → ApprovalStore,Human oversight; configurable autonomy
Streaming (DD-066),SSE; 8 event types,Real-time; simpler than WebSocket
Resilience,ResilientExecutor + CircuitBreaker per provider,Prevent cascade; graceful degradation
Sessions,Redis (30-min hot) + PostgreSQL (durable),Fast resumption + persistent history

*Summary above for quick reference; see inline sections for detailed implementation notes*

### Frontend Patterns

frontend_patterns[7]{pattern,implementation,rationale}
State split (DD-065),MobX for UI; TanStack Query for server data,Clear ownership; never store API data in MobX
Feature folders,features/{domain}/ per business domain,Colocated components; hooks; stores
Editor extensions,13 TipTap extensions (independently testable),Modular editor capabilities
Optimistic updates,TanStack onMutate + snapshot + rollback,Instant feedback; MobX tracks in-flight ops
SSE handling,Custom sse-client.ts (fetch ReadableStream for POST),EventSource is GET-only; custom supports POST + auth
Auto-save,MobX reaction → 2s debounce → saveNote(),No save button; dirty state tracked
Accessibility,WCAG 2.2 AA: keyboard nav; ARIA; focus management; prefers-reduced-motion,Inclusive by default

*Summary above for quick reference; full patterns with React/TypeScript examples: see `frontend/CLAUDE.md`*

---

## UI/UX Design System

*Full specification: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0*

### Design Philosophy

Three adjectives: **Warm, Capable, Collaborative**.

**Inspirations**: Craft (layered surfaces), Apple (squircle corners, frosted glass), Things 3 (natural colors, spacious calm).

**NOT**: Cold enterprise software, generic shadcn/ui defaults, AI as separate "system", dense displays.

### Color System

**Base Palette** (Warm Neutrals):

base_palette[6]{token,light,dark,usage}
--background,#FDFCFA,#1A1A1A,Primary surface
--background-subtle,#F7F5F2,#1F1F1F,Secondary surface
--foreground,#171717,#EDEDED,Primary text
--foreground-muted,#737373,#999999,Secondary text
--border,#E5E2DD,#2E2E2E,Borders
--border-subtle,#EBE8E4,#262626,Subtle borders

**Accent Colors**:

accent_colors[7]{token,value,usage}
--primary,#29A386 / #34B896,Primary actions (teal-green)
--primary-hover,#238F74,Hover state
--primary-muted,#29A38615,Subtle backgrounds
--ai,#6B8FAD / #7DA4C4,AI elements (dusty blue)
--ai-muted,#6B8FAD15,AI annotation backgrounds
--ai-border,#6B8FAD30,AI element borders
--destructive,#D9534F / #E06560,Delete/remove actions

**Issue State Colors**: Backlog `#9C9590`, Todo `#5B8FC9`, In Progress `#D9853F`, In Review `#8B7EC8`, Done `#29A386`, Cancelled `#D9534F`

**Priority Colors**: Urgent `#D9534F`, High `#D9853F`, Medium `#C4A035`, Low `#5B8FC9`, None `#9C9590`

### Component Design Language

**Buttons**: 6 variants (default/secondary/outline/ghost/destructive/ai). 5 sizes. Hover: scale 2% + shadow.

**Cards**: 4 variants (default/elevated/interactive/glass). Interactive: translateY -2px + scale 1% on hover.

**Inputs**: 38px height, rounded 10px, 14px font, focus primary border + 3px ring.

*Full component specs, typography, spacing, animations: see `specs/001-pilot-space-mvp/ui-design-spec.md` Sections 5-6*

### Page Catalog

pages[12]{page,route,capabilities}
Login,/login,Centered form; email/password + OAuth
Home,/[workspaceSlug],Redirects to Notes List (Note Canvas = home)
Notes List,.../notes,Grid/List toggle; search; sort; filters
Note Editor,.../notes/[noteId],65/35 split (canvas + ChatView); auto-save 2s
Issues,.../issues,Board/List/Table; filters; keyboard nav
Issue Detail,.../issues/[issueId],70/30 split; inline edit; AI Context tabs
Projects,.../projects,3-col grid; progress bars
Cycle Detail,.../cycles/[cycleId],Burndown + Velocity charts
AI Chat,.../chat,Full-page ChatView; session list
Approvals,.../approvals,Tabs; countdown timer; content diff
AI Costs,.../costs,Summary cards; cost trends; export CSV
Settings,.../settings/*,General; Members; AI Providers; Integrations

*Full wireframes and interaction patterns: see `specs/001-pilot-space-mvp/ui-design-spec.md` Sections 7-9*

---

## Key Entities

entities[10]{entity,purpose,relationships}
Note,Block-based TipTap document; home view default,Has annotations; issue links; discussions
NoteAnnotation,AI margin suggestion per block,Belongs to Note + block_id; confidence 0-1
NoteIssueLink,Bidirectional note↔issue connection,CREATED/EXTRACTED/REFERENCED types
Issue,Work item with state machine,Belongs to Project; has State/Cycle/Labels
AIContext,Aggregated issue context,Belongs to Issue
Cycle,Sprint container with velocity metrics,Contains Issues; belongs to Project
Module,Epic grouping with progress tracking,Contains Issues; optional hierarchy
ChatSession,Multi-turn conversation; SDK session,Has messages; 24h TTL
ChatMessage,Role + content + tool_calls + token_usage,Belongs to ChatSession
TokenUsage,Per-request BYOK cost tracking,prompt/completion/cached tokens; cost_usd

**Issue State Machine**: Backlog → Todo → In Progress → In Review → Done. Any → Cancelled. Done → Todo (reopen). No skipping.

**State-Cycle Constraints**:

state_cycle_rules[7]{state,cycle_requirement,transition_notes}
Backlog,No Cycle assignment,Issues in backlog are not scheduled
Todo,Cycle optional,Can be assigned to backlog / current / future cycle
In Progress,Cycle required,Must be assigned to active cycle
In Review,Cycle required,Must remain in active cycle
Done,Leaves active cycle,Archived with cycle completion metrics
Cancelled,Leaves cycle immediately,No archival; excluded from metrics
Reopened (Done→Todo),Returns to original cycle or Todo,Cycle reassignment allowed

*Full data model (21 entities): see `specs/001-pilot-space-mvp/data-model.md`*

---

## Documentation Entry Points

### Specifications

spec_docs[6]{topic,document}
MVP specification,specs/001-pilot-space-mvp/spec.md
MVP implementation plan,specs/001-pilot-space-mvp/plan.md
Phase 2/3 specs,specs/002-*/spec.md; specs/003-*/spec.md
Data model (21 entities),specs/001-pilot-space-mvp/data-model.md
UI/UX spec (v4.0),specs/001-pilot-space-mvp/ui-design-spec.md
Business design (v2.0),specs/001-pilot-space-mvp/business-design.md

### Architecture

arch_docs[8]{topic,document}
Architecture overview,docs/architect/README.md
Agent architecture,docs/architect/pilotspace-agent-architecture.md
Claude SDK integration,docs/architect/claude-agent-sdk-architecture.md
Feature-to-component mapping,docs/architect/feature-story-mapping.md
Backend architecture,docs/architect/backend-architecture.md
Frontend architecture,docs/architect/frontend-architecture.md
RLS security patterns,docs/architect/rls-patterns.md

### Standards & Patterns

pattern_docs[5]{topic,document}
Architecture decisions (88),docs/DESIGN_DECISIONS.md
Dev patterns (start here),docs/dev-pattern/README.md
Pilot Space patterns,docs/dev-pattern/45-pilot-space-patterns.md
MobX patterns,docs/dev-pattern/21c-frontend-mobx-state.md
Feature specs (17 features),docs/PILOT_SPACE_FEATURES.md

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

## AI Agent Instructions

### For All Agents

- Read this file first before implementation work
- Load dev patterns in the order above
- Check `feature-story-mapping.md` for affected components
- Follow quality gates (see [Quality Standards](#quality-standards))
- 700 lines max per code file (py, tsx, etc.). Conventional commits.

### For Backend Agents

**See `backend/CLAUDE.md` for complete backend development guide.**

Key principles:
- CQRS-lite: `Service.execute(Payload) → Result`, not direct DB manipulation
- Repository pattern for all data access
- Verify RLS policies for all multi-tenant queries (scoped by `workspace_id`)
- Async SQLAlchemy only. No blocking I/O.
- AI features respect DD-003 (human-in-the-loop via PermissionHandler)

### For Frontend Agents

**See `frontend/CLAUDE.md` for complete frontend development guide.**

Key principles:
- MobX for UI state (`makeAutoObservable`, `observer()`). Never store API data in MobX.
- TanStack Query for server state (`useQuery`, `useMutation` with optimistic updates)
- shadcn/ui base components, extend with feature variants
- WCAG 2.2 AA: keyboard nav, ARIA labels, focus management
- AI interactions through PilotSpaceStore (unified), not siloed stores

### For AI/Agent Layer Agents

PilotSpaceAgent is the single orchestrator for user-facing conversations. **Exception**: Fast-path independent agents (GhostTextAgent) allowed for latency-critical operations (<2.5s SLA) that require direct provider calls without orchestrator overhead.

**Simple tasks** → skills (`.claude/skills/`)
**Complex tasks** → subagents (spawned by orchestrator)

Key requirements:
- All tools return operation payloads (`status: pending_apply`), not direct mutations
- ContentConverter for TipTap ↔ Markdown with block ID preservation
- SSE: SDK message → `transform_sdk_message()` → Frontend event
- Prompt caching enabled (`cache_control: ephemeral`)
- ResilientExecutor for retries, CircuitBreaker for provider failures

**One-shot query() integration with CQRS-lite**:
```python
# Router layer
@router.post("/enhance")
async def enhance_text(payload: EnhanceTextPayload, service: IssueService):
    result = await service.execute(payload)  # CQRS-lite pattern
    return result

# Service layer
class IssueService:
    async def execute(self, payload: EnhanceTextPayload) -> Result:
        # One-shot query to Claude Sonnet
        enhanced = await sdk.query(
            prompt=f"Enhance this text: {payload.text}",
            provider="claude-sonnet"
        )
        # Return domain entity or value object
        return Result(enhanced_text=enhanced.content)
```

**Conversational multi-turn with orchestrator**:
```python
# SSE streaming endpoint
@router.post("/chat")
async def chat_stream(message: str, session_id: str):
    async def event_generator():
        async for event in pilot_space_agent.invoke(message, session_id):
            yield event  # SSE events: text_delta, tool_use, content_update
    return StreamingResponse(event_generator())
```

### For Testing Agents

- **Backend**: pytest `--cov=.`, async with pytest-asyncio, fixture-based DB sessions
- **Frontend**: Vitest unit, Playwright E2E
- Coverage > 80%
- E2E critical paths: skill invocation, subagent invocation, approval flow, session resumption, error recovery

---

## Core Principles

**Keep solutions simple and focused.** Only make changes directly requested or clearly necessary. Don't add features, refactor code, or make "improvements" beyond what was asked.

**Prefer editing existing files to creating new ones.** Only create new files when adding distinct functionality (new entity, new router, new feature module).

**Read and understand relevant files before proposing changes.** Don't speculate about code you haven't inspected. Review existing style, conventions, and abstractions before implementing.

**Write tests for all new features and bug fixes.** 80% coverage catches 85% of regressions before deployment.

**Respect security boundaries.** RLS violations expose sensitive data across workspaces. Verify RLS policies for all multi-tenant queries.

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

### AI Components

- **MCP Tool**: Python function registered via `create_note_tools_server()`. Exposed to Claude SDK. Returns operation payloads (`status: pending_apply`).
- **Skill**: YAML-defined behavior. May invoke one or more MCP tools. Example: `extract-issues` skill invokes `extract_issues` MCP tool.
- **Operation Payload**: Structured response from MCP tool indicating pending changes. Backend applies transformations before DB commit.

### Approval Categories (DD-003)

- **Non-destructive**: Auto-execute, notify user (labels, annotations, auto-transitions). No approval required.
- **Content creation**: Require approval, configurable (create issues, PR comments). User can enable/disable per operation type.
- **Destructive**: Always require approval (delete issues, merge PRs, archive workspaces). Cannot be disabled.

## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:

1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes

### Claude Agent SDK Documentation

Read index at `docs/claude-sdk.txt` for full documentation.

## Active Technologies

- TypeScript 5.3+ / Next.js 14+ (App Router) + React 18, MobX 6+, TanStack Query 5+, TipTap 3.16+, TailwindCSS 3.4+, shadcn/ui (007-issue-detail-page)
- N/A (frontend-only; backend APIs already exist) (007-issue-detail-page)

## Recent Changes

- 007-issue-detail-page: Added TypeScript 5.3+ / Next.js 14+ (App Router) + React 18, MobX 6+, TanStack Query 5+, TipTap 3.16+, TailwindCSS 3.4+, shadcn/ui


