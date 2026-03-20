---
phase: 33-video-embeds
plan: 02
subsystem: ui
tags: [tiptap, video-embed, youtube, vimeo, slash-command, paste-rule, extension]

# Dependency graph
requires:
  - phase: 33-video-embeds/33-01
    provides: YoutubeExtension and VimeoNode extension modules with isVideoUrl/extractVimeoId helpers
provides:
  - YoutubeExtension and VimeoNode registered in Group 3 of createEditorExtensions.ts (before BlockIdExtension)
  - VideoPasteDetector registered in Group 5 of createEditorExtensions.ts
  - /video slash command with inline URL input prompt (VideoUrlPrompt)
  - Paste-triggered embed offer for standalone YouTube/Vimeo URLs
affects:
  - 34-file-preview
  - 35-artifacts-page
  - any phase using createEditorExtensions

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Inline DOM input for slash command URL entry (no modal, no React portal)
    - PasteRule with anchored regex + requestAnimationFrame for post-paste offer UI
    - Group 3 block-type registration before BlockIdExtension (PRE-002)
    - Group 5 decoration/interaction layer registration after BlockIdExtension

key-files:
  created:
    - frontend/src/features/notes/editor/extensions/VideoUrlPrompt.ts
    - frontend/src/features/notes/editor/extensions/VideoPasteDetector.ts
  modified:
    - frontend/src/features/notes/editor/extensions/createEditorExtensions.ts
    - frontend/src/features/notes/editor/extensions/slash-command-items.ts

key-decisions:
  - "VideoPasteDetector registered in Group 5 after SlashCommandExtension — decoration/interaction layer, not a block-type node"
  - "showVideoUrlPrompt appends to document.body not editor DOM — avoids ProseMirror focus conflicts"
  - "PasteRule only fires on standalone URLs (anchored ^...$ regex); empty paragraph guard prevents offer on non-empty lines"
  - "outsideClick listener registered via setTimeout(100ms) — prevents immediate dismiss from the paste mouseup event"

patterns-established:
  - "Pattern: slash command URL entry uses transient DOM input injected into document.body at coordsAtPos position"
  - "Pattern: paste offer uses requestAnimationFrame to show embed UI after paste transaction settles"

requirements-completed:
  - VID-01
  - VID-02
  - VID-03

# Metrics
duration: 12min
completed: 2026-03-19
---

# Phase 33 Plan 02: Video Embeds — Editor Wiring Summary

**YoutubeExtension + VimeoNode wired into Group 3 of createEditorExtensions with /video slash command (inline URL prompt) and VideoPasteDetector (PasteRule embed offer) in Group 5**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-19T14:34:55Z
- **Completed:** 2026-03-19T14:45:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `VideoUrlPrompt.ts` — exports `showVideoUrlPrompt()`, injects transient fixed-position DOM input below cursor for /video URL entry without a modal or React portal
- Created `VideoPasteDetector.ts` — exports `VideoPasteDetector` Extension with anchored `VIDEO_URL_REGEX` PasteRule; shows "Embed video?" offer (Embed/Dismiss buttons) when a standalone YouTube/Vimeo URL is pasted into an empty paragraph
- Registered `YoutubeExtension` and `VimeoNode` in Group 3 of `createEditorExtensions.ts` (lines 401, 404 — before `BlockIdExtension` at line 411, confirming non-null blockId on video nodes)
- Registered `VideoPasteDetector` in Group 5 (line 496 — after BlockIdExtension)
- Added `/video` slash command to `getDefaultCommands()` in the `media` group; calls `showVideoUrlPrompt`; invalid URL shows `toast.error('Please enter a valid YouTube or Vimeo URL')`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create VideoUrlPrompt.ts and VideoPasteDetector.ts** - `4d68529a` (feat)
2. **Task 2: Register extensions in editor + add /video slash command** - `10c079c8` (feat)

## Files Created/Modified

- `frontend/src/features/notes/editor/extensions/VideoUrlPrompt.ts` — `showVideoUrlPrompt(editor, onConfirm)`: fixed-position DOM input appended to document.body, Enter confirms URL, Escape refocuses editor, blur cleans up
- `frontend/src/features/notes/editor/extensions/VideoPasteDetector.ts` — `VideoPasteDetector` Extension: PasteRule with `VIDEO_URL_REGEX`, checks pasted node is empty paragraph, shows inline Embed/Dismiss offer via `showEmbedOffer()`, accepts insert YouTube via `setYoutubeVideo()` or Vimeo via `insertContent({type:'vimeo'})`
- `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` — Added imports for `YoutubeExtension`, `VimeoNode`, `VideoPasteDetector`; pushed YouTube+Vimeo in Group 3 after FigureExtension; pushed VideoPasteDetector in Group 5 after SlashCommandExtension
- `frontend/src/features/notes/editor/extensions/slash-command-items.ts` — Added imports for `toast`, `isVideoUrl`, `extractVimeoId`, `showVideoUrlPrompt`; added `/video` command entry in `media` group with inline URL prompt and error toast

## Group 3 Ordering Verification

Grep output confirming Group 3 ordering:

```
401:  extensions.push(YoutubeExtension);
404:  extensions.push(VimeoNode);
411:    BlockIdExtension.configure({
496:  extensions.push(VideoPasteDetector);
```

YoutubeExtension (401) and VimeoNode (404) both appear BEFORE BlockIdExtension (411), ensuring non-null blockIds on video embed nodes. VideoPasteDetector (496) appears AFTER BlockIdExtension in Group 5.

## Decisions Made

- `VideoPasteDetector` placed in Group 5 (not Group 3): it's a decoration/interaction layer — it does not define a new node type, so it doesn't need to precede BlockIdExtension
- `showVideoUrlPrompt` appends the DOM input to `document.body` (not the editor DOM) to prevent ProseMirror's focus management from interfering with input focus
- The `outsideClick` listener for the embed offer is registered with `setTimeout(100ms)` to prevent the paste event's mouseup from immediately dismissing it
- Pre-existing test failures (localStorage, ghost-text-store, workspace-nav) confirmed unrelated to this plan's changes via git stash verification

## Deviations from Plan

None — plan executed exactly as written.

The plan noted `group: 'media'` needed adding to the SlashCommand union type, but it was already present from Phase 32. The `/video` command was added to the existing media group without type changes.

## Issues Encountered

- Prettier reformatted `VideoUrlPrompt.ts` on first commit attempt (function signature split across lines). Re-staged and committed successfully on second attempt.
- Pre-existing test failures (55 files, 307 tests) confirmed pre-existing via git stash; none related to video embed code.

## Next Phase Readiness

- Video embed feature is fully wired and functional: `/video` slash command works, paste detection works
- `YoutubeExtension` and `VimeoNode` are in Group 3 — ready for Phase 34's `FilePreviewModal` to use the same editor instance
- `pnpm type-check` returns 0 errors

---
*Phase: 33-video-embeds*
*Completed: 2026-03-19*
