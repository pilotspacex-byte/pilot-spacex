# Implementation Plan: v1.0-beta — Team-Ready AI Workspace

**Feature**: v1.0-beta — Team-Ready AI Workspace
**Branch**: `021-v1-beta`
**Spec**: `specs/021-v1-beta-close-the-loop/spec.md`
**Created**: 2026-02-28
**Author**: Tin Dang

---

## Summary

Make Pilot Space viable for daily team use by activating dead code, connecting existing infrastructure, and building two new full-stack features (Modules CRUD + Notification Pipeline). 12 stories across 4 sprints, organized into 4 pillars: Find Anything, Organize at Scale, Stay Informed, Complete the Workflow.

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | Python 3.12+, TypeScript 5.3+ |
| **Primary Dependencies** | FastAPI 0.110+, Next.js 16+, MobX 6+, TanStack Query 5+, TipTap 3.16+, shadcn/ui |
| **Storage** | PostgreSQL 16+ (pgvector), Redis 7, Meilisearch 1.6 |
| **Testing** | pytest + pytest-asyncio (backend), Vitest (frontend) |
| **Target Platform** | Web (browser, desktop-first) |
| **Performance Goals** | Search <500ms, Notifications <5s delivery, Export <3s |
| **Constraints** | RLS multi-tenant, 700-line file limit, >80% test coverage, Conventional Commits |
| **Scale/Scope** | 5-100 users per workspace, <10,000 items per workspace |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Language/Framework matches constitution mandates (Python 3.12+, Next.js 16+)
- [x] Database choice aligns (PostgreSQL 16+ — reuse existing models + new notifications table)
- [x] Auth approach follows requirements (Supabase Auth + RLS)
- [x] Architecture patterns match (CQRS-lite services, MobX+TanStack, shadcn/ui)

### Simplicity Gate

- [x] Using minimum services — no new microservices; extends existing routers and services
- [x] No future-proofing — activating built components, not building speculative features
- [x] No premature abstractions — following established Cycles CRUD pattern for Modules

### Quality Gate

- [x] Test strategy: unit tests for services/stores/components, >80% coverage
- [x] Type checking: pyright (backend), TypeScript strict (frontend)
- [x] File size limits: 700 lines max
- [x] Linting: ruff (backend), eslint (frontend)

---

## Requirements-to-Architecture Mapping

| FR ID | Requirement | Technical Approach | Components |
|-------|------------|-------------------|------------|
| FR-001 | Global search modal (Cmd+K) | Meilisearch backend endpoint + SearchModal component | `workspace_search.py`, `SearchModal.tsx`, `UIStore.ts` |
| FR-002 | Command palette (Cmd+P) | shadcn cmdk + command registry + context ordering | `CommandPalette.tsx`, `command-registry.ts`, `UIStore.ts` |
| FR-003 | Notes full-text search | Replace client-side filter with Meilisearch API call | `notes.ts` (API), notes list page |
| FR-004 | Keyboard shortcut guide | Overlay reading from command registry | `ShortcutGuide.tsx` |
| FR-005 | Modules page with CRUD | Follow Cycles pattern: router → service → repo → schema | Full stack (see S4 below) |
| FR-006 | Module assignment on issues | ModuleSelector component in property panel | `ModuleSelector.tsx`, issue detail page |
| FR-007 | TemplatePicker on new note | Mount existing component in sidebar + notes page | `sidebar.tsx`, notes page |
| FR-008 | Template editor for admins | Reuse note editor with save-as-template action | `TemplateEditor.tsx`, settings page |
| FR-009 | Notification delivery (<5s) | pgmq queue + SSE push + NotificationStore | Notification pipeline (see S7) |
| FR-010 | Notification persistence | New `notifications` table with RLS + priority enum | `notification.py` model, migration |
| FR-011 | Team activity on homepage | Extend homepage `/activity` endpoint for team members | `homepage.py`, `DailyBrief` component |
| FR-012 | Issue filter options | Pass workspace members + labels to FilterBar props | `IssueViewsRoot.tsx` |
| FR-013 | Markdown export | TipTap `tiptap-markdown` → download `.md` file | Note page `handleExport` |
| FR-014 | PDF export | Browser print-to-PDF (v1) | Note page `handleExport` |
| FR-015 | AI skill discoverability | Skills in command palette + slash menu + settings page | `command-registry.ts`, `SlashCommandExtension` |

---

## Sprint 0: Prerequisites (Meilisearch Indexing)

> **Must complete before Sprint 1 (note search) and Sprint 2 (global search) work.** Meilisearch client methods exist and the client is healthy, but no service ever calls `index_document()` — notes and issues are never indexed. Search returns empty results without this.

**What Exists**:
- `backend/src/pilot_space/infrastructure/search/meilisearch.py` — `index_document()`, `update_document()`, `delete_document()` all implemented
- 3 indexes configured: ISSUES, NOTES, PAGES
- Zero calls from any service to these methods

**What to Build**:
- Inject `MeilisearchClient` into note create/update/delete services → call `index_document(IndexName.NOTES, {...})` after DB commit
- Inject `MeilisearchClient` into issue create/update/delete services → call `index_document(IndexName.ISSUES, {...})` after DB commit
- Extract `content_text` from TipTap JSON (flatten text nodes) for note indexing

**Design Decision**: Index synchronously after DB commit (not via queue) — simpler, and indexing latency (<50ms) is acceptable within the service layer for v1.

**Key Files**:
| File | Action |
|------|--------|
| `backend/src/pilot_space/application/services/note/create_note_service.py` | Modify — add `index_document(NOTES, ...)` |
| `backend/src/pilot_space/application/services/note/update_note_service.py` | Modify — add `update_document(NOTES, ...)` |
| `backend/src/pilot_space/application/services/issue/create_issue_service.py` | Modify — add `index_document(ISSUES, ...)` |
| `backend/src/pilot_space/application/services/issue/update_issue_service.py` | Modify — add `update_document(ISSUES, ...)` |
| `backend/src/pilot_space/container/container.py` | Modify — inject MeilisearchClient into note/issue services |

---

## Sprint 1: Quick Wins + Foundation

### S5: Activate TemplatePicker (FR-007) — XS

**What Exists**:
- `frontend/src/features/notes/components/TemplatePicker.tsx` — 100% built, 4 SDLC templates, keyboard navigation, TanStack Query
- `frontend/src/components/layout/sidebar.tsx:309` — `handleNewNote` calls `createNote.mutate(createNoteDefaults())` directly

**What to Build**:
- Add state to sidebar: `showTemplatePicker` boolean
- `handleNewNote` → open TemplatePicker dialog instead of direct create
- TemplatePicker `onConfirm(template)` → `createNote.mutate({...template content})`; `onConfirm(null)` → blank note
- Same for "New Note" button on notes list page

**Design Decision**: Dialog overlay (not page navigation). User can Escape to cancel without creating anything.

**Key Files**:
| File | Action |
|------|--------|
| `frontend/src/components/layout/sidebar.tsx` | Modify — mount TemplatePicker, update `handleNewNote` |
| `frontend/src/features/notes/components/TemplatePicker.tsx` | Read-only — verify props interface |
| Notes list page (if separate "New Note" button exists) | Modify — same TemplatePicker mounting |

---

### S9: Wire Issue Filter Options (FR-012) — S

**What Exists**:
- `frontend/src/features/issues/components/views/FilterBar.tsx` — `assigneeOptions` and `labelOptions` props, both default to `[]`
- `frontend/src/features/issues/components/views/IssueViewsRoot.tsx` — passes no options to toolbar

**What to Build**:
- In `IssueViewsRoot`, read workspace members from `workspaceStore.currentMembers` → map to `assigneeOptions` format
- Fetch workspace labels (from existing labels API or TanStack query) → map to `labelOptions` format
- Pass both to the toolbar/filter bar component chain

**Key Files**:
| File | Action |
|------|--------|
| `frontend/src/features/issues/components/views/IssueViewsRoot.tsx` | Modify — pass options |
| `frontend/src/features/issues/components/views/FilterBar.tsx` | Read-only — verify option shape |
| `frontend/src/stores/WorkspaceStore.ts` | Read-only — verify `currentMembers` accessor |

---

### S12: Full-text Note Search (FR-003) — S

> **Prerequisite**: Sprint 0 T-P1 must complete first — notes are not currently indexed in Meilisearch.

**What Exists**:
- `backend/src/pilot_space/infrastructure/search/meilisearch.py` — `search_notes(query, workspace_id)` method
- `frontend/src/services/api/notes.ts` — notes API client
- Notes list page has a search box that filters client-side by title/topic

**What to Build**:
- Backend: Search endpoint already reachable via S1's `workspace_search.py` (shared), OR add `?search=` param to existing notes list endpoint that delegates to Meilisearch
- Frontend: Replace client-side `filter()` with API call using debounced search query
- Show content snippet highlights in search results

**Design Decision**: Add `search` query param to existing `GET /workspaces/{id}/notes` endpoint. When present, delegate to Meilisearch instead of DB query. This avoids a separate endpoint and maintains the existing notes list API contract.

**Key Files**:
| File | Action |
|------|--------|
| `backend/src/pilot_space/api/v1/routers/workspace_notes.py` | Modify — add `search` param, delegate to Meilisearch |
| `backend/src/pilot_space/infrastructure/search/meilisearch.py` | Read-only — use `search_notes()` |
| Frontend notes list page | Modify — debounced API call instead of client filter |

---

### S3: Keyboard Shortcut Guide (FR-004) — S

**What Exists**:
- Nothing — no component or data structure for shortcuts

**What to Build**:
- `ShortcutGuide.tsx` — overlay component showing categorized shortcuts
- Shortcut data sourced from S2's command registry (or inline if S2 not yet complete — Sprint 1 is parallel with Sprint 2)
- `?` keydown handler (only outside text inputs)
- Mount in workspace layout

**Design Decision**: Simple modal overlay. If S2 (command registry) is available, read from it. Otherwise, hardcode a static shortcut map that S2 will later extend.

**Key Files**:
| File | Action |
|------|--------|
| `frontend/src/features/command-palette/ShortcutGuide.tsx` | Create |
| Workspace layout component | Modify — mount ShortcutGuide + keydown listener |

---

## Sprint 2: Find Anything

### S1: Global Search Modal (FR-001) — M

> **Prerequisite**: Sprint 0 T-P2 must complete first — issues are not currently indexed in Meilisearch.

**What Exists**:
- `backend/src/pilot_space/infrastructure/search/meilisearch.py` — `search()`, `search_issues()`, `search_notes()` with workspace scoping
- `backend/src/pilot_space/infrastructure/search/config.py` — `IndexName` enum (ISSUES, NOTES, PAGES)
- `frontend/src/stores/UIStore.ts` — `searchModalOpen` with toggle/open/close
- No search API router. No frontend SearchModal component.

**What to Build**:
- **Backend**: `workspace_search.py` router — `GET /workspaces/{id}/search?q=&type=&limit=` → calls `MeilisearchClient.search()` with workspace filter → returns unified results with type badges
- **Frontend**: `SearchModal.tsx` using shadcn `Dialog` + cmdk or custom input — recent items on empty query, live results on typing, type filter tabs, preview on Tab, navigate on Enter
- **Frontend**: `search-api.ts` — typed API client wrapping the search endpoint
- **Frontend**: Global `Cmd+K` keydown handler in workspace layout (or via `UIStore`)

**Design Decision**: Unified endpoint returns all types with `type` discriminator. Frontend filters client-side by tab. Server-side limit per type (default 5 per type, 20 total). Fallback: if Meilisearch unhealthy, return empty with error message (no client-side search fallback for global search — S12 handles notes-specific fallback).

**Key Files**:
| File | Action |
|------|--------|
| `backend/src/pilot_space/api/v1/routers/workspace_search.py` | Create — search endpoint |
| `backend/src/pilot_space/main.py` | Modify — mount search router |
| `frontend/src/features/search/SearchModal.tsx` | Create — modal component |
| `frontend/src/features/search/search-api.ts` | Create — API client |
| `frontend/src/stores/UIStore.ts` | Modify — Cmd+K handler |
| Workspace layout | Modify — mount SearchModal, keybinding |

---

### S2: Command Palette (FR-002) — M

**What Exists**:
- `frontend/src/stores/UIStore.ts` — `commandPaletteOpen` with toggle/open/close
- `frontend/src/components/ui/command.tsx` — shadcn cmdk wrapper (`CommandDialog`, `CommandInput`, `CommandList`, `CommandGroup`, `CommandItem`)
- 24 AI skill YAML definitions in `backend/.claude/skills/`

**What to Build**:
- **`command-registry.ts`** — static registry of commands grouped by category:
  - Navigation: all workspace routes (Notes, Issues, Cycles, Projects, Modules, Settings, etc.)
  - AI Skills: 24 skills parsed from YAML or hardcoded with name + description + trigger
  - Editor Actions: bold, italic, heading, list (only shown when in editor context)
  - Settings: theme, shortcuts, notifications
  Each command: `{ id, label, description, category, shortcut?, icon?, action: () => void }`
- **`CommandPalette.tsx`** — uses shadcn `CommandDialog`, reads `UIStore.commandPaletteOpen`, renders grouped commands, fuzzy search via cmdk built-in
- **Cmd+P** keydown handler
- **Context-aware ordering**: if current route is note editor, Editor Actions first; if homepage, Navigation first

**Design Decision**: Static registry (not dynamic). Skills list is hardcoded from known skill names — no runtime YAML parsing in frontend. Command actions use `router.push()` for navigation; AI skills use `pilotSpaceStore.setActiveSkill(skillName)` (at `frontend/src/stores/ai/PilotSpaceStore.ts:581`) then `router.push(`/${workspaceSlug}/chat`)` — **not** `chatStore.setInput()` which does not exist.

**Key Files**:
| File | Action |
|------|--------|
| `frontend/src/features/command-palette/CommandPalette.tsx` | Create |
| `frontend/src/features/command-palette/command-registry.ts` | Create |
| `frontend/src/stores/UIStore.ts` | Modify — Cmd+P handler |
| Workspace layout | Modify — mount CommandPalette |

---

### S10: Note Export (FR-013, FR-014) — M

**What Exists**:
- `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx:294` — `handleExport` is empty stub (`// Export functionality - to be implemented`)
- `frontend/src/components/editor/RichNoteHeader.tsx` — `onExport` prop wired to a dropdown menu item
- TipTap `tiptap-markdown` extension provides `editor.storage.markdown.getMarkdown()`
- Issue detail page already has a working export system (`clone-context-panel.tsx` with `ExportFormat`)

**What to Build**:
- **Markdown export**: `handleExport` → get editor instance → `editor.storage.markdown.getMarkdown()` → create Blob → trigger download as `{note-title}.md`
- **PDF export**: Open browser print dialog with print-optimized CSS (v1 — no server-side PDF generation)
- **Export dropdown**: Replace single `onExport` callback with dropdown offering "Download Markdown" and "Print / Save as PDF"
- Handle inline issue badges: convert `[PS-42]` nodes to text in Markdown output

**Design Decision**: Markdown via TipTap's built-in converter. PDF via `window.print()` with `@media print` styles. No server-side PDF generation in v1. The existing `RichNoteHeader` dropdown structure supports multiple export options — extend it.

**Key Files**:
| File | Action |
|------|--------|
| `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx` | Modify — implement `handleExport` |
| `frontend/src/components/editor/RichNoteHeader.tsx` | Modify — export dropdown with Markdown + PDF options |
| `frontend/src/components/editor/NoteCanvasEditor.tsx` | Read-only — verify editor ref access |

---

## Sprint 3: Organize & Communicate

### S4: Modules/Epics (FR-005, FR-006) — L

**What Exists**:
- `backend/src/pilot_space/infrastructure/database/models/module.py` — SQLAlchemy model: name, description, status (PLANNED/ACTIVE/COMPLETED/CANCELLED), target_date, lead_id, sort_order, project_id FK
- Issue model has `module_id` FK with index
- Migration `003` + `013` created the table
- No router, service, repository, schema, or frontend page

**What to Build (Backend)**:
Follow the Cycles CRUD pattern exactly:

1. **Repository**: `module_repository.py` — `BaseRepository[Module]`, `ModuleFilters` dataclass, cursor pagination, `selectinload` for project/lead/issues relationships
2. **Services**: `create_module_service.py`, `update_module_service.py`, `delete_module_service.py`, `list_modules_service.py`, `get_module_service.py` — each with `@dataclass` Payload/Result + `execute()` async
3. **Schemas**: `module.py` — `ModuleCreate`, `ModuleUpdate`, `ModuleResponse` (with `from_module()` factory), `ModuleListResponse`
4. **Router**: `workspace_modules.py` — CRUD endpoints at `/workspaces/{id}/modules`, workspace-scoped
5. **DI wiring**: Register repository + services in `container.py`, create typed deps in `deps.py`
6. **Progress calculation**: Service computes `% done issues` by querying issue states for the module

**What to Build (Frontend)**:
1. **API client**: `frontend/src/services/api/modules.ts` — list, get, create, update, delete
2. **Page route**: `frontend/src/app/(workspace)/[workspaceSlug]/modules/page.tsx`
3. **Module list**: Cards with name, lead avatar, issue count, progress bar, target date, status badge
4. **Module detail**: Filtered issue list for the module, module metadata, edit form
5. **ModuleSelector**: Searchable dropdown component for issue detail property panel (same pattern as CycleSelector)
6. **Sidebar**: Add "Modules" nav item

**Design Decision**: No new migration needed — table already exists. Progress = `count(issues where state='done') / count(all issues)` for the module. ModuleSelector follows CycleSelector pattern exactly.

**Key Files**:
| File | Action |
|------|--------|
| `backend/src/pilot_space/infrastructure/database/repositories/module_repository.py` | Create |
| `backend/src/pilot_space/application/services/module/` | Create (5 service files) |
| `backend/src/pilot_space/api/v1/schemas/module.py` | Create |
| `backend/src/pilot_space/api/v1/routers/workspace_modules.py` | Create |
| `backend/src/pilot_space/container/container.py` | Modify — register module deps |
| `backend/src/pilot_space/main.py` | Modify — mount modules router |
| `frontend/src/services/api/modules.ts` | Create |
| `frontend/src/app/(workspace)/[workspaceSlug]/modules/page.tsx` | Create |
| `frontend/src/features/modules/` | Create (list, detail, store components) |
| `frontend/src/components/layout/sidebar.tsx` | Modify — add Modules nav |
| Issue detail page property panel | Modify — add ModuleSelector |

**Pattern Reference**: `workspace_cycles.py` (router), `cycle/` (services), `cycle_repository.py` (repo), `cycle.py` (schema)

---

### S7: Notification Pipeline (FR-009, FR-010) — L

**What Exists**:
- `frontend/src/stores/NotificationStore.ts` — full MobX store with `addNotification()`, `markAsRead()`, priority badges, bell icon — `addNotification()` called by zero code paths
- `backend/src/pilot_space/infrastructure/queue/supabase_queue.py` — `QueueName.NOTIFICATIONS`, `enqueue_notification(user_id, notification_type, data)` — never called
- `backend/src/pilot_space/api/v1/streaming.py` — `format_sse_event()` helper
- No `notifications` database table, no notification router, no worker

**What to Build (Backend)**:

1. **Model**: `notification.py` — `Notification` SQLAlchemy model: id, workspace_id, user_id, type (enum: COMMENT, ASSIGNMENT, STATE_CHANGE, MENTION, PR_REVIEW), title, description, priority (URGENT/IMPORTANT/FYI), source_type, source_id, is_read, created_at
2. **Migration**: `051_notifications.py` — CREATE TABLE + RLS policies (user can only read own notifications within workspace). Also include `notification_preferences` table: `(user_id UUID, workspace_id UUID, notification_type VARCHAR, enabled BOOLEAN DEFAULT true, PRIMARY KEY (user_id, workspace_id, notification_type))` with same RLS. **051** is the next sequential number after current highest `050_add_chat_attachments_cleanup_cron.py`.
3. **Repository**: `notification_repository.py` — list (paginated, unread filter), mark_read, mark_all_read, count_unread
4. **Services**: `create_notification_service.py`, `list_notifications_service.py`, `mark_read_service.py`
5. **Router**: `workspace_notifications.py` — `GET /` (list), `GET /unread-count`, `PATCH /{id}/read`, `POST /mark-all-read`, `GET /stream` (SSE)
6. **Event source hooks**: Add `enqueue_notification()` calls in:
   - Comment creation service → notify issue assignees
   - Issue assignment service → notify assigned user
   - Issue state change service → notify watchers
   - PR review handler → notify PR author
7. **Worker**: Process notification queue → persist to DB + SSE push
8. **SSE channel**: Use existing `StreamingResponse` pattern — notification SSE endpoint per user

**What to Build (Frontend)**:
1. Connect `NotificationStore` to `GET /notifications` API on mount
2. Subscribe to notification SSE for real-time delivery: `source.onerror = () => { source.close(); setTimeout(() => this.subscribeToSSE(), 5000); }` — 5s reconnect on disconnect
3. Wire the existing bell icon + notification panel to live data
4. **Notification preferences settings page** (`settings/notifications/page.tsx`) — per-type toggle list; `NotificationStore` fetches preferences on init

**Design Decision**: Reuse existing SSE infrastructure (not WebSocket). Notification worker is a pgmq consumer following the `pr_review_handler.py` pattern. Priority classification is set at creation time based on notification type (ASSIGNMENT → IMPORTANT, COMMENT → FYI, etc.). No Supabase Realtime — use SSE polling + queue.

**Key Files**:
| File | Action |
|------|--------|
| `backend/src/pilot_space/infrastructure/database/models/notification.py` | Create |
| `backend/alembic/versions/051_notifications.py` | Create — next after 050 |
| `backend/src/pilot_space/infrastructure/database/repositories/notification_repository.py` | Create |
| `backend/src/pilot_space/application/services/notification/` | Create (5 services incl. preferences) |
| `backend/src/pilot_space/api/v1/routers/workspace_notifications.py` | Create |
| `backend/src/pilot_space/api/v1/schemas/notification.py` | Create |
| `backend/src/pilot_space/infrastructure/queue/handlers/notification_handler.py` | Create |
| `backend/src/pilot_space/container/container.py` | Modify — register notification deps |
| `backend/src/pilot_space/main.py` | Modify — mount notifications router |
| Comment/assignment/state-change services | Modify — add `enqueue_notification()` calls |
| `frontend/src/stores/NotificationStore.ts` | Modify — connect to API + SSE + preferences |
| `frontend/src/services/api/notifications.ts` | Create |
| `frontend/src/app/(workspace)/[workspaceSlug]/settings/notifications/page.tsx` | Create — preferences toggles |

---

### S6: Template Editor (FR-008) — M

**What Exists**:
- `backend/src/pilot_space/api/v1/routers/note_templates.py` — full CRUD backend
- `frontend/src/services/api/templates.ts` — frontend API client
- `frontend/src/features/notes/components/TemplatePicker.tsx` — "Create Template" card has empty stub

**What to Build**:
- Template editor page: reuse `NoteCanvasEditor` with a "Save as Template" action instead of normal auto-save
- Settings/Templates management page: list all system + custom templates, edit/delete custom ones
- Wire "Create Template" in TemplatePicker to navigate to template editor

**Design Decision**: Template editor IS the note editor with modified save behavior. Content stored as TipTap JSON (same as notes). No special template fields in v1 — just a name, description, and content.

**Key Files**:
| File | Action |
|------|--------|
| `frontend/src/app/(workspace)/[workspaceSlug]/settings/templates/page.tsx` | Create |
| `frontend/src/features/notes/components/TemplatePicker.tsx` | Modify — wire "Create Template" |
| `frontend/src/features/notes/components/TemplateEditor.tsx` | Create — editor with save-as-template |

---

## Sprint 4: Team Awareness + Polish

### S8: Team Activity Feed (FR-011) — M

**What Exists**:
- `backend/src/pilot_space/api/v1/routers/homepage.py` — `GET /activity` returns personal notes + issues grouped by today/yesterday/this_week
- `backend/src/pilot_space/infrastructure/database/models/activity.py` — Activity model, 25+ ActivityType values, issue-scoped
- Frontend homepage `DailyBrief` component

**What to Build**:
- **Backend**: Extend `GET /activity` (or add `GET /activity/team`) to include activities by other workspace members. Add `actor_id` + `actor_name` + `actor_avatar` to response.
- **Frontend**: Add "Team Activity" section to DailyBrief showing attributed actions: "[Avatar] Alice moved PS-42 to In Review — 1h ago"
- Hide section when empty

**Key Files**:
| File | Action |
|------|--------|
| `backend/src/pilot_space/api/v1/routers/homepage.py` | Modify — extend activity query |
| `backend/src/pilot_space/api/v1/schemas/homepage.py` | Modify — add actor fields |
| Frontend homepage DailyBrief component | Modify — add Team Activity section |

---

### S11: AI Skill Discoverability (FR-015) — M

**What Exists**:
- `SkillMenu` triggered by `\` in chat input
- `SlashCommandExtension` in note editor with slash command menu
- 24 skill YAML definitions
- S2's command palette (by Sprint 4, S2 is complete)

**What to Build**:
- Add "AI Skills" category to command registry (S2) with all 24 skills
- Add "AI Actions" group to note editor slash menu with editor-relevant skills (extract-issues, improve-writing, summarize, generate-diagram)
- Enhance Settings/Skills page to show all skills with descriptions, trigger commands, and approval requirements

**Key Files**:
| File | Action |
|------|--------|
| `frontend/src/features/command-palette/command-registry.ts` | Modify — add AI skills category |
| Note editor SlashCommandExtension | Modify — add AI actions group |
| `frontend/src/app/(workspace)/[workspaceSlug]/settings/skills/page.tsx` | Modify — enhance skill browser |

---

## Cross-Cutting Concerns

### RLS Policies

Only S7 (Notifications) requires a new table with RLS:
- `notifications` table: users can only read/update their own notifications within their workspace
- Policy: `workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = current_setting('app.current_user_id')::uuid) AND user_id = current_setting('app.current_user_id')::uuid`
- Service-role bypass for notification worker

Modules table already has RLS from migration `003`/`013`.

### DI Container Wiring

Two new service groups to register in `container.py`:
1. **Module**: ModuleRepository + 5 CRUD services
2. **Notification**: NotificationRepository + 3 services + NotificationHandler

Follow existing pattern: repository in InfraContainer, services in AppContainer, typed deps in `deps.py`.

### Test Strategy

| Story | Backend Tests | Frontend Tests |
|-------|--------------|----------------|
| S1 | Search endpoint unit + integration | SearchModal component tests |
| S2 | — | CommandPalette + registry tests |
| S3 | — | ShortcutGuide render test |
| S4 | Module CRUD service + repository tests | Module page + selector tests |
| S5 | — | TemplatePicker mounting test |
| S6 | — | TemplateEditor save test |
| S7 | Notification service + handler + API tests | NotificationStore connection test |
| S8 | Activity endpoint team filter test | Team Activity section test |
| S9 | — | FilterBar with populated options test |
| S10 | — | Export download test |
| S11 | — | Command palette AI skills test |
| S12 | Search delegation test | Notes list search test |

### Migration Strategy

- **S4 (Modules)**: No new migration — table already exists
- **S7 (Notifications)**: New migration `051_notifications.py`. Verify chain: `cd backend && alembic heads` → single head. Current highest is `050_add_chat_attachments_cleanup_cron.py` → next is **051**.
- All other stories: no migrations

---

## Verification Plan

### Per-Sprint Verification

**Sprint 1**:
1. Click "New Note" in sidebar → TemplatePicker opens → select Sprint Planning → note created with template
2. Open Issues → Assignee filter dropdown shows workspace members → Label dropdown shows labels
3. Search notes by body content → results include content snippets
4. Press `?` outside text input → shortcut guide overlay appears

**Sprint 2**:
1. Press Cmd+K → SearchModal opens → type query → results from notes, issues, projects
2. Press Cmd+P → CommandPalette opens → navigate to "Extract Issues" skill → chat input pre-filled
3. Open note → Export → Markdown → `.md` file downloads with correct formatting
4. Open note → Export → PDF → print dialog opens

**Sprint 3**:
1. Create module → assign issues → progress bar shows % done
2. Open issue detail → Module property → select module from dropdown
3. Comment on issue → assignee receives notification within 5s → bell shows count
4. Click notification → navigate to source → marked as read
5. Create Template → save → appears in TemplatePicker

**Sprint 4**:
1. Homepage shows "Team Activity" with teammate actions + avatars
2. Cmd+P → "AI Skills" group shows 24 skills with descriptions
3. Note editor `/` → "AI Actions" group shows extract-issues, improve-writing, etc.
4. Full workflow: Create note from template → extract issues → assign to module → receive notification → export note as Markdown

### Quality Gates

```bash
# Backend
cd backend && uv run pyright && uv run ruff check && uv run pytest --cov=.

# Frontend
cd frontend && pnpm lint && pnpm type-check && pnpm test
```

Coverage must remain >80% after each sprint.
