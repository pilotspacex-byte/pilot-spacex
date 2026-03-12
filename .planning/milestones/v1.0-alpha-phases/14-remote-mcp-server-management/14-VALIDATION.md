---
phase: 14
slug: remote-mcp-server-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend); Vitest (frontend) |
| **Config file** | `backend/pyproject.toml` (pytest), `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -q` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -q`
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | MCP-01..06 | unit | `cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 0 | MCP-04 | unit | `cd backend && uv run pytest tests/ai/agents/test_remote_mcp_loading.py -q` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 0 | MCPStore | unit | `cd frontend && pnpm test src/stores/ai/__tests__/MCPServersStore.test.ts` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 1 | MCP-01 | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_register_server -x` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 1 | MCP-02 | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_token_encrypted_at_rest -x` | ❌ W0 | ⬜ pending |
| 14-02-03 | 02 | 1 | MCP-03 | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_oauth_callback_stores_token -x` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 2 | MCP-04 | unit | `uv run pytest tests/ai/agents/test_remote_mcp_loading.py -x` | ❌ W0 | ⬜ pending |
| 14-04-01 | 04 | 2 | MCP-05 | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_status_endpoint -x` | ❌ W0 | ⬜ pending |
| 14-04-02 | 04 | 2 | MCP-06 | unit | `uv run pytest tests/api/test_workspace_mcp_servers.py::test_delete_removes_from_agent -x` | ❌ W0 | ⬜ pending |
| 14-05-01 | 05 | 3 | MCPStore | unit | `cd frontend && pnpm test src/stores/ai/__tests__/MCPServersStore.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/api/test_workspace_mcp_servers.py` — stubs for MCP-01 through MCP-06
- [ ] `backend/tests/ai/agents/test_remote_mcp_loading.py` — stubs for MCP-04 agent injection
- [ ] `frontend/src/stores/ai/__tests__/MCPServersStore.test.ts` — stubs for frontend store

*Existing test infrastructure (pytest-asyncio, conftest fixtures, Vitest) covers all tooling needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OAuth 2.0 redirect flow end-to-end | MCP-03 | Requires real OAuth provider callback with browser redirect | 1. Register MCP server with OAuth auth type; 2. Click "Authorize" button; 3. Complete OAuth flow in browser; 4. Verify token stored and status shows "connected" |
| Connection status badge reflects live server reachability | MCP-05 | Requires a live remote MCP server endpoint | 1. Register server with valid URL; 2. Verify badge shows "connected"; 3. Stop server; 4. Refresh page and verify badge shows "failed" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
