# Phase 32: Workspace Management + Git Clone - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Autonomous mode — derived from ROADMAP + research

<domain>
## Phase Boundary

App-managed project directory system with configurable base path, git clone with progress/cancellation, linking existing repos, project status dashboard, and HTTPS+PAT credential configuration. This is the first phase that gives users local filesystem capabilities.

</domain>

<decisions>
## Implementation Decisions

### Workspace Directory
- Default base path: `~/PilotSpace/projects/` (created on first launch if missing)
- User can change base path via native folder picker (tauri-plugin-dialog)
- Configuration persisted in Tauri Store (`workspace-config.json`)
- Each cloned repo gets its own subdirectory under the base path

### Git Clone
- Use `git2-rs` with `vendored-libgit2` feature (no system dependency)
- Use `auth-git2` crate for credential callback loop protection
- Progress reported via `tauri::ipc::Channel` with 2% throttle (not per-object)
- Cancellation via `AtomicBool` checked in progress callback
- HTTPS + Personal Access Token as primary auth (SSH only macOS/Linux, deferred)

### Existing Repos
- User can link an existing local folder via folder picker dialog
- App validates it's a git repo (checks for `.git/` directory)
- Linked repos tracked in Tauri Store alongside cloned repos

### Project Status Dashboard
- Shows all managed repos (cloned + linked) with:
  - Repo name, path, remote URL
  - Sync status (up-to-date, behind, ahead, diverged)
  - Last activity timestamp
- Refresh on app focus or manual trigger

### Claude's Discretion
- MobX store structure for workspace state
- Dashboard layout and component hierarchy
- Error handling for inaccessible/deleted repos

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/tauri.ts` — IPC invoke wrappers (Phase 30)
- `frontend/src/lib/tauri-auth.ts` — auth token sync (Phase 31)
- `tauri-app/src-tauri/src/commands/auth.rs` — Rust command pattern (Phase 31)
- `tauri-app/src-tauri/capabilities/default.json` — permissions model

### Established Patterns
- Tauri IPC: TypeScript → `invoke('command_name', { args })` → Rust `#[tauri::command]`
- Progress streaming: `tauri::ipc::Channel` for real-time updates
- MobX stores for UI state, TanStack Query for server state
- shadcn/ui components for consistent design

### Integration Points
- `tauri-app/src-tauri/src/lib.rs` — register new commands in invoke handler
- `tauri-app/src-tauri/Cargo.toml` — add git2, auth-git2 dependencies
- Frontend sidebar — add workspace/project navigation

</code_context>

<specifics>
## Specific Ideas

- Research warns: git2 `Repository` is NOT `Send` — use managed state mutex pattern
- Research warns: git2-rs credential callbacks loop infinitely on auth failure — `auth-git2` crate has loop detection
- Progress throttle to 2% increments prevents WebView memory issues (research pitfall)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-workspace-management-git-clone*
*Context gathered: 2026-03-20 via autonomous mode*
