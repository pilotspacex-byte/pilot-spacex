---
phase: 27-project-hub-issue-views
plan: "01"
subsystem: ui
tags: [react, mobx, issue-views, priority-view, project-hub, localStorage]

# Dependency graph
requires:
  - phase: 26-sidebar-tree-navigation
    provides: ProjectPageTree navigation infrastructure
provides:
  - Per-project ViewMode persistence in IssueViewStore (projectViewModes Map)
  - ViewMode type alias including 'priority'
  - PriorityView component (5 swimlane groups using ListGroup)
  - Project overview page replaced with IssueViewsRoot hub
  - IssueToolbar extended with Priority view button
  - IssueViewsRoot reads/writes view mode per-project scope
affects: [project-hub, issue-views, toolbar, priority-grouping]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-entity scoped store state via Map (projectViewModes) with global fallback
    - Thin page wrapper pattern: page.tsx delegates entirely to IssueViewsRoot
    - Swimlane view pattern: reuses ListGroup for priority-based grouping

key-files:
  created:
    - frontend/src/features/issues/components/views/priority/PriorityView.tsx
    - frontend/src/features/issues/components/views/priority/index.ts
    - frontend/src/features/issues/components/views/priority/__tests__/PriorityView.test.tsx
    - frontend/src/stores/features/issues/__tests__/IssueViewStore.test.ts
  modified:
    - frontend/src/stores/features/issues/IssueViewStore.ts
    - frontend/src/features/issues/components/views/IssueViewsRoot.tsx
    - frontend/src/features/issues/components/views/IssueToolbar.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/overview/page.tsx

key-decisions:
  - "ViewMode type exported from IssueViewStore — single source of truth for all view mode typing"
  - "projectViewModes uses Map<string, ViewMode> observable — MobX auto-observes Map mutations"
  - "getEffectiveViewMode falls back to global viewMode — backward compatible with workspace-level /issues page"
  - "setEffectiveViewMode(mode) without projectId updates global viewMode — keeps setViewMode contract"
  - "Project overview page replaced with thin IssueViewsRoot wrapper — no separate stats dashboard"
  - "PriorityView renders all 5 groups regardless of count — consistent UI, empty groups show 0 badge"
  - "Mobile auto-switch covers both 'table' and 'priority' modes — both are desktop-first layouts"

patterns-established:
  - "Per-entity state scoping: store global state + per-entity Map, getEffective/setEffective methods with fallback"
  - "Thin page wrappers: Next.js page extracts params, delegates all rendering to feature component"

requirements-completed: [HUB-01, HUB-02, HUB-03]

# Metrics
duration: 13min
completed: 2026-03-12
---

# Phase 27 Plan 01: Project Hub Issue Views Summary

**Per-project view mode persistence via IssueViewStore.projectViewModes Map, PriorityView with 5 priority swimlanes using ListGroup, and project overview page replaced with full IssueViewsRoot issue hub**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-12T18:36:48Z
- **Completed:** 2026-03-12T18:50:13Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Introduced `ViewMode` type alias (`'board' | 'list' | 'table' | 'priority'`) as a single source of truth
- Added `projectViewModes: Map<string, ViewMode>` to IssueViewStore with `getEffectiveViewMode`/`setEffectiveViewMode` methods — project-scoped view mode with global fallback and localStorage persistence
- Created `PriorityView` component that groups issues into Urgent/High/Medium/Low/No Priority swimlanes using `ListGroup`; empty groups render with 0 badge per spec
- Replaced project overview stats dashboard with thin `IssueViewsRoot` wrapper — projects are now full issue hubs
- Extended `IssueToolbar` with Priority button and `projectId` prop for scoped view mode reads/writes
- IssueViewsRoot mobile auto-switch now handles both `'table'` and `'priority'` modes

## Task Commits

1. **Task 1: Per-project IssueViewStore persistence and PriorityView component** - `c97551e5` (feat, TDD)
2. **Task 2: Project hub page, IssueViewsRoot priority integration, and toolbar extension** - `e97ac8a7` (feat)

## Files Created/Modified

- `frontend/src/stores/features/issues/IssueViewStore.ts` — ViewMode type, projectViewModes Map, getEffectiveViewMode/setEffectiveViewMode, persistence updates
- `frontend/src/features/issues/components/views/priority/PriorityView.tsx` — New: 5-group swimlane view using ListGroup
- `frontend/src/features/issues/components/views/priority/index.ts` — New: barrel export
- `frontend/src/features/issues/components/views/priority/__tests__/PriorityView.test.tsx` — New: grouping, empty groups, loading, collapse tests
- `frontend/src/stores/features/issues/__tests__/IssueViewStore.test.ts` — New: getEffectiveViewMode, setEffectiveViewMode, persistence, reset tests
- `frontend/src/features/issues/components/views/IssueViewsRoot.tsx` — PriorityView import and render branch, projectId-scoped view mode, mobile auto-switch update
- `frontend/src/features/issues/components/views/IssueToolbar.tsx` — Priority button added, projectId prop, scoped active check
- `frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/overview/page.tsx` — Replaced with thin IssueViewsRoot wrapper

## Decisions Made

- `ViewMode` type exported from IssueViewStore — single source of truth for all view mode typing. Replaces inline `'board' | 'list' | 'table'` union types across the codebase.
- `projectViewModes` uses `Map<string, ViewMode>` observable — MobX auto-observes Map mutations (no manual action needed in makeAutoObservable).
- `getEffectiveViewMode` falls back to global `viewMode` — workspace-level /issues page is unaffected by project-level changes (key isolation requirement).
- Project overview page replaced entirely — became a thin wrapper. Stats/cycle/recent-issues dashboard removed per plan spec.
- `PriorityView` renders all 5 groups always (not just non-empty) — consistent swimlane layout, 0 badge indicates no issues at that priority.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

Pre-commit prek hook uses a stash/unstash cycle for unstaged files that conflicted with prettier reformatting. Resolution: committed each task with only task-relevant files staged, stashing pre-existing unrelated changes to eliminate the conflict window.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Project hub is fully functional with Board/List/Table/Priority views
- Per-project view mode persists independently from workspace-level view mode
- Priority view infrastructure reusable for other grouping dimensions
- Ready for Phase 27 Plan 02 (additional project hub features)

---
*Phase: 27-project-hub-issue-views*
*Completed: 2026-03-12*
