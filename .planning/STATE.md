---
gsd_state_version: 1.0
milestone: v1.1.0
milestone_name: MCP Platform Hardening
status: executing
stopped_at: Completed 32-03-PLAN.md (token_expires_at schema field + ExpiryBadge frontend component)
last_updated: "2026-03-20T02:23:02Z"
last_activity: 2026-03-20 — Phase 32 plan 03 executed (MCPO-03)
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 8
  completed_plans: 5
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control.
**Current focus:** Phase 32 — OAuth Refresh Flow (planned, ready to execute)

## Current Position

Phase: 32 of 35 (OAuth Refresh Flow)
Plan: 03 complete (32-03)
Status: Executing — Wave 2 plans complete (32-02, 32-03)
Last activity: 2026-03-20 — Phase 32 plan 03 executed (token_expires_at schema field + ExpiryBadge frontend UI)

Progress: [░░░░░░░░░░] 0% (0/6 phases complete, 4/8 plans complete across v1.1.0)

## Wave Structure for Phase 32

| Wave | Plans | Parallelizable | Dependencies |
|------|-------|----------------|--------------|
| 1 | 32-01 (DB migration + model + OAuth callback storage) | Solo | None |
| 2 | 32-02 (auto-refresh logic), 32-03 (frontend expiry badge + schema) | Yes | Both depend on 32-01 model columns |

Execute order: Run 32-01 first (wave 1), then 32-02 and 32-03 in parallel (wave 2).

Note: 32-02 and 32-03 are independent at the file level — 32-02 touches only backend router + stream utils, 32-03 touches only backend schema + frontend. They can run in parallel after 32-01 lands.

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

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-20T02:23:02Z
Stopped at: Completed 32-03-PLAN.md (token_expires_at schema field + ExpiryBadge frontend component)
Resume file: None
Next action: /gsd:execute-phase 32 (remaining plans in phase 32, if any)
