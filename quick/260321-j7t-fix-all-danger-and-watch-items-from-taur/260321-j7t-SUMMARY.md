---
phase: quick-fix
plan: 01
subsystem: tauri-desktop
tags: [security, csp, updater, git, rust, typescript, unit-tests]
dependency_graph:
  requires: []
  provides: [hardened-tauri-config, dedup-project-store, deleted-file-staging, typed-update-cache, rust-unit-tests]
  affects: [tauri-app/src-tauri/tauri.conf.json, tauri-app/src-tauri/src/commands/workspace.rs, tauri-app/src-tauri/src/commands/git.rs, tauri-app/src-tauri/src/commands/terminal.rs, frontend/src/lib/tauri.ts]
tech_stack:
  added: [tempfile = "3" dev-dependency for Rust tests]
  patterns: [import type for compile-time-safe Tauri plugin typing, conditional add_path vs remove_path for git staging, position-based dedup for JSON arrays]
key_files:
  modified:
    - tauri-app/src-tauri/tauri.conf.json
    - tauri-app/src-tauri/src/commands/workspace.rs
    - tauri-app/src-tauri/src/commands/git.rs
    - tauri-app/src-tauri/src/commands/terminal.rs
    - tauri-app/src-tauri/Cargo.toml
    - frontend/src/lib/tauri.ts
decisions:
  - "Localhost CSP entries are harmless in production (no local server), but required for dev mode to reach backend:8000 and Supabase:18000"
  - "tempfile added as dev-dependency (not dependency) — only needed for Rust unit tests, never compiled into production binary"
  - "import type erases at compile time — correct pattern for typing Tauri plugin objects without SSG build failures"
metrics:
  duration_minutes: 3
  tasks_completed: 3
  files_modified: 6
  completed_date: "2026-03-21"
---

# Quick Fix 260321-j7t: Fix All DANGER and WATCH Items from Tauri Deep Context Report

**One-liner:** Resolved all security (CSP localhost), correctness (dedup project store, deleted-file staging), and code quality (typed update cache, Rust unit tests) issues in the Tauri desktop client.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix DANGER items in tauri.conf.json (CSP, updater URL) | cd56d08d | tauri.conf.json |
| 2 | Fix WATCH items in Rust commands (dedup, deleted staging) + unit tests | ad593284 | workspace.rs, git.rs, terminal.rs, Cargo.toml |
| 3 | Type cachedUpdateHandle in frontend tauri.ts | 9f3cfae8 | frontend/src/lib/tauri.ts |

## What Was Done

### Task 1: DANGER Items in tauri.conf.json

**CSP connect-src (DANGER-CSP):** Added `http://localhost:8000 ws://localhost:8000 http://localhost:18000 ws://localhost:18000` to the CSP `connect-src` directive. Dev mode was silently blocked from reaching the backend API (port 8000) and Supabase Kong gateway (port 18000). These entries are harmless in production — no local server exists to connect to.

**Updater endpoint (DANGER-UPDATER-URL):** Replaced `OWNER` placeholder with `pilotspace` (the real GitHub org). The app would have failed all update checks silently.

**Updater pubkey (DANGER-UPDATER-PUBKEY):** Acknowledged. The base64 value decodes to a placeholder comment. No code change — real key requires interactive TTY per Phase 39-01 decision.

### Task 2: WATCH Items in Rust Commands

**Deduplication in `append_project_to_store` (WATCH-DEDUP):** Added `iter().position()` check before pushing to the projects array. If a project with the same `path` already exists, its entry is updated in-place. Prevents duplicate entries when re-cloning or re-linking the same repo.

**Deleted file staging in `git_stage` (WATCH-STAGE-DELETE):** The original code called `index.add_path()` unconditionally, which fails for files that no longer exist on disk. Fixed by checking `abs.exists()` — uses `index.remove_path()` for deleted files and `index.add_path()` for existing files.

**Rust unit tests (WATCH-RUST-TESTS):**
- `workspace.rs`: 3 tests for `extract_remote_url` (found URL, no origin section, missing .git/config)
- `terminal.rs`: 2 tests for `detect_default_shell` (SHELL env var, fallback to /bin/bash)
- `git.rs`: No pure testable functions without a full Repository fixture — skipped per plan
- Added `tempfile = "3"` as dev-dependency for creating temp dirs in tests

### Task 3: Typed Update Cache (WATCH-TYPED-CACHE)

Replaced `any` type on `cachedUpdateHandle` with `Update | null` using `import type { Update } from '@tauri-apps/plugin-updater'` at the top of `tauri.ts`. `import type` is erased at compile time — does not cause SSG build failures. Also typed the local `update` variable in `downloadAndInstallUpdate` and removed the `eslint-disable-next-line` comment.

## Verification Results

- `cargo check`: Passes, no errors
- `cargo test -- --test-threads=1`: 5 tests pass (0 failed)
- `pnpm type-check`: Passes, no errors
- CSP contains `localhost:8000` and `localhost:18000`: Confirmed
- Updater endpoint uses `pilotspace` org: Confirmed
- `position` dedup logic in workspace.rs: Confirmed
- `remove_path` for deleted files in git.rs: Confirmed

## Deviations from Plan

**1. [Rule 3 - Blocking] Added tempfile dev-dependency**
- **Found during:** Task 2 (unit tests for extract_remote_url)
- **Issue:** `extract_remote_url` tests require creating temp directories with `.git/config` files. `tempfile` crate was not in Cargo.toml.
- **Fix:** Added `tempfile = "3"` under `[dev-dependencies]` in Cargo.toml — dev-only, not compiled into production binary.
- **Files modified:** tauri-app/src-tauri/Cargo.toml
- **Commit:** ad593284

## Self-Check: PASSED

All modified files confirmed present on disk. All 3 task commits confirmed in git log.
