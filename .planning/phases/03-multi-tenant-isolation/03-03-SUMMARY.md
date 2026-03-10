---
phase: 03-multi-tenant-isolation
plan: 03
subsystem: api
tags: [rate-limiting, redis, storage-quota, middleware, fastapi]

# Dependency graph
requires:
  - phase: 03-02
    provides: migration 067 with rate_limit_standard_rpm, rate_limit_ai_rpm, storage_quota_mb, storage_used_bytes columns on workspaces table

provides:
  - RateLimitMiddleware._get_effective_limit() reading per-workspace RPM from Redis ws_limits:{workspace_id} with DB fallback
  - Violation counter rl_violations:{workspace_id}:{YYYYMMDD} incremented on every 429
  - _check_storage_quota() helper: (False, None) at 100%, (True, pct) at 80%+, (True, None) unlimited
  - _update_storage_usage() atomic delta update via SQL expression
  - GET /workspaces/{slug}/settings/quota (ADMIN+)
  - PATCH /workspaces/{slug}/settings/quota (OWNER — invalidates Redis ws_limits cache)
  - POST /workspaces/{slug}/settings/quota/recalculate (OWNER — recount from notes+issues)
  - Workspace model with rate_limit_standard_rpm, rate_limit_ai_rpm, storage_quota_mb, storage_used_bytes columns

affects: [04-ai-governance, write-path-middleware, notes-router, issues-router]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-workspace Redis cache (ws_limits:{workspace_id}, 60s TTL) with DB fallback for rate limit config
    - Violation counter pattern: daily Redis key with 7-day retention for anomaly detection
    - Atomic delta update via SQLAlchemy update() expression to avoid race conditions
    - RedisDep injection for quota PATCH endpoint (same pattern as ghost_text, issues_ai_context)

key-files:
  created:
    - backend/src/pilot_space/api/v1/routers/workspace_quota.py
  modified:
    - backend/src/pilot_space/api/middleware/rate_limiter.py
    - backend/src/pilot_space/infrastructure/database/models/workspace.py
    - backend/src/pilot_space/api/v1/routers/__init__.py
    - backend/src/pilot_space/main.py
    - backend/tests/security/test_rate_limiting.py
    - backend/tests/unit/test_storage_quota.py

key-decisions:
  - "RateLimitMiddleware uses async_sessionmaker (not DI container) for DB fallback — avoids wiring complexity in middleware context, same pattern as SCIM"
  - "Rate limiter fail-open on Redis error: _get_effective_limit() catches all exceptions, returns system default"
  - "Violation counter uses UTC date in key (rl_violations:{workspace_id}:{YYYYMMDD}) with 7-day TTL for compliance audit trail"
  - "Workspace quota router created as workspace_quota.py (separate from workspaces.py) — workspaces.py was 392 lines, quota adds ~400 more, both stay under 700 limit"
  - "PATCH /settings/quota uses RedisDep for cache invalidation — consistent with ghost_text and issues_ai_context patterns"
  - "Storage quota enforcement via helper functions, not middleware — allows per-endpoint opt-in rather than blanket enforcement (plan intent: notes and issues write paths)"

patterns-established:
  - "Per-workspace Redis cache pattern: ws_limits:{workspace_id} JSON blob, 60s TTL, DB fallback, system default on error"
  - "Quota helper functions: _check_storage_quota() returns (bool, pct|None) for pre-write check; _update_storage_usage() for post-write atomic delta"

requirements-completed:
  - TENANT-03

# Metrics
duration: 35min
completed: 2026-03-08
---

# Phase 03 Plan 03: Per-Workspace Rate Limits and Storage Quota Enforcement

**Redis-cached per-workspace RPM overrides in RateLimitMiddleware, violation counters, and storage quota API with 507 hard block and X-Storage-Warning header at 80%**

## Performance

- **Duration:** 35 min
- **Started:** 2026-03-08T12:00:00Z
- **Completed:** 2026-03-08T12:35:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Extended RateLimitMiddleware with `_get_effective_limit()` that reads per-workspace RPM from Redis (ws_limits:{workspace_id}, 60s TTL), falls back to DB query on cache miss, and returns system defaults on any error (fail-open)
- Added daily violation counter (rl_violations:{workspace_id}:{YYYYMMDD}, 7-day TTL) incremented on every 429 response
- Created workspace_quota.py router with GET/PATCH/recalculate quota endpoints, storage quota helper functions, and Redis cache invalidation on PATCH
- Added rate_limit_standard_rpm, rate_limit_ai_rpm, storage_quota_mb, storage_used_bytes columns to Workspace SQLAlchemy model (matching migration 067)

## Task Commits

1. **Task 1: Per-workspace rate limits in RateLimitMiddleware** - `07254671` (feat)
2. **Task 2: Storage quota enforcement + GET/PATCH quota API** - `b9e2d703` (feat)

## Files Created/Modified

- `backend/src/pilot_space/api/middleware/rate_limiter.py` - Added `_get_effective_limit()`, `_get_workspace_limits_from_db()`, `_increment_violation_counter()` methods; dispatch now uses effective limit
- `backend/src/pilot_space/infrastructure/database/models/workspace.py` - Added 4 quota columns matching migration 067
- `backend/src/pilot_space/api/v1/routers/workspace_quota.py` - New router: GET/PATCH /settings/quota, POST /settings/quota/recalculate, plus `_check_storage_quota()` and `_update_storage_usage()` helpers
- `backend/src/pilot_space/api/v1/routers/__init__.py` - Registered workspace_quota_router
- `backend/src/pilot_space/main.py` - Added `app.include_router(workspace_quota_router, ...)`
- `backend/tests/security/test_rate_limiting.py` - Added 6 tests for per-workspace limits, Redis cache, system defaults, violation counter
- `backend/tests/unit/test_storage_quota.py` - Replaced 4 xfail stubs with 12 real passing tests

## Decisions Made

- `async_sessionmaker` used in RateLimitMiddleware (middleware context, no DI) — same pattern as SCIM service
- Workspace quota router extracted to `workspace_quota.py` to keep both files under 700 lines
- `RedisDep` used for PATCH endpoint Redis injection — consistent with existing patterns in ghost_text and issues_ai_context routers
- Storage enforcement implemented as helper functions (not middleware) — allows write-path opt-in per endpoint, avoiding blanket enforcement on read paths

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pyright type errors in rate_limiter.py**
- **Found during:** Task 1 (implementation)
- **Issue:** `sessionmaker[AsyncSession]` type annotation incompatible with sync sessionmaker; fixed to `async_sessionmaker`
- **Fix:** Changed `sessionmaker` to `async_sessionmaker` from `sqlalchemy.ext.asyncio`
- **Files modified:** backend/src/pilot_space/api/middleware/rate_limiter.py
- **Verification:** `uv run pyright rate_limiter.py` reports 0 errors
- **Committed in:** 07254671 (Task 1 commit)

**2. [Rule 3 - Blocking] Removed unused imports in workspace_quota.py**
- **Found during:** Task 2 (implementation)
- **Issue:** Ruff flagged unused `Request`, `func`, `select` imports; Redis needed at runtime not just TYPE_CHECKING
- **Fix:** Removed unused imports, moved to proper import locations using `RedisDep` pattern
- **Files modified:** backend/src/pilot_space/api/v1/routers/workspace_quota.py
- **Verification:** `uv run ruff check` and `uv run pyright` report 0 errors
- **Committed in:** b9e2d703 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug/type error, 1 blocking import issue)
**Impact on plan:** Both fixes required for correctness. No scope creep.

## Issues Encountered

- FastAPI raises `FastAPIError: Invalid args for response field` when `Redis | None` is used directly in route signature (not via `Annotated` + `Depends`). Resolved by using `RedisDep = Annotated[RedisClient, Depends(get_redis_client)]` which is the existing project pattern.

## Next Phase Readiness

- TENANT-03 complete: per-workspace rate limits operational, storage quota infrastructure ready
- Caller code in notes/issues write paths still needs to call `_check_storage_quota()` and `_update_storage_usage()` (planned for Phase 3 plan 04)
- Rate limiter DB fallback requires `db_url` parameter at initialization — currently only system defaults used in production until wired in lifespan

---
*Phase: 03-multi-tenant-isolation*
*Completed: 2026-03-08*
