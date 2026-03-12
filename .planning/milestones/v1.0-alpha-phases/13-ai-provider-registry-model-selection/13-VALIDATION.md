---
phase: 13
slug: ai-provider-registry-model-selection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend), Vitest + React Testing Library (frontend) |
| **Config file** | `backend/pyproject.toml`, `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/unit/ai/ tests/unit/routers/test_ai_configuration.py -x -q` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~30 seconds (quick), ~90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit/ai/ tests/unit/routers/test_ai_configuration.py -x -q`
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 0 | AIPR-01 | unit | `cd backend && uv run pytest tests/unit/routers/test_ai_configuration.py -x -q` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 0 | AIPR-02 | unit | `cd backend && uv run pytest tests/unit/routers/test_ai_configuration.py::test_create_custom_provider -x` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 0 | AIPR-05 | unit | `cd backend && uv run pytest tests/unit/routers/test_ai_configuration.py::test_provider_status -x` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 0 | AIPR-03 | unit | `cd backend && uv run pytest tests/unit/ai/test_model_listing.py -x` | ❌ W0 | ⬜ pending |
| 13-01-05 | 01 | 0 | AIPR-04 | unit | `cd backend && uv run pytest tests/unit/ai/test_pilotspace_agent_model_override.py -x` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 0 | CHAT-01 | unit | `cd frontend && pnpm test src/features/ai/ChatView/__tests__/ModelSelector.test.tsx` | ❌ W0 | ⬜ pending |
| 13-02-02 | 02 | 0 | CHAT-02 | unit | `cd frontend && pnpm test src/stores/ai/__tests__/PilotSpaceStore.model.test.ts` | ❌ W0 | ⬜ pending |
| 13-02-03 | 02 | 0 | CHAT-03 | unit | `cd frontend && pnpm test src/features/ai/ChatView/__tests__/ModelSelector.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/unit/routers/test_ai_configuration.py` — stubs for AIPR-01, AIPR-02, AIPR-05
- [ ] `backend/tests/unit/ai/test_model_listing.py` — stubs for AIPR-03
- [ ] `backend/tests/unit/ai/test_pilotspace_agent_model_override.py` — stubs for AIPR-04
- [ ] `frontend/src/features/ai/ChatView/__tests__/ModelSelector.test.tsx` — stubs for CHAT-01, CHAT-03
- [ ] `frontend/src/stores/ai/__tests__/PilotSpaceStore.model.test.ts` — stubs for CHAT-02

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Provider status reflects live API key validity (connected/invalid/unreachable) | AIPR-01 | Requires real provider API calls | 1. Add valid Anthropic key → verify "connected"; 2. Add invalid key → verify "invalid key"; 3. Use unreachable base_url → verify "unreachable" |
| Custom provider appears alongside built-in providers in model selector | AIPR-02 | Requires full UI integration | 1. Register custom provider; 2. Open model selector in chat → verify it appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
