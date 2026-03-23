# Phase 30: Tauri Shell + Static Export — Research

**Researched:** 2026-03-20
**Domain:** Tauri v2 desktop shell scaffolding, Next.js static export mode, GitHub Actions cross-platform CI matrix
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SHELL-01 | User can launch native desktop app with embedded Pilot Space web UI | Tauri v2 scaffold + `tauri.conf.json` + Next.js static export; `frontendDist: "../frontend/out"` points Tauri WebView at the built static output |
| SHELL-02 | Existing Next.js frontend builds in both web (standalone) and desktop (static export) modes via NEXT_TAURI flag | `NEXT_TAURI=true` env guard in `next.config.ts`; switch `output: 'export'`, `images.unoptimized`, disable rewrites and redirects; 35 `useParams()` call-sites and 2 server-side route handlers must be audited and adapted |
</phase_requirements>

---

## Summary

Phase 30 establishes the Tauri desktop shell and confirms the Next.js frontend builds cleanly in static export mode. It is the foundation for every downstream phase — no native Rust code (auth, git, terminal) can be written until the static export is verified clean.

The work splits into three concerns. First, a new `tauri-app/` top-level directory must be scaffolded with `tauri.conf.json`, `src-tauri/Cargo.toml`, a capabilities file, and a minimal Rust entry point (`lib.rs` + `main.rs`). Tauri v2's `@tauri-apps/cli` init tooling produces most of this automatically; the main decisions are `devUrl`, `frontendDist`, `identifier`, and window configuration. Second, `frontend/next.config.ts` must grow a build-mode toggle (`NEXT_TAURI=true`) that switches `output: 'export'`, sets `images.unoptimized: true`, and disables the `rewrites()` and `redirects()` that require a running Node.js server. Two existing route handlers (`app/api/health/route.ts` and `app/api/v1/ai/chat/route.ts`) are server-only and are silently dropped in static export — both must be addressed. The docs detail page (`/[workspaceSlug]/docs/[slug]/page.tsx`) uses `fs.readFileSync` on the server — it must be audited for static export compatibility. Third, a GitHub Actions workflow file must produce unsigned build artifacts for all four platform targets from day one.

**Critical discovery from codebase inspection:** `useParams()` is called in 35 places across the Next.js app (not counting test files). The existing `WorkspaceGuard` component wraps every workspace page and reads `params.workspaceSlug` from `useParams()`. If `useParams()` returns empty in the Tauri static export, the guard fails and every workspace page is inaccessible. This must be the first thing verified when the static export build runs. The upstream Next.js bug (#54393, #79380) distinguishes between `useParams()` for *truly* static segments vs. dynamic segments. Research suggests that because Tauri uses client-side navigation (not file-based routing for the `tauri://` scheme), `useParams()` works correctly at runtime when navigating via `router.push()` — the issue only occurs if the page is loaded directly from a static file without prior navigation. Phase 30 must include a verification step that navigates to a dynamic route inside the Tauri WebView.

**Primary recommendation:** Scaffold `tauri-app/` first, add the `NEXT_TAURI` toggle to `next.config.ts` second, run `next build` with `NEXT_TAURI=true` immediately to surface all static export errors before writing any Rust code, then wire up the GitHub Actions CI matrix so Windows and Linux failures surface in CI from the first commit.

---

## Standard Stack

### Core (Phase 30 only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tauri (Rust crate) | 2.10.3 | Desktop shell, WebView host, IPC framework | Official Tauri v2; stable since Oct 2024; official Next.js static export support documented |
| @tauri-apps/api | 2.10.1 | JS/TS bindings for `invoke()`, window, events | Must version-match the Rust crate exactly |
| @tauri-apps/cli | 2.10.1 | `tauri init`, `tauri dev`, `tauri build` | Wraps cargo build + bundler; handles signing hooks |
| tauri-apps/tauri-action | v0 (latest) | GitHub Actions cross-platform build matrix | Official Tauri CI action; handles platform runners, artifact upload, code signing env vars |

### Supporting (Phase 30 minimal setup)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tauri-plugin-shell | ~2.2 | Sidecar/shell permissions (needed in capabilities file for future phases) | Register in Phase 30 capabilities even if not yet implemented — avoids IPC capability errors in Phase 31+ |
| tauri-plugin-store | 2.4.2 | Persistent KV store — auth tokens, workspace dir | Register plugin in `lib.rs` in Phase 30; used heavily from Phase 31 onward |
| swatinem/rust-cache | v2 | Cache Cargo build artifacts in CI | Reduces macOS CI from 20 min to 5-8 min on subsequent runs |
| dtolnay/rust-toolchain | stable | Install Rust in CI matrix runners | Preferred over `actions-rs/toolchain` (deprecated) |

### Not in Phase 30 (later phases)

git2-rs, tauri-plugin-pty, @xterm/xterm, react-diff-view, PyInstaller — these are Phase 32–35 concerns. Do not add them here.

### Alternatives Considered

| Recommended | Alternative | Tradeoff |
|-------------|-------------|----------|
| `output: 'export'` with `NEXT_TAURI=true` guard | Node.js sidecar (Next.js standalone in Tauri) | Node sidecar adds ~84MB binary, port management complexity, breaks Tauri's clean process model. Static export is correct for this architecture. |
| Separate `tauri-app/` directory | Nest Tauri inside `frontend/` | Pollutes frontend package boundary; harder to add Rust code; conflicts with `frontend/package.json` scope. Separate directory mirrors monorepo conventions. |
| NSIS + WiX bundle config | NSIS only | WiX `.msi` requires Windows runner (already in matrix); having both formats maximizes enterprise compatibility. |

**Installation (Phase 30 only):**

```bash
# From monorepo root
mkdir tauri-app && cd tauri-app
pnpm init
pnpm add -D @tauri-apps/cli@2.10.1

# Init Tauri project (interactive or with flags)
pnpm tauri init --app-name "Pilot Space" \
  --window-title "Pilot Space" \
  --before-dev-command "cd ../frontend && pnpm dev" \
  --before-build-command "cd ../frontend && NEXT_TAURI=true pnpm build" \
  --dev-url "http://localhost:3000" \
  --frontend-dist "../frontend/out"

# Add Tauri JS API to frontend (not tauri-app — frontend renders in WebView)
cd ../frontend
pnpm add @tauri-apps/api@2.10.1
```

**Version verification (confirmed 2026-03-20):**
- `@tauri-apps/cli`: 2.10.1 (npm registry)
- `tauri` Rust crate: 2.10.3 (crates.io)
- `@tauri-apps/api`: 2.10.1 (npm registry)

---

## Architecture Patterns

### Recommended Project Structure (Phase 30 deliverable)

```
tauri-app/                         # NEW top-level directory
├── package.json                   # devDep: @tauri-apps/cli; scripts: tauri dev, tauri build
└── src-tauri/
    ├── Cargo.toml                 # [dependencies]: tauri 2, tauri-plugin-shell 2, tauri-plugin-store 2, serde 1
    ├── Cargo.lock                 # committed to repo
    ├── build.rs                   # single line: tauri_build::build()
    ├── tauri.conf.json            # app id, devUrl, frontendDist, bundle settings
    ├── capabilities/
    │   └── default.json           # IPC permissions — Phase 30 needs minimal set
    ├── icons/                     # PNG 32-512, ICNS, ICO (generated by tauri init)
    └── src/
        ├── main.rs                # #![cfg_attr(not(debug_assertions), windows_subsystem = "windows")] fn main() { lib::run() }
        └── lib.rs                 # tauri::Builder with plugin registrations + invoke_handler![]

# frontend/ modifications (minimal for Phase 30):
frontend/
├── next.config.ts                 # MODIFIED: conditional output + images + rewrites
└── src/
    └── lib/
        └── tauri.ts               # NEW: isTauri() detection utility (no invoke() yet)

# CI:
.github/workflows/
└── tauri-build.yml                # NEW: 4-runner matrix, artifact upload
```

### Pattern 1: Tauri v2 `lib.rs` Entry Point

**What:** Tauri v2 split entry point — `main.rs` calls `lib::run()`. This allows unit testing the Tauri setup and is required for the Tauri v2 project structure.

**When to use:** Always. This is the Tauri v2 standard; the old v1 pattern with everything in `main.rs` is deprecated.

**Example:**
```rust
// src-tauri/src/main.rs
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
fn main() {
    pilot_space_lib::run()
}

// src-tauri/src/lib.rs
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .invoke_handler(tauri::generate_handler![])  // empty for Phase 30
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Pattern 2: `tauri.conf.json` for Phase 30

**What:** Minimal configuration for Phase 30. Points `devUrl` at Next.js dev server and `frontendDist` at the static export output directory.

**Key decisions:**
- `identifier` must be a reverse-domain string: `"io.pilotspace.app"` — used by macOS bundle ID, Windows installer key, and app data directory. Cannot be changed after first release.
- `useHttpsScheme: true` on Windows — prevents `localStorage` and `IndexedDB` from resetting on every app restart. Must be set from Phase 30 even if auth isn't wired yet.
- `devTools: true` for debug builds — essential for WebView debugging during development.

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "Pilot Space",
  "version": "0.1.0",
  "identifier": "io.pilotspace.app",
  "build": {
    "beforeDevCommand": "cd ../frontend && pnpm dev",
    "beforeBuildCommand": "cd ../frontend && NEXT_TAURI=true pnpm build",
    "devUrl": "http://localhost:3000",
    "frontendDist": "../frontend/out"
  },
  "app": {
    "windows": [
      {
        "title": "Pilot Space",
        "width": 1280,
        "height": 800,
        "minWidth": 900,
        "minHeight": 600,
        "useHttpsScheme": true
      }
    ],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  }
}
```

### Pattern 3: `next.config.ts` Static Export Toggle

**What:** Build-mode guard that switches Next.js from `standalone` (Docker/web) to `export` (Tauri) based on the `NEXT_TAURI` environment variable.

**Critical:** The existing `next.config.ts` has:
1. `output: 'standalone'` — must become conditional
2. `async rewrites()` — must be removed for Tauri builds (no server)
3. `async redirects()` — must be removed for Tauri builds
4. `outputFileTracingIncludes` — only meaningful for standalone; remove or guard for Tauri
5. `images.remotePatterns` — server-side optimization unavailable in static export; must set `unoptimized: true`
6. `experimental.optimizePackageImports` — safe to keep in both modes

```typescript
// next.config.ts — Phase 30 target state
import type { NextConfig } from 'next';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const isTauriBuild = process.env.NEXT_TAURI === 'true';

const nextConfig: NextConfig = {
  output: isTauriBuild ? 'export' : 'standalone',

  // Required for static export — server cannot optimize images at request time
  images: isTauriBuild
    ? { unoptimized: true }
    : {
        remotePatterns: [
          {
            protocol: 'https',
            hostname: '*.supabase.co',
            pathname: '/storage/v1/object/public/**',
          },
        ],
      },

  // outputFileTracingIncludes only applies to standalone builds
  ...(isTauriBuild
    ? {}
    : {
        outputFileTracingIncludes: {
          '/[workspaceSlug]/docs/[slug]': ['./src/features/docs/content/*.md'],
        },
      }),

  // rewrites() and redirects() require a running Node.js server — unavailable in static export
  ...(isTauriBuild
    ? {}
    : {
        async rewrites() {
          return [{ source: '/api/v1/:path*', destination: `${BACKEND_URL}/api/v1/:path*` }];
        },
        async redirects() {
          return [
            { source: '/:slug/settings/skills', destination: '/:slug/roles', permanent: true },
            { source: '/:slug/settings/members', destination: '/:slug/members', permanent: true },
          ];
        },
      }),

  poweredByHeader: false,
  reactStrictMode: true,

  experimental: {
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-avatar',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-popover',
      '@radix-ui/react-scroll-area',
      '@radix-ui/react-separator',
      '@radix-ui/react-slot',
      '@radix-ui/react-tooltip',
      'date-fns',
      '@tiptap/core',
      '@tiptap/react',
      '@tiptap/pm',
      '@tiptap/starter-kit',
      '@tiptap/extension-placeholder',
      '@tiptap/extension-character-count',
      'recharts',
    ],
  },
};

export default nextConfig;
```

### Pattern 4: `isTauri()` Detection Utility

**What:** Single utility function for detecting Tauri runtime. Must be checked before any `@tauri-apps/api` import to prevent SSG errors.

**When to use:** Any frontend code that behaves differently in desktop vs web mode. Phase 30 establishes this pattern; later phases add `invoke()` wrappers to the same file.

```typescript
// frontend/src/lib/tauri.ts  (Phase 30 creates this empty but correct)
/**
 * Detect if running inside a Tauri desktop shell.
 * @tauri-apps/api imports must ALWAYS be lazy (dynamic import) or gated
 * by isTauri() to prevent SSG build errors.
 */
export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

// Phase 31+ will add typed invoke() wrappers here.
// NEVER call invoke() directly in components — always go through this module.
```

### Pattern 5: GitHub Actions 4-Runner Build Matrix

**What:** Tauri cannot cross-compile across OS boundaries. A 4-runner matrix is mandatory to produce artifacts for all platforms.

**Key points for Phase 30:**
- This is a **build-only** workflow (no signing yet — signing is Phase 38)
- Use `tauri-apps/tauri-action@v0` which handles the full build pipeline
- Linux runner requires `libwebkit2gtk-4.1-dev` (NOT 4.0 — Tauri v2 requires 4.1)
- Upload artifacts with `upload-artifact` so they are downloadable from CI
- `swatinem/rust-cache@v2` is essential — first cold build on macOS takes 20+ minutes

```yaml
# .github/workflows/tauri-build.yml
name: Tauri Build

on:
  push:
    branches: [main, develop, 'feat/tauri-*']
  pull_request:
    branches: [main, develop]

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - platform: macos-latest
            target: aarch64-apple-darwin
            artifact-name: pilot-space-macos-arm64
          - platform: macos-13
            target: x86_64-apple-darwin
            artifact-name: pilot-space-macos-x86_64
          - platform: ubuntu-22.04
            target: x86_64-unknown-linux-gnu
            artifact-name: pilot-space-linux-x64
          - platform: windows-latest
            target: x86_64-pc-windows-msvc
            artifact-name: pilot-space-windows-x64

    runs-on: ${{ matrix.platform }}
    name: Build ${{ matrix.artifact-name }}

    steps:
      - uses: actions/checkout@v4

      - name: Install Linux system dependencies
        if: matrix.platform == 'ubuntu-22.04'
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            libwebkit2gtk-4.1-dev \
            libappindicator3-dev \
            librsvg2-dev \
            patchelf

      - name: Install Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Cache Rust build artifacts
        uses: swatinem/rust-cache@v2
        with:
          workspaces: './tauri-app/src-tauri -> target'

      - name: Install frontend dependencies
        working-directory: frontend
        run: pnpm install --frozen-lockfile

      - name: Install Tauri CLI
        working-directory: tauri-app
        run: pnpm install --frozen-lockfile

      - name: Build Tauri app
        uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NEXT_TAURI: 'true'
          NEXT_PUBLIC_BACKEND_URL: 'https://api.pilotspace.io'
          # Signing secrets referenced but empty for Phase 30 (unsigned builds)
          # APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
          # APPLE_ID: ${{ secrets.APPLE_ID }}
        with:
          projectPath: './tauri-app'
          tauriScript: 'pnpm tauri'
          args: '--target ${{ matrix.target }}'

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact-name }}
          path: |
            tauri-app/src-tauri/target/${{ matrix.target }}/release/bundle/
          retention-days: 7
```

### Pattern 6: Dynamic Route Behavior in Static Export

**What:** Research finding on `useParams()` in `output: 'export'` mode. This determines whether dynamic routes require changes.

**Findings (MEDIUM-HIGH confidence, from Next.js issues #54393 and #79380 + official docs):**

The Next.js static export + client-side navigation interaction works as follows:
- When navigating via `router.push('/workspace-slug/issues/issue-id')` in the browser/WebView, the Next.js client router handles this as a **client-side navigation** — it does NOT reload the page from a static file. `useParams()` returns the correct values from the client router state.
- The problem occurs only when a user **directly accesses** a dynamic URL (types in address bar, page refresh). In a web static export served by Nginx, the server must be configured to serve `index.html` for all routes (SPA fallback). In Tauri, the `tauri://localhost` scheme maps static files, so `/workspace-slug/issues/issue-id` would look for `out/workspace-slug/issues/issue-id/index.html` — which does not exist unless `generateStaticParams()` was called.

**This app's pattern:** `WorkspaceGuard` wraps every workspace page and reads `params.workspaceSlug` from `useParams()`. The guard fetches workspace data via the API after hydration. This is pure client-side — no `generateStaticParams()` is used. This means:
1. On initial app load, Tauri shows the root page (`/`) — a redirect to the last-visited workspace path happens via client-side logic.
2. All subsequent navigation is client-side via `router.push()` — `useParams()` works correctly.
3. **The risk:** Hard-refreshing inside the Tauri WebView on a dynamic route (which users don't typically do) would fail. This is acceptable for a desktop app.

**Resolution for Phase 30:** Verify empirically by running the static export and confirming client-side navigation reaches dynamic routes correctly. No route changes should be needed. The `trailingSlash: true` option in `next.config.ts` is recommended to ensure static files are generated at `[slug]/index.html` rather than `[slug].html`, which aligns with how the Tauri WebView serves files.

### Pattern 7: Handling Server-Side Route Handlers

**What:** Two route handlers must be addressed for static export:

1. `app/api/health/route.ts` — Docker/Kubernetes health check. Not needed in the Tauri build. Solution: excluded automatically (static export skips all route handlers). No action needed — just document it.

2. `app/api/v1/ai/chat/route.ts` — SSE streaming proxy for AI chat. This forwards requests from the browser to the FastAPI backend to bypass Next.js rewrite buffering. In Tauri mode, the `/api/v1/:path*` rewrite does not exist — the frontend calls `NEXT_PUBLIC_BACKEND_URL` directly. The AI chat component must use the direct backend URL when `isTauri()` returns true. This is handled by ensuring `NEXT_PUBLIC_BACKEND_URL` is set correctly and the AI chat fetch call uses the full URL.

**Action for Phase 30:** Audit the AI chat component's fetch URL — confirm it works with `NEXT_PUBLIC_BACKEND_URL` directly, not via the `/api/v1/ai/chat` route handler proxy.

3. `app/(workspace)/[workspaceSlug]/docs/[slug]/page.tsx` — reads markdown files from disk using `fs.readFileSync`. This is a **Server Component** with server-side file I/O. In static export mode, this page will be pre-rendered at build time — `generateStaticParams` must be provided or the build will fail. The `docsBySlug` map provides the list of available slugs, so `generateStaticParams` can be implemented. However, the workspace slug is dynamic — the route is `[workspaceSlug]/docs/[slug]`. This is a doubly-dynamic route that may require special handling.

**Critical finding for docs route:** The `outputFileTracingIncludes` config item that includes the markdown files only applies to `standalone` output. In static export, the markdown content must either be (a) bundled at build time via `generateStaticParams` + inline import, or (b) the docs page must be converted to a client-side page that fetches content via a static JSON manifest. This is the most complex static export issue in this codebase.

### Anti-Patterns to Avoid

- **Committing `target/` directory in `src-tauri/`:** Add `tauri-app/src-tauri/target` to `.gitignore` immediately. The compiled Rust artifacts are gigabytes in size.
- **Missing `Cargo.lock` commit:** Unlike library crates, application Cargo.lock files should be committed. Tauri is an application; commit the lockfile.
- **Using `TAURI_BUILD` instead of `NEXT_TAURI`:** The project research documents use `NEXT_TAURI` consistently. Using a different env var name causes confusion and breaks the `beforeBuildCommand` in `tauri.conf.json`.
- **Setting `identifier` to a placeholder:** The `identifier` in `tauri.conf.json` is used for the app data directory path on all platforms. Changing it post-release corrupts existing user stores. Set it to `io.pilotspace.app` permanently from Phase 30.
- **Using `tauri://localhost` as the Supabase OAuth redirect URI:** This is the Tauri internal WebView protocol. OAuth redirect URIs must use a registered custom scheme (`pilotspace://`) via `tauri-plugin-deep-link`. This is Phase 31's concern, but the identifier decision made in Phase 30 affects the deep link scheme name.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-platform Tauri builds | Custom Dockerfile or build scripts per platform | `tauri-apps/tauri-action@v0` GitHub Action | Handles all 4 platforms, signing env var injection, artifact paths — building from scratch takes days and misses edge cases |
| Tauri runtime detection | Any check other than `'__TAURI_INTERNALS__' in window` | Official `isTauri()` pattern from Tauri v2 docs | Other detection methods (checking `window.__TAURI__`, user-agent) are unreliable or non-standard in v2 |
| Static export build mode config | Separate `next.config.tauri.ts` files | Single `next.config.ts` with `NEXT_TAURI` guard | Two separate config files diverge silently; single file with env guard is verifiable in one place |
| Icon generation | Manually creating ICNS, ICO, multi-res PNGs | `tauri icon` CLI command | `pnpm tauri icon icon.png` generates all required icon formats for all platforms from one source image |

**Key insight:** The hardest part of Phase 30 is not the Tauri scaffold (which is mostly automatic) — it is the Next.js static export compatibility audit. Budget at least half the phase time for verifying and fixing static export issues.

---

## Common Pitfalls

### Pitfall 1: Docs Page Server-Side File I/O Blocks Static Export

**What goes wrong:** `app/(workspace)/[workspaceSlug]/docs/[slug]/page.tsx` calls `fs.readFileSync` in a Server Component. In `output: 'export'`, Next.js attempts to pre-render this page at build time. The doubly-dynamic route `[workspaceSlug]/docs/[slug]` requires `generateStaticParams()` to enumerate all combinations — but `workspaceSlug` values are runtime user data, not known at build time.

**Why it happens:** Static export requires all paths to be enumerable at build time OR the page must be a pure client-side component. A Server Component with `fs.readFileSync` cannot become a client component without removing the server-side file read.

**How to avoid:** Two options:
1. Convert the docs detail page to a client-side component with a build-time JSON manifest (preferred). Extract all markdown files into a static `docs-manifest.json` at build time, import it in the client component, render client-side.
2. Add `generateStaticParams` that returns a fixed set of `workspaceSlug` placeholder values plus all real doc slugs from `docsBySlug` — this produces static pages but embeds the doc content in the HTML. Works but bloats the `out/` directory for every workspace-slug permutation.

**Warning signs:** Build fails with "Page couldn't be rendered statically because it used `fs`" or similar when running `NEXT_TAURI=true next build`.

**Phase to address:** Phase 30, Plan 30-02 (Next.js static export audit).

### Pitfall 2: `outputFileTracingIncludes` Remains in Config

**What goes wrong:** The existing `outputFileTracingIncludes` config tells the standalone build to include markdown files in the traced output. If this remains uncommented when `NEXT_TAURI=true`, the build may fail or warn because `outputFileTracingIncludes` has no effect in export mode but is attempting to trace files for a server component that no longer exists in the output.

**How to avoid:** Guard `outputFileTracingIncludes` behind `!isTauriBuild` as shown in the `next.config.ts` pattern above.

### Pitfall 3: Forgetting `trailingSlash: true` for Static Export

**What goes wrong:** Without `trailingSlash: true`, Next.js generates `[slug].html` files. Tauri's WebView serving static files from `out/` expects `[slug]/index.html`. Deep links and direct navigation in the WebView may fail to find the correct static file.

**How to avoid:** Add `trailingSlash: true` to the `next.config.ts` when `isTauriBuild` is true.

### Pitfall 4: Missing Linux WebKit2GTK Version

**What goes wrong:** Using `libwebkit2gtk-4.0-dev` (Tauri v1 dependency) instead of `libwebkit2gtk-4.1-dev` (Tauri v2 requirement) on the `ubuntu-22.04` CI runner causes the Rust build to fail with a `pkg-config` error.

**How to avoid:** The CI matrix MUST install `libwebkit2gtk-4.1-dev` (NOT 4.0). The `ubuntu-22.04` runner has version 4.1 available in its package registry. Ubuntu 20.04 does NOT have 4.1 — that is why `ubuntu-22.04` is specified.

### Pitfall 5: Cold Rust Build Timeout on macOS CI

**What goes wrong:** First Rust compilation of a Tauri app on macOS GitHub Actions takes 15-25 minutes. The default GitHub Actions job timeout is 6 hours (sufficient), but without Rust caching, every CI run incurs this cost, making the CI slow and expensive.

**How to avoid:** Add `swatinem/rust-cache@v2` before the build step, pointing `workspaces` at `./tauri-app/src-tauri -> target`. This reduces subsequent builds to 2-5 minutes.

### Pitfall 6: `identifier` Cannot Be Changed Post-Release

**What goes wrong:** The `identifier` in `tauri.conf.json` determines the app data directory path on all platforms (e.g., `~/Library/Application Support/io.pilotspace.app` on macOS). Changing it after users have installed the app means their Tauri Store data (auth tokens, workspace prefs) is lost.

**How to avoid:** Set `identifier: "io.pilotspace.app"` from the first commit and never change it. Do not use a placeholder or temporary value.

### Pitfall 7: AI Chat SSE Proxy Breaks Silently

**What goes wrong:** The existing AI chat uses the `/api/v1/ai/chat` Next.js route handler as an SSE streaming proxy to avoid buffering. In Tauri mode, the rewrite is disabled and the route handler is dropped. If the AI chat component still uses a relative URL `/api/v1/ai/chat`, it sends requests to `tauri://localhost/api/v1/ai/chat` which returns 404.

**Why it's hard to notice:** The build succeeds. The error only appears at runtime in the Tauri app when the AI chat feature is used.

**How to avoid:** Audit the AI chat fetch call. If it uses a relative URL `/api/v1/ai/chat`, it must be changed to use `NEXT_PUBLIC_BACKEND_URL + '/api/v1/ai/chat'` when in Tauri mode. The `isTauri()` guard or the direct `NEXT_PUBLIC_BACKEND_URL` prefix handles this.

---

## Code Examples

### Minimal `src-tauri/Cargo.toml` for Phase 30

```toml
[package]
name = "pilot-space"
version = "0.1.0"
description = "Pilot Space Desktop"
authors = []
edition = "2021"
rust-version = "1.77.2"

[lib]
name = "pilot_space_lib"
crate-type = ["staticlib", "cdylib", "rlib"]

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
tauri-plugin-store = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[features]
default = ["custom-protocol"]
custom-protocol = ["tauri/custom-protocol"]
```

### Minimal `capabilities/default.json` for Phase 30

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Default capabilities for Pilot Space desktop app",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "store:allow-load",
    "store:allow-set",
    "store:allow-get",
    "store:allow-delete",
    "store:allow-save"
  ]
}
```

### `isTauri()` import with lazy API usage (critical pattern)

```typescript
// Correct: lazy import prevents SSG errors
async function openDevTools() {
  if (!isTauri()) return;
  const { getCurrentWindow } = await import('@tauri-apps/api/window');
  (await getCurrentWindow()).show();
}

// WRONG: top-level import breaks Next.js SSG build
import { getCurrentWindow } from '@tauri-apps/api/window'; // DO NOT DO THIS
```

### Adding `trailingSlash` to static export config

```typescript
const nextConfig: NextConfig = {
  output: isTauriBuild ? 'export' : 'standalone',
  trailingSlash: isTauriBuild ? true : undefined,
  // ... rest of config
};
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tauri v1 `tauri.conf.json` with `build.distDir` | Tauri v2 `tauri.conf.json` with `build.frontendDist` | Tauri 2.0 (Oct 2024) | Field renamed; v1 configs fail silently if used with v2 CLI |
| `tauri-plugin-*` v1 (`tauri-plugin-store = "0.x"`) | All plugins now versioned at `"2"` for Tauri v2 | Tauri 2.0 | Old plugin versions are incompatible with Tauri v2 Rust crate |
| `actions-rs/toolchain` GitHub Action | `dtolnay/rust-toolchain` GitHub Action | 2023 | `actions-rs` organization is archived; `dtolnay/rust-toolchain` is the community standard |
| `libwebkit2gtk-4.0-dev` for Linux | `libwebkit2gtk-4.1-dev` for Linux | Tauri 2.0 | WebKit2GTK 4.1 required; 4.0 builds fail with pkg-config errors |
| `xterm` npm package | `@xterm/xterm` npm package | 2024 | Old unscoped `xterm` package is deprecated; all addons moved to `@xterm/*` scope |

**Deprecated/outdated:**
- `tauri build --target universal-apple-darwin` (universal binary): Works but produces a single large binary; two separate builds (`aarch64` + `x86_64`) are simpler to manage for CI artifacts and notarization.
- `outputFileTracingIncludes` in static export: Has no effect; only meaningful for `standalone` output.

---

## Open Questions

1. **Docs page static export compatibility**
   - What we know: `[workspaceSlug]/docs/[slug]/page.tsx` is a Server Component using `fs.readFileSync`. Static export cannot server-render at request time.
   - What's unclear: Whether `generateStaticParams` with known doc slugs (from `docsBySlug`) + a wildcard workspace slug is acceptable, or whether the page must be converted to a client component.
   - Recommendation: Plan 30-02 must include a specific task to convert the docs detail page to a client-side approach. Prefer the JSON manifest approach (bundle doc content as static JSON at build time, render client-side) over `generateStaticParams` with fake workspace slug permutations.

2. **AI chat SSE proxy replacement in Tauri mode**
   - What we know: The SSE proxy route handler `api/v1/ai/chat/route.ts` is dropped in static export. The frontend AI chat component must call the backend directly.
   - What's unclear: Whether the CORS configuration on the FastAPI backend allows requests from `tauri://localhost` origin. This must be verified.
   - Recommendation: Add `tauri://localhost` to the FastAPI backend's allowed CORS origins as part of Plan 30-01 (or as a documented backend prerequisite). This is a backend config change, not a frontend code change.

3. **`useParams()` reliability across all 35 call-sites**
   - What we know: Client-side navigation via `router.push()` preserves `useParams()` values. Direct URL access (page refresh, direct link) in Tauri would fail to find the static file.
   - What's unclear: Whether the Tauri app's `app://` or `tauri://` scheme supports a SPA-style "catch-all" fallback to serve `index.html` for all routes, which would enable page refresh to work correctly.
   - Recommendation: Research the Tauri WebView `frontendDist` file serving behavior for missing paths — specifically whether a `404.html` or `index.html` fallback can be configured. Add `trailingSlash: true` and verify that navigating within the Tauri app works correctly for all main routes during Phase 30 testing.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 2.x (configured in `frontend/vitest.config.ts`) |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && pnpm test` |
| Full suite command | `cd frontend && pnpm test:coverage` |
| E2E command | `cd frontend && pnpm test:e2e` (Playwright) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHELL-01 | Tauri window launches and renders Next.js UI | manual smoke | Manual: `cd tauri-app && pnpm tauri dev` — verify window opens | ❌ Wave 0 |
| SHELL-01 | `isTauri()` returns true in Tauri context, false in browser | unit | `pnpm test -- --grep "isTauri"` | ❌ Wave 0 |
| SHELL-02 | `next build` with `NEXT_TAURI=true` succeeds without errors | CI smoke | `NEXT_TAURI=true pnpm build` — exit code 0 | ❌ Wave 0 (run in CI) |
| SHELL-02 | All dynamic routes navigate correctly in static export | manual smoke | Manual: launch Tauri app, navigate to `/[workspaceSlug]/issues/[issueId]` | ❌ Wave 0 |
| SHELL-02 | `next.config.ts` applies `output: 'export'` when `NEXT_TAURI=true` | unit | `pnpm test -- --grep "next config"` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd frontend && pnpm test` (Vitest unit tests, ~30s)
- **Per wave merge:** `cd frontend && pnpm test:coverage` (full suite with coverage)
- **Phase gate:** `NEXT_TAURI=true cd frontend && pnpm build` — static export build must succeed before marking phase complete

### Wave 0 Gaps

- [ ] `frontend/src/lib/__tests__/tauri.test.ts` — covers `isTauri()` detection (SHELL-01)
- [ ] `frontend/src/app/__tests__/next-config.test.ts` — covers build mode toggle logic (SHELL-02). Note: `next.config.ts` is a module; test by importing and checking behavior under env vars.
- [ ] CI: `NEXT_TAURI=true pnpm build` step added to `tauri-build.yml` before `tauri-action` — validates static export compiles cleanly on every PR

---

## Sources

### Primary (HIGH confidence)

- [Tauri v2 official docs — Next.js integration](https://v2.tauri.app/start/frontend/nextjs/) — static export requirement, `frontendDist` config, `devUrl` config
- [Tauri v2 official docs — project structure](https://v2.tauri.app/start/project-structure/) — `lib.rs` / `main.rs` split, Cargo.toml structure
- [Tauri v2 official docs — GitHub Actions pipeline](https://v2.tauri.app/distribute/pipelines/github/) — 4-runner matrix, `libwebkit2gtk-4.1-dev`, `swatinem/rust-cache`, `tauri-apps/tauri-action`
- [Tauri v2 official docs — capabilities](https://v2.tauri.app/security/capabilities/) — `capabilities/default.json` format, permission identifiers
- [Tauri v2 official docs — configuration](https://v2.tauri.app/reference/config/) — `tauri.conf.json` schema, `useHttpsScheme`, `identifier` immutability
- [Next.js static export guide](https://nextjs.org/docs/app/guides/static-exports) — full list of unsupported features, `trailingSlash` recommendation
- [Next.js issue #54393](https://github.com/vercel/next.js/issues/54393) — `useParams()` behavior in `output: export`
- [Next.js issue #79380](https://github.com/vercel/next.js/issues/79380) — dynamic params in client-only SPA with `output: export`
- [Codebase inspection] — `frontend/next.config.ts`, `frontend/src/app/api/`, `frontend/src/app/(workspace)/[workspaceSlug]/docs/[slug]/page.tsx`, `frontend/src/components/workspace-guard.tsx`, dynamic route inventory (35 `useParams()` call-sites)

### Secondary (MEDIUM confidence)

- [tauri-apps/tauri-action GitHub Action](https://github.com/tauri-apps/tauri-action) — `projectPath`, `tauriScript`, `args` parameters verified in action README
- [Tauri v2 + Next.js Monorepo Guide](https://melvinoostendorp.nl/blog/tauri-v2-nextjs-monorepo-guide) — community guide, consistent with official docs on `frontendDist` and `devUrl`
- [tauri-nextjs-starter](https://github.com/motz0815/tauri-nextjs-starter) — reference implementation for Next.js 15 + Tauri v2 monorepo structure

### Tertiary (LOW confidence)

- None for Phase 30 — all critical findings are backed by official sources or direct codebase inspection.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — Tauri v2 versions verified against official docs (2026-03-20); `tauri-apps/tauri-action` verified against official GitHub Actions guide
- Architecture: HIGH — `tauri.conf.json` patterns from official Tauri v2 docs; `next.config.ts` changes derived from direct inspection of the existing config file
- Pitfalls: HIGH — Static export issues confirmed via official Next.js docs + issue tracker; `libwebkit2gtk-4.1-dev` version confirmed in official Tauri v2 CI guide; docs page `fs.readFileSync` issue identified by direct codebase inspection
- Dynamic route behavior: MEDIUM-HIGH — Official docs confirm the limitation; empirical behavior in Tauri SPA mode requires verification in Plan 30-02

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (Tauri v2 and Next.js 16 are stable; unlikely to change in 30 days)
