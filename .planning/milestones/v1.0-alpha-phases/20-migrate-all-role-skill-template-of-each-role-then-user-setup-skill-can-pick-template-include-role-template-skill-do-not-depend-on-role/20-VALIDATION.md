---
phase: 20
slug: skill-template-catalog
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24+ (backend), vitest (frontend) |
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
| 20-01-01 | 01 | 1 | P20-01 | unit | `cd backend && uv run pytest tests/unit/repositories/test_skill_template_repository.py -x` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | P20-02 | unit | `cd backend && uv run pytest tests/unit/repositories/test_user_skill_repository.py -x` | ❌ W0 | ⬜ pending |
| 20-02-01 | 02 | 1 | P20-03 | unit | `cd backend && uv run pytest tests/unit/migrations/test_077_migration.py -x` | ❌ W0 | ⬜ pending |
| 20-03-01 | 03 | 2 | P20-04 | unit | `cd backend && uv run pytest tests/unit/ai/agents/test_role_skill_materializer.py -x` | ✅ update | ⬜ pending |
| 20-04-01 | 04 | 2 | P20-05 | unit | `cd backend && uv run pytest tests/unit/routers/test_skill_templates_router.py -x` | ❌ W0 | ⬜ pending |
| 20-04-02 | 04 | 2 | P20-06 | unit | `cd backend && uv run pytest tests/unit/routers/test_user_skills_router.py -x` | ❌ W0 | ⬜ pending |
| 20-05-01 | 05 | 3 | P20-07 | unit | `cd backend && uv run pytest tests/unit/services/test_seed_templates_service.py -x` | ❌ W0 | ⬜ pending |
| 20-05-02 | 05 | 3 | P20-08 | unit | `cd backend && uv run pytest tests/unit/services/test_create_user_skill_service.py -x` | ❌ W0 | ⬜ pending |
| 20-06-01 | 06 | 3 | P20-09 | unit | `cd frontend && pnpm vitest run src/features/settings --reporter=verbose` | ✅ update | ⬜ pending |
| 20-06-02 | 06 | 3 | P20-10 | unit | `cd frontend && pnpm vitest run src/services/api/user-skills.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/repositories/test_skill_template_repository.py` — stubs for P20-01
- [ ] `tests/unit/repositories/test_user_skill_repository.py` — stubs for P20-02
- [ ] `tests/unit/services/test_seed_templates_service.py` — stubs for P20-07
- [ ] `tests/unit/services/test_create_user_skill_service.py` — stubs for P20-08
- [ ] `tests/unit/routers/test_skill_templates_router.py` — stubs for P20-05
- [ ] `tests/unit/routers/test_user_skills_router.py` — stubs for P20-06
- [ ] `frontend/src/services/api/user-skills.test.ts` — stubs for P20-10

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Template catalog UI browsing | P20-09 | Visual layout, card interactions | Navigate to Settings → Skills, verify template cards display with source badges, "Use This" buttons work |
| AI skill personalization flow | P20-08 | Requires AI provider | Pick template → enter experience → verify AI generates personalized skill content |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
