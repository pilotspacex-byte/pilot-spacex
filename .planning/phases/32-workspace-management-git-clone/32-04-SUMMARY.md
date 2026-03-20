---
phase: 32-workspace-management-git-clone
plan: "04"
subsystem: tauri-desktop
tags: [gap-closure, routing, navigation, rust-commands, ipc]
dependency_graph:
  requires: ["32-02", "32-03"]
  provides: ["WKSP-04", "WKSP-02-reset"]
  affects: ["frontend/sidebar", "tauri-app/workspace-commands", "desktop-settings"]
tech_stack:
  added: []
  patterns:
    - "Tauri-only sidebar section via module-level isTauri() guard"
    - "Dedicated Rust reset command deletes Store key (vs empty-string sentinel anti-pattern)"
    - "IPC wrapper pattern: resetProjectsDir() in tauri.ts"
key_files:
  created:
    - frontend/src/app/(workspace)/[workspaceSlug]/local-repos/page.tsx
  modified:
    - frontend/src/components/layout/sidebar.tsx
    - tauri-app/src-tauri/src/commands/workspace.rs
    - tauri-app/src-tauri/src/lib.rs
    - frontend/src/lib/tauri.ts
    - frontend/src/features/settings/pages/desktop-settings-page.tsx
decisions:
  - "Dedicated reset_projects_dir Rust command deletes projects_dir Store key instead of overloading set_projects_dir with empty-string sentinel — cleaner semantics, no path validation on reset"
  - "desktopNavSection defined at module level using isTauri() — stable const, no React state/effect needed, consistent with settingsNavSections pattern"
metrics:
  duration_seconds: 228
  completed_date: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 5
---

# Phase 32 Plan 04: Gap Closure — Route + Sidebar + Reset Command Summary

**One-liner:** Wired orphaned ProjectDashboard into reachable /local-repos route with Tauri-only sidebar section, and replaced broken empty-string reset sentinel with dedicated `reset_projects_dir` Rust command.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire ProjectDashboard into route and sidebar (Tauri-only) | 93f9b04c | local-repos/page.tsx, sidebar.tsx |
| 2 | Fix "Reset to default" — add reset_projects_dir Rust command and rewire frontend | 7aeb793b | workspace.rs, lib.rs, tauri.ts, desktop-settings-page.tsx |

## What Was Built

### Task 1: ProjectDashboard Route + Sidebar Nav

**Route page** created at `frontend/src/app/(workspace)/[workspaceSlug]/local-repos/page.tsx`:
- Renders `<ProjectDashboard />` when `isTauri()` is true
- Shows a graceful fallback message in browser context
- `'use client'` directive for static export (NEXT_TAURI=true) compatibility

**Sidebar nav item** added in `sidebar.tsx`:
- Imported `HardDrive` from lucide-react and `isTauri` from `@/lib/tauri`
- Module-level `desktopNavSection` constant: evaluates `isTauri()` once at initialization
- `navigation` useMemo spread `desktopNavSection` into sections array when non-null
- Shows "Local Repos" under a "Desktop" nav section in the Tauri shell sidebar

### Task 2: Reset to Default Fix

**Problem:** `handleReset` in `desktop-settings-page.tsx` called `setProjectsDir('')` — Rust's `set_projects_dir` validates the path with `is_dir()`, so an empty string always returned an error.

**Fix:**
- Added `reset_projects_dir` Rust command in `workspace.rs`: calls `store.delete("projects_dir")` so `get_projects_dir` falls through to the `~/PilotSpace/projects/` default
- Registered `reset_projects_dir` in `generate_handler![]` in `lib.rs`
- Added `resetProjectsDir()` IPC wrapper in `frontend/src/lib/tauri.ts`
- Rewired `handleReset` in `desktop-settings-page.tsx` to call `resetProjectsDir()` instead of `setProjectsDir('')`

## Verification Results

| Check | Result |
|-------|--------|
| `tsc --noEmit` (frontend) | PASS — zero errors |
| `cargo check` (tauri-app) | PASS — zero errors |
| Route file exists | PASS |
| Sidebar has local-repos nav | PASS |
| reset uses dedicated command | PASS |
| No empty-string sentinel | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `frontend/src/app/(workspace)/[workspaceSlug]/local-repos/page.tsx` — FOUND
- `frontend/src/components/layout/sidebar.tsx` contains `local-repos` — FOUND
- `tauri-app/src-tauri/src/commands/workspace.rs` contains `reset_projects_dir` — FOUND
- `tauri-app/src-tauri/src/lib.rs` contains `reset_projects_dir` — FOUND
- `frontend/src/lib/tauri.ts` contains `resetProjectsDir` — FOUND
- `frontend/src/features/settings/pages/desktop-settings-page.tsx` contains `resetProjectsDir` — FOUND
- Commit `93f9b04c` — FOUND
- Commit `7aeb793b` — FOUND
