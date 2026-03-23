---
phase: 26-sidebar-tree-navigation
plan: "01"
subsystem: notes-tree
tags: [backend, frontend, tree, tanstack-query, mobx, tdd]
dependency_graph:
  requires:
    - "24-01: Note model tree columns (parent_id, depth, position)"
    - "25-01: NoteRepository.get_children() and get_siblings()"
  provides:
    - "NoteCreate schema with parent_id field"
    - "CreateNoteService depth/position computation from parent"
    - "buildTree and getAncestors frontend utilities"
    - "useProjectPageTree and usePersonalPages TanStack Query hooks"
    - "UIStore.expandedNodes with MobX observable Set and localStorage persistence"
  affects:
    - "26-02: Sidebar tree UI components consume these hooks and UIStore"
tech_stack:
  added:
    - "frontend/src/lib/tree-utils.ts: buildTree (two-pass flat->nested), getAncestors"
  patterns:
    - "TDD: RED->GREEN for all 3 tasks"
    - "MagicMock strategy for service unit tests (avoids SQLAlchemy ORM instrumentation)"
    - "MobX observable Set annotation for fine-grained Set mutation tracking"
    - "TanStack Query select transform for tree construction"
key_files:
  created:
    - backend/tests/unit/services/test_create_note_service_tree.py
    - frontend/src/lib/tree-utils.ts
    - frontend/src/lib/__tests__/tree-utils.test.ts
    - frontend/src/features/notes/hooks/useProjectPageTree.ts
    - frontend/src/features/notes/hooks/usePersonalPages.ts
    - frontend/src/stores/__tests__/UIStore.test.ts
  modified:
    - backend/src/pilot_space/api/v1/schemas/note.py
    - backend/src/pilot_space/application/services/note/create_note_service.py
    - frontend/src/types/note.ts
    - frontend/src/features/notes/hooks/index.ts
    - frontend/src/stores/UIStore.ts
    - frontend/src/services/api/notes.ts
decisions:
  - "Used get_children() (not get_siblings()) in CreateNoteService for position computation — no exclude_note_id needed during creation since note doesn't exist yet"
  - "notesApi.update() changed from Partial<CreateNoteData> to Partial<UpdateNoteData> — fixes null parentId type incompatibility discovered when adding parentId to Note type"
  - "MobX expandedNodes annotated as observable in makeAutoObservable overrides — standard Set is not reactive without explicit annotation (RESEARCH.md Pitfall 2)"
  - "usePersonalPages filters client-side (no projectId) — backend lacks project_id=null filter, acceptable at 5-100 member scale"
metrics:
  duration_seconds: 668
  completed_date: "2026-03-12"
  tasks_completed: 3
  tasks_total: 3
  files_created: 6
  files_modified: 6
  tests_added: 26
requirements:
  - NAV-01
  - NAV-02
  - NAV-03
---

# Phase 26 Plan 01: Tree Foundation — Data Layer Summary

**One-liner:** Backend parent_id depth enforcement + frontend buildTree/getAncestors utilities + TanStack Query hooks + MobX observable expandedNodes with localStorage persistence.

## What Was Built

### Task 1: Backend parent_id Support

Added `parent_id: UUID | None` to both `NoteCreate` schema and `CreateNotePayload` dataclass. `CreateNoteService.execute()` now:

1. Rejects personal page nesting (parent_id without project_id)
2. Fetches parent note, raises ValueError if not found
3. Enforces depth <= 2 (raises ValueError if parent.depth == 2)
4. Calls `get_children(parent_id)` to find existing children, computes `position = max_child_position + 1000` (or 1000 for first child)
5. Passes `parent_id`, `depth`, `position` to the Note constructor

8 unit tests in `test_create_note_service_tree.py` cover all behavioral specifications.

### Task 2: Frontend Types + Tree Utilities

Extended `Note` interface with `parentId?: string | null`, `depth?: number`, `position?: number`. Extended `CreateNoteData` with `parentId?: string`.

Created `frontend/src/lib/tree-utils.ts`:
- `buildTree()`: Two-pass O(n) algorithm — pass 1 builds id->node map, pass 2 attaches children to parents collecting roots. Orphan nodes (missing parent) promoted to roots. All children sorted by position ascending.
- `getAncestors()`: Traverses parentId chain root-first, stops on missing parent.

12 unit tests cover all plan behaviors including orphans, sorting, empty input, partial chains.

Also fixed: `notesApi.update()` now accepts `Partial<UpdateNoteData>` instead of `Partial<CreateNoteData>` — required because `Note.parentId` is `string | null | undefined` and `null` is incompatible with `CreateNoteData.parentId: string | undefined`.

### Task 3: TanStack Query Hooks + UIStore Expand State

- `useProjectPageTree(workspaceId, projectId)`: Queries all project notes (page=1, size=100), transforms via `buildTree` in `select`. Uses `projectTreeKeys` for cache key namespacing.
- `usePersonalPages(workspaceId)`: Queries all workspace notes, filters client-side to those without `projectId`. Uses `personalPagesKeys`.
- Both hooks exported from `features/notes/hooks/index.ts` barrel.

`UIStore` additions:
- `expandedNodes: Set<string>` annotated as `observable` in `makeAutoObservable` overrides (critical for Set mutation tracking)
- `toggleNodeExpanded(nodeId)`: add/remove from Set
- `isNodeExpanded(nodeId)`: query Set
- `PersistedUIState` extended with `expandedNodes: string[]`
- `setupPersistence()` reaction serializes `Array.from(expandedNodes)`
- `loadFromStorage()` restores `new Set(state.expandedNodes ?? [])`

6 UIStore tests cover toggle, isExpanded, localStorage serialization, hydration, and MobX reactivity.

## Test Summary

| Suite | Tests | Result |
|-------|-------|--------|
| backend/test_create_note_service_tree.py | 8 | PASS |
| frontend/tree-utils.test.ts | 12 | PASS |
| frontend/UIStore.test.ts | 6 | PASS |
| **Total** | **26** | **PASS** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used `get_children` instead of `get_siblings` in CreateNoteService**
- **Found during:** Task 1 implementation
- **Issue:** Plan's action spec said "Fetch siblings via `self._note_repo.get_siblings()`" but `get_siblings` requires an `exclude_note_id: UUID` — the new note doesn't have an ID yet during creation.
- **Fix:** Used `get_children(parent_id)` instead, which returns all current children without exclusion requirement. Correct for position computation.
- **Files modified:** `create_note_service.py`, `test_create_note_service_tree.py`
- **Commit:** 3dea3e9e

**2. [Rule 2 - Missing Type Fix] Changed `notesApi.update()` from `Partial<CreateNoteData>` to `Partial<UpdateNoteData>`**
- **Found during:** Task 2 type-check
- **Issue:** Adding `parentId?: string | null` to `Note` interface caused `NoteStore.updateNote(data: Partial<Note>)` to fail type-check because `null` is not assignable to `string | undefined`.
- **Fix:** `notesApi.update()` now uses `Partial<UpdateNoteData>` which correctly models partial update payloads.
- **Files modified:** `frontend/src/services/api/notes.ts`
- **Commit:** 641bc23f

**3. [Rule 3 - Test Fix] Raw string for regex in pytest.raises match**
- **Found during:** Task 1 commit (pre-commit hook ruff RUF043)
- **Issue:** `match="(?i)parent"` requires raw string `r"(?i)parent"` per ruff RUF043.
- **Fix:** Changed to `match=r"(?i)parent"`.
- **Files modified:** `test_create_note_service_tree.py`
- **Commit:** 3dea3e9e

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `backend/tests/unit/services/test_create_note_service_tree.py` | FOUND |
| `frontend/src/lib/tree-utils.ts` | FOUND |
| `frontend/src/features/notes/hooks/useProjectPageTree.ts` | FOUND |
| `frontend/src/features/notes/hooks/usePersonalPages.ts` | FOUND |
| `frontend/src/stores/__tests__/UIStore.test.ts` | FOUND |
| Commit `3dea3e9e` (Task 1) | FOUND |
| Commit `641bc23f` (Task 2) | FOUND |
| Commit `ba1950de` (Task 3) | FOUND |
