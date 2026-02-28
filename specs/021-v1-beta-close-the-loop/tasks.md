# Task Breakdown: v1.0-beta — Team-Ready AI Workspace

**Plan**: `specs/021-v1-beta-close-the-loop/plan.md`
**Branch**: `021-v1-beta`
**Created**: 2026-02-28
**Author**: Tin Dang

---

## Task Summary

| Sprint | Tasks | Type | Effort |
|--------|-------|------|--------|
| 0: Prerequisites | T-P1, T-P2 | Meilisearch indexing hooks — must complete before S1/S12 work | 0.5 week |
| 1: Quick Wins + Foundation | T-001 to T-008 | Activate dead code, wire props, connect Meilisearch | 1 week |
| 2: Find Anything | T-009 to T-021 | New components + backend endpoint + export | 2 weeks |
| 3: Organize & Communicate | T-022 to T-042 | Full-stack CRUD (Modules) + Notification pipeline + Template editor | 2 weeks |
| 3b: Notification Preferences | T-041b | Notification preferences table + settings UI (FR-010) | 0.5 week |
| 4: Team Awareness + Polish | T-043 to T-051 | Extend homepage, skill discoverability, E2E | 1 week |

**Total**: 56 tasks, ~6 weeks. Sprint 0 must complete before Sprint 1/2 search tasks. Sprint 1 and Sprint 2 otherwise run in parallel.

---

## Sprint 0: Prerequisites (Meilisearch Indexing)

> **Required before S1 (global search) and S12 (note search) work.** Meilisearch is deployed and client methods exist but no service calls them — notes and issues are never indexed. Search returns empty results without this.

### T-P1: Wire Meilisearch indexing on note create/update (Prereq for S12)

**Type**: Backend wiring | **Scope**: Backend | **Effort**: S

**Steps**:
1. Read `backend/src/pilot_space/application/services/note/create_note_service.py` and `update_note_service.py`
2. Inject `MeilisearchClient` via DI into both services (add to container)
3. After successful DB commit in `create_note_service.execute()`, call: `await meilisearch.index_document(IndexName.NOTES, { id, title, content_text, topics, workspace_id, project_id, created_at })`
4. After successful DB commit in `update_note_service.execute()`, call: `await meilisearch.update_document(IndexName.NOTES, note_id, {...updated fields})`
5. On note delete: call `await meilisearch.delete_document(IndexName.NOTES, note_id)`
6. Extract `content_text` from TipTap JSON content (flatten all text nodes) for indexing
7. Write unit tests — verify indexing called on create/update/delete

**Files**:
- `backend/src/pilot_space/application/services/note/create_note_service.py` (modify)
- `backend/src/pilot_space/application/services/note/update_note_service.py` (modify)
- `backend/src/pilot_space/infrastructure/search/meilisearch.py` (read-only — use `index_document()`)
- `backend/src/pilot_space/container/container.py` (modify — inject MeilisearchClient into note services)

**Blocked-by**: None
**Acceptance**: Creating a note → note appears in Meilisearch notes index. Updating title → index updated. Deleting → removed from index.

---

### T-P2: Wire Meilisearch indexing on issue create/update (Prereq for S1)

**Type**: Backend wiring | **Scope**: Backend | **Effort**: S

**Steps**:
1. Read `backend/src/pilot_space/application/services/issue/create_issue_service.py` and `update_issue_service.py`
2. Inject `MeilisearchClient` via DI into both services
3. After successful DB commit, call: `await meilisearch.index_document(IndexName.ISSUES, { id, identifier, title, description, state, priority, workspace_id, project_id })`
4. After update, call `await meilisearch.update_document(IndexName.ISSUES, issue_id, {...})`
5. On issue delete: call `await meilisearch.delete_document(IndexName.ISSUES, issue_id)`
6. Write unit tests

**Files**:
- `backend/src/pilot_space/application/services/issue/create_issue_service.py` (modify)
- `backend/src/pilot_space/application/services/issue/update_issue_service.py` (modify)
- `backend/src/pilot_space/container/container.py` (modify)

**Blocked-by**: None
**Acceptance**: Creating an issue → issue appears in Meilisearch issues index. State change → index updated.

---

## Sprint 1: Quick Wins + Foundation

### T-001: Mount TemplatePicker in sidebar "New Note" flow (S5)

**Type**: Activation | **Scope**: Frontend | **Effort**: XS

**Steps**:
1. Read `frontend/src/features/notes/components/TemplatePicker.tsx` — verify props: `{ workspaceId, isAdmin, onConfirm, onClose, onCreateTemplate? }`
2. In `frontend/src/components/layout/sidebar.tsx`, add `useState` for `showTemplatePicker`
3. Change `handleNewNote` (L309) from `createNote.mutate(createNoteDefaults())` to `setShowTemplatePicker(true)`
4. Render `<TemplatePicker>` dialog:
   - `onConfirm(template: NoteTemplate)` → `createNote.mutate({ content: template.content, title: template.name })`
   - `onConfirm(null)` → `createNote.mutate(createNoteDefaults())` (blank note)
   - `template.content` is TipTap JSON (`{ type: 'doc', content: [...] }`) — matches `CreateNoteData.content: dict`
5. `onClose` → `setShowTemplatePicker(false)`
6. Add `onCreateTemplate` prop handler: `() => { setShowTemplatePicker(false); router.push(`/${workspaceSlug}/settings/templates`) }` — wires the currently-stub "Create Template" card to navigate to template settings

**Files**:
- `frontend/src/components/layout/sidebar.tsx` (modify)
- `frontend/src/features/notes/components/TemplatePicker.tsx` (modify — add `onCreateTemplate?: () => void` prop, wire Create Template card onClick)

**Blocked-by**: None
**Acceptance**: Click "New Note" → TemplatePicker opens → select template → note created with template content. Select "Blank" → empty note. Click "Create Template" → navigates to `/settings/templates`.

---

### T-002: Mount TemplatePicker in notes list page "New Note" button (S5)

**Type**: Activation | **Scope**: Frontend | **Effort**: XS

**Steps**:
1. Find the "New Note" button in the notes list page
2. Apply same TemplatePicker dialog pattern as T-001
3. Share TemplatePicker state via a custom hook if both callsites exist in different components

**Files**:
- Notes list page component (modify)

**Blocked-by**: T-001
**Acceptance**: Click "New Note" on notes list page → TemplatePicker opens.

---

### T-003: Wire assignee options to FilterBar (S9)

**Type**: Wiring | **Scope**: Frontend | **Effort**: XS

**Steps**:
1. Read `frontend/src/features/issues/components/views/IssueViewsRoot.tsx` — find where FilterBar/IssueToolbar is rendered
2. Read `frontend/src/stores/WorkspaceStore.ts` — verify `currentMembers` accessor returns `{ id, name, avatar }[]`
3. Map `currentMembers` to `assigneeOptions` format: `{ value: member.id, label: member.name, avatar: member.avatar }`
4. Pass `assigneeOptions` prop down the component chain to FilterBar

**Files**:
- `frontend/src/features/issues/components/views/IssueViewsRoot.tsx` (modify)
- `frontend/src/stores/WorkspaceStore.ts` (read-only)

**Blocked-by**: None
**Acceptance**: Open Issues view → Assignee filter dropdown shows all workspace members with avatars.

---

### T-004: Wire label options to FilterBar (S9)

**Type**: Wiring | **Scope**: Frontend | **Effort**: S

**Note**: Labels are **project-scoped** (`IssueLabel` model has `project_id` FK). No dedicated labels list endpoint exists — need to add one or query via the issues feature.

**Steps**:
1. Check `backend/src/pilot_space/api/v1/routers/` — if no labels list endpoint exists, add `GET /workspaces/{id}/projects/{projectId}/labels` returning `[{ id, name, color }]`
2. In frontend, add `labelsApi.list(workspaceId, projectId)` to `frontend/src/services/api/` (or use existing LabelSelector query)
3. In `IssueViewsRoot`, determine current project context (from URL params or filter state)
4. TanStack Query: fetch labels for current project (or union of all workspace projects if no project filter active)
5. Map to `labelOptions`: `{ value: label.id, label: label.name, color: label.color }`
6. Pass `labelOptions` prop down to FilterBar

**Files**:
- `backend/src/pilot_space/api/v1/routers/workspace_projects.py` or new router (modify/create — labels endpoint)
- `frontend/src/features/issues/components/views/IssueViewsRoot.tsx` (modify)
- `frontend/src/services/api/labels.ts` (create if needed)

**Blocked-by**: None
**Acceptance**: Open Issues view → Label filter dropdown shows project labels with color swatches. Selecting a label filters issues.

---

### T-005: Configure Meilisearch search_notes to return highlights (S12)

**Type**: Backend enhancement | **Scope**: Backend | **Effort**: XS

**Steps**:
1. Read `backend/src/pilot_space/infrastructure/search/meilisearch.py` — `search_notes()` at line 561
2. Add `attributes_to_highlight=["title", "content"]` parameter to the inner `self.search()` call
3. Verify the base `search()` method accepts and forwards this parameter to Meilisearch API
4. Response will include `_formatted` field in each hit with `<em>` tags around matches

**Files**:
- `backend/src/pilot_space/infrastructure/search/meilisearch.py` (modify — `search_notes()`)

**Blocked-by**: T-P1 (notes must be indexed first)
**Acceptance**: `search_notes("caching")` returns hits with `_formatted.content` containing `<em>caching</em>`.

---

### T-006: Add search param to notes list endpoint + highlights (S12)

**Type**: Backend enhancement | **Scope**: Backend | **Effort**: S

**Steps**:
1. Read `backend/src/pilot_space/api/v1/routers/workspace_notes.py` — find list endpoint
2. Add optional `search: str | None = Query(None)` parameter
3. When `search` is provided, call `MeilisearchClient.search_notes(search, workspace_id)` with `attributes_to_highlight=["title", "content"]` → return matched notes with `_formatted` snippets
4. Also update `search_notes()` in `meilisearch.py` to accept + forward `attributes_to_highlight` param (see T-005)
5. When `search` is None, use existing DB query (preserve current behavior)
6. Write unit test for search delegation

**Files**:
- `backend/src/pilot_space/api/v1/routers/workspace_notes.py` (modify)
- `backend/src/pilot_space/infrastructure/search/meilisearch.py` (modify — add `attributes_to_highlight` param to `search_notes()`)

**Blocked-by**: T-P1 (notes must be indexed), T-005 (highlights configured)
**Acceptance**: `GET /workspaces/{id}/notes?search=caching+strategy` returns notes matching body content with `_formatted.content` snippets.

---

### T-007: Replace client-side note search with Meilisearch API call (S12)

**Type**: Frontend wiring | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Find the notes list search input and its handler
2. Replace client-side `filter()` with debounced API call: `notesApi.list({ search: query })`
3. Show content snippet highlights in results (if Meilisearch returns `_formatted` fields)
4. Empty query → default sort by recent (preserve current behavior)

**Files**:
- Notes list page component (modify)
- `frontend/src/services/api/notes.ts` (modify — add `search` param to list request)

**Blocked-by**: T-006
**Acceptance**: Type "caching strategy" in notes search → results include notes with that phrase in body. Clear search → all notes shown.

---

### T-007: Create ShortcutGuide component (S3)

**Type**: New component | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Create `frontend/src/features/command-palette/ShortcutGuide.tsx`
2. Define shortcut categories: Navigation (Cmd+K search, Cmd+P palette), Editor (Cmd+B bold, Cmd+I italic, etc.), AI (\ for skills), General (? for this guide)
3. Render as modal overlay with shadcn `Dialog` — grouped sections, key combos styled as `<kbd>` elements
4. Write component test

**Files**:
- `frontend/src/features/command-palette/ShortcutGuide.tsx` (create)

**Blocked-by**: None
**Acceptance**: Component renders shortcut categories with correct key combos.

---

### T-008: Mount ShortcutGuide with `?` keybinding (S3)

**Type**: Integration | **Scope**: Frontend | **Effort**: XS

**Steps**:
1. Add `shortcutGuideOpen` state to `UIStore` (or local state in workspace layout)
2. Add `?` keydown handler: check `event.target` is not input/textarea/contenteditable → toggle guide
3. Mount `<ShortcutGuide open={...} onClose={...}>` in workspace layout

**Files**:
- Workspace layout component (modify)
- `frontend/src/stores/UIStore.ts` (modify — optional)

**Blocked-by**: T-007
**Acceptance**: Press `?` outside text input → shortcut guide opens. Press `?` inside text input → types `?` normally.

---

## Sprint 2: Find Anything

### T-009: Create workspace search backend endpoint (S1)

**Type**: New endpoint | **Scope**: Backend | **Effort**: M

**Steps**:
1. Create `backend/src/pilot_space/api/v1/routers/workspace_search.py`
2. Define `GET /workspaces/{workspace_id}/search` with params: `q: str`, `type: str | None` (notes/issues/all), `limit: int = 20`
3. Call `MeilisearchClient.search(q, workspace_id, type_filter)` → return unified results
4. Response schema: `{ results: [{ id, type, title, snippet, url, metadata }], total }`
5. Handle Meilisearch unavailable: return 503 with message
6. Mount router in `main.py`
7. Write unit + integration tests

**Files**:
- `backend/src/pilot_space/api/v1/routers/workspace_search.py` (create)
- `backend/src/pilot_space/api/v1/schemas/search.py` (create — response schema)
- `backend/src/pilot_space/main.py` (modify — mount router)
- `backend/src/pilot_space/infrastructure/search/meilisearch.py` (read-only)

**Blocked-by**: None
**Acceptance**: `GET /workspaces/{id}/search?q=auth&type=notes` returns matching notes with snippets.

---

### T-010: Create search API client (S1)

**Type**: Frontend API | **Scope**: Frontend | **Effort**: XS

**Steps**:
1. Create `frontend/src/features/search/search-api.ts`
2. Define typed client: `searchApi.search(workspaceId, query, type?, limit?)` → `SearchResult[]`
3. Follow existing pattern from `frontend/src/services/api/notes.ts`

**Files**:
- `frontend/src/features/search/search-api.ts` (create)

**Blocked-by**: T-009
**Acceptance**: API client types match backend schema. Calls resolve correctly.

---

### T-011: Create SearchModal component (S1)

**Type**: New component | **Scope**: Frontend | **Effort**: M

**Steps**:
1. Create `frontend/src/features/search/SearchModal.tsx`
2. Use shadcn `Dialog` + custom search input (or cmdk `CommandInput`)
3. Empty state: show recent items (from TanStack query cache or dedicated recent API)
4. Typing state: debounced search (300ms) → show results grouped by type with badges (Note, Issue, Project)
5. Type filter tabs: All, Notes, Issues
6. Tab key: preview selected result (side panel or expanded row)
7. Enter key: navigate to result → close modal
8. Escape: close modal
9. Wire to `UIStore.searchModalOpen`
10. **Error handling**: If search endpoint returns 503/error → show toast "Search temporarily unavailable" and fall back to client-side title filter on the notes list page (do not show blank results)
11. Write component tests

**Files**:
- `frontend/src/features/search/SearchModal.tsx` (create)
- `frontend/src/features/search/index.ts` (create — barrel export)

**Blocked-by**: T-010
**Acceptance**: SearchModal opens, shows results on typing, navigates on Enter, closes on Escape.

---

### T-012: Add Cmd+K global keybinding for search (S1)

**Type**: Integration | **Scope**: Frontend | **Effort**: XS

**Steps**:
1. In workspace layout, add `useEffect` with `keydown` listener for Cmd+K (Mac) / Ctrl+K (Win)
2. `event.preventDefault()` AND `event.stopPropagation()` — prevents browser address bar focus and bubbling to other handlers
3. Toggle `UIStore.searchModalOpen`
4. Mount `<SearchModal>` in workspace layout
5. Handle both Mac (`metaKey + 'k'`) and Windows/Linux (`ctrlKey + 'k'`)

**Files**:
- Workspace layout component (modify)
- `frontend/src/stores/UIStore.ts` (read-only — already has `searchModalOpen`)

**Blocked-by**: T-011
**Acceptance**: Cmd+K (Mac) / Ctrl+K (Win) opens SearchModal. Browser address bar does NOT focus. Works in Chrome, Firefox, Safari.

---

### T-013: Write SearchModal tests (S1)

**Type**: Test | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Test: renders empty state with recent items
2. Test: shows search results on query input
3. Test: filters by type when tab selected
4. Test: navigates on Enter
5. Test: closes on Escape
6. Test: handles Meilisearch error gracefully

**Files**:
- `frontend/src/features/search/__tests__/SearchModal.test.tsx` (create)

**Blocked-by**: T-011
**Acceptance**: All tests pass. Coverage >80% for SearchModal.

---

### T-014: Create command registry (S2)

**Type**: New module | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Create `frontend/src/features/command-palette/command-registry.ts`
2. Define `Command` type: `{ id, label, description, category: 'navigation'|'ai-skills'|'editor'|'settings', shortcut?, icon?, action: () => void }`
3. Define `getCommands(context: { currentRoute, isEditor })` function
4. Navigation commands: Go to Notes, Issues, Cycles, Projects, Modules, Settings (each with `router.push()`)
5. AI Skills: 24 entries with name, description, action → `pilotSpaceStore.setActiveSkill(skillName)` then `router.push(`/${workspaceSlug}/chat`)` (uses `PilotSpaceStore.setActiveSkill(skill, args?)` at `frontend/src/stores/ai/PilotSpaceStore.ts:581` — sets `activeSkill` consumed on next `sendMessage()`)
6. Editor Actions (contextual): bold, italic, heading, list, code block
7. Settings: Theme, Shortcuts, Notifications
8. Context-aware ordering: if `isEditor`, show Editor first; if homepage, show Navigation first

**Files**:
- `frontend/src/features/command-palette/command-registry.ts` (create)

**Blocked-by**: None
**Acceptance**: `getCommands()` returns categorized commands. AI skills category has 24 entries.

---

### T-015: Create CommandPalette component (S2)

**Type**: New component | **Scope**: Frontend | **Effort**: M

**Steps**:
1. Create `frontend/src/features/command-palette/CommandPalette.tsx`
2. Use shadcn `CommandDialog` from `frontend/src/components/ui/command.tsx`
3. Read commands from registry (T-014)
4. Render `CommandGroup` per category, `CommandItem` per command
5. On select: execute `command.action()` → close palette
6. Wire to `UIStore.commandPaletteOpen`
7. Show keyboard shortcut hints next to commands (if `command.shortcut` exists)

**Files**:
- `frontend/src/features/command-palette/CommandPalette.tsx` (create)
- `frontend/src/features/command-palette/index.ts` (create — barrel export)

**Blocked-by**: T-014
**Acceptance**: CommandPalette renders grouped commands. Fuzzy search filters correctly. Selecting a command executes its action.

---

### T-016: Add Cmd+P global keybinding for command palette (S2)

**Type**: Integration | **Scope**: Frontend | **Effort**: XS

**Steps**:
1. In workspace layout, add Cmd+P (Mac) / Ctrl+P (Win) listener
2. `event.preventDefault()` to suppress browser print dialog
3. Toggle `UIStore.commandPaletteOpen`
4. Mount `<CommandPalette>` in workspace layout

**Files**:
- Workspace layout component (modify)

**Blocked-by**: T-015
**Acceptance**: Cmd+P opens CommandPalette from any workspace page.

---

### T-017: Write CommandPalette tests (S2)

**Type**: Test | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Test: renders all command categories
2. Test: fuzzy search filters commands
3. Test: selecting navigation command calls router.push
4. Test: selecting AI skill command sets chat input
5. Test: context-aware ordering (editor context → editor commands first)

**Files**:
- `frontend/src/features/command-palette/__tests__/CommandPalette.test.tsx` (create)

**Blocked-by**: T-015
**Acceptance**: All tests pass. Coverage >80%.

---

### T-018: Implement Markdown export in handleExport (S10)

**Type**: Implementation | **Scope**: Frontend | **Effort**: S

**Steps**:
1. In `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx:294`
2. Get editor instance (via ref or context)
3. **Pre-process**: Remove `data-property-block` div from DOM before Markdown conversion (per CLAUDE.md tiptap rule) — `PropertyBlockNode` has no markdown serializer and will produce garbage output. Strip it: the property data is editor-UI-only and not meaningful in Markdown.
4. Call `editor.storage.markdown.getMarkdown()` — InlineIssueExtension serializes as `[PS-42](issue:uuid "title")`, NoteLinkExtension serializes as `[note-title](note:uuid)` (both have custom serializers)
5. Post-process the output string: replace `(issue:uuid "...")` patterns with nothing → output `[PS-42]` plain text
6. Create `Blob` with `text/markdown` type → trigger download as `{note.title || 'untitled'}.md`
7. Show success toast

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx` (modify)

**Blocked-by**: None
**Acceptance**: Click Export → Markdown → `.md` file downloads with correct heading, list, code block formatting.

---

### T-019: Implement PDF export via browser print (S10)

**Type**: Implementation | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Add `@media print` CSS to note editor styles — hide sidebar, header, toolbar; show content full-width
2. Implement PDF export action: apply print-optimized class → `window.print()` → remove class
3. Or: use a print-specific layout that renders note content cleanly

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx` (modify)
- Print CSS file or inline styles (create/modify)

**Blocked-by**: None
**Acceptance**: Click Export → PDF → browser print dialog opens with clean note layout.

---

### T-020: Add export dropdown with Markdown + PDF options (S10)

**Type**: UI enhancement | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Read `frontend/src/components/editor/RichNoteHeader.tsx` — find the export dropdown menu item
2. Replace single "Export" item with a submenu: "Download Markdown" and "Print / Save as PDF"
3. Wire each to the respective handler (T-018 for Markdown, T-019 for PDF)

**Files**:
- `frontend/src/components/editor/RichNoteHeader.tsx` (modify)
- `frontend/src/components/editor/InlineNoteHeader.tsx` (modify — if it also has export)
- `frontend/src/components/editor/NoteCanvasEditor.tsx` (modify — update `onExport` prop type if needed)

**Blocked-by**: T-018, T-019
**Acceptance**: Export dropdown shows "Download Markdown" and "Print / Save as PDF" options.

---

### T-021: Write export tests (S10)

**Type**: Test | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Test: Markdown export produces valid `.md` with headings, lists, code blocks
2. Test: Inline issue badges convert to `[PS-XX]` text in Markdown
3. Test: Export dropdown renders both options
4. Mock `window.print` for PDF test

**Files**:
- Note page test file (create or extend)

**Blocked-by**: T-020
**Acceptance**: All tests pass.

---

## Sprint 3: Organize & Communicate

### T-022: Create ModuleRepository (S4)

**Type**: Backend infrastructure | **Scope**: Backend | **Effort**: S

**Steps**:
1. Create `backend/src/pilot_space/infrastructure/database/repositories/module_repository.py`
2. Extend `BaseRepository[Module]`
3. Define `ModuleFilters` dataclass: `project_id`, `status`, `lead_id`
4. Implement: `list_by_workspace()` with cursor pagination, `get_by_id()`, `get_with_issue_stats()` (joins issue counts by state)
5. Use `selectinload` for project + lead relationships
6. Write unit tests

**Files**:
- `backend/src/pilot_space/infrastructure/database/repositories/module_repository.py` (create)
- Pattern ref: `backend/src/pilot_space/infrastructure/database/repositories/cycle_repository.py`

**Blocked-by**: None
**Acceptance**: Repository queries return modules with project/lead/issue-stats loaded.

---

### T-023: Create Module CRUD services (S4)

**Type**: Backend services | **Scope**: Backend | **Effort**: M

**Steps**:
1. Create `backend/src/pilot_space/application/services/module/` directory
2. Create `__init__.py` with exports
3. `create_module_service.py`: Payload(name, description, project_id, status, target_date, lead_id) → Result(module)
4. `update_module_service.py`: Payload(module_id, partial fields) → Result(module)
5. `delete_module_service.py`: Payload(module_id) → Result(success)
6. `list_modules_service.py`: Payload(workspace_id, filters, cursor) → Result(modules, cursor)
7. `get_module_service.py`: Payload(module_id) → Result(module with progress stats)
8. Progress calculation in get:
   - Count issues by state for module: `total = count(all issues)`, `done = count(issues where state = 'done')`
   - `progress_percent = 0 if total == 0 else round(done / total * 100)` — **guard against division by zero**
   - `is_overdue = target_date is not None AND target_date < date.today() AND (total - done) > 0` — incomplete = non-Done/non-Cancelled
   - Include in Result: `total_issues`, `done_issues`, `progress_percent`, `is_overdue`
9. Write unit tests for each service, including:
   - `test_progress_with_zero_issues()` → progress = 0, is_overdue = False
   - `test_progress_with_all_done()` → progress = 100, is_overdue = False
   - `test_is_overdue_with_past_target_date()` → is_overdue = True when incomplete

**Files**:
- `backend/src/pilot_space/application/services/module/` (create — 5 service files + `__init__.py`)
- Pattern ref: `backend/src/pilot_space/application/services/cycle/`

**Blocked-by**: T-022
**Acceptance**: All 5 services execute correctly. Get returns module with progress percentage.

---

### T-024: Create Module Pydantic schemas (S4)

**Type**: Backend schemas | **Scope**: Backend | **Effort**: S

**Steps**:
1. Create `backend/src/pilot_space/api/v1/schemas/module.py`
2. `ModuleCreate(BaseSchema)`: name, description, project_id, status?, target_date?, lead_id?
3. `ModuleUpdate(BaseSchema)`: all fields optional
4. `ModuleResponse(BaseSchema)`: all fields + `from_module()` factory + progress fields (total_issues, done_issues, progress_percent)
5. `ModuleListResponse`: list + cursor pagination
6. Follow camelCase alias pattern from `BaseSchema`

**Files**:
- `backend/src/pilot_space/api/v1/schemas/module.py` (create)
- Pattern ref: `backend/src/pilot_space/api/v1/schemas/cycle.py`

**Blocked-by**: None
**Acceptance**: Schemas validate and serialize correctly with camelCase output.

---

### T-025: Create modules router (S4)

**Type**: Backend router | **Scope**: Backend | **Effort**: M

**Steps**:
1. Create `backend/src/pilot_space/api/v1/routers/workspace_modules.py`
2. Endpoints: `POST /` (create), `GET /` (list with filters), `GET /{id}` (get with progress), `PATCH /{id}` (update), `DELETE /{id}` (soft delete)
3. Workspace-scoped: use `_resolve_workspace()` pattern
4. DI: `Annotated` typed dependencies for services
5. Mount in `main.py`
6. Write integration tests

**Files**:
- `backend/src/pilot_space/api/v1/routers/workspace_modules.py` (create)
- `backend/src/pilot_space/main.py` (modify — mount router)
- Pattern ref: `backend/src/pilot_space/api/v1/routers/workspace_cycles.py`

**Blocked-by**: T-023, T-024
**Acceptance**: All CRUD endpoints work. `GET /{id}` returns progress stats.

---

### T-026: Wire Module DI container (S4)

**Type**: DI wiring | **Scope**: Backend | **Effort**: XS

**Steps**:
1. Read `backend/src/pilot_space/container/container.py` — identify registration pattern
2. Register `ModuleRepository` in infra container
3. Register 5 module services in app container
4. Create typed dependency functions in `deps.py`

**Files**:
- `backend/src/pilot_space/container/container.py` (modify)
- DI deps file (modify)

**Blocked-by**: T-022, T-023
**Acceptance**: Module services injectable via `Annotated[...]` in router.

---

### T-027: Create modules API client (S4)

**Type**: Frontend API | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Create `frontend/src/services/api/modules.ts`
2. Define: `modulesApi.list(workspaceId, filters?)`, `.get(workspaceId, moduleId)`, `.create(workspaceId, data)`, `.update(workspaceId, moduleId, data)`, `.delete(workspaceId, moduleId)`
3. Follow pattern from `frontend/src/services/api/cycles.ts`

**Files**:
- `frontend/src/services/api/modules.ts` (create)

**Blocked-by**: T-025
**Acceptance**: API client matches backend schema types.

---

### T-028: Create modules list page (S4)

**Type**: Frontend page | **Scope**: Frontend | **Effort**: M

**Steps**:
1. Create `frontend/src/app/(workspace)/[workspaceSlug]/modules/page.tsx` — `'use client'`, `useParams()`
2. Create `frontend/src/features/modules/ModuleListPage.tsx` — main list component
3. TanStack Query for module list: `useQuery(['modules', workspaceId], () => modulesApi.list(workspaceId))`
4. Render card grid: name, lead avatar, issue count, progress bar, target date, status badge, overdue indicator
5. "Create Module" button → create dialog (name, description, project, target date, lead)
6. Add "Modules" to sidebar navigation

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/modules/page.tsx` (create)
- `frontend/src/features/modules/ModuleListPage.tsx` (create)
- `frontend/src/features/modules/ModuleCard.tsx` (create)
- `frontend/src/features/modules/CreateModuleDialog.tsx` (create)
- `frontend/src/components/layout/sidebar.tsx` (modify — add nav item)

**Blocked-by**: T-027
**Acceptance**: Modules page shows cards with progress bars. Create dialog works.

---

### T-029: Create module detail page (S4)

**Type**: Frontend page | **Scope**: Frontend | **Effort**: M

**Steps**:
1. Create `frontend/src/app/(workspace)/[workspaceSlug]/modules/[moduleId]/page.tsx`
2. Create `frontend/src/features/modules/ModuleDetailPage.tsx`
3. Module metadata header: name, description, status, target date, lead, progress bar
4. Filtered issue list: show issues assigned to this module (reuse existing issue list components)
5. Edit module inline or via dialog

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/modules/[moduleId]/page.tsx` (create)
- `frontend/src/features/modules/ModuleDetailPage.tsx` (create)

**Blocked-by**: T-028
**Acceptance**: Module detail shows metadata + filtered issue list. Edit works.

---

### T-030: Create ModuleSelector for issue detail (S4)

**Type**: Frontend component | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Create `frontend/src/features/modules/ModuleSelector.tsx`
2. Follow `CycleSelector` pattern: searchable dropdown, displays current module, allows clear
3. Props: `moduleId`, `onSelect(moduleId)`, `workspaceId`
4. Integrate into issue detail property panel (PropertyBlockView or equivalent)
5. On select: `PATCH /issues/{id}` with `{ moduleId }`

**Files**:
- `frontend/src/features/modules/ModuleSelector.tsx` (create)
- Issue detail property panel component (modify — add Module property row)

**Blocked-by**: T-027
**Acceptance**: Issue detail shows Module property. Selecting a module updates the issue.

---

### T-031: Write Module backend tests (S4)

**Type**: Test | **Scope**: Backend | **Effort**: M

**Steps**:
1. Repository tests: list, get, get_with_stats, create, update, delete
2. Service tests: each CRUD service with mocked repo
3. Router integration tests: all 5 endpoints
4. Progress calculation test: correct % with various issue state distributions

**Files**:
- `backend/tests/` (create test files following existing test structure)

**Blocked-by**: T-025
**Acceptance**: All tests pass. Coverage >80% for module code.

---

### T-032: Write Module frontend tests (S4)

**Type**: Test | **Scope**: Frontend | **Effort**: S

**Steps**:
1. ModuleListPage: renders cards, create dialog works
2. ModuleCard: displays correct data, progress bar fills correctly
3. ModuleSelector: search, select, clear
4. API client: request/response shape

**Files**:
- `frontend/src/features/modules/__tests__/` (create)

**Blocked-by**: T-028, T-030
**Acceptance**: All tests pass. Coverage >80%.

---

### T-033: Create Notification model + migration (S7)

**Type**: Database | **Scope**: Backend | **Effort**: M

**Steps**:
1. Verify alembic head: `cd backend && alembic heads` — single head (current last migration is `050_add_chat_attachments_cleanup_cron.py`)
2. Create `backend/src/pilot_space/infrastructure/database/models/notification.py`:
   - Fields: id (UUID), workspace_id (FK), user_id (FK), type (enum: COMMENT, ASSIGNMENT, STATE_CHANGE, MENTION, PR_REVIEW), title, description, priority (enum: URGENT, IMPORTANT, FYI), source_type (str), source_id (UUID), is_read (bool, default false), created_at
3. Create migration: `alembic revision --autogenerate -m "Add notifications table"`
4. Add RLS policies:
   - Users read/update own notifications in own workspaces
   - Service-role bypass for notification worker
5. Add indexes: (workspace_id, user_id, is_read), (user_id, created_at DESC)
6. Verify: `alembic heads` → single head, `alembic check` → matches models

**Files**:
- `backend/src/pilot_space/infrastructure/database/models/notification.py` (create)
- `backend/alembic/versions/051_notifications.py` (create — **next after 050**)

**Blocked-by**: None
**Acceptance**: Migration runs. RLS enforced. `alembic heads` shows single head.

---

### T-034: Create NotificationRepository (S7)

**Type**: Backend infrastructure | **Scope**: Backend | **Effort**: S

**Steps**:
1. Create `backend/src/pilot_space/infrastructure/database/repositories/notification_repository.py`
2. Extend `BaseRepository[Notification]`
3. Methods: `list_for_user(user_id, workspace_id, unread_only?, cursor)`, `count_unread(user_id, workspace_id)`, `mark_read(notification_id)`, `mark_all_read(user_id, workspace_id)`

**Files**:
- `backend/src/pilot_space/infrastructure/database/repositories/notification_repository.py` (create)

**Blocked-by**: T-033
**Acceptance**: Repository methods execute correctly with RLS context.

---

### T-035: Create Notification services (S7)

**Type**: Backend services | **Scope**: Backend | **Effort**: M

**Steps**:
1. Create `backend/src/pilot_space/application/services/notification/`
2. `create_notification_service.py`: Payload(workspace_id, user_id, type, title, description, priority, source_type, source_id) → persist to DB
3. `list_notifications_service.py`: Payload(user_id, workspace_id, unread_only, cursor) → paginated list
4. `mark_read_service.py`: Payload(notification_id or all) → update is_read
5. Write unit tests

**Files**:
- `backend/src/pilot_space/application/services/notification/` (create)

**Blocked-by**: T-034
**Acceptance**: Services create, list, and update notifications correctly.

---

### T-036: Create notifications router + schemas (S7)

**Type**: Backend router | **Scope**: Backend | **Effort**: M

**Steps**:
1. Create `backend/src/pilot_space/api/v1/schemas/notification.py` — response schemas
2. Create `backend/src/pilot_space/api/v1/routers/workspace_notifications.py`
3. Endpoints: `GET /` (list, paginated, `?unread_only=true`), `GET /unread-count`, `PATCH /{id}/read`, `POST /mark-all-read`
4. Workspace-scoped, user-scoped (from auth context)
5. Mount in `main.py`
6. Write integration tests

**Files**:
- `backend/src/pilot_space/api/v1/schemas/notification.py` (create)
- `backend/src/pilot_space/api/v1/routers/workspace_notifications.py` (create)
- `backend/src/pilot_space/main.py` (modify — mount router)

**Blocked-by**: T-035
**Acceptance**: All endpoints work. Unread count returns correct number.

---

### T-037: Create notification SSE endpoint (S7)

**Type**: Backend streaming | **Scope**: Backend | **Effort**: M

**Steps**:
1. Add `GET /workspaces/{id}/notifications/stream` SSE endpoint in notifications router
2. Use `StreamingResponse` with async generator (pattern from `streaming.py`)
3. Poll notification queue every 5s or use PostgreSQL LISTEN/NOTIFY for real-time delivery
4. Format events with `format_sse_event('notification', data)`
5. Include heartbeat comment every 30s to prevent proxy timeouts: `yield ": heartbeat\n\n"`
6. Emit `retry: 5000` SSE field so browser auto-reconnects within 5s on disconnect

**Files**:
- `backend/src/pilot_space/api/v1/routers/workspace_notifications.py` (modify — add stream endpoint)
- `backend/src/pilot_space/api/v1/streaming.py` (read-only — reuse `format_sse_event`)

**Blocked-by**: T-036
**Acceptance**: SSE endpoint streams notification events. Heartbeat keeps connection alive.

---

### T-038: Add enqueue_notification calls at event sources (S7)

**Type**: Backend wiring | **Scope**: Backend | **Effort**: M

**Steps**:
1. **Comment creation**: Modify `backend/src/pilot_space/application/services/discussion/create_discussion_service.py` — after comment saved, call `enqueue_notification(assignee_user_ids, 'COMMENT', title, description)`
2. **Issue assignment/state change**: Modify `backend/src/pilot_space/application/services/issue/update_issue_service.py` — after successful update, check if `assignee_id` changed → `enqueue_notification(new_assignee, 'ASSIGNMENT', ...)` and if `state` changed → `enqueue_notification(watchers, 'STATE_CHANGE', ...)`
3. **@mention detection**: In `create_discussion_service.py`, parse comment body for `@username` patterns → look up user_id → `enqueue_notification(mentioned_user, 'MENTION', ...)`
4. Use existing `SupabaseQueueClient.enqueue_notification(user_id, notification_type, data)` at `backend/src/pilot_space/infrastructure/queue/supabase_queue.py:617`
5. Write unit tests for each hook

**Files**:
- `backend/src/pilot_space/application/services/discussion/create_discussion_service.py` (modify — comments + @mentions)
- `backend/src/pilot_space/application/services/issue/update_issue_service.py` (modify — assignment + state change)
- `backend/src/pilot_space/infrastructure/queue/supabase_queue.py` (read-only)

**Blocked-by**: T-033
**Acceptance**: Creating a comment enqueues a notification. Changing issue state enqueues a notification.

---

### T-039: Create notification queue handler (S7)

**Type**: Backend worker | **Scope**: Backend | **Effort**: M

**Steps**:
1. Create `backend/src/pilot_space/infrastructure/queue/handlers/notification_handler.py`
2. Follow `pr_review_handler.py` pattern: class with deps + `execute(payload)`
3. Dequeue notification → call `CreateNotificationService.execute()` to persist → format SSE event → push to connected clients
4. ACK on success, NACK on failure with retry

**Files**:
- `backend/src/pilot_space/infrastructure/queue/handlers/notification_handler.py` (create)
- Pattern ref: `backend/src/pilot_space/infrastructure/queue/handlers/pr_review_handler.py`

**Blocked-by**: T-035, T-038
**Acceptance**: Queue handler processes notifications and persists them to DB.

---

### T-040: Wire Notification DI container (S7)

**Type**: DI wiring | **Scope**: Backend | **Effort**: XS

**Steps**:
1. Register `NotificationRepository` in infra container
2. Register notification services in app container
3. Register `NotificationHandler` in queue container
4. Create typed deps

**Files**:
- `backend/src/pilot_space/container/container.py` (modify)

**Blocked-by**: T-034, T-035, T-039
**Acceptance**: All notification components injectable.

---

### T-041: Connect NotificationStore to API + SSE (S7)

**Type**: Frontend wiring | **Scope**: Frontend | **Effort**: M

**Steps**:
1. Create `frontend/src/services/api/notifications.ts` — list, unread-count, mark-read, mark-all-read
2. Modify `frontend/src/stores/NotificationStore.ts`:
   - On init: fetch `unread-count` → set badge
   - On panel open: fetch notifications list (paginated)
   - Subscribe to notification SSE endpoint using `EventSource` or `fetch()` stream:
     ```typescript
     private subscribeToSSE() {
       const source = new EventSource(url);
       source.addEventListener('notification', (e) => runInAction(() => this.addNotification(JSON.parse(e.data))));
       source.onerror = () => { source.close(); setTimeout(() => this.subscribeToSSE(), 5000); }; // 5s reconnect
     }
     ```
   - `markAsRead(notificationId)` → individual API call + local `is_read = true` update (explicit read — user must interact)
   - `markAllAsRead()` → API call + local update
3. Verify bell icon shows real unread count. Notification panel shows live data.

**Files**:
- `frontend/src/services/api/notifications.ts` (create)
- `frontend/src/stores/NotificationStore.ts` (modify)

**Blocked-by**: T-036, T-037
**Acceptance**: Bell icon shows unread count. Panel shows notifications. Real-time updates via SSE. Connection auto-reconnects within 5s if dropped.

---

### T-041b: Notification preferences — per-type settings (FR-010)

**Type**: Full stack | **Scope**: Both | **Effort**: M

**Context**: Spec FR-010 requires "per-type user preferences" (enable/disable COMMENT, ASSIGNMENT, STATE_CHANGE, MENTION, PR_REVIEW notifications). This is currently missing from tasks T-033 through T-041.

**Steps**:
1. **Migration**: Add `notification_preferences` table (append to `051_notifications.py` migration):
   ```sql
   (user_id UUID, workspace_id UUID, notification_type VARCHAR, enabled BOOLEAN DEFAULT true,
   PRIMARY KEY (user_id, workspace_id, notification_type))
   ```
   Include RLS: user can only read/update own preferences.
2. **Backend service**: `get_notification_preferences_service.py`, `update_notification_preference_service.py`
3. **Router endpoint**: `GET /workspaces/{id}/notifications/preferences` + `PATCH /workspaces/{id}/notifications/preferences/{type}`
4. **Notification filter**: In `notification_handler.py` (T-039), check user's preference for the notification type before persisting — skip if disabled
5. **Frontend settings page**: Create `frontend/src/app/(workspace)/[workspaceSlug]/settings/notifications/page.tsx` — toggle list per type with descriptions
6. **NotificationStore**: Fetch preferences on init; expose as observable for settings page

**Files**:
- `backend/alembic/versions/051_notifications.py` (modify — add preferences table)
- `backend/src/pilot_space/application/services/notification/` (add 2 services)
- `backend/src/pilot_space/api/v1/routers/workspace_notifications.py` (modify — add preferences endpoints)
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/notifications/page.tsx` (create)
- `frontend/src/stores/NotificationStore.ts` (modify — add preferences state)

**Blocked-by**: T-033, T-039, T-041
**Acceptance**: User disables COMMENT notifications → comments by teammates no longer appear in bell. Settings page shows per-type toggles.

---

### T-042: Create template editor and settings page (S6)

**Type**: Frontend page | **Scope**: Frontend | **Effort**: M

**Steps**:
1. Create `frontend/src/app/(workspace)/[workspaceSlug]/settings/templates/page.tsx`
2. List system templates (read-only) + custom templates (editable, deletable)
3. "Create Template" button → opens editor
4. Create `frontend/src/features/notes/components/TemplateEditor.tsx` — reuse `NoteCanvasEditor` with:
   - Template name + description fields
   - "Save as Template" action (not auto-save) → `templatesApi.create(workspaceId, { name, description, content })`
5. Wire TemplatePicker's "Create Template" card to navigate to template editor
6. Write component tests

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/templates/page.tsx` (create)
- `frontend/src/features/notes/components/TemplateEditor.tsx` (create)
- `frontend/src/features/notes/components/TemplatePicker.tsx` (modify — wire "Create Template")
- `frontend/src/services/api/templates.ts` (read-only — already exists)

**Blocked-by**: T-001 (TemplatePicker must be active)
**Acceptance**: Create custom template → appears in TemplatePicker. Settings page lists all templates.

---

## Sprint 4: Team Awareness + Polish

### T-043: Extend homepage activity for team members (S8)

**Type**: Backend enhancement | **Scope**: Backend | **Effort**: M

**Steps**:
1. Read `backend/src/pilot_space/api/v1/routers/homepage.py` — understand `/activity` query
2. Add `GET /activity/team` endpoint (or `?scope=team` param on existing endpoint)
3. Query activities for all workspace members (not just current user)
4. Include actor fields: `actor_id`, `actor_name`, `actor_avatar_url`
5. Limit to last 24h, cap at 20 items
6. Update response schema with actor fields

**Files**:
- `backend/src/pilot_space/api/v1/routers/homepage.py` (modify)
- `backend/src/pilot_space/api/v1/schemas/homepage.py` (modify — add actor fields)

**Blocked-by**: None
**Acceptance**: `GET /activity/team` returns activities from all workspace members with actor attribution.

---

### T-044: Add Team Activity section to homepage (S8)

**Type**: Frontend component | **Scope**: Frontend | **Effort**: M

**Steps**:
1. Find the DailyBrief component on the homepage
2. Add "Team Activity" section below personal activity
3. TanStack Query for team activity: `useQuery(['activity', 'team', workspaceId])`
4. Render: `[Avatar] Alice moved PS-42 to In Review — 1h ago`
5. Hide section when no team activity in last 24h
6. "View all" link when >10 items

**Files**:
- Frontend homepage DailyBrief component (modify)

**Blocked-by**: T-043
**Acceptance**: Homepage shows Team Activity with teammate avatars and attributed actions. Hidden when empty.

---

### T-045: Write team activity tests (S8)

**Type**: Test | **Scope**: Both | **Effort**: S

**Steps**:
1. Backend: team activity endpoint returns correct data with actor fields
2. Frontend: Team Activity section renders, hides when empty

**Files**:
- Backend test file (create)
- Frontend test file (create)

**Blocked-by**: T-044
**Acceptance**: All tests pass.

---

### T-046: Add AI Skills to command registry (S11)

**Type**: Enhancement | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Modify `command-registry.ts` (T-014) — ensure all 24 skills are in "AI Skills" category
2. Each skill: name, description, trigger command, icon
3. Action: open chat view → set input to `\skill-name`
4. If command palette is already built (T-015), this is just data in the registry

**Files**:
- `frontend/src/features/command-palette/command-registry.ts` (modify)

**Blocked-by**: T-014
**Acceptance**: Cmd+P → "AI Skills" category shows all 24 skills.

---

### T-047: Add AI Actions to note editor slash menu (S11)

**Type**: Enhancement | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Find `SlashCommandExtension` in note editor extensions
2. Add "AI Actions" group with editor-relevant skills: extract-issues, improve-writing, summarize, generate-diagram
3. On select: open ChatView with `\skill-name` pre-filled

**Files**:
- Note editor SlashCommandExtension (modify)

**Blocked-by**: None
**Acceptance**: Type `/` in note editor → "AI Actions" group shows 4 skills.

---

### T-048: Enhance Settings/Skills page (S11)

**Type**: Enhancement | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Find existing Settings/Skills page
2. Enhance to show: skill name, description, trigger command (`\skill-name`), approval requirement, category
3. Link each skill to its trigger action (open chat with skill command)

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/skills/page.tsx` (modify)

**Blocked-by**: None
**Acceptance**: Settings → Skills shows all skills with descriptions and trigger commands.

---

### T-049: Write AI Skill discoverability tests (S11)

**Type**: Test | **Scope**: Frontend | **Effort**: XS

**Steps**:
1. Test: command registry includes 24 AI skills
2. Test: slash menu shows AI Actions group
3. Test: Settings/Skills page renders all skills

**Files**:
- Relevant test files (create/extend)

**Blocked-by**: T-046, T-047, T-048
**Acceptance**: All tests pass.

---

### T-050: E2E full workflow smoke test (Release Gate)

**Type**: E2E test | **Scope**: Both | **Effort**: M

**Steps**:
1. Login → Homepage loads with digest
2. Cmd+K → search for a note → navigate
3. Create note from Sprint Planning template
4. Write content → extract issues via AI
5. Assign issues to a module
6. Comment on issue → notification appears for assignee
7. Export note as Markdown → verify file
8. Cmd+P → navigate to Modules → verify progress

**Files**:
- E2E test file (create)

**Blocked-by**: All Sprint 1-3 tasks
**Acceptance**: Full workflow completes without errors.

---

### T-051: Performance + Accessibility audit (Release Gate)

**Type**: Audit | **Scope**: Frontend | **Effort**: S

**Steps**:
1. Lighthouse audit on key pages: Homepage, Notes List, Issue Detail, Module Detail
2. Verify all new components have ARIA labels and keyboard navigation
3. Verify search modals trap focus correctly
4. Verify Cmd+K/Cmd+P don't interfere with browser defaults
5. Fix any WCAG 2.2 AA violations

**Files**:
- Various (fixes as needed)

**Blocked-by**: All Sprint 1-3 tasks
**Acceptance**: Lighthouse >90 on all key pages. No WCAG AA violations.

---

## Dependency Graph

```
Sprint 0 (prerequisites — must complete before search tasks in S1/S2):
  T-P1 (note indexing) — independent, gates: T-005, T-006, T-007 (note search chain)
  T-P2 (issue indexing) — independent, gates: T-009, T-010, T-011 (global search)

Sprint 1 (all independent, parallelizable after T-P1/T-P2):
  T-001 (TemplatePicker sidebar) ← T-002 (TemplatePicker notes page)
  T-003 (wire assignees) — independent
  T-004 (wire labels) — independent
  T-P1 ← T-005 (Meilisearch highlights config) ← T-006 (notes search param + FE) ← T-007 (replace client-side search)
  T-008 (ShortcutGuide) — independent

Sprint 2 (mostly independent):
  T-P2 ← T-009 (search endpoint) ← T-010 (search API) ← T-011 (SearchModal) ← T-012 (Cmd+K), T-013 (tests)
  T-014 (registry) ← T-015 (CommandPalette) ← T-016 (Cmd+P), T-017 (tests)
  T-018 (MD export), T-019 (PDF export) ← T-020 (export dropdown) ← T-021 (tests)

Sprint 3 (two parallel tracks):
  Track A — Modules:
    T-022 (repo) ← T-023 (services) ← T-025 (router) ← T-026 (DI), T-031 (BE tests)
    T-024 (schemas) ← T-025
    T-025 ← T-027 (API client) ← T-028 (list page) ← T-029 (detail page), T-032 (FE tests)
    T-027 ← T-030 (ModuleSelector)

  Track B — Notifications:
    T-033 (model+migration) ← T-034 (repo) ← T-035 (services) ← T-036 (router) ← T-037 (SSE)
    T-033 ← T-038 (event hooks) ← T-039 (handler) ← T-040 (DI)
    T-036, T-037 ← T-041 (frontend wiring)
    T-033, T-039, T-041 ← T-041b (notification preferences)

  T-042 (template editor) depends on T-001

Sprint 4 (depends on Sprint 2-3):
  T-043 (team API) ← T-044 (team UI) ← T-045 (tests)
  T-014 ← T-046 (AI skills in palette)
  T-047 (slash menu AI) — independent
  T-048 (settings skills) — independent
  T-046, T-047, T-048 ← T-049 (tests)
  All ← T-050 (E2E), T-051 (audit)
```
