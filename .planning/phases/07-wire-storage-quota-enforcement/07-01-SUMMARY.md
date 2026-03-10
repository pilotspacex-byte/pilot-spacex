---
phase: 07-wire-storage-quota-enforcement
plan: 01
subsystem: testing
tags: [pytest, tdd, storage-quota, unit-tests, asyncio, mock, patch]

# Dependency graph
requires:
  - phase: 03-multi-tenant-isolation
    provides: workspace_quota.py with _check_storage_quota and _update_storage_usage helpers

provides:
  - 7 RED test stubs in tests/unit/services/test_storage_quota_wiring.py defining the wiring contract
  - Patch targets for _check_storage_quota and _update_storage_usage across workspace_issues, workspace_notes, ai_attachments routers

affects:
  - 07-02-PLAN (implements quota wiring to make these tests GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytest.raises() merged into multi-context with-statement (SIM117) for cleaner test structure"
    - "TDD RED phase: patch targets declared before imports exist; AttributeError == expected failure signal"

key-files:
  created:
    - backend/tests/unit/services/test_storage_quota_wiring.py
  modified: []

key-decisions:
  - "Tests use patch() on router module paths (not workspace_quota.py) because the contract is about wiring imports into routers, not the helpers themselves"
  - "pytest.raises() placed inside the multi-context with-statement to satisfy SIM117 without nesting — compatible with patch() context managers"
  - "All 7 tests produce FAILED (not ERROR) via AttributeError from patch() — this is the canonical RED signal for Wave 1"

patterns-established:
  - "Router wiring tests: patch _check_storage_quota and _update_storage_usage at router module scope, call router function directly (no TestClient)"
  - "Helper mock builders (_make_workspace, _make_issue_create_request) keep test bodies concise"

requirements-completed:
  - TENANT-03

# Metrics
duration: 10min
completed: 2026-03-09
---

# Phase 07 Plan 01: Write Storage Quota Wiring Test Stubs Summary

**7 TDD RED test stubs defining the TENANT-03 router wiring contract: 507 blocks, X-Storage-Warning headers, and _update_storage_usage call verification across issue create/update, note create, and attachment upload**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-09T06:20:00Z
- **Completed:** 2026-03-09T06:31:13Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `backend/tests/unit/services/test_storage_quota_wiring.py` with all 7 required test functions
- All 7 tests collected without syntax errors (`pytest --collect-only` passes)
- All 7 tests fail with `FAILED` status (not `ERROR`) — correct RED state from `AttributeError` on patch targets that don't exist yet in routers
- Lint-clean (ruff passes with zero violations); pre-commit hooks pass

## Task Commits

1. **Task 1: Write failing test stubs for all TENANT-03 wiring behaviors** - `cf8c069b` (test)

## Files Created/Modified

- `backend/tests/unit/services/test_storage_quota_wiring.py` — 7 RED test stubs: 507 block assertions, X-Storage-Warning header contract, _update_storage_usage call verification across workspace_issues, workspace_notes, ai_attachments

## Decisions Made

- Tests patch at router module paths (`pilot_space.api.v1.routers.workspace_issues._check_storage_quota`) not at `workspace_quota._check_storage_quota` — the contract is about import wiring in the routers, not the helpers themselves
- `pytest.raises()` merged into the outer multi-context `with` statement to satisfy ruff SIM117 (no nested with statements) while retaining `AttributeError`-as-failure semantics
- Helper factory functions `_make_workspace()`, `_make_issue_create_request()` etc. keep test bodies under 30 lines each — readable without fixture over-engineering

## Deviations from Plan

None — plan executed exactly as written. Lint fixes (B018 useless expression, SIM117 nested with) were minor style corrections applied before the first commit.

## Issues Encountered

Minor ruff violations on initial write: `B018` (useless expression `mock_check`) and `SIM117` (nested `with` statements). Both fixed inline before commit — merged `pytest.raises()` into the outer `with` context and removed the useless bare expression.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Test scaffold is complete; plan 02 must wire `_check_storage_quota` and `_update_storage_usage` imports into `workspace_issues.py`, `workspace_notes.py`, and `ai_attachments.py`
- Plan 02 must add quota check before the write and update call after for each path
- Tests will turn GREEN exactly when the wiring is correct — no changes to this test file required

---
*Phase: 07-wire-storage-quota-enforcement*
*Completed: 2026-03-09*
