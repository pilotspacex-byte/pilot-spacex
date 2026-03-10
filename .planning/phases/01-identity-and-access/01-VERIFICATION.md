---
phase: 01-identity-and-access
verified: 2026-03-07T16:07:57Z
status: passed
score: 7/7 truths verified
gaps: []
gap_resolution:
  - truth: "Admin can view, create, update, delete custom RBAC roles via API"
    status: resolved
    fix: "Added custom_roles_router to import block and app.include_router() in main.py (commit 5905274f)"
---

# Phase 1: Identity and Access Verification Report

**Phase Goal:** Implement enterprise identity and access management — SSO (SAML 2.0 + OIDC), custom RBAC, workspace sessions, SCIM 2.0 provisioning, and the supporting admin UI.
**Verified:** 2026-03-07T16:07:57Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Admin can configure SAML 2.0 SSO (AUTH-01) | VERIFIED | `SamlAuthProvider` (307 lines) with `get_login_url`, `process_response`, `get_metadata_xml`; `SsoService.configure_saml`; router endpoints `/saml/initiate`, `/saml/callback`, `/saml/metadata`, `/saml/config`; 70 tests pass |
| 2 | Admin can configure OIDC SSO (AUTH-02) | VERIFIED | `SsoService.configure_oidc`, `SsoService.configure_role_claim_mapping`; OIDC config endpoints in `auth_sso.py`; `useSsoLogin` calls `supabase.auth.signInWithOAuth`; login page wired |
| 3 | Users receive workspace roles from IdP claims (AUTH-03) | VERIFIED | `SsoService.map_claims_to_role` (never returns "owner", defaults to "member"); `apply_sso_role`; `POST /auth/sso/claim-role` endpoint; `useApplyClaimsRole` hook; 70 tests pass including 5 claim-mapping tests |
| 4 | Admin can force SSO-only login (AUTH-04) | VERIFIED | `SsoService.set_sso_required` stores flag; `GET /auth/sso/login-check` returns 403 with "This workspace requires SSO login" message when `sso_required=true`; login page hides email/password form when `ssoRequired=true` |
| 5 | Admin can define custom RBAC roles with per-resource permissions (AUTH-05) | FAILED | `RbacService` (291 lines), `check_permission`, `BUILTIN_ROLE_PERMISSIONS`, `custom_roles_router` (6 endpoints) all exist and test clean — but `custom_roles_router` is NOT registered in `main.py`, making all RBAC endpoints unreachable at runtime |
| 6 | Admin can view all active sessions and force-terminate any session (AUTH-06) | VERIFIED | `SessionRecordingMiddleware` with 60s throttle + Redis revocation check; `SessionService.list_sessions`, `force_terminate`, `terminate_all_for_user`; sessions router (3 endpoints); `SecuritySettingsPage` with sessions table, terminate button, "(you)" badge |
| 7 | Admin can configure SCIM 2.0 auto-provision/deprovision (AUTH-07) | VERIFIED | `ScimService` (487 lines) with provision (creates Supabase user), deprovision (`is_active=False`, no data deletion), PATCH ops; 7 SCIM endpoints at `/api/v1/scim/v2/{slug}/`; SCIM bearer token auth via `scim_token_hash`; `SecuritySettingsPage` has SCIM token generation UI |

**Score: 6/7 truths verified**

---

### Required Artifacts

| Artifact | Status | Lines | Evidence |
|----------|--------|-------|----------|
| `backend/alembic/versions/064_add_sso_rbac_session_tables.py` | VERIFIED | — | Creates `custom_roles`, `workspace_sessions`; alters `workspace_members` (adds `custom_role_id` FK, `is_active`); full RLS (ENABLE, FORCE, workspace isolation, service_role bypass) |
| `backend/src/pilot_space/infrastructure/database/models/custom_role.py` | VERIFIED | 84 | `CustomRole(WorkspaceScopedModel)`, unique constraint on `(workspace_id, name)` |
| `backend/src/pilot_space/infrastructure/database/models/workspace_session.py` | VERIFIED | 109 | `WorkspaceSession(WorkspaceScopedModel)`, `session_token_hash`, `revoked_at` |
| `backend/src/pilot_space/infrastructure/auth/saml_auth.py` | VERIFIED | 307 | `SamlAuthProvider`, `SamlValidationError`, all 3 methods implemented |
| `backend/src/pilot_space/application/services/sso_service.py` | VERIFIED | 550 | All methods: `configure_saml`, `configure_oidc`, `set_sso_required`, `get_sso_status`, `provision_saml_user`, `configure_role_claim_mapping`, `map_claims_to_role`, `apply_sso_role` |
| `backend/src/pilot_space/application/services/rbac_service.py` | VERIFIED | 291 | `RbacService`, `DuplicateRoleNameError`, all 5 CRUD methods |
| `backend/src/pilot_space/infrastructure/database/permissions.py` | VERIFIED | 142 | `check_permission`, `BUILTIN_ROLE_PERMISSIONS` (4 built-in roles) |
| `backend/src/pilot_space/application/services/session_service.py` | VERIFIED | 274 | `SessionService`, `record_session` (60s throttle), `force_terminate`, `terminate_all_for_user` |
| `backend/src/pilot_space/api/v1/middleware/session_recording.py` | VERIFIED | — | `SessionRecordingMiddleware`, REVOKED_KEY check, LASTSEEN_KEY throttle, `is_active=False` blocks deprovisioned users |
| `backend/src/pilot_space/application/services/scim_service.py` | VERIFIED | 487 | `ScimService`, all methods: `provision_user`, `deprovision_user` (sets `is_active=False`), `patch_user`, `generate_scim_token` |
| `backend/src/pilot_space/api/v1/routers/auth_sso.py` | VERIFIED | 697 | 9+ endpoints including `GET /auth/sso/status` (unauthenticated), `POST /auth/sso/claim-role`, `GET /auth/sso/login-check` (403 when `sso_required=true`) |
| `backend/src/pilot_space/api/v1/routers/custom_roles.py` | ORPHANED | 343 | 6 endpoints exist, importable, DI wired — but NOT registered in `main.py` |
| `backend/src/pilot_space/api/v1/routers/sessions.py` | VERIFIED | 265 | 3 endpoints; registered in `main.py` as `workspace_sessions_router` |
| `backend/src/pilot_space/api/v1/routers/scim.py` | VERIFIED | 515 | 7 endpoints; registered in `main.py` as `scim_router` |
| `backend/src/pilot_space/infrastructure/database/repositories/custom_role_repository.py` | VERIFIED | — | Exists |
| `backend/src/pilot_space/infrastructure/database/repositories/workspace_session_repository.py` | VERIFIED | — | Exists |
| `frontend/src/features/settings/pages/sso-settings-page.tsx` | VERIFIED | 632 | 4 sections: SAML form, OIDC config, role claim mapping, SSO enforcement toggle; not `observer()` |
| `frontend/src/features/settings/pages/roles-settings-page.tsx` | VERIFIED | 567 | Roles table with create/edit/delete Dialog, permission grid; not `observer()` |
| `frontend/src/features/settings/pages/security-settings-page.tsx` | VERIFIED | 476 | Sessions table with `(you)` badge, terminate actions; SCIM section with token generation UI |
| `frontend/src/features/settings/hooks/use-sso-settings.ts` | VERIFIED | 162 | All hooks: `useSamlConfig`, `useUpdateSamlConfig`, `useOidcConfig`, `useUpdateOidcConfig`, `useSetSsoRequired`, `useRoleClaimMapping`, `useUpdateRoleClaimMapping` |
| `frontend/src/features/settings/hooks/use-custom-roles.ts` | VERIFIED | 128 | All hooks: `useCustomRoles`, `useCustomRole`, `useCreateRole`, `useUpdateRole`, `useDeleteRole`, `useAssignRole` |
| `frontend/src/features/settings/hooks/use-sessions.ts` | VERIFIED | 66 | `useSessions` (30s polling), `useTerminateSession`, `useTerminateAllUserSessions` |
| `frontend/src/features/settings/hooks/use-scim.ts` | VERIFIED | 24 | `useGenerateScimToken` |
| `frontend/src/features/auth/hooks/use-sso-login.ts` | VERIFIED | 105 | `useWorkspaceSsoStatus`, `useSsoLogin` (SAML → fetch+redirect, OIDC → `signInWithOAuth`), `useApplyClaimsRole` |
| `frontend/src/features/members/components/member-role-badge.tsx` | VERIFIED | 51 | Shows custom role name or built-in badge; wired in `member-row.tsx` and `member-card.tsx` |
| `frontend/src/app/(workspace)/[workspaceSlug]/settings/sso/page.tsx` | VERIFIED | — | App Router page exists |
| `frontend/src/app/(workspace)/[workspaceSlug]/settings/roles/page.tsx` | VERIFIED | — | App Router page exists |
| `frontend/src/app/(workspace)/[workspaceSlug]/settings/security/page.tsx` | VERIFIED | — | App Router page exists |
| `backend/tests/unit/services/test_sso_service.py` | VERIFIED | — | 22 tests, all passing |
| `backend/tests/unit/services/test_rbac_service.py` | VERIFIED | — | 16 tests, all passing |
| `backend/tests/unit/services/test_session_service.py` | VERIFIED | — | 8 tests, all passing |
| `backend/tests/unit/routers/test_auth_sso.py` | VERIFIED | — | 11 tests, all passing |
| `backend/tests/unit/routers/test_scim.py` | VERIFIED | — | 13 tests, all passing |

**Total backend test count: 70 passing, 0 failing**

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `custom_role.py` | `workspace_member.py` | `custom_role_id` FK | WIRED | Migration 064 adds FK with `ondelete="SET NULL"` |
| `064_migration` | `workspace_sessions table` | `op.create_table` | WIRED | Migration creates table with full schema |
| `auth_sso.py router` | `SamlAuthProvider` | `_get_saml_provider()` | WIRED | Factory function instantiated at line 63; called at lines 205, 258, 339 |
| `saml_auth.py process_response` | Supabase admin API | `auth.admin.create_user` | WIRED | `SsoService.provision_saml_user` calls admin client |
| `permissions.py check_permission` | `custom_role_repository.get()` | async DB lookup | WIRED | `check_permission` queries member with `joinedload` of `custom_role` relationship |
| `custom_roles.py router` | `rbac_service` | `RbacServiceDep` | PARTIAL | DI wired via `dependencies.py` but router NOT registered in `main.py` |
| `SessionRecordingMiddleware` | Redis | `session:lastseen:{token_hash}` key (60s TTL) | WIRED | `_LASTSEEN_KEY_TEMPLATE` at line 34; throttle logic present |
| `session_service.force_terminate` | Supabase `auth.admin.sign_out` | `supabase_admin_client` | WIRED | `terminate_all_for_user` calls `supabase_admin_client.auth.admin.sign_out` |
| `SessionRecordingMiddleware revocation check` | Redis `session:revoked:{workspace_id}:{token_hash}` | `redis.get(key)` | WIRED | `_REVOKED_KEY_TEMPLATE` at line 33; checked on every request |
| `scim.py get_scim_workspace dependency` | `workspace.settings['scim_token_hash']` | SHA-256 comparison | WIRED | Lines 152-163 in `scim.py`: hash compared against stored `scim_token_hash` |
| `scim_service.provision_user` | `supabase admin_client.auth.admin.create_user()` | email from SCIM User | WIRED | `ScimService.provision_user` calls Supabase admin API |
| `scim_service.deprovision_user` | `workspace_member.is_active = False` | `member_repo.update()` | WIRED | `deprovision_user` sets `is_active=False` at line 228 |
| `sso-settings-page.tsx` | `/api/v1/auth/sso/saml/config` | `useUpdateSamlConfig` mutation | WIRED | `useUpdateSamlConfig` consumed at line 97; mutation fires on save |
| `roles-settings-page.tsx` | `/api/v1/workspaces/{slug}/roles` | `useCustomRoles` query + `useCreateRole` mutation | WIRED (but 404 at runtime) | Hooks wired, but endpoint unreachable due to missing router registration |
| `security-settings-page.tsx terminate button` | `/workspaces/{slug}/sessions/{id} DELETE` | `useTerminateSession` mutation | WIRED | Hook consumed at line 150; mutation fires on confirm |
| `security-settings-page.tsx generate token button` | `/workspaces/{slug}/settings/scim-token POST` | `useGenerateScimToken` mutation | WIRED | Hook consumed at line 152 |
| `login page SSO button` | `use-sso-login.ts useSsoLogin` | `onClick` handler | WIRED | Line 124 in login/page.tsx calls `initiateSsoLogin` |
| `useSsoLogin (OIDC path)` | `Supabase auth.signInWithOAuth` | `supabase.auth.signInWithOAuth()` | WIRED | Line 64 in `use-sso-login.ts` |
| `useSsoLogin (SAML path)` | `GET /api/v1/auth/sso/saml/initiate` | fetch then redirect | WIRED | Lines 72-78 in `use-sso-login.ts` |
| `useApplyClaimsRole` | `POST /api/v1/auth/sso/claim-role` | POST after OIDC login | WIRED | Line 100 in `use-sso-login.ts` |

---

### Requirements Coverage

| Requirement | Plans | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| AUTH-01 | 01-01, 01-02, 01-07, 01-09 | Admin can configure SAML 2.0 SSO with Okta/Azure AD | SATISFIED | `SamlAuthProvider` + `SsoService.configure_saml` + `auth_sso.py` SAML endpoints + `SsoSettingsPage` SAML form |
| AUTH-02 | 01-01, 01-05, 01-07, 01-09 | Admin can configure OIDC SSO with Google Workspace or compatible provider | SATISFIED | `SsoService.configure_oidc` + OIDC endpoints in `auth_sso.py` + `SsoSettingsPage` OIDC section + `useSsoLogin` OIDC path |
| AUTH-03 | 01-01, 01-05, 01-09 | Users receive workspace roles from IdP claims | SATISFIED | `map_claims_to_role` (default "member", never "owner") + `apply_sso_role` + `POST /auth/sso/claim-role` + `useApplyClaimsRole` |
| AUTH-04 | 01-01, 01-05, 01-07, 01-09 | Admin can force SSO-only login (disable password auth) | SATISFIED | `SsoService.set_sso_required` + `GET /auth/sso/login-check` returns 403 + login page hides email/password form when `ssoRequired=true` |
| AUTH-05 | 01-01, 01-03, 01-07, 01-09 | Admin can define custom RBAC roles with per-resource permission grants | BLOCKED | All backend logic exists and tests pass, but `custom_roles_router` is NOT in `main.py` — endpoints return 404 at runtime |
| AUTH-06 | 01-01, 01-04, 01-08 | Admin can view all active sessions and force-terminate any session | SATISFIED | `SessionRecordingMiddleware` + `SessionService` + sessions router (registered in main.py) + `SecuritySettingsPage` sessions table |
| AUTH-07 | 01-01, 01-06, 01-08 | Admin can configure SCIM 2.0 to auto-provision/deprovision users | SATISFIED | `ScimService` (provision/deprovision/patch) + SCIM router (registered in main.py) + SCIM bearer token auth + `SecuritySettingsPage` SCIM section |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `backend/src/pilot_space/main.py` | `custom_roles_router` exported but not registered | Blocker | All 6 RBAC endpoints (AUTH-05) are unreachable; `GET /workspaces/{slug}/roles` returns 404 |

No stub implementations, TODO/FIXME markers, or placeholder returns found in any Phase 1 service, router, or frontend component files.

---

### Human Verification Required

#### 1. SAML Assertion End-to-End Flow

**Test:** Configure a SAML IdP (or mock), trigger login via `GET /auth/sso/saml/initiate`, submit a SAML assertion to the callback endpoint.
**Expected:** User created in Supabase, workspace membership created, valid JWT returned.
**Why human:** Requires a live SAML IdP or signed XML assertions; cannot generate valid `python3-saml` signed assertions in unit tests.

#### 2. SSO-Only Mode Login Block

**Test:** Set `sso_required=true` on a workspace, then attempt email/password login on the login page (not via API).
**Expected:** Email/password form is hidden; only the SSO button is shown; attempting to submit credentials via API returns 403.
**Why human:** UI rendering behavior and the interaction between frontend and backend SSO enforcement check.

#### 3. SCIM Provisioning with Real IdP

**Test:** Configure Okta or Azure AD SCIM client, point at `/api/v1/scim/v2/{slug}/Users`, generate a SCIM token, and trigger a provisioning event.
**Expected:** User created in Supabase, workspace member created with `is_active=true`; deprovisioning event sets `is_active=false` without deleting data.
**Why human:** Requires live IdP SCIM client; SCIM payload format varies by provider.

#### 4. SessionRecordingMiddleware Throttle Behavior

**Test:** Make two authenticated requests within 60 seconds to the same workspace endpoint.
**Expected:** Only one DB write to `workspace_sessions`; second request skips the upsert but succeeds normally.
**Why human:** Throttle behavior depends on Redis TTL behavior in a live Redis instance.

---

### Gaps Summary

**1 gap blocking goal achievement:**

**AUTH-05 — RBAC endpoints unreachable at runtime.**
The `custom_roles_router` was implemented fully (343 lines, 6 endpoints covering create/list/get/update/delete role and assign role to member), exported from `routers/__init__.py`, and DI-wired via `RbacServiceDep` in `dependencies.py`. However, it was never added to `app.include_router()` in `main.py`. All 16 RBAC service tests pass, but the admin cannot reach the role management API.

The fix is a 2-line addition to `main.py`:
1. Add `custom_roles_router` to the import block from `pilot_space.api.v1.routers`
2. Add `app.include_router(custom_roles_router, prefix=API_V1_PREFIX)` to the router registration section

**All other AUTH requirements (AUTH-01, 02, 03, 04, 06, 07) are fully implemented, tested (70 backend tests passing), and wired end-to-end through backend services, API routers, frontend hooks, and admin UI pages.**

---

_Verified: 2026-03-07T16:07:57Z_
_Verifier: Claude (gsd-verifier)_
