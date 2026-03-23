---
phase: quick
plan: "01"
subsystem: notes
tags: [bug-fix, cycle-guard, serialization, error-codes, row-locking, sentinel-pattern, memoization, pagination]
dependency_graph:
  requires: []
  provides: [PR-32-fixes-complete]
  affects: [move_page_service, update_note_service, workspace_notes_router, note_repository, note_detail_page, project_page_tree]
tech_stack:
  added: []
  patterns: [UNSET-sentinel, for-update-locking, pagination-loop, useMemo-stabilization]
key_files:
  created:
    - backend/tests/unit/services/test_update_note_service.py
  modified:
    - backend/src/pilot_space/application/services/note/move_page_service.py
    - backend/src/pilot_space/application/services/note/update_note_service.py
    - backend/src/pilot_space/api/v1/routers/workspace_notes.py
    - backend/src/pilot_space/infrastructure/database/repositories/note_repository.py
    - backend/tests/unit/services/conftest.py
    - backend/tests/unit/services/test_move_page_service.py
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx
    - frontend/src/features/notes/hooks/useProjectPageTree.ts
decisions:
  - "UNSET sentinel exported from update_note_service.py so router can import and use it without re-defining"
  - "for_update param on get_siblings defaults to False to preserve backward compat; MovePageService always passes True"
  - "Cycle guard checks descendant_ids AFTER fetching descendants (reuses the same query result)"
  - "Pagination loop in useProjectPageTree uses item accumulation with spread; acceptable for page tree sizes"
metrics:
  duration: "25 minutes"
  completed_date: "2026-03-13"
  tasks_completed: 2
  files_changed: 10
---

# Quick Task 01: Fix PR #32 CodeRabbit Review Comments Summary

All 8 issues from the PR #32 CodeRabbit review addressed with corresponding tests.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix backend issues 1-6 | d9109865 | move_page_service.py, update_note_service.py, workspace_notes.py, note_repository.py, conftest.py, test_move_page_service.py, test_update_note_service.py |
| 2 | Fix frontend issues 7-8 | 7a4ea008, cb469ba1 | useProjectPageTree.ts, page.tsx |

## Issues Fixed

### Issue 1 — Self-parenting cycle guard (Critical)

`MovePageService.execute` now raises `ValueError("Cannot move a page to itself")` when `new_parent_id == note.id`, checked immediately after fetching the note. An ancestor-descendant cycle check was added after `get_descendants`: if `new_parent_id` appears in `descendant_ids`, raises `ValueError` containing "cycle".

**File:** `backend/src/pilot_space/application/services/note/move_page_service.py`

### Issue 2 — icon_emoji in response builders

Added `icon_emoji=note.icon_emoji` to all three response builders in `workspace_notes.py`:
- `_note_to_response()`
- `_note_to_detail_response()`
- `_note_to_tree_response()`

The `NoteResponse` schema already had `icon_emoji: str | None` — the builders were just not passing it.

**File:** `backend/src/pilot_space/api/v1/routers/workspace_notes.py`

### Issue 3 — 404 vs 422 error mapping

`move_page` and `reorder_page` handlers now inspect the `ValueError` message for "not found" (case-insensitive) and return 404; all other validation errors return 422.

**File:** `backend/src/pilot_space/api/v1/routers/workspace_notes.py`

### Issue 4 — Tail-slot FOR UPDATE locking

Added `for_update: bool = False` parameter to `NoteRepository.get_siblings`. When `True`, applies `.with_for_update()` to the query (serializes concurrent position reads in PostgreSQL). `MovePageService._compute_tail_position` now calls with `for_update=True`.

**File:** `backend/src/pilot_space/infrastructure/database/repositories/note_repository.py`

### Issue 5 — Emoji clear semantics (UNSET sentinel)

Replaced `icon_emoji: str | None = None` with an `UNSET` sentinel (module-level `object()`) in `UpdateNotePayload`. The logic now:
- `UNSET` (field omitted) → no-op, existing emoji preserved
- `None` (explicit null) → clears emoji (sets DB field to NULL)
- `""` or whitespace-only → treats as clear, stores NULL
- Non-empty string → sets new emoji value

Router updated to pass `update_data.get("icon_emoji", UNSET)` to distinguish between `null` sent by client vs field absent from JSON body.

**File:** `backend/src/pilot_space/application/services/note/update_note_service.py`

### Issue 6 — SQLite test DDL

Added `icon_emoji TEXT,` column to the `notes` CREATE TABLE statement in `backend/tests/unit/services/conftest.py` (after `last_edited_by_id`).

**File:** `backend/tests/unit/services/conftest.py`

### Issue 7 — Memoize sanitizeNoteContent

Added `const sanitizedContent = useMemo(() => sanitizeNoteContent(note?.content), [note?.content])` with the other memo hooks (before early returns). The NoteCanvas `content` prop now receives `{sanitizedContent}` instead of an inline `{sanitizeNoteContent(note.content)}` call that created a new object reference every render.

**File:** `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx`

### Issue 8 — Project tree pagination

Replaced the capped `notesApi.list(workspaceId, { projectId }, 1, 100)` with a `while (hasNext)` pagination loop that accumulates all pages into `allItems`. Projects with more than 100 pages are now fully loaded.

**File:** `frontend/src/features/notes/hooks/useProjectPageTree.ts`

## Tests Added

| File | Count | Coverage |
|------|-------|---------|
| test_move_page_service.py | +4 new tests | self-parenting, cycle, for_update call verification |
| test_update_note_service.py | 8 tests (new file) | UNSET/None/empty/whitespace/set emoji semantics, not-found, title trim, no-op |

Total: 20 tests (12 existing + 8 new), all passing.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist:
- FOUND: backend/src/pilot_space/application/services/note/move_page_service.py
- FOUND: backend/src/pilot_space/application/services/note/update_note_service.py
- FOUND: backend/src/pilot_space/api/v1/routers/workspace_notes.py
- FOUND: backend/src/pilot_space/infrastructure/database/repositories/note_repository.py
- FOUND: backend/tests/unit/services/conftest.py
- FOUND: backend/tests/unit/services/test_move_page_service.py
- FOUND: backend/tests/unit/services/test_update_note_service.py
- FOUND: frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx
- FOUND: frontend/src/features/notes/hooks/useProjectPageTree.ts

Commits exist:
- FOUND: d9109865 (backend fixes 1-6)
- FOUND: 7a4ea008 (frontend Issue 8 pagination)
- FOUND: cb469ba1 (frontend Issue 7 memoize)
