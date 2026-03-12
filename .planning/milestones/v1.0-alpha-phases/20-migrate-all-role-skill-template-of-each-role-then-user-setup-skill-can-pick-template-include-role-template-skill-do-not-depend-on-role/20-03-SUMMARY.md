---
phase: 20-skill-template-catalog
plan: 03
subsystem: api
tags: [fastapi, pydantic, rest-api, skill-templates, user-skills]

# Dependency graph
requires:
  - phase: 20-skill-template-catalog-01
    provides: SkillTemplate and UserSkill models, repositories
  - phase: 20-skill-template-catalog-02
    provides: CreateUserSkillService with AI personalization
provides:
  - Skill templates CRUD router (admin CRUD + member browse)
  - User skills CRUD router (owner-only operations)
  - Pydantic v2 request/response schemas for both resources
  - API registration in main.py and routers/__init__.py
affects: [20-04-frontend-catalog]

# Tech tracking
tech-stack:
  added: []
  patterns: [workspace-scoped-admin-router, owner-only-user-resource-router, built-in-template-read-only-guard]

key-files:
  created:
    - backend/src/pilot_space/api/v1/schemas/skill_template.py
    - backend/src/pilot_space/api/v1/schemas/user_skill.py
    - backend/src/pilot_space/api/v1/routers/skill_templates.py
    - backend/src/pilot_space/api/v1/routers/user_skills.py
    - backend/tests/unit/routers/test_skill_templates_router.py
    - backend/tests/unit/routers/test_user_skills_router.py
  modified:
    - backend/src/pilot_space/api/v1/routers/__init__.py
    - backend/src/pilot_space/main.py

key-decisions:
  - "Module-level imports for SkillTemplateRepository and UserSkillRepository in routers -- enables unittest.mock.patch at module path"
  - "Built-in templates only allow is_active toggle -- other field changes return 403 to preserve platform-maintained content"
  - "POST /user-skills returns 409 (not 400) on duplicate template -- distinguishes 'already exists' from 'invalid request'"
  - "UserSkillSchema includes computed template_name from joined relationship -- single query for UI display"
  - "X-Workspace-ID header required -- follows RequestContextMiddleware pattern from existing workspace-scoped routers"

patterns-established:
  - "Built-in read-only guard: check template.source == 'built_in' before allowing mutations beyond is_active"
  - "Owner-only user resource: verify skill.user_id == current_user_id before PATCH/DELETE"

requirements-completed: [P20-05, P20-06]

# Metrics
duration: 16min
completed: 2026-03-11
---

# Phase 20 Plan 03: Skill Template & User Skill API Endpoints Summary

**REST API endpoints for skill templates (admin CRUD with built-in guard) and user skills (owner-only CRUD with AI personalization via CreateUserSkillService), Pydantic v2 schemas, 23 passing tests**

## Performance

- **Duration:** 16 min
- **Started:** 2026-03-11T13:39:45Z
- **Completed:** 2026-03-11T13:55:45Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Skill templates CRUD: GET (all members browse), POST/PATCH/DELETE (admin only), built-in templates read-only (is_active toggle only)
- User skills CRUD: GET/PATCH/DELETE (owner only), POST delegates to CreateUserSkillService for AI personalization, 409 on duplicate template
- Pydantic v2 schemas with ConfigDict(from_attributes=True) for both resources
- Both routers registered in main.py and routers/__init__.py with workspace prefix
- 23 passing unit tests across both routers

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic schemas + skill templates admin router** - `610fc1be` (feat)
2. **Task 2: User skills router + API registration** - `9377bb37` (feat -- code absorbed into 20-02 docs commit due to prek stash behavior)

## Files Created/Modified
- `backend/src/pilot_space/api/v1/schemas/skill_template.py` - SkillTemplateSchema, SkillTemplateCreate, SkillTemplateUpdate
- `backend/src/pilot_space/api/v1/schemas/user_skill.py` - UserSkillSchema (with computed template_name), UserSkillCreate, UserSkillUpdate
- `backend/src/pilot_space/api/v1/routers/skill_templates.py` - Admin CRUD router with built-in guard
- `backend/src/pilot_space/api/v1/routers/user_skills.py` - User skill CRUD router with ownership guards
- `backend/src/pilot_space/api/v1/routers/__init__.py` - Added skill_templates_router and user_skills_router exports
- `backend/src/pilot_space/main.py` - Registered both routers with workspace prefix
- `backend/tests/unit/routers/test_skill_templates_router.py` - 12 tests for skill templates router
- `backend/tests/unit/routers/test_user_skills_router.py` - 11 tests for user skills router

## Decisions Made
- Module-level imports for repositories in routers (not function-local) -- enables unittest.mock.patch with simple module path; follows Phase 13 precedent
- Built-in templates only allow is_active toggle; other field changes return 403 -- preserves platform-maintained content integrity
- POST /user-skills returns 409 on duplicate template, 400 on invalid template -- HTTP status codes distinguish error types
- UserSkillSchema includes computed template_name from joined SkillTemplate relationship -- avoids extra query for UI
- X-Workspace-ID header required by RequestContextMiddleware -- consistent with all workspace-scoped routers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added X-Workspace-ID header to test fixtures**
- **Found during:** Task 1 (skill templates router tests)
- **Issue:** RequestContextMiddleware requires X-Workspace-ID header; test requests returned 400 "X-Workspace-ID header required"
- **Fix:** Added X-Workspace-ID header to both admin_client and non_admin_client fixtures
- **Files modified:** backend/tests/unit/routers/test_skill_templates_router.py
- **Verification:** All 12 tests pass
- **Committed in:** 610fc1be (Task 1 commit)

**2. [Rule 3 - Blocking] Switched from function-local to module-level repository imports**
- **Found during:** Task 1 (test mock setup)
- **Issue:** Function-local imports prevent unittest.mock.patch from finding the attribute at module level
- **Fix:** Moved SkillTemplateRepository and UserSkillRepository imports to module level
- **Files modified:** backend/src/pilot_space/api/v1/routers/skill_templates.py, backend/src/pilot_space/api/v1/routers/user_skills.py
- **Verification:** All tests pass with mock patches working correctly
- **Committed in:** 610fc1be (Task 1), 9377bb37 (Task 2)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes necessary for test infrastructure. No scope creep.

## Issues Encountered
- Pre-commit hook (prek) stash/unstash mechanism caused Task 2 code to be absorbed into the 20-02 docs commit (9377bb37) instead of getting its own atomic commit. This happened because prek stashes unstaged changes, but pyright modifies files (cache), creating stash conflicts. The code is correctly committed, just in a non-ideal commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both routers registered and functional, ready for Plan 04 (frontend catalog)
- Skill templates browseable at GET /api/v1/workspaces/{id}/skill-templates
- User skills manageable at /api/v1/workspaces/{id}/user-skills
- AI personalization active via CreateUserSkillService from Plan 02

---
*Phase: 20-skill-template-catalog*
*Completed: 2026-03-11*
