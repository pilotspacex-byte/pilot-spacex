---
phase: 03-multi-tenant-isolation
plan: 04
subsystem: api
tags: [bearer-token, admin, operator-dashboard, fastapi, sqlalchemy, redis, secretstr]

# Dependency graph
requires:
  - phase: 03-01
    provides: RLS isolation tests scaffold and UPPERCASE enum fix
provides:
  - get_super_admin FastAPI dependency validating PILOT_SPACE_SUPER_ADMIN_TOKEN
  - GET /api/v1/admin/workspaces — cross-workspace list with health metrics
  - GET /api/v1/admin/workspaces/{slug} — workspace detail with top members and AI actions
  - pilot_space_super_admin_token SecretStr field in Settings
affects: [03-07, operator-dashboard-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Class-based lazy session factory to avoid PLW0603 global statement (admin router)
    - HTTPBearer(auto_error=False) + manual 401 — ensures WWW-Authenticate header on 401
    - Redis SCAN (non-blocking) for rate-limit violation aggregation; fail-open on error
    - SecretStr for admin token — masks in repr/logs/Pydantic errors without extra config

key-files:
  created:
    - backend/src/pilot_space/dependencies/admin.py
    - backend/src/pilot_space/api/v1/routers/admin.py
  modified:
    - backend/src/pilot_space/config.py
    - backend/src/pilot_space/api/v1/routers/__init__.py
    - backend/src/pilot_space/main.py
    - backend/tests/routers/test_admin.py

key-decisions:
  - "Admin router uses class-based _AdminSessionFactory (not global) — avoids PLW0603, keeps test patchability"
  - "HTTPBearer(auto_error=False) so missing header returns 401 with WWW-Authenticate, not 403"
  - "Redis rl_violations SCAN with fail-open — admin view degrades gracefully if Redis is down"
  - "No DI wiring for admin router — factory pattern same as SCIM (avoids container complexity)"

patterns-established:
  - "Class-based lazy-init for module-level singletons: avoids global statement, patchable in tests"
  - "Token masking via Pydantic SecretStr: no custom logging filter needed, masked by default"

requirements-completed:
  - TENANT-04

# Metrics
duration: 9min
completed: 2026-03-08
---

# Phase 3 Plan 04: Super-Admin Operator Dashboard Backend Summary

**Bearer token authenticated cross-workspace admin API with SecretStr token in settings, Redis violation counts, and SQL aggregation for workspace health metrics**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-03-08T08:18:06Z
- **Completed:** 2026-03-08T08:27:27Z
- **Tasks:** 2 (TDD: RED + GREEN for each task)
- **Files modified:** 6

## Accomplishments
- `get_super_admin` dependency: validates bearer token against `PILOT_SPACE_SUPER_ADMIN_TOKEN` env var (SecretStr); returns 401 for missing/invalid/unconfigured token
- `GET /api/v1/admin/workspaces`: cross-workspace list with member_count, owner_email, storage_used_bytes, ai_action_count, rate_limit_violation_count (Redis SCAN)
- `GET /api/v1/admin/workspaces/{slug}`: workspace detail with top 5 active members, last 10 AI actions, quota config; 404 on unknown slug
- Token never appears in logs (logged as `****`); SecretStr prevents repr/model_dump exposure
- 8 tests all passing; no regressions in router test suite

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: failing tests for dependency + settings** - `b1fc7348` (test)
2. **Task 1+2 GREEN: implement production code** - `208d6d35` (feat)

_Note: TDD tasks RED→GREEN. Both tasks' implementations committed together as a single GREEN commit after lint fixes._

## Files Created/Modified
- `backend/src/pilot_space/dependencies/admin.py` - `get_super_admin` FastAPI dependency
- `backend/src/pilot_space/api/v1/routers/admin.py` - Admin router: list + detail endpoints
- `backend/src/pilot_space/config.py` - Added `pilot_space_super_admin_token: SecretStr | None`
- `backend/src/pilot_space/api/v1/routers/__init__.py` - Export `admin_router`
- `backend/src/pilot_space/main.py` - Register `admin_router` at `/api/v1/admin`
- `backend/tests/routers/test_admin.py` - 8 tests replacing xfail stubs

## Decisions Made
- Admin router uses `_AdminSessionFactory` class (not `global`) — avoids `PLW0603` while keeping the module-level lazy-init pattern testable via `patch`
- `HTTPBearer(auto_error=False)` — FastAPI default `auto_error=True` would return 403 for missing schemes; we override to 401 with `WWW-Authenticate: Bearer` header per RFC 6750
- Redis `SCAN` (not `KEYS`) for rate-limit violations — non-blocking, safe under load; fails open returning 0 if Redis unavailable
- No DI wiring — factory pattern identical to SCIM router; no `wiring_config.modules` update needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced `global` statement with class-based factory**
- **Found during:** GREEN phase — ruff reported `PLW0603`
- **Issue:** `global _admin_session_factory` triggers ruff warning; plan sketched this pattern
- **Fix:** Introduced `_AdminSessionFactory` callable class; instance assigned as `_get_admin_session_factory`
- **Files modified:** `backend/src/pilot_space/api/v1/routers/admin.py`
- **Verification:** `ruff check` passes, tests still pass (class instance is patchable)
- **Committed in:** `208d6d35`

**2. [Rule 1 - Bug] Replaced bare try/except/pass with contextlib.suppress**
- **Found during:** GREEN phase — ruff reported `SIM105`
- **Issue:** `try: ... except (ValueError, TypeError): pass` in Redis value parsing
- **Fix:** `with contextlib.suppress(ValueError, TypeError): total += int(v)`
- **Files modified:** `backend/src/pilot_space/api/v1/routers/admin.py`
- **Committed in:** `208d6d35`

---

**Total deviations:** 2 auto-fixed (Rule 1 - code quality)
**Impact on plan:** Both fixes address ruff lint rules; no behavioral change. No scope creep.

## Issues Encountered
- Pre-commit ruff-format reformatted `admin.py` on first commit attempt — re-staged and committed successfully on second attempt. Expected behavior.

## User Setup Required
Set environment variable at deployment time:
```bash
PILOT_SPACE_SUPER_ADMIN_TOKEN=<random-256-bit-secret>
```
This value is never logged, never exposed in `repr()`, and must be rotated via env var update (no DB record).

## Next Phase Readiness
- Admin backend complete; frontend dashboard (Plan 03-07) can use `GET /api/v1/admin/workspaces` and `GET /api/v1/admin/workspaces/{slug}`
- Rate-limit violation tracking requires Redis keys in `rl_violations:{workspace_id}:{date}` format written by rate-limit middleware (Plan 03-03 writes these)
- No blockers for remaining Phase 3 plans

---
*Phase: 03-multi-tenant-isolation*
*Completed: 2026-03-08*
