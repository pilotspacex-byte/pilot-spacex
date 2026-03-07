---
phase: 01-identity-and-access
plan: 01
subsystem: database
tags: [migration, models, rls, rbac, sso, scim, test-scaffolds]
dependency_graph:
  requires: []
  provides:
    - custom_roles DB table
    - workspace_sessions DB table
    - workspace_members.custom_role_id FK
    - workspace_members.is_active column
    - CustomRole SQLAlchemy model
    - WorkspaceSession SQLAlchemy model
    - 23 test stubs covering AUTH-01 through AUTH-07
  affects:
    - workspace_members (added 2 columns)
    - workspace.py (added custom_roles relationship)
    - models/__init__.py (2 new exports)
tech_stack:
  added: []
  patterns:
    - WorkspaceScopedModel base class (UUID PK + timestamps + soft-delete + workspace_id FK)
    - JSONBCompat type decorator (JSONB on PostgreSQL, JSON fallback for SQLite tests)
    - RLS workspace isolation via workspace_members membership subquery
    - xfail(strict=False) test scaffolds for TDD RED phase
key_files:
  created:
    - backend/alembic/versions/064_add_sso_rbac_session_tables.py
    - backend/src/pilot_space/infrastructure/database/models/custom_role.py
    - backend/src/pilot_space/infrastructure/database/models/workspace_session.py
    - backend/tests/unit/services/test_sso_service.py
    - backend/tests/unit/services/test_rbac_service.py
    - backend/tests/unit/services/test_session_service.py
    - backend/tests/unit/routers/test_auth_sso.py
    - backend/tests/unit/routers/test_scim.py
  modified:
    - backend/src/pilot_space/infrastructure/database/models/workspace_member.py
    - backend/src/pilot_space/infrastructure/database/models/workspace.py
    - backend/src/pilot_space/infrastructure/database/models/__init__.py
decisions:
  - "WorkspaceSession uses own-rows RLS (user_id = current_user) rather than workspace isolation — sessions are private; admins use service_role for force-terminate"
  - "custom_roles RLS uses workspace_members subquery join (same pattern as graph_nodes) — isolates per workspace without requiring per-user policy rows"
  - "is_active added to workspace_members not as soft_delete — SCIM deactivation must be reversible (re-provision) without touching is_deleted semantics"
  - "session_token_hash is SHA-256 hex (64 chars) — never store raw tokens in DB"
  - "Test scaffolds use xfail(strict=False) not skip — xfail runs the test body and reports XFAIL/XPASS, giving better visibility when implementation begins"
metrics:
  duration_minutes: 5
  completed_date: "2026-03-07"
  tasks_completed: 2
  files_created: 8
  files_modified: 3
---

# Phase 1 Plan 1: DB Foundation & Test Scaffolds Summary

**One-liner:** Alembic migration 064 creates custom_roles and workspace_sessions tables with full RLS, alters workspace_members with RBAC/SCIM columns, and adds 23 xfail test stubs covering AUTH-01 through AUTH-07.

## What Was Built

### Task 1: SQLAlchemy Models

**CustomRole** (`custom_role.py`):
- Extends `WorkspaceScopedModel` (UUID PK, timestamps, soft-delete, workspace_id FK)
- `name` String(100), `description` Text nullable, `permissions` JSONBCompat list[str] nullable
- Unique constraint on `(workspace_id, name)` — enforced at DB and application layer
- Bi-directional relationships to `Workspace` and `WorkspaceMember`

**WorkspaceSession** (`workspace_session.py`):
- Extends `WorkspaceScopedModel`
- `user_id` FK to `users.id`, `session_token_hash` String(64) SHA-256 hex
- `ip_address` String(45) — IPv6-safe (max 45 chars), `user_agent` Text
- `last_seen_at` DateTime TZ with `server_default=now()`, `revoked_at` DateTime TZ nullable
- `is_active` property: `revoked_at is None`
- Indexes: `session_token_hash`, `user_id`, `workspace_id`

**WorkspaceMember updates**:
- Added `custom_role_id` (UUID nullable FK to `custom_roles.id` ON DELETE SET NULL) with index
- Added `is_active` (Boolean not null, `server_default="true"`) for SCIM provisioning lifecycle

**Workspace updates**:
- Added `custom_roles` relationship (`list[CustomRole]`, cascade all delete-orphan, lazy select)

### Task 2: Migration 064 + Test Scaffolds

**Migration 064** (`064_add_sso_rbac_session_tables.py`):
- Creates `custom_roles` and `workspace_sessions` tables matching model definitions
- Alters `workspace_members` with `custom_role_id` FK and `is_active` column
- RLS for `custom_roles`: ENABLE + FORCE + workspace_member subquery isolation + service_role bypass
- RLS for `workspace_sessions`: ENABLE + FORCE + own-rows policy (user_id = current_user) + service_role bypass
- Complete `downgrade()`: drops policies → removes FK columns → drops tables in dependency order

**Test Scaffolds** (23 tests, all xfail pending implementation):
- `test_sso_service.py` — 6 tests: AUTH-01 (SAML config/validation), AUTH-02 (OIDC), AUTH-03 (role claim mapping + default), AUTH-04 (sso_required flag)
- `test_rbac_service.py` — 5 tests: AUTH-05 (create role, check allowed, check denied, built-in fallback, name uniqueness)
- `test_session_service.py` — 5 tests: AUTH-06 (record, throttle, force_terminate+revoked_at, force_terminate+Redis, terminate_all)
- `test_auth_sso.py` — 3 tests: AUTH-04 (reject password login), AUTH-01 (SAML redirect), AUTH-06 (revoked session 401)
- `test_scim.py` — 4 tests: AUTH-07 (provision, deprovision soft-deactivate, patch, invalid token 401)

## Deviations from Plan

None — plan executed exactly as written.

The only auto-fixes were ruff import sorting and formatting (2 pre-commit hook runs), which are cosmetic tooling fixes, not code deviations.

## Self-Check

### Created files exist
- backend/alembic/versions/064_add_sso_rbac_session_tables.py: FOUND
- backend/src/pilot_space/infrastructure/database/models/custom_role.py: FOUND
- backend/src/pilot_space/infrastructure/database/models/workspace_session.py: FOUND
- backend/tests/unit/services/test_sso_service.py: FOUND
- backend/tests/unit/services/test_rbac_service.py: FOUND
- backend/tests/unit/services/test_session_service.py: FOUND
- backend/tests/unit/routers/test_auth_sso.py: FOUND
- backend/tests/unit/routers/test_scim.py: FOUND

### Commits exist
- bb04e37a: feat(01-identity-and-access): add CustomRole and WorkspaceSession SQLAlchemy models
- b973b7ca: feat(01-identity-and-access): add migration 064 and AUTH test scaffolds

### Verification results
- `python -c "...CustomRole...WorkspaceSession..."`: OK
- `alembic heads`: 064_add_sso_rbac_session_tables (head) — single head
- `pytest --co` on 5 scaffold files: 23 tests collected, no import errors

## Self-Check: PASSED
