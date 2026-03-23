# Phase 3: Excel Renderer - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Preview `.xlsx` and `.xls` files inside the artifact modal as a scrollable table with multi-sheet tab navigation, column resize, frozen header row, and in-sheet search with highlight matching. Must not freeze the browser on large files (up to 10 MB).

</domain>

<decisions>
## Implementation Decisions

### Parsing strategy (XLSX-01, performance)
- Use SheetJS 0.20.3 Community Edition — install from CDN tarball: `pnpm install --save https://cdn.sheetjs.com/xlsx-0.20.3/xlsx-0.20.3.tgz`
- Always pass `{ dense: true }` to `XLSX.read()` for memory efficiency on sparse sheets
- [auto] Selected: `setTimeout(fn, 0)` deferred parse for MVP (Option B from research) — simpler than Web Worker, unblocks the main thread enough to show spinner. Web Worker can be added later if needed.
- Show loading spinner during parse — same pattern as existing `isLoading` state in `useFileContent`
- Apply `MAX_ROWS = 500` cap (identical to CsvRenderer) — never render more than 500 rows
- Show truncation banner: "Showing 500 of N rows. Download for full data." (same text as CsvRenderer)

### Table rendering (XLSX-01)
- Render parsed data using shadcn `Table` + `ScrollArea` (same as CsvRenderer)
- First row treated as header row by default (same as CsvRenderer)
- Display stored/computed cell values — NO formula evaluation (SheetJS CE reads last-saved values)
- Empty cells render as empty `<td>` — no placeholder text

### Sheet tab navigation (XLSX-02)
- Tab bar at bottom of the renderer (below the table, above the truncation banner)
- SheetJS exposes `workbook.SheetNames[]` — render as horizontal scrollable tab strip
- Active sheet highlighted with primary color; inactive tabs use muted styling
- Clicking a tab re-parses that sheet from the same workbook object (no re-read of ArrayBuffer)
- Default: first sheet active on open

### Column resize (XLSX-03)
- Draggable column borders using CSS `resize` on `<th>` elements or a lightweight column-resize handler
- [auto] Selected: CSS-based approach first (simpler). If inadequate, add JS drag handler.
- Frozen header row: Use `position: sticky; top: 0; z-index: 1` on `<thead>` within ScrollArea
- Header row stays visible while scrolling through data rows

### Search within sheet (XLSX-04)
- Search input in the renderer toolbar (above the table)
- Client-side filter: iterate through parsed row data, highlight matching cells
- [auto] Selected: Highlight matching cells with `bg-yellow-200/50` (or `bg-primary/20`) background, show "N matches" count
- Search is per-sheet (switching sheets clears search)
- Debounce search input (300ms) to avoid per-keystroke re-renders on large datasets

### Claude's Discretion
- Exact tab bar styling and scrollable overflow behavior
- Whether to auto-detect header row vs always use first row
- Merged cell handling (SheetJS provides merge ranges — render or flatten)
- Column width defaults (auto-fit or fixed)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing patterns to follow
- `frontend/src/features/artifacts/components/renderers/CsvRenderer.tsx` — Primary reference: 500-row cap, Papa.parse, shadcn Table, ScrollArea, truncation banner
- `frontend/src/features/artifacts/components/FilePreviewModal.tsx` — Dynamic import registration

### Library documentation
- `.planning/research/STACK.md` — SheetJS 0.20.3 CDN install, ArrayBuffer API, `dense: true`, `sheet_to_json()` API
- `.planning/research/SUMMARY.md` §Critical Pitfalls — Pitfall 4 (main thread freeze), Pitfall 5 (unlimited rows)

### Performance concerns
- `.planning/research/PITFALLS.md` — Pitfall 4 (SheetJS synchronous parse), Pitfall 5 (unlimited DOM rows crash), Pitfall 6 (Worker memory leak)
- `.planning/STATE.md` §Blockers — Web Worker bundling in Next.js App Router

### Phase 1 output (dependency)
- `frontend/src/features/artifacts/utils/mime-type-router.ts` — Must have 'xlsx' RendererType
- `frontend/src/features/artifacts/hooks/useFileContent.ts` — Must return ArrayBuffer for 'xlsx' type

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CsvRenderer.tsx`: Direct template — same table structure, row cap, truncation banner. Copy and adapt.
- `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`: shadcn/ui components
- `ScrollArea`: shadcn/ui — wraps the table for scrollable viewport
- `Input`: shadcn/ui — use for search input field

### Established Patterns
- Row cap: `MAX_ROWS = 500` with truncation banner — identical to CsvRenderer
- Lazy loading: `dynamic(() => import('./renderers/XlsxRenderer').then(...))` with `{ ssr: false }`
- Parse result memoization: `React.useMemo` wrapping the parse call — same as CsvRenderer's Papa.parse

### Integration Points
- `FilePreviewModal.tsx`: Add `case 'xlsx':` in renderContent() switch
- New file: `frontend/src/features/artifacts/components/renderers/XlsxRenderer.tsx`
- Package.json: Add `xlsx` from CDN tarball

</code_context>

<specifics>
## Specific Ideas

- "Like Google Sheets preview" — clean table with sheet tabs at bottom
- Search highlight should be subtle (not jarring yellow) — use primary color at low opacity

</specifics>

<deferred>
## Deferred Ideas

- Column sorting (client-side on parsed data) — could be added later
- Formula display bar — low demand, deferred
- Web Worker migration — if setTimeout approach causes visible jank on real files

</deferred>

---

*Phase: 03-excel-renderer*
*Context gathered: 2026-03-22*
