# Phase 37: One-Click Implement Flow + Tray - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Autonomous mode — derived from ROADMAP + research

<domain>
## Phase Boundary

End-to-end "Implement Issue" orchestration: user selects an issue, app creates a branch, runs `pilot implement` via sidecar with terminal output, then stages/commits/pushes the result. System tray with minimize-to-tray and background notifications for completion/CI events.

</domain>

<decisions>
## Implementation Decisions

### Run Pilot Implement (CLI-02)
- Spawn pilot-cli sidecar with `implement <issue-id>` args
- Stream stdout/stderr to embedded terminal (Phase 34)
- Show real-time progress in terminal panel
- Handle exit codes (0=success, non-zero=failure with message)

### One-Click Implement Flow (CLI-03)
- User clicks "Implement" on an issue in the web UI
- App orchestrates: create branch → run `pilot implement` → stage all → commit → push
- Each step shown as progress indicator
- Failure at any step stops the flow with clear error
- Auto-opens terminal panel for streaming output

### System Tray (SHELL-03)
- Minimize to tray on window close (configurable: close vs minimize)
- Tray icon with context menu (Show, Quit)
- Background notification when implement completes
- Use `tauri-plugin-notification` for native OS notifications

### Claude's Discretion
- Implement button placement (issue detail page, issue list, command palette)
- Progress step indicator design
- Tray icon design (reuse app icon)
- Notification content and grouping

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `commands/sidecar.rs` — run_sidecar + cancel_sidecar (Phase 35)
- `commands/git.rs` — branch create, stage, commit, push (Phases 32-33, 36)
- `commands/terminal.rs` — PTY sessions (Phase 34)
- `frontend/src/lib/tauri.ts` — runSidecar, gitBranchCreate, gitStage, gitCommit, gitPush wrappers
- `GitStore.ts` — branch/stage/commit/push actions (Phase 33, 36)
- `TerminalStore.ts` — terminal panel visibility (Phase 34)
- Issue detail page — existing in web app

### Established Patterns
- MobX stores for orchestration state
- Channel-based streaming for process output
- shadcn/ui for consistent UI

### Integration Points
- Issue detail page — add "Implement" button (Tauri-only)
- Terminal panel — auto-open for implement output
- System tray — new Tauri plugin integration

</code_context>

<specifics>
## Specific Ideas

- The one-click flow is the primary differentiator of the desktop app
- Research identified this as "what justifies the desktop app over the web UI"
- `pilot implement` uses `--oneshot` flag for non-interactive mode in automated flows

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>

---

*Phase: 37-one-click-implement-tray*
*Context gathered: 2026-03-20 via autonomous mode*
