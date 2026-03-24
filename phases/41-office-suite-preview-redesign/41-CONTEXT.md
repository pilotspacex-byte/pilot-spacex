# Phase 41: Office Suite Preview Redesign - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning
**Source:** Auto-generated from roadmap, existing plans, UI-SPEC, and codebase analysis

<domain>
## Phase Boundary

Redesign the Office document preview experience (Excel, Word, PowerPoint) to match Google Docs-level UX and customer experience. Polished layouts, responsive design, intuitive interactions, and professional visual quality. All rendering is client-side only (no server conversion). Preview-only — no editing of Office documents.

</domain>

<decisions>
## Implementation Decisions

### XLSX Renderer (Google Sheets Feel)
- Frozen header row with sticky positioning — headers stay visible during scroll
- Column resizing via mouse drag with visual resize handle
- Sheet tab bar at bottom for multi-sheet workbooks — active tab highlighted with accent color
- Search with debounced input and cell highlight (yellow background on matches)
- 500-row truncation cap with warning banner ("Showing first 500 rows")
- SheetJS (`xlsx`) library for parsing with `XLSX.read()` and `dense: true` mode
- Loading spinner for large files (up to 10 MB)

### DOCX Renderer (Google Docs Feel)
- Dual-engine rendering: `docx-preview@0.3.7` (primary) + `mammoth@1.12.0` (fallback)
- Sandboxed iframe with `srcdoc` for style isolation from app styles
- Page-break CSS indicators at break points
- Table of contents sidebar (224px) extracted from DOCX headings with scroll-to navigation
- DOMPurify sanitization with dedicated DOCX config (blocks `javascript:` URIs)
- Dynamic imports with `ssr: false` (both libraries reference `window`/`document`)

### PPTX Renderer (Google Slides Feel)
- Canvas-based slide rendering via PptxViewJS
- 16:9 aspect ratio maintained with ResizeObserver
- Thumbnail strip sidebar (156px) with lazy rendering via IntersectionObserver
- Prev/Next navigation buttons + Left/Right arrow key controls
- "Slide N / M" counter
- Fullscreen slideshow mode with floating pill navigation overlay
- Slide canvas styling: `rounded-lg overflow-hidden shadow-md ring-1 ring-border/40 bg-white`

### Annotation Panel
- 320px wide sidebar showing current slide annotations
- Per-slide notes with real-time persistence via TanStack Query
- Create: textarea with Cmd+Enter submit hint
- Edit: pencil icon (owner-only), inline textarea replacement
- Delete: trash icon (owner-only), immediate optimistic fade (no confirmation dialog)
- Annotation count badge on collapsed icon (capped at "9+")
- Backend: `ArtifactAnnotation` model with RLS and hard delete (not soft delete)

### Infrastructure
- Extension-first MIME type resolution (check file extension before MIME type — handles `application/octet-stream`)
- `useFileContent` extended with `res.arrayBuffer()` for binary Office files
- Backend allowlist extended for `.docx`, `.doc`, `.pptx`, `.ppt` MIME types
- All Office renderers lazy-loaded via `next/dynamic` with `ssr: false`
- Legacy formats (`.doc`, `.xls`, `.ppt`) show DownloadFallback with "legacy format" reason

### Responsive & Keyboard
- All previews work in both normal and maximized modal states
- PPTX: arrow keys for slide navigation, Escape to close fullscreen
- Modal: Escape to close (existing behavior preserved)

### Claude's Discretion
- Exact animation timings for slide transitions
- Cell selection/highlight behavior in XLSX beyond search
- ToC sidebar collapse/expand trigger mechanism
- Thumbnail strip scroll behavior (snap vs smooth)
- Annotation panel collapse animation style

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Artifact Infrastructure
- `frontend/src/features/artifacts/components/FilePreviewModal.tsx` — Modal shell, renderer dispatch (438 lines)
- `frontend/src/features/artifacts/utils/mime-type-router.ts` — MIME type → RendererType routing table (188 lines)
- `frontend/src/features/artifacts/hooks/useFileContent.ts` — Content fetching hook (needs ArrayBuffer extension)
- `frontend/src/features/artifacts/components/renderers/` — 7 existing renderers (Markdown, Text, JSON, Code, CSV, HTML, Image)

### UI Design Contract
- `.planning/phases/41-office-suite-preview-redesign/41-UI-SPEC.md` — Full UI design specification (406 lines)

### Phase Research
- `.planning/phases/41-office-suite-preview-redesign/41-RESEARCH.md` — Technical research findings

### Existing v1.2 Planning (reference only — Phase 41 is a REDESIGN)
- `.planning/milestones/v1.2-office-suite/` — Original v1.2 milestone plans and summaries

### Project Design System
- `specs/001-pilot-space-mvp/ui-design-spec.md` — UI/UX design specification v4.0
- `.impeccable.md` — Design context, brand personality

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FilePreviewModal.tsx` — Modal shell with maximize toggle, download button, renderer dispatch. Extend `renderContent()` for Office types.
- `resolveRenderer()` — Single routing table in `mime-type-router.ts`. Add `xlsx`, `docx`, `pptx` RendererType values.
- `useFileContent` hook — TanStack Query with 55-min stale time. Extend for `res.arrayBuffer()` binary mode.
- `dompurify@3.3.1` — Already installed. Reuse for DOCX HTML sanitization.
- `DownloadFallback` component — Already exists for unsupported types. Reuse for legacy Office formats.
- `next/dynamic` with `ssr: false` — Established pattern for heavy components (CodeRenderer, HtmlRenderer).

### Established Patterns
- Lazy-loaded renderers via `next/dynamic` — all Office renderers MUST follow this pattern
- TanStack Query for server state (annotations use same patterns as existing artifact hooks)
- shadcn/ui components for UI (Tooltip, Button, Separator, Badge, ScrollArea)
- MobX for UI state — but annotation panel state should use TanStack Query (server state)

### Integration Points
- `FilePreviewModal.renderContent()` — Switch statement adding Office cases
- `mime-type-router.ts` — Add Office RendererType values and extension mappings
- `useFileContent.ts` — Add ArrayBuffer branch for binary renderer types
- Backend `ALLOWED_EXTENSIONS` — Add `.docx`, `.doc`, `.pptx`, `.ppt`

</code_context>

<specifics>
## Specific Ideas

- "Google Docs-level UX" means each renderer should feel as polished as its Google counterpart
- XLSX should feel like opening a spreadsheet in Google Sheets — not a raw HTML table
- DOCX should feel like reading in Google Docs — clean prose, not raw HTML dump
- PPTX should feel like presenting in Google Slides — smooth transitions, proper aspect ratio
- Annotation panel connects Pilot Space's "Note-First" paradigm to presentations — users annotate slides as part of their workflow

</specifics>

<deferred>
## Deferred Ideas

- Live editing of Office documents — explicit out-of-scope per PROJECT.md
- PDF preview — not requested, download fallback acceptable
- Video/audio preview — download fallback covers these
- File size limit increase beyond 10 MB — not needed
- XLSX cell selection/editing — preview only, no spreadsheet editing
- DOCX commenting/track changes — preview only

</deferred>

---

*Phase: 41-office-suite-preview-redesign*
*Context gathered: 2026-03-24 via auto mode*
