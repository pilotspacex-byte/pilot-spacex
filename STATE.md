---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Tauri Desktop Client
status: completed
stopped_at: Completed 42-01-PLAN.md
last_updated: "2026-03-24T10:17:15Z"
last_activity: "2026-03-24 - Plan 42-01 complete: CommandPalette + ActionRegistry + 6 action modules, 20 tests green, tsc PASS"
progress:
  total_phases: 18
  completed_phases: 12
  total_plans: 44
  completed_plans: 42
  percent: 95
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control.
**Current focus:** v1.1 Tauri Desktop Client — Phase 31: Auth Bridge

## Current Position

Phase: 42 of 46 (Command Palette and Breadcrumb Navigation)
Plan: 3 of 3 in current phase (COMPLETE)
Status: Phase 42 complete
Last activity: 2026-03-24 - Plan 42-01 complete: CommandPalette + ActionRegistry + 6 action modules, 20 tests green, tsc PASS

Progress: [█████████░] 95% (Phase 42: 3/3 plans complete)

## Milestone History

| Milestone | Phases | Plans | Requirements | Shipped |
|-----------|--------|-------|-------------|---------|
| v1.0 Enterprise | 1–11 | 46 | 30/30 | 2026-03-09 |
| v1.0-alpha Pre-Production Launch | 12–23 | 37 | 39/39 + 7 gap items | 2026-03-12 |
| v1.0.0-alpha2 Notion-Style Restructure | 24–29 | 14 | 17/17 | 2026-03-12 |
| v1.1 Tauri Desktop Client | 30–38 | 25 | 30/30 | 2026-03-20 |

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
- [Phase 36]: CommitPanel uses local useState for commitMessage (ephemeral UI) + stores commit success via lastCommitOid; FileGroup upgraded to FileStatus[] for checkbox stage/unstage; two-column ProjectDashboard layout with w-[280px] left sidebar
- [Phase 37]: implement-complete CustomEvent dispatched from ImplementStore — decouples store from tray notification component; TrayNotificationListener subscribes independently
- [Phase 37]: [Phase 37-02]: show_menu_on_left_click(false) used — left click shows window, right click shows context menu
- [Phase 37]: [Phase 37-02]: TrayNotificationListener is plain component (not observer) — no MobX state consumed; mounted in workspace-slug-layout via dynamic import ssr:false
- [Phase 37]: sidecarId captured from first SidecarOutput event (id field) — enables mid-flight cancel before process exits
- [Phase 38]: signingIdentity null in tauri.conf.json: tauri-action reads APPLE_SIGNING_IDENTITY from env; null avoids hardcoding team ID in source
- [Phase 38]: Sidecar pre-signing: sign pilot-cli binary individually before tauri-action bundles app to satisfy notarization
- [Phase 38]: PyInstaller entitlements: allow-unsigned-executable-memory + disable-library-validation required for onedir sidecar notarization
- [Phase 38]: bundle.targets changed from 'all' to explicit array ['dmg','deb','appimage','msi'] — avoids building unnecessary formats and documents platform intent
- [Phase 38]: certificateThumbprint: null in tauri.conf.json mirrors signingIdentity: null pattern — Azure Key Vault env vars injected at CI build time, never hardcoded in source
- [Phase 38]: AzureSignTool sidecar pre-signing on Windows: sign pilot-cli-.exe before tauri-action bundles .msi to maintain signing chain; mirrors macOS codesign pre-signing from Plan 01
- [Phase 38]: tauri_plugin_updater::Builder::new().build() used (not init()) — Builder pattern allows configuring custom headers or check intervals in future without API change
- [Phase 38]: dialog: false in tauri.conf.json updater config — UI handled by UpdateNotification component (non-blocking banner, not a blocking modal dialog)
- [Phase 38]: releaseDraft: true in tauri-release.yml — releases require manual publish to prevent accidental production releases; cancel-in-progress: false prevents partial artifact corruption
- [Phase 38]: 5-second mount delay on UpdateNotification — avoids competing with app init and Supabase auth token load on startup; installs on restart (not forced) to respect user autonomy
- [Phase 39-01]: Tauri keygen requires interactive TTY — placeholder pubkey used; real key must be generated locally and added as TAURI_SIGNING_PRIVATE_KEY GitHub secret before first release
- [Phase 39-01]: dawidd6/action-download-artifact@v6 used for cross-workflow sidecar download in tauri-build.yml with if_no_artifact_found: warn to avoid deadlock on parallel CI runs
- [Phase 40]: Block math requires newline-separated syntax for katex-display rendering
- [Phase 40]: rehypeMermaid replaces pre>code.language-mermaid with div[data-mermaid] for React component mapping

- [Phase 40-01]: PM block regex validates against 10 known types; invalid types silently skipped
- [Phase 40-01]: FileStore eviction policy: oldest non-dirty, non-active tab first; fallback to oldest if all dirty
- [Phase 40-01]: FileStore uses Map<string, OpenFile> for O(1) lookup with insertion-order preservation
- [Phase 40-03]: useState (not useRef) for editor/monaco instances consumed during render -- React 19 react-hooks/refs
- [Phase 40-03]: Regex constants exported without /g flag; fresh instances created in parseMarkdownLine with /g
- [Phase 40-03]: PMBlockViewZone is plain component (NOT observer) -- React 19 flushSync constraint
- [Phase 40-03]: View zone portals built in useEffect+setState, not useMemo, to avoid reading refs during render- [Phase 40-04]: disposeInlineCompletions replaces freeInlineCompletions in Monaco 0.55.1 InlineCompletionsProvider
- [Phase 40-04]: Y.Text type name 'monaco' (distinct from 'prosemirror' used by TipTap Yjs binding)
- [Phase 40-04]: MonacoNoteEditor uses useState (not useRef) for editor/monaco instances consumed during render — React 19 refs rule
- [Phase 40]: FileIconByExt is a standalone component (not dynamic useMemo) to satisfy React 19 static-components lint rule
- [Phase 40]: useQuickOpen resets selectedIndex in setQuery callback rather than useEffect to satisfy React 19 set-state-in-effect lint rule
- [Phase 40]: Preview panel replaces editor content via toggle, not a separate third panel (per UI-SPEC)
- [Phase 40]: useMonacoNote composite hook takes options object for clarity with 9 parameters; ghost text defaults to no-op; collab auto-disabled without supabase client
- [Phase 40]: NoteCanvas default export flipped to NoteCanvasMonaco; TipTap available as NoteCanvasLegacy named export
- [Phase 40]: EditorLayout saveFn wired via onSave prop for generic persistence (parent decides how to save)
- [Phase 41]: ImageLightbox extracted to separate file to keep FilePreviewModal under 700-line pre-commit limit
- [Phase 41]: Existing XlsxRenderer from PR #85 kept as-is; XLSX.read({ dense: true }) preferred over sheetRows: 501 for accurate total row count in truncation banner
- [Phase 41]: Controlled component pattern: PptxRenderer is a pure canvas renderer; navigation, keyboard, fullscreen live in FilePreviewModal parent
- [Phase 41]: PR #85 annotation backend uses direct repo injection (no service layer) -- accepted as valid CRUD pattern
- [Phase 41-06]: PptxAnnotationPanel is plain React component (not observer) -- React 19 flushSync constraint
- [Phase 41-06]: workspaceId/projectId added as optional props to FilePreviewModalProps for backward compatibility
- [Phase 41-06]: isPptxFile() helper in FilePreviewModal detects PPTX by MIME type + extension since RendererType lacks 'pptx'
- [Phase 41]: Pre-existing test failures (52 files) confirmed unrelated to Phase 41; all 85 Phase 41 tests pass
- [Phase 42-01]: ActionRegistry is plain module-level Map, not MobX store -- palette reads snapshot on open, no reactivity needed
- [Phase 42-01]: useRecentActions reads localStorage fresh each call (no stale cache) for cross-tab consistency
- [Phase 42-01]: Action modules use context-based closures with optional chaining for safe no-op when context not wired
- [Phase 42-02]: React 19 compliant isLoading: batched state object { symbols, isLoading } instead of synchronous setState in effect body
- [Phase 42-02]: Stack-based symbol hierarchy: pop until parent with lower level, PM blocks nest under most recent heading
- [Phase 42-02]: EditorLike interface for useSymbolOutline to decouple from Monaco types

### Roadmap Evolution

- Phase 40 added: WebGPU Note Canvas + IDE File Editor
- Phase 42 added: Command Palette and Breadcrumb Navigation
- Phase 43 added: LSP Integration and Code Intelligence
- Phase 44 added: Web Git Integration and Source Control Panel
- Phase 45 added: Editor Plugin API and Custom Block Types
- Phase 46 added: Multi-Theme System and Editor Customization

### Pending Todos

None.

### Blockers/Concerns

- Windows EV code signing certificate must be procured during Phase 30 (1-2 week lead time) to avoid blocking Phase 38
- Apple Developer credentials must be configured in CI during Phase 30 to avoid blocking Phase 38 notarization

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260321-j7t | Fix all DANGER and WATCH items from Tauri deep context report | 2026-03-21 | 9f3cfae8 | Verified | [260321-j7t-fix-all-danger-and-watch-items-from-taur](./quick/260321-j7t-fix-all-danger-and-watch-items-from-taur/) |

## Session Continuity

Last session: 2026-03-24T10:17:15Z
Stopped at: Completed 42-01-PLAN.md
Resume file: .planning/phases/42-command-palette-and-breadcrumb-navigation/42-03-PLAN.md
Next action: Phase 42 complete (3/3 plans). Execute Plan 42-03 if not already done, or proceed to Phase 43.
