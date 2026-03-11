---
phase: 20-skill-template-catalog
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, postgresql, rls, skill-templates, user-skills]

# Dependency graph
requires:
  - phase: 016-workspace-role-skills
    provides: WorkspaceRoleSkill model and repository pattern
provides:
  - SkillTemplate SQLAlchemy model (workspace-scoped, source enum)
  - UserSkill SQLAlchemy model (user_id + template_id FK)
  - SkillTemplateRepository CRUD with workspace-scoped queries
  - UserSkillRepository CRUD with user-workspace queries
  - Alembic migration 077 with schema + data migration + RLS
affects: [20-02-materializer-refactor, 20-03-api-endpoints, 20-04-frontend-catalog]

# Tech tracking
tech-stack:
  added: []
  patterns: [workspace-scoped-model-with-source-enum, partial-unique-index-on-nullable-fk]

key-files:
  created:
    - backend/src/pilot_space/infrastructure/database/models/skill_template.py
    - backend/src/pilot_space/infrastructure/database/models/user_skill.py
    - backend/src/pilot_space/infrastructure/database/repositories/skill_template_repository.py
    - backend/src/pilot_space/infrastructure/database/repositories/user_skill_repository.py
    - backend/alembic/versions/077_add_skill_templates_and_user_skills.py
    - backend/tests/unit/repositories/test_skill_template_repository.py
    - backend/tests/unit/repositories/test_user_skill_repository.py
  modified:
    - backend/src/pilot_space/infrastructure/database/models/__init__.py

key-decisions:
  - "SkillTemplate is_active defaults true (unlike WorkspaceRoleSkill which defaults false) -- templates are immediately visible in catalog"
  - "UserSkill has no role_type or is_primary -- skills are decoupled from roles, all active skills are equal"
  - "Partial unique index on (user_id, workspace_id, template_id) allows nullable template_id for custom skills"
  - "Data migration uses LEFT JOIN for template_id linking -- custom role user_skills get template_id=NULL"
  - "length() instead of char_length() in CheckConstraints -- ANSI SQL compatible with SQLite test DB"

patterns-established:
  - "Source enum pattern: source VARCHAR(20) with values 'built_in', 'workspace', 'custom' for template origin tracking"
  - "Nullable FK with partial unique index: allows multiple custom skills (template_id=NULL) per user-workspace"

requirements-completed: [P20-01, P20-02, P20-03]

# Metrics
duration: 6min
completed: 2026-03-11
---

# Phase 20 Plan 01: Skill Template Catalog Persistence Summary

**SkillTemplate and UserSkill models with Alembic migration 077 (schema + data migration from RoleTemplate/WorkspaceRoleSkill/UserRoleSkill), repositories, RLS policies, and 35 passing unit tests**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-11T13:29:57Z
- **Completed:** 2026-03-11T13:36:26Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- SkillTemplate model: workspace-scoped, source enum (built_in/workspace/custom), nullable role_type for lineage, is_active defaults true
- UserSkill model: user_id + template_id (nullable FK to skill_templates), no role_type/is_primary, multiple active skills per user
- Alembic migration 077 with full data migration preserving existing role-based skills in new tables
- Both repositories with comprehensive CRUD, workspace isolation, and soft delete
- 35 passing unit tests covering all repository methods and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: SkillTemplate + UserSkill models and repositories** - `a498a46e` (feat)
2. **Task 2: Alembic migration 077 with schema creation and data migration** - `6e7ababe` (feat)

## Files Created/Modified
- `backend/src/pilot_space/infrastructure/database/models/skill_template.py` - SkillTemplate model with source enum, partial unique index, check constraints
- `backend/src/pilot_space/infrastructure/database/models/user_skill.py` - UserSkill model with nullable template_id FK, joined relationships
- `backend/src/pilot_space/infrastructure/database/models/__init__.py` - Registered both new models
- `backend/src/pilot_space/infrastructure/database/repositories/skill_template_repository.py` - CRUD with get_active_by_workspace, get_by_workspace
- `backend/src/pilot_space/infrastructure/database/repositories/user_skill_repository.py` - CRUD with get_by_user_workspace, get_by_user_workspace_template
- `backend/alembic/versions/077_add_skill_templates_and_user_skills.py` - Schema + data migration + RLS
- `backend/tests/unit/repositories/test_skill_template_repository.py` - 17 tests for SkillTemplateRepository
- `backend/tests/unit/repositories/test_user_skill_repository.py` - 18 tests for UserSkillRepository

## Decisions Made
- SkillTemplate is_active defaults true (unlike WorkspaceRoleSkill which defaults false) -- templates are immediately visible in catalog without admin activation
- UserSkill has no role_type or is_primary columns -- skills are fully decoupled from roles, all active skills are equal
- Partial unique index on (user_id, workspace_id, template_id) with nullable template_id -- allows multiple custom skills per user-workspace
- Data migration uses LEFT JOIN for template_id linking so custom role user_skills get template_id=NULL
- Used length() not char_length() in CheckConstraints for SQLite test DB compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added workspace_members table to user_skill test schema**
- **Found during:** Task 1 (UserSkill repository tests)
- **Issue:** SQLite test schema missing workspace_members table; User model's joined relationship to WorkspaceMember triggered lazy load during refresh()
- **Fix:** Added workspace_members CREATE TABLE to _SCHEMA_SQL in test_user_skill_repository.py
- **Files modified:** backend/tests/unit/repositories/test_user_skill_repository.py
- **Verification:** All 18 UserSkill tests pass
- **Committed in:** a498a46e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for test infrastructure to work. No scope creep.

## Issues Encountered
- `alembic check` reports "Target database is not up to date" -- expected since migration 077 was created but not yet applied to the dev database. `alembic heads` confirms single head at 077.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both tables and repositories ready for Plan 02 (materializer refactor)
- Migration file ready to apply to dev database when needed
- Old tables untouched -- backward compatible during transition

---
*Phase: 20-skill-template-catalog*
*Completed: 2026-03-11*
