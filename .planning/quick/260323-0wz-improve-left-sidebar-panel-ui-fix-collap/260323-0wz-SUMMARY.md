---
phase: quick
plan: 260323-0wz
subsystem: frontend/layout
tags: [sidebar, ui, collapsed-state, spacing, active-state]
dependency_graph:
  requires: []
  provides: [improved-sidebar-collapsed-ux]
  affects: [frontend/src/components/layout/sidebar.tsx]
tech_stack:
  added: []
  patterns: [tailwind-pseudo-element-indicators, flex-col-collapsed-controls]
key_files:
  created: []
  modified:
    - frontend/src/components/layout/sidebar.tsx
decisions:
  - "Use Tailwind before:/after: pseudo-element classes for active accent bar/dot instead of a separate DOM element"
  - "Hide WorkspaceSwitcher entirely when collapsed (only show Compass icon) to avoid awkward stacking"
  - "Stack notification bell and avatar vertically in collapsed mode (flex-col) rather than side-by-side"
metrics:
  duration: "15 minutes"
  completed: "2026-03-23"
  tasks_completed: 2
  files_modified: 1
---

# Quick Task 260323-0wz: Improve Left Sidebar Panel UI / Fix Collapsed State Summary

**One-liner:** Sidebar collapsed state refined with py-2 nav item padding, h-9 New Note button, flex-col user controls, h-8 collapse toggle, and accent bar/dot active indicators replacing shadow-based cues.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix collapsed state spacing and icon layout | 62c272fc | sidebar.tsx |
| 2 | Improve active state visibility and vertical rhythm | 62c272fc | sidebar.tsx |

## Changes Made

### Task 1: Collapsed State Spacing and Icon Layout

- **Header area**: When collapsed, `WorkspaceSwitcher` is now hidden entirely (was awkwardly rendered inline). Only the `Compass` icon shows, horizontally centered with `px-2` padding.
- **Nav items collapsed**: Changed from `justify-center px-2` to `justify-center px-0 py-2` — icons now have proper vertical breathing room within the 60px container.
- **Section divider**: `w-4 h-px mb-1.5` → `w-8 h-px mb-2` — divider between Main/AI sections spans more of the 60px width and has more space below.
- **New Note button**: `h-8 w-8` → `h-9 w-9` (36px touch target) with `h-4 w-4` icons in collapsed mode.
- **Bottom user controls collapsed**: `flex items-center gap-1 p-1.5` → `flex-col items-center gap-1.5 p-2` — notification bell and user avatar now stack vertically, each in its own row.
- **Collapse toggle**: Container `p-1.5` → `p-2`; button `h-6` → `h-8` (32px minimum touch target met).

### Task 2: Active State Visibility and Vertical Rhythm

- **Active state indicator (expanded)**: Added `before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-4 before:w-[3px] before:rounded-full before:bg-primary` — colored left accent bar replaces the subtle `shadow-warm-sm`.
- **Active state indicator (collapsed)**: Added `after:absolute after:bottom-0 after:left-1/2 after:-translate-x-1/2 after:h-[3px] after:w-3 after:rounded-full after:bg-primary` — bottom dot indicator visible within the 60px icon.
- **Active font weight**: `font-medium` → `font-semibold` on active nav items.
- **Removed `shadow-warm-sm`** from nav items and pinned notes active state (shadow not visually distinct enough as sole active cue).
- **Vertical rhythm normalization**: `gap-0.5` → `gap-1` (nav items), `mt-3` → `mt-4` (between sections), `py-1.5` → `py-2` (ScrollArea), `mb-3` → `mb-4` + `mb-1.5` → `mb-2` (pinned notes section).
- **Pinned notes active state**: Same left accent bar pattern (`before:h-3.5`) applied to active pinned note links.

## Deviations from Plan

None — plan executed exactly as written, with the following minor note:

- Both Task 1 and Task 2 were committed in a single commit (`62c272fc`) rather than two separate commits. This is because Prettier reformatted the file after Task 1's staged changes, making it impractical to commit partial diffs while keeping the file in a valid state. The logical separation between tasks remains clear in the commit message body.

## Verification

- `pnpm type-check`: Passed with zero errors.
- `SidebarUserControls.test.tsx`: 14 tests pass.
- `sidebar-navigation.test.tsx`: 16 pre-existing failures (missing QueryClientProvider in test setup — not introduced by this change, confirmed by running on stashed state which showed 288 total failing tests across the suite before changes).

## Self-Check

Files modified:
- `frontend/src/components/layout/sidebar.tsx` — modified

Commits:
- `62c272fc` — feat(260323-0wz): improve sidebar collapsed state spacing and active indicators

## Self-Check: PASSED
