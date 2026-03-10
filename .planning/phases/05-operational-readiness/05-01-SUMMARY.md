---
phase: 05-operational-readiness
plan: "01"
subsystem: infra
tags: [health-checks, kubernetes, fastapi, asyncio, monitoring]

# Dependency graph
requires: []
provides:
  - "GET /health/live: shallow liveness probe returning {status: ok}, no DB/Redis touch"
  - "GET /health/ready: deep readiness probe with parallel DB/Redis/Supabase checks"
  - "GET /health: backward-compatible alias for /health/ready with full nested-checks structure"
  - "health_checks.py with check_database, check_redis, check_supabase async functions"
  - "Auth middleware PUBLIC_ROUTES updated to include /health/live and /health/ready"
affects: [05-02, 05-03, 05-04, 05-05, 05-06, kubernetes-deployment, monitoring-stack]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-tier health check: liveness (shallow, no deps) vs readiness (deep, parallel async checks)"
    - "asyncio.timeout() nesting: 2s per-check, 5s total — prevents cascading timeouts"
    - "CRITICAL_CHECKS frozenset to distinguish unhealthy (DB/Redis down) from degraded (Supabase down)"
    - "TDD RED/GREEN: failing test scaffold committed before implementation"

key-files:
  created:
    - backend/src/pilot_space/infrastructure/health_checks.py
    - backend/src/pilot_space/api/routers/health.py
    - backend/src/pilot_space/api/routers/__init__.py
    - backend/tests/routers/test_health.py
  modified:
    - backend/src/pilot_space/api/middleware/auth_middleware.py
    - backend/src/pilot_space/main.py

key-decisions:
  - "health_router mounted at root level (not under /api/v1 prefix) — health checks are infra, not API versioned resources"
  - "CRITICAL_CHECKS = {database, redis} — supabase failure yields degraded not unhealthy; supabase outage should not stop traffic"
  - "check_redis creates a short-lived RedisClient for the probe instead of reusing app-level singleton — isolates health check connectivity from app connection pool"
  - "Legacy /health route handled via dual @router.get decorators — avoids separate handler function, same readiness logic"

patterns-established:
  - "Health check functions use lazy imports (inside try block) to defer module-level import errors until probe time"
  - "Each check returns {status: ok|error, latency_ms|error} dict — consistent shape for monitoring tool parsing"

requirements-completed:
  - OPS-03

# Metrics
duration: 4min
completed: 2026-03-08
---

# Phase 5 Plan 01: Health Check Endpoints Summary

**Two-tier Kubernetes health probes with async DB/Redis/Supabase dependency checks, structured JSON response, and auth bypass — replacing stub endpoints with production-ready liveness and readiness handlers**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-08T16:45:20Z
- **Completed:** 2026-03-08T16:49:00Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments

- Liveness probe at /health/live returns `{"status": "ok"}` in <1ms with zero external dependency calls
- Readiness probe at /health/ready and /health performs parallel async checks for database (SELECT 1), Redis (PING), and Supabase (/health) with 2s per-check and 5s total timeouts
- Status logic: unhealthy (DB or Redis down), degraded (Supabase only down), healthy (all pass)
- Old stub handlers in main.py replaced; auth middleware updated with new route paths

## Task Commits

Each task was committed atomically:

1. **Task 1: Health checker infrastructure + test scaffold (RED)** - `6959d51f` (test)
2. **Task 2: Health router + main.py wiring + auth bypass (GREEN)** - `984231dd` (feat)

**Plan metadata:** (included in final docs commit)

_Note: TDD tasks had two commits per plan (RED scaffold then GREEN implementation)_

## Files Created/Modified

- `backend/src/pilot_space/infrastructure/health_checks.py` - Async check_database, check_redis, check_supabase functions
- `backend/src/pilot_space/api/routers/health.py` - Health router with /health/live and /health/ready handlers
- `backend/src/pilot_space/api/routers/__init__.py` - Package init for top-level routers
- `backend/tests/routers/test_health.py` - 6 OPS-03 unit tests (liveness, readiness, db-down, degraded, legacy, no-auth)
- `backend/src/pilot_space/api/middleware/auth_middleware.py` - Added /health/live and /health/ready to PUBLIC_ROUTES
- `backend/src/pilot_space/main.py` - Replaced stub handlers with health_router include_router call

## Decisions Made

- health_router mounted at root level without /api/v1 prefix — health checks are infrastructure, not versioned API resources; Kubernetes probes expect stable /health/live not /api/v1/health/live
- CRITICAL_CHECKS = {database, redis} — Supabase failure causes degraded not unhealthy; a Supabase Gateway outage should not stop Kubernetes from routing traffic (DB/Redis still work)
- Separate RedisClient instance in check_redis rather than reusing app singleton — health probe should independently verify connectivity without relying on pool state
- Dual @router.get decorators on readiness() for both /health/ready and /health — avoids code duplication while maintaining backward compatibility with monitoring tools using the old /health path

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-commit ruff hook auto-fixed import ordering in health_checks.py (import group ordering); required re-staging after first commit attempt. Not a logic change.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- /health/live and /health/ready are operational and will correctly signal pod health to Kubernetes
- Monitoring tools can parse structured `checks` dict to alert on specific dependency failures
- Ready for 05-02 (structured logging) and subsequent operational readiness plans

## Self-Check: PASSED

- FOUND: backend/src/pilot_space/infrastructure/health_checks.py
- FOUND: backend/src/pilot_space/api/routers/health.py
- FOUND: backend/tests/routers/test_health.py
- FOUND: .planning/phases/05-operational-readiness/05-01-SUMMARY.md
- FOUND commit: 6959d51f (test RED)
- FOUND commit: 984231dd (feat GREEN)
- FOUND commit: d6fcbdf8 (docs metadata)

---
*Phase: 05-operational-readiness*
*Completed: 2026-03-08*
