---
phase: 12-onboarding-first-run-ux
plan: "03"
subsystem: ui
tags: [react, nextjs, mobx, localstorage, workspace-switcher]

# Dependency graph
requires:
  - phase: 12-01
    provides: WorkspaceContext stabilised as authoritative workspace source
provides:
  - saveLastWorkspacePath / getLastWorkspacePath localStorage utilities (workspace-nav.ts)
  - Member count display below workspace name in workspace switcher popover
  - Last-visited path restoration on workspace switch (WS-01, WS-02)
  - Pathname tracking in WorkspaceSlugLayout via useEffect
affects:
  - Any future workspace navigation enhancements
  - End-to-end onboarding flows that switch workspaces

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "localStorage wrapper with SSR guard (typeof window === 'undefined') and silent error swallowing"
    - "Path filter: settings paths (/settings/) excluded from saved navigation state"
    - "TDD RED→GREEN: test file written before implementation, confirmed failing, then implementation written"

key-files:
  created:
    - frontend/src/lib/workspace-nav.ts
    - frontend/src/lib/__tests__/workspace-nav.test.ts
    - frontend/src/components/__tests__/workspace-switcher.test.tsx
  modified:
    - frontend/src/components/layout/workspace-switcher.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/layout.tsx

key-decisions:
  - "saveLastWorkspacePath filters /settings/ paths — on workspace switch users land on their last non-settings page, not inside settings of a different workspace"
  - "getLastWorkspacePath returns null (not '') on failure — callers use null-coalescing to fall back to workspace root without branching on empty string"
  - "Pathname tracking in WorkspaceSlugLayout useEffect with [pathname, workspaceSlug] deps — covers both initial mount and SPA navigation within workspace"

patterns-established:
  - "localStorage utility pattern: SSR guard + try/catch + unit tests with vi.spyOn(Storage.prototype) for error cases"
  - "Observer component test pattern: vi.mock('mobx-react-lite') as passthrough, vi.mock('@/stores') for store, vi.mock('@/lib/workspace-nav') for utilities"

requirements-completed:
  - WS-01
  - WS-02

# Metrics
duration: 5min
completed: 2026-03-09
---

# Phase 12 Plan 03: Workspace Switcher Enhancements Summary

**localStorage-backed per-workspace last-path tracking + member count in workspace switcher popover via saveLastWorkspacePath/getLastWorkspacePath utilities**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-09T22:46:41Z
- **Completed:** 2026-03-09T22:51:06Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created `workspace-nav.ts` with `saveLastWorkspacePath` / `getLastWorkspacePath` localStorage utilities (SSR-safe, settings-path filtered, error-swallowing)
- Added member count display (`3 members` / `1 member`) below workspace name in the switcher popover list (WS-01)
- `handleSelectWorkspace` now reads `getLastWorkspacePath(slug)` and routes to stored path or workspace root (WS-02)
- `WorkspaceSlugLayout` tracks pathname via `useEffect` and persists every non-settings navigation to localStorage (WS-02)
- 12 unit tests: 9 for workspace-nav utilities, 3 for workspace-switcher component

## Task Commits

Each task was committed atomically:

1. **Task 1: Create workspace-nav.ts utility with localStorage path tracking** - `c745dfe1` (test — TDD RED+GREEN)
2. **Task 2: Add member count + last-path navigation to workspace-switcher and layout** - `e9a03122` (feat)

_Note: TDD tasks committed as single commit covering RED → GREEN (both test file and implementation)._

## Files Created/Modified

- `frontend/src/lib/workspace-nav.ts` - saveLastWorkspacePath / getLastWorkspacePath with SSR guard, settings filter, silent error swallowing
- `frontend/src/lib/__tests__/workspace-nav.test.ts` - 9 unit tests covering happy path, settings filter, SSR no-op, error swallowing
- `frontend/src/components/layout/workspace-switcher.tsx` - Added `getLastWorkspacePath` import; member count div in list items; last-path aware `handleSelectWorkspace`
- `frontend/src/app/(workspace)/[workspaceSlug]/layout.tsx` - Added `usePathname`, `useEffect`, `saveLastWorkspacePath` for pathname tracking
- `frontend/src/components/__tests__/workspace-switcher.test.tsx` - 3 component tests covering member count rendering, last-path navigation, and fallback to workspace root

## Decisions Made

- Settings paths (`/settings/`) are filtered in `saveLastWorkspacePath` — prevents users landing in another workspace's settings panel on switch
- `getLastWorkspacePath` returns `null` on failure, callers use `??` operator to fall back cleanly
- Pathname tracking uses `useEffect` in `WorkspaceSlugLayout` (not middleware) — keeps tracking client-side, co-located with workspace context

## Deviations from Plan

None - plan executed exactly as written. Prettier auto-formatted `workspace-switcher.tsx` on first commit attempt; re-staged and committed successfully.

## Issues Encountered

- Prettier pre-commit hook reformatted `workspace-switcher.tsx` on first commit attempt (inline JSX in `<div>` got multi-line formatting). Re-staged the formatted file and committed on second attempt. Not a code issue.
- First test for "renders member count" used `getByText('Workspace Alpha')` which matched two elements (trigger button + list item). Fixed to use `getByText('Workspace Beta')` (only appears in list, not trigger) for the name assertion.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WS-01 and WS-02 complete. Phase 12 all 3 plans done.
- Workspace switcher now shows member context and preserves navigation state across switches.
- Phase 13 (AI Provider Registry + Model Selection) can begin independently.

---
*Phase: 12-onboarding-first-run-ux*
*Completed: 2026-03-09*
