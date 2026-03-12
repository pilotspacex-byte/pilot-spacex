---
phase: 016-workspace-role-skills
plan: "02"
subsystem: database
tags: [sqlalchemy, alembic, postgres, rls, repository-pattern]

requires:
  - phase: 016-01
    provides: xfail/todo TDD stubs for WRSKL-01..04

provides:
  - WorkspaceRoleSkill SQLAlchemy model extending WorkspaceScopedModel
  - WorkspaceRoleSkillRepository with 6 CRUD methods
  - Alembic migration 073 creating workspace_role_skills table with RLS
  - Partial unique index on (workspace_id, role_type) WHERE is_deleted = false
  - Hot-path composite index on (workspace_id, is_active) for materializer

affects:
  - 016-03 (service layer builds on this model + repository)
  - 016-04 (router endpoints use WorkspaceRoleSkillRepository)

tech-stack:
  added: []
  patterns:
    - Partial unique index via Index(..., postgresql_where=text(...)) for soft-delete-compatible uniqueness
    - Repository overrides create/soft_delete with domain-specific signatures rather than generic BaseRepository methods
    - is_active=False default as approval gate pattern (WRSKL-02)

key-files:
  created:
    - backend/src/pilot_space/infrastructure/database/models/workspace_role_skill.py
    - backend/src/pilot_space/infrastructure/database/repositories/workspace_role_skill_repository.py
    - backend/alembic/versions/073_add_workspace_role_skills.py
  modified:
    - backend/src/pilot_space/infrastructure/database/models/__init__.py

key-decisions:
  - "created_by is nullable (SET NULL on user delete) — workspace skill persists after creator leaves the workspace"
  - "Partial unique index (WHERE is_deleted = false) instead of standard UniqueConstraint — allows re-create after soft-delete without uniqueness violation"
  - "soft_delete() also sets is_active=False atomically — ensures skill is immediately excluded from materializer hot-path without requiring a separate deactivate call"
  - "RLS policy uses workspace_members subquery join pattern (matching 072 dismissals) — consistent with multi-tenant isolation approach across codebase"

patterns-established:
  - "Repository.create() takes named kwargs matching domain fields, not a pre-built entity — cleaner call site for service layer"
  - "get_active_by_workspace() is the materializer injection point: filters is_active=True AND is_deleted=False, ordered by role_type"
  - "get_by_id() does not filter is_deleted — caller handles deleted state; enables activate/deactivate to find soft-deleted rows if needed"

requirements-completed: [WRSKL-01, WRSKL-02, WRSKL-03]

duration: 18min
completed: 2026-03-10
---

# Phase 16 Plan 02: Workspace Role Skills Persistence Summary

**WorkspaceRoleSkill SQLAlchemy model + repository with partial-unique soft-delete-compatible index and Alembic migration 073 with RLS policies**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-10T08:10:00Z
- **Completed:** 2026-03-10T08:28:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- WorkspaceRoleSkill model with 6 business fields extending WorkspaceScopedModel; partial unique index on (workspace_id, role_type) WHERE is_deleted = false prevents uniqueness violations on re-create after soft-delete
- WorkspaceRoleSkillRepository with create, get_by_id, get_by_workspace, get_active_by_workspace, activate, deactivate, soft_delete — service layer can consume directly in Plan 03
- Migration 073 with workspace_members subquery RLS isolation policy + service_role bypass, matching existing codebase pattern from migration 072

## Task Commits

Each task was committed atomically:

1. **Task 1: WorkspaceRoleSkill model + repository** - `b7462876` (feat)
2. **Task 2: Alembic migration 073** - `116e0772` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `backend/src/pilot_space/infrastructure/database/models/workspace_role_skill.py` - WorkspaceRoleSkill model: 6 business fields, partial unique index, hot-path composite index, check constraints
- `backend/src/pilot_space/infrastructure/database/repositories/workspace_role_skill_repository.py` - Repository: 6 methods with domain-specific signatures and docstrings
- `backend/alembic/versions/073_add_workspace_role_skills.py` - Migration 073: table DDL, partial unique index via raw SQL, composite indexes, RLS policies with workspace isolation + service bypass
- `backend/src/pilot_space/infrastructure/database/models/__init__.py` - Added WorkspaceRoleSkill import and export

## Decisions Made

- `created_by` is nullable with SET NULL on delete — workspace skill persists after the creator leaves the workspace; admin ownership does not cascade to content deletion
- Used `Index(..., postgresql_where=text("is_deleted = false"))` instead of `UniqueConstraint` — standard UniqueConstraint would block re-create after soft-delete; partial index excludes deleted rows from uniqueness enforcement
- `soft_delete()` sets `is_active=False` atomically before marking `is_deleted=True` — ensures immediate exclusion from materializer hot-path without requiring a separate deactivate call
- `get_by_id()` does NOT filter `is_deleted` — intentional; allows `activate()` and `deactivate()` to operate on any row regardless of deleted state via a single lookup method

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- ruff-format auto-corrected import ordering in migration 073 during pre-commit hook (I001); restaged and recommitted — not a code logic issue.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Model and repository fully ready for Plan 03 service layer
- `get_active_by_workspace()` is the materializer injection point (WRSKL-03)
- alembic heads shows single head 073 — migration chain clean
- All 4 xfail stubs from 016-01 remain XFAIL (TDD loop stays open for Plan 03 green tests)

---
*Phase: 016-workspace-role-skills*
*Completed: 2026-03-10*
