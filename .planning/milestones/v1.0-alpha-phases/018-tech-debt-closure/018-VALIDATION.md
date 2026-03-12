---
phase: 18
slug: tech-debt-closure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio (backend), Playwright 1.58.0 (E2E) |
| **Config file** | `backend/pyproject.toml`, `frontend/playwright.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/audit/ tests/unit/test_workspace_encryption.py -x -q` |
| **Full suite command** | `cd backend && uv run pytest --cov -q` |
| **Estimated runtime** | ~30 seconds (quick), ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/audit/ tests/unit/test_workspace_encryption.py -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest --cov -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | DEBT-01 | E2E (Playwright) | `cd frontend && pnpm test:e2e --grep "oidc"` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 1 | DEBT-02 | unit | `cd backend && uv run pytest tests/ -k "note_content" -x` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 1 | DEBT-02 | unit | `cd backend && uv run pytest tests/ -k "issue_relation" -x` | ❌ W0 | ⬜ pending |
| 18-03-01 | 03 | 1 | DEBT-03 | integration | `cd backend && uv run pytest tests/audit/test_audit_api.py tests/audit/test_audit_export.py -x` | ✅ (xfail) | ⬜ pending |
| 18-03-02 | 03 | 1 | DEBT-03 | integration | `cd backend && uv run pytest tests/audit/test_immutability.py -x` | ✅ (xfail) | ⬜ pending |
| 18-04-01 | 04 | 1 | DEBT-04 | unit | `cd backend && uv run pytest tests/unit/test_workspace_encryption.py -x` | ✅ (xfail) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/e2e/oidc-login.spec.ts` — stubs for DEBT-01 OIDC E2E flow
- [ ] `backend/tests/unit/ai/test_note_content_server_approval.py` — stubs for DEBT-02 note_content_server wiring
- [ ] `backend/tests/unit/ai/test_issue_relation_server_approval.py` — stubs for DEBT-02 issue_relation_server wiring
- [ ] Audit conftest `AsyncClient` fixture with auth headers — covers DEBT-03

*Existing infrastructure covers DEBT-04 (test file exists, currently xfail).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real OIDC provider login (Okta/Azure AD/Google) | DEBT-01 | Requires real IdP tenant credentials | 1. Configure provider in SSO settings 2. Initiate SSO login 3. Complete IdP auth 4. Verify authenticated session |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
