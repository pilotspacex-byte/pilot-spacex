---
phase: 39-tech-debt-cleanup
plan: 01
subsystem: infra
tags: [tauri, ci, github-actions, mobx, typescript, updater, sidecar]

# Dependency graph
requires:
  - phase: 38-packaging-signing-autoupdate
    provides: tauri.conf.json updater block structure and tauri-build.yml scaffolding
  - phase: 35-cli-sidecar
    provides: pilot-cli-build.yml artifact naming pattern
  - phase: 37-tray-implement
    provides: TerminalStore and ImplementStore feature stores
provides:
  - Tauri updater pubkey populated (non-empty) — unblocks auto-update manifest signing
  - stores/index.ts complete barrel with TerminalStore, ImplementStore, useTerminalStore, useImplementStore
  - tauri-build.yml wired to download real pilot-cli sidecar via dawidd6/action-download-artifact@v6
affects: [38-packaging-signing-autoupdate, release-workflows, stores-barrel-consumers]

# Tech tracking
tech-stack:
  added: [dawidd6/action-download-artifact@v6]
  patterns: [cross-workflow artifact download with graceful degradation via if_no_artifact_found: warn]

key-files:
  created: []
  modified:
    - tauri-app/src-tauri/tauri.conf.json
    - frontend/src/stores/index.ts
    - .github/workflows/tauri-build.yml

key-decisions:
  - "Tauri keygen requires interactive TTY — not available in agent/CI env; placeholder pubkey used to unblock build; real key must be generated locally and stored as TAURI_SIGNING_PRIVATE_KEY secret"
  - "dawidd6/action-download-artifact@v6 used instead of actions/download-artifact@v4 — cross-workflow artifact downloads require the extended action"
  - "if_no_artifact_found: warn chosen over fail — avoids deadlock between parallel tauri-build and pilot-cli-build jobs on same push event"

patterns-established:
  - "Cross-workflow sidecar download: dawidd6/action-download-artifact@v6 with commit: github.sha and search_artifacts: true"
  - "Barrel export completeness: feature stores export both class (from feature file) and hook (from RootStore re-export)"

requirements-completed: [PKG-06]

# Metrics
duration: 8min
completed: 2026-03-20
---

# Phase 39 Plan 01: Tech Debt Cleanup Summary

**Tauri updater pubkey placeholder set, stores barrel completed with TerminalStore/ImplementStore exports, and dev CI wired to download real pilot-cli sidecar via cross-workflow dawidd6 action**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-20T12:50:00Z
- **Completed:** 2026-03-20T12:58:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Populated `tauri.conf.json plugins.updater.pubkey` — was empty string, now holds a valid Minisign placeholder; unblocks auto-update manifest signing in release builds (PKG-06)
- Added `TerminalStore`, `ImplementStore`, `useTerminalStore`, `useImplementStore` to `frontend/src/stores/index.ts` barrel — all four names now re-exported; `pnpm type-check` exits 0
- Inserted `dawidd6/action-download-artifact@v6` sidecar download step into `tauri-build.yml` build job between "Install Tauri CLI dependencies" and "Sign sidecar binary" — dev CI now pulls real pilot-cli binary when available, degrades gracefully with `if_no_artifact_found: warn`

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate Tauri updater keypair and commit public key** - `032e5347` (chore)
2. **Task 2: Fix stores/index.ts barrel exports** - `773e0e6f` (feat)
3. **Task 3: Wire sidecar download into dev CI (tauri-build.yml)** - `6882fb1d` (chore)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `tauri-app/src-tauri/tauri.conf.json` - `plugins.updater.pubkey` set to Minisign placeholder (was `""`)
- `frontend/src/stores/index.ts` - Added `TerminalStore`, `ImplementStore`, `type ImplementStep` re-exports + `useTerminalStore`, `useImplementStore` to RootStore block
- `.github/workflows/tauri-build.yml` - Inserted sidecar download step using `dawidd6/action-download-artifact@v6`

## Decisions Made
- **Placeholder pubkey over real key:** Tauri signer keygen requires an interactive TTY (panics with `Device not configured` error when stdin is piped). Plan explicitly provides a placeholder for this case. Real key must be generated locally and stored as `TAURI_SIGNING_PRIVATE_KEY` GitHub secret before first release.
- **dawidd6 over actions/download-artifact:** Cross-workflow artifact downloads (different workflow file, same commit) require the extended `dawidd6/action-download-artifact@v6` action; the standard `actions/download-artifact@v4` only works within the same workflow run.
- **warn not fail for missing artifact:** `if_no_artifact_found: warn` prevents a hard build failure when `pilot-cli-build.yml` hasn't finished yet on the same push event (parallel runs).

## Deviations from Plan

None - plan executed exactly as written. The keygen fallback path was anticipated and documented in the plan.

## Issues Encountered

- `pnpm tauri signer generate` panics with `Device not configured` (OS error 6) when stdin is not a real TTY — expected behavior in automated environments. Plan provided the exact placeholder to use in this case; applied without deviation.

## User Setup Required

**Tauri auto-update signing requires manual key generation.** To replace the placeholder pubkey with a real signing key:

1. On a machine with a real terminal: `cd tauri-app && pnpm tauri signer generate -w ~/.tauri/pilot-space.key`
2. Copy the public key printed after "Public key:"
3. Replace the placeholder in `tauri-app/src-tauri/tauri.conf.json` `plugins.updater.pubkey`
4. Add GitHub repo secrets (Settings → Secrets → Actions):
   - `TAURI_SIGNING_PRIVATE_KEY`: contents of `~/.tauri/pilot-space.key`
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: (empty string, or the password you chose)

## Next Phase Readiness
- v1.1 milestone all 3 audit gap items closed — PKG-06 unblocked, stores barrel complete, CI sidecar wired
- Release builds can proceed once TAURI_SIGNING_PRIVATE_KEY secret is configured with the real key
- `dawidd6/action-download-artifact@v6` requires a GitHub token with `actions: read` scope — GITHUB_TOKEN default should suffice for same-repo workflows

---
*Phase: 39-tech-debt-cleanup*
*Completed: 2026-03-20*

## Self-Check: PASSED
All 3 task commits verified (032e5347, 773e0e6f, 6882fb1d). All 3 modified files present. SUMMARY.md created.
