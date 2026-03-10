---
phase: 01-identity-and-access
plan: 09
subsystem: auth
tags: [sso, saml, oidc, supabase, react, tanstack-query, member-roles, custom-roles]

# Dependency graph
requires:
  - phase: 01-05
    provides: SSO backend endpoints (/auth/sso/status, /auth/sso/saml/initiate, /auth/sso/claim-role)
  - phase: 01-07
    provides: SSO settings admin UI + useRoleClaimMapping hook patterns
  - phase: 01-08
    provides: SecuritySettingsPage patterns (plain React, no observer for TanStack-only pages)

provides:
  - SSO login button on login page (shows when workspace has SSO configured via workspace_id param)
  - useWorkspaceSsoStatus hook (queries /auth/sso/status, no auth required)
  - useSsoLogin hook (OIDC via supabase.auth.signInWithOAuth; SAML via /saml/initiate redirect)
  - useApplyClaimsRole hook (POSTs to /auth/sso/claim-role after OIDC callback)
  - Auth callback updated to apply SSO role claims (non-fatal on failure)
  - MemberRoleBadge component (custom role name OR built-in role badge, unified visual style)
  - WorkspaceMember TypeScript interface extended with custom_role and is_active fields

affects:
  - Phase 2 (AI features): WorkspaceMember interface now has custom_role for permission checks
  - Future member list implementations should use MemberRoleBadge for role column

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SSO login gate: workspace_id in URL query param triggers SSO status fetch before rendering form"
    - "OIDC via Supabase signInWithOAuth with workspace_id in redirectTo for post-login role mapping"
    - "Auth callback applies SSO role claims non-fatally (graceful degradation)"
    - "MemberRoleBadge: single component for custom/built-in role display — replaces inline Badge usage"

key-files:
  created:
    - frontend/src/features/auth/hooks/use-sso-login.ts
    - frontend/src/features/auth/hooks/__tests__/use-sso-login.test.ts
    - frontend/src/features/members/components/member-role-badge.tsx
    - frontend/src/features/members/components/__tests__/member-role-badge.test.tsx
  modified:
    - frontend/src/app/(auth)/login/page.tsx
    - frontend/src/app/(auth)/callback/page.tsx
    - frontend/src/features/issues/hooks/use-workspace-members.ts
    - frontend/src/features/members/components/member-card.tsx
    - frontend/src/features/settings/components/member-row.tsx

key-decisions:
  - "SSO button visible only when workspace_id is in URL query param — avoids showing SSO for non-SSO workspaces at the shared login page"
  - "OIDC path uses Supabase signInWithOAuth — Supabase handles PKCE, provider redirect, and session establishment"
  - "SAML path: fetch /saml/initiate then window.location.href — browser hard-navigate to IdP"
  - "Claims role application in callback is non-fatal — unmapped claims default to member on backend"
  - "MemberRoleBadge data-testid: role-badge-{role} for built-in, role-badge-custom for custom roles"
  - "WorkspaceMember.custom_role and is_active are optional fields (? modifier) — backwards compatible with existing API responses"

patterns-established:
  - "useWorkspaceSsoStatus: enabled only when workspaceId is non-null; 60s staleTime"
  - "useSsoLogin: returns stable callback (useCallback), no deps — safe to call in event handlers"
  - "MemberRoleBadge: accepts role + customRole, renders null when both are null/undefined"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04]

# Metrics
duration: 7min
completed: 2026-03-07
---

# Phase 1 Plan 9: SSO Login Flow + MemberRoleBadge Summary

**SSO login button with SAML/OIDC redirect, post-OIDC role claim application, and MemberRoleBadge component for custom roles in member views**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-07T15:52:12Z
- **Completed:** 2026-03-07T16:00:02Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Login page shows "Continue with SSO" button when `workspace_id` query param is present and workspace has SSO configured
- Login page hides email/password form entirely when `sso_required=true` (SSO-only enforcement, AUTH-04)
- SAML flow: fetches redirect URL from `/auth/sso/saml/initiate` then hard-navigates to IdP
- OIDC flow: delegates to `supabase.auth.signInWithOAuth` with `workspace_id` in `redirectTo` for post-login role claims
- Auth callback page applies SSO role claims after OIDC login (non-fatal — graceful degradation when no mapping configured)
- MemberRoleBadge: unified component shows custom role name (outline Badge) or built-in role badge — used in member-card and member-row
- WorkspaceMember interface extended with `custom_role` and `is_active` optional fields

## Task Commits

1. **Task 1: SSO login hooks + login page SSO integration** - `69b32ed4` (feat)
2. **Task 2: MemberRoleBadge component for custom roles** - `9219dc7e` (feat)

## Files Created/Modified

- `frontend/src/features/auth/hooks/use-sso-login.ts` - Three hooks: useWorkspaceSsoStatus, useSsoLogin, useApplyClaimsRole
- `frontend/src/features/auth/hooks/__tests__/use-sso-login.test.ts` - 8 unit tests (TDD)
- `frontend/src/features/members/components/member-role-badge.tsx` - MemberRoleBadge component
- `frontend/src/features/members/components/__tests__/member-role-badge.test.tsx` - 12 unit tests (TDD)
- `frontend/src/app/(auth)/login/page.tsx` - SSO button + sso_required enforcement
- `frontend/src/app/(auth)/callback/page.tsx` - SSO claims role application post-OIDC
- `frontend/src/features/issues/hooks/use-workspace-members.ts` - Added custom_role and is_active fields
- `frontend/src/features/members/components/member-card.tsx` - Uses MemberRoleBadge
- `frontend/src/features/settings/components/member-row.tsx` - Uses MemberRoleBadge

## Decisions Made

- SSO button only appears when `workspace_id` is in URL query param — prevents SSO button showing on the general login page for non-SSO users
- `useApplyClaimsRole` in callback is non-fatal — if role mapping not configured or claim-role fails, user still logs in as their default role
- MemberRoleBadge custom role uses `variant="outline"` to match member/guest visual style — custom roles are team-specific and treated as peer to the built-in non-elevated roles

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — pre-commit hook (prettier) reformatted files on first commit attempt; resolved by re-staging after hook ran.

## User Setup Required

None - no external service configuration required. The SSO login flow requires workspace SSO to be configured via the admin SSO settings page (from plan 01-07).

## Next Phase Readiness

- Phase 1 identity and access complete: all 9 plans executed
- AUTH-01 through AUTH-04 requirements fulfilled
- SSO login flow is end-to-end: admin configures SAML/OIDC (01-07) → user logs in via SSO button (01-09) → role claims applied (01-09)
- MemberRoleBadge ready for Phase 2 features that display member lists with custom roles

---
*Phase: 01-identity-and-access*
*Completed: 2026-03-07*
