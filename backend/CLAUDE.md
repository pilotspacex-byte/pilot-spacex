# Backend Development Guide - Pilot Space

**For project overview and general context, see main CLAUDE.md at project root.**

## Quick Reference

### Quality Gates (Run Before Every Commit)

```bash
uv run pyright && uv run ruff check && uv run pytest --cov=.
```

All three gates must PASS. No exceptions. **80% test coverage requirement** catches 85% of regressions before deployment.

### Critical Constants

| Constraint | Value | Rationale |
|------------|-------|-----------|
| File size limit | 700 lines | Files >700 lines become unmaintainable and untestable |
| Test coverage | >80% (strictly greater) | Metric directly correlates with production stability |
| Async-only I/O | Required | Blocking calls cause thread starvation, degrades API latency 10-50x |
| Database pool | 5 base + 10 overflow | Prevents connection exhaustion under load |

### Development Commands

**Setup**: `cd backend && uv venv && source .venv/bin/activate && uv sync && pre-commit install`

**Dev server**: `uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000`

**Quality gates**: `uv run pyright && uv run ruff check && uv run pytest --cov=.`

**Migrations**: `alembic revision --autogenerate -m "Description"` then `alembic upgrade head`

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

Organized by concern with clear separation of responsibilities:

```
frontend/browser
    ↓ REST + SSE (cookies/Bearer)
Presentation Layer (api/v1/)
├─ 20 FastAPI routers
├─ Pydantic v2 request/response schemas
├─ Middleware: auth, CORS, rate limiting, RFC 7807 errors
└─ WebSocket handler for real-time updates
    ↓ Service.execute(Payload) → Result
Application Layer (application/services/)
├─ 8 domain services (note, issue, cycle, ai_context, annotation, discussion, integration)
├─ CQRS-lite command/query pattern
├─ Payload validation at boundary
└─ State transition management
    ↓ Domain logic, validation, invariants
Domain Layer (domain/)
├─ Rich domain entities (Issue, Note, Cycle, User)
├─ Domain services (pure logic, no I/O)
├─ Domain events (IssueCreated, IssueStateChanged, etc.)
└─ Business rule validation
    ↓ Data access abstraction
Infrastructure Layer (infrastructure/)
├─ 22 SQLAlchemy models + 21 Alembic migrations
├─ 15 repositories (abstract persistence)
├─ RLS enforcement (workspace_id scoping)
├─ External clients: Redis, Meilisearch, Supabase
└─ Encryption, caching, queuing
    ↓ Agent orchestration, MCP tools, provider routing
AI Layer (ai/)
├─ PilotSpaceAgent (centralized orchestrator)
├─ Subagents (PR review, AI context, doc generation)
├─ Skill system (.claude/skills/ auto-discovery)
├─ MCP tools registry (33 tools across 6 servers)
├─ Provider routing (Claude Opus/Sonnet, Gemini Flash)
├─ Session management (Redis hot + PostgreSQL durable)
└─ Cost tracking, resilience, approval workflows
```

### Root Configuration Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, lifespan (startup/shutdown), router mounting |
| `container.py` | Dependency injection (dependency-injector DSL) |
| `config.py` | Pydantic Settings (environment variables) |
| `dependencies.py` | FastAPI Depends functions (session injection) |

---

## Backend Patterns (Reference: docs/dev-pattern/45-pilot-space-patterns.md)

### CQRS-lite Pattern (DD-064)

**Command/Query separation without Event Sourcing.**

Pattern: `Service.execute(Payload) → Result`

**Complete implementation details, examples, and best practices**: See [application/CLAUDE.md](src/pilot_space/application/CLAUDE.md) - Section "CQRS-lite Pattern Implementation"

### Repository Pattern

**Data access abstraction. All database queries flow through repositories.**

**Complete repository implementation, patterns, and RLS enforcement**: See [infrastructure/CLAUDE.md](src/pilot_space/infrastructure/CLAUDE.md) - Section "Repository Pattern"

**Quick Summary**:
- BaseRepository[T] with 14 core methods (CRUD + pagination)
- 18 specialized repositories (Issue, Note, Cycle, AI, etc.)
- RLS enforcement via workspace_id scoping
- Eager loading to prevent N+1 queries
- Soft delete by default

### Domain Events

**Publish events after successful persist to notify listeners of state changes.**

**Complete domain event architecture and patterns**: See [domain/CLAUDE.md](src/pilot_space/domain/CLAUDE.md) - Section "Domain Events Architecture"

**Note**: Domain events infrastructure is planned but not yet fully implemented (classes designed).

### Dependency Injection (DD-064)

**All dependencies explicitly declared and injected. No global state.**

**Complete DI container setup and injection patterns**: See [api/CLAUDE.md](src/pilot_space/api/CLAUDE.md) - Section "Dependency Injection Pattern"

**Quick Summary**:
- dependency-injector DSL for container definition
- FastAPI Depends() for request-scoped injection
- Singletons: config, engine, session_factory
- Factories: repositories, services (new instance per request)

### Error Handling (RFC 7807)

**All API errors return RFC 7807 Problem Details.**

**Complete error handling middleware and patterns**: See [api/CLAUDE.md](src/pilot_space/api/CLAUDE.md) - Section "Error Handling"

**Quick Summary**:
- Middleware converts exceptions to RFC 7807 format
- HTTP status codes: 400, 401, 403, 404, 422, 429, 500
- Pydantic validation errors with detailed field info
- Automatic instance URL tracking

---

## Security: Row-Level Security (RLS)

**RLS violations expose sensitive data across workspaces.** Database-level enforcement prevents application-layer bypass. **CRITICAL SECURITY BOUNDARY.**

**Complete RLS implementation, policy examples, and enforcement patterns**: See [infrastructure/CLAUDE.md](src/pilot_space/infrastructure/CLAUDE.md) - Section "RLS (Row-Level Security)"

**Quick Summary**:
- RLS enabled on all multi-tenant tables
- Four roles: owner, admin, member, guest
- PostgreSQL session variables: `app.current_user_id`, `app.current_workspace_id`
- Middleware sets RLS context on every request
- Verification checklist for new features
- Common pitfalls with ❌/✅ examples

---

## Database & ORM

### SQLAlchemy 2.0 Async

**CRITICAL**: All I/O must be async. No blocking calls in async functions (use `loop.run_in_executor()` for file I/O).

**CRITICAL**: Always eager load relationships with `.options(joinedload(...))` to prevent N+1 queries.

**See [infrastructure/CLAUDE.md](src/pilot_space/infrastructure/CLAUDE.md) - "SQLAlchemy Async Patterns" and "N+1 Query Prevention"** for complete examples and best practices.

### Models & Repositories

**22 SQLAlchemy models**: Core (User, Workspace, WorkspaceMember), Issues (Issue, State, IssueLabel, IssueLink, Module), Notes (Note, NoteAnnotation, NoteIssueLink), Cycles, AI entities (AIContext, AISession, AIMessage, etc.), and support models.

**15 repositories** providing RLS-enforced data access. See [infrastructure/CLAUDE.md](src/pilot_space/infrastructure/CLAUDE.md) - "Repository Pattern" for full architecture.

### Migrations (Alembic)

```bash
# Create new migration
alembic revision --autogenerate -m "Add issue_priority column"

# Apply pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Check migration status
alembic current
```

---

## API Layer: 20 FastAPI Routers

**Complete router documentation, middleware pipeline, and endpoint patterns**: See [api/CLAUDE.md](src/pilot_space/api/CLAUDE.md)

### Router Organization (Quick Reference)

**Core Resources** (7 routers, 35+ endpoints): workspaces, workspace_members, workspace_invitations, projects, issues, workspace_notes, workspace_cycles

**AI Features** (10 routers, 40+ endpoints): ai_chat (PilotSpaceAgent), ghost_text, ai_pr_review, ai_extraction, ai_annotations, ai_approvals, ai_costs, ai_configuration, ai_sessions, ai_context, notes_ai, workspace_notes_ai

**Support** (3+ routers, 15+ endpoints): auth, integrations, webhooks, homepage, skills, role_skills, mcp_tools, debug

**Middleware Pipeline**: RequestContext → CORS → ErrorHandler → RateLimiter → Auth → Router

---

## Application Services (32 Services Across 9 Domains)

**Complete service documentation, CQRS-lite patterns, and implementation examples**: See [application/CLAUDE.md](src/pilot_space/application/CLAUDE.md)

### Service Categories (Quick Reference)

**Note Services** (5): Create, Update, Get, CreateFromChat, AIUpdate
**Issue Services** (5): Create, Update, List, Get, Activity
**Cycle Services** (5): Create, Update, Get, AddToIssue, Rollover
**AI Services** (3): GenerateAIContext, RefineAIContext, ExportAIContext
**Annotation Services** (1): Create with confidence scoring
**Discussion Services** (1): Create with atomic first comment
**Integration Services** (4): GitHub OAuth, Webhook, Commit linking, Auto-transition
**Onboarding Services** (3): CreateGuidedNote, GetProgress, UpdateProgress
**RoleSkill Services** (4): CRUD + Generate
**Homepage Services** (3): Activity, Digest, DismissSuggestion
**Workspace Services** (1): InviteMember

All services follow CQRS-lite pattern: `Service.execute(Payload) → Result`

---

## AI Layer Architecture

**Complete AI layer documentation with all components**: See [ai/CLAUDE.md](src/pilot_space/ai/CLAUDE.md)

### Quick Reference

**PilotSpaceAgent Orchestrator** (DD-086): Centralized routing to skills/subagents with Claude Sonnet

**Subagents** (3): PRReviewAgent (Opus, <5min), AIContextAgent (Sonnet, <30s), DocGeneratorAgent (Sonnet, <60s)

**Skills System** (DD-087): Filesystem-based auto-discovery from `.claude/skills/` (8 skills: extract-issues, enhance-issue, improve-writing, summarize, find-duplicates, recommend-assignee, decompose-tasks, generate-diagram)

**MCP Tools** (33 total across 6 servers): note, note_content, issue, issue_relation, project, comment

**Provider Routing** (DD-011): Task-based selection (PR review→Opus, context→Sonnet, ghost text→Flash) + fallback chain

**Resilience**: ResilientExecutor + CircuitBreaker per provider (5 failures → OPEN, 60s recovery)

**Cost Tracking**: Per-request token logging with provider-specific pricing and budget alerts at 90%

**Approval Workflow** (DD-003): Non-destructive→auto, content creation→configurable, destructive→always require

---

## Testing

### Test Coverage Requirement: >80%

**Command**: `pytest --cov=. --cov-report=html`

**Target**: 85%+ is ideal. <80% means untested code paths → regressions in production.

**Test organization** by concern: `unit/services/`, `unit/repositories/`, `unit/domain/`, `integration/`, `e2e/`

**See `docs/dev-pattern/` for test pattern examples:** Unit test structure, fixtures, mocking, integration test patterns for RLS verification.

---

## Pre-Submission Checklist

**Rate confidence (0-1) before submitting code.**

**Architecture & Design**:
- [ ] CQRS-lite pattern followed (Service.execute() → Result): ___
- [ ] Repository pattern used (no direct DB access in services): ___
- [ ] Domain logic in entities, not services: ___
- [ ] All exceptions converted to RFC 7807: ___

**Security**:
- [ ] RLS policy added/verified for multi-tenant tables: ___
- [ ] Workspace membership validated before mutations: ___
- [ ] No sensitive data in logs: ___
- [ ] API keys stored in Supabase Vault, never hardcoded: ___

**Code Quality**:
- [ ] Tests cover happy path + 2 edge cases: ___
- [ ] Coverage >80% (run `pytest --cov=.`): ___
- [ ] No blocking I/O in async functions: ___
- [ ] File stays under 700 lines: ___
- [ ] No N+1 queries (eager loading used): ___
- [ ] No TODOs, mocks, or placeholders: ___

**Database**:
- [ ] Migrations created for schema changes: ___
- [ ] Soft deletes used (is_deleted column): ___
- [ ] Indexes added for query performance: ___
- [ ] No hardcoded IDs in queries: ___

**AI Integration** (if applicable):
- [ ] Tool returns operation payload (not direct mutation): ___
- [ ] Prompt caching enabled (`cache_control: ephemeral`): ___
- [ ] ResilientExecutor used for external API calls: ___
- [ ] Human-in-the-loop approval for destructive actions: ___
- [ ] Cost tracking enabled: ___

**Documentation**:
- [ ] Docstrings on all public functions: ___
- [ ] Type hints on all parameters and returns: ___
- [ ] Complex logic has inline comments: ___

**If any score <0.9, address gaps before completion.**

---

## Common Patterns Reference

### Load Order for New Backend Features

1. `docs/architect/feature-story-mapping.md` → Find US-XX and affected components
2. `docs/dev-pattern/45-pilot-space-patterns.md` → Project overrides (CQRS-lite, RLS, etc.)
3. Domain-specific patterns:
   - `07-repository.md` (data access)
   - `08-service-layer.md` (business logic)
   - `20-validation.md` (request validation)
4. Cross-cutting patterns:
   - `26-di.md` (dependency injection)
   - `06-error-handling.md` (RFC 7807)
   - `25-async.md` (async best practices)

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

**Don't use**:
- Placeholders, TODOs, or pseudo-code
- Mocks or stubs in production code
- Blocking I/O in async functions (except in executor)
- Direct SQLAlchemy model manipulation in API layer
- Global state or singletons (except config via DI)
- Hard-coded IDs or magic numbers

**Always use**:
- Service classes with explicit payloads and results
- Repository pattern for all data access
- RFC 7807 Problem Details for all errors
- Async SQLAlchemy with RLS enforcement
- Dependency injection for all dependencies
- Conventional commits: feat/fix/refactor(scope): description
- Eager loading for relationships (`.options(joinedload(...))`)
- Type hints (pyright strict mode)
- Unit tests (>80% coverage)

---

## Generation Metadata

**Documentation Generated**: 2026-02-10

**Scope**: Complete backend codebase analysis
- 20 FastAPI routers (Core + AI + Support)
- 8 application services
- 22 SQLAlchemy models
- 15 repositories
- 33 MCP tools across 6 servers
- PilotSpaceAgent orchestrator + 3 subagents
- Skill system + provider routing + cost tracking

**Patterns Detected**:
- CQRS-lite (Service.execute(Payload) → Result)
- Repository pattern (BaseRepository[T] with RLS)
- Domain events (IssueCreated, IssueStateChanged, etc.)
- Dependency injection (dependency-injector)
- RFC 7807 error handling
- RLS enforcement (workspace_id scoping)
- Async SQLAlchemy (no blocking I/O)
- SSE streaming (ChatView, ghost text, AI context)
- Circuit breaker + exponential backoff (resilience)
- Prompt caching (ephemeral for cost savings)

**Coverage Gaps**:
- Phase 2 features not yet implemented: PR review streaming, Slack integration, bulk operations
- Health check endpoint minimal (could add DB/Redis/Meilisearch connectivity checks)
- Webhook signature verification (GitHub) implemented but not fully tested
- Missing API rate limit enforcement tests

**Suggested Next Steps**:
1. Add database health checks to `/ready` endpoint
2. Implement E2E tests for full RLS isolation workflows
3. Create performance benchmarks for large issue queries (N+1 prevention)
4. Document MCP tool error handling and validation
5. Add cost tracking integration tests
