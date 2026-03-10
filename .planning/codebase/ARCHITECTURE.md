# Architecture

**Analysis Date:** 2026-03-07

## Pattern Overview

**Overall:** Monorepo with two independent applications: a Python FastAPI backend (Clean Architecture, 5-layer) and a Next.js frontend (Feature-Folder with dual state managers). An optional Python CLI and a self-hosted Supabase authcore service complete the stack.

**Key Characteristics:**
- Backend enforces strict layer separation: API → Application → Domain → Infrastructure, with a DI container wiring all dependencies
- Frontend separates UI state (MobX) from server cache (TanStack Query) — these must never be mixed
- All multi-tenant data isolation enforced at the database layer via PostgreSQL RLS policies set per-request
- AI layer is an autonomous subsystem: `PilotSpaceAgent` orchestrator with subagents, skills (single-turn, stateless), and MCP tool servers
- Background workers (digest, memory, notification) run as asyncio tasks inside the FastAPI process, consuming a Supabase/pgmq queue

---

## Backend Layers

**API Layer:**
- Purpose: HTTP entry points — validation, auth extraction, response serialization
- Location: `backend/src/pilot_space/api/`
- Contains: Routers (`api/v1/routers/`), Pydantic schemas (`api/v1/schemas/`), middleware, dependency functions (`api/v1/dependencies.py`, `api/v1/dependencies_pilot.py`)
- Depends on: Application layer (via injected services)
- Used by: External HTTP clients (frontend, CLI, webhooks)
- Note: Every router function that uses DI-provided services MUST declare `session: SessionDep` to populate the ContextVar before resolution

**Application Layer:**
- Purpose: Use-case orchestration — business rules, transaction boundaries, event enqueuing
- Location: `backend/src/pilot_space/application/services/`
- Contains: One service class per use case, organized by domain subdirectory (e.g., `services/issue/`, `services/note/`, `services/cycle/`)
- Depends on: Repository interfaces (infrastructure), queue client
- Used by: API routers via DI container

**Domain Layer:**
- Purpose: Value objects, domain events, pure business rules (minimal, mostly thin)
- Location: `backend/src/pilot_space/domain/`
- Contains: `domain/models/` (Python dataclasses, not SQLAlchemy), `domain/events/`, `domain/services/`
- Depends on: Nothing (pure Python)
- Used by: Application services

**Infrastructure Layer:**
- Purpose: External system adapters — database, cache, queue, auth, storage
- Location: `backend/src/pilot_space/infrastructure/`
- Contains:
  - `infrastructure/database/models/` — SQLAlchemy ORM models (35+ tables)
  - `infrastructure/database/repositories/` — Concrete repository implementations (30+ repos)
  - `infrastructure/database/base.py` — `BaseModel`, `WorkspaceScopedModel`, `TimestampMixin`, `SoftDeleteMixin`
  - `infrastructure/database/rls.py` — `set_rls_context()` sets `app.current_user_id` session variable for RLS
  - `infrastructure/queue/` — Supabase/pgmq queue client and message handlers
  - `infrastructure/cache/` — Redis client
  - `infrastructure/auth/` — Supabase JWT verification
  - `infrastructure/storage/` — File storage (Supabase Storage)
- Depends on: External services (PostgreSQL, Redis, Supabase)

**DI Container Layer:**
- Purpose: Wires all layers together; provides singleton and factory scopes
- Location: `backend/src/pilot_space/container/`
- Contains: `container.py` (main `Container` class inheriting `InfraContainer`), `_base.py` (infrastructure providers), `_factories.py` (complex factory functions)
- Key pattern: Services declared as `providers.Factory`, singletons (`PilotSpaceAgent`, `SkillConcurrencyManager`) as `providers.Singleton`
- Wired modules (only these can use `@inject`): `pilot_space.dependencies`, `pilot_space.api.v1.dependencies`, `pilot_space.api.v1.dependencies_pilot`, `pilot_space.api.v1.repository_deps`, `pilot_space.api.v1.intent_deps`

**AI Subsystem:**
- Purpose: All generative AI features — chat, ghost text, issue enhancement, PR review, knowledge graph
- Location: `backend/src/pilot_space/ai/`
- Contains:
  - `ai/agents/pilotspace_agent.py` — Single orchestrator, all user-facing AI routes through here
  - `ai/agents/subagents/` — Multi-turn stateful subagents (PR review, AI context, doc generator)
  - `ai/skills/skill_executor.py` — Single-turn, stateless skill handler
  - `ai/mcp/` — 33 MCP tool servers (6 categories)
  - `ai/providers/provider_selector.py` — Task-based model selection (Opus/Sonnet/Flash), 20 task types
  - `ai/infrastructure/resilience.py` — Exponential backoff (1-60s, 3 retries) + circuit breaker (3 failures → OPEN, 30s recovery)
  - `ai/infrastructure/cost_tracker.py` — Per-request token + cost logging
  - `ai/session/session_manager.py` — Redis hot cache (30min TTL) + PostgreSQL durable (24h TTL)
  - `ai/workers/` — `DigestWorker`, `MemoryWorker`, `NotificationWorker` (asyncio tasks)
  - `ai/templates/skills/` — YAML skill definitions (auto-discovered from `.claude/skills/`)

---

## Frontend Layers

**Next.js App Router (Pages):**
- Purpose: Route definitions, server-side data bootstrapping, layout composition
- Location: `frontend/src/app/`
- Contains: Route groups `(auth)/` and `(workspace)/[workspaceSlug]/`, nested dynamic routes
- Pattern: Workspace routes require `[workspaceSlug]` path segment; issue detail routes include `[issueId]`

**Feature Modules:**
- Purpose: Self-contained vertical slices — each feature owns components, hooks, stores, editor extensions
- Location: `frontend/src/features/`
- Contains: `ai/`, `cycles/`, `github/`, `homepage/`, `integrations/`, `issues/`, `members/`, `notes/`, `onboarding/`, `settings/`
- Pattern: Each feature exposes public API via `index.ts` barrel: `import { useNotes } from '@/features/notes'`

**Shared Components:**
- Purpose: Cross-feature UI primitives and layout shells
- Location: `frontend/src/components/`
- Contains: `ui/` (shadcn/ui primitives), `layout/`, `navigation/`, `editor/` (TipTap base), `issues/`, `search/`, `ai/chat/`

**State (MobX):**
- Purpose: UI state management — panels open/closed, optimistic IDs, local selections
- Location: `frontend/src/stores/`
- Contains: `RootStore.ts` (aggregator), `AuthStore.ts`, `WorkspaceStore.ts`, `UIStore.ts`, `NotificationStore.ts`, `OnboardingStore.ts`, `RoleSkillStore.ts`, `TaskStore.ts`, and feature stores under `stores/features/` (`IssueStore`, `NoteStore`, `CycleStore`) and `stores/ai/` (AIStore with 11 sub-stores)
- Rule: Never store API response data in MobX — that belongs in TanStack Query

**Server Cache (TanStack Query):**
- Purpose: Server state — fetched data, mutations with optimistic updates and rollback
- Location: Hooks inside feature modules (e.g., `features/issues/hooks/`, `features/notes/hooks/`)
- Pattern: Snapshot + rollback on `onMutate` / `onError` / `onSettled`

**API Services:**
- Purpose: Typed wrappers around `apiClient` (axios singleton)
- Location: `frontend/src/services/api/`
- Contains: One file per API domain (`issues.ts`, `notes.ts`, `workspaces.ts`, etc.)
- Auth: `apiClient` automatically injects `Authorization: Bearer <token>` and `X-Workspace-Id` headers on every request

---

## Data Flow

**Backend HTTP Request:**

1. HTTP request arrives at FastAPI (middleware: `RequestContextMiddleware` → CORS → auth)
2. Router dependency `get_current_user_id` validates JWT, `SessionDep` opens async DB session and stores in ContextVar
3. DI container resolves `Application Service` via `@inject` + `Provide[Container.x]`
4. Application service calls `set_rls_context(session, user_id, workspace_id)` before repository access
5. Repository executes SQLAlchemy async query (RLS policy filters rows by session variable)
6. Service returns domain data; router serializes to Pydantic schema
7. Response: `Content-Type: application/problem+json` on errors (RFC 7807), `application/json` on success

**AI Chat (SSE Stream):**

1. Frontend `POST /api/v1/ai/chat` with `ChatRequest`
2. `ai_chat.py` router injects `PilotSpaceAgent` singleton
3. Agent retrieves per-workspace BYOK API key from Vault
4. Agent assembles system prompt (prompt layers + role skill templates)
5. `ClaudeSDKClient` processes: skill match → `SkillExecutor`; subagent → spawn; tool call → MCP handler
6. MCP tool handler returns `{"status": "pending_apply", ...}` payload
7. `transform_sdk_message()` converts to SSE events (`text_delta`, `content_update`, `approval_request`, `task_progress`)
8. Frontend `useContentUpdates()` hook processes SSE → TipTap mutation or API call

**Frontend User Action:**

1. User interacts with `observer()` component
2. MobX store action updates UI state synchronously
3. TanStack Query mutation calls API service (`issuesApi.create(...)`)
4. On `onMutate`: cancel queries → snapshot → apply optimistic update to cache
5. On `onError`: rollback to snapshot
6. On `onSettled`: invalidate query keys → triggers background refetch

**Background Queue Workers:**

1. Service enqueues message via `SupabaseQueueClient.enqueue(QueueName.AI_LOW, payload)`
2. Worker polls queue (`DigestWorker`, `MemoryWorker`, `NotificationWorker`) in asyncio loop
3. Handler processes message (e.g., KG population, embedding generation, notification persistence)
4. Dead-letter queue (`QueueName.DEAD_LETTER`) receives failed messages after retries

---

## Key Abstractions

**BaseRepository:**
- Purpose: Generic CRUD, soft-delete, cursor pagination, text search
- Location: `backend/src/pilot_space/infrastructure/database/repositories/base.py`
- Pattern: `class IssueRepository(BaseRepository[Issue])` — concrete repos extend with domain-specific queries
- Soft delete: `is_deleted=True`, `deleted_at=now()` — `get_by_id()` excludes deleted by default

**WorkspaceScopedModel:**
- Purpose: Ensures all multi-tenant entities carry `workspace_id` FK enforced by RLS
- Location: `backend/src/pilot_space/infrastructure/database/base.py`
- Pattern: `class Issue(WorkspaceScopedModel)` — automatic `workspace_id` column + RLS hook

**BaseRepository Pagination:**
- Pattern: Cursor-based, not offset — cursor is ISO-encoded sort field value
- `CursorPage[T]` returned with `next_cursor`, `prev_cursor`, `has_next`, `has_prev`

**PilotSpaceAgent:**
- Purpose: Single orchestrator — all user AI chat, skill execution, subagent delegation
- Location: `backend/src/pilot_space/ai/agents/pilotspace_agent.py`
- Pattern: Singleton in DI container; `GhostTextAgent` is the only agent that bypasses it (latency requirement <2s)

**RootStore:**
- Purpose: Single aggregator for all MobX stores, passed via React context
- Location: `frontend/src/stores/RootStore.ts`
- Pattern: `const { issueStore, noteStore } = useStore()` — domain stores accessed via typed hooks
- `rootStore` is a singleton module-level instance; `StoreContext.Provider` wraps the full app in `Providers`

**Approval Workflow (DD-003):**
- Purpose: Human-in-the-loop gate for destructive AI actions
- Location: `backend/src/pilot_space/ai/sdk/permission_handler.py`
- Pattern: Non-destructive → auto-approve; content creation → configurable; destructive → always require human approval via `approval_request` SSE event

---

## Entry Points

**Backend:**
- Location: `backend/src/pilot_space/main.py`
- Triggers: `uvicorn pilot_space.main:app --reload --port 8000`
- Responsibilities: Constructs FastAPI app, registers all 60+ routers under `/api/v1`, starts asyncio workers (digest, memory, notification), connects Redis, validates JWT config on startup

**Frontend:**
- Location: `frontend/src/app/layout.tsx`
- Triggers: Next.js App Router root layout
- Responsibilities: Wraps app in `<Providers>` (QueryClient + StoreContext + ThemeProvider + TooltipProvider + Toaster)

**Frontend Providers:**
- Location: `frontend/src/components/providers.tsx`
- Responsibilities: `QueryClientProvider` (TanStack Query), `StoreContext.Provider` (MobX `rootStore`), `ThemeProvider`, `TooltipProvider`, `Toaster`

**CLI:**
- Location: `cli/` (pyproject.toml entry point)
- Commands: `pilot login`, `pilot implement <issue-id>` (interactive or `--oneshot` for CI)

---

## Error Handling

**Backend Strategy:** RFC 7807 Problem Details (`Content-Type: application/problem+json`)

**Patterns:**
- All `HTTPException` and `RequestValidationError` converted to `ProblemDetail` via `register_exception_handlers(app)` in `backend/src/pilot_space/api/middleware/error_handler.py`
- AI layer: exponential backoff (3 retries, 1–60s) + circuit breaker (3 failures, 30s reset) via `ResilientExecutor`
- Repositories: return `None` on not-found (caller raises 404); `IntegrityError` surfaces as 409

**Frontend Strategy:** `ApiError` class (extends `Error`) wraps all backend errors

**Patterns:**
- `ApiError.fromAxiosError()` in `frontend/src/services/api/client.ts` handles RFC 7807 and legacy `{detail}` formats
- 401: auto-retry with refreshed token → logout + redirect `/login?error=session_expired` on failure
- 429: toast with `retry-after` header value
- 500+: generic server error toast

---

## Cross-Cutting Concerns

**Logging:** `structlog` on backend (`infrastructure/logging.py`); `configure_structlog(settings)` called at startup. Key: `logger.info("event_name", key=value)` structured event pattern.

**Validation:** Pydantic v2 at API boundaries (schemas in `api/v1/schemas/`); SQLAlchemy types enforce DB constraints.

**Authentication:** Supabase JWT (`Bearer` token) validated per-request via `get_current_user_id` dependency; workspace membership checked via `get_current_workspace_id` dependency; RLS enforced at DB level with `set_rls_context()`.

**Multi-tenancy:** Every query to workspace-scoped tables requires `set_rls_context(session, user_id, workspace_id)` before execution. RLS policies use UPPERCASE enum values (`'OWNER'`, `'ADMIN'`, `'MEMBER'`, `'GUEST'`).

**Soft Deletes:** Default for all entities via `SoftDeleteMixin`. `BaseRepository.delete(entity, hard=False)` sets `is_deleted=True`. Restored within 30 days (FR-063).

---

*Architecture analysis: 2026-03-07*
