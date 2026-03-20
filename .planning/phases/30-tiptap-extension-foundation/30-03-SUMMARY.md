---
phase: 30-tiptap-extension-foundation
plan: "03"
subsystem: ui
tags: [tiptap, react, context-bridge, heading-dropdown, radix-ui, mobx, nodeview]

# Dependency graph
requires:
  - phase: 30-tiptap-extension-foundation/30-01
    provides: RED tests for node-view-bridge and SelectionToolbar headings
provides:
  - createNodeViewBridgeContext typed factory — plain React context bridge for TipTap NodeViews
  - Heading dropdown (H1/H2/H3/Normal) in SelectionToolbar with active label display
  - Pull quote toggle button in SelectionToolbar with data-active state attribute
affects:
  - 32-file-card-nodeview (uses createNodeViewBridgeContext for FileCardView)
  - 33-video-embed-nodeview (uses createNodeViewBridgeContext for VideoEmbedView)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "NodeView context bridge: plain NodeView root -> React context -> observer() child"
    - "Heading level computed in render body via editor.isActive() (synchronous, no useState)"
    - "DropdownMenu from shadcn/ui for heading level picker in floating toolbar"

key-files:
  created:
    - frontend/src/features/notes/editor/extensions/node-view-bridge.ts
  modified:
    - frontend/src/components/editor/SelectionToolbar.tsx
    - frontend/src/features/notes/editor/extensions/index.ts

key-decisions:
  - "createNodeViewBridgeContext<T>() factory pattern: each NodeView gets its own typed context — prevents cross-contamination between multiple NodeViews"
  - "headingLabel computed in render body not useState: component re-renders on selectionUpdate events, making fresh isActive() reads always correct when toolbar is visible"
  - "Pull quote toggle reads isPullQuote from editor.isActive in render body — same synchronous pattern as headingLevel"
  - "SelectionToolbar MUST NOT be wrapped in observer() — flushSync constraint documented in component JSDoc"

patterns-established:
  - "Pattern: NodeView bridge — createNodeViewBridgeContext() factory creates typed Provider + useBridgeContext hook; plain NodeView root wraps observer() children"
  - "Pattern: Toolbar state from ProseMirror — compute active state synchronously from editor.isActive() in render body, no useState required"

requirements-completed:
  - EDIT-02

# Metrics
duration: 21min
completed: "2026-03-19"
---

# Phase 30 Plan 03: NodeView Bridge Utility + Heading Dropdown Summary

**createNodeViewBridgeContext<T>() factory with flushSync constraint doc + H1/H2/H3/Normal dropdown in SelectionToolbar + pull quote toggle, making 10 RED tests GREEN**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-19T12:20:49Z
- **Completed:** 2026-03-19T12:42:26Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Built `createNodeViewBridgeContext<T>()` generic factory with full doc comment explaining the React 19 flushSync constraint — establishes the reusable pattern for Phase 32 (FileCardView) and Phase 33 (VideoEmbedView)
- Added heading dropdown (H1/H2/H3/Normal) to SelectionToolbar using Radix DropdownMenu; trigger button shows active heading level label computed synchronously from `editor.isActive()`
- Added pull quote toggle button with `data-active` attribute driven by `editor.isActive('blockquote', { pullQuote: true })` — toolbar state reads without MobX
- 4/4 node-view-bridge tests GREEN, 6/6 SelectionToolbar heading tests GREEN; 0 type errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create node-view-bridge.ts utility** - `ed99130e` (feat)
2. **Task 2: Add heading dropdown and pull quote toggle to SelectionToolbar** - `483ff25f` (feat)

## Files Created/Modified

- `frontend/src/features/notes/editor/extensions/node-view-bridge.ts` - createNodeViewBridgeContext<T>() factory: typed React context bridge for TipTap NodeViews, with full flushSync constraint doc comment
- `frontend/src/components/editor/SelectionToolbar.tsx` - Added Quote import, DropdownMenu imports, setHeadingLevel/togglePullQuote callbacks, headingLevel/headingLabel/isPullQuote computed state, heading dropdown JSX, pull quote toggle button JSX
- `frontend/src/features/notes/editor/extensions/index.ts` - Added createNodeViewBridgeContext barrel export with constraint comment

## Decisions Made

- `createNodeViewBridgeContext<T>()` uses `createContext<T | null>(null)` with null guard in `useBridgeContext()` — throws on missing provider with exact error string the tests assert against
- `headingLevel` computed with `([1, 2, 3] as const).find(...)` in render body rather than effect + state — synchronous ProseMirror reads are always fresh on selectionUpdate re-renders
- `DropdownMenuTrigger asChild` wrapping a `Button` keeps consistent button styling and size from existing toolbar buttons
- SelectionToolbar `getAttributes` call inside `togglePullQuote` callback only — not in render path, so mock editor without `getAttributes` doesn't cause test failures

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed JSX-style comment inside TSDoc block comment**
- **Found during:** Task 1 (node-view-bridge.ts creation)
- **Issue:** The plan's doc comment example included `{/* observer() child */}` inside a TSDoc `/** ... */` block. The `*/` inside the JSX comment prematurely closes the outer TSDoc block comment, causing a parse error: `ERROR: Unexpected "}"` at the `}` of the JSX comment
- **Fix:** Removed the inline JSX comment from within the TSDoc code example; the surrounding `observer()` context is clear from the surrounding prose
- **Files modified:** frontend/src/features/notes/editor/extensions/node-view-bridge.ts
- **Verification:** 4/4 node-view-bridge tests GREEN after fix
- **Committed in:** ed99130e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in plan's code example)
**Impact on plan:** Minor syntax fix only. No behavior change, no scope change.

## Issues Encountered

- Pre-commit hook (prek) stashes/unstashes unstaged changes during commit — this caused a concern about whether lint could revert changes, but the test confirmed all changes survived the commit cycle correctly

## Next Phase Readiness

- `createNodeViewBridgeContext` exported from extensions barrel and ready for Phase 32 (FileCardView) and Phase 33 (VideoEmbedView) to import
- SelectionToolbar heading dropdown and pull quote toggle fully functional and tested
- Phase 30 Plan 04 (or remaining plans) can proceed — all EDIT-02 requirements satisfied

## Self-Check: PASSED

- FOUND: frontend/src/features/notes/editor/extensions/node-view-bridge.ts
- FOUND: frontend/src/components/editor/SelectionToolbar.tsx (with heading dropdown + pull quote)
- FOUND: .planning/phases/30-tiptap-extension-foundation/30-03-SUMMARY.md
- FOUND commit: ed99130e (Task 1: node-view-bridge.ts)
- FOUND commit: 483ff25f (Task 2: SelectionToolbar heading dropdown)
- FOUND commit: 2a95d5cd (docs: plan metadata)

---
*Phase: 30-tiptap-extension-foundation*
*Completed: 2026-03-19*
