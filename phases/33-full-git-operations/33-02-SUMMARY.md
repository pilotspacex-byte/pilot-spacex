---
phase: 33-full-git-operations
plan: "02"
subsystem: ui
tags: [mobx, tauri, ipc, git, typescript, stores]

# Dependency graph
requires:
  - phase: 33-01
    provides: Rust commands git_pull, git_push, git_status, git_branch_list/create/switch/delete with GitPullResult, FileStatus, GitRepoStatus, BranchInfo structs
  - phase: 32-02
    provides: gitClone Channel<GitProgress> pattern established in tauri.ts
provides:
  - Typed TypeScript interfaces matching all Phase 33 Rust structs (GitPullResult, FileStatus, GitRepoStatus, BranchInfo)
  - 7 new IPC wrappers in tauri.ts (gitPull, gitPush, gitStatus, gitBranchList, gitBranchCreate, gitBranchSwitch, gitBranchDelete)
  - GitStore MobX observable store with full pull/push/branch CRUD state
  - useGitStore() hook exported from RootStore and stores/index.ts
affects: [33-03, 33-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GitStore follows ProjectStore pattern: makeAutoObservable, runInAction, lazy import('@/lib/tauri') inside each action"
    - "Query wrappers (gitStatus, gitBranchList) return safe defaults when not in Tauri; mutation wrappers throw"
    - "Channel<GitProgress> pattern reused for gitPull and gitPush streaming progress"

key-files:
  created:
    - frontend/src/lib/tauri.ts (4 new interfaces + 7 new wrappers appended)
    - frontend/src/stores/features/git/GitStore.ts
  modified:
    - frontend/src/stores/RootStore.ts
    - frontend/src/stores/index.ts

key-decisions:
  - "GitStore.setRepoPath() clears all state and auto-calls refreshAll() on non-empty path — ensures UI always has fresh state when switching repos"
  - "modifiedFiles computed excludes untracked (not untracked); stagedFiles filters f.staged — matches expected UI grouping for diff view"

patterns-established:
  - "GitStore pattern: each action lazy-imports only the specific tauri wrapper it needs (not the full module)"
  - "refreshAll() uses Promise.all([refreshStatus(), refreshBranches()]) for parallel fetch"
  - "pull()/push() set isPulling/isPushing before IPC call and clear in both success and error paths via runInAction"

requirements-completed: [GIT-02, GIT-03, GIT-04, GIT-05, GIT-06]

# Metrics
duration: 6min
completed: 2026-03-20
---

# Phase 33 Plan 02: Typed IPC Wrappers and GitStore Summary

**Typed IPC layer for 7 git commands (pull/push/status/branch CRUD) + MobX GitStore with 12 observables, 6 computeds, and 11 actions registered on RootStore via useGitStore hook**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-20T06:58:58Z
- **Completed:** 2026-03-20T07:04:19Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added 4 TypeScript interfaces (GitPullResult, FileStatus, GitRepoStatus, BranchInfo) matching Rust structs exactly, including snake_case field names for Tauri serde serialization
- Implemented 7 IPC wrapper functions: gitPull/gitPush use Channel<GitProgress> streaming; gitStatus/gitBranchList are safe query wrappers returning defaults outside Tauri; gitBranchCreate/Switch/Delete are mutation wrappers
- Created GitStore with full reactive state for all git operations — observables for status, branches, pull/push progress/result/error, plus 6 computed derivations and 11 actions following the ProjectStore pattern
- Registered GitStore on RootStore and re-exported useGitStore() from stores/index.ts

## Task Commits

Each task was committed atomically:

1. **Task 1: Add typed IPC wrappers and TS interfaces to tauri.ts** - `0d46b904` (feat)
2. **Task 2: Create GitStore MobX store and register on RootStore** - `83164701` (feat)

## Files Created/Modified
- `frontend/src/lib/tauri.ts` - Added 4 new interfaces and 7 new IPC wrappers after the existing git commands section
- `frontend/src/stores/features/git/GitStore.ts` - New GitStore class with full observable state management
- `frontend/src/stores/RootStore.ts` - Added git: GitStore field, constructor init, reset() call, and useGitStore() hook
- `frontend/src/stores/index.ts` - Added useGitStore and GitStore to re-exports

## Decisions Made
- GitStore.setRepoPath() auto-triggers refreshAll() on non-empty path — ensures UI automatically loads fresh data when a project is selected
- Query wrappers return safe defaults outside Tauri mode (empty arrays/objects) while mutation wrappers throw — consistent with existing tauri.ts pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Prettier reformatted the GitStore import block during pre-commit hook on first commit attempt — re-staged the formatted file and committed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 33-03 can now import useGitStore() and all 4 TypeScript interfaces for building the GitStatusPanel, BranchSelector, PullPushBar, and ConflictList UI components
- All 7 IPC wrappers are ready; Rust commands were implemented in Plan 33-01

## Self-Check: PASSED

- FOUND: frontend/src/lib/tauri.ts
- FOUND: frontend/src/stores/features/git/GitStore.ts
- FOUND: frontend/src/stores/RootStore.ts
- FOUND: frontend/src/stores/index.ts
- FOUND commit: 0d46b904
- FOUND commit: 83164701
