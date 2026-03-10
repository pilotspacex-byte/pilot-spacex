---
phase: 01-identity-and-access
plan: 07
subsystem: frontend-settings
tags: [sso, rbac, settings, tanstack-query, react]
dependency_graph:
  requires: [01-02, 01-03]
  provides: [sso-settings-ui, custom-roles-ui]
  affects: [settings-navigation]
tech_stack:
  added: []
  patterns:
    - TanStack Query hooks for SSO and RBAC API operations
    - Plain React component (not observer()) for settings pages
    - Vitest + Testing Library test pattern with vi.mock
key_files:
  created:
    - frontend/src/features/settings/hooks/use-sso-settings.ts
    - frontend/src/features/settings/hooks/use-custom-roles.ts
    - frontend/src/features/settings/hooks/index.ts
    - frontend/src/features/settings/pages/sso-settings-page.tsx
    - frontend/src/features/settings/pages/roles-settings-page.tsx
    - frontend/src/features/settings/pages/__tests__/sso-settings-page.test.tsx
    - frontend/src/features/settings/pages/__tests__/roles-settings-page.test.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/sso/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/roles/page.tsx
  modified:
    - frontend/src/features/settings/pages/index.ts
    - frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx
decisions:
  - SsoSettingsPage is a plain React component (not observer()) — settings pages
    use TanStack Query exclusively for server state; no MobX observables needed
  - useSetSsoRequired mutation renamed to ssoRequiredMutation at call site to avoid
    naming conflict with setSsoRequired React state setter
  - 409 conflict errors in useCreateRole/useUpdateRole bubble to callers; callers
    display inline error rather than toast
  - Permission expand logic (manage implies delete/write/read) applied client-side
    via expandPermissions() function; backend also enforces hierarchy
metrics:
  duration: ~35 min
  completed: "2026-03-07T15:34:00Z"
  tasks: 2
  files: 11
---

# Phase 1 Plan 7: Admin SSO and RBAC Settings UI Summary

Admin settings UI for SSO configuration (SAML 2.0 + OIDC) and custom RBAC role
management, connecting AUTH-01/AUTH-02/AUTH-04/AUTH-05 backend APIs to production-ready
settings pages with TanStack Query hooks, permission matrix UI, and full test coverage.

## What Was Built

### Task 1: TanStack Query hooks + tests (TDD)

**use-sso-settings.ts** — 7 hooks covering all SSO operations:
- `useSamlConfig(workspaceSlug)` — GET SAML config
- `useUpdateSamlConfig(workspaceSlug)` — PUT SAML config, sets query cache on success
- `useOidcConfig(workspaceSlug)` — GET OIDC config
- `useUpdateOidcConfig(workspaceSlug)` — PUT OIDC config
- `useSetSsoRequired(workspaceSlug)` — PATCH SSO enforcement, invalidates SAML cache
- `useRoleClaimMapping(workspaceSlug)` — GET claim-role mappings
- `useUpdateRoleClaimMapping(workspaceSlug)` — PUT claim-role mappings

**use-custom-roles.ts** — 6 hooks for RBAC role management:
- `useCustomRoles`, `useCustomRole` — GET lists and individual roles
- `useCreateRole`, `useUpdateRole` — mutations that invalidate list cache; 409 conflict bubbles to callers
- `useDeleteRole` — invalidates list cache
- `useAssignRole` — PATCH member's custom_role_id, invalidates members cache

**hooks/index.ts** — barrel exports all hooks from use-workspace-settings, use-sso-settings, use-custom-roles

**Tests (RED → GREEN):**
- sso-settings-page.test.tsx: 9 tests — SAML section, OIDC section, SSO toggle, role claim mapping, loading state, warning on enable, access restriction, copy button, save mutation
- roles-settings-page.test.tsx: 11 tests — roles list, empty state, create button, dialog open, permission badges, delete confirmation, edit dialog, permission checkboxes, loading state, access restriction, 409 duplicate error

### Task 2: Settings pages + App Router wiring

**sso-settings-page.tsx** — 4-card layout:
1. SAML 2.0 Configuration: entity_id, SSO URL, X.509 certificate, read-only ACS URL with copy button
2. OIDC / OAuth 2.0 Configuration: provider dropdown (Google/Azure/Okta), client ID, client secret, issuer URL (Azure/Okta only)
3. Role Claim Mapping: claim key + dynamic claim_value → role_id rows (add/remove)
4. SSO Enforcement: Switch with warning message when enabling

**roles-settings-page.tsx** — full CRUD UI:
- Roles table with permission badges (truncated to 5, +N more overflow)
- Create/Edit Dialog with permission matrix (7 resources x 4 actions checkboxes)
- manage-implies-lower logic via `expandPermissions()` client-side
- Delete confirmation AlertDialog with membership impact warning
- Form validation: name required, at least 1 permission required
- Inline 409 duplicate name error display

**App Router pages:**
- `/settings/sso/page.tsx` — Server Component wrapper
- `/settings/roles/page.tsx` — Server Component wrapper

**Settings navigation** — layout.tsx updated with SSO (Shield icon) and Custom Roles (Users icon) in Workspace section.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Naming collision: setSsoRequired**
- **Found during:** Task 1 GREEN phase (transform error at build)
- **Issue:** `const setSsoRequired = useSetSsoRequired(...)` shadowed `const [ssoRequired, setSsoRequired] = React.useState(false)` — esbuild rejected the duplicate symbol
- **Fix:** Renamed mutation result to `ssoRequiredMutation`; updated all call sites
- **Files modified:** `sso-settings-page.tsx`
- **Commit:** 3b9b490d

**2. [Rule 1 - Bug] Test mock missing ApiError export**
- **Found during:** Task 1 GREEN phase (test run)
- **Issue:** `vi.mock('@/services/api', ...)` replaced the entire module with only `apiClient`; dynamic `import('@/services/api')` in the duplicate-name test couldn't find `ApiError`
- **Fix:** Used `importOriginal` pattern to spread actual module before overriding `apiClient`
- **Files modified:** `roles-settings-page.test.tsx`
- **Commit:** 3b9b490d

**3. [Rule 1 - Bug] TypeScript strict array access type errors**
- **Found during:** Task 1 type-check
- **Issue:** `getAllByRole(...)[0]` inferred as `HTMLElement | undefined`; `user.click()` requires `Element`
- **Fix:** Added non-null assertions `[0]!` at 3 locations in test file
- **Files modified:** `roles-settings-page.test.tsx`
- **Commit:** 3b9b490d

**4. [Rule 1 - Bug] Test assertion for provider dropdown caused multiple-element error**
- **Found during:** Task 1 GREEN phase
- **Issue:** `getByText('Google Workspace')` matched both the SelectTrigger display value and SelectContent item
- **Fix:** Changed test to assert on Client ID/Client Secret inputs instead of provider text
- **Files modified:** `sso-settings-page.test.tsx`
- **Commit:** 3b9b490d

## Self-Check

Checking created files exist and commits are present:

- [x] `frontend/src/features/settings/hooks/use-sso-settings.ts` — created
- [x] `frontend/src/features/settings/hooks/use-custom-roles.ts` — created
- [x] `frontend/src/features/settings/hooks/index.ts` — created
- [x] `frontend/src/features/settings/pages/sso-settings-page.tsx` — created
- [x] `frontend/src/features/settings/pages/roles-settings-page.tsx` — created
- [x] `frontend/src/features/settings/pages/__tests__/sso-settings-page.test.tsx` — created (9 tests)
- [x] `frontend/src/features/settings/pages/__tests__/roles-settings-page.test.tsx` — created (11 tests)
- [x] `frontend/src/app/(workspace)/[workspaceSlug]/settings/sso/page.tsx` — created
- [x] `frontend/src/app/(workspace)/[workspaceSlug]/settings/roles/page.tsx` — created
- [x] Task 1 commit: 3b9b490d
- [x] Task 2 commit: ec750636
- [x] pnpm lint: 0 errors
- [x] pnpm type-check: clean
- [x] pnpm test: 20/20 passing

## Self-Check: PASSED
