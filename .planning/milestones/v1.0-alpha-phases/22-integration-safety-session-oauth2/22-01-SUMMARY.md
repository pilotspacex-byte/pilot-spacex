---
phase: 22-integration-safety-session-oauth2
plan: 01
subsystem: api
tags: [fastapi, asyncio, sqlalchemy, oauth2, session-management, background-tasks]

# Dependency graph
requires:
  - phase: 14-mcp-integration
    provides: MCP server CRUD, OAuth callback endpoint
  - phase: 19-workspace-plugin-seeding
    provides: SeedPluginsService and workspace creation hook
provides:
  - Independent-session background task pattern for SeedPluginsService
  - Workspace-slug-aware OAuth callback redirect
affects: [frontend-mcp-settings, workspace-creation-flow]

# Tech tracking
tech-stack:
  added: []
  patterns: [independent-session-background-task, workspace-slug-in-oauth-state]

key-files:
  created: []
  modified:
    - backend/src/pilot_space/api/v1/routers/workspaces.py
    - backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py
    - backend/tests/unit/services/test_seed_plugins_service.py
    - backend/tests/api/test_workspace_mcp_servers.py

key-decisions:
  - "Use get_db_session() async context manager for background tasks instead of passing request session"
  - "Store workspace_slug in Redis state_data during OAuth URL generation for callback redirect"
  - "Fallback to /settings/mcp-servers for legacy state_data without workspace_slug (backward compat)"

patterns-established:
  - "Independent session background task: use get_db_session() in fire-and-forget tasks, never pass request-scoped session"
  - "OAuth state enrichment: include workspace_slug in Redis state for redirect URL reconstruction"

requirements-completed: [SKRG-05, MCP-03]

# Metrics
duration: 18min
completed: 2026-03-12
---

# Phase 22 Plan 01: Integration Safety Summary

**Fixed SeedPluginsService session-sharing race condition with independent get_db_session() and OAuth callback redirect with workspace slug prefix**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-12T04:07:24Z
- **Completed:** 2026-03-12T04:25:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Eliminated session-sharing race condition: background plugin seeding now uses its own DB session via get_db_session()
- OAuth callback redirect now includes workspace slug prefix (/{slug}/settings/mcp-servers)
- Backward compatibility maintained for legacy OAuth state without workspace_slug
- Added 5 new tests covering both fixes (2 for background task, 3 for OAuth redirect)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix SeedPluginsService session-sharing race condition** - `5b450338` (test: RED), `e3e11754` (feat: GREEN)
2. **Task 2: Fix OAuth callback redirect to include workspace slug** - `db984c49` (feat+test: GREEN)

_Note: TDD tasks have RED (failing test) and GREEN (implementation) commits_

## Files Created/Modified
- `backend/src/pilot_space/api/v1/routers/workspaces.py` - Extracted _seed_workspace_background() with independent session
- `backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py` - Added workspace_slug to OAuth state and redirect URL
- `backend/tests/unit/services/test_seed_plugins_service.py` - Tests for independent session and non-fatal exception handling
- `backend/tests/api/test_workspace_mcp_servers.py` - Tests for OAuth redirect with/without workspace slug

## Decisions Made
- Used get_db_session() async context manager for the background task (same pattern as mcp_oauth_callback)
- Kept SeedPluginsService import lazy inside the background task to avoid circular imports
- Error paths before state parsing (error, missing_params, no_redis, invalid_state, state_decode_error) use fallback_redirect without workspace slug since slug is unavailable at that point

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-commit hooks (prek) stash/restore cycle caused file modifications to be lost during commits, requiring re-application of edits
- Some pre-existing frontend files were accidentally included in intermediate commits by the hook system

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend OAuth redirect fix is complete; frontend MCP settings page can now receive the workspace-prefixed redirect
- Background task pattern established for future fire-and-forget operations

---
*Phase: 22-integration-safety-session-oauth2*
*Completed: 2026-03-12*

## Self-Check: PASSED

All 4 modified files verified on disk. All 3 task commits verified in git log.
