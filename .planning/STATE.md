---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 33-03-PLAN.md
last_updated: "2026-03-19T21:13:34.802Z"
last_activity: 2026-03-19 — 33-01 executed (migration 093 + ORM + PATCH endpoint + ActionType.REMOTE_MCP_TOOL)
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 11
  completed_plans: 9
  percent: 9
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control.
**Current focus:** Phase 33 — Remote MCP Approval Framework (planned, ready to execute)

## Current Position

Phase: 33 of 35 (Remote MCP Approval Framework)
Plan: 01 (33-01 complete — migration 093, ORM McpApprovalMode, PATCH endpoint, ActionType.REMOTE_MCP_TOOL)
Status: In Progress — wave 1 complete, waves 2 (33-02 + 33-03) ready to run in parallel
Last activity: 2026-03-19 — 33-01 executed (migration 093 + ORM + PATCH endpoint + ActionType.REMOTE_MCP_TOOL)

Progress: [░░░░░░░░░░] 9% (1/6 phases complete in v1.1.0, 7/11 plans complete)

## Wave Structure for Phase 33

| Wave | Plans | Parallelizable | Dependencies |
|------|-------|----------------|--------------|
| 1 | 33-01 (DB migration + ORM + PATCH endpoint + ActionType) | Solo | None |
| 2 | 33-02 (backend approval wiring), 33-03 (frontend toggle) | Yes | Both depend on 33-01 ORM model |

Execute order: Run 33-01 first (wave 1), then 33-02 and 33-03 in parallel (wave 2).

Note: 33-02 and 33-03 are independent at the file level — 33-02 touches only backend AI SDK + agent, 33-03 touches only frontend stores/components. They can run in parallel after 33-01 lands.

## Milestone History

| Milestone | Phases | Plans | Requirements | Shipped |
|-----------|--------|-------|-------------|---------|
| v1.0 Enterprise | 1–11 | 46 | 30/30 | 2026-03-09 |
| v1.0-alpha Pre-Production Launch | 12–23 | 37 | 39/39 + 7 gap items | 2026-03-12 |
| v1.0.0-alpha2 Notion-Style Restructure | 24–29 | 14 | 17/17 | 2026-03-12 |
| v1.1.0 MCP Platform Hardening | 30–35 | TBD | 0/19 | In progress |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
- [Phase quick-04]: Skip SQLite-incompatible execute tests with @pytest.mark.skip and TEST_DATABASE_URL hint
- [Phase quick-04]: Remove sys.modules module-level mocks that leak across test session
- [quick-260317-bch]: pilotspace_agent.py excluded from pre-commit 700-line check (orchestrator file)
- [quick-260317-hms]: WorkspaceLLMConfig is frozen dataclass in provider_selector.py (colocation avoids circular imports)
- [Phase 31]: _validate_mcp_url extracted to infrastructure/ssrf.py to avoid AI-layer → API-layer circular import
- [31-04]: Enforcement check in lifespan mirrors jwt_provider_validated pattern; non-production bypassed to preserve dev key fallback behavior
- [31-04]: Tests use extracted helper function matching lifespan logic, patching pilot_space.config.get_settings for get_encryption_service() override
- [Phase 31]: MCP_SERVER_CAP = 10 at module level makes constant importable by tests; cap check placed before WorkspaceMcpServer construction
- [31-02]: Import alias `from ssrf import validate_mcp_url as _validate_mcp_url` means zero changes to existing field_validator call sites
- [31-02]: cast("McpServerConfig", {...}) used for TypedDict union assignment — ruff TC006 requires quoted type arg
- [Phase 32]: _refresh_oauth_token placed in workspace_mcp_servers.py (alongside _exchange_oauth_code) and lazy-imported in stream utils to avoid circular deps
- [Phase 32]: token_expires_at uses naive-datetime guard (replace(tzinfo=UTC)) in _load_remote_mcp_servers for SQLite test compatibility
- [Phase 32]: refresh_token_encrypted is never echoed in WorkspaceMcpServerResponse — only token_expires_at is exposed to the frontend
- [32-01]: encrypt_api_key moved to module-level import in workspace_mcp_servers.py so tests can patch workspace_mcp_servers.encrypt_api_key directly
- [32-01]: _exchange_oauth_code returns None (not partial tuple) when access_token absent — preserves None sentinel for the error redirect path
- [32-03]: ExpiryBadge co-located in mcp-server-card.tsx (not a separate file) — follows existing AuthTypeBadge/StatusBadge pattern in same file
- [32-03]: Backend token_expires_at was already present from 32-01; Task 1 became verification-only
- [Phase 32]: _refresh_oauth_token extracted to _mcp_server_oauth_helpers.py — workspace_mcp_servers.py hit 690-line threshold
- [Phase 32]: Lazy import of _refresh_oauth_token inside _load_remote_mcp_servers avoids circular imports
- [33-01]: VARCHAR(16) + CHECK constraint used for approval_mode instead of DB enum — avoids Alembic enum migration complexity
- [33-01]: logger.info removed from PATCH /approval-mode handler to stay within 700-line pre-commit limit
- [33-01]: McpApprovalMode StrEnum placed in ORM model file (not approval.py) to keep column-level enums co-located with their model
- [Phase 33]: workspace_mcp_servers.py is at ~670 lines — PATCH /approval-mode endpoint must stay lean or extract to helper; check line count before writing
- [Phase 33]: can_use_tool callback uses lazy imports inside _handle_remote_mcp_approval to avoid circular imports (same pattern as existing lazy imports in question_adapter.py)
- [Phase 33]: MCPServerCard is NOT an observer — approval mode toggle uses onUpdateApprovalMode prop pattern, parent mcp-servers-settings-page.tsx (observer) owns the store call
- [Phase 33]: Server key format for approval map uses UUID from _load_remote_mcp_servers (remote_{id}), not display_name normalization
- [Phase 33]: approval_mode optional on MCPServer for backwards compat; Switch in server info column not actions column; MCPA-03 uses InlineApprovalCard GenericJSON fallback (no new component)

### Pending Todos

None.

### Blockers/Concerns

- MEDIUM confidence: `can_use_tool` SDK callback may not fire for native MCP tool calls. RESEARCH.md flags this as the key integration risk (Pitfall 2). Plan 33-02 Task 1 includes unit tests that mock the callback path, but a live integration test post-execution is recommended before shipping.

## Session Continuity

Last session: 2026-03-19T21:13:30.657Z
Stopped at: Completed 33-03-PLAN.md
Resume file: None
Next action: /gsd:execute-phase 33 (plans 33-02 + 33-03 in parallel)
