---
phase: 42-command-palette-and-breadcrumb-navigation
plan: 02
subsystem: ui
tags: [breadcrumbs, symbol-outline, markdown-parser, navigation, mobx, react-hooks]

# Dependency graph
requires:
  - phase: 40-webgpu-note-canvas-ide-file-editor
    provides: FileStore, OpenFile types, pmBlockMarkers parser
provides:
  - BreadcrumbBar component with clickable path segments and sibling Popover dropdowns
  - useBreadcrumbs hook deriving segments from FileStore activeFile
  - parseMarkdownSymbols parser building heading hierarchy with PM block support
  - useSymbolOutline hook with 500ms debounce and cursor-tracking active symbol
  - SymbolOutlinePanel component with collapsible tree and kind-appropriate icons
affects: [42-03-editor-integration, 43-lsp-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [stack-based-symbol-hierarchy, debounced-symbol-extraction, cursor-tracking-active-symbol]

key-files:
  created:
    - frontend/src/features/breadcrumbs/types.ts
    - frontend/src/features/breadcrumbs/hooks/useBreadcrumbs.ts
    - frontend/src/features/breadcrumbs/hooks/useBreadcrumbs.test.ts
    - frontend/src/features/breadcrumbs/components/BreadcrumbBar.tsx
    - frontend/src/features/breadcrumbs/components/BreadcrumbSegment.tsx
    - frontend/src/features/symbol-outline/types.ts
    - frontend/src/features/symbol-outline/parsers/markdownSymbols.ts
    - frontend/src/features/symbol-outline/parsers/markdownSymbols.test.ts
    - frontend/src/features/symbol-outline/hooks/useSymbolOutline.ts
    - frontend/src/features/symbol-outline/hooks/useSymbolOutline.test.ts
    - frontend/src/features/symbol-outline/components/SymbolOutlinePanel.tsx
    - frontend/src/features/symbol-outline/components/SymbolTreeItem.tsx
  modified:
    - frontend/src/features/command-palette/registry/ActionRegistry.ts
    - frontend/src/features/command-palette/registry/ActionRegistry.test.ts

key-decisions:
  - "React 19 compliant isLoading: batched state object instead of synchronous setState in effect body"
  - "Stack-based symbol hierarchy: pop until parent with lower level, PM blocks nest under most recent heading"
  - "EditorLike interface for useSymbolOutline to decouple from Monaco types"

patterns-established:
  - "Stack-based markdown symbol parser: maintains [level, symbol][] stack for O(n) hierarchy building"
  - "Debounced symbol extraction: 500ms markdown, 1000ms code, with cleanup-based loading state"
  - "BreadcrumbSegment siblings resolved by walking FileTreeItem tree to matching depth"

requirements-completed: [CMD-02, CMD-03]

# Metrics
duration: 11min
completed: 2026-03-24
---

# Phase 42 Plan 02: Breadcrumb Navigation & Symbol Outline Summary

**BreadcrumbBar with sibling Popover dropdowns and SymbolOutlinePanel with stack-based markdown heading parser, PM block extraction, and cursor-tracking active symbol**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-24T09:49:08Z
- **Completed:** 2026-03-24T10:00:00Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- BreadcrumbBar derives path segments from FileStore activeFile with clickable Popover sibling navigation
- parseMarkdownSymbols builds hierarchical DocumentSymbol tree from headings (H1-H6) and PM block markers
- useSymbolOutline provides debounced (500ms) symbol extraction with active symbol tracking via editor cursor position
- SymbolOutlinePanel renders collapsible tree with kind-appropriate icons (Hash, Blocks, FunctionSquare, etc.)
- 21 passing unit tests across 3 test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Breadcrumb types, useBreadcrumbs hook, and BreadcrumbBar component** - `ad181162` (feat)
2. **Task 2: Symbol outline types, markdown parser, useSymbolOutline hook, and panel component** - `fdb7a8b9` (feat)

_Note: TDD tasks have RED+GREEN in single commit (tests written first, then implementation)_

## Files Created/Modified
- `frontend/src/features/breadcrumbs/types.ts` - BreadcrumbSegment interface
- `frontend/src/features/breadcrumbs/hooks/useBreadcrumbs.ts` - Derive segments from activeFile path + file tree
- `frontend/src/features/breadcrumbs/hooks/useBreadcrumbs.test.ts` - 7 tests for path splitting, siblings, notes
- `frontend/src/features/breadcrumbs/components/BreadcrumbBar.tsx` - Observer component with lateral navigation
- `frontend/src/features/breadcrumbs/components/BreadcrumbSegment.tsx` - Popover trigger with sibling dropdown
- `frontend/src/features/symbol-outline/types.ts` - DocumentSymbol, SymbolKind types
- `frontend/src/features/symbol-outline/parsers/markdownSymbols.ts` - Stack-based heading + PM block parser
- `frontend/src/features/symbol-outline/parsers/markdownSymbols.test.ts` - 8 tests for hierarchy building
- `frontend/src/features/symbol-outline/hooks/useSymbolOutline.ts` - Debounced extraction + cursor tracking
- `frontend/src/features/symbol-outline/hooks/useSymbolOutline.test.ts` - 6 tests for debounce, cursor, loading
- `frontend/src/features/symbol-outline/components/SymbolOutlinePanel.tsx` - ScrollArea panel with tree
- `frontend/src/features/symbol-outline/components/SymbolTreeItem.tsx` - Recursive tree item with icons
- `frontend/src/features/command-palette/registry/ActionRegistry.ts` - Fixed stub to real implementation (Rule 3)
- `frontend/src/features/command-palette/registry/ActionRegistry.test.ts` - Fixed TS2532 non-null assertions

## Decisions Made
- React 19 compliance: `isLoading` tracked via batched state object `{ symbols, isLoading }` with cleanup-function setState pattern to avoid synchronous setState in effect body
- Stack-based markdown parser: maintains `[level, DocumentSymbol][]` stack, pops until finding parent with lower heading level
- EditorLike interface abstracts Monaco dependency for testability -- mock editor with getPosition/onDidChangeCursorPosition

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ActionRegistry stub and test TS errors from 42-01**
- **Found during:** Task 1 (commit blocked by tsc pre-commit hook)
- **Issue:** ActionRegistry.ts was a placeholder stub with no parameters; test imported non-existent `clearAllActions`; array indexing without non-null assertions
- **Fix:** Implemented full ActionRegistry with Map-based registry, priority sorting, clearAllActions; added `!` assertions to test array access
- **Files modified:** `frontend/src/features/command-palette/registry/ActionRegistry.ts`, `frontend/src/features/command-palette/registry/ActionRegistry.test.ts`
- **Verification:** tsc passes, eslint passes
- **Committed in:** ad181162 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed React 19 lint violations in useSymbolOutline**
- **Found during:** Task 2 (commit blocked by eslint pre-commit hook)
- **Issue:** `setIsLoading(true)` synchronously in effect body violates react-hooks/set-state-in-effect; useRef access during render violates react-hooks/refs
- **Fix:** Replaced separate isLoading state with batched state object `{ symbols, isLoading }` using cleanup-function setState pattern
- **Files modified:** `frontend/src/features/symbol-outline/hooks/useSymbolOutline.ts`
- **Verification:** eslint passes, all tests still green
- **Committed in:** fdb7a8b9 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for pre-commit hooks. No scope creep.

## Issues Encountered
None beyond the lint/type issues documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Breadcrumb and symbol outline components ready for integration into EditorLayout (Plan 42-03)
- useSymbolOutline accepts EditorLike interface for Monaco editor wiring
- BreadcrumbBar accepts fileTreeItems prop for tree-based sibling resolution

## Self-Check: PASSED

All 12 created files verified present. Both task commits (ad181162, fdb7a8b9) verified in git log. 21/21 tests passing.

---
*Phase: 42-command-palette-and-breadcrumb-navigation*
*Completed: 2026-03-24*
