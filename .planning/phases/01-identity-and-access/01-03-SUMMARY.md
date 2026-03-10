---
phase: 01-identity-and-access
plan: 03
subsystem: rbac
tags: [rbac, custom-roles, permissions, auth]
dependency_graph:
  requires: [01-01]
  provides: [AUTH-05]
  affects: [workspace-members, workspace-settings]
tech_stack:
  added: []
  patterns: [builtin-role-permissions-map, permission-string-validation, soft-delete-with-cascade-nullify]
key_files:
  created:
    - backend/src/pilot_space/infrastructure/database/permissions.py
    - backend/src/pilot_space/infrastructure/database/repositories/custom_role_repository.py
    - backend/src/pilot_space/infrastructure/database/repositories/workspace_member_repository.py
    - backend/src/pilot_space/application/services/rbac_service.py
    - backend/src/pilot_space/api/v1/routers/custom_roles.py
    - backend/src/pilot_space/api/v1/schemas/rbac.py
    - backend/tests/unit/services/test_rbac_service.py
  modified:
    - backend/src/pilot_space/container/container.py
    - backend/src/pilot_space/api/v1/dependencies.py
    - backend/src/pilot_space/api/v1/routers/__init__.py
    - backend/src/pilot_space/main.py
decisions:
  - "Custom role takes precedence over built-in WorkspaceRole; built-in used when custom_role_id is NULL"
  - "BUILTIN_ROLE_PERMISSIONS uses lowercase keys; WorkspaceRole enum stores UPPERCASE — normalized via .lower()"
  - "delete_role() nullifies member assignments before soft-delete to prevent orphaned FKs"
  - "WorkspaceMemberRepository is a dedicated RBAC-ops repo separate from WorkspaceRepository"
metrics:
  duration: ~45min
  completed: "2026-03-07T15:18:58Z"
  tasks: 2
  files: 14
---

# Phase 01 Plan 03: Custom RBAC Summary

Custom role management with per-resource permission grants, check_permission() resolver, and 6-endpoint admin API.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | permissions.py + CustomRoleRepository + RbacService (TDD) | 2256bec7 | permissions.py, custom_role_repository.py, workspace_member_repository.py, rbac_service.py, test_rbac_service.py |
| 2 | Custom roles router + DI wiring | 6b42851b | custom_roles.py, schemas/rbac.py, container.py, dependencies.py, main.py, routers/__init__.py |

## What Was Built

**permissions.py**: `BUILTIN_ROLE_PERMISSIONS` dict mapping 4 built-in roles (owner/admin/member/guest) to frozensets of `resource:action` strings. `check_permission()` async helper — single DB query with `joinedload` on `WorkspaceMember.custom_role`, custom role takes precedence over built-in role.

**CustomRoleRepository**: `get(role_id, workspace_id)`, `get_by_name(workspace_id, name, exclude_id=None)`, `list_for_workspace(workspace_id)`, `soft_delete(role_id, workspace_id)` — all workspace-scoped.

**WorkspaceMemberRepository**: RBAC-focused repo for `get_by_user_workspace()`, `update()`, `clear_custom_role_assignments(role_id)` — clears `custom_role_id=NULL` on all affected members.

**RbacService**: `create_role` (validates permission strings, checks name uniqueness), `list_roles`, `get_role`, `update_role` (partial update), `delete_role` (clears assignments then soft-deletes), `assign_role_to_member` (set/clear custom_role_id). Raises `DuplicateRoleNameError`, `RoleNotFoundError`, `MemberNotFoundError`.

**custom_roles router** (6 endpoints under `/workspaces/{slug}/roles`):
1. `GET /` — list roles
2. `POST /` — create (409 on duplicate name, 422 on invalid permissions)
3. `GET /{role_id}` — get single
4. `PATCH /{role_id}` — partial update
5. `DELETE /{role_id}` — soft-delete (204)
6. `PUT /members/{user_id}/role` — assign/clear custom role

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written.

### Notes

Task 2 (router + DI wiring) was committed as part of the 01-04 sessions plan commit (`6b42851b`) to bundle all wiring changes. `WorkspaceMemberRepository` was not in the original plan but was added (Rule 2) as a clean separation from the existing `WorkspaceRepository` which handles general workspace-member operations.

## Test Coverage

- 16 unit tests in `test_rbac_service.py` (all green)
- Covers: custom role allowed/denied, built-in OWNER/GUEST/MEMBER fallback, inactive member denial, non-member denial, BUILTIN_ROLE_PERMISSIONS correctness, RbacService CRUD with mocked repos, assign/clear role, delete clears assignments

## Self-Check: PASSED

All key files exist and commits are verified in `git log`.
