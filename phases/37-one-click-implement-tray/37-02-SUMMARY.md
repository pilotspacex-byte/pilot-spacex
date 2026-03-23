---
phase: 37-one-click-implement-tray
plan: "02"
subsystem: tauri-desktop
tags: [tauri, system-tray, notifications, rust, frontend]
dependency_graph:
  requires: [37-01]
  provides: [system-tray-icon, minimize-to-tray, native-os-notifications, send-notification-ipc]
  affects: [tauri-app/src-tauri, frontend/src/lib/tauri.ts, frontend/src/components/desktop, frontend/src/app/(workspace)]
tech_stack:
  added:
    - tauri-plugin-notification = "2" (native OS notifications)
    - tauri feature: tray-icon
  patterns:
    - TrayIconBuilder with on_tray_icon_event + on_menu_event
    - CloseRequested WindowEvent interception (prevent_close + hide)
    - NotificationExt::notification().builder().show() pattern
    - next/dynamic with ssr:false for Tauri-only DOM listeners
key_files:
  created:
    - tauri-app/src-tauri/src/commands/tray.rs
    - frontend/src/components/desktop/tray-notification-listener.tsx
  modified:
    - tauri-app/src-tauri/Cargo.toml
    - tauri-app/src-tauri/src/commands/mod.rs
    - tauri-app/src-tauri/src/lib.rs
    - tauri-app/src-tauri/capabilities/default.json
    - tauri-app/src-tauri/tauri.conf.json
    - frontend/src/lib/tauri.ts
    - frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx
decisions:
  - "[Phase 37-02]: show_menu_on_left_click(false) used instead of deprecated menu_on_left_click — left click shows window directly, right click shows context menu"
  - "[Phase 37-02]: TrayNotificationListener is NOT observer() — no MobX observables consumed; plain useEffect with DOM event listener is sufficient"
  - "[Phase 37-02]: TrayNotificationListener mounted in workspace-slug-layout (persistent across navigation) via dynamic import ssr:false — avoids SSG build errors"
  - "[Phase 37-02]: sendNotification in tauri.ts uses lazy dynamic import of @tauri-apps/api/core — consistent with all other IPC wrappers in the file"
  - "[Phase 37-02]: Task 2 frontend work (sendNotification, TrayNotificationListener) was pre-committed by Plan 37-01 executor as Rule 2 auto-fix — Task 2 verification confirmed completeness"
metrics:
  duration_minutes: 5
  completed_date: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 7
---

# Phase 37 Plan 02: System Tray + Native OS Notifications Summary

**One-liner:** System tray with minimize-to-tray, Show/Quit context menu, and native OS notifications via tauri-plugin-notification wired to the implement-complete CustomEvent.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Rust tray module + notification plugin + lib.rs wiring | 4f6236e2 | Cargo.toml, tray.rs, mod.rs, lib.rs, capabilities/default.json, tauri.conf.json |
| 2 | Frontend sendNotification wrapper + TrayNotificationListener | af0ac7f4 | tauri.ts, tray-notification-listener.tsx, workspace-slug-layout.tsx |

## What Was Built

### Rust layer (Task 1)

**`commands/tray.rs`** — Three exported symbols:

- `setup_tray(app)` — Builds a `TrayIconBuilder` with the app's default icon, tooltip "Pilot Space", and a context menu with "Show Window" and "Quit" items. Left-click on the tray icon shows+focuses the main window directly (using `show_menu_on_left_click(false)`). Menu events route to `show` (show+focus window) and `quit` (`app.exit(0)`).

- `setup_close_to_tray(app)` — Intercepts `WindowEvent::CloseRequested` on the main window, calls `api.prevent_close()`, and hides the window to the tray. Makes the window close button minimize rather than quit.

- `send_notification(app, title, body)` — `#[tauri::command]` that uses `NotificationExt::notification().builder().title().body().show()` to fire a native OS notification.

**`lib.rs` wiring:**
- `.plugin(tauri_plugin_notification::init())` registered in plugin chain
- `.setup(|app| { setup_tray(app.handle())?; setup_close_to_tray(app.handle()); Ok(()) })` called before invoke_handler
- `commands::tray::send_notification` added to `generate_handler![]`

**`capabilities/default.json`:** Added `notification:default`, `notification:allow-is-permission-granted`, `notification:allow-request-permission`, `notification:allow-notify`

**`tauri.conf.json`:** Added `"trayIcon": { "iconPath": "icons/32x32.png", "iconAsTemplate": true }` for macOS menu bar mask icon support

### Frontend layer (Task 2)

**`frontend/src/lib/tauri.ts`** — Added `sendNotification(title, body)` async wrapper. No-op outside Tauri. Uses lazy `import('@tauri-apps/api/core')` consistent with all IPC wrappers.

**`frontend/src/components/desktop/tray-notification-listener.tsx`** — `TrayNotificationListener` plain React component (not observer). `useEffect` with `[]` deps: registers `implement-complete` DOM event listener, fires `sendNotification` with success/failure message on event, cleans up on unmount. Returns null.

**`workspace-slug-layout.tsx`** — `TrayNotificationListener` added via `dynamic()` with `ssr: false`, rendered as `{isTauri() && <TrayNotificationListener />}` alongside the existing `TerminalPanel`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Deprecated `menu_on_left_click` API**
- **Found during:** Task 1 (cargo check warning)
- **Issue:** `TrayIconBuilder::menu_on_left_click` is deprecated in the installed version of tauri (2.10.3); the current API is `show_menu_on_left_click`
- **Fix:** Changed to `.show_menu_on_left_click(false)` — same semantics, no warnings
- **Files modified:** `tauri-app/src-tauri/src/commands/tray.rs`
- **Commit:** 4f6236e2

### Pre-completed Work

Task 2 frontend files (`sendNotification`, `TrayNotificationListener`, `workspace-slug-layout.tsx` mount) were implemented by the Plan 37-01 executor as a Rule 2 auto-fix ("missing critical functionality" — the notification chain was incomplete without the frontend side). All acceptance criteria verified present and correct in commit `af0ac7f4`.

## Verification Results

- `cargo check` — Passed, 0 warnings
- `npx tsc --noEmit` — Passed, 0 errors
- `pnpm lint` — Passed, 0 errors (17 pre-existing warnings in unrelated files)
- All 11 acceptance criteria for Task 1: PASS
- All 5 acceptance criteria for Task 2: PASS

## Self-Check: PASSED

Files created/modified:
- `tauri-app/src-tauri/src/commands/tray.rs` — FOUND
- `frontend/src/components/desktop/tray-notification-listener.tsx` — FOUND
- `frontend/src/lib/tauri.ts` (sendNotification added) — FOUND
- `frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx` (TrayNotificationListener mounted) — FOUND

Commits:
- `4f6236e2` — feat(37-02): Rust tray module + notification plugin + lib.rs wiring — FOUND
- `af0ac7f4` — feat(37-01): ImplementIssueButton (contains Task 2 work as pre-fix) — FOUND
