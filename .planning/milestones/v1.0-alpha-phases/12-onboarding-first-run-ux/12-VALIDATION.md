---
phase: 12
slug: onboarding-first-run-ux
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && pnpm test --run --reporter=verbose src/features/onboarding` |
| **Full suite command** | `cd frontend && pnpm test --run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && pnpm test --run src/features/onboarding`
- **After every plan wave:** Run `cd frontend && pnpm test --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | BUG-01 | unit | `cd frontend && pnpm test --run src/app/\\(workspace\\)` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | ONBD-01 | unit | `cd frontend && pnpm test --run src/app/page` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | ONBD-02 | unit | `cd frontend && pnpm test --run src/features/onboarding` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 2 | ONBD-03 | unit | `cd frontend && pnpm test --run src/features/onboarding/components/ApiKeySetupStep` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 2 | ONBD-04 | unit | `cd frontend && pnpm test --run src/features/onboarding` | ❌ W0 | ⬜ pending |
| 12-02-03 | 02 | 2 | ONBD-05 | unit | `cd frontend && pnpm test --run src/features/onboarding` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 2 | WS-01 | unit | `cd frontend && pnpm test --run src/components/workspace-switcher` | ❌ W0 | ⬜ pending |
| 12-03-02 | 03 | 2 | WS-02 | unit | `cd frontend && pnpm test --run src/lib/workspace-nav` | ❌ W0 | ⬜ pending |
| 12-03-03 | 03 | 2 | BUG-02 | manual | n/a | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/app/__tests__/page.test.tsx` — stubs for ONBD-01, BUG-02: auto-create workspace flow
- [ ] `frontend/src/app/(workspace)/[workspaceSlug]/__tests__/page.test.tsx` — stubs for BUG-01: workspaceId UUID sourcing
- [ ] `frontend/src/features/onboarding/components/__tests__/ApiKeySetupStep.test.tsx` — stubs for ONBD-03: inline key validation UI
- [ ] `frontend/src/features/onboarding/__tests__/OnboardingChecklist.test.tsx` — stubs for ONBD-04, ONBD-05
- [ ] `frontend/src/components/__tests__/workspace-switcher.test.tsx` — stubs for WS-01: member count display
- [ ] `frontend/src/lib/__tests__/workspace-nav.test.tsx` — stubs for WS-02: saveLastWorkspacePath, getLastWorkspacePath

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| New sign-up redirects to workspace, never blank page | BUG-02, ONBD-01 | Requires real Supabase auth flow + first-user state in test DB | 1. Create fresh account via `/sign-up`. 2. Complete email confirmation. 3. Verify redirect goes to `/{workspace-slug}` with onboarding checklist visible, not a blank screen. |
| Workspace switcher navigation lands on last-visited page | WS-02 | Requires multi-workspace session with navigation history | 1. Switch to workspace A, navigate to `/issues`. 2. Switch to workspace B. 3. Switch back to workspace A. Verify landing on `/issues`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
