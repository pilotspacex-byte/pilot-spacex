# Implementation Plan: MVP-018 Note-First Complete

**Spec**: `specs/018-mvp-note-first-complete/spec.md`
**Branch**: `018-mvp-note-first-complete`
**Created**: 2026-02-20
**Updated**: 2026-02-20 (v2 — debugging/wiring/polish plan, not greenfield)

---

## Key Finding: Codebase is 95% Complete

Component tracer reveals the codebase has 200+ frontend components, 51 backend routers (150+ endpoints), 41 DB models with full RLS, 13 TipTap extensions, and full AI chat with 20+ rendering components. The bugs are **shallow routing, data-binding, and null-check issues** — not missing features.

**This plan focuses on: (1) bug fixes, (2) wiring existing components, (3) UX polish.**

---

## Phase Overview

| Phase | Priority | FRs | Type | Effort |
|-------|----------|-----|------|--------|
| 1: Stabilize | P1 | FR-001 to FR-007 | Bug fixes — routing, data binding, null checks | 2 days |
| 2: Wire | P1 | FR-008 to FR-015, FR-021, FR-022 | Connect existing components that aren't hooked up | 3 days |
| 3: Polish | P2-P3 | FR-016 to FR-025 | UX improvements to existing flows | 2 days |

---

## Phase 1: Bug Fixes — Routing, Data Binding, Null Checks (P1)

All 7 bugs are independent and can be fixed in parallel.

### FR-001: Issues Kanban state mapping

**Symptom**: All 50 issues in Backlog column; other columns show 0.
**Type**: Data binding bug — state field mapping mismatch.

**Root Cause**: Frontend Kanban column IDs likely don't match backend state values. The backend stores issue state as a string (e.g., `"backlog"`, `"todo"`, `"in_progress"`). The frontend column definitions may expect different values or use the wrong field name.

**Fix**: Align frontend column IDs with backend state values. This is a one-line-per-column mapping fix.

**Files**:
- `frontend/src/features/issues/components/` — Kanban board component (column definitions)
- `frontend/src/features/issues/hooks/` — Issue query hook (verify `state` field in response mapping)

---

### FR-002: AI Chat 404 error

**Symptom**: Navigating to AI Chat shows 404 at `/pilot-space-demo/ai-chat`.
**Type**: Routing bug — URL path mismatch.

**Root Cause**: Sidebar defines `{ name: 'AI Chat', path: 'chat' }` (line 62, sidebar.tsx) which resolves to `/${slug}/chat`. The page exists at `frontend/src/app/(workspace)/[workspaceSlug]/chat/page.tsx`. The 404 was observed at `/pilot-space-demo/ai-chat` — the actual route is `/pilot-space-demo/chat`. Either the user navigated to the wrong URL, or there's a runtime error in `getAIStore()` / `PilotSpaceStore` initialization that renders as 404.

**Fix**: Verify sidebar URL construction OR fix runtime error in ChatView mount (likely `getAIStore()` returns undefined before store initialization).

**Files**:
- `frontend/src/app/(workspace)/[workspaceSlug]/chat/page.tsx` — Check mount error
- `frontend/src/stores/ai/AIStore.ts` — `getAIStore()` initialization

---

### FR-003: Approvals "Bad Request" error

**Symptom**: Approvals page shows "Bad Request" error on load.
**Type**: URL path mismatch between frontend API client and backend router.

**Root Cause (confirmed)**: Frontend calls `/workspaces/${workspaceId}/approvals/pending` (approvals.ts:21) but backend router is mounted at `/api/v1/approvals` (main.py:242 — `ai_approvals_router` at `API_V1_PREFIX`). The backend expects `/api/v1/approvals/...` not `/api/v1/workspaces/{id}/approvals/...`. The workspace ID is passed via `X-Workspace-Id` header, not URL path.

**Fix**: Update frontend API client URL from `/workspaces/${workspaceId}/approvals/...` to `/approvals/...`. OR update backend router mounting to use workspace prefix.

**Files**:
- `frontend/src/services/api/approvals.ts` — Fix URL paths (lines 21, 36, 44, 50, 57, 66, 74)
- `backend/src/pilot_space/main.py` — Alternatively, mount at workspace prefix

---

### FR-004: Costs page "Not Found" error

**Symptom**: Costs page shows "Failed to load cost data - Not Found".
**Type**: URL path mismatch between frontend API client and backend router.

**Root Cause (confirmed)**: Frontend calls `/workspaces/${workspaceId}/ai/costs/summary` (ai.ts:224) but backend router has `prefix="/costs"` mounted at `/api/v1` (main.py:245). The actual backend path is `/api/v1/costs/summary`. Frontend uses a workspace-scoped URL with an extra `/ai/` segment that doesn't exist.

**Fix**: Update frontend API client URL from `/workspaces/${workspaceId}/ai/costs/summary` to `/costs/summary`. OR update backend mounting.

**Files**:
- `frontend/src/services/api/ai.ts` — Fix cost endpoint URL (line 224 and related)
- `backend/src/pilot_space/main.py` — Alternatively, mount at workspace prefix

---

### FR-005: Homepage note cards show "0 words"

**Symptom**: Note cards display "0 words" instead of actual word count.
**Type**: Missing data — API response field not populated.

**Root Cause**: Either (a) `word_count` field is not computed/stored in backend, or (b) backend returns it as 0/null, or (c) frontend reads wrong field name.

**Fix**: Ensure backend computes word count from TipTap JSON content on save and returns it in the notes list response. OR compute client-side from content.

**Files**:
- `frontend/src/features/homepage/components/` — Note card (check field name used)
- `backend/src/pilot_space/api/v1/routers/homepage.py` — Check response schema
- `backend/src/pilot_space/api/v1/routers/workspace_notes.py` — Check word_count field

---

### FR-006: Issue Detail shows "null pts" and "No priority"

**Symptom**: Issue detail shows literal "null pts" and "No priority" even with seeded data.
**Type**: Null-check / rendering bug.

**Root Cause**: Frontend renders `${estimate_points} pts` without null check, producing `"null pts"`. Priority field may not be mapped from backend response to frontend display label.

**Fix**: Add null-safe rendering: `estimate_points ? \`${estimate_points} pts\` : "No estimate"`. Fix priority display to map value to label.

**Files**:
- `frontend/src/features/issues/components/issue-properties-panel.tsx`
- `frontend/src/features/issues/components/issue-header.tsx`

---

### FR-007: Sidebar PINNED and RECENT always empty

**Symptom**: Sidebar sections show no notes.
**Type**: Data loading — notes never loaded into MobX store.

**Root Cause (confirmed)**: Sidebar reads `noteStore.pinnedNotes` and `noteStore.recentNotes` which are computed from `noteStore.notesList`. But `notesList` is derived from the internal `notes: Map` which is never populated because no component calls `noteStore.loadNotes()` on workspace mount.

**Fix**: Either (a) trigger `noteStore.loadNotes()` when workspace changes (e.g., in sidebar useEffect), or (b) replace MobX-dependent logic with TanStack Query `useQuery` hook directly in sidebar.

**Files**:
- `frontend/src/components/layout/sidebar.tsx` — Add note loading trigger
- `frontend/src/stores/features/notes/NoteStore.ts` — Verify `loadNotes()` populates map

---

## Phase 2: Wire Existing Components (P1)

These features have existing backend endpoints and frontend components. The work is connecting them and ensuring data flows correctly.

### FR-008 + FR-021: Homepage activity feed with date grouping and previews

**Existing**: `frontend/src/features/homepage/components/ActivityFeed/` directory exists. Backend `homepage_router` is mounted. `DigestPanel/` exists.

**Wire**: Verify ActivityFeed component fetches from homepage endpoint and groups by date (Today/Yesterday/This Week). Ensure note cards include content preview (first 2 lines from TipTap JSON). This may just need the query hook wired correctly.

**Files**:
- `frontend/src/features/homepage/components/ActivityFeed/`
- `frontend/src/features/homepage/hooks/` or `api/`
- `backend/src/pilot_space/api/v1/routers/homepage.py`

---

### FR-009: AI workspace insights on homepage

**Existing**: `DigestPanel/` component exists. Backend has `DigestWorker` (main.py:121-124). `homepage_router` is mounted.

**Wire**: Verify DigestPanel fetches digest data and renders. Add fallback stats view when no AI digest available (show basic counts from existing data).

**Files**:
- `frontend/src/features/homepage/components/DigestPanel/`
- `backend/src/pilot_space/api/v1/routers/homepage.py`

---

### FR-010: Slash command menu

**Existing**: `SlashCommandExtension.ts` exists. `slash-command-items.ts` and `slash-command-menu.ts` exist. `createEditorExtensions.ts` factory exists.

**Wire**: Verify SlashCommandExtension is included in `createEditorExtensions()`. Verify it includes all 8 block types: Heading 1-3, Bullet List, Numbered List, Task List, Code Block, Quote, Table, Divider. Add any missing items to `slash-command-items.ts`.

**Files**:
- `frontend/src/features/notes/editor/extensions/SlashCommandExtension.ts`
- `frontend/src/features/notes/editor/extensions/slash-command-items.ts`
- `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts`

---

### FR-011: Floating toolbar on text selection

**Existing**: TipTap BubbleMenu is a standard TipTap feature. Editor components exist in `frontend/src/components/editor/`.

**Wire**: Verify BubbleMenu is configured in the editor with: Bold, Italic, Strikethrough, Code, Link, Highlight options.

**Files**:
- `frontend/src/components/editor/` — Check for BubbleMenu/FloatingToolbar
- `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts`

---

### FR-012: Auto-save with save indicator

**Existing**: NoteStore has `isSaving`, `lastSavedAt`, `hasUnsavedChanges`. Auto-save with 2s debounce is documented.

**Wire**: Verify the MobX reaction fires. Verify SaveStatus component exists and is rendered in editor header.

**Files**:
- `frontend/src/stores/features/notes/NoteStore.ts`
- `frontend/src/components/editor/` (SaveStatus component)

---

### FR-013 + FR-014: Intent extraction and issue creation

**Existing**: Backend `ai_extraction_router` and `intents_router` exist. `workspace_note_issue_links_router` exists. Frontend has IssueLinkExtension and InlineIssueExtension.

**Wire**: Verify extraction endpoint works (call with note content, get categorized intents). Verify the frontend has an "Extract issues" trigger in the editor. Wire the approval flow: user reviews intents → approves → creates issue + NoteIssueLink.

**Files**:
- `backend/src/pilot_space/api/v1/routers/ai_extraction.py`
- `backend/src/pilot_space/api/v1/routers/intents.py`
- `backend/src/pilot_space/api/v1/routers/workspace_note_issue_links.py`
- `frontend/src/features/notes/editor/extensions/InlineIssueExtension.ts`

---

### FR-015: Inline issue badges

**Existing**: `IssueLinkExtension.ts` and `InlineIssueExtension.ts` both exist. `InlineIssueComponent.tsx` exists.

**Wire**: Verify after extraction, inline badges are inserted in TipTap content at the right position. Verify clicking badge navigates to issue detail.

**Files**:
- `frontend/src/features/notes/editor/extensions/IssueLinkExtension.ts`
- `frontend/src/features/notes/editor/extensions/InlineIssueExtension.ts`
- `frontend/src/features/notes/editor/extensions/InlineIssueComponent.tsx`

---

### FR-022: Version history with restore

**Existing**: `VersionHistoryPanel.tsx`, `useNoteVersions.ts`, `versionApi.ts` all exist (modified in git status). Backend `note_versions_router` exists.

**Wire**: Verify the version history panel lists versions and restore works. Fix any data binding issues in the modified files.

**Files**:
- `frontend/src/components/editor/VersionHistoryPanel.tsx`
- `frontend/src/hooks/useNoteVersions.ts`
- `frontend/src/features/notes/services/versionApi.ts`
- `backend/src/pilot_space/api/v1/routers/note_versions.py`

---

## Phase 3: UX Polish (P2-P3)

### FR-016 + FR-017: AI Context + Copy for Claude Code

**Existing**: `ai-context-panel.tsx`, `ai-context-tab.tsx`, `ai-context-streaming.tsx`, `claude-code-prompt-card.tsx`, `copy-context.ts` all exist. Backend `issues_ai_context_router` and `issues_ai_context_streaming_router` both exist.

**Polish**: Verify context includes 5 sections (description, criteria, requirements, notes, dependencies). Verify "Copy for Claude Code" formats correctly and copies to clipboard.

---

### FR-018 + FR-019 + FR-020: Kanban drag-drop, cards, List/Table views

**Existing**: Issue components exist. IssueStore has `viewMode` ('board'|'list'|'table'). Check for dnd-kit or similar in package.json.

**Polish**: Verify drag-and-drop works. Verify issue cards show identifier, title, priority, assignee. Verify List/Table view alternatives render.

---

### FR-023: Workspace invitation

**Existing**: Backend `workspace_invitations_router` exists. Frontend members page exists.
**Known bug**: "Invite Members" dispatches CustomEvent with no listener.

**Polish**: Fix invite button to call API directly instead of CustomEvent.

---

### FR-024: AI Providers

**Existing**: AI providers page and backend `ai_configuration_router` exist.
**Known bug**: Shows `[object Object]` error.

**Polish**: Fix error serialization to display meaningful messages.

---

### FR-025: Command palette (MAY)

**Existing**: UIStore has `commandPaletteOpen`. Likely a component exists.

**Polish**: Wire Cmd+K shortcut and verify search works. Low priority — implement only if time permits.

---

## Cross-Cutting Notes

### Backend Router Mounting Reference (from main.py)

| Router | Mount Prefix | Actual Path |
|--------|-------------|-------------|
| `ai_approvals_router` | `/api/v1` | `/api/v1/approvals/...` |
| `ai_costs_router` | `/api/v1` | `/api/v1/costs/...` |
| `ai_chat_router` | `/api/v1/ai` | `/api/v1/ai/chat/...` |
| `workspace_notes_router` | `/api/v1/workspaces` | `/api/v1/workspaces/{id}/notes/...` |
| `workspace_issues_router` | `/api/v1/workspaces` | `/api/v1/workspaces/{id}/issues/...` |

### Fix Strategy: Frontend vs Backend

For URL mismatches (FR-003, FR-004), prefer fixing the **frontend API client** to match existing backend routes rather than changing backend mounting. Backend routes are stable and tested; frontend client URLs are isolated changes.

### Testing Strategy

- Unit tests for each bug fix (especially state mapping and null checks)
- Smoke test: Login → Homepage (word counts) → Issues (Kanban columns) → AI Chat → Approvals → Costs
- Verify sidebar PINNED/RECENT after workspace load

### Known Issues from Previous Work (MEMORY.md)

These may still apply:
- RLS policies use UPPERCASE enum but DB stores lowercase → check if this affects issue state queries
- Alembic migration chain was broken in previous branch → verify before running migrations
- `_is_demo_workspace` undefined → may affect homepage endpoint
