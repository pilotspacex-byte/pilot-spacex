---
phase: 27-project-hub-issue-views
plan: "02"
subsystem: notes/pages
tags: [emoji, page-tree, sidebar, ux, migration]
dependency_graph:
  requires:
    - 24-01 (Note ORM + page tree columns migration 079)
    - 26-01 (ProjectPageTree sidebar component)
  provides:
    - icon_emoji column on notes table (migration 080)
    - NoteResponse.icon_emoji in API responses
    - PageTreeNode.iconEmoji in sidebar tree
    - Emoji picker in page header (note detail page)
  affects:
    - backend/src/pilot_space/infrastructure/database/models/note.py
    - backend/src/pilot_space/api/v1/schemas/note.py
    - backend/src/pilot_space/application/services/note/update_note_service.py
    - backend/src/pilot_space/api/v1/routers/workspace_notes.py
    - frontend/src/types/note.ts
    - frontend/src/features/notes/hooks/useUpdateNote.ts
    - frontend/src/lib/tree-utils.ts
    - frontend/src/components/layout/ProjectPageTree.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx
tech_stack:
  added: []
  patterns:
    - Radix Popover for emoji picker (same pattern as PropertyChip picker)
    - TanStack Query cache invalidation on mutation (projectTreeKeys)
    - Pydantic max_length validation for emoji field
    - SQLAlchemy partial index (PostgreSQL WHERE clause) for non-null emoji
key_files:
  created:
    - backend/alembic/versions/080_add_note_icon_emoji.py
    - backend/tests/unit/schemas/test_note_icon_emoji.py
  modified:
    - backend/src/pilot_space/infrastructure/database/models/note.py
    - backend/src/pilot_space/api/v1/schemas/note.py
    - backend/src/pilot_space/application/services/note/update_note_service.py
    - backend/src/pilot_space/api/v1/routers/workspace_notes.py
    - frontend/src/types/note.ts
    - frontend/src/features/notes/hooks/useUpdateNote.ts
    - frontend/src/lib/tree-utils.ts
    - frontend/src/components/layout/ProjectPageTree.tsx
    - frontend/src/components/layout/__tests__/ProjectPageTree.test.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/__tests__/page-breadcrumb-integration.test.tsx
decisions:
  - Empty string iconEmoji maps to None (remove emoji) — service layer converts "" to NULL, schema allows empty string so client can send "" to remove
  - Partial PostgreSQL index on icon_emoji WHERE NOT NULL — minimizes index size since most pages will have no emoji
  - Emoji picker uses Radix Popover with plain text input (maxLength=10) — no heavy emoji picker library dependency; user types or pastes emoji directly
  - Query invalidation for project tree cache on emoji change — ensures sidebar updates immediately without polling
  - Added useQueryClient mock to page-breadcrumb-integration.test.tsx (Rule 2 auto-fix) — test lacked QueryClientProvider wrapper needed by new useQueryClient() call
metrics:
  duration: "51 minutes"
  completed_date: "2026-03-13"
  tasks_completed: 2
  files_changed: 11
  commits: 2
---

# Phase 27 Plan 02: Page Emoji Icons Summary

**One-liner:** Notion-style emoji icon support for pages — VARCHAR(10) DB column, full API passthrough, sidebar conditional render, and Popover picker in page header.

## What Was Built

### Backend

**Migration 080** (`080_add_note_icon_emoji.py`) adds `icon_emoji VARCHAR(10)` column to the `notes` table with a partial index (`WHERE icon_emoji IS NOT NULL`) to minimize index footprint — the majority of pages will have no emoji.

**ORM model** — `icon_emoji: Mapped[str | None]` added after `position` in `Note` model. Nullable, no server default (NULL by default).

**Schemas:**
- `NoteUpdate.icon_emoji: str | None` — validated with `max_length=10`
- `NoteResponse.icon_emoji: str | None` — returned in all note responses
- `PageTreeResponse` and `NoteDetailResponse` inherit `icon_emoji` from `NoteResponse` automatically

**Service:** `UpdateNotePayload.icon_emoji: str | None` added. Service converts empty string (`""`) to `None` (remove emoji) so clients can pass `""` to clear the icon.

**Router:** PATCH `/workspaces/{id}/notes/{noteId}` passes `icon_emoji` from `update_data` to `UpdateNotePayload`.

### Frontend

**Types:** `Note.iconEmoji` and `UpdateNoteData.iconEmoji` added to `src/types/note.ts`. `useUpdateNote.UpdateNoteData` also updated.

**tree-utils:** `PageTreeNode.iconEmoji` and `FlatNote.iconEmoji` added. `buildTree` propagates `note.iconEmoji ?? null` to tree nodes.

**ProjectPageTree:** The `FileText` icon in the page link is replaced with a conditional: emoji `<span>` when `node.iconEmoji` is set, otherwise the original `FileText` lucide icon.

**Note detail page:** Emoji zone above the editor:
- Shows existing emoji (2xl text, clickable to open picker) or `SmilePlus` icon (if no emoji)
- Radix `Popover` with `Input` (maxLength=10) and Set button
- Remove option shown when emoji exists
- `handleEmojiChange` calls `updateNote.mutate({ iconEmoji })` then invalidates `projectTreeKeys.tree(workspaceId, projectId)` so the sidebar refreshes immediately

## Tests

- 12 backend unit tests (`test_note_icon_emoji.py`) covering NoteUpdate validation, NoteResponse defaults, PageTreeResponse inheritance
- 2 new frontend tests (Tests 9 and 10 in `ProjectPageTree.test.tsx`) — emoji render path and FileText fallback
- `page-breadcrumb-integration.test.tsx` extended with `useQueryClient` mock (auto-fix for new hook dependency)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added useQueryClient mock to breadcrumb integration test**
- **Found during:** Task 2 — running breadcrumb integration tests after adding `useQueryClient()` call to `page.tsx`
- **Issue:** `page-breadcrumb-integration.test.tsx` lacked `QueryClientProvider` — `useQueryClient()` threw "No QueryClient set" at render
- **Fix:** Added `vi.mock('@tanstack/react-query', ...)` with `useQueryClient` returning a mock with `invalidateQueries`, `cancelQueries`, `getQueryData`, `setQueryData`
- **Files modified:** `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/__tests__/page-breadcrumb-integration.test.tsx`
- **Commit:** 32ff9c9a

**2. [Rule 1 - Bug] RUF012 ClassVar annotation for test class attributes**
- **Found during:** Task 1 pre-commit hook
- **Issue:** Pydantic test class had `_base_fields = {...}` as mutable class attribute without `ClassVar` annotation — ruff RUF012 error
- **Fix:** Added `ClassVar[dict[str, object]]` type annotation to `_base_fields` in both test classes
- **Files modified:** `backend/tests/unit/schemas/test_note_icon_emoji.py`
- **Commit:** 35a85c9e

**3. [Rule 1 - Bug] useUpdateNote.UpdateNoteData missing iconEmoji**
- **Found during:** Task 2 type-check
- **Issue:** `useUpdateNote.ts` has its own local `UpdateNoteData` interface separate from `types/note.ts UpdateNoteData` — TypeScript error when calling `updateNote.mutate({ iconEmoji })` in `page.tsx`
- **Fix:** Added `iconEmoji?: string | null` to `useUpdateNote.UpdateNoteData` interface
- **Files modified:** `frontend/src/features/notes/hooks/useUpdateNote.ts`
- **Commit:** 32ff9c9a

**4. [Rule 3 - Blocking] Merge conflict resolution in backend/src/pilot_space/main.py**
- **Found during:** Task 2 commit
- **Issue:** Stash/restore from prek hooks conflicted with pre-existing merge conflict markers in `main.py` (from unrelated branch merge of `user_skills_router`)
- **Fix:** Resolved conflict by keeping both sides (`user_skills_router` include retained), staged all conflict-resolved files before commit
- **Files modified:** `backend/src/pilot_space/main.py`
- **Commit:** 32ff9c9a (included in Task 2 commit)

## Self-Check

All 8 key files found. Both task commits verified: 35a85c9e (Task 1) and 32ff9c9a (Task 2).

## Self-Check: PASSED
