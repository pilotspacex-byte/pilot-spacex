# Phase 4: PowerPoint Base - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Slide-by-slide `.pptx` preview with navigation controls (Prev/Next), "Slide N of M" counter, slide thumbnail strip sidebar, and fullscreen slideshow mode with keyboard navigation. `.ppt` legacy files degrade to download fallback. No annotations in this phase — that's Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Rendering approach (PPTX-01)
- Use PptxViewJS 1.1.8 — Canvas-based PPTX renderer accepting ArrayBuffer
- Render slides to `<canvas>` element inside the modal body
- Controlled component: `currentSlide` index as React state in FilePreviewModal, passed as prop to PptxRenderer
- PptxRenderer exposes `onSlideCountKnown(total)` callback after parse — modal uses this for "N of M" counter
- [auto] Selected: Single canvas, re-render on slide change (simpler than pre-rendering all slides)

### Navigation controls (PPTX-01)
- Prev/Next buttons below the slide canvas (centered, icon buttons with `ChevronLeft`/`ChevronRight`)
- "Slide N of M" counter between the buttons
- Keyboard navigation: Left arrow = prev, Right arrow = next (only when renderer is focused or in fullscreen)
- Prev disabled on slide 1, Next disabled on last slide
- [auto] Selected: Buttons + keyboard + slide counter in a compact toolbar below the canvas

### Slide thumbnail strip (PPTX-02)
- Vertical strip on the left side of the modal (like PowerPoint's slide panel)
- Each thumbnail: small canvas render of the slide (e.g., 120px wide)
- Active slide highlighted with primary color border
- Click thumbnail → jump to that slide
- [auto] Selected: Lazy-render thumbnails — only render visible thumbnails + 2 ahead/behind (virtual scroll for large decks)
- Toggle visibility: button in modal header bar (hidden by default to maximize slide viewing area)

### Fullscreen slideshow (PPTX-04)
- Use browser Fullscreen API (`element.requestFullscreen()`)
- In fullscreen: slide fills viewport, black background, no UI chrome except subtle slide counter
- Left/Right arrow keys navigate slides
- Escape exits fullscreen (browser default behavior)
- [auto] Selected: Fullscreen button in the modal header bar (next to maximize button)

### Slide navigation state
- `currentSlide: number` and `slideCount: number` as `React.useState` in FilePreviewModal
- NOT in ArtifactStore — this is ephemeral, no cross-component subscribers
- Reset to slide 0 when modal opens (same as `isMaximized` reset pattern)
- PptxRenderer is a controlled component: receives `currentSlide` prop, calls `onNavigate(index)`

### Legacy format fallback
- `.ppt` files detected by extension in the renderer (same as Phase 1's routing)
- Show `DownloadFallback` with `reason="legacy"` — "PowerPoint 97-2003 (.ppt) files require a desktop application"

### Claude's Discretion
- Exact thumbnail size and spacing
- Canvas aspect ratio handling (16:9 vs 4:3 presentations)
- Slide transition animation (if any — probably none for v1)
- Touch/swipe gesture support (mobile)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Library documentation
- `.planning/research/STACK.md` — PptxViewJS 1.1.8 API: `loadFile(ArrayBuffer)`, slide count, navigation
- `.planning/research/SUMMARY.md` §Architecture Approach — Controlled component prop contract

### Existing patterns
- `frontend/src/features/artifacts/components/FilePreviewModal.tsx` — `isMaximized` state pattern, modal header actions
- `frontend/src/features/artifacts/components/renderers/HtmlRenderer.tsx` — Tab bar pattern (source/preview toggle) — reuse for thumbnail toggle

### Phase 1 output (dependency)
- `frontend/src/features/artifacts/utils/mime-type-router.ts` — Must have 'pptx' RendererType
- `frontend/src/features/artifacts/hooks/useFileContent.ts` — Must return ArrayBuffer for 'pptx' type

### Phase 5 interface contract
- PptxRenderer MUST expose: `currentSlide` (prop), `onSlideCountKnown(total)` (callback), `onNavigate(index)` (callback)
- Phase 5 annotations will connect to this interface — do not change it without updating Phase 5 context

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FilePreviewModal`: Already has `isMaximized` state, header actions (download, maximize, close) — add fullscreen button, slide nav state
- `Button` (shadcn/ui): For nav buttons
- `ChevronLeft`, `ChevronRight`, `Maximize2`, `Play` (lucide-react): Icon components

### Established Patterns
- Modal state management: `React.useState` + `React.useEffect` reset on open — follow for slide state
- Lazy loading: `dynamic(() => import('./renderers/PptxRenderer').then(...))` with `{ ssr: false }`

### Integration Points
- `FilePreviewModal.tsx`: Add slide navigation state, fullscreen handler, thumbnail toggle, case 'pptx' in renderContent()
- New file: `frontend/src/features/artifacts/components/renderers/PptxRenderer.tsx`
- Package.json: Add `pptxviewjs` dependency

</code_context>

<specifics>
## Specific Ideas

- Fullscreen should feel like actual PowerPoint slideshow — black background, centered slide, minimal chrome
- Thumbnail strip like PowerPoint's left panel — vertical, scrollable, compact

</specifics>

<deferred>
## Deferred Ideas

- Slide transition animations — skip for v1
- Speaker notes display — not in scope
- Touch/swipe gestures for mobile — consider in future

</deferred>

---

*Phase: 04-powerpoint-base*
*Context gathered: 2026-03-22*
