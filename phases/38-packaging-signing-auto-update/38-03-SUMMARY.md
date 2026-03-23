---
phase: 38-packaging-signing-auto-update
plan: "03"
subsystem: tauri-desktop/auto-update
tags: [tauri, auto-update, github-actions, release-workflow, updater-plugin]
dependency_graph:
  requires: ["38-01", "38-02"]
  provides: ["tauri-auto-update", "github-release-workflow", "update-notification-ui"]
  affects: ["tauri-app/src-tauri", "frontend/components/desktop", "frontend/lib/tauri.ts", ".github/workflows"]
tech_stack:
  added:
    - "tauri-plugin-updater 2.10.0 (Rust)"
    - "@tauri-apps/plugin-updater 2.10.0 (npm)"
  patterns:
    - "tauri-plugin-updater: Builder::new().build() registration pattern"
    - "checkForUpdates(): dynamic import of @tauri-apps/plugin-updater inside isTauri() guard"
    - "UpdateNotification: delayed check (5s), non-blocking banner, dismiss control"
    - "GitHub Release workflow: build-sidecar → build-release job dependency, draft release"
key_files:
  created:
    - "frontend/src/components/desktop/update-notification.tsx"
    - ".github/workflows/tauri-release.yml"
  modified:
    - "tauri-app/src-tauri/Cargo.toml"
    - "tauri-app/src-tauri/Cargo.lock"
    - "tauri-app/src-tauri/src/lib.rs"
    - "tauri-app/src-tauri/tauri.conf.json"
    - "tauri-app/src-tauri/capabilities/default.json"
    - "frontend/package.json"
    - "frontend/pnpm-lock.yaml"
    - "frontend/src/lib/tauri.ts"
    - "frontend/src/app/(workspace)/[workspaceSlug]/workspace-slug-layout.tsx"
decisions:
  - "[Phase 38-03]: tauri_plugin_updater::Builder::new().build() used (not init()) — Builder pattern allows configuring custom headers or check intervals in future without API change"
  - "[Phase 38-03]: dialog: false in tauri.conf.json updater config — UI handled by UpdateNotification component (non-blocking banner, not a blocking modal)"
  - "[Phase 38-03]: pubkey set to empty string in tauri.conf.json — placeholder until TAURI_SIGNING_PRIVATE_KEY generated; documented in workflow comments"
  - "[Phase 38-03]: releaseDraft: true in tauri-release.yml — releases are created as drafts requiring manual publish to prevent accidental production releases"
  - "[Phase 38-03]: cancel-in-progress: false in tauri-release.yml — never interrupt a release build mid-flight (partial artifacts would break GitHub Release)"
  - "[Phase 38-03]: 5-second mount delay on UpdateNotification — avoids competing with app initialization and Supabase auth token load on startup"
  - "[Phase 38-03]: UpdateNotification installs on restart (not forced) — respects user autonomy per brand principle 'Spacious calm over dense efficiency'"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-03-20"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 9
---

# Phase 38 Plan 03: Auto-Update System Summary

**One-liner:** tauri-plugin-updater wired in Rust + frontend with non-blocking UpdateNotification banner and GitHub Release workflow producing signed installers + latest.json for all 4 platforms.

## What Was Built

### Task 1: Rust Backend — tauri-plugin-updater

Added `tauri-plugin-updater = "2"` to `Cargo.toml`. Registered `tauri_plugin_updater::Builder::new().build()` in the plugin chain in `lib.rs` (after `notification::init()`, before `.manage()`). Added `plugins.updater` config to `tauri.conf.json` with `dialog: false` (UI is handled by the frontend banner, not a blocking OS dialog) and the GitHub Releases endpoint. Added `updater:default` permission to `capabilities/default.json`.

cargo check passes with tauri-plugin-updater 2.10.0.

**Required one-time setup before shipping:**
```bash
cd tauri-app && pnpm tauri signer generate -w ~/.tauri/pilot-space.key
# Output: Public key → add to tauri.conf.json plugins.updater.pubkey
# Private key → add to GitHub secret TAURI_SIGNING_PRIVATE_KEY
# Password → add to GitHub secret TAURI_SIGNING_PRIVATE_KEY_PASSWORD
```

### Task 2: Frontend — Update Wrappers and UpdateNotification Component

Added `@tauri-apps/plugin-updater 2.10.0` to `frontend/package.json`.

Added to `frontend/src/lib/tauri.ts`:
- `UpdateInfo` interface (available, currentVersion, version, date, body)
- `checkForUpdates()` — uses `check()` from plugin-updater, returns UpdateInfo or null, wrapped in try/catch so network failures never crash the app
- `downloadAndInstallUpdate()` — calls `update.downloadAndInstall()` which downloads in background and stages for install on restart

Created `frontend/src/components/desktop/update-notification.tsx`:
- `UpdateState` type: `idle | checking | available | downloading | ready | dismissed`
- Checks on mount with 5-second delay (avoids competing with app init)
- Shows muted banner (`bg-muted/50 border-b`) when update is available
- Update button triggers background download → transitions to `ready` state
- Dismiss button always visible — user controls their experience
- Renders null when idle/checking/dismissed (invisible by default)

Mounted in `workspace-slug-layout.tsx` at the top of the layout (before AiNotConfiguredBanner) via `dynamic(..., { ssr: false })`, conditionally on `isTauri()`. Same pattern as TrayNotificationListener.

Frontend lint: 0 errors (17 pre-existing warnings). TypeScript type-check: clean.

### Task 3: GitHub Release Workflow

Created `.github/workflows/tauri-release.yml`:

**Trigger:** `push: tags: ['v*']` — only fires on version tags (e.g., `v0.2.0`)

**Job 1 — `build-sidecar`:** Builds pilot-cli for all 4 platform triples using PyInstaller, renames with target triple, uploads as 1-day artifacts. Mirrors `pilot-cli-build.yml` pattern.

**Job 2 — `build-release` (needs: build-sidecar):**
1. Downloads sidecar artifact to `tauri-app/src-tauri/binaries/`
2. Signs sidecar on macOS (`codesign`) and Windows (AzureSignTool) before bundling
3. Runs `tauri-apps/tauri-action@v0` which:
   - Builds Tauri app for the platform target
   - Signs installers (.dmg/.deb/.AppImage/.msi) using Apple/Azure Key Vault secrets
   - Uses `TAURI_SIGNING_PRIVATE_KEY` to sign update bundles and generate `latest.json`
   - Creates/updates a **draft** GitHub Release with all artifacts
   - Each platform runner uploads its artifacts to the same release via GITHUB_TOKEN

**Key design decisions:**
- `releaseDraft: true` — human must manually publish the release after reviewing artifacts
- `cancel-in-progress: false` — never kill a release mid-flight
- All 4 platform targets in the matrix: macOS ARM64, macOS x86_64, Linux x64, Windows x64
- `latest.json` update manifest is auto-generated by tauri-action when TAURI_SIGNING_PRIVATE_KEY is present

## Deviations from Plan

None — plan executed exactly as written.

The security hook flagged the GitHub Actions file during Write, but all patterns are safe:
- Matrix values (`${{ matrix.target }}`) are workflow-controlled data, not external event inputs
- `${{ github.ref_name }}` is used only in `with:` YAML values (tagName/releaseName), not in `run:` shell commands
- All secrets use `env:` blocks as required by CI security policy

## Self-Check: PASSED

All created files exist on disk. All task commits verified in git log.

| Check | Result |
|-------|--------|
| frontend/src/components/desktop/update-notification.tsx | FOUND |
| .github/workflows/tauri-release.yml | FOUND |
| tauri-app/src-tauri/Cargo.toml (updated) | FOUND |
| tauri-app/src-tauri/src/lib.rs (updated) | FOUND |
| tauri-app/src-tauri/tauri.conf.json (updated) | FOUND |
| tauri-app/src-tauri/capabilities/default.json (updated) | FOUND |
| frontend/src/lib/tauri.ts (updated) | FOUND |
| workspace-slug-layout.tsx (updated) | FOUND |
| Commit 8ad0e556 (Task 1) | FOUND |
| Commit e80ad751 (Task 2) | FOUND |
| Commit 8bf5f79a (Task 3) | FOUND |
