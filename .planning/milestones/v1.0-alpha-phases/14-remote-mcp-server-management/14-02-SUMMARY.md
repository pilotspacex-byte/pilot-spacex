---
phase: 14-remote-mcp-server-management
plan: 02
subsystem: database
tags: [sqlalchemy, alembic, pydantic, rls, fernet-encryption, mcp, postgresql]

# Dependency graph
requires:
  - phase: 14-01
    provides: Wave 0 xfail test stubs driving green implementation

provides:
  - "Alembic migration 071: workspace_mcp_servers table + mcp_auth_type enum + RLS policies"
  - "WorkspaceMcpServer SQLAlchemy model with encrypted token field"
  - "WorkspaceMcpServerRepository: get_active_by_workspace, get_by_workspace_and_id, create, update, soft_delete"
  - "Pydantic schemas: WorkspaceMcpServerCreate, WorkspaceMcpServerResponse, WorkspaceMcpServerListResponse, McpServerStatusResponse, WorkspaceMcpServerUpdate"

affects: [14-03-crud-router, 14-04-agent-wiring, 18-tech-debt-closure]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "WorkspaceScopedModel inheritance for multi-tenant table isolation"
    - "StrEnum for PostgreSQL enum types with create_type=False (enum created in migration)"
    - "BaseRepository extension pattern with workspace-scoped query methods"
    - "Pydantic response schemas exclude encrypted fields by design (security)"

key-files:
  created:
    - backend/alembic/versions/071_add_workspace_mcp_servers.py
    - backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py
    - backend/src/pilot_space/infrastructure/database/repositories/workspace_mcp_server_repository.py
    - backend/src/pilot_space/api/v1/schemas/mcp_server.py

key-decisions:
  - "WorkspaceMcpServerRepository.get_by_workspace_and_id instead of overriding BaseRepository.get_by_id — avoids incompatible parameter signature (entity_id vs server_id) caught by pyright"
  - "create/update override BaseRepository with type: ignore[override] — parameter renamed to entity for type safety while keeping workspace-specific refresh semantics"
  - "WorkspaceMcpServerUpdate schema added (not in plan spec) — partial update shape required by Plan 03 PATCH endpoint; added proactively as Rule 2 missing critical"
  - "auth_token_encrypted column is String(1024) — Fernet base64 ciphertext of 32-byte key + nonce + MAC fits within 512 chars but 1024 gives headroom for larger tokens"

patterns-established:
  - "McpAuthType StrEnum: BEARER = 'bearer', OAUTH2 = 'oauth2' — string values match DB enum literals"
  - "Response schemas never include encrypted columns — WorkspaceMcpServerResponse omits auth_token_encrypted by design"
  - "Soft-delete lifecycle: is_deleted=False filter on all active queries; soft_delete() calls model.soft_delete() then session.flush()"

requirements-completed: [MCP-01, MCP-02, MCP-06]

# Metrics
duration: 18min
completed: 2026-03-10
---

# Phase 14 Plan 02: Remote MCP Server Management — DB Persistence Layer Summary

**workspace_mcp_servers PostgreSQL table with RLS isolation, Fernet-encrypted token storage, workspace-scoped repository, and full Pydantic CRUD schemas**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-03-10T09:20:00Z
- **Completed:** 2026-03-10T09:38:00Z
- **Tasks:** 2
- **Files modified:** 4 created

## Accomplishments

- Migration 071 creates `workspace_mcp_servers` table with `mcp_auth_type` enum, full RLS (workspace isolation + service_role bypass), and workspace_id index
- `WorkspaceMcpServer` SQLAlchemy model inherits `WorkspaceScopedModel`; carries encrypted token field and OAuth2 metadata columns
- `WorkspaceMcpServerRepository` provides all 5 CRUD methods Plans 03/04 need: `get_active_by_workspace`, `get_by_workspace_and_id`, `create`, `update`, `soft_delete`
- All Pydantic schemas cleanly typed (pyright 0 errors, ruff passed); xfail tests remain xfail

## Task Commits

1. **Task 1+2: Migration, model, repository, schemas** - `5b975379` (feat)

_Note: Task 1 files (migration + model) were partially staged from prior session; committed together with Task 2 files after all quality gates passed._

## Files Created/Modified

- `backend/alembic/versions/071_add_workspace_mcp_servers.py` - Migration creating mcp_auth_type enum, workspace_mcp_servers table, RLS policies, workspace_id index
- `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py` - WorkspaceMcpServer model with McpAuthType enum
- `backend/src/pilot_space/infrastructure/database/repositories/workspace_mcp_server_repository.py` - CRUD repository with workspace-scoped queries
- `backend/src/pilot_space/api/v1/schemas/mcp_server.py` - All request/response Pydantic schemas

## Decisions Made

- **`get_by_workspace_and_id` over `get_by_id` override** — pyright caught incompatible method override (parameter name `entity_id` vs `server_id`). Following AIConfigurationRepository pattern with explicit workspace-scoped method.
- **`WorkspaceMcpServerUpdate` schema added proactively** — Plan 03 PATCH endpoint will require it. Added as Rule 2 auto-fix (missing critical functionality for completeness).
- **`create` and `update` use `type: ignore[override]`** — These methods need to `self.session.add(entity)` before flush (different from base), so override is intentional and well-typed internally.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added WorkspaceMcpServerUpdate schema**
- **Found during:** Task 2 (Pydantic schemas creation)
- **Issue:** Plan spec listed 4 schemas but Plan 03 PATCH endpoint requires an update schema
- **Fix:** Added `WorkspaceMcpServerUpdate` with all optional fields for partial updates
- **Files modified:** backend/src/pilot_space/api/v1/schemas/mcp_server.py
- **Verification:** Import succeeds, pyright 0 errors
- **Committed in:** 5b975379

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Update schema required for Plan 03 PATCH endpoint; adding it here avoids a Plan 03 deviation.

## Issues Encountered

- Pre-commit hook (prek) conflicted with untracked files being stashed when staged files had `AM` (added + modified) status. Root cause: ruff import-ordering and line-length fixes applied by prior incomplete commit attempts. Fixed by running ruff manually on the working tree, re-staging, then committing with no unstaged changes.

## Next Phase Readiness

- Plan 03 (CRUD router) can import `WorkspaceMcpServerCreate`, `WorkspaceMcpServerResponse`, and `WorkspaceMcpServerRepository` directly
- Plan 04 (agent wiring) can import `WorkspaceMcpServer` model and `WorkspaceMcpServerRepository`
- `alembic upgrade head` will create the `workspace_mcp_servers` table with full RLS isolation

---
*Phase: 14-remote-mcp-server-management*
*Completed: 2026-03-10*
