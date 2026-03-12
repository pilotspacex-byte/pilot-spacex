---
phase: 19-skill-registry-and-plugin-system
plan: 02
subsystem: database
tags: [sqlalchemy, alembic, postgresql, rls, jsonb, repository-pattern]

requires:
  - phase: 016-workspace-role-skills
    provides: "WorkspaceRoleSkill model/repo pattern, migration 073"
provides:
  - "WorkspacePlugin SQLAlchemy model with JSONB references"
  - "WorkspaceGithubCredential SQLAlchemy model with encrypted PAT"
  - "Alembic migration 074 with RLS + partial unique index"
  - "WorkspacePluginRepository with active/installed/name queries"
  - "WorkspaceGithubCredentialRepository with upsert pattern"
affects: [019-03, 019-04]

tech-stack:
  added: []
  patterns: [upsert-repository, partial-unique-index, jsonb-default]

key-files:
  created:
    - backend/src/pilot_space/infrastructure/database/models/workspace_plugin.py
    - backend/src/pilot_space/infrastructure/database/models/workspace_github_credential.py
    - backend/src/pilot_space/infrastructure/database/repositories/workspace_plugin_repository.py
    - backend/src/pilot_space/infrastructure/database/repositories/workspace_github_credential_repository.py
    - backend/alembic/versions/074_add_workspace_plugins.py
  modified:
    - backend/src/pilot_space/infrastructure/database/models/__init__.py

key-decisions:
  - "WorkspacePlugin is_active defaults to True (not False like WorkspaceRoleSkill) -- plugins are active on install, admin can deactivate"
  - "WorkspaceGithubCredentialRepository uses upsert pattern (get-or-create) -- one PAT per workspace"
  - "Partial unique index on (workspace_id, repo_owner, repo_name, skill_name) WHERE is_deleted = false -- allows re-install after soft-delete"

patterns-established:
  - "Upsert repository: get_by_workspace + create-or-update for one-per-workspace entities"
  - "JSONB column with server_default '[]'::jsonb for array-typed metadata"

requirements-completed: [SKRG-01, SKRG-02, SKRG-03, SKRG-04, SKRG-05]

duration: 5min
completed: 2026-03-10
---

# Phase 19 Plan 02: Persistence Layer Summary

**WorkspacePlugin + WorkspaceGithubCredential models, Alembic migration 074 with RLS + partial unique index, and two async repositories**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-10T15:00:47Z
- **Completed:** 2026-03-10T15:06:04Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Two SQLAlchemy models following WorkspaceScopedModel pattern with proper column types
- Alembic migration 074 with full RLS (ENABLE + FORCE + workspace isolation + service_role bypass) on both tables
- Partial unique index preventing duplicate plugin installs per workspace
- Two repository classes with async query patterns matching existing codebase conventions

## Task Commits

Each task was committed atomically:

1. **Task 1: WorkspacePlugin + WorkspaceGithubCredential models** - `9a213486` (feat)
2. **Task 2: Repositories + Alembic migration 074** - `1936c6af` (feat)

## Files Created/Modified
- `backend/src/pilot_space/infrastructure/database/models/workspace_plugin.py` - WorkspacePlugin model with JSONB references, partial unique index, composite active index
- `backend/src/pilot_space/infrastructure/database/models/workspace_github_credential.py` - WorkspaceGithubCredential model with encrypted PAT
- `backend/src/pilot_space/infrastructure/database/models/__init__.py` - Registered both new models for Alembic autogenerate
- `backend/src/pilot_space/infrastructure/database/repositories/workspace_plugin_repository.py` - CRUD + get_active_by_workspace + get_by_workspace_and_name
- `backend/src/pilot_space/infrastructure/database/repositories/workspace_github_credential_repository.py` - get_by_workspace + upsert
- `backend/alembic/versions/074_add_workspace_plugins.py` - Migration with RLS, indexes, downgrade

## Decisions Made
- WorkspacePlugin is_active defaults to True (plugins are active on install, unlike WorkspaceRoleSkill which defaults to False for approval gate)
- Upsert pattern for WorkspaceGithubCredential (one PAT per workspace, update existing or create new)
- Partial unique index excludes soft-deleted rows, enabling re-install after deletion

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-commit hook caught accidental McpAuthType/WorkspaceMcpServer re-export in models/__init__.py (pyright reportUnusedImport) -- removed the extra import before successful commit

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Models and repositories ready for Plan 03 (service layer + router endpoints)
- Migration 074 is single head, ready for `alembic upgrade head`
- Repository interfaces match the signatures expected by Plan 03 service layer

---
*Phase: 19-skill-registry-and-plugin-system*
*Completed: 2026-03-10*
