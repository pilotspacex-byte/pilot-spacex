---
phase: 36-diff-viewer-commit-ui
plan: "02"
subsystem: ui
tags: [react, mobx, virtuoso, git, diff-viewer, syntax-highlighting, tailwind]

requires:
  - phase: 36-01
    provides: "FileDiff type in tauri.ts, GitStore diff state (selectedFilePath, fileDiffs, isLoadingDiff, diffError, fetchDiff, selectFile)"

provides:
  - "DiffViewer component rendering unified diff with colored +/- line annotations and line number gutters"
  - "parseDiffLines() helper parsing unified diff text into typed DiffLine objects"
  - "Virtualized rendering via react-virtuoso for 1000+ line diffs (DIFF-05)"
  - "DiffViewer exported from features/git/index.ts"

affects:
  - "36-03-commit-panel — imports DiffViewer from features/git"

tech-stack:
  added: []
  patterns:
    - "Virtuoso-based list virtualization for large text content in Tauri panels"
    - "Unified diff parsing without external library — custom parseDiffLines() from raw git output"

key-files:
  created:
    - frontend/src/features/git/components/diff-viewer.tsx
  modified:
    - frontend/src/features/git/index.ts

key-decisions:
  - "No external diff rendering library — custom parseDiffLines() avoids react-diff-view/git-diff-view bundle weight; git2-rs already provides standard unified diff format"
  - "react-virtuoso for virtualization over ScrollArea — Virtuoso handles virtual DOM at row level, preventing UI freeze on 1000+ line diffs (DIFF-05)"

patterns-established:
  - "DiffLineRow sub-component: renders one unified diff line with fixed-width old/new line number gutters (w-12 each), colored backgrounds, and monospace content area"
  - "Binary/empty/loading/error guard-clause pattern before reaching main virtualized render path"

requirements-completed: [DIFF-01, DIFF-05]

duration: 8min
completed: 2026-03-20
---

# Phase 36 Plan 02: Diff Viewer Summary

**DiffViewer React component parsing unified diff text into virtualized colored +/- rows with dual line-number gutters, binary file detection, and all loading/error states**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-20T08:46:00Z
- **Completed:** 2026-03-20T08:54:44Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Implemented `parseDiffLines()` helper that splits unified diff text into typed `DiffLine` objects (header/hunk/addition/deletion/context) with running old/new line number counters that reset per hunk
- Built `DiffViewer` observer component covering all states: no selection, loading, error, binary, empty diff, and normal virtualized diff
- Wired virtualization via `react-virtuoso` (already installed) — `Virtuoso` renders only visible rows, keeping UI responsive for diffs of any size
- All 7 acceptance criteria verified; TypeScript compiles cleanly with zero errors

## Task Commits

1. **Task 1: DiffViewer component with syntax-highlighted unified diff** - `18c5ffa1` (feat)

**Plan metadata:** _(created next)_

## Files Created/Modified

- `frontend/src/features/git/components/diff-viewer.tsx` - DiffViewer component (270 lines): parseDiffLines helper, DiffLineRow sub-component, main observer component with all state branches
- `frontend/src/features/git/index.ts` - Added `export { DiffViewer }` from diff-viewer module

## Decisions Made

- No external diff rendering library used: `react-diff-view` and `@git-diff-view/react` add significant bundle weight and are unnecessary because git2-rs already provides standard unified diff format — custom `parseDiffLines()` is ~60 lines and sufficient
- `react-virtuoso` (already installed at ^4.18.1) chosen for virtualization over a `ScrollArea` with all rows in DOM — Virtuoso virtualizes at the React element level, preventing layout thrash on 1000+ line diffs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript strict-mode errors in parseDiffLines and itemContent**
- **Found during:** Task 1 verification (tsc --noEmit)
- **Issue:** Three TypeScript errors: `lines[lines.length - 1]` possibly undefined (TS2532), `match[1]`/`match[2]` possibly undefined (TS2345), `lines[index]` possibly undefined in Virtuoso `itemContent` (TS2322)
- **Fix:** (1) Extracted `lastLine` local variable with explicit `!== undefined` guard; (2) Changed `if (match)` to `if (match?.[1] && match?.[2])`; linter auto-added `!` assertion on `lines[index]`
- **Files modified:** frontend/src/features/git/components/diff-viewer.tsx
- **Verification:** `npx tsc --noEmit` exits with 0 errors
- **Committed in:** 18c5ffa1 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - TypeScript strict-mode type errors)
**Impact on plan:** Necessary for correctness; no scope creep.

## Issues Encountered

None beyond the TypeScript strict-mode fixes above.

## Next Phase Readiness

- `DiffViewer` is exported from `features/git/index.ts` and ready for import by Plan 36-03 (CommitPanel integration)
- Component accepts optional `maxHeight` prop for flexible embedding in the commit sidebar
- No blockers

---
*Phase: 36-diff-viewer-commit-ui*
*Completed: 2026-03-20*
