---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Tauri Desktop Client
status: completed
stopped_at: Completed 36-02-PLAN.md
last_updated: "2026-03-20T08:55:48.575Z"
last_activity: "2026-03-20 — Phase 31 Plan 03 complete — pilotspace:// deep link OAuth PKCE flow for Google/GitHub social login"
progress:
  total_phases: 9
  completed_phases: 6
  total_plans: 20
  completed_plans: 19
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control.
**Current focus:** v1.1 Tauri Desktop Client — Phase 31: Auth Bridge

## Current Position

Phase: 31 of 38 (Auth Bridge)
Plan: 3 of 3 in current phase
Status: Phase complete
Last activity: 2026-03-20 — Phase 31 Plan 03 complete — pilotspace:// deep link OAuth PKCE flow for Google/GitHub social login

Progress: [██████████] 100% (v1.1: 6/6 plans)

## Milestone History

| Milestone | Phases | Plans | Requirements | Shipped |
|-----------|--------|-------|-------------|---------|
| v1.0 Enterprise | 1–11 | 46 | 30/30 | 2026-03-09 |
| v1.0-alpha Pre-Production Launch | 12–23 | 37 | 39/39 + 7 gap items | 2026-03-12 |
| v1.0.0-alpha2 Notion-Style Restructure | 24–29 | 14 | 17/17 | 2026-03-12 |
| v1.1 Tauri Desktop Client | 30–38 | ~25 | 30/30 | — |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
- [Roadmap]: Phases 34 (Terminal) and 35 (CLI Sidecar) depend only on Phase 30 — can run in parallel with 32/33 if desired
- [Roadmap]: SHELL-03 (system tray) assigned to Phase 37 — depends on terminal + sidecar + diff being complete before tray notifications are meaningful
- [Research flag]: tauri-plugin-pty is a community plugin; evaluate tauri-plugin-shell streaming sufficiency at Phase 34 planning time
- [Research flag]: Windows EV certificate procurement takes 1-2 weeks — initiate at Phase 30 start, not Phase 38
- [Research flag]: Next.js dynamic route audit scope unknown until Phase 30 begins; budget extra time if >5 unique dynamic route patterns found
- [Phase 030]: Identifier io.pilotspace.app is permanent — determines app data dir path, cannot change post-release
- [Phase 030]: useHttpsScheme: true set from Phase 30 — prevents localStorage/IndexedDB reset on Windows restarts
- [Phase 030]: isTauri() detects Tauri shell via __TAURI_INTERNALS__ in window — all @tauri-apps/api imports must be lazy/dynamic
- [Phase 030]: tauri-app/frontend/out placeholder dir required for cargo check (generate_context! validates frontendDist at compile time)
- [Phase 030]: Use generateStaticParams placeholder ('_') for workspace slug — empty array causes Next.js 16 to report missing params on child pages
- [Phase 030]: Layout-split pattern required for 'use client' layouts — Server Component wrapper exports generateStaticParams, client component handles rendering
- [Phase 030]: API route handlers changed from force-dynamic to force-static — POST handlers always execute per-request in standalone mode; force-static unblocks static export
- [Phase 030]: ubuntu-22.04 (not ubuntu-latest) in CI to ensure libwebkit2gtk-4.1-dev availability for Tauri v2 Linux builds
- [Phase 030]: macos-13 runner for x86_64 CI target — macos-latest now resolves to Apple Silicon (ARM64) runners
- [Phase 030]: fail-fast: false in Tauri CI matrix — all 4 platform builds run to completion to expose platform-specific failures independently
- [Phase 030]: Signing secrets commented out for Phase 30 unsigned builds — Phase 38 will populate APPLE_CERTIFICATE and Windows EV certificate secrets
- [Phase 031-01]: pilot-auth.json store file name consistent between Rust StoreExt and JS @tauri-apps/plugin-store
- [Phase 031-01]: StoreOptions.defaults is required in plugin-store 2.4.2 — pass { defaults: {} } when no defaults needed
- [Phase 031-01]: syncTokenToTauriStore idempotent via initialized flag — safe in React StrictMode double-mount
- [Phase 031-01]: Dynamic import of @tauri-apps/plugin-store inside syncTokenToTauriStore prevents SSG build errors
- [Phase 31]: keyring v3 crate used directly — tauri-plugin-keyring only at v0.1.0 (not Tauri v2 compatible)
- [Phase 31]: Tauri Store retained post-migration as WebView sync channel — keychain is Rust source of truth only
- [Phase 31]: Dynamic import of @tauri-apps/plugin-deep-link inside initDeepLinkListener prevents SSG build errors — same pattern as other Tauri plugin imports
- [Phase 31]: isTauri() static import in AuthStore.ts is safe — reads window.__TAURI_INTERNALS__ only, no @tauri-apps/* API imported at module level
- [Phase 32]: spawn_blocking used for all git2 operations — Repository is not Send
- [Phase 32]: OnceLock<Arc<AtomicBool>> for cancel flag — safe static initialization shared across cancel_clone and git_clone
- [Phase 32]: PAT stored under git_pat keychain account, never returned to frontend — get_git_credentials returns has_pat:bool only
- [Phase 32]: DesktopSettingsPage is NOT wrapped in observer() — no MobX observables consumed; plain React state via useState/useCallback is sufficient
- [Phase 32]: settingsNavSections computed at module level via isTauri() — Tauri-only Desktop nav group appended conditionally without React state/effect
- [Phase 32]: gitClone wrapper creates Channel<GitProgress> and wires onmessage to callback — Tauri v2 streaming pattern for progress
- [Phase 32]: CloneRepoDialog prevents dialog close during active clone via onOpenChange guard — UX safety for long-running operations
- [Phase 32]: Dedicated reset_projects_dir Rust command deletes projects_dir Store key instead of overloading set_projects_dir with empty-string sentinel
- [Phase 32]: desktopNavSection defined at module level using isTauri() — stable const, no React state/effect needed
- [Phase 33]: git_pull returns conflict file list without auto-committing — user must resolve manually
- [Phase 33]: build_callbacks helper extracted for fetch-phase; git_push uses inline callbacks for push_transfer_progress (different signature)
- [Phase 33]: git_branch_switch uses CheckoutBuilder::default().safe() to protect uncommitted changes
- [Phase 33]: GitStore.setRepoPath() auto-triggers refreshAll() on non-empty path — UI always has fresh state when switching repos
- [Phase 33]: modifiedFiles/stagedFiles computed properties filter status.files for git diff UI grouping
- [Phase 33]: GitStatusPanel calls gitStore.setRepoPath() via useEffect to auto-trigger refreshAll() on mount
- [Phase 33]: BranchSelector uses Popover+Command (cmdk) pattern — consistent with other selector components in the codebase
- [Phase 33]: ProjectDashboard uses stopPropagation on expanded git panel to prevent card collapse when interacting with git controls
- [Phase 34]: portable-pty@0.9 used for PTY backend — tauri-pty crate does not exist; std::thread::spawn for blocking PTY reader; 16ms batch flush via Channel prevents IPC memory leak (Pitfall 7)
- [Phase 34]: Dynamic-only xterm.js imports prevent SSG build failures — all @xterm/* inside useEffect; css.d.ts type declaration added for dynamic CSS import; TerminalPanel uses ssr:false dynamic import in workspace-slug-layout
- [Phase 35]: onedir mode chosen: --onefile incompatible with Tauri sidecar on Windows (DLL extraction failures)
- [Phase 35]: pilot_cli.backup.* subpackage explicitly listed in hiddenimports — PyInstaller static analysis misses conditional imports
- [Phase 35]: CI workflow uses env: vars in run: steps for matrix values — project security policy prevents inline ${{ matrix.* }} in shell commands
- [Phase 35]: Stub binary (empty file) in binaries/ for local cargo check — gitignored, real binary from CI (35-01)
- [Phase 35]: shell:allow-execute + shell:allow-spawn both required in capabilities for sidecar spawn to work
- [Phase 35]: on_output param passed as snake_case in invoke() payload; cwd passed as null (not undefined) for Option<String> None mapping
- [Phase 36]: git_diff accumulates staged+unstaged diffs via HashMap; git_unstage uses reset_default; git_commit detects unborn HEAD; GitStore.selectFile auto-triggers fetchDiff
- [Phase 36-diff-viewer-commit-ui]: No external diff rendering library — custom parseDiffLines() avoids react-diff-view bundle weight; git2-rs provides standard unified diff format
- [Phase 36-diff-viewer-commit-ui]: react-virtuoso Virtuoso component used for diff virtualization — renders only visible rows, preventing UI freeze on 1000+ line diffs (DIFF-05)

### Pending Todos

None.

### Blockers/Concerns

- Windows EV code signing certificate must be procured during Phase 30 (1-2 week lead time) to avoid blocking Phase 38
- Apple Developer credentials must be configured in CI during Phase 30 to avoid blocking Phase 38 notarization

## Session Continuity

Last session: 2026-03-20T08:55:48.573Z
Stopped at: Completed 36-02-PLAN.md
Resume file: None
Next action: /gsd:execute-phase 31
