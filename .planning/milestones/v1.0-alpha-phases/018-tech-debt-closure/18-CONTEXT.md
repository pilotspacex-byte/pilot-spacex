# Phase 18: Tech Debt Closure - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve 4 known v1.0 gaps: OIDC login flow E2E verification, MCP approval wiring correctness, xfail audit test fixes, and key rotation re-encryption implementation. All are backend/infrastructure — no new user-facing features.

</domain>

<decisions>
## Implementation Decisions

### OIDC Verification (DEBT-01)
- Verify all 3 providers: Okta, Azure AD, Google Workspace — success criteria requires all
- Playwright E2E test using mock IdP (`oidc-server-mock` or similar) for CI regression
- Manual verification checklist for real provider test tenants (one-time pre-release)
- Test should cover full flow: SSO settings page → initiate login → IdP redirect → callback → authenticated session

### MCP Approval Wiring (DEBT-02)
- Audit ALL MCP servers for `check_approval_from_db()` usage, not just the two named
- Known gap: `note_content_server.py` uses static `get_tool_approval_level()` — must swap to `check_approval_from_db()` for every tool execution
- `issue_server.py`, `comment_server.py`, `project_server.py` already use the correct pattern — verify only
- `issue_relation_server` tools are within `issue_server.py` — already correct, confirm and document
- Every tool must receive `ToolContext` with `user_role` for DB-based approval lookup

### Audit Test Fixes (DEBT-03)
- Fix ALL xfail audit tests (17+ across `test_audit_api.py`, `test_audit_export.py`, `test_immutability.py`), not just the "2" mentioned
- Root cause: missing async HTTP client fixture that can call audit API endpoints
- Create proper `AsyncClient` (httpx) fixture with auth headers and workspace context
- Remove `xfail` markers once tests pass — no `strict=False` remnants

### Key Rotation (DEBT-04)
- Online rotation — service stays up, no maintenance window required
- Dual-key read during transition: decrypt tries new key first, falls back to old key
- Batch re-encryption per workspace with progress tracking
- Atomic per-workspace: failure on one workspace doesn't block others; retry mechanism for failed
- Old key retained in DB until all content confirmed re-encrypted, then marked inactive
- Rotation endpoint restricted to workspace owner (not admin)

### Claude's Discretion
- Mock IdP library choice for Playwright tests
- Batch size for key rotation re-encryption
- Exact async client fixture implementation pattern
- Whether to add a rotation progress API endpoint or keep it backend-only

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `check_approval_from_db()` in `ai/tools/mcp_server.py:153` — the correct approval pattern, already used by 3 MCP servers
- `workspace_encryption.py` — encrypt/decrypt functions exist, needs rotation logic added
- `workspace_encryption_repository.py` — key storage and retrieval
- `workspace_encryption_key` model — has key versioning support
- `auth_sso.py` + `sso_service.py` — SSO backend endpoints exist
- `use-sso-login.ts` + `sso-settings-page.tsx` — SSO frontend exists
- `test_mcp_server_approval.py` — comprehensive test suite for approval patterns to follow

### Established Patterns
- MCP servers: `check_approval_from_db(tool_name, action_type, ctx)` for every tool execution
- Test fixtures: `db_session` for unit tests, `db_session_committed` for integration
- xfail stubs: `pytest.mark.xfail(strict=False)` with `pytest.fail()` body — to be replaced with real implementations
- Service pattern: Direct instantiation (not DI) for lightweight per-request services (SCIM, related-issues pattern)

### Integration Points
- `note_content_server.py` line 59: `_chk = check_approval_from_db` is imported but only used as reference — actual tools call `get_tool_approval_level()`
- `note_content_server.py` imports from `mcp_server.py`: needs `ToolContext` and `check_approval_from_db`
- `workspace_encryption.py` connects to `workspace_encryption_repository.py` for key CRUD
- Audit router at `api/v1/routers/` — tests need httpx `AsyncClient` wired to the FastAPI app

</code_context>

<specifics>
## Specific Ideas

- note_content_server.py already imports check_approval_from_db (line 19) and assigns `_chk = check_approval_from_db` (line 59) but doesn't actually call it in tool handlers — the static `get_tool_approval_level()` is used instead. The fix should use the existing import.
- Key rotation test at `test_workspace_encryption.py:107` describes the exact expected behavior: encrypt with v1, rotate to v2, decrypt with v2 succeeds, decrypt with v1 fails.
- All audit xfail tests follow the same pattern: they try to call API endpoints but lack a proper async HTTP client fixture.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 018-tech-debt-closure*
*Context gathered: 2026-03-11*
