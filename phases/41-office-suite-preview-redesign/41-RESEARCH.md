# Phase 41: Office Suite Preview Redesign - Research

**Researched:** 2026-03-24
**Domain:** Frontend — Office document rendering (XLSX, DOCX, PPTX) in browser
**Confidence:** MEDIUM-HIGH

## Summary

This phase redesigns the file preview experience for Office documents (Excel, Word, PowerPoint) to achieve Google Docs-level UX within the existing `FilePreviewModal` component. The current codebase has NO Office document renderers -- only text, code, CSV, markdown, HTML, JSON, and image renderers exist. The mime-type router does not even have routes for xlsx/docx/pptx types, and the backend upload service only allows `.xlsx`/`.xls` (no `.docx` or `.pptx`).

The approved UI-SPEC (`41-UI-SPEC.md`) defines detailed layout contracts, interaction patterns, and design tokens for all three renderers plus an annotation panel. The annotation panel requires backend CRUD endpoints that do not exist yet -- this is a full-stack feature, not frontend-only.

**Primary recommendation:** Use SheetJS (xlsx) for XLSX parsing, docx-preview + mammoth fallback for DOCX rendering, and either `@kandiforge/pptx-renderer` or `pptxviewjs` for PPTX canvas rendering. Build annotation CRUD as a new backend endpoint set with a lightweight DB model. All three renderers should be dynamic imports to avoid bloating the main bundle.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| XLSX-RENDER | XLSX preview feels like Google Sheets -- frozen headers, smooth scrolling, clean sheet tabs, responsive column resizing | SheetJS `xlsx` parses workbooks to JSON; shadcn Table + sticky headers + custom resize handles |
| DOCX-RENDER | DOCX preview feels like Google Docs -- clean prose rendering, navigable ToC sidebar, proper page feel | docx-preview renders to HTML in sandboxed iframe; mammoth.js as fallback; heading extraction for ToC |
| PPTX-RENDER | PPTX preview feels like Google Slides -- slide canvas with 16:9 aspect, slide transitions, thumbnail nav, fullscreen | Canvas-based renderer (`@kandiforge/pptx-renderer` or `pptxviewjs`); thumbnail strip with IntersectionObserver |
| ANNOT-PANEL | Annotation panel -- per-slide notes with real-time persistence, edit/delete UX | New backend CRUD endpoints + TanStack Query mutations; optimistic UI |
| RESPONSIVE | All previews work in normal and maximized modal states | ResizeObserver for canvas; flex layouts; responsive sidebars |
| KEYBOARD | Keyboard navigation -- arrows for slides, Escape to close | KeyboardEvent listeners; Radix Dialog handles Escape |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| xlsx (SheetJS) | 0.18.5 | Parse XLSX/XLS to JSON | De facto standard; 35K+ GitHub stars; pure JS; parses sheets, merged cells, formulas |
| docx-preview | 0.3.7 | Render DOCX to HTML | Best fidelity for Word rendering in browser; preserves styles, tables, images |
| mammoth | 1.12.0 | DOCX to HTML fallback | Semantic HTML conversion; lighter weight; fallback when docx-preview fails |
| @kandiforge/pptx-renderer | 3.3.0 | Canvas-based PPTX slide rendering | React-native component; canvas rendering; filmstrip nav built-in; TypeScript |

**Alternative PPTX option:** `pptxviewjs` (1.1.9) -- framework-agnostic canvas renderer with Chart.js support. Requires `jszip` peer dependency. Choose `@kandiforge/pptx-renderer` first for its React-native API and built-in filmstrip; fall back to `pptxviewjs` if rendering quality is insufficient.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | ^5.90.19 | Annotation CRUD mutations | Already installed; use for annotation create/edit/delete |
| @tanstack/react-virtual | ^3.13.0 | Virtual scroll for large sheets | Already installed; use if XLSX has >100 visible rows |
| @radix-ui/react-tooltip | ^1.2.8 | Icon-only button tooltips | Already installed; UI-SPEC requires tooltips on all toolbar buttons |
| @radix-ui/react-scroll-area | ^1.2.10 | Scrollable panels | Already installed; ToC sidebar, annotation panel, thumbnail strip |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| xlsx (SheetJS CE) | exceljs | exceljs is heavier (~500KB vs ~300KB); SheetJS is more battle-tested for read-only |
| docx-preview | Only mammoth | mammoth loses visual fidelity (no page breaks, styles); docx-preview preserves Word look |
| @kandiforge/pptx-renderer | pptxviewjs | pptxviewjs is framework-agnostic (more setup); @kandiforge is React-first with TypeScript |
| Custom annotation backend | Local storage | Local storage is per-device, not shared; backend enables team collaboration |

**Installation:**
```bash
cd frontend && pnpm add xlsx docx-preview mammoth @kandiforge/pptx-renderer
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/features/artifacts/
  components/
    FilePreviewModal.tsx          # Existing — add dynamic imports for new renderers
    PptxAnnotationPanel.tsx       # NEW — per-slide annotation CRUD
    renderers/
      XlsxRenderer.tsx            # NEW — SheetJS parsing + shadcn Table
      DocxRenderer.tsx             # NEW — docx-preview + mammoth fallback
      DocxTocSidebar.tsx           # NEW — heading extraction + scroll-to
      PptxRenderer.tsx             # NEW — canvas renderer wrapper
      PptxThumbnailStrip.tsx       # NEW — lazy thumbnail sidebar
      DownloadFallback.tsx         # Existing — add "legacy" reason for .doc/.ppt
    preview-skeletons.tsx          # Existing — add new skeleton variants
  hooks/
    useFileContent.ts              # Existing — needs binary fetch mode (ArrayBuffer)
    usePptxAnnotations.ts          # NEW — TanStack Query CRUD for annotations
  utils/
    mime-type-router.ts            # Existing — add xlsx/docx/pptx routes
```

### Pattern 1: Dynamic Import for Heavy Renderers
**What:** Each Office renderer is loaded via `next/dynamic` with a type-matched skeleton
**When to use:** Always -- xlsx (~300KB), docx-preview (~200KB), pptx renderer (~150KB) must not bloat the main bundle
**Example:**
```typescript
const XlsxRenderer = dynamic(
  () => import('./renderers/XlsxRenderer').then((m) => ({ default: m.XlsxRenderer })),
  { loading: () => <TableSkeleton /> }
);
```

### Pattern 2: Binary Content Fetch
**What:** Office files are binary -- `useFileContent` currently only returns text. Must add ArrayBuffer fetch path.
**When to use:** For xlsx, docx, pptx files where `response.arrayBuffer()` is needed instead of `response.text()`
**Example:**
```typescript
// In useFileContent.ts, add binary mode:
const isBinary = ['xlsx', 'docx', 'pptx'].includes(rendererType);
const data = isBinary ? await res.arrayBuffer() : await res.text();
```

### Pattern 3: Sandboxed Iframe for DOCX
**What:** docx-preview renders into a container element. For security isolation, render inside a sandboxed iframe.
**When to use:** DOCX rendering -- prevents injected styles/scripts from affecting the host page
**Example:**
```typescript
// sandbox="allow-same-origin" allows CSS to work but blocks scripts
<iframe
  ref={iframeRef}
  sandbox="allow-same-origin"
  title={`Preview of ${filename}`}
  aria-label={`Document preview: ${filename}`}
/>
```

### Pattern 4: ResizeObserver for Canvas
**What:** PPTX canvas must maintain 16:9 aspect ratio and re-render when container resizes
**When to use:** PptxRenderer and thumbnail strip
**Example:**
```typescript
useEffect(() => {
  const observer = new ResizeObserver(([entry]) => {
    const width = entry.contentRect.width;
    setCanvasWidth(width);
  });
  observer.observe(containerRef.current);
  return () => observer.disconnect();
}, []);
```

### Pattern 5: Optimistic Mutations for Annotations
**What:** Annotation create/edit/delete uses TanStack Query optimistic updates
**When to use:** PptxAnnotationPanel CRUD operations
**Example:**
```typescript
const createAnnotation = useMutation({
  mutationFn: (data) => apiClient.post(`/artifacts/${artifactId}/annotations`, data),
  onMutate: async (newAnnotation) => {
    await queryClient.cancelQueries({ queryKey: annotationKeys.list(artifactId, slideIndex) });
    const previous = queryClient.getQueryData(annotationKeys.list(artifactId, slideIndex));
    queryClient.setQueryData(annotationKeys.list(artifactId, slideIndex), (old) => [
      ...(old ?? []),
      { ...newAnnotation, id: `temp-${Date.now()}`, isPending: true },
    ]);
    return { previous };
  },
  onError: (_err, _new, context) => {
    queryClient.setQueryData(annotationKeys.list(artifactId, slideIndex), context?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: annotationKeys.list(artifactId, slideIndex) });
  },
});
```

### Anti-Patterns to Avoid
- **Loading entire workbook into state:** SheetJS can parse huge files; limit display to 500 rows (UI-SPEC truncation contract)
- **Rendering all thumbnails eagerly:** Use IntersectionObserver with 200px rootMargin for lazy rendering; cache after first render
- **Using observer() on heavy renderer components:** Same TipTap constraint applies -- canvas renderers with ResizeObserver + MobX can cause flushSync errors in React 19
- **Fetching annotations on every slide change without debounce:** Batch or prefetch adjacent slides

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XLSX parsing | Custom XML parser | SheetJS `xlsx` | Merged cells, formulas, date formats, encoding -- thousands of edge cases |
| DOCX rendering | HTML template from XML | `docx-preview` | Word has complex style inheritance, nested tables, image positioning |
| PPTX slide rendering | SVG/DOM slide builder | Canvas-based renderer library | Text positioning, shape rendering, gradients, master slides -- extreme complexity |
| Column resize drag | Custom mouse tracking | Pointer events + state | But DO use the custom pattern from UI-SPEC (no library needed for simple resize handles) |
| Tooltip on icon buttons | Custom tooltip div | Radix `<Tooltip>` (via shadcn) | Already installed; handles positioning, accessibility, delay |

**Key insight:** Office file formats are enormously complex (OOXML spec is 6,000+ pages). Every "simple" feature (merged cells, master slides, style inheritance) has dozens of edge cases. Use specialized parsers; focus engineering effort on UX polish, not format parsing.

## Common Pitfalls

### Pitfall 1: SheetJS Community Edition Limitations
**What goes wrong:** SheetJS CE (the npm `xlsx` package) is read-only and does NOT include the Pro features (styling, cell formatting, colors). Cells come as raw values only.
**Why it happens:** SheetJS split into CE (free, Apache 2.0) and Pro (paid). The npm package is CE.
**How to avoid:** Design the XLSX renderer to accept raw cell values and apply your own styling via Tailwind/shadcn. Do NOT expect cell background colors, font styles, or conditional formatting from the parser.
**Warning signs:** Attempting to read `cell.s` (style) properties and getting undefined.

### Pitfall 2: docx-preview Requires DOM Container
**What goes wrong:** `docx-preview.renderAsync()` needs a real DOM element. In React, the ref may not be ready on first render.
**Why it happens:** The library mutates DOM directly (not React-friendly). Must ensure ref is populated before calling render.
**How to avoid:** Use `useEffect` with a ref guard: `if (!containerRef.current) return;`. For iframe isolation, render into the iframe's `contentDocument.body`.
**Warning signs:** Blank preview or "Cannot read properties of null" errors.

### Pitfall 3: Binary Fetch with Signed URLs
**What goes wrong:** Current `useFileContent` returns `string` (text). Office files need `ArrayBuffer`. Fetching as text corrupts binary data.
**Why it happens:** The hook was designed for text renderers only.
**How to avoid:** Add a `binary` mode to `useFileContent` that calls `res.arrayBuffer()`. Return `ArrayBuffer | string` union. Or create a separate `useFileBinaryContent` hook.
**Warning signs:** Garbled/empty output from parsers, "Invalid file" errors from SheetJS/docx-preview.

### Pitfall 4: Canvas High-DPI Rendering
**What goes wrong:** Canvas renders blurry on Retina/HiDPI displays.
**Why it happens:** Canvas logical pixels != device pixels. Must scale by `window.devicePixelRatio`.
**How to avoid:** `@kandiforge/pptx-renderer` handles this internally. If using `pptxviewjs`, set canvas width/height to `logical * dpr` and scale context.
**Warning signs:** Blurry text in slide previews on Mac Retina displays.

### Pitfall 5: Backend Extension Allowlist
**What goes wrong:** Users cannot upload .docx or .pptx files -- upload returns 422.
**Why it happens:** `_ALLOWED_EXTENSIONS` in `artifact_upload_service.py` only includes `.xlsx` and `.xls`. Missing `.docx`, `.doc`, `.pptx`, `.ppt`.
**How to avoid:** Add Office extensions to both the service allowlist and the router display list. Also update the mime-type router on the frontend.
**Warning signs:** "Unsupported file type" errors when uploading Word/PowerPoint files.

### Pitfall 6: Annotation Backend Does Not Exist
**What goes wrong:** Frontend annotation panel has no API to call.
**Why it happens:** This is a new feature -- no annotation model, migration, or endpoints exist.
**How to avoid:** Build a minimal annotation backend: model (artifact_id, slide_index, content, user_id, timestamps), repository, service, and REST endpoints. Include RLS policies per project rules.
**Warning signs:** 404 errors from annotation API calls.

### Pitfall 7: Large File Memory Pressure
**What goes wrong:** Parsing a 10MB XLSX with 100K rows causes browser tab to freeze or crash.
**Why it happens:** SheetJS loads entire workbook into memory; rendering 100K rows in DOM is impossible.
**How to avoid:** UI-SPEC mandates 500-row display limit with truncation warning. Parse only first 500 rows or use SheetJS `sheetRows` option to limit parsing. Show amber banner for truncated data.
**Warning signs:** Browser tab becomes unresponsive, high memory usage in DevTools.

## Code Examples

### XLSX: Parse Workbook with SheetJS
```typescript
import * as XLSX from 'xlsx';

function parseWorkbook(buffer: ArrayBuffer) {
  const workbook = XLSX.read(buffer, { type: 'array', sheetRows: 501 }); // 500 + header
  const sheetNames = workbook.SheetNames;
  const firstSheet = workbook.Sheets[sheetNames[0]];
  const data = XLSX.utils.sheet_to_json<string[]>(firstSheet, { header: 1 });
  const headers = data[0] ?? [];
  const rows = data.slice(1, 501); // Max 500 data rows
  const isTruncated = data.length > 501;
  return { sheetNames, headers, rows, isTruncated, totalRows: data.length - 1 };
}
```

### DOCX: Dual-Engine Render
```typescript
import { renderAsync } from 'docx-preview';

async function renderDocx(buffer: ArrayBuffer, container: HTMLElement) {
  try {
    await renderAsync(buffer, container, undefined, {
      className: 'docx-preview',
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: false,
      breakPages: true,
    });
  } catch {
    // Fallback to mammoth -- use DOMPurify to sanitize HTML output
    const mammoth = await import('mammoth');
    const DOMPurify = (await import('dompurify')).default;
    const result = await mammoth.convertToHtml({ arrayBuffer: buffer });
    const sanitized = DOMPurify.sanitize(result.value);
    container.textContent = ''; // Clear before inserting
    const template = document.createElement('template');
    template.innerHTML = sanitized;
    container.appendChild(template.content);
  }
}
```

### DOCX: Heading Extraction for ToC
```typescript
function extractHeadings(iframeDoc: Document): { id: string; text: string; level: number }[] {
  const headings = iframeDoc.querySelectorAll('h1, h2, h3, h4, h5, h6');
  return Array.from(headings).map((el, i) => {
    const id = el.id || `heading-${i}`;
    if (!el.id) el.id = id;
    return {
      id,
      text: el.textContent?.trim() ?? '',
      level: parseInt(el.tagName[1]),
    };
  });
}
```

### PPTX: Using @kandiforge/pptx-renderer
```typescript
import { PptxRenderer } from '@kandiforge/pptx-renderer';

<PptxRenderer
  pptxSource={arrayBuffer}
  initialSlide={0}
  width={containerWidth}
  height={containerWidth * 9 / 16}
  onSlideChange={(index) => setCurrentSlide(index)}
/>
```

### Mime-Type Router Update
```typescript
// Add to resolveRenderer in mime-type-router.ts:
// After CSV check, before markdown:
const OFFICE_MIMES: Record<string, RendererType> = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
  'application/vnd.ms-excel': 'xlsx',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
  'application/msword': 'docx',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
  'application/vnd.ms-powerpoint': 'pptx',
};
// Also check extensions: xlsx, xls -> 'xlsx'; docx, doc -> 'docx'; pptx, ppt -> 'pptx'
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Server-side LibreOffice conversion | Client-side JS parsers (SheetJS, docx-preview) | 2020+ | No server dependency; faster preview; works offline |
| DOM-based PPTX rendering | Canvas-based PPTX rendering | 2024+ | Better fidelity; proper font/shape rendering; no CSS conflicts |
| Single DOCX engine | Dual-engine (docx-preview + mammoth fallback) | Common pattern | Higher success rate; graceful degradation |

**Deprecated/outdated:**
- `js-xlsx` old package name: Use `xlsx` (same library, renamed)
- PPTXjs (jQuery-based): Outdated; use canvas-based alternatives
- Office Online embed URLs: Requires Microsoft 365 account; not self-hosted friendly

## Open Questions

1. **@kandiforge/pptx-renderer vs pptxviewjs**
   - What we know: Both render PPTX to canvas. @kandiforge is React-native with filmstrip. pptxviewjs is framework-agnostic with Chart.js support.
   - What's unclear: Rendering fidelity comparison. Neither has extensive community testing.
   - Recommendation: Start with @kandiforge/pptx-renderer (React-first API). If rendering quality is poor, swap to pptxviewjs. Keep the renderer behind an abstraction layer.

2. **Annotation Backend Scope**
   - What we know: UI-SPEC defines per-slide annotations with CRUD. No backend exists.
   - What's unclear: Should annotations be scoped to artifact or to artifact+user? Should they support mentions or rich text?
   - Recommendation: Start simple -- plain text, scoped to artifact + slide_index, visible to all workspace members. Follow existing artifact patterns for RLS.

3. **Legacy Format Support (.doc, .xls, .ppt)**
   - What we know: Old binary formats are not supported by docx-preview or SheetJS CE well.
   - What's unclear: Do users upload old-format files?
   - Recommendation: Show `DownloadFallback` with reason "legacy" for `.doc`, `.ppt`. SheetJS handles `.xls` adequately.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 3.1.0 + @testing-library/react 16.2.0 |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && pnpm test -- --run` |
| Full suite command | `cd frontend && pnpm test` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| XLSX-RENDER | Parses workbook, renders table with headers | unit | `cd frontend && pnpm test -- --run src/features/artifacts/components/__tests__/XlsxRenderer.test.tsx` | No -- Wave 0 |
| DOCX-RENDER | Renders docx in iframe, extracts headings for ToC | unit | `cd frontend && pnpm test -- --run src/features/artifacts/components/__tests__/DocxRenderer.test.tsx` | No -- Wave 0 |
| PPTX-RENDER | Renders slides, navigates, maintains aspect ratio | unit | `cd frontend && pnpm test -- --run src/features/artifacts/components/__tests__/PptxRenderer.test.tsx` | No -- Wave 0 |
| ANNOT-PANEL | CRUD annotations with optimistic updates | unit | `cd frontend && pnpm test -- --run src/features/artifacts/components/__tests__/PptxAnnotationPanel.test.tsx` | No -- Wave 0 |
| MIME-ROUTE | Routes office MIME types to correct renderer | unit | `cd frontend && pnpm test -- --run src/features/artifacts/utils/__tests__/mime-type-router.test.ts` | Partial -- exists but no office routes |
| KEYBOARD | Arrow keys navigate slides, Escape closes | unit | Covered in PptxRenderer test | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && pnpm test -- --run`
- **Per wave merge:** `cd frontend && pnpm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/features/artifacts/components/__tests__/XlsxRenderer.test.tsx` -- covers XLSX-RENDER
- [ ] `src/features/artifacts/components/__tests__/DocxRenderer.test.tsx` -- covers DOCX-RENDER
- [ ] `src/features/artifacts/components/__tests__/PptxRenderer.test.tsx` -- covers PPTX-RENDER
- [ ] `src/features/artifacts/components/__tests__/PptxAnnotationPanel.test.tsx` -- covers ANNOT-PANEL
- [ ] `src/features/artifacts/hooks/__tests__/usePptxAnnotations.test.ts` -- covers annotation hook
- [ ] Mock factories for ArrayBuffer test data (small valid .xlsx/.docx/.pptx fixtures)

## Sources

### Primary (HIGH confidence)
- SheetJS official docs: https://docs.sheetjs.com/ -- API, sheet_to_json, sheetRows option
- docx-preview npm: https://www.npmjs.com/package/docx-preview -- renderAsync API, v0.3.7
- mammoth npm: https://www.npmjs.com/package/mammoth -- convertToHtml API, v1.12.0
- Existing codebase: `FilePreviewModal.tsx`, `mime-type-router.ts`, `useFileContent.ts`, `artifact_upload_service.py`

### Secondary (MEDIUM confidence)
- @kandiforge/pptx-renderer npm: https://www.npmjs.com/package/@kandiforge/pptx-renderer -- React canvas renderer, v3.3.0
- pptxviewjs npm: v1.1.9 -- alternative canvas renderer with Chart.js support

### Tertiary (LOW confidence)
- Rendering fidelity comparison between @kandiforge and pptxviewjs -- no independent benchmarks found
- pptxviewjs event API (loadComplete, slideChanged) -- sourced from search results, not verified in code

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM-HIGH -- SheetJS and docx-preview are well-established; PPTX renderer options are newer and less proven
- Architecture: HIGH -- patterns follow existing codebase conventions (dynamic imports, TanStack Query, shadcn components)
- Pitfalls: HIGH -- identified from direct codebase analysis (missing extensions, missing backend, binary fetch gap)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain; library versions unlikely to change significantly)
