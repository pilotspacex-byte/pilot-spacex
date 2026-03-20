---
phase: 30-tiptap-extension-foundation
plan: 01
subsystem: testing
tags: [vitest, tiptap, prosemirror, react-testing-library, tdd, red-tests]

# Dependency graph
requires: []
provides:
  - "PullQuoteExtension.test.ts: 5 RED tests covering EDIT-01 (attr toggle, markdown serialize, round-trip, blockId)"
  - "SelectionToolbar-headings.test.tsx: 6 RED tests covering EDIT-02 (H1/H2/P label, toggleHeading dispatch, pull quote active state)"
  - "node-view-bridge.test.ts: 4 RED tests covering NodeView bridge factory (provider, throw, value, isolation)"
affects:
  - 30-02 (PullQuoteExtension implementation — these tests turn GREEN)
  - 30-03 (SelectionToolbar + node-view-bridge implementation — these tests turn GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED phase — test files committed before production code exists"
    - "Captured selectionUpdate listener pattern for testing components with internal visibility state"
    - "Mock editor factory pattern with isActiveMap override for SelectionToolbar tests"

key-files:
  created:
    - "frontend/src/features/notes/editor/extensions/__tests__/PullQuoteExtension.test.ts"
    - "frontend/src/components/editor/__tests__/SelectionToolbar-headings.test.tsx"
    - "frontend/src/features/notes/editor/extensions/__tests__/node-view-bridge.test.ts"
  modified: []

key-decisions:
  - "SelectionToolbar tests use captured event listener approach to fire selectionUpdate and make toolbar visible, rather than directly mocking isVisible state"
  - "SelectionToolbar tests mock getAIStore and useSelectionAIActions at module level to isolate from store dependencies"
  - "node-view-bridge tests use renderHook from @testing-library/react — no DOM rendering needed, pure hook behavior"

patterns-established:
  - "Pattern: buildMockEditor() with isActiveMap record type for declarative editor state setup"
  - "Pattern: fireSelectionUpdate() closure returned alongside mock editor for event simulation"
  - "Pattern: All test function names use test_ prefix to match existing project convention"

requirements-completed:
  - EDIT-01
  - EDIT-02

# Metrics
duration: 8min
completed: 2026-03-19
---

# Phase 30 Plan 01: TipTap Extension Foundation — RED Test Scaffolding Summary

**15 failing RED tests across 3 files establish TDD gate for PullQuoteExtension (EDIT-01), SelectionToolbar heading dropdown (EDIT-02), and NodeView context bridge utility before any production code is written**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-19T12:12:12Z
- **Completed:** 2026-03-19T12:20:00Z
- **Tasks:** 3 (all TDD RED phase)
- **Files modified:** 3 created

## Accomplishments

- PullQuoteExtension.test.ts: 5 RED tests fail with "Failed to resolve import ../PullQuoteExtension" — proves tests are real and test the correct module path
- SelectionToolbar-headings.test.tsx: 6 RED tests fail with "Unable to find element" for `data-testid="heading-dropdown-trigger"` and `data-testid="pull-quote-toggle"` — proves tests target the actual UI elements Plan 03 will add
- node-view-bridge.test.ts: 4 RED tests fail with "Failed to resolve import ../node-view-bridge" — proves tests reference the correct module path Plan 03 will create

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED tests for PullQuoteExtension (EDIT-01)** - `ae25630e` (test)
2. **Task 2: Write RED tests for SelectionToolbar heading dropdown (EDIT-02)** - `944b9adf` (test)
3. **Task 3: Write RED tests for node-view-bridge utility** - `d70f47ba` (test)

_Note: TDD RED phase — only test commits, no production code commits._

## Files Created/Modified

- `frontend/src/features/notes/editor/extensions/__tests__/PullQuoteExtension.test.ts` - 5 RED tests for EDIT-01: attr toggle, markdown serialize, round-trip, blockId assignment
- `frontend/src/components/editor/__tests__/SelectionToolbar-headings.test.tsx` - 6 RED tests for EDIT-02: heading label computation, toggleHeading dispatch, pull quote active state
- `frontend/src/features/notes/editor/extensions/__tests__/node-view-bridge.test.ts` - 4 RED tests for NodeView bridge: factory shape, throws outside provider, returns value inside provider, cross-context isolation

## Decisions Made

- **SelectionToolbar visibility approach:** The toolbar only renders when `isVisible=true` (internal state, triggered by `selectionUpdate` event). Tests capture the event listener during `editor.on()` and fire it via a `fireSelectionUpdate()` closure — this correctly simulates a real text selection without needing a full ProseMirror editor in component tests.
- **Mock module granularity:** `getAIStore` and `useSelectionAIActions` mocked at module level so SelectionToolbar renders without real AI store wiring. This isolates heading behavior from AI action complexity.
- **Test file extension:** `node-view-bridge.test.ts` (not `.tsx`) because the utility is pure TypeScript with React context — no JSX rendering needed in the test file itself (renderHook handles the React wrapping).

## Deviations from Plan

None — plan executed exactly as written. All test file contents match the plan specification.

## Issues Encountered

- Prettier reformatted `SelectionToolbar-headings.test.tsx` after first commit attempt (multi-line function signature). Staged the reformatted file and committed in second pass. No functional changes — purely formatting.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 can now proceed: implement PullQuoteExtension.ts → PullQuoteExtension.test.ts turns GREEN
- Plan 03 can proceed in parallel: implement SelectionToolbar heading dropdown + pull quote toggle + node-view-bridge.ts → SelectionToolbar-headings.test.tsx and node-view-bridge.test.ts turn GREEN
- All test imports reference correct final file paths — no path changes needed when implementations land

---
*Phase: 30-tiptap-extension-foundation*
*Completed: 2026-03-19*

## Self-Check: PASSED

- FOUND: frontend/src/features/notes/editor/extensions/__tests__/PullQuoteExtension.test.ts
- FOUND: frontend/src/components/editor/__tests__/SelectionToolbar-headings.test.tsx
- FOUND: frontend/src/features/notes/editor/extensions/__tests__/node-view-bridge.test.ts
- FOUND: .planning/phases/30-tiptap-extension-foundation/30-01-SUMMARY.md
- FOUND commit ae25630e (Task 1 — PullQuoteExtension tests)
- FOUND commit 944b9adf (Task 2 — SelectionToolbar heading tests)
- FOUND commit d70f47ba (Task 3 — node-view-bridge tests)
