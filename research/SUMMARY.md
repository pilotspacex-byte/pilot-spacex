# Project Research Summary

**Project:** Pilot Space v1.1 — Tauri Desktop Client
**Domain:** Cross-platform desktop app wrapping an existing Next.js/FastAPI web platform with native git operations, embedded terminal, and AI CLI sidecar
**Researched:** 2026-03-20
**Confidence:** HIGH

## Executive Summary

Pilot Space v1.1 adds a Tauri v2 desktop shell around the existing Next.js 15 frontend, giving developers a native app experience with git operations, an embedded terminal, and one-click `pilot implement` workflows — without abandoning the web platform. The architecture is well-understood: Tauri uses the OS system WebView (WKWebView on macOS, WebKit2GTK on Linux, WebView2 on Windows), which keeps binary size at 10-30MB vs Electron's 200MB, and bridges JavaScript to Rust via JSON-RPC IPC. The remote FastAPI + Supabase backend stays entirely off-device; the desktop adds native capabilities on top of the existing web stack, not a separate backend.

The single most important constraint driving all other decisions is that Tauri cannot run a Node.js server, so Next.js must switch to `output: 'export'` (static HTML/JS) for production Tauri builds. This is a hard requirement that ripples into every phase: dynamic routes with `useParams()`, the `/api/v1/:path*` proxy rewrite, Supabase auth callback route handlers, and `next/image` all need audit and adaptation before any Tauri Rust code can be written. The recommended approach maintains a `NEXT_TAURI=true` build-mode toggle so the existing Docker/web deployment is untouched.

The primary risks are the security handling of Supabase JWTs (must move out of `localStorage` and into OS keychain before shipping), the Windows AV false-positive rate on PyInstaller sidecar binaries (requires EV code signing certificate), and the xterm.js PTY memory leak from high-frequency Tauri IPC events (requires output batching from day one). All three risks have known mitigations documented in official Tauri and upstream project issue trackers. The recommended implementation path runs platform verification (Next.js static export audit) before building any native code, to surface routing and API issues early.

## Key Findings

### Recommended Stack

The Tauri v2 ecosystem is mature and stable (v2.10.3, March 2026). The recommended additions to the existing stack are all verified against official documentation and crates.io. No changes to the existing FastAPI, Next.js, MobX, TanStack Query, shadcn/ui, or Supabase stack are needed — the desktop client sits on top of the web platform as a pure addition. See `STACK.md` for full installation commands, version compatibility table, and code snippets.

**Core technologies:**
- **Tauri v2 (2.10.3 / @tauri-apps/api 2.10.1):** Desktop shell and IPC framework — uses OS system WebView, 10-30MB binary, actively maintained, official Next.js static export support
- **git2-rs (0.20.4, vendored-libgit2):** Rust bindings for libgit2 — handles clone/pull/push/diff/status without requiring `git` on user machine; use `auth-git2` crate for credential handling with loop detection
- **@xterm/xterm (5.5.0) + tauri-plugin-pty:** Embedded terminal emulator — used by VS Code and GitHub Codespaces; the scoped `@xterm/*` package (old `xterm` package is deprecated and must not be used)
- **PyInstaller (6.19.0):** Compiles `pilot` CLI Python binary per platform — no Python required on user machine; v6.13+ explicitly supports uv-managed Python; use `--onedir` not `--onefile`
- **tauri-plugin-shell, tauri-plugin-fs, tauri-plugin-store, tauri-plugin-dialog, tauri-plugin-os:** Supporting Tauri v2 plugins for sidecar spawning, file system access, persistent config, and platform detection
- **react-diff-view (or @git-diff-view/react):** Pure-React diff renderer consuming unified diff strings from git2-rs — ~50KB vs Monaco's 4MB; do not use Monaco for pure diff display
- **tauri-apps/tauri-action (GitHub Actions):** Cross-platform build matrix for macOS ARM64, macOS x86_64, Linux x64, Windows x64 — required because Tauri cannot cross-compile across OS boundaries

### Expected Features

The feature set splits cleanly into P1 (required for v1.1 launch) and P2 (add after v1.1 validation). The full priority matrix is in `FEATURES.md`. The critical dependency chain: Next.js static export is the foundation, auth bridge is required before any authenticated native operation, workspace directory management before git operations, and git operations before the "Implement Issue" end-to-end flow.

**Must have (table stakes — v1.1):**
- Tauri shell with embedded Next.js WebView (static export mode, IPC capabilities file)
- Supabase auth token bridge (OS keychain, not `localStorage`) — required before any authenticated git or sidecar operation
- App-managed workspace directory (`~/PilotSpace/projects/`, configurable via native dialog)
- Git clone, pull, push via HTTPS + PAT (git2-rs; SSH as secondary path)
- pilot CLI as compiled sidecar (PyInstaller `--onedir`, per-platform binary from CI matrix)
- Embedded terminal panel (xterm.js + tauri-plugin-pty, batched output, 10,000-line scrollback)
- Diff viewer (unified diff from git2-rs rendered by react-diff-view)
- Stage / unstage / commit UI (file checklist, commit message input)
- Cross-platform packaging: macOS dmg, Linux AppImage/deb, Windows NSIS

**Should have (differentiators — add after v1.1 validation):**
- One-click "Implement Issue" end-to-end flow (clone → branch → sidecar → commit loop)
- AI-assisted commit messages (diff → FastAPI AI → user edit → commit)
- Credential management UI (Settings panel for GitHub PAT stored in OS keychain)
- Auto-update via tauri-plugin-updater and GitHub Releases manifest
- System tray with notification badge for background AI actions

**Defer (v2+):**
- GitLab support, multi-repo workspace, conflict resolution UI, offline mode, bundled local LLM

**Anti-features (do not build):**
- Bundled FastAPI + Supabase backend (500MB+, incompatible with desktop distribution model)
- Full IDE features (IntelliSense, debugger — scope creep that builds a VS Code competitor)
- Real-time collaborative terminal sharing (WebRTC relay required, niche feature with high complexity)

### Architecture Approach

The architecture adds a new `tauri-app/` top-level directory to the monorepo. The Tauri `src-tauri/` Rust backend owns all native operations (git, PTY, sidecar, auth store) and exposes them to the WebView via typed IPC commands. All `invoke()` calls are centralized in a single `frontend/src/lib/tauri.ts` wrapper module — components never import `@tauri-apps/api` directly, which keeps the codebase deployable as both web app and desktop app and allows full Vitest mocking. The remote FastAPI backend and Supabase remain untouched; only the `NEXT_PUBLIC_API_URL` must be set to the full backend URL in Tauri mode (the `/api/v1/:path*` proxy rewrite is disabled). See `ARCHITECTURE.md` for full system diagrams, all five IPC patterns with code examples, data flows, and the ordered build table.

**Major components:**
1. `tauri-app/src-tauri/` — Rust backend: IPC command modules (`git.rs`, `terminal.rs`, `shell.rs`, `auth.rs`, `workspace.rs`), managed state structs (`GitState`, `TerminalState`, `SidecarState` — each `Mutex<T>` locked independently to prevent contention)
2. `frontend/src/lib/tauri.ts` (new) — typed IPC wrapper layer; `isTauri()` detection; single mock point for Vitest; never scatter `invoke()` calls across components
3. `frontend/src/features/git/` + `frontend/src/features/terminal/` (new) — `GitStore` (MobX), `TerminalStore` (MobX), `DiffViewer.tsx`, `CommitPanel.tsx`, `TerminalPanel.tsx`
4. `pilot-cli` sidecar — PyInstaller binary per platform, spawned from Rust via `tauri-plugin-shell`, output streamed via `Channel<String>` to xterm.js terminal
5. GitHub Actions matrix (4 runners: macos-latest ARM, macos-13 x86, ubuntu-22.04, windows-latest) — CI is the only way to produce all platform binaries; cross-compilation across OS boundaries is not supported by Tauri

### Critical Pitfalls

All pitfalls have HIGH confidence ratings based on official Tauri GitHub issues, upstream libgit2 bugs, and official Next.js issues. See `PITFALLS.md` for full prevention detail, warning signs, and recovery costs.

1. **Next.js dynamic routes break in static export** — `useParams()` returns empty in Tauri production builds. Audit every dynamic route before any Rust work begins; replace path params with query strings for user-data routes (`/issues?id=...`). Confirmed Next.js bug #54393 and #79380.

2. **Server Actions and API route handlers silently vanish** — Supabase PKCE auth callback (`app/api/auth/callback/route.ts`) does not exist in static export output; OAuth silently fails in the built app. Replace with Tauri deep link handler (`tauri-plugin-deep-link`) intercepting `pilotspace://auth/callback`.

3. **Auth JWT in `localStorage` is a security regression** — In Tauri's WebView, all JavaScript runs in the same origin; any malicious npm package can read Supabase tokens. Mandatory: move to OS keychain via `tauri-plugin-keyring` or `tauri-plugin-stronghold` before any release.

4. **xterm.js PTY IPC memory leak** — Tauri Channel callbacks on `window.__TAURI_INTERNALS__.callbacks` are never garbage collected at high frequency (confirmed issues #12724 and #13133). Batch PTY output on Rust side at 16ms intervals; use `Channel` API (not event system) with explicit `channel.close()` on session end.

5. **PyInstaller sidecar antivirus false positives on Windows** — 15-40/70 AV engines flag PyInstaller binaries as malware (heuristic match on extractor pattern). Requires EV code signing certificate ($300-500/year, HSM-backed since June 2023) before Windows distribution; submit binary to Microsoft's whitelist portal 1-3 days before each release.

6. **git2-rs credential callback infinite loop** — libgit2 calls credential callback indefinitely on auth failure; can pin CPU at 100% with empty SSH agent. Use `auth-git2` crate which has built-in loop detection; never use naive `Cred::ssh_key_from_agent()` without attempt counter.

7. **macOS notarization blocks every sidecar binary individually** — Every Mach-O binary in the bundle (main app + sidecar) must be code-signed and notarized. Notarization takes 3-30 minutes and can spike to 60+ minutes. Set CI timeout to 45 minutes; configure hardened runtime entitlements; set up Apple Developer credentials in CI during Phase 1 (not Phase 6) to avoid last-minute blocking.

## Implications for Roadmap

The dependency chain is strictly ordered: static export must work before auth bridge, auth bridge before git operations, git operations before terminal/sidecar, and all of these before cross-platform packaging. Code signing credentials (Apple Developer, Windows EV certificate) must be set up in CI early to avoid blocking at the end of the milestone.

### Phase 1: Tauri Shell and Next.js Static Export

**Rationale:** Foundation for everything else. The Next.js static export mode must be verified clean before any Rust code is written — broken routing or vanishing API routes discovered late are expensive to fix. The `tauri-app/` scaffold and GitHub Actions multi-platform CI matrix must also be set up now so Windows installer issues surface immediately, not at the end of the milestone.
**Delivers:** Working Tauri window displaying the existing Next.js frontend in static export mode, IPC capabilities file, `isTauri()` detection utility, `next.config.ts` build-mode toggle (`NEXT_TAURI=true`), GitHub Actions CI matrix (all 4 platform runners), all Next.js routing issues resolved, `next/image` unoptimized config for Tauri mode.
**Addresses:** Tauri shell + WebView, cross-platform CI skeleton (features P1)
**Avoids:** Pitfalls 1 (`useParams()` breakage in dynamic routes), 2 (API route handlers silently vanish), 3 (`next/image` static export build failure), 11 (Windows CI runner absent from the start)

### Phase 2: Auth Bridge and Credential Security

**Rationale:** The Supabase JWT must be securely bridged to Rust before any authenticated native operation (git push, sidecar with backend calls). This phase also makes the irrevocable security decision about token storage — `localStorage` vs OS keychain. Setting a bad precedent here is expensive to recover from post-launch (requires rotating all affected user sessions).
**Delivers:** `syncTokenToTauriStore()` in root layout, `tauri-auth.ts` + `auth.rs` command, OS keychain integration for auth tokens, Supabase deep link callback (`pilotspace://auth/callback`) replacing the route handler, Windows `useHttpsScheme: true` configured (prevents localStorage reset on app restart).
**Uses:** tauri-plugin-store, tauri-plugin-deep-link, tauri-plugin-keyring
**Avoids:** Pitfall 8 (JWT in localStorage security regression), Pitfall 2 (auth callback route handler)

### Phase 3: Sidecar Compilation Pipeline

**Rationale:** PyInstaller build decisions (`--onedir` not `--onefile`) and CI configuration must be locked before git and terminal work begins. The sidecar naming conventions, Windows AV mitigation choice (Nuitka vs. EV signing), and platform binary placement in `tauri-app/binaries/` must be finalized before they are integrated into later phases. Changing this after CI is configured is expensive.
**Delivers:** `pilot` CLI compiled to platform-specific binaries via PyInstaller `--onedir` (macOS ARM, macOS x86, Linux x64, Windows x64), CI matrix producing artifacts per runner, Tauri `externalBin` configuration, EV certificate procurement or Nuitka build decision, VirusTotal scan gate in CI.
**Uses:** PyInstaller 6.19.0, GitHub Actions matrix (4 runners), tauri-plugin-shell
**Avoids:** Pitfall 5 (orphan processes from PyInstaller `--onefile` on Windows), Pitfall 6 (Windows Defender false positive), Pitfall 9 (macOS sidecar notarization)

### Phase 4: Git Operations

**Rationale:** git2-rs is the core native capability differentiating the desktop app from the web. Once the auth bridge exists and workspace directory management is in place, git operations (clone, pull, push, status, diff) can be built with full credential integration. Credential callback safety must be designed from the first commit.
**Delivers:** `commands/git.rs` (git_clone, git_pull, git_push, git_status, git_diff), `GitState` managed struct, `GitStore` MobX store, credential loop protection via `auth-git2` crate, cross-platform `PathBuf` path handling (no string concatenation), progress streaming via `Channel<GitProgress>` with 2% throttle, app-managed workspace directory with native folder picker via tauri-plugin-dialog.
**Uses:** git2-rs 0.20.4 (vendored-libgit2), auth-git2, tauri-plugin-fs, tauri-plugin-dialog, tauri-plugin-store
**Avoids:** Pitfall 4 (credential infinite loop), Pitfall 10 (Windows path separator corruption from mixed slashes)

### Phase 5: Embedded Terminal and Diff Viewer UI

**Rationale:** The xterm.js terminal panel and git diff/commit UI are the user-visible layers over the native operations built in Phase 4. These can only be built after git operations and the sidecar exist. PTY memory management must be designed correctly from the start — retrofitting batching after the fact requires rewriting the entire IPC layer.
**Delivers:** `TerminalPanel.tsx` (xterm.js, `@xterm/addon-fit`, resize handling via SIGWINCH, 10,000-line scrollback), `useTerminal.ts` hook with batched output (16ms buffer, `requestAnimationFrame` drain), `Channel` API with explicit session lifecycle and `close_terminal(sessionId)` cleanup, `DiffViewer.tsx` (react-diff-view rendering git2-rs unified diff output, virtualized for large diffs), `CommitPanel.tsx` (stage/unstage file list with checkboxes, commit message input, commit button), `GitStatusBar.tsx` (branch, ahead/behind display), `run_pilot_command` Rust command streaming sidecar output to terminal Channel.
**Uses:** @xterm/xterm 5.5.0, @xterm/addon-fit 0.11.0, react-diff-view, tauri-plugin-pty, Channel API
**Avoids:** Pitfall 7 (PTY IPC memory leak), UX pitfalls (no progress indicator, no terminal persistence across navigation)

### Phase 6: Cross-Platform Packaging and Signing

**Rationale:** Packaging is last because it requires all platform binaries (Tauri app + pilot sidecar) to exist. Code signing is mandatory — both for macOS Gatekeeper (app notarization + sidecar signing) and Windows SmartScreen (EV certificate). Cannot be deferred to post-launch without blocking any paid user on Windows.
**Delivers:** macOS `.dmg` (code-signed, notarized, hardened runtime entitlements), Linux `.AppImage` and `.deb`, Windows NSIS `.exe` (EV code signed), full 4-runner GitHub Actions release workflow with artifact upload, Apple Developer credentials configured in CI, Windows EV signing via Azure Key Vault.
**Uses:** tauri-action GitHub Action, Apple Developer Program (codesign + notarytool), Windows EV certificate (HSM-backed via Azure Key Vault)
**Avoids:** Pitfall 9 (macOS notarization failure), Pitfall 6 (Windows AV), Pitfall 11 (WiX `.msi` requires Windows CI runner)

### Phase 7: One-Click Implement Issue Flow (v1.x differentiator)

**Rationale:** This is the primary value proposition of the desktop app — the end-to-end loop from issue selection to committed code via `pilot implement`. It is built after all P1 infrastructure (git, sidecar, terminal, auth) is validated and stable. Attempting to build this end-to-end flow before each component works independently will hide which layer is causing failures.
**Delivers:** Issue → clone → branch → `pilot implement` (streamed to terminal) → stage → commit → push → update issue state. AI-assisted commit message generation via FastAPI AI endpoint. Credential management Settings UI (GitHub PAT in OS keychain).
**Addresses:** One-click Implement Issue flow, AI commit messages, credential management UI (features P2)

### Phase Ordering Rationale

- **Static export first:** `useParams()` and auth callback route handler bugs discovered late cost days to fix across many files; surfacing them before writing any Rust is mandatory.
- **Auth before git:** git push requires credentials; the OS keychain auth bridge must exist before credential storage is designed.
- **Sidecar before terminal:** The terminal's primary purpose is streaming pilot CLI output; the binary must exist to test the integration end-to-end.
- **Git before UI:** The diff viewer and commit panel only display data; they need the git2-rs layer to provide real data.
- **Packaging last, signing setup early:** Configure Apple Developer and Windows EV credentials in CI during Phase 1 (shell setup), not Phase 6, so the final build is not blocked by a 1-2 week certificate procurement delay.

### Research Flags

Phases needing deeper implementation research during planning:
- **Phase 2 (Auth Bridge):** `tauri-plugin-deep-link` for custom URL scheme + Supabase PKCE flow adaptation is community-documented but not officially verified end-to-end. Validate the `pilotspace://auth/callback` flow against the exact Supabase JS client version in use. The `@supabase/ssr` package's cookie-based session model may need replacement with `@supabase/js` for static export.
- **Phase 3 (Sidecar Compilation):** PyInstaller `--onedir` vs Nuitka decision for Windows AV false positives is a judgment call with tradeoffs in build time and AV detection rates. Run VirusTotal benchmarks on a test binary before committing to one toolchain in CI.
- **Phase 5 (Terminal):** `tauri-plugin-pty` is a community plugin (v0.1.1, 2025-03-10), not official Tauri. Evaluate whether `tauri-plugin-shell` streaming (simpler, official) is sufficient for the terminal use case vs. full PTY (bidirectional stdin, SIGWINCH for resize, proper ANSI handling). This decision significantly affects implementation complexity.

Phases with well-documented standard patterns (research optional):
- **Phase 1 (Shell + Static Export):** Official Tauri + Next.js guide is complete and accurate. Follow docs exactly.
- **Phase 4 (Git Operations):** git2-rs patterns are stable and well-documented. Use `auth-git2` crate as documented.
- **Phase 6 (Packaging):** `tauri-action` GitHub Action with official signing guides covers all platforms.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core technologies verified against official Tauri v2 docs and crates.io; version numbers confirmed as of March 2026. Community sources used only for supplementary patterns. |
| Features | HIGH | Feature list derived from Tauri v2 official docs; dependency ordering is logical and verified by architecture research. One MEDIUM caveat: `tauri-plugin-pty` is a community plugin not part of official Tauri. |
| Architecture | HIGH | IPC patterns, static export mode toggle, sidecar lifecycle, and auth store patterns are all directly from official Tauri v2 docs. Community blog posts are consistent with official docs where overlapping. |
| Pitfalls | HIGH | 12 of 14 pitfall sources are official GitHub issues (Tauri, libgit2, Next.js repos) or official docs. All critical pitfalls have confirmed upstream issues with issue numbers cited. |

**Overall confidence:** HIGH

### Gaps to Address

- **`tauri-plugin-pty` stability:** Community plugin (not official Tauri). At implementation time, evaluate whether `tauri-plugin-shell` streaming is sufficient for the full PTY use case (bidirectional stdin, terminal resize via SIGWINCH). If `tauri-plugin-shell` lacks PTY features needed, `tauri-plugin-pty` is the recommended fallback.

- **Windows EV certificate lead time:** Procurement of an HSM-backed EV code signing certificate (required since June 2023 for Windows OV/EV certificates) takes 1-2 weeks. This must be initiated at project kickoff, not during Phase 6, to avoid blocking the release.

- **Next.js dynamic route audit scope:** The codebase has deeply nested dynamic routes (`/[workspaceSlug]/issues/[issueId]`, `/[workspaceSlug]/projects/[projectId]/pages/[pageId]`). The full `useParams()` audit scope is unknown until Phase 1 begins. Budget extra time if more than 5 unique dynamic route patterns are found.

- **Supabase `@supabase/ssr` vs `@supabase/js` in static export:** The `@supabase/ssr` package was designed for Next.js SSR cookie handling. In static export mode, cookie-based session management may require switching to `@supabase/js` with localStorage (then migrating to OS keychain) or adapting the existing SSR helpers. Validate this at Phase 2 start before committing to an auth architecture.

## Sources

### Primary (HIGH confidence)
- [Tauri v2 official docs](https://v2.tauri.app/) — architecture, IPC, sidecar, Next.js integration, signing, GitHub Actions pipeline
- [Next.js static export guide](https://nextjs.org/docs/app/guides/static-exports) — full list of unsupported features in export mode
- [Next.js issue #54393](https://github.com/vercel/next.js/issues/54393) — `useParams()` not supported in `output: export`
- [Next.js issue #79380](https://github.com/vercel/next.js/issues/79380) — dynamic params for client-only SPA with `output: export`
- [Tauri issue #12724](https://github.com/tauri-apps/tauri/issues/12724) — memory leak when emitting events at high frequency
- [Tauri issue #13133](https://github.com/tauri-apps/tauri/issues/13133) — Channel event listeners create memory leak
- [Tauri issue #11686](https://github.com/tauri-apps/tauri/issues/11686) — PyInstaller two-process tree; `child.kill()` leaves child alive on Windows
- [libgit2 issue #3471](https://github.com/libgit2/libgit2/issues/3471) — infinite credential callback loop with SSH agent
- [PyInstaller issue #6754](https://github.com/pyinstaller/pyinstaller/issues/6754) — antivirus false positive rate confirmed ongoing
- [git2 crate docs.rs](https://docs.rs/git2) — version 0.20.4, vendored-libgit2 feature
- [auth-git2 crate](https://crates.io/crates/auth-git2) — credential loop detection
- [tauri-plugin-store](https://docs.rs/crate/tauri-plugin-store/latest) — version 2.4.2
- [@xterm/xterm on npm](https://www.npmjs.com/package/@xterm/xterm) — version 5.5.0
- [Tauri v2 macOS code signing docs](https://v2.tauri.app/distribute/sign/macos/) — notarization requirements
- [Tauri v2 Windows code signing docs](https://v2.tauri.app/distribute/sign/windows/) — HSM requirement since June 2023

### Secondary (MEDIUM confidence)
- [tauri-plugin-pty](https://github.com/Tnze/tauri-plugin-pty) — community PTY plugin (v0.1.1, released 2025-03-10)
- [Supabase + Tauri OAuth deep links](https://medium.com/@nathancovey23/supabase-google-oauth-in-a-tauri-2-0-macos-app-with-deep-links-f8876375cb0a) — PKCE auth flow in Tauri 2.0
- [Tauri v2 + Next.js Monorepo Guide](https://melvinoostendorp.nl/blog/tauri-v2-nextjs-monorepo-guide) — community blog consistent with official docs
- [git2 clone progress in Tauri](https://dev.to/yexiyue/how-to-implement-git-clone-operation-progress-display-and-cancellation-in-rust-with-tauri-and-git2-37ec) — throttle pattern for Channel callbacks
- [Electron vs Tauri 2025](https://www.dolthub.com/blog/2025-11-13-electron-vs-tauri/) — binary size and ecosystem comparison

### Tertiary (LOW confidence)
- [2026 PyInstaller vs Nuitka comparison](https://ahmedsyntax.com/2026-comparison-pyinstaller-vs-cx-freeze-vs-nui/) — binary size and AV detection benchmarks (third-party; run own VirusTotal validation before committing to toolchain)

---
*Research completed: 2026-03-20*
*Ready for roadmap: yes*
