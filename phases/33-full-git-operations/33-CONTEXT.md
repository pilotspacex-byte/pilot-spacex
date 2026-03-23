# Phase 33: Full Git Operations - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Autonomous mode — derived from ROADMAP + research

<domain>
## Phase Boundary

Add pull, push, branch management (list/create/switch/delete), working directory status (changed/staged/untracked files), and merge conflict detection on top of the git2-rs foundation from Phase 32. This completes the core git client capabilities.

</domain>

<decisions>
## Implementation Decisions

### Pull & Push
- Reuse git2-rs + auth-git2 credential pattern from Phase 32's git.rs
- Progress streaming via `tauri::ipc::Channel` with 2% throttle (same as clone)
- Pull uses fetch + merge (fast-forward preferred, notify on conflict)
- Push requires upstream tracking branch; error clearly if not set

### Branch Management
- List: `git2::Repository::branches()` with local + remote filter
- Create: from current HEAD, optional tracking setup
- Switch: `git2::Repository::set_head()` + checkout
- Delete: refuse if branch is current; warn if unmerged

### Status
- `git2::Repository::statuses()` for changed/staged/untracked files
- Group by status type (modified, added, deleted, untracked, conflicted)
- Return file paths relative to repo root

### Conflict Detection
- During pull, check for conflicted entries in status after merge
- Present list of conflicted files to user
- Do NOT auto-resolve — user handles externally (in their editor)

### Claude's Discretion
- MobX GitStore structure and observable state design
- Status refresh strategy (on-demand vs polling vs filesystem watcher)
- Branch selector UI component design
- Conflict notification UI pattern

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tauri-app/src-tauri/src/commands/git.rs` — clone + credential pattern (Phase 32)
- `frontend/src/lib/tauri.ts` — IPC wrappers pattern established
- `frontend/src/stores/features/projects/ProjectStore.ts` — MobX store pattern
- `frontend/src/features/projects/components/` — dashboard UI pattern

### Established Patterns
- Rust git commands use `spawn_blocking` for git2 operations (not Send)
- Progress streaming via Channel with throttle
- MobX observable stores + observer components
- shadcn/ui for consistent UI components

### Integration Points
- Extend `commands/git.rs` with pull, push, status, branch commands
- Register new commands in `lib.rs` invoke handler
- Add new IPC wrappers to `frontend/src/lib/tauri.ts`
- Create GitStore and git UI components

</code_context>

<specifics>
## Specific Ideas

- Git status should be refreshable from the project dashboard
- Branch selector could be a dropdown in the dashboard card header
- Conflict notification should be prominent but non-blocking

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-full-git-operations*
*Context gathered: 2026-03-20 via autonomous mode*
