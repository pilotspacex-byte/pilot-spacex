---
phase: 36-editor-ux-polish
plan: 01
subsystem: ui
tags: [mobx, react, appshell, focus-mode, uistore, sidebar, tdd]

# Dependency graph
requires: []
provides:
  - "UIStore.isFocusMode MobX observable boolean (session-only, not persisted)"
  - "UIStore.enterFocusMode() / exitFocusMode() / toggleFocusMode() actions"
  - "AppShell conditionally hides sidebar and hamburger bar when isFocusMode is true"
affects:
  - 36-editor-ux-polish/36-02 (NoteDetailPage reads isFocusMode and passes as prop to NoteCanvasLayout)
  - Any component that reads uiStore.isFocusMode directly

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Session-only MobX observable: field declared on class, NOT added to PersistedUIState or setupPersistence reaction"
    - "AppShell focus-mode guard: conditional render replaces unconditional motion.aside for sidebar branches"

key-files:
  created: []
  modified:
    - frontend/src/stores/UIStore.ts
    - frontend/src/stores/__tests__/UIStore.test.ts
    - frontend/src/components/layout/app-shell.tsx

key-decisions:
  - "isFocusMode is session-only — NOT added to PersistedUIState interface and NOT tracked in setupPersistence reaction; focus mode resets on page reload (intentional)"
  - "AppShell mobile branch uses ternary (!uiStore.isFocusMode ? <AnimatePresence> : null) rather than adding guard inside AnimatePresence — ensures the entire mobile sidebar tree is unmounted in focus mode"
  - "AppShell desktop branch uses && conditional render (not width:0 animation trick) — removes sidebar from the DOM so main content naturally expands to full width"

patterns-established:
  - "Session-only observable pattern: add as plain class field, exclude from PersistedUIState and setupPersistence tracked expression"

requirements-completed: [EDIT-03]

# Metrics
duration: 10min
completed: 2026-03-19
---

# Phase 36 Plan 01: isFocusMode MobX Observable + AppShell Wiring Summary

**MobX isFocusMode session-only observable added to UIStore with enter/exit/toggle actions, AppShell sidebar and hamburger bar hidden when focus mode is active**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-19T16:00:00Z
- **Completed:** 2026-03-19T16:09:32Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `isFocusMode = false` observable to UIStore following existing action pattern (commandPaletteOpen / searchModalOpen)
- Added `enterFocusMode()`, `exitFocusMode()`, `toggleFocusMode()` actions — intentionally excluded from PersistedUIState and setupPersistence reaction
- Wired AppShell: mobile sidebar AnimatePresence wrapped in `!isFocusMode` ternary; desktop/tablet motion.aside replaced with `&&` conditional render; hamburger bar gets `!isFocusMode` guard
- 6 new unit tests (TDD): default value, toggle, enter, exit, non-persistence contract, MobX reactivity

## Task Commits

Each task was committed atomically:

1. **Task 1: Add isFocusMode observable to UIStore** - `be5ef365` (feat)
2. **Task 2: Hide sidebar and hamburger bar in AppShell when isFocusMode is true** - `be5be748` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 followed TDD (RED: 6 failing tests, GREEN: implementation, all 12 pass)_

## Files Created/Modified
- `frontend/src/stores/UIStore.ts` - Added `isFocusMode` field and `enterFocusMode` / `exitFocusMode` / `toggleFocusMode` action methods
- `frontend/src/stores/__tests__/UIStore.test.ts` - Added `UIStore — isFocusMode focus mode` describe block with 6 tests including non-persistence contract verification
- `frontend/src/components/layout/app-shell.tsx` - Three targeted changes: mobile sidebar guard, desktop sidebar conditional render, hamburger bar guard

## Decisions Made
- `isFocusMode` is session-only: excluded from `PersistedUIState` interface and `setupPersistence` reaction's tracked expression. Focus mode resets on page reload — this is intentional per plan spec.
- Desktop sidebar uses `&&` conditional render (not `width: 0` animation trick) — removes the DOM node entirely so the flex main content area fills the full viewport without any layout calculation.
- Mobile branch uses ternary form `!isFocusMode ? <AnimatePresence>...</AnimatePresence> : null` rather than adding an `&&` guard inside AnimatePresence — ensures the full mobile sidebar subtree is unmounted.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- `pnpm lint --max-warnings 0` exits 1 due to 19 pre-existing warnings in other files (coverage JS, e2e specs, test mocks, workspace-guard.tsx). No warnings exist in any file touched by this plan. Pre-existing warnings are out of scope per deviation rules.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `UIStore.isFocusMode`, `enterFocusMode()`, `exitFocusMode()`, `toggleFocusMode()` are ready for Plan 02 to use
- AppShell sidebar already hides on `isFocusMode = true` — Plan 02 can call `uiStore.enterFocusMode()` from NoteDetailPage and the shell chrome disappears
- No blockers

---
*Phase: 36-editor-ux-polish*
*Completed: 2026-03-19*

## Self-Check: PASSED

- `frontend/src/stores/UIStore.ts` — FOUND
- `frontend/src/stores/__tests__/UIStore.test.ts` — FOUND
- `frontend/src/components/layout/app-shell.tsx` — FOUND
- `.planning/phases/36-editor-ux-polish/36-01-SUMMARY.md` — FOUND
- Commit `be5ef365` — FOUND
- Commit `be5be748` — FOUND
