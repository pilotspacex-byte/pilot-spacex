---
phase: 32-inline-editor-features
plan: 03
subsystem: ui
tags: [tiptap, prosemirror, react, typescript, editor, image, caption, markdown]

requires:
  - phase: 32-inline-editor-features/32-01
    provides: "Wave 0 RED test scaffold FigureExtension.test.ts"
  - phase: 32-inline-editor-features/32-02
    provides: "FileCardExtension pattern for atom nodes + addExtensions() standalone editor pattern"

provides:
  - "FigureExtension: TipTap 'figure' block node with content: 'inline*' for editable captions"
  - "FigureNodeView: plain (non-observer) NodeView wrapper rendering img + NodeViewContent for figcaption"
  - "FigureView.tsx: intentionally minimal — documents Phase 34 hook point for FilePreviewModal"
  - "Markdown serialization: ![captionText](src) — caption textContent used as alt attribute"

affects:
  - 32-04-slash-commands-media
  - 34-file-preview-modal

tech-stack:
  added: []
  patterns:
    - "FigureExtension uses content: 'inline*' (not atom) — figcaption is ProseMirror child content, not attrs"
    - "FigureNodeView renders img directly + delegates caption to NodeViewContent (TipTap content slot)"
    - "addExtensions() bundles StarterKit + Markdown for standalone editor use in tests"
    - "state.write('![alt](src)') in markdown serializer — not returning string (tiptap-markdown 0.9 API)"
    - "data-figure-artifact-id on <figure> element for Phase 34 FilePreviewModal integration"

key-files:
  created:
    - frontend/src/features/notes/editor/extensions/figure/FigureExtension.ts
    - frontend/src/features/notes/editor/extensions/figure/FigureNodeView.tsx
    - frontend/src/features/notes/editor/extensions/figure/FigureView.tsx
  modified:
    - frontend/src/features/notes/editor/extensions/__tests__/FigureExtension.test.ts

key-decisions:
  - "FigureNodeView uses NodeViewContent (not a separate FigureView) for caption slot — no MobX observer needed since attrs come directly from node.attrs"
  - "state.write() in serialize() instead of return string — tiptap-markdown 0.9 requires state mutation, not return value"
  - "addExtensions() with StarterKit + Markdown in FigureExtension — enables isolated test execution without full createEditorExtensions() setup"
  - "NodeViewContent as='div' instead of as='figcaption' — NodeViewContent TypeScript types only accept 'div' as default, figcaption causes TS2322"

patterns-established:
  - "Non-atom content nodes (content: 'inline*') need addExtensions() for standalone test support"
  - "FigureView.tsx minimal stub pattern: exists for file structure consistency, documents future integration points"

requirements-completed: [EDIT-04, EDIT-05]

duration: 15min
completed: 2026-03-19
---

# Phase 32 Plan 03: FigureExtension Summary

**TipTap 'figure' block node with content: 'inline*' editable caption via NodeViewContent + markdown round-trip as ![caption](src)**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-19T20:47:00Z
- **Completed:** 2026-03-19T21:00:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- FigureExtension: TipTap block node with `content: 'inline*'` so figcaption text is stored as ProseMirror child nodes (not attrs), making it natively editable
- FigureNodeView: plain (non-observer) wrapper that renders `<img>` directly + delegates caption slot to `NodeViewContent` — no separate FigureView needed
- Markdown serialization via `state.write()`: `![textContent](src)` — caption textContent used as alt, survives markdown round-trip
- All 4 TDD tests passing: registers schema, creates with attrs, serializes markdown, preserves caption text

## Task Commits

Each task was committed atomically:

1. **Task 1: FigureExtension node definition + NodeView wrapper** - `18c9dac1` (feat)
2. **Task 2: FigureView.tsx — minimal stub, structure parity** - `a3e5b883` (feat)

## Files Created/Modified

- `frontend/src/features/notes/editor/extensions/figure/FigureExtension.ts` — TipTap Node definition: figure, content: 'inline*', 4 attrs (src, alt, artifactId, status), markdown serializer
- `frontend/src/features/notes/editor/extensions/figure/FigureNodeView.tsx` — Plain (non-observer) NodeView: img rendering + NodeViewContent for caption slot; data-figure-artifact-id for Phase 34
- `frontend/src/features/notes/editor/extensions/figure/FigureView.tsx` — Intentionally minimal stub; documents Phase 34 hook point; no exports
- `frontend/src/features/notes/editor/extensions/__tests__/FigureExtension.test.ts` — Removed @ts-expect-error (module now exists, RED→GREEN)

## Decisions Made

- Used `state.write()` in `addStorage().markdown.serialize()` instead of returning a string — tiptap-markdown 0.9's MarkdownSerializer expects the serializer to call `state.write()`, not return a value (return value is ignored)
- `NodeViewContent as="div"` (not `as="figcaption"`) — TypeScript's `NodeViewContent<T>` defaults to `"div"` and the type constraint `NoInfer<T>` means `"figcaption"` produces TS2322; HTML semantics maintained via CSS class `note-figure-caption`
- `addExtensions()` bundles StarterKit + Markdown — required for `content: 'inline*'` nodes (non-atom) to work in isolation; TipTap deduplicates by name when used in parent editor
- FigureView.tsx is minimal with no exports — FigureNodeView handles all rendering directly; FileCardView comparison shows FigureView would only be needed if MobX observables were required

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Incorrect import source for ReactNodeViewRenderer**
- **Found during:** Task 1 verification (tests)
- **Issue:** FigureExtension imported `ReactNodeViewRenderer` from `@tiptap/core` — it doesn't exist there; must import from `@tiptap/react`
- **Fix:** Changed import to `import { ReactNodeViewRenderer } from '@tiptap/react'`
- **Files modified:** `FigureExtension.ts`
- **Verification:** Tests pass after fix
- **Committed in:** `18c9dac1` (Task 1)

**2. [Rule 1 - Bug] Missing StarterKit + Markdown in addExtensions()**
- **Found during:** Task 1 TDD (RED→GREEN)
- **Issue:** `FigureExtension` alone lacks `doc` node schema; `new Editor({ extensions: [FigureExtension] })` throws "Schema is missing its top node type ('doc')"
- **Fix:** Added `addExtensions()` returning `[StarterKit, Markdown.configure(...)]` — same pattern established by FileCardExtension in Plan 02
- **Files modified:** `FigureExtension.ts`
- **Verification:** All 4 tests pass
- **Committed in:** `18c9dac1` (Task 1)

**3. [Rule 1 - Bug] NodeViewContent as="figcaption" TypeScript error**
- **Found during:** Task 1 type-check
- **Issue:** `NodeViewContent<T>` type definition uses `NoInfer<T>` which causes TS2322 when passing `as="figcaption"` (only `"div"` is the inferred default)
- **Fix:** Changed to `as="div"` with explanatory comment; caption semantics maintained via `className="note-figure-caption"`
- **Files modified:** `FigureNodeView.tsx` (auto-fixed by linter during development)
- **Verification:** `pnpm type-check` passes cleanly
- **Committed in:** `18c9dac1` (Task 1)

---

**Total deviations:** 3 auto-fixed (Rule 1 — import error, schema setup, TypeScript type constraint)
**Impact on plan:** All auto-fixes required for correct TypeScript/TipTap behavior. No scope creep.

## Issues Encountered

- Task 1 TDD commit note: FigureExtension.ts was committed as part of Plan 02's `18c9dac1` commit (Plan 02 executor pre-created the figure files alongside FileCard). Task 1 work was still executed and verified — commit hash `18c9dac1` is the correct reference for Task 1 completion.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plans 32-04 (slash-command-media) can reference FigureExtension for the `/image` command
- Phase 34 (FilePreviewModal): `data-figure-artifact-id` attribute is ready on `<figure>` elements; FigureView.tsx documents the hook point for click-to-preview
- FigureExtension registration in `createEditorExtensions.ts` Group 3 (BEFORE BlockIdExtension) is NOT yet done — Plan 32-04 or a dedicated wiring plan should add it

---
*Phase: 32-inline-editor-features*
*Completed: 2026-03-19*

## Self-Check: PASSED

All created files verified present. All commits verified in git log.
- FigureExtension.ts: FOUND
- FigureNodeView.tsx: FOUND
- FigureView.tsx: FOUND
- 32-03-SUMMARY.md: FOUND
- Commits 18c9dac1 (Task 1), a3e5b883 (Task 2), 7de4cc47 (docs): ALL FOUND
