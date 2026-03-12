---
phase: 016-workspace-role-skills
plan: "01"
subsystem: testing
tags: [pytest, vitest, xfail, tdd, workspace-role-skills, stubs]

# Dependency graph
requires:
  - phase: 015-related-issues
    provides: xfail stub patterns (pytest.fail, strict=False, it.todo)
provides:
  - 13 backend xfail stubs across 3 new test files (WRSKL-01..03)
  - 2 materializer xfail stubs appended to existing file (WRSKL-03..04)
  - 5 frontend it.todo() stubs for WorkspaceSkillCard component (WRSKL-01..02)
  - 4 frontend it.todo() stubs for workspace-role-skills API client (WRSKL-01..02)
affects: [016-02-impl-model-repo, 016-03-impl-service-router, 016-04-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "xfail stubs: pytest.mark.xfail(strict=False) + pytest.fail('not implemented') body"
    - "frontend stubs: it.todo() for Vitest pending state, import only from vitest"
    - "pytestmark = pytest.mark.asyncio at module level to avoid per-test decorator"

key-files:
  created:
    - backend/tests/unit/repositories/test_workspace_role_skill_repository.py
    - backend/tests/unit/services/test_workspace_role_skill_service.py
    - backend/tests/unit/api/test_workspace_role_skills_router.py
    - frontend/src/features/settings/components/__tests__/workspace-skill-card.test.tsx
    - frontend/src/services/api/__tests__/workspace-role-skills.test.ts
  modified:
    - backend/tests/unit/ai/agents/test_role_skill_materializer.py

key-decisions:
  - "No imports from not-yet-existing modules in stubs — prevents import failures from breaking whole test file"
  - "pytestmark = pytest.mark.asyncio used instead of per-test decorator — matches pattern from test_workspace_role_skill_repository.py"

patterns-established:
  - "Wave 0 stubs: create before implementation so automated verify commands run from Plan 02 onward"

requirements-completed: [WRSKL-01, WRSKL-02, WRSKL-03, WRSKL-04]

# Metrics
duration: 8min
completed: 2026-03-10
---

# Phase 16 Plan 01: Workspace Role Skills Wave 0 Stubs Summary

**15 xfail/todo stubs across 6 files establishing TDD baseline for admin-generated workspace role skills (WRSKL-01..04)**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-10T15:00:00Z
- **Completed:** 2026-03-10T15:08:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- 13 backend xfail stubs in 3 new files: repository CRUD/constraint, service generate/activate/list/delete/rate-limit, router 403 guard + 201/200 success
- 2 materializer xfail stubs appended to existing test file for WRSKL-03 workspace skill inheritance and WRSKL-04 personal skill override precedence
- 5 frontend it.todo() stubs for WorkspaceSkillCard (active/pending badge, activate/remove handlers)
- 4 frontend it.todo() stubs for workspace-role-skills API client (GET/POST/activate/DELETE)
- All stubs collected without errors by both pytest and vitest

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend xfail stubs — repository, service, and router tests** - `1d2cb1a5` (test)
2. **Task 2: Extend materializer tests + frontend stubs** - `1dc79a25` (test)

## Files Created/Modified
- `backend/tests/unit/repositories/test_workspace_role_skill_repository.py` - 4 xfail stubs for WorkspaceRoleSkillRepository CRUD + UNIQUE constraint (WRSKL-01..03)
- `backend/tests/unit/services/test_workspace_role_skill_service.py` - 5 xfail stubs for WorkspaceRoleSkillService generate/activate/list/delete/rate-limit (WRSKL-01..02)
- `backend/tests/unit/api/test_workspace_role_skills_router.py` - 4 xfail stubs for admin-only 403 guard + 201/200 admin success (WRSKL-01..02)
- `backend/tests/unit/ai/agents/test_role_skill_materializer.py` - appended 2 xfail stubs for workspace skill injection and personal skill precedence (WRSKL-03..04)
- `frontend/src/features/settings/components/__tests__/workspace-skill-card.test.tsx` - 5 it.todo() stubs for WorkspaceSkillCard component (WRSKL-01..02)
- `frontend/src/services/api/__tests__/workspace-role-skills.test.ts` - 4 it.todo() stubs for workspace-role-skills API client (WRSKL-01..02)

## Decisions Made
- No imports from not-yet-existing modules in stubs — prevents entire test file collection failure when implementation is absent
- `pytestmark = pytest.mark.asyncio` at module level instead of per-test decorator — matches existing test_role_skill_repository.py pattern in this codebase

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
- Ruff and prettier formatters modified files during pre-commit hooks (auto-fixed blank lines, wrapped long strings). Re-staged and re-committed after formatter changes. No semantic changes to stubs.

## Next Phase Readiness
- All 15 stubs ready for Plans 02 and 03 to implement against
- Plan 02 implements WorkspaceRoleSkill model, migration, and repository (turns repo stubs green)
- Plan 03 implements service and router (turns service + router stubs green)
- Plan 04 implements frontend UI (turns component + API client stubs green)
- Materializer stubs (WRSKL-03..04) will be turned green when materialize_role_skills is extended in Plan 04

---
*Phase: 016-workspace-role-skills*
*Completed: 2026-03-10*
