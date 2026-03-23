# Requirements: Pilot Space

**Defined:** 2026-03-20
**Core Value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control — AI accelerates without replacing human judgment.

## v1.1 Requirements

Requirements for Tauri Desktop Client milestone. Each maps to roadmap phases.

### Tauri Shell

- [x] **SHELL-01**: User can launch native desktop app with embedded Pilot Space web UI
- [x] **SHELL-02**: Existing Next.js frontend builds in both web (standalone) and desktop (static export) modes via NEXT_TAURI flag
- [x] **SHELL-03**: User can minimize app to system tray and receive background notifications

### Authentication

- [x] **AUTH-01**: Supabase JWT token syncs from WebView to Tauri Rust backend via Tauri Store
- [x] **AUTH-02**: User session persists across app restarts (Windows useHttpsScheme enabled)
- [x] **AUTH-03**: Auth tokens stored in OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- [x] **AUTH-04**: User can sign in via Supabase OAuth (Google, GitHub) using deep link redirect

### Git Operations

- [x] **GIT-01**: User can clone a repository with progress indicator and cancellation
- [x] **GIT-02**: User can pull latest changes from remote with progress UI
- [x] **GIT-03**: User can push commits to remote with progress UI
- [x] **GIT-04**: User can view repository status (changed/staged/untracked files)
- [x] **GIT-05**: User can list, create, switch, and delete branches
- [x] **GIT-06**: App detects merge conflicts during pull and notifies user
- [x] **GIT-07**: User can configure HTTPS + Personal Access Token credentials for git operations

### Pilot CLI

- [x] **CLI-01**: pilot CLI compiled as standalone sidecar binary (PyInstaller) shipped with app
- [x] **CLI-02**: User can run `pilot implement` on an issue with streaming output in terminal
- [x] **CLI-03**: One-click "Implement Issue" flow: select issue → auto-branch → implement → stage/commit → push
- [x] **CLI-04**: Sidecar binary built for all 4 platform targets in CI

### Terminal

- [x] **TERM-01**: User can open an embedded terminal panel (xterm.js) inside the app
- [x] **TERM-02**: Terminal supports full PTY (interactive programs, arrow keys, tab completion, ANSI colors)
- [x] **TERM-03**: User can run arbitrary shell commands with streaming output
- [x] **TERM-04**: Terminal output uses batched IPC Channel to prevent memory leaks

### Diff & Commit

- [x] **DIFF-01**: User can view file diffs for working directory changes
- [x] **DIFF-02**: User can stage and unstage individual files
- [x] **DIFF-03**: User can write a commit message and commit staged changes
- [x] **DIFF-04**: User can push commits to remote after committing
- [x] **DIFF-05**: Diff viewer shows inline annotations with syntax highlighting

### Workspace

- [x] **WKSP-01**: App manages default project directory (~/ PilotSpace/projects/) for cloned repos
- [x] **WKSP-02**: User can configure base project directory path in settings
- [x] **WKSP-03**: User can link existing local repositories to Pilot Space projects
- [x] **WKSP-04**: User can see project status dashboard (cloned repos, sync status, last activity)

### Packaging

- [x] **PKG-01**: App packaged as .dmg for macOS (ARM64 + Intel)
- [x] **PKG-02**: App packaged as .deb and .AppImage for Linux (x64)
- [x] **PKG-03**: App packaged as .msi for Windows (x64)
- [x] **PKG-04**: macOS build includes code signing and Apple notarization
- [x] **PKG-05**: Windows build includes code signing
- [x] **PKG-06**: App supports auto-update with in-app notification and background download

## Future Requirements

### Enhanced Desktop Experience

- **DESK-01**: Offline mode with local cache and sync-on-reconnect
- **DESK-02**: Native file watcher for automatic git status refresh
- **DESK-03**: Multiple terminal tabs/splits
- **DESK-04**: Built-in code editor (Monaco/CodeMirror) for quick edits

## Out of Scope

| Feature | Reason |
|---------|--------|
| Bundled local FastAPI server | Massive complexity (DB, auth, migrations); remote server sufficient |
| SSH key management for git | git2-rs SSH broken on Windows; HTTPS+PAT is universal |
| Mobile/tablet Tauri builds | Tauri mobile is beta; desktop-first for developer workflows |
| Offline-first architecture | Requires local DB, conflict resolution; deferred to future milestone |
| Built-in code editor | Scope creep; users have VS Code/editors; focus on git+terminal+implement |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SHELL-01 | Phase 30 | Complete |
| SHELL-02 | Phase 30 | Complete |
| SHELL-03 | Phase 37 | Complete |
| AUTH-01 | Phase 31 | Complete |
| AUTH-02 | Phase 31 | Complete |
| AUTH-03 | Phase 31 | Complete |
| AUTH-04 | Phase 31 | Complete |
| GIT-01 | Phase 32 | Complete |
| GIT-02 | Phase 33 | Complete |
| GIT-03 | Phase 33 | Complete |
| GIT-04 | Phase 33 | Complete |
| GIT-05 | Phase 33 | Complete |
| GIT-06 | Phase 33 | Complete |
| GIT-07 | Phase 32 | Complete |
| CLI-01 | Phase 35 | Complete |
| CLI-02 | Phase 37 | Complete |
| CLI-03 | Phase 37 | Complete |
| CLI-04 | Phase 35 | Complete |
| TERM-01 | Phase 34 | Complete |
| TERM-02 | Phase 34 | Complete |
| TERM-03 | Phase 34 | Complete |
| TERM-04 | Phase 34 | Complete |
| DIFF-01 | Phase 36 | Complete |
| DIFF-02 | Phase 36 | Complete |
| DIFF-03 | Phase 36 | Complete |
| DIFF-04 | Phase 36 | Complete |
| DIFF-05 | Phase 36 | Complete |
| WKSP-01 | Phase 32 | Complete |
| WKSP-02 | Phase 32 | Complete |
| WKSP-03 | Phase 32 | Complete |
| WKSP-04 | Phase 32 | Complete |
| PKG-01 | Phase 38 | Complete |
| PKG-02 | Phase 38 | Complete |
| PKG-03 | Phase 38 | Complete |
| PKG-04 | Phase 38 | Complete |
| PKG-05 | Phase 38 | Complete |
| PKG-06 | Phase 38 | Complete |

**Coverage:**
- v1.1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 — traceability filled after roadmap creation*
