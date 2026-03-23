# Phase 31: Auth Bridge - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Autonomous mode — derived from ROADMAP + research

<domain>
## Phase Boundary

Sync Supabase JWT from the WebView to the Tauri Rust backend, persist sessions across app restarts, store tokens securely in the OS keychain, and handle OAuth deep link redirects. This phase bridges web-based Supabase Auth to the native desktop environment.

</domain>

<decisions>
## Implementation Decisions

### Token Sync
- WebView calls `syncTokenToTauriStore()` in the root layout after Supabase auth state changes
- Tauri Store plugin (`pilot-auth.json`) is the intermediate storage between WebView and Rust
- Windows requires `useHttpsScheme: true` in tauri.conf.json (already set in Phase 30) to prevent localStorage reset

### Keychain Storage
- Use `tauri-plugin-keyring` (or OS-native credential APIs) for secure token storage
- Migrate from Tauri Store → OS keychain on app startup
- macOS: Keychain, Windows: Credential Manager, Linux: Secret Service (libsecret)

### OAuth Deep Links
- Register `pilotspace://auth/callback` custom URL scheme via `tauri-plugin-deep-link`
- Supabase PKCE OAuth flow: browser opens → user authenticates → redirect to `pilotspace://auth/callback?code=...`
- App intercepts deep link, extracts auth code, calls `supabase.auth.exchangeCodeForSession()`

### Claude's Discretion
- Token refresh strategy (proactive vs on-demand)
- Error handling for expired/invalid tokens
- Keychain service name and account conventions

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/supabase/` — existing Supabase client setup
- `frontend/src/stores/auth-store.ts` — MobX auth state management
- `tauri-app/src-tauri/src/lib.rs` — Tauri app setup (Phase 30)
- `frontend/src/lib/tauri.ts` — `isTauri()` detection utility (Phase 30)

### Established Patterns
- Supabase Auth with PKCE flow already in codebase
- MobX stores for UI state, TanStack Query for server state
- Tauri IPC via `@tauri-apps/api/core` invoke()

### Integration Points
- Root layout must call token sync after auth state changes
- Rust commands need auth token for API calls in later phases
- tauri.conf.json already has `useHttpsScheme: true` from Phase 30

</code_context>

<specifics>
## Specific Ideas

- Research identified auth bridge as "the hardest table-stakes feature"
- Apple WebView restricts non-HTTPS redirects — deep link approach required
- `auth-git2` crate (Phase 32+) will consume tokens from this bridge

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 31-auth-bridge*
*Context gathered: 2026-03-20 via autonomous mode*
