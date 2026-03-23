# Phase 2: Word Renderer - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Preview `.docx` files inside the artifact modal with preserved formatting (fonts, colors, alignment, images). Mammoth fallback when docx-preview fails. Page-break indicators. Table of contents sidebar navigation. `.doc` legacy files degrade gracefully to download fallback (handled in Phase 1).

</domain>

<decisions>
## Implementation Decisions

### Rendering approach (DOCX-01)
- Primary renderer: `docx-preview` 0.3.7 — renders DOCX directly into a DOM container with CSS styling
- Render into a `<div>` inside the modal body, wrapped in `overflow-auto` scrollable container
- docx-preview outputs styled HTML — must be contained to prevent style leakage (use scoped container or iframe)
- [auto] Selected: Render into sandboxed iframe (same pattern as HtmlRenderer) for style isolation

### Fallback strategy (DOCX-02)
- When docx-preview throws an error, catch and re-render using mammoth.js
- mammoth converts DOCX ArrayBuffer → HTML string
- Mammoth HTML output goes through DOMPurify with dedicated `DOCX_PURIFY_CONFIG`
- [auto] Selected: Show fallback seamlessly — no error flash. Use React error boundary or try/catch in render effect

### Security — DOMPurify config (critical)
- MUST NOT reuse `HtmlRenderer`'s `PURIFY_CONFIG` — it doesn't block `javascript:` hrefs
- Dedicated `DOCX_PURIFY_CONFIG` with:
  - `ALLOWED_URI_REGEXP: /^(?:https?|mailto|data):/i` — blocks `javascript:` scheme
  - `FORBID_TAGS: ['script', 'object', 'embed', 'style', 'link', 'base', 'meta']`
  - `FORBID_ATTR: ['style']` may be too aggressive for docx-preview (which uses inline styles) — test and relax if needed
- Pin mammoth `>= 1.11.0` to avoid CVE-2025-11849

### Page-break indicators (DOCX-03)
- docx-preview renders page breaks as elements with specific CSS classes — detect and style as visual dividers
- [auto] Selected: Horizontal rule with "Page break" label (subtle, non-intrusive)
- mammoth fallback: does not preserve page breaks — show continuous flow (acceptable degradation)

### Table of contents sidebar (DOCX-04)
- Extract headings from the rendered DOM after docx-preview finishes
- Query `h1, h2, h3` elements in the rendered container
- Display as a collapsible sidebar on the left (similar to code editor outline)
- Click a heading → `element.scrollIntoView({ behavior: 'smooth' })`
- [auto] Selected: Sidebar hidden by default, toggle button in the modal header bar
- mammoth fallback: headings still render as `<h1>-<h3>` — ToC extraction works on both renderers

### Claude's Discretion
- Exact sidebar width and styling
- Whether to show heading nesting depth indicators (indentation)
- Loading spinner design during docx-preview render
- How to handle very small DOCX files (< 1KB) — likely empty or corrupt

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing patterns to follow
- `frontend/src/features/artifacts/components/renderers/HtmlRenderer.tsx` — Sandboxed iframe pattern + DOMPurify config (reference, but use dedicated DOCX config)
- `frontend/src/features/artifacts/components/renderers/CsvRenderer.tsx` — Large content handling pattern (row cap, truncation banner)
- `frontend/src/features/artifacts/components/FilePreviewModal.tsx` — Dynamic import registration + renderContent() switch

### Security
- `.planning/research/PITFALLS.md` — Pitfall 2 (mammoth XSS via javascript: hrefs), Pitfall 3 (CVE-2025-11849)
- `.planning/research/SUMMARY.md` §Critical Pitfalls — DOMPurify ALLOWED_URI_REGEXP requirement

### Libraries
- `.planning/research/STACK.md` — docx-preview 0.3.7 and mammoth 1.12.0 API details, installation

### Phase 1 output (dependency)
- `frontend/src/features/artifacts/utils/mime-type-router.ts` — Must have 'docx' RendererType from Phase 1
- `frontend/src/features/artifacts/hooks/useFileContent.ts` — Must return ArrayBuffer for 'docx' type from Phase 1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `HtmlRenderer.tsx`: Sandboxed iframe pattern — reuse for docx-preview output isolation
- `DOMPurify`: Already installed — create dedicated `DOCX_PURIFY_CONFIG`
- `ScrollArea` component: From shadcn/ui — use for ToC sidebar scroll

### Established Patterns
- Lazy loading: `const DocxRenderer = dynamic(() => import('./renderers/DocxRenderer').then(...))` with `{ ssr: false }`
- Error state: `DownloadFallback` component with `reason="error"` — reuse for catastrophic renderer failure

### Integration Points
- `FilePreviewModal.tsx`: Add `case 'docx':` in renderContent() switch
- New file: `frontend/src/features/artifacts/components/renderers/DocxRenderer.tsx`
- Package.json: Add `docx-preview` and `mammoth` dependencies

</code_context>

<specifics>
## Specific Ideas

- docx-preview should render "like Google Docs" — continuous scrollable view, not paginated
- mammoth fallback should be invisible to the user — no "using fallback renderer" banner unless useful for debugging

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-word-renderer*
*Context gathered: 2026-03-22*
