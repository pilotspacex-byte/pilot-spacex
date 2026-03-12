---
phase: 019-skill-registry-and-plugin-system
plan: 01
subsystem: testing
tags: [pytest, vitest, xfail, tdd-stubs, wave-0]

requires:
  - phase: 016-workspace-role-skills
    provides: xfail stub pattern (test_workspace_role_skills_router.py)
provides:
  - 14 backend xfail test stubs covering SKRG-01 through SKRG-05
  - 7 frontend it.todo() stubs covering SKRG-01, SKRG-02, SKRG-04
  - backend/tests/unit/agents/ test package
affects: [019-02, 019-03, 019-04]

tech-stack:
  added: []
  patterns: [xfail-stubs-wave-0, it-todo-stubs-wave-0]

key-files:
  created:
    - backend/tests/unit/api/test_workspace_plugins_router.py
    - backend/tests/unit/services/test_install_plugin_service.py
    - backend/tests/unit/services/test_seed_plugins_service.py
    - backend/tests/unit/agents/__init__.py
    - backend/tests/unit/agents/test_plugin_skill_materializer.py
    - frontend/src/stores/ai/__tests__/PluginsStore.test.ts
    - frontend/src/features/settings/components/__tests__/plugin-card.test.tsx
  modified: []

key-decisions:
  - "No module-level imports from not-yet-existing modules in xfail stubs -- prevents collection failure"
  - "pytest.fail() inside xfail bodies (not assert False) -- satisfies PT015 and B011 ruff rules"
  - "Created backend/tests/unit/agents/ package for materializer tests -- new test subdirectory"

patterns-established:
  - "Wave 0 xfail pattern: module-level import pytest only, function-local imports for future modules"

requirements-completed: [SKRG-01, SKRG-02, SKRG-03, SKRG-04, SKRG-05]

duration: 2min
completed: 2026-03-10
---

# Phase 19 Plan 01: Test Scaffolds Summary

**Wave 0 xfail/todo stubs for skill registry plugin system: 14 backend + 7 frontend test contracts**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-10T14:55:45Z
- **Completed:** 2026-03-10T14:58:07Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- 14 backend xfail stubs across 4 files covering all 5 SKRG requirements (SKRG-01 through SKRG-05)
- 7 frontend it.todo() stubs across 2 files covering SKRG-01, SKRG-02, SKRG-04
- Created backend/tests/unit/agents/ package for future agent tests
- All stubs collect and run cleanly: pytest exits 0 (14 xfailed), vitest exits 0 (7 todo)

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend xfail stubs -- router + services** - `a8384b32` (test)
2. **Task 2: Backend xfail stub -- materializer + frontend it.todo() stubs** - `9ccd6185` (test)

## Files Created/Modified

- `backend/tests/unit/api/test_workspace_plugins_router.py` - SKRG-01/04 browse repo + update check xfail stubs
- `backend/tests/unit/services/test_install_plugin_service.py` - SKRG-02 install flow xfail stubs
- `backend/tests/unit/services/test_seed_plugins_service.py` - SKRG-05 workspace seeding xfail stubs
- `backend/tests/unit/agents/__init__.py` - New agents test package
- `backend/tests/unit/agents/test_plugin_skill_materializer.py` - SKRG-03 materialization xfail stubs
- `frontend/src/stores/ai/__tests__/PluginsStore.test.ts` - SKRG-01/02/04 store it.todo() stubs
- `frontend/src/features/settings/components/__tests__/plugin-card.test.tsx` - SKRG-01/02/04 component it.todo() stubs

## Decisions Made

- No module-level imports from not-yet-existing modules -- prevents pytest collection failure when implementation modules are absent
- pytest.fail() inside xfail bodies (not assert False) -- satisfies PT015 and B011 ruff rules without changing xfail semantics
- Created backend/tests/unit/agents/ as a new test package -- materializer tests need a home separate from ai/ tests

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Prettier reformatted frontend stub files on first commit attempt (added semicolons) -- re-staged and committed successfully on retry

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 6 test files in place as Nyquist compliance gate
- Plans 02-04 can proceed: implementations must turn xfail stubs green
- backend/tests/unit/agents/ package ready for additional agent test files

---
*Phase: 019-skill-registry-and-plugin-system*
*Completed: 2026-03-10*
