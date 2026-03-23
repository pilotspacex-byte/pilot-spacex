# Phase 34: Embedded Terminal - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Autonomous mode — derived from ROADMAP + research

<domain>
## Phase Boundary

Embedded terminal panel inside the Tauri app using xterm.js for rendering and tauri-plugin-pty (or tauri-plugin-shell fallback) for PTY backend. Users can open a terminal, run interactive programs with full ANSI support, and execute arbitrary shell commands with streaming output. Memory-safe via batched IPC Channel.

</domain>

<decisions>
## Implementation Decisions

### PTY Backend
- Use `tauri-plugin-pty` (v0.1.1) for full pseudo-terminal support
- Fallback to `tauri-plugin-shell` if PTY plugin is unstable
- Rust module: `commands/terminal.rs` with create/write/resize/close commands
- Managed state: `TerminalState` holding active PTY sessions (HashMap<session_id, PtyProcess>)

### Output Streaming
- Use `tauri::ipc::Channel` (NOT `emit_all`) to prevent memory leaks (research pitfall)
- Batch output at 16ms intervals on the Rust side before sending to frontend
- Explicit `close()` on session end to clean up Channel resources
- 10,000-line scrollback buffer in xterm.js

### Frontend Terminal
- `@xterm/xterm@5.5.0` + `@xterm/addon-fit@0.11.0` for responsive resize
- `TerminalPanel.tsx` — toggleable bottom panel (like VS Code terminal)
- `useTerminal` hook managing xterm instance lifecycle
- Terminal sessions: create, switch between, close tabs

### Claude's Discretion
- Terminal panel toggle animation and keyboard shortcut
- Multiple terminal tab management UI
- Default shell detection per platform (bash/zsh on macOS/Linux, cmd/powershell on Windows)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/tauri.ts` — IPC wrapper pattern
- `tauri-app/src-tauri/src/commands/` — command module pattern
- `tauri-app/src-tauri/src/lib.rs` — plugin and command registration

### Established Patterns
- Channel-based streaming (used in git clone/pull/push)
- MobX stores for UI state
- shadcn/ui components for consistent design

### Integration Points
- Register terminal commands in lib.rs
- Add TerminalPanel to main layout (below content area)
- Terminal will be used by Phase 35 (pilot CLI sidecar) and Phase 37 (one-click implement)

</code_context>

<specifics>
## Specific Ideas

- Research warns: Tauri event system has confirmed memory leak for high-frequency streams (#12724)
- Must use `ipc::Channel` with explicit close(), not `emit_all`
- 16ms batching prevents WebView freeze under high output volume

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 34-embedded-terminal*
*Context gathered: 2026-03-20 via autonomous mode*
