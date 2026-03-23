---
phase: 38-packaging-signing-auto-update
plan: 01
subsystem: infra
tags: [tauri, macos, codesign, notarization, hardened-runtime, github-actions, ci, apple-developer, sidecar]

# Dependency graph
requires:
  - phase: 35-sidecar-cli-integration
    provides: pilot-cli sidecar binary built and placed at binaries/pilot-cli-{target}
  - phase: 30-tauri-scaffold
    provides: tauri-build.yml CI workflow with matrix runners

provides:
  - Entitlements.plist with hardened runtime entitlements for PyInstaller sidecar notarization
  - tauri.conf.json macOS bundle config with entitlements path, signingIdentity, minimumSystemVersion
  - All 6 APPLE_* signing secrets wired into tauri-action env block (active, not commented)
  - Conditional sidecar pre-signing step (macOS only, no-op when secrets absent)
  - Tag-based (v*) release trigger for CI builds

affects:
  - 38-02-windows-signing
  - 38-03-auto-update

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conditional sidecar signing: codesign step runs only when APPLE_SIGNING_IDENTITY env var is non-empty — safe for unsigned CI builds"
    - "Hardened runtime entitlements for PyInstaller: allow-unsigned-executable-memory + disable-library-validation required for onedir bundles"
    - "tauri-action auto-notarization: when APPLE_ID + APPLE_PASSWORD + APPLE_TEAM_ID are set, tauri-action invokes notarytool automatically"
    - "signingIdentity: null in tauri.conf.json means tauri-action reads APPLE_SIGNING_IDENTITY from environment"

key-files:
  created:
    - tauri-app/src-tauri/Entitlements.plist
  modified:
    - tauri-app/src-tauri/tauri.conf.json
    - .github/workflows/tauri-build.yml

key-decisions:
  - "allow-unsigned-executable-memory entitlement is required for PyInstaller sidecar: onedir mode loads Python bytecode dynamically at startup"
  - "disable-library-validation entitlement required: PyInstaller bundles dylibs that are not individually Apple-signed"
  - "signingIdentity set to null in tauri.conf.json — tauri-action reads APPLE_SIGNING_IDENTITY from env at build time; null means no hardcoded identity"
  - "Sidecar signing placed before tauri-action: sidecar must be signed individually before the app bundle is signed to satisfy notarization"
  - "timeout-minutes raised from 60 to 90: Apple notarization can take 30-60 minutes under load"
  - "Tag trigger v* added to push.branches list: enables release builds from version tags without separate release workflow"
  - "tauri-action handles notarization automatically: no manual xcrun notarytool submit step needed when APPLE_ID + APPLE_PASSWORD + APPLE_TEAM_ID are present"

patterns-established:
  - "Apple signing: never hardcode signing identity in tauri.conf.json — use null + APPLE_SIGNING_IDENTITY env var"
  - "Sidecar pre-signing: sign sidecar binary before tauri-action to satisfy macOS notarization requirement"
  - "Conditional CI secrets: use env.VAR != '' guard so unsigned builds work when secrets are absent"

requirements-completed: [PKG-01, PKG-04]

# Metrics
duration: 8min
completed: 2026-03-20
---

# Phase 38 Plan 01: macOS Code Signing and Notarization Summary

**Hardened runtime Entitlements.plist + tauri-action Apple secrets wired for signed + notarized .dmg production from ARM64 and Intel macOS runners**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-20T09:30:00Z
- **Completed:** 2026-03-20T09:38:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created Entitlements.plist with the three hardened runtime keys required for PyInstaller sidecar notarization: allow-unsigned-executable-memory, disable-library-validation, network.client
- Updated tauri.conf.json macOS bundle section with entitlements path, null signingIdentity (injected via env), and minimumSystemVersion 10.15 (Catalina)
- Wired all 6 APPLE_* secrets into tauri-action env block; sidecar pre-signing step added with conditional guard for unsigned CI builds
- Added v* tag push trigger and increased job timeout to 90 minutes for notarization headroom

## Task Commits

Each task was committed atomically:

1. **Task 1: Add macOS entitlements and update tauri.conf.json** - `71945895` (feat)
2. **Task 2: Wire Apple signing secrets and sidecar pre-signing** - `0e4319b4` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `tauri-app/src-tauri/Entitlements.plist` - Hardened runtime entitlements: allow-unsigned-executable-memory, disable-library-validation, network.client
- `tauri-app/src-tauri/tauri.conf.json` - macOS bundle: entitlements path, signingIdentity null, minimumSystemVersion 10.15
- `.github/workflows/tauri-build.yml` - All 6 APPLE_* secrets active, sidecar signing step, v* tag trigger, 90-min timeout

## Decisions Made
- `signingIdentity: null` in tauri.conf.json — tauri-action reads `APPLE_SIGNING_IDENTITY` from environment; null avoids hardcoding a team ID in source
- Sidecar signing step placed before tauri-action: sidecar binary must be individually codesigned before the enclosing app bundle is signed and submitted for notarization
- `if: runner.os == 'macOS' && env.APPLE_SIGNING_IDENTITY != ''` guard on sidecar step: unsigned CI builds (PRs, branches without secrets) work transparently
- Notarization delegated fully to tauri-action — when APPLE_ID + APPLE_PASSWORD + APPLE_TEAM_ID are set it invokes `xcrun notarytool` automatically; no manual submit step needed
- Minimum system version set to 10.15 (Catalina): earliest macOS that supports hardened runtime + notarization without special accommodations

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

**External services require manual configuration** — Apple Developer credentials must be added as GitHub repository secrets before macOS CI produces signed builds:

| Secret | Source |
|--------|--------|
| `APPLE_CERTIFICATE` | Base64-encoded .p12 exported from Keychain Access (Developer ID Application certificate) |
| `APPLE_CERTIFICATE_PASSWORD` | Password used when exporting the .p12 |
| `APPLE_SIGNING_IDENTITY` | Certificate common name, e.g. `Developer ID Application: Your Company (TEAMID)` |
| `APPLE_ID` | Apple ID email used for App Store Connect / notarytool |
| `APPLE_PASSWORD` | App-specific password from appleid.apple.com -> Sign-In and Security -> App-Specific Passwords |
| `APPLE_TEAM_ID` | 10-character Team ID from developer.apple.com -> Membership |

When secrets are absent, CI produces unsigned builds — backward compatible with Phase 30 behavior.

## Next Phase Readiness
- macOS signing config is complete and merged; Phase 38-02 can proceed with Windows EV certificate wiring independently
- Phase 38-03 (auto-update) depends on signed builds being available but does not depend on this plan's specific files
- Both macOS runners (macos-latest ARM64, macos-13 x86_64) will produce signed + notarized .dmg once Apple secrets are configured in GitHub repo settings

## Self-Check: PASSED

- FOUND: tauri-app/src-tauri/Entitlements.plist
- FOUND: tauri-app/src-tauri/tauri.conf.json
- FOUND: .github/workflows/tauri-build.yml
- FOUND: .planning/phases/38-packaging-signing-auto-update/38-01-SUMMARY.md
- FOUND commit: 71945895 (Task 1)
- FOUND commit: 0e4319b4 (Task 2)

---
*Phase: 38-packaging-signing-auto-update*
*Completed: 2026-03-20*
