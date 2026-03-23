---
phase: 38-packaging-signing-auto-update
plan: 02
subsystem: infra
tags: [tauri, windows, codesign, ev-certificate, azure-key-vault, azuresigntool, linux, deb, appimage, msi, github-actions, ci, wix]

# Dependency graph
requires:
  - phase: 38-01-macos-signing
    provides: tauri-build.yml with APPLE_* secrets and sidecar pre-signing step

provides:
  - Explicit bundle targets array ["dmg", "deb", "appimage", "msi"] in tauri.conf.json
  - Windows bundle section with sha256 digest, DigiCert timestamp, downloadBootstrapper WebView2
  - AzureSignTool install step for Windows CI runner
  - 5 AZURE_KEY_VAULT_* secrets wired into tauri-action env block
  - Conditional Windows sidecar signing step (AzureSignTool, no-op when secrets absent)
  - All 4 platform runners producing correct installer artifacts

affects:
  - 38-03-auto-update

# Tech tracking
tech-stack:
  added:
    - "AzureSignTool (dotnet global tool) — signs PE binaries and .msi using Azure Key Vault EV certificate"
  patterns:
    - "Windows EV signing: AzureSignTool reads AZURE_KEY_VAULT_* env vars; tauri-action also reads same vars for .msi signing"
    - "Conditional Windows signing: if: runner.os == 'Windows' && env.AZURE_KEY_VAULT_URI != '' — unsigned builds still work"
    - "WebView2 downloadBootstrapper: minimal .msi size, bootstrapper fetches WebView2 runtime on first install"
    - "certificateThumbprint: null in tauri.conf.json — tauri-action uses Azure Key Vault env vars, no local thumbprint"
    - "Sidecar pre-signing for Windows: AzureSignTool signs pilot-cli-.exe before tauri-action bundles .msi"

key-files:
  created: []
  modified:
    - tauri-app/src-tauri/tauri.conf.json
    - .github/workflows/tauri-build.yml

key-decisions:
  - "bundle.targets changed from 'all' to ['dmg', 'deb', 'appimage', 'msi'] — precise control over installer formats; avoids building .rpm, .nsis, .app unnecessarily"
  - "certificateThumbprint: null in tauri.conf.json — tauri-action reads AZURE_KEY_VAULT_* from environment at build time; avoids hardcoding certificate identity in source"
  - "AzureSignTool installed via dotnet global tool install — standard cross-platform method supported by tauri-action"
  - "Windows sidecar signing placed before tauri-action: .exe must be individually signed before being bundled into .msi"
  - "WebView2 downloadBootstrapper chosen over embedBootstrapper/offlineInstaller — keeps .msi small; WebView2 is pre-installed on Windows 11 and most Windows 10 builds"
  - "DigiCert timestamp server (timestamp.digicert.com) used — widely trusted, free for timestamping, same as macOS plan"
  - "Signing conditional on AZURE_KEY_VAULT_URI env var presence — builds without secrets produce unsigned .msi (development/PR builds)"

patterns-established:
  - "Azure Key Vault signing: never hardcode certificate thumbprint — use null + env vars pattern mirrors macOS signingIdentity: null"
  - "Platform-specific signing: runner.os == 'Windows' guard mirrors runner.os == 'macOS' pattern from Plan 01"
  - "Sidecar pre-signing: same pattern as macOS — sign sidecar before tauri-action to satisfy code signing chain"

requirements-completed: [PKG-02, PKG-03, PKG-05]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 38 Plan 02: Linux/Windows Packaging and Windows EV Signing Summary

**Windows .msi with Azure Key Vault EV signing, Linux .deb/.AppImage targets, and AzureSignTool sidecar pre-signing wired into the 4-runner CI matrix**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-20T09:37:59Z
- **Completed:** 2026-03-20T09:40:31Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Updated bundle targets from "all" to explicit ["dmg", "deb", "appimage", "msi"] — each platform runner now builds exactly the right installer format
- Added Windows bundle section to tauri.conf.json with EV signing config: sha256 digest, DigiCert timestamp server, downloadBootstrapper WebView2 mode
- Wired 5 AZURE_KEY_VAULT_* secrets to tauri-action env block and added AzureSignTool global install step for the Windows CI runner
- Added conditional Windows sidecar pre-signing step using AzureSignTool (mirrors macOS codesign pattern from Plan 01)

## Task Commits

Each task was committed atomically:

1. **Task 1: Configure Windows signing and update tauri.conf.json bundle targets** - `415c448b` (feat)
2. **Task 2: Wire Windows EV signing secrets and Linux deps into CI workflow** - `bedf64bd` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `tauri-app/src-tauri/tauri.conf.json` - Explicit targets array, bundle.windows section (sha256 digest, DigiCert timestamp, downloadBootstrapper WebView2, certificateThumbprint: null)
- `.github/workflows/tauri-build.yml` - AzureSignTool install step, Windows sidecar signing step, 5 AZURE_KEY_VAULT_* env vars in tauri-action

## Decisions Made
- `bundle.targets` changed from `"all"` to `["dmg", "deb", "appimage", "msi"]`: explicit list prevents building unnecessary formats (.rpm, .nsis, .app) and documents intent clearly
- `certificateThumbprint: null` in tauri.conf.json mirrors the macOS `signingIdentity: null` pattern — Azure env vars are injected at CI build time
- `webviewInstallMode.downloadBootstrapper` chosen: keeps .msi small, WebView2 runtime is pre-installed on most modern Windows machines
- AzureSignTool sidecar signing placed before tauri-action: the signed .exe must exist before tauri-action bundles it into .msi to maintain signing chain integrity
- Signing conditioned on `env.AZURE_KEY_VAULT_URI != ''`: PR/branch builds without secrets produce unsigned installers — fully backward compatible

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

**External services require manual configuration** — Azure Key Vault EV certificate secrets must be added as GitHub repository secrets before Windows CI produces signed builds:

| Secret | Source |
|--------|--------|
| `AZURE_KEY_VAULT_URI` | Azure Portal -> Key Vault -> Overview -> Vault URI |
| `AZURE_KEY_VAULT_CLIENT_ID` | Azure Portal -> App registrations -> Application (client) ID of the service principal with Key Vault Crypto User role |
| `AZURE_KEY_VAULT_CLIENT_SECRET` | Azure Portal -> App registrations -> Certificates & secrets -> New client secret |
| `AZURE_KEY_VAULT_TENANT_ID` | Azure Portal -> Microsoft Entra ID -> Overview -> Tenant ID |
| `AZURE_KEY_VAULT_CERT_NAME` | Azure Portal -> Key Vault -> Certificates -> Name of the EV code signing certificate |

**Dashboard configuration required:**
- Import EV certificate into Azure Key Vault: Azure Portal -> Key Vault -> Certificates -> Generate/Import
- Grant service principal signing access: Azure Portal -> Key Vault -> Access policies -> Add (Key: Sign, Certificate: Get)

When secrets are absent, CI produces unsigned .msi builds — backward compatible with Phase 30 behavior.

## Next Phase Readiness
- Windows signing config is complete; Phase 38-03 (auto-update) can proceed with Tauri updater plugin configuration
- Linux .deb and .AppImage production is now explicitly configured via bundle targets
- All 4 platform runners (macOS ARM64, macOS x86_64, Linux x64, Windows x64) produce the correct installer format
- Signing is conditional — development builds and PRs without Azure secrets still produce installable unsigned .msi

## Self-Check: PASSED

- FOUND: tauri-app/src-tauri/tauri.conf.json
- FOUND: .github/workflows/tauri-build.yml
- FOUND: .planning/phases/38-packaging-signing-auto-update/38-02-SUMMARY.md
- FOUND commit: 415c448b (Task 1)
- FOUND commit: bedf64bd (Task 2)

---
*Phase: 38-packaging-signing-auto-update*
*Completed: 2026-03-20*
