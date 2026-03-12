---
phase: 015-related-issues
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, rls, pytest, xfail, vitest, todo-stubs, dismissal]

# Dependency graph
requires:
  - phase: 014-remote-mcp-server-management
    provides: WorkspaceScopedModel and RLS migration patterns (migration 071 as down_revision)
  - phase: 001-identity-and-access
    provides: users table FK target for user_id; WorkspaceScopedModel base

provides:
  - xfail test harness for RELISS-01..04 (8 tests, all XFAIL)
  - it.todo frontend stubs for RelatedIssuesPanel (5 todos)
  - IssueSuggestionDismissal SQLAlchemy model with UniqueConstraint + composite indexes
  - IssueSuggestionDismissalRepository with get_dismissed_target_ids + create_dismissal
  - Alembic migration 072 with RLS enabled + service_role bypass

affects: [015-02, 015-03, 015-04, 015-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - xfail(strict=False) with pytest.fail() body for Wave 0 test stubs (PT015/B011 ruff-compliant)
    - Direct instantiation repository pattern (no DI container) consistent with KG/SCIM repos
    - UNIQUE constraint as idempotency guard for dismissal upserts

key-files:
  created:
    - backend/tests/api/test_related_issues.py
    - frontend/src/features/issues/components/__tests__/related-issues-panel.test.tsx
    - backend/src/pilot_space/infrastructure/database/models/issue_suggestion_dismissal.py
    - backend/src/pilot_space/infrastructure/database/repositories/issue_suggestion_dismissal_repository.py
    - backend/alembic/versions/072_add_issue_suggestion_dismissals.py
  modified: []

key-decisions:
  - "pytest.fail() instead of assert False for xfail stubs — satisfies PT015 and B011 ruff rules without changing xfail semantics"
  - "IssueSuggestionDismissalRepository uses direct instantiation (not DI) — lightweight per-request helper, consistent with KnowledgeGraphRepository/SCIM pattern"
  - "UNIQUE constraint (user_id, source_issue_id, target_issue_id) as idempotency guard — callers catch IntegrityError and treat as no-op rather than pre-checking"
  - "Composite indexes (workspace_id, source_issue_id) and (workspace_id, user_id) — two primary query access patterns for filtering suggestions"

patterns-established:
  - "Wave 0 xfail stubs: function-local imports inside xfail test bodies prevent collection failure when router doesn't exist yet"
  - "Frontend Wave 0: it.todo() in describe block without component import — avoids build error before component is built"

requirements-completed: [RELISS-01, RELISS-02, RELISS-03, RELISS-04]

# Metrics
duration: 6min
completed: 2026-03-10
---

# Phase 15 Plan 01: Related Issues Scaffolding Summary

**Wave 0 scaffolding: 8 xfail backend stubs + 5 frontend todos + IssueSuggestionDismissal model/repo/migration 072 with RLS**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-10T05:10:18Z
- **Completed:** 2026-03-10T05:16:04Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- 8 xfail(strict=False) test stubs covering RELISS-01..04 — all XFAIL, zero errors, ready to drive TDD implementation in plans 02-04
- 5 `it.todo()` frontend stubs for RelatedIssuesPanel — pending state communicates intent-to-implement, no component import to cause build errors
- IssueSuggestionDismissal model + repository + migration 072 — complete persistence layer for RELISS-04 dismissal, including RLS workspace isolation and service_role bypass

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend xfail test stubs for RELISS-01..04** - `49c86695` (test)
2. **Task 2: Frontend it.todo stubs for RELISS-01 and RELISS-04** - `0776bddf` (test)
3. **Task 3: IssueSuggestionDismissal model, repository, and migration 072** - `8cfa0d12` (feat)

**Plan metadata:** (docs: this SUMMARY.md commit)

## Files Created/Modified

- `backend/tests/api/test_related_issues.py` - 8 xfail stubs for RELISS-01..04 with function-local imports
- `frontend/src/features/issues/components/__tests__/related-issues-panel.test.tsx` - 5 it.todo stubs for RelatedIssuesPanel
- `backend/src/pilot_space/infrastructure/database/models/issue_suggestion_dismissal.py` - IssueSuggestionDismissal SQLAlchemy model
- `backend/src/pilot_space/infrastructure/database/repositories/issue_suggestion_dismissal_repository.py` - Repository with get_dismissed_target_ids + create_dismissal
- `backend/alembic/versions/072_add_issue_suggestion_dismissals.py` - Migration 072 (down_revision=071, RLS enabled)

## Decisions Made

- **pytest.fail() for xfail stubs**: `assert False` triggers PT015 (PT rule) and B011 (bugbear) ruff errors. `pytest.fail("Not implemented")` is semantically identical for xfail but lint-clean.
- **Direct instantiation repository**: IssueSuggestionDismissalRepository follows the KnowledgeGraphRepository / SCIM pattern — instantiated directly with session, no DI container registration needed. Simple, lightweight, no wiring complexity.
- **UNIQUE constraint as idempotency guard**: Rather than pre-checking existence before insert, callers catch IntegrityError and treat it as a no-op. This is the standard approach for dismissal patterns (same as DigestDismissal intent).
- **Composite indexes**: Two access patterns identified — filtering suggestions per source issue (`workspace_id, source_issue_id`) and admin queries per user (`workspace_id, user_id`) — both indexed upfront.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced `assert False` with `pytest.fail()` to satisfy ruff PT015/B011**
- **Found during:** Task 1 commit (pre-commit hook failure)
- **Issue:** ruff PT015 flags `assert False` as "Assertion always fails, replace with pytest.fail()" and B011 flags `assert False` as disallowed. The plan specified `assert False, "Not implemented"` but this triggers lint failures.
- **Fix:** Replaced all 8 `assert False, "Not implemented"` instances with `pytest.fail("Not implemented")`. Semantics for xfail are identical.
- **Files modified:** `backend/tests/api/test_related_issues.py`
- **Verification:** `uv run pytest tests/api/test_related_issues.py -x -q` still shows 8 XFAIL, ruff passes
- **Committed in:** `49c86695` (Task 1 commit, second attempt)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Lint-only fix, no semantic change to test behavior. All xfail tests function identically.

## Issues Encountered

- `alembic check` reports "Target database is not up to date" — expected behavior in dev environment where migration 072 has not been applied yet. `alembic heads` confirms single head `072_add_issue_suggestion_dismissals` which is the correct state for a newly added migration.

## User Setup Required

None - no external service configuration required. Migration 072 must be applied before RELISS-04 endpoints are tested against a live database.

## Next Phase Readiness

- Test harness ready: plans 02-04 can implement endpoints and watch xfail → xpass progression
- Dismissal data layer complete: plan 03 (suggestions endpoint) can import and use IssueSuggestionDismissalRepository immediately
- Migration 072 chain intact at single head: plan 05 can add migration 073 with `down_revision = "072_add_issue_suggestion_dismissals"`

---
*Phase: 015-related-issues*
*Completed: 2026-03-10*
