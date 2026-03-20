---
phase: 37-artifact-preview-rendering-engine
plan: "01"
subsystem: frontend/artifacts
tags: [html-preview, sandboxed-iframe, dompurify, renderer, security, tdd]
dependency_graph:
  requires: []
  provides: [HtmlRenderer, html-preview RendererType]
  affects:
    - frontend/src/features/artifacts/utils/mime-type-router.ts
    - frontend/src/features/artifacts/components/FilePreviewModal.tsx
tech_stack:
  added: [dompurify (existing dep, new usage site)]
  patterns: [sandboxed-iframe, source-preview-toggle, DOMPurify sanitization, TDD RED-GREEN]
key_files:
  created:
    - frontend/src/features/artifacts/components/renderers/HtmlRenderer.tsx
    - frontend/src/features/artifacts/components/__tests__/HtmlRenderer.test.tsx
  modified:
    - frontend/src/features/artifacts/utils/mime-type-router.ts
    - frontend/src/features/artifacts/components/FilePreviewModal.tsx
    - frontend/src/features/artifacts/utils/__tests__/mime-type-router.test.ts
decisions:
  - "HtmlRenderer defaults to source mode (safe-by-default) — user opts into live preview"
  - "sandbox='allow-same-origin' only — never allow-scripts, prevents JS execution in iframe"
  - "FORBID_TAGS=['script','object','embed'] in DOMPurify config — defense-in-depth on top of iframe sandbox"
  - "html/htm removed from CODE_EXTENSIONS Set — html-preview is a separate routing path"
  - "FilePreviewModal wired immediately (Rule 2: missing critical functionality) — prevents html-preview falling to DownloadFallback"
metrics:
  duration: "3m 53s"
  completed: "2026-03-20"
  tasks_completed: 2
  files_created: 2
  files_modified: 3
---

# Phase 37 Plan 01: HtmlRenderer and HTML Preview Routing Summary

**One-liner:** Sandboxed HTML live preview with `DOMPurify` sanitization and `allow-same-origin`-only iframe, toggled from source-mode default via tab bar.

## What Was Built

- `HtmlRenderer.tsx`: Source/Preview tab bar component. Source mode delegates to `CodeRenderer` (syntax-highlighted HTML). Preview mode renders HTML in a sandboxed iframe with `DOMPurify.sanitize()` applied before setting `srcDoc`. Defaults to source mode for safe-by-default posture.
- `mime-type-router.ts`: Added `'html-preview'` to the `RendererType` union. Rule 5 now returns `'html-preview'` for `text/html`, `.html`, and `.htm` files. `html` and `htm` removed from `CODE_EXTENSIONS` Set.
- `FilePreviewModal.tsx`: Added `HtmlRenderer` import and `case 'html-preview'` in the renderer switch.
- Tests: 8 HtmlRenderer unit tests + 3 updated mime-type-router HTML routing tests (all GREEN, 97 total).

## Success Criteria Verified

- [x] HtmlRenderer.tsx exists and exports `HtmlRenderer` component
- [x] HTML files route to `'html-preview'` in mime-type-router (not `'code'`)
- [x] HtmlRenderer defaults to `'source'` mode (safe-by-default)
- [x] HtmlRenderer `'preview'` mode uses sandboxed iframe with DOMPurify
- [x] iframe sandbox does NOT contain `'allow-scripts'`
- [x] All artifact tests pass (97/97)
- [x] TypeScript compilation passes (`pnpm type-check`)
- [x] ESLint passes (0 errors, 18 pre-existing warnings in unrelated files)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FilePreviewModal missing html-preview case in switch**
- **Found during:** Task 2 — artifact tests showed `FilePreviewModal.test.tsx` failing because `html-preview` was falling to `DownloadFallback` in the switch statement
- **Issue:** `FilePreviewModal` switch only covered `markdown`, `text`, `json`, `code`, `csv` — new `html-preview` type hit `default: DownloadFallback`
- **Fix:** Added `HtmlRenderer` import and `case 'html-preview': return <HtmlRenderer content={content} filename={filename} />;` to the switch
- **Files modified:** `frontend/src/features/artifacts/components/FilePreviewModal.tsx`
- **Commit:** bf330331

**2. [Rule 1 - Bug] TypeScript error: PURIFY_CONFIG FORBID_TAGS readonly vs mutable string[]**
- **Found during:** Task 2 type-check
- **Issue:** `as const` made `FORBID_TAGS` `readonly ["script", "object", "embed"]` which is incompatible with `DOMPurify.Config`'s `string[]` parameter
- **Fix:** Changed `as const` to explicit `as string[]` cast on `FORBID_TAGS`
- **Files modified:** `frontend/src/features/artifacts/components/renderers/HtmlRenderer.tsx`
- **Commit:** bf330331 (same commit as FilePreviewModal fix)

## Self-Check: PASSED

All key files exist on disk. Both commits (81148bdf, bf330331) found in git log. 97/97 tests pass.
