---
phase: 34-mcp-observability
plan: 01
subsystem: api
tags: [audit-log, mcp, hashlib, sqlalchemy, alembic, fastapi, pydantic]

# Dependency graph
requires:
  - phase: 33-remote-mcp-approval
    provides: WorkspaceMcpServer model with approval_mode; migration 093; mcp__remote_*__* tool name convention
provides:
  - AuditLogHook._create_audit_callback() extended with remote MCP detection (action='ai.mcp_tool_call')
  - GET /api/v1/ai/mcp-usage endpoint returning per-server + per-tool invocation counts
  - Migration 094: partial index on audit_log WHERE action='ai.mcp_tool_call'
  - 14 unit tests: 8 for hook extension, 6 for endpoint
affects:
  - Phase 34-02 (frontend MCP usage dashboard tab — reads from this endpoint)
  - Future phases using audit_log for compliance queries

# Tech tracking
tech-stack:
  added: []  # hashlib is stdlib, no new dependencies
  patterns:
    - "Remote MCP audit: detect mcp__remote_{uuid}__tool_name via split('__', 2); write action='ai.mcp_tool_call' to audit_log"
    - "Partial index on audit_log for fast action-filtered queries (postgresql_where constraint)"
    - "JSONB GROUP BY via func.json_extract_path_text() — SQLite+PostgreSQL portable"
    - "elif guard on is_remote_mcp to prevent double-write: MCP branch xor generic branch per callback invocation"

key-files:
  created:
    - backend/src/pilot_space/api/v1/routers/mcp_usage.py
    - backend/alembic/versions/094_add_mcp_audit_index.py
    - backend/tests/unit/ai/sdk/test_hooks_lifecycle_mcp.py
    - backend/tests/unit/routers/test_mcp_usage.py
  modified:
    - backend/src/pilot_space/ai/sdk/hooks_lifecycle.py
    - backend/src/pilot_space/api/v1/routers/ai.py
    - backend/src/pilot_space/api/v1/routers/__init__.py

key-decisions:
  - "Store server_key (not display_name) in audit_log payload at log time; resolve display_name at query time via WorkspaceMcpServer JOIN — avoids coupling hook to agent state and handles name changes correctly"
  - "Use elif guard (not separate if) for remote MCP vs generic audit path so only one DB write fires per PostToolUse callback invocation"
  - "Full 64-char SHA-256 hex digest for input_hash (not prefix) — audit requirement"
  - "Patch AuditLogRepository at the repository module path (not hooks_lifecycle) for test mocking, since the import is lazy (inside callback)"

requirements-completed: [MCPOB-01, MCPOB-02]

# Metrics
duration: 10min
completed: 2026-03-20
---

# Phase 34 Plan 01: MCP Observability — Audit Trail + Usage Endpoint Summary

**Remote MCP tool calls now produce immutable audit_log rows (action='ai.mcp_tool_call') and a new GET /api/v1/ai/mcp-usage endpoint returns per-server+per-tool invocation counts from those rows**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-19T21:27:54Z
- **Completed:** 2026-03-19T21:38:37Z
- **Tasks:** 4 (TDD: 2 RED + 2 GREEN/implementation)
- **Files modified:** 7

## Accomplishments
- Extended `AuditLogHook._create_audit_callback()` to detect `mcp__remote_{uuid}__*` tool names and write enriched `ai.mcp_tool_call` audit rows with server_key, bare_tool, SHA-256 input hash, and duration_ms
- New `GET /api/v1/ai/mcp-usage` endpoint with date range filtering, GROUP BY aggregation via portable `json_extract_path_text()`, and display_name resolution from `workspace_mcp_servers`
- Migration 094: partial index `ix_audit_log_mcp_tool_calls` on `(workspace_id, created_at) WHERE action='ai.mcp_tool_call'` for fast dashboard queries
- 14 unit tests: all GREEN; existing 742 unit tests unaffected

## Task Commits

1. **Task 1: Tests for MCPOB-01 audit hook extension (RED)** - `c2a5a7ca` (test)
2. **Task 2: Tests for MCPOB-02 mcp-usage endpoint (RED)** - `001c6e1e` (test)
3. **Task 3: Implement remote MCP audit detection (GREEN)** - `bf68f10d` (feat)
4. **Task 4: Create mcp_usage.py router + migration 094 (GREEN)** - `e072e29a` (feat)

## Files Created/Modified
- `backend/src/pilot_space/ai/sdk/hooks_lifecycle.py` - Added hashlib import; extended _create_audit_callback() with remote MCP detection branch and elif guard
- `backend/src/pilot_space/api/v1/routers/mcp_usage.py` - New GET /mcp-usage endpoint with Pydantic response models
- `backend/src/pilot_space/api/v1/routers/ai.py` - Register mcp_usage_router as sub-router
- `backend/src/pilot_space/api/v1/routers/__init__.py` - Export mcp_usage_router in __all__
- `backend/alembic/versions/094_add_mcp_audit_index.py` - Partial index migration
- `backend/tests/unit/ai/sdk/test_hooks_lifecycle_mcp.py` - 8 unit tests for MCPOB-01
- `backend/tests/unit/routers/test_mcp_usage.py` - 6 unit tests for MCPOB-02

## Decisions Made
- Store `server_key` (opaque "remote_{uuid}") in audit_log payload at log time; resolve `display_name` at query time via workspace_mcp_servers JOIN — avoids coupling AuditLogHook to agent state and handles server renames correctly
- Use `elif not is_remote_mcp` guard instead of two independent `if` blocks to prevent double DB writes in a single PostToolUse callback invocation
- Full 64-char SHA-256 hex for `input_hash` (plan specifies full digest, not prefix)
- Patch `AuditLogRepository` at the repository module path for unit tests since the callback uses a lazy local import

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test mock patch target**
- **Found during:** Task 1 (RED phase — test execution)
- **Issue:** Initial tests patched `pilot_space.ai.sdk.hooks_lifecycle.AuditLogRepository` which doesn't exist at module level (lazy import inside callback)
- **Fix:** Changed patch target to `pilot_space.infrastructure.database.repositories.audit_log_repository.AuditLogRepository` — the source module where the symbol lives
- **Files modified:** `backend/tests/unit/ai/sdk/test_hooks_lifecycle_mcp.py`
- **Verification:** All 8 hook tests pass
- **Committed in:** c2a5a7ca

**2. [Rule 1 - Bug] Fixed test_get_mcp_usage_requires_auth assertion**
- **Found during:** Task 4 (GREEN phase — first run)
- **Issue:** Set comprehension `{(r.path, list(r.methods))}` fails with `unhashable type: list`; route path shows as `/mcp-usage` not `""` when queried from router.routes directly
- **Fix:** Replaced with list comprehension checking for `"GET"` in route methods
- **Files modified:** `backend/tests/unit/routers/test_mcp_usage.py`
- **Verification:** All 6 endpoint tests pass
- **Committed in:** e072e29a

**3. [Rule 1 - Bug] Fixed ruff I001 import sort issues**
- **Found during:** Task 3 and Task 4 (pre-commit hook)
- **Issue:** `import uuid as _uuid` inside if-block preceded std-lib imports; migration import block unsorted
- **Fix:** Reordered imports; `ruff check --fix` applied; replaced `try/except/pass` with `contextlib.suppress`
- **Files modified:** `hooks_lifecycle.py`, `mcp_usage.py`, `094_add_mcp_audit_index.py`
- **Verification:** `ruff check` passes with no errors
- **Committed in:** bf68f10d, e072e29a

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs)
**Impact on plan:** Minor test infrastructure fixes and code style corrections. No scope creep, no behavioral changes.

## Issues Encountered
None — all issues were auto-fixed via deviation rules.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- MCPOB-01 and MCPOB-02 backend requirements fully implemented
- `GET /api/v1/ai/mcp-usage` is reachable (visible in FastAPI /docs)
- Phase 34-02 (frontend MCP usage dashboard tab) can proceed immediately — endpoint response shape matches the `McpToolUsageResponse` types in 34-02-PLAN.md

---
*Phase: 34-mcp-observability*
*Completed: 2026-03-20*
