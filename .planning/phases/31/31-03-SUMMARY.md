---
phase: 31-mcp-infra-hardening
plan: 03
subsystem: backend/mcp
tags: [mcp, cap, repository, fastapi, tests]
dependency_graph:
  requires: []
  provides: [count_active_by_workspace, MCP_SERVER_CAP]
  affects: [workspace_mcp_servers router, WorkspaceMcpServerRepository]
tech_stack:
  added: []
  patterns: [SQLAlchemy func.count, HTTP 422 cap enforcement]
key_files:
  created: []
  modified:
    - backend/src/pilot_space/infrastructure/database/repositories/workspace_mcp_server_repository.py
    - backend/src/pilot_space/api/v1/routers/workspace_mcp_servers.py
    - backend/tests/api/test_workspace_mcp_servers.py
decisions:
  - "MCP_SERVER_CAP = 10 at module level makes the constant importable by tests"
  - "Cap check placed after set_rls_context but before WorkspaceMcpServer construction to avoid wasted object allocation"
  - "Repo instantiation moved up (before cap check) so the same instance handles both count and create"
  - "Integration tests use flush() not commit() to stay compatible with rollback-wrapped db_session fixture"
metrics:
  duration: "4 minutes"
  completed: "2026-03-20"
  tasks_completed: 1
  files_changed: 3
requirements:
  - MCPI-04
---

# Phase 31 Plan 03: Add Per-Workspace MCP Server Cap Summary

Add `count_active_by_workspace()` to `WorkspaceMcpServerRepository` and enforce a hard cap of 10 active MCP servers per workspace in the registration endpoint, returning HTTP 422 with a human-readable remediation message when the cap is exceeded.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Add count_active_by_workspace + MCP_SERVER_CAP + cap check + tests | 624785d4 | Done |

## What Was Built

### Repository (`workspace_mcp_server_repository.py`)
- Added `func` to the sqlalchemy import (`and_, func, select`)
- Added `count_active_by_workspace(workspace_id: UUID) -> int` method using `SELECT COUNT(*) WHERE workspace_id = ? AND is_deleted = FALSE`

### Router (`workspace_mcp_servers.py`)
- Added `MCP_SERVER_CAP = 10` constant at module level (after logger, before router)
- Moved `WorkspaceMcpServerRepository` import and instantiation before `WorkspaceMcpServer(...)` constructor
- Added cap check: `if count >= MCP_SERVER_CAP: raise HTTPException(422, ...)`
- Removed duplicate repo instantiation that previously appeared after the server object constructor

### Tests (`test_workspace_mcp_servers.py`)
Added 7 new MCPI-04 tests:
1. `test_mcp_server_cap_tenth_succeeds` — verifies `MCP_SERVER_CAP == 10`
2. `test_mcp_server_cap_eleventh_fails` — verifies count >= cap triggers 422 with "10" and "maximum" in detail
3. `test_mcp_server_cap_message_readable` — verifies "Delete an existing server" appears in detail
4. `test_count_active_by_workspace_method_exists` — verifies method exists and is a coroutine
5. `test_count_active_by_workspace_excludes_deleted` — DB integration: 2 active + 1 deleted → count == 2
6. `test_count_active_by_workspace_empty` — DB integration: empty workspace → count == 0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test DB session used `commit()` instead of `flush()`**
- **Found during:** Task 1 (GREEN — tests failing after first run)
- **Issue:** The `db_session` fixture wraps in a rollback transaction. Calling `await db_session.commit()` closes the transaction and subsequent queries fail with `InvalidRequestError: Can't operate on closed transaction`.
- **Fix:** Replaced `await db_session.commit()` with `await db_session.flush()` in both DB integration tests.
- **Files modified:** `backend/tests/api/test_workspace_mcp_servers.py`
- **Commit:** 624785d4

**2. [Rule 3 - Blocking] Pre-existing pyright error in `pilotspace_stream_utils.py` blocking commit**
- **Found during:** Task 1 commit (pre-commit hook failure)
- **Issue:** `pilotspace_stream_utils.py` had unstaged changes (from another plan on the same branch) that added `cast` usage in function bodies, but the stash temporarily removed `cast` from the import, causing pyright to report an unused import error in the stashed version.
- **Fix:** Staged `pilotspace_stream_utils.py` and its test file together with this plan's changes.
- **Files modified:** `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py`, `backend/tests/unit/ai/agents/test_pilotspace_stream_utils.py`
- **Commit:** 624785d4

## Verification Results

```
cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -q
# 11 passed, 6 xfailed (pre-existing stubs)

cd backend && uv run pyright src/...workspace_mcp_server_repository.py src/...workspace_mcp_servers.py
# 0 errors, 0 warnings, 0 informations

cd backend && uv run ruff check src/...workspace_mcp_server_repository.py src/...workspace_mcp_servers.py
# All checks passed!
```

## Self-Check: PASSED

- [x] `count_active_by_workspace` exists in `workspace_mcp_server_repository.py`
- [x] `MCP_SERVER_CAP = 10` defined in `workspace_mcp_servers.py`
- [x] Cap check is before `WorkspaceMcpServer(...)` constructor in `register_mcp_server`
- [x] Commit 624785d4 exists
- [x] All 11 non-xfail tests pass
- [x] Pyright and ruff clean on both source files
