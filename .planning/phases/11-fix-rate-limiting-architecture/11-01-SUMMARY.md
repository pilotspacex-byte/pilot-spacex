---
phase: 11-fix-rate-limiting-architecture
plan: "01"
subsystem: api
tags: [rate-limiting, redis, middleware, starlette, fastapi, tenant-isolation]

# Dependency graph
requires:
  - phase: 05-operational-readiness
    provides: RateLimitMiddleware skeleton in rate_limiter.py
provides:
  - Lazy Redis accessor pattern in RateLimitMiddleware (_resolve_redis)
  - Module-level RateLimitMiddleware registration in main.py (TENANT-03 now active)
  - Integration test proving middleware intercepts and returns 429 via TestClient
affects:
  - Any phase adding or modifying middleware registration order
  - Any phase modifying DI container redis_client provider

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy container resolution in middleware (resolve once on first dispatch, flag _redis_resolved)
    - BaseHTTPMiddleware must return Response not raise HTTPException (JSONResponse(429) not raise)
    - Module-level middleware registration for Starlette stack freeze compatibility

key-files:
  created: []
  modified:
    - backend/src/pilot_space/api/middleware/rate_limiter.py
    - backend/src/pilot_space/main.py
    - backend/tests/security/test_rate_limiting.py

key-decisions:
  - "Lazy resolution via _resolve_redis(request): reads container.redis_client().client on first dispatch, no-op on subsequent calls — follows SessionRecordingMiddleware._resolve_dependencies pattern"
  - "dispatch() returns JSONResponse(429) instead of raising HTTPException(429): Starlette collapse_excgroups converts raised exceptions to 500 in BaseHTTPMiddleware context"
  - "Module-level app.add_middleware(RateLimitMiddleware) with no constructor args — all dependencies resolved lazily from request.app.state.container"

patterns-established:
  - "Lazy DI resolution in BaseHTTPMiddleware: set a _resolved flag, read from request.app.state.container on first dispatch, fail-open (log debug, skip rate limiting) if container not ready"
  - "Return JSONResponse for error responses inside BaseHTTPMiddleware.dispatch() — never raise HTTPException"

requirements-completed: [TENANT-03]

# Metrics
duration: 45min
completed: 2026-03-09
---

# Phase 11 Plan 01: Fix Rate Limiting Architecture Summary

**Lazy Redis accessor + module-level registration makes TENANT-03 per-workspace rate limiting active for all requests, with JSONResponse-based 429 returns that survive Starlette's exception middleware**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-03-09T00:00:00Z
- **Completed:** 2026-03-09T00:45:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fixed silent TENANT-03 regression: `app.add_middleware()` inside lifespan is a no-op after Starlette builds the frozen middleware stack. Moved registration to module scope.
- Added `_resolve_redis(request)` lazy accessor that reads `container.redis_client().client` on first dispatch and also wires `_session_factory` from `container.settings().database_url`, matching `SessionRecordingMiddleware` pattern exactly.
- Discovered and fixed secondary bug: `dispatch()` was using `_raise_rate_limit_exceeded()` which raises `HTTPException(429)` inside `BaseHTTPMiddleware`. Starlette's `collapse_excgroups` converts this to 500. Changed to `return _rate_limit_exceeded_response()` which returns `JSONResponse(429)` directly.
- Updated 4 existing tests that used `pytest.raises(HTTPException)` pattern — these now assert `response.status_code == 429` on the returned response.
- Added `TestRateLimitMiddlewareMainRegistration.test_middleware_active_returns_429_via_testclient` — uses `TestClient(app)` context manager + `patch.object(_resolve_redis)` to inject mock Redis. Verifies middleware is in the built stack AND returns 429 on limit exceeded. All 47 tests pass.

## Task Commits

Each task was committed atomically:

1. **Task 1: Lazy Redis accessor in RateLimitMiddleware** - `2b494f93` (feat)
2. **Task 2: Module-level registration + integration test** - `a722509f` (feat)

## Files Created/Modified
- `backend/src/pilot_space/api/middleware/rate_limiter.py` - Added `_resolve_redis()`, `_rate_limit_exceeded_response()`, changed `dispatch()` to call lazy resolver and return JSONResponse on 429, added `_redis_resolved` flag
- `backend/src/pilot_space/main.py` - Added module-level `app.add_middleware(RateLimitMiddleware)`, removed commented-out lifespan block
- `backend/tests/security/test_rate_limiting.py` - Updated 4 tests from raise-based to response-based 429 assertion, added `TestRateLimitMiddlewareMainRegistration` integration test class

## Decisions Made
- **Lazy resolution pattern**: Follow `SessionRecordingMiddleware._resolve_dependencies` exactly — single flag (`_redis_resolved`), read from `request.app.state.container`, fail-open on any exception (log debug, skip limiting)
- **JSONResponse not HTTPException**: `BaseHTTPMiddleware.dispatch()` must return a `Response` object for error conditions. Raising `HTTPException` inside dispatch causes Starlette's `collapse_excgroups` to escalate it to 500. Kept `_raise_rate_limit_exceeded()` for backward compatibility but dispatch now uses `_rate_limit_exceeded_response()`.
- **No-arg module-level registration**: `app.add_middleware(RateLimitMiddleware)` with zero constructor arguments. All dependencies resolved on first request.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] dispatch() returned 500 instead of 429 on rate limit exceeded**
- **Found during:** Task 2 (integration test)
- **Issue:** Integration test `TestClient` returned 500 on rate limit. Root cause: `dispatch()` called `self._raise_rate_limit_exceeded()` which raises `HTTPException(429)`. Inside `BaseHTTPMiddleware`, any raised exception is caught by Starlette's `collapse_excgroups` and re-raised as 500 via `ServerErrorMiddleware`.
- **Fix:** Added `_rate_limit_exceeded_response()` returning `JSONResponse(status_code=429)`. Changed `dispatch()` to `return self._rate_limit_exceeded_response()`. Kept `_raise_rate_limit_exceeded()` for backward compat (no active callers in dispatch path).
- **Files modified:** `backend/src/pilot_space/api/middleware/rate_limiter.py`
- **Verification:** Integration test returns 429. All 47 rate limiting tests pass.
- **Committed in:** `a722509f` (Task 2 commit)

**2. [Rule 1 - Bug] 4 existing tests broke after dispatch behavior change**
- **Found during:** Task 2 (test run after fixing dispatch)
- **Issue:** Tests used `pytest.raises(HTTPException)` expecting dispatch to raise. After dispatch now returns `JSONResponse`, these tests failed with "DID NOT RAISE".
- **Fix:** Updated all 4 affected tests to call the middleware directly and assert `response.status_code == status.HTTP_429_TOO_MANY_REQUESTS`.
- **Files modified:** `backend/tests/security/test_rate_limiting.py`
- **Verification:** All tests pass after update.
- **Committed in:** `a722509f` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs discovered during integration testing)
**Impact on plan:** Both fixes required for correctness — the 500-vs-429 bug was the exact root of the integration test failure. No scope creep.

## Issues Encountered
- prek pre-commit hook stashes unstaged changes during commit, which caused phase 10 changes (`auth_sso.py` 702-line violation) to temporarily surface. Resolved by using `git restore --staged` to unstage unrelated files before committing.
- ruff-format hook reformatted staged files after first commit attempt, requiring re-stage before second attempt.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- TENANT-03 rate limiting is now fully active. Per-workspace overrides (via `ws_limits:{workspace_id}` Redis cache backed by DB columns `rate_limit_standard_rpm` / `rate_limit_ai_rpm`) are operational.
- Phase 10 (audit log repository wiring) continues in parallel on the same branch.

---
*Phase: 11-fix-rate-limiting-architecture*
*Completed: 2026-03-09*
