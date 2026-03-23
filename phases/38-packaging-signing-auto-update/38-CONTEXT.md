# Phase 38: Packaging + Signing + Auto-Update - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Autonomous mode — derived from ROADMAP + research

<domain>
## Phase Boundary

Production-ready installers for all 3 platforms with code signing, macOS notarization, and in-app auto-update. This is the final phase — after this, the app is distributable.

</domain>

<decisions>
## Implementation Decisions

### macOS Packaging (PKG-01, PKG-04)
- .dmg installer for both ARM64 and Intel via `tauri-apps/tauri-action`
- Code signing with Apple Developer certificate (codesign)
- Notarization via `notarytool` (30-60 min CI budget)
- Sidecar binaries must be individually signed before app signing
- Hardened runtime entitlements required

### Linux Packaging (PKG-02)
- .deb package for Ubuntu/Debian
- .AppImage for universal Linux
- No code signing required (optional GPG)

### Windows Packaging (PKG-03, PKG-05)
- .msi installer via WiX
- EV code signing via Azure Key Vault (or SignPath)
- Eliminates SmartScreen warnings for users

### Auto-Update (PKG-06)
- `tauri-plugin-updater` for in-app update checks
- GitHub Releases as update manifest source
- Background download + install-on-restart
- Update notification in app UI (non-blocking)

### Claude's Discretion
- Update check frequency (on launch, hourly, daily)
- Update notification UI design
- Release channel naming (stable, beta)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/tauri-build.yml` — existing 4-runner CI matrix (Phase 30)
- `.github/workflows/pilot-cli-build.yml` — sidecar build pipeline (Phase 35)
- `tauri-app/src-tauri/tauri.conf.json` — existing Tauri config with all plugins

### Established Patterns
- GitHub Actions matrix strategy for cross-platform builds
- `tauri-apps/tauri-action@v0` for building Tauri apps
- Artifact upload/download between workflow jobs

### Integration Points
- Merge sidecar build into main tauri-build workflow (or use workflow_call)
- Add signing secrets to GitHub Actions
- Add updater plugin to Tauri config and frontend

</code_context>

<specifics>
## Specific Ideas

- Research warns: macOS notarization can spike to 30-60 min — set generous CI timeouts
- Research warns: PyInstaller sidecar must be signed individually on macOS (Tauri bug #11992)
- Research warns: Windows EV cert procurement takes 1-2 weeks — should be in progress

</specifics>

<deferred>
## Deferred Ideas

None — final phase

</deferred>

---

*Phase: 38-packaging-signing-auto-update*
*Context gathered: 2026-03-20 via autonomous mode*
