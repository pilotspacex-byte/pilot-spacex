---
phase: 22
slug: integration-safety-session-oauth2
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio (backend), vitest (frontend) |
| **Config file** | `backend/pyproject.toml`, `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py tests/api/test_workspace_mcp_servers.py -x` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py tests/api/test_workspace_mcp_servers.py -x`
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | SKRG-05 | unit | `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py -x` | ✅ (needs new case) | ⬜ pending |
| 22-01-02 | 01 | 1 | SKRG-05 | unit | `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py -x` | ❌ W0 | ⬜ pending |
| 22-02-01 | 02 | 1 | MCP-03 | unit | `cd frontend && pnpm test -- --run mcp-server-card` | ❌ W0 | ⬜ pending |
| 22-02-02 | 02 | 1 | MCP-03 | unit | `cd frontend && pnpm test -- --run mcp-servers-settings` | ❌ W0 | ⬜ pending |
| 22-02-03 | 02 | 1 | MCP-03 | unit | `cd backend && uv run pytest tests/api/test_workspace_mcp_servers.py -x -k oauth` | ✅ (xfail stub) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New test case in `backend/tests/unit/services/test_seed_plugins_service.py` — verify independent session usage (SKRG-05)
- [ ] New test case for non-fatal exception handling in background seed task (SKRG-05)
- [ ] `frontend/src/features/settings/components/__tests__/mcp-server-card.test.tsx` — Authorize button renders for OAuth2 servers (MCP-03)
- [ ] `frontend/src/features/settings/pages/__tests__/mcp-servers-settings-page.test.tsx` — OAuth status toast handling (MCP-03)
- [ ] Update `backend/tests/api/test_workspace_mcp_servers.py` xfail stubs — OAuth callback with workspace slug (MCP-03)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OAuth2 redirect to provider and back | MCP-03 | Requires real OAuth provider and browser redirect | 1. Add OAuth2 MCP server config, 2. Click Authorize, 3. Verify redirect to provider, 4. Complete auth, 5. Verify redirect back with success toast |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
