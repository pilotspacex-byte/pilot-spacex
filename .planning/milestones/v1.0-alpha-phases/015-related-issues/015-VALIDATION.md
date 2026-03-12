---
phase: 15
slug: related-issues
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (async) + vitest (frontend) |
| **Config file** | `backend/pyproject.toml` + `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/api/test_related_issues.py -x -q` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~45 seconds (backend) + ~30 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/api/test_related_issues.py -x -q`
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | RELISS-01,02,03,04 | unit stub | `pytest tests/api/test_related_issues.py -x -q` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 0 | RELISS-01,04 | unit stub | `cd frontend && pnpm test -- related-issues-panel` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | RELISS-01,02,03,04 | unit | `pytest tests/api/test_related_issues.py -x -q` | ✅ W0 | ⬜ pending |
| 15-02-02 | 02 | 1 | RELISS-02 | unit | `pytest tests/api/test_related_issues.py::test_create_related_link -x` | ✅ W0 | ⬜ pending |
| 15-02-03 | 02 | 1 | RELISS-04 | unit | `pytest tests/api/test_related_issues.py::test_dismiss_suggestion -x` | ✅ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | RELISS-01 | unit | `cd frontend && pnpm test -- related-issues-panel` | ✅ W0 | ⬜ pending |
| 15-03-02 | 03 | 2 | RELISS-02 | unit | `cd frontend && pnpm test -- related-issues-panel` | ✅ W0 | ⬜ pending |
| 15-03-03 | 03 | 2 | RELISS-03,04 | unit | `cd frontend && pnpm test -- related-issues-panel` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/api/test_related_issues.py` — xfail stubs for RELISS-01, RELISS-02, RELISS-03, RELISS-04
- [ ] `frontend/src/features/issues/components/__tests__/related-issues-panel.test.tsx` — frontend stubs for RELISS-01, RELISS-04

*These test files do not exist yet; Wave 0 creates them.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Related panel visible on issue detail page | RELISS-01 | Browser rendering | Navigate to an issue, verify "Related Issues" panel appears |
| Manual link appears on both issues | RELISS-02 | Cross-issue state | Link A→B, open B, confirm A appears in its related panel |
| Dismissed suggestion never re-appears | RELISS-04 | Persistence across sessions | Dismiss suggestion, reload page, confirm it's gone |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
