---
phase: 1
slug: identity-and-access
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend) |
| **Config file** | `backend/pyproject.toml`, `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/ -q -x` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -q -x`
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | AUTH-01 | unit | `cd backend && uv run pytest tests/unit/services/test_sso_service.py tests/unit/services/test_rbac_service.py tests/unit/services/test_session_service.py -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | AUTH-01 | unit | `cd backend && uv run pytest tests/unit/services/test_sso_service.py -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/unit/services/test_sso_service.py tests/unit/routers/test_auth_sso.py -q` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/unit/routers/test_auth_sso.py -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | AUTH-02 | unit | `cd backend && uv run pytest tests/unit/routers/test_auth_sso.py -q` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | AUTH-05 | unit | `cd backend && uv run pytest tests/unit/services/test_session_service.py -q` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 3 | AUTH-02 | unit | `cd backend && uv run pytest tests/unit/services/test_sso_service.py tests/unit/routers/test_auth_sso.py -q` | ❌ W0 | ⬜ pending |
| 1-06-01 | 06 | 2 | AUTH-07 | unit | `cd backend && uv run pytest tests/unit/routers/test_scim.py -q` | ❌ W0 | ⬜ pending |
| 1-07-01 | 07 | 3 | AUTH-01 | frontend | `cd frontend && pnpm test -- --run src/features/settings/pages/__tests__/sso-settings-page.test.tsx` | ❌ W0 | ⬜ pending |
| 1-07-02 | 07 | 3 | AUTH-05 | frontend | `cd frontend && pnpm test -- --run src/features/settings/pages/__tests__/roles-settings-page.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/services/test_sso_service.py` — stubs for AUTH-01 (SSO provider CRUD + sso_status)
- [ ] `tests/unit/services/test_rbac_service.py` — stubs for AUTH-05 (custom role CRUD)
- [ ] `tests/unit/services/test_session_service.py` — stubs for AUTH-05 (session list + force-terminate)
- [ ] `tests/unit/routers/test_auth_sso.py` — stubs for AUTH-01/02/04 (SAML flow + /sso/status)
- [ ] `tests/unit/routers/test_scim.py` — stubs for AUTH-07 (SCIM provisioning/deprovisioning)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Actual SSO login flow via Okta/Azure AD/Google | AUTH-01 | Requires live IdP credentials + browser | Configure test IdP in dev env, attempt login, verify JWT contains workspace role |
| SSO-only mode blocks email/password login in browser | AUTH-02 | UI login flow requires browser interaction | Enable SSO-only, attempt email/password login, verify blocked with correct error message |
| SCIM provisioner sync (Okta/Azure AD SCIM client) | AUTH-07 | Requires live SCIM client from IdP | Configure Okta SCIM app, provision user, verify workspace membership created |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
