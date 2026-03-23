# Phase 36: Diff Viewer + Commit UI - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning
**Source:** Autonomous mode — derived from ROADMAP + research

<domain>
## Phase Boundary

File diff viewer with syntax highlighting, stage/unstage individual files, commit message input with commit action, push after commit. A lightweight git client UI layer on top of the git2-rs commands from Phase 33.

</domain>

<decisions>
## Implementation Decisions

### Diff Viewer
- Use `react-diff-view` or `@git-diff-view/react` for rendering diffs
- Rust `git_diff` command returns unified diff output per file
- Syntax highlighting via diff component's built-in support
- Virtualized rendering for large diffs (prevent UI freeze)

### Stage/Unstage
- Rust `git_stage` and `git_unstage` commands using git2-rs index operations
- UI: checkbox per file in the status list
- Bulk stage all / unstage all actions

### Commit + Push
- Commit message textarea with character count
- Commit button creates commit from staged files
- Push button appears after successful commit
- Combined "Commit & Push" shortcut action

### Claude's Discretion
- Diff viewer component library choice
- Split vs unified diff view default
- Commit message template or conventional commit suggestions

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `commands/git.rs` — git_status, git_push already exist (Phase 33)
- `GitStore.ts` — MobX store with status observables (Phase 33)
- `git-status-panel.tsx` — existing file status display (Phase 33)
- `frontend/src/lib/tauri.ts` — IPC wrapper pattern

### Established Patterns
- git2-rs commands in `commands/git.rs`
- GitStore MobX actions
- shadcn/ui Dialog, Button, Input components

### Integration Points
- Add `git_diff`, `git_stage`, `git_unstage`, `git_commit` Rust commands
- Extend GitStore with diff/stage/commit actions
- DiffViewer and CommitPanel components in `features/git/`

</code_context>

<specifics>
## Specific Ideas

- Diff should be accessible from clicking any changed file in GitStatusPanel
- CommitPanel could be a slide-out panel or dialog
- Large diffs need virtualization to prevent render blocking

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>

---

*Phase: 36-diff-viewer-commit-ui*
*Context gathered: 2026-03-20 via autonomous mode*
