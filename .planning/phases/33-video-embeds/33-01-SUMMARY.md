---
phase: 33-video-embeds
plan: 01
subsystem: ui
tags: [tiptap, youtube, vimeo, video-embed, tiptap-markdown, iframe, sandbox]

# Dependency graph
requires:
  - phase: 32-inline-editor-features
    provides: FigureExtension pattern (state.write serialize, no ReactNodeViewRenderer)
  - phase: 30-tiptap-extension-foundation
    provides: Group 3 registration pattern, BlockIdExtension ordering constraint
provides:
  - YoutubeExtension (Youtube.extend wrapper with nocookie:true, sandbox attrs, markdown serialize)
  - VimeoNode (custom ~70-line Node.create with extractVimeoId, isVideoUrl, sandbox attrs, markdown serialize)
  - Test coverage for VID-01, VID-02, VID-03, VID-04 (YouTube sandbox)
affects:
  - 33-02 (registers both extensions in createEditorExtensions.ts Group 3)

# Tech tracking
tech-stack:
  added:
    - "@tiptap/extension-youtube@3.20.4"
  patterns:
    - "Youtube.extend() wrapper with addStorage() markdown.serialize override"
    - "URL hostname check for domain-safe pattern matching (extractVimeoId)"
    - "No ReactNodeViewRenderer — renderHTML-only block nodes (iframe)"

key-files:
  created:
    - frontend/src/features/notes/editor/extensions/YoutubeExtension.ts
    - frontend/src/features/notes/editor/extensions/VimeoNode.ts
    - frontend/src/features/notes/editor/extensions/__tests__/YoutubeExtension.test.ts
    - frontend/src/features/notes/editor/extensions/__tests__/VimeoNode.test.ts
  modified:
    - frontend/package.json
    - frontend/pnpm-lock.yaml

key-decisions:
  - "renderHTML-only for both extensions — no ReactNodeViewRenderer needed for plain iframes (avoids React 19 flushSync crash)"
  - "extractVimeoId uses URL hostname check (not regex on full URL string) — prevents notvimeo.com false positive match"
  - "addPasteRules() in VimeoNode is a no-op — real paste offer UI lives in VideoPasteDetector (Plan 02)"

patterns-established:
  - "Pattern: Wrap official TipTap extension with .extend() to add addStorage().markdown.serialize — does not override renderHTML"
  - "Pattern: Custom leaf node uses Node.create({ atom: true }) with mergeAttributes for iframe sandbox hardcoding"
  - "Pattern: extractVimeoId uses new URL() + hostname check for domain-safe extraction"

requirements-completed:
  - VID-01
  - VID-02
  - VID-04

# Metrics
duration: 7min
completed: 2026-03-19
---

# Phase 33 Plan 01: Video Embed Extensions Summary

**YoutubeExtension wrapper and custom VimeoNode with iframe sandbox attributes and tiptap-markdown serialization, installed @tiptap/extension-youtube@3.20.4**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-19T14:23:00Z
- **Completed:** 2026-03-19T14:30:38Z
- **Tasks:** 2 (RED + GREEN TDD cycle)
- **Files modified:** 6

## Accomplishments

- Installed `@tiptap/extension-youtube@3.20.4` — official TipTap 3.x YouTube extension
- `YoutubeExtension.ts`: Youtube.extend() wrapper with `nocookie: true`, `sandbox` iframe attribute, `[▶ YouTube](src)` markdown serialization
- `VimeoNode.ts`: custom ~70-line Node.create() with `extractVimeoId`, `isVideoUrl`, `sandbox` iframe attribute, `[▶ Vimeo](src)` markdown serialization
- 12/12 tests passing across both test files (3 YouTube, 9 Vimeo)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — install package + failing tests** - `75705ff0` (test)
2. **Task 2: GREEN — implement both extensions** - `94d49ab1` (feat)

_Note: TDD tasks committed separately (RED then GREEN)_

## Files Created/Modified

- `frontend/src/features/notes/editor/extensions/YoutubeExtension.ts` — Youtube.extend() wrapper with nocookie, sandbox, [▶ YouTube] serialize
- `frontend/src/features/notes/editor/extensions/VimeoNode.ts` — custom VimeoNode with extractVimeoId, isVideoUrl, sandbox, [▶ Vimeo] serialize
- `frontend/src/features/notes/editor/extensions/__tests__/YoutubeExtension.test.ts` — 3 tests: VID-01 insert, VID-04 sandbox, VID-01 round-trip
- `frontend/src/features/notes/editor/extensions/__tests__/VimeoNode.test.ts` — 9 tests: extractVimeoId (3), isVideoUrl (4), VID-04 sandbox, VID-02 round-trip
- `frontend/package.json` — added @tiptap/extension-youtube@^3.20.4
- `frontend/pnpm-lock.yaml` — updated lockfile

## Decisions Made

- **renderHTML-only confirmed** — neither extension needs ReactNodeViewRenderer; plain iframes work via renderHTML with no interactive NodeView needed (avoids MobX observer / React 19 flushSync crash)
- **addPasteRules() in VimeoNode is a no-op** — the plan specifies the real paste detection UI (VideoPasteDetector) lives in Plan 02; VimeoNode just registers the pattern placeholder
- **extractVimeoId uses URL hostname check** — switched from regex on full URL string to `new URL()` + `hostname === 'vimeo.com'` check; see deviation below

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed extractVimeoId false positive on notvimeo.com**

- **Found during:** Task 2 (VimeoNode.ts implementation)
- **Issue:** Initial implementation used `/vimeo\.com\/(\d+)/` regex on the full URL string; this matched `notvimeo.com/123` because `vimeo.com` appears as a substring. Test 3 (`extractVimeoId('https://notvimeo.com/123') === null`) failed.
- **Fix:** Replaced regex with `new URL()` + `hostname === 'vimeo.com'` check — same pattern as `isVideoUrl()`. Domain boundary is enforced by URL parser.
- **Files modified:** `frontend/src/features/notes/editor/extensions/VimeoNode.ts`
- **Verification:** All 12 tests pass including the notvimeo.com boundary test
- **Committed in:** `94d49ab1` (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in regex pattern)
**Impact on plan:** Required for correctness of VID-02. No scope creep.

## Issues Encountered

- `@ts-expect-error` directives written in RED phase became "unused" TypeScript errors in GREEN phase (expected TDD artifact) — removed in the same GREEN commit.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Both extensions are self-contained and ready for Plan 02 to register in `createEditorExtensions.ts` Group 3
- `YoutubeExtension` already configured with `nocookie: true` and sandbox; Plan 02 just needs `extensions.push(YoutubeExtension)`
- `VimeoNode` exports `extractVimeoId` and `isVideoUrl` which Plan 02's `/video` slash command and paste detection will import
- No blockers

---
*Phase: 33-video-embeds*
*Completed: 2026-03-19*
