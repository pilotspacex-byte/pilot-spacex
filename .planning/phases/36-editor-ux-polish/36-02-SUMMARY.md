---
phase: 36-editor-ux-polish
plan: 02
subsystem: ui
tags: [react, tiptap, focus-mode, keyboard-shortcuts, mobx, prop-threading, tdd]

# Dependency graph
requires:
  - 36-editor-ux-polish/36-01 (UIStore.isFocusMode observable + AppShell wiring)
provides:
  - "isFocusMode prop threading from NoteDetailPage through NoteCanvas to NoteCanvasLayout"
  - "Cmd+Shift+F / Ctrl+Shift+F keyboard shortcut to toggle focus mode"
  - "Escape key exits focus mode when isFocusMode=true (Escape guard prevents accidental consumption)"
  - "InlineNoteHeader Maximize2 focus toggle button with aria-label + aria-pressed"
  - "NoteCanvasLayout: 6 chrome elements hidden when isFocusMode=true"
  - "NoteCanvasLayout: fixed Minimize2 exit button at z-[41] in focus mode"
  - "NoteDetailPage unmount cleanup: exitFocusMode() prevents focus mode leaking to other pages"
  - "document-canvas max-w-[720px] single constant in focus mode (vs. responsive ladder)"
affects:
  - Any future plan that reads isFocusMode from NoteCanvasProps

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Prop threading pattern: observer NoteDetailPage reads MobX store, passes as plain prop to non-observer child"
    - "TDD inline handler pattern: test keyboard handler logic directly without mounting complex hooks"
    - "Fixed affordance button pattern: fixed top-3 right-3 z-[41] with backdrop-blur for focus mode exit"

key-files:
  created:
    - frontend/src/components/editor/__tests__/NoteCanvasEditor.focus-mode.test.ts
    - frontend/src/components/editor/__tests__/InlineNoteHeader.focus-mode.test.tsx
  modified:
    - frontend/src/components/editor/NoteCanvasEditor.tsx
    - frontend/src/components/editor/NoteCanvasLayout.tsx
    - frontend/src/components/editor/InlineNoteHeader.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx

key-decisions:
  - "NoteCanvasLayout is NOT observer() — isFocusMode arrives as prop from NoteDetailPage (observer); adding observer() would cause nested flushSync crash in React 19 with TipTap NodeViews"
  - "Escape guard: e.key === 'Escape' && isFocusMode — no e.preventDefault(), allows slash command ProseMirror-level Escape to run first"
  - "Fixed exit button renders in editorContainerRef div (not outside layout) — stays in scroll context, z-[41] below dialog z-index"
  - "document-canvas uses single max-w-[720px] constant in focus mode — not a responsive ladder, gives consistent comfortable reading width"
  - "Unmount cleanup added to NoteDetailPage (not NoteCanvasLayout) — page owns focus mode lifetime; canvas is a display component"

patterns-established:
  - "Chrome gating pattern: wrap each UI chrome element with !isFocusMode && (original condition)"
  - "Keyboard shortcut extension: add handlers to existing useEffect + update deps array"

requirements-completed: [EDIT-03]

# Metrics
duration: 9min
completed: 2026-03-19
---

# Phase 36 Plan 02: isFocusMode Prop Threading + UX Implementation Summary

**Cmd+Shift+F focus mode fully wired: keyboard shortcut, chrome hiding, Maximize2 toggle button, fixed Minimize2 exit affordance, and NoteDetailPage unmount cleanup**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-03-19T16:12:34Z
- **Completed:** 2026-03-19T16:21:45Z
- **Tasks:** 2
- **Files modified:** 4, created: 2

## Accomplishments

- Extended `NoteCanvasProps` with `isFocusMode?: boolean` and `onToggleFocusMode?: () => void`
- Added `isFocusMode` and `onToggleFocusMode` destructuring in `useNoteCanvasEditor`
- Extended keyboard shortcut useEffect: Cmd/Ctrl+Shift+F calls `onToggleFocusMode?.()`, Escape when `isFocusMode=true` calls `onToggleFocusMode?.()` (no `preventDefault`)
- Updated useEffect deps: `[isChatViewOpen, handleChatViewOpen, onSave, isFocusMode, onToggleFocusMode]`
- Added 7 unit tests for keyboard shortcut behaviors (TDD pattern: inline handler construction)
- In `NoteCanvasLayout`: added `Minimize2` and `Tooltip*` imports, destructured new props, wrapped 6 chrome elements with `!isFocusMode` guard, updated `document-canvas` width logic, added fixed exit button at `z-[41]`
- In `InlineNoteHeader`: added `Maximize2` import, added `isFocusMode` and `onToggleFocusMode` to `InlineNoteHeaderProps` interface, added focus toggle button with correct `aria-label` + `aria-pressed` attributes
- In `NoteDetailPage`: imported `useUIStore`, added `const uiStore = useUIStore()`, added cleanup `useEffect` calling `uiStore.exitFocusMode()` on unmount, passed `isFocusMode={uiStore.isFocusMode}` and `onToggleFocusMode={uiStore.toggleFocusMode}` to `NoteCanvas`
- Added 6 unit tests for `InlineNoteHeader` focus mode button (render, aria-label, aria-pressed, click handler, absent-when-undefined)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend NoteCanvasProps and add keyboard shortcut in NoteCanvasEditor** - `bf4e6f00` (feat)
2. **Task 2: Thread isFocusMode through NoteDetailPage, NoteCanvasLayout chrome hide, InlineNoteHeader focus button** - `ff6590d9` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 followed TDD — tests written first to define keyboard shortcut behaviors, then implementation added. All 7 tests pass. Task 2 tests also all pass (6 InlineNoteHeader focus mode tests)._

## Files Created/Modified

- `frontend/src/components/editor/NoteCanvasEditor.tsx` — Added `isFocusMode` and `onToggleFocusMode` to interface + destructuring; extended keyboard shortcut useEffect with Cmd+Shift+F and Escape guard handlers
- `frontend/src/components/editor/NoteCanvasLayout.tsx` — Added imports, destructured new props, wrapped 6 chrome elements, focus-aware canvas width, fixed exit button
- `frontend/src/components/editor/InlineNoteHeader.tsx` — Added `Maximize2` import, `isFocusMode`/`onToggleFocusMode` props, focus toggle button with full aria attributes
- `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx` — `useUIStore` import, uiStore usage, unmount cleanup, new NoteCanvas props
- `frontend/src/components/editor/__tests__/NoteCanvasEditor.focus-mode.test.ts` — 7 keyboard shortcut tests
- `frontend/src/components/editor/__tests__/InlineNoteHeader.focus-mode.test.tsx` — 6 focus button UI tests

## Decisions Made

- `NoteCanvasLayout` is NOT wrapped in `observer()` — isFocusMode flows as a prop from the `observer()` NoteDetailPage. This is a non-negotiable constraint: adding `observer()` to NoteCanvasLayout causes a nested `flushSync` crash in React 19 when TipTap NodeViews are active.
- Escape key guard: `e.key === 'Escape' && isFocusMode` — no `e.preventDefault()` on the Escape handler so slash command menus (which register Escape at ProseMirror level, before `window`) can dismiss themselves first.
- Fixed Minimize2 exit button is placed inside the `editorContainerRef` div so it appears within the editor scroll context. `z-[41]` places it above the focus mode overlay but below dialog z-index levels.
- Unmount cleanup lives in `NoteDetailPage`, not `NoteCanvasLayout` — the page component owns the focus mode lifetime; the canvas is a display component that receives state as props.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Pre-commit hook ran prettier and reformatted `InlineNoteHeader.focus-mode.test.tsx` (multi-line JSX → single-line) and `NoteCanvasLayout.tsx` (wrapped conditionals → inline). Needed to re-stage and re-commit.

## User Setup Required

None.

## Next Phase Readiness

- Complete focus mode UX is now functional end-to-end: Cmd+Shift+F enters/exits, Escape exits, sidebar is hidden (Plan 01), all chrome is hidden (this plan), fixed exit button is available
- No blockers

## Self-Check: PASSED

- `frontend/src/components/editor/NoteCanvasEditor.tsx` — FOUND
- `frontend/src/components/editor/NoteCanvasLayout.tsx` — FOUND
- `frontend/src/components/editor/InlineNoteHeader.tsx` — FOUND
- `frontend/src/app/(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx` — FOUND
- `frontend/src/components/editor/__tests__/NoteCanvasEditor.focus-mode.test.ts` — FOUND
- `frontend/src/components/editor/__tests__/InlineNoteHeader.focus-mode.test.tsx` — FOUND
- `.planning/phases/36-editor-ux-polish/36-02-SUMMARY.md` — FOUND
- Commit `bf4e6f00` — FOUND
- Commit `ff6590d9` — FOUND
