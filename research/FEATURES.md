# Feature Research

**Domain:** Tauri desktop client — WebView shell, git operations, embedded terminal, diff viewer, sidecar process management, cross-platform packaging
**Researched:** 2026-03-20
**Confidence:** HIGH (Tauri v2 official docs + verified community patterns)

## Feature Landscape

### Table Stakes (Users Expect These)

Features a desktop app MUST have. Missing these makes the app feel broken, unfinished, or worse than just using the web.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Tauri shell with embedded Next.js WebView | The entire premise — existing web UI runs inside a native window | HIGH | Requires `output: 'export'` in next.config.mjs (SSG only; SSR is incompatible with Tauri). `frontendDist: "../out"` in tauri.conf.json. `devUrl: http://localhost:3000` for dev. All Tauri JS APIs must be imported as Client Components (`'use client'`). [MEDIUM confidence on exact config until validated] |
| Supabase auth token bridge (WebView ↔ Rust) | Users log in once — both the web UI and native Rust commands must share the same session | HIGH | Deep link pattern for OAuth PKCE: Tauri handles `tauri://` scheme redirect, extracts auth code, sets Supabase session via JS injection into WebView. Alternative: WebView handles auth normally, Rust reads session from `localStorage` via evaluate_script. Existing Supabase PKCE flow must be adapted. See [Supabase + Google OAuth in Tauri 2.0](https://medium.com/@nathancovey23/supabase-google-oauth-in-a-tauri-2-0-macos-app-with-deep-links-f8876375cb0a). |
| IPC bridge from Next.js to Rust commands | Frontend must call native Rust commands (git, file system, spawn sidecar) | MEDIUM | Use `@tauri-apps/api` `invoke()` — wraps `window.__TAURI_INTERNALS__.invoke()`. All Tauri API calls require `'use client'` components. Do NOT import at module level in server components. Capabilities file (`src-tauri/capabilities/default.json`) must grant each command permission explicitly. |
| App-managed workspace directory | Users expect a predictable place for cloned repos (`~/PilotSpace/projects/`) | LOW | Tauri `$HOME` path variable. `tauri-plugin-fs` with `$HOME` scope. Configurable base path stored in app config (Tauri `tauri-plugin-store` or Rust config file). Create on first launch if absent. |
| Git repository clone | Fundamental git operation — users expect to clone a repo by URL | HIGH | `git2-rs` Rust crate (libgit2 bindings). Requires `features = ["https", "ssh"]` in Cargo.toml for network support. Progress reported via Tauri `Channel` type with 60ms throttle to avoid UI freeze. Cancellation via `Arc<AtomicBool>`. SSH authentication on Windows has known issues with modern key formats — use HTTPS + token as primary auth method. |
| Git pull / push | Stay current with remote, push committed changes | HIGH | `git2-rs` with credential callbacks. Use `auth-git2` crate to simplify credential resolution. Store GitHub/GitLab tokens in native keychain via `tauri-plugin-keyring` (wrapper over Rust `keyring` crate). SSH works on macOS/Linux; HTTPS + token is safest cross-platform option. |
| pilot CLI as embedded sidecar | Users expect `pilot implement` to run directly in the app without installing Python | HIGH | PyInstaller (primary) or Nuitka to compile `pilot` CLI to a self-contained binary. Platform-specific naming: `pilot-cli-x86_64-apple-darwin`, `pilot-cli-aarch64-apple-darwin`, `pilot-cli-x86_64-pc-windows-msvc`, `pilot-cli-x86_64-unknown-linux-gnu`. Bundle via `externalBin` in tauri.conf.json. Spawn from Rust using `app.shell().sidecar("pilot-cli")`. Note: macOS requires the sidecar binary to be code-signed and notarized alongside the main app (known bug #11992 in Tauri). |
| Embedded terminal with streaming output | Developers need to see CLI output in real-time — a static log is insufficient | HIGH | `xterm.js` (5.x) in the WebView as the terminal renderer. `tauri-plugin-pty` (v0.1.1, released 2025-03-10) as the PTY layer — spawns shell, streams data bidirectionally. Alternative: `tauri-terminal` reference implementation (xterm.js + `portable-pty`). Bidirectional: xterm.js `onData` → write to PTY stdin; PTY stdout → xterm.js `write()`. |
| Diff viewer for staged/unstaged changes | Developers reviewing code changes expect a proper diff UI, not raw text | MEDIUM | `@git-diff-view/react` (MrWangJustToDo, supports React/Vue/Solid, GitHub-style UI, syntax highlighting, split/unified views, SSR support). Alternative: `react-diff-view` (otakustay, git unified diff format, more customizable). Parse git diff output from `git2-rs` `diff_index_to_workdir()` and `diff_head_to_index()` on the Rust side; send unified diff string to frontend via IPC. |
| Stage / unstage files and commit | Users cannot skip this — it's the core git workflow | MEDIUM | Rust command: `stage_files(paths: Vec<String>)` → `git2::Repository::index()` → `index.add_path()`. Commit: `repo.commit()` with signature. Unstage: `index.remove_path()`. Frontend: file list with checkboxes (stage/unstage per file), commit message textarea, Commit button. Modeled on GitHub Desktop's minimal workflow. |
| Cross-platform packaging (macOS, Linux, Windows) | Users download an installer, not a dev build | HIGH | `tauri-action` GitHub Action. Matrix: `macos-latest` (ARM64 + x86_64 via `--target` flag), `ubuntu-22.04` (AppImage + .deb), `windows-latest` (NSIS + MSI). macOS requires Apple Developer account for code signing + notarization. Windows requires EV certificate or self-signed (Gatekeeper/SmartScreen warnings otherwise). |
| Native file system permissions (scoped) | App must read/write to workspace directory without user having to approve each file | MEDIUM | `tauri-plugin-fs` with `$HOME/PilotSpace/**` scope in capabilities. Deny path traversal by default. Windows `perMachine` MSI/NSIS installs need admin for `$RESOURCES` writes — use `$APPDATA` instead for workspace config. |

### Differentiators (Competitive Advantage)

Features that make Pilot Space desktop distinct from just running the web app in a browser tab, or from generic tools like GitHub Desktop + terminal + browser.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| One-click "Implement Issue" flow | User selects an issue in the web UI, clicks "Implement", the desktop app clones the repo, creates a branch, and launches `pilot implement` in the embedded terminal — entire loop in one app | HIGH | Requires: IPC message from WebView → Rust trigger → git2-rs clone/branch → sidecar spawn → PTY stream. The sequence ties together every major desktop feature. This is the primary value prop of the desktop app. |
| Inline git commit alongside issue context | Commit and link to the issue without switching apps — commit message pre-populated from issue title | MEDIUM | Read issue context from WebView state via IPC (or shared store). Pre-populate commit message with `[PS-{issue_id}] {issue_title}`. Stage and commit via Rust command. After commit, optionally trigger `git push` and auto-update issue state to "In Review". |
| AI-assisted commit messages | `pilot implement` output used to generate a meaningful commit message, not just "fix stuff" | MEDIUM | After `pilot implement` runs, diff output is available. Pass diff to existing AI infrastructure (via remote FastAPI) to suggest commit message. User edits and approves. Consistent with "human-in-the-loop" principle (DD-003). |
| Streaming terminal for `pilot implement` | Real-time token-by-token output while AI is implementing — users see AI thinking in the terminal | HIGH | Combine PTY streaming with `xterm.js` ANSI rendering. `pilot implement` already outputs streaming text via its own CLI. The PTY layer in Tauri (tauri-plugin-pty) propagates this naturally. |
| App-level credential management | Store GitHub tokens, SSH keys in native OS keychain — never in plaintext config files | MEDIUM | `tauri-plugin-keyring` wrapping OS keychain (Keychain.app on macOS, libsecret on Linux, Windows Credential Manager). UI: Settings → Credentials panel (token input, masked display, test connection button). Tokens used by git2-rs credential callbacks during clone/push. |
| System tray with notification badge | Background monitoring: pilot implement running, CI status — surfaced in system tray while app is minimized | MEDIUM | `tauri-plugin-notification` + system tray (`tray-icon` crate via Tauri). Badge count shows pending AI actions or CI failures. Click tray icon to restore app. Runs as a persistent background process even when window is closed. |
| Auto-update | App self-updates without users going to a website | MEDIUM | `tauri-plugin-updater`. Requires signed update artifacts. Host update manifest on GitHub Releases (static JSON approach). Check for updates on app launch. Show update prompt (non-blocking). Private key held in GitHub Actions secrets, public key in tauri.conf.json. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Bundle FastAPI backend locally in the desktop app | "Offline support" or "enterprise air-gap" | Bundling FastAPI + Supabase + PostgreSQL + Redis into the desktop binary is enormous complexity: port management, migration handling, storage management, crash recovery. Binary size would exceed 500MB. | Remote backend (already decided in PROJECT.md). Enterprise customers self-host the backend. Desktop app connects over HTTPS. The value is the native git/CLI integration, not backend bundling. |
| Full IDE features (IntelliSense, debugger, extensions) | "Replace VS Code" | This is building VS Code. Monaco + language servers + debugger adapters are years of work. Scope creep that abandons the SDLC-platform focus. | Embed xterm.js terminal — users can run their own editor (`code .`) from the terminal. Focus on issue management + git workflow, not code editing. |
| Direct SSH key generation in-app | "Set up SSH so I don't have to" | SSH key generation, adding to SSH agent, registering with GitHub — complex multi-step OS-level operation. Platform differences (macOS Keychain, Windows OpenSSH agent, Linux ssh-agent). | Support HTTPS + Personal Access Token as primary auth (simpler, widely supported). SSH works if user already has it configured on their machine via system ssh-agent. Explicitly out of scope for v1.1. |
| Real-time collaborative terminal sharing | "Pair programming via shared PTY" | Requires WebRTC or WebSocket relay, session multiplexing (tmux-like), permission model. Enormous complexity for a niche feature. | Users share context through issue notes and AI-generated summaries. Async collaboration is the paradigm. |
| Offline git operations against local replica | "Work without internet" | git2-rs works offline for local operations, but issues/notes require the remote FastAPI. Partial offline creates confusing state: what's synced, what's not. | Desktop app requires network. Offline mode deferred to a future milestone where full sync strategy is designed holistically. |
| Git rebase / cherry-pick / interactive rebase UI | "Advanced git workflow support" | Interactive rebase requires a conflict resolution UI, rebase state machine, complex edge case handling. Better to defer to a later iteration. | Expose basic operations: clone, pull, push, stage, commit. Users can drop to the embedded terminal for advanced git operations. |
| Bundled Ollama / local LLM | "Air-gap AI" | 4-8GB model download, GPU memory requirements, model management UI — completely separate product track. BYOK already supports local endpoints via custom OpenAI-compatible providers. | BYOK model already supports local endpoints (users point to their own Ollama server). The desktop app does not host AI itself. |

## Feature Dependencies

```
[Tauri Shell + Next.js WebView]  ← foundation; everything depends on this
    └──requires──> [Next.js static export (output: 'export')]
    └──requires──> [Client Component pattern for Tauri APIs]
    └──requires──> [tauri.conf.json capabilities file]

[Auth Token Bridge]
    └──requires──> [Tauri Shell + Next.js WebView]
    └──requires──> [Deep link handler or localStorage bridge]

[App-Managed Workspace Directory]
    └──requires──> [tauri-plugin-fs with $HOME scope]
    └──requires──> [tauri-plugin-store for config persistence]

[Git Clone / Pull / Push]
    └──requires──> [App-Managed Workspace Directory] (target path)
    └──requires──> [Credential Management] (auth tokens for remote)
    └──requires──> [git2-rs with https + ssh features]

[Pilot CLI Sidecar]
    └──requires──> [Tauri sidecar binary (PyInstaller build)] per platform
    └──requires──> [Auth Token Bridge] (sidecar needs JWT to call backend)
    └──requires──> [App-Managed Workspace Directory] (working directory for sidecar)

[Embedded Terminal (PTY)]
    └──requires──> [tauri-plugin-pty]
    └──requires──> [xterm.js in WebView]
    └──enhances──> [Pilot CLI Sidecar] (streams sidecar output to terminal)

[Diff Viewer]
    └──requires──> [Git Clone] (repo must exist locally)
    └──requires──> [@git-diff-view/react in WebView]
    └──requires──> [Rust command to generate unified diff via git2-rs]

[Stage / Unstage / Commit]
    └──requires──> [Git Clone] (repo must be cloned)
    └──requires──> [Diff Viewer] (users review before staging)
    └──enhances──> [Auth Token Bridge] (commit can trigger push)

[One-Click "Implement Issue" Flow]
    └──requires──> [Git Clone]
    └──requires──> [Pilot CLI Sidecar]
    └──requires──> [Embedded Terminal]
    └──requires──> [Auth Token Bridge] (issue context from WebView)
    └──enhances──> [Stage / Unstage / Commit] (full loop)

[Cross-Platform Packaging]
    └──requires──> [tauri-action GitHub Action]
    └──requires──> [Code signing certs (Apple Developer + Windows EV)]
    └──requires──> [Platform-specific sidecar binaries built per arch]

[Auto-Update]
    └──requires──> [Cross-Platform Packaging]
    └──requires──> [tauri-plugin-updater + signing keys]
    └──requires──> [Update manifest hosted on GitHub Releases]
```

### Dependency Notes

- **Next.js static export is non-negotiable:** Tauri cannot use Next.js SSR or Server Components. The entire frontend must be exported as static HTML/JS. This means any feature using Server Actions, `getServerSideProps`, or route handlers needs to be moved to API calls against the remote FastAPI backend. Audit existing pages before starting.

- **Auth bridge is a prerequisite for sidecar:** The `pilot implement` sidecar needs a valid JWT to call the remote FastAPI. The auth bridge must work before the sidecar can make authenticated API calls.

- **Platform-specific sidecar binaries must be pre-built per target arch:** PyInstaller must run natively on each target OS. GitHub Actions matrix builds handle this: macOS runner builds `aarch64-apple-darwin` and `x86_64-apple-darwin` binaries, Windows runner builds `x86_64-pc-windows-msvc`, Ubuntu runner builds `x86_64-unknown-linux-gnu`. These must be ready before Tauri packaging.

- **git2-rs SSH vs HTTPS:** SSH authentication on Windows has known limitations with libgit2 (modern key formats unsupported). Design credential management around HTTPS + PAT as primary path. SSH works on macOS/Linux as a secondary path.

- **Diff viewer depends on Rust-side diff generation:** The React component renders a unified diff string — it does not call git itself. Rust generates the diff via `git2::Diff` and serializes it to unified diff format before sending over IPC.

## MVP Definition

### Launch With (v1.1)

Minimum viable for the Tauri desktop client to deliver its core value: one-click issue implementation with native git workflow.

- [ ] **Tauri shell + Next.js WebView** — static export config, IPC capabilities, basic window chrome
- [ ] **Auth token bridge** — Supabase session available to Rust commands; single sign-on with existing web auth
- [ ] **App-managed workspace directory** — configurable base path, created on first launch
- [ ] **Git clone + pull + push** — HTTPS + token auth via `git2-rs`; progress streaming via Tauri Channel
- [ ] **pilot CLI sidecar** — PyInstaller binary per platform, spawnable from Rust, stdout streams to PTY
- [ ] **Embedded terminal (xterm.js + tauri-plugin-pty)** — runs arbitrary shell commands; primary output surface for `pilot implement`
- [ ] **Diff viewer** — unified diff rendered by `@git-diff-view/react`; shows staged vs unstaged changes
- [ ] **Stage / unstage / commit UI** — file list with checkboxes, commit message input, commit button
- [ ] **macOS + Linux packaging** — code-signed `.dmg` and `AppImage`/`.deb` via `tauri-action`
- [ ] **Windows packaging** — NSIS installer (can defer EV code signing for v1.x)

### Add After Validation (v1.x)

- [ ] **One-click "Implement Issue" end-to-end flow** — orchestrate clone → branch → sidecar → commit sequence
- [ ] **AI-assisted commit messages** — diff → AI suggestion → user edits → commit
- [ ] **Credential management UI** — Settings panel for GitHub tokens stored in OS keychain
- [ ] **System tray + notification badge** — background monitoring while app is minimized
- [ ] **Auto-update** — `tauri-plugin-updater` with GitHub Releases manifest

### Future Consideration (v2+)

- [ ] **GitLab support** — git2-rs is provider-agnostic; GitLab requires its own token type and API integration (already in Out of Scope for v1.1 per PROJECT.md)
- [ ] **Multi-repo workspace** — manage multiple cloned repos in one app view
- [ ] **Conflict resolution UI** — visual three-way merge for merge conflicts
- [ ] **Branch management UI** — create, checkout, delete, list branches
- [ ] **Offline mode** — full sync strategy to be designed separately

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Tauri shell + Next.js WebView | HIGH | HIGH | P1 |
| Auth token bridge | HIGH | HIGH | P1 |
| App-managed workspace directory | HIGH | LOW | P1 |
| Git clone + pull + push (HTTPS) | HIGH | HIGH | P1 |
| pilot CLI sidecar (PyInstaller) | HIGH | HIGH | P1 |
| Embedded terminal (xterm.js + PTY) | HIGH | MEDIUM | P1 |
| Diff viewer | HIGH | MEDIUM | P1 |
| Stage / unstage / commit UI | HIGH | MEDIUM | P1 |
| macOS + Linux packaging | HIGH | HIGH | P1 |
| Windows packaging | MEDIUM | MEDIUM | P1 |
| One-click "Implement Issue" flow | HIGH | HIGH | P2 |
| AI-assisted commit messages | MEDIUM | MEDIUM | P2 |
| Credential management UI | HIGH | MEDIUM | P2 |
| Auto-update | MEDIUM | MEDIUM | P2 |
| System tray + notification badge | LOW | MEDIUM | P2 |
| GitLab support | MEDIUM | MEDIUM | P3 |
| Multi-repo workspace | LOW | HIGH | P3 |
| Conflict resolution UI | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.1 launch — app is incomplete without these
- P2: Should have, add once P1 is validated and working
- P3: Nice to have, future milestone scope

## Competitor Feature Analysis

| Feature | GitHub Desktop | Tower (macOS) | Pilot Space Desktop Approach |
|---------|---------------|---------------|------------------------------|
| Git UI | Stage/unstage/commit, basic diff, branch management | Full git client — stash, interactive rebase, tags, submodules | Stage/unstage/commit + diff viewer. Advanced ops via terminal. |
| Embedded terminal | No | Yes (Tower 4+) | Yes — primary output for `pilot implement` |
| AI integration | GitHub Copilot suggestions (commit message) | None | `pilot implement` runs full AI implementation; AI-assisted commit message |
| Auth model | GitHub-only OAuth | Any git host via credentials | HTTPS + PAT (via OS keychain); GitHub is primary |
| Issue integration | Opens GitHub.com for issues | None | Native issue list from Pilot Space web UI (shared WebView) |
| Cross-platform | macOS + Windows | macOS only | macOS + Linux + Windows |
| Auto-update | Yes | Yes | Yes (tauri-plugin-updater) |
| App size | ~200MB (Electron-based) | ~50MB (native) | ~30-50MB (Tauri uses system WebView, no bundled Chromium) |

## Existing Assets to Reuse

| Existing Asset | Location | Reuse For |
|----------------|----------|-----------|
| `pilot implement` CLI | `cli/` Python package | Compile to sidecar binary via PyInstaller |
| Next.js App Router frontend | `frontend/` | Embed in Tauri WebView — 95% reuse |
| Supabase Auth PKCE flow | `frontend/src/lib/supabase.ts` | Adapt for deep link callback in Tauri |
| `@tauri-apps/api` | Add to `frontend/package.json` | IPC invoke() calls from Next.js components |
| `shadcn/ui` components | `frontend/src/components/ui/` | Terminal panel, diff viewer, commit UI shells |
| MobX stores | `frontend/src/stores/` | `TerminalStore`, `GitStore` for desktop-specific state |
| TanStack Query | Already in frontend | Git status polling (30s interval) |
| GitHub Actions CI | `.github/workflows/` | Extend with `tauri-action` matrix build step |

## Sources

- [Tauri 2.0 Architecture](https://v2.tauri.app/concept/architecture/) — HIGH confidence (official)
- [Tauri Next.js setup guide](https://v2.tauri.app/start/frontend/nextjs/) — HIGH confidence (official)
- [Tauri Sidecar docs](https://v2.tauri.app/develop/sidecar/) — HIGH confidence (official)
- [Tauri File System plugin](https://v2.tauri.app/plugin/file-system/) — HIGH confidence (official)
- [Tauri Updater plugin](https://v2.tauri.app/plugin/updater/) — HIGH confidence (official)
- [Tauri GitHub Actions pipeline](https://v2.tauri.app/distribute/pipelines/github/) — HIGH confidence (official)
- [macOS Code Signing guide](https://v2.tauri.app/distribute/sign/macos/) — HIGH confidence (official)
- [git2-rs crate](https://crates.io/crates/git2) — HIGH confidence (official crates.io)
- [git2-rs progress + cancellation in Tauri](https://dev.to/yexiyue/how-to-implement-git-clone-operation-progress-display-and-cancellation-in-rust-with-tauri-and-git2-37ec) — MEDIUM confidence (community, verified pattern)
- [tauri-plugin-pty](https://github.com/Tnze/tauri-plugin-pty) — MEDIUM confidence (community plugin, v0.1.1 released 2025-03-10)
- [git-diff-view React component](https://github.com/MrWangJustToDo/git-diff-view) — MEDIUM confidence (community)
- [Supabase + Tauri OAuth deep links](https://medium.com/@nathancovey23/supabase-google-oauth-in-a-tauri-2-0-macos-app-with-deep-links-f8876375cb0a) — MEDIUM confidence (community, recent 2025)
- [tauri-plugin-keyring](https://github.com/HuakunShen/tauri-plugin-keyring) — MEDIUM confidence (community)
- [Tauri + Python sidecar (FastAPI) example](https://github.com/dieharders/example-tauri-v2-python-server-sidecar) — MEDIUM confidence (community reference)
- [git2-rs Windows SSH limitations](https://github.com/rust-lang/git2-rs/pull/876) — HIGH confidence (official git2-rs repo issue)
- [Electron vs Tauri comparison 2025](https://www.dolthub.com/blog/2025-11-13-electron-vs-tauri/) — MEDIUM confidence (technical blog)

---
*Feature research for: Tauri desktop client — embedded WebView, git operations, embedded terminal, diff viewer, sidecar process management, cross-platform packaging*
*Researched: 2026-03-20*
