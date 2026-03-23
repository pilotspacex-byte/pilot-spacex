---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: milestone
status: planning
stopped_at: Completed 05-pptx-annotations 05-02-PLAN.md
last_updated: "2026-03-22T09:33:14.100Z"
last_activity: 2026-03-21 — Roadmap created for v1.2 Office Suite Preview
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 10
  completed_plans: 10
  percent: 10
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-21)

**Core value:** Think first, structure later — notes are the entry point, not forms.
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 5 (Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-21 — Roadmap created for v1.2 Office Suite Preview

Progress: [█░░░░░░░░░] 10%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01-foundation P01 | 4 min | 3 tasks | 6 files |
| Phase 01-foundation P02 | 15 | 2 tasks | 2 files |
| Phase 02-word-renderer P01 | 5 | 2 tasks | 5 files |
| Phase 02-word-renderer P02 | 7 | 2 tasks | 4 files |
| Phase 03-excel-renderer P01 | 8 | 2 tasks | 4 files |
| Phase 03-excel-renderer P02 | 8 | 2 tasks | 1 files |
| Phase 04-powerpoint-base PP01 | 4 | 2 tasks | 4 files |
| Phase 04-powerpoint-base P02 | 3 | 2 tasks | 2 files |
| Phase 05-pptx-annotations PP01 | 8 | 2 tasks | 9 files |
| Phase 05-pptx-annotations P02 | 4 | 3 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-phase]: Client-side only parsing — no server-side conversion; all libraries lazy-loaded via next/dynamic with ssr: false
- [Pre-phase]: Phase order Word before Excel — Word validates ArrayBuffer pipeline with simpler renderer before Excel adds Worker complexity
- [Pre-phase]: PPTX annotations in Phase 5 (separate from base in Phase 4) — requires stable renderer prop contract and new artifact_annotations backend table
- [Phase 01-foundation]: Extension check precedes MIME check for Office files — octet-stream workaround requires ext-first resolution
- [Phase 01-foundation]: BINARY_RENDERER_TYPES exported from useFileContent.ts as canonical Set for downstream Office renderer binary/text branching
- [Phase 01-foundation]: FilePreviewModal Office cases use DownloadFallback stubs (xlsx/docx/pptx) — real renderers added in Phases 2-4
- [Phase 01-foundation]: Office format early return placed before content-fetch checks in FilePreviewModal — legacy formats don't need fetch, modern formats need placeholder until Phase 2-4
- [Phase 01-foundation]: isLegacyOfficeFormat() checks file extension (.doc/.xls/.ppt) for legacy format detection, matching extension-first resolution in resolveRenderer
- [Phase 02-word-renderer]: DOCX_PURIFY_CONFIG dedicated module with ALLOWED_URI_REGEXP=/^(?:https?|mailto|data:image\/):/i blocks javascript: hrefs from mammoth output; allows style attributes unlike HtmlRenderer config
- [Phase 02-word-renderer]: docx-preview renders into off-screen div then innerHTML extracted to iframe srcdoc; provides style isolation without shadow DOM complexity
- [Phase 02-word-renderer]: mammoth fallback invisible to user — no banner shown; renderMode stored as data-render-mode attribute for debugging only
- [Phase 02-word-renderer]: DOMParser heading extraction from HTML string before iframe creation — avoids sandboxed iframe DOM access limitation
- [Phase 02-word-renderer]: allow-scripts sandbox injection for scroll-on-load — most reliable approach for sandbox='' iframes without postMessage listener
- [Phase 02-word-renderer]: tocOpen lifted to FilePreviewModal (Option A) — cleaner than useImperativeHandle, aligns with React unidirectional data flow
- [Phase 03-excel-renderer]: SheetJS installed from CDN tarball; setTimeout deferred parse over Web Worker (simpler, STATE.md blocker on Next.js bundling); XLSX.read with dense:true for memory efficiency
- [Phase 03-excel-renderer]: JS drag handler chosen over CSS resize:horizontal — CSS resize on th inconsistent cross-browser; JS approach reliable in table-fixed layout
- [Phase 03-excel-renderer]: highlightCell as standalone function (not hook) — pure function returning React.ReactNode, no side effects
- [Phase 04-powerpoint-base]: Controlled component pattern: currentSlide state in FilePreviewModal not ArtifactStore; Phase 5 interface contract locked: currentSlide prop, onSlideCountKnown, onNavigate callbacks
- [Phase 04-powerpoint-base]: Single canvas re-render per slide change; PPTXViewer destroy() on unmount; default 16:9 aspect ratio for canvas sizing
- [Phase 04-powerpoint-base]: Separate PPTXViewer instance for thumbnails avoids cross-instance state with main PptxRenderer; thumbnail strip hidden in fullscreen; showThumbnails defaults false
- [Phase 05-pptx-annotations]: Hard delete for annotations (no soft-delete): annotations are ephemeral comments, not audited entities
- [Phase 05-pptx-annotations]: Author ownership enforced at router layer (404+403 checks) in addition to RLS workspace isolation
- [Phase 05-pptx-annotations]: Migration 096 merges two 095 heads using tuple down_revision
- [Phase 05-pptx-annotations]: Use useParams() inside FilePreviewModal to get projectId; workspaceId/currentUserId from MobX stores via useStore()
- [Phase 05-pptx-annotations]: PptxAnnotationPanel toggle state is internal; collapses to narrow icon strip with badge; hidden during fullscreen

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: Web Worker bundling in Next.js App Router requires verification — next.config.js may need webWorker/turbo config for new URL() pattern. setTimeout fallback is documented escape hatch.
- [Phase 4]: PptxViewJS exact gzip bundle size is estimated (~120 KB) not measured — verify after install before declaring Phase 4 plan count.

## Session Continuity

Last session: 2026-03-22T09:29:16.226Z
Stopped at: Completed 05-pptx-annotations 05-02-PLAN.md
Resume file: None
