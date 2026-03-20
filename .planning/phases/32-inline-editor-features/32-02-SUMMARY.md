---
phase: 32-inline-editor-features
plan: 02
subsystem: ui
tags: [tiptap, mobx, react, typescript, context-bridge, prosemirror, tiptap-markdown]

requires:
  - phase: 32-inline-editor-features/32-01
    provides: "ArtifactStore MobX store with useArtifactStore() hook + upload progress tracking"
  - phase: 30-tiptap-extension-foundation
    provides: "ReactNodeViewRenderer + node-view-bridge.ts pattern + createEditorExtensions Group 3 slot"

provides:
  - "FileCardExtension: TipTap atom block node named 'fileCard' with 5 attrs (artifactId, filename, mimeType, sizeBytes, status)"
  - "FileCardContext: React context bridge with FileCardContextValue interface and useFileCardContext() hook"
  - "FileCardNodeView: plain (non-observer) NodeView wrapper using context bridge pattern"
  - "FileCardView: observer child rendering uploading (progress bar), ready (icon+metadata), and error (retry) states"
  - "Markdown serializer: [filename](artifact://uuid) for ready nodes, empty string for uploading nodes"

affects:
  - 32-03-figure-extension
  - 32-04-slash-commands-media
  - 34-file-preview-modal

tech-stack:
  added: []
  patterns:
    - "FileCardExtension.addExtensions() includes StarterKit + Markdown for isolated test support — TipTap deduplicates by name when already registered in parent editor"
    - "Markdown serializer uses state.write() + state.closeBlock() — returning a string from serialize() does nothing in ProseMirror-style serializer"
    - "NodeView context bridge: FileCardNodeView (plain) wraps FileCardView (observer) in FileCardContext.Provider — prevents React 19 flushSync crash"

key-files:
  created:
    - frontend/src/features/notes/editor/extensions/file-card/FileCardExtension.ts
    - frontend/src/features/notes/editor/extensions/file-card/FileCardContext.ts
    - frontend/src/features/notes/editor/extensions/file-card/FileCardNodeView.tsx
    - frontend/src/features/notes/editor/extensions/file-card/FileCardView.tsx
  modified:
    - frontend/src/features/notes/editor/extensions/__tests__/FileCardExtension.test.ts
    - frontend/src/features/notes/editor/extensions/figure/FigureNodeView.tsx

key-decisions:
  - "FileCardExtension.addExtensions() includes StarterKit + Markdown — required for markdown test isolation; TipTap deduplicates extensions by name so no double-registration in full editor"
  - "Markdown serialize() uses state.write()/state.closeBlock() not return value — ProseMirror serializer is stateful mutation, not pure function return"
  - "FileCardNodeView is a plain React function (no observer) — follows node-view-bridge.ts pattern to avoid React 19 flushSync crash from nested useSyncExternalStore"
  - "Fixed pre-existing FigureNodeView type error (NodeViewContent as='figcaption' not in allowed types) via Rule 3 — blocking pre-commit typescript hook"

patterns-established:
  - "TipTap atom nodes needing markdown serialization: addStorage().markdown.serialize(state, node) must call state.write() + state.closeBlock() — not return a string"
  - "Self-contained TipTap extension tests: use addExtensions() to include StarterKit + Markdown — eliminates need to import them in every test makeEditor() call"

requirements-completed: [ARTF-01]

duration: 15min
completed: 2026-03-19
---

# Phase 32 Plan 02: FileCardExtension Summary

**TipTap atom block node for uploaded files: context-bridge NodeView with MobX observer child, markdown serializer emitting `[filename](artifact://uuid)` for ready nodes**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-19T20:44:00Z
- **Completed:** 2026-03-19T20:59:00Z
- **Tasks:** 2 (Task 1 + Task 2 committed together)
- **Files modified:** 6

## Accomplishments

- FileCardExtension TipTap atom block node with 5 attrs and correct parseHTML/renderHTML/addNodeView wiring
- FileCardContext React bridge exposing FileCardContextValue (attrs + readOnly + updateAttributes) to observer child
- FileCardNodeView plain wrapper (NO observer) → context bridge → FileCardView (observer) pattern correctly applied
- FileCardView renders uploading (progress bar from ArtifactStore), error (destructive card + retry button), ready (icon + filename + size) states
- Markdown serializer: `state.write('[filename](artifact://uuid)')` + `state.closeBlock(node)` for ready nodes; uploading nodes silently dropped
- All 4 TDD tests GREEN: registers as fileCard, creates with correct attrs, serializes to [filename](artifact://uuid), omits uploading nodes

## Task Commits

Each task was committed atomically:

1. **Task 1+2: FileCardExtension + Context + NodeView + FileCardView** - `18c9dac1` (feat)

## Files Created/Modified

- `frontend/src/features/notes/editor/extensions/file-card/FileCardExtension.ts` — TipTap Node definition with addStorage().markdown serializer; addExtensions() for self-contained test support
- `frontend/src/features/notes/editor/extensions/file-card/FileCardContext.ts` — FileCardContextValue interface, FileCardContext, useFileCardContext() hook
- `frontend/src/features/notes/editor/extensions/file-card/FileCardNodeView.tsx` — Plain (non-observer) NodeView wrapper, creates context value from node.attrs
- `frontend/src/features/notes/editor/extensions/file-card/FileCardView.tsx` — Observer child: uploading progress bar, ready metadata card, error retry button
- `frontend/src/features/notes/editor/extensions/__tests__/FileCardExtension.test.ts` — Removed stale @ts-expect-error (module now exists)
- `frontend/src/features/notes/editor/extensions/figure/FigureNodeView.tsx` — Fixed pre-existing type error: NodeViewContent as="div" (figcaption not in allowed prop types)

## Decisions Made

- **addExtensions() with StarterKit + Markdown**: The test scaffold used `(editor.storage as any).markdown?.getMarkdown?.()` which requires the Markdown extension to be active. Including StarterKit + Markdown in `addExtensions()` makes the FileCardExtension self-contained for testing. TipTap deduplicates extensions by name when the same extension is already registered in the parent editor — no double-registration risk.
- **state.write() + state.closeBlock() in serialize()**: Initial implementation returned a string from the serialize function, but tiptap-markdown's MarkdownSerializerState is a ProseMirror-style stateful serializer — `serialize()` must mutate `state` via `state.write()` and `state.closeBlock()`, not return values. The return value is ignored.
- **Plain NodeView wrapper**: Confirmed same constraint as IssueEditorContent — FileCardNodeView must NOT be wrapped in observer(). The context bridge pattern (plain wrapper → FileCardContext.Provider → observer child) is the correct approach.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed FigureNodeView pre-existing type error blocking pre-commit hook**
- **Found during:** Task 1+2 commit attempt
- **Issue:** Pre-commit TypeScript hook failed on `FigureNodeView.tsx` (from a previous incomplete session): `Type '"figcaption"' is not assignable to type '"div"'` — NodeViewContent only accepts "div" as the `as` prop type
- **Fix:** Changed `as="figcaption"` to `as="div"` in FigureNodeView.tsx; semantics preserved via CSS class
- **Files modified:** `frontend/src/features/notes/editor/extensions/figure/FigureNodeView.tsx`
- **Verification:** `pnpm type-check` returns no errors; pre-commit hook passes
- **Committed in:** `18c9dac1` (included in same commit)

**2. [Rule 1 - Bug] Fixed markdown serialize() returning string instead of using state.write()**
- **Found during:** Task 1 TDD verification (3/4 tests passing, serialization test failing)
- **Issue:** Initial serialize implementation `return '[filename](artifact://uuid)'` — tiptap-markdown ignores the return value; serializer requires `state.write()` mutation
- **Fix:** Changed to `state.write('[filename](artifact://uuid)')` + `state.closeBlock(node)` for ready nodes; empty case calls only `state.closeBlock(node)`
- **Files modified:** `frontend/src/features/notes/editor/extensions/file-card/FileCardExtension.ts`
- **Verification:** All 4 FileCardExtension tests pass; markdown serialization test GREEN
- **Committed in:** `18c9dac1` (same commit)

**3. [Rule 3 - Blocking] Added StarterKit to addExtensions() for schema completeness**
- **Found during:** Task 1 first test run
- **Issue:** `Editor({ extensions: [FileCardExtension] })` threw "Schema is missing its top node type ('doc')" — Markdown extension alone doesn't provide doc/text nodes
- **Fix:** Added `StarterKit` alongside `Markdown` in `addExtensions()`
- **Files modified:** `frontend/src/features/notes/editor/extensions/file-card/FileCardExtension.ts`
- **Verification:** All 4 tests pass; no schema errors
- **Committed in:** `18c9dac1` (same commit)

---

**Total deviations:** 3 auto-fixed (1 Rule 1 bug, 2 Rule 3 blocking)
**Impact on plan:** All fixes necessary for correctness and to unblock the commit. No scope creep.

## Issues Encountered

- tiptap-markdown's serialize() is ProseMirror-style (stateful mutation), not a pure function — must call `state.write()` and `state.closeBlock()`, not return values. This was the primary non-obvious constraint to discover.
- Pre-existing FigureNodeView.tsx from a previous session was blocking the TypeScript pre-commit hook — needed Rule 3 fix to unblock.

## Next Phase Readiness

- Plan 03 (FigureExtension) can proceed — FigureExtension.ts already exists in the repo (from a previous session), and FigureNodeView.tsx type errors are now fixed
- Plan 04 (slash commands media group) can reference FileCardExtension for /file command
- Phase 34 (FilePreviewModal) can wire the ready card's onClick using the `artifactId` from node attrs

---
*Phase: 32-inline-editor-features*
*Completed: 2026-03-19*

## Self-Check: PASSED

All created files verified present. All commits verified in git log.
- FileCardExtension.ts: FOUND
- FileCardContext.ts: FOUND
- FileCardNodeView.tsx: FOUND
- FileCardView.tsx: FOUND
- 32-02-SUMMARY.md: FOUND
- Commits 18c9dac1, 787f8bef: ALL FOUND
