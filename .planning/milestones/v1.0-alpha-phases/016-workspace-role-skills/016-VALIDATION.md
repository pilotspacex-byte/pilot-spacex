---
phase: 16
slug: workspace-role-skills
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-10
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend) |
| **Config file** | `backend/pyproject.toml`, `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest tests/unit/repositories/test_workspace_role_skill_repository.py tests/unit/services/test_workspace_role_skill_service.py tests/unit/api/test_workspace_role_skills_router.py -q` |
| **Full suite command** | `make quality-gates-backend && make quality-gates-frontend` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/unit/repositories/test_workspace_role_skill_repository.py tests/unit/services/test_workspace_role_skill_service.py tests/unit/api/test_workspace_role_skills_router.py tests/unit/ai/agents/test_role_skill_materializer.py -q`
- **After every plan wave:** Run `make quality-gates-backend && make quality-gates-frontend`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | WRSKL-01 | unit | `cd backend && uv run pytest tests/unit/repositories/test_workspace_role_skill_repository.py tests/unit/services/test_workspace_role_skill_service.py tests/unit/api/test_workspace_role_skills_router.py --co -q` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | WRSKL-03 | unit | `cd backend && uv run pytest tests/unit/ai/agents/test_role_skill_materializer.py --co -q` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 2 | WRSKL-01 | unit | `cd backend && uv run pytest tests/unit/repositories/test_workspace_role_skill_repository.py -q` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 3 | WRSKL-01 | unit | `cd backend && uv run pytest tests/unit/services/test_workspace_role_skill_service.py tests/unit/api/test_workspace_role_skills_router.py -q` | ❌ W0 | ⬜ pending |
| 16-03-02 | 03 | 3 | WRSKL-03 | unit | `cd backend && uv run pytest tests/unit/ai/agents/test_role_skill_materializer.py -q` | ❌ W0 | ⬜ pending |
| 16-04-01 | 04 | 4 | WRSKL-01 | unit | `cd frontend && pnpm test --run src/services/api/__tests__/workspace-role-skills.test.ts` | ❌ W0 | ⬜ pending |
| 16-04-02 | 04 | 4 | WRSKL-02 | unit | `cd frontend && pnpm test --run src/features/settings/components/__tests__/workspace-skill-card.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/unit/repositories/test_workspace_role_skill_repository.py` — xfail stubs for WRSKL-01..03
- [ ] `backend/tests/unit/services/test_workspace_role_skill_service.py` — xfail stubs for WRSKL-01..02
- [ ] `backend/tests/unit/api/test_workspace_role_skills_router.py` — xfail stubs for WRSKL-01..02 admin guard
- [ ] Extend `backend/tests/unit/ai/agents/test_role_skill_materializer.py` — xfail stubs for WRSKL-03, WRSKL-04, and new `test_workspace_skill_inherited_when_no_personal_skills`
- [ ] `frontend/src/features/settings/components/__tests__/workspace-skill-card.test.tsx` — it.todo() vitest stubs
- [ ] `frontend/src/services/api/__tests__/workspace-role-skills.test.ts` — it.todo() vitest stubs

*Note: Existing test infrastructure (pytest + vitest) is already in place. Wave 0 only needs stub files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI skill generation produces valid YAML output | WRSKL-01 | AI generation is non-deterministic | Trigger generation, verify skill appears in review UI with parseable content |
| Personal skill takes precedence over workspace skill in agent context | WRSKL-04 | Requires live AI agent interaction | Create workspace skill + personal skill for same role, confirm agent uses personal skill |
| Member with no personal skill inherits workspace skill in AI session | WRSKL-03 | Requires live AI agent interaction | Create + activate workspace skill; verify MEMBER chat session reflects inherited skill |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 45s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
