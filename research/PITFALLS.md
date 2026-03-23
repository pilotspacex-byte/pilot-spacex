# Pitfalls Research

**Domain:** Adding Tauri desktop client with Next.js WebView, git operations, CLI sidecar, and embedded terminal to existing web-based SDLC platform (Pilot Space v1.1)
**Researched:** 2026-03-20
**Confidence:** HIGH (based on official Tauri v2 docs, libgit2 upstream issues, and verified community reports)

## Critical Pitfalls

### Pitfall 1: Next.js App Router Dynamic Routes Break With `output: export`

**What goes wrong:**
Pilot Space uses Next.js 15 App Router with deeply nested dynamic routes like `/[workspaceSlug]/issues/[issueId]` and `/[workspaceSlug]/projects/[projectId]/pages/[pageId]`. Tauri cannot run a Node.js server, so the Next.js frontend must be built with `output: 'export'`. In static export mode, `useParams()` on client components does NOT work — the build completes but navigation to dynamic routes renders the wrong content or blank pages. This is a confirmed Next.js bug (issue #54393) that remained open as of 2025.

**Why it happens:**
Static export generates `[issueId]/index.html` files at build time, but in a Tauri WebView the `tauri://localhost` protocol uses file-based routing. When navigating to a dynamic segment using `router.push()`, the WebView loads the static HTML but the `useParams()` hook returns null or incorrect values because there is no server to parse path parameters — the entire app runs as a client-side SPA on a `tauri://` URL scheme.

**How to avoid:**
1. Audit every route that uses `useParams()` before starting the Tauri wrapper. Replace path-based dynamic params with query strings for any route that must work in static export: `/issues/[issueId]` → `/issues?id=[issueId]`.
2. Add `generateStaticParams()` for routes where the full parameter set is known at build time (e.g., static pages). For user-data-driven routes (issues, projects), use query params.
3. Set `output: 'export'` and `trailingSlash: true` in `next.config.js` and run `next build` locally before doing any Tauri integration to surface all static export errors.
4. Configure `tauri.conf.json` `devUrl` to point to `http://localhost:3000` (Next.js dev server) so development uses SSR and you can prototype freely, but ensure production always builds with `output: 'export'`.

**Warning signs:**
- `/issues/[issueId]` renders blank or shows the wrong issue after `next build`
- `useParams()` returns `{}` in production Tauri build but works in dev
- Browser console shows "missing params for route" errors
- `next build` exits without error but `next export` output has zero dynamic route HTML files

**Phase to address:**
Phase 1 (Tauri Shell Setup) — must run `next build` with `output: 'export'` before writing any Tauri Rust code. Fix all routing issues before building the shell.

---

### Pitfall 2: Server Actions and API Routes Silently Vanish in Static Export

**What goes wrong:**
Any Next.js Route Handler (`app/api/*/route.ts`) and all Server Actions are completely dropped in `output: 'export'`. They do not error during build — they simply do not exist in the output. If the frontend codebase has any API routes (e.g., `app/api/auth/callback/route.ts` for Supabase OAuth), they will not function in the Tauri WebView.

**Why it happens:**
Pilot Space's existing frontend relies on Supabase's `@supabase/ssr` package, which requires server-side cookie handling via Route Handlers for auth callback. The `app/api/auth/callback/route.ts` pattern that handles the PKCE exchange requires a running Next.js server. In static export, this handler does not exist.

**How to avoid:**
1. Audit `frontend/src/app/api/` for all Route Handlers. Every one of these must be replaced with Tauri-side logic (Rust commands or deep link handling).
2. Replace Supabase PKCE auth callback handler with a Tauri deep link handler (`tauri-plugin-deep-link`) that intercepts `pilotspace://auth/callback` and passes the token to the WebView via IPC.
3. Do not use Next.js middleware (`middleware.ts`) — it requires a server runtime and is silently dropped in static export.
4. Verify by running `next build && ls out/` — any API route that was silently dropped will be absent, confirming you have not shipped dead routes.

**Warning signs:**
- Auth redirects fail silently in the built Tauri app but work in `next dev`
- `middleware.ts` redirects stop working in production Tauri build
- OAuth callback URLs return 404 after login
- `next build` logs show "API routes cannot be used with output: export" warning that was dismissed

**Phase to address:**
Phase 1 (Tauri Shell Setup) — before auth bridge work begins. Document every Route Handler that must be migrated or eliminated.

---

### Pitfall 3: `next/image` Breaks the Static Export Build

**What goes wrong:**
Pilot Space uses `next/image` components throughout the UI (user avatars, integration icons, logos). In `output: 'export'` mode, `next/image` requires `images: { unoptimized: true }` in `next.config.js`. Without it, the build fails with `Error: Image Optimization using the default loader is not compatible with export`. This blocks the entire Tauri build pipeline.

**Why it happens:**
Next.js's default image optimization API requires a running server to resize and cache images on-demand. Static export has no server, so Next.js refuses to build unless you explicitly opt out of optimization.

**How to avoid:**
1. Add `images: { unoptimized: true }` to `next.config.js` under an environment check that only applies this in Tauri builds (to avoid degrading the web deployment).
2. Alternatively, replace `next/image` with a standard `<img>` tag for Tauri-specific builds, or use a third-party static optimizer (`next-image-export-optimizer`) that pre-optimizes images at build time.
3. Use a build-time env variable `TAURI_BUILD=true` to conditionally toggle image config so the web deployment retains optimization.

**Warning signs:**
- `next build` fails with "Image Optimization using the default loader is not compatible with export"
- Images display but are unoptimized and large, causing slow initial render in WebView
- Responsive image sizes missing in static output

**Phase to address:**
Phase 1 (Tauri Shell Setup) — first `next build` with `output: 'export'` will surface this immediately.

---

### Pitfall 4: git2-rs Credential Callback Infinite Loop on Failed Authentication

**What goes wrong:**
When implementing git clone/pull/push using git2-rs, the credential callback can be called indefinitely if authentication fails. libgit2 will keep asking for credentials until it receives a hard error or valid credentials. With SSH agent authentication on macOS, if the SSH agent has no valid key for the remote, the callback loops at nearly 100% CPU. With HTTPS and token auth, if the token is stale or rejected, the same loop occurs.

**Why it happens:**
libgit2's authentication model calls the credential callback every time authentication fails, expecting the application to either provide new credentials or return an error to stop. git2-rs does not add automatic loop detection. A naive callback that always returns `Cred::ssh_key_from_agent(username)` will loop forever on an empty SSH agent.

**How to avoid:**
1. Track how many times the credential callback has been called within a single operation. After 3 attempts, return `Err(git2::Error::from_str("auth failed"))` to break the loop.
2. Use the `auth-git2` crate (verified crates.io, actively maintained) instead of implementing credential logic from scratch — it handles SSH agent fallback, key file fallback, and credential helper integration with loop detection built in.
3. Separate the three credential types explicitly: SSH key from agent → SSH key from `~/.ssh/id_*` file → HTTPS token from OS keychain. Each type gets one attempt.
4. Surface authentication errors to the UI immediately rather than retrying silently. Show a credential input dialog on first failure rather than burning retries in the background.

**Warning signs:**
- Git clone hangs indefinitely with no progress indicator
- Tauri app CPU spikes to 100% during a git operation
- App becomes unresponsive during clone/pull/push
- SSH agent is empty (no keys loaded) but git operations don't fail fast

**Phase to address:**
Phase 3 (Git Operations) — write the credential callback with loop detection from the start. Do not prototype with `Cred::default()`.

---

### Pitfall 5: PyInstaller `--onefile` Sidecar Fails to Clean Up on Windows App Exit

**What goes wrong:**
When `pilot implement` is compiled with PyInstaller in `--onefile` mode and run as a Tauri sidecar, closing the Tauri app leaves orphan Python processes running on Windows. PyInstaller `--onefile` mode extracts to a `_MEIxxxxxx` temp directory on every startup and spawns a separate extraction process before the actual Python process. Tauri's `child.kill()` only kills the wrapper process, leaving the inner Python interpreter running. On Windows, this also locks the temp directory, causing the next launch to extract to a different temp path.

**Why it happens:**
PyInstaller `--onefile` creates a two-process tree: a bootstrap extractor process that creates a temp directory, then spawns the actual application process. Tauri's sidecar kill signal reaches the parent bootstrap process but not the child Python interpreter. On Windows specifically, the parent-child process relationship means `SIGTERM` to the parent does not propagate to children.

**How to avoid:**
1. Use PyInstaller `--onedir` mode instead of `--onefile` for the sidecar. This is faster to start (no extraction), predictable temp directory, and the single process is killable. Bundle the onedir output as `bin/pilot-implement-{target-triple}/`.
2. If `--onefile` is required for distribution size: use Tauri's `AppHandle::on_window_event` to listen for window close events and send a shutdown signal to the sidecar before the Tauri process exits. Give it 2 seconds to clean up before force-killing.
3. Use Nuitka for compilation instead of PyInstaller — Nuitka compiles Python to C extensions, produces a single true executable (not an extractor), and does not have the two-process problem.
4. Add a startup lock file in the sidecar that prevents double-launch (the same temp directory being used by two instances).

**Warning signs:**
- Task Manager shows Python processes persisting after app close on Windows
- Second launch of the app fails because temp directory is locked
- Sidecar startup takes 10-25 seconds on Windows (extraction on every start)
- `child.kill()` returns success but the Python process is still visible

**Phase to address:**
Phase 2 (Sidecar Compilation) — choose `--onedir` vs `--onefile` before the sidecar build pipeline is designed. Changing this after CI is configured is expensive.

---

### Pitfall 6: Sidecar Binary Triggers Windows Defender False Positive

**What goes wrong:**
Python executables compiled with PyInstaller are consistently flagged as malware by Windows Defender and VirusTotal. The false positive rate for PyInstaller binaries is approximately 15-40 AV engines out of 70, regardless of the binary content. This blocks enterprise deployment — Windows Defender will quarantine the sidecar on installation or first run, preventing `pilot implement` from executing. Nuitka has a lower false positive rate but Windows Defender has also flagged it (Nuitka issue #2495).

**Why it happens:**
PyInstaller's bundling mechanism (UPX compression + Python runtime extraction) matches known malware packer signatures. The bootstrap extraction pattern is identical to self-extracting malware droppers. Antivirus engines use heuristics, not just signatures, and Python bundlers trigger many heuristics simultaneously.

**How to avoid:**
1. Code sign the sidecar binary with an Authenticode certificate (EV or OV). EV code signing certificates dramatically reduce false positive rates because they require hardware HSM storage (Azure Key Vault) and are associated with a verified identity. This is mandatory for Windows distribution.
2. Prefer Nuitka over PyInstaller — Nuitka compiles Python to real C extensions without the extractor pattern, giving cleaner binary output with lower AV hit rates.
3. Submit the signed binary to Microsoft's malware submission portal (`https://www.microsoft.com/en-us/wdsi/filesubmission`) before each release to get the specific binary whitelisted. This takes 1-3 business days.
4. Budget for an EV code signing certificate in the project timeline. Azure Key Vault HSM-backed certificates cost approximately $300-500/year and the CI setup for signing adds 2-3 days of work.

**Warning signs:**
- VirusTotal scan of the compiled binary shows >5 AV detections
- Internal testing on Windows Enterprise machines shows Defender blocking on install
- Users report the app is quarantined before it launches
- Windows SmartScreen blocks the installer itself (separate from Defender)

**Phase to address:**
Phase 2 (Sidecar Compilation) AND Phase 6 (Cross-Platform Packaging). Code signing setup must happen before Windows packaging, but the false positive mitigation (Nuitka choice) must happen in Phase 2.

---

### Pitfall 7: xterm.js PTY IPC Flooding Causes Memory Leak in Tauri WebView

**What goes wrong:**
Terminal output from long-running commands (build scripts, `pilot implement`) can generate thousands of data chunks per second. Each PTY output chunk triggers a Tauri event emitted from Rust to the WebView. Tauri's event system has a confirmed memory leak (issue #12724) where the `Channel` API's `transformCallback` function registers callbacks on the `window` object but never cleans them up. After sustained terminal output, WebView memory climbs continuously, eventually causing the tab to crash.

**Why it happens:**
Tauri's IPC uses `transformCallback` to register each callback as a property on `window.__TAURI_INTERNALS__.callbacks`. Each `Channel.onmessage` call that isn't explicitly cleaned up creates a permanent reference. For high-frequency PTY output, this means thousands of uncollectable callbacks accumulate per terminal session.

**How to avoid:**
1. Do NOT use Tauri's event system (`emit_all` / `listen`) for continuous PTY output. Use `tauri::ipc::Channel` (the streaming API in Tauri v2) and call `channel.close()` when the command exits to release the callback registration.
2. Batch PTY output on the Rust side: accumulate output for 16ms (one frame) before sending to the WebView. This reduces the IPC message rate from potentially thousands/second to ~60/second.
3. In the frontend, use xterm.js's `terminal.write()` inside a `requestAnimationFrame` loop to drain a buffer rather than calling `write()` on every IPC message.
4. Implement an explicit terminal session lifecycle: `open_terminal()` returns a session ID, all output goes through that session, `close_terminal(sessionId)` cleans up the Rust PTY and the frontend channel listener.
5. Set a hard buffer limit (e.g., 10,000 lines) in xterm.js via `scrollback` option to bound memory on the frontend side.

**Warning signs:**
- `window.__TAURI_INTERNALS__.callbacks` object growing unboundedly (check in browser devtools)
- WebView memory climbing continuously during a running terminal session
- Terminal slows down significantly after 5+ minutes of output
- Tauri app RAM usage grows from 200MB to 1GB+ during a build command

**Phase to address:**
Phase 4 (Embedded Terminal) — design the PTY-to-xterm.js bridge with batching from the start. Retrofitting this after the fact requires rewriting the entire IPC layer.

---

### Pitfall 8: Supabase Auth Token Stored in localStorage is Accessible to Any Code Running in WebView

**What goes wrong:**
Supabase's `@supabase/ssr` client stores the JWT access token and refresh token in `localStorage`. In a Tauri WebView, any injected JavaScript or compromised dependency in the Next.js bundle can read the token directly from `localStorage`, extract it, and use it to authenticate as the user against the Pilot Space API. This is worse than a web browser context because the WebView is not sandboxed by the same-origin policy in the same way — malicious code in the Tauri app context has access to OS resources.

**Why it happens:**
`localStorage` was designed for web browsers where the same-origin policy limits access. In Tauri's WebView, all JavaScript on the page runs in the same origin (`tauri://localhost`), so any malicious package in `node_modules` that executes in the WebView can read auth tokens.

**How to avoid:**
1. Move JWT storage out of `localStorage` and into the OS credential store (macOS Keychain, Windows Credential Manager, Linux Secret Service) using `tauri-plugin-keychain` or the `tauri-plugin-stronghold` plugin.
2. Architect a clean separation: the Rust backend holds the raw Supabase JWT. The WebView makes a Tauri IPC call (`invoke('get_auth_header')`) to get just the `Authorization` header value for the current request. The token itself never touches WebView JavaScript memory.
3. Enable Content Security Policy (CSP) in `tauri.conf.json` to prevent inline script injection and restrict `connect-src` to known API domains. This does not fully protect localStorage but reduces the attack surface.
4. For the auth flow: use `tauri-plugin-deep-link` to handle the OAuth callback in Rust, exchange the code for tokens in Rust, and store only in the OS keychain. The WebView receives a session signal (not the raw token) and re-fetches its Supabase client state.

**Warning signs:**
- Supabase auth tokens visible in Chrome DevTools `Application > Local Storage` within the Tauri WebView
- Supply chain audit shows third-party npm packages with access to `window.localStorage`
- Sentry or error tracking sending auth tokens in breadcrumbs (token accidentally serialized)
- Tauri CSP headers not configured in `tauri.conf.json`

**Phase to address:**
Phase 1 (Auth Bridge) — this is the first security-critical decision. Do not ship a prototype with `localStorage`-based token storage, even temporarily, as it sets a precedent that is hard to refactor later.

---

### Pitfall 9: macOS Notarization Blocks Every Sidecar Binary Individually

**What goes wrong:**
On macOS, every embedded binary in a Tauri app bundle must be individually code-signed AND notarized. The `pilot-implement-aarch64-apple-darwin` sidecar binary, the main Tauri binary, and any embedded helper tools all need valid Apple Developer signatures. If even one binary in the bundle is unsigned, Gatekeeper blocks the entire app. Additionally, `tauri-action` in GitHub Actions runs notarization (upload to Apple, wait for response) for every architecture, adding 10-20 minutes per build and sometimes timing out.

**Why it happens:**
Apple's Gatekeeper verifies every Mach-O binary in an app bundle's `MacOS/` and `Frameworks/` directories. Tauri includes the sidecar in the bundle automatically, but does not automatically code-sign it — the developer must configure `codesign` arguments in `tauri.conf.json` under `bundle.macOS.signingIdentity` and ensure the sidecar is listed in `externalBin`. The notarization wait time (typically 3-10 minutes) can occasionally spike to 60+ minutes, causing CI timeout failures.

**How to avoid:**
1. Configure `tauri.conf.json` with `"signingIdentity": "Developer ID Application: Your Name (TEAMID)"` so all binaries in the bundle are signed with the same identity.
2. Use hardened runtime entitlements (`tauri.conf.json > bundle.macOS.entitlements`) — notarization requires hardened runtime since 2019. Without it, notarization submission will fail immediately.
3. Set CI timeout for the macOS notarization step to 30 minutes (not the default 10), and add retry logic around the `notarytool` submission step.
4. Build `aarch64-apple-darwin` and `x86_64-apple-darwin` as separate CI jobs in parallel (not sequential) to halve total macOS CI time.
5. Do not build universal binaries unless specifically required — two separate builds (`aarch64` + `x86_64`) are simpler to manage and debug than universal binary edge cases with the sidecar.
6. Store the Apple certificate as a base64-encoded `.p12` in GitHub Secrets (`APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`). The `tauri-action` GitHub Action reads these automatically.

**Warning signs:**
- macOS CI job runs for >15 minutes with no output (notarization hung)
- Gatekeeper blocks the `.dmg` with "can't be opened because it is from an unidentified developer"
- Sidecar binary launches but macOS shows security warning for the binary separately
- `xcrun notarytool submit` exits with "Package Invalid" — missing hardened runtime

**Phase to address:**
Phase 6 (Cross-Platform Packaging) — but set up Apple Developer credentials in CI during Phase 1 (Shell Setup) to avoid blocking at the end of the milestone.

---

### Pitfall 10: Cross-Platform Path Handling in git2-rs Operations Corrupts Paths on Windows

**What goes wrong:**
Git repository paths passed from the Next.js frontend (JavaScript) to Rust via IPC use forward slashes (`/`). git2-rs on Windows expects either forward slashes or backslashes, but the OS APIs in Rust use `Path` / `PathBuf` which normalize to backslashes. When constructing paths programmatically (e.g., repo root + `/` + relative file path for staging), naive string concatenation produces mixed-separator paths like `C:\Users\user/repos/project/src/file.ts` that cause git2-rs operations to fail with `ENOENT`.

**Why it happens:**
JavaScript always sends paths with forward slashes. Rust's `std::path::Path` normalizes to OS-native separators. If the Tauri IPC handler receives a string path from JavaScript and joins it with `format!("{}/{}", base, relative)` instead of using `Path::new(base).join(relative)`, the result is an invalid path on Windows.

**How to avoid:**
1. Never build file paths with string concatenation in the Rust backend. Always use `std::path::PathBuf` and `.join()`. Example: `PathBuf::from(base_path).join(relative_path)` handles separator normalization automatically.
2. When receiving paths from the JavaScript frontend over IPC, parse them with `PathBuf::from(incoming_string)` immediately and work exclusively with `PathBuf` in Rust until the path needs to be serialized back to JSON (where `.to_string_lossy()` is acceptable).
3. For the workspace directory configuration (user-configurable base path), store the canonical form using `fs::canonicalize()` which returns the absolute platform-native path. Store this canonical path in the Tauri app config, not the user-input string.
4. On Windows, test with paths that have spaces (e.g., `C:\Users\John Doe\repos\`) as spaces in Windows paths trigger additional quoting requirements in any shell execution.

**Warning signs:**
- `git2::Error` with `ENOENT` or "path does not exist" on Windows when the path visually looks correct
- File staging fails on Windows but works on macOS/Linux
- Repository discovery (`Repository::discover()`) fails for valid repos on Windows
- Paths with UNC format (`\\server\share`) causing panics in path manipulation code

**Phase to address:**
Phase 3 (Git Operations) — write platform-path test cases on Windows from the first commit of the git operations module.

---

### Pitfall 11: Tauri `.msi` Installer Can Only Be Built on Windows

**What goes wrong:**
The Windows `.msi` installer requires WiX Toolset, which only runs on Windows. The Tauri `tauri-action` GitHub Action handles this by running the Windows build job on a `windows-latest` runner, but if the team uses only macOS or Linux development machines, there is no local way to test the Windows installer. The NSIS installer (alternative to WiX) can be cross-compiled from Linux, but produces `.exe` (not `.msi`) and has different behavior.

**Why it happens:**
WiX is a Windows-only tool. Tauri's bundler shells out to WiX for `.msi` creation. Cross-compilation of Windows apps from macOS/Linux is technically possible for the Rust binary but not for the installer wrapper.

**How to avoid:**
1. Accept that Windows installer testing must happen in CI (`windows-latest` runner) or a Windows VM. Do not spend time trying to cross-compile `.msi` locally on macOS.
2. Use NSIS (`.exe` installer) as the primary Windows distribution format and `.msi` as a secondary format. NSIS can be cross-compiled. Configure `tauri.conf.json` to produce both: `"bundle": { "windows": { "nsis": {...}, "wix": {...} } }`.
3. Set up the GitHub Actions matrix early (Phase 1) with jobs for all three platforms so Windows installer issues surface in CI before the packaging phase.
4. Use `act` (GitHub Actions local runner) on macOS to simulate the Windows job workflow without pushing to GitHub. Note that `act` uses Docker containers and cannot run actual Windows builds, but it validates the workflow YAML.

**Warning signs:**
- CI workflow has only `ubuntu-latest` and `macos-latest` runners (Windows build missing)
- `.msi` installer silently fails during CI and no artifact is uploaded
- Windows runner in CI uses the wrong Rust target (`x86_64-pc-windows-gnu` instead of `x86_64-pc-windows-msvc`)
- WiX build fails because a required WiX component version is not installed on the CI runner

**Phase to address:**
Phase 1 (Tauri Shell Setup) — add all three CI runner jobs in the first GitHub Actions workflow file. Fix immediately when Windows CI fails rather than deferring.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use `localStorage` for JWT token in Tauri | Supabase JS client works without modification | Token exposed to any WebView JavaScript; security regression; enterprise customers will flag in pentest | Never — migrate to OS keychain before first release |
| Ship sidecar unsigned on Windows | Skips $300-500 EV cert cost | Windows Defender quarantines binary; enterprise Windows machines block installation; blocks any paid user | Never for production; acceptable for internal dev builds only |
| PyInstaller `--onefile` for sidecar | Single file, easy to copy | 10-25s startup delay; orphan processes on Windows; temp directory lock issues; higher AV false positive rate | Only acceptable for internal tooling, never for end-user sidecar |
| Skip batching for PTY output → xterm.js | Simplest implementation | Memory leak via uncollected Tauri channel callbacks; WebView OOM crash during long builds | Never — batch from day one; the overhead is trivial |
| Single CI job building all platforms on macOS | Simpler workflow YAML | Windows `.msi` cannot be built on macOS; cross-compilation misses Windows-specific bugs | Never — three separate jobs are required |
| String concatenation for file paths in Rust | Readable code | Invalid paths on Windows due to separator mismatch; fails only in production | Never — use `PathBuf::join()` always |
| Rely on system git instead of git2-rs | Zero compilation dependency | System git may not exist on user machine; git version differences cause behavioral differences; no progress reporting | Only for local dev and debugging; never in production sidecar |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Next.js + Tauri | Running `next dev` and assuming production behavior matches | Build with `output: 'export'` locally on every PR that touches routing. Divergence between dev and export modes causes surprises in Phase 3+ |
| Supabase Auth + Tauri deep links | Registering `tauri://` as OAuth redirect URI in Supabase | Use a custom deep link scheme (`pilotspace://auth/callback`) registered with the OS via `tauri-plugin-deep-link`, NOT `tauri://` which is the WebView internal protocol |
| git2-rs + macOS Keychain | Expecting git2-rs to automatically use macOS Keychain for HTTPS credentials | macOS Keychain integration requires the `git2_credentials` or `auth-git2` crate — raw git2-rs has no keychain awareness |
| PyInstaller sidecar + Tauri | Using `Command::new("pilot-implement")` instead of `Command::new_sidecar("pilot-implement")` | `new_sidecar()` resolves the architecture-suffixed binary path automatically and registers it in Tauri's cleanup on app exit; bare `Command::new()` skips both |
| xterm.js + Tauri IPC | Using `window.__TAURI__.event.listen()` for PTY data stream | Use `tauri::ipc::Channel` (Tauri v2 streaming API) rather than the event system for continuous streams — the event system has memory leaks at high frequency |
| GitHub Actions + macOS notarization | Setting CI timeout to default 10 minutes | Notarization can take 3-30 minutes; set timeout to 45 minutes and add a retry step for the `notarytool` submission |
| Windows code signing + Azure Key Vault | Using a local exportable `.pfx` certificate | Since June 2023, new OV/EV code signing certificates require HSM storage; configure `tauri-action` to use Azure Key Vault via `AZURE_KEY_VAULT_URI` env vars |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| High-frequency PTY events through Tauri IPC | WebView memory grows by 10-50MB/min during active terminal; eventual OOM | Batch output on Rust side at 16ms intervals; use Channel API with explicit cleanup | First build command that generates >100 lines/second of output |
| Loading full git history for diff viewer | Diff viewer hangs for repos with >1000 commits | Paginate commit history (50 at a time); load diff lazily only when commit is clicked | Repos with >500 commits |
| git2-rs blocking the Tauri main thread | UI freezes during git clone (can take minutes) | Run all git2-rs operations on a Tokio background task via `tauri::async_runtime::spawn_blocking` | Any clone of a repo >50MB |
| WebView rendering large unified diffs | Browser tab stalls on 10,000+ line diffs | Virtualize diff lines (only render visible lines); limit diff to first 5,000 lines with "Show more" | Any diff of a generated file or lock file |
| Sidecar startup on every `pilot implement` invocation | Command takes 20+ seconds before doing work | Implement a long-running sidecar server mode that accepts commands via stdin/IPC and stays alive between invocations | First use by any user expecting CLI-speed response |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing JWT in `localStorage` in Tauri WebView | Any malicious npm package can exfiltrate the user's Supabase JWT and impersonate them | Store tokens exclusively in OS keychain via `tauri-plugin-keychain`; WebView receives only session signals via IPC |
| Allowing arbitrary shell commands via `shell:allow-execute` capability | Malicious content loaded in WebView can execute arbitrary OS commands | Use Tauri v2 capability scoping: restrict shell plugin to specific pre-approved command patterns; never grant `shell:allow-execute` with `*` arguments |
| Filesystem scope too permissive (`**/*`) | WebView JavaScript can read any file on the user's machine | Scope `fs` plugin to specific directories (`$APPDATA/PilotSpace`, `$HOME/PilotSpace/projects`) using `tauri.conf.json` scopes |
| Logging git credentials during debugging | SSH keys or HTTPS tokens written to log files or crash reports | Never log `Cred::*` values; implement a `Debug` impl that redacts sensitive fields; check `RUST_LOG` level before enabling debug output |
| Deep link URL not validated before processing | OAuth callback deep link could be crafted to inject a forged token | Validate that deep link origin matches the expected Supabase project URL; verify the token signature server-side, not just accept the deep link payload |
| Sidecar allowed to access all network resources | Compromised sidecar can exfiltrate data to arbitrary hosts | Use Tauri's process capability scoping to limit sidecar to specific allowed origins; the pilot CLI should only reach the configured Pilot Space backend URL |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress indicator during git clone | Users think the app froze when cloning a large repo | Show a progress bar with bytes transferred and estimated time; git2-rs provides `RemoteCallbacks::transfer_progress` for this |
| PTY session not persisting across navigation | User opens terminal, navigates away, terminal state lost | Store xterm.js `serialize-addon` snapshot in memory when terminal panel is hidden; restore state on re-open |
| Sidecar startup delay not communicated | `pilot implement` runs but 10+ seconds pass with no feedback | Show a "Starting pilot CLI..." loading state immediately on first invocation; keep sidecar alive between commands |
| Native file dialogs not used for directory picker | Users must type full paths for workspace directory setup | Use `tauri-plugin-dialog` `open()` with `directory: true` for the workspace base path picker |
| No error distinction between network failures and auth failures in git operations | "Clone failed" with no actionable information | Map git2-rs error codes to user-facing messages: `GIT_ENOTFOUND` → "Repository not found", `GIT_EAUTH` → "Authentication failed — check your credentials" |

## "Looks Done But Isn't" Checklist

- [ ] **Next.js static export:** Often missing dynamic route support — verify every URL pattern in the app loads correctly in a `next build` + `out/` static server, not just in `next dev`
- [ ] **Auth bridge:** Often missing token refresh handling — verify that a 1-hour JWT expiry correctly triggers a refresh from the OS keychain, not a logout
- [ ] **Git credentials:** Often missing SSH key passphrase prompt — verify that an encrypted SSH key prompts the user (not silently fails) before giving up
- [ ] **Sidecar lifecycle:** Often missing cleanup on crash — verify that if the Tauri app is force-killed (not cleanly exited), the sidecar process is also terminated within 5 seconds
- [ ] **macOS notarization:** Often missing entitlements file — verify the `.entitlements` file includes `com.apple.security.cs.allow-jit` if the WebView requires it; notarization will fail silently without it
- [ ] **Windows installer:** Often missing VC++ runtime — verify the `.msi` bundles the MSVC runtime or includes a prerequisite check, otherwise the app fails to start on clean Windows installs
- [ ] **xterm.js terminal:** Often missing resize handling — verify that resizing the terminal panel sends `SIGWINCH` to the PTY and xterm.js re-wraps long lines
- [ ] **Cross-platform paths:** Often missing UNC path handling on Windows (`\\server\share`) — verify path normalization handles Windows UNC paths without panicking
- [ ] **Diff viewer:** Often missing binary file handling — verify the diff viewer shows "Binary files differ" instead of crashing on `.png`, `.jar`, or `.wasm` diffs
- [ ] **CI matrix:** Often missing `upload-artifact` for all three platforms — verify CI produces downloadable artifacts for macOS ARM, macOS x86, Linux, and Windows on every PR

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Dynamic routes broken in static export | HIGH | Audit all `useParams()` calls across the full Next.js app (can be 50+ occurrences); replace with query params; update all `router.push()` callsites |
| JWT stored in localStorage (security regression) | HIGH | Implement OS keychain storage; audit logs for any token leaks; rotate all affected user sessions; force re-login |
| PyInstaller sidecar orphan processes on Windows | MEDIUM | Rebuild sidecar with `--onedir` mode or switch to Nuitka; update CI pipeline; no user data impact but requires new release |
| PTY memory leak in WebView | MEDIUM | Replace event-based PTY stream with Channel API; requires rewriting the terminal IPC bridge but no Rust side changes |
| macOS notarization failure in CI | LOW | Add hardened runtime entitlements to `tauri.conf.json`; re-trigger CI; typically resolved in one build cycle |
| Windows code signing not set up before release | HIGH | Must acquire and configure EV certificate; submit existing builds to Microsoft for whitelisting; 1-2 week delay |
| git2-rs credential loop causing hang | MEDIUM | Add attempt counter to credential callback; release hotfix patch; no user data impact |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Next.js dynamic routes break in static export | Phase 1: Tauri Shell + Next.js Export | Run `next build` with `output: 'export'`; navigate to every dynamic route in the built app |
| Server Actions / API routes vanish | Phase 1: Tauri Shell + Next.js Export | Audit `app/api/` directory; verify auth callback works via deep link |
| `next/image` breaks static export build | Phase 1: Tauri Shell + Next.js Export | First `next build` will fail immediately; add `unoptimized: true` before proceeding |
| Auth token stored in localStorage | Phase 2: Auth Bridge | Security test: open Tauri DevTools, check Application > Local Storage — must be empty of JWT |
| Sidecar binary AV false positive | Phase 2: Sidecar Compilation | Run VirusTotal scan on compiled binary before CI is finalized; target <5 detections |
| PyInstaller orphan processes | Phase 2: Sidecar Compilation | Test app force-kill on Windows; verify no Python processes remain after 5 seconds |
| git2-rs credential loop | Phase 3: Git Operations | Test with empty SSH agent + invalid token; operation must fail with error within 3 seconds |
| Cross-platform path corruption | Phase 3: Git Operations | Run integration tests on Windows runner with paths containing spaces and UNC format |
| xterm.js PTY memory leak | Phase 4: Embedded Terminal | Run a 10-minute build command; monitor WebView memory in Tauri DevTools; must not grow unboundedly |
| macOS notarization blocks sidecar | Phase 6: Cross-Platform Packaging | Verify entire `.app` bundle passes `spctl --assess --verbose` and `codesign --verify` |
| Windows `.msi` requires Windows CI runner | Phase 1: CI Setup | Add `windows-latest` job in first commit of `.github/workflows/build.yml` |

## Sources

- [Tauri v2 Next.js setup guide](https://v2.tauri.app/start/frontend/nextjs/) — static export requirement, image config (HIGH confidence, official docs)
- [Next.js issue #54393: `useParams()` not supported with `output: export`](https://github.com/vercel/next.js/issues/54393) — confirmed upstream bug (HIGH confidence, official repo)
- [Next.js issue #79380: Cannot use dynamic params for client-only SPA with `output: export`](https://github.com/vercel/next.js/issues/79380) — still open as of 2025 (HIGH confidence)
- [Tauri sidecar documentation](https://v2.tauri.app/develop/sidecar/) — binary naming, target triple suffix, permissions (HIGH confidence, official docs)
- [Tauri issue #11686: PyInstaller creates two processes, `child.kill()` leaves parent](https://github.com/tauri-apps/tauri/issues/11686) — confirmed Windows bug (HIGH confidence)
- [Tauri issue #12724: Memory leak when emitting events](https://github.com/tauri-apps/tauri/issues/12724) — confirmed memory leak (HIGH confidence, Feb 2025)
- [Tauri issue #13133: Channel event listeners create memory leak](https://github.com/tauri-apps/tauri/issues/13133) — confirmed (HIGH confidence)
- [libgit2 issue #3471: Infinite loop with SSH agent and GIT_EAUTH](https://github.com/libgit2/libgit2/issues/3471) — upstream libgit2 bug affecting git2-rs (HIGH confidence)
- [auth-git2 crate](https://crates.io/crates/auth-git2) — credential handler with loop detection (HIGH confidence)
- [PyInstaller issue #6754: `--onefile` antivirus false positives](https://github.com/pyinstaller/pyinstaller/issues/6754) — confirmed, ongoing (HIGH confidence)
- [Nuitka issue #2495: Windows Defender blocks Nuitka onefile exe](https://github.com/Nuitka/Nuitka/issues/2495) — confirmed (HIGH confidence)
- [Tauri v2 macOS code signing docs](https://v2.tauri.app/distribute/sign/macos/) — notarization requirements (HIGH confidence, official docs)
- [Tauri v2 Windows code signing docs](https://v2.tauri.app/distribute/sign/windows/) — HSM requirement since June 2023 (HIGH confidence, official docs)
- [Tauri security advisory GHSA-6mv3-wm7j-h4w5: filesystem scope too permissive](https://github.com/tauri-apps/tauri/security/advisories/GHSA-6mv3-wm7j-h4w5) — glob pattern exploit (HIGH confidence)
- [PyInstaller onefile slow startup discussion](https://github.com/orgs/pyinstaller/discussions/9080) — 10-25s startup documented (HIGH confidence)
- [Tauri GitHub Actions pipeline guide](https://v2.tauri.app/distribute/pipelines/github/) — official CI configuration (HIGH confidence, official docs)

---
*Pitfalls research for: Pilot Space v1.1 Tauri Desktop Client*
*Researched: 2026-03-20*
