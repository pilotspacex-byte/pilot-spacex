---
phase: quick-11
plan: 01
subsystem: api,frontend
tags: [bugfix, ai-configuration, note-issue-link, type-alignment]
dependency_graph:
  requires: []
  provides:
    - "AI config POST accepts workspace_id as query param"
    - "NoteIssueLink(EXTRACTED) created on issue extraction"
    - "Frontend NoteIssueLink type aligned with backend"
  affects:
    - "frontend/src/features/settings/components/custom-provider-form.tsx"
    - "backend/src/pilot_space/api/v1/routers/workspace_notes_ai.py"
    - "frontend/src/types/issue.ts"
    - "frontend/src/features/issues/components/source-notes-list.tsx"
    - "frontend/src/features/issues/components/note-preview-card.tsx"
    - "frontend/src/features/issues/components/issue-graph.tsx"
tech_stack:
  added: []
  patterns:
    - "FastAPI query param vs body field resolution"
    - "session.add() for NoteIssueLink inside extraction loop"
    - "Lowercase enum string values for frontend/backend alignment"
key_files:
  created:
    - "backend/tests/unit/routers/test_ai_configuration_workspace_id.py"
    - "backend/tests/unit/routers/test_create_extracted_issues_links.py"
  modified:
    - "backend/src/pilot_space/api/v1/routers/workspace_notes_ai.py"
    - "frontend/src/features/settings/components/custom-provider-form.tsx"
    - "frontend/src/types/issue.ts"
    - "frontend/src/features/issues/components/source-notes-list.tsx"
    - "frontend/src/features/issues/components/note-preview-card.tsx"
    - "frontend/src/features/issues/components/issue-graph.tsx"
    - "frontend/src/features/ai/ChatView/MessageList/ContextCards.tsx"
    - "frontend/src/features/issues/components/__tests__/source-notes-list.test.tsx"
    - "frontend/src/features/issues/components/__tests__/issue-graph.test.tsx"
    - "frontend/src/features/issues/components/__tests__/note-preview-card.test.tsx"
    - "frontend/src/features/issues/components/__tests__/issue-properties-panel.test.tsx"
    - "frontend/src/features/issues/components/__tests__/issue-chat-empty-state.test.tsx"
decisions:
  - "Fixed frontend to send workspace_id as query param (not in body) to match FastAPI resolution"
  - "Added NoteIssueLink creation inside extraction loop before session.commit"
  - "Changed frontend linkType union to lowercase to match backend NoteLinkType string values"
  - "Replaced CREATED with related in frontend test fixtures (CREATED does not exist in backend)"
metrics:
  duration: "~18 minutes"
  completed_date: "2026-03-15"
  tasks: 3
  files: 12
---

# Phase quick-11 Plan 01: Fix Browser-Testing Issues Summary

Three bugs found during browser testing fixed: AI configuration POST returning 500 due to workspace_id body vs query-param mismatch, create_extracted_issues not persisting NoteIssueLink traceability records, and frontend/backend link type enum case mismatch.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Fix AI config workspace_id query param and NoteIssueLink creation | 54c6cce8 | Done |
| 2 | Align frontend NoteIssueLink type with backend NoteLinkType enum | d4a62dd5 | Done |
| 3 | Run quality gates on both backend and frontend | (verification) | Done |

## What Was Built

### Bug 1: AI Config POST returning 500 (workspace_id resolution)

**Root cause:** `custom-provider-form.tsx` sent `workspace_id` inside the POST body. The backend's `create_ai_configuration` signature has `workspace_id: UUID` as a direct parameter (not inside the Pydantic schema), so FastAPI treats it as a **query parameter**. The body field was ignored, causing the endpoint to fail with a 422/500.

**Fix:** Changed the `apiClient.post` call to pass `workspace_id` via `params`:
```ts
await apiClient.post('/ai/configurations', { ...body }, { params: { workspace_id: workspaceId } })
```

This matches how `loadModels` already sends `workspace_id` as a query param.

### Bug 2: create_extracted_issues not creating NoteIssueLink records

**Root cause:** The endpoint created issues but never called `session.add(NoteIssueLink(...))`, so extraction had no traceability back to the source note.

**Fix:** Added NoteIssueLink creation inside the extraction loop:
```python
link = NoteIssueLink(
    note_id=note_id,
    issue_id=result.issue.id,
    link_type=NoteLinkType.EXTRACTED,
    block_id=extracted.source_block_id,
    workspace_id=workspace.id,
)
session.add(link)
```
The existing `await session.commit()` at the end of the loop persists both issues and links atomically.

### Bug 3: Frontend/backend link type enum mismatch

**Root cause:** Backend `NoteLinkType` string values are lowercase (`"extracted"`, `"referenced"`, `"related"`, `"inline"`). Frontend had `'CREATED' | 'EXTRACTED' | 'REFERENCED'` — uppercase, wrong values, and missing `related`/`inline`.

**Fix:** Updated `NoteIssueLink.linkType` type to lowercase union matching backend exactly:
```ts
linkType: 'extracted' | 'referenced' | 'related' | 'inline';
```

Updated all consumers: `source-notes-list.tsx`, `note-preview-card.tsx`, `issue-graph.tsx`, `ContextCards.tsx`, and all test files.

## Quality Gates

| Gate | Result |
|------|--------|
| Backend ruff lint | PASS (0 errors) |
| Backend pyright | PASS (0 errors) |
| Backend pytest (unit) | PASS (3972 passed, 0 failed) |
| Frontend ESLint | PASS (0 errors, 21 pre-existing warnings) |
| Frontend tsc --noEmit | PASS (0 errors) |
| Frontend vitest (modified files) | PASS (35/35 tests pass) |

Note: Frontend vitest has 223 pre-existing failures in unrelated files (QueryClient setup issues in `issue-properties-panel.test.tsx`, NoteCanvasEditor, etc.) — confirmed identical failures on `main` before this work.

## Deviations from Plan

**1. [Rule 2 - Missing handling] session.add uses MagicMock, not AsyncMock**
- **Found during:** Task 1 TDD RED phase
- **Issue:** `AsyncMock()` wraps all attributes (including `.add`) as coroutines. `session.add()` in SQLAlchemy is synchronous, causing the test's `added_objects` list to stay empty.
- **Fix:** Overrode `session.add = MagicMock(side_effect=...)` explicitly after creating the `AsyncMock` session.
- **Files modified:** `test_create_extracted_issues_links.py`

**2. [Rule 2 - Missing handling] E741 ambiguous variable name in tests**
- **Found during:** Task 1 pre-commit hook
- **Issue:** ruff flagged `l` as ambiguous variable name in generator expression.
- **Fix:** Renamed to `lnk` in generator expressions.

**3. [Rule 2 - Missing handling] Additional files using uppercase linkType**
- **Found during:** Task 2 type-check run
- **Issue:** 5 additional files also used uppercase `linkType` values: `note-preview-card.tsx`, `issue-graph.tsx`, `ContextCards.tsx`, and 3 test files.
- **Fix:** Updated all to use lowercase values matching backend enum.

## Self-Check: PASSED

All files present:
- [x] `backend/src/pilot_space/api/v1/routers/workspace_notes_ai.py` — FOUND
- [x] `frontend/src/features/settings/components/custom-provider-form.tsx` — FOUND
- [x] `frontend/src/types/issue.ts` — FOUND
- [x] `backend/tests/unit/routers/test_ai_configuration_workspace_id.py` — FOUND
- [x] `backend/tests/unit/routers/test_create_extracted_issues_links.py` — FOUND

All commits present:
- [x] `54c6cce8` — fix AI config workspace_id query param and NoteIssueLink creation — FOUND
- [x] `d4a62dd5` — align frontend NoteIssueLink type with backend NoteLinkType enum — FOUND
