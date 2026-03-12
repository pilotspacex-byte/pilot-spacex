---
phase: 018-tech-debt-closure
plan: 03
subsystem: testing
tags: [playwright, oidc, docker, e2e, sso, oidc-server-mock]

requires:
  - phase: 08-fix-sso-integration
    provides: SSO backend endpoints (SAML + OIDC config, enforcement, status)
provides:
  - Mock OIDC IdP Docker infrastructure for CI-reproducible SSO testing
  - Playwright E2E test covering OIDC flow for 3 provider types (Okta, Azure AD, Google)
  - Reusable oidc-mock Playwright fixture with Docker lifecycle management
affects: [ci-pipeline, sso-testing, auth-regression]

tech-stack:
  added: [oidc-server-mock, playwright-fixtures]
  patterns: [parameterized-e2e-tests, docker-fixture-lifecycle]

key-files:
  created:
    - infra/oidc-mock/docker-compose.yml
    - infra/oidc-mock/oidc-mock-config.json
    - infra/oidc-mock/oidc-mock-users.json
    - frontend/e2e/fixtures/oidc-mock.ts
    - frontend/e2e/oidc-login.spec.ts
  modified: []

key-decisions:
  - "oidc-server-mock chosen as mock IdP -- purpose-built for testing, supports OIDC discovery, configurable users/clients"
  - "E2E tests verify config API + mock IdP interaction rather than full Supabase OIDC handshake -- Supabase Auth provider registry not dynamically configurable at runtime"
  - "Playwright fixture uses worker scope for Docker lifecycle -- container shared across all tests in a worker, started once"

patterns-established:
  - "Docker-backed E2E fixture: start/health-check/stop pattern for external services in Playwright"
  - "Parameterized provider tests: PROVIDER_CONFIGS array iterating test.describe per provider"

requirements-completed: [DEBT-01]

duration: 5min
completed: 2026-03-11
---

# Phase 018 Plan 03: OIDC E2E Test Summary

**Playwright E2E test for OIDC SSO login flow using oidc-server-mock Docker IdP, covering Okta/Azure AD/Google Workspace with parameterized test suites**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-11T06:16:51Z
- **Completed:** 2026-03-11T06:21:30Z
- **Tasks:** 1 (Task 2 is non-blocking checkpoint)
- **Files created:** 5

## Accomplishments
- Mock OIDC IdP Docker setup with 3 client configurations and 3 test users with provider-specific claims
- Playwright fixture managing Docker container lifecycle (start, health check, teardown) at worker scope
- Parameterized E2E tests verifying OIDC discovery, authorize endpoint, login flow, and callback URL construction for all 3 provider types
- SSO settings API integration test for OIDC configuration CRUD

## Task Commits

Each task was committed atomically:

1. **Task 1: Mock OIDC IdP Docker setup + Playwright E2E test** - `df6295e2` (feat)

## Files Created/Modified
- `infra/oidc-mock/docker-compose.yml` - Docker compose for oidc-server-mock on port 9090
- `infra/oidc-mock/oidc-mock-config.json` - 3 OIDC client configs (Okta, Azure AD, Google) with PKCE support
- `infra/oidc-mock/oidc-mock-users.json` - 3 test users with provider-specific claims (groups, hd, email)
- `frontend/e2e/fixtures/oidc-mock.ts` - Playwright fixture for Docker lifecycle + client credential constants
- `frontend/e2e/oidc-login.spec.ts` - Parameterized E2E tests for OIDC SSO flow across 3 providers

## Decisions Made
- Used oidc-server-mock (ghcr.io/soluto/oidc-server-mock) as the mock IdP -- purpose-built for testing OIDC flows, supports configurable users, clients, claims, and PKCE
- Tests verify the SSO config API and mock IdP interaction rather than the full Supabase OIDC handshake, because Supabase Auth's provider registry is not dynamically configurable at test runtime
- Port 9090 chosen for mock IdP to avoid conflicts with backend (8000), frontend (3000), and Supabase Kong (18000)
- Docker fixture uses worker scope in Playwright -- container is shared across all tests in a worker, avoiding repeated start/stop overhead

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed eslint unused variable warnings**
- **Found during:** Task 1 (pre-commit hook)
- **Issue:** `oidcMock`, `client`, and `capturedRedirectUrl` variables flagged as unused by eslint
- **Fix:** Prefixed unused destructured param with `_`, removed unused `capturedRedirectUrl` tracking code
- **Files modified:** `frontend/e2e/oidc-login.spec.ts`
- **Verification:** Pre-commit hooks pass cleanly on second attempt
- **Committed in:** df6295e2 (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor lint fix. No scope creep.

## Issues Encountered
- Pre-commit eslint and prettier hooks caught formatting and unused variable issues on first commit attempt. Fixed inline and recommitted successfully.

## User Setup Required
None - no external service configuration required. Docker must be available for running mock IdP.

## Next Phase Readiness
- OIDC E2E test infrastructure ready for CI integration
- Mock IdP can be extended with additional users/clients for future SSO test scenarios
- Manual verification against real IdP test tenants remains optional (Task 2 checkpoint)

---
*Phase: 018-tech-debt-closure*
*Completed: 2026-03-11*

## Self-Check: PASSED

All 5 created files verified on disk. Commit df6295e2 verified in git log.
