# Task Breakdown: MVP-018 Note-First Complete

**Plan**: `specs/018-mvp-note-first-complete/plan.md`
**Branch**: `018-mvp-note-first-complete`
**Created**: 2026-02-20
**Updated**: 2026-02-20 (v2 — debug/wire/polish tasks, not greenfield)

---

## Key Context: Codebase is 95% Complete

200+ frontend components, 51 backend routers, 41 DB models, 13 TipTap extensions already built. All bugs are shallow: URL mismatches, missing data loading calls, null checks, field name mismatches.

## Task Summary

| Phase | Tasks | Type | Effort |
|-------|-------|------|--------|
| 1: Bug Fixes | T-001 to T-007 | Fix routing, URL paths, data binding, null checks | 2 days |
| 2: Wiring | T-008 to T-014 | Connect existing components, verify data flow | 3 days |
| 3: Polish | T-015 to T-019 | UX improvements to existing flows | 2 days |

**Total**: 19 tasks, ~7 days. All Phase 1 tasks are independent and parallelizable.

---

## Phase 1: Bug Fixes (all independent, parallelizable)

### T-001: Fix Issues Kanban state mapping (FR-001)

**Type**: Data binding fix | **Scope**: Frontend

**Symptom**: All 50 issues in Backlog column; other columns show 0.
**Root cause**: Frontend Kanban column IDs don't match backend `state` field values (likely casing or field name mismatch).

**Steps**:
1. Call `GET /api/v1/workspaces/{id}/issues` — note exact `state` values (e.g., `"backlog"`, `"todo"`, `"in_progress"`)
2. Find Kanban column definitions in `frontend/src/features/issues/components/`
3. Align column IDs with backend state values
4. Unit test: grouping logic

**Files**:
- `frontend/src/features/issues/components/` — board/kanban component (column defs)
- `frontend/src/features/issues/hooks/` — issue list query hook (response mapping)

**Acceptance**: Issues distributed across all 6 Kanban columns matching their actual state.

---

### T-002: Fix AI Chat 404 error (FR-002)

**Type**: Runtime error fix | **Scope**: Frontend

**Symptom**: AI Chat 404 at `/pilot-space-demo/ai-chat`.
**Root cause**: Sidebar correctly links to `/chat` (sidebar.tsx:62). Route page exists. Most likely a runtime error in `getAIStore()` or `PilotSpaceStore` initialization that crashes the page component, causing Next.js error boundary to show 404.

**Steps**:
1. Read `frontend/src/stores/ai/AIStore.ts` — check `getAIStore()` for null/undefined returns
2. Read `frontend/src/app/(workspace)/[workspaceSlug]/chat/page.tsx` — check error handling
3. Add null guard or loading state for store initialization
4. Verify page renders

**Files**:
- `frontend/src/stores/ai/AIStore.ts`
- `frontend/src/app/(workspace)/[workspaceSlug]/chat/page.tsx`
- `frontend/src/features/ai/ChatView/ChatView.tsx`

**Acceptance**: Clicking "AI Chat" in sidebar loads chat page without errors.

---

### T-003: Fix Approvals "Bad Request" (FR-003)

**Type**: URL path mismatch | **Scope**: Frontend API client

**Symptom**: Approvals page shows "Bad Request" on load.
**Root cause (confirmed)**: Frontend calls `/workspaces/${workspaceId}/approvals/pending` (approvals.ts:21) but backend is at `/api/v1/approvals/...` — not workspace-scoped in URL path. Router mounted at `API_V1_PREFIX` (main.py:242), workspace passed via `X-Workspace-Id` header.

**Fix**: Change frontend URLs from `/workspaces/${id}/approvals/...` to `/approvals/...`.

**Files**:
- `frontend/src/services/api/approvals.ts` — Fix 7 URL paths (lines 21, 36, 44, 50, 57, 66, 74)

**Acceptance**: Approvals page loads. Shows empty state or approval list.

---

### T-004: Fix Costs "Not Found" (FR-004)

**Type**: URL path mismatch | **Scope**: Frontend API client

**Symptom**: "Failed to load cost data - Not Found".
**Root cause (confirmed)**: Frontend calls `/workspaces/${workspaceId}/ai/costs/summary` (ai.ts:224) but backend is at `/api/v1/costs/summary`. Extra `/workspaces/{id}/ai/` prefix doesn't exist.

**Fix**: Change frontend URLs from `/workspaces/${id}/ai/costs/...` to `/costs/...`.

**Files**:
- `frontend/src/services/api/ai.ts` — Fix cost endpoint URLs

**Acceptance**: Costs page loads. Shows cost dashboard or empty state.

---

### T-005: Fix Homepage note word counts (FR-005)

**Type**: Missing data / field mapping | **Scope**: Frontend + Backend

**Symptom**: Note cards show "0 words".
**Root cause**: Either `word_count` not computed/stored server-side, not in API response, or frontend reads wrong field name.

**Steps**:
1. Check homepage note card component — what field name is rendered
2. Check backend notes response schema — verify `word_count` / `wordCount` field
3. If missing: compute word count from TipTap JSON content (server-side on save, or client-side)
4. If field name mismatch: fix frontend to use correct name

**Files**:
- `frontend/src/features/homepage/components/` — note card
- `backend/src/pilot_space/api/v1/routers/homepage.py`
- `backend/src/pilot_space/api/v1/routers/workspace_notes.py`

**Acceptance**: Note cards display accurate word counts.

---

### T-006: Fix Issue Detail "null pts" / "No priority" (FR-006)

**Type**: Null-check fix | **Scope**: Frontend

**Symptom**: "null pts" and "No priority" shown even with seeded data.
**Root cause**: `${estimate_points} pts` without null guard → `"null pts"`. Priority not mapped to display label.

**Steps**:
1. Read `issue-properties-panel.tsx` and `issue-header.tsx`
2. Fix estimate: null check → show "No estimate" instead of "null pts"
3. Fix priority: map backend value to display label
4. Verify backend returns these fields populated

**Files**:
- `frontend/src/features/issues/components/issue-properties-panel.tsx`
- `frontend/src/features/issues/components/issue-header.tsx`

**Acceptance**: Shows actual values. Null → "No estimate" / "No priority".

---

### T-007: Fix Sidebar PINNED/RECENT empty (FR-007)

**Type**: Data loading fix | **Scope**: Frontend

**Symptom**: PINNED and RECENT sections always empty.
**Root cause (confirmed)**: `noteStore.pinnedNotes` and `recentNotes` derive from `noteStore.notesList` which is empty — `loadNotes()` never called on workspace mount.

**Steps**:
1. Add `useEffect` in sidebar or workspace layout that calls `noteStore.loadNotes()` on workspace change
2. OR use TanStack Query `useQuery` directly in sidebar
3. Verify backend returns `is_pinned` field mapped to frontend `isPinned`

**Files**:
- `frontend/src/components/layout/sidebar.tsx` (around line 270)
- `frontend/src/stores/features/notes/NoteStore.ts`

**Acceptance**: PINNED shows up to 5 pinned notes. RECENT shows last 10.

---

## Phase 2: Wire Existing Components

### T-008: Wire homepage activity feed with date grouping (FR-008, FR-021)

**Type**: Wiring | **Scope**: Frontend + Backend verification
**Depends on**: T-005

**What exists**: `ActivityFeed/` directory. Backend `homepage_router`.

**Steps**:
1. Read `frontend/src/features/homepage/components/ActivityFeed/` — check existing components
2. Verify ActivityFeed fetches from homepage endpoint
3. Wire date grouping (Today/Yesterday/This Week/Earlier) if not wired
4. Wire note content previews (first 2 lines TipTap → plaintext) on cards

**Files**:
- `frontend/src/features/homepage/components/ActivityFeed/`
- `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx`

**Acceptance**: Activity grouped by date. Note cards show 2-line previews.

---

### T-009: Wire AI digest panel on homepage (FR-009)

**Type**: Wiring | **Scope**: Frontend + Backend verification
**Depends on**: T-008

**What exists**: `DigestPanel/` component. Backend `DigestWorker`. `homepage_router`.

**Steps**:
1. Read `DigestPanel/` — check expected data shape
2. Verify backend digest endpoint returns data
3. Add fallback: basic workspace stats when no AI digest

**Files**:
- `frontend/src/features/homepage/components/DigestPanel/`
- `backend/src/pilot_space/api/v1/routers/homepage.py`

**Acceptance**: Insights panel shows workspace health metrics.

---

### T-010: Verify slash commands and floating toolbar (FR-010, FR-011)

**Type**: Verification | **Scope**: Frontend

**What exists**: `SlashCommandExtension.ts`, `slash-command-items.ts`, `slash-command-menu.ts`. 13 TipTap extensions.

**Steps**:
1. Read `slash-command-items.ts` — verify 8 block types (Heading 1-3, Bullet/Numbered/Task List, Code, Quote, Table, Divider)
2. Read `createEditorExtensions.ts` — verify SlashCommand included
3. Check BubbleMenu for floating toolbar (Bold, Italic, Strikethrough, Code, Link, Highlight)
4. Add any missing items

**Files**:
- `frontend/src/features/notes/editor/extensions/slash-command-items.ts`
- `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts`
- `frontend/src/components/editor/` — BubbleMenu / toolbar

**Acceptance**: "/" shows 8+ block types. Text selection shows 6 formatting options.

---

### T-011: Verify auto-save and save indicator (FR-012)

**Type**: Verification | **Scope**: Frontend

**What exists**: NoteStore with `isSaving`, `lastSavedAt`, `hasUnsavedChanges`, 2s debounce.

**Steps**:
1. Read NoteStore auto-save reaction
2. Find SaveStatus component — verify wired to editor header
3. Fix disconnected wiring if needed

**Files**:
- `frontend/src/stores/features/notes/NoteStore.ts`
- `frontend/src/components/editor/`

**Acceptance**: Edit triggers auto-save after 2s. Indicator shows status.

---

### T-012: Wire intent extraction UI (FR-013, FR-014)

**Type**: Wiring | **Scope**: Frontend + Backend verification

**What exists**: Backend `ai_extraction_router`, `intents_router`, `workspace_note_issue_links_router`. Frontend `InlineIssueExtension.ts`, `InlineIssueComponent.tsx`.

**Steps**:
1. Read extraction endpoint schema — request/response format
2. Verify "Extract issues" trigger exists in editor UI (if not, add toolbar button)
3. Wire flow: extract → display categorized intents → approve → create issue + NoteIssueLink

**Files**:
- `backend/src/pilot_space/api/v1/routers/ai_extraction.py`
- `backend/src/pilot_space/api/v1/routers/intents.py`
- `frontend/src/features/notes/` — editor toolbar, extraction panel

**Acceptance**: Extract → categorized intents → approve → issue created with NoteIssueLink.

---

### T-013: Wire inline issue badges after extraction (FR-015)

**Type**: Wiring | **Scope**: Frontend
**Depends on**: T-012

**What exists**: `IssueLinkExtension.ts`, `InlineIssueExtension.ts`, `InlineIssueComponent.tsx`.

**Steps**:
1. Read InlineIssueExtension — how badges render
2. After extraction approval, verify badge inserted at extraction point
3. Verify click navigates to issue detail

**Files**:
- `frontend/src/features/notes/editor/extensions/InlineIssueExtension.ts`
- `frontend/src/features/notes/editor/extensions/InlineIssueComponent.tsx`

**Acceptance**: Inline badges appear after extraction. Click navigates to issue.

---

### T-014: Verify version history panel (FR-022)

**Type**: Verification | **Scope**: Frontend + Backend

**What exists**: `VersionHistoryPanel.tsx`, `useNoteVersions.ts`, `versionApi.ts` (all modified in git status). Backend `note_versions_router`.

**Steps**:
1. Read modified files — understand current state
2. Verify list → view → restore flow
3. Fix issues in modified files

**Files**:
- `frontend/src/components/editor/VersionHistoryPanel.tsx`
- `frontend/src/hooks/useNoteVersions.ts`
- `frontend/src/features/notes/services/versionApi.ts`

**Acceptance**: Version list shows. Restore replaces content.

---

## Phase 3: UX Polish

### T-015: Verify AI Context and "Copy for Claude Code" (FR-016, FR-017)

**Type**: Verification | **Scope**: Frontend + Backend

**What exists**: `ai-context-panel.tsx`, `ai-context-tab.tsx`, `claude-code-prompt-card.tsx`, `copy-context.ts`. Backend context endpoints.

**Steps**:
1. Verify AI Context tab renders 5 sections (description, criteria, requirements, notes, dependencies)
2. Verify "Copy for Claude Code" formats and copies markdown prompt
3. Fix rendering/data issues

**Files**:
- `frontend/src/features/issues/components/ai-context-panel.tsx`
- `frontend/src/features/issues/components/claude-code-prompt-card.tsx`
- `frontend/src/lib/copy-context.ts`

**Acceptance**: 5 context sections render. Copy produces AI-optimized markdown.

---

### T-016: Polish Kanban drag-drop and issue cards (FR-018, FR-019)

**Type**: Polish | **Scope**: Frontend
**Depends on**: T-001

**What exists**: Issue components. IssueStore with viewMode.

**Steps**:
1. Check `package.json` for dnd-kit or similar
2. Verify drag-and-drop works between columns
3. Verify cards show: identifier, title, priority color, assignee avatar
4. Fix missing elements

**Files**:
- `frontend/src/features/issues/components/`
- `frontend/package.json`

**Acceptance**: Drag-and-drop moves issues. Cards show all info.

---

### T-017: Verify List and Table views (FR-020)

**Type**: Verification | **Scope**: Frontend
**Depends on**: T-001

**What exists**: IssueStore `viewMode` ('board'|'list'|'table').

**Steps**:
1. Find view mode toggle and list/table components
2. Verify table has sortable columns
3. Fix rendering issues

**Files**:
- `frontend/src/features/issues/components/`
- `frontend/src/app/(workspace)/[workspaceSlug]/issues/page.tsx`

**Acceptance**: Three view modes work. Table has sortable columns.

---

### T-018: Fix workspace invitation and AI providers (FR-023, FR-024)

**Type**: Bug fix | **Scope**: Frontend

**Known bugs**:
- "Invite Members" dispatches unhandled CustomEvent
- AI Providers shows `[object Object]` error

**Steps**:
1. Fix invite: replace CustomEvent with direct API call
2. Fix AI Providers: serialize error object to readable string
3. Verify flows work

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/members/page.tsx`
- `frontend/src/app/(workspace)/[workspaceSlug]/settings/ai-providers/page.tsx`

**Acceptance**: Invite shows modal. AI Providers shows readable errors.

---

### T-019: Wire Command+K palette (FR-025, MAY)

**Type**: Polish — optional | **Scope**: Frontend

**What exists**: UIStore `commandPaletteOpen` state.

**Steps**:
1. Check if command palette component exists
2. Wire Cmd+K shortcut
3. Implement search if needed

**Files**:
- `frontend/src/stores/UIStore.ts`
- `frontend/src/components/`

**Acceptance**: Cmd+K opens searchable palette.

---

## Dependencies Graph

```
Phase 1 (all independent — can all run in parallel):
  T-001  T-002  T-003  T-004  T-005  T-006  T-007

Phase 2:
  T-005 ─── T-008 ─── T-009
  T-001 ─── T-016, T-017
  T-010, T-011, T-014 (independent)
  T-012 ─── T-013

Phase 3:
  T-015, T-018, T-019 (independent)
```

## Execution Plan

```
Day 1: T-001 to T-007 (all parallel — 7 bug fixes)
Day 2: T-008, T-010, T-011, T-014 (parallel — homepage, editor, versions)
Day 3: T-009, T-012 (parallel — digest panel, extraction wiring)
Day 4: T-013, T-015, T-016 (parallel — badges, AI context, kanban)
Day 5: T-017, T-018, T-019 (parallel — views, settings, palette)
```
