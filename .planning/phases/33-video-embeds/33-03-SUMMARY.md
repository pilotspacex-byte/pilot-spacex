---
phase: 33-video-embeds
plan: "03"
subsystem: frontend-config
tags: [csp, headers, next-config, css, video-embed, youtube, vimeo]
dependency_graph:
  requires: []
  provides: [csp-frame-src-header, video-embed-css]
  affects: [next.config.ts, globals.css]
tech_stack:
  added: []
  patterns: [next-headers-csp, responsive-iframe-aspect-ratio]
key_files:
  created: []
  modified:
    - frontend/next.config.ts
    - frontend/src/app/globals.css
decisions:
  - "CSP directive is frame-src only (not full CSP policy) — minimal surface, additive pattern"
  - "frame-src 'self' preserves any same-origin iframes; only 1 iframe found in codebase (test file)"
  - "aspect-ratio: 16/9 via CSS property (not padding-top hack) — modern browsers support it"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-19T14:25:14Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 33 Plan 03: CSP Headers and Video Embed CSS Summary

**One-liner:** CSP `frame-src 'self' https://www.youtube-nocookie.com https://player.vimeo.com` header added to Next.js config, plus responsive `.video-embed` CSS class at 16:9 aspect ratio.

## What Was Changed

### Task 1: next.config.ts — CSP header + optimizePackageImports (commit b62a96a0)

Two changes to `frontend/next.config.ts`:

1. **`async headers()` function added** — returns a single CSP `Content-Security-Policy` header applied to all routes (`source: '/(.*)'`). The exact header value written is:

   ```
   frame-src 'self' https://www.youtube-nocookie.com https://player.vimeo.com
   ```

   - `'self'`: preserves any same-origin iframe usage
   - `https://www.youtube-nocookie.com`: used by `@tiptap/extension-youtube` (nocookie mode)
   - `https://player.vimeo.com`: used by the custom VimeoNode extension

2. **`@tiptap/extension-youtube` added to `experimental.optimizePackageImports`** — placed after `@tiptap/extension-character-count`, before `recharts`.

All existing config (rewrites, redirects, output, outputFileTracingIncludes, poweredByHeader, reactStrictMode, images) is unchanged.

### Task 2: globals.css — .video-embed CSS (commit 5b4336be)

Appended at the end of `frontend/src/app/globals.css`:

- `.video-embed`: `width: 100%`, `aspect-ratio: 16 / 9`, `border: none`, `border-radius: var(--radius, 6px)`, `display: block`, `margin: 1rem 0`
- `.video-embed--youtube`, `.video-embed--vimeo`: `max-width: 100%` — variant classes for provider-specific sizing
- `.video-url-prompt:focus`: `outline: 2px solid var(--ring, #94a3b8)` — focus style for URL input overlays

## Existing iframe Usage Audit

One iframe found in the entire codebase:
- `frontend/src/features/notes/editor/extensions/pm-blocks/__tests__/MermaidPreview.test.tsx`

This is a **test file only** — not a production iframe. The `frame-src 'self'` directive preserves same-origin iframes, so this test file is not affected. No production iframes are broken.

## Verification Results

- `grep "frame-src.*youtube-nocookie.*vimeo" frontend/next.config.ts` — 1 match (line 41)
- `grep "extension-youtube" frontend/next.config.ts` — 1 match in optimizePackageImports (line 95)
- `grep "async headers" frontend/next.config.ts` — 1 match (line 30)
- `grep "video-embed" frontend/src/app/globals.css` — 4 matches (.video-embed, comment, .video-embed--youtube, .video-embed--vimeo)
- `grep "aspect-ratio: 16" frontend/src/app/globals.css` — 1 match (line 2747)
- `grep "video-url-prompt" frontend/src/app/globals.css` — 1 match (line 2760)
- `pnpm type-check` — 3 pre-existing errors in `YoutubeExtension.test.ts` (TDD RED state from Plan 33-01, `setYoutubeVideo` not yet implemented). **0 new errors from this plan's changes.**

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `frontend/next.config.ts` — FOUND: async headers(), frame-src, @tiptap/extension-youtube
- `frontend/src/app/globals.css` — FOUND: .video-embed, aspect-ratio: 16 / 9, .video-url-prompt
- Commits b62a96a0 and 5b4336be — both present in git log
