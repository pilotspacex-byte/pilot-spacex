---
phase: 23
slug: tech-debt-sweep
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend), Vitest + RTL (frontend) |
| **Config file** | `backend/pyproject.toml`, `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/unit/routers/test_ai_configuration.py tests/api/test_related_issues.py -x -q` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run relevant test file(s) for the changed module
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| AIPR-05-a | 01 | 1 | AIPR-05 | unit | `cd backend && uv run pytest tests/unit/routers/test_ai_configuration.py -x -q` | ✅ (extend) | ⬜ pending |
| AIPR-05-b | 02 | 1 | AIPR-05 | unit | `cd frontend && pnpm test -- --run src/features/settings/pages/__tests__/ai-settings-page.test.tsx` | ✅ (extend) | ⬜ pending |
| CQ-01 | 01 | 1 | code quality | manual | `test ! -f backend/src/pilot_space/api/v1/schemas/mcp_server.py` | N/A | ⬜ pending |
| CQ-02 | 01 | 1 | code quality | unit | `cd backend && uv run pytest tests/api/test_related_issues.py -x -q` | ✅ | ⬜ pending |
| CQ-03 | 01 | 1 | code quality | unit | `cd backend && uv run pytest tests/api/test_related_issues.py -x -q` | ✅ (verify) | ⬜ pending |
| CQ-04 | 02 | 1 | code quality | unit | `cd frontend && pnpm test -- --run src/features/settings/components/__tests__/plugin-card.test.tsx` | ✅ (update) | ⬜ pending |
| CQ-05 | 01 | 1 | code quality | manual | `wc -l backend/src/pilot_space/api/v1/routers/ai_chat.py` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dead file removed | CQ-01 | File deletion, no unit test needed | `test ! -f backend/src/pilot_space/api/v1/schemas/mcp_server.py` |
| ai_chat.py < 700 lines | CQ-05 | Line count check | `wc -l backend/src/pilot_space/api/v1/routers/ai_chat.py` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
