---
phase: 37-one-click-implement-tray
plan: "01"
subsystem: frontend/tauri-desktop
tags: [mobx, tauri, implement-pipeline, git-automation, sidecar]
dependency_graph:
  requires:
    - 35-01 (pilot-cli sidecar binary)
    - 36-01 (git diff/stage/commit commands)
    - 34-01 (terminal panel)
    - 33-01 (git branch/push commands)
  provides:
    - ImplementStore (pipeline orchestration)
    - ImplementIssueButton (one-click implement UI)
    - implement-complete window CustomEvent (for tray notification)
    - runPilotImplement tauri.ts wrapper
  affects:
    - frontend/src/stores/RootStore.ts
    - frontend/src/lib/tauri.ts
    - frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx
tech_stack:
  added:
    - ImplementStore (new MobX store)
    - TrayNotificationListener (new render-null component)
  patterns:
    - dynamic import of @tauri-apps/* inside store actions (SSG safety)
    - runInAction wrapping all post-async state mutations
    - observer() + custom hook (useImplementStore) pattern
    - Dynamic next/dynamic import with ssr:false for Tauri-only components
    - window CustomEvent for cross-component pipeline completion signaling
key_files:
  created:
    - frontend/src/stores/features/implement/ImplementStore.ts
    - frontend/src/features/implement/components/implement-issue-button.tsx
    - frontend/src/features/implement/index.ts
    - frontend/src/components/desktop/tray-notification-listener.tsx
  modified:
    - frontend/src/lib/tauri.ts (added runPilotImplement, sendNotification)
    - frontend/src/stores/RootStore.ts (registered ImplementStore, useImplementStore hook)
    - frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx (ImplementIssueButton integration)
    - frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx (TrayNotificationListener mount)
decisions:
  - "implement-complete CustomEvent dispatched from ImplementStore._emitComplete() — decouples store from tray component; TrayNotificationListener subscribes independently"
  - "runInAction used for all post-async state mutations — consistent with GitStore pattern throughout codebase"
  - "ImplementIssueButton rendered in a dedicated bar below IssueNoteHeader — avoids modifying IssueNoteHeaderProps interface"
  - "TrayNotificationListener added in workspace-slug-layout.tsx (Tauri-only) — survives client-side navigation, appropriate mount point"
  - "sidecarId captured from first SidecarOutput event (not from SidecarResult) — enables mid-flight cancellation before process exits"
metrics:
  duration_minutes: 6
  completed_date: "2026-03-20"
  tasks_completed: 2
  files_created: 4
  files_modified: 4
requirements_satisfied: [CLI-02, CLI-03]
---

# Phase 37 Plan 01: One-Click Implement Pipeline Summary

One-liner: MobX ImplementStore orchestrating the full branch-implement-stage-commit-push pipeline with ImplementIssueButton progress dialog and TrayNotificationListener for native OS notifications.

## What Was Built

### ImplementStore (`frontend/src/stores/features/implement/ImplementStore.ts`)

Full pipeline orchestrator with 8-state machine (`idle` → `branching` → `implementing` → `staging` → `committing` → `pushing` → `done` / `error`).

Key design decisions:
- All tauri IPC via dynamic `await import('@/lib/tauri')` — consistent with GitStore/ProjectStore pattern, prevents SSG build errors
- `runInAction` wrapping all post-async mutations — MobX requires this in strict mode
- `sidecarId` captured from the first `SidecarOutput` event (id field) — enables cancel before process completes
- Output buffer capped at 500 lines (shift + push pattern) — prevents unbounded memory growth during long-running implementations
- `_emitComplete()` dispatches `implement-complete` window CustomEvent — decouples the store from notification UI

### runPilotImplement wrapper (`frontend/src/lib/tauri.ts`)

Simple wrapper: `runSidecar(['implement', issueId, '--oneshot'], cwd, onOutput)`. Centralizes the sidecar args pattern so ImplementStore doesn't embed CLI arg knowledge.

Also added `sendNotification` wrapper (invokes Rust `send_notification` command) — required by TrayNotificationListener.

### ImplementIssueButton (`frontend/src/features/implement/components/implement-issue-button.tsx`)

Observer component with:
- Trigger button (disabled if no project linked, disabled while running)
- Progress dialog with `onInteractOutside` prevented during active pipeline
- Step icon mapping: GitBranch (branching), Loader2 (implementing/staging/committing/pushing), CheckCircle2 (done), XCircle (error)
- Last 20 lines of sidecar output in scrollable monospace area
- Cancel button gated by `canCancel` (only during `implementing` step)
- Close button gated by `isDone || isError`; calls `implementStore.reset()` on close

### TrayNotificationListener (`frontend/src/components/desktop/tray-notification-listener.tsx`)

Render-null component. Subscribes to `implement-complete` CustomEvent and fires native OS notifications via `sendNotification` IPC. Mounted in `workspace-slug-layout.tsx` (Tauri-only) so it survives navigation.

### Issue Detail Page Integration

`ImplementIssueButton` rendered in a dedicated `<div>` bar below `IssueNoteHeader`, gated by `isTauri()`. Dynamic import with `ssr: false` prevents static export failures.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Duplicate TrayNotificationListener declaration in workspace-slug-layout.tsx**
- **Found during:** Task 2 commit (pre-commit hook TS error)
- **Issue:** Two identical `const TrayNotificationListener = dynamic(...)` declarations — TypeScript `TS6133: 'TrayNotificationListener' is declared but its value is never read`
- **Fix:** Removed the duplicate declaration (second one was identical to first)
- **Files modified:** `frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx`
- **Commit:** af0ac7f4

**2. [Rule 2 - Missing critical functionality] TrayNotificationListener + sendNotification not yet in scope**
- **Found during:** Task 2 — workspace-slug-layout.tsx already referenced `TrayNotificationListener` in unstaged changes
- **Context:** The file had been pre-edited as part of Phase 37 planning work. The component `TrayNotificationListener` and its Rust IPC wrapper `sendNotification` were referenced but not implemented.
- **Fix:** Created `TrayNotificationListener` component and `sendNotification` wrapper — both required for the `implement-complete` CustomEvent chain to function end-to-end
- **Files modified:** `frontend/src/components/desktop/tray-notification-listener.tsx` (new), `frontend/src/lib/tauri.ts` (sendNotification added)
- **Commit:** af0ac7f4

## Self-Check

### Files Verified Exist

- FOUND: `frontend/src/stores/features/implement/ImplementStore.ts`
- FOUND: `frontend/src/features/implement/components/implement-issue-button.tsx`
- FOUND: `frontend/src/features/implement/index.ts`
- FOUND: `frontend/src/components/desktop/tray-notification-listener.tsx`

### Commits Verified

- FOUND: `c00b54c1` — feat(37-01): ImplementStore MobX store + runPilotImplement wrapper + RootStore registration
- FOUND: `af0ac7f4` — feat(37-01): ImplementIssueButton component + issue detail page integration

## Self-Check: PASSED
