---
phase: 20-skill-template-catalog
plan: 02
subsystem: backend-services
tags: [materializer, skill-templates, user-skills, ai-generation, services]

# Dependency graph
requires:
  - phase: 20-skill-template-catalog
    plan: 01
    provides: SkillTemplate and UserSkill models, repositories
provides:
  - Refactored role_skill_materializer reading from new tables
  - SeedTemplatesService for workspace template seeding
  - CreateUserSkillService for AI-based user skill creation
affects: [20-03-api-endpoints, 20-04-frontend-catalog]

# Tech tracking
tech-stack:
  added: []
  patterns: [operationalerror-fallback-for-migration-safety, fire-and-forget-seeding, ai-generation-reuse]

key-files:
  created:
    - backend/src/pilot_space/application/services/skill_template/__init__.py
    - backend/src/pilot_space/application/services/skill_template/seed_templates_service.py
    - backend/src/pilot_space/application/services/user_skill/__init__.py
    - backend/src/pilot_space/application/services/user_skill/create_user_skill_service.py
    - backend/tests/unit/services/test_seed_templates_service.py
    - backend/tests/unit/services/test_create_user_skill_service.py
  modified:
    - backend/src/pilot_space/ai/agents/role_skill_materializer.py
    - backend/tests/unit/ai/agents/test_role_skill_materializer.py
    - backend/tests/unit/ai/agents/conftest.py

key-decisions:
  - "New table path is primary, legacy path is OperationalError fallback -- no feature flag needed"
  - "Skill dir naming uses skill-{sanitized_name}-{id[:6]} to avoid collisions while being human-readable"
  - "SeedTemplatesService uses idempotency guard (check for existing built_in source) before seeding"
  - "CreateUserSkillService reuses GenerateRoleSkillService for AI personalization rather than duplicating"
  - "Legacy frontmatter functions kept separate from new ones to preserve backward compatibility"

patterns-established:
  - "OperationalError fallback pattern for gradual migration: try new tables, except OperationalError use old tables"
  - "Template-based AI skill generation: load template, augment with user experience, generate via AI with template fallback"

requirements-completed: [P20-04, P20-07, P20-08]

# Metrics
duration: 13min
completed: 2026-03-11
---

# Phase 20 Plan 02: Materializer Refactor and Core Services Summary

**Refactored materializer to read from user_skills + skill_templates with OperationalError fallback, plus SeedTemplatesService for workspace seeding and CreateUserSkillService for AI personalization**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-11T13:39:35Z
- **Completed:** 2026-03-11T13:52:53Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Materializer now reads from user_skills (personal) and skill_templates (workspace fallback) with OperationalError guard for legacy tables
- Directory naming: skill-{sanitized_name}-{id[:6]} for human-readable, collision-free paths
- _sanitize_skill_dir_name helper: lowercases, replaces non-alphanumeric with hyphens, falls back to ID prefix
- Legacy path extracted to _materialize_from_legacy_tables (preserves backward compatibility)
- SeedTemplatesService: copies RoleTemplate rows into skill_templates as built_in, idempotent, non-fatal
- CreateUserSkillService: validates template, checks duplicates, generates via GenerateRoleSkillService, creates UserSkill
- 30 passing tests total (20 materializer + 4 seed service + 6 create service)

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor materializer to read from new tables** - `74ed163a` (feat)
2. **Task 2: SeedTemplatesService and CreateUserSkillService** - `a8afb0a1` (feat)

## Files Created/Modified
- `backend/src/pilot_space/ai/agents/role_skill_materializer.py` - Refactored with new/legacy paths, _sanitize_skill_dir_name, new frontmatter builders
- `backend/tests/unit/ai/agents/test_role_skill_materializer.py` - Expanded from 7 to 20 tests covering new table path, fallback, cleanup
- `backend/tests/unit/ai/agents/conftest.py` - Added skill_templates and user_skills DDL for SQLite test DB
- `backend/src/pilot_space/application/services/skill_template/__init__.py` - Package init
- `backend/src/pilot_space/application/services/skill_template/seed_templates_service.py` - Workspace template seeding
- `backend/src/pilot_space/application/services/user_skill/__init__.py` - Package init
- `backend/src/pilot_space/application/services/user_skill/create_user_skill_service.py` - AI-based user skill creation
- `backend/tests/unit/services/test_seed_templates_service.py` - 4 tests for seeding
- `backend/tests/unit/services/test_create_user_skill_service.py` - 6 tests for skill creation

## Decisions Made
- New table path is primary, legacy is OperationalError fallback -- migration safety without feature flags
- Skill dir naming: skill-{sanitized_name}-{id[:6]} balances readability and uniqueness
- SeedTemplatesService checks for existing built_in source before seeding (idempotency)
- CreateUserSkillService reuses GenerateRoleSkillService rather than duplicating AI generation logic
- Legacy frontmatter functions kept separate (_build_legacy_frontmatter) to avoid breaking existing materializer behavior
- pilotspace_agent.py NOT modified -- materialize_role_skills wrapper name preserved

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added skill_templates and user_skills tables to agent test conftest**
- **Found during:** Task 1 (materializer tests)
- **Issue:** SQLite test schema in `tests/unit/ai/agents/conftest.py` missing new tables; UserSkill/SkillTemplate model queries would fail
- **Fix:** Added CREATE TABLE DDL for skill_templates and user_skills to _CREATE_TABLES_SQL
- **Files modified:** backend/tests/unit/ai/agents/conftest.py
- **Committed in:** 74ed163a

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for test infrastructure. No scope creep.

## Issues Encountered
- Pre-existing unstaged changes in main.py and routers/__init__.py (from future plans) caused stash conflicts during commits. Resolved by isolating staged files.
- Pre-existing pyright error in main.py (unused skill_templates_router import) is out of scope for this plan.

## Next Phase Readiness
- Materializer ready to be used by pilotspace_agent.py (same function signature)
- SeedTemplatesService ready to be wired into workspace creation flow
- CreateUserSkillService ready to be exposed via API endpoints (Plan 03)

---
*Phase: 20-skill-template-catalog*
*Completed: 2026-03-11*
