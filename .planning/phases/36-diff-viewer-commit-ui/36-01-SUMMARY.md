---
phase: 36-diff-viewer-commit-ui
plan: "01"
subsystem: tauri-git-ipc
tags: [rust, git2, tauri-commands, mobx, typescript, ipc]
dependency_graph:
  requires: []
  provides: [git_diff-command, git_stage-command, git_unstage-command, git_commit-command, FileDiff-interface, GitStore-diff-stage-commit-actions]
  affects: [tauri-app/src-tauri/src/commands/git.rs, tauri-app/src-tauri/src/lib.rs, frontend/src/lib/tauri.ts, frontend/src/stores/features/git/GitStore.ts]
tech_stack:
  added: [git2::DiffFormat, git2::DiffOptions, git2::ObjectType, git2::Signature]
  patterns: [spawn_blocking-for-git2, lazy-dynamic-import-for-tauri-api, runInAction-mobx, makeAutoObservable]
key_files:
  created: []
  modified:
    - tauri-app/src-tauri/src/commands/git.rs
    - tauri-app/src-tauri/src/lib.rs
    - frontend/src/lib/tauri.ts
    - frontend/src/stores/features/git/GitStore.ts
decisions:
  - "git_diff collects both staged (diff_tree_to_index) and unstaged (diff_index_to_workdir) diffs via per-file HashMap accumulation to avoid duplicate paths"
  - "git_unstage uses repo.reset_default with HEAD tree Object — resets index without touching working tree"
  - "git_commit detects unborn HEAD via repo.head().is_err() and passes empty parents slice for initial commit"
  - "GitStore.selectFile auto-triggers fetchDiff for non-null paths — single call point for file selection in DiffViewer UI"
  - "stageAll/unstageAll derived from this.status.files — avoids separate observable, stays in sync with refreshStatus"
metrics:
  duration: "4 minutes"
  completed: "2026-03-20"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
  lines_added: ~455
---

# Phase 36 Plan 01: Git Diff/Stage/Commit Rust IPC + TypeScript Store Layer Summary

**One-liner:** 4 new git2-rs IPC commands (diff/stage/unstage/commit) with matching TypeScript wrappers and MobX GitStore extensions providing the complete backend+store layer for DiffViewer and CommitPanel.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Add git_diff, git_stage, git_unstage, git_commit Rust commands | 4358fbf2 | git.rs +226 lines, lib.rs +4 commands registered |
| 2 | Add TypeScript IPC wrappers and extend GitStore | d0c3b6e8 | tauri.ts +62 lines, GitStore.ts +175 lines |

## What Was Built

### Rust Layer (git.rs)

**FileDiff struct** — serializable response with `path: String`, `diff: String` (unified patch text), `is_binary: bool`.

**git_diff command** — returns `Vec<FileDiff>` for a single file or all changed files. Collects both unstaged (`diff_index_to_workdir`) and staged (`diff_tree_to_index vs HEAD`) diffs. Uses a `HashMap<String, FileDiff>` to accumulate per-file patch text across both diff passes via `DiffFormat::Patch`. Binary files are identified via `delta.flags().is_binary()` and returned with empty diff string. Handles repos with no HEAD (initial state) by using `Option<Tree>`.

**git_stage command** — opens repo index, calls `index.add_path(Path::new(&path))` for each path, then `index.write()` to persist.

**git_unstage command** — peels HEAD to `ObjectType::Tree` generic Object, then calls `repo.reset_default(Some(&head_obj), paths)` to reset index entries without touching the working tree.

**git_commit command** — writes index tree, gets HEAD parent commit (empty slice for unborn HEAD), resolves git signature (falls back to `"Pilot Space <noreply@pilotspace.dev>"`), creates commit and returns OID hex string.

All 4 commands run in `spawn_blocking` (Repository is not Send).

### TypeScript Layer (tauri.ts + GitStore.ts)

**FileDiff interface** — matches Rust struct exactly.

**4 IPC wrappers** — follow the existing lazy-import + `isTauri()` guard pattern:
- `gitDiff(repoPath, filePath?)` — returns `[]` in browser mode
- `gitStage(repoPath, paths)` — throws if not in Tauri mode
- `gitUnstage(repoPath, paths)` — throws if not in Tauri mode
- `gitCommit(repoPath, message)` — throws if not in Tauri mode

**GitStore extensions:**
- New observables: `selectedFilePath`, `fileDiffs`, `isLoadingDiff`, `diffError`, `isCommitting`, `commitError`, `lastCommitOid`, `isStaging`, `stageError`
- New actions: `fetchDiff`, `stageFiles`, `unstageFiles`, `stageAll`, `unstageAll`, `commit`, `selectFile`, `clearCommitState`
- `setRepoPath()` and `reset()` updated to clear all new fields

## Verification

- `cargo check` — passes with 0 errors (finished in 2.01s)
- `tsc --noEmit` — passes with 0 errors
- All 9 acceptance criteria checks pass for Task 1
- All 10 acceptance criteria checks pass for Task 2
- Prettier hook passes on all modified frontend files

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `tauri-app/src-tauri/src/commands/git.rs` — exists, contains all 4 commands and FileDiff struct
- `tauri-app/src-tauri/src/lib.rs` — exists, contains all 4 command registrations
- `frontend/src/lib/tauri.ts` — exists, contains FileDiff interface and 4 wrapper functions
- `frontend/src/stores/features/git/GitStore.ts` — exists, contains all new observables and actions
- Commit 4358fbf2 — verified in git log
- Commit d0c3b6e8 — verified in git log
