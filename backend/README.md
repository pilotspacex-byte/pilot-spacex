# Pilot Space Backend

AI-Augmented SDLC Platform with Note-First Workflow - Backend API

**For project overview and general context, see main [CLAUDE.md](../CLAUDE.md) at project root.**

## Quick Start

```bash
# Install dependencies
uv sync

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run development server
uv run uvicorn pilot_space.main:app --reload

# Run tests
uv run pytest

# Run quality checks
uv run ruff check .
uv run pyright
```

## Mock AI Mode (Development)

**Save $5K/month in development costs** by using deterministic AI responses without external API calls.

### Enable Mock Mode

```bash
# In .env
APP_ENV=development
AI_FAKE_MODE=true
AI_FAKE_LATENCY_MS=500  # Simulated response time
AI_FAKE_STREAMING_CHUNK_DELAY_MS=50
```

### Features

- **Zero API costs** - No calls to Claude, OpenAI, or Gemini
- **Deterministic** - Same input = same output (great for testing)
- **Fast development** - No rate limits, instant responses
- **Offline** - Works without internet connection
- **All 10 agents supported**:
  - GhostTextAgent (inline completions)
  - IssueEnhancerAgent (title/description enhancement)
  - MarginAnnotationAgent (contextual annotations)
  - IssueExtractorAgent (extract issues from notes)
  - ConversationAgent (AI chat)
  - AssigneeRecommenderAgent (assignee suggestions)
  - DuplicateDetectorAgent (duplicate issue detection)
  - CommitLinkerAgent (issue reference extraction)
  - AIContextAgent (comprehensive context generation)
  - PRReviewAgent (code review)

### Production

Mock mode is **automatically disabled** in production (`APP_ENV=production`). It only activates when both conditions are met:
- `APP_ENV=development`
- `AI_FAKE_MODE=true`

---

## Quality Gates (Run Before Every Commit)

```bash
uv run pyright && uv run ruff check && uv run pytest --cov=.
```

All three gates must PASS. No exceptions. **80% test coverage requirement.**

### Critical Constants

| Constraint | Value | Rationale |
|------------|-------|-----------|
| File size limit | 700 lines | Maintainability and testability |
| Test coverage | >80% (strictly greater) | Correlates with production stability |
| Async-only I/O | Required | Blocking calls degrade API latency 10-50x |
| Database pool | 5 base + 10 overflow | Prevents connection exhaustion |

### Development Commands

```bash
# Setup
cd backend && uv venv && source .venv/bin/activate && uv sync && pre-commit install

# Dev server
uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000

# Migrations
alembic revision --autogenerate -m "Description" && alembic upgrade head
```

---

## Backend Architecture Overview

### Technology Stack

| Component | Technology | Version | Decision |
|-----------|-----------|---------|----------|
| Framework | FastAPI | 0.110+ | DD-001 (async-first) |
| ORM | SQLAlchemy 2.0 (async) | 2.0+ | DD-001 |
| Validation | Pydantic v2 | 2.6+ | DD-001 |
| DI Container | dependency-injector | 4+ | DD-064 |
| Runtime | Python | 3.12+ | -- |

### 5-Layer Clean Architecture

```
frontend/browser
    | REST + SSE (cookies/Bearer)
Presentation Layer (api/v1/)
|-- 20 FastAPI routers, Pydantic v2 schemas, middleware (auth, CORS, rate limiting, RFC 7807)
    | Service.execute(Payload) -> Result
Application Layer (application/services/)
|-- 8 domain services, CQRS-lite command/query pattern
    | Domain logic, validation, invariants
Domain Layer (domain/)
|-- Rich domain entities (Issue, Note, Cycle), domain events, business rules
    | Data access abstraction
Infrastructure Layer (infrastructure/)
|-- 22 SQLAlchemy models, 15 repositories, RLS enforcement, Redis, Meilisearch
    | Agent orchestration, MCP tools, provider routing
AI Layer (ai/)
|-- PilotSpaceAgent orchestrator, subagents, MCP tools (33), skills (8), provider routing
```

### Root Configuration Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, lifespan (startup/shutdown), router mounting |
| `container.py` | Dependency injection (dependency-injector DSL) |
| `config.py` | Pydantic Settings (environment variables) |
| `dependencies.py` | FastAPI Depends functions (session injection) |

---

## Backend Patterns

### CQRS-lite (DD-064)

Command/Query separation without Event Sourcing. Pattern: `Service.execute(Payload) -> Result`. See [application/README.md](src/pilot_space/application/README.md).

### Repository Pattern

BaseRepository[T] with 14 core methods, 18 specialized repositories, RLS enforcement via workspace_id scoping. See [infrastructure/README.md](src/pilot_space/infrastructure/README.md).

### Dependency Injection (DD-064)

FastAPI + dependency-injector with ContextVar session scoping. Session management via `SessionDep` trigger, service/repository injection via type aliases in `api/v1/dependencies.py`. Container configuration in `container.py`. See [api/README.md](src/pilot_space/api/README.md) for injection patterns.

### Error Handling (RFC 7807)

All API errors return RFC 7807 Problem Details. Status codes: 400, 401, 403, 404, 422, 429, 500. See [api/README.md](src/pilot_space/api/README.md).

---

## Security: Row-Level Security (RLS)

**RLS violations expose sensitive data across workspaces. CRITICAL SECURITY BOUNDARY.**

- RLS enabled on all multi-tenant tables
- Four roles: owner, admin, member, guest
- PostgreSQL session variables: `app.current_user_id`, `app.current_workspace_id`
- Middleware sets RLS context on every request

See [infrastructure/README.md](src/pilot_space/infrastructure/README.md) for full RLS architecture.

---

## API Layer: 20 FastAPI Routers

**Core Resources** (7 routers, 35+ endpoints): workspaces, workspace_members, workspace_invitations, projects, issues, workspace_notes, workspace_cycles

**AI Features** (10 routers, 40+ endpoints): ai_chat, ghost_text, ai_pr_review, ai_extraction, ai_annotations, ai_approvals, ai_costs, ai_configuration, ai_sessions, ai_context

**Support** (3+ routers, 15+ endpoints): auth, integrations, webhooks, homepage, skills, role_skills, mcp_tools, debug

**Middleware Pipeline**: RequestContext -> CORS -> ErrorHandler -> RateLimiter -> Auth -> Router

See [api/README.md](src/pilot_space/api/README.md) for full router documentation.

---

## Application Services (32 Services Across 9 Domains)

| Domain | Services |
|--------|----------|
| Note | Create, Update, Get, CreateFromChat, AIUpdate |
| Issue | Create, Update, List, Get, Activity |
| Cycle | Create, Update, Get, AddToIssue, Rollover |
| AI | GenerateAIContext, RefineAIContext, ExportAIContext |
| Integration | GitHub OAuth, Webhook, Commit linking, Auto-transition |
| Onboarding | CreateGuidedNote, GetProgress, UpdateProgress |
| RoleSkill | CRUD + Generate |
| Homepage | Activity, Digest, DismissSuggestion |
| Workspace | InviteMember |

All follow CQRS-lite: `Service.execute(Payload) -> Result`. See [application/README.md](src/pilot_space/application/README.md).

---

## AI Layer Architecture

See [ai/README.md](src/pilot_space/ai/README.md) for complete documentation.

**PilotSpaceAgent** (DD-086): Centralized orchestrator routing to skills/subagents (Sonnet default)

**Subagents** (3): PRReviewAgent (Opus), AIContextAgent (Sonnet), DocGeneratorAgent (Sonnet)

**Skills** (8): extract-issues, enhance-issue, improve-writing, summarize, find-duplicates, recommend-assignee, decompose-tasks, generate-diagram

**MCP Tools** (33 across 6 servers): note, note_content, issue, issue_relation, project, comment

**Provider Routing** (DD-011): Task-based selection + per-task fallback chains

**Resilience**: ResilientExecutor + CircuitBreaker (3 failures -> OPEN, 30s recovery)

---

## Submodule Documentation

| Module | Doc | Covers |
|--------|-----|--------|
| AI Layer | [`ai/README.md`](src/pilot_space/ai/README.md) | Agents, MCP tools, providers, sessions |
| API Layer | [`api/README.md`](src/pilot_space/api/README.md) | Routers, schemas, middleware, DI |
| Application | [`application/README.md`](src/pilot_space/application/README.md) | Services, CQRS-lite, payloads |
| Domain | [`domain/README.md`](src/pilot_space/domain/README.md) | Entities, business rules, events |
| Infrastructure | [`infrastructure/README.md`](src/pilot_space/infrastructure/README.md) | Repositories, models, RLS, Redis |
| Integrations | [`integrations/README.md`](src/pilot_space/integrations/README.md) | GitHub, Slack |

---

## Testing

**Command**: `pytest --cov=. --cov-report=html`

**Target**: >80% coverage. Test organization: `unit/services/`, `unit/repositories/`, `unit/domain/`, `integration/`, `e2e/`

---

## Pre-Submission Checklist

**Architecture & Design**:
- [ ] CQRS-lite pattern followed (Service.execute() -> Result)
- [ ] Repository pattern used (no direct DB access in services)
- [ ] Domain logic in entities, not services
- [ ] All exceptions converted to RFC 7807

**Security**:
- [ ] RLS policy added/verified for multi-tenant tables
- [ ] Workspace membership validated before mutations
- [ ] No sensitive data in logs
- [ ] API keys stored in Supabase Vault

**Code Quality**:
- [ ] Tests cover happy path + 2 edge cases
- [ ] Coverage >80%
- [ ] No blocking I/O in async functions
- [ ] File stays under 700 lines
- [ ] No N+1 queries (eager loading used)
- [ ] No TODOs, mocks, or placeholders

**Database**:
- [ ] Migrations created for schema changes
- [ ] Soft deletes used (is_deleted column)
- [ ] Indexes added for query performance

**AI Integration** (if applicable):
- [ ] Tool returns operation payload (not direct mutation)
- [ ] ResilientExecutor used for external API calls
- [ ] Human-in-the-loop approval for destructive actions
- [ ] Cost tracking enabled

---

## Common Patterns Reference

### Load Order for New Backend Features

1. `docs/architect/feature-story-mapping.md` -> Find US-XX and affected components
2. `docs/dev-pattern/45-pilot-space-patterns.md` -> Project overrides
3. Domain-specific: `07-repository.md`, `08-service-layer.md`, `20-validation.md`
4. Cross-cutting: `26-di.md`, `06-error-handling.md`, `25-async.md`

### Key Documentation Links

| Topic | Document |
|-------|----------|
| Architecture overview | `docs/architect/backend-architecture.md` |
| RLS security patterns | `docs/architect/rls-patterns.md` |
| Design decisions (88 total) | `docs/DESIGN_DECISIONS.md` |
| Feature-to-component mapping | `docs/architect/feature-story-mapping.md` |
| PilotSpaceAgent architecture | `docs/architect/pilotspace-agent-architecture.md` |

---

## Standards Summary

**Don't use**: Placeholders/TODOs, mocks in production, blocking I/O in async, direct model manipulation in API layer, global state, hard-coded IDs

**Always use**: Service classes with payloads/results, repository pattern, RFC 7807 errors, async SQLAlchemy with RLS, dependency injection, conventional commits, eager loading, type hints (pyright strict), unit tests (>80%)

## License

MIT
