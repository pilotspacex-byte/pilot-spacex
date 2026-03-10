# Codebase Structure

**Analysis Date:** 2026-03-07

## Directory Layout

```
pilot-space/                          # Monorepo root
├── backend/                          # Python FastAPI backend
│   ├── alembic/                      # Database migrations
│   │   └── versions/                 # Migration files (immutable once committed)
│   ├── src/pilot_space/              # Main application package
│   │   ├── main.py                   # FastAPI app entry point, router registration, worker startup
│   │   ├── config.py                 # Settings (Pydantic, lru_cache)
│   │   ├── ai/                       # AI subsystem (agents, skills, providers, MCP tools, workers)
│   │   ├── api/                      # HTTP layer (routers, schemas, middleware)
│   │   ├── application/              # Use-case services (one service per use case)
│   │   ├── container/                # Dependency injection container (dependency-injector)
│   │   ├── dependencies/             # FastAPI dependency functions (auth, session, workspace)
│   │   ├── domain/                   # Domain models, events, pure business logic
│   │   ├── infrastructure/           # External adapters (DB, cache, queue, auth, storage)
│   │   ├── integrations/             # GitHub, Slack integration adapters
│   │   ├── schemas/                  # Shared Pydantic schemas (cross-feature)
│   │   └── spaces/                   # SpaceManager — filesystem workspace abstraction for AI
│   ├── tests/                        # Test suite
│   │   ├── conftest.py               # Fixtures (SQLite in-memory by default)
│   │   ├── cli/                      # CLI tests
│   │   ├── unit/                     # Unit tests (service/repository layer)
│   │   └── integration/              # Integration tests (require TEST_DATABASE_URL=postgres)
│   ├── docs/                         # Backend-specific architecture docs
│   ├── pyproject.toml                # uv/pip config, ruff, pyright, pytest settings
│   └── alembic.ini                   # Alembic migration config
├── frontend/                         # Next.js frontend
│   ├── src/
│   │   ├── app/                      # Next.js App Router pages and layouts
│   │   │   ├── layout.tsx            # Root layout (fonts, Providers wrapper)
│   │   │   ├── (auth)/               # Auth route group (login, callback, reset-password)
│   │   │   ├── (workspace)/          # Workspace route group (requires workspaceSlug)
│   │   │   │   └── [workspaceSlug]/  # Dynamic workspace segment
│   │   │   │       ├── issues/       # Issues list + [issueId]/ detail
│   │   │   │       ├── notes/        # Notes list + [noteId]/ editor
│   │   │   │       ├── projects/     # Projects + [projectId]/ with sub-routes
│   │   │   │       ├── chat/         # AI chat interface
│   │   │   │       ├── cycles/       # Cycle management
│   │   │   │       ├── members/      # Members + [userId]/ profile
│   │   │   │       └── settings/     # Settings sub-routes (ai-providers, billing, etc.)
│   │   │   ├── api/health/           # Next.js API route for health check
│   │   │   └── welcome/              # Welcome/onboarding landing
│   │   ├── features/                 # Feature-folder modules (vertical slices)
│   │   │   ├── ai/                   # Conversational AI (ChatView, SSE, approvals)
│   │   │   ├── cycles/               # Sprint/cycle management
│   │   │   ├── github/               # GitHub OAuth + PR links
│   │   │   ├── homepage/             # Note-First homepage, activity feed, digest
│   │   │   ├── integrations/         # External integration hooks
│   │   │   ├── issues/               # Issue CRUD, AI context, Note-First editor
│   │   │   ├── members/              # Member profiles and management
│   │   │   ├── notes/                # Block editor (TipTap), ghost text, version history
│   │   │   ├── onboarding/           # 3-step workspace onboarding
│   │   │   └── settings/             # Workspace/AI/profile settings
│   │   ├── components/               # Shared UI components (cross-feature)
│   │   │   ├── ui/                   # shadcn/ui primitives
│   │   │   ├── layout/               # App shell, sidebar, header
│   │   │   ├── navigation/           # Nav menus
│   │   │   ├── editor/               # Shared TipTap base extensions
│   │   │   ├── issues/               # Shared issue selectors (state, priority, assignee)
│   │   │   ├── search/               # Command palette (Cmd+K)
│   │   │   ├── ai/                   # Shared AI chat components
│   │   │   └── providers.tsx         # Root provider composition
│   │   ├── stores/                   # MobX stores (UI state only)
│   │   │   ├── RootStore.ts          # Aggregator + context + typed hooks
│   │   │   ├── AuthStore.ts          # Auth state
│   │   │   ├── WorkspaceStore.ts     # Active workspace
│   │   │   ├── UIStore.ts            # Global UI flags (sidebar, modals)
│   │   │   ├── NotificationStore.ts  # Notification UI state
│   │   │   ├── OnboardingStore.ts    # Onboarding step state
│   │   │   ├── RoleSkillStore.ts     # Role skill templates
│   │   │   ├── TaskStore.ts          # Task UI state
│   │   │   ├── ai/                   # AIStore + 11 sub-stores (GhostText, Approval, etc.)
│   │   │   └── features/             # Feature-level stores (IssueStore, NoteStore, CycleStore, IssueViewStore)
│   │   ├── services/                 # API and auth services
│   │   │   ├── api/                  # Typed API wrappers (one per domain)
│   │   │   │   └── client.ts         # axios singleton, auth interceptor, RFC 7807 error class
│   │   │   └── auth/                 # Auth provider abstraction (Supabase)
│   │   ├── hooks/                    # Global shared hooks (auth, workspace)
│   │   ├── lib/                      # Utilities (queryClient, formatters, validators)
│   │   └── types/                    # Shared TypeScript type definitions
│   ├── next.config.ts                # Next.js config
│   ├── tailwind.config.ts            # Tailwind config
│   └── package.json                  # pnpm dependencies
├── cli/                              # pilot-cli (Python, uv)
│   └── pyproject.toml                # CLI package config
├── authcore/                         # Supabase Auth self-hosted service
│   └── src/authcore/                 # Mirrors backend Clean Architecture (api/application/domain/infrastructure)
├── infra/                            # Infrastructure as code
│   └── supabase/                     # Supabase local stack (docker-compose.yml)
├── docs/                             # Cross-cutting documentation
│   ├── DESIGN_DECISIONS.md           # 88 architecture decisions (DD-001 to DD-088)
│   ├── BUSINESS_CONTEXT.md           # Product vision and constraints
│   └── dev-pattern/                  # Developer pattern guides (45+ patterns)
├── specs/                            # Feature specifications
├── scripts/                          # Utility scripts
├── design-system/                    # Design tokens and references
├── docker-compose.yml                # Full stack orchestration
├── Makefile                          # Quality gate commands
└── CLAUDE.md                         # Project instructions for Claude
```

---

## Directory Purposes

**`backend/src/pilot_space/ai/`:**
- Purpose: All AI features — agent orchestration, MCP tools, provider routing, background workers
- Key files:
  - `agents/pilotspace_agent.py` — Main orchestrator (singleton in DI container)
  - `agents/subagents/` — Stateful multi-turn subagents (PR review, AI context, doc generator)
  - `mcp/tools/` — 33 MCP tool handlers (note_server, issue_server, memory_server, etc.)
  - `providers/provider_selector.py` — Task-type → model routing (20 task types)
  - `infrastructure/resilience.py` — Retry + circuit breaker
  - `workers/digest_worker.py`, `workers/memory_worker.py`, `workers/notification_worker.py` — asyncio background tasks
  - `templates/skills/` — YAML skill definitions (auto-discovered from `.claude/skills/`)

**`backend/src/pilot_space/api/v1/routers/`:**
- Purpose: One file per API resource group; all mounted to `/api/v1` in `main.py`
- Naming: `workspace_issues.py` = workspace-scoped CRUD; `issues.py` = cross-workspace activities
- Key pattern: Workspace-scoped resources use `/workspaces/{workspace_id}/` prefix routes

**`backend/src/pilot_space/application/services/`:**
- Purpose: One class per use case, grouped by domain subdirectory
- Structure: `services/issue/create_issue_service.py`, `services/note/create_note_service.py`, etc.
- Pattern: Services use `Payload` dataclasses as input; return domain/ORM objects

**`backend/src/pilot_space/infrastructure/database/models/`:**
- Purpose: SQLAlchemy ORM models (one file per entity, 35+ models)
- Key models: `issue.py`, `note.py`, `project.py`, `workspace.py`, `user.py`, `cycle.py`, `ai_session.py`, `graph_node.py`, `graph_edge.py`, `memory_entry.py`
- Base classes: `BaseModel` (UUID PK + timestamps + soft delete), `WorkspaceScopedModel` (+ workspace_id FK)

**`backend/src/pilot_space/infrastructure/database/repositories/`:**
- Purpose: 30+ concrete repositories extending `BaseRepository[T]`
- Pattern: `class IssueRepository(BaseRepository[Issue])` — adds domain-specific query methods
- Key: `base.py` provides `get_by_id`, `create`, `update`, `delete` (soft), `paginate` (cursor-based), `find_by`, `search`

**`backend/src/pilot_space/container/`:**
- Purpose: Dependency injection wiring (dependency-injector library)
- Files: `container.py` (main `Container`), `_base.py` (`InfraContainer`), `_factories.py` (complex factory functions)
- Access pattern: `container = get_container()` (lazy singleton), then `container.wire(modules=[...])`

**`frontend/src/features/notes/`:**
- Purpose: Note-First block editor, collaboration, ghost text, version history
- Key files:
  - `editor/config.ts` — `createEditorExtensions()` factory (16 TipTap extensions)
  - `editor/extensions/` — `BlockIdExtension`, `GhostTextExtension`, `IssueLinkExtension`, `SlashCommandExtension`
  - `collab/` — Yjs collaboration state
  - `stores/VersionStore.ts` — Version panel MobX state (panel, selected version, diff pair, restore)

**`frontend/src/features/issues/`:**
- Purpose: Issue CRUD, Note-First issue detail page, AI context generation
- Key files:
  - `contexts/issue-note-context.ts` — Context bridge for TipTap ↔ MobX integration (avoids nested flushSync)
  - `editor/property-block-extension.ts` — TipTap Node + 2 ProseMirror guard plugins
  - `components/issue-editor-content.tsx` — MUST NOT be `observer()` (TipTap + MobX React 19 conflict)

**`frontend/src/features/ai/`:**
- Purpose: Conversational AI interface, SSE stream handling, human-in-the-loop approvals
- Key subdirs: `ChatView/` (main UI), `ChatView/ApprovalOverlay/` (DD-003 approval UI), `ChatView/hooks/` (SSE processing)

**`frontend/src/stores/`:**
- Purpose: MobX observable state only — no API data
- Key files:
  - `RootStore.ts` — Aggregates all stores, provides `useStore()`, `useIssueStore()`, etc.
  - `ai/` — `AIStore` with 11 sub-stores (chat, ghost text, approvals, sessions, etc.)
  - `features/issues/IssueViewStore.ts` — Issue list view state (filter, sort, selected)
  - `features/notes/NoteStore.ts` — Note panel state

**`backend/alembic/versions/`:**
- Purpose: Database migrations (immutable once committed)
- Naming: `NNN_description.py` (sequential number prefix)
- Rule: NEVER edit existing files; create NEW migration to fix issues. Verify single head with `alembic heads`.

---

## Key File Locations

**Entry Points:**
- `backend/src/pilot_space/main.py` — FastAPI app factory, all routers, lifespan (workers + Redis)
- `frontend/src/app/layout.tsx` — Next.js root layout with font config
- `frontend/src/components/providers.tsx` — Provider composition (QueryClient + MobX + Theme)
- `frontend/src/stores/RootStore.ts` — MobX root store singleton + all domain hooks

**Configuration:**
- `backend/src/pilot_space/config.py` — `Settings` (Pydantic), `get_settings()` with `@lru_cache`
- `backend/.env.example` → `backend/.env` — Backend env vars (Supabase URL/keys, DB URL, Redis URL, AI keys)
- `frontend/.env.example` → `frontend/.env.local` — Frontend env vars (Supabase anon key, API URL)
- `backend/pyproject.toml` — uv deps, ruff config, pyright config, pytest coverage (80% threshold)
- `frontend/next.config.ts` — Next.js build config

**Core Logic:**
- `backend/src/pilot_space/container/container.py` — ALL service wiring; source of truth for DI
- `backend/src/pilot_space/infrastructure/database/repositories/base.py` — `BaseRepository[T]` (generic CRUD + pagination)
- `backend/src/pilot_space/infrastructure/database/rls.py` — `set_rls_context()` (required before workspace queries)
- `backend/src/pilot_space/ai/agents/pilotspace_agent.py` — AI orchestrator
- `backend/src/pilot_space/ai/providers/provider_selector.py` — Task → model routing
- `frontend/src/services/api/client.ts` — axios singleton, auth interceptor, `ApiError` class

**Testing:**
- `backend/tests/conftest.py` — SQLite in-memory engine (default); set `TEST_DATABASE_URL` for PostgreSQL
- `backend/tests/unit/` — Unit tests (service, repository layer)
- `backend/tests/integration/` — Integration tests (require committed DB session, PostgreSQL features)
- `frontend/src/**/__tests__/` — Vitest tests co-located within feature/component dirs

---

## Naming Conventions

**Backend Files:**
- Snake_case for all Python files: `create_issue_service.py`, `issue_repository.py`
- Service files: `{verb}_{entity}_service.py` (e.g., `create_issue_service.py`, `update_note_service.py`)
- Router files: `{entity}.py` or `{scope}_{entity}.py` (e.g., `issues.py`, `workspace_issues.py`)
- Repository files: `{entity}_repository.py`
- Model files: `{entity}.py` (singular)
- Migration files: `NNN_{description}.py` (sequential number prefix, immutable after commit)

**Frontend Files:**
- PascalCase for React components: `IssueDetailPage.tsx`, `PropertyBlockView.tsx`
- camelCase for hooks, utilities, services: `useIssueStore.ts`, `issuesApi.ts`, `formatDate.ts`
- kebab-case for feature module files that are not components: `issue-note-context.ts`, `property-block-extension.ts`
- Store files: `{Domain}Store.ts` (e.g., `IssueStore.ts`, `NoteStore.ts`)

**Frontend Directories:**
- Feature folders: lowercase singular (`issues/`, `notes/`, `ai/`, `cycles/`)
- Route groups: parenthesized (`(auth)/`, `(workspace)/`)
- Dynamic segments: bracket notation (`[workspaceSlug]/`, `[issueId]/`)

---

## Where to Add New Code

**New Backend API Endpoint:**
1. Add Pydantic schemas: `backend/src/pilot_space/api/v1/schemas/{entity}.py`
2. Create application service: `backend/src/pilot_space/application/services/{domain}/{verb}_{entity}_service.py`
3. Add router function: `backend/src/pilot_space/api/v1/routers/{entity}.py` (or new file)
4. Register service in DI container: `backend/src/pilot_space/container/container.py`
5. Import router and register in: `backend/src/pilot_space/main.py`
6. Write tests: `backend/tests/unit/test_{entity}_service.py`

**New SQLAlchemy Model:**
1. Create model file: `backend/src/pilot_space/infrastructure/database/models/{entity}.py`
2. Extend `WorkspaceScopedModel` (for workspace-scoped) or `BaseModel`
3. Add to `__init__.py` barrel in models dir
4. Create repository: `backend/src/pilot_space/infrastructure/database/repositories/{entity}_repository.py`
5. Register repository in `backend/src/pilot_space/container/_base.py` (`InfraContainer`)
6. Create Alembic migration: `cd backend && alembic revision --autogenerate -m "add_{entity}"`
7. Add RLS policies to migration (see `rules/rls-check.md`)
8. Verify migration chain: `cd backend && alembic heads`

**New Frontend Feature Module:**
1. Create dir: `frontend/src/features/{feature}/`
2. Add subdirs: `components/`, `hooks/`, `stores/` (if needed)
3. Create `index.ts` barrel for public API
4. Add TanStack Query hooks in `hooks/` (use `useQuery` / `useMutation`)
5. Add MobX store if UI state needed: extend in `frontend/src/stores/RootStore.ts`
6. Add API service: `frontend/src/services/api/{feature}.ts` using `apiClient`
7. Wire route: `frontend/src/app/(workspace)/[workspaceSlug]/{feature}/page.tsx`

**New Frontend Component:**
- Feature-specific: `frontend/src/features/{feature}/components/{ComponentName}.tsx`
- Cross-feature shared: `frontend/src/components/{category}/{ComponentName}.tsx`
- MobX-consuming: wrap with `observer(function ComponentName() { ... })`
- Tests co-located: `{feature}/components/__tests__/{ComponentName}.test.tsx`

**New AI Skill:**
1. Create YAML file: `.claude/skills/{SKILL_NAME}.md` (auto-discovered by `skill_discovery.py`)
2. Add template if needed: `backend/src/pilot_space/ai/templates/skills/{skill}/`
3. Skills are single-turn, stateless — do NOT add state or session management

**New MCP Tool:**
1. Add function with `@tool` decorator to appropriate server in `backend/src/pilot_space/ai/mcp/tools/`
2. Return JSON payload `{"status": "pending_apply", ...}` for content operations
3. Respect RLS: call `set_rls_context()` before any repository access

**Database Migration:**
1. Verify single head: `cd backend && alembic heads`
2. Check current head: compare with `backend/alembic/versions/` highest number
3. Create: `cd backend && alembic revision --autogenerate -m "description"`
4. Add RLS policies manually (autogenerate does NOT generate them)
5. Validate: `cd backend && alembic heads && alembic check`

**Utilities:**
- Backend shared helpers: `backend/src/pilot_space/infrastructure/` (appropriate subdirectory)
- Frontend shared utilities: `frontend/src/lib/{utility}.ts`
- Frontend shared hooks: `frontend/src/hooks/{useHookName}.ts`

---

## Special Directories

**`backend/alembic/versions/`:**
- Purpose: Database migration history
- Generated: Partially (autogenerate creates table DDL; RLS policies added manually)
- Committed: Yes — immutable once merged; NEVER edit existing files

**`backend/.venv/`:**
- Purpose: Python virtual environment (managed by uv)
- Generated: Yes
- Committed: No

**`frontend/.next/`:**
- Purpose: Next.js build output
- Generated: Yes
- Committed: No

**`backend/src/pilot_space/ai/templates/`:**
- Purpose: YAML skill definitions, role templates, prompt rules for AI layer
- Generated: No — hand-authored
- Committed: Yes — version-controlled, auto-discovered at startup

**`.claude/skills/`:**
- Purpose: Skill YAML files discovered by `skill_discovery.py` at startup
- Generated: No — authored by developers
- Committed: Yes

**`.planning/codebase/`:**
- Purpose: AI-generated codebase analysis documents for GSD workflow
- Generated: Yes (by `gsd:map-codebase` commands)
- Committed: Yes

**`docs/dev-pattern/`:**
- Purpose: 45+ developer pattern guides (canonical reference for all patterns)
- Key files: `45-pilot-space-patterns.md` (project overrides), `21c-frontend-mobx-state.md` (MobX), `07-repository.md`, `20-component.md`
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-03-07*
