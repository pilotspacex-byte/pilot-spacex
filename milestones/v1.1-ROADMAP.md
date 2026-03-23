# Roadmap: Pilot Space

## Milestones

- ✅ **v1.0 Enterprise** — Phases 1–11 (shipped 2026-03-09)
- ✅ **v1.0-alpha Pre-Production Launch** — Phases 12–23 (shipped 2026-03-12)
- ✅ **v1.0.0-alpha2 Notion-Style Restructure** — Phases 24–29 (shipped 2026-03-12)
- 🚧 **v1.1 Tauri Desktop Client** — Phases 30–38 (in progress)

## Phases

<details>
<summary>✅ v1.0 Enterprise (Phases 1–11) — SHIPPED 2026-03-09</summary>

- [x] Phase 1: Identity & Access (9/9 plans) — completed 2026-03-07
- [x] Phase 2: Compliance & Audit (5/5 plans) — completed 2026-03-08
- [x] Phase 3: Multi-Tenant Isolation (8/8 plans) — completed 2026-03-08
- [x] Phase 4: AI Governance (10/10 plans) — completed 2026-03-08
- [x] Phase 5: Operational Readiness (7/7 plans) — completed 2026-03-09
- [x] Phase 6: Wire Rate Limiting + SCIM Token (1/1 plans) — completed 2026-03-09
- [x] Phase 7: Wire Storage Quota Enforcement (2/2 plans) — completed 2026-03-09
- [x] Phase 8: Fix SSO Integration (1/1 plans) — completed 2026-03-09
- [x] Phase 9: Login Audit Events (1/1 plans) — completed 2026-03-09
- [x] Phase 10: Wire Audit Trail (1/1 plans) — completed 2026-03-09
- [x] Phase 11: Fix Rate Limiting Architecture (1/1 plans) — completed 2026-03-09

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.0-alpha Pre-Production Launch (Phases 12–23) — SHIPPED 2026-03-12</summary>

- [x] Phase 12: Onboarding & First-Run UX (3/3 plans) — completed 2026-03-09
- [x] Phase 13: AI Provider Registry + Model Selection (4/4 plans) — completed 2026-03-10
- [x] Phase 14: Remote MCP Server Management (4/4 plans) — completed 2026-03-10
- [x] Phase 15: Related Issues (3/3 plans) — completed 2026-03-10
- [x] Phase 16: Workspace Role Skills (4/4 plans) — completed 2026-03-10
- [x] Phase 17: Skill Action Buttons (2/2 plans) — completed 2026-03-11
- [x] Phase 18: Tech Debt Closure (3/3 plans) — completed 2026-03-11
- [x] Phase 19: Skill Registry & Plugin System (4/4 plans) — completed 2026-03-11
- [x] Phase 20: Skill Template Catalog (4/4 plans) — completed 2026-03-11
- [x] Phase 21: Documentation & Verification Closure (2/2 plans) — completed 2026-03-12
- [x] Phase 22: Integration Safety — Session & OAuth2 UI (2/2 plans) — completed 2026-03-12
- [x] Phase 23: Tech Debt Sweep (2/2 plans) — completed 2026-03-12

Full archive: `.planning/milestones/v1.0-alpha-ROADMAP.md`

</details>

<details>
<summary>✅ v1.0.0-alpha2 Notion-Style Restructure (Phases 24–29) — SHIPPED 2026-03-12</summary>

- [x] Phase 24: Page Tree Data Model (2/2 plans) — completed 2026-03-12
- [x] Phase 25: Tree API & Page Service (2/2 plans) — completed 2026-03-12
- [x] Phase 26: Sidebar Tree & Navigation (3/3 plans) — completed 2026-03-12
- [x] Phase 27: Project Hub & Issue Views (2/2 plans) — completed 2026-03-12
- [x] Phase 28: Visual Design Refresh (2/2 plans) — completed 2026-03-12
- [x] Phase 29: Responsive Layout & Drag-and-Drop (3/3 plans) — completed 2026-03-12

Full archive: `.planning/milestones/v1.0.0-alpha2-ROADMAP.md`

</details>

### 🚧 v1.1 Tauri Desktop Client (In Progress)

**Milestone Goal:** Wrap the existing Pilot Space web app in a Tauri desktop shell with native local capabilities — git operations, pilot CLI execution, embedded terminal, diff viewer — so developers can manage projects AND execute code from one app.

- [x] **Phase 30: Tauri Shell + Static Export** — Scaffold tauri-app/, wire Next.js static export mode, verify all dynamic routes and CI matrix (completed 2026-03-20)
- [x] **Phase 31: Auth Bridge** — Sync Supabase JWT to OS keychain via Tauri Store; deep link OAuth callback (completed 2026-03-20)
- [x] **Phase 32: Workspace Management + Git Clone** — App-managed project directory, configure base path, link repos, clone with progress (completed 2026-03-20)
- [x] **Phase 33: Full Git Operations** — Pull, push, branch management, status, conflict detection (completed 2026-03-20)
- [x] **Phase 34: Embedded Terminal** — xterm.js panel with full PTY, batched IPC output, arbitrary shell commands (completed 2026-03-20)
- [x] **Phase 35: Pilot CLI Sidecar** — Compile pilot binary per platform, wire into app, CI matrix artifacts (completed 2026-03-20)
- [x] **Phase 36: Diff Viewer + Commit UI** — File diff view, stage/unstage, commit message, push (completed 2026-03-20)
- [x] **Phase 37: One-Click Implement Flow + Tray** — End-to-end issue→implement→commit loop; system tray with notifications (completed 2026-03-20)
- [x] **Phase 38: Packaging + Signing + Auto-Update** — Signed .dmg/.deb/.AppImage/.msi per platform, notarization, auto-update (completed 2026-03-20)
- [x] **Phase 39: Tech Debt Cleanup** — Auto-update pubkey, stores barrel exports, dev CI sidecar download (completed 2026-03-20)

## Phase Details

### Phase 30: Tauri Shell + Static Export
**Goal**: A working Tauri window displays the existing Next.js frontend; the app compiles and runs on macOS, Linux, and Windows from the CI matrix
**Depends on**: Nothing (first phase of v1.1)
**Requirements**: SHELL-01, SHELL-02
**Success Criteria** (what must be TRUE):
  1. User can launch the desktop app and see the full Pilot Space UI inside a native window
  2. The existing Next.js frontend builds in both web (standalone) and desktop (static export, NEXT_TAURI=true) modes without errors
  3. All dynamic routes (e.g., /[workspaceSlug]/issues/[issueId]) navigate correctly in the static export build inside the WebView
  4. GitHub Actions CI matrix produces unsigned app artifacts for all 4 platform targets (macOS ARM, macOS x86, Linux x64, Windows x64)
**Plans:** 3/3 plans complete

Plans:
- [x] 030-01-PLAN.md — Scaffold tauri-app/ directory, Cargo.toml, tauri.conf.json, capabilities, isTauri() utility
- [x] 030-02-PLAN.md — Next.js static export mode toggle, docs page client-side conversion, dual-mode build verification
- [x] 030-03-PLAN.md — GitHub Actions CI 4-runner build matrix, artifact upload, Rust caching

### Phase 31: Auth Bridge
**Goal**: Users can sign in and their Supabase session persists securely across app restarts, with tokens stored in the OS keychain rather than browser localStorage
**Depends on**: Phase 30
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):
  1. Supabase JWT token is readable by the Tauri Rust backend after the user signs in (WebView-to-Rust sync)
  2. User session survives an app restart — user is still logged in when reopening the app
  3. Auth tokens are stored in the OS keychain (macOS Keychain / Windows Credential Manager / Linux Secret Service), not in localStorage
  4. User can sign in via Google or GitHub OAuth and be redirected back into the app via deep link (pilotspace://auth/callback)
**Plans:** 3/3 plans complete

Plans:
- [ ] 31-01-PLAN.md — Tauri Store token sync: syncTokenToTauriStore() in Providers, auth.rs Rust commands, typed IPC wrappers
- [ ] 31-02-PLAN.md — OS keychain storage: tauri-plugin-keyring, keychain read/write, Store-to-keychain migration
- [ ] 31-03-PLAN.md — Deep link OAuth callback: tauri-plugin-deep-link, pilotspace:// scheme, exchangeCodeForSession

### Phase 32: Workspace Management + Git Clone
**Goal**: The app manages a default project directory and users can clone a repository into it with visual progress feedback
**Depends on**: Phase 31
**Requirements**: WKSP-01, WKSP-02, WKSP-03, WKSP-04, GIT-01, GIT-07
**Success Criteria** (what must be TRUE):
  1. App creates and uses ~/PilotSpace/projects/ as the default directory for cloned repositories
  2. User can change the base project directory path in Settings using a native folder picker dialog
  3. User can clone a repository by entering its URL; a progress bar shows clone progress and a cancel button stops the operation
  4. User can link an existing local repository folder to a Pilot Space project
  5. User can see a dashboard showing all managed repos with their sync status and last activity
  6. User can configure HTTPS + Personal Access Token credentials for git operations
**Plans:** 4/4 plans complete

Plans:
- [ ] 32-01-PLAN.md — Rust backend: workspace.rs (dir management, folder picker, project list), git.rs (clone with progress/cancel, PAT credential storage via keyring)
- [ ] 32-02-PLAN.md — Frontend: typed IPC wrappers, ProjectStore MobX, project dashboard UI with clone + link dialogs
- [ ] 32-03-PLAN.md — Settings: Desktop settings page (project directory config + git credentials), wired into Settings modal (Tauri-only)

### Phase 33: Full Git Operations
**Goal**: Users can perform all essential day-to-day git operations (pull, push, branch management, status) from inside the app
**Depends on**: Phase 32
**Requirements**: GIT-02, GIT-03, GIT-04, GIT-05, GIT-06
**Success Criteria** (what must be TRUE):
  1. User can pull latest changes from remote with a progress indicator
  2. User can push committed changes to remote with a progress indicator
  3. User can view a list of all changed, staged, and untracked files in the repository
  4. User can list branches, create a new branch, switch to a branch, and delete a branch
  5. When a pull results in merge conflicts, the app notifies the user with the list of conflicted files
**Plans:** 3/3 plans complete

Plans:
- [ ] 33-01-PLAN.md — Rust: git_pull, git_push with progress Channel + conflict detection; git_status, branch CRUD commands
- [ ] 33-02-PLAN.md — Frontend: typed IPC wrappers in tauri.ts + GitStore MobX store with observables/actions
- [ ] 33-03-PLAN.md — Frontend: GitStatusPanel, BranchSelector, ConflictBanner components wired into ProjectDashboard

### Phase 34: Embedded Terminal
**Goal**: Users can open a terminal panel inside the app and run interactive programs with full PTY support
**Depends on**: Phase 30
**Requirements**: TERM-01, TERM-02, TERM-03, TERM-04
**Success Criteria** (what must be TRUE):
  1. User can open an embedded terminal panel inside the app that shows a live shell prompt
  2. Interactive programs (vim, less, htop) work correctly with arrow keys, tab completion, and ANSI colors
  3. User can run any shell command and see streaming output in real time
  4. Terminal runs for extended periods and under high output volume without memory leaks or app slowdown
**Plans:** 2/2 plans complete

Plans:
- [ ] 34-01-PLAN.md — PTY Rust backend — tauri-plugin-pty (or tauri-plugin-shell fallback), terminal.rs module, TerminalState managed struct, batched output at 16ms intervals via Channel API
- [ ] 34-02-PLAN.md — TerminalPanel.tsx frontend — @xterm/xterm 5.5.0, @xterm/addon-fit, useTerminal hook, session lifecycle with close_terminal() cleanup, 10,000-line scrollback

### Phase 35: Pilot CLI Sidecar
**Goal**: The pilot CLI binary ships with the app pre-compiled for every platform and can be spawned by the Rust backend
**Depends on**: Phase 30
**Requirements**: CLI-01, CLI-04
**Success Criteria** (what must be TRUE):
  1. The app bundles a compiled pilot CLI binary that requires no Python installation on the user's machine
  2. CI matrix produces platform-specific pilot binaries for all 4 targets (macOS ARM, macOS x86, Linux x64, Windows x64) as build artifacts
  3. The Rust backend can spawn the sidecar binary and receive streaming output
**Plans:** 2/2 plans complete

Plans:
- [ ] 35-01-PLAN.md — PyInstaller build pipeline — pyinstaller.spec, --onedir mode, per-platform CI matrix jobs producing tauri-app/binaries/ artifacts
- [ ] 35-02-PLAN.md — Tauri externalBin config + sidecar.rs Rust module — tauri-plugin-shell, spawn with Channel streaming, SidecarState managed struct

### Phase 36: Diff Viewer + Commit UI
**Goal**: Users can review file diffs, stage changes, write a commit message, and push — a lightweight git client UI on top of the git layer
**Depends on**: Phase 33
**Requirements**: DIFF-01, DIFF-02, DIFF-03, DIFF-04, DIFF-05
**Success Criteria** (what must be TRUE):
  1. User can click on any changed file and see its diff with syntax-highlighted inline annotations
  2. User can check/uncheck individual files to stage or unstage them
  3. User can type a commit message and click Commit to create a commit from staged files
  4. User can push the committed changes to remote directly from the commit UI
  5. Large diffs (hundreds of files, thousands of lines) render without the UI freezing
**Plans:** 3/3 plans complete

Plans:
- [ ] 36-01-PLAN.md — Rust git_diff/git_stage/git_unstage/git_commit commands + TypeScript IPC wrappers + GitStore extensions
- [ ] 36-02-PLAN.md — DiffViewer component with unified diff parsing, syntax-highlighted lines, react-virtuoso virtualization
- [ ] 36-03-PLAN.md — CommitPanel with stage/unstage checkboxes, commit message, commit+push; GitStatusPanel interactive files; ProjectDashboard integration

### Phase 37: One-Click Implement Flow + Tray
**Goal**: Users can trigger the full implement loop from inside the app — select issue, auto-branch, run pilot implement with live terminal output, then commit and push — and receive background notifications via the system tray
**Depends on**: Phase 34, Phase 35, Phase 36
**Requirements**: CLI-02, CLI-03, SHELL-03
**Success Criteria** (what must be TRUE):
  1. User can run pilot implement on an issue and watch streaming output appear in the embedded terminal
  2. User can trigger One-Click Implement: select an issue, and the app automatically creates a branch, runs pilot implement, and stages/commits/pushes the result
  3. User can minimize the app to the system tray and receive background notifications (e.g., implement complete, CI status)
**Plans:** 2/2 plans complete

Plans:
- [ ] 37-01-PLAN.md — ImplementStore MobX orchestrator + ImplementIssueButton UI on issue detail page (CLI-02, CLI-03)
- [ ] 37-02-PLAN.md — System tray with minimize-to-tray, tray icon menu, native OS notifications on implement completion (SHELL-03)

### Phase 38: Packaging + Signing + Auto-Update
**Goal**: Signed, distributable app installers are produced for all platforms from the CI matrix, with in-app auto-update
**Depends on**: Phase 37
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05, PKG-06
**Success Criteria** (what must be TRUE):
  1. macOS users receive a .dmg installer that passes Gatekeeper without warnings (code-signed and notarized)
  2. Linux users receive .deb and .AppImage packages that install and run without configuration
  3. Windows users receive a .msi installer that installs without SmartScreen blocking (EV code signed)
  4. When a new version is available, the app shows an in-app notification and downloads the update in the background
**Plans:** 3/3 plans complete

Plans:
- [ ] 38-01-PLAN.md — macOS .dmg with Apple code signing, notarization, hardened runtime entitlements, sidecar signing (PKG-01, PKG-04)
- [ ] 38-02-PLAN.md — Linux .deb + .AppImage, Windows .msi with EV code signing via Azure Key Vault (PKG-02, PKG-03, PKG-05)
- [ ] 38-03-PLAN.md — tauri-plugin-updater, GitHub Release workflow, in-app update notification + background download (PKG-06)

### Phase 39: Tech Debt Cleanup
**Goal**: Close tech debt items from milestone audit — auto-update pubkey, stores barrel exports, dev CI sidecar download
**Depends on**: Phase 38
**Requirements**: PKG-06 (partial — pubkey completes auto-update verification)
**Gap Closure:** Closes gaps from v1.1-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. `tauri.conf.json plugins.updater.pubkey` contains a non-empty public key string
  2. `stores/index.ts` exports `TerminalStore`, `useTerminalStore`, `ImplementStore`, `useImplementStore`
  3. `tauri-build.yml` downloads pilot-cli sidecar artifacts before building (dev CI includes real binary)
**Plans**: 1 plan

Plans:
- [x] 39-01-PLAN.md — Auto-update pubkey, stores barrel exports, dev CI sidecar download

## Progress

**Execution Order:**
Phases execute in numeric order: 30 → 31 → 32 → 33 → 34 → 35 → 36 → 37 → 38 → 39
Note: Phase 34 and Phase 35 depend only on Phase 30, so they can run in parallel with Phase 32/33 if desired.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1–11 | v1.0 | 46/46 | Complete | 2026-03-09 |
| 12–23 | v1.0-alpha | 37/37 | Complete | 2026-03-12 |
| 24–29 | v1.0.0-alpha2 | 14/14 | Complete | 2026-03-12 |
| 30. Tauri Shell + Static Export | 3/3 | Complete    | 2026-03-20 | - |
| 31. Auth Bridge | 3/3 | Complete    | 2026-03-20 | - |
| 32. Workspace + Git Clone | 4/4 | Complete    | 2026-03-20 | - |
| 33. Full Git Operations | 3/3 | Complete    | 2026-03-20 | - |
| 34. Embedded Terminal | 2/2 | Complete    | 2026-03-20 | - |
| 35. Pilot CLI Sidecar | 2/2 | Complete    | 2026-03-20 | - |
| 36. Diff Viewer + Commit UI | 3/3 | Complete    | 2026-03-20 | - |
| 37. One-Click Implement + Tray | 2/2 | Complete    | 2026-03-20 | - |
| 38. Packaging + Signing + Auto-Update | 3/3 | Complete    | 2026-03-20 | - |
| 39. Tech Debt Cleanup | 1/1 | Complete    | 2026-03-20 | - |

**v1.1 total: 10 phases, ~26 plans, 30 requirements**

---
*v1.0 shipped: 2026-03-09 — 11 phases, 46 plans, 30/30 requirements*
*v1.0-alpha shipped: 2026-03-12 — 12 phases, 37 plans, 39/39 requirements + 7 gap closure items*
*v1.0.0-alpha2 shipped: 2026-03-12 — 6 phases, 14 plans, 17/17 requirements*
*v1.1 roadmap created: 2026-03-20 — 9 phases, ~25 plans, 30/30 requirements*
