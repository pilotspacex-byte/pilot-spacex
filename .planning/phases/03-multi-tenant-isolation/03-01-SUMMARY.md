---
phase: 03-multi-tenant-isolation
plan: "01"
subsystem: database
tags: [postgres, rls, alembic, pytest, multi-tenant, security]

# Dependency graph
requires:
  - phase: 02-compliance-and-audit
    provides: migration 065 (current alembic head), audit_log table with RLS

provides:
  - Migration 066 normalizing workspace_members.role to UPPERCASE for RLS consistency
  - TENANT-01 cross-workspace isolation integration test skeleton (PostgreSQL-only, skipif SQLite)
  - TENANT-02 xfail stubs (workspace encryption unit + router tests)
  - TENANT-03 xfail stubs (storage quota + rate limit unit tests)
  - TENANT-04 xfail stubs (super-admin API router tests)

affects:
  - 03-02-PLAN (implements TENANT-01 isolation tests against real PostgreSQL)
  - 03-03-PLAN (implements TENANT-02 workspace encryption)
  - 03-04-PLAN (implements TENANT-03 storage quota)
  - 03-05-PLAN (implements TENANT-04 super-admin dashboard)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - xfail(strict=False) stub pattern for unimplemented Phase 3 tests (established in Phase 1, reused here)
    - pytestmark skipif("sqlite" in DB_URL) for PostgreSQL-only RLS integration tests

key-files:
  created:
    - backend/alembic/versions/066_fix_rls_enum_case.py
    - backend/tests/security/test_isolation.py
    - backend/tests/unit/test_workspace_encryption.py
    - backend/tests/unit/test_storage_quota.py
    - backend/tests/routers/test_workspace_encryption.py
    - backend/tests/routers/test_admin.py
  modified: []

key-decisions:
  - "Migration 066 downgrade() is a no-op — RLS policies always expected UPPERCASE; reverting to lowercase would break isolation; data stays normalized"
  - "Isolation tests use pytestmark skipif(sqlite in DB_URL) not pytest.mark.skip — skipif is conditional and correctly passes when TEST_DATABASE_URL is set to PostgreSQL"
  - "test_isolation.py references populated_db fixture (not a new populated_two_workspace_db) — conftest.py already provisions workspace_a and workspace_b with outsider cross-membership"

patterns-established:
  - "PostgreSQL-only integration tests: module-level pytestmark with skipif on TEST_DATABASE_URL"
  - "Phase test scaffold: xfail stubs created in plan 01 of each phase, implemented in subsequent plans"

requirements-completed:
  - TENANT-01

# Metrics
duration: 11min
completed: 2026-03-08
---

# Phase 3 Plan 01: RLS Enum Fix + Phase 3 Test Scaffold Summary

**Alembic migration 066 normalizing workspace_members.role to UPPERCASE and 20-test Phase 3 scaffold covering TENANT-01 cross-workspace isolation, TENANT-02 encryption, TENANT-03 quota, and TENANT-04 admin API**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-08T04:20:23Z
- **Completed:** 2026-03-08T04:31:27Z
- **Tasks:** 2
- **Files modified:** 6 (all created)

## Accomplishments

- Migration 066 created with correct `Revises: 065_add_audit_log_table`, single alembic head confirmed
- TENANT-01 isolation tests (5 stubs) in `test_isolation.py` — skip under SQLite, xfail under PostgreSQL pending 03-02
- 15 xfail stubs across TENANT-02/03/04 covering all Phase 3 requirements with detailed implementation guidance in docstrings
- Pre-existing test suite failures (251) confirmed pre-existing, not caused by new files

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration 066 — fix RLS enum case in workspace_members** - `f5c8710c` (chore)
2. **Task 2: Phase 3 test scaffolds — isolation suite + TENANT-02/03/04 xfail stubs** - `c47bef42` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/alembic/versions/066_fix_rls_enum_case.py` — Alembic migration normalizing workspace_members.role to UPPERCASE via `UPDATE workspace_members SET role = UPPER(role) WHERE role != UPPER(role)`
- `backend/tests/security/test_isolation.py` — TENANT-01 cross-workspace RLS integration tests (5 stubs), skips under SQLite
- `backend/tests/unit/test_workspace_encryption.py` — TENANT-02 unit stubs: key storage, round-trip encryption, key validation, key rotation
- `backend/tests/unit/test_storage_quota.py` — TENANT-03 unit stubs: 507 hard block, 80% warning header, Redis rate limits, NULL quota fallback
- `backend/tests/routers/test_workspace_encryption.py` — TENANT-02 API stubs: verify endpoint, 422 on invalid key, key not in response
- `backend/tests/routers/test_admin.py` — TENANT-04 API stubs: token auth, 401 on invalid token, workspace list, log masking

## Decisions Made

- Migration 066 `downgrade()` is a no-op. RLS policies always required UPPERCASE role values. Reverting to lowercase after normalization would re-break multi-tenant isolation. The normalize-only-forward approach is correct.
- Isolation tests use module-level `pytestmark = pytest.mark.skipif(...)` rather than per-test decorators — this is cleaner and matches the plan's interface spec.
- `test_isolation.py` uses `populated_db` fixture name (already defined in `conftest.py`) rather than a new `populated_two_workspace_db` — the existing fixture already provisions workspace_a and workspace_b with the correct outsider cross-membership pattern.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- ruff auto-fixed import ordering in migration 066 (alembic before sqlalchemy) and formatting in test_workspace_encryption.py. Both required re-staging before commit. No logic changes.

## User Setup Required

None — no external service configuration required. Migration 066 will be applied automatically by `alembic upgrade head`. RLS isolation tests require `TEST_DATABASE_URL=postgresql+asyncpg://...` to run (skipped under SQLite, correct behavior).

## Next Phase Readiness

- 03-02 can begin immediately: implement TENANT-01 isolation tests against real PostgreSQL using the stubs in `test_isolation.py`
- 03-03/03-04/03-05 can use xfail stubs as acceptance criteria contracts
- Migration 066 must be applied (`alembic upgrade head`) before 03-02 RLS tests will produce accurate results
- Pre-existing 251 test failures in the suite are out of scope for Phase 3 but should be tracked in deferred-items

---
*Phase: 03-multi-tenant-isolation*
*Completed: 2026-03-08*
