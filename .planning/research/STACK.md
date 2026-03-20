# Stack Research

**Domain:** Tauri Desktop Client — embedding Next.js, native git, terminal, CLI sidecar, cross-platform packaging
**Researched:** 2026-03-20
**Confidence:** HIGH (core Tauri/git2/xterm verified via official docs and crates.io; PyInstaller via PyPI; xterm addons via npm)

## Scope

Stack additions needed for v1.1 Tauri Desktop Client milestone. Existing stack (FastAPI, Next.js 16.1, React 19.2, MobX, TanStack Query, shadcn/ui, TipTap, Tailwind, PostgreSQL, Supabase) is already validated — do not change.

New capabilities required:
1. Tauri v2 app shell wrapping existing Next.js frontend in a WebView
2. Auth bridge between WebView (Supabase JWT) and Tauri Rust backend
3. Git operations (clone, pull, push, diff, stage, commit) via Rust
4. pilot CLI as compiled sidecar binary — no Python on user machine
5. Embedded terminal panel (xterm.js) for streaming CLI output
6. Diff viewer + commit/stage UI
7. Cross-platform builds: macOS ARM + Intel, Linux x64, Windows x64

---

## Critical Constraint: next.config.ts Must Change for Tauri Production

The current `next.config.ts` uses `output: 'standalone'` and `rewrites()` for the dev-to-backend proxy. These are **incompatible** with Tauri's production WebView model.

Tauri production builds require `output: 'export'` (static HTML/CSS/JS served from the `out/` directory). The Next.js static export mode explicitly does not support:
- `rewrites()` — not available
- `redirects()` — not available
- `headers()` — not available
- Server Actions — not available
- API Routes (pages router) — not available
- Middleware — not available
- `output: 'standalone'` — incompatible

**Recommended approach:** Maintain two build modes in `next.config.ts`:
- `TAURI_BUILD=true` → `output: 'export'`, `images: { unoptimized: true }`, no rewrites, direct API calls to `NEXT_PUBLIC_BACKEND_URL`
- Default → `output: 'standalone'`, rewrites as today (for Docker/web deployment)

All existing `fetch('/api/v1/...')` relative calls must become `fetch(process.env.NEXT_PUBLIC_BACKEND_URL + '/api/v1/...')` when `TAURI_BUILD=true`. The Tauri WebView calls the remote FastAPI directly over HTTPS.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| tauri (Rust crate) | 2.10.3 | Desktop app shell, system APIs, WebView host | Stable as of Oct 2024, actively maintained (v2.10.3 = Mar 2026). System WebView (WKWebView/WebKit2GTK/WebView2) = minimal binary size vs Electron's bundled Chromium. Official support for Next.js SSG. |
| @tauri-apps/api | 2.10.1 | JS/TS bindings: invoke, IPC, events, window | Versioned in sync with Rust crate. Required for all WebView→Rust communication. |
| @tauri-apps/cli | 2.10.1 | Build toolchain: `tauri dev`, `tauri build` | Wraps cargo build + bundler; handles signing and notarization hooks |
| git2 (Rust crate) | 0.20.4 | libgit2 bindings for Rust: clone/pull/push/diff/status | Memory-safe, threadsafe wrapper over libgit2 1.9.0. Vendored libgit2 (no system dependency). Higher-level than raw libgit2 C calls. Used by Gitoxide for non-network operations. |
| @xterm/xterm | 5.5.0 | Browser-based terminal emulator | Official scoped package (old `xterm` package deprecated). Used by VS Code, GitHub Codespaces. Renders ANSI escape sequences, handles resize, integrates with PTY streams. |
| PyInstaller | 6.19.0 | Compile pilot CLI Python binary (no Python required on user machine) | Bundles Python interpreter + dependencies into single-file or one-directory executable. Simpler cross-platform support than Nuitka; widely used for Tauri Python sidecars. v6.19.0 released Mar 2026. Works with uv-managed virtualenvs. |

### Supporting Libraries (Rust — add to `src-tauri/Cargo.toml`)

| Crate | Version | Purpose | When to Use |
|-------|---------|---------|-------------|
| tauri-plugin-shell | ~2.2 | Spawn sidecar binaries, execute shell commands, stream stdout/stderr | Required for pilot CLI sidecar invocation and shell command execution |
| tauri-plugin-fs | ~2.4 | Filesystem read/write with path scoping (AppData, Home, etc.) | Reading/writing workspace directory, config files, cloned repo files |
| tauri-plugin-store | 2.4.2 | Persistent key-value JSON store (encrypted option) | Storing user preferences: workspace base path, theme, last-visited project |
| tauri-plugin-os | ~2.2 | OS info: platform, version, architecture | Platform-specific behavior (e.g., path separators, binary names for sidecar) |
| tauri-plugin-dialog | ~2.5 | Native file/folder picker dialogs | Letting user choose project workspace base directory |
| tauri-plugin-process | ~2.2 | Exit app, restart, get PID | Graceful shutdown of sidecar processes on app exit |
| tokio | 1.x | Async runtime for Rust backend | Required for async git operations + sidecar process management; already used by Tauri |
| serde / serde_json | 1.x | Serialization for IPC payloads | Tauri IPC passes JSON between WebView and Rust; serde derives on all command argument/return types |

### Supporting Libraries (npm/JS — add to `frontend/package.json`)

| Package | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @xterm/xterm | 5.5.0 | Terminal emulator component | All terminal panel rendering (PTY output from pilot CLI, shell commands) |
| @xterm/addon-fit | 0.11.0 | Auto-resize terminal to container dimensions | Required — terminal must respond to panel resize events |
| @xterm/addon-web-links | ~0.11 | Clickable URLs in terminal output | Nice-to-have; file paths and URLs in CLI output become clickable |
| react-diff-view | 3.x | Unified/split diff rendering from git patch text | Pure-React, parses unified diff format directly — ideal for `git show` / `git diff` output. Lighter than Monaco for pure diff display. |
| @tauri-apps/plugin-shell | ~2.2 | JS bindings for tauri-plugin-shell | Spawning sidecar, executing commands from WebView JS |
| @tauri-apps/plugin-fs | ~2.4 | JS bindings for tauri-plugin-fs | File operations from frontend (reading workspace structure) |
| @tauri-apps/plugin-store | 2.4.x | JS bindings for tauri-plugin-store | Persisting desktop-specific settings from frontend |
| @tauri-apps/plugin-dialog | ~2.5 | JS bindings for tauri-plugin-dialog | File/folder picker dialogs triggered from frontend |
| @tauri-apps/plugin-os | ~2.2 | JS bindings for tauri-plugin-os | Platform detection in frontend |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Rust toolchain (stable) | Compiles Tauri Rust backend | Min 1.77.2 required by Tauri plugins. Install via rustup. |
| cargo-tauri (via @tauri-apps/cli) | `tauri dev` hot-reload, `tauri build` production build | Installed via npm; no separate cargo install needed |
| tauri-apps/tauri-action (GitHub Action) | CI cross-platform builds | Builds macOS ARM64, macOS x86_64, Linux x64, Windows x64 in parallel via matrix strategy. Handles code signing keys as secrets. |
| rustup target add | Add cross-compilation targets | `aarch64-apple-darwin` + `x86_64-apple-darwin` for macOS universal; `x86_64-unknown-linux-gnu`; `x86_64-pc-windows-msvc` |
| uv run pyinstaller | Compile pilot CLI to binary | Run within pilot CLI's uv virtualenv; output binary placed in `src-tauri/binaries/` with target triple suffix |

---

## Installation

```bash
# 1. Install Rust (if not present)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 2. Add macOS cross-compilation targets (for universal binary CI)
rustup target add aarch64-apple-darwin x86_64-apple-darwin

# 3. Scaffold Tauri in the monorepo root
cd /path/to/pilot-space
pnpm add -D @tauri-apps/cli@2.10.1
pnpm tauri init
# Set: app name "Pilot Space", window title "Pilot Space",
#      beforeDevCommand "cd frontend && pnpm dev",
#      beforeBuildCommand "cd frontend && TAURI_BUILD=true pnpm build",
#      devUrl "http://localhost:3000",
#      frontendDist "../frontend/out"

# 4. Add Tauri JS API to frontend
cd frontend
pnpm add @tauri-apps/api@2.10.1
pnpm add @xterm/xterm@5.5.0 @xterm/addon-fit@0.11.0 @xterm/addon-web-links
pnpm add react-diff-view
pnpm add @tauri-apps/plugin-shell @tauri-apps/plugin-fs @tauri-apps/plugin-store @tauri-apps/plugin-dialog @tauri-apps/plugin-os

# 5. Add Rust crates to src-tauri/Cargo.toml
# [dependencies]
# git2 = { version = "0.20", features = ["vendored-libgit2"] }
# tauri-plugin-shell = "2"
# tauri-plugin-fs = "2"
# tauri-plugin-store = "2"
# tauri-plugin-os = "2"
# tauri-plugin-dialog = "2"
# tauri-plugin-process = "2"
# serde = { version = "1", features = ["derive"] }
# serde_json = "1"

# 6. Compile pilot CLI sidecar
cd cli
uv run pyinstaller --onefile --name pilot pilot/main.py
# Rename output with target triple suffix
TRIPLE=$(rustc --print host-tuple)
cp dist/pilot src-tauri/binaries/pilot-${TRIPLE}
```

---

## next.config.ts Changes Required

```typescript
// Detect Tauri build mode
const isTauriBuild = process.env.TAURI_BUILD === 'true';

const nextConfig: NextConfig = {
  // Static export for Tauri; standalone for Docker/web
  output: isTauriBuild ? 'export' : 'standalone',

  // Required for static export — next/image optimization is server-side
  images: isTauriBuild
    ? { unoptimized: true }
    : {
        remotePatterns: [{ protocol: 'https', hostname: '*.supabase.co', ... }],
      },

  // Rewrites only work in standalone/server mode — omit for Tauri
  ...(isTauriBuild
    ? {}
    : {
        async rewrites() { return [{ source: '/api/v1/:path*', destination: '...' }]; },
      }),
};
```

**Implication for all API calls:** Under `TAURI_BUILD=true`, the frontend has no `/api/v1/*` proxy. All `fetch('/api/v1/...')` calls must use the absolute backend URL. Implement a utility:

```typescript
// lib/api-url.ts
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? '';
export const apiUrl = (path: string) => `${BACKEND}${path}`;
// Usage: fetch(apiUrl('/api/v1/issues'))  — works in both modes
```

---

## Tauri Sidecar: pilot CLI

The pilot CLI is a Python app managed by uv. It must be compiled to a self-contained binary for Tauri sidecar distribution (users must not need Python installed).

**Naming convention** (required by Tauri):
```
src-tauri/binaries/pilot-aarch64-apple-darwin      # macOS ARM
src-tauri/binaries/pilot-x86_64-apple-darwin       # macOS Intel
src-tauri/binaries/pilot-x86_64-unknown-linux-gnu  # Linux
src-tauri/binaries/pilot-x86_64-pc-windows-msvc.exe # Windows
```

**`src-tauri/tauri.conf.json`:**
```json
{
  "bundle": {
    "externalBin": ["binaries/pilot"]
  }
}
```

**Capabilities (`src-tauri/capabilities/default.json`):**
```json
{
  "permissions": [
    {
      "identifier": "shell:allow-execute",
      "allow": [{ "name": "binaries/pilot", "sidecar": true }]
    }
  ]
}
```

**Invocation from Rust:**
```rust
use tauri_plugin_shell::ShellExt;
let sidecar = app.shell().sidecar("pilot").unwrap();
let (mut rx, child) = sidecar.args(["implement", issue_id]).spawn()?;
// Stream events from rx to WebView via Tauri event system
```

**PyInstaller vs Nuitka decision:** Use PyInstaller 6.19.0.
- PyInstaller is the documented standard for Tauri Python sidecars
- Nuitka transpiles to C — faster startup, smaller binary (~58MB vs ~94MB), better IP protection — but significantly slower build times and harder to debug in CI
- For a CLI tool (not compute-intensive GUI), PyInstaller's maturity and simpler CI integration outweigh Nuitka's runtime gains
- PyInstaller 6.13+ explicitly supports uv-managed Python installations (fixed discovery of shared library)

---

## Cross-Platform Build CI

Tauri cannot meaningfully cross-compile across OS boundaries (each platform requires its native system libraries). Use GitHub Actions matrix builds:

```yaml
# .github/workflows/tauri-release.yml (excerpt)
jobs:
  build:
    strategy:
      matrix:
        include:
          - platform: macos-latest     # ARM (M1+)
            target: aarch64-apple-darwin
          - platform: macos-13          # Intel
            target: x86_64-apple-darwin
          - platform: ubuntu-22.04
            target: x86_64-unknown-linux-gnu
          - platform: windows-latest
            target: x86_64-pc-windows-msvc
    runs-on: ${{ matrix.platform }}
    steps:
      - name: Install Linux dependencies
        if: matrix.platform == 'ubuntu-22.04'
        run: sudo apt-get install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}
      - uses: swatinem/rust-cache@v2
      - uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
          APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
```

**Linux dependency note:** Tauri v2 requires `libwebkit2gtk-4.1-dev` (not 4.0 as in v1). The `ubuntu-22.04` runner has this available.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Tauri v2 | Electron | When: team is JS-only (no Rust), bundled Chromium version control is critical, or Linux GTK issues are blockers. Electron is ~200MB binary vs Tauri ~10-15MB. |
| Tauri v2 | Wails (Go) | When: team is Go-heavy. Similar architecture but smaller ecosystem. |
| git2-rs (libgit2) | Gitoxide (gix crate) | When: pure-Rust implementation without C FFI is needed. Gitoxide is the future but lacks network operations in stable today. Use git2 for full clone/push/pull. |
| git2-rs | Shelling out to system git | When: git operations are trivial and system git is guaranteed present. Unreliable on Windows; version variance across systems; not recommended for shipped desktop app. |
| PyInstaller | Nuitka | When: IP protection or binary size are critical. Nuitka produces faster, smaller binaries but has 5-10x longer build times. For pilot CLI (a short-lived subprocess), PyInstaller is correct. |
| react-diff-view | @monaco-editor/react DiffEditor | When: you also need a full code editor in the same view. Monaco is 4MB+ bundle size; react-diff-view is ~50KB. For a pure diff display panel, react-diff-view is correct. |
| @xterm/xterm | xterm (old package) | Never — old package is deprecated, last published 3 years ago. Always use `@xterm/xterm`. |
| Static export + direct API URL | Node.js sidecar (Next.js standalone in Tauri) | When: SSR features (Server Actions, middleware, API routes) are required in desktop mode. Adds ~84MB Node.js binary, complex port management, process lifecycle issues. Avoid unless proven necessary. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `xterm` (old unscoped package) | Deprecated, last published 2023, unmaintained | `@xterm/xterm@5.5.0` |
| `output: 'standalone'` in Tauri build | Requires Node.js server runtime; not supported in Tauri WebView | `output: 'export'` with `TAURI_BUILD=true` env guard |
| `next/image` default loader in Tauri build | Server-side optimization not available in static export | Set `images: { unoptimized: true }` in Tauri build mode |
| Next.js `rewrites()` in Tauri build | Not supported in static export | Direct API calls using `NEXT_PUBLIC_BACKEND_URL` |
| Bundling FastAPI backend in Tauri | Enormous complexity: FastAPI + Supabase + Postgres cannot run locally without Docker | Keep remote backend; Tauri connects over HTTPS (validated architecture decision) |
| Bundling Supabase in Tauri | Postgres + GoTrue + storage = ~1GB Docker stack; not desktop-appropriate | Remote Supabase; auth tokens bridged via IPC |
| Gitoxide (`gix`) for network operations | Network operations (clone/fetch/push) are not yet stable in Gitoxide as of early 2026 | git2 (libgit2 bindings); revisit when Gitoxide network layer stabilizes |
| `bundleName` or `sidecar` without target triple suffix | Tauri sidecar lookup fails silently without the correct `{name}-{target-triple}` naming | Always generate platform-named binaries via `rustc --print host-tuple` |
| System git via `std::process::Command` | Version variance, missing on some Windows machines, PATH issues in macOS GUI apps | git2 Rust crate with vendored libgit2 |

---

## Stack Patterns

**Auth bridge (WebView → Rust):**
Use Tauri's IPC `invoke()`. WebView holds Supabase JWT in localStorage; on app init, JS calls `invoke('get_auth_state')`. Rust Tauri command reads token via IPC event, stores in Tauri managed state (`app.manage()`), attaches as `Authorization: Bearer` header on all git operations that need auth-gated API calls.

**Terminal streaming (xterm.js + sidecar):**
- Rust spawns sidecar via `tauri-plugin-shell`, receives stdout/stderr events
- Rust emits Tauri events (`app.emit("terminal-output", data)`)
- Frontend xterm terminal subscribes to events via `listen('terminal-output', ...)`
- `@xterm/addon-fit` handles resize when panel dimensions change

**git2 thread safety:**
git2 `Repository` is not `Send` — do not move it across threads directly. Pattern: create a `Mutex<Repository>` in Tauri managed state, lock per command, clone paths as needed. For long-running clone operations, use `tokio::task::spawn_blocking`.

**Next.js dynamic imports for Tauri APIs:**
```typescript
// Tauri APIs must be lazy-imported — not available during Next.js SSG build
const { invoke } = await import('@tauri-apps/api/core');
// Or: use next/dynamic with ssr: false for components using Tauri APIs
```

**Tauri detection utility:**
```typescript
export const isTauri = () => typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
```

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| tauri 2.10.3 | Rust 1.77.2+ | Use stable toolchain; nightly not required |
| tauri 2.10.3 | @tauri-apps/api 2.10.1 | Must keep Rust crate and JS package in version sync |
| tauri 2.10.3 | @tauri-apps/cli 2.10.1 | CLI version must match crate version |
| tauri-plugin-* 2.x | tauri 2.x | All official plugins are versioned under 2.x for Tauri v2 |
| git2 0.20.4 | libgit2 1.9.0 (vendored) | Enable `features = ["vendored-libgit2"]` in Cargo.toml to avoid system dependency |
| @xterm/xterm 5.5.0 | @xterm/addon-fit 0.11.0 | Addon versions must match xterm major version; use 0.11.x addons with xterm 5.x |
| Next.js 16.1.4 | output: 'export' | App Router is fully supported in static export; Server Actions and middleware are not |
| PyInstaller 6.19.0 | uv-managed Python | Python 3.8+ supported; 6.13+ explicitly fixes uv Python discovery |

---

## Sources

- [Tauri v2 releases page](https://v2.tauri.app/release/) — tauri 2.10.3, @tauri-apps/api 2.10.1, @tauri-apps/cli 2.10.1 (HIGH confidence)
- [Tauri v2 Next.js setup guide](https://v2.tauri.app/start/frontend/nextjs/) — official static export requirement, out/ frontendDist configuration (HIGH confidence)
- [Next.js static export guide](https://nextjs.org/docs/app/guides/static-exports) — complete list of unsupported features in export mode, version 16.2.0 docs (HIGH confidence)
- [Tauri sidecar documentation](https://v2.tauri.app/develop/sidecar/) — naming conventions, tauri.conf.json, capabilities config, Rust invocation pattern (HIGH confidence)
- [Tauri Node.js sidecar guide](https://v2.tauri.app/learn/sidecar-nodejs/) — sidecar process lifecycle patterns, long-running process IPC (HIGH confidence)
- [Tauri GitHub Actions pipeline guide](https://v2.tauri.app/distribute/pipelines/github/) — cross-platform matrix config, Ubuntu libwebkit2gtk-4.1-dev requirement (HIGH confidence)
- [git2 crate on docs.rs](https://docs.rs/crate/git2/latest) — version 0.20.4, libgit2 1.9.0 required, vendored feature (HIGH confidence)
- [@xterm/xterm on npm](https://www.npmjs.com/package/@xterm/xterm?activeTab=versions) — version 5.5.0, scoped package (HIGH confidence)
- [@xterm/addon-fit on npm](https://www.npmjs.com/package/@xterm/addon-fit) — version 0.11.0 (HIGH confidence)
- [tauri-plugin-store on crates.io](https://docs.rs/crate/tauri-plugin-store/latest) — version 2.4.2 (HIGH confidence)
- [tauri-plugin-fs on docs.rs](https://docs.rs/crate/tauri-plugin-fs/latest) — version 2.4.5 (HIGH confidence)
- [PyInstaller changelog](https://pyinstaller.org/en/stable/CHANGES.html) — version 6.19.0, March 2026 (HIGH confidence)
- [vercel/next.js discussion #90982](https://github.com/vercel/next.js/discussions/90982) — Next.js standalone in Tauri sidecar patterns, env var timing issues (MEDIUM confidence — community discussion, not official docs)
- [tauri-apps/tauri discussion #6083](https://github.com/tauri-apps/tauri/discussions/6083) — real-world Next.js + Tauri experiences, dynamic import workaround for Tauri APIs (MEDIUM confidence)
- [2026 PyInstaller vs Nuitka comparison](https://ahmedsyntax.com/2026-comparison-pyinstaller-vs-cx-freeze-vs-nui/) — binary size and build speed data (MEDIUM confidence — third-party benchmarks)

---
*Stack research for: Tauri Desktop Client — Next.js WebView embedding, git2-rs, xterm.js, PyInstaller sidecar, cross-platform builds*
*Researched: 2026-03-20*
