---
phase: quick-260318-naw
plan: "01"
subsystem: frontend/settings
tags: [investigation, settings-modal, migration, frontend]
dependency_graph:
  requires: []
  provides: [settings-modal-migration-plan]
  affects: [frontend/src/features/settings, frontend/src/app/(workspace)/settings]
tech_stack:
  added: []
  patterns: [strangler-fig, radix-dialog-nested, react-lazy-panels, settings-modal-context]
key_files:
  created:
    - .planning/quick/260318-naw-checkout-new-branch-then-investigate-to-/INVESTIGATION.md
  modified: []
decisions:
  - "Modal shell uses custom wide DialogContent (min(900px,calc(100vw-2rem)) x min(700px,calc(100vh-2rem))) rather than the default sm:max-w-lg variant"
  - "Navigation inside modal uses local activeSection state instead of URL routing, with optional ?settings=<id> query param for shareable links"
  - "Strangler fig approach: build modal alongside routes, migrate one page at a time, remove old routes in Phase 4"
  - "SettingsModalContext (Option A) chosen over UIStore extension for trigger mechanism — purpose-built context, cleaner separation"
  - "React.lazy per panel to preserve code-splitting and avoid loading all 13+ settings bundles on modal mount"
  - "Sheet and full-page modal approaches rejected; sidebar-nav Dialog is the correct pattern for 11+ settings sections"
metrics:
  duration_minutes: 35
  completed_date: "2026-03-18"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 0
---

# Quick Task 260318-naw: Settings Modal Migration Investigation Summary

**One-liner:** Full audit of 14 settings pages with complexity tiers, modal-readiness scores, and a 4-phase 9-plan strangler-fig migration plan from full-page routes to a wide Radix Dialog with sidebar nav and React.lazy content panels.

## What Was Done

### Task 1: Feature Branch + Settings Page Catalogue

Created branch `feat/settings-modal` from `main` and audited all settings pages:

- 14 routes catalogued (11 in `settingsNavSections` + billing + members redirect + integrations inline)
- Each page scored on complexity (Simple/Medium/Complex) and modal-readiness (1/2/3)
- Score distribution: 5 drop-in (score 1), 6 minor tweaks (score 2), 4 significant rework (score 3)
- Identified 2 pages with `beforeunload` guards (workspace-general, profile)
- Identified 9+ nested dialog/sheet components across skills, roles, security, and general pages
- Catalogued all 8 settings hooks with stale times and query patterns

### Task 2: Modal Architecture + Phased Migration Plan

Produced a comprehensive architecture and migration plan covering:

- Modal shell design: wide `DialogContent` (900px x 700px), left sidebar nav (w-52), scrollable content area
- Local `activeSection` state replacing URL-based navigation
- `SettingsModalContext` pattern for open/close/section trigger from sidebar
- `React.lazy` per panel for preserved code-splitting
- Mobile: full-screen modal + `Select` dropdown replacing sidebar on `< lg` screens
- 4 key technical risks identified and mitigated (beforeunload guard, deep links, nested dialogs, guest role redirect)
- 4-phase migration plan with 9 total plans: Shell (3) + Medium pages (2) + Complex pages (3) + Cleanup (1)

## Deviations from Plan

None — plan executed exactly as written. Both tasks completed in a single INVESTIGATION.md document since the content was developed together during the audit pass.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 + 2 | 32638952 | feat(settings): create feature branch and catalogue all settings pages |

## Key Findings

1. **Low migration risk overall:** Route files are already thin wrappers — page components in `features/settings/pages/` can be imported directly into the modal with zero changes for 5 of 14 pages.

2. **Integrations page needs extraction:** `app/.../settings/integrations/page.tsx` contains the full component inline (not a thin wrapper). Must extract to `features/settings/pages/` before modal import.

3. **Nested dialogs are safe:** Radix Dialog handles nested z-index stacking internally. No z-index hacks needed. The only case requiring testing is `SkillGeneratorModal` (20KB, SSE streaming) inside the modal.

4. **beforeunload needs replacement:** 2 pages use `window.addEventListener('beforeunload', ...)` which does not fire on modal close. Need a close-guard `AlertDialog` in the modal shell with unsaved-changes registration.

5. **`useParams` is safe everywhere:** All pages use `useParams()` which works correctly inside a modal rendered within the workspace route tree.

## Self-Check

- [x] INVESTIGATION.md created at correct path
- [x] INVESTIGATION.md is 756 lines (min: 200)
- [x] INVESTIGATION.md has 8 sections (min: 6)
- [x] Branch `feat/settings-modal` checked out
- [x] Commit 32638952 exists
