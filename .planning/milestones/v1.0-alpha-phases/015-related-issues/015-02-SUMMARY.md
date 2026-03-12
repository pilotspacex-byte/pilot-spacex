---
phase: 015-related-issues
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, knowledge-graph, semantic-search, issue-linking, dismissal, rls]

# Dependency graph
requires:
  - phase: 015-01
    provides: IssueSuggestionDismissalRepository, IssueSuggestionDismissal model, xfail test stubs

provides:
  - GET /{wid}/issues/{iid}/related-suggestions — semantic suggestions with KG + dismissal filtering
  - POST /{wid}/issues/{iid}/related-suggestions/{tid}/dismiss — idempotent dismissal endpoint
  - POST /{wid}/issues/{iid}/relations — create RELATED IssueLink with bidirectional dup check
  - DELETE /{wid}/issues/{iid}/relations/{link_id} — soft-delete link
  - KnowledgeGraphRepositoryDep in repository_deps.py

affects: [016-workspace-role-skills, 015-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - dependency-override test pattern with mock session + patched _resolve_workspace
    - pre-generate UUID before session.flush() when mock sessions skip ORM defaults
    - direct instantiation of KnowledgeGraphRepository + IssueSuggestionDismissalRepository per request

key-files:
  created:
    - backend/src/pilot_space/api/v1/routers/related_issues.py
  modified:
    - backend/src/pilot_space/api/v1/repository_deps.py
    - backend/src/pilot_space/api/v1/routers/__init__.py
    - backend/src/pilot_space/main.py
    - backend/tests/api/test_related_issues.py

key-decisions:
  - "All 4 RELISS endpoints in single related_issues.py router (not split across workspace_issues.py) — test stubs import from related_issues, keeping them co-located avoids confusing import split"
  - "Pre-generate link UUID via uuid4() before session.flush() — SQLAlchemy default=uuid.uuid4 is flush-time, not __init__-time; mock sessions skip flush so ID stays None without pre-gen"
  - "Test pattern: dependency_overrides + patch(_resolve_workspace) — follows test_workspace_tasks.py pattern; isolates routes from DI container and live DB"
  - "RelatedSuggestion uses issue_id field (not id) — test stubs checked item['issue_id']"
  - "IssueLinkCreateResponse is a custom Pydantic model (not IssueLinkSchema) — test checks source_issue_id/target_issue_id directly, not nested related_issue object"
  - "Delete returns 404 when link not found (not idempotent 204) — plan spec explicit, test updated to match"

patterns-established:
  - "Router test pattern: mock_session.add = MagicMock() (sync) to suppress AsyncMock coroutine warning"

requirements-completed:
  - RELISS-01
  - RELISS-02
  - RELISS-03
  - RELISS-04

# Metrics
duration: 34min
completed: 2026-03-10
---

# Phase 15 Plan 02: Related Issues API Endpoints Summary

**4 REST endpoints for semantic issue suggestions, manual linking, and dismissal wired to KnowledgeGraphRepository + IssueSuggestionDismissalRepository; 8 xfail tests transitioned to 9 passing**

## Performance

- **Duration:** 34 min
- **Started:** 2026-03-10T05:20:04Z
- **Completed:** 2026-03-10T05:53:54Z
- **Tasks:** 2 (combined into 1 commit — Tasks 1+2 share the same router file)
- **Files modified:** 5

## Accomplishments
- Created `related_issues.py` router with all 4 RELISS endpoints; mounts at `/api/v1/workspaces`
- Added `KnowledgeGraphRepositoryDep` to `repository_deps.py` for future DI use
- Transitioned 8 xfail stubs to 9 real passing tests using dependency-override pattern
- Implemented bidirectional duplicate check for RELATED links (409 on A→B when B→A exists)
- Implemented idempotent dismissal (IntegrityError on UNIQUE constraint → 204 no-op)

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: Related Issues API endpoints** - `d582aac2` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified
- `backend/src/pilot_space/api/v1/routers/related_issues.py` - 4 endpoints: GET suggestions, POST dismiss, POST/DELETE relations
- `backend/src/pilot_space/api/v1/repository_deps.py` - Added KnowledgeGraphRepositoryDep
- `backend/src/pilot_space/api/v1/routers/__init__.py` - Export related_issues_router
- `backend/src/pilot_space/main.py` - Mount related_issues_router at /api/v1/workspaces
- `backend/tests/api/test_related_issues.py` - Transitioned 8 xfail stubs → 9 passing tests

## Decisions Made
- All 4 RELISS endpoints in single `related_issues.py` — test stubs import from `related_issues`, co-location avoids confusing split
- Pre-generate link UUID via `uuid4()` before `session.flush()` — SQLAlchemy `default=uuid.uuid4` is flush-time (not `__init__`-time); mock sessions skip flush, leaving ID as None without pre-gen
- Test pattern follows `test_workspace_tasks.py`: `app.dependency_overrides` + `patch(_resolve_workspace)` + `patch(set_rls_context)` for full isolation from live DB
- `RelatedSuggestion` uses `issue_id` field (not `id`) — test stubs checked `item['issue_id']`
- `IssueLinkCreateResponse` is a custom Pydantic model — tests check `source_issue_id`/`target_issue_id` directly
- DELETE returns 404 when link not found — plan spec explicit; test updated to check 404 (not 204)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test file used db_session + real app fixture, not compatible with SQLite StaticPool**
- **Found during:** Task 1 (tests ran)
- **Issue:** Original xfail tests used `authenticated_client` (real app routes via DI container) + `db_session` (in-memory SQLite). Routes use DI container DB (different from test SQLite), so workspace data written to `db_session` was invisible to routes. Also, function-scoped `test_engine` with StaticPool caused "index already exists" errors when multiple tests ran.
- **Fix:** Rewrote tests to use `app.dependency_overrides` + `patch(_resolve_workspace)` pattern (established in `test_workspace_tasks.py`), eliminating dependency on `db_session` for route isolation
- **Files modified:** `backend/tests/api/test_related_issues.py`
- **Verification:** 9 tests pass; xfailed count dropped from 40 to 32; passed count increased by 9
- **Committed in:** `d582aac2`

**2. [Rule 1 - Bug] router file name mismatch — tests import `related_issues`, plan specified `workspace_issue_suggestions`**
- **Found during:** Task 1 (analyzing test file)
- **Issue:** All 8 xfail stubs imported from `pilot_space.api.v1.routers.related_issues` but plan called for `workspace_issue_suggestions.py`
- **Fix:** Created `related_issues.py` (not `workspace_issue_suggestions.py`) to match test imports
- **Files modified:** None (design decision at creation)
- **Verification:** Router importable; tests pass

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs in test design and naming inconsistency)
**Impact on plan:** Both fixes required for tests to pass. No scope creep.

## Issues Encountered
- SQLAlchemy `default=uuid.uuid4` in `mapped_column` is applied at flush-time (not at Python object creation). Mock sessions that skip flush leave `id` as `None`. Fixed by pre-generating UUID in the router endpoint.
- Test infrastructure: `authenticated_client` uses the real DI container database, while `db_session` uses SQLite in-memory — they are separate connections. Tests that write to `db_session` cannot make routes see that data. Solution: use `app.dependency_overrides`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All RELISS-01..04 backend API contracts complete and tested
- Frontend can now consume:
  - `GET /api/v1/workspaces/{wid}/issues/{iid}/related-suggestions`
  - `POST /api/v1/workspaces/{wid}/issues/{iid}/related-suggestions/{tid}/dismiss`
  - `POST /api/v1/workspaces/{wid}/issues/{iid}/relations`
  - `DELETE /api/v1/workspaces/{wid}/issues/{iid}/relations/{link_id}`
- Phase 15 Plan 03 (frontend UI) can now proceed

---
*Phase: 015-related-issues*
*Completed: 2026-03-10*

## Self-Check: PASSED
- FOUND: backend/src/pilot_space/api/v1/routers/related_issues.py
- FOUND: .planning/phases/015-related-issues/015-02-SUMMARY.md
- FOUND: commit d582aac2
