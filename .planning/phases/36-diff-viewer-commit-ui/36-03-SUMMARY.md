---
phase: 36-diff-viewer-commit-ui
plan: "03"
subsystem: tauri-git-ui
tags: [react, mobx, commit-panel, git-status-panel, diff-viewer, shadcn-ui, typescript]
dependency_graph:
  requires: [DiffViewer-component, GitStore-diff-stage-commit-actions]
  provides: [CommitPanel-component, interactive-GitStatusPanel, project-dashboard-git-layout]
  affects:
    - frontend/src/features/git/components/commit-panel.tsx
    - frontend/src/features/git/components/git-status-panel.tsx
    - frontend/src/features/git/index.ts
    - frontend/src/features/projects/components/project-dashboard.tsx
tech_stack:
  added: []
  patterns:
    - observer-mobx
    - shadcn-checkbox
    - useState-ephemeral-ui-state
    - useEffect-auto-dismiss
    - two-column-layout-flex
key_files:
  created:
    - frontend/src/features/git/components/commit-panel.tsx
  modified:
    - frontend/src/features/git/components/git-status-panel.tsx
    - frontend/src/features/git/index.ts
    - frontend/src/features/projects/components/project-dashboard.tsx
decisions:
  - "commitMessage stored in local useState (not GitStore) — ephemeral UI state that belongs to the component lifecycle"
  - "Push button only visible when status.ahead > 0 — avoids dead button for repos with no unpushed commits"
  - "CommitPanel auto-clears message and starts 5s dismiss timer on lastCommitOid — ties success feedback lifecycle to store signal"
  - "FileGroup receives FileStatus[] not string[] — gives checkbox toggle access to staged boolean without repeated find() calls"
  - "stopPropagation on checkbox container div (not Checkbox itself) — prevents file selection event while allowing native checkbox interaction"
  - "Two-column layout in ProjectDashboard: w-[280px] fixed left sidebar + flex-1 right diff viewer — mirrors VS Code source control panel layout"
metrics:
  duration: "6 minutes"
  completed: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
  lines_added: ~290
---

# Phase 36 Plan 03: CommitPanel + Interactive GitStatusPanel + ProjectDashboard Integration Summary

**One-liner:** CommitPanel with staged-file count, commit textarea, Commit/Commit+Push/Push buttons and OID success banner; GitStatusPanel upgraded with per-file Checkbox stage/unstage and clickable file rows for diff selection; both wired into ProjectDashboard as a VS Code-style two-column layout.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Create CommitPanel and update GitStatusPanel with interactive file rows | 76c40546 | commit-panel.tsx (new, 172 lines), git-status-panel.tsx (updated), index.ts (+CommitPanel export) |
| 2 | Wire CommitPanel and DiffViewer into ProjectDashboard | 5ce9f328 | project-dashboard.tsx (two-column layout) |

## What Was Built

### CommitPanel (`commit-panel.tsx`)

MobX `observer` component — reads GitStore, all local UI state via `useState`:

- **Stage summary** line: "N file(s) staged" with `GitCommit` icon; shows `stageError` inline if set
- **Textarea** (`<Textarea rows={3}>`) with `commitMessage` local state and character count below
- **Commit** button (primary): disabled when message empty, no staged files, or `isCommitting`
- **Commit & Push** button (outline): same disabled logic; after successful commit calls `gitStore.push()`, shows "Pushing..." state via `isPushingAfterCommit` local flag
- **Push** button (ghost): only rendered when `status.ahead > 0`; shows push count ("Push 2 commits")
- **Success banner**: renders `bg-green-500/10` with `<Check />` icon and short OID (`lastCommitOid.slice(0, 7)`) when commit succeeds; `useEffect` clears message immediately and triggers `clearCommitState()` after 5 seconds
- **Error display**: `commitError` shown below buttons with `<AlertCircle />` in `text-destructive`

### GitStatusPanel (`git-status-panel.tsx`)

Updated `FileGroup` component signature — now accepts `FileStatus[]` instead of `string[]`, plus:

- `staged: boolean` — determines checkbox state (checked for staged files, unchecked for unstaged)
- `selectedPath: string | null` — highlights currently selected file with `bg-muted`
- `onFileClick: (path) => void` — called when the row div is clicked
- `onToggleStage: (path, stage) => void` — called from checkbox `onCheckedChange`
- `bulkAction?: { label, onClick, disabled }` — rendered as ghost button in section header

**File row interaction:**
- Entire row is `cursor-pointer` with `hover:bg-muted/50` / `bg-muted` (selected)
- `onClick` on the row calls `onFileClick(file.path)` → `gitStore.selectFile(path)`
- Checkbox wrapped in `<div onClick={(e) => e.stopPropagation()}>` to prevent dual-trigger
- Checkbox `onCheckedChange` calls `onToggleStage(path, !staged)` → `stageFiles` or `unstageFiles`

**Section headers** now show bulk action buttons:
- Staged → "Unstage All" (calls `gitStore.unstageAll()`)
- Modified → "Stage All" (calls `gitStore.stageAll()`)
- Untracked → "Stage All" (calls `gitStore.stageAll()`)
- All buttons disabled when `gitStore.isStaging`

### ProjectDashboard Integration

The expanded git panel now uses a two-column flex layout:

```
[Left 280px fixed]              [Right flex-1]
  GitStatusPanel                  DiffViewer maxHeight=400px
  ──────────────────
  CommitPanel
```

Imports updated: `DiffViewer`, `CommitPanel`, `Separator` added from `@/features/git` and `@/components/ui/separator`.

## Verification

1. `tsc --noEmit` passes with 0 errors
2. CommitPanel exported and wired into ProjectDashboard
3. DiffViewer wired into ProjectDashboard right column
4. GitStatusPanel has interactive checkboxes for stage/unstage
5. Full workflow enabled: click file → see diff, check/uncheck → stage/unstage, type message → commit → push

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/features/git/components/commit-panel.tsx` — exists, 172 lines
- `frontend/src/features/git/components/git-status-panel.tsx` — exists, contains FileStatus[], Checkbox, selectFile, stageFiles, unstageFiles, Stage All, Unstage All
- `frontend/src/features/git/index.ts` — contains `export { CommitPanel }` and `export { DiffViewer }`
- `frontend/src/features/projects/components/project-dashboard.tsx` — contains DiffViewer, CommitPanel, w-[280px]
- Commit 76c40546 — verified in git log
- Commit 5ce9f328 — verified in git log
