---
phase: 32-workspace-management-git-clone
plan: "02"
subsystem: tauri-frontend
tags: [typescript, mobx, tauri-ipc, react, shadcn-ui, git-clone, workspace-management]
dependency_graph:
  requires: [32-01-rust-backend]
  provides: [typed-ipc-wrappers, project-store, project-dashboard-ui]
  affects: [32-03-desktop-settings]
tech_stack:
  added: []
  patterns:
    - MobX makeAutoObservable with runInAction for async actions
    - Tauri v2 Channel<T> for streaming progress (gitClone)
    - isTauri() guard + lazy dynamic import for all @tauri-apps/api usage
    - observer() wrapper on all components reading MobX observables
key_files:
  created:
    - frontend/src/stores/features/projects/ProjectStore.ts
    - frontend/src/features/projects/components/project-dashboard.tsx
    - frontend/src/features/projects/components/clone-repo-dialog.tsx
    - frontend/src/features/projects/components/link-repo-dialog.tsx
    - frontend/src/features/projects/index.ts
  modified:
    - frontend/src/lib/tauri.ts
    - frontend/src/stores/RootStore.ts
    - frontend/src/stores/index.ts
decisions:
  - "gitClone wrapper creates Channel<GitProgress> and wires onmessage to callback — Tauri v2 streaming pattern"
  - "CloneRepoDialog prevents closing during active clone via onOpenChange guard"
  - "LinkRepoDialog uses local isLinking state separate from store.error to avoid stale error display"
  - "ProjectDashboard useEffect guards with isTauri() — loadProjects no-ops in browser/SSG"
metrics:
  duration_seconds: 392
  completed_date: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 3
---

# Phase 32 Plan 02: Typed IPC Wrappers + Project Dashboard UI Summary

**One-liner:** MobX ProjectStore with gitClone Channel streaming, plus observer dashboard, clone-with-progress dialog, and native folder-picker link dialog using shadcn/ui.

## What Was Built

### tauri.ts — New Types + IPC Wrappers

Three interfaces added matching Rust structs from Plan 01:

| Interface | Fields |
|-----------|--------|
| `ProjectEntry` | name, path, remote_url, linked, added_at |
| `GitProgress` | pct, message |
| `GitCredentialInfo` | username, has_pat |

Five workspace command wrappers and four git command wrappers added. All follow the established pattern: `isTauri()` guard, lazy `await import('@tauri-apps/api/core')`, typed `invoke<T>()` call.

**`gitClone`** creates a `Channel<GitProgress>` and wires `channel.onmessage = onProgress` — this is the Tauri v2 Channel API pattern for streaming data from Rust to the WebView.

### ProjectStore — MobX Observable Store

| Observable | Type | Purpose |
|------------|------|---------|
| `projects` | `ProjectEntry[]` | All managed repos |
| `projectsDir` | `string` | Base directory path |
| `isLoading` | `boolean` | Loading state for list |
| `error` | `string \| null` | Load error |
| `isCloning` | `boolean` | Clone in progress |
| `cloneProgress` | `GitProgress \| null` | Current progress |
| `cloneError` | `string \| null` | Clone error |

Actions: `loadProjects`, `cloneRepo` (with progress callback), `cancelClone` (best-effort), `linkExistingRepo`, `reset`.

`cloneRepo` derives the target directory automatically: extracts repo name from URL (strips `.git` suffix) and appends to `projectsDir`.

### ProjectDashboard Component

Observer component that calls `loadProjects()` on mount (isTauri-gated). Shows:
- Header with title, base directory path, "Clone Repository" + "Link Existing" action buttons
- Loading: animated pulse skeleton rows
- Error: red error block with message
- Empty state: centered card with FolderGit2 icon and action buttons
- Repo list: card-style rows with GitBranch icon, name, path (mono), remote URL, Cloned/Linked badge, added-at date

### CloneRepoDialog Component

Observer dialog with URL input, shadcn/ui Progress bar bound to `cloneProgress.pct`, and state-conditional buttons:
- Not cloning: Cancel + Clone buttons (Clone disabled when URL empty)
- Cloning: "Cancel Clone" button only, input and Clone button disabled
- Error: red destructive message block
- Success: auto-closes and resets URL

Prevents dialog close during active clone via `onOpenChange` guard.

### LinkRepoDialog Component

Observer dialog with:
- Readonly path input showing selected folder
- "Browse..." button → calls `openFolderDialog()` (native OS picker)
- "Link Repository" button → calls `linkExistingRepo(path)`
- Local `isLinking` state for button disable/text change
- Error display from `projectStore.error`

### RootStore Integration

- `projects: ProjectStore` field added to class
- `new ProjectStore()` in constructor
- `this.projects.reset()` in `reset()`
- `useProjectStore()` hook exported from RootStore and stores/index.ts

## Deviations from Plan

None — plan executed exactly as written.

The project dashboard files (`project-dashboard.tsx`, `clone-repo-dialog.tsx`, `link-repo-dialog.tsx`, `index.ts`) were present in the repository from a prior session's commit (`63a492e3 feat(32-03)`) but had not been committed as part of plan 32-02. The Task 2 commit (`6bec0633`) captured the prettier-formatted `ProjectStore.ts` change alongside the already-present dashboard files.

## Verification Results

```
pnpm type-check: PASSED (0 errors)
tauri.ts exports: getProjectsDir, linkRepo, gitClone, cancelClone — FOUND
features/projects/index.ts exports: ProjectDashboard, CloneRepoDialog, LinkRepoDialog — FOUND
RootStore: projects: ProjectStore field — FOUND
useProjectStore() hook — FOUND
```

## Self-Check: PASSED

- frontend/src/lib/tauri.ts: FOUND (modified)
- frontend/src/stores/features/projects/ProjectStore.ts: FOUND (created)
- frontend/src/stores/RootStore.ts: FOUND (modified, projects field + hook)
- frontend/src/stores/index.ts: FOUND (modified, useProjectStore export)
- frontend/src/features/projects/components/project-dashboard.tsx: FOUND
- frontend/src/features/projects/components/clone-repo-dialog.tsx: FOUND
- frontend/src/features/projects/components/link-repo-dialog.tsx: FOUND
- frontend/src/features/projects/index.ts: FOUND
- Task 1 commit 96aa6fc7: FOUND
- Task 2 commit 6bec0633: FOUND
