---
phase: 14-remote-mcp-server-management
plan: 01
subsystem: testing
tags: [pytest, vitest, xfail, mcp, mcp-servers, wave-0, tdd]

# Dependency graph
requires: []
provides:
  - "Wave 0 xfail test stubs for workspace MCP server API (MCP-01..06)"
  - "Wave 0 xfail test stubs for remote MCP hot-loading in agent (MCP-04)"
  - "Wave 0 it.todo test stubs for MCPServersStore frontend observable"
affects: [14-remote-mcp-server-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "xfail(strict=False) stubs: test files exist and run before implementation ships"
    - "it.todo() stubs: Vitest pending tests for Wave 0 frontend contracts"
    - "Local fixtures inside test bodies: keep xfail isolation correct when imports fail"

key-files:
  created:
    - backend/tests/api/__init__.py
    - backend/tests/api/test_workspace_mcp_servers.py
    - backend/tests/ai/__init__.py
    - backend/tests/ai/agents/__init__.py
    - backend/tests/ai/agents/test_remote_mcp_loading.py
    - frontend/src/stores/ai/__tests__/MCPServersStore.test.ts
  modified: []

key-decisions:
  - "xfail(strict=False) on API stubs: tests run their body but mark XFAIL on any failure so suite exits 0 in Wave 0"
  - "Imports inside test bodies (not module level): prevents import failure from breaking the entire xfail file when implementation modules are absent"
  - "it.todo() for frontend stubs: Vitest treats todo as pending (not failing), correct Wave 0 state before MCPServersStore is built"
  - "Local fixtures (mcp_workspace_with_admin, mcp_workspace_with_member) defined in test file: decouples from root conftest, avoids polluting shared fixture namespace"

patterns-established:
  - "Pattern 1: Local xfail fixture: define workspace fixtures locally in API test files for feature-specific RLS/role setup"
  - "Pattern 2: Deferred assertion shape: each xfail stub body contains the exact assert statements that will pass once implementation ships"

requirements-completed: [MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06]

# Metrics
duration: 18min
completed: 2026-03-10
---

# Phase 14 Plan 01: Remote MCP Server Management Summary

**Wave 0 behavioral contract: 9 xfail pytest stubs + 6 Vitest todo stubs defining the full MCP-01..06 acceptance criteria before any implementation code exists**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-10T09:06:00Z
- **Completed:** 2026-03-10T09:24:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created `backend/tests/api/test_workspace_mcp_servers.py` with 6 xfail stubs covering MCP-01 through MCP-06 (register, token encrypted, OAuth callback, status endpoint, delete, admin-only gate)
- Created `backend/tests/ai/agents/test_remote_mcp_loading.py` with 3 xfail stubs covering MCP-04 agent hot-loading (builds SSE config, skips on decrypt failure, empty dict on no workspace)
- Created `frontend/src/stores/ai/__tests__/MCPServersStore.test.ts` with 6 it.todo() stubs covering loadServers, registerServer, removeServer, checkStatus behaviors
- All 9 backend tests exit 0 as XFAIL; all 6 frontend tests exit 0 as todo/pending

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend API test stubs (MCP-01 through MCP-06)** - `4c96a238` (test)
2. **Task 2: Agent injection test stub (MCP-04) + frontend store stub** - `67a3bd31` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/tests/api/__init__.py` - Package init for new API tests directory
- `backend/tests/api/test_workspace_mcp_servers.py` - 6 xfail stubs: register_server, token_encrypted_at_rest, oauth_callback_stores_token, status_endpoint, delete_removes_from_agent, admin_only
- `backend/tests/ai/__init__.py` - Package init for AI tests directory
- `backend/tests/ai/agents/__init__.py` - Package init for agent tests subdirectory
- `backend/tests/ai/agents/test_remote_mcp_loading.py` - 3 xfail stubs: builds_sse_config, skips_on_decrypt_failure, empty_no_workspace
- `frontend/src/stores/ai/__tests__/MCPServersStore.test.ts` - 6 it.todo() stubs for MCPServersStore observable behavior

## Decisions Made

- Imports inside test function bodies (not module-level): When the implementation modules (`workspace_mcp_server.py`, `pilotspace_stream_utils._load_remote_mcp_servers`) don't exist yet, a module-level import would break the entire test file and prevent xfail collection. Function-local imports keep each test isolated so xfail works correctly.
- Local workspace fixtures defined in `test_workspace_mcp_servers.py`: The MCP API tests need workspace+admin and workspace+member setups with specific roles. Defining them locally avoids polluting the shared root conftest and keeps the fixture semantics clear per test file.
- `it.todo()` chosen over `it.skip()` for frontend stubs: Vitest's todo explicitly documents intent-to-implement, whereas skip implies deliberate exclusion. Both exit 0 but todo communicates Wave 0 state more clearly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed EN DASH character from docstring (RUF002)**
- **Found during:** Task 1 (pre-commit hook)
- **Issue:** Module docstring used unicode EN DASH (U+2013) in "plans 02-03" - ruff RUF002 flags ambiguous unicode
- **Fix:** Replaced EN DASH with ASCII hyphen-minus in two docstring locations
- **Files modified:** `backend/tests/api/test_workspace_mcp_servers.py`
- **Verification:** `uv run ruff check` passes cleanly
- **Committed in:** `4c96a238` (Task 1 commit)

**2. [Rule 1 - Bug] Fixed unsorted imports and unused uuid4 import (I001, F401)**
- **Found during:** Task 2 (pre-commit hook)
- **Issue:** Ruff flagged unsorted import blocks inside test function bodies; `uuid4` was imported but unused in two test functions
- **Fix:** `uv run ruff check --fix` auto-sorted imports and removed unused uuid4 imports
- **Files modified:** `backend/tests/ai/agents/test_remote_mcp_loading.py`
- **Verification:** `uv run ruff check` passes cleanly
- **Committed in:** `67a3bd31` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - linting bugs caught by pre-commit)
**Impact on plan:** Both were minor linting issues caught by pre-commit hooks. No scope creep.

## Issues Encountered

- Pre-commit hooks caught EN DASH (unicode RUF002) in docstring and unsorted import blocks on first commit attempts. Fixed inline before final commit, no impact on test behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 test infrastructure complete; plans 14-02 (DB model + migration), 14-03 (API router), 14-04 (agent wiring), 14-05 (frontend store) can now run the test suite to validate implementation
- All 9 xfail backend tests will turn XPASS as each plan ships its implementation
- 6 frontend todos will be converted to real assertions in plan 14-05

---
*Phase: 14-remote-mcp-server-management*
*Completed: 2026-03-10*

## Self-Check: PASSED

- FOUND: backend/tests/api/test_workspace_mcp_servers.py
- FOUND: backend/tests/ai/agents/test_remote_mcp_loading.py
- FOUND: frontend/src/stores/ai/__tests__/MCPServersStore.test.ts
- FOUND: commit 4c96a238
- FOUND: commit 67a3bd31
