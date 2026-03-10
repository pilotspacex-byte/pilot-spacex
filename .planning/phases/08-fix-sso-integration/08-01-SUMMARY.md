---
phase: 08-fix-sso-integration
plan: 01
subsystem: auth
tags: [sso, saml, oidc, fastapi, nextjs, supabase-auth, verifyOtp, magiclink, slug-routing]

# Dependency graph
requires:
  - phase: 01-identity-and-access
    provides: SSO router (auth_sso.py), SsoService, SAML auth provider, role claim mapping
provides:
  - slug-based admin SSO endpoints (workspace_slug replaces workspace_id:UUID)
  - SAML callback returning RedirectResponse with token_hash
  - provision_saml_user calling generate_link and returning token_hash
  - frontend /auth/saml-callback page exchanging token_hash via verifyOtp
affects: [any frontend calling SSO admin config endpoints, SAML login flow, SSO e2e tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_resolve_and_authorize: combined slug-resolution + permission check helper (reduces boilerplate on 7 admin endpoints)"
    - "TDD RED→GREEN: failing tests committed before implementation, then all pass after fixes"
    - "SAML callback as browser redirect (302) instead of JSON response — enables frontend to handle JWT exchange"

key-files:
  created:
    - frontend/src/app/(auth)/saml-callback/page.tsx
    - frontend/src/app/(auth)/saml-callback/page.test.tsx
  modified:
    - backend/src/pilot_space/api/v1/routers/auth_sso.py
    - backend/src/pilot_space/application/services/sso_service.py
    - backend/tests/unit/routers/test_auth_sso.py
    - backend/tests/unit/services/test_sso_service.py

key-decisions:
  - "auth_sso.py uses _resolve_and_authorize helper (not per-endpoint resolve+check) — reduces 7-endpoint boilerplate from 5 lines to 1 line each while staying under 700-line limit"
  - "saml_callback workspace_id stays UUID — IdP is server-side POST with UUID embedded in initiate flow; changing would break IdP integration"
  - "provision_saml_user calls generate_link inside same try block — token_hash generation failure is fatal (user can't log in without it)"
  - "SamlCallbackPage is plain component (NOT observer()) — no MobX observables; matches pattern established for all auth pages"
  - "Frontend test uses synchronous mockGet.mockImplementation — simpler than async dynamic imports in mock helpers"

patterns-established:
  - "_resolve_and_authorize(slug, session, user_id): single call for resolve+permission check in admin endpoints"
  - "SAML JWT exchange: backend generates magiclink token_hash → redirect to /auth/saml-callback → verifyOtp → session"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04]

# Metrics
duration: 11min
completed: 2026-03-09
---

# Phase 08 Plan 01: Fix SSO Integration Summary

**End-to-end SAML SSO unblocked: slug-based admin endpoints (no more 422), SAML callback returns 302 redirect with magic-link token_hash, frontend /auth/saml-callback page exchanges token_hash via supabase.auth.verifyOtp**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-09T07:08:28Z
- **Completed:** 2026-03-09T07:19:27Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Fixed 7 admin SSO endpoints (configure_saml, get_saml_config, configure_oidc, get_oidc_config, set_sso_enforcement, configure_role_claim_mapping, get_role_claim_mapping) to accept `workspace_slug: str` instead of `workspace_id: UUID` — eliminates 422 errors from frontend slug-based calls
- Fixed SAML callback to return `RedirectResponse(302)` with `token_hash` instead of JSON placeholder — enables frontend to exchange hash for real JWT
- Added `provision_saml_user` → `admin.generate_link(type="magiclink")` → `token_hash` in return dict — closes the missing JWT link
- Created `/auth/saml-callback` frontend page that calls `supabase.auth.verifyOtp` to establish Supabase JWT session from SAML login

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failing tests (RED phase)** - `204eaed9` (test)
2. **Task 2: Fix backend slug endpoints + SAML callback redirect (GREEN phase)** - `318273e0` (feat)
3. **Task 3: Add frontend saml-callback page + tests** - `93df7800` (feat)

_Note: TDD tasks — test commit before implementation commit._

## Files Created/Modified

- `backend/src/pilot_space/api/v1/routers/auth_sso.py` — Added `_resolve_workspace`, `_resolve_and_authorize` helpers; changed 7 admin endpoints from `workspace_id:UUID` to `workspace_slug:str`; changed `saml_callback` return from `dict` to `RedirectResponse`
- `backend/src/pilot_space/application/services/sso_service.py` — Added `get_settings` import; added `admin.generate_link` call in `provision_saml_user`; `token_hash` added to return dict
- `backend/tests/unit/routers/test_auth_sso.py` — 6 new tests for slug-based endpoints and callback redirect
- `backend/tests/unit/services/test_sso_service.py` — 2 new tests for `provision_saml_user` generate_link behavior
- `frontend/src/app/(auth)/saml-callback/page.tsx` — New SAML callback page: reads token_hash, calls verifyOtp, applies role mapping, redirects
- `frontend/src/app/(auth)/saml-callback/page.test.tsx` — 4 Vitest tests covering all branches

## Decisions Made

- `_resolve_and_authorize` helper consolidates slug→UUID resolution + settings:manage permission check into a single `await` call, keeping each admin endpoint under 5 additional lines and the file under 700 lines
- `saml_callback`'s `workspace_id: UUID` parameter was intentionally NOT changed (IdP posts UUID embedded from the initiate flow — changing it would break IdP integration)
- `provision_saml_user` raises RuntimeError on `generate_link` failure (not non-fatal) — token_hash is required for the frontend to establish a session; silent failure would leave the user unable to log in
- `SamlCallbackPage` is a plain React component (not observer()) — consistent with all existing auth pages; no MobX observables needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added _resolve_and_authorize combined helper**
- **Found during:** Task 2 (implementing 7 admin endpoints)
- **Issue:** Repeating 5-line `_resolve_workspace` + `check_permission` block on 7 endpoints pushed file to 778 lines (max 700)
- **Fix:** Extracted `_resolve_and_authorize(slug, session, user_id)` helper — reduces each endpoint to 1 line; file dropped to 696 lines
- **Files modified:** backend/src/pilot_space/api/v1/routers/auth_sso.py
- **Verification:** 41 tests pass, pyright clean, file under 700 lines
- **Committed in:** 318273e0 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed SamlConfigRequest name_id_format=None in test**
- **Found during:** Task 2 GREEN phase test run
- **Issue:** Test passed `name_id_format=None` but field has type `str` with default value — pydantic ValidationError
- **Fix:** Removed the explicit `name_id_format=None` argument (let the default apply)
- **Files modified:** backend/tests/unit/routers/test_auth_sso.py
- **Verification:** test_configure_saml_accepts_workspace_slug passes
- **Committed in:** 318273e0 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correctness and line limit compliance. No scope creep.

## Issues Encountered

- Pre-commit `detect-secrets` flagged `client_secret="secret-abc"` in test — resolved by adding `# pragma: allowlist secret` comment and using a clearly non-secret value
- Pre-commit `ruff-format` and `prettier` reformatted files on first commit — re-staged after formatting on second attempt

## Next Phase Readiness

- AUTH-01 through AUTH-04 are now functionally complete end-to-end for SAML flows
- OIDC callback flow may need similar treatment if OIDC uses a different mechanism (not covered in this phase)
- E2E tests for SAML login flow can now be written against working endpoints

---
*Phase: 08-fix-sso-integration*
*Completed: 2026-03-09*

## Self-Check: PASSED

All 6 files exist. All 3 task commits verified in git history.
