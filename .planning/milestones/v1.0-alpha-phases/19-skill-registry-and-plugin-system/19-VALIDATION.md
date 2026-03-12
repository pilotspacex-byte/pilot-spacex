---
phase: 19
slug: skill-registry-and-plugin-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend), vitest (frontend) |
| **Config file** | `backend/pyproject.toml`, `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/unit/ -x -q` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit/ -x -q`
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | SKRG-01 | unit | `cd backend && uv run pytest tests/unit/api/test_workspace_plugins_router.py -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | SKRG-02 | unit | `cd backend && uv run pytest tests/unit/services/test_install_plugin_service.py -x` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | SKRG-03 | unit | `cd backend && uv run pytest tests/unit/agents/test_plugin_skill_materializer.py -x` | ❌ W0 | ⬜ pending |
| 19-01-04 | 01 | 1 | SKRG-04 | unit | `cd backend && uv run pytest tests/unit/api/test_workspace_plugins_router.py::test_update_check -x` | ❌ W0 | ⬜ pending |
| 19-01-05 | 01 | 1 | SKRG-05 | unit | `cd backend && uv run pytest tests/unit/services/test_seed_plugins_service.py -x` | ❌ W0 | ⬜ pending |
| 19-02-01 | 02 | 2 | SKRG-01 | unit | `cd frontend && pnpm test stores/ai/PluginsStore.test.ts` | ❌ W0 | ⬜ pending |
| 19-02-02 | 02 | 2 | SKRG-04 | unit | `cd frontend && pnpm test features/settings/components/plugin-card.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/unit/api/test_workspace_plugins_router.py` — stubs for SKRG-01, SKRG-04
- [ ] `backend/tests/unit/services/test_install_plugin_service.py` — stubs for SKRG-02
- [ ] `backend/tests/unit/agents/test_plugin_skill_materializer.py` — stubs for SKRG-03
- [ ] `backend/tests/unit/services/test_seed_plugins_service.py` — stubs for SKRG-05
- [ ] `frontend/src/stores/ai/__tests__/PluginsStore.test.ts` — stubs for SKRG-01 frontend
- [ ] `frontend/src/features/settings/components/__tests__/plugin-card.test.tsx` — stubs for SKRG-04 frontend

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Plugin install wires MCP tools + action buttons after admin confirmation | SKRG-02 | Requires Phase 17 (action buttons) + Phase 14 (MCP) integration — multi-system | Install plugin with MCP bindings, verify MCP tool appears in workspace MCP list and action button appears in workspace buttons |
| "Update available" badge shown in sidebar nav | SKRG-03 | CSS/visual badge rendering requires browser | Open Settings → Plugins after an update is available, verify orange badge on sidebar nav item |
| New workspace seeded at creation | SKRG-05 | Requires full onboarding flow | Create new workspace, verify default plugins auto-installed in Settings → Plugins |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
