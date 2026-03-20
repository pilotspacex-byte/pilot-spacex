---
phase: 30-tiptap-extension-foundation
plan: "02"
subsystem: ui
tags: [tiptap, prosemirror, tiptap-markdown, blockquote, pull-quote, editor-extension, markdown-serialization, slash-command]

# Dependency graph
requires:
  - phase: 30-01
    provides: RED tests for PullQuoteExtension (5 tests), established test patterns for TDD GREEN phase
provides:
  - PullQuoteExtension.ts with Blockquote.extend(), pullQuote attr, tiptap-markdown 0.9 serialize, parse.updateDOM round-trip
  - /pullquote slash command in blocks group
  - [data-pull-quote] CSS override in globals.css
  - PullQuoteExtension barrel export from extensions/index.ts
  - StarterKit blockquote disabled, PullQuoteExtension takes its place (blockquote: false)
affects:
  - Phase 31+ (any phase that adds block extensions — same Group 1 pattern now established)
  - Phase 33 (SelectionToolbar pull quote toggle button uses togglePullQuote command from this extension)

# Tech tracking
tech-stack:
  added:
    - "@tiptap/extension-blockquote 3.20.4 (explicit dep — was transitive via starter-kit)"
  patterns:
    - "Blockquote.extend() for style-variant nodes — keeps name 'blockquote', adds boolean attr"
    - "tiptap-markdown 0.9 addStorage().markdown.serialize(state, node) — ProseMirror-style serialize API"
    - "tiptap-markdown 0.9 addStorage().markdown.parse.updateDOM(element) — DOM post-processing for round-trip"
    - "StarterKit blockquote: false + custom extension replacing it in Group 1"

key-files:
  created:
    - frontend/src/features/notes/editor/extensions/PullQuoteExtension.ts
  modified:
    - frontend/src/features/notes/editor/extensions/createEditorExtensions.ts
    - frontend/src/features/notes/editor/extensions/slash-command-items.ts
    - frontend/src/features/notes/editor/extensions/index.ts
    - frontend/src/app/globals.css
    - frontend/package.json (added @tiptap/extension-blockquote)
    - frontend/pnpm-lock.yaml

key-decisions:
  - "Used parse.updateDOM hook (not parse.setup markdown-it plugin) for round-trip — simpler, handles rendered HTML directly"
  - "Added @tiptap/extension-blockquote as explicit dep — it was transitive via starter-kit but not accessible from the package root"
  - "PullQuoteExtension pushed in Group 1 (not Group 3) — it's a style variant of blockquote, not a new block type; BlockIdExtension already covers 'blockquote'"

patterns-established:
  - "Pattern: extend StarterKit node with boolean attr toggle — name stays same, blockquote: false in StarterKit.configure()"
  - "Pattern: tiptap-markdown 0.9 parse.updateDOM for markdown round-trip — mutate DOM before TipTap parseHTML runs"
  - "Pattern: install explicit dep when using a package that exists only as transitive dependency"

requirements-completed:
  - EDIT-01

# Metrics
duration: 18min
completed: "2026-03-19"
---

# Phase 30 Plan 02: PullQuoteExtension Summary

**Blockquote.extend() with pullQuote boolean attr, tiptap-markdown 0.9 serialize/round-trip, /pullquote slash command, and [data-pull-quote] CSS — EDIT-01 fully shipped, 5/5 tests GREEN**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-03-19T19:18:00Z
- **Completed:** 2026-03-19T19:36:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- PullQuoteExtension.ts created with `Blockquote.extend()` — keeps `name: 'blockquote'`, adds `pullQuote` boolean attribute, tiptap-markdown 0.9 `serialize`, `parse.updateDOM` for round-trip, and `togglePullQuote` command
- StarterKit blockquote disabled (`blockquote: false`) and replaced by PullQuoteExtension in Group 1 of `createEditorExtensions.ts`
- `/pullquote` slash command added to `blocks` group in `slash-command-items.ts`
- `[data-pull-quote]` CSS override added to `globals.css` — 1.2em font, 4px solid `--accent` border, `--foreground` color
- All 5 EDIT-01 tests pass GREEN, markdown-integration tests still 5/5 GREEN (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PullQuoteExtension.ts** - `6ec5e725` (feat)
2. **Task 2: Wire PullQuoteExtension + slash command + CSS + index export** - `0e9f6685` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `frontend/src/features/notes/editor/extensions/PullQuoteExtension.ts` - NEW: Blockquote.extend() with pullQuote attr, tiptap-markdown 0.9 serialize + parse.updateDOM, togglePullQuote command
- `frontend/src/features/notes/editor/extensions/createEditorExtensions.ts` - MODIFIED: added `blockquote: false` to StarterKit.configure(), push PullQuoteExtension after StarterKit (Group 1)
- `frontend/src/features/notes/editor/extensions/slash-command-items.ts` - MODIFIED: /pullquote command in blocks group (after existing quote command)
- `frontend/src/features/notes/editor/extensions/index.ts` - MODIFIED: added `export { PullQuoteExtension }` in Core extensions section
- `frontend/src/app/globals.css` - MODIFIED: added `.document-canvas .prose blockquote[data-pull-quote]` CSS override
- `frontend/package.json` - MODIFIED: added `@tiptap/extension-blockquote` as explicit dependency
- `frontend/pnpm-lock.yaml` - MODIFIED: lock file updated for new dep

## Decisions Made

- **`parse.updateDOM` over `parse.setup`** — Used tiptap-markdown 0.9's `parse.updateDOM(element)` hook (called after markdown-it renders HTML, before TipTap parseHTML) to detect `[!quote]` marker paragraphs and stamp `data-pull-quote` on the blockquote element. This gave full round-trip without needing to write a markdown-it plugin.
- **Explicit `@tiptap/extension-blockquote` dep** — The package was accessible as a transitive dep but not resolvable from the package root in pnpm. Made it explicit to ensure reliable imports. Version 3.20.4 installed (latest compatible with tiptap 3.16).
- **Group 1 placement (not Group 3)** — PullQuoteExtension is a style variant of blockquote (same schema name), not a new node type. BlockIdExtension already covers `'blockquote'` in its hardcoded types list, so Group 3 placement was not needed. Placed immediately after StarterKit push in Group 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing @tiptap/extension-blockquote explicit dependency**
- **Found during:** Task 1 (test run after creating PullQuoteExtension.ts)
- **Issue:** `Failed to resolve import "@tiptap/extension-blockquote"` — package was a transitive dep only, not in package.json; pnpm couldn't resolve it from the project root
- **Fix:** `pnpm add @tiptap/extension-blockquote` — installed version 3.20.4 as explicit dep
- **Files modified:** `frontend/package.json`, `frontend/pnpm-lock.yaml`
- **Verification:** Tests ran without import error after install
- **Committed in:** 6ec5e725 (Task 1 commit)

**2. [Rule 1 - Bug] Added parse.updateDOM for markdown round-trip**
- **Found during:** Task 1 (test run — `test_pull_quote_round_trip_markdown_survives_re_parse` failed)
- **Issue:** The plan noted round-trip as "best-effort" but the test asserted `pullQuote: true` must survive. Standard `parseHTML` (which reads `data-pull-quote` from DOM) doesn't fire when tiptap-markdown parses the serialized `> [!quote]\n> text` markdown — markdown-it renders a plain `<blockquote>` without the attribute.
- **Fix:** Added `addStorage().markdown.parse.updateDOM(element)` hook that detects `[!quote]` as first paragraph text in blockquotes, adds `data-pull-quote` attribute, and removes the marker paragraph — making `parseHTML` fire correctly
- **Files modified:** `frontend/src/features/notes/editor/extensions/PullQuoteExtension.ts`
- **Verification:** 5/5 tests GREEN including round-trip test
- **Committed in:** 6ec5e725 (Task 1 commit, before commit was finalized)

---

**Total deviations:** 2 auto-fixed (1 blocking dep issue, 1 bug in round-trip parsing)
**Impact on plan:** Both auto-fixes were necessary for tests to pass and correctness. No scope creep.

## Issues Encountered

None beyond what is documented in Deviations from Plan.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- EDIT-01 fully implemented and tested — pull quote can be toggled on any blockquote via `editor.commands.togglePullQuote()`
- Pattern established: extend StarterKit node with boolean attr + tiptap-markdown 0.9 serialize API
- `parse.updateDOM` round-trip pattern documented in PullQuoteExtension.ts for future reference
- Plan 30-03 (SelectionToolbar heading dropdown + pull quote toggle) can use `togglePullQuote` command directly

---
*Phase: 30-tiptap-extension-foundation*
*Completed: 2026-03-19*
