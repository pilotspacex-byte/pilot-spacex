---
phase: 17
slug: skill-action-buttons
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + Vitest (frontend) |
| **Config file** | backend/pyproject.toml + frontend/vitest.config.ts |
| **Quick run command** | `cd backend && uv run pytest tests/unit/routers/test_workspace_action_buttons.py -x` / `cd frontend && pnpm test -- --run src/features/settings/components/__tests__/action-buttons-tab-content.test.tsx` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command for affected layer (backend or frontend)
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | SKBTN-01 | unit | `cd backend && uv run pytest tests/unit/routers/test_workspace_action_buttons.py -x` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | SKBTN-02 | unit | `cd backend && uv run pytest tests/unit/schemas/test_skill_action_button_schemas.py -x` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | SKBTN-01 | unit | `cd frontend && pnpm test -- --run src/features/settings/components/__tests__/action-buttons-tab-content.test.tsx` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 2 | SKBTN-03 | unit | `cd frontend && pnpm test -- --run src/features/issues/components/__tests__/action-button-bar.test.tsx` | ❌ W0 | ⬜ pending |
| 17-03-02 | 03 | 2 | SKBTN-03 | unit | `cd frontend && pnpm test -- --run src/features/issues/components/__tests__/action-button-bar.test.tsx` | ❌ W0 | ⬜ pending |
| 17-04-01 | 04 | 2 | SKBTN-04 | manual | Requires live agent + approval config | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/unit/routers/test_workspace_action_buttons.py` — stubs for SKBTN-01, SKBTN-02
- [ ] `backend/tests/unit/schemas/test_skill_action_button_schemas.py` — stubs for SKBTN-02
- [ ] `frontend/src/services/api/__tests__/skill-action-buttons.test.ts` — stubs for API client
- [ ] `frontend/src/features/settings/components/__tests__/action-buttons-tab-content.test.tsx` — stubs for SKBTN-01
- [ ] `frontend/src/features/issues/components/__tests__/action-button-bar.test.tsx` — stubs for SKBTN-03

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Approval gate fires for destructive actions | SKBTN-04 | Requires live PilotSpaceAgent + approval policy + destructive tool invocation | 1. Create button bound to destructive MCP tool 2. Click button on issue page 3. Verify approval dialog appears before execution |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
