---
phase: 6
slug: wire-rate-limiting-scim-token
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run pytest tests/security/test_rate_limiting.py tests/unit/routers/test_scim.py -q` |
| **Full suite command** | `cd backend && uv run pytest --cov` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/security/test_rate_limiting.py tests/unit/routers/test_scim.py -q`
- **After every plan wave:** Run `cd backend && uv run pytest --cov`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | TENANT-03 | unit | `cd backend && uv run pytest tests/security/test_rate_limiting.py -q` | ✅ | ⬜ pending |
| 6-01-02 | 01 | 1 | AUTH-07 | unit | `cd backend && uv run pytest tests/unit/routers/test_scim.py -q` | ✅ | ⬜ pending |
| 6-01-03 | 01 | 2 | TENANT-03 | unit | `cd backend && uv run pytest tests/security/test_rate_limiting.py -k "test_rate_limit_429" -q` | ❌ W0 | ⬜ pending |
| 6-01-04 | 01 | 2 | AUTH-07 | unit | `cd backend && uv run pytest tests/unit/routers/test_scim.py -k "test_scim_token_endpoint_calls_service" -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/security/test_rate_limiting.py` — add `test_rate_limit_middleware_registered_returns_429` stub for TENANT-03 wiring (includes middleware stack assertion)
- [ ] `tests/unit/routers/test_scim.py` — add `test_scim_token_endpoint_calls_service` stub for AUTH-07

*Existing infrastructure (pytest, mock_redis, conftest.py) covers all framework requirements.*

---

## Manual-Only Verifications

None. The middleware stack presence check is now covered by the automated `test_rate_limit_middleware_registered_returns_429` test, which asserts `RateLimitMiddleware` is found in the Starlette middleware stack before issuing the request.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
