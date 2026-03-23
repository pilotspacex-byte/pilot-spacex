---
phase: 34-embedded-terminal
plan: "01"
subsystem: tauri-pty-backend
tags: [rust, pty, terminal, ipc, portable-pty, typescript, tauri]
dependency_graph:
  requires: []
  provides: [PTY-session-lifecycle, terminal-ipc-channel, terminal-ts-wrappers]
  affects: [tauri-app/src-tauri, frontend/src/lib/tauri.ts]
tech_stack:
  added: [portable-pty@0.9, uuid@1]
  patterns: [Channel-streaming, batched-output-16ms, Arc-Mutex-writer-sharing, std-thread-blocking-io]
key_files:
  created:
    - tauri-app/src-tauri/src/commands/terminal.rs
  modified:
    - tauri-app/src-tauri/Cargo.toml
    - tauri-app/src-tauri/src/commands/mod.rs
    - tauri-app/src-tauri/src/lib.rs
    - frontend/src/lib/tauri.ts
decisions:
  - "portable-pty@0.9 chosen over tauri-plugin-pty — gives direct control over PTY lifecycle without plugin abstraction; tauri-pty crate does not exist as named"
  - "std::thread::spawn (not tokio::spawn) for PTY reader — blocking I/O requires OS thread, not async task"
  - "Arc<Mutex<Box<dyn Write>>> for PTY writer — enables concurrent write_terminal calls alongside the reader thread"
  - "16ms flush interval via Instant::elapsed — avoids per-byte IPC events (Pitfall 7 / issues #12724, #13133)"
  - "Mutex<HashMap> (not RwLock) for TerminalSessions — write operations (every keystroke) are frequent, RwLock gains nothing"
metrics:
  duration_seconds: 218
  completed_date: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 4
---

# Phase 34 Plan 01: PTY Backend with Batched Output Streaming Summary

PTY backend using `portable-pty` with 16ms-batched Channel streaming and typed TypeScript wrappers for create/write/resize/close session lifecycle.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add PTY backend (terminal.rs + Cargo deps + lib.rs wiring) | f52a6179 | Cargo.toml, terminal.rs, mod.rs, lib.rs |
| 2 | Add typed TypeScript IPC wrappers | 476efd20 | frontend/src/lib/tauri.ts |

## What Was Built

### Rust PTY Backend (`terminal.rs`)

Four `#[tauri::command]` functions managing PTY session lifecycle:

- **`create_terminal(rows, cols, on_output)`** — opens a native PTY pair via `portable_pty::native_pty_system()`, spawns the user's default shell (`$SHELL` / `%COMSPEC%`), spawns a `std::thread` reader that accumulates output and flushes to the `Channel<TerminalOutput>` every 16ms, stores the session in `TerminalSessions`.
- **`write_terminal(session_id, data)`** — writes raw bytes to the PTY writer via `Arc<Mutex<Box<dyn Write>>>`.
- **`resize_terminal(session_id, rows, cols)`** — calls `master.resize(PtySize { rows, cols })` which sends SIGWINCH.
- **`close_terminal(session_id)`** — removes session from HashMap, calls `child.kill()`, drops PTY master (EOF → reader thread exits). Idempotent.

### TypeScript IPC Wrappers (`tauri.ts`)

Five additions to the existing typed wrapper module:
- `TerminalOutput` and `TerminalSessionInfo` interfaces
- `createTerminal(rows, cols, onOutput)` — creates `Channel<TerminalOutput>`, wires `onmessage`, calls `invoke('create_terminal', ...)`
- `writeTerminal(sessionId, data)` — no-op when not in Tauri (graceful browser fallback)
- `resizeTerminal(sessionId, rows, cols)` — no-op when not in Tauri
- `closeTerminal(sessionId)` — no-op when not in Tauri

## Verification

- `cargo check` passes in `tauri-app/src-tauri/` — zero errors, zero warnings
- `tsc --noEmit` passes in `frontend/` — zero errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] tauri-pty crate name correction**
- **Found during:** Task 1 dependency resolution
- **Issue:** Plan specified `tauri-pty = "0.1"` but no such crate exists on crates.io. `tauri-plugin-pty = "0.2.1"` exists but is a full Tauri plugin (different architecture).
- **Fix:** Used `portable-pty = "0.9"` (the plan's documented fallback) — provides the same `CommandBuilder`, `PtySize`, `native_pty_system()`, `MasterPty`, `Child` API the plan described.
- **Files modified:** `Cargo.toml`
- **Commit:** f52a6179

**2. [Rule 3 - Blocking] Prettier reformatted resizeTerminal signature**
- **Found during:** Task 2 commit (pre-commit hook)
- **Issue:** Multi-line function signature for `resizeTerminal` was collapsed to single line by prettier
- **Fix:** Re-staged the prettified file and committed cleanly
- **Files modified:** `frontend/src/lib/tauri.ts`
- **Commit:** 476efd20

## Self-Check: PASSED

Files verified:
- `tauri-app/src-tauri/src/commands/terminal.rs` — exists, contains all 4 commands
- `tauri-app/src-tauri/Cargo.toml` — contains portable-pty, uuid deps
- `tauri-app/src-tauri/src/commands/mod.rs` — contains `pub mod terminal`
- `tauri-app/src-tauri/src/lib.rs` — contains TerminalSessions::new() + all 4 commands in handler
- `frontend/src/lib/tauri.ts` — contains all 4 wrappers + 2 interfaces

Commits verified:
- f52a6179 — exists in log
- 476efd20 — exists in log
