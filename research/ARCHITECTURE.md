# Architecture Research

**Domain:** Tauri Desktop Client — embedding existing Next.js web app with native git/CLI/terminal features
**Researched:** 2026-03-20
**Confidence:** HIGH (Tauri v2 official docs verified), MEDIUM (Next.js static export limitations verified via official source + community), HIGH (IPC patterns from official Tauri v2 docs)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        tauri-app/ (NEW)                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  WebView (Chromium/WebKit/WKWebView — per platform)          │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │  Next.js 15 static export (output: 'export')           │  │   │
│  │  │  • All existing pages/features unchanged               │  │   │
│  │  │  • Axios -> NEXT_PUBLIC_API_URL (remote FastAPI)        │  │   │
│  │  │  • Supabase client -> remote Supabase                  │  │   │
│  │  │  • MobX + TanStack Query (unchanged)                   │  │   │
│  │  │  • xterm.js terminal panel (NEW component)             │  │   │
│  │  │  • Diff viewer panel (NEW component)                   │  │   │
│  │  │  • TauriStore adapter for auth tokens (NEW)            │  │   │
│  │  └────────────────┬───────────────────────────────────────┘  │   │
│  └───────────────────┼──────────────────────────────────────────┘   │
│                       │ @tauri-apps/api invoke() / Channel events    │
│                       v                                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  src-tauri/ (Rust — Tauri v2 backend)                        │   │
│  │                                                              │   │
│  │  Commands (IPC handlers):                                    │   │
│  │  • git_clone, git_pull, git_push, git_status, git_diff       │   │
│  │  • spawn_terminal, write_stdin, kill_terminal                 │   │
│  │  • run_pilot_command (pilot-cli sidecar wrapper)             │   │
│  │  • run_shell_command (tests, builds)                         │   │
│  │  • get_auth_token, set_auth_token (Store bridge)             │   │
│  │  • get_workspace_dir, set_workspace_dir                      │   │
│  │                                                              │   │
│  │  State (managed via tauri::State<T>):                        │   │
│  │  • GitState (open Repository handles, credential cache)      │   │
│  │  • TerminalState (PTY handles by session_id)                 │   │
│  │  • SidecarState (pilot-cli child handle)                     │   │
│  │                                                              │   │
│  │  Sidecar:                                                    │   │
│  │  • pilot-cli (PyInstaller per platform, no Python required)  │   │
│  │    spawned on-demand, output streamed via Channel<String>    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

External (unchanged, remote):
  FastAPI backend     https://api.pilotspace.io  (or self-hosted)
  Supabase Auth       https://supabase.pilotspace.io:18000
  PostgreSQL + Redis  (inaccessible directly from desktop client)
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `tauri-app/src-tauri/` | Rust Tauri v2 backend: IPC commands, process management, git ops | Tauri v2, git2-rs, tauri-plugin-shell, tauri-plugin-store |
| `tauri-app/` (root) | Tauri project root with `tauri.conf.json`, Tauri CLI build target | Points devUrl at `http://localhost:3000`, frontendDist at `../frontend/out` |
| `frontend/` (existing, modified) | Next.js static export in Tauri build mode; adds Tauri-aware feature flags | Conditional `output: 'export'` via `NEXT_TAURI=true`; `isTauri()` guard |
| `frontend/src/lib/tauri.ts` (NEW) | Typed wrapper for all `invoke()` calls; `isTauri()` platform detection | Re-exports typed wrappers; never use `@tauri-apps/api` directly in components |
| `frontend/src/features/terminal/` (NEW) | xterm.js embedded terminal panel | xterm.js + tauri-plugin-pty or shell plugin streaming |
| `frontend/src/features/git/` (NEW) | Diff viewer, commit/stage UI, git status bar | React components consuming Tauri `git_*` IPC commands |
| pilot-cli sidecar | `pilot implement` compiled binary, no Python runtime on user machine | PyInstaller (per platform, built in CI matrix per OS runner) |
| Tauri Store | Persistent KV store for auth tokens and workspace dir; readable from both JS and Rust | `@tauri-apps/plugin-store` in JS, `tauri-plugin-store` in Rust |

## Recommended Project Structure

```
tauri-app/                             # NEW top-level directory in monorepo
├── package.json                       # devDep: @tauri-apps/cli; scripts: tauri dev, tauri build
└── src-tauri/
    ├── Cargo.toml                     # Rust deps: tauri, git2, tauri-plugin-shell,
    │                                  #   tauri-plugin-store, tauri-plugin-pty
    ├── tauri.conf.json                # app id, devUrl, frontendDist, externalBin, bundle
    ├── build.rs                       # tauri_build::build()
    ├── capabilities/
    │   └── default.json               # IPC permissions: shell:allow-spawn, shell:allow-sidecar,
    │                                  #   store:allow-*, pty:allow-*
    ├── icons/                         # App icons (PNG 32-512, ICNS, ICO)
    └── src/
        ├── main.rs                    # Desktop entry: lib::run()
        ├── lib.rs                     # tauri::Builder, invoke_handler!, plugin registration
        ├── commands/
        │   ├── mod.rs
        │   ├── git.rs                 # git_clone, git_pull, git_push, git_status, git_diff
        │   ├── terminal.rs            # spawn_terminal, write_stdin, kill_terminal
        │   ├── shell.rs               # run_pilot_command, run_shell_command
        │   ├── auth.rs                # get_auth_token, set_auth_token (Store bridge)
        │   └── workspace.rs           # get_workspace_dir, set_workspace_dir
        └── state/
            ├── mod.rs
            ├── git_state.rs           # Managed state: open Repository handles
            ├── terminal_state.rs      # Managed state: HashMap<SessionId, Child>
            └── sidecar_state.rs       # Managed state: Option<Child> for pilot-cli

# In existing frontend/ — minimal additions:
frontend/
├── next.config.ts                     # MODIFIED: conditional output: 'export' when NEXT_TAURI=true
├── src/
│   ├── lib/
│   │   ├── tauri.ts                   # NEW: isTauri(), typed invoke() wrappers
│   │   └── tauri-auth.ts              # NEW: syncTokenToTauriStore()
│   ├── features/
│   │   ├── terminal/                  # NEW: xterm.js terminal panel
│   │   │   ├── components/
│   │   │   │   └── TerminalPanel.tsx  # xterm.js terminal UI
│   │   │   └── hooks/
│   │   │       └── useTerminal.ts     # session lifecycle, output streaming
│   │   └── git/                       # NEW: git operations UI
│   │       ├── components/
│   │       │   ├── DiffViewer.tsx     # unified diff renderer
│   │       │   ├── CommitPanel.tsx    # stage/commit UI
│   │       │   └── GitStatusBar.tsx   # branch, ahead/behind display
│   │       ├── stores/
│   │       │   └── GitStore.ts        # MobX observable git state
│   │       └── hooks/
│   │           └── useGitOps.ts       # TanStack mutation wrappers
│   └── app/
│       └── layout.tsx                 # MODIFIED: call syncTokenToTauriStore() on mount

# In existing cli/ — build artifacts (not committed):
cli/
└── dist/                              # PyInstaller output per platform
    ├── pilot-aarch64-apple-darwin     # macOS Apple Silicon
    ├── pilot-x86_64-apple-darwin      # macOS Intel
    ├── pilot-x86_64-unknown-linux-gnu # Linux x64
    └── pilot-x86_64-pc-windows-msvc.exe  # Windows
```

### Structure Rationale

- **`tauri-app/` as new top-level directory:** Tauri requires a `src-tauri/` subtree with `tauri.conf.json`. Placing the Tauri project at a new top-level `tauri-app/` mirrors how `frontend/`, `backend/`, and `cli/` are organized — each package is self-contained. A nested location (e.g., inside `frontend/`) would pollute the frontend package boundary.

- **`tauri.conf.json` points at `../frontend`:** `devUrl: "http://localhost:3000"` for development (Next.js dev server). `frontendDist: "../frontend/out"` for production (static export). This avoids copying or duplicating frontend code into `src-tauri/`.

- **`frontend/src/lib/tauri.ts` wrapper:** Centralizes all `invoke()` calls and `isTauri()` detection. Components never import `@tauri-apps/api` directly — this keeps the codebase deployable as both web app and desktop app. The module can be mocked entirely in Vitest.

- **`commands/` sub-modules in Rust:** Keeps `lib.rs` clean. Each domain (git, terminal, shell, auth, workspace) gets its own module with a focused command surface area. Avoids a 1000-line `lib.rs`.

- **`state/` sub-modules:** Tauri manages shared Rust state via `tauri::State<T>`. Separate structs per domain prevent a monolithic state blob and allow independent `Mutex<T>` locking without contention.

## Architectural Patterns

### Pattern 1: Static Export Mode Toggle

**What:** Next.js supports `output: 'standalone'` (Docker/SSR web deploy) and `output: 'export'` (Tauri static embedding). The codebase must support both with a single `next.config.ts`.

**When to use:** Always. The Tauri `beforeBuildCommand` in `tauri.conf.json` sets `NEXT_TAURI=true` before running `next build`. Web CI pipelines do not set this variable.

**Trade-offs:** Two code paths in one config file. The main constraint: Next.js API routes and route handlers do not generate static output. The existing `app/api/health/route.ts` (which uses `force-dynamic`) is silently skipped in export mode — no error, but no file generated.

**Example:**
```typescript
// next.config.ts
const isTauriBuild = process.env.NEXT_TAURI === 'true';
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';

const nextConfig: NextConfig = {
  // Standalone for Docker, export for Tauri
  output: isTauriBuild ? 'export' : 'standalone',
  images: {
    // Static export cannot optimize images at request time
    unoptimized: isTauriBuild,
    remotePatterns: isTauriBuild ? [] : [
      { protocol: 'https', hostname: '*.supabase.co', pathname: '/storage/v1/object/public/**' }
    ],
  },
  // Rewrites only work with a Node.js server — skip for Tauri
  ...(isTauriBuild ? {} : {
    async rewrites() {
      return [{ source: '/api/v1/:path*', destination: `${BACKEND_URL}/api/v1/:path*` }];
    },
  }),
};
```

### Pattern 2: Typed IPC Command Wrapper

**What:** All Tauri IPC calls go through `frontend/src/lib/tauri.ts`. TypeScript types mirror Rust command signatures exactly. No component ever calls `invoke('some-string')` directly.

**When to use:** Every new Rust command gets a corresponding typed wrapper in `tauri.ts` before any consumer uses it. This is the single point of contact between the frontend and native layer.

**Trade-offs:** One extra indirection layer, but removes string-literal command names from business logic, enables complete mocking in Vitest, and makes the native API surface visible at a glance.

**Example:**
```typescript
// frontend/src/lib/tauri.ts
import { invoke } from '@tauri-apps/api/core';

export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

export interface GitStatusResult {
  branch: string;
  ahead: number;
  behind: number;
  modified: string[];
  staged: string[];
  untracked: string[];
}

export async function gitStatus(repoPath: string): Promise<GitStatusResult> {
  return invoke<GitStatusResult>('git_status', { repoPath });
}

// Channel-based streaming for long operations
export async function gitClone(
  url: string,
  targetDir: string,
  onProgress: (pct: number, message: string) => void
): Promise<void> {
  const { Channel } = await import('@tauri-apps/api/core');
  const channel = new Channel<{ pct: number; message: string }>();
  channel.onmessage = ({ pct, message }) => onProgress(pct, message);
  return invoke('git_clone', { url, targetDir, onProgress: channel });
}
```

### Pattern 3: Auth Token Bridge (WebView to Rust)

**What:** The Supabase JWT lives in the WebView's `localStorage` (managed by the Supabase JS client). Rust commands that need auth (e.g., git push over HTTPS with token, or making authenticated backend calls from Rust) read the token via the Tauri Store plugin.

**When to use:** Call `syncTokenToTauriStore()` once in the root layout `useEffect` (Tauri mode only). Any Rust command needing the JWT reads from the Store rather than making a round-trip back to the WebView.

**Trade-offs:** The Tauri Store file (`pilot-auth.json`) is written to the app data directory. On macOS, `tauri-plugin-store` files are not encrypted by default — they are plaintext JSON. For higher security, use `tauri-plugin-stronghold` or OS keychain APIs. For v1.1, the Store is acceptable.

**Critical Windows config:** Set `"useHttpsScheme": true` in the `app > windows` section of `tauri.conf.json`. Without this, `localStorage` and `IndexedDB` are reset on every app restart on Windows.

**Example:**
```typescript
// frontend/src/lib/tauri-auth.ts
import { load } from '@tauri-apps/plugin-store';
import { supabase } from '@/lib/supabase';
import { isTauri } from './tauri';

export async function syncTokenToTauriStore(): Promise<void> {
  if (!isTauri()) return;
  const store = await load('pilot-auth.json', { autoSave: true });
  supabase.auth.onAuthStateChange(async (_event, session) => {
    if (session?.access_token) {
      await store.set('access_token', session.access_token);
      await store.set('refresh_token', session.refresh_token ?? null);
    } else {
      await store.delete('access_token');
      await store.delete('refresh_token');
    }
  });
}
```

```rust
// src-tauri/src/commands/auth.rs
use tauri_plugin_store::StoreExt;

#[tauri::command]
pub async fn get_auth_token(app: tauri::AppHandle) -> Result<Option<String>, String> {
    let store = app.store("pilot-auth.json").map_err(|e| e.to_string())?;
    let token = store.get("access_token")
        .and_then(|v| v.as_str().map(String::from));
    Ok(token)
}
```

### Pattern 4: Sidecar Lifecycle with Streaming Output

**What:** `pilot-cli` runs as a Tauri sidecar (PyInstaller-compiled binary per platform). Long-running commands like `pilot implement PS-123` stream output back to the WebView via `tauri::ipc::Channel<String>`. The xterm.js panel renders each line in real time.

**When to use:** Every invocation of `pilot implement`, `pilot login`. Never fire-and-forget a sidecar — always attach an output channel so the terminal panel receives live output and the user can see what is happening.

**Trade-offs:** PyInstaller binaries are ~30-80 MB per platform. Cannot cross-compile — requires OS-specific CI runners (macOS, Linux, Windows) to produce each binary. Must throttle `channel.send()` calls during progress callbacks to avoid overwhelming the WebView event loop.

**Example:**
```rust
// src-tauri/src/commands/shell.rs
use tauri_plugin_shell::ShellExt;
use tauri::ipc::Channel;

#[tauri::command]
pub async fn run_pilot_command(
    app: tauri::AppHandle,
    args: Vec<String>,
    on_output: Channel<String>,
) -> Result<i32, String> {
    let (mut rx, _child) = app.shell()
        .sidecar("pilot")
        .map_err(|e| e.to_string())?
        .args(&args)
        .spawn()
        .map_err(|e| e.to_string())?;

    while let Some(event) = rx.recv().await {
        match event {
            tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                let _ = on_output.send(String::from_utf8_lossy(&line).into_owned());
            }
            tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                let _ = on_output.send(format!("[stderr] {}", String::from_utf8_lossy(&line)));
            }
            tauri_plugin_shell::process::CommandEvent::Terminated(status) => {
                return Ok(status.code.unwrap_or(-1));
            }
            _ => {}
        }
    }
    Ok(0)
}
```

### Pattern 5: Git Operations via git2-rs

**What:** All git operations run in async Tauri commands backed by the `git2` crate. No shelling out to the `git` binary — it is not guaranteed to be installed, especially on Windows. Progress (clone percentage) streams via `Channel<GitProgress>`.

**When to use:** Clone, pull, push, status, diff. The Rust side owns Repository handles in `GitState` (Mutex-protected); the WebView only sees serializable result types.

**Trade-offs:** git2 links `libgit2` statically in Tauri builds. Diff output is raw unified patch text — the frontend diff viewer must parse this or use a React diff library such as `react-diff-view`. Credential management (PAT for HTTPS, SSH key path for SSH) must be explicit in git2 credential callbacks; store PATs in the Tauri Store.

**Example:**
```rust
// src-tauri/src/commands/git.rs
use git2::{Repository, RemoteCallbacks, FetchOptions, build::RepoBuilder};
use tauri::ipc::Channel;

#[derive(serde::Serialize, Clone)]
pub struct GitProgress { pub pct: u32, pub message: String }

#[tauri::command]
pub async fn git_clone(
    url: String,
    target_dir: String,
    on_progress: Channel<GitProgress>,
) -> Result<(), String> {
    let mut callbacks = RemoteCallbacks::new();
    let mut last_pct = 0u32;
    callbacks.transfer_progress(|stats| {
        if stats.total_objects() > 0 {
            let pct = (stats.received_objects() * 100 / stats.total_objects()) as u32;
            // Throttle: only send when pct changes by >=2 to avoid flooding WebView
            if pct >= last_pct + 2 || pct == 100 {
                last_pct = pct;
                let _ = on_progress.send(GitProgress {
                    pct,
                    message: format!("{}/{} objects", stats.received_objects(), stats.total_objects()),
                });
            }
        }
        true
    });
    let mut fo = FetchOptions::new();
    fo.remote_callbacks(callbacks);
    RepoBuilder::new()
        .fetch_options(fo)
        .clone(&url, std::path::Path::new(&target_dir))
        .map_err(|e| e.to_string())?;
    Ok(())
}
```

## Data Flow

### Request Flow: Web App API Calls (unchanged in Tauri)

```
User action in WebView
    |
    v
React component (observer) -> TanStack Query mutation
    |
    v
Axios client (src/services/api/client.ts)
    -> Authorization: Bearer <supabase_jwt>   (from getAuthProviderSync().getToken())
    -> X-Workspace-Id header                  (from localStorage)
    |
    v
NEXT_PUBLIC_API_URL -> https://api.pilotspace.io/api/v1/...
    |
    v
FastAPI backend (remote, unchanged)
```

Note: In Tauri mode, there is no Next.js server proxy. `NEXT_PUBLIC_API_URL` must be the full backend URL, baked into the static export at build time. The existing `/api/v1/:path*` rewrite in `next.config.ts` is disabled when `NEXT_TAURI=true`.

### Request Flow: Native Git Operation

```
User clicks "Clone Repo" in Git panel
    |
    v
GitStore.cloneRepo(url, dir)    [MobX action]
    |
    v
tauri.ts: gitClone(url, dir, progressCallback)
    |
    v
invoke('git_clone', { url, targetDir, onProgress: channel })  -- IPC
    |
    v
Rust: git.rs::git_clone command
    -> git2::build::RepoBuilder::clone()
    -> callbacks.transfer_progress -> channel.send(GitProgress)
    |
    v
Channel events -> progressCallback(pct, msg)   -- back in WebView
    |
    v
GitStore.cloneProgress observable -> ProgressBar component re-renders
```

### Request Flow: pilot CLI Execution

```
User clicks "Implement PS-123" (or types in xterm.js terminal)
    |
    v
TerminalStore.runPilotCommand(['implement', 'PS-123'])  [MobX action]
    |
    v
invoke('run_pilot_command', { args, onOutput: channel })
    |
    v
Rust: shell.rs::run_pilot_command
    -> app.shell().sidecar("pilot").args(...).spawn()
    -> CommandEvent::Stdout/Stderr -> channel.send(line)
    |
    v
Channel events -> xterm.js writeln(line)   -- real-time terminal output
    |
    v
CommandEvent::Terminated -> TerminalStore.commandExitCode = n
```

### Auth Token Flow

```
App startup (Tauri mode):
    |
    v
root layout useEffect: syncTokenToTauriStore() called
    |
    v
supabase.auth.onAuthStateChange -> store.set('access_token', jwt)
    |
    v
Tauri Store: pilot-auth.json persisted to app data dir

When Rust needs token (git push with PAT, etc.):
    |
    v
get_auth_token command -> app.store("pilot-auth.json").get("access_token")
    |
    v
Returns Option<String> JWT to calling Rust code
```

### State Management

```
WebView (JavaScript):
  MobX RootStore (existing + additions)
    ├── GitStore (NEW)
    │     observables: repoPath, branch, status, cloneProgress, diffOutput
    │     actions: cloneRepo, pullRepo, pushRepo, stageFile, commitChanges
    │     -> invoke() via tauri.ts wrappers
    ├── TerminalStore (NEW)
    │     observables: sessions Map<id, TerminalSession>, activeSessionId
    │     actions: createSession, closeSession, runPilotCommand, writeInput
    │     -> invoke() via tauri.ts wrappers
    └── (all existing stores unchanged)

Rust (Tauri managed state):
  tauri::State<Mutex<GitState>>       (open Repository handles per path)
  tauri::State<Mutex<TerminalState>>  (active PTY child handles by session_id)
  tauri::State<Mutex<SidecarState>>   (running pilot-cli child, if any)
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single developer | Current approach sufficient; all native state in-process |
| Team (5-50) | No change — each user has their own desktop install; collaboration state stays on remote backend |
| Enterprise (50-500) | Desktop app is purely a local shell; all collaboration data stays in FastAPI+PostgreSQL; no peer-to-peer needed |

### Scaling Priorities

1. **First bottleneck:** Large repo clones blocking UI. Mitigated by streaming progress via Channel. `git2` clone runs on the Tauri async tokio runtime, never blocking the WebView event loop. Throttle `channel.send()` calls (send on pct change >= 2, not every object).

2. **Second bottleneck:** Multiple simultaneous terminal sessions. Use `HashMap<SessionId, Child>` in `TerminalState`; each session gets its own OS PTY. Limit to approximately 10 concurrent sessions with UI enforcement.

## Anti-Patterns

### Anti-Pattern 1: Bundling the Backend

**What people do:** Try to bundle FastAPI + PostgreSQL + Supabase into the Tauri app for offline use.

**Why it's wrong:** FastAPI + Python runtime + PostgreSQL + Supabase + Redis = hundreds of MB, complex startup orchestration, and platform-specific dependency issues. The PROJECT.md explicitly chose "Remote FastAPI backend (not bundled)" because enterprise users already have a deployed backend.

**Do this instead:** Always connect to the remote backend via `NEXT_PUBLIC_API_URL`. If offline caching becomes a requirement later, implement TanStack Query offline persistence — not a bundled server.

### Anti-Pattern 2: Scattered `invoke()` Calls

**What people do:** Import `@tauri-apps/api` and call `invoke('command-name', {...})` directly in components and stores throughout the codebase.

**Why it's wrong:** String-based command names have no type safety. Component code becomes untestable. Web deploy breaks because `@tauri-apps/api` throws when `window.__TAURI_INTERNALS__` is absent, causing hydration errors on the web build.

**Do this instead:** All `invoke()` calls live in `frontend/src/lib/tauri.ts`. Components and stores call typed wrapper functions. The `isTauri()` guard is checked once per wrapper. The entire module can be mocked in Vitest.

### Anti-Pattern 3: SSR/Server Features in Tauri Static Export

**What people do:** Use Next.js API routes, Server Actions, or server-only `fetch` in Server Components, then wonder why the Tauri build fails.

**Why it's wrong:** `output: 'export'` strips all server-side code. The existing `app/api/health/route.ts` uses `export const dynamic = 'force-dynamic'` — this is silently skipped in export mode. The proxy rewrite at `/api/v1/:path*` requires a running Next.js server and is unavailable in the static export.

**Do this instead:** All API calls go to the remote FastAPI backend via `NEXT_PUBLIC_API_URL` (full URL). The proxy rewrite is disabled when `NEXT_TAURI=true`. There are no server-only pages in this codebase (all data fetching is TanStack Query client-side), so existing pages work without modification.

### Anti-Pattern 4: Single Platform Sidecar Build

**What people do:** Build the PyInstaller binary on macOS and assume it works on all platforms.

**Why it's wrong:** PyInstaller cannot cross-compile. A macOS arm64 binary cannot run on Linux x86_64 or Windows. Tauri requires architecture-specific suffix naming: `pilot-aarch64-apple-darwin`, `pilot-x86_64-apple-darwin`, `pilot-x86_64-unknown-linux-gnu`, `pilot-x86_64-pc-windows-msvc.exe`.

**Do this instead:** Use a GitHub Actions matrix with `runs-on: [macos-latest, macos-13, ubuntu-latest, windows-latest]`. Each runner builds its own PyInstaller binary and places it in `tauri-app/binaries/` with the correct triple suffix before `tauri build` executes.

### Anti-Pattern 5: Dynamic Route Pages Without Client-Side Data Fetching

**What people do:** Assume dynamic routes like `[workspaceSlug]` or `[issueId]` work automatically in static export mode because they work in SSR mode.

**Why it's wrong:** With `output: 'export'`, Next.js cannot server-render dynamic routes at request time. `generateStaticParams()` would require enumerating all workspace slugs at build time — impossible for a SaaS app.

**Do this instead:** This codebase already uses the correct pattern — all data fetching is TanStack Query client-side in observer components. The existing pages use `'use client'` implicitly (via MobX observer) and fetch after hydration. No changes needed for existing pages; new Tauri-specific pages must follow the same client-side pattern.

### Anti-Pattern 6: Unthrottled Channel Progress Callbacks

**What people do:** Call `channel.send()` on every git transfer progress event (potentially thousands of times per second during clone).

**Why it's wrong:** Frequent IPC calls to the WebView via `Channel` can freeze the UI. The Tauri team explicitly documented this gotcha for git2 progress callbacks.

**Do this instead:** Throttle `channel.send()` — only send when progress changes by 2+ percentage points or at operation completion. Store `last_pct` in the closure and gate on the delta.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Remote FastAPI backend | Axios -> `NEXT_PUBLIC_API_URL` (full URL; no proxy in Tauri mode) | CORS must be enabled on the backend for `tauri://localhost` origin |
| Remote Supabase Auth | Supabase JS client (unchanged); token synced to Tauri Store via `onAuthStateChange` | Set `useHttpsScheme: true` in `tauri.conf.json` on Windows to prevent localStorage reset |
| GitHub (git operations) | git2-rs credential callbacks; PAT stored in Tauri Store | SSH key support via git2 ssh credentials; no GitHub OAuth in v1.1 |
| pilot-cli sidecar | `app.shell().sidecar("pilot")` with output streamed via `Channel<String>` | Per-platform binary built by CI matrix (4 runners) |

### Internal Boundaries: New vs. Modified

| Boundary | Communication | Status |
|----------|---------------|--------|
| WebView JS -> Rust commands | `invoke()` via Tauri IPC (JSON-RPC over custom protocol) | NEW: `frontend/src/lib/tauri.ts` wrapper module |
| WebView JS -> auth token store | `@tauri-apps/plugin-store` read/write | NEW: `syncTokenToTauriStore()` called in root layout |
| Rust commands -> git2 | Direct Rust function calls within `commands/git.rs` | NEW: entire `git.rs` module |
| Rust commands -> pilot-cli sidecar | `tauri_plugin_shell::ShellExt::sidecar()` + streaming channel | NEW: `commands/shell.rs` |
| Rust commands -> PTY / xterm.js | `tauri-plugin-pty` (pseudo-terminal) or shell plugin streaming | NEW: `commands/terminal.rs` |
| `frontend/next.config.ts` | Conditional `output: 'export'` for Tauri build mode | MODIFIED: `NEXT_TAURI` env var branch |
| `frontend/src/services/api/client.ts` | `NEXT_PUBLIC_API_URL` must be full URL in Tauri mode; no `/api/v1` proxy | MODIFIED: remove implicit proxy fallback assumption in Tauri build |
| `frontend/src/app/layout.tsx` | Add `syncTokenToTauriStore()` call in useEffect | MODIFIED |
| Monorepo root | Add `tauri-app/` directory | NEW: entire directory |
| GitHub Actions CI | Add Tauri build matrix job (4 runners: macos-latest, macos-13, ubuntu-latest, windows-latest) | NEW: `.github/workflows/tauri-build.yml` |

### Build Order Considerations

| Order | Task | Depends On | Rationale |
|-------|------|------------|-----------|
| 1 | `tauri-app/` scaffold, `tauri.conf.json`, `src-tauri/` skeleton | Nothing | Foundation; must exist before anything else |
| 2 | `frontend/next.config.ts` static export mode | Scaffold | Verify Next.js builds cleanly with `output: 'export'`; surface route/component issues early |
| 3 | Dynamic route fix audit (if any routes fail static export) | Export mode | Must be clean before Tauri can load the static output |
| 4 | Tauri Store auth bridge (`tauri-auth.ts` + `auth.rs`) | Scaffold + export mode | Auth bridge needed before any authenticated native operations |
| 5 | git2-rs commands (status, diff, clone, pull, push) | Auth bridge | Core native capability; git ops require auth for push |
| 6 | Git UI components (DiffViewer, CommitPanel, GitStatusBar, GitStore) | git2-rs commands | Frontend over the git IPC layer |
| 7 | pilot-cli sidecar compilation (PyInstaller CI matrix) | CLI binary | Parallel with git work; sidecar binary needed before terminal integration |
| 8 | xterm.js terminal panel + streaming output | Sidecar compilation | Terminal renders sidecar output |
| 9 | Shell command execution (test/build runner) | Terminal panel | Reuses terminal panel infrastructure |
| 10 | Cross-platform build pipeline (GitHub Actions matrix + signing) | All above | Package everything; macOS notarization, Windows signing |

## Sources

- [Tauri v2: Next.js Integration](https://v2.tauri.app/start/frontend/nextjs/) — HIGH confidence (official Tauri docs)
- [Tauri v2: Calling Rust from Frontend (IPC)](https://v2.tauri.app/develop/calling-rust/) — HIGH confidence (official Tauri docs)
- [Tauri v2: Embedding External Binaries (Sidecars)](https://v2.tauri.app/develop/sidecar/) — HIGH confidence (official Tauri docs)
- [Tauri v2: Shell Plugin](https://v2.tauri.app/plugin/shell/) — HIGH confidence (official Tauri docs)
- [Tauri v2: Store Plugin](https://v2.tauri.app/plugin/store/) — HIGH confidence (official Tauri docs)
- [Tauri v2: GitHub Actions Pipeline](https://v2.tauri.app/distribute/pipelines/github/) — HIGH confidence (official Tauri docs)
- [Tauri v2: Project Structure](https://v2.tauri.app/start/project-structure/) — HIGH confidence (official Tauri docs)
- [git2 crate documentation](https://docs.rs/git2) — HIGH confidence (official Rust crate docs)
- [git2 clone progress + Tauri channel throttling](https://dev.to/yexiyue/how-to-implement-git-clone-operation-progress-display-and-cancellation-in-rust-with-tauri-and-git2-37ec) — MEDIUM confidence (community verified, throttle requirement confirmed)
- [Tauri v2 + Next.js Monorepo Guide](https://melvinoostendorp.nl/blog/tauri-v2-nextjs-monorepo-guide) — MEDIUM confidence (community blog, consistent with official docs)
- [tauri-nextjs-starter (Next.js v15 + Tauri v2)](https://github.com/motz0815/tauri-nextjs-starter) — MEDIUM confidence (community reference implementation)
- [Next.js App Router static export: dynamic routes discussion](https://github.com/vercel/next.js/discussions/64660) — MEDIUM confidence (official Next.js discussion, confirmed limitation)
- [Supabase + Tauri: PKCE auth + localStorage pattern](https://medium.com/@nathancovey23/supabase-google-oauth-in-a-tauri-2-0-macos-app-with-deep-links-f8876375cb0a) — MEDIUM confidence (community implementation, consistent with Tauri security docs)
- [tauri-plugin-pty for embedded terminal](https://github.com/Tnze/tauri-plugin-pty) — MEDIUM confidence (community plugin; evaluate vs `tauri-plugin-shell` streaming at implementation time)
- [Tauri v2: Windows localStorage requires useHttpsScheme](https://github.com/tauri-apps/tauri/issues/10981) — MEDIUM confidence (official GitHub issue)

---
*Architecture research for: Tauri Desktop Client — Pilot Space v1.1*
*Researched: 2026-03-20*
