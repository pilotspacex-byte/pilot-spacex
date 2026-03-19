---
phase: 32-inline-editor-features
plan: 04
subsystem: ui
tags: [tiptap, editor, file-upload, slash-commands, prosemirror, artifacts, mobx]

# Dependency graph
requires:
  - phase: 32-inline-editor-features/32-01
    provides: ArtifactStore + artifactsApi.upload/getSignedUrl
  - phase: 32-inline-editor-features/32-02
    provides: FileCardExtension (fileCard node type)
  - phase: 32-inline-editor-features/32-03
    provides: FigureExtension (figure node type)

provides:
  - FileCardExtension + FigureExtension registered in Group 3 of createEditorExtensions
  - /image and /file slash commands in 'media' group
  - Drop handler routing image/* to FigureNode, other files to FileCardNode
  - uploadFileAndUpdateNode() upload helper wired to artifactsApi + ArtifactStore
  - Stale fileCard node cleanup on editor mount (removes artifactId: null nodes)
  - pilot:upload-artifact CustomEvent listener bridging slash commands to upload logic

affects:
  - 33-video-embed (next wave — uses same createEditorExtensions Group 3 pattern)
  - 34-file-preview-modal (FigureNode and FileCardNode are entry points to preview modal)
  - NoteCanvasEditor (uses createEditorExtensions and EditorOptions)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "editorRef closure variable: captured in onCreate callback so the drop handler's EditorView can pass a typed Editor to upload helpers without casting EditorView.editor"
    - "pilot:upload-artifact CustomEvent: decouples slash command execute callbacks from direct API knowledge — slash-command-items.ts fires event, config.ts listens and handles upload"
    - "openFilePicker() helper: creates hidden <input type=file>, triggers click, handles change + focus cancel — cross-browser file picker without drag-drop zone"
    - "Stale node cleanup in onCreate: scans for fileCard nodes with artifactId: null, deletes them from end to start to preserve position validity"

key-files:
  created: []
  modified:
    - frontend/src/features/notes/editor/extensions/slash-command-items.ts
    - frontend/src/features/notes/editor/extensions/createEditorExtensions.ts
    - frontend/src/features/notes/editor/config.ts
    - frontend/src/features/notes/editor/types.ts

key-decisions:
  - "editorRef closure (not view.editor cast): EditorView.editor exists at TipTap runtime but is not in @tiptap/pm types — closure variable set in onCreate avoids unsafe cast"
  - "pilot:upload-artifact CustomEvent: slash-command-items.ts fires event on editor.view.dom, config.ts listens in onCreate — keeps slash commands free of API knowledge"
  - "getSignedUrl called after upload for figure nodes: image src must be a signed URL, not the artifact ID; falls back to artifact ID if getSignedUrl fails"
  - "SlashCommand.group union updated in both slash-command-items.ts AND types.ts: types.ts has a parallel SlashCommand interface that also needed 'media' added"

patterns-established:
  - "Group 3 extension registration: new media node types pushed after PMBlockExtension, before BlockIdExtension.configure() — ensures BlockIdExtension assigns IDs to all nodes"
  - "uploadFileAndUpdateNode(): shared helper for both drop and slash command upload paths — finds uploading node by filename/alt match, updates attrs on complete/error"

requirements-completed: [ARTF-02, ARTF-03, EDIT-04]

# Metrics
duration: 30min
completed: 2026-03-19
---

# Phase 32 Plan 04: Editor Extension Wiring Summary

**FileCardExtension + FigureExtension wired into editor: Group 3 registration, /image and /file slash commands, file drop routing to nodes, and stale node cleanup on mount**

## Performance

- **Duration:** 30 min
- **Started:** 2026-03-19T21:10:00Z
- **Completed:** 2026-03-19T21:19:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- /image and /file slash commands added to 'media' group — users can insert media via slash menu
- FileCardExtension and FigureExtension registered in Group 3 (lines 394-395, before BlockIdExtension at 402)
- Drop handler routes image/* to FigureNode and other files to FileCardNode with placeholder-then-upload pattern
- Upload helper (uploadFileAndUpdateNode) calls artifactsApi.upload, updates node attrs on completion, shows sonner toast on error
- Stale fileCard nodes (artifactId: null) removed on editor mount — prevents leftover placeholders from crashed uploads

## Task Commits

Each task was committed atomically:

1. **Task 1: Slash commands — add 'media' group with /image and /file entries** - `f6546f97` (feat)
2. **Task 2: Extension registration + drop handler + stale node cleanup** - `629066f7` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `frontend/src/features/notes/editor/extensions/slash-command-items.ts` — Added 'media' to group union, openFilePicker() helper, /image and /file commands
- `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` — Imports and pushes FileCardExtension + FigureExtension in Group 3
- `frontend/src/features/notes/editor/config.ts` — uploadFileAndUpdateNode() helper, updated drop handler, onCreate stale cleanup + event listener
- `frontend/src/features/notes/editor/types.ts` — EditorOptions gains workspaceId/projectId; SlashCommand.group gains 'media'

## Decisions Made

- **editorRef closure pattern**: `EditorView.editor` exists at TipTap runtime but is not in `@tiptap/pm` type definitions. A `let editorRef: Editor | null = null` closure variable captured in `onCreate` avoids a type-unsafe cast while giving the drop handler a typed `Editor` reference.
- **pilot:upload-artifact CustomEvent**: Slash command execute callbacks fire a DOM CustomEvent on `editor.view.dom`; `config.ts` listens in `onCreate`. This keeps `slash-command-items.ts` free of API dependencies and follows the single-responsibility pattern established for other extensions.
- **SlashCommand.group updated in types.ts too**: `slash-command-items.ts` has its own `SlashCommand` interface, but `types.ts` has a parallel one. Both needed 'media' added to avoid TypeScript assignability errors when the two interfaces are used interchangeably.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Updated SlashCommand.group in types.ts**
- **Found during:** Task 2 (type-check run)
- **Issue:** `types.ts` exports a `SlashCommand` interface with `group: 'formatting' | 'blocks' | 'ai'` — identical to the one in `slash-command-items.ts` but maintained separately. Not updating it would cause type errors when callers use `types.ts` imports.
- **Fix:** Added 'media' to the group union in `types.ts` line 174
- **Files modified:** `frontend/src/features/notes/editor/types.ts`
- **Verification:** `pnpm type-check` passes with no errors
- **Committed in:** `629066f7` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical type update)
**Impact on plan:** Required for type correctness; no scope creep.

## Issues Encountered

- `view.editor` cast (`view.editor as Editor`) failed type-check because `@tiptap/pm/view`'s `EditorView` doesn't declare `.editor`. Resolved with `editorRef` closure variable set in `onCreate`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FileCard and Figure nodes are now reachable from editor UI via slash menu and file drop
- Upload flow is end-to-end: node insertion → artifactsApi.upload → node attr update (ready/error)
- Phase 33 (video embed) can follow the same Group 3 extension registration pattern
- Phase 34 (file preview modal) can pick up FileCardView and FigureNodeView as entry points

---
*Phase: 32-inline-editor-features*
*Completed: 2026-03-19*
