---
phase: 35-pilot-cli-sidecar
plan: "02"
subsystem: infra
tags: [tauri, rust, sidecar, ipc, channel, streaming, typescript, pilot-cli]

# Dependency graph
requires:
  - phase: 35-01
    provides: Compiled pilot-cli PyInstaller binary placed in tauri-app/src-tauri/binaries/
provides:
  - Tauri externalBin config pointing to binaries/pilot-cli
  - Rust sidecar.rs module with run_sidecar + cancel_sidecar IPC commands
  - SidecarProcesses managed state for lifecycle tracking and cancellation
  - TypeScript runSidecar + cancelSidecar wrappers with Channel streaming
affects:
  - 37-implement-flow (one-click implement invokes run_sidecar)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - tauri-plugin-shell ShellExt.sidecar() for externalBin process spawn
    - Channel<T> streaming for real-time stdout/stderr from long-running sidecar
    - Mutex<HashMap<id, Child>> managed state for multi-process lifecycle tracking
    - isTauri() guard + dynamic import pattern for TypeScript IPC wrappers

key-files:
  created:
    - tauri-app/src-tauri/src/commands/sidecar.rs
  modified:
    - tauri-app/src-tauri/tauri.conf.json
    - tauri-app/src-tauri/capabilities/default.json
    - tauri-app/src-tauri/src/commands/mod.rs
    - tauri-app/src-tauri/src/lib.rs
    - frontend/src/lib/tauri.ts

key-decisions:
  - "Stub binary (empty file) placed in binaries/ for local cargo check — gitignored, real binary produced by CI (35-01)"
  - "shell:allow-execute + shell:allow-spawn both required in capabilities — sidecar spawn fails without both permissions"
  - "on_output channel param uses snake_case in Tauri IPC invoke payload — Rust serde deserializes camelCase-to-snake_case automatically"
  - "cwd passed as null (not undefined) for Option<String> None mapping — undefined serializes incorrectly in Tauri IPC"

patterns-established:
  - "SidecarProcesses pattern: Mutex<HashMap<String, SidecarChild>> for multi-process tracking with idempotent cancel"
  - "CommandEvent match pattern: Stdout/Stderr bytes converted via from_utf8_lossy, Error forwarded to stderr stream, Terminated captures exit code"

requirements-completed: [CLI-01]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 35 Plan 02: Pilot CLI Sidecar IPC Summary

**Tauri externalBin wiring for pilot-cli sidecar with streaming Channel IPC and TypeScript wrappers — run_sidecar spawns process, streams stdout/stderr, cancel_sidecar kills by ID**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T07:53:26Z
- **Completed:** 2026-03-20T07:57:47Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Configured `bundle.externalBin` in tauri.conf.json to declare `binaries/pilot-cli` as Tauri-managed sidecar
- Created `sidecar.rs` with `run_sidecar` (spawn + Channel streaming + exit code) and `cancel_sidecar` (idempotent kill)
- Added `SidecarProcesses` managed state to lib.rs for multi-process lifecycle tracking
- Added `shell:allow-execute` and `shell:allow-spawn` permissions to capabilities/default.json
- Exported `runSidecar` and `cancelSidecar` TypeScript wrappers following established isTauri + Channel pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Configure Tauri externalBin and create sidecar.rs Rust module** - `71c9f5d0` (feat)
2. **Task 2: Add TypeScript IPC wrappers for sidecar commands** - `1ed7c179` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `tauri-app/src-tauri/src/commands/sidecar.rs` - Rust sidecar module: SidecarOutput, SidecarResult structs; run_sidecar command with Channel streaming; cancel_sidecar command with idempotent kill; SidecarProcesses managed state
- `tauri-app/src-tauri/tauri.conf.json` - Added `bundle.externalBin: ["binaries/pilot-cli"]`
- `tauri-app/src-tauri/capabilities/default.json` - Added `shell:allow-execute` and `shell:allow-spawn` permissions
- `tauri-app/src-tauri/src/commands/mod.rs` - Added `pub mod sidecar`
- `tauri-app/src-tauri/src/lib.rs` - Added `.manage(SidecarProcesses::new())` and both commands to `generate_handler!`
- `frontend/src/lib/tauri.ts` - Added `SidecarOutput`, `SidecarResult` interfaces; `runSidecar` and `cancelSidecar` functions

## Decisions Made
- **Stub binary for cargo check:** Tauri's build.rs validates externalBin path at compile time. Created an empty `binaries/pilot-cli-aarch64-apple-darwin` stub (gitignored via pre-existing rule) so `cargo check` passes locally. Real binary produced by CI 35-01 workflow.
- **Both shell permissions required:** `shell:allow-execute` alone is insufficient; `shell:allow-spawn` is also needed for sidecar spawn to succeed.
- **snake_case in invoke payload:** Tauri IPC deserializes payload keys as snake_case on the Rust side. The `on_output` channel parameter must be passed as `on_output` (not `onOutput`) in the TypeScript invoke call.
- **null vs undefined for Option<String>:** `cwd ?? null` ensures the Rust `Option<String>` receives `None` when cwd is not provided. Passing `undefined` causes Tauri IPC serialization issues.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `tauri::Manager` import and unnecessary `mut` binding**
- **Found during:** Task 1 (cargo check)
- **Issue:** `use tauri::Manager` was unused (ShellExt comes from tauri_plugin_shell directly), and `mut child` in cancel_sidecar was flagged as unnecessary since `kill()` takes `&mut self` internally
- **Fix:** Removed `use tauri::Manager` import; changed `mut child` to `child` in cancel_sidecar (compiler accepted it, kill() works via method receiver)
- **Files modified:** tauri-app/src-tauri/src/commands/sidecar.rs
- **Verification:** cargo check passes with zero warnings
- **Committed in:** 71c9f5d0 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - cleanup)
**Impact on plan:** Minor cleanup, no scope creep. Plan executed correctly.

## Issues Encountered
- Tauri build script validates externalBin binary existence at compile time (not just warning — hard error). Required creating a local stub binary to unblock cargo check. This was anticipated in plan acceptance criteria ("may warn about missing binary") but actual behavior is a build error. Resolved via gitignored stub binary.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 37 (one-click implement flow) can now call `runSidecar(["implement", issueId, "--oneshot"], repoPath, onOutput)` to stream pilot-cli output to UI
- `cancelSidecar(id)` available for abort button implementation
- Both Rust and TypeScript layers type-checked and committed

## Self-Check: PASSED

All 6 key files found on disk. Both task commits (71c9f5d0, 1ed7c179) verified in git log.

---
*Phase: 35-pilot-cli-sidecar*
*Completed: 2026-03-20*
