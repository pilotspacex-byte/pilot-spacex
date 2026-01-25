# Tasks: Pilot Space MVP

**Source**: `/specs/001-pilot-space-mvp/`
**Required**: plan.md, spec.md
**Optional**: research.md (loaded), data-model.md (loaded), contracts/ (loaded), quickstart.md (loaded)

**Generated**: 2026-01-23 | **Updated**: 2026-01-24 (All MVP Phases Complete - T001-T360 done)
**User Stories**: 6 (P0+P1) | **Entities**: 21 | **Total Tasks**: 399

**Task Details**: See `tasks/` directory for implementation guidance per task.
- [📋 Task Index](tasks/_INDEX.md) - Overview and dependency graph

**Future Phases**:
- Phase 2 (P2): 81 tasks (T216-T296) → See `specs/002-pilot-space-phase2/tasks.md`
- Phase 3 (P3): 26 tasks (T297-T322) → See `specs/003-pilot-space-phase3/tasks.md`

*Note: Task IDs T216-T322 are reserved for Phase 2/3 and defined in their respective task files. MVP tasks use T001-T215 + T323-T361 (Polish + Cross-cutting).*

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label (Phase 3+ only) |

**Sub-task Numbering**: Tasks with letter suffixes (e.g., T034a, T129a) represent related tasks added after initial sequencing to extend a parent task's scope without renumbering. This maintains stable task references across documents.

---

## Phase 1: Setup

Project initialization and shared infrastructure.

📄 **Task Details**: [P1-T001-T008.md](tasks/P1-T001-T008.md) | [P1-T009-T016.md](tasks/P1-T009-T016.md) | [P1-T017-T023.md](tasks/P1-T017-T023.md)

### Backend Setup

- [x] T001 Create backend project structure: `backend/src/pilot_space/` with subdirectories (api, domain, ai, infrastructure, integrations) → [Details](tasks/P1-T001-T008.md#t001-create-backend-project-structure)
- [x] T002 Initialize FastAPI project with `backend/src/pilot_space/main.py` entry point → [Details](tasks/P1-T001-T008.md#t002-initialize-fastapi-project-with-mainpy)
- [x] T003 [P] Create `backend/pyproject.toml` with dependencies (fastapi, sqlalchemy[asyncio], alembic, pydantic, anthropic-sdk, dependency-injector) → [Details](tasks/P1-T001-T008.md#t003-p-create-pyprojecttoml-with-dependencies)
- [x] T004 [P] Configure `backend/src/pilot_space/config.py` with Pydantic Settings for environment variables → [Details](tasks/P1-T001-T008.md#t004-p-configure-pydantic-settings)
- [x] T005 [P] Setup `backend/.python-version` for Python 3.12+ → [Details](tasks/P1-T001-T008.md#t005-p-setup-python-version-file)
- [x] T006 [P] Configure ruff linting in `backend/ruff.toml` → [Details](tasks/P1-T001-T008.md#t006-p-configure-ruff-linting)
- [x] T007 [P] Configure pyright in `backend/pyrightconfig.json` with strict mode → [Details](tasks/P1-T001-T008.md#t007-p-configure-pyright-type-checking)
- [x] T008 [P] Create pre-commit hooks in `backend/.pre-commit-config.yaml` → [Details](tasks/P1-T001-T008.md#t008-p-create-pre-commit-hooks)

### Frontend Setup

- [x] T009 Create frontend project structure: `frontend/src/` with subdirectories (app, components, features, stores, services, hooks, lib) → [Details](tasks/P1-T009-T016.md#t009-create-frontend-project-structure)
- [x] T010 Initialize Next.js 14 project with `frontend/src/app/` app router → [Details](tasks/P1-T009-T016.md#t010-initialize-nextjs-14-project)
- [x] T011 [P] Create `frontend/package.json` with dependencies (react, mobx, @tanstack/react-query, @tiptap/react, tailwindcss, @tanstack/react-virtual) → [Details](tasks/P1-T009-T016.md#t011-p-create-packagejson-with-dependencies)
- [x] T012 [P] Configure TypeScript strict mode in `frontend/tsconfig.json` → [Details](tasks/P1-T009-T016.md#t012-p-configure-typescript-strict-mode)
- [x] T013 [P] Configure TailwindCSS in `frontend/tailwind.config.ts` → [Details](tasks/P1-T009-T016.md#t013-p-configure-tailwindcss)
- [x] T014 [P] Configure ESLint in `frontend/.eslintrc.json` → [Details](tasks/P1-T009-T016.md#t014-p-configure-eslint)
- [x] T015 [P] Setup Vitest config in `frontend/vitest.config.ts` → [Details](tasks/P1-T009-T016.md#t015-p-setup-vitest-config)
- [x] T016 [P] Setup Playwright config in `frontend/playwright.config.ts` → [Details](tasks/P1-T009-T016.md#t016-p-setup-playwright-config)

### Infrastructure Setup

- [x] T017 Create Docker Compose file in `infra/docker/docker-compose.yml` with services (postgres, redis, meilisearch, supabase) → [Details](tasks/P1-T017-T023.md#t017-create-docker-compose-file)
- [x] T018 [P] Create `infra/docker/Dockerfile.backend` for FastAPI → [Details](tasks/P1-T017-T023.md#t018-p-create-backend-dockerfile)
- [x] T019 [P] Create `infra/docker/Dockerfile.frontend` for Next.js → [Details](tasks/P1-T017-T023.md#t019-p-create-frontend-dockerfile)
- [x] T020 [P] Create `.env.example` with all required environment variables → [Details](tasks/P1-T017-T023.md#t020-p-create-envexample)
- [x] T021 Configure Supabase local development in `supabase/config.toml` → [Details](tasks/P1-T017-T023.md#t021-configure-supabase-local-development)

### Quality Gates

- [x] T022 Create quality gate script `scripts/quality-check.sh` running: ruff, pyright, pytest, pnpm lint, pnpm type-check, pnpm test → [Details](tasks/P1-T017-T023.md#t022-create-quality-gate-script)
- [x] T023 [P] Configure GitHub Actions CI in `.github/workflows/ci.yml` → [Details](tasks/P1-T017-T023.md#t023-p-configure-github-actions-ci)

**Checkpoint**: Project scaffolding complete - can start foundational work.

---

## Phase 2: Foundational

Core infrastructure required before user story work.

📄 **Task Details**: [P2-T024-T035.md](tasks/P2-T024-T035.md) | [P2-T036-T050.md](tasks/P2-T036-T050.md) | [P2-T051-T067.md](tasks/P2-T051-T067.md)

### Database Foundation (PostgreSQL + pgvector)

- [x] T024 Create SQLAlchemy async engine config in `backend/src/pilot_space/infrastructure/database/engine.py` → [Details](tasks/P2-T024-T035.md#t024-create-sqlalchemy-async-engine-config)
- [x] T025 Create SQLAlchemy base model in `backend/src/pilot_space/infrastructure/database/base.py` with UUID PK, timestamps, soft delete mixin → [Details](tasks/P2-T024-T035.md#t025-create-sqlalchemy-base-model)
- [x] T026 Configure Alembic in `backend/alembic.ini` and `backend/alembic/env.py` for async migrations → [Details](tasks/P2-T024-T035.md#t026-configure-alembic-for-async-migrations)
- [x] T027 Create pgvector extension migration in `backend/alembic/versions/001_enable_pgvector.py` → [Details](tasks/P2-T024-T035.md#t027-create-pgvector-extension-migration)

### Tier 1 Entities: User & Workspace (Foundational)

- [x] T028 Create User SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/user.py` → [Details](tasks/P2-T024-T035.md#t028-create-user-sqlalchemy-model)
- [x] T029 Create Workspace SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/workspace.py` → [Details](tasks/P2-T024-T035.md#t029-create-workspace-sqlalchemy-model)
- [x] T030 Create WorkspaceMember SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/workspace_member.py` → [Details](tasks/P2-T024-T035.md#t030-create-workspacemember-sqlalchemy-model)
- [x] T031 Create migration for User, Workspace, WorkspaceMember tables in `backend/alembic/versions/002_core_entities.py` → [Details](tasks/P2-T024-T035.md#t031-create-migration-for-user-workspace-workspacemember)

### Tier 2 Entities: Project & Workflow Structure

- [x] T032 Create Project SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/project.py` → [Details](tasks/P2-T024-T035.md#t032-create-project-sqlalchemy-model)
- [x] T033 Create State SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/state.py` with state groups per FR-003 (unstarted: Backlog/Todo, started: InProgress/InReview, completed: Done, cancelled: Cancelled) → [Details](tasks/P2-T024-T035.md#t033-create-state-sqlalchemy-model)
- [x] T034 Create Label SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/label.py` → [Details](tasks/P2-T024-T035.md#t034-create-label-sqlalchemy-model)
- [x] T034a Create Module SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/module.py` *(Note: Module = Epic per FR-006. Data model foundation only - full Module/Epic feature in Phase 2 US-05)*
- [x] T035 Create migration for Project, State, Label, Module tables in `backend/alembic/versions/003_project_entities.py` → [Details](tasks/P2-T024-T035.md#t035-create-migration-for-project-state-label-module)

### Repository Layer (Base)

- [x] T036 Create generic BaseRepository in `backend/src/pilot_space/infrastructure/database/repositories/base.py` with CRUD, soft delete, restore, cursor pagination
- [x] T037 [P] Create UserRepository in `backend/src/pilot_space/infrastructure/database/repositories/user_repository.py`
- [x] T038 [P] Create WorkspaceRepository in `backend/src/pilot_space/infrastructure/database/repositories/workspace_repository.py`
- [x] T039 [P] Create ProjectRepository in `backend/src/pilot_space/infrastructure/database/repositories/project_repository.py`
- [x] T040a Create AIConfiguration SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/ai_configuration.py` for workspace-level LLM provider settings with encrypted API keys (FR-022)

### Authentication (Supabase Auth)

- [x] T040 Create Supabase Auth client in `backend/src/pilot_space/infrastructure/auth/supabase_auth.py`
- [x] T041 Create JWT validation middleware in `backend/src/pilot_space/api/middleware/auth_middleware.py`
- [x] T042 Create current_user dependency in `backend/src/pilot_space/dependencies.py`
- [x] T043 Create RLS policy helper functions in `backend/src/pilot_space/infrastructure/database/rls.py`
- [x] T044 Create RLS policies migration for workspace isolation in `backend/alembic/versions/004_rls_policies.py`

### API Foundation

- [x] T045 Create FastAPI router aggregator in `backend/src/pilot_space/api/v1/__init__.py`
- [x] T046 Create RFC 7807 error handler in `backend/src/pilot_space/api/middleware/error_handler.py`
- [x] T047 [P] Create Pydantic base schemas in `backend/src/pilot_space/api/v1/schemas/base.py` (PaginatedResponse, ErrorResponse)
- [x] T048 Create CORS middleware config in `backend/src/pilot_space/api/middleware/cors.py`
- [x] T048a Create rate limiting middleware in `backend/src/pilot_space/api/middleware/rate_limiter.py` implementing: 1000 req/min standard, 100 req/min AI endpoints per NFR-019; **per-workspace tracking** using Redis with key pattern `ratelimit:{workspace_id}:{endpoint_type}`; return `429 Too Many Requests` with `Retry-After` header

### Dependency Injection

- [x] T049 Create DI container in `backend/src/pilot_space/container.py` using dependency-injector
- [x] T050 Wire repositories and services to container in `backend/src/pilot_space/container.py`

### Auth Endpoints

- [x] T051 Create auth schemas in `backend/src/pilot_space/api/v1/schemas/auth.py` (LoginRequest, AuthResponse, TokenResponse)
- [x] T052 Create auth router in `backend/src/pilot_space/api/v1/routers/auth.py` with login, callback, refresh, me endpoints

### Workspace Endpoints

- [x] T053 Create workspace schemas in `backend/src/pilot_space/api/v1/schemas/workspace.py`
- [x] T053a Create AIConfiguration schemas and endpoints in `backend/src/pilot_space/api/v1/schemas/ai_configuration.py` and `backend/src/pilot_space/api/v1/routers/ai_configuration.py` for workspace admin LLM key management (FR-022)
- [x] T054 Create workspace router in `backend/src/pilot_space/api/v1/routers/workspaces.py` with CRUD and member management

### Project Endpoints

- [x] T055 Create project schemas in `backend/src/pilot_space/api/v1/schemas/project.py`
- [x] T056 Create project router in `backend/src/pilot_space/api/v1/routers/projects.py` with CRUD

### Frontend Foundation

- [x] T057 Create RootStore MobX store in `frontend/src/stores/RootStore.ts`
- [x] T058 [P] Create AuthStore MobX store in `frontend/src/stores/AuthStore.ts`
- [x] T059 [P] Create WorkspaceStore MobX store in `frontend/src/stores/WorkspaceStore.ts`
- [x] T060 [P] Create UIStore MobX store in `frontend/src/stores/UIStore.ts`
- [x] T061 Create TanStack Query client config in `frontend/src/lib/queryClient.ts`
- [x] T062 Create API client in `frontend/src/services/api/client.ts` with axios instance and auth interceptor
- [x] T063 Create root layout in `frontend/src/app/layout.tsx` with providers (MobX, TanStack Query, Supabase Auth)
- [x] T064 [P] Create shadcn/ui base components in `frontend/src/components/ui/` (Button, Modal, Tooltip, Input, Select)

### Cache Infrastructure

- [x] T065 Create Redis client in `backend/src/pilot_space/infrastructure/cache/redis.py`

### Queue Infrastructure

- [x] T066 Create Supabase Queue client in `backend/src/pilot_space/infrastructure/queue/supabase_queue.py` using pgmq
- [x] T066a Create Edge Function timeout handler in `backend/src/pilot_space/infrastructure/queue/error_handlers.py` with retry logic per spec.md edge case (3 retries, exponential backoff)

### Search Infrastructure

- [x] T067 Create Meilisearch client in `backend/src/pilot_space/infrastructure/search/meilisearch.py`

**Checkpoint**: Foundation complete - user stories can start.

---

## Phase 3: User Story 1 - Note-First Collaborative Writing (P0) 🎯 MVP

**Goal**: Enable users to create notes with AI ghost text, margin annotations, and issue extraction
**Verify**: Create a note, see ghost text after 500ms typing pause, view margin annotations, extract issue from text

📄 **Task Details**: [P3-US01-T068-T096.md](tasks/P3-US01-T068-T096.md) | [P3-US01-T097-T117.md](tasks/P3-US01-T097-T117.md)

### Database Models

- [x] T068 [US1] Create Template SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/template.py` *(Note: Foundational entity for AI ghost text context - full Template feature in Phase 2 US-15)*
- [x] T069 [US1] Create Note SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/note.py` with TipTap JSONB content
- [x] T070 [US1] Create NoteAnnotation SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/note_annotation.py`
- [x] T071 [US1] Create ThreadedDiscussion SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/threaded_discussion.py`
- [x] T072 [US1] Create DiscussionComment SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/discussion_comment.py`
- [x] T073 [US1] Create migration for Note entities in `backend/alembic/versions/005_note_entities.py` *(Note: Page model created in migration but no CRUD endpoints - full Pages feature in Phase 2 US-06)*
- [x] T073a [US1] Create NoteIssueLink junction table in `backend/src/pilot_space/infrastructure/database/models/note_issue_link.py` for bidirectional note-issue sync

### Repositories

- [x] T074 [P] [US1] Create NoteRepository in `backend/src/pilot_space/infrastructure/database/repositories/note_repository.py`
- [x] T075 [P] [US1] Create NoteAnnotationRepository in `backend/src/pilot_space/infrastructure/database/repositories/note_annotation_repository.py`
- [x] T076 [P] [US1] Create DiscussionRepository in `backend/src/pilot_space/infrastructure/database/repositories/discussion_repository.py`
- [x] T077 [P] [US1] Create TemplateRepository in `backend/src/pilot_space/infrastructure/database/repositories/template_repository.py`

### Services (CQRS-lite)

- [x] T078 [US1] Create CreateNoteService in `backend/src/pilot_space/application/services/note/create_note_service.py`
- [x] T079 [US1] Create UpdateNoteService in `backend/src/pilot_space/application/services/note/update_note_service.py`
- [x] T080 [US1] Create GetNoteService in `backend/src/pilot_space/application/services/note/get_note_service.py`
- [x] T081 [US1] Create CreateAnnotationService in `backend/src/pilot_space/application/services/annotation/create_annotation_service.py`
- [x] T082 [US1] Create CreateDiscussionService in `backend/src/pilot_space/application/services/discussion/create_discussion_service.py`

### AI Agents (US1)

- [x] T083 [US1] Create base AI agent class in `backend/src/pilot_space/ai/agents/base.py` with Claude SDK integration
- [x] T084 [US1] Create GhostTextAgent in `backend/src/pilot_space/ai/agents/ghost_text_agent.py` with 500ms debounce, 50 token max, Gemini Flash provider, **word boundary buffering (DD-067)**: buffer chunks until whitespace/punctuation before streaming to client
- [x] T085 [US1] Create MarginAnnotationAgent in `backend/src/pilot_space/ai/agents/margin_annotation_agent.py` for suggestion/warning/issue_candidate annotations
- [x] T086 [US1] Create IssueExtractorAgent in `backend/src/pilot_space/ai/agents/issue_extractor_agent.py` for extracting issues from note content
- [x] T087 [US1] Create ghost text prompt template in `backend/src/pilot_space/ai/prompts/ghost_text.py`
- [x] T088 [P] [US1] Create margin annotation prompt template in `backend/src/pilot_space/ai/prompts/margin_annotation.py`
- [x] T089 [P] [US1] Create issue extraction prompt template in `backend/src/pilot_space/ai/prompts/issue_extraction.py`

### SSE Streaming Infrastructure

- [x] T090 [US1] Create SSE response helper in `backend/src/pilot_space/api/utils/sse.py`
- [x] T091 [US1] Create AI orchestrator in `backend/src/pilot_space/ai/orchestrator.py` for task routing

### AI Error Handling (Cross-cutting)

- [x] T091a [US1] Create AI error types in `backend/src/pilot_space/ai/exceptions.py` (RateLimitError, ProviderUnavailableError, TokenLimitExceededError, InvalidResponseError)
- [x] T091b [US1] Implement circuit breaker pattern in `backend/src/pilot_space/ai/circuit_breaker.py` for provider failover (3 failures → 30s backoff)
- [x] T091c [US1] Create retry decorator in `backend/src/pilot_space/ai/utils/retry.py` with exponential backoff (initial: 1s, max: 30s, max_retries: 3)
- [x] T091d [US1] Implement graceful degradation in AI agents: ghost text → "AI temporarily unavailable" (3s fade), annotations → hide panel, PR review → queue with notification
- [x] T091e [US1] Create AI telemetry middleware in `backend/src/pilot_space/ai/telemetry.py` for error tracking, latency metrics, cost logging
- [x] T091f [US1] Create ConversationAgent in `backend/src/pilot_space/ai/agents/conversation_agent.py` for multi-turn AI discussions in note threaded discussions using Claude SDK multi-turn conversation with context retention (US-01 AS-5, AS-6, AS-14)

### API Endpoints

- [x] T092 [US1] Create note schemas in `backend/src/pilot_space/api/v1/schemas/note.py` (NoteCreate, NoteUpdate, NoteResponse, NoteDetailResponse)
- [x] T093 [US1] Create annotation schemas in `backend/src/pilot_space/api/v1/schemas/annotation.py`
- [x] T094 [US1] Create discussion schemas in `backend/src/pilot_space/api/v1/schemas/discussion.py`
- [x] T095 [US1] Create notes router in `backend/src/pilot_space/api/v1/routers/notes.py` with CRUD, ghost-text SSE, annotations, discussions, **issue links**: `POST/DELETE /api/v1/notes/{id}/issues/{issueId}` for bidirectional sync (T073a)
- [x] T096 [US1] Create AI router in `backend/src/pilot_space/api/v1/routers/ai.py` with ghost-text streaming endpoint

### Frontend: Note Canvas

- [x] T097 [US1] Create NoteStore MobX store in `frontend/src/stores/NoteStore.ts`
- [x] T098 [US1] Create TipTap editor base config in `frontend/src/features/notes/editor/config.ts`
- [x] T099 [US1] Create GhostTextExtension TipTap extension in `frontend/src/features/notes/editor/extensions/GhostTextExtension.ts` with Tab/→ acceptance, **word boundary display (DD-067)**: never display partial tokens; → accepts word-by-word (split on whitespace only)
- [x] T100 [US1] Create MarginAnnotationExtension TipTap extension in `frontend/src/features/notes/editor/extensions/MarginAnnotationExtension.ts`
- [x] T101 [US1] Create IssueLinkExtension TipTap extension in `frontend/src/features/notes/editor/extensions/IssueLinkExtension.ts`
- [x] T102 [P] [US1] Create CodeBlockExtension TipTap extension in `frontend/src/features/notes/editor/extensions/CodeBlockExtension.ts` with syntax highlighting
- [x] T103 [P] [US1] Create MentionExtension TipTap extension in `frontend/src/features/notes/editor/extensions/MentionExtension.ts`
- [x] T104 [P] [US1] Create SlashCommandExtension TipTap extension in `frontend/src/features/notes/editor/extensions/SlashCommandExtension.ts`
- [x] T105 [US1] Create NoteCanvas component in `frontend/src/components/editor/NoteCanvas.tsx` with virtualization for 1000+ blocks
- [x] T106 [US1] Create MarginAnnotations component in `frontend/src/components/editor/MarginAnnotations.tsx` with resizable panel (150-350px, 200px default), **draggable left border resize handle** (`cursor: col-resize`), store width in localStorage, CSS Anchor Positioning API with fallback for Safari/Firefox
- [x] T107 [US1] Create IssueExtractionPanel component in `frontend/src/components/editor/IssueExtractionPanel.tsx` with rainbow-bordered boxes
- [x] T108 [US1] Create ThreadedDiscussion component in `frontend/src/components/editor/ThreadedDiscussion.tsx`
- [x] T109 [US1] Create SelectionToolbar component in `frontend/src/components/editor/SelectionToolbar.tsx` for AI action triggers
- [x] T110 [US1] Create RichNoteHeader component in `frontend/src/components/editor/RichNoteHeader.tsx` with metadata (date, author, word count, reading time)
- [x] T110a [US1] Create VersionHistoryPanel component in `frontend/src/components/editor/VersionHistoryPanel.tsx` with AI reasoning display per FR-020
- [x] T111 [US1] Create AutoTOC component in `frontend/src/components/editor/AutoTOC.tsx` for auto-generated table of contents
- [x] T112 [US1] Create OutlineTree component in `frontend/src/components/navigation/OutlineTree.tsx` for note sidebar

### Note Pinning (US1 Scenario 20)

- [x] T112a [US1] Add `is_pinned` boolean field to Note model and create PinNoteService in `backend/src/pilot_space/application/services/note/pin_note_service.py`
- [x] T112b [US1] Add pin/unpin endpoint to notes router `POST /api/v1/notes/{id}/pin` with toggle behavior
- [x] T112c [US1] Create PinnedNotesList component in `frontend/src/components/navigation/PinnedNotesList.tsx` for sidebar top section

### Frontend: Pages

- [x] T113 [US1] Create notes list page in `frontend/src/app/(workspace)/notes/page.tsx`
- [x] T114 [US1] Create note detail page in `frontend/src/app/(workspace)/notes/[noteId]/page.tsx`
- [x] T115 [US1] Create note hooks (useNotes, useNote, useCreateNote) in `frontend/src/features/notes/hooks/`

### Frontend: Real-time & Auto-save

- [x] T116 [US1] Create auto-save hook in `frontend/src/features/notes/hooks/useAutoSave.ts` with 1-2s debounce
- [x] T117 [US1] Create ghost text SSE client in `frontend/src/features/notes/services/ghostTextService.ts`
- [x] T117a [US1] Create useIssueSyncListener hook in `frontend/src/features/notes/hooks/useIssueSyncListener.ts` subscribing to Supabase Realtime for linked issue state changes, displaying sync indicator badge when linked issue changes state (US-01 AS-12)

**Checkpoint**: US1 complete - Note canvas functional with ghost text, annotations, issue extraction.

---

## Phase 4: User Story 2 - Create and Manage Issues with AI Assistance (P1)

**Goal**: Enable AI-enhanced issue creation with suggestions, duplicate detection, and confidence tags
**Verify**: Create issue, see AI suggestions for title/labels/priority, detect duplicates, accept/reject suggestions

📄 **Task Details**: [P4-US02-T118-T154.md](tasks/P4-US02-T118-T154.md)

### Database Models

- [x] T118 [US2] Create Issue SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/issue.py` with ai_metadata JSONB
- [x] T119 [US2] Create issue_labels junction table in `backend/src/pilot_space/infrastructure/database/models/issue_label.py`
- [x] T120 [US2] Create Activity SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/activity.py`
- [x] T121 [US2] Create migration for Issue entities in `backend/alembic/versions/006_issue_entities.py`

### Repositories

- [x] T122 [P] [US2] Create IssueRepository in `backend/src/pilot_space/infrastructure/database/repositories/issue_repository.py`
- [x] T123 [P] [US2] Create ActivityRepository in `backend/src/pilot_space/infrastructure/database/repositories/activity_repository.py`
- [x] T124 [P] [US2] Create LabelRepository in `backend/src/pilot_space/infrastructure/database/repositories/label_repository.py`

### Services (CQRS-lite)

- [x] T125 [US2] Create CreateIssueService in `backend/src/pilot_space/application/services/issue/create_issue_service.py` with AI enhancement
- [x] T126 [US2] Create UpdateIssueService in `backend/src/pilot_space/application/services/issue/update_issue_service.py`
- [x] T127 [US2] Create GetIssueService in `backend/src/pilot_space/application/services/issue/get_issue_service.py`
- [x] T128 [US2] Create ListIssuesService in `backend/src/pilot_space/application/services/issue/list_issues_service.py` with cursor pagination
- [x] T129 [US2] Create RecordActivityService in `backend/src/pilot_space/application/services/activity/record_activity_service.py`
- [x] T129a [US2] Create ApprovalFlowService in `backend/src/pilot_space/application/services/ai/approval_flow_service.py` for human-in-loop AI action approval (FR-032) → Frontend: T354-T356

### Activity Logging (FR-064)

- [x] T129b [US2] Create activity logging decorator in `backend/src/pilot_space/application/services/decorators/activity_logger.py` for automatic audit trail on entity changes
- [x] T129c [US2] Integrate activity logging into CreateIssueService, UpdateIssueService (T125-T126) via decorator
- [x] T129d [US1] Integrate activity logging into CreateNoteService, UpdateNoteService (T078-T079) via decorator

### AI Agents (US2)

- [x] T130 [US2] Create IssueEnhancerAgent in `backend/src/pilot_space/ai/agents/issue_enhancer_agent.py` for title/description/labels/priority suggestions
- [x] T131 [US2] Create DuplicateDetectorAgent in `backend/src/pilot_space/ai/agents/duplicate_detector_agent.py` with pgvector similarity
- [x] T132 [US2] Create AssigneeRecommenderAgent in `backend/src/pilot_space/ai/agents/assignee_recommender_agent.py` using Anthropic Haiku for fast recommendations based on code ownership and expertise mapping (7th MVP agent per plan.md)
- [x] T133 [P] [US2] Create issue enhancement prompt in `backend/src/pilot_space/ai/prompts/issue_enhancement.py`
- [x] T134 [P] [US2] Create duplicate detection prompt in `backend/src/pilot_space/ai/prompts/duplicate_detection.py`

### RAG Pipeline for Duplicate Detection (Sequential - T135→T136→T137→T138→T139)

- [x] T135 [US2] Create Embedding SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/embedding.py` with pgvector
- [x] T136 [US2] Create migration for Embedding table with HNSW index in `backend/alembic/versions/007_embedding_table.py` (blocked by: T135)
- [x] T137 [US2] Create embeddings service in `backend/src/pilot_space/ai/rag/embeddings.py` using OpenAI text-embedding-3-large (blocked by: T136)
- [x] T138 [US2] Create retriever service in `backend/src/pilot_space/ai/rag/retriever.py` for similarity search (blocked by: T137)
- [x] T139 [US2] Create indexer worker in `backend/src/pilot_space/ai/rag/indexer.py` for async embedding generation (blocked by: T138)

### API Endpoints

- [x] T140 [US2] Create issue schemas in `backend/src/pilot_space/api/v1/schemas/issue.py`
- [x] T141 [US2] Create AI suggestion schemas in `backend/src/pilot_space/api/v1/schemas/ai_suggestion.py` (IssueEnhancement, DuplicateCandidate)
- [x] T142 [US2] Create issues router in `backend/src/pilot_space/api/v1/routers/issues.py` with CRUD, activity log
- [x] T143 [US2] Add enhance-issue endpoint to AI router in `backend/src/pilot_space/api/v1/routers/ai.py`
- [x] T144 [US2] Add detect-duplicates endpoint to AI router in `backend/src/pilot_space/api/v1/routers/ai.py`

### Frontend: Issue Management

- [x] T145 [US2] Create IssueStore MobX store in `frontend/src/stores/IssueStore.ts`
- [x] T146 [US2] Create IssueCreateModal component in `frontend/src/components/issues/IssueCreateModal.tsx` with AI suggestions
- [x] T147 [US2] Create DuplicateDetection component in `frontend/src/components/issues/DuplicateDetection.tsx`
- [x] T148 [US2] Create ConfidenceTags component in `frontend/src/components/ai/ConfidenceTags.tsx` (Recommended, Default, Alternative)
- [x] T149 [US2] Create IssueDetail component in `frontend/src/components/issues/IssueDetail.tsx`
- [x] T150 [US2] Create IssueList component in `frontend/src/components/issues/IssueList.tsx` with virtualization
- [x] T151 [US2] Create IssueQuickView component in `frontend/src/components/issues/IssueQuickView.tsx`
- [x] T152 [US2] Create issue hooks (useIssues, useIssue, useCreateIssue) in `frontend/src/features/issues/hooks/`

### Frontend: Pages

- [x] T153 [US2] Create issues list page in `frontend/src/app/(workspace)/projects/[projectId]/issues/page.tsx`
- [x] T154 [US2] Create issue detail page in `frontend/src/app/(workspace)/projects/[projectId]/issues/[issueId]/page.tsx`

### Issue View Components (FR-008, FR-009)

- [x] T150a [US2] Create IssueFilter component in `frontend/src/components/issues/IssueFilter.tsx` for filtering by state, priority, assignee, label, date range (FR-008)
- [x] T150b [US2] Create IssueCalendarView component in `frontend/src/components/issues/IssueCalendarView.tsx` for calendar layout view (FR-009)

### Soft Delete Restoration (FR-063)

*Note: Sub-task lettering (T154a, T154b, etc.) is used for related tasks that extend a parent task's scope without breaking sequential ordering.*

- [x] T154a [US2] Add restore endpoint to issues router `POST /api/v1/issues/{id}/restore` with permission check (creator OR admin)
- [x] T154b [US2] Add trash view endpoint `GET /api/v1/workspaces/{id}/trash` listing all soft-deleted entities
- [x] T154c [US2] Create TrashView component in `frontend/src/components/workspace/TrashView.tsx` with restore button
- [x] T154d [US2] Add RLS policy for restore permission in `backend/alembic/versions/004_rls_policies.py` allowing restore if creator OR admin/owner

### Issue Context Menu (US2 AS-8)

- [x] T154e [US2] Create RelatedIssuesAgent in `backend/src/pilot_space/ai/agents/related_issues_agent.py` using pgvector similarity to find semantically related issues (AS-8)
- [x] T154f [US2] Add find-related-issues endpoint `GET /api/v1/issues/{id}/related` returning top 5 related issues with similarity scores
- [x] T154g [US2] Create IssueContextMenu component in `frontend/src/components/issues/IssueContextMenu.tsx` with AI section: "Find Related Issues", "Suggest Assignee", "Enhance with AI"

### Bulk Issue Operations (US2 AS-7)

- [x] T154h [US2] Create BulkIssueSummaryAgent in `backend/src/pilot_space/ai/agents/bulk_issue_summary_agent.py` for summarizing multiple issues and extracting common themes (AS-7)
- [x] T154i [US2] Add bulk-analyze endpoint `POST /api/v1/ai/bulk-analyze-issues` accepting array of issue IDs and returning summary with common themes

**Checkpoint**: US2 complete - AI-enhanced issue creation with duplicate detection.

---

## Phase 5: User Story 4 - Plan and Track Sprints (P1)

**Goal**: Enable sprint planning with cycles, velocity tracking, and burndown metrics
**Verify**: Create cycle, add issues, view board with drag-drop state changes, see velocity/burndown

📄 **Task Details**: [P5-US04-T155-T171.md](tasks/P5-US04-T155-T171.md)

### Database Models

- [x] T155 [US4] Create Cycle SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/cycle.py`
- [x] T156 [US4] Create migration for Cycle entity in `backend/alembic/versions/008_cycle_entity.py`

### Repositories

- [x] T157 [US4] Create CycleRepository in `backend/src/pilot_space/infrastructure/database/repositories/cycle_repository.py`

### Services (CQRS-lite)

- [x] T158 [US4] Create CreateCycleService in `backend/src/pilot_space/application/services/cycle/create_cycle_service.py`
- [x] T159 [US4] Create GetCycleService in `backend/src/pilot_space/application/services/cycle/get_cycle_service.py` with velocity computation
- [x] T160 [US4] Create AddIssueToCycleService in `backend/src/pilot_space/application/services/cycle/add_issue_to_cycle_service.py`
- [x] T161 [US4] Create RolloverCycleService in `backend/src/pilot_space/application/services/cycle/rollover_cycle_service.py`

### API Endpoints

- [x] T162 [US4] Create cycle schemas in `backend/src/pilot_space/api/v1/schemas/cycle.py`
- [x] T163 [US4] Create cycles router in `backend/src/pilot_space/api/v1/routers/cycles.py` with CRUD, issue assignment

### Frontend: Sprint Planning

- [x] T164 [US4] Create CycleStore MobX store in `frontend/src/stores/CycleStore.ts`
- [x] T165 [US4] Create CycleBoard component in `frontend/src/components/cycles/CycleBoard.tsx` with drag-drop
- [x] T166 [US4] Create VelocityChart component in `frontend/src/components/cycles/VelocityChart.tsx`
- [x] T167 [US4] Create BurndownChart component in `frontend/src/components/cycles/BurndownChart.tsx`
- [x] T168 [US4] Create CycleRolloverModal component in `frontend/src/components/cycles/CycleRolloverModal.tsx`
- [x] T169 [US4] Create cycle hooks (useCycles, useCycle, useCreateCycle) in `frontend/src/features/cycles/hooks/`

### Frontend: Pages

- [x] T170 [US4] Create cycles list page in `frontend/src/app/(workspace)/projects/[projectId]/cycles/page.tsx`
- [x] T171 [US4] Create cycle detail page in `frontend/src/app/(workspace)/projects/[projectId]/cycles/[cycleId]/page.tsx`

**Checkpoint**: ✅ US4 complete - Sprint planning with cycles and metrics.

---

## Phase 6: User Story 18 - Link and Track GitHub Repositories (P1)

**Goal**: Enable GitHub integration with OAuth, PR/commit linking, and auto-transitions
**Verify**: Connect GitHub, link repo, see commits/PRs on issues, auto-transition on PR merge

📄 **Task Details**: [P6-US18-T172-T192.md](tasks/P6-US18-T172-T192.md)

### Database Models

- [x] T172 [US18] Create Integration SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/integration.py`
- [x] T173 [US18] Create IntegrationLink SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/integration_link.py`
- [x] T174 [US18] Create migration for Integration entities in `backend/alembic/versions/009_integration_entities.py`

### Repositories

- [x] T175 [P] [US18] Create IntegrationRepository in `backend/src/pilot_space/infrastructure/database/repositories/integration_repository.py`
- [x] T176 [P] [US18] Create IntegrationLinkRepository in `backend/src/pilot_space/infrastructure/database/repositories/integration_link_repository.py`

### GitHub Client

- [x] T177 [US18] Create GitHub API client in `backend/src/pilot_space/integrations/github/client.py`
- [x] T178 [US18] Create GitHub webhook handler in `backend/src/pilot_space/integrations/github/webhooks.py`
- [x] T179 [US18] Create GitHub sync service in `backend/src/pilot_space/integrations/github/sync.py` for commit/PR linking
- [x] T180 [US18] Create CommitLinkerAgent in `backend/src/pilot_space/ai/agents/commit_linker_agent.py` for parsing issue references

### Services

- [x] T181 [US18] Create ConnectGitHubService in `backend/src/pilot_space/application/services/integration/connect_github_service.py`
- [x] T182 [US18] Create ProcessGitHubWebhookService in `backend/src/pilot_space/application/services/integration/process_github_webhook_service.py`
- [x] T183 [US18] Create LinkCommitService in `backend/src/pilot_space/application/services/integration/link_commit_service.py`
- [x] T184 [US18] Create AutoTransitionService in `backend/src/pilot_space/application/services/integration/auto_transition_service.py` for PR merge → issue complete
- [x] T184a [US18] Create scheduled commit scanner job in `backend/src/pilot_space/infrastructure/queue/handlers/commit_scanner_handler.py` using pg_cron to scan for missed commits every 15 minutes (hybrid approach per spec.md clarification)

### API Endpoints

- [x] T185 [US18] Create integration schemas in `backend/src/pilot_space/api/v1/schemas/integration.py`
- [x] T186 [US18] Create integrations router in `backend/src/pilot_space/api/v1/routers/integrations.py` with GitHub OAuth flow
- [x] T187 [US18] Create webhooks router in `backend/src/pilot_space/api/v1/routers/webhooks.py` for GitHub events

### Frontend: GitHub Integration

- [x] T188 [US18] Create GitHubIntegration component in `frontend/src/components/integrations/GitHubIntegration.tsx`
- [x] T189 [US18] Create BranchSuggestion component in `frontend/src/components/integrations/BranchSuggestion.tsx`
- [x] T189a [US18] Create branch name generation endpoint `GET /api/v1/issues/{id}/suggested-branch` in issues router returning format `feature/{prefix}-{id}-{slug}` (FR-093)
- [x] T189b [US18] Add copy-to-clipboard functionality to BranchSuggestion component with success toast notification
- [x] T190 [US18] Create PRLinkBadge component in `frontend/src/components/integrations/PRLinkBadge.tsx`
- [x] T191 [US18] Create CommitList component in `frontend/src/components/integrations/CommitList.tsx`

### Frontend: Settings Page

- [x] T192 [US18] Create integrations settings page in `frontend/src/app/(workspace)/settings/integrations/page.tsx`

**Checkpoint**: ✅ US18 complete - GitHub integration with PR/commit linking.

---

## Phase 7: User Story 3 - Receive AI Code Review on Pull Requests (P1)

**Goal**: Enable automated AI code review on PR open with severity-tagged inline comments
**Verify**: Open PR, AI review posts comments within 5 min, see severity (Critical/Warning/Suggestion)

📄 **Task Details**: [P7-US03-T193-T200.md](tasks/P7-US03-T193-T200.md)

### AI Agents (US3)

- [x] T193 [US3] Create PRReviewAgent in `backend/src/pilot_space/ai/agents/pr_review_agent.py` using Claude Opus with tools
- [x] T194 [US3] Create PR review prompt template in `backend/src/pilot_space/ai/prompts/pr_review.py` covering architecture, security, quality

### Queue Processing

- [x] T195 [US3] Create PR review job handler in `backend/src/pilot_space/infrastructure/queue/handlers/pr_review_handler.py`
- [x] T195a [US3] Register PR review handler with Supabase Queues in `backend/src/pilot_space/infrastructure/queue/registry.py`
- [x] T196 [US3] Create PR review task status tracking in `backend/src/pilot_space/application/services/ai/pr_review_service.py`

### API Endpoints

- [x] T197 [US3] Create PR review schemas in `backend/src/pilot_space/api/v1/schemas/pr_review.py`
- [x] T198 [US3] Add trigger-pr-review endpoint to integrations router
- [x] T199 [US3] Add get-pr-review-status endpoint to AI router

### Frontend: PR Review Display

- [x] T200 [US3] Create PRReviewStatus component in `frontend/src/components/integrations/PRReviewStatus.tsx`

### Review Dimension Implementation (DD-006)

- [x] T200a [US3] Implement security analysis in PRReviewAgent with vulnerability detection, auth checks, input validation review
- [x] T200b [US3] Implement performance profiling in PRReviewAgent with complexity analysis, N+1 detection, memory patterns
- [x] T200c [US3] Implement architecture compliance in PRReviewAgent with design patterns, modularity, SOLID principles
- [x] T200d [US3] Implement documentation gap detection in PRReviewAgent with docstring coverage, comment quality, API docs
- [x] T200e [US3] Implement large PR handling in PRReviewAgent: prioritize review for PRs >5000 lines or >50 files, review critical paths (security, core logic, public APIs) with summary noting partial review and recommendations (AS-6)

**Checkpoint**: ✅ US3 complete - AI code review on PRs.

---

## Phase 8: User Story 12 - AI Context for Issues (P1)

**Goal**: Enable AI-aggregated context with related issues, docs, code, tasks, and Claude Code prompts
**Verify**: Open issue AI Context tab, see aggregated context, copy prompts, chat to refine

📄 **Task Details**: [P8-US12-T201-T215.md](tasks/P8-US12-T201-T215.md)

### Database Models

- [x] T201 [US12] Create AIContext SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/ai_context.py`
- [x] T202 [US12] Create migration for AIContext entity in `backend/alembic/versions/010_ai_context_entity.py`

### AI Agents (US12)

- [x] T203 [US12] Create AIContextAgent in `backend/src/pilot_space/ai/agents/ai_context_agent.py` using Claude Opus multi-turn
- [x] T204 [US12] Create CodeContextExtractor in `backend/src/pilot_space/ai/utils/code_context_extractor.py` for AST analysis
- [x] T205 [US12] Create AI context prompt template in `backend/src/pilot_space/ai/prompts/ai_context.py`

### Services

- [x] T206 [US12] Create GenerateAIContextService in `backend/src/pilot_space/application/services/ai/generate_ai_context_service.py`
- [x] T207 [US12] Create RefineAIContextService in `backend/src/pilot_space/application/services/ai/refine_ai_context_service.py` for chat refinement
- [x] T208 [US12] Create ExportAIContextService in `backend/src/pilot_space/application/services/ai/export_ai_context_service.py` for markdown export

### API Endpoints

- [x] T209 [US12] Create AI context schemas in `backend/src/pilot_space/api/v1/schemas/ai_context.py`
- [x] T210 [US12] Add AI context endpoints to issues router (get, regenerate, chat, export)

### Frontend: AI Context

- [x] T211 [US12] Create AIContext component in `frontend/src/components/issues/AIContext.tsx`
- [x] T212 [US12] Create ContextItemList component in `frontend/src/components/issues/ContextItemList.tsx`
- [x] T213 [US12] Create TaskChecklist component in `frontend/src/components/issues/TaskChecklist.tsx`
- [x] T214 [US12] Create ClaudeCodePrompt component in `frontend/src/components/issues/ClaudeCodePrompt.tsx` with copy button
- [x] T215 [US12] Create ContextChat component in `frontend/src/components/issues/ContextChat.tsx`

**Checkpoint**: ✅ US12 complete - AI context aggregation for issues.

---

## Phase Final: Polish

Cross-cutting concerns after all stories complete.

### Testing

- [x] T323 [P] Create backend test configuration in `backend/tests/conftest.py`
- [x] T324 [P] Create integration tests for auth in `backend/tests/integration/test_auth.py`
- [x] T325 [P] Create integration tests for notes in `backend/tests/integration/test_notes.py`
- [x] T326 [P] Create integration tests for issues in `backend/tests/integration/test_issues.py`
- [x] T327 [P] Create frontend component tests for NoteCanvas in `frontend/src/components/editor/__tests__/NoteCanvas.test.tsx`
- [x] T328 [P] Create E2E tests for note workflow in `frontend/e2e/notes.spec.ts`
- [x] T329 [P] Create E2E tests for issue workflow in `frontend/e2e/issues.spec.ts`
- [x] T329a [P] Create E2E tests for PR review workflow in `frontend/e2e/pr-review.spec.ts`
- [x] T329b [P] Create E2E tests for cycle/sprint workflow in `frontend/e2e/cycles.spec.ts`
- [x] T329c [P] Create E2E tests for AI context workflow in `frontend/e2e/ai-context.spec.ts`
- [x] T329d [P] Create E2E tests for GitHub integration in `frontend/e2e/github.spec.ts`

### Documentation

- [x] T330 [P] Update API documentation with OpenAPI in `backend/src/pilot_space/main.py`: enable FastAPI automatic OpenAPI generation, add schema validation to CI (`openapi-spec-validator`), verify all endpoints have Pydantic schemas, generate `specs/001-pilot-space-mvp/contracts/openapi.yaml`
- [x] T331 [P] Create developer setup guide in `docs/DEVELOPER_SETUP.md`
- [x] T332 [P] Validate quickstart.md against actual setup process

### Performance Optimization

- [x] T333 Optimize note canvas rendering for 1000+ blocks with virtualization: **performance test for 5000+ blocks** (spec.md edge case), use @tanstack/react-virtual with dynamic row heights, scroll position preservation, add performance regression test in `frontend/e2e/performance/note-canvas-perf.spec.ts`
- [x] T334 Add Redis caching for AI responses in `backend/src/pilot_space/infrastructure/cache/ai_cache.py`
- [x] T335 Add database query optimization (eager loading, N+1 prevention)

### Security Hardening

- [x] T336 Audit RLS policies for all tables
- [x] T337 Audit rate limiting configuration and verify NFR-019 compliance (1000 req/min standard, 100 req/min AI) *(Implementation in T048a)*

### Infrastructure & Deployment (NFR-011 to NFR-018)

- [x] T338 [P] Create Kubernetes manifests in `infra/k8s/` for backend and frontend deployments (NFR-011, NFR-012)
- [x] T339 [P] Create Terraform modules in `infra/terraform/` for Supabase project provisioning (NFR-013)
- [x] T340 Configure health check endpoints in `backend/src/pilot_space/api/v1/routers/health.py` (NFR-017)
- [x] T341 [P] Create environment configuration templates for dev/staging/production (NFR-016)

### Backup & Recovery (NFR-003, NFR-004)

- [x] T342 Create backup script in `scripts/backup.sh` using Supabase CLI for daily backups (NFR-003)
- [x] T343 Document failover procedure in `docs/DISASTER_RECOVERY.md` for AZ failover (NFR-004)

### Accessibility Implementation (NFR-008 to NFR-010)

- [x] T344 [P] Add axe-core accessibility tests to `frontend/e2e/accessibility.spec.ts` (NFR-008)
- [x] T345 [P] Create keyboard navigation tests in `frontend/e2e/keyboard-navigation.spec.ts` (NFR-009)
- [x] T346 [P] Add screen reader ARIA audit checklist in `docs/ARIA_AUDIT.md` (NFR-010)

### Human-in-the-Loop (FR-032, Constitution Principle I)

- [x] T354 Create ApprovalDialog component in `frontend/src/components/ai/ApprovalDialog.tsx` for confirming AI create/modify/delete actions (FR-032, Constitution I)
- [x] T355 Create useApprovalFlow hook in `frontend/src/hooks/useApprovalFlow.ts` to integrate with ApprovalFlowService (T129a)
- [x] T356 Add approval integration to IssueCreateModal, IssueExtractionPanel, and AI Context regenerate actions

### Data Export/Import (FR-065, FR-094)

- [x] T357 Create JSON schema definitions in `backend/src/pilot_space/schemas/export_schema.json` for workspace backup format validation. Schema includes: version, workspace metadata, projects array, issues array, notes array, cycles array, labels array, members array (roles only, no passwords). Validates structure before import.
- [x] T358 Create ExportWorkspaceService in `backend/src/pilot_space/application/services/workspace/export_workspace_service.py` generating ZIP archive with structured JSON. Structure: `workspace.json` (metadata), `projects/{id}.json`, `issues/{id}.json`, `notes/{id}.json`. Excludes: API keys, tokens, embeddings. Includes: activity logs, attachments manifest.
- [x] T359 Create ImportWorkspaceService in `backend/src/pilot_space/application/services/workspace/import_workspace_service.py` with schema validation and conflict resolution. Strategies: skip_existing, overwrite, rename. Validates foreign key integrity. Re-generates UUIDs on import. Transaction-safe rollback on failure.
- [x] T360 Add export/import endpoints to workspaces router: `GET /api/v1/workspaces/{id}/export` (returns ZIP download), `POST /api/v1/workspaces/{id}/import` (multipart upload). Admin-only permissions. Progress tracking via SSE for large imports.

### Explicitly Deferred (Post-MVP)

| Requirement | Description | Target Phase |
|-------------|-------------|--------------|
| FR-109 | ClamAV malware scanning for uploads | Enterprise (Phase 3+) |

**Checkpoint**: ✅ Polish complete - MVP ready for deployment.

---

## Dependencies

### Phase Order (MVP)

```
Setup (T001-T023) → Foundational (T024-T067) → User Stories (T068-T215) → Polish (T323-T337)
```

### Critical Path (MVP)

```
T001-T023 (Setup)
    ↓
T024-T067 (Foundation - DB, Auth, API base)
    ↓
T068-T117 (US1: Notes) ────────────────────┐
    ↓                                       │
T118-T154 (US2: Issues) ◄──────────────────┤
    ↓                                       │
T155-T171 (US4: Cycles) ◄──────────────────┤
    │                                       │
    ├──► T172-T192 (US18: GitHub) ─────────┤
    │         ↓                             │
    │    T193-T200 (US3: PR Review) ◄──────┤
    │                                       │
    └──► T201-T215 (US12: AI Context) ◄────┘
              ↓
    MVP Complete → Phase 2/3 can start
```

### User Story Dependencies (MVP)

| Story | Depends On | Can Run After |
|-------|------------|---------------|
| US1 | Foundation | T067 |
| US2 | US1 (Note-to-Issue extraction) | T117 |
| US4 | US2 (Issues exist) | T154 |
| US18 | US2 (Issues to link) | T154 |
| US3 | US18 (GitHub connected) | T192 |
| US12 | US2, US18 | T192 |

**Future phases**: See [Phase 2 tasks](../002-pilot-space-phase2/tasks.md) and [Phase 3 tasks](../003-pilot-space-phase3/tasks.md)

### Parallel Opportunities by Phase

**Phase 2 (Foundational)**:
```bash
# Can run in parallel:
T037 UserRepository || T038 WorkspaceRepository || T039 ProjectRepository
T057 RootStore || T058 AuthStore || T059 WorkspaceStore || T060 UIStore
```

**Phase 3 (US1)**:
```bash
# Can run in parallel:
T074 NoteRepository || T075 NoteAnnotationRepository || T076 DiscussionRepository
T088 margin_annotation.py || T089 issue_extraction.py
T102 CodeBlockExtension || T103 MentionExtension || T104 SlashCommandExtension
```

**Phase 4 (US2)**:
```bash
# Can run in parallel:
T122 IssueRepository || T123 ActivityRepository || T124 LabelRepository
T133 issue_enhancement.py || T134 duplicate_detection.py
```

---

## Implementation Strategy

### MVP First (Recommended)

1. Setup (T001-T023) → Foundation (T024-T067) → US1 Notes (T068-T117)
2. Validate: Note canvas functional with ghost text, annotations
3. US2 Issues (T118-T154) → Validate: AI-enhanced issue creation
4. Deploy MVP for early feedback

### Incremental (After MVP)

1. Add US4 Cycles → test → deploy
2. Add US18 GitHub → US3 PR Review → test → deploy
3. Add US12 AI Context → test → deploy
4. Continue with P2/P3 stories per priority

### Parallel Team Strategy

| Team | Stories | Estimated Tasks |
|------|---------|-----------------|
| Backend Core | Foundation, US1, US2 services | T024-T067, T068-T144 |
| Frontend Core | US1, US2 components | T097-T117, T145-T154 |
| AI/ML | All AI agents | T083-T091, T130-T139, T193-T208 |
| Integrations | US18, US3, US9 | T172-T200, T285-T292 |
| Platform | US10, US11, US16 | T297-T322 |

---

## Deferred Requirements (Phase 2)

The following functional requirements have data model foundations in MVP but full implementation is deferred to Phase 2:

| FR | Description | MVP Foundation | Phase 2 Reference |
|----|-------------|----------------|-------------------|
| FR-025 | AI task decomposition | Template model (T068) | TaskDecomposerAgent in Phase 2 US-05 |
| FR-028 | AI documentation generation | Page model in migration (T073) | DocumentGeneratorAgent in Phase 2 US-06 |
| FR-029 | Diagram generation (Mermaid) | TipTap base config (T098) | DiagramGeneratorAgent in Phase 2 US-06 |
| FR-030 | AI content origin tracking | ai_metadata JSONB on Issue (T118) | Provenance UI in Phase 2 |
| FR-031 | AI content labeling UI | ai_metadata JSONB on Issue (T118) | Content Labels in Phase 2 |

*See `specs/002-pilot-space-phase2/tasks.md` for full task definitions.*

---

## Validation Checklist

- [x] 6 MVP user stories from spec.md have corresponding phases (US1-4, US12, US18)
- [x] 21 entities from data-model.md have creation tasks
- [x] All endpoints from contracts/ have implementation tasks
- [x] No circular dependencies between tasks
- [x] Each story phase has checkpoint statement
- [x] Task IDs are sequential (T001-T215 for MVP + T323-T360 for Polish + Cross-cutting)
- [x] [P] markers correctly identify parallelizable work
- [x] File paths match plan.md project structure
- [x] P2/P3 tasks migrated to separate phase files

---

## Summary (MVP)

| Metric | Count |
|--------|-------|
| Total MVP Tasks | 271 |
| Setup Phase | 23 |
| Foundational Phase | 49 |
| User Story Phases (P0+P1) | 170 |
| Polish + Cross-cutting Phase | 29 |
| Parallel Opportunities | ~55 tasks marked [P] |
| Critical Path Length | ~105 tasks |

**MVP Scope**: T001-T215 + T323-T360 = 271 tasks

*Task counts include sub-tasks (e.g., T091f, T112a-c, T117a, T129b-d, T154a-i, T184a, T189a-b, T200a-e, T354-T360).*

**New Tasks Added (Analysis Remediation v3)**:
- T091f: ConversationAgent for multi-turn discussions (M-05)
- T112a-c: Note pinning (H-02)
- T117a: Issue sync Realtime listener (M-04)
- T129b-d: Activity logging (H-01)
- T154e-g: RelatedIssuesAgent, context menu (C-02)
- T154h-i: BulkIssueSummaryAgent (M-01)
- T184a: Scheduled commit scanner (M-06)
- T189a-b: Branch suggestion API (H-03)
- T200e: Large PR handling (C-01)
- T354-T356: Human-in-the-loop UI
- T357-T360: Data export/import with detailed ACs (M-07)

**Future Phases**:
- Phase 2 (P2): 81 tasks → [Phase 2 tasks](../002-pilot-space-phase2/tasks.md)
- Phase 3 (P3): 26 tasks → [Phase 3 tasks](../003-pilot-space-phase3/tasks.md)
- **Total (All Phases)**: 352 tasks
